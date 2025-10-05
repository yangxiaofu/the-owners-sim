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

from calendar.calendar_component import CalendarComponent
from calendar.simulation_executor import SimulationExecutor
from calendar.date_models import Date
from events import EventDatabaseAPI
from playoff_system.playoff_seeder import PlayoffSeeder
from playoff_system.playoff_manager import PlayoffManager
from playoff_system.playoff_scheduler import PlayoffScheduler
from playoff_system.seeding_models import PlayoffSeeding
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
        verbose_logging: bool = True
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
        """
        self.database_path = database_path
        self.season_year = season_year
        self.dynasty_id = dynasty_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        self.logger = logging.getLogger(self.__class__.__name__)

        # Default Wild Card start date (second Saturday of January)
        if wild_card_start_date is None:
            wild_card_start_date = Date(2025, 1, 11)

        self.wild_card_start_date = wild_card_start_date

        # Ensure database directory exists
        Path(database_path).parent.mkdir(parents=True, exist_ok=True)

        # Ensure dynasty exists in database (auto-create if needed)
        from database.connection import DatabaseConnection
        db_conn = DatabaseConnection(database_path)
        db_conn.ensure_dynasty_exists(dynasty_id)

        # Initialize core components
        self.calendar = CalendarComponent(
            start_date=wild_card_start_date,
            season_year=season_year
        )

        self.event_db = EventDatabaseAPI(database_path)

        self.simulation_executor = SimulationExecutor(
            calendar=self.calendar,
            event_db=self.event_db,
            database_path=database_path,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            season_year=season_year
        )

        # Playoff-specific components
        self.playoff_seeder = PlayoffSeeder()
        self.playoff_manager = PlayoffManager()
        self.playoff_scheduler = PlayoffScheduler(
            event_db_api=self.event_db,
            playoff_manager=self.playoff_manager
        )

        # Playoff state tracking
        self.current_round = 'wild_card'
        self.original_seeding: Optional[PlayoffSeeding] = None
        self.completed_games: Dict[str, List[Dict]] = {
            'wild_card': [],
            'divisional': [],
            'conference': [],
            'super_bowl': []
        }
        # Store actual bracket objects
        self.brackets: Dict[str, Optional['PlayoffBracket']] = {
            'wild_card': None,
            'divisional': None,
            'conference': None,
            'super_bowl': None
        }

        # Statistics tracking
        self.total_games_played = 0
        self.total_days_simulated = 0

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
            print(f"ADVANCING DAY - {self.current_round.upper()} ROUND")
            print(f"{'='*80}")

        # Get current date BEFORE advancing
        current_date = self.calendar.get_current_date()

        if self.verbose_logging:
            print(f"Current Date: {current_date}")
            print(f"Total Days Simulated: {self.total_days_simulated + 1}")

        # Simulate all games scheduled for TODAY (before advancing)
        simulation_result = self.simulation_executor.simulate_day(current_date)

        if self.verbose_logging:
            print(f"\n[DEBUG] simulation_result keys: {list(simulation_result.keys())}")
            print(f"[DEBUG] simulation_result content: {simulation_result}")

        # NOW advance calendar by 1 day for next call
        advance_result = self.calendar.advance(1)
        self.total_days_simulated += 1

        # Update statistics
        games_played = len([g for g in simulation_result.get('games_played', []) if g.get('success', False)])
        self.total_games_played += games_played

        if self.verbose_logging:
            print(f"[DEBUG] games_played count (from 'games_played' key): {games_played}")
            print(f"[DEBUG] Raw games list length: {len(simulation_result.get('games_played', []))}")

        # Detect round transitions and track completed games
        round_transitioned = False
        if games_played > 0:
            if self.verbose_logging:
                print(f"\n[DEBUG] Processing {games_played} games for tracking...")

            for i, game in enumerate(simulation_result.get('games_played', [])):
                if self.verbose_logging:
                    print(f"[DEBUG] Game {i+1}: event_id={game.get('event_id')}, success={game.get('success')}")

                if game.get('success', False):
                    # Detect which round this game belongs to by checking the event_id
                    game_round = self._detect_game_round(game.get('event_id', ''))

                    if self.verbose_logging:
                        print(f"[DEBUG]   Detected round: {game_round}, current_round: {self.current_round}")

                    # If game is from a different round, transition
                    if game_round and game_round != self.current_round:
                        if self.verbose_logging:
                            print(f"\n🔄 Round transition detected: {self.current_round} → {game_round}")
                        self.current_round = game_round
                        round_transitioned = True

                    # Track game in appropriate round (with duplicate detection)
                    event_id = game.get('event_id', '')
                    existing_event_ids = [g.get('event_id', '') for g in self.completed_games[self.current_round]]

                    if self.verbose_logging:
                        print(f"[DEBUG]   Existing event_ids in {self.current_round}: {len(existing_event_ids)}")
                        print(f"[DEBUG]   Is duplicate? {event_id in existing_event_ids}")

                    if event_id and event_id not in existing_event_ids:
                        self.completed_games[self.current_round].append(game)
                        if self.verbose_logging:
                            print(f"[DEBUG]   ✅ Game added to {self.current_round}! Total now: {len(self.completed_games[self.current_round])}")
                    elif event_id in existing_event_ids:
                        # This should NEVER happen if dynasty isolation is working correctly
                        error_msg = (
                            f"CRITICAL: Duplicate game detected: {event_id}. "
                            f"This indicates a bug in dynasty isolation or event scheduling. "
                            f"Check that playoff events are properly filtered by dynasty_id."
                        )
                        self.logger.error(error_msg)
                        raise RuntimeError(error_msg)
                else:
                    if self.verbose_logging:
                        print(f"[DEBUG]   ⚠️  Game marked as unsuccessful, not tracking")

        # Check if current round is complete
        round_complete = self._is_round_complete(self.current_round)

        if self.verbose_logging and games_played > 0:
            print(f"\n✅ Day complete: {games_played} game(s) played")
            print(f"Round progress: {len(self.completed_games[self.current_round])}/{self._get_expected_game_count(self.current_round)} games")

        return {
            "date": str(current_date),
            "games_played": games_played,
            "results": simulation_result.get('games_played', []),
            "current_round": self.current_round,
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
            print(f"ADVANCING WEEK - {self.current_round.upper()} ROUND")
            print(f"{'='*80}")

        start_date = self.calendar.get_current_date()
        daily_results = []
        total_games_this_week = 0
        rounds_completed = []

        # Simulate 7 days
        for day in range(7):
            day_result = self.advance_day()
            daily_results.append(day_result)
            total_games_this_week += day_result['games_played']

            # Check if round completed and schedule next round
            if day_result['round_complete']:
                if self.verbose_logging:
                    print(f"\n[DEBUG] Day {day+1}: Round {self.current_round} is complete!")
                    print(f"[DEBUG] Games played today: {day_result['games_played']}")

                if self.current_round != 'super_bowl':
                    if self.verbose_logging:
                        print(f"[DEBUG] Calling _schedule_next_round() for {self.current_round}")
                    rounds_completed.append(self.current_round)
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
            print(f"Total Playoff Games: {self.total_games_played}")
            if rounds_completed:
                print(f"Rounds Completed: {', '.join(r.title() for r in rounds_completed)}")
            print(f"{'='*80}")

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "total_games_played": total_games_this_week,
            "daily_results": daily_results,
            "current_round": self.current_round,
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
        initial_games = self.total_games_played
        initial_days = self.total_days_simulated

        # Advance until THIS SPECIFIC round is complete (safety limit: 30 days)
        max_days = 30
        days_simulated = 0

        while not self._is_round_complete(round_to_complete) and days_simulated < max_days:
            self.advance_day()
            days_simulated += 1

        games_in_round = self.total_games_played - initial_games

        # The round that was just completed
        completed_round = round_to_complete

        # Get completed games for the round that was just completed
        round_results = self.completed_games[completed_round].copy()

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
        initial_games = self.total_games_played
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
                rounds_completed.append(self.current_round)

                # If Super Bowl just completed, we're done
                if self.current_round == 'super_bowl':
                    break

                # Otherwise, schedule next round
                self._schedule_next_round()

            # Display progress every 7 days
            if self.verbose_logging and days_simulated % 7 == 0:
                current_date = self.calendar.get_current_date()
                print(f"\n📊 Progress Update (Day {days_simulated})")
                print(f"   Current Date: {current_date}")
                print(f"   Current Round: {self.current_round.title()}")
                print(f"   Total Games Played: {self.total_games_played}")

        final_date = self.calendar.get_current_date()
        total_games = self.total_games_played - initial_games

        # Determine Super Bowl winner
        super_bowl_winner = None
        if self.completed_games['super_bowl']:
            sb_game = self.completed_games['super_bowl'][0]
            super_bowl_winner = sb_game.get('winner_id')

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
            "current_round": self.current_round,
            "original_seeding": self.original_seeding,
            "wild_card": self.brackets['wild_card'],
            "divisional": self.brackets['divisional'],
            "conference": self.brackets['conference'],
            "super_bowl": self.brackets['super_bowl']
        }

        return bracket

    def get_round_games(self, round_name: str) -> List[Dict[str, Any]]:
        """
        Get games for a specific playoff round.

        Args:
            round_name: 'wild_card', 'divisional', 'conference', or 'super_bowl'

        Returns:
            List of game dictionaries with matchup and result information
        """
        if round_name not in self.ROUND_ORDER:
            raise ValueError(f"Invalid round name: {round_name}")

        return self.completed_games.get(round_name, [])

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
        round_progress = {
            round_name: {
                "games_completed": len(self.completed_games[round_name]),
                "games_expected": self._get_expected_game_count(round_name),
                "complete": len(self.completed_games[round_name]) >= self._get_expected_game_count(round_name)
            }
            for round_name in self.ROUND_ORDER
        }

        return {
            "current_date": str(current_date),
            "current_round": self.current_round,
            "active_round": self.get_active_round(),
            "games_played": self.total_games_played,
            "days_simulated": self.total_days_simulated,
            "round_progress": round_progress
        }

    def get_active_round(self) -> str:
        """
        Get the current "active" playoff round based on completion status.

        This is different from self.current_round which only updates when
        games from the next round are simulated. This method determines the
        active round based on:
        1. Which rounds have been completed
        2. Which rounds have games scheduled

        Returns:
            Round name ('wild_card', 'divisional', 'conference', 'super_bowl')

        Examples:
            - Wild Card complete, Divisional scheduled → returns 'divisional'
            - Divisional in progress → returns 'divisional'
            - All complete → returns 'super_bowl'
        """
        # Check each round in order
        for round_name in self.ROUND_ORDER:
            games_completed = len(self.completed_games[round_name])
            games_expected = self._get_expected_game_count(round_name)

            # If this round is incomplete, it's the active round
            if games_completed < games_expected:
                return round_name

        # All rounds complete - playoffs are over, return final round
        return 'super_bowl'

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
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"INITIALIZING PLAYOFF BRACKET WITH {seeding_type}")
            print(f"{'='*80}")

        # Check if Wild Card round already scheduled for this dynasty/season
        existing_events = self.event_db.get_events_by_type("GAME")
        dynasty_playoff_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_"
        dynasty_playoff_events = [
            e for e in existing_events
            if e.get('game_id', '').startswith(dynasty_playoff_prefix)
        ]

        if dynasty_playoff_events:
            if self.verbose_logging:
                print(f"\n✅ Found existing playoff bracket for dynasty '{self.dynasty_id}': {len(dynasty_playoff_events)} games")
                print(f"   Reusing existing playoff schedule")

            # Use provided seeding if available, otherwise generate random seeding for display
            if initial_seeding:
                self.original_seeding = initial_seeding
            else:
                self.original_seeding = self._generate_random_seeding()

            # TODO: Reconstruct bracket structure from existing events if needed
            # For now, bracket will be populated as games are simulated

            if self.verbose_logging:
                print(f"{'='*80}")
            return

        # No existing playoff events for this dynasty - generate new bracket
        # Use provided seeding if available, otherwise generate random seeding
        if initial_seeding:
            self.original_seeding = initial_seeding
        else:
            self.original_seeding = self._generate_random_seeding()

        if self.verbose_logging:
            print(f"\nAFC Seeding:")
            for seed in self.original_seeding.afc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

            print(f"\nNFC Seeding:")
            for seed in self.original_seeding.nfc.seeds:
                print(f"  #{seed.seed}: Team {seed.team_id} ({seed.record_string})")

        # Schedule Wild Card round
        try:
            result = self.playoff_scheduler.schedule_wild_card_round(
                seeding=self.original_seeding,
                start_date=self.wild_card_start_date,
                season=self.season_year,
                dynasty_id=self.dynasty_id
            )

            # Store the wild card bracket
            self.brackets['wild_card'] = result['bracket']

            if self.verbose_logging:
                print(f"\n✅ Wild Card round scheduled: {result['games_scheduled']} games")
                print(f"{'='*80}")

        except Exception as e:
            self.logger.error(f"Error scheduling Wild Card round: {e}")
            if self.verbose_logging:
                print(f"❌ Wild Card scheduling failed: {e}")
            raise

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

    def _is_round_complete(self) -> bool:
        """
        Check if current round is complete.

        Returns:
            True if all expected games for current round are complete
        """
        expected = self._get_expected_game_count(self.current_round)
        completed = len(self.completed_games[self.current_round])
        return completed >= expected

    def _is_round_complete(self, round_name: str) -> bool:
        """
        Check if a specific round is complete.

        Args:
            round_name: Name of round to check ('wild_card', 'divisional', etc.)

        Returns:
            True if all expected games for the round are complete
        """
        expected = self._get_expected_game_count(round_name)
        completed = len(self.completed_games[round_name])
        return completed >= expected

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

        Args:
            round_name: Round name

        Returns:
            Expected game count
        """
        expected_counts = {
            'wild_card': 6,
            'divisional': 4,
            'conference': 2,
            'super_bowl': 1
        }
        return expected_counts.get(round_name, 0)

    def _schedule_next_round(self):
        """
        Schedule the next playoff round based on completed results.

        Updates current_round and schedules games for the next round.
        Prevents duplicate scheduling by checking if round already exists.
        Finds the last completed round, then schedules the next one.
        """
        if self.verbose_logging:
            print(f"\n[DEBUG] _schedule_next_round() called")
            print(f"[DEBUG] Current round: {self.current_round}")
            print(f"[DEBUG] Completed games status:")
            for round_name in self.ROUND_ORDER:
                count = len(self.completed_games[round_name])
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
        if active_index == 0 and len(self.completed_games[active_round]) == 0:
            if self.verbose_logging:
                print(f"[DEBUG] Early return: No completed rounds yet (active={active_round}, games=0)")
            self.logger.warning("No completed rounds yet - cannot schedule next round")
            return

        # The completed round is the one before the active round
        # (or the active round itself if it's complete)
        if len(self.completed_games[active_round]) >= self._get_expected_game_count(active_round):
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

        # Check if next round already scheduled (prevent duplicates)
        event_prefix = f"playoff_{self.dynasty_id}_{self.season_year}_{next_round}_"
        existing_events = self.event_db.get_events_by_game_id_prefix(
            event_prefix,
            event_type="GAME"
        )

        if self.verbose_logging:
            print(f"[DEBUG] Checking for existing {next_round} events with prefix: {event_prefix}")
            print(f"[DEBUG] Found {len(existing_events)} existing events")

        if existing_events:
            if self.verbose_logging:
                print(f"[DEBUG] Early return: {next_round.title()} round already scheduled ({len(existing_events)} games)")
                print(f"   Skipping duplicate scheduling")
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
            # Convert completed games to GameResult objects for PlayoffScheduler
            # Use the round that just completed (not self.current_round which may be stale)
            completed_games = self.completed_games.get(completed_round, [])
            completed_results = self._convert_games_to_results(completed_games)

            if self.verbose_logging:
                print(f"Converting {len(completed_games)} completed games to {len(completed_results)} results")

            # Schedule next round using PlayoffScheduler
            # Pass completed_round (not self.current_round which may be stale)
            result = self.playoff_scheduler.schedule_next_round(
                completed_results=completed_results,
                current_round=completed_round,
                original_seeding=self.original_seeding,
                start_date=start_date,
                season=self.season_year,
                dynasty_id=self.dynasty_id
            )

            # Store the bracket for this round
            self.brackets[next_round] = result['bracket']

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
        completed = self.completed_games.get(round_name, [])
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

        self.current_round = 'wild_card'
        self.completed_games = {
            'wild_card': [],
            'divisional': [],
            'conference': [],
            'super_bowl': []
        }
        self.total_games_played = 0
        self.total_days_simulated = 0

        # Reinitialize bracket
        self._initialize_playoff_bracket()

        if self.verbose_logging:
            print(f"\n✅ Playoffs reset to {self.wild_card_start_date}")

    def __str__(self) -> str:
        """String representation"""
        return (f"PlayoffController(season={self.season_year}, "
                f"round={self.current_round}, "
                f"games={self.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"PlayoffController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
