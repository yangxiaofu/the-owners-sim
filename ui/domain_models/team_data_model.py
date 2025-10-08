"""
Team Data Model for The Owner's Sim UI

Domain model that encapsulates team roster, salary cap, depth chart, and coaching staff data access.
Owns all database API instances and provides clean data access interface for controllers.

Architecture:
    View Layer → Controller Layer → Domain Model Layer (THIS) → Database APIs

Responsibilities:
    - OWN: Database API instances (PlayerRosterAPI, CapDatabaseAPI, TeamDataLoader)
    - DO: All team data access, roster queries, cap calculations, contract merging
    - RETURN: Clean DTOs/dicts to controllers
    - NO: Qt dependencies, UI concerns, user interaction handling
"""

from typing import List, Dict, Any, Optional
import json
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.player_roster_api import PlayerRosterAPI
from salary_cap.cap_database_api import CapDatabaseAPI
from team_management.teams.team_loader import TeamDataLoader, Team


class TeamDataModel:
    """
    Domain model for team roster and salary cap data access.

    Encapsulates all business logic related to:
    - Team roster retrieval with contract integration
    - Salary cap summaries and contract formatting
    - Depth chart management (future)
    - Coaching staff information (future)

    This model owns all database API instances and provides a clean interface
    for controllers to access team-related data without direct database coupling.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize team data model.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize all database API instances (model owns these)
        self.player_roster_api = PlayerRosterAPI(db_path)
        self.cap_db_api = CapDatabaseAPI(db_path)
        self.team_loader = TeamDataLoader()

        # Initialize DatabaseConnection for dynasty queries
        from database.connection import DatabaseConnection
        self.db_connection = DatabaseConnection(db_path)

    # ==================== Team Roster Operations ====================

    def get_team_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get complete team roster with contract information merged.

        Retrieves player roster from database and enriches with contract details
        including formatted salary strings and contract years.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries with format:
            [
                {
                    'player_id': int,
                    'number': int,
                    'name': str,          # "Last, First" format
                    'position': str,      # First position from positions list
                    'age': int,           # Calculated from years_pro
                    'overall': int,       # Rating from attributes
                    'contract': str,      # "2yr/$45.0M" or "N/A"
                    'salary': str,        # "$22.5M" or "$0"
                    'status': str         # 'ACT', 'IR', 'PUP', etc.
                },
                ...
            ]

            Returns empty list [] if:
            - Team has no roster in database
            - Dynasty not initialized
            - Database query fails

        Example:
            roster = model.get_team_roster(22)  # Detroit Lions
            for player in roster:
                print(f"{player['number']} {player['name']} - {player['position']} ({player['overall']})")
        """
        try:
            # Step 1: Get roster from database
            roster_players = self.player_roster_api.get_team_roster(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )

            # Convert sqlite3.Row objects to dictionaries
            roster_players = [dict(player) for player in roster_players]

            # Step 2: Get all contracts for team
            contracts = self.cap_db_api.get_team_contracts(
                team_id=team_id,
                season=self.season,
                dynasty_id=self.dynasty_id,
                active_only=True
            )

            # Convert contracts to dicts if needed
            contracts = [dict(c) if not isinstance(c, dict) else c for c in contracts]

            # Step 3: Create lookup dict for fast contract access
            contract_map = {c['player_id']: c for c in contracts}

            # Step 4: Merge players with contracts and format
            formatted_roster = []
            for player in roster_players:
                contract = contract_map.get(player['player_id'])
                formatted_player = self._merge_player_contract(player, contract)
                formatted_roster.append(formatted_player)

            return formatted_roster

        except Exception as e:
            # Gracefully handle missing data - roster might not be initialized yet
            print(f"[ERROR TeamDataModel] No roster data available for team {team_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _merge_player_contract(
        self,
        player: Dict[str, Any],
        contract: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Merge player data with contract information and format for display.

        Extracts player attributes, calculates age, formats contract strings,
        and returns a clean DTO suitable for UI display.

        Args:
            player: Player dict from database (includes positions JSON, attributes JSON)
            contract: Contract dict from database or None

        Returns:
            Formatted player dict with all display-ready fields

        Notes:
            - Positions stored as JSON array: ["QB", "WR"] → first position used
            - Attributes stored as JSON dict: {"overall": 85, ...}
            - Contract years calculated from start_year/end_year
        """
        # Parse positions JSON (stored as string in database)
        try:
            positions = json.loads(player['positions']) if isinstance(player['positions'], str) else player['positions']
            primary_position = positions[0] if positions else "UNK"
        except (json.JSONDecodeError, KeyError, IndexError):
            primary_position = "UNK"

        # Parse attributes JSON to extract overall rating
        try:
            attributes = json.loads(player['attributes']) if isinstance(player['attributes'], str) else player['attributes']
            overall = attributes.get('overall', 0)
        except (json.JSONDecodeError, KeyError):
            overall = 0

        # Calculate age from years_pro (assume rookie age of 22)
        age = self._calculate_age(player.get('years_pro', 0))

        # Format name as "Last, First"
        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        formatted_name = f"{last_name}, {first_name}"

        # Format contract and salary strings
        contract_str = self._format_contract(contract)
        salary_str = self._format_salary(contract)

        # Get status (default to 'ACT' if not specified)
        status = player.get('status', 'ACT')

        return {
            'player_id': player['player_id'],
            'number': player.get('number', 0),
            'name': formatted_name,
            'position': primary_position,
            'age': age,
            'overall': overall,
            'contract': contract_str,
            'salary': salary_str,
            'status': status
        }

    def _format_contract(self, contract: Optional[Dict[str, Any]]) -> str:
        """
        Format contract as "2yr/$45.0M" string.

        Args:
            contract: Contract dict with start_year, end_year, total_value

        Returns:
            Formatted contract string (e.g., "2yr/$45.0M") or "N/A" if no contract

        Examples:
            - 1-year contract: "1yr/$15.0M"
            - 5-year contract: "5yr/$125.0M"
            - No contract: "N/A"
        """
        if not contract:
            return "N/A"

        try:
            # Calculate contract years from start/end year
            years = contract['end_year'] - contract['start_year'] + 1

            # Convert total value from cents to millions
            total_value_millions = contract['total_value'] / 1_000_000.0

            return f"{years}yr/${total_value_millions:.1f}M"

        except (KeyError, TypeError):
            return "N/A"

    def _format_salary(self, contract: Optional[Dict[str, Any]]) -> str:
        """
        Format current year salary as "$22.5M" string.

        Retrieves contract year details for current season and extracts total cap hit.

        Args:
            contract: Contract dict with contract_id

        Returns:
            Formatted salary string (e.g., "$22.5M") or "$0" if no contract

        Examples:
            - Cap hit $22,500,000: "$22.5M"
            - Cap hit $5,000,000: "$5.0M"
            - No contract: "$0"
        """
        if not contract:
            return "$0"

        try:
            # Get contract year details for current season
            year_details = self.cap_db_api.get_contract_year_details(
                contract_id=contract['contract_id'],
                season_year=self.season
            )

            if not year_details:
                return "$0"

            # Extract total cap hit from first result (should only be one for specific season)
            total_cap_hit = year_details[0].get('total_cap_hit', 0)

            # Convert from cents to millions
            cap_hit_millions = total_cap_hit / 1_000_000.0

            return f"${cap_hit_millions:.1f}M"

        except Exception as e:
            print(f"[WARN TeamDataModel] Error formatting salary: {e}")
            return "$0"

    def _calculate_age(self, years_pro: int) -> int:
        """
        Calculate player age based on years of professional experience.

        Assumes average rookie age of 22 years old.

        Args:
            years_pro: Number of years player has been in NFL

        Returns:
            Estimated age in years

        Examples:
            - Rookie (0 years pro): 22 years old
            - 5th year player: 27 years old
            - 10th year veteran: 32 years old
        """
        ROOKIE_AGE = 22
        return ROOKIE_AGE + years_pro

    # ==================== Salary Cap Operations ====================

    def get_cap_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get complete salary cap summary for team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with cap summary:
            {
                'cap_limit': int,
                'cap_used': int,
                'cap_space': int,
                'dead_money': int,
                'top_51_active': bool,
                ...
            }

            Returns empty dict {} if no cap data exists

        TODO: Implement complete cap summary retrieval
        """
        # TODO: Implement cap summary retrieval
        # Will use: self.cap_db_api.get_team_cap_summary(team_id, self.season, self.dynasty_id)
        return {}

    # ==================== Depth Chart Operations ====================

    def get_depth_chart(self, team_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get team depth chart organized by position.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary mapping position to sorted player list:
            {
                'QB': [player1, player2, ...],
                'RB': [player1, player2, ...],
                ...
            }

            Returns empty dict {} if no depth chart exists

        TODO: Implement depth chart retrieval and sorting logic
        """
        # TODO: Implement depth chart retrieval
        # Will use: self.player_roster_api.get_team_roster() + depth_chart_order sorting
        return {}

    # ==================== Coaching Staff Operations ====================

    def get_coaching_staff(self, team_id: int) -> Dict[str, Any]:
        """
        Get team coaching staff information.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with coaching staff:
            {
                'head_coach': {...},
                'offensive_coordinator': {...},
                'defensive_coordinator': {...},
                'special_teams_coordinator': {...}
            }

            Returns empty dict {} if no coaching data exists

        TODO: Implement coaching staff retrieval
        """
        # TODO: Implement coaching staff retrieval
        # Will load from src/config/coaching_staff/ JSON files
        return {}

    # ==================== Metadata Access ====================

    def get_dynasty_team_id(self) -> Optional[int]:
        """
        Get the user's team ID for this dynasty.

        Returns:
            Team ID (1-32) if dynasty has a user team, None for commissioner mode

        Example:
            team_id = model.get_dynasty_team_id()
            if team_id:
                print(f"User controls team {team_id}")
            else:
                print("Commissioner mode - no user team")
        """
        query = "SELECT team_id FROM dynasties WHERE dynasty_id = ?"
        result = self.db_connection.execute_query(query, (self.dynasty_id,))

        if result and len(result) > 0:
            team_id = result[0]['team_id']
            return team_id if team_id else None
        return None

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty metadata.

        Returns:
            Dictionary containing:
            {
                'dynasty_id': str,  # Dynasty identifier
                'season': str       # Season year (e.g., '2025')
            }

        Example:
            info = model.get_dynasty_info()
            print(f"Dynasty: {info['dynasty_id']}, Season: {info['season']}")
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }
