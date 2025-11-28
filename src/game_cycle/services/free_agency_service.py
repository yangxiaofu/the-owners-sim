"""
Free Agency Service for Game Cycle.

Handles free agent signing operations during the offseason free agency stage.
Uses MarketValueCalculator to generate realistic contract offers.
"""

from datetime import date
from typing import Dict, List, Any, Optional
import logging
import json

from persistence.transaction_logger import TransactionLogger


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
        season: int
    ):
        """
        Initialize the free agency service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

        # Lazy-loaded cap helper
        self._cap_helper = None

        # Transaction logger for audit trail
        self._transaction_logger = TransactionLogger(db_path)

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

            # Extract overall from JSON attributes
            attributes = player.get("attributes", {})
            if isinstance(attributes, str):
                attributes = json.loads(attributes)
            overall = attributes.get("overall", 0)

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
        player_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Sign a free agent to a team with a market-value contract.

        Args:
            player_id: Player ID to sign
            team_id: Team ID signing the player
            player_info: Optional player info dict (to avoid extra DB query)

        Returns:
            Dict with:
                - success: bool
                - new_contract_id: int (if successful)
                - contract_details: dict with AAV, years, etc.
                - player_name: str
                - error_message: str (if failed)
        """
        from salary_cap.cap_database_api import CapDatabaseAPI
        from salary_cap.contract_manager import ContractManager
        from salary_cap.cap_calculator import CapCalculator
        from database.player_roster_api import PlayerRosterAPI
        from offseason.market_value_calculator import MarketValueCalculator

        try:
            roster_api = PlayerRosterAPI(self._db_path)
            cap_api = CapDatabaseAPI(self._db_path)
            contract_manager = ContractManager(self._db_path)
            cap_calculator = CapCalculator(self._db_path)
            market_calculator = MarketValueCalculator()

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

            # Calculate market value
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
                from_team_id=None,  # From free agency
                to_team_id=team_id,
                transaction_date=date(self._season + 1, 3, 15),  # FA period date (next year)
                details={
                    "contract_years": years,
                    "contract_value": total_value,
                    "guaranteed": guaranteed,
                    "position": position,
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
                }
            }

        except Exception as e:
            self._logger.error(f"Failed to sign free agent {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def process_ai_signings(
        self,
        user_team_id: int,
        max_signings_per_team: int = 3
    ) -> Dict[str, Any]:
        """
        Process AI team free agent signings.

        For each AI team (not user_team_id):
        1. Get team's positional needs (simple gap analysis)
        2. Find best available FA for each need
        3. Sign if cap space allows

        Args:
            user_team_id: User's team ID (to skip)
            max_signings_per_team: Maximum signings per AI team

        Returns:
            Dict with:
                - signings: List of signing info dicts
                - events: List of event strings for UI
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

                # Find best available FA at this position
                best_fa = None
                for fa in available_fas:
                    if fa["position"].lower() == need_position.lower():
                        if fa["estimated_aav"] <= cap_space:
                            best_fa = fa
                            break  # Take the first (highest rated) that fits

                if best_fa:
                    # Sign the player
                    result = self.sign_free_agent(best_fa["player_id"], team_id, None)

                    if result["success"]:
                        signings.append({
                            "player_id": best_fa["player_id"],
                            "player_name": result["player_name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                            "contract_details": result.get("contract_details", {}),
                        })
                        events.append(
                            f"{team.abbreviation} signed FA {result['player_name']}"
                        )

                        # Update cap space
                        cap_space -= best_fa["estimated_aav"]
                        signings_made += 1

                        # Remove from available pool
                        available_fas = [
                            fa for fa in available_fas
                            if fa["player_id"] != best_fa["player_id"]
                        ]

        self._logger.info(f"AI FA signings complete: {len(signings)} signings")

        return {
            "signings": signings,
            "events": events,
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