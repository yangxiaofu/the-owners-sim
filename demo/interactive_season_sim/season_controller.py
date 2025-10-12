"""
Season Controller

Core orchestration logic for season simulation.
Coordinates calendar advancement, event execution, and standings tracking.

This controller is the central component for daily and weekly season simulation,
managing the interaction between:
- CalendarComponent (date/time management)
- EventDatabaseAPI (event storage/retrieval)
- SimulationWorkflow (game execution pipeline)
- SimulationExecutor (day simulation orchestration)
- DatabaseAPI (standings and statistics retrieval)
"""

import logging
import sys
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directories to path for imports
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent
sys.path.insert(0, str(project_root / "src"))

from calendar.calendar_component import CalendarComponent
from calendar.simulation_executor import SimulationExecutor
from calendar.date_models import Date
from events import EventDatabaseAPI, GameEvent
from workflows import SimulationWorkflow
from database.api import DatabaseAPI

# Import RandomScheduleGenerator from this directory
try:
    from .random_schedule_generator import RandomScheduleGenerator
except ImportError:
    # Direct execution - use absolute import
    from random_schedule_generator import RandomScheduleGenerator


class SeasonController:
    """
    Core orchestration logic for season simulation.

    Provides comprehensive season management including:
    - Daily and weekly simulation advancement
    - Schedule generation and loading
    - Standings tracking and retrieval
    - Upcoming games querying
    - Current state inspection

    Usage:
        # Create controller
        controller = SeasonController(
            database_path="season_2024.db",
            start_date=Date(2024, 9, 5),
            season_year=2024,
            dynasty_id="my_dynasty"
        )

        # Advance by day
        result = controller.advance_day()

        # Advance by week
        weekly_result = controller.advance_week()

        # Check standings
        standings = controller.get_current_standings()

        # Simulate entire season
        summary = controller.simulate_to_end()
    """

    def __init__(
        self,
        database_path: str,
        start_date: Date,
        season_year: int,
        dynasty_id: str = "default",
        enable_persistence: bool = True,
        verbose_logging: bool = True,
        phase_state: Optional['PhaseState'] = None
    ):
        """
        Initialize season controller.

        Args:
            database_path: Path to SQLite database for event and game storage
            start_date: Dynasty start date - should be ONE DAY BEFORE first game
                       (e.g., Sept 4 if first game is Sept 5)
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            dynasty_id: Dynasty context for data isolation
            enable_persistence: Whether to persist game results to database
            verbose_logging: Whether to print detailed progress messages
            phase_state: Optional shared PhaseState object for multi-phase coordination
        """
        self.database_path = database_path
        self.season_year = season_year
        self.dynasty_id = dynasty_id
        print(f"[DYNASTY_TRACE] SeasonController.__init__(): dynasty_id={dynasty_id}")
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        self.logger = logging.getLogger(self.__class__.__name__)

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Ensure dynasty exists in database (auto-create if needed)
        from database.connection import DatabaseConnection
        db_conn = DatabaseConnection(database_path)
        db_conn.ensure_dynasty_exists(dynasty_id)

        # Store phase_state for passing to components
        self.phase_state = phase_state

        # Initialize core components
        self.calendar = CalendarComponent(
            start_date=start_date,
            season_year=season_year,
            phase_state=phase_state
        )

        self.event_db = EventDatabaseAPI(database_path)

        self.simulation_executor = SimulationExecutor(
            calendar=self.calendar,
            event_db=self.event_db,
            database_path=database_path,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            season_year=season_year,
            phase_state=phase_state
        )

        self.database_api = DatabaseAPI(database_path)

        # Statistics tracking
        self.total_games_played = 0
        self.total_days_simulated = 0
        self.current_week = 1

        # Initialize schedule
        self._initialize_schedule()

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {season_year}")
            print(f"Start Date: {start_date}")
            print(f"Dynasty: {dynasty_id}")
            print(f"Database: {database_path}")
            print(f"Persistence: {'ENABLED' if enable_persistence else 'DISABLED'}")
            print(f"{'='*80}")

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance calendar by 1 day and simulate all scheduled games.

        Returns:
            Dictionary with simulation results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "standings_updated": bool,
                "current_phase": str,
                "phase_transitions": List[Dict],
                "success": bool,
                "errors": List[str]
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"ADVANCING DAY")
            print(f"{'='*80}")

        # Advance calendar by 1 day
        advance_result = self.calendar.advance(1)
        current_date = advance_result.end_date
        self.total_days_simulated += 1

        if self.verbose_logging:
            print(f"Current Date: {current_date}")
            print(f"Total Days Simulated: {self.total_days_simulated}")

        # Simulate all games scheduled for this day
        simulation_result = self.simulation_executor.simulate_day(current_date)

        # Update statistics
        games_played = len([g for g in simulation_result.get('games_played', []) if g.get('success', False)])
        self.total_games_played += games_played

        # Determine if standings were updated (games were played)
        standings_updated = games_played > 0

        if self.verbose_logging and games_played > 0:
            print(f"\n✅ Day complete: {games_played} game(s) played")

        return {
            "date": str(current_date),
            "games_played": games_played,
            "results": simulation_result.get('games_played', []),
            "standings_updated": standings_updated,
            "current_phase": simulation_result.get('current_phase', 'REGULAR_SEASON'),
            "phase_transitions": simulation_result.get('phase_transitions', []),
            "success": simulation_result.get('success', True),
            "errors": simulation_result.get('errors', [])
        }

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance calendar by 7 days, simulating all scheduled games.

        Returns:
            Dictionary with weekly summary:
            {
                "week_number": int,
                "start_date": str,
                "end_date": str,
                "total_games_played": int,
                "daily_results": List[Dict],
                "standings_updated": bool,
                "success": bool
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"ADVANCING WEEK {self.current_week}")
            print(f"{'='*80}")

        start_date = self.calendar.get_current_date()
        daily_results = []
        total_games_this_week = 0

        # Simulate 7 days
        for day in range(7):
            day_result = self.advance_day()
            daily_results.append(day_result)
            total_games_this_week += day_result['games_played']

        end_date = self.calendar.get_current_date()

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"WEEK {self.current_week} COMPLETE")
            print(f"{'='*80}")
            print(f"Date Range: {start_date} to {end_date}")
            print(f"Games Played: {total_games_this_week}")
            print(f"Total Season Games: {self.total_games_played}")
            print(f"{'='*80}")

        self.current_week += 1

        return {
            "week_number": self.current_week - 1,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_games_played": total_games_this_week,
            "daily_results": daily_results,
            "standings_updated": total_games_this_week > 0,
            "success": all(d.get('success', False) for d in daily_results)
        }

    def simulate_to_end(self) -> Dict[str, Any]:
        """
        Simulate remaining season until all games are complete.

        Advances day-by-day until phase changes or all scheduled games
        are completed. Displays progress every 7 days.

        Returns:
            Dictionary with final summary:
            {
                "total_games": int,
                "total_days": int,
                "final_date": str,
                "final_phase": str,
                "final_standings": Dict,
                "success": bool
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATING TO END OF SEASON'.center(80)}")
            print(f"{'='*80}")

        start_date = self.calendar.get_current_date()
        initial_phase = self.calendar.get_current_phase()
        days_simulated = 0
        games_played_total = 0

        # Continue until phase changes or no more games (safety limit: 365 days)
        max_days = 365
        days_since_last_game = 0
        max_days_without_games = 30  # Stop if no games for 30 days

        while days_simulated < max_days:
            # Check if we've gone too long without games
            if days_since_last_game >= max_days_without_games:
                if self.verbose_logging:
                    print(f"\n⚠️  No games scheduled for {max_days_without_games} days - ending simulation")
                break

            # Advance day
            day_result = self.advance_day()
            days_simulated += 1
            games_this_day = day_result['games_played']
            games_played_total += games_this_day

            if games_this_day > 0:
                days_since_last_game = 0
            else:
                days_since_last_game += 1

            # Display progress every 7 days
            if self.verbose_logging and days_simulated % 7 == 0:
                current_date = self.calendar.get_current_date()
                print(f"\n📊 Progress Update (Day {days_simulated})")
                print(f"   Current Date: {current_date}")
                print(f"   Total Games Played: {games_played_total}")
                print(f"   Current Phase: {day_result['current_phase']}")

            # Check for phase transitions
            if day_result['phase_transitions']:
                if self.verbose_logging:
                    print(f"\n🔄 Phase transition detected - season simulation complete")
                break

            # Check if phase changed
            current_phase = self.calendar.get_current_phase()
            if current_phase != initial_phase:
                if self.verbose_logging:
                    print(f"\n🔄 Phase changed from {initial_phase.value} to {current_phase.value}")
                break

        final_date = self.calendar.get_current_date()
        final_phase = self.calendar.get_current_phase()
        final_standings = self.get_current_standings()

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON SIMULATION COMPLETE'.center(80)}")
            print(f"{'='*80}")
            print(f"Start Date: {start_date}")
            print(f"End Date: {final_date}")
            print(f"Total Days Simulated: {days_simulated}")
            print(f"Total Games Played: {games_played_total}")
            print(f"Final Phase: {final_phase.value}")
            print(f"{'='*80}")

        return {
            "total_games": games_played_total,
            "total_days": days_simulated,
            "final_date": str(final_date),
            "final_phase": final_phase.value,
            "final_standings": final_standings,
            "success": True
        }

    def get_current_standings(self) -> Dict[str, Any]:
        """
        Get current standings from database.

        Returns:
            Dictionary with standings organized by division and conference:
            {
                "divisions": {
                    "AFC East": [...],
                    "NFC North": [...],
                    ...
                },
                "conferences": {
                    "AFC": [...],
                    "NFC": [...]
                }
            }
        """
        try:
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data:
                self.logger.warning(f"No standings found for {self.dynasty_id}, season {self.season_year}")
                return {"divisions": {}, "conferences": {}}

            return standings_data

        except Exception as e:
            self.logger.error(f"Error retrieving standings: {e}")
            return {"divisions": {}, "conferences": {}}

    def get_playoff_seeding(self) -> Dict[str, Any]:
        """
        Get current playoff seeding based on standings.

        Returns:
            Dictionary with playoff seeding for both conferences:
            {
                "season": int,
                "week": int,
                "afc": {"seeds": [...], "division_winners": [...], "wildcards": [...]},
                "nfc": {"seeds": [...], "division_winners": [...], "wildcards": [...]},
                "calculation_date": str
            }
        """
        try:
            # Get current standings from database
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data:
                self.logger.warning(f"No standings found for playoff seeding")
                return {}

            # Convert to format expected by PlayoffSeeder
            from playoff_system import PlayoffSeeder

            # DatabaseAPI returns standings organized by division/conference
            # Each team_data has: {'team_id': int, 'standing': EnhancedTeamStanding}
            # Need to flatten to dict[team_id, EnhancedTeamStanding]
            standings_dict = {}
            for division_name, teams in standings_data.get('divisions', {}).items():
                for team_data in teams:
                    team_id = team_data['team_id']
                    # Use the EnhancedTeamStanding object directly from database
                    standings_dict[team_id] = team_data['standing']

            # Calculate playoff seeding
            seeder = PlayoffSeeder()
            seeding = seeder.calculate_seeding(standings_dict, self.season_year, self.current_week)

            return seeding.to_dict()

        except Exception as e:
            self.logger.error(f"Error calculating playoff seeding: {e}")
            return {}

    def get_upcoming_games(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get games scheduled in the next N days.

        Args:
            days: Number of days ahead to look

        Returns:
            List of game dictionaries with matchup information
        """
        current_date = self.calendar.get_current_date()

        # Convert Date object to string format for DatabaseAPI
        start_date_str = f"{current_date.year:04d}-{current_date.month:02d}-{current_date.day:02d}"

        # Use centralized DatabaseAPI method
        return self.database_api.get_upcoming_games(start_date_str, days)

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get comprehensive current state of the season.

        Returns:
            Dictionary with current season state:
            {
                "current_date": str,
                "week_number": int,
                "games_played": int,
                "phase": str,
                "days_simulated": int,
                "phase_info": Dict
            }
        """
        current_date = self.calendar.get_current_date()
        phase = self.calendar.get_current_phase()
        phase_info = self.calendar.get_phase_info()

        return {
            "current_date": str(current_date),
            "week_number": self.current_week,
            "games_played": self.total_games_played,
            "phase": phase.value,
            "days_simulated": self.total_days_simulated,
            "phase_info": phase_info
        }

    def _initialize_schedule(self):
        """
        Generate or load schedule for the season.

        Creates a complete 272-game NFL season schedule using
        RandomScheduleGenerator and stores it in the event database.
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"INITIALIZING SEASON SCHEDULE")
            print(f"{'='*80}")

        # Check if schedule already exists for this dynasty
        # Use dynasty-filtered query to prevent cross-dynasty data contamination
        existing_games = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # Filter for regular season games only (exclude playoff games)
        regular_season_games = [
            e for e in existing_games
            if not e.get('event_id', '').startswith('playoff_')
            and not e.get('event_id', '').startswith('preseason_')
        ]

        if regular_season_games:
            if self.verbose_logging:
                print(f"✅ Found existing schedule: {len(regular_season_games)} games")
                print(f"{'='*80}")
            return

        # Generate new schedule
        if self.verbose_logging:
            print(f"Generating new schedule for {self.season_year} season...")

        try:
            # Get season start date from calendar (convert Date to datetime)
            season_start_date = self.calendar.get_current_date()
            season_start_datetime = datetime(
                season_start_date.year,
                season_start_date.month,
                season_start_date.day,
                20, 0  # Default to 8:00 PM for Thursday night start
            )

            # Create schedule generator with event database
            generator = RandomScheduleGenerator(event_db=self.event_db, dynasty_id=self.dynasty_id)

            # Generate 272 games (17 weeks × 16 games per week)
            # The generator will automatically store games in the event database
            schedule_events = generator.generate_season(
                season_year=self.season_year,
                start_date=season_start_datetime
            )

            if self.verbose_logging:
                print(f"✅ Schedule generated: {len(schedule_events)} games")
                print(f"{'='*80}")

        except Exception as e:
            self.logger.error(f"Error initializing schedule: {e}")
            if self.verbose_logging:
                print(f"❌ Schedule generation failed: {e}")
            raise

    def reset_season(self, new_start_date: Optional[Date] = None):
        """
        Reset the season to a new starting point.

        Useful for testing or restarting a season.

        Args:
            new_start_date: New starting date (uses original if None)
        """
        if new_start_date:
            self.calendar.reset(new_start_date)

        self.total_games_played = 0
        self.total_days_simulated = 0
        self.current_week = 1

        if self.verbose_logging:
            print(f"\n✅ Season reset to {self.calendar.get_current_date()}")

    def __str__(self) -> str:
        """String representation"""
        return (f"SeasonController(season={self.season_year}, "
                f"date={self.calendar.get_current_date()}, "
                f"games={self.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"SeasonController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
