"""
Draft Data Model - Domain Model for Draft UI

This module provides data access and business logic for draft-related UI components.
Follows the Domain Model pattern established in CalendarDataModel.

ARCHITECTURE PATTERN:
-------------------
The domain model serves as an intermediary layer between the UI Controller and the
database/business logic layer.

Responsibilities:
- Query draft order from database (draft_order table)
- Retrieve draft prospects and draft picks made
- Merge draft order with prospect data
- Enrich draft data with team names and metadata
- Handle dynasty-specific data isolation

Attributes:
    dynasty_id: Dynasty identifier for data isolation
    season: Current season year
    draft_class_api: Draft class database API instance (owned by model)
    draft_order_service: Draft order calculation service (owned by model)
    team_loader: Team metadata loader (owned by model)
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.draft_class_api import DraftClassAPI
from offseason.draft_order_service import DraftOrderService, DraftPickOrder, TeamRecord
from team_management.teams.team_loader import TeamDataLoader
from database.api import DatabaseAPI
from database.playoff_results_api import PlayoffResultsAPI
from offseason.draft_utils import convert_standings_to_team_records, convert_all_draft_picks


class DraftDataModel:
    """
    Domain model for draft data access and business logic.

    This class demonstrates the Domain Model pattern by:
    - Owning all database API instances (DraftClassAPI, DraftOrderService, TeamDataLoader)
    - Encapsulating all business logic for draft operations
    - Providing clean, testable interfaces without UI dependencies
    - Serving as a data access layer for draft UI components

    Responsibilities:
    - Query draft order from database/service
    - Retrieve draft prospects and picks made
    - Merge draft order with prospect data
    - Enrich data with team names and metadata
    - Manage dynasty-specific data isolation
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int = 2025):
        """
        Initialize draft data model.

        The domain model OWNS all database API instances. This ensures:
        - Single source of truth for database connections
        - Consistent dynasty/season context across queries
        - Clear ownership of data access responsibilities

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            season: Current season year (default: 2025)
        """
        self.dynasty_id = dynasty_id
        self.season = season
        self.db_path = db_path

        # Domain model OWNS the database APIs
        # Controllers delegate all data access to this model
        self.draft_class_api = DraftClassAPI(db_path)
        self.draft_order_service = DraftOrderService(dynasty_id, season)
        self.team_loader = TeamDataLoader()
        self.database_api = DatabaseAPI(db_path)

    def get_draft_order(self, round_number: Optional[int] = None) -> Dict[str, Any]:
        """
        Get draft order for specific round or all rounds WITH EDGE CASE HANDLING.

        EDGE CASES HANDLED:
        -------------------
        1. Missing standings: Returns empty picks with error message
        2. Incomplete playoffs: Returns partial draft order with warning
        3. Missing schedule data: Uses SOS = 0.500 default with warning
        4. Database errors: Returns empty picks with error logged
        5. Invalid round number: Returns empty picks with error

        Args:
            round_number: Optional round number (1-7). If None, returns all rounds.

        Returns:
            Dict with:
            {
                'picks': List[Dict],  # Draft pick dicts
                'playoffs_complete': bool,  # True if playoffs finished
                'errors': List[str],  # Error messages (empty if successful)
                'warnings': List[str]  # Warning messages (non-fatal issues)
            }
        """
        result = {
            'picks': [],
            'playoffs_complete': True,
            'errors': [],
            'warnings': []
        }

        try:
            # Step 1: Get standings from database
            try:
                standings = self.database_api.get_standings(
                    dynasty_id=self.dynasty_id,
                    season=self.season - 1,
                    season_type="regular_season"
                )
            except Exception as e:
                result['errors'].append(f"Failed to fetch standings: {str(e)}")
                return result

            # Validate standings exist
            if not standings or 'divisions' not in standings:
                result['errors'].append("No standings data found. Please complete a regular season first.")
                return result

            # Check if divisions are empty
            total_teams = sum(len(teams) for teams in standings['divisions'].values())
            if total_teams == 0:
                result['errors'].append("No standings data found. Please complete a regular season first.")
                return result

            # Step 2: Convert standings to TeamRecord format
            try:
                team_records = convert_standings_to_team_records(standings)
            except ValueError as e:
                result['errors'].append(f"Invalid standings data: {str(e)}")
                return result

            # Check if all teams have 0-0-0 records (indicates no games played)
            if all(rec.wins == 0 and rec.losses == 0 and rec.ties == 0 for rec in team_records):
                result['errors'].append("No games played yet. Please complete a regular season first.")
                return result

            # Step 3: Get playoff results (handle incomplete playoffs)
            playoff_api = PlayoffResultsAPI(self.db_path)
            try:
                playoff_results = playoff_api.get_playoff_results(
                    dynasty_id=self.dynasty_id,
                    season=self.season - 1
                )
                result['playoffs_complete'] = True
            except ValueError as e:
                # Playoffs incomplete - use empty results
                result['playoffs_complete'] = False
                result['warnings'].append("Playoffs not complete. Draft order shows non-playoff teams only.")
                playoff_results = {
                    'wild_card_losers': [],
                    'divisional_losers': [],
                    'conference_losers': [],
                    'super_bowl_loser': None,
                    'super_bowl_winner': None
                }

            # Step 4: Get schedules and calculate SOS
            try:
                schedules = self.database_api.get_all_team_schedules(
                    dynasty_id=self.dynasty_id,
                    season=self.season - 1,
                    season_type="regular_season"
                )

                # Calculate SOS for each team (populates service cache)
                for team_record in team_records:
                    team_schedule = schedules.get(team_record.team_id, [])
                    if team_schedule:
                        self.draft_order_service.calculate_strength_of_schedule(
                            team_id=team_record.team_id,
                            all_standings=team_records,
                            schedule=team_schedule
                        )
            except Exception as e:
                result['warnings'].append(f"Schedule data unavailable. Using default SOS (0.500): {str(e)}")

            # Step 5: Calculate draft order
            try:
                draft_picks = self.draft_order_service.calculate_draft_order(
                    standings=team_records,
                    playoff_results=playoff_results
                )
            except ValueError as e:
                result['errors'].append(f"Draft order calculation failed: {str(e)}")
                return result

            # Step 6: Convert to dict format
            picks = []
            all_teams = {team.team_id: team for team in self.team_loader.get_all_teams()}

            for pick in draft_picks:
                team = all_teams.get(pick.team_id)
                team_name = team.full_name if team else f"Team {pick.team_id}"
                team_abbrev = team.abbreviation if team else f"T{pick.team_id}"

                pick_dict = {
                    'overall_pick': pick.overall_pick,
                    'round_number': pick.round_number,
                    'pick_in_round': pick.pick_in_round,
                    'team_id': pick.team_id,
                    'original_team_id': pick.original_team_id,
                    'team_name': team_name,
                    'team_abbrev': team_abbrev,
                    'team_record': pick.team_record,
                    'reason': pick.reason,
                    'sos': pick.strength_of_schedule,
                    'is_executed': False,
                    'player': None,
                }
                picks.append(pick_dict)

            # Step 7: Enrich picks
            picks = self._enrich_picks_with_team_data(picks)
            picks = self._add_player_data(picks)

            # Step 8: Filter by round if specified
            if round_number is not None:
                if round_number < 1 or round_number > 7:
                    result['errors'].append(f"Invalid round number: {round_number}. Must be 1-7.")
                    return result
                picks = [p for p in picks if p['round_number'] == round_number]

            result['picks'] = picks
            return result

        except Exception as e:
            result['errors'].append(f"Unexpected error: {str(e)}")
            return result

    def get_team_draft_picks(self, team_id: int) -> List[Dict[str, Any]]:
        """
        Get all draft picks for a specific team.

        BUSINESS LOGIC:
        --------------
        Filter complete draft order to show only picks owned by specified team.
        Useful for "Team View" tab in draft UI.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of team's picks across all 7 rounds
        """
        result = self.get_draft_order()
        all_picks = result['picks']
        return [pick for pick in all_picks if pick['team_id'] == team_id]

    def get_available_prospects(
        self,
        position_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get available (undrafted) prospects.

        Args:
            position_filter: Position to filter by (e.g., "QB", "WR")
            limit: Maximum prospects to return

        Returns:
            List of prospect dicts with player info
        """
        # Check if draft class exists for this dynasty/season
        if not self.draft_class_api.dynasty_has_draft_class(self.dynasty_id, self.season):
            return []

        # Get prospects from database
        if position_filter:
            prospects = self.draft_class_api.get_prospects_by_position(
                dynasty_id=self.dynasty_id,
                season=self.season,
                position=position_filter,
                available_only=True
            )
        else:
            prospects = self.draft_class_api.get_all_prospects(
                dynasty_id=self.dynasty_id,
                season=self.season,
                available_only=True
            )

        # Limit results
        return prospects[:limit]

    def get_draft_pick_details(self, overall_pick: int) -> Dict[str, Any]:
        """
        Get details for a specific draft pick.

        Args:
            overall_pick: Overall pick number (1-224)

        Returns:
            Dict with pick details including player if drafted
        """
        all_picks = self.get_draft_order()
        for pick in all_picks:
            if pick['overall_pick'] == overall_pick:
                return pick
        return {}

    def is_draft_complete(self) -> bool:
        """
        Check if all 224 picks have been made.

        Returns:
            True if all picks are completed
        """
        summary = self.get_draft_summary()
        return summary['picks_remaining'] == 0

    def get_draft_summary(self) -> Dict[str, Any]:
        """
        Get draft summary statistics.

        BUSINESS LOGIC:
        --------------
        Calculate summary stats from draft order and prospect data:
        - Total picks in draft
        - How many picks have been made
        - How many picks remaining
        - Current round
        - Current pick number

        Returns:
            {
                'total_picks': int,
                'picks_made': int,
                'picks_remaining': int,
                'current_round': int,
                'current_pick': int,
            }
        """
        # Get all picks (new dict format)
        result = self.get_draft_order()
        all_picks = result['picks']

        if not all_picks:
            return {
                'total_picks': 224,  # 7 rounds × 32 picks
                'picks_made': 0,
                'picks_remaining': 224,
                'current_round': 1,
                'current_pick': 1,
            }

        # Count picks made (those with player assigned)
        picks_made = sum(1 for pick in all_picks if pick.get('player') is not None)
        total_picks = len(all_picks)
        picks_remaining = total_picks - picks_made

        # Find current pick (first unpicked)
        current_round = 1
        current_pick = 1
        for pick in all_picks:
            if pick.get('player') is None:
                current_round = pick['round_number']
                current_pick = pick['overall_pick']
                break

        return {
            'total_picks': total_picks,
            'picks_made': picks_made,
            'picks_remaining': picks_remaining,
            'current_round': current_round,
            'current_pick': current_pick,
        }

    def get_dynasty_info(self) -> Dict[str, str]:
        """
        Get dynasty information.

        Returns:
            Dict with dynasty_id and season as strings
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': str(self.season)
        }

    def _calculate_strength_of_schedule(
        self,
        schedules: Dict[int, List[int]],
        team_records: List[TeamRecord]
    ) -> Dict[int, float]:
        """
        Calculate strength of schedule for each team.

        SOS = average opponent win percentage

        Args:
            schedules: Dict mapping team_id -> list of opponent team_ids
            team_records: List of TeamRecord objects with win percentages

        Returns:
            Dict mapping team_id -> SOS value (0.0-1.0)
        """
        # Create dict mapping team_id -> win_percentage
        win_pct_by_team = {
            record.team_id: record.win_percentage
            for record in team_records
        }

        sos_dict = {}

        # Calculate SOS for each team
        for team_id, opponent_ids in schedules.items():
            if not opponent_ids:
                # No schedule data - use 0.500 as default
                sos_dict[team_id] = 0.500
                continue

            # Calculate average opponent win percentage
            opponent_win_pcts = [
                win_pct_by_team.get(opp_id, 0.500)
                for opp_id in opponent_ids
            ]

            sos = sum(opponent_win_pcts) / len(opponent_win_pcts)
            sos_dict[team_id] = sos

        return sos_dict

    # ========================================================================
    # PRIVATE ENRICHMENT METHODS
    # ========================================================================

    def _enrich_picks_with_team_data(self, picks: List[Dict]) -> List[Dict]:
        """
        Enrich pick dictionaries with team information for UI display.

        Adds to each pick:
        - team_name: Full team name (e.g., "Detroit Lions") [if not present]
        - team_abbrev: Abbreviation (e.g., "DET") [if not present]
        - primary_color: Team primary color hex code
        - secondary_color: Team secondary color hex code
        - original_team_name: Original team name (for traded picks)
        - original_team_abbrev: Original team abbreviation

        Note: team_name and team_abbrev may already be set by get_draft_order().
        This method only adds them if missing, and always adds color data.

        Args:
            picks: List of pick dictionaries from get_draft_order()

        Returns:
            Same list with team data added to each dict
        """
        for pick in picks:
            # Enrich current team data
            team_id = pick.get('team_id')
            if team_id:
                team = self.team_loader.get_team_by_id(team_id)
                if team:
                    # Only set if not already present (get_draft_order may have set it)
                    if 'team_name' not in pick:
                        pick['team_name'] = team.full_name
                    if 'team_abbrev' not in pick:
                        pick['team_abbrev'] = team.abbreviation
                    # Always add colors
                    pick['primary_color'] = team.colors.get('primary', '#000000')
                    pick['secondary_color'] = team.colors.get('secondary', '#FFFFFF')
                else:
                    # Team not found - use placeholder values
                    if 'team_name' not in pick:
                        pick['team_name'] = 'Unknown Team'
                    if 'team_abbrev' not in pick:
                        pick['team_abbrev'] = 'UNK'
                    pick['primary_color'] = '#000000'
                    pick['secondary_color'] = '#FFFFFF'

            # Enrich original team data (for traded picks)
            original_team_id = pick.get('original_team_id')
            if original_team_id:
                original_team = self.team_loader.get_team_by_id(original_team_id)
                if original_team:
                    pick['original_team_name'] = original_team.full_name
                    pick['original_team_abbrev'] = original_team.abbreviation
                else:
                    pick['original_team_name'] = 'Unknown Team'
                    pick['original_team_abbrev'] = 'UNK'

        return picks

    def _add_player_data(self, picks: List[Dict]) -> List[Dict]:
        """
        Add drafted player information to executed picks.

        Adds to each pick (if player drafted):
        - player_name: Player's full name
        - position: Player position
        - college: Player's college
        - overall_rating: Player's overall rating

        Args:
            picks: List of pick dictionaries

        Returns:
            Same list with player data added where available
        """
        for pick in picks:
            # Check if pick has been executed
            is_executed = pick.get('is_executed', False)

            if is_executed and 'player_id' in pick:
                # Get player data from draft class API
                player_id = pick['player_id']
                prospect = self.draft_class_api.get_prospect_by_id(
                    player_id=player_id,
                    dynasty_id=self.dynasty_id
                )

                if prospect:
                    # Add player data to pick
                    pick['player_name'] = f"{prospect['first_name']} {prospect['last_name']}"
                    pick['position'] = prospect.get('position')
                    pick['college'] = prospect.get('college')
                    pick['overall_rating'] = prospect.get('overall')
                else:
                    # Player not found - use None values
                    pick['player_name'] = None
                    pick['position'] = None
                    pick['college'] = None
                    pick['overall_rating'] = None
            else:
                # Pick not executed - add None values
                pick['player_name'] = None
                pick['position'] = None
                pick['college'] = None
                pick['overall_rating'] = None

        return picks
