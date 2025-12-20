"""
Re-signing Service for Game Cycle.

Handles player re-signing decisions during the offseason re-signing stage.
Uses MarketValueCalculator to generate realistic contract offers.
"""

from datetime import date
from typing import Dict, List, Any, Optional, Tuple
import logging

from src.persistence.transaction_logger import TransactionLogger


class ResigningService:
    """
    Service for re-signing stage operations.

    Manages:
    - Getting expiring contracts for a team
    - Re-signing players with market-value contracts
    - Releasing players to free agency
    - Processing AI team re-signing decisions
    """

    def __init__(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        valuation_service: Optional[Any] = None
    ):
        """
        Initialize the re-signing service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
            valuation_service: Optional ValuationService for contract valuations
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded cap helper
        self._cap_helper = None

        # Lazy-loaded persona/attractiveness services
        self._persona_service = None
        self._attractiveness_service = None
        self._preference_engine = None

        # Optional valuation service for sophisticated contract calculations
        self._valuation_service = valuation_service

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

    def _get_cap_helper(self):
        """Get or create cap helper instance.

        Uses season + 1 because during offseason re-signing,
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

    def _calculate_age(self, birthdate: Optional[str]) -> int:
        """Calculate age from birthdate string."""
        if not birthdate:
            return 25  # Default
        try:
            birth_year = int(birthdate.split("-")[0])
            return self._season - birth_year
        except (ValueError, IndexError):
            return 25

    def _estimate_role(self, team_id: int, position: str, overall: int) -> str:
        """Estimate player's role on the team.

        Simple heuristic:
        - 85+ overall: starter
        - 70-84 overall: rotational
        - <70 overall: backup
        """
        if overall >= 85:
            return "starter"
        elif overall >= 70:
            return "rotational"
        else:
            return "backup"

    def _get_dev_type(self, archetype_id: Optional[str]) -> str:
        """
        Get development type abbreviation from archetype ID.

        Args:
            archetype_id: Archetype ID to look up

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
        market_aav: int,
        position: str,
        overall: int
    ) -> Dict[str, Any]:
        """Check if player accepts the re-signing offer based on preferences.

        Key difference from FA: is_current_team=True gives loyalty bonus.

        Returns:
            Dict with:
                - accepted: bool
                - probability: float (0.0-1.0)
                - concerns: List[str]
                - interest_level: str ("low", "medium", "high")
        """
        from src.player_management.preference_engine import ContractOffer

        try:
            # Get or generate player persona
            persona_service = self._get_persona_service()
            persona = persona_service.get_persona(player_id)

            if persona is None:
                age = self._calculate_age(player_info.get("birthdate"))
                persona = persona_service.generate_persona(
                    player_id=player_id,
                    age=age,
                    overall=overall,
                    position=position,
                    team_id=team_id,  # Current team, unlike FA
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
                market_aav=market_aav,
                role=self._estimate_role(team_id, position, overall)
            )

            # Evaluate offer - KEY: is_current_team=True for re-signing
            preference_engine = self._get_preference_engine()
            accepted, probability, concerns = preference_engine.should_accept_offer(
                persona=persona,
                team=team_attractiveness,
                offer=offer,
                is_current_team=True,  # KEY DIFFERENCE: Loyalty bonus applies
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
            # Fallback: Accept (don't block re-signing due to preference system errors)
            return {
                "accepted": True,
                "probability": 0.50,
                "concerns": [],
                "interest_level": "medium"
            }

    def get_cap_summary(self, team_id: int) -> dict:
        """
        Get salary cap summary for a team.

        Args:
            team_id: Team ID

        Returns:
            Dict with salary_cap_limit, total_spending, available_space,
            dead_money, is_compliant
        """
        return self._get_cap_helper().get_cap_summary(team_id)

    def get_expiring_contracts(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get all players with expiring contracts for a team.

        Args:
            team_id: Team ID to get expiring contracts for

        Returns:
            List of player dictionaries with contract info
        """
        from salary_cap.cap_database_api import CapDatabaseAPI
        from database.player_roster_api import PlayerRosterAPI

        cap_api = CapDatabaseAPI(self._db_path)
        roster_api = PlayerRosterAPI(self._db_path)

        # Get all active contracts for this team
        contracts = cap_api.get_team_contracts(
            team_id=team_id,
            dynasty_id=self._dynasty_id,
            season=self._season,
            active_only=True
        )

        expiring_players = []

        for contract in contracts:
            player_id = contract.get("player_id")
            years_remaining = contract.get("end_year", self._season) - self._season + 1

            # Contract expires if years_remaining <= 1
            if years_remaining <= 1:
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

                if player_info:
                    # Extract position from JSON array
                    positions = player_info.get("positions", [])
                    if isinstance(positions, str):
                        import json
                        positions = json.loads(positions)
                    position = positions[0] if positions else ""

                    # Extract overall and potential from JSON attributes
                    attributes = player_info.get("attributes", {})
                    if isinstance(attributes, str):
                        import json
                        attributes = json.loads(attributes)
                    overall = attributes.get("overall", 0)
                    potential = attributes.get("potential", overall)

                    # Calculate age from birthdate if available
                    age = 0
                    birthdate = player_info.get("birthdate")
                    if birthdate:
                        from datetime import datetime
                        try:
                            birth_year = int(birthdate.split("-")[0])
                            age = self._season - birth_year
                        except (ValueError, IndexError):
                            pass

                    # Calculate AAV from contract total_value
                    total_value = contract.get("total_value", 0)
                    contract_years = contract.get("contract_years", 1)
                    aav = total_value // contract_years if contract_years > 0 else 0

                    # Get development type from archetype
                    archetype_id = player_info.get("archetype_id")
                    dev_type = self._get_dev_type(archetype_id)

                    expiring_players.append({
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": position,
                        "age": age,
                        "overall": overall,
                        "potential": potential,
                        "dev_type": dev_type,
                        "years_pro": player_info.get("years_pro", 0),
                        "salary": aav,
                        "years_remaining": years_remaining,
                        "contract_id": contract.get("contract_id"),
                    })

        # Sort by overall rating (highest first)
        expiring_players.sort(key=lambda x: x.get("overall", 0), reverse=True)

        return expiring_players

    def get_gm_rejection_recommendations(
        self,
        team_id: int,
        expiring_players: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get GM's recommendations for players NOT to extend.

        Evaluates each expiring player using _should_ai_resign() and
        returns those the GM recommends releasing with reasoning.

        Args:
            team_id: Team ID
            expiring_players: Optional list of expiring players (to avoid re-query)

        Returns:
            List of dicts with:
                - player_id: int
                - player_name: str
                - position: str
                - age: int
                - overall: int
                - current_salary: int
                - reason: str (primary rejection reason)
                - concerns: List[str] (detailed concerns)
                - acceptance_probability: float (0.0-1.0)
                - category: str ("age", "performance", "preference", "expendable")
        """
        # Get expiring contracts if not provided
        if expiring_players is None:
            expiring_players = self.get_expiring_contracts(team_id)

        rejections = []

        for player in expiring_players:
            # Run GM evaluation logic
            should_attempt, probability, concerns = self._should_ai_resign(
                player, team_id
            )

            # Only include players GM recommends NOT extending
            if not should_attempt:
                # Determine primary category
                category = self._categorize_rejection_reason(concerns, player)

                rejection = {
                    "player_id": player["player_id"],
                    "player_name": player.get("name", "Unknown"),
                    "position": player.get("position", ""),
                    "age": player.get("age", 0),
                    "overall": player.get("overall", 0),
                    "current_salary": player.get("salary", 0),
                    "reason": concerns[0] if concerns else "GM does not recommend extension",
                    "concerns": concerns,
                    "acceptance_probability": probability,
                    "category": category
                }
                rejections.append(rejection)

        # Sort by category priority, then by overall rating (descending)
        category_priority = {"age": 1, "performance": 2, "preference": 3, "expendable": 4}
        rejections.sort(
            key=lambda x: (category_priority.get(x["category"], 99), -x["overall"])
        )

        return rejections

    def _categorize_rejection_reason(
        self,
        concerns: List[str],
        player: Dict[str, Any]
    ) -> str:
        """
        Categorize rejection reason for UI display.

        Args:
            concerns: List of concern strings
            player: Player dict with age, overall

        Returns:
            Category: "age", "performance", "preference", or "expendable"
        """
        if not concerns:
            return "performance"

        primary_concern = concerns[0].lower()

        # Age-related
        if any(keyword in primary_concern for keyword in ["old", "age", "declining", "prime"]):
            return "age"

        # Performance-related
        if any(keyword in primary_concern for keyword in ["below", "threshold", "rating"]):
            return "performance"

        # Preference/acceptance related
        if any(keyword in primary_concern for keyword in ["probability", "unlikely", "reject"]):
            return "preference"

        # Expendable (owner directive)
        if "expendable" in primary_concern:
            return "expendable"

        return "performance"  # Default

    def resign_player(
        self,
        player_id: int,
        team_id: int,
        player_info: Optional[Dict[str, Any]] = None,
        skip_preference_check: bool = False
    ) -> Dict[str, Any]:
        """
        Re-sign a player with a new market-value contract.

        Uses MarketValueCalculator to determine contract terms automatically.
        Checks player preferences unless skip_preference_check is True.

        Args:
            player_id: Player ID to re-sign
            team_id: Team ID
            player_info: Optional player info dict (to avoid extra DB query)
            skip_preference_check: If True, bypass player preference check

        Returns:
            Dict with:
                - success: bool
                - new_contract_id: int (if successful)
                - contract_details: dict with AAV, years, etc.
                - player_name: str
                - error_message: str (if failed)
                - rejection_reason: str (if rejected by player)
                - concerns: List[str] (if rejected)
                - acceptance_probability: float (if rejected)
                - interest_level: str (if rejected)
        """
        from salary_cap.cap_database_api import CapDatabaseAPI
        from salary_cap.contract_manager import ContractManager
        from database.player_roster_api import PlayerRosterAPI
        from offseason.market_value_calculator import MarketValueCalculator

        try:
            roster_api = PlayerRosterAPI(self._db_path)
            cap_api = CapDatabaseAPI(self._db_path)
            contract_manager = ContractManager(self._db_path)
            market_calculator = MarketValueCalculator()

            # Get player info if not provided
            if player_info is None:
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not found",
                }

            import json

            # Handle both "name" key (from get_expiring_contracts) and first_name/last_name keys (from roster API)
            player_name = player_info.get("name") or f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Extract position from JSON positions array
            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            position = positions[0] if positions else ""

            # Extract overall from JSON attributes object
            attributes = player_info.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 70)

            # Calculate age from birthdate
            age = 25  # Default
            birthdate = player_info.get("birthdate")
            if birthdate:
                try:
                    birth_year = int(birthdate.split("-")[0])
                    age = self._season - birth_year
                except (ValueError, IndexError):
                    pass

            years_pro = player_info.get("years_pro", 3)

            # Calculate market value for the new contract
            # Use ValuationService if available, otherwise fall back to MarketValueCalculator
            if self._valuation_service:
                try:
                    # Prepare player data for valuation service
                    player_data = {
                        "position": position,
                        "overall_rating": overall,
                        "age": age,
                        "player_id": player_id,
                        "years_pro": years_pro,
                        "attributes": attributes,
                    }

                    # Get GM archetype if available
                    gm_archetype = None
                    try:
                        from team_management.gm_archetype import GMArchetype
                        from team_management.teams.team_loader import TeamDataLoader
                        team_loader = TeamDataLoader()
                        team_data = team_loader.get_team_by_id(team_id)
                        if team_data and hasattr(team_data, 'gm_archetype'):
                            gm_archetype = team_data.gm_archetype
                    except Exception as e:
                        self._logger.debug(f"Could not load GM archetype: {e}")

                    # Valuate player using sophisticated engine
                    valuation_result = self._valuation_service.valuate_player(
                        player_data=player_data,
                        team_id=team_id,
                        gm_archetype=gm_archetype,
                    )

                    # Extract contract offer from valuation result
                    aav = valuation_result.offer.aav
                    years = valuation_result.offer.years
                    guaranteed = valuation_result.offer.guaranteed
                    signing_bonus = valuation_result.offer.signing_bonus
                    total_value = valuation_result.offer.total_value

                    self._logger.info(
                        f"Using ValuationService for {player_name}: "
                        f"{years}yr/${aav:,} AAV (${total_value:,} total)"
                    )

                except Exception as e:
                    self._logger.warning(
                        f"ValuationService failed for {player_name}, using fallback: {e}"
                    )
                    # Fall back to MarketValueCalculator
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
            else:
                # Fallback to existing logic
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
                    market_aav=aav,  # At market value for re-signings
                    position=position,
                    overall=overall
                )

                if not acceptance_result["accepted"]:
                    self._logger.info(
                        f"Player {player_name} declined re-signing from team {team_id}: "
                        f"{acceptance_result['concerns']}"
                    )
                    return {
                        "success": False,
                        "error_message": "Player declined re-signing offer",
                        "rejection_reason": "Player declined based on preferences",
                        "concerns": acceptance_result["concerns"],
                        "acceptance_probability": acceptance_result["probability"],
                        "interest_level": acceptance_result["interest_level"],
                    }

            # Check cap space for NEXT season (offseason re-signings)
            from salary_cap.cap_calculator import CapCalculator
            cap_calculator = CapCalculator(self._db_path)
            cap_space = cap_calculator.calculate_team_cap_space(
                team_id=team_id,
                season=self._season + 1,  # Next league year
                dynasty_id=self._dynasty_id
            )

            if aav > cap_space:
                return {
                    "success": False,
                    "error_message": f"Insufficient cap space. Need ${aav:,}, have ${cap_space:,}",
                }

            # Generate year-by-year base salaries (roughly even distribution)
            # Slightly increasing each year for realism
            base_salaries = []
            remaining_after_bonus = total_value - signing_bonus
            for i in range(years):
                # Each year gets slightly more (5% increase per year)
                year_weight = 1.0 + (i * 0.05)
                total_weight = sum(1.0 + (j * 0.05) for j in range(years))
                year_salary = int((remaining_after_bonus * year_weight) / total_weight)
                base_salaries.append(year_salary)

            # Generate guaranteed amounts (front-loaded)
            guaranteed_amounts = []
            remaining_guarantee = guaranteed - signing_bonus  # signing bonus already guaranteed
            for i in range(years):
                if i < years // 2 + 1:  # First half + 1 years get guarantees
                    year_guarantee = remaining_guarantee // (years // 2 + 1)
                    guaranteed_amounts.append(year_guarantee)
                else:
                    guaranteed_amounts.append(0)

            # Deactivate old contract first
            old_contract = cap_api.get_player_contract(
                player_id=player_id,
                team_id=team_id,
                season=self._season,
                dynasty_id=self._dynasty_id
            )
            if old_contract:
                cap_api.void_contract(old_contract["contract_id"])

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

            self._logger.info(
                f"Re-signed {player_name} ({position}): {years} years, ${total_value:,}"
            )

            # Log transaction for audit trail
            self._transaction_logger.log_transaction(
                dynasty_id=self._dynasty_id,
                season=self._season + 1,  # Contract is for next season
                transaction_type="UFA_SIGNING",
                player_id=player_id,
                player_name=player_name,
                position=position,
                from_team_id=team_id,  # Re-signing = same team
                to_team_id=team_id,
                transaction_date=date(self._season + 1, 2, 15),  # Re-signing period (next year)
                details={
                    "contract_years": years,
                    "contract_value": total_value,
                    "guaranteed": guaranteed,
                    "is_resigning": True,
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
                    "position": position,
                    "overall": overall,
                    "age": age,
                }
            }

        except Exception as e:
            self._logger.error(f"Failed to re-sign player {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def release_player(
        self,
        player_id: int,
        team_id: int,
        player_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Release player to free agency.

        Sets player's team_id to 0 (free agent pool) and deactivates current contract.

        Args:
            player_id: Player ID to release
            team_id: Current team ID
            player_info: Optional player info dict

        Returns:
            Dict with:
                - success: bool
                - player_name: str
                - error_message: str (if failed)
        """
        from salary_cap.cap_database_api import CapDatabaseAPI
        from database.player_roster_api import PlayerRosterAPI

        try:
            roster_api = PlayerRosterAPI(self._db_path)
            cap_api = CapDatabaseAPI(self._db_path)

            # Get player info if not provided
            if player_info is None:
                player_info = roster_api.get_player_by_id(self._dynasty_id, player_id)

            if not player_info:
                return {
                    "success": False,
                    "error_message": f"Player {player_id} not found",
                }

            # Handle both "name" key (from get_expiring_contracts) and first_name/last_name keys (from roster API)
            player_name = player_info.get("name") or f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

            # Extract position from JSON positions array
            import json
            positions = player_info.get("positions", [])
            if isinstance(positions, str):
                positions = json.loads(positions)
            player_position = positions[0] if positions else ""

            # Extract overall from JSON attributes object
            attributes = player_info.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            player_overall = attributes.get("overall", 0)

            # Calculate age from birthdate
            player_age = player_info.get("age", 0)  # Use cached age if available
            if not player_age:
                birthdate = player_info.get("birthdate")
                if birthdate:
                    try:
                        birth_year = int(birthdate.split("-")[0])
                        player_age = self._season - birth_year
                    except (ValueError, IndexError):
                        player_age = 0

            # Get current team_id from player_info
            current_team_id = player_info.get("team_id", team_id)

            # Deactivate current contract
            contract = cap_api.get_player_contract(
                player_id=player_id,
                team_id=current_team_id,
                season=self._season,
                dynasty_id=self._dynasty_id
            )
            if contract:
                cap_api.void_contract(contract["contract_id"])

            # Move player to free agent pool (team_id = 0)
            roster_api.update_player_team(
                dynasty_id=self._dynasty_id,
                player_id=player_id,
                new_team_id=0  # 0 = Free Agent
            )

            self._logger.info(f"Released {player_name} to free agency")

            # Log transaction for audit trail
            self._transaction_logger.log_transaction(
                dynasty_id=self._dynasty_id,
                season=self._season + 1,  # Release is during next season's offseason
                transaction_type="RELEASE",
                player_id=player_id,
                player_name=player_name,
                position=player_position,
                from_team_id=current_team_id,
                to_team_id=None,  # To free agency
                transaction_date=date(self._season + 1, 2, 15),  # Re-signing period (next year)
                details={
                    "reason": "contract_not_renewed",
                }
            )

            return {
                "success": True,
                "player_name": player_name,
                "position": player_position,
                "overall": player_overall,
                "age": player_age,
            }

        except Exception as e:
            self._logger.error(f"Failed to release player {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def process_ai_resignings(self, user_team_id: int) -> Dict[str, Any]:
        """
        Process AI team re-signing decisions with player preference awareness.

        For each AI team (not user_team_id):
        1. Get expiring contracts
        2. Evaluate player preferences
        3. Re-sign or release each player

        Args:
            user_team_id: User's team ID (to skip)

        Returns:
            Dict with:
                - resigned: List of re-signed player info
                - released: List of released player info
                - rejections: List of players who rejected re-signing
                - events: List of event strings for UI
        """
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        resigned = []
        released = []
        rejections = []
        events = []

        for team in all_teams:
            team_id = team.team_id

            # Skip user's team
            if team_id == user_team_id:
                continue

            # Get expiring contracts for this team
            expiring = self.get_expiring_contracts(team_id)

            for player in expiring:
                player_id = player["player_id"]
                player_name = player.get("name", "Unknown")

                # Check if AI should attempt re-signing using preferences
                should_attempt, probability, concerns = self._should_ai_resign(
                    player, team_id
                )

                if should_attempt:
                    # Attempt re-signing (includes preference check)
                    result = self.resign_player(player_id, team_id, player)

                    if result["success"]:
                        resigned.append({
                            "player_id": player_id,
                            "player_name": result["player_name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "contract_details": result.get("contract_details", {}),
                        })
                        events.append(
                            f"{team.abbreviation} re-signed {result['player_name']}"
                        )
                    elif result.get("rejection_reason"):
                        # Player rejected the re-signing offer
                        rejections.append({
                            "player_id": player_id,
                            "player_name": player_name,
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "reason": result.get("rejection_reason"),
                            "concerns": result.get("concerns", []),
                            "acceptance_probability": result.get("acceptance_probability"),
                        })
                        # Release player to free agency since they rejected
                        release_result = self.release_player(player_id, team_id, player)
                        if release_result["success"]:
                            released.append({
                                "player_id": player_id,
                                "player_name": player_name,
                                "team_id": team_id,
                                "team_name": team.full_name,
                                "position": release_result.get("position", player.get("position", "")),
                                "overall": release_result.get("overall", player.get("overall", 0)),
                                "age": release_result.get("age", player.get("age", 0)),
                            })
                            events.append(
                                f"{team.abbreviation}: {player_name} rejected re-signing, became free agent"
                            )
                else:
                    # AI decided not to attempt re-signing
                    result = self.release_player(player_id, team_id, player)
                    if result["success"]:
                        released.append({
                            "player_id": player_id,
                            "player_name": result["player_name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "position": result.get("position", player.get("position", "")),
                            "overall": result.get("overall", player.get("overall", 0)),
                            "age": result.get("age", player.get("age", 0)),
                        })
                        events.append(
                            f"{team.abbreviation} released {result['player_name']} to free agency"
                        )

        self._logger.info(
            f"AI re-signing complete: {len(resigned)} re-signed, "
            f"{len(rejections)} rejected, {len(released)} released"
        )

        return {
            "resigned": resigned,
            "released": released,
            "rejections": rejections,
            "events": events,
        }

    def _should_ai_resign(
        self,
        player: Dict[str, Any],
        team_id: int
    ) -> Tuple[bool, float, List[str]]:
        """
        Decide if AI should re-sign a player using player preferences.

        Uses player persona and team attractiveness to determine likelihood
        of successful re-signing. Falls back to basic heuristics if persona
        system is unavailable.

        Args:
            player: Player dict with overall, age, position, player_id
            team_id: Team ID attempting the re-signing

        Returns:
            Tuple of (should_attempt, acceptance_probability, concerns)
        """
        overall = player.get("overall", 0)
        age = player.get("age", 0)
        position = player.get("position", "")
        player_id = player.get("player_id")

        # Basic checks first
        # Elite players always try to re-sign (unless very old)
        if overall >= 85 and age >= 35:
            return (False, 0.0, ["Player too old to invest in"])

        # Old + mediocre = release
        if age >= 32 and overall < 80:
            return (False, 0.0, ["Player declining with age"])

        # Very old players = release unless elite
        if age >= 34 and overall < 85:
            return (False, 0.0, ["Player past prime"])

        # Below average players = release
        if overall < 65:
            return (False, 0.0, ["Player below re-signing threshold"])

        # Try to get preference-based evaluation
        if player_id:
            try:
                persona_service = self._get_persona_service()
                persona = persona_service.get_persona(player_id)

                if persona:
                    # Get team attractiveness
                    attractiveness_service = self._get_attractiveness_service()
                    team_attractiveness = attractiveness_service.get_team_attractiveness(team_id)

                    # Calculate market value for evaluation
                    from src.player_management.preference_engine import ContractOffer

                    years_pro = player.get("years_pro", 3)

                    # Use ValuationService if available
                    if self._valuation_service:
                        try:
                            player_data = {
                                "position": position,
                                "overall_rating": overall,
                                "age": age,
                                "player_id": player_id,
                                "years_pro": years_pro,
                            }

                            valuation_result = self._valuation_service.valuate_player(
                                player_data=player_data,
                                team_id=team_id,
                                gm_archetype=None,  # AI uses default logic
                            )

                            market_aav = valuation_result.offer.aav
                            years = valuation_result.offer.years
                            guaranteed = valuation_result.offer.guaranteed
                            signing_bonus = valuation_result.offer.signing_bonus

                        except Exception:
                            # Fallback to MarketValueCalculator
                            from offseason.market_value_calculator import MarketValueCalculator
                            market_calculator = MarketValueCalculator()
                            market_value = market_calculator.calculate_player_value(
                                position=position,
                                overall=overall,
                                age=age,
                                years_pro=years_pro
                            )
                            market_aav = int(market_value["aav"] * 1_000_000)
                            years = market_value["years"]
                            guaranteed = int(market_value["guaranteed"] * 1_000_000)
                            signing_bonus = int(market_value["signing_bonus"] * 1_000_000)
                    else:
                        # Fallback to MarketValueCalculator
                        from offseason.market_value_calculator import MarketValueCalculator
                        market_calculator = MarketValueCalculator()
                        market_value = market_calculator.calculate_player_value(
                            position=position,
                            overall=overall,
                            age=age,
                            years_pro=years_pro
                        )
                        market_aav = int(market_value["aav"] * 1_000_000)
                        years = market_value["years"]
                        guaranteed = int(market_value["guaranteed"] * 1_000_000)
                        signing_bonus = int(market_value["signing_bonus"] * 1_000_000)

                    offer = ContractOffer(
                        team_id=team_id,
                        aav=market_aav,
                        total_value=market_aav * years,
                        years=years,
                        guaranteed=guaranteed,
                        signing_bonus=signing_bonus,
                        market_aav=market_aav,
                        role=self._estimate_role(team_id, position, overall)
                    )

                    preference_engine = self._get_preference_engine()
                    team_score = preference_engine.calculate_team_score(
                        persona=persona,
                        team=team_attractiveness,
                        offer=offer,
                        is_current_team=True,  # KEY: Loyalty bonus applies
                        is_drafting_team=(team_id == persona.drafting_team_id)
                    )

                    probability = preference_engine.calculate_acceptance_probability(
                        persona=persona,
                        team_score=team_score,
                        offer_vs_market=1.0  # At market value
                    )

                    concerns = preference_engine.get_concerns(
                        persona, team_attractiveness, offer
                    )

                    # AI decision based on probability
                    # High probability: definitely try
                    # Medium probability: try if important player
                    # Low probability: skip unless star
                    if probability >= 0.60:
                        return (True, probability, concerns)
                    elif probability >= 0.40 and overall >= 80:
                        return (True, probability, concerns)
                    else:
                        return (False, probability, concerns)

            except Exception as e:
                self._logger.warning(f"Preference evaluation failed: {e}")
                # Fall through to default logic

        # Default logic: attempt if decent player
        # Good starters usually re-sign
        if overall >= 75:
            return (True, 0.50, [])

        # Premium positions get more leeway
        premium_positions = [
            "quarterback", "left_tackle", "right_tackle",
            "defensive_end", "cornerback", "wide_receiver"
        ]
        if position in premium_positions and overall >= 68:
            return (True, 0.50, [])

        # Default: re-sign average or better starters
        if overall >= 70:
            return (True, 0.50, [])

        return (False, 0.0, [])

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