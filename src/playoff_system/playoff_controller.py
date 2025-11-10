"""
Playoff Controller

Core orchestration logic for playoff simulation.
Coordinates calendar advancement, playoff bracket generation, and game execution.

This controller is the central component for playoff simulation, managing the interaction between:
- CalendarComponent (date/time management)
- EventDatabaseAPI (event storage/retrieval)
- SimulationExecutor (game execution orchestration)
- PlayoffSeeder (playoff seeding calculation)
- PlayoffManager (bracket generation)
- PlayoffScheduler (GameEvent creation)
"""

import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

# Use try/except to handle both production and test imports
try:
    from src.calendar.calendar_component import CalendarComponent
    from src.calendar.simulation_executor import SimulationExecutor
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.calendar_component import CalendarComponent
    from src.calendar.simulation_executor import SimulationExecutor
    from src.calendar.date_models import Date

from events import EventDatabaseAPI
from playoff_system.playoff_seeder import PlayoffSeeder
from playoff_system.playoff_manager import PlayoffManager
from playoff_system.playoff_scheduler import PlayoffScheduler
from playoff_system.seeding_models import PlayoffSeeding
from playoff_system.playoff_state import PlayoffState
from playoff_system.bracket_persistence import BracketPersistence
from stores.standings_store import EnhancedTeamStanding
from shared.game_result import GameResult
from team_management.teams.team_loader import get_team_by_id


class PlayoffController:
    """
    Core orchestration logic for playoff simulation.

    Provides comprehensive playoff management including:
    - Daily and weekly simulation advancement
    - Automatic bracket generation and scheduling
    - Round-by-round progression with re-seeding
    - Bracket state inspection
    - Simulate-to-Super-Bowl capability

    Usage:
        # Create controller
        controller = PlayoffController(
            database_path="playoff_2024.db",
            dynasty_id="my_dynasty",
            season_year=2024
        )

        # Advance by day
        result = controller.advance_day()

        # Advance by week
        weekly_result = controller.advance_week()

        # Advance until round completes
        round_result = controller.advance_to_next_round()

        # Simulate to Super Bowl
        summary = controller.simulate_to_super_bowl()

        # Check bracket state
        bracket = controller.get_current_bracket()
    """

    # Playoff round progression
    ROUND_ORDER = ['wild_card', 'divisional', 'conference', 'super_bowl']

    # NFL Playoff scheduling (dates relative to Wild Card start)
    WILD_CARD_OFFSET = 0      # Wild Card starts on Day 0
    DIVISIONAL_OFFSET = 7     # Divisional starts 7 days after Wild Card
    CONFERENCE_OFFSET = 14    # Conference starts 14 days after Wild Card
    SUPER_BOWL_OFFSET = 28    # Super Bowl starts 28 days after Wild Card

    def __init__(
        self,
        database_path: str,
        dynasty_id: str = "default",
        season_year: int = 2024,
        wild_card_start_date: Optional[Date] = None,
        initial_seeding: Optional[PlayoffSeeding] = None,
        enable_persistence: bool = True,
        verbose_logging: bool = True,
        phase_state: Optional['PhaseState'] = None,
        fast_mode: bool = False
    ):
        """
        Initialize playoff controller.

        Args:
            database_path: Path to SQLite database for event and game storage
            dynasty_id: Dynasty context for data isolation
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            wild_card_start_date: Starting date for Wild Card round (defaults to Jan 11, 2025)
            initial_seeding: Playoff seeding from regular season standings (if None, generates random seeding)
            enable_persistence: Whether to persist game results to database
            verbose_logging: Whether to print detailed progress messages
            phase_state: Shared PhaseState object for cross-phase state management (optional)
            fast_mode: Skip actual simulations, generate fake results for ultra-fast testing
        """
        self.database_path = database_path
        self.season_year = season_year
        self.dynasty_id = dynasty_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging
        self.fast_mode = fast_mode

        self.logger = logging.getLogger(self.__class__.__name__)

        # DIAGNOSTIC: Log playoff controller initialization with season info
        if verbose_logging:
            print(f"[PLAYOFF_CONTROLLER] Initializing with season_year={season_year}, dynasty_id='{dynasty_id}'")

        # Default Wild Card start date (second Saturday of January)
        if wild_card_start_date is None:
            wild_card_start_date = Date(2025, 1, 11)

        self.wild_card_start_date = wild_card_start_date

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Ensure dynasty exists in database (auto-create if needed)
        from database.connection import DatabaseConnection
        from database.api import DatabaseAPI
        db_conn = DatabaseConnection(database_path)
        db_conn.ensure_dynasty_exists(dynasty_id)

        # Initialize DatabaseAPI for clean data access
        self.database_api = DatabaseAPI(database_path)

        # Initialize core components
        self.calendar = CalendarComponent(
            start_date=wild_card_start_date,
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
            phase_state=phase_state,
            fast_mode=fast_mode
        )

        # Playoff-specific components
        self.playoff_seeder = PlayoffSeeder()
        self.playoff_manager = PlayoffManager()
        self.playoff_scheduler = PlayoffScheduler(
            event_db_api=self.event_db,
            playoff_manager=self.playoff_manager
        )

        # NEW: Centralized state management
        self.state = PlayoffState()
        self.persistence = BracketPersistence(self.event_db)

        # Legacy field aliases for backward compatibility (will be removed in Phase 4)
        # These allow existing code to work while we migrate
        self.completed_games = self.state.completed_games
        self.brackets = self.state.brackets

        # Legacy direct property aliases (these properties exist directly on PlayoffState)
        # Access via self.state.property_name, but we provide direct aliases for compatibility
        self.current_round = self.state.current_round
        self.original_seeding = self.state.original_seeding
        self.total_games_played = self.state.total_games_played
        self.total_days_simulated = self.state.total_days_simulated

        # Initialize playoff bracket with provided seeding or random seeding
        self._initialize_playoff_bracket(initial_seeding)

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'PLAYOFF CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {season_year}")
            print(f"Wild Card Start: {wild_card_start_date}")
            print(f"Dynasty: {dynasty_id}")
            print(f"Database: {database_path}")
            print(f"Persistence: {'ENABLED' if enable_persistence else 'DISABLED'}")
            print(f"{'='*80}")

    def advance_day(self) -> Dict[str, Any]:
        """
        Simulate games on current date, then advance calendar by 1 day.

        Returns:
            Dictionary with simulation results:
            {
                "date": str,
                "games_played": int,
                "results": List[Dict],
                "current_round": str,
                "round_complete": bool,
                "success": bool,
                "errors": List[str]
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"ADVANCING DAY - {self.state.current_round.upper()} ROUND")
            print(f"{'='*80}")

        # Get current date BEFORE advancing
        current_date = self.calendar.get_current_date()

        if self.verbose_logging:
            print(f"Current Date: {current_date}")
            print(f"Total Days Simulated: {self.state.total_days_simulated + 1}")

        # Simulate all games scheduled for TODAY (before advancing)
        simulation_result = self.simulation_executor.simulate_day(current_date)

        if self.verbose_logging:
            print(f"\n[DEBUG] simulation_result keys: {list(simulation_result.keys())}")
            print(f"[DEBUG] simulation_result content: {simulation_result}")

        # NOW advance calendar by 1 day for next call
        advance_result = self.calendar.advance(1)

        # Update statistics
        games_played = len([g for g in simulation_result.get('games_played', []) if g.get('success', False)])

        if self.verbose_logging:
            print(f"[DEBUG] games_played count (from 'games_played' key): {games_played}")
            print(f"[DEBUG] Raw games list length: {len(simulation_result.get('games_played', []))}")

        # Update round transition tracking (results already in database)
        # No need to track in-memory - database is single source of truth
        if games_played > 0:
            if self.verbose_logging:
                print(f"\n[DEBUG] Processing {games_played} games for round tracking...")

            for i, game in enumerate(simulation_result.get('games_played', [])):
                if self.verbose_logging:
                    print(f"[DEBUG] Game {i+1}: event_id={game.get('event_id')}, success={game.get('success')}")

                if game.get('success', False):
                    # Detect round from game_id for display purposes only
                    game_id = game.get('game_id', game.get('event_id', ''))
                    game_round = self._detect_game_round(game_id)

                    if not game_round or game_round not in self.ROUND_ORDER:
                        self.logger.warning(f"Could not detect round for game: {game_id}")
                        continue

                    # Update current_round for UI display (not used for logic)
                    if game_round != self.state.current_round:
                        if self.verbose_logging:
                            print(f"[PLAYOFF] Round transition: {self.state.current_round} → {game_round}")
                        self.state.current_round = game_round
                else:
                    if self.verbose_logging:
                        print(f"[DEBUG]   ⚠️  Game marked as unsuccessful, not tracking")

        # Update counters in state
        self.state.total_days_simulated += 1
        self.state.total_games_played += games_played  # Track total games from database

        # Check if current round is complete
        round_complete = self._is_round_complete(self.state.current_round)

        # Schedule next round if current round just completed
        if round_complete and self.state.current_round != 'super_bowl':
            if self.verbose_logging:
                print(f"\n[PLAYOFF] Round {self.state.current_round} complete! Scheduling next round...")

            try:
                self._schedule_next_round()
            except Exception as e:
                from src.playoff_system.playoff_exceptions import PlayoffSchedulingException
                raise PlayoffSchedulingException(
                    message=f"Failed to schedule next round after {self.state.current_round}",
                    round_name=self.state.current_round,
                    operation="auto_advance_to_next_round",
                    context_dict={
                        "dynasty_id": self.dynasty_id,
                        "season": self.season,
                        "completed_round": self.state.current_round
                    }
                ) from e

        if self.verbose_logging and games_played > 0:
            print(f"\n✅ Day complete: {games_played} game(s) played")
            # Query database for accurate round progress
            completed_count = len(self._get_completed_games_from_database(self.state.current_round))
            print(f"Round progress: {completed_count}/{self._get_expected_game_count(self.state.current_round)} games")

        return {
            "date": str(current_date),
            "games_played": games_played,
            "results": simulation_result.get('games_played', []),
            "current_round": self.state.current_round,
            "round_complete": round_complete,
            "success": simulation_result.get('success', True),
            "errors": simulation_result.get('errors', [])
        }

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance calendar by 7 days, simulating all scheduled games.

        Returns:
            Dictionary with weekly summary:
            {
                "start_date": str,
                "end_date": str,
                "total_games_played": int,
                "daily_results": List[Dict],
                "current_round": str,
                "rounds_completed": List[str],
                "success": bool
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"ADVANCING WEEK - {self.state.current_round.upper()} ROUND")
            print(f"{'='*80}")

        start_date = self.calendar.get_current_date()
        daily_results = []
        total_games_this_week = 0
        rounds_completed = []
        rounds_completed_this_week = set()  # FIX #1: Track already-completed rounds to prevent duplicates

        # Simulate 7 days
        for day in range(7):
            day_result = self.advance_day()
            daily_results.append(day_result)
            total_games_this_week += day_result['games_played']

            # Check if round completed and schedule next round
            if day_result['round_complete']:
                current_round_name = self.state.current_round

                # FIX #1: Prevent duplicate round completion processing
                if current_round_name in rounds_completed_this_week:
                    if self.verbose_logging:
                        print(f"[DEBUG] Day {day+1}: Round {current_round_name} already processed this week, skipping")
                    continue

                # Mark this round as processed for this week
                rounds_completed_this_week.add(current_round_name)
                if self.verbose_logging:
                    print(f"\n[DEBUG] Day {day+1}: Round {self.state.current_round} is complete!")
                    print(f"[DEBUG] Games played today: {day_result['games_played']}")

                # DATABASE VERIFICATION: Confirm playoff events exist after round completion
                playoff_event_count = self.database_api.count_playoff_events(
                    dynasty_id=self.dynasty_id,
                    season_year=self.season_year
                )

                print(f"[PLAYOFF_VERIFICATION] Round '{self.state.current_round}' complete!")
                print(f"[PLAYOFF_VERIFICATION] Database check: {playoff_event_count} playoff events exist for dynasty '{self.dynasty_id}'")
                print(f"[PLAYOFF_VERIFICATION] Expected: {self.state.total_games_played} completed games")
                if playoff_event_count < self.state.total_games_played:
                    print(f"[PLAYOFF_VERIFICATION] ⚠️  WARNING: Event count mismatch! Some playoff events may not have been saved!")

                if self.state.current_round != 'super_bowl':
                    if self.verbose_logging:
                        print(f"[DEBUG] Calling _schedule_next_round() for {self.state.current_round}")
                    rounds_completed.append(self.state.current_round)
                    self._schedule_next_round()
                    if self.verbose_logging:
                        print(f"[DEBUG] _schedule_next_round() returned")
                else:
                    if self.verbose_logging:
                        print(f"[DEBUG] Not scheduling next round (already at Super Bowl)")

        end_date = self.calendar.get_current_date()

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"WEEK COMPLETE")
            print(f"{'='*80}")
            print(f"Date Range: {start_date} to {end_date}")
            print(f"Games Played: {total_games_this_week}")
            print(f"Total Playoff Games: {self.state.total_games_played}")
            if rounds_completed:
                print(f"Rounds Completed: {', '.join(r.title() for r in rounds_completed)}")
            print(f"{'='*80}")

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_games_played": total_games_this_week,
            "daily_results": daily_results,
            "current_round": self.state.current_round,
            "rounds_completed": rounds_completed,
            "success": all(d.get('success', False) for d in daily_results)
        }

    def advance_to_next_round(self) -> Dict[str, Any]:
        """
        Advance calendar until active round completes, then schedule next round.

        Continues day-by-day simulation until all games in the active round
        are finished. Automatically schedules the next round if applicable.

        Uses get_active_round() to determine which round to simulate, ensuring
        correct behavior even when self.current_round hasn't transitioned yet.

        Returns:
            Dictionary with round completion summary:
            {
                "completed_round": str,
                "games_played": int,
                "days_simulated": int,
                "next_round": str or None,
                "next_round_scheduled": bool,
                "success": bool
            }
        """
        # Use active round instead of current_round for accurate tracking
        active_round = self.get_active_round()

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'ADVANCING TO NEXT ROUND'.center(80)}")
            print(f"{'='*80}")
            print(f"Active Round: {active_round.title()}")

        # Track which round we're about to complete
        round_to_complete = active_round
        initial_games = self.state.total_games_played
        initial_days = self.state.total_days_simulated

        # Advance until THIS SPECIFIC round is complete (safety limit: 30 days)
        max_days = 30
        days_simulated = 0

        while not self._is_round_complete(round_to_complete) and days_simulated < max_days:
            self.advance_day()
            days_simulated += 1

        games_in_round = self.state.total_games_played - initial_games

        # The round that was just completed
        completed_round = round_to_complete

        # Get completed games for the round that was just completed
        round_results = self.state.completed_games[completed_round].copy()

        # Schedule next round if not Super Bowl
        next_round_scheduled = False
        next_round = None

        if completed_round != 'super_bowl':
            self._schedule_next_round()
            # Note: current_round is still 'completed_round' after this
            # It will only change when we start simulating the next round's games
            next_round = self._get_next_round_name(completed_round)
            next_round_scheduled = True

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'ROUND COMPLETE'.center(80)}")
            print(f"{'='*80}")
            print(f"Completed Round: {completed_round.title()}")
            print(f"Games Played: {games_in_round}")
            print(f"Days Simulated: {days_simulated}")
            if next_round_scheduled:
                print(f"Next Round Scheduled: {next_round.title()}")
                print(f"  ⚠️  Call 'Complete Current Round' again to simulate {next_round.title()}")
            print(f"{'='*80}")

        return {
            "completed_round": completed_round,
            "round_name": completed_round,  # For display compatibility
            "games_played": games_in_round,
            "days_simulated": days_simulated,
            "results": round_results,
            "next_round": next_round,
            "next_round_scheduled": next_round_scheduled,
            "success": True
        }

    def simulate_to_super_bowl(self) -> Dict[str, Any]:
        """
        Simulate all remaining playoff rounds until Super Bowl completes.

        Advances day-by-day through all playoff rounds, scheduling each
        subsequent round as the previous one completes.

        Returns:
            Dictionary with complete playoff summary:
            {
                "total_games": int,
                "total_days": int,
                "rounds_completed": List[str],
                "super_bowl_winner": int (team_id),
                "final_date": str,
                "success": bool
            }
        """
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SIMULATING TO SUPER BOWL'.center(80)}")
            print(f"{'='*80}")

        start_date = self.calendar.get_current_date()
        initial_games = self.state.total_games_played
        rounds_completed = []

        # Continue until Super Bowl is complete (safety limit: 60 days)
        max_days = 60
        days_simulated = 0

        while days_simulated < max_days:
            # Advance day
            day_result = self.advance_day()
            days_simulated += 1

            # Check if round completed
            if day_result['round_complete']:
                rounds_completed.append(self.state.current_round)

                # If Super Bowl just completed, we're done
                if self.state.current_round == 'super_bowl':
                    break

                # Otherwise, schedule next round
                self._schedule_next_round()

            # Display progress every 7 days
            if self.verbose_logging and days_simulated % 7 == 0:
                current_date = self.calendar.get_current_date()
                print(f"\n📊 Progress Update (Day {days_simulated})")
                print(f"   Current Date: {current_date}")
                print(f"   Current Round: {self.state.current_round.title()}")
                print(f"   Total Games Played: {self.state.total_games_played}")

        final_date = self.calendar.get_current_date()
        total_games = self.state.total_games_played - initial_games

        # Determine Super Bowl winner (database-first pattern for app restart compatibility)
        super_bowl_winner = None
        super_bowl_games = self._get_completed_games_from_database('super_bowl')
        if super_bowl_games:
            super_bowl_winner = super_bowl_games[0].get('winner_id')

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'PLAYOFF SIMULATION COMPLETE'.center(80)}")
            print(f"{'='*80}")
            print(f"Start Date: {start_date}")
            print(f"End Date: {final_date}")
            print(f"Total Days Simulated: {days_simulated}")
            print(f"Total Games Played: {total_games}")
            print(f"Rounds Completed: {', '.join(r.title() for r in rounds_completed)}")
            if super_bowl_winner:
                print(f"Super Bowl Champion: Team {super_bowl_winner}")
            print(f"{'='*80}")

        return {
            "total_games": total_games,
            "total_days": days_simulated,
            "rounds_completed": rounds_completed,
            "super_bowl_winner": super_bowl_winner,
            "final_date": str(final_date),
            "success": True
        }

    def get_current_bracket(self) -> Dict[str, Any]:
        """
        Get current playoff bracket state.

        Returns:
            Dictionary with bracket information:
            {
                "current_round": str,
                "wild_card": PlayoffBracket or None,
                "divisional": PlayoffBracket or None,
                "conference": PlayoffBracket or None,
                "super_bowl": PlayoffBracket or None,
                "original_seeding": PlayoffSeeding
            }
        """
        bracket = {
            "current_round": self.state.current_round,
            "original_seeding": self.state.original_seeding,
            "wild_card": self.state.brackets['wild_card'],
            "divisional": self.state.brackets['divisional'],
            "conference": self.state.brackets['conference'],
            "super_bowl": self.state.brackets['super_bowl']
        }

        return bracket

    def get_round_games(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific playoff round FROM DATABASE.

        Single source of truth: Queries database for ALL games (scheduled AND completed).
        This method is used by the UI to display the complete bracket structure.

        Args:
            round_name: 'wild_card', 'divisional', 'conference', or 'super_bowl'

        Returns:
            List of game dictionaries with matchup and result information:
            - Completed games: Include scores, winner_id, status='completed'
            - Scheduled games: Include teams, status='scheduled', no scores
        """
        if round_name not in self.ROUND_ORDER:
            raise ValueError(f"Invalid round name: {round_name}")

        return self._get_all_playoff_games_from_database(round_name)

    def get_current_state(self) -> Dict[str, Any]:
        """
        Get comprehensive current state of the playoffs.

        Returns:
            Dictionary with current playoff state:
            {
                "current_date": str,
                "current_round": str,
                "games_played": int,
                "days_simulated": int,
                "round_progress": {...}
            }
        """
        current_date = self.calendar.get_current_date()

        # Query database for round progress (single source of truth)
        round_progress = {
            round_name: {
                "games_completed": len(self._get_completed_games_from_database(round_name)),
                "games_expected": self._get_expected_game_count(round_name),
                "complete": self._is_round_complete(round_name)
            }
            for round_name in self.ROUND_ORDER
        }

        return {
            "current_date": str(current_date),
            "current_round": self.state.current_round,
            "active_round": self.get_active_round(),
            "games_played": self.state.total_games_played,
            "days_simulated": self.state.total_days_simulated,
            "round_progress": round_progress
        }

    def get_active_round(self) -> str:
        """
        Get the current "active" playoff round based on DATABASE completion status.

        Single source of truth: Queries database to determine which rounds are complete.
        This ensures correct behavior even after app restart.

        Returns:
            The name of the first incomplete round, or 'complete' if all rounds done
        """
        # Check each round in order - first incomplete round is active
        for round_name in self.ROUND_ORDER:
            completed_games = self._get_completed_games_from_database(round_name)
            expected = self._get_expected_game_count(round_name)

            if len(completed_games) < expected:
                # This round is incomplete - it's the active round
                return round_name

        # All rounds complete
        return 'complete'

    def get_super_bowl_date(self) -> Date:
        """
        Get the date of the Super Bowl game.

        Required for offseason scheduling - offseason events are calculated
        relative to the Super Bowl date (e.g., Free Agency = SB + 31 days).

        Returns:
            Date: Date when Super Bowl was/will be played

        Raises:
            RuntimeError: If Super Bowl game not found or not scheduled
        """
        # Get Super Bowl games from bracket
        super_bowl_games = self.get_round_games("super_bowl")

        if not super_bowl_games:
            raise RuntimeError(
                "Super Bowl game not found. Playoffs may not have advanced to Super Bowl round. "
                f"Current active round: {self.get_active_round()}"
            )

        # Get first (and only) Super Bowl game
        sb_game = super_bowl_games[0]

        # Extract date from game parameters
        # Game structure: {'game_id': ..., 'parameters': {'game_date': 'YYYY-MM-DD', ...}, ...}
        game_date_str = sb_game.get('game_date')
        if not game_date_str and 'parameters' in sb_game:
            game_date_str = sb_game['parameters'].get('game_date')

        if not game_date_str:
            raise RuntimeError(
                f"Super Bowl game exists but has no game_date. Game data: {sb_game}"
            )

        # Parse date string to Date object
        # Handle both "YYYY-MM-DD" and "YYYY-MM-DDTHH:MM:SS" formats
        if 'T' in game_date_str:
            game_date_str = game_date_str.split('T')[0]

        return Date.from_string(game_date_str)

    def get_super_bowl_winner(self) -> Optional[int]:
        """
        Get Super Bowl winner team ID.

        Uses database as single source of truth (works after app restart).
        Required for offseason scheduling - determines which team won the championship.

        Returns:
            int: Team ID of Super Bowl champion
            None: If Super Bowl not yet played

        Raises:
            PlayoffStateException: If Super Bowl marked complete but no data found
            PlayoffStateException: If Super Bowl data exists but winner_id is None
        """
        from src.playoff_system.playoff_exceptions import PlayoffStateException

        # Check if Super Bowl round is complete
        if not self._is_round_complete('super_bowl'):
            return None

        # Query database for completed Super Bowl games
        super_bowl_games = self._get_completed_games_from_database('super_bowl')

        # Data corruption check: Round complete but no game data
        if not super_bowl_games:
            raise PlayoffStateException(
                message="Super Bowl round marked complete but no game data found in database",
                current_round='super_bowl',
                context_dict={
                    'dynasty_id': self.dynasty_id,
                    'season_year': self.season_year,
                    'operation': 'get_super_bowl_winner'
                }
            )

        # Validate exactly one Super Bowl game
        if len(super_bowl_games) > 1:
            raise PlayoffStateException(
                message=f"Expected exactly 1 Super Bowl, found {len(super_bowl_games)}",
                current_round='super_bowl',
                context_dict={
                    'dynasty_id': self.dynasty_id,
                    'season_year': self.season_year,
                    'game_count': len(super_bowl_games),
                    'operation': 'get_super_bowl_winner'
                }
            )

        # Extract winner
        sb_game = super_bowl_games[0]
        winner_id = sb_game.get('winner_id')

        # Data corruption check: Game exists but no winner
        if winner_id is None:
            raise PlayoffStateException(
                message="Super Bowl game exists but winner_id is None (data corruption)",
                current_round='super_bowl',
                context_dict={
                    'dynasty_id': self.dynasty_id,
                    'season_year': self.season_year,
                    'game_id': sb_game.get('game_id'),
                    'home_team': sb_game.get('home_team_id'),
                    'away_team': sb_game.get('away_team_id'),
                    'home_score': sb_game.get('home_score'),
                    'away_score': sb_game.get('away_score'),
                    'operation': 'get_super_bowl_winner'
                }
            )

        return winner_id

    def is_super_bowl_complete(self) -> bool:
        """
        Check if Super Bowl has been played (not just scheduled).

        Returns:
            True if Super Bowl game has been simulated with results
            False if Super Bowl not played or only scheduled
        """
        return self._is_round_complete('super_bowl')

    def is_playoffs_started(self) -> bool:
        """
        Check if playoffs have started.

        Returns:
            True if any playoff games have been scheduled
            False if playoffs not yet initialized
        """
        # Check if bracket has been created
        if not self.state.brackets or not self.state.brackets.get('wild_card'):
            return False

        # Verify at least one playoff game exists in database
        wild_card_games = self._get_all_games_from_database('wild_card')
        return len(wild_card_games) > 0

    # ========== Private Helper Methods ==========

    def _initialize_playoff_bracket(self, initial_seeding: Optional[PlayoffSeeding] = None):
        """
        Generate initial playoff bracket with provided or random seeding.

        Creates playoff seeding and schedules the Wild Card round.
        Checks for existing playoff events for this dynasty/season to avoid duplicates.

        Args:
            initial_seeding: Optional playoff seeding from regular season standings.
                           If None, generates random seeding for standalone demos.
        """
        seeding_type = "REAL SEEDING" if initial_seeding else "RANDOM SEEDING"

        # LOGGING: Track every initialization call
        print(f"\n[PLAYOFF_SCHEDULING] ===== _initialize_playoff_bracket() CALLED =====")
        print(f"[PLAYOFF_SCHEDULING] Dynasty: {self.dynasty_id}")
        print(f"[PLAYOFF_SCHEDULING] Season: {self.season_year}")
        print(f"[PLAYOFF_SCHEDULING] Seeding Type: {seeding_type}")
        print(f"[PLAYOFF_SCHEDULING] Database: {self.database_path}")

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"INITIALIZING PLAYOFF BRACKET WITH {seeding_type}")
            print(f"{'='*80}")

        # Check if Wild Card round already scheduled for this dynasty/season
        # Use dynasty-filtered query to prevent cross-dynasty data contamination
        existing_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # Filter for playoff games (defensive NULL check)
        playoff_game_prefix = f"playoff_{self.season_year}_"
        dynasty_playoff_events = [
            e for e in existing_events
            if e.get('game_id') and e.get('game_id').startswith(playoff_game_prefix)
        ]

        if dynasty_playoff_events:
            if self.verbose_logging:
                print(f"\n✅ Found existing playoff bracket for dynasty '{self.dynasty_id}': {len(dynasty_playoff_events)} games")
                print(f"   Game ID pattern: {playoff_game_prefix}*")
                print(f"   Reusing existing playoff schedule")

            # Determine seeding to use (real from standings or random for testing)
            seeding_to_use = initial_seeding if initial_seeding else self._generate_random_seeding()

            # Reconstruct bracket state WITH seeding (prevents NoneType crash)
            self._reconstruct_bracket_from_events(dynasty_playoff_events, seeding_to_use)

            # Defensive: Ensure seeding is set (should already be set by reconstruction)
            if self.state.original_seeding is None:
                self.state.original_seeding = seeding_to_use

            # Re-schedule brackets to populate self.brackets dict
            # This ensures UI has bracket structure (matchups) in addition to results
            self._reschedule_brackets_from_completed_games()

            if self.verbose_logging:
                print(f"{'='*80}")
            return

        # No existing playoff events for this dynasty - generate new bracket
        # Use provided seeding if available, otherwise generate random seeding
        if initial_seeding:
            self.state.original_seeding = initial_seeding
        else:
            self.state.original_seeding = self._generate_random_seeding()

        if self.verbose_logging:
            print(f"\nAFC Seeding:")
            for seed in self.state.original_seeding.afc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

            print(f"\nNFC Seeding:")
            for seed in self.state.original_seeding.nfc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

        # Schedule Wild Card round
        try:
            result = self.playoff_scheduler.schedule_wild_card_round(
                seeding=self.state.original_seeding,
                start_date=self.wild_card_start_date,
                season=self.season_year,
                dynasty_id=self.dynasty_id
            )

            # Store the wild card bracket
            self.state.brackets['wild_card'] = result['bracket']

            if self.verbose_logging:
                print(f"\n✅ Wild Card round scheduled: {result['games_scheduled']} games")
                print(f"{'='*80}")

        except Exception as e:
            self.logger.error(f"Error scheduling Wild Card round: {e}")
            if self.verbose_logging:
                print(f"❌ Wild Card scheduling failed: {e}")
            raise

    def _reconstruct_bracket_from_events(
        self,
        playoff_events: List[Dict[str, Any]],
        original_seeding: 'PlayoffSeeding'
    ):
        """
        Reconstruct playoff bracket state from existing game events in database.

        NOW DELEGATES TO: BracketPersistence.reconstruct_state()

        When the PlayoffController is reinitialized (e.g., after app restart),
        this method rebuilds the in-memory bracket state by parsing completed
        playoff game events from the database.

        Args:
            playoff_events: List of playoff game events from database
            original_seeding: Playoff seeding to restore (prevents NoneType crash)
        """
        # Delegate to persistence layer WITH seeding
        self.state = self.persistence.reconstruct_state(
            playoff_events=playoff_events,
            detect_round_func=self._detect_game_round,
            original_seeding=original_seeding
        )

        # Verbose logging (optional)
        if self.verbose_logging:
            print(f"✅ Bracket reconstruction complete:")
            for round_name in self.ROUND_ORDER:
                count = len(self.state.completed_games[round_name])
                expected = self.state._get_expected_game_count(round_name)
                status = "COMPLETE" if count >= expected else f"{count}/{expected}"
                print(f"   {round_name.title()}: {status}")

    def _reschedule_brackets_from_completed_games(self):
        """
        Reconstruct playoff bracket OBJECTS from existing database events.

        **CRITICAL: This method does NOT create any database events!**

        This method is called after `_reconstruct_bracket_from_events()` to populate
        the `self.brackets` dict with bracket structure information. While reconstruction
        rebuilds `self.completed_games` (results), it doesn't populate `self.brackets`
        (matchup structure). This method leverages the deterministic nature of playoff
        brackets: same seeding always produces the same bracket structure.

        Strategy:
        1. Reconstruct Wild Card bracket OBJECT using playoff_manager (NO events created)
        2. For each subsequent round, check if games exist in completed_games
        3. If yes, generate bracket OBJECT using playoff_manager (NO events created)
        4. Store all bracket objects in self.brackets dict for UI consumption

        This approach:
        - Uses playoff_manager (generates objects) NOT playoff_scheduler (creates events)
        - Works with any partial bracket state (mid-playoffs reload)
        - Produces identical bracket structure to original (deterministic)
        - ZERO database writes - purely in-memory reconstruction
        """
        print(f"\n[DEBUG _reschedule_brackets] ===== METHOD CALLED =====")
        print(f"[DEBUG _reschedule_brackets] self.state.brackets BEFORE: {list(self.state.brackets.keys())}")
        for round_name in self.ROUND_ORDER:
            bracket = self.state.brackets.get(round_name)
            print(f"[DEBUG _reschedule_brackets]   {round_name}: {type(bracket).__name__ if bracket else 'None'}")
            if bracket and hasattr(bracket, 'games'):
                print(f"[DEBUG _reschedule_brackets]     -> has {len(bracket.games)} games")

        if self.verbose_logging:
            print(f"\n🔄 Reconstructing bracket structure from existing events...")
            print(f"   ⚠️  This should NOT create any new database events!")

        # Round date offsets (relative to Wild Card start)
        round_offsets = {
            'wild_card': self.WILD_CARD_OFFSET,
            'divisional': self.DIVISIONAL_OFFSET,
            'conference': self.CONFERENCE_OFFSET,
            'super_bowl': self.SUPER_BOWL_OFFSET
        }

        # 1. Always reconstruct Wild Card round bracket (WITHOUT creating events)
        # CRITICAL: Use playoff_manager NOT playoff_scheduler to avoid creating new events
        try:
            wc_start_date = self.wild_card_start_date.add_days(round_offsets['wild_card'])

            # Generate bracket structure WITHOUT creating database events
            wc_bracket = self.playoff_manager.generate_wild_card_bracket(
                seeding=self.state.original_seeding,
                start_date=wc_start_date,
                season=self.season_year
            )
            self.state.brackets['wild_card'] = wc_bracket

            print(f"[DEBUG _reschedule_brackets] Wild Card bracket created!")
            print(f"[DEBUG _reschedule_brackets]   Type: {type(wc_bracket).__name__}")
            print(f"[DEBUG _reschedule_brackets]   Has .games attribute: {hasattr(wc_bracket, 'games')}")
            if hasattr(wc_bracket, 'games'):
                print(f"[DEBUG _reschedule_brackets]   Number of games: {len(wc_bracket.games)}")

            if self.verbose_logging:
                print(f"   ✅ Wild Card bracket reconstructed (0 events created)")

        except Exception as e:
            self.logger.error(f"Error reconstructing Wild Card bracket: {e}")
            if self.verbose_logging:
                print(f"   ❌ Wild Card bracket reconstruction failed: {e}")

        # 2. Re-schedule subsequent rounds if they have games
        # Must process in order: divisional → conference → super_bowl
        for round_name in ['divisional', 'conference', 'super_bowl']:
            # Check if this round has any games (scheduled or completed) by querying DATABASE
            # FIX: Use database query instead of in-memory completed_games to detect scheduled games after app restart
            round_games_db = self._get_all_playoff_games_from_database(round_name)
            if len(round_games_db) == 0:
                # No games in this round yet, stop here
                if self.verbose_logging:
                    print(f"   ⏭️  {round_name.title()} round: No games found, skipping")
                break

            # This round has games, re-schedule its bracket
            try:
                # Get the previous round's completed games
                prev_round = self._get_previous_round_name(round_name)
                if not prev_round:
                    if self.verbose_logging:
                        print(f"   ⚠️  {round_name.title()}: Cannot determine previous round")
                    break

                # Check if previous round is complete by querying DATABASE
                # FIX: Use database query instead of in-memory completed_games to detect completed games after app restart
                prev_round_games_db = self._get_completed_games_from_database(prev_round)
                prev_round_complete = len(prev_round_games_db) >= self._get_expected_game_count(prev_round)
                if not prev_round_complete:
                    if self.verbose_logging:
                        print(f"   ⚠️  {round_name.title()}: Previous round ({prev_round}) not complete")
                    break

                # Convert previous round's games to GameResult objects
                # Use previously queried database games (prev_round_games_db from above)
                completed_results = self._convert_games_to_results(prev_round_games_db)

                # Calculate start date for this round
                start_date = self.wild_card_start_date.add_days(round_offsets[round_name])

                # Generate bracket structure WITHOUT creating database events
                # CRITICAL: Use playoff_manager NOT playoff_scheduler to avoid creating new events
                if round_name == 'divisional':
                    bracket = self.playoff_manager.generate_divisional_bracket(
                        wild_card_results=completed_results,
                        original_seeding=self.state.original_seeding,
                        start_date=start_date,
                        season=self.season_year
                    )
                elif round_name == 'conference':
                    bracket = self.playoff_manager.generate_conference_championship_bracket(
                        divisional_results=completed_results,
                        start_date=start_date,
                        season=self.season_year
                    )
                elif round_name == 'super_bowl':
                    bracket = self.playoff_manager.generate_super_bowl_bracket(
                        conference_results=completed_results,
                        start_date=start_date,
                        season=self.season_year
                    )

                # Store bracket structure (no events created)
                self.state.brackets[round_name] = bracket

                print(f"[DEBUG _reschedule_brackets] {round_name.title()} bracket created!")
                print(f"[DEBUG _reschedule_brackets]   Type: {type(bracket).__name__}")
                print(f"[DEBUG _reschedule_brackets]   Has .games attribute: {hasattr(bracket, 'games')}")
                if hasattr(bracket, 'games'):
                    print(f"[DEBUG _reschedule_brackets]   Number of games: {len(bracket.games)}")

                if self.verbose_logging:
                    print(f"   ✅ {round_name.title()} bracket reconstructed (0 events created)")

            except Exception as e:
                self.logger.error(f"Error reconstructing {round_name} bracket: {e}")
                if self.verbose_logging:
                    print(f"   ❌ {round_name.title()} bracket reconstruction failed: {e}")
                # Stop processing subsequent rounds on error
                break

        print(f"\n[DEBUG _reschedule_brackets] ===== FINAL STATE =====")
        print(f"[DEBUG _reschedule_brackets] self.state.brackets AFTER: {list(self.state.brackets.keys())}")
        for round_name in self.ROUND_ORDER:
            bracket = self.state.brackets.get(round_name)
            print(f"[DEBUG _reschedule_brackets]   {round_name}: {type(bracket).__name__ if bracket else 'None'}")
            if bracket and hasattr(bracket, 'games'):
                print(f"[DEBUG _reschedule_brackets]     -> has {len(bracket.games)} games")

        if self.verbose_logging:
            print(f"✅ Bracket reconstruction complete - UI ready (0 new events created)")

    def _get_previous_round_name(self, current_round: str) -> Optional[str]:
        """
        Get the name of the previous playoff round.

        Args:
            current_round: Current round name

        Returns:
            Previous round name or None if already at Wild Card
        """
        try:
            current_index = self.ROUND_ORDER.index(current_round)
            if current_index > 0:
                return self.ROUND_ORDER[current_index - 1]
        except (ValueError, IndexError):
            pass
        return None

    def _generate_random_seeding(self) -> PlayoffSeeding:
        """
        Generate random playoff seeding for testing.

        Creates 7 random teams per conference with random records.

        Returns:
            PlayoffSeeding with random teams and records
        """
        from playoff_system.seeding_models import PlayoffSeed, ConferenceSeeding

        # AFC teams: 1-16
        afc_teams = list(range(1, 17))
        random.shuffle(afc_teams)
        afc_playoff_teams = afc_teams[:7]

        # NFC teams: 17-32
        nfc_teams = list(range(17, 33))
        random.shuffle(nfc_teams)
        nfc_playoff_teams = nfc_teams[:7]

        # Generate random records (better records for higher seeds)
        def create_seed(team_id: int, seed_num: int, conference: str) -> PlayoffSeed:
            # Higher seeds get better records
            wins = 14 - seed_num + random.randint(0, 2)
            losses = 17 - wins
            win_pct = wins / 17.0

            # Determine division (simplified)
            if conference == 'AFC':
                divisions = ['AFC East', 'AFC North', 'AFC South', 'AFC West']
            else:
                divisions = ['NFC East', 'NFC North', 'NFC South', 'NFC West']

            division = divisions[(seed_num - 1) % 4]

            return PlayoffSeed(
                seed=seed_num,
                team_id=team_id,
                wins=wins,
                losses=losses,
                ties=0,
                win_percentage=win_pct,
                division_winner=(seed_num <= 4),
                division_name=division,
                conference=conference,
                points_for=wins * 25,
                points_against=losses * 20,
                point_differential=wins * 25 - losses * 20,
                division_record="4-2",
                conference_record=f"{wins-3}-{losses-3}"
            )

        # Create AFC seeding
        afc_seeds = [
            create_seed(team_id, seed_num, 'AFC')
            for seed_num, team_id in enumerate(afc_playoff_teams, start=1)
        ]

        afc_seeding = ConferenceSeeding(
            conference='AFC',
            seeds=afc_seeds,
            division_winners=afc_seeds[:4],
            wildcards=afc_seeds[4:],
            clinched_teams=[s.team_id for s in afc_seeds],
            eliminated_teams=[tid for tid in range(1, 17) if tid not in afc_playoff_teams]
        )

        # Create NFC seeding
        nfc_seeds = [
            create_seed(team_id, seed_num, 'NFC')
            for seed_num, team_id in enumerate(nfc_playoff_teams, start=1)
        ]

        nfc_seeding = ConferenceSeeding(
            conference='NFC',
            seeds=nfc_seeds,
            division_winners=nfc_seeds[:4],
            wildcards=nfc_seeds[4:],
            clinched_teams=[s.team_id for s in nfc_seeds],
            eliminated_teams=[tid for tid in range(17, 33) if tid not in nfc_playoff_teams]
        )

        return PlayoffSeeding(
            season=self.season_year,
            week=18,
            afc=afc_seeding,
            nfc=nfc_seeding,
            tiebreakers_applied=[],
            calculation_date=datetime.now().isoformat()
        )

    def _is_round_complete(self, round_name: str) -> bool:
        """
        Check if a specific round is complete by querying DATABASE.

        Single source of truth: Queries database for completed games with results.
        This ensures correct behavior even after app restart.

        Args:
            round_name: The playoff round to check

        Returns:
            True if all expected games for this round have been completed
        """
        completed_games = self._get_completed_games_from_database(round_name)
        expected = self._get_expected_game_count(round_name)
        return len(completed_games) >= expected

    def _is_active_round_complete(self) -> bool:
        """
        Check if the active round is complete.

        This uses get_active_round() to determine which round to check,
        ensuring correct behavior even when self.current_round hasn't
        transitioned yet.

        Returns:
            True if all expected games for active round are complete
        """
        active_round = self.get_active_round()
        return self._is_round_complete(active_round)

    def _get_expected_game_count(self, round_name: str) -> int:
        """
        Get expected number of games for a round.

        NOW DELEGATES TO: PlayoffState._get_expected_game_count()
        """
        return self.state._get_expected_game_count(round_name)

    def _get_completed_games_from_database(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Query database for completed playoff games with results for a specific round.

        FIX #2: This method directly queries the events table to find games that have
        been SIMULATED (have results), not just scheduled. This solves the issue where
        self.state.completed_games is empty after app reload because it only tracks
        in-memory simulated games.

        Args:
            round_name: Playoff round name ('wild_card', 'divisional', 'conference', 'super_bowl')

        Returns:
            List of completed game dictionaries with results, including:
            - event_id: Game identifier
            - game_id: Full game ID
            - away_team_id: Away team ID
            - home_team_id: Home team ID
            - away_score: Final away score
            - home_score: Final home score
            - winner_id: Winning team ID
            - success: True (only returns successful games)
        """
        import json

        # Query all playoff events for this dynasty/season/round
        all_playoff_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # Filter for this specific round
        round_prefix = f"playoff_{self.season_year}_{round_name}_"
        completed_games = []

        for event in all_playoff_events:
            game_id = event.get('game_id', '')

            # Check if this game belongs to the target round
            if not game_id.startswith(round_prefix):
                continue

            # Parse event data
            event_data = event.get('data', '{}')
            if isinstance(event_data, str):
                try:
                    event_data = json.loads(event_data)
                except json.JSONDecodeError:
                    continue

            # Check if game has results (was simulated)
            results = event_data.get('results')
            if not results:
                continue  # Skip scheduled but not simulated games

            # Extract game parameters and results
            parameters = event_data.get('parameters', {})
            away_team_id = parameters.get('away_team_id')
            home_team_id = parameters.get('home_team_id')
            away_score = results.get('away_score')
            home_score = results.get('home_score')

            # Validate required fields
            if away_team_id is None or home_team_id is None:
                continue
            if away_score is None or home_score is None:
                continue

            # Determine winner
            winner_id = home_team_id if home_score > away_score else away_team_id

            # Build completed game record
            completed_game = {
                'event_id': game_id,  # Use game_id as event_id
                'game_id': game_id,
                'away_team_id': away_team_id,
                'home_team_id': home_team_id,
                'away_score': away_score,
                'home_score': home_score,
                'winner_id': winner_id,
                'success': True
            }

            completed_games.append(completed_game)

        if self.verbose_logging and completed_games:
            print(f"[DATABASE_QUERY] Found {len(completed_games)} completed games for {round_name} round")

        return completed_games

    def _get_all_playoff_games_from_database(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Query database for ALL playoff games (scheduled AND completed) for a specific round.

        This method is designed for UI display purposes, returning both:
        - Scheduled games (not yet simulated, no results)
        - Completed games (simulated with results and scores)

        Unlike _get_completed_games_from_database(), this method does NOT filter out
        scheduled games, allowing the UI to display the full bracket structure including
        future matchups.

        Args:
            round_name: Playoff round name ('wild_card', 'divisional', 'conference', 'super_bowl')

        Returns:
            List of game dictionaries including:
            - event_id: Game identifier
            - game_id: Full game ID
            - away_team_id: Away team ID
            - home_team_id: Home team ID
            - away_score: Final away score (0 if scheduled)
            - home_score: Final home score (0 if scheduled)
            - winner_id: Winning team ID (None if scheduled)
            - status: 'completed' or 'scheduled'
            - game_date: Game date (if available)
            - success: True for completed games, False for scheduled
        """
        import json

        # Query all playoff events for this dynasty/season
        # FILTERING #1: Dynasty isolation via get_events_by_dynasty()
        all_playoff_events = self.event_db.get_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            event_type="GAME"
        )

        # FILTERING #2: Season + Round filtering via game_id prefix
        round_prefix = f"playoff_{self.season_year}_{round_name}_"

        # DIAGNOSTIC: Log query details for debugging season mismatch issues
        if self.verbose_logging:
            print(f"[PLAYOFF_QUERY] Querying playoff games:")
            print(f"  Round: {round_name}")
            print(f"  Season Year: {self.season_year}")
            print(f"  Query Prefix: {round_prefix}")
            print(f"  Total playoff events in database: {len(all_playoff_events)}")

        all_games = []

        for event in all_playoff_events:
            game_id = event.get('game_id', '')

            # Check if this game belongs to the target round
            if not game_id.startswith(round_prefix):
                continue

            # Parse event data
            event_data = event.get('data', '{}')
            if isinstance(event_data, str):
                try:
                    event_data = json.loads(event_data)
                except json.JSONDecodeError:
                    continue

            # Extract game parameters (always present, even for scheduled games)
            parameters = event_data.get('parameters', {})
            away_team_id = parameters.get('away_team_id')
            home_team_id = parameters.get('home_team_id')
            game_date = parameters.get('game_date')

            # Validate required fields
            if away_team_id is None or home_team_id is None:
                continue

            # Check if game has results (was simulated)
            results = event_data.get('results')

            if not results:
                # SCHEDULED GAME - no results yet, include as scheduled
                game_dict = {
                    'event_id': game_id,
                    'game_id': game_id,
                    'away_team_id': away_team_id,
                    'home_team_id': home_team_id,
                    'away_score': 0,
                    'home_score': 0,
                    'winner_id': None,
                    'status': 'scheduled',
                    'success': False,
                    'game_date': game_date
                }
                all_games.append(game_dict)
            else:
                # COMPLETED GAME - has results, include with scores
                away_score = results.get('away_score')
                home_score = results.get('home_score')

                # Validate scores
                if away_score is None or home_score is None:
                    continue

                # Determine winner
                winner_id = home_team_id if home_score > away_score else away_team_id

                game_dict = {
                    'event_id': game_id,
                    'game_id': game_id,
                    'away_team_id': away_team_id,
                    'home_team_id': home_team_id,
                    'away_score': away_score,
                    'home_score': home_score,
                    'winner_id': winner_id,
                    'status': 'completed',
                    'success': True,
                    'game_date': game_date
                }
                all_games.append(game_dict)

        if self.verbose_logging and all_games:
            scheduled_count = sum(1 for g in all_games if g['status'] == 'scheduled')
            completed_count = sum(1 for g in all_games if g['status'] == 'completed')
            print(f"[DATABASE_QUERY] Found {len(all_games)} total games for {round_name} round "
                  f"({completed_count} completed, {scheduled_count} scheduled)")

        return all_games

    def _schedule_next_round(self):
        """
        Schedule the next playoff round based on completed results.

        Updates current_round and schedules games for the next round.
        Prevents duplicate scheduling by checking if round already exists.
        Finds the last completed round, then schedules the next one.
        """
        if self.verbose_logging:
            print(f"\n[DEBUG] _schedule_next_round() called")
            print(f"[DEBUG] Current round: {self.state.current_round}")
            print(f"[DEBUG] Completed games status:")
            for round_name in self.ROUND_ORDER:
                count = len(self.state.completed_games[round_name])
                expected = self._get_expected_game_count(round_name)
                print(f"  - {round_name}: {count}/{expected} games")

        # Find the last COMPLETED round (not the active/incomplete one)
        # The active round is the first incomplete round, so the completed round
        # is the one before it (or none if active_round is wild_card with 0 games)
        active_round = self.get_active_round()
        active_index = self.ROUND_ORDER.index(active_round)

        if self.verbose_logging:
            print(f"[DEBUG] Active round (from get_active_round()): {active_round} (index {active_index})")

        # If active round is first round AND has no games, there's no completed round yet
        if active_index == 0 and len(self.state.completed_games[active_round]) == 0:
            if self.verbose_logging:
                print(f"[DEBUG] Early return: No completed rounds yet (active={active_round}, games=0)")
            self.logger.warning("No completed rounds yet - cannot schedule next round")
            return

        # The completed round is the one before the active round
        # (or the active round itself if it's complete)
        # Query database for accurate completion status (single source of truth)
        completed_games_db = self._get_completed_games_from_database(active_round)
        if len(completed_games_db) >= self._get_expected_game_count(active_round):
            # Active round is complete, use it as completed round
            completed_round = active_round
            if self.verbose_logging:
                print(f"[DEBUG] Active round is complete, using as completed_round: {completed_round}")
        else:
            # Active round is incomplete, so the completed round is the previous one
            if active_index == 0:
                if self.verbose_logging:
                    print(f"[DEBUG] Early return: Active round is first round and incomplete")
                self.logger.warning("Active round is first round and incomplete - cannot schedule next")
                return
            completed_round = self.ROUND_ORDER[active_index - 1]
            if self.verbose_logging:
                print(f"[DEBUG] Active round incomplete, using previous round as completed_round: {completed_round}")

        # Find the next round after the completed one
        try:
            completed_index = self.ROUND_ORDER.index(completed_round)
        except ValueError:
            if self.verbose_logging:
                print(f"[DEBUG] Early return: Unknown round: {completed_round}")
            self.logger.error(f"Unknown round: {completed_round}")
            return

        if completed_index >= len(self.ROUND_ORDER) - 1:
            if self.verbose_logging:
                print(f"[DEBUG] Early return: Already at Super Bowl, no next round")
            self.logger.warning("Already at Super Bowl - no next round to schedule")
            return

        next_round = self.ROUND_ORDER[completed_index + 1]

        if self.verbose_logging:
            print(f"[DEBUG] Determined: completed_round={completed_round}, next_round={next_round}")

        # Check for existing round games (delegate to BracketPersistence)
        existing_events = self.persistence.check_existing_round(
            dynasty_id=self.dynasty_id,
            season=self.season_year,
            round_name=next_round
        )

        if existing_events:
            if self.verbose_logging:
                print(f"⏭️  Skipping {next_round} scheduling - {len(existing_events)} games already exist")
            return

        # Calculate start date for next round
        round_offsets = {
            'divisional': self.DIVISIONAL_OFFSET,
            'conference': self.CONFERENCE_OFFSET,
            'super_bowl': self.SUPER_BOWL_OFFSET
        }

        offset = round_offsets.get(next_round, 0)
        start_date = self.wild_card_start_date.add_days(offset)

        if self.verbose_logging:
            print(f"[DEBUG] Date calculation: wild_card_start={self.wild_card_start_date}, offset={offset}, start_date={start_date}")
            print(f"\n{'='*80}")
            print(f"SCHEDULING {next_round.upper()} ROUND")
            print(f"{'='*80}")
            print(f"Completed Round: {completed_round.title()}")
            print(f"Start Date: {start_date}")

        try:
            # FIX #3: Query database directly for completed games with results
            # This solves the issue where self.state.completed_games is empty after app reload
            # because it only tracks in-memory simulated games
            completed_games = self._get_completed_games_from_database(completed_round)

            if not completed_games:
                if self.verbose_logging:
                    print(f"[ERROR] Cannot schedule {next_round}: No completed games found for {completed_round}")
                    print(f"[ERROR] Database query returned 0 games with results")
                self.logger.error(f"Cannot schedule {next_round}: No completed games for {completed_round}")
                return

            # Convert completed games to GameResult objects for PlayoffScheduler
            completed_results = self._convert_games_to_results(completed_games)

            if self.verbose_logging:
                print(f"[DATABASE_QUERY] Retrieved {len(completed_games)} completed games from database")
                print(f"Converting {len(completed_games)} completed games to {len(completed_results)} results")

            # Schedule next round using PlayoffScheduler
            # Pass completed_round (not self.current_round which may be stale)
            result = self.playoff_scheduler.schedule_next_round(
                completed_results=completed_results,
                current_round=completed_round,
                original_seeding=self.state.original_seeding,
                start_date=start_date,
                season=self.season_year,
                dynasty_id=self.dynasty_id
            )

            # Store the bracket for this round in state
            self.state.brackets[next_round] = result['bracket']

            # DO NOT update current_round here - let it transition naturally
            # when we start simulating games from the next round
            # self.current_round = next_round  # REMOVED - causes premature round transition

            if self.verbose_logging:
                print(f"[DEBUG] Scheduling succeeded! Result: {result.get('games_scheduled')} games scheduled")
                print(f"✅ {next_round.title()} round scheduled: {result['games_scheduled']} games")
                print(f"  (Will transition to {next_round.title()} when games are simulated)")
                print(f"[DEBUG] _schedule_next_round() completed successfully")
                print(f"{'='*80}")

        except Exception as e:
            self.logger.error(f"Error scheduling {next_round} round: {e}")
            if self.verbose_logging:
                print(f"[DEBUG] Exception caught in _schedule_next_round(): {e}")
                print(f"❌ {next_round.title()} scheduling failed: {e}")
                import traceback
                traceback.print_exc()
            # Don't update current_round on error
            # Let the round stay where it is until games are actually ready

    def _get_next_round_name(self, current_round: str) -> Optional[str]:
        """
        Get the name of the next playoff round.

        Args:
            current_round: Current round name

        Returns:
            Next round name or None if already at Super Bowl
        """
        try:
            current_index = self.ROUND_ORDER.index(current_round)
            if current_index < len(self.ROUND_ORDER) - 1:
                return self.ROUND_ORDER[current_index + 1]
        except (ValueError, IndexError):
            pass
        return None

    def _detect_game_round(self, game_id: str) -> Optional[str]:
        """
        Detect which playoff round a game belongs to from its game_id.

        Game IDs follow format: playoff_{dynasty_id}_{season}_{round}_{game_number}

        Note: dynasty_id and round may contain underscores, so we match from the end.

        Args:
            game_id: Game ID string

        Returns:
            Round name ('wild_card', 'divisional', 'conference', 'super_bowl') or None
        """
        if not game_id or 'playoff_' not in game_id:
            return None

        try:
            # Since dynasty_id can contain underscores, we need to check for known rounds
            # by testing each possible round name
            for round_name in self.ROUND_ORDER:
                # Check if game_id ends with _{round_name}_{number}
                # e.g., "playoff_debug_dynasty_2024_wild_card_1" contains "_wild_card_1"
                # Pattern: _{round_name}_{one_or_more_digits}
                import re
                pattern = f"_{round_name}_\\d+$"
                if re.search(pattern, game_id):
                    return round_name

        except (IndexError, ValueError):
            pass

        return None

    def _convert_games_to_results(self, games: List[Dict[str, Any]]) -> List[GameResult]:
        """
        Convert completed game dictionaries to GameResult objects.

        Args:
            games: List of game dictionaries with keys:
                - home_team_id: int
                - away_team_id: int
                - home_score: int
                - away_score: int
                - winner_id: int

        Returns:
            List of GameResult objects for PlayoffScheduler
        """
        results = []

        for game in games:
            # Skip failed games
            if not game.get('success', False):
                continue

            # Load team objects
            home_team = get_team_by_id(game['home_team_id'])
            away_team = get_team_by_id(game['away_team_id'])

            # Create final score dictionary
            final_score = {
                home_team.team_id: game.get('home_score', 0),
                away_team.team_id: game.get('away_score', 0)
            }

            # Determine winner
            winner_id = game.get('winner_id')
            winner = home_team if winner_id == home_team.team_id else away_team

            # Create GameResult
            result = GameResult(
                home_team=home_team,
                away_team=away_team,
                final_score=final_score,
                winner=winner,
                total_plays=game.get('total_plays', 0),
                season_type="playoffs"
            )

            results.append(result)

        return results

    def _get_round_summary(self, round_name: str) -> Dict[str, Any]:
        """
        Get summary information for a playoff round.

        Args:
            round_name: Round name

        Returns:
            Dictionary with round summary
        """
        completed = self.state.completed_games.get(round_name, [])
        expected = self._get_expected_game_count(round_name)

        return {
            "round_name": round_name,
            "games_completed": len(completed),
            "games_expected": expected,
            "complete": len(completed) >= expected,
            "games": completed
        }

    def reset_playoffs(self, new_wild_card_date: Optional[Date] = None):
        """
        Reset the playoffs to a new starting point.

        Useful for testing or restarting playoffs with different seeding.

        Args:
            new_wild_card_date: New Wild Card start date (uses original if None)
        """
        if new_wild_card_date:
            self.wild_card_start_date = new_wild_card_date
            self.calendar.reset(new_wild_card_date)

        # Delegate to state reset
        self.state.reset()

        # Reinitialize bracket
        self._initialize_playoff_bracket()

        if self.verbose_logging:
            print(f"\n✅ Playoffs reset to {self.wild_card_start_date}")

    def clear_playoff_games(self) -> int:
        """
        Clear all playoff games for current dynasty/season.

        This is a safety method to ensure clean playoff scheduling.
        Useful for:
        - Removing old playoff games from previous test runs
        - Rescheduling playoffs after changing seeding
        - Dynasty cleanup operations

        Returns:
            Number of playoff games deleted
        """
        deleted = self.event_db.delete_playoff_events_by_dynasty(
            dynasty_id=self.dynasty_id,
            season=self.season_year
        )

        if self.verbose_logging and deleted > 0:
            print(f"🗑️  Cleared {deleted} old playoff game(s) for dynasty '{self.dynasty_id}', season {self.season_year}")

        return deleted

    def __str__(self) -> str:
        """String representation"""
        return (f"PlayoffController(season={self.season_year}, "
                f"round={self.state.current_round}, "
                f"games={self.state.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"PlayoffController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
