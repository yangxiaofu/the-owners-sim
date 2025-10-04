"""
Full Season Controller

Unified controller orchestrating complete NFL season simulation from
Week 1 Regular Season → Super Bowl → Offseason.

This controller manages the three distinct phases:
1. REGULAR_SEASON: 272 games across 18 weeks
2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
3. OFFSEASON: Post-season state with summary

Responsibilities:
- Coordinate SeasonController and PlayoffController
- Handle automatic phase transitions
- Maintain calendar continuity
- Preserve dynasty isolation
- Provide unified API for day/week advancement
"""

import logging
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

# Add parent directories to path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(current_dir.parent / "interactive_season_sim"))

from calendar.date_models import Date
from calendar.season_phase_tracker import SeasonPhase
from playoff_system.playoff_controller import PlayoffController
from playoff_system.playoff_seeder import PlayoffSeeder
from database.api import DatabaseAPI

# Import SeasonController from interactive_season_sim
try:
    from season_controller import SeasonController
except ImportError:
    # Fallback to absolute import
    from demo.interactive_season_sim.season_controller import SeasonController


class FullSeasonController:
    """
    Unified controller orchestrating complete NFL season simulation.

    Manages three distinct phases:
    1. REGULAR_SEASON: 272 games across 18 weeks
    2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
    3. OFFSEASON: Post-season state with summary

    Usage:
        # Create controller
        controller = FullSeasonController(
            database_path="season_2024.db",
            dynasty_id="my_dynasty",
            season_year=2024
        )

        # Advance by day
        result = controller.advance_day()

        # Advance by week
        weekly_result = controller.advance_week()

        # Simulate to end
        summary = controller.simulate_to_end()

        # Check current phase
        phase = controller.get_current_phase()
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str = "default",
        season_year: int = 2024,
        start_date: Optional[Date] = None,
        enable_persistence: bool = True,
        verbose_logging: bool = True
    ):
        """
        Initialize full season controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            start_date: Season start date (defaults to Week 1 Thursday)
            enable_persistence: Whether to save stats to database
            verbose_logging: Whether to print progress messages
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        self.logger = logging.getLogger(self.__class__.__name__)

        # Default to first Thursday in September
        if start_date is None:
            start_date = Date(season_year, 9, 5)

        self.start_date = start_date

        # Initialize season controller (always starts in regular season)
        self.season_controller = SeasonController(
            database_path=database_path,
            start_date=start_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging
        )

        # Access the shared calendar from season controller
        self.calendar = self.season_controller.calendar

        # Playoff controller created when needed
        self.playoff_controller: Optional[PlayoffController] = None

        # State tracking
        self.current_phase = SeasonPhase.REGULAR_SEASON
        self.active_controller = self.season_controller

        # Season summary (generated in offseason)
        self.season_summary: Optional[Dict[str, Any]] = None

        # Statistics
        self.total_games_played = 0
        self.total_days_simulated = 0

        # Database API for data retrieval
        self.database_api = DatabaseAPI(database_path)

        # Calculate last scheduled regular season game date for flexible end-of-season detection
        self.last_regular_season_game_date = self._get_last_regular_season_game_date()

        # Ensure dynasty record exists (required for foreign key constraints)
        self.database_api.db_connection.ensure_dynasty_exists(
            dynasty_id=dynasty_id,
            dynasty_name=f"Dynasty {dynasty_id}",
            owner_name=None,
            team_id=None
        )

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'FULL SEASON CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {season_year}")
            print(f"Start Date: {start_date}")
            print(f"Dynasty: {dynasty_id}")
            print(f"Database: {database_path}")
            print(f"Current Phase: {self.current_phase.value}")
            print(f"Persistence: {'ENABLED' if enable_persistence else 'DISABLED'}")
            print(f"{'='*80}")

    # ========== Public API ==========

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance simulation by 1 day.

        Returns:
            Dictionary with results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "current_phase": str,
                "phase_transition": Optional[Dict],
                "success": bool
            }
        """
        # Handle offseason case
        if self.current_phase == SeasonPhase.OFFSEASON:
            return {
                "date": str(self.calendar.get_current_date()),
                "games_played": 0,
                "results": [],
                "current_phase": "offseason",
                "phase_transition": None,
                "success": True,
                "message": "Season complete. No more games to simulate."
            }

        # Delegate to active controller
        result = self.active_controller.advance_day()

        # Update statistics
        self.total_games_played += result.get('games_played', 0)
        self.total_days_simulated += 1

        # Check for phase transitions
        phase_transition = self._check_phase_transition()
        if phase_transition:
            result['phase_transition'] = phase_transition

        result['current_phase'] = self.current_phase.value

        return result

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 7 days.

        Returns:
            Dictionary with weekly summary
        """
        if self.current_phase == SeasonPhase.OFFSEASON:
            return {
                "week_complete": False,
                "current_phase": "offseason",
                "message": "Season complete."
            }

        # Delegate to active controller
        result = self.active_controller.advance_week()

        # Update statistics
        self.total_games_played += result.get('total_games_played', 0)

        # Check for phase transitions
        phase_transition = self._check_phase_transition()
        if phase_transition:
            result['phase_transition'] = phase_transition

        result['current_phase'] = self.current_phase.value

        return result

    def simulate_to_end(self) -> Dict[str, Any]:
        """
        Simulate entire remaining season (all phases).

        Continues until offseason reached.

        Returns:
            Complete season summary
        """
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATING TO END OF SEASON'.center(80)}")
            print(f"{'='*80}")

        # Continue until offseason
        while self.current_phase != SeasonPhase.OFFSEASON:
            self.advance_week()

        return {
            "start_date": str(start_date),
            "end_date": str(self.calendar.get_current_date()),
            "total_games": self.total_games_played - initial_games,
            "final_phase": self.current_phase.value,
            "season_summary": self.season_summary,
            "success": True
        }

    def get_current_phase(self) -> SeasonPhase:
        """Get current season phase."""
        return self.current_phase

    def get_current_standings(self) -> Dict[str, Any]:
        """
        Get current standings (only available during regular season).

        Returns:
            Standings organized by division/conference
        """
        if self.current_phase != SeasonPhase.REGULAR_SEASON:
            # Return final standings from database
            return self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

        return self.season_controller.get_current_standings()

    def get_playoff_bracket(self) -> Optional[Dict[str, Any]]:
        """
        Get playoff bracket (only available during playoffs).

        Returns:
            Bracket data or None if not in playoffs
        """
        if self.current_phase != SeasonPhase.PLAYOFFS:
            return None

        if not self.playoff_controller:
            return None

        return self.playoff_controller.get_current_bracket()

    def get_current_state(self) -> Dict[str, Any]:
        """Get comprehensive current state."""
        return {
            "current_phase": self.current_phase.value,
            "current_date": str(self.calendar.get_current_date()),
            "season_year": self.season_year,
            "dynasty_id": self.dynasty_id,
            "total_games_played": self.total_games_played,
            "total_days_simulated": self.total_days_simulated,
            "active_controller": type(self.active_controller).__name__ if self.active_controller else None
        }

    # ========== Private Methods ==========

    def _check_phase_transition(self) -> Optional[Dict[str, Any]]:
        """
        Check if phase transition should occur.

        Returns:
            Transition info if occurred, None otherwise
        """
        if self.current_phase == SeasonPhase.REGULAR_SEASON:
            if self._is_regular_season_complete():
                self._transition_to_playoffs()
                return {
                    "from_phase": "regular_season",
                    "to_phase": "playoffs",
                    "trigger": "272_games_complete"
                }

        elif self.current_phase == SeasonPhase.PLAYOFFS:
            if self._is_super_bowl_complete():
                self._transition_to_offseason()
                return {
                    "from_phase": "playoffs",
                    "to_phase": "offseason",
                    "trigger": "super_bowl_complete"
                }

        return None

    def _get_last_regular_season_game_date(self) -> Date:
        """
        Query event database to find the date of the last scheduled regular season game.

        This provides flexible end-of-season detection that adapts to any schedule length
        (17 weeks, 18 weeks, etc.) without code changes.

        Returns:
            Date of the last scheduled regular season game
        """
        try:
            # Get all GAME events from event database
            all_game_events = self.season_controller.event_db.get_events_by_type("GAME")

            # Filter for regular season games (exclude playoff/preseason)
            regular_season_events = [
                e for e in all_game_events
                if not e.get('game_id', '').startswith('playoff_')
                and not e.get('game_id', '').startswith('preseason_')
            ]

            if not regular_season_events:
                # No regular season games scheduled - return season end date as fallback
                self.logger.warning("No regular season games found in event database")
                return Date(self.season_year, 12, 31)  # Dec 31 fallback

            # Find the event with the maximum timestamp
            last_event = max(regular_season_events, key=lambda e: e['timestamp'])

            # Convert timestamp to Date
            last_datetime = last_event['timestamp']
            last_date = Date(
                year=last_datetime.year,
                month=last_datetime.month,
                day=last_datetime.day
            )

            if self.verbose_logging:
                self.logger.info(f"Last regular season game scheduled for: {last_date}")

            return last_date

        except Exception as e:
            self.logger.error(f"Error calculating last regular season game date: {e}")
            # Fallback to Dec 31 if calculation fails
            return Date(self.season_year, 12, 31)

    def _is_regular_season_complete(self) -> bool:
        """
        Check if regular season is complete by comparing current date to last scheduled game.

        This replaces the hardcoded game count check (>= 272) with a flexible date-based
        approach that adapts to any schedule length.

        Returns:
            True if current date is after the last scheduled regular season game
        """
        current_date = self.calendar.get_current_date()
        return current_date > self.last_regular_season_game_date

    def _is_super_bowl_complete(self) -> bool:
        """Check if Super Bowl has been played."""
        if not self.playoff_controller:
            return False

        super_bowl_games = self.playoff_controller.get_round_games('super_bowl')
        return len(super_bowl_games) > 0

    def _transition_to_playoffs(self):
        """Execute transition from regular season to playoffs."""
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'REGULAR SEASON COMPLETE - PLAYOFFS STARTING'.center(80)}")
            print(f"{'='*80}")

        try:
            # 1. Get final standings from database
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data or not standings_data.get('divisions'):
                self.logger.error("No standings found for playoff seeding")
                raise RuntimeError("Cannot calculate playoff seeding - no standings available")

            # 2. Convert standings to format expected by PlayoffSeeder
            # DatabaseAPI returns standings organized by division/conference
            # Each team_data has: {'team_id': int, 'standing': EnhancedTeamStanding}
            standings_dict = {}
            for division_name, teams in standings_data.get('divisions', {}).items():
                for team_data in teams:
                    team_id = team_data['team_id']
                    # Use the EnhancedTeamStanding object directly from database
                    standings_dict[team_id] = team_data['standing']

            # 3. Calculate playoff seeding using PlayoffSeeder
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict,
                season=self.season_year,
                week=18
            )

            if self.verbose_logging:
                print(f"\n📋 Playoff Seeding Calculated")
                print(f"\nAFC Seeds:")
                for seed in playoff_seeding.afc.seeds:
                    print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")
                print(f"\nNFC Seeds:")
                for seed in playoff_seeding.nfc.seeds:
                    print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

            # 4. Calculate Wild Card start date
            wild_card_date = self._calculate_wild_card_date()

            if self.verbose_logging:
                print(f"\n📅 Wild Card Weekend: {wild_card_date}")

            # 5. Initialize PlayoffController with real seeding and shared calendar
            self.playoff_controller = PlayoffController(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season_year=self.season_year,
                wild_card_start_date=wild_card_date,
                enable_persistence=self.enable_persistence,
                verbose_logging=self.verbose_logging
            )

            # Replace the playoff controller's calendar with the shared calendar
            # to maintain date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # Override the playoff controller's random seeding with real seeding
            self.playoff_controller.original_seeding = playoff_seeding

            # Schedule Wild Card round with real seeding
            result = self.playoff_controller.playoff_scheduler.schedule_wild_card_round(
                seeding=playoff_seeding,
                start_date=wild_card_date,
                season=self.season_year,
                dynasty_id=self.dynasty_id
            )

            # Store the wild card bracket
            self.playoff_controller.brackets['wild_card'] = result['bracket']

            # 6. Update state
            self.current_phase = SeasonPhase.PLAYOFFS
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ Playoff bracket initialized: {result['games_scheduled']} games scheduled")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error transitioning to playoffs: {e}")
            if self.verbose_logging:
                print(f"❌ Playoff transition failed: {e}")
            raise

    def _transition_to_offseason(self):
        """Execute transition from playoffs to offseason."""
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON COMPLETE - ENTERING OFFSEASON'.center(80)}")
            print(f"{'='*80}")

        try:
            # 1. Get Super Bowl result
            super_bowl_games = self.playoff_controller.get_round_games('super_bowl')
            super_bowl_result = super_bowl_games[0] if super_bowl_games else None

            champion_id = None
            if super_bowl_result:
                champion_id = super_bowl_result.get('winner_id')

            # 2. Update state
            self.current_phase = SeasonPhase.OFFSEASON
            self.active_controller = None  # No active controller in offseason

            # 3. Generate season summary
            self.season_summary = self._generate_season_summary()

            # 4. Notify user
            if self.verbose_logging:
                if champion_id:
                    from team_management.teams.team_loader import get_team_by_id
                    champion = get_team_by_id(champion_id)
                    print(f"\n🏆 Super Bowl Champion: {champion.full_name}")

                print(f"\n📊 Season Summary Generated")
                print(f"   Total Games: {self.total_games_played}")
                print(f"   Total Days: {self.total_days_simulated}")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error transitioning to offseason: {e}")
            if self.verbose_logging:
                print(f"❌ Offseason transition failed: {e}")
            raise

    def _calculate_wild_card_date(self) -> Date:
        """
        Calculate Wild Card weekend start date.

        NFL Scheduling:
        - Week 18 typically ends Sunday, January 6-7
        - Wild Card starts 2 weeks later (Saturday, January 18-19)

        Returns:
            Wild Card Saturday date
        """
        # Get current date (after Week 18)
        final_reg_season_date = self.calendar.get_current_date()

        # Add 14 days (2 weeks)
        wild_card_date = final_reg_season_date.add_days(14)

        # Adjust to next Saturday
        # Use Python's weekday() where Monday=0, Saturday=5, Sunday=6
        while wild_card_date.to_python_date().weekday() != 5:  # 5 = Saturday
            wild_card_date = wild_card_date.add_days(1)
            # Safety check to prevent infinite loop
            if wild_card_date.days_until(final_reg_season_date) > 30:
                # If we've gone more than 30 days, something is wrong
                # Just use the date 14 days out
                wild_card_date = final_reg_season_date.add_days(14)
                break

        return wild_card_date

    def _generate_season_summary(self) -> Dict[str, Any]:
        """
        Generate comprehensive season summary.

        Returns:
            Summary with standings, champions, stat leaders
        """
        try:
            # Get final standings
            final_standings = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            # Get Super Bowl winner
            super_bowl_games = self.playoff_controller.get_round_games('super_bowl') if self.playoff_controller else []
            champion_id = super_bowl_games[0]['winner_id'] if super_bowl_games else None

            # Note: Stat leaders queries would require additional DatabaseAPI methods
            # For now, we'll return basic summary
            summary = {
                "season_year": self.season_year,
                "dynasty_id": self.dynasty_id,
                "final_standings": final_standings,
                "super_bowl_champion": champion_id,
                "total_games": self.total_games_played,
                "total_days": self.total_days_simulated,
                "final_date": str(self.calendar.get_current_date())
            }

            # Try to get stat leaders if methods exist
            try:
                # These would be future enhancements to DatabaseAPI
                # For now, they're placeholders
                summary["regular_season_leaders"] = {}
                summary["playoff_leaders"] = {}
            except Exception as e:
                self.logger.warning(f"Could not retrieve stat leaders: {e}")

            return summary

        except Exception as e:
            self.logger.error(f"Error generating season summary: {e}")
            return {
                "season_year": self.season_year,
                "dynasty_id": self.dynasty_id,
                "error": str(e)
            }

    def __str__(self) -> str:
        """String representation"""
        return (f"FullSeasonController(season={self.season_year}, "
                f"phase={self.current_phase.value}, "
                f"games={self.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"FullSeasonController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
