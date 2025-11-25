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
from database.dynasty_state_api import DynastyStateAPI
from salary_cap.cap_database_api import CapDatabaseAPI
from team_management.teams.team_loader import TeamDataLoader, Team
from constants.position_abbreviations import get_position_abbreviation
from shared.player_utils import get_player_age
from depth_chart.depth_chart_api import DepthChartAPI


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
        self.dynasty_state_api = DynastyStateAPI(db_path)
        self.depth_chart_api = DepthChartAPI(db_path)
        self.team_loader = TeamDataLoader()

        # Initialize DatabaseConnection for dynasty queries
        from database.connection import DatabaseConnection
        self.db_connection = DatabaseConnection(db_path)

    # ==================== Team Roster Operations ====================

    def get_full_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get FULL team roster including inactive players (active + inactive).

        Unlike get_team_roster(), this returns ALL players regardless of roster_status.
        Useful for complete roster management and tracking 90-man roster.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of player dictionaries with all roster players (active + inactive).
            Each player dict includes 'roster_status' field ('active' or 'inactive').

        Example:
            full_roster = model.get_full_roster(22)  # Detroit Lions
            active_count = sum(1 for p in full_roster if p.get('roster_status') == 'active')
            total_count = len(full_roster)
        """
        try:
            # Get full roster from PlayerRosterAPI (includes roster_status)
            full_roster_players = self.player_roster_api.get_full_roster(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )

            # Convert sqlite3.Row objects to dictionaries
            full_roster_players = [dict(player) for player in full_roster_players]

            # Get all contracts for team
            contracts = self.cap_db_api.get_team_contracts(
                team_id=team_id,
                season=self.season,
                dynasty_id=self.dynasty_id,
                active_only=True
            )

            # Convert contracts to dicts if needed
            contracts = [dict(c) if not isinstance(c, dict) else c for c in contracts]

            # Create lookup dict for fast contract access
            contract_map = {c['player_id']: c for c in contracts}

            # Merge players with contracts and format
            formatted_roster = []
            for player in full_roster_players:
                contract = contract_map.get(player['player_id'])
                formatted_player = self._merge_player_contract(player, contract)
                # Preserve roster_status from database
                formatted_player['roster_status'] = player.get('roster_status', 'active')
                formatted_roster.append(formatted_player)

            return formatted_roster

        except Exception as e:
            # Gracefully handle missing data
            print(f"[ERROR TeamDataModel] No full roster data available for team {team_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

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

    def get_full_roster(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get FULL team roster including inactive players.

        Unlike get_team_roster(), this returns ALL players on the roster
        regardless of roster_status (active/inactive). Use for UI roster display
        where we want to show complete roster with status indicators.

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
                    'status': str,        # 'ACT', 'IR', 'PUP', etc.
                    'roster_status': str  # 'active' or 'inactive'
                },
                ...
            ]

            Returns empty list [] if:
            - Team has no roster in database
            - Dynasty not initialized
            - Database query fails

        Example:
            full_roster = model.get_full_roster(22)  # Detroit Lions (all 60 players)
            active_roster = model.get_team_roster(22)  # Detroit Lions (53 active only)

            for player in full_roster:
                status_icon = "✓" if player['roster_status'] == 'active' else "○"
                print(f"{status_icon} {player['number']} {player['name']}")
        """
        try:
            # Step 1: Get FULL roster from database (no status filter)
            roster_players = self.player_roster_api.get_full_roster(
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
            positions_raw = player['positions']
            if isinstance(positions_raw, str):
                # Handle empty strings by using default
                positions = json.loads(positions_raw) if positions_raw.strip() else []
            else:
                positions = positions_raw
            primary_position = positions[0] if positions else "UNK"
            # Convert to NFL abbreviation (e.g., "wide_receiver" → "WR")
            primary_position = get_position_abbreviation(primary_position)
        except (json.JSONDecodeError, KeyError, IndexError):
            primary_position = "UNK"

        # Parse attributes JSON to extract overall rating
        try:
            attributes_raw = player['attributes']
            if isinstance(attributes_raw, str):
                # Handle empty strings by using default
                attributes = json.loads(attributes_raw) if attributes_raw.strip() else {}
            else:
                attributes = attributes_raw
            overall = attributes.get('overall', 0)
        except (json.JSONDecodeError, KeyError):
            overall = 0

        # Calculate age from birthdate if available, otherwise estimate from years_pro
        age = self._calculate_age(player)

        # Format name as "Last, First"
        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        formatted_name = f"{last_name}, {first_name}"

        # Format contract and salary strings
        contract_str = self._format_contract(contract)
        salary_str = self._format_salary(contract)

        # Get status (default to 'ACT' if not specified)
        status = player.get('status', 'ACT')

        # Get roster_status (active or inactive)
        roster_status = player.get('roster_status', 'active')

        return {
            'player_id': player['player_id'],
            'number': player.get('number', 0),
            'name': formatted_name,
            'position': primary_position,
            'age': age,
            'overall': overall,
            'contract': contract_str,
            'salary': salary_str,
            'status': status,
            'roster_status': roster_status  # NEW: Active or inactive
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

    def _calculate_age(self, player: Dict[str, Any]) -> int:
        """
        Calculate player age from birthdate if available, otherwise estimate from years_pro.

        Uses accurate birthdate calculation when available, falling back to years_pro estimation.

        Args:
            player: Player dict containing birthdate and/or years_pro

        Returns:
            Player age in years

        Examples:
            - With birthdate: Accurate age based on current simulation date
            - Without birthdate (fallback): Estimated from years_pro + 22
        """
        birthdate = player.get('birthdate')
        years_pro = player.get('years_pro', 0)

        # Get current simulation date
        current_date = self.dynasty_state_api.get_current_date(self.dynasty_id, self.season)

        # Use shared utility function (handles birthdate + fallback)
        return get_player_age(
            birthdate=birthdate,
            current_date=current_date,
            years_pro=years_pro,
            rookie_age=22
        )

    # ==================== Salary Cap Operations ====================

    def get_team_contracts(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get team contracts with player information for finances display.

        Retrieves all active contracts for a team and merges with player roster data
        to provide complete contract information formatted for UI display.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of contract dictionaries with format:
            [
                {
                    'player': str,        # "Last, First" format
                    'pos': str,           # Position abbreviation (QB, WR, LB, etc.)
                    'cap_hit': int,       # Current year cap hit in dollars
                    'years_left': int,    # Years remaining on contract
                    'dead_money': int     # Dead money if released today (dollars)
                },
                ...
            ]

            Returns empty list [] if:
            - Team has no contracts in database
            - Dynasty not initialized
            - Database query fails

        Example:
            contracts = model.get_team_contracts(22)  # Detroit Lions
            for contract in contracts:
                print(f"{contract['player']} ({contract['pos']}) - ${contract['cap_hit']/1_000_000:.1f}M cap hit")
        """
        try:
            # Step 1: Get all active contracts for team
            contracts = self.cap_db_api.get_team_contracts(
                team_id=team_id,
                season=self.season,
                dynasty_id=self.dynasty_id,
                active_only=True
            )

            # Convert to dicts if needed
            contracts = [dict(c) if not isinstance(c, dict) else c for c in contracts]

            if not contracts:
                return []

            # Step 2: Get roster to map player_id to player names/positions
            roster_players = self.player_roster_api.get_team_roster(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )

            # Convert to dicts and create player lookup
            roster_players = [dict(player) for player in roster_players]
            player_map = {player['player_id']: player for player in roster_players}

            # Step 3: Merge contract with player data and format
            formatted_contracts = []
            for contract in contracts:
                player = player_map.get(contract['player_id'])
                if not player:
                    continue  # Skip contracts for players not on roster

                formatted_contract = self._format_contract_for_display(contract, player)
                formatted_contracts.append(formatted_contract)

            return formatted_contracts

        except Exception as e:
            print(f"[ERROR TeamDataModel] Failed to load contracts for team {team_id}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _format_contract_for_display(
        self,
        contract: Dict[str, Any],
        player: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format contract and player data for finances UI display.

        Args:
            contract: Contract dict from database
            player: Player dict from database

        Returns:
            Formatted contract dict ready for UI display
        """
        # Parse player position
        try:
            positions_raw = player['positions']
            if isinstance(positions_raw, str):
                # Handle empty strings by using default
                positions = json.loads(positions_raw) if positions_raw.strip() else []
            else:
                positions = positions_raw
            primary_position = positions[0] if positions else "UNK"
            primary_position = get_position_abbreviation(primary_position)
        except (json.JSONDecodeError, KeyError, IndexError):
            primary_position = "UNK"

        # Format player name as "Last, First"
        first_name = player.get('first_name', '')
        last_name = player.get('last_name', '')
        player_name = f"{last_name}, {first_name}"

        # Get current year cap hit
        try:
            year_details = self.cap_db_api.get_contract_year_details(
                contract_id=contract['contract_id'],
                season_year=self.season
            )
            cap_hit = year_details[0].get('total_cap_hit', 0) if year_details else 0
        except Exception:
            cap_hit = 0

        # Calculate years remaining on contract
        years_left = contract['end_year'] - self.season + 1
        years_left = max(0, years_left)  # Ensure non-negative

        # Calculate dead money (simplified - full remaining guaranteed money)
        # TODO: Implement proper dead money calculation with June 1 designation logic
        dead_money = contract.get('total_guaranteed', 0)

        return {
            'player': player_name,
            'pos': primary_position,
            'cap_hit': cap_hit,
            'years_left': years_left,
            'dead_money': dead_money
        }

    def get_cap_summary(self, team_id: int) -> Dict[str, Any]:
        """
        Get complete salary cap summary for team.

        Retrieves salary cap totals, spending, cap space, and roster count
        for UI display in finances tab.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary with cap summary:
            {
                'cap_limit': int,           # Total salary cap limit
                'cap_used': int,            # Current cap spending
                'cap_space': int,           # Available cap space
                'roster_count': int,        # Current roster count
                'dead_money': int,          # Dead money total
                'top_51_active': bool,      # Whether top-51 rule is active
                # Projections:
                'next_year_cap': int,       # Projected next year cap
                'next_year_commitments': int,  # Committed spending next year
                'next_year_space': int      # Projected cap space next year
            }

            Returns empty dict {} if no cap data exists

        Example:
            summary = model.get_cap_summary(22)  # Detroit Lions
            print(f"Cap Space: ${summary['cap_space']/1_000_000:.1f}M")
        """
        try:
            # Get cap summary from database view
            cap_summary = self.cap_db_api.get_team_cap_summary(
                team_id=team_id,
                season=self.season,
                dynasty_id=self.dynasty_id
            )

            if not cap_summary:
                # No cap data initialized - return empty dict
                return {}

            # Get roster count
            roster_players = self.player_roster_api.get_team_roster(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )
            roster_count = len(list(roster_players))

            # Get dead money total
            dead_money_entries = self.cap_db_api.get_team_dead_money(
                team_id=team_id,
                season=self.season,
                dynasty_id=self.dynasty_id
            )
            dead_money_total = sum(entry.get('current_year_dead_money', 0) for entry in dead_money_entries)

            # TODO: Calculate next year projections
            # For now, use placeholder values
            next_year_cap = 238_200_000  # Projected 2026 cap
            next_year_commitments = 0  # Calculate from multi-year contracts
            next_year_space = next_year_cap - next_year_commitments

            return {
                'cap_limit': cap_summary.get('total_cap_limit', 0),
                'cap_used': cap_summary.get('total_cap_used', 0),
                'cap_space': cap_summary.get('cap_space_available', 0),
                'roster_count': roster_count,
                'dead_money': dead_money_total,
                'top_51_active': cap_summary.get('is_top_51_active', False),
                'next_year_cap': next_year_cap,
                'next_year_commitments': next_year_commitments,
                'next_year_space': next_year_space
            }

        except Exception as e:
            # Gracefully handle missing cap data (database may not have cap tables initialized)
            if "no such table" in str(e).lower():
                # Cap system not initialized yet - return empty summary silently
                return {}
            else:
                # Other errors - log with traceback
                print(f"[ERROR TeamDataModel] Failed to load cap summary for team {team_id}: {e}")
                import traceback
                traceback.print_exc()
                return {}

    # ==================== Depth Chart Operations ====================

    def get_full_depth_chart(self, team_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get complete team depth chart organized by position.

        Retrieves depth chart for all positions and formats for UI display.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dictionary mapping position to sorted player list:
            {
                'quarterback': [
                    {
                        'player_id': int,
                        'player_name': str,
                        'overall': int,
                        'depth_order': int,
                        'position': str
                    },
                    ...
                ],
                'running_back': [...],
                ...
            }

            Returns empty dict {} if no depth chart exists

        Example:
            depth_chart = model.get_full_depth_chart(22)  # Detroit Lions
            for position, players in depth_chart.items():
                print(f"{position}: {len(players)} players")
        """
        try:
            # Get full depth chart from API
            full_depth_chart = self.depth_chart_api.get_full_depth_chart(
                dynasty_id=self.dynasty_id,
                team_id=team_id
            )

            return full_depth_chart

        except Exception as e:
            print(f"[ERROR TeamDataModel] Failed to load depth chart for team {team_id}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_position_depth_chart(self, team_id: int, position: str) -> List[Dict[str, Any]]:
        """
        Get depth chart for specific position.

        Args:
            team_id: Team ID (1-32)
            position: Position name (e.g., "quarterback", "running_back")

        Returns:
            List of players sorted by depth_chart_order:
            [
                {
                    'player_id': int,
                    'player_name': str,
                    'overall': int,
                    'depth_order': int,
                    'position': str
                },
                ...
            ]

            Returns empty list [] if no players at position

        Example:
            qb_depth = model.get_position_depth_chart(22, "quarterback")
            for i, player in enumerate(qb_depth, 1):
                print(f"{i}. {player['player_name']} ({player['overall']} OVR)")
        """
        try:
            # Get position depth chart from API
            position_depth_chart = self.depth_chart_api.get_position_depth_chart(
                dynasty_id=self.dynasty_id,
                team_id=team_id,
                position=position
            )

            return position_depth_chart

        except Exception as e:
            print(f"[ERROR TeamDataModel] Failed to load depth chart for {position}: {e}")
            import traceback
            traceback.print_exc()
            return []

    def reorder_position_depth_chart(
        self,
        team_id: int,
        position: str,
        ordered_player_ids: List[int]
    ) -> bool:
        """
        Reorder depth chart for a specific position.

        Updates depth_chart_order for all players at position based on new order.
        First player gets depth_order=1 (starter), second gets depth_order=2, etc.

        Args:
            team_id: Team ID (1-32)
            position: Position name (e.g., "quarterback", "running_back")
            ordered_player_ids: List of player IDs in desired depth chart order

        Returns:
            True if reorder succeeded, False otherwise

        Example:
            # Swap QB1 and QB2
            qb_depth = model.get_position_depth_chart(22, "quarterback")
            ordered_ids = [qb_depth[1]['player_id'], qb_depth[0]['player_id']]
            success = model.reorder_position_depth_chart(22, "quarterback", ordered_ids)
            if success:
                print("Depth chart reordered successfully!")
        """
        try:
            # Call API to reorder depth chart
            success = self.depth_chart_api.reorder_position_depth(
                dynasty_id=self.dynasty_id,
                team_id=team_id,
                position=position,
                ordered_player_ids=ordered_player_ids
            )

            return success

        except Exception as e:
            print(f"[ERROR TeamDataModel] Failed to reorder depth chart for {position}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def swap_player_depths(
        self,
        team_id: int,
        player1_id: int,
        player2_id: int
    ) -> bool:
        """
        Swap depth chart positions between two players.

        Players must be on same team and same position. Their depth_chart_order
        values will be exchanged atomically in the database.

        Args:
            team_id: Team ID (1-32)
            player1_id: First player ID (typically starter)
            player2_id: Second player ID (typically bench player)

        Returns:
            True if swap succeeded, False otherwise

        Example:
            # Swap starter QB with backup QB
            success = model.swap_player_depths(22, starter_id=12345, bench_id=67890)
            if success:
                print("QB depth chart swapped successfully!")
        """
        try:
            # Call API to swap depth positions
            success = self.depth_chart_api.swap_depth_positions(
                dynasty_id=self.dynasty_id,
                team_id=team_id,
                player1_id=player1_id,
                player2_id=player2_id
            )

            return success

        except Exception as e:
            print(f"[ERROR TeamDataModel] Failed to swap player depths: {e}")
            import traceback
            traceback.print_exc()
            return False

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
