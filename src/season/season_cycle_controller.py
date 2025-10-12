"""
Season Cycle Controller

Unified controller orchestrating the complete NFL season cycle from
Week 1 Regular Season → Super Bowl → Offseason.

This controller manages the three distinct phases:
1. REGULAR_SEASON: 272 games across 18 weeks
2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
3. OFFSEASON: Post-season state with summary (future: draft, free agency, training camp)

Responsibilities:
- Coordinate SeasonController (regular season) and PlayoffController (playoffs)
- Handle automatic phase transitions
- Maintain calendar continuity across phases
- Preserve dynasty isolation
- Provide unified API for day/week advancement
- Support complete annual simulation cycle

This is a production-ready controller that should be used for full season simulations.
For individual phase control, use SeasonController or PlayoffController directly.
"""

import logging
from typing import Dict, List, Any, Optional

from calendar.date_models import Date
from calendar.season_phase_tracker import SeasonPhase
from calendar.phase_state import PhaseState
from playoff_system.playoff_controller import PlayoffController
from playoff_system.playoff_seeder import PlayoffSeeder
from database.api import DatabaseAPI


class SeasonCycleController:
    """
    Unified controller orchestrating complete NFL season simulation cycle.

    Manages three distinct phases:
    1. REGULAR_SEASON: 272 games across 18 weeks
    2. PLAYOFFS: 13 games (Wild Card → Super Bowl)
    3. OFFSEASON: Post-season state with summary

    Usage:
        # Create controller
        controller = SeasonCycleController(
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
        initial_phase: SeasonPhase = SeasonPhase.REGULAR_SEASON,
        enable_persistence: bool = True,
        verbose_logging: bool = True
    ):
        """
        Initialize season cycle controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            start_date: Dynasty start date - should be ONE DAY BEFORE first game
                       (defaults to Sept 4 for first game on Sept 5)
            initial_phase: Starting phase (REGULAR_SEASON, PLAYOFFS, or OFFSEASON)
                          Used when loading saved dynasty mid-season
            enable_persistence: Whether to save stats to database
            verbose_logging: Whether to print progress messages
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        print(f"[DYNASTY_TRACE] SeasonCycleController.__init__(): dynasty_id={dynasty_id}")
        self.season_year = season_year
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        self.logger = logging.getLogger(self.__class__.__name__)

        # Default to day before first game (first game is Thursday Sept 5, dynasty starts Wednesday Sept 4)
        if start_date is None:
            start_date = Date(season_year, 9, 4)

        self.start_date = start_date

        # Create shared phase state with correct starting phase (single source of truth)
        self.phase_state = PhaseState(initial_phase)

        # Import SeasonController here to avoid circular imports
        from demo.interactive_season_sim.season_controller import SeasonController

        # Initialize season controller (always starts in regular season)
        self.season_controller = SeasonController(
            database_path=database_path,
            start_date=start_date,
            season_year=season_year,
            dynasty_id=dynasty_id,
            enable_persistence=enable_persistence,
            verbose_logging=verbose_logging,
            phase_state=self.phase_state
        )

        # Access the shared calendar from season controller
        self.calendar = self.season_controller.calendar

        # Playoff controller created when needed
        self.playoff_controller: Optional[PlayoffController] = None

        # Season summary (generated in offseason)
        self.season_summary: Optional[Dict[str, Any]] = None

        # Statistics
        self.total_games_played = 0
        self.total_days_simulated = 0

        # Database API for data retrieval (MUST be initialized before phase-aware initialization)
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

        # State tracking - set active controller based on initial phase
        # IMPORTANT: This comes AFTER database_api initialization because _restore_playoff_controller() needs it
        if initial_phase == SeasonPhase.PLAYOFFS:
            # Restore playoff controller from database
            self._restore_playoff_controller()
            self.active_controller = self.playoff_controller
        elif initial_phase == SeasonPhase.OFFSEASON:
            # No active controller in offseason
            self.active_controller = None
        else:
            # Regular season - use season controller
            self.active_controller = self.season_controller

        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON CYCLE CONTROLLER INITIALIZED'.center(80)}")
            print(f"{'='*80}")
            print(f"Season: {season_year}")
            print(f"Start Date: {start_date}")
            print(f"Dynasty: {dynasty_id}")
            print(f"Database: {database_path}")
            print(f"Current Phase: {self.phase_state.phase.value}")
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
        if self.phase_state.phase == SeasonPhase.OFFSEASON:
            # Execute any scheduled offseason events for this day
            try:
                current_date = self.calendar.get_current_date()

                # Import SimulationExecutor to trigger events
                from calendar.simulation_executor import SimulationExecutor

                executor = SimulationExecutor(
                    database_path=self.database_path,
                    calendar=self.calendar,
                    dynasty_id=self.dynasty_id
                )

                # Simulate events for current day
                event_results = executor.simulate_day(current_date)

                # Advance calendar
                self.calendar.advance_to_next_day()
                self.total_days_simulated += 1

                return {
                    "date": str(current_date),
                    "games_played": 0,
                    "events_triggered": event_results.get('events_executed', []),
                    "results": [],
                    "current_phase": "offseason",
                    "phase_transition": None,
                    "success": True,
                    "message": f"Offseason day complete. {len(event_results.get('events_executed', []))} events triggered."
                }

            except Exception as e:
                self.logger.error(f"Error during offseason day advancement: {e}")
                # Fallback to basic advancement
                self.calendar.advance_to_next_day()
                self.total_days_simulated += 1

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

        result['current_phase'] = self.phase_state.phase.value

        return result

    def advance_week(self) -> Dict[str, Any]:
        """
        Advance simulation by 7 days.

        Returns:
            Dictionary with weekly summary
        """
        if self.phase_state.phase == SeasonPhase.OFFSEASON:
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
        if self.verbose_logging:
            print(f"\n[DEBUG] advance_week(): Before phase transition check, phase = {self.phase_state.phase.value}")

        phase_transition = self._check_phase_transition()
        if phase_transition:
            result['phase_transition'] = phase_transition
            if self.verbose_logging:
                print(f"[DEBUG] advance_week(): Phase transition occurred: {phase_transition}")

        if self.verbose_logging:
            print(f"[DEBUG] advance_week(): After phase transition check, phase = {self.phase_state.phase.value}")

        result['current_phase'] = self.phase_state.phase.value

        # Add current date to result (matching what advance_day() returns)
        # This ensures UI controllers can properly update the displayed date
        result['date'] = str(self.calendar.get_current_date())

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
        while self.phase_state.phase != SeasonPhase.OFFSEASON:
            self.advance_week()

        return {
            "start_date": str(start_date),
            "end_date": str(self.calendar.get_current_date()),
            "total_games": self.total_games_played - initial_games,
            "final_phase": self.phase_state.phase.value,
            "season_summary": self.season_summary,
            "success": True
        }

    def simulate_to_phase_end(self, progress_callback=None) -> Dict[str, Any]:
        """
        Simulate until current phase ends (phase transition detected).

        Stops when phase changes, giving user control at phase boundaries.
        This allows users to review playoff brackets, make offseason decisions, etc.

        Args:
            progress_callback: Optional callback(week_num, games_played) for UI progress updates

        Returns:
            Summary dict with weeks_simulated, total_games, phase_transition info:
            {
                'start_date': str,
                'end_date': str,
                'weeks_simulated': int,
                'total_games': int,
                'starting_phase': str,
                'ending_phase': str,
                'phase_transition': bool,
                'success': bool
            }
        """
        starting_phase = self.phase_state.phase
        start_date = self.calendar.get_current_date()
        initial_games = self.total_games_played
        weeks_simulated = 0

        if self.verbose_logging:
            title = f"SIMULATING TO END OF {starting_phase.value.upper()}"
            print(f"\n{'='*80}")
            print(f"{title.center(80)}")
            print(f"{'='*80}")

        # Continue until phase changes
        consecutive_empty_weeks = 0
        max_empty_weeks = 3  # Safety valve: stop if 3 weeks pass with no games

        while self.phase_state.phase == starting_phase and self.phase_state.phase != SeasonPhase.OFFSEASON:
            games_before = self.total_games_played
            result = self.advance_week()
            games_after = self.total_games_played
            weeks_simulated += 1

            # Track consecutive empty weeks (no games played)
            if games_after == games_before:
                consecutive_empty_weeks += 1
                if consecutive_empty_weeks >= max_empty_weeks:
                    if self.verbose_logging:
                        print(f"[WARNING] Stopping simulation: {consecutive_empty_weeks} consecutive weeks with no games")
                    break
            else:
                consecutive_empty_weeks = 0  # Reset counter when games are played

            # Progress callback for UI updates
            if progress_callback:
                games_this_iteration = self.total_games_played - initial_games
                progress_callback(weeks_simulated, games_this_iteration)

        return {
            'start_date': str(start_date),
            'end_date': str(self.calendar.get_current_date()),
            'weeks_simulated': weeks_simulated,
            'total_games': self.total_games_played - initial_games,
            'starting_phase': starting_phase.value,
            'ending_phase': self.phase_state.phase.value,
            'phase_transition': self.phase_state.phase != starting_phase,
            'success': True
        }

    def get_current_phase(self) -> SeasonPhase:
        """Get current season phase."""
        return self.phase_state.phase

    def get_current_standings(self) -> Dict[str, Any]:
        """
        Get current standings (only available during regular season).

        Returns:
            Standings organized by division/conference
        """
        if self.phase_state.phase != SeasonPhase.REGULAR_SEASON:
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
        if self.phase_state.phase != SeasonPhase.PLAYOFFS:
            return None

        if not self.playoff_controller:
            return None

        return self.playoff_controller.get_current_bracket()

    def get_current_state(self) -> Dict[str, Any]:
        """Get comprehensive current state."""
        return {
            "current_phase": self.phase_state.phase.value,
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
        if self.verbose_logging:
            print(f"\n[DEBUG] Checking phase transition (current phase: {self.phase_state.phase.value})")

        if self.phase_state.phase == SeasonPhase.REGULAR_SEASON:
            if self._is_regular_season_complete():
                self._transition_to_playoffs()
                return {
                    "from_phase": "regular_season",
                    "to_phase": "playoffs",
                    "trigger": "272_games_complete"
                }

        elif self.phase_state.phase == SeasonPhase.PLAYOFFS:
            if self._is_super_bowl_complete():
                if self.verbose_logging:
                    print(f"[DEBUG] Super Bowl complete! Transitioning to offseason...")
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

        Filters:
        - Only this dynasty's games (dynasty_id)
        - Only regular season games (exclude playoffs/preseason)
        - Only reasonable weeks (weeks 1-18 to avoid corrupted data)

        Returns:
            Date of the last scheduled regular season game for this dynasty
        """
        try:
            # Get all GAME events from event database
            all_game_events = self.season_controller.event_db.get_events_by_type("GAME")

            # Filter for regular season games WITH DYNASTY ISOLATION
            regular_season_events = [
                e for e in all_game_events
                # CRITICAL: Only look at this dynasty's games
                if e.get('dynasty_id') == self.dynasty_id
                # Exclude playoff and preseason games
                and not e.get('game_id', '').startswith('playoff_')
                and not e.get('game_id', '').startswith('preseason_')
                # CRITICAL: Only include weeks 1-18 (ignore corrupted future games)
                and 1 <= e.get('data', {}).get('parameters', {}).get('week', 0) <= 18
            ]

            if not regular_season_events:
                # No regular season games scheduled - return season end date as fallback
                self.logger.warning(f"No regular season games found for dynasty {self.dynasty_id}")
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
                game_id = last_event.get('game_id', 'unknown')
                week = last_event.get('data', {}).get('parameters', {}).get('week', '?')
                self.logger.info(f"Last regular season game scheduled for: {last_date} (Week {week}, game_id={game_id})")

            return last_date

        except Exception as e:
            self.logger.error(f"Error calculating last regular season game date: {e}")
            # Fallback to Dec 31 if calculation fails
            return Date(self.season_year, 12, 31)

    def _is_regular_season_complete(self) -> bool:
        """
        Check if regular season is complete.

        Uses a hybrid approach for reliability:
        1. Primary: Check if 272 games have been played (most reliable)
        2. Fallback: Check if current date is after last scheduled game

        This handles both normal completion and edge cases (corrupted schedules).

        Returns:
            True if regular season is complete (either by game count or date)
        """
        # PRIMARY CHECK: Have all 272 regular season games been played?
        # This is the most reliable indicator and handles corrupted schedules
        games_played = self.total_games_played
        if games_played >= 272:
            if self.verbose_logging:
                print(f"[DEBUG] Regular season complete: {games_played} games played (threshold: 272)")
            return True

        # FALLBACK CHECK: Has date passed last scheduled regular season game?
        # This handles edge cases where games might not all be played
        current_date = self.calendar.get_current_date()
        date_check = current_date > self.last_regular_season_game_date

        if self.verbose_logging:
            print(f"[DEBUG] Regular season check:")
            print(f"  - Games played: {games_played}/272")
            print(f"  - Current date: {current_date}")
            print(f"  - Last scheduled game: {self.last_regular_season_game_date}")
            print(f"  - Date check result: {date_check}")

        return date_check

    def _is_super_bowl_complete(self) -> bool:
        """Check if Super Bowl has been played."""
        if not self.playoff_controller:
            if self.verbose_logging:
                print(f"\n[DEBUG] Checking Super Bowl completion: playoff_controller is None!")
            return False

        super_bowl_games = self.playoff_controller.get_round_games('super_bowl')
        is_complete = len(super_bowl_games) > 0

        # Debug logging
        if self.verbose_logging:
            print(f"\n[DEBUG] _is_super_bowl_complete() called:")
            print(f"  - playoff_controller exists: True")
            print(f"  - Super Bowl games: {super_bowl_games}")
            print(f"  - Super Bowl games count: {len(super_bowl_games)}")
            print(f"  - Is complete: {is_complete}")
            if super_bowl_games:
                print(f"  - Super Bowl winner: {super_bowl_games[0].get('winner_id')}")

        return is_complete

    def _transition_to_playoffs(self):
        """Execute transition from regular season to playoffs."""
        # Guard: prevent redundant transitions if already in playoffs
        if self.phase_state.phase == SeasonPhase.PLAYOFFS:
            if self.verbose_logging:
                print(f"\n⚠️  Already in playoffs phase, skipping transition")
            return

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
                initial_seeding=playoff_seeding,  # Pass real seeding from regular season!
                enable_persistence=self.enable_persistence,
                verbose_logging=self.verbose_logging,
                phase_state=self.phase_state
            )

            # Replace the playoff controller's calendar with the shared calendar
            # to maintain date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # Override the playoff controller's random seeding with real seeding
            self.playoff_controller.original_seeding = playoff_seeding

            # Note: PlayoffController.__init__() already handles Wild Card scheduling
            # via _initialize_playoff_bracket(), which checks for existing playoff games
            # and either schedules new games OR reconstructs bracket from existing games.
            # No need to schedule here - that would bypass the duplicate check!

            # 6. Update state
            self.phase_state.phase = SeasonPhase.PLAYOFFS
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ Playoff transition complete")
                print(f"   PlayoffController initialized and bracket ready")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error transitioning to playoffs: {e}")
            if self.verbose_logging:
                print(f"❌ Playoff transition failed: {e}")
            raise

    def _restore_playoff_controller(self):
        """
        Restore PlayoffController when loading saved dynasty mid-playoffs.

        Called during initialization when phase_state indicates dynasty is in playoffs.
        Reconstructs bracket from existing database events without re-scheduling games.
        """
        # Guard: prevent duplicate initialization
        if self.playoff_controller is not None:
            if self.verbose_logging:
                print(f"⚠️  Playoff controller already initialized, skipping restoration")
            return

        try:
            if self.verbose_logging:
                print(f"\n{'='*80}")
                print(f"{'RESTORING PLAYOFF STATE FROM DATABASE'.center(80)}")
                print(f"{'='*80}")

            # 1. Query database for final standings (needed for seeding)
            standings_data = self.database_api.get_standings(
                dynasty_id=self.dynasty_id,
                season=self.season_year
            )

            if not standings_data or not standings_data.get('divisions'):
                self.logger.error("No standings found - cannot restore playoff controller")
                raise RuntimeError("Cannot restore playoff bracket - no standings available")

            # 2. Convert standings to format expected by PlayoffSeeder
            standings_dict = {}
            for division_name, teams in standings_data.get('divisions', {}).items():
                for team_data in teams:
                    team_id = team_data['team_id']
                    standings_dict[team_id] = team_data['standing']

            # 3. Calculate playoff seeding
            seeder = PlayoffSeeder()
            playoff_seeding = seeder.calculate_seeding(
                standings=standings_dict,
                season=self.season_year,
                week=18
            )

            # 4. Estimate Wild Card date (mid-January)
            # When restoring, exact date matters less since games already scheduled
            wild_card_date = Date(self.season_year + 1, 1, 18)

            if self.verbose_logging:
                print(f"\n📋 Playoff Seeding Restored")
                print(f"📅 Wild Card Weekend: {wild_card_date}")

            # 5. Initialize PlayoffController
            # The controller's __init__ will detect existing playoff games and reconstruct bracket
            self.playoff_controller = PlayoffController(
                database_path=self.database_path,
                dynasty_id=self.dynasty_id,
                season_year=self.season_year,
                wild_card_start_date=wild_card_date,
                initial_seeding=playoff_seeding,
                enable_persistence=self.enable_persistence,
                verbose_logging=self.verbose_logging,
                phase_state=self.phase_state
            )

            # 6. Share calendar for date continuity
            self.playoff_controller.calendar = self.calendar
            self.playoff_controller.simulation_executor.calendar = self.calendar

            # 7. Set as active controller
            self.active_controller = self.playoff_controller

            if self.verbose_logging:
                print(f"\n✅ PlayoffController restored successfully")
                print(f"   Bracket reconstructed from existing database events")
                print(f"{'='*80}\n")

        except Exception as e:
            self.logger.error(f"Error restoring playoff controller: {e}")
            if self.verbose_logging:
                print(f"❌ Playoff restoration failed: {e}")
            raise

    def _transition_to_offseason(self):
        """Execute transition from playoffs to offseason."""
        if self.verbose_logging:
            print(f"\n{'='*80}")
            print(f"{'SEASON COMPLETE - ENTERING OFFSEASON'.center(80)}")
            print(f"{'='*80}")
            print(f"[DEBUG] _transition_to_offseason() called")
            print(f"[DEBUG] Current phase before transition: {self.phase_state.phase.value}")

        # CRITICAL DIAGNOSTIC: Verify playoff events exist BEFORE transition
        import sqlite3
        print(f"\n[PLAYOFF_LIFECYCLE] ===== BEFORE OFFSEASON TRANSITION =====")
        verify_conn = sqlite3.connect(self.database_path)
        verify_cursor = verify_conn.cursor()
        verify_cursor.execute("""
            SELECT COUNT(*) FROM events
            WHERE dynasty_id = ?
              AND event_type = 'GAME'
              AND game_id LIKE ?
        """, (self.dynasty_id, f"playoff_{self.season_year}_%"))
        playoff_count_before = verify_cursor.fetchone()[0]
        verify_conn.close()
        print(f"[PLAYOFF_LIFECYCLE]   Dynasty: {self.dynasty_id}")
        print(f"[PLAYOFF_LIFECYCLE]   Database: {self.database_path}")
        print(f"[PLAYOFF_LIFECYCLE]   Playoff events in database: {playoff_count_before}")
        if playoff_count_before == 0:
            print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: NO PLAYOFF EVENTS FOUND!")

        try:
            # 1. Get Super Bowl result
            super_bowl_games = self.playoff_controller.get_round_games('super_bowl')
            super_bowl_result = super_bowl_games[0] if super_bowl_games else None

            champion_id = None
            if super_bowl_result:
                champion_id = super_bowl_result.get('winner_id')

            # 2. Update state
            if self.verbose_logging:
                print(f"[DEBUG] Setting phase_state.phase to OFFSEASON...")
            self.phase_state.phase = SeasonPhase.OFFSEASON
            self.active_controller = None  # No active controller in offseason
            if self.verbose_logging:
                print(f"[DEBUG] Current phase after setting: {self.phase_state.phase.value}")

            # Schedule offseason events
            try:
                from offseason.offseason_event_scheduler import OffseasonEventScheduler

                scheduler = OffseasonEventScheduler()

                # Get Super Bowl date from result
                super_bowl_date = None
                if super_bowl_result and super_bowl_result.get('game_date'):
                    game_date_obj = super_bowl_result['game_date']
                    # Convert to Date if it's a datetime
                    if hasattr(game_date_obj, 'year'):
                        from calendar.date_models import Date
                        super_bowl_date = Date(game_date_obj.year, game_date_obj.month, game_date_obj.day)

                # If no date in result, use current calendar date
                if not super_bowl_date:
                    super_bowl_date = self.calendar.get_current_date()

                # Schedule all offseason events
                scheduling_result = scheduler.schedule_offseason_events(
                    super_bowl_date=super_bowl_date,
                    season_year=self.season_year,
                    dynasty_id=self.dynasty_id,
                    event_db=self.season_controller.event_db
                )

                if self.verbose_logging:
                    print(f"\n📅 Offseason Events Scheduled:")
                    print(f"   Deadline Events: {scheduling_result['deadline_events']}")
                    print(f"   Window Events: {scheduling_result['window_events']}")
                    print(f"   Milestone Events: {scheduling_result['milestone_events']}")
                    print(f"   Total Events: {scheduling_result['total_events']}")

            except Exception as e:
                self.logger.error(f"Error scheduling offseason events: {e}")
                if self.verbose_logging:
                    print(f"⚠️  Warning: Could not schedule offseason events: {e}")

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

            # CRITICAL DIAGNOSTIC: Verify playoff events STILL exist AFTER transition
            print(f"\n[PLAYOFF_LIFECYCLE] ===== AFTER OFFSEASON TRANSITION =====")
            verify_conn_after = sqlite3.connect(self.database_path)
            verify_cursor_after = verify_conn_after.cursor()
            verify_cursor_after.execute("""
                SELECT COUNT(*) FROM events
                WHERE dynasty_id = ?
                  AND event_type = 'GAME'
                  AND game_id LIKE ?
            """, (self.dynasty_id, f"playoff_{self.season_year}_%"))
            playoff_count_after = verify_cursor_after.fetchone()[0]
            verify_conn_after.close()
            print(f"[PLAYOFF_LIFECYCLE]   Playoff events in database: {playoff_count_after}")
            if playoff_count_after == 0:
                print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: PLAYOFF EVENTS DISAPPEARED!")
            elif playoff_count_after != playoff_count_before:
                print(f"[PLAYOFF_LIFECYCLE]   ⚠️  WARNING: Event count changed! Before: {playoff_count_before}, After: {playoff_count_after}")
            else:
                print(f"[PLAYOFF_LIFECYCLE]   ✅ Playoff events preserved ({playoff_count_after} events)")

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
        return (f"SeasonCycleController(season={self.season_year}, "
                f"phase={self.phase_state.phase.value}, "
                f"games={self.total_games_played})")

    def __repr__(self) -> str:
        """Detailed representation"""
        return (f"SeasonCycleController(database_path='{self.database_path}', "
                f"season_year={self.season_year}, "
                f"dynasty_id='{self.dynasty_id}')")
