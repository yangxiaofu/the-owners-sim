"""
Re-signing Service for Game Cycle.

Handles player re-signing decisions during the offseason re-signing stage.
Uses MarketValueCalculator to generate realistic contract offers.
"""

from typing import Dict, List, Any, Optional
import logging


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
        season: int
    ):
        """
        Initialize the re-signing service.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Current season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._logger = logging.getLogger(__name__)

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

                    # Extract overall from JSON attributes
                    attributes = player_info.get("attributes", {})
                    if isinstance(attributes, str):
                        import json
                        attributes = json.loads(attributes)
                    overall = attributes.get("overall", 0)

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

                    expiring_players.append({
                        "player_id": player_id,
                        "name": f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip(),
                        "position": position,
                        "age": age,
                        "overall": overall,
                        "years_pro": player_info.get("years_pro", 0),
                        "salary": aav,
                        "years_remaining": years_remaining,
                        "contract_id": contract.get("contract_id"),
                    })

        # Sort by overall rating (highest first)
        expiring_players.sort(key=lambda x: x.get("overall", 0), reverse=True)

        return expiring_players

    def resign_player(
        self,
        player_id: int,
        team_id: int,
        player_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Re-sign a player with a new market-value contract.

        Uses MarketValueCalculator to determine contract terms automatically.

        Args:
            player_id: Player ID to re-sign
            team_id: Team ID
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

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
            position = player_info.get("position", "")
            overall = player_info.get("overall_rating", 70)
            age = player_info.get("age", 25)
            years_pro = player_info.get("years_pro", 3)

            # Calculate market value for the new contract
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

            # Create new contract
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
                season=self._season
            )

            self._logger.info(
                f"Re-signed {player_name} ({position}): {years} years, ${total_value:,}"
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

            player_name = f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()

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

            return {
                "success": True,
                "player_name": player_name,
            }

        except Exception as e:
            self._logger.error(f"Failed to release player {player_id}: {e}")
            return {
                "success": False,
                "error_message": str(e),
            }

    def process_ai_resignings(self, user_team_id: int) -> Dict[str, Any]:
        """
        Process AI team re-signing decisions.

        For each AI team (not user_team_id):
        1. Get expiring contracts
        2. Decide based on overall rating + age
        3. Re-sign or release each player

        Args:
            user_team_id: User's team ID (to skip)

        Returns:
            Dict with:
                - resigned: List of re-signed player info
                - released: List of released player info
                - events: List of event strings for UI
        """
        from team_management.teams.team_loader import TeamDataLoader

        team_loader = TeamDataLoader()
        all_teams = team_loader.get_all_teams()

        resigned = []
        released = []
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
                should_resign = self._should_ai_resign(player)

                if should_resign:
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
                else:
                    result = self.release_player(player_id, team_id, player)
                    if result["success"]:
                        released.append({
                            "player_id": player_id,
                            "player_name": result["player_name"],
                            "team_id": team_id,
                            "team_name": team.full_name,
                        })
                        events.append(
                            f"{team.abbreviation} released {result['player_name']} to free agency"
                        )

        self._logger.info(
            f"AI re-signing complete: {len(resigned)} re-signed, {len(released)} released"
        )

        return {
            "resigned": resigned,
            "released": released,
            "events": events,
        }

    def _should_ai_resign(self, player: Dict[str, Any]) -> bool:
        """
        Decide if AI should re-sign a player.

        Simple algorithm based on:
        - Overall rating
        - Age
        - Position value

        Args:
            player: Player dict with overall, age, position

        Returns:
            True if AI should re-sign, False to release
        """
        overall = player.get("overall", 0)
        age = player.get("age", 0)
        position = player.get("position", "")

        # Elite players always re-sign (unless very old)
        if overall >= 85:
            return age < 35

        # Old + mediocre = release
        if age >= 32 and overall < 80:
            return False

        # Very old players = release unless elite
        if age >= 34:
            return overall >= 85

        # Good starters usually re-sign
        if overall >= 75:
            return True

        # Premium positions get more leeway
        premium_positions = [
            "quarterback", "left_tackle", "right_tackle",
            "defensive_end", "cornerback", "wide_receiver"
        ]
        if position in premium_positions:
            return overall >= 68

        # Default: re-sign average or better starters
        return overall >= 70

    def get_team_cap_space(self, team_id: int) -> int:
        """
        Get available cap space for a team.

        Args:
            team_id: Team ID

        Returns:
            Available cap space in dollars
        """
        from salary_cap.cap_calculator import CapCalculator

        calculator = CapCalculator(self._db_path)
        return calculator.calculate_team_cap_space(
            team_id=team_id,
            season=self._season,
            dynasty_id=self._dynasty_id
        )