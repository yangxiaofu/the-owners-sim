"""
League Controller for The Owner's Sim UI

Mediates between League View and database for league-wide statistics.
Provides access to standings, playoff picture, and statistical leaders.
"""

from typing import List, Dict, Any, Optional
import sys
import os

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from team_management.teams.team_loader import TeamDataLoader, Team
from database.api import DatabaseAPI
from database.dynasty_state_api import DynastyStateAPI
from src.calendar.season_phase_tracker import SeasonPhase


class LeagueController:
    """
    Controller for League view operations.

    Manages league-wide statistics, standings, and playoff scenarios.
    Follows the pattern: View → Controller → Database

    Separation of concerns:
    - LeagueController: League-wide statistics (THIS)
    - SeasonController: Season management and calendar operations
    - TeamController: Team-specific data and roster management
    """

    def __init__(self, db_path: str, dynasty_id: str, main_window=None):
        """
        Initialize league controller.

        Args:
            db_path: Path to SQLite database
            dynasty_id: Dynasty identifier for data isolation
            main_window: Reference to MainWindow for season access (optional)
        """
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.main_window = main_window

        # Initialize data access components
        self.team_loader = TeamDataLoader()
        self.db_api = DatabaseAPI(db_path)
        self.dynasty_api = DynastyStateAPI(db_path)  # For phase detection

    @property
    def season(self) -> int:
        """Current season year (proxied from main window)."""
        if self.main_window is not None:
            return self.main_window.season
        return 2025  # Fallback for testing/standalone usage

    def get_all_teams(self) -> List[Team]:
        """
        Get all 32 NFL teams with metadata.

        Returns:
            List of Team objects with full metadata
        """
        return self.team_loader.get_all_teams()

    def get_teams_by_division(self, conference: str, division: str) -> List[Team]:
        """
        Get teams in a specific division.

        Args:
            conference: 'AFC' or 'NFC'
            division: 'North', 'South', 'East', or 'West'

        Returns:
            List of Team objects in the division
        """
        return self.team_loader.get_teams_by_division(conference, division)

    def get_teams_by_conference(self, conference: str) -> List[Team]:
        """
        Get teams by conference.

        Args:
            conference: 'AFC' or 'NFC'

        Returns:
            List of Team objects in the conference
        """
        return self.team_loader.get_teams_by_conference(conference)

    def _get_current_season_type(self) -> str:
        """
        Determine the season_type based on current phase from dynasty_state.

        Maps the current phase (PRESEASON, REGULAR_SEASON, PLAYOFFS, OFFSEASON)
        to the database season_type column value ('preseason', 'regular_season', 'playoffs').

        Returns:
            str: 'preseason', 'regular_season', or 'playoffs'
            Defaults to 'regular_season' if phase cannot be determined or on error.
        """
        try:
            # Get current dynasty state
            state = self.dynasty_api.get_current_state(self.dynasty_id, self.season)

            if not state:
                return 'regular_season'  # Safe default

            # Get current phase from state (lowercase string from database)
            current_phase_str = state.get('current_phase', 'regular_season')

            # Convert to SeasonPhase enum (handles case-insensitive conversion)
            try:
                current_phase = SeasonPhase.from_string(current_phase_str)
            except ValueError:
                # Fallback to regular season if invalid phase
                current_phase = SeasonPhase.REGULAR_SEASON

            # Map enum to season_type for standings query
            # OFFSEASON shows regular_season final records, others map directly
            if current_phase.value == "offseason":
                season_type = SeasonPhase.REGULAR_SEASON.value
            else:
                season_type = current_phase.value

            print(f"[LeagueController] Current phase: {current_phase.name}, season_type: {season_type}")
            return season_type

        except Exception as e:
            print(f"[WARNING LeagueController] Could not determine season_type: {e}, using 'regular_season'")
            return 'regular_season'  # Safe fallback

    def get_standings(self) -> Dict[str, Any]:
        """
        Get current league standings for the current phase.

        Returns standings matching the current season phase:
        - During PRESEASON: Shows preseason records
        - During REGULAR_SEASON: Shows regular season records
        - During PLAYOFFS: Shows playoff records
        - During OFFSEASON: Shows regular season final records

        Returns:
            Standings data structure organized by:
            - divisions: 8 NFL divisions with team standings
            - conferences: AFC/NFC conference standings
            - overall: League-wide standings
            - playoff_picture: Current playoff seeding

            Returns empty dict if no season data available.
        """
        try:
            # Get season_type for current phase
            season_type = self._get_current_season_type()

            # Query standings for current phase
            standings = self.db_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season,
                season_type=season_type  # ✅ Pass season_type based on current phase
            )
            return standings
        except Exception as e:
            # Gracefully handle missing data
            print(f"[ERROR] Failed to load standings: {e}")
            return {}

    def get_team_record(self, team_id: int) -> Optional[Dict[str, int]]:
        """
        Get win-loss-tie record for a specific team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Dict with 'wins', 'losses', 'ties' or None if no data available
        """
        standings = self.get_standings()

        if not standings or 'divisions' not in standings:
            return None

        # Search through divisions for this team
        for division_name, division_data in standings['divisions'].items():
            # division_data is already a list of team dicts
            for team_dict in division_data:
                if 'standing' in team_dict:
                    standing = team_dict['standing']
                    if standing.team_id == team_id:
                        return {
                            'wins': standing.wins,
                            'losses': standing.losses,
                            'ties': standing.ties
                        }

        return None

    def get_playoff_picture(self) -> Dict[str, Any]:
        """
        Get current playoff picture with seeding and scenarios.

        Returns:
            Dict with:
            - afc_seeds: List of AFC playoff teams (1-7 seeds)
            - nfc_seeds: List of NFC playoff teams (1-7 seeds)
            - in_hunt: Teams still in playoff contention
            - eliminated: Teams eliminated from playoffs

            Returns empty dict if playoffs not yet determined.
        """
        # TODO: Implement playoff picture calculation
        # For now, extract from standings structure
        standings = self.get_standings()

        if not standings or 'playoff_picture' not in standings:
            return {}

        return standings.get('playoff_picture', {})

    def get_statistical_leaders(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get league leaders in a statistical category.

        Args:
            category: Statistical category (e.g., 'passing_yards', 'rushing_yards', 'sacks')
            limit: Number of leaders to return (default: 10)

        Returns:
            List of dicts with player stats, sorted by category descending

            Returns empty list if no stats available.
        """
        # TODO: Implement statistical leaders query
        # This will require player_stats table queries
        print(f"[INFO LeagueController] Statistical leaders not yet implemented for category: {category}")
        return []

    def get_league_totals(self) -> Dict[str, Any]:
        """
        Get league-wide aggregate statistics.

        Returns:
            Dict with:
            - total_points: Total points scored league-wide
            - total_yards: Total yards gained league-wide
            - average_ppg: Average points per game
            - total_games: Total games played

            Returns empty dict if no stats available.
        """
        # TODO: Implement league totals calculation
        print(f"[INFO LeagueController] League totals not yet implemented")
        return {}

    def get_dynasty_info(self) -> Dict[str, Any]:
        """
        Get current dynasty context information.

        Returns:
            Dict with dynasty_id and season
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season': self.season
        }
