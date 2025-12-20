"""
Free Agency Service for Game Cycle.

Handles free agent signing operations during the offseason free agency stage.
Uses MarketValueCalculator to generate realistic contract offers.
"""

from datetime import date
from typing import Dict, List, Any, Optional, Callable
import logging
import json

from src.persistence.transaction_logger import TransactionLogger
from src.constants.position_normalizer import normalize_position


class FreeAgencyService:
    """
    Service for free agency stage operations.

    Manages:
    - Getting available free agents (team_id = 0)
    - Signing free agents with market-value contracts
    - Processing AI team signings based on team needs
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        valuation_service_factory: Optional[Callable[[int], Any]] = None
    ):
        """
        Initialize the free agency service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
            valuation_service_factory: Optional factory function that creates
                ValuationService instances per team. Signature: (team_id: int) -> ValuationService
                If provided, NPC teams will use the ContractValuationEngine for offers.
                If None, falls back to MarketValueCalculator (legacy behavior).
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded cap helper
        self._cap_helper = None

        # Lazy-loaded persona/attractiveness services for player preferences
        self._persona_service = None
        self._attractiveness_service = None
        self._preference_engine = None

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

        # Optional valuation service factory for sophisticated contract offers
        self._valuation_service_factory = valuation_service_factory

    def _get_cap_helper(self):
        """Get or create cap helper instance.

        Uses season + 1 because during offseason free agency,
        contracts and cap calculations are for the NEXT league year.
        """
        if self._cap_helper is None:
            from .cap_helper import CapHelper
            # Offseason contracts/cap are for NEXT season
            self._cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
        return self._cap_helper

    def _get_persona_service(self):
        """Lazy-load PlayerPersonaService."""
        if self._persona_service is None:
            from src.game_cycle.services.player_persona_service import PlayerPersonaService
            self._persona_service = PlayerPersonaService(
                self._db_path, self._dynasty_id, self._season
            )
        return self._persona_service

    def _get_attractiveness_service(self):
        """Lazy-load TeamAttractivenessService."""
        if self._attractiveness_service is None:
            from src.game_cycle.services.team_attractiveness_service import TeamAttractivenessService
            from src.game_cycle.database.connection import GameCycleDatabase
            db = GameCycleDatabase(self._db_path)
            self._attractiveness_service = TeamAttractivenessService(
                db, self._dynasty_id, self._season
            )
        return self._attractiveness_service

    def _get_preference_engine(self):
        """Lazy-load PlayerPreferenceEngine."""
        if self._preference_engine is None:
            from src.player_management.preference_engine import PlayerPreferenceEngine
            self._preference_engine = PlayerPreferenceEngine()
        return self._preference_engine

    def _get_gm_archetype(self, team_id: int):
        """Get GM archetype for a team.

        Args:
            team_id: Team ID

        Returns:
            GMArchetype instance or None if not available
        """
        try:
            from team_management.gm_archetype_factory import GMArchetypeFactory
            factory = GMArchetypeFactory()
            return factory.get_team_archetype(team_id)
        except Exception as e:
            self._logger.warning(f"Could not load GM archetype for team {team_id}: {e}")
            return None

    def _calculate_npc_contract_offer(
        self,
        player_info: Dict[str, Any],
        team_id: int,
        position: str,
        overall: int,
        age: int,
        years_pro: int
    ) -> Dict[str, Any]:
        """Calculate contract offer for NPC team.

        Uses ContractValuationEngine if available, otherwise falls back
        to MarketValueCalculator.

        Args:
            player_info: Full player info dict
            team_id: Team making the offer
            position: Player position
            overall: Overall rating
            age: Player age
            years_pro: Years in the league

        Returns:
            Dict with aav, years, total_value, signing_bonus, guaranteed (all in dollars)
        """
        # Try valuation engine first if available
        if self._valuation_service_factory:
            try:
                valuation_service = self._valuation_service_factory(team_id)
                gm_archetype = self._get_gm_archetype(team_id)

                # Build player data dict for valuation engine
                player_data = {
                    "position": position,
                    "overall_rating": overall,
                    "age": age,
                }

                # Add optional fields if available
                if "attributes" in player_info:
                    player_data["attributes"] = player_info["attributes"]

                valuation_result = valuation_service.valuate_player(
                    player_data=player_data,
                    team_id=team_id,
                    gm_archetype=gm_archetype,
                )

                # Extract offer details
                offer = valuation_result.offer
                return {
                    "aav": offer.aav,
                    "years": offer.years,
                    "total_value": offer.total_value,
                    "signing_bonus": offer.signing_bonus,
                    "guaranteed": offer.guaranteed_money,
                }

            except Exception as e:
                self._logger.warning(
                    f"Valuation engine failed for team {team_id}, "
                    f"falling back to MarketValueCalculator: {e}"
                )

        # Fallback to legacy MarketValueCalculator
        from offseason.market_value_calculator import MarketValueCalculator
        market_calculator = MarketValueCalculator()

        market_value = market_calculator.calculate_player_value(
            position=position,
            overall=overall,
            age=age,
            years_pro=years_pro
        )

        # Convert from millions to dollars
        return {
            "aav": int(market_value["aav"] * 1_000_000),
            "years": market_value["years"],
            "total_value": int(market_value["total_value"] * 1_000_000),
            "signing_bonus": int(market_value["signing_bonus"] * 1_000_000),
            "guaranteed": int(market_value["guaranteed"] * 1_000_000),
        }

    def _get_dev_type(self, archetype_id: Optional[str]) -> str:
        """
        Get development type from archetype.

        Args:
            archetype_id: Archetype identifier

        Returns:
            Development type: "E" (early), "N" (normal), or "L" (late)
        """
        if not archetype_id:
            return "N"
        try:
            from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry
            registry = ArchetypeRegistry()
            archetype = registry.get_archetype(archetype_id)
            if archetype and archetype.development_curve:
                return {"early": "E", "normal": "N", "late": "L"}.get(archetype.development_curve, "N")
        except Exception:
            pass
        return "N"

    def _calculate_age(self, birthdate: Optional[str]) -> int:
        """Calculate age from birthdate string.

        Args:
            birthdate: Birthdate in YYYY-MM-DD format

        Returns:
            Age in years, defaults to 25 if birthdate is invalid
        """
        if not birthdate:
            return 25  # Default
        try:
            birth_year = int(birthdate.split("-")[0])
            return self._season - birth_year
        except (ValueError, IndexError):
            return 25

    def _estimate_role(self, team_id: int, position: str, overall: int) -> str:
        """Estimate player's role on the team.

        Simple heuristic based on overall rating:
        - 85+ overall: starter
        - 70-84 overall: rotational
        - <70 overall: backup

        Args:
            team_id: Team ID (reserved for future roster comparison)
            position: Player position
            overall: Player overall rating

        Returns:
            Role string: 'starter', 'rotational', or 'backup'
        """
        if overall >= 85:
            return "starter"
        elif overall >= 70:
            return "rotational"
        else:
            return "backup"

    def _check_player_acceptance(
        self,
        player_id: int,
        player_info: Dict[str, Any],
        team_id: int,
        aav: int,
        total_value: int,
        years: int,
        guaranteed: int,
        signing_bonus: int,
        position: str,
        overall: int
    ) -> Dict[str, Any]:
        """Check if player accepts the offer based on preferences.

        Uses player persona and team attractiveness to evaluate whether
        the player would accept a contract offer from the team.

        Args:
            player_id: Player ID
            player_info: Player info dict
            team_id: Team ID making the offer
            aav: Average annual value in dollars
            total_value: Total contract value in dollars
            years: Contract length
            guaranteed: Guaranteed money in dollars
            signing_bonus: Signing bonus in dollars
            position: Player position
            overall: Player overall rating

        Returns:
            Dict with:
                - accepted: bool
                - probability: float (0.0-1.0)
                - concerns: List[str]
                - interest_level: str ("low", "medium", "high")
        """
        try:
            from src.player_management.preference_engine import ContractOffer

            # Get or generate player persona
            persona_service = self._get_persona_service()
            persona = persona_service.get_persona(player_id)

            if persona is None:
                # Generate persona for this player
                age = self._calculate_age(player_info.get("birthdate"))
                persona = persona_service.generate_persona(
                    player_id=player_id,
                    age=age,
                    overall=overall,
                    position=position,
                    team_id=0,  # Free agent, no current team
                )
                persona_service.save_persona(persona)

            # Get team attractiveness
            attractiveness_service = self._get_attractiveness_service()
            team_attractiveness = attractiveness_service.get_team_attractiveness(team_id)

            # Build contract offer
            offer = ContractOffer(
                team_id=team_id,
                aav=aav,
                total_value=total_value,
                years=years,
                guaranteed=guaranteed,
                signing_bonus=signing_bonus,
                market_aav=aav,  # At market value for FA signings
                role=self._estimate_role(team_id, position, overall)
            )

            # Evaluate offer
            preference_engine = self._get_preference_engine()
            accepted, probability, concerns = preference_engine.should_accept_offer(
                persona=persona,
                team=team_attractiveness,
                offer=offer,
                is_current_team=False,  # FA is not on any team
                is_drafting_team=(team_id == persona.drafting_team_id)
            )

            # Determine interest level
            if probability >= 0.75:
                interest_level = "high"
            elif probability >= 0.45:
                interest_level = "medium"
            else:
                interest_level = "low"

            return {
                "accepted": accepted,
                "probability": probability,
                "concerns": concerns,
                "interest_level": interest_level
            }

        except Exception as e:
            self._logger.error(f"Preference check failed for player {player_id}: {e}")
            # Fallback: Accept the offer (don't block signing due to preference system errors)
            return {
                "accepted": True,
                "probability": 0.50,
                "concerns": [],
                "interest_level": "medium"
            }

    def get_cap_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get salary cap summary for a team.

        Args:
            team_id: Team ID

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant
        """
        return self._get_cap_helper().get_cap_summary(team_id)

    def get_available_free_agents(
        self,
        position_filter: Optional[str] = None,
        min_overall: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all available free agents (team_id = 0).

        Args:
            position_filter: Optional position to filter by
            min_overall: Optional minimum overall rating

        Returns:
            List of player dictionaries with estimated contract values
        """
        from database.player_roster_api import PlayerRosterAPI
        from offseason.market_value_calculator import MarketValueCalculator

        roster_api = PlayerRosterAPI(self._db_path)
        market_calculator = MarketValueCalculator()

        # Get all free agents
        free_agents = roster_api.get_free_agents(self._dynasty_id)

        result = []
        for player in free_agents:
            player_id = player.get("player_id")

            # Extract position from JSON array
            positions = player.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else ""

            # Apply position filter if specified
            if position_filter and position.lower() != position_filter.lower():
                continue

            # Extract overall and potential from JSON attributes
            attributes = player.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 0)
            potential = attributes.get("potential", 0)

            # Apply min overall filter if specified
            if min_overall and overall < min_overall:
                continue

            # Calculate age from birthdate
            age = 0
            birthdate = player.get("birthdate")
            if birthdate:
                try:
                    birth_year = int(birthdate.split("-")[0])
                    age = self._season - birth_year
                except (ValueError, IndexError):
                    pass

            years_pro = player.get("years_pro", 0)

            # Get development type from archetype
            archetype_id = player.get("archetype_id")
            dev_type = self._get_dev_type(archetype_id)

            # Calculate market value for contract estimate
            market_value = market_calculator.calculate_player_value(
                position=position,
                overall=overall,
                age=age,
                years_pro=years_pro
            )

            # Convert to dollars
            estimated_aav = int(market_value["aav"] * 1_000_000)
            estimated_years = market_value["years"]
            estimated_total = int(market_value["total_value"] * 1_000_000)

            result.append({
                "player_id": player_id,
                "name": f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
                "position": position,
                "age": age,
                "overall": overall,
                "potential": potential,
                "dev_type": dev_type,
                "years_pro": years_pro,
                "estimated_aav": estimated_aav,
                "estimated_years": estimated_years,
                "estimated_total": estimated_total,
            })

        # Sort by overall rating (highest first)
        result.sort(key=lambda x: x.get("overall", 0), reverse=True)

        return result

    def sign_free_agent(
        self,
        player_id: int,
        team_id: int,
        player_info: Optional[Dict[str, Any]] = None,
        skip_preference_check: bool = False,
        fa_guidance: Optional[Any] = None,
        use_valuation_engine: bool = False,
        contract_terms: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sign a free agent to a team with a market-value contract.

        Includes player preference check - players may reject offers based on
        their persona and the team's attractiveness.

        Budget stance modifiers (if fa_guidance provided):
        - AGGRESSIVE: Offer 5-10% above market (increases acceptance chance)
        - MODERATE: Offer market value (no modifier)
        - CONSERVATIVE: Offer 5-10% below market (decreases acceptance chance)

        Args:
            player_id: Player ID to sign
            team_id: Team ID signing the player
            player_info: Optional player info dict (to avoid extra DB query)
            skip_preference_check: If True, bypasses player preference check
            fa_guidance: Optional FAGuidance with budget_stance directive
            use_valuation_engine: If True, uses ContractValuationEngine for NPC teams
                (requires valuation_service_factory to be set). User team always
                uses MarketValueCalculator regardless of this setting.
            contract_terms: Optional dict with pre-negotiated contract terms from
                GM proposal (aav, years, total, guaranteed, signing_bonus).
                If provided, these terms are used instead of recalculating.

        Returns:
            Dict with:
                - success: bool
                - new_contract_id: int (if successful)
                - contract_details: dict with AAV, years, etc.
                - player_name: str
                - error_message: str (if failed)
                - rejection_reason: str (if player declined)
                - concerns: List[str] (if player declined)
                - acceptance_probability: float (if player declined)
                - interest_level: str (if player declined)
                - budget_modifier: float (if fa_guidance provided)
        """
        from salary_cap.cap_database_api import CapDatabaseAPI
        from salary_cap.contract_manager import ContractManager
        from salary_cap.cap_calculator import CapCalculator
        from database.player_roster_api import PlayerRosterAPI

        try:
            roster_api = PlayerRosterAPI(self._db_path)
            cap_api = CapDatabaseAPI(self._db_path)
            contract_manager = ContractManager(self._db_path)
            cap_calculator = CapCalculator(self._db_path)

            # Get player info if not provided
            if player_info is None:
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not found",
                }

            # Verify player is a free agent
            current_team_id = player_info.get("team_id", -1)
            if current_team_id != 0:
                return {
                    "success": False,
                    "error_message": f"Player is not a free agent (team_id={current_team_id})",
                }

            # Extract player details
            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else ""

            attributes = player_info.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 70)

            # Calculate age
            age = 25
            birthdate = player_info.get("birthdate")
            if birthdate:
                try:
                    birth_year = int(birthdate.split("-")[0])
                    age = self._season - birth_year
                except (ValueError, IndexError):
                    pass

            years_pro = player_info.get("years_pro", 3)
            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Calculate contract offer:
            # 1. Use contract_terms if provided (from GM proposal approval)
            # 2. Otherwise, use valuation engine for NPCs if enabled
            # 3. Otherwise, fallback to MarketValueCalculator
            if contract_terms:
                # Use pre-negotiated terms from GM proposal
                aav = contract_terms.get("aav", 0)
                years = contract_terms.get("years", 1)
                total_value = contract_terms.get("total", contract_terms.get("total_value", aav * years))
                signing_bonus = contract_terms.get("signing_bonus", 0)
                guaranteed = contract_terms.get("guaranteed", 0)
                self._logger.info(
                    f"Using proposal contract terms for {player_name}: "
                    f"{years}yr, ${aav:,} AAV, ${total_value:,} total"
                )
            elif use_valuation_engine:
                contract_offer = self._calculate_npc_contract_offer(
                    player_info=player_info,
                    team_id=team_id,
                    position=position,
                    overall=overall,
                    age=age,
                    years_pro=years_pro
                )
                aav = contract_offer["aav"]
                years = contract_offer["years"]
                total_value = contract_offer["total_value"]
                signing_bonus = contract_offer["signing_bonus"]
                guaranteed = contract_offer["guaranteed"]
            else:
                # Legacy MarketValueCalculator path (user team or NPC without valuation engine)
                from offseason.market_value_calculator import MarketValueCalculator
                market_calculator = MarketValueCalculator()

                market_value = market_calculator.calculate_player_value(
                    position=position,
                    overall=overall,
                    age=age,
                    years_pro=years_pro
                )

                # Convert from millions to dollars
                total_value = int(market_value["total_value"] * 1_000_000)
                aav = int(market_value["aav"] * 1_000_000)
                signing_bonus = int(market_value["signing_bonus"] * 1_000_000)
                guaranteed = int(market_value["guaranteed"] * 1_000_000)
                years = market_value["years"]

            # Apply budget stance modifier (Tollgate 7: Owner directive integration)
            budget_modifier = 1.0
            if fa_guidance:
                import random
                budget_stance = getattr(fa_guidance, 'budget_stance', 'moderate').lower()

                if budget_stance == 'aggressive':
                    # Offer 5-10% above market (better chance of acceptance)
                    budget_modifier = random.uniform(1.05, 1.10)
                elif budget_stance == 'conservative':
                    # Offer 5-10% below market (lower chance of acceptance)
                    budget_modifier = random.uniform(0.90, 0.95)
                # else: moderate = 1.0 (no change)

                # Apply modifier to contract values
                total_value = int(total_value * budget_modifier)
                aav = int(aav * budget_modifier)
                signing_bonus = int(signing_bonus * budget_modifier)
                guaranteed = int(guaranteed * budget_modifier)

                self._logger.info(
                    f"FA contract for {player_name}: {budget_stance.upper()} stance, "
                    f"{budget_modifier:.2f}x modifier"
                )

            # Player preference check (unless skipped)
            if not skip_preference_check:
                acceptance_result = self._check_player_acceptance(
                    player_id=player_id,
                    player_info=player_info,
                    team_id=team_id,
                    aav=aav,
                    total_value=total_value,
                    years=years,
                    guaranteed=guaranteed,
                    signing_bonus=signing_bonus,
                    position=position,
                    overall=overall
                )

                if not acceptance_result["accepted"]:
                    self._logger.info(
                        f"FA {player_name} declined offer from team {team_id}: "
                        f"{acceptance_result['concerns']}"
                    )
                    return {
                        "success": False,
                        "error_message": "Player declined offer",
                        "player_name": player_name,
                        "rejection_reason": "Player declined based on preferences",
                        "concerns": acceptance_result["concerns"],
                        "acceptance_probability": acceptance_result["probability"],
                        "interest_level": acceptance_result["interest_level"],
                    }

            # Check cap space for NEXT season (offseason signings)
            cap_space = cap_calculator.calculate_team_cap_space(
                team_id=team_id,
                season=self._season + 1,  # Cap space for next league year
                dynasty_id=self._dynasty_id
            )

            if aav > cap_space:
                return {
                    "success": False,
                    "error_message": f"Insufficient cap space. Need ${aav:,}, have ${cap_space:,}",
                }

            # Generate year-by-year base salaries
            base_salaries = []
            remaining_after_bonus = total_value - signing_bonus
            for i in range(years):
                year_weight = 1.0 + (i * 0.05)
                total_weight = sum(1.0 + (j * 0.05) for j in range(years))
                year_salary = int((remaining_after_bonus * year_weight) / total_weight)
                base_salaries.append(year_salary)

            # Generate guaranteed amounts (front-loaded)
            guaranteed_amounts = []
            remaining_guarantee = guaranteed - signing_bonus
            for i in range(years):
                if i < years // 2 + 1:
                    year_guarantee = remaining_guarantee // (years // 2 + 1)
                    guaranteed_amounts.append(year_guarantee)
                else:
                    guaranteed_amounts.append(0)

            # Create new contract (starts NEXT season during offseason)
            new_contract_id = contract_manager.create_contract(
                player_id=player_id,
                team_id=team_id,
                dynasty_id=self._dynasty_id,
                contract_years=years,
                total_value=total_value,
                signing_bonus=signing_bonus,
                base_salaries=base_salaries,
                guaranteed_amounts=guaranteed_amounts,
                contract_type="VETERAN",
                season=self._season + 1  # Contract starts NEXT league year
            )

            # Calculate Year-1 cap hit (SSOT for cap projections)
            # Matches contract_manager.create_contract() calculation
            proration_years = min(years, 5)
            year1_bonus_proration = signing_bonus // proration_years if proration_years > 0 else 0
            year1_cap_hit = base_salaries[0] + year1_bonus_proration

            # Update player's team_id
            roster_api.update_player_team(
                dynasty_id=self._dynasty_id,
                player_id=player_id,
                new_team_id=team_id
            )

            # Update player's contract_id to reference the new contract
            roster_api.update_player_contract_id(
                dynasty_id=self._dynasty_id,
                player_id=player_id,
                contract_id=new_contract_id
            )

            self._logger.info(
                f"Signed FA {player_name} ({position}) to team {team_id}: {years} years, ${total_value:,}"
            )

            # Log transaction for audit trail
            self._transaction_logger.log_transaction(
                dynasty_id=self._dynasty_id,
                season=self._season + 1,  # Contract is for next season
                transaction_type="UFA_SIGNING",
                player_id=player_id,
                player_name=player_name,
                position=position,
                from_team_id=None,  # From free agency
                to_team_id=team_id,
                transaction_date=date(self._season + 1, 3, 15),  # FA period date (next year)
                details={
                    "contract_years": years,
                    "contract_value": total_value,
                    "guaranteed": guaranteed,
                }
            )

            return {
                "success": True,
                "new_contract_id": new_contract_id,
                "player_name": player_name,
                "contract_details": {
                    "years": years,
                    "total_value": total_value,
                    "aav": aav,
                    "guaranteed": guaranteed,
                    "signing_bonus": signing_bonus,
                    "year1_cap_hit": year1_cap_hit,  # SSOT for cap projections
                    "position": position,
                    "overall": overall,
                    "age": age,
                },
                "budget_modifier": budget_modifier,
            }

        except Exception as e:
            self._logger.error(f"Failed to sign free agent {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def evaluate_player_interest(
        self,
        player_id: int,
        team_id: int,
        player_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate a player's interest level in a team BEFORE making an offer.

        Use this to show UI indicators and help users understand likelihood
        of signing before committing.

        Args:
            player_id: Player ID
            team_id: Team ID
            player_info: Optional player info dict

        Returns:
            Dict with:
                - interest_score: int (0-100) - normalized team score
                - interest_level: str ("very_low", "low", "medium", "high", "very_high")
                - acceptance_probability: float
                - concerns: List[str]
                - suggested_premium: float (e.g., 1.15 = offer 15% above market)
                - team_score: int (0-100) - raw team score for backwards compatibility
                - persona_type: str - player's persona type for UI hints
        """
        try:
            from database.player_roster_api import PlayerRosterAPI
            from offseason.market_value_calculator import MarketValueCalculator
            from src.player_management.preference_engine import ContractOffer

            roster_api = PlayerRosterAPI(self._db_path)
            market_calculator = MarketValueCalculator()

            # Get player info if not provided
            if player_info is None:
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "interest_level": "unknown",
                    "acceptance_probability": 0.0,
                    "concerns": ["Player not found"],
                    "suggested_premium": 1.0,
                    "team_score": 0
                }

            # Extract player details
            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else ""

            attributes = player_info.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 70)

            age = self._calculate_age(player_info.get("birthdate"))
            years_pro = player_info.get("years_pro", 3)

            # Calculate market value
            market_value = market_calculator.calculate_player_value(
                position=position,
                overall=overall,
                age=age,
                years_pro=years_pro
            )
            aav = int(market_value["aav"] * 1_000_000)
            total_value = int(market_value["total_value"] * 1_000_000)
            guaranteed = int(market_value["guaranteed"] * 1_000_000)
            years = market_value["years"]
            signing_bonus = int(market_value["signing_bonus"] * 1_000_000)

            # Get or generate persona
            persona_service = self._get_persona_service()
            persona = persona_service.get_persona(player_id)

            if persona is None:
                persona = persona_service.generate_persona(
                    player_id=player_id,
                    age=age,
                    overall=overall,
                    position=position,
                    team_id=0,
                )
                persona_service.save_persona(persona)

            # Get team attractiveness
            attractiveness_service = self._get_attractiveness_service()
            team_attractiveness = attractiveness_service.get_team_attractiveness(team_id)

            # Build hypothetical offer at market value
            offer = ContractOffer(
                team_id=team_id,
                aav=aav,
                total_value=total_value,
                years=years,
                guaranteed=guaranteed,
                signing_bonus=signing_bonus,
                market_aav=aav,
                role=self._estimate_role(team_id, position, overall)
            )

            # Get preference engine evaluation
            preference_engine = self._get_preference_engine()
            team_score = preference_engine.calculate_team_score(
                persona=persona,
                team=team_attractiveness,
                offer=offer,
                is_current_team=False,
                is_drafting_team=(team_id == persona.drafting_team_id)
            )
            probability = preference_engine.calculate_acceptance_probability(
                persona=persona,
                team_score=team_score,
                offer_vs_market=1.0  # At market value
            )
            concerns = preference_engine.get_concerns(persona, team_attractiveness, offer)

            # Determine interest level based on team_score (0-100)
            # Color bands: Green (80+), Blue (65-79), Gray (50-64), Orange (35-49), Red (<35)
            if team_score >= 80:
                interest_level = "very_high"
                suggested_premium = 0.95  # Can even get discount
            elif team_score >= 65:
                interest_level = "high"
                suggested_premium = 1.0  # No premium needed
            elif team_score >= 50:
                interest_level = "medium"
                suggested_premium = 1.10  # 10% above market
            elif team_score >= 35:
                interest_level = "low"
                suggested_premium = 1.20  # 20% above market
            else:
                interest_level = "very_low"
                suggested_premium = 1.30  # 30% above market (if even possible)

            return {
                "interest_score": team_score,  # Normalized 0-100 for UI
                "interest_level": interest_level,
                "acceptance_probability": probability,
                "concerns": concerns,
                "suggested_premium": suggested_premium,
                "team_score": team_score,  # Backwards compatibility
                "persona_type": persona.persona_type.value  # For UI hints
            }

        except Exception as e:
            self._logger.error(f"Interest evaluation failed for player {player_id}: {e}")
            return {
                "interest_score": 50,
                "interest_level": "unknown",
                "acceptance_probability": 0.5,
                "concerns": [],
                "suggested_premium": 1.0,
                "team_score": 50,
                "persona_type": "unknown"
            }

    def get_player_persona_data(self, player_id: int) -> Dict[str, Any]:
        """Get full persona data for signing dialog.

        Returns detailed persona information for UI display including
        persona type and preference weights.

        Args:
            player_id: Player ID

        Returns:
            Dict with persona_type and preference weights (0-100)
        """
        try:
            persona_service = self._get_persona_service()
            persona = persona_service.get_persona(player_id)

            if persona is None:
                return {
                    "persona_type": "unknown",
                    "money_importance": 50,
                    "winning_importance": 50,
                    "location_importance": 50,
                    "playing_time_importance": 50,
                    "loyalty_importance": 50,
                    "market_size_importance": 50
                }

            return {
                "persona_type": persona.persona_type.value,
                "money_importance": persona.money_importance,
                "winning_importance": persona.winning_importance,
                "location_importance": persona.location_importance,
                "playing_time_importance": persona.playing_time_importance,
                "loyalty_importance": persona.loyalty_importance,
                "market_size_importance": persona.market_size_importance
            }

        except Exception as e:
            self._logger.error(f"Failed to get persona data for player {player_id}: {e}")
            return {
                "persona_type": "unknown",
                "money_importance": 50,
                "winning_importance": 50,
                "location_importance": 50,
                "playing_time_importance": 50,
                "loyalty_importance": 50,
                "market_size_importance": 50
            }

    def process_ai_signings(
        self,
        user_team_id: int,
        max_signings_per_team: int = 3,
        max_attempts_per_signing: int = 3
    ) -> Dict[str, Any]:
        """
        Process AI team free agent signings with player preference awareness.

        For each AI team (not user_team_id):
        1. Get team's positional needs (simple gap analysis)
        2. Evaluate player interest before offering
        3. Sign if cap space allows and player accepts
        4. Handle rejections and try other players

        Args:
            user_team_id: User's team ID (to skip)
            max_signings_per_team: Maximum signings per AI team
            max_attempts_per_signing: Max players to try per position need

        Returns:
            Dict with:
                - signings: List of signing info dicts
                - events: List of event strings for UI
                - rejections: List of rejection info dicts
        """
        from team_management.teams.team_loader import TeamDataLoader
        from database.player_roster_api import PlayerRosterAPI
        from salary_cap.cap_calculator import CapCalculator

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()
        roster_api = PlayerRosterAPI(self._db_path)
        cap_calculator = CapCalculator(self._db_path)

        signings = []
        events = []
        rejections = []

        # Get current free agent pool
        available_fas = self.get_available_free_agents()

        for team in all_teams:
            team_id = team.team_id

            # Skip user's team
            if team_id == user_team_id:
                continue

            # Get team's cap space for NEXT season (offseason signings)
            cap_space = cap_calculator.calculate_team_cap_space(
                team_id=team_id,
                season=self._season + 1,  # Cap space for next league year
                dynasty_id=self._dynasty_id
            )

            # Skip teams with no cap space
            if cap_space <= 0:
                continue

            # Get team's positional needs (simple approach: look at roster gaps)
            team_needs = self._get_team_positional_needs(team_id, roster_api)

            signings_made = 0

            # Try to fill needs with available FAs
            for need_position in team_needs:
                if signings_made >= max_signings_per_team:
                    break

                # Try multiple players at this position
                attempts = 0
                signed = False

                for fa in available_fas[:]:  # Iterate over copy
                    if signed or attempts >= max_attempts_per_signing:
                        break

                    if fa["position"].lower() != need_position.lower():
                        continue

                    if fa["estimated_aav"] > cap_space:
                        continue

                    # Evaluate player interest first
                    interest = self.evaluate_player_interest(
                        fa["player_id"], team_id, None
                    )

                    # Skip if interest is very low and we've tried others
                    if interest["interest_level"] == "low" and attempts > 0:
                        continue

                    attempts += 1

                    # Try to sign (will check preferences internally)
                    # Use valuation engine if available, otherwise fallback to legacy calculator
                    result = self.sign_free_agent(
                        fa["player_id"], team_id, None,
                        skip_preference_check=False,  # Check preferences
                        use_valuation_engine=True  # Enable valuation engine for NPC teams
                    )

                    if result["success"]:
                        signings.append({
                            "player_id": fa["player_id"],
                            "player_name": result["player_name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "contract_details": result.get("contract_details", {}),
                        })
                        events.append(
                            f"{team.abbreviation} signed FA {result['player_name']}"
                        )

                        # Update cap space
                        cap_space -= fa["estimated_aav"]
                        signings_made += 1

                        # Remove from available pool
                        available_fas.remove(fa)
                        signed = True
                    else:
                        # Player rejected - log it
                        rejections.append({
                            "player_id": fa["player_id"],
                            "player_name": fa["name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "reason": result.get("rejection_reason"),
                            "concerns": result.get("concerns", [])
                        })

        self._logger.info(
            f"AI FA signings complete: {len(signings)} signed, {len(rejections)} rejected"
        )

        return {
            "signings": signings,
            "events": events,
            "rejections": rejections,
        }

    def _get_team_positional_needs(
        self,
        team_id: int,
        roster_api
    ) -> List[str]:
        """
        Get list of positional needs for a team.

        Simple approach: Check for positions with few or no players.

        Args:
            team_id: Team ID
            roster_api: PlayerRosterAPI instance

        Returns:
            List of position strings that need filling
        """
        # Key positions every team needs
        key_positions = [
            "quarterback", "running_back", "wide_receiver", "tight_end",
            "left_tackle", "left_guard", "center", "right_guard", "right_tackle",
            "defensive_end", "defensive_tackle", "linebacker",
            "cornerback", "safety"
        ]

        # Get team roster
        roster = roster_api.get_team_roster(self._dynasty_id, team_id)

        # Count players at each position
        position_counts = {}
        for player in roster:
            positions = player.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            for pos in positions:
                pos_lower = pos.lower()
                position_counts[pos_lower] = position_counts.get(pos_lower, 0) + 1

        # Find positions with gaps (< 2 players)
        needs = []
        for pos in key_positions:
            count = position_counts.get(pos, 0)
            if count < 2:
                needs.append(pos)

        return needs[:5]  # Limit to top 5 needs

    def get_team_cap_space(self, team_id: int) -> int:
        """
        Get available cap space for a team for NEXT season.

        During offseason, cap space is calculated for the upcoming
        league year, not the just-completed season.

        Args:
            team_id: Team ID

        Returns:
            Available cap space in dollars
        """
        from salary_cap.cap_calculator import CapCalculator

        calculator = CapCalculator(self._db_path)
        return calculator.calculate_team_cap_space(
            team_id=team_id,
            season=self._season + 1,  # Next season during offseason
            dynasty_id=self._dynasty_id
        )