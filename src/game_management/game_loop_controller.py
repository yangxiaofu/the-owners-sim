"""
Game Loop Controller

Orchestrates complete NFL game simulation by coordinating all existing components:
- GameManager for clock, possession, and scoring
- CoachingStaff for realistic play calling
- DriveManager for individual drives
- PlayEngine for play execution
- Statistics tracking throughout

Designed for unit testing with clear separation of concerns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import json
import logging
import random
from pathlib import Path

from game_management.game_manager import GameManager, GamePhase
from game_management.overtime_manager import (
    IOvertimeManager, RegularSeasonOvertimeManager,
    OvertimePossessionTracker, OvertimePhase
)
from game_management.drive_transition_manager import DriveTransitionManager
from game_management.game_constants import (
    # Field position
    DEFAULT_TOUCHBACK_YARD_LINE, FIRST_DOWN_DISTANCE, FOURTH_DOWN,
    PAT_FIELD_POSITION, PAT_KICK_FIELD_POSITION,
    # Scoring
    TOUCHDOWN_POINTS, FIELD_GOAL_POINTS, SAFETY_POINTS, EXTRA_POINT_POINTS,
    # Time
    QUARTER_DURATION_SECONDS, REGULATION_QUARTERS, PAT_TIME_SECONDS,
    TWO_MINUTES_SECONDS, FIVE_MINUTES_SECONDS, TEN_MINUTES_SECONDS,
    GAME_DURATION_MINUTES,
    # Play thresholds
    BIG_PLAY_THRESHOLD_YARDS, SACK_THRESHOLD_YARDS,
    # Clutch
    CLOSE_GAME_POINT_THRESHOLD, FOURTH_QUARTER_CLOSE_THRESHOLD,
    FOURTH_QUARTER_MODERATE_THRESHOLD, FOURTH_QUARTER_PRESSURE_THRESHOLD,
    ClutchPressure,
    # Crowd noise
    HOME_OFFENSE_BASE_NOISE, AWAY_OFFENSE_BASE_NOISE, CROWD_LEAD_BONUS,
    CROWD_FOURTH_QUARTER_BONUS, MAX_CROWD_NOISE,
    # Weather
    WeatherCondition, WEATHER_PROBABILITY_CLEAR, WEATHER_PROBABILITY_RAIN,
    WEATHER_PROBABILITY_WIND,
    # Other
    PRIMETIME_VARIANCE, DEFAULT_PLAYBOOK, TeamSide, MomentumEvent,
    PATOutcome, SpecialTeamsFormation,
)
from play_engine.game_state.drive_manager import DriveManager, DriveResult as DriveManagerResult, DriveEndReason
from play_engine.play_calling.coaching_staff import CoachingStaff
from play_engine.play_calling.staff_factory import StaffFactory
from play_engine.play_calling.play_caller import PlayCaller, PlayCallContext
from play_engine.core.engine import simulate
from play_engine.core.params import PlayEngineParams
from play_engine.core.play_result import PlayResult
from play_engine.simulation.stats import PlayerStatsAccumulator, TeamStatsAccumulator, PlayerStats
from play_engine.simulation.field_goal import FieldGoalSimulator
from play_engine.game_state.field_position import FieldPosition, FieldZone
from play_engine.game_state.down_situation import DownState, calculate_first_down_line
from play_engine.mechanics.rb_rotation import RBSubstitutionManager
from play_engine.mechanics.penalties.penalty_engine import PlayContext
from team_management.teams.team_loader import Team
from team_management.players.player import Position
from game_management.centralized_stats_aggregator import CentralizedStatsAggregator
from game_management.scoreboard import ScoringType
from game_management.momentum_tracker import MomentumTracker
from shared.game_result import GameResult
from game_management.player_performance_tracker import PlayerPerformanceTracker
from game_management.random_events import RandomEventChecker
from game_management.rivalry_modifiers import RivalryGameModifiers, get_rivalry_game_description
from game_management.quarter_continuation_manager import QuarterContinuationManager, DriveEndState

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass
class DriveResult:
    """Complete drive result with statistics and outcomes"""
    possessing_team_id: int
    starting_field_position: int
    ending_field_position: int
    drive_outcome: DriveEndReason
    plays: List[PlayResult] = field(default_factory=list)
    total_plays: int = 0
    total_yards: int = 0
    time_elapsed: int = 0  # seconds
    points_scored: int = 0
    pat_result: Optional[Any] = None  # PAT attempt result after touchdown
    quarter_started: int = 1  # Quarter when drive began (1-4 for regulation, 5+ for OT)
    starting_clock_seconds: int = QUARTER_DURATION_SECONDS  # Game clock time remaining when drive started
    # ✅ FIX: Store kickoff result that started this drive (for UI display)
    kickoff_result: Optional[Any] = None  # KickoffResult from transition to this drive
    # ✅ FIX: Store starting down state for quarter continuation display (Q1→Q2, Q3→Q4)
    starting_down: int = 1              # Down when drive STARTED (1-4)
    starting_distance: int = FIRST_DOWN_DISTANCE  # Yards to go when drive STARTED
    # ✅ FIX: Store final down state for quarter continuation (Q1→Q2, Q3→Q4)
    final_down: int = 1               # Down when drive ended (1-4)
    final_distance: int = FIRST_DOWN_DISTANCE  # Yards to go when drive ended



class GameLoopController:
    """
    Main game simulation orchestrator that coordinates all NFL game systems.
    
    Takes a prepared game setup and runs complete games with realistic
    play calling, drive management, and statistics tracking.
    """
    
    def __init__(self, game_manager: GameManager,
                 home_team: Team, away_team: Team,
                 home_coaching_staff_config: Dict, away_coaching_staff_config: Dict,
                 home_roster: List, away_roster: List,
                 overtime_manager: IOvertimeManager = None,
                 game_date=None,
                 season_type: str = "regular_season",
                 rivalry_modifiers: RivalryGameModifiers = None,
                 # Dependency injection for testability
                 momentum_tracker: MomentumTracker = None,
                 performance_tracker: PlayerPerformanceTracker = None,
                 random_event_checker: RandomEventChecker = None):
        """
        Initialize game loop controller with all required components

        Args:
            game_manager: Initialized GameManager with clock, scoreboard, possession
            home_team: Home team metadata
            away_team: Away team metadata
            home_coaching_staff_config: Coaching staff JSON configuration
            away_coaching_staff_config: Coaching staff JSON configuration
            home_roster: Home team player roster
            away_roster: Away team player roster
            overtime_manager: Manager for overtime rules, defaults to RegularSeasonOvertimeManager
            game_date: Date of the game
            season_type: Type of season ("regular_season" or "playoffs")
            rivalry_modifiers: RivalryGameModifiers for rivalry games (Milestone 11)
            momentum_tracker: Optional MomentumTracker instance (for testing)
            performance_tracker: Optional PlayerPerformanceTracker instance (for testing)
            random_event_checker: Optional RandomEventChecker instance (for testing)
        """
        self.game_manager = game_manager
        self.home_team = home_team
        self.away_team = away_team
        # Sort rosters by depth_chart_order to ensure starters get snaps first
        # This is critical for proper snap tracking - without sorting, backups may get
        # snaps instead of starters if they appear earlier in the roster list
        self.home_roster = sorted(
            home_roster,
            key=lambda p: (getattr(p, 'depth_chart_order', 99), -getattr(p, 'overall', 0))
        )
        self.away_roster = sorted(
            away_roster,
            key=lambda p: (getattr(p, 'depth_chart_order', 99), -getattr(p, 'overall', 0))
        )
        self.game_date = game_date
        self.season_type = season_type
        
        # Initialize overtime manager with default if none provided
        self.overtime_manager = overtime_manager or RegularSeasonOvertimeManager()
        
        # Create CoachingStaff instances from JSON configs
        self.home_coaching_staff = self._create_coaching_staff_from_config(
            home_coaching_staff_config, home_team.team_id
        )
        self.away_coaching_staff = self._create_coaching_staff_from_config(
            away_coaching_staff_config, away_team.team_id
        )
        
        # Create PlayCaller instances for both teams
        self.home_play_caller = PlayCaller(
            coaching_staff=self.home_coaching_staff,
            playbook_name=DEFAULT_PLAYBOOK
        )
        self.away_play_caller = PlayCaller(
            coaching_staff=self.away_coaching_staff,
            playbook_name=DEFAULT_PLAYBOOK
        )

        # RB rotation managers - distribute carries between starter/backup based on OC philosophy
        self.home_rb_manager = RBSubstitutionManager.from_coaching_staff(
            self.home_coaching_staff.offensive_coordinator
        )
        self.away_rb_manager = RBSubstitutionManager.from_coaching_staff(
            self.away_coaching_staff.offensive_coordinator
        )

        # Game tracking
        self.drive_results: List[DriveResult] = []
        self.total_plays = 0

        # Drive transition tracking
        self.next_drive_field_position: Optional[int] = None
        self.next_drive_possessing_team_id: Optional[int] = None
        self.next_drive_kickoff_result: Optional[Any] = None  # Store kickoff result for next drive
        # Quarter continuation - preserve down state when drive continues across quarters
        self.next_drive_down: Optional[int] = None
        self.next_drive_yards_to_go: Optional[int] = None

        # Statistics tracking - use CentralizedStatsAggregator for comprehensive statistics
        self.stats_aggregator = CentralizedStatsAggregator(
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id,
            game_identifier=f"Game_{away_team.abbreviation}_at_{home_team.abbreviation}"
        )

        # Legacy statistics components (for backward compatibility if needed)
        self.player_stats = self.stats_aggregator.player_stats
        self.team_stats = self.stats_aggregator.team_stats

        # Momentum tracking for realistic game flow
        # Use injected instance or create default (dependency injection for testability)
        self.momentum_tracker = momentum_tracker or MomentumTracker()

        # Variance & Unpredictability tracking (Tollgate 7)
        # Use injected instances or create defaults (dependency injection for testability)
        self.performance_tracker = performance_tracker or PlayerPerformanceTracker()
        self.random_event_checker = random_event_checker or RandomEventChecker()

        # Environmental context (Tollgate 6) - set at game start
        self.game_weather = self._initialize_weather()
        self.is_primetime_game = False  # Can be set to True for primetime games

        # Rivalry modifiers for enhanced rivalry games (Milestone 11)
        self.rivalry_modifiers = rivalry_modifiers or RivalryGameModifiers()

        # Drive transition manager for handling drive-to-drive transitions
        self.drive_transition_manager = DriveTransitionManager(
            possession_manager=self.game_manager.possession_manager,
            game_clock=self.game_manager.game_clock
        )

        # Quarter continuation manager for preserving down state across Q1→Q2 and Q3→Q4
        self.quarter_continuation_manager = QuarterContinuationManager()

    def run_game(self) -> GameResult:
        """
        Main game simulation method that orchestrates complete NFL game

        Returns:
            GameResult with comprehensive game statistics and drive summaries
        """
        logger.info("Starting Game Loop Simulation: %s @ %s",
                    self.away_team.abbreviation, self.home_team.abbreviation)

        # Initialize game with coin toss and opening setup
        self.game_manager.start_game()

        # ✅ FIX: Simulate opening kickoff (same as _handle_drive_transition does for post-score)
        # Away team kicks to home team at game start (simplified coin toss logic)
        opening_kickoff_result = self.drive_transition_manager._simulate_kickoff(
            kicking_team_id=self.away_team.team_id,
            receiving_team_id=self.home_team.team_id,
            is_onside_kick=False
        )

        # Store for Drive 1 to pick up
        self.next_drive_kickoff_result = opening_kickoff_result
        self.next_drive_field_position = opening_kickoff_result.starting_field_position
        self.next_drive_possessing_team_id = self.home_team.team_id

        # Reset performance tracker for new game (Tollgate 7: Variance & Unpredictability)
        # Streaks don't carry over between games
        self.performance_tracker.reset_all()
        
        # Run all four quarters
        for quarter in range(1, REGULATION_QUARTERS + 1):
            self._run_quarter(quarter)
            
            # Advance to next quarter/half after current quarter completes
            game_continues = self.game_manager.advance_quarter()
            if not game_continues:
                break
                
            # Check if game is over (non-overtime scenario)
            if self._is_game_over():
                break
        
        # Handle overtime if needed
        if self._needs_overtime():
            self._run_overtime()
        
        # Generate final result
        return self._generate_final_result()
    
    def _run_quarter(self, quarter: int) -> None:
        """Run a single quarter with drive sequences"""
        
        # Run drives until quarter ends
        while not self._is_quarter_complete():
            possessing_team_id = self.game_manager.possession_manager.get_possessing_team_id()
            
            if possessing_team_id is None:
                # Need to start a drive - handle kickoff or possession determination
                possessing_team_id = self._determine_next_possession()
            
            # Run single drive
            drive_result = self._run_drive(possessing_team_id)
            self.drive_results.append(drive_result)
            
            # Handle drive transition (possession change, field position, etc.)
            self._handle_drive_transition(drive_result)
    
    def _run_drive(self, possessing_team_id: int) -> DriveResult:
        """
        Run a single offensive drive
        
        Args:
            possessing_team_id: Team ID of the team with possession
            
        Returns:
            DriveResult with complete drive statistics
        """
        
        # Check for quarter continuation (Q1→Q2, Q3→Q4)
        # This uses the refactored QuarterContinuationManager for testable, reliable behavior
        continuation = self.quarter_continuation_manager.get_next_drive_state()

        # DEBUG: Log continuation state retrieval
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"QUARTER_CONT_DEBUG: should_continue={continuation.should_continue}, "
                     f"field_pos={continuation.field_position}, down={continuation.down}, "
                     f"yards_to_go={continuation.yards_to_go}, reason={continuation.reason}, "
                     f"legacy_down={self.next_drive_down}, legacy_ytg={self.next_drive_yards_to_go}")

        if continuation.should_continue:
            # Quarter continuation - preserve down/distance/field position
            starting_yard_line = continuation.field_position
            starting_down_state = DownState(
                current_down=continuation.down,
                yards_to_go=continuation.yards_to_go,
                first_down_line=calculate_first_down_line(starting_yard_line, continuation.yards_to_go)
            )
            logger.debug(f"QUARTER_CONT_DEBUG: Using QuarterContinuationManager state: {continuation.down}&{continuation.yards_to_go}")
        else:
            # New drive - use transition field position if available, otherwise default to touchback
            starting_yard_line = self.next_drive_field_position if self.next_drive_field_position is not None else DEFAULT_TOUCHBACK_YARD_LINE

            # Check if legacy down state is available (from DriveTransitionManager for continuations)
            if self.next_drive_down is not None and self.next_drive_yards_to_go is not None:
                # Use legacy down state (fallback for quarter continuations)
                starting_down_state = DownState(
                    current_down=self.next_drive_down,
                    yards_to_go=self.next_drive_yards_to_go,
                    first_down_line=calculate_first_down_line(starting_yard_line, self.next_drive_yards_to_go)
                )
                logger.debug(f"QUARTER_CONT_DEBUG: Using legacy down state: {self.next_drive_down}&{self.next_drive_yards_to_go}")
            else:
                # True new drive - 1st & 10
                starting_down_state = DownState(
                    current_down=1,
                    yards_to_go=FIRST_DOWN_DISTANCE,
                    first_down_line=calculate_first_down_line(starting_yard_line, FIRST_DOWN_DISTANCE)
                )

        # Clear ALL transition state AFTER use (OUTSIDE both branches)
        # This ensures legacy vars persist until they're actually needed
        self.next_drive_field_position = None
        self.next_drive_possessing_team_id = None
        self.next_drive_down = None
        self.next_drive_yards_to_go = None

        starting_position = FieldPosition(
            yard_line=starting_yard_line,
            possession_team=possessing_team_id,
            field_zone=FieldZone.OWN_TERRITORY
        )

        drive_manager = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down_state,
            possessing_team_id=possessing_team_id
        )

        # Reset drive-level state for red zone tracking
        # NFL "Red Zone TD %" = TDs / Red Zone Trips (not TDs / Red Zone Plays)
        self.stats_aggregator.reset_drive_state(possessing_team_id)

        # ✅ FIX: Capture quarter and clock at drive START (not end)
        drive_start_quarter = self.game_manager.game_clock.quarter
        drive_start_clock = self.game_manager.game_clock.time_remaining_seconds

        # Track drive statistics
        plays_in_drive: List[PlayResult] = []
        drive_total_yards = 0
        
        # Main drive loop - run plays until drive ends OR quarter time expires
        # FIX: Added quarter completion check to prevent plays executing at 0:00
        while not drive_manager.is_drive_over() and not self._is_quarter_complete():
            # ✅ CRITICAL: Capture down/distance BEFORE the play is processed
            # This is needed for situational stats (3rd down %, 4th down %, red zone %)
            pre_play_situation = drive_manager.get_current_situation()
            pre_play_down = pre_play_situation.down if pre_play_situation else 1
            pre_play_yards_to_go = pre_play_situation.yards_to_go if pre_play_situation else 10
            pre_play_field_position = pre_play_situation.field_position if pre_play_situation else 25

            # Run single play
            play_result = self._run_play(drive_manager, possessing_team_id)

            # ✅ FIX 7: Process play FIRST to finalize field position and scoring detection
            drive_manager.process_play_result(play_result)

            # ✅ FIX 7: Get the FINALIZED play from drive_manager's history
            # DriveManager has already updated field positions, detected scoring, and stored corrected play
            if drive_manager.play_history:
                finalized_play = drive_manager.play_history[-1]

                # DEBUG: Check if we're getting the same object or a different one
                if finalized_play is not play_result:
                    logger.warning("finalized_play is a DIFFERENT object than play_result - "
                                   "could cause double stat recording")

                # DEBUG: Check if this is a scoring play
                if getattr(finalized_play, 'is_scoring_play', False):
                    logger.debug("SCORING PLAY ADDED: points=%d, outcome=%s",
                                 getattr(finalized_play, 'points', 0),
                                 getattr(finalized_play, 'outcome', 'unknown'))

                plays_in_drive.append(finalized_play)

            # ✅ FIX: Record stats AFTER drive processing so TDs are included
            # DriveManager._update_touchdown_attribution() has already run at this point
            current_situation = drive_manager.get_current_situation() if not drive_manager.is_drive_over() else None

            # Use last known situation if drive just ended
            if current_situation is None:
                # Drive ended, use final position for stats context
                final_position = drive_manager.get_current_field_position()
                final_down = drive_manager.get_current_down_state()
                down = final_down.current_down
                yards_to_go = final_down.yards_to_go
                field_position = final_position.yard_line
            else:
                down = current_situation.down
                yards_to_go = current_situation.yards_to_go
                field_position = current_situation.field_position

            # ✅ CRITICAL: Use PRE-PLAY down/distance for situational stats
            # This is the down BEFORE the play was executed, which is what we need
            # to correctly track 3rd down conversions, 4th down conversions, etc.
            self.stats_aggregator.record_play_result(
                play_result=play_result,
                possessing_team_id=possessing_team_id,
                down=pre_play_down,
                yards_to_go=pre_play_yards_to_go,
                field_position=pre_play_field_position
            )

            # Update statistics
            self.total_plays += 1
            drive_total_yards += play_result.yards

        # FIX: Check if drive ended due to time expiration (quarter clock hit 0:00)
        # This happens when _is_quarter_complete() is True but drive_manager.is_drive_over() is False
        if self._is_quarter_complete() and not drive_manager.is_drive_over():
            drive_manager.end_due_to_time_expiration()

        # Get final drive result from DriveManager
        drive_manager_result = drive_manager.get_drive_result()

        # DEBUG: Check for duplicate plays
        if len(plays_in_drive) != len(set(id(p) for p in plays_in_drive)):
            logger.warning("plays_in_drive contains DUPLICATE plays: total=%d, unique=%d",
                           len(plays_in_drive), len(set(id(p) for p in plays_in_drive)))

        # DEBUG: Compare our plays list with drive_manager's list
        if len(plays_in_drive) != len(drive_manager.play_history):
            logger.warning("Play count mismatch: plays_in_drive=%d, drive_manager.play_history=%d",
                           len(plays_in_drive), len(drive_manager.play_history))

        # Calculate points from scoring plays in this drive
        drive_points = sum(
            getattr(play, 'points', 0)
            for play in plays_in_drive
            if getattr(play, 'is_scoring_play', False)
        )

        # STRICT VALIDATION: Scoring drives MUST have is_scoring_play=True on at least one play
        # This catches bugs in the play engine where points are set but is_scoring_play is not
        # NOTE: Safeties excluded - they are DEFENSIVE scores (points go to OTHER team)
        if drive_manager_result.end_reason.value in ['touchdown', 'field_goal'] and drive_points == 0:
            # Gather diagnostic info
            all_points = [(i, getattr(p, 'points', 0), getattr(p, 'is_scoring_play', False), getattr(p, 'outcome', 'unknown'))
                          for i, p in enumerate(plays_in_drive)]
            plays_with_points = [(i, pts, scoring, outcome) for i, pts, scoring, outcome in all_points if pts > 0]

            error_msg = (
                f"SCORING PLAY FLAG MISMATCH: Drive ended as {drive_manager_result.end_reason.value} "
                f"but no plays have is_scoring_play=True.\n"
                f"  Total plays: {len(plays_in_drive)}\n"
                f"  Plays with points>0 but is_scoring_play=False: {plays_with_points}\n"
                f"  All play data (idx, points, is_scoring, outcome): {all_points}"
            )

            # Raise exception to catch this bug during development
            raise ValueError(error_msg)

        # Convert to our DriveResult format

        # Get final down state for quarter continuation (Q1→Q2, Q3→Q4)
        final_down_state = drive_manager.get_current_down_state()

        # Capture drive end state for quarter continuation (Q1→Q2, Q3→Q4)
        # This uses the refactored QuarterContinuationManager which handles all the logic
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"QUARTER_CONT_CAPTURE: quarter={self.game_manager.game_clock.quarter}, "
                     f"end_reason={drive_manager_result.end_reason}, "
                     f"field_pos={drive_manager.current_position.yard_line}, "
                     f"down={final_down_state.current_down}, yards_to_go={final_down_state.yards_to_go}")

        self.quarter_continuation_manager.capture_drive_end(DriveEndState(
            possessing_team_id=possessing_team_id,
            field_position=drive_manager.current_position.yard_line,
            down=final_down_state.current_down,
            yards_to_go=final_down_state.yards_to_go,
            end_reason=drive_manager_result.end_reason,
            quarter=self.game_manager.game_clock.quarter
        ))

        drive_result = DriveResult(
            possessing_team_id=possessing_team_id,
            starting_field_position=drive_manager.starting_position.yard_line,  # ✅ FIX 8: Get actual starting position
            ending_field_position=drive_manager.current_position.yard_line,
            drive_outcome=drive_manager_result.end_reason,
            plays=plays_in_drive,
            total_plays=len(plays_in_drive),
            total_yards=drive_total_yards,
            time_elapsed=300,  # TODO: Calculate actual time
            points_scored=drive_points,  # ✅ Calculate from scoring plays
            quarter_started=drive_start_quarter,  # ✅ FIX: Use captured value from drive START
            starting_clock_seconds=drive_start_clock,  # ✅ FIX: Use captured value from drive START
            # ✅ FIX: Attach kickoff result that started this drive (for UI display)
            kickoff_result=self.next_drive_kickoff_result,
            # ✅ FIX: Store starting down state for play-by-play display (quarter continuations)
            starting_down=starting_down_state.current_down,
            starting_distance=starting_down_state.yards_to_go,
            # ✅ FIX: Store final down state for quarter continuation
            final_down=final_down_state.current_down,
            final_distance=final_down_state.yards_to_go
        )

        # Clear the stored kickoff result after using it
        self.next_drive_kickoff_result = None

        return drive_result
    
    def _run_play(self, drive_manager: DriveManager, possessing_team_id: int) -> PlayResult:
        """
        Run a single play within a drive
        
        Args:
            drive_manager: Current drive state manager
            possessing_team_id: Team with possession
            
        Returns:
            PlayResult from play execution
        """
        # Get current drive situation
        current_situation = drive_manager.get_current_situation()

        # Get momentum aggression modifier for offensive team (used for fourth-down decisions)
        offensive_team_momentum_type = 'home' if possessing_team_id == self.home_team.team_id else 'away'
        momentum_aggression_modifier = self.momentum_tracker.get_aggression_modifier(offensive_team_momentum_type)

        # Calculate score differential from possessing team's perspective
        # This enables GameScript (CONTROL_GAME, DESPERATION, etc.) to adjust run/pass ratios
        home_score = self.game_manager.scoreboard.get_team_score(self.home_team.team_id)
        away_score = self.game_manager.scoreboard.get_team_score(self.away_team.team_id)
        if possessing_team_id == self.home_team.team_id:
            score_differential = home_score - away_score
        else:
            score_differential = away_score - home_score

        # Build raw game state for GameSituationAnalyzer (enables game script modifiers)
        raw_game_state = {
            'home_score': home_score,
            'away_score': away_score,
            'quarter': self.game_manager.game_clock.quarter,
            'time_remaining': self.game_manager.game_clock.time_remaining_seconds,
            'possessing_team_id': possessing_team_id,
            'home_team_id': self.home_team.team_id,
            'away_team_id': self.away_team.team_id,
            'score_differential': score_differential,  # Key field for GameScript calculation
            # Additional fields for detailed play calling
            'field_position': current_situation.field_position,
            'down': current_situation.down,
            'yards_to_go': current_situation.yards_to_go,
        }

        # Create play call context with momentum modifier and game state
        play_context = PlayCallContext(
            situation=current_situation,
            momentum_aggression_modifier=momentum_aggression_modifier,
            raw_game_state=raw_game_state
        )
        
        # Get play callers for both teams
        offensive_play_caller = (self.home_play_caller if possessing_team_id == self.home_team.team_id 
                               else self.away_play_caller)
        defensive_play_caller = (self.away_play_caller if possessing_team_id == self.home_team.team_id 
                               else self.home_play_caller)
        
        # Select plays
        offensive_play_call = offensive_play_caller.select_offensive_play(play_context)
        defensive_play_call = defensive_play_caller.select_defensive_play(play_context)
        
        # Get team rosters
        offensive_players = (self.home_roster if possessing_team_id == self.home_team.team_id
                           else self.away_roster)
        defensive_players = (self.away_roster if possessing_team_id == self.home_team.team_id
                           else self.home_roster)

        # Determine team IDs for proper player stats attribution
        offensive_team_id = (self.home_team.team_id if possessing_team_id == self.home_team.team_id
                             else self.away_team.team_id)
        defensive_team_id = (self.away_team.team_id if possessing_team_id == self.home_team.team_id
                             else self.home_team.team_id)

        # NEW: Get momentum modifier for offensive team
        offensive_team_momentum = 'home' if possessing_team_id == self.home_team.team_id else 'away'
        momentum_modifier = self.momentum_tracker.get_momentum_modifier(offensive_team_momentum)

        # NEW (Milestone 11, Tollgate 5): Apply rivalry offensive boost
        # Rivalry games enhance player performance - multiply momentum by rivalry boost
        is_home_offense = (possessing_team_id == self.home_team.team_id)
        rivalry_offensive_boost = (
            self.rivalry_modifiers.home_offensive_boost if is_home_offense
            else self.rivalry_modifiers.away_offensive_boost
        )
        momentum_modifier = momentum_modifier * rivalry_offensive_boost

        # RB rotation: Select RB for run plays based on workload distribution
        rb_manager = self.home_rb_manager if possessing_team_id == self.home_team.team_id else self.away_rb_manager
        available_rbs = [p for p in offensive_players if getattr(p, 'primary_position', None) == Position.RB]
        selected_rb = rb_manager.select_rb_for_carry(available_rbs) if available_rbs else None

        # Create PlayEngineParams with momentum, variance trackers, environmental params, and selected RB
        play_params = PlayEngineParams(
            offensive_play_call=offensive_play_call,
            defensive_play_call=defensive_play_call,
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_team_id=offensive_team_id,
            defensive_team_id=defensive_team_id,
            momentum_modifier=momentum_modifier,  # Tollgate 5: Momentum
            weather_condition=self._get_weather_condition(),  # Tollgate 6: Weather effects
            crowd_noise_level=self._get_crowd_noise_level(possessing_team_id),  # Tollgate 6: Crowd noise
            clutch_factor=self._calculate_clutch_factor(raw_game_state),  # Tollgate 6: Clutch performance
            primetime_variance=self._get_primetime_variance(),  # Tollgate 6: Primetime variance
            is_away_team=(possessing_team_id != self.home_team.team_id),  # Tollgate 6: Home/away context
            performance_tracker=self.performance_tracker,  # Tollgate 7: Hot/cold streaks
            random_event_checker=self.random_event_checker,  # Tollgate 7: Rare events
            selected_ball_carrier=selected_rb,  # RB rotation for workload distribution
            field_position=current_situation.field_position,  # Pass actual field position
            down=current_situation.down,  # Pass current down
            distance=current_situation.yards_to_go  # Pass yards to go
        )

        # Execute play
        play_result = simulate(play_params)

        # Record RB carry for workload tracking (only for run plays)
        if selected_rb and hasattr(offensive_play_call, 'play_type'):
            play_type_str = str(offensive_play_call.play_type).upper()
            if 'RUN' in play_type_str:
                # Use player_id if available, otherwise use name+number key for synthetic players
                player_id = getattr(selected_rb, 'player_id', None)
                if player_id:
                    rb_manager.record_carry(player_id)
                else:
                    # Fallback for synthetic players (benchmarking mode)
                    player_key = f"{selected_rb.name}_{selected_rb.number}"
                    rb_manager.record_carry(player_key)

        # NEW: Detect and process momentum events after play
        self._process_momentum_events(play_result, offensive_team_id, defensive_team_id, current_situation)

        # NEW: Apply momentum decay after each play
        self.momentum_tracker.decay()

        # Advance game clock by play time
        clock_result = self.game_manager.game_clock.advance_time(play_result.time_elapsed)

        # FIX: Cap time_elapsed to actual time consumed (prevents quarter time overflow)
        # When a play takes 25 seconds but only 3 remain, clock caps at 0 but time_elapsed
        # should reflect only 3 seconds consumed, not 25
        if clock_result.time_advanced < play_result.time_elapsed:
            play_result.time_elapsed = clock_result.time_advanced

        # ✅ FIX: Stats recording moved to _run_drive() AFTER drive processing
        # This ensures TDs added by DriveManager are included in stats

        return play_result
    
    def _handle_drive_transition(self, drive_result: DriveResult) -> None:
        """Handle possession changes and field position after drive ends"""
        # Record drive completion in statistics
        self.stats_aggregator.record_drive_completion(
            drive_outcome=drive_result.drive_outcome.value,
            possessing_team_id=drive_result.possessing_team_id
        )

        # Create a temporary DriveManager with the drive result for DriveTransitionManager
        # We need to convert our DriveResult back to the format DriveTransitionManager expects
        temp_drive_position = FieldPosition(
            yard_line=drive_result.ending_field_position,
            possession_team=drive_result.possessing_team_id,
            field_zone=FieldZone.OWN_TERRITORY  # Simplified
        )
        # Use actual down state from drive for quarter continuation (Q1→Q2, Q3→Q4)
        temp_drive_down = DownState(
            current_down=drive_result.final_down,
            yards_to_go=drive_result.final_distance,
            first_down_line=calculate_first_down_line(drive_result.ending_field_position, drive_result.final_distance)
        )

        temp_drive_manager = DriveManager(
            starting_position=temp_drive_position,
            starting_down_state=temp_drive_down,
            possessing_team_id=drive_result.possessing_team_id
        )
        temp_drive_manager.drive_ended = True
        temp_drive_manager.end_reason = drive_result.drive_outcome

        # ✅ FIX: For punts, use the ACTUAL punt result from the drive's last play
        # instead of re-simulating with different random values
        actual_punt_play = None
        if drive_result.drive_outcome == DriveEndReason.PUNT and drive_result.plays:
            # Find the punt play (should be the last play)
            for play in reversed(drive_result.plays):
                if getattr(play, 'is_punt', False) or getattr(play, 'punt_distance', None) is not None:
                    actual_punt_play = play
                    break

        # Use DriveTransitionManager to handle the transition
        transition_result = self.drive_transition_manager.handle_drive_transition(
            completed_drive=temp_drive_manager,
            home_team_id=self.home_team.team_id,
            away_team_id=self.away_team.team_id,
            actual_punt_play=actual_punt_play  # Pass actual punt data
        )

        # FIX: Consume transition time (punt return, kickoff return, etc.)
        # This time was previously calculated but never consumed by the game clock
        if hasattr(transition_result, 'time_elapsed') and transition_result.time_elapsed > 0:
            self.game_manager.game_clock.advance_time(transition_result.time_elapsed)

        # Handle scoring if applicable
        if drive_result.drive_outcome == DriveEndReason.TOUCHDOWN:
            self.game_manager.scoreboard.add_score(drive_result.possessing_team_id, ScoringType.TOUCHDOWN)
            # Simulate PAT (extra point) after touchdown
            pat_result = self._simulate_pat_attempt(drive_result.possessing_team_id)

            # ✅ Store PAT result in drive_result for display
            drive_result.pat_result = pat_result

            if pat_result['made']:
                self.game_manager.scoreboard.add_score(drive_result.possessing_team_id, ScoringType.EXTRA_POINT)
            # Record PAT stats to aggregator with correct PAT context
            if pat_result['stats']:
                self.stats_aggregator.record_play_result(
                    play_result=pat_result['stats'],
                    possessing_team_id=drive_result.possessing_team_id,
                    down=0,           # PAT context - not part of standard down sequence
                    yards_to_go=0,    # PAT context - binary make/miss, not distance-based
                    field_position=PAT_FIELD_POSITION  # PAT spot: opponent's 2-yard line
                )

        elif drive_result.drive_outcome == DriveEndReason.FIELD_GOAL:
            self.game_manager.scoreboard.add_score(drive_result.possessing_team_id, ScoringType.FIELD_GOAL)
            # Field goal stats already recorded in _run_drive() - no duplicate needed
            # (PAT recording at lines 409-415 is correct - those are ONLY recorded here)
            
        elif drive_result.drive_outcome == DriveEndReason.SAFETY:
            # Safety scores 2 points for the opposing team
            opposing_team_id = self.away_team.team_id if drive_result.possessing_team_id == self.home_team.team_id else self.home_team.team_id
            self.game_manager.scoreboard.add_score(opposing_team_id, ScoringType.SAFETY)
        
        # Store transition information for next drive setup
        self.next_drive_field_position = transition_result.new_starting_field_position
        self.next_drive_possessing_team_id = transition_result.new_possessing_team_id
        # ✅ FIX: Store kickoff result for the next drive's display
        self.next_drive_kickoff_result = transition_result.kickoff_result
        # Store down state for quarter continuation (Q1→Q2, Q3→Q4)
        self.next_drive_down = transition_result.continuing_down
        self.next_drive_yards_to_go = transition_result.continuing_yards_to_go
    
    def _create_coaching_staff_from_config(self, config: Dict, team_id: int) -> CoachingStaff:
        """Create CoachingStaff instance from JSON configuration"""
        factory = StaffFactory()
        # Use the balanced staff creation as a simple implementation
        # TODO: Enhance this to use actual config data
        return factory.create_balanced_staff(f"Team_{team_id}")
    
    def _determine_next_possession(self) -> int:
        """Determine which team gets possession next (kickoffs, etc.)"""
        # For now, default to home team - TODO: Implement proper logic
        return self.home_team.team_id

    def _simulate_pat_attempt(self, team_id: int) -> Dict[str, Any]:
        """
        Simulate a Point After Touchdown (PAT) extra point attempt.

        PAT attempts are 33-yard field goals (from the 15-yard line + 18 yards to goal line).

        Args:
            team_id: ID of the team attempting the PAT

        Returns:
            Dict with 'made' (bool) and 'stats' (PlayStatsSummary) keys
        """
        # Get player lists using the same pattern as regular plays
        offensive_players = (self.home_roster if team_id == self.home_team.team_id
                           else self.away_roster)
        defensive_players = (self.away_roster if team_id == self.home_team.team_id
                           else self.home_roster)

        # Create field goal simulator with player lists
        try:
            fg_simulator = FieldGoalSimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=SpecialTeamsFormation.FIELD_GOAL.value,  # Standard PAT formation
                defensive_formation=SpecialTeamsFormation.FIELD_GOAL_BLOCK.value  # Standard PAT defense
            )
        except (IndexError, AttributeError, KeyError) as e:
            logger.warning("PAT simulator init failed: %s. Defaulting to made.", e)
            return {
                'made': True,
                'stats': None
            }

        # PAT is from opponent's 15-yard line (NFL rule since 2015)
        # FG distance formula: (100 - field_position) + 17
        # Target: 33-34 yards to match NFL PAT distance (92-94% accuracy range)
        # Set field_position = 83 → distance = (100-83)+17 = 34 yards (in 31-40 range)
        pat_context = PlayContext(
            down=0,  # Not applicable for PAT
            distance=0,  # Not applicable for PAT
            field_position=PAT_KICK_FIELD_POSITION,  # NFL PAT: 15-yard line → 33-yard attempt
            quarter=self.game_manager.game_clock.quarter,
            time_remaining=str(self.game_manager.game_clock.time_remaining_seconds),
            play_type="field_goal",
            offensive_formation=SpecialTeamsFormation.FIELD_GOAL.value,
            defensive_formation=SpecialTeamsFormation.FIELD_GOAL_BLOCK.value
        )

        # Simulate PAT attempt (33-yard NFL distance for 92-94% accuracy)
        try:
            # Use simulate_field_goal_play with skip_fake_decision=True
            # PAT attempts should NEVER be fake FGs - the fake FG logic was causing
            # 35% of PATs to be treated as fake attempts with ~54% success rate,
            # dragging overall XP accuracy down to ~52% instead of ~89%
            fg_result = fg_simulator.simulate_field_goal_play(context=pat_context, skip_fake_decision=True)

            # Mark stats as extra point attempt (not field goal)
            if fg_result.player_stats:
                for player_stat in fg_result.player_stats:
                    # Convert field goal stats to extra point stats for ALL players
                    # Only convert fields that have non-zero values

                    # 1. Convert FG attempts to XP attempts (kicker only will have this)
                    fg_attempts = getattr(player_stat, 'field_goal_attempts', 0)
                    if fg_attempts > 0:
                        setattr(player_stat, 'extra_points_attempted', fg_attempts)
                        setattr(player_stat, 'field_goal_attempts', 0)

                    # 2. Convert FG made to XP made (kicker only will have this)
                    fg_made = getattr(player_stat, 'field_goals_made', 0)
                    if fg_made > 0:
                        setattr(player_stat, 'extra_points_made', fg_made)
                        setattr(player_stat, 'field_goals_made', 0)

                    # 3. Clear FG miss/block stats (defensive coding)
                    # Always clear these to prevent blocked PATs being recorded as blocked FGs
                    setattr(player_stat, 'field_goals_missed', 0)
                    setattr(player_stat, 'field_goals_blocked', 0)

            # Convert to PlayResult (required by stats_aggregator)
            pat_made = fg_result.field_goal_outcome == "made"
            pat_play_result = PlayResult(
                outcome=PATOutcome.MADE.value if pat_made else PATOutcome.MISSED.value,
                yards=0,  # PAT doesn't gain yards
                points=EXTRA_POINT_POINTS if pat_made else 0,
                time_elapsed=PAT_TIME_SECONDS,
                player_stats_summary=fg_result,
                is_scoring_play=pat_made
            )

            return {
                'made': pat_made,
                'stats': pat_play_result
            }
        except Exception as e:
            # If PAT simulation fails, default to made (98% success rate in NFL)
            logger.exception("PAT simulation error: %s (type: %s). Defaulting to made.",
                             e, type(e).__name__)
            return {
                'made': True,
                'stats': None
            }

    def _is_quarter_complete(self) -> bool:
        """Check if current quarter is complete based on game clock"""
        return self.game_manager.game_clock.is_end_of_quarter
    
    def _is_game_over(self) -> bool:
        """Check if game is over (regulation time)"""
        game_state = self.game_manager.get_game_state()
        return game_state.phase == GamePhase.FINAL
    
    def _needs_overtime(self) -> bool:
        """Check if game is tied and needs overtime"""
        game_state = self.game_manager.get_game_state()
        home_score = game_state.score[self.home_team.team_id]
        away_score = game_state.score[self.away_team.team_id]
        
        return (game_state.quarter >= REGULATION_QUARTERS and
                home_score == away_score and
                game_state.phase != GamePhase.FINAL)
    
    def _run_overtime(self) -> None:
        """
        Handle overtime using modular overtime manager with NFL possession rules.

        NFL OT Rules (2023+):
        - Both teams get at least one possession (guaranteed possession)
        - Exception: First team scores a TD = game ends immediately
        - After both possess: any score wins (sudden death)
        - Regular season: 10-minute period, can end in tie
        - Playoffs: 15-minute periods, continues until winner

        This method delegates to the overtime manager for rule-specific logic
        and uses OvertimePossessionTracker to enforce guaranteed possession.
        """
        logger.info("OVERTIME!")

        # Handle overtime periods until resolution
        while True:
            game_state = self.game_manager.get_game_state()

            # Check if overtime should continue
            if not self.overtime_manager.should_enter_overtime(game_state) and \
               not self.overtime_manager.should_continue_overtime(game_state):
                break

            # Get configuration for next overtime period
            overtime_setup = self.overtime_manager.setup_overtime_period()

            # Execute the overtime period with possession tracking
            game_ended = self._execute_overtime_period_with_tracking(overtime_setup)

            if game_ended:
                logger.info("Overtime ended - winner determined after %d period(s)",
                            self.overtime_manager.periods_completed)
                break

            # Check if game should end after this period (time expired)
            game_state = self.game_manager.get_game_state()
            if not self.overtime_manager.should_continue_overtime(game_state):
                logger.info("Overtime ended after %d period(s)",
                            self.overtime_manager.periods_completed)
                break
            else:
                logger.info("Still tied after %d period(s), continuing...",
                            self.overtime_manager.periods_completed)

    def _execute_overtime_period_with_tracking(self, overtime_setup) -> bool:
        """
        Execute a single overtime period with NFL possession tracking.

        Args:
            overtime_setup: OvertimeSetup object with period configuration

        Returns:
            True if game ended (winner determined), False if period ended with tie
        """
        logger.info("Overtime period: %s", overtime_setup.description)

        # Use GameManager API to set up overtime period
        self.game_manager.start_overtime_period(
            quarter=overtime_setup.quarter_number,
            time_seconds=overtime_setup.clock_time_seconds,
            possession_team_id=overtime_setup.possession_team_id
        )

        # Determine which team gets first possession
        possessing_team_id = self.game_manager.get_possessing_team_id()
        other_team_id = (self.away_team.team_id
                         if possessing_team_id == self.home_team.team_id
                         else self.home_team.team_id)

        # ✅ FIX: Simulate overtime kickoff (like opening kickoff)
        # The team NOT receiving kicks to the receiving team
        overtime_kickoff_result = self.drive_transition_manager._simulate_kickoff(
            kicking_team_id=other_team_id,
            receiving_team_id=possessing_team_id,
            is_onside_kick=False
        )

        # Store for first OT drive to pick up
        self.next_drive_kickoff_result = overtime_kickoff_result
        self.next_drive_field_position = overtime_kickoff_result.starting_field_position
        self.next_drive_possessing_team_id = possessing_team_id

        # ✅ FIX: Clear quarter continuation state to prevent inheriting 4th quarter down/distance
        self.quarter_continuation_manager.clear_continuation()

        logger.info("OT kickoff: Team %d kicks to Team %d, ball at %d-yard line",
                    other_team_id, possessing_team_id,
                    overtime_kickoff_result.starting_field_position)

        # Create possession tracker for NFL rules enforcement
        ot_tracker = OvertimePossessionTracker(
            team_a_id=possessing_team_id,
            team_b_id=other_team_id
        )

        logger.info("OT possession tracking: Team %d has first possession", possessing_team_id)

        # Run drives with possession tracking
        while not self.game_manager.is_quarter_over():
            possessing_team_id = self.game_manager.get_possessing_team_id()

            # Run the drive
            drive_result = self._run_drive(possessing_team_id)
            self.drive_results.append(drive_result)

            # FIX: Update scoreboard IMMEDIATELY after drive ends
            # This must happen BEFORE checking if game should end, otherwise
            # sudden-death OT TDs don't update the scoreboard (bug fix)
            if drive_result.drive_outcome != DriveEndReason.TIME_EXPIRATION:
                self._handle_drive_transition(drive_result)

            # Classify drive result for possession tracking
            result_type = self._classify_drive_result_for_ot(drive_result)
            points = drive_result.points_scored

            # Record possession result
            ot_tracker.record_possession(possessing_team_id, result_type, points)

            logger.info("OT possession: Team %d - %s (%d pts) | Phase: %s",
                        possessing_team_id, result_type, points,
                        ot_tracker.get_current_phase().value)

            # Check if game should end based on NFL rules
            if ot_tracker.should_game_end():
                winner_id = ot_tracker.get_winning_team_id()
                logger.info("OVERTIME WINNER: Team %d", winner_id)
                self.game_manager.end_game()
                return True

        # Period ended without a winner (time expired while tied)
        return False

    def _classify_drive_result_for_ot(self, drive_result: 'DriveResult') -> str:
        """
        Classify a drive result for overtime possession tracking.

        Args:
            drive_result: Completed drive result

        Returns:
            Result type string: "touchdown", "field_goal", "turnover", "punt", etc.
        """
        outcome = drive_result.drive_outcome

        if outcome == DriveEndReason.TOUCHDOWN:
            return "touchdown"
        elif outcome == DriveEndReason.FIELD_GOAL:
            return "field_goal"
        elif outcome == DriveEndReason.SAFETY:
            return "safety"
        elif outcome in [DriveEndReason.TURNOVER_INTERCEPTION, DriveEndReason.TURNOVER_FUMBLE]:
            return "turnover"
        elif outcome == DriveEndReason.PUNT:
            return "punt"
        elif outcome == DriveEndReason.TURNOVER_ON_DOWNS:
            return "turnover_on_downs"
        elif outcome == DriveEndReason.TIME_EXPIRATION:
            return "time_expired"
        elif outcome == DriveEndReason.FIELD_GOAL_MISSED:
            return "field_goal_missed"
        else:
            return "other"

    def _execute_overtime_period(self, overtime_setup) -> None:
        """
        Execute a single overtime period using the provided configuration.

        DEPRECATED: Use _execute_overtime_period_with_tracking instead.
        Kept for backwards compatibility.

        Args:
            overtime_setup: OvertimeSetup object with period configuration
        """
        logger.info("Overtime period: %s", overtime_setup.description)

        # Use GameManager API to set up overtime period
        self.game_manager.start_overtime_period(
            quarter=overtime_setup.quarter_number,
            time_seconds=overtime_setup.clock_time_seconds,
            possession_team_id=overtime_setup.possession_team_id
        )

        # Run the overtime period using existing quarter logic
        # This reuses all existing drive management, play calling, etc.
        self._run_quarter(overtime_setup.quarter_number)
    
    def _generate_final_result(self) -> GameResult:
        """Generate comprehensive final game result"""
        game_state = self.game_manager.get_game_state()
        
        # Determine winner
        home_score = game_state.score[self.home_team.team_id]
        away_score = game_state.score[self.away_team.team_id]
        
        if home_score > away_score:
            winner = self.home_team
        elif away_score > home_score:
            winner = self.away_team
        else:
            winner = None  # Tie (shouldn't happen in NFL)

        # Debug logging for winner calculation
        logger.debug("Winner calculated: %s (team_id=%s, home=%d, away=%d)",
                     winner.full_name if winner else 'TIE',
                     winner.team_id if winner else None,
                     home_score, away_score)

        # Finalize statistics
        final_score_dict = {
            self.home_team.team_id: home_score,
            self.away_team.team_id: away_score
        }
        self.stats_aggregator.finalize_game(final_score_dict)
        
        # Generate comprehensive statistics for export/serialization
        comprehensive_stats = self.stats_aggregator.get_all_statistics()

        # Add momentum summary to comprehensive statistics
        momentum_summary = self.momentum_tracker.get_summary()
        comprehensive_stats['momentum'] = {
            'home': {
                'momentum_value': momentum_summary['home_momentum'],
                'momentum_level': momentum_summary['home_level'],
                'performance_modifier': momentum_summary['home_modifier'],
                'aggression_modifier': momentum_summary['home_aggression']
            },
            'away': {
                'momentum_value': momentum_summary['away_momentum'],
                'momentum_level': momentum_summary['away_level'],
                'performance_modifier': momentum_summary['away_modifier'],
                'aggression_modifier': momentum_summary['away_aggression']
            }
        }

        # Get PlayerGameStats objects ready for persistence - using new conversion method
        player_stats = self.stats_aggregator.get_player_game_statistics()              # Returns List[PlayerGameStats]

        # Note: PlayerGameStats already have correct team_id, no fixing needed

        home_team_stats = self.stats_aggregator.get_team_statistics(self.home_team.team_id)  # Must return TeamStats
        away_team_stats = self.stats_aggregator.get_team_statistics(self.away_team.team_id)  # Must return TeamStats

        # Add momentum information to team stats for box score display
        # Convert TeamStats objects to dictionaries and add momentum
        if hasattr(home_team_stats, '__dict__'):
            home_stats_dict = home_team_stats.__dict__.copy()
        else:
            home_stats_dict = {}
        home_stats_dict['Momentum'] = f"{momentum_summary['home_level']} ({momentum_summary['home_momentum']:.1f})"

        if hasattr(away_team_stats, '__dict__'):
            away_stats_dict = away_team_stats.__dict__.copy()
        else:
            away_stats_dict = {}
        away_stats_dict['Momentum'] = f"{momentum_summary['away_level']} ({momentum_summary['away_momentum']:.1f})"

        # Validation assertions to catch issues immediately
        assert isinstance(player_stats, list), f"Expected list, got {type(player_stats)}"
        assert len(player_stats) > 0, f"No player statistics generated - this indicates a fundamental issue. Total plays: {self.total_plays}"
        assert home_team_stats is not None, f"No home team stats for team {self.home_team.team_id}"
        assert away_team_stats is not None, f"No away team stats for team {self.away_team.team_id}"

        # Validate first player statistics structure (dictionary format)
        first_player = player_stats[0]
        if isinstance(first_player, dict):
            assert 'player_name' in first_player, f"Player stats dictionary missing player_name: {type(first_player)}, available keys: {list(first_player.keys())}"
            assert 'passing_yards' in first_player, f"Player stats dictionary missing stats: {type(first_player)}, available keys: {list(first_player.keys())}"
        else:
            # Fallback for object format
            assert hasattr(first_player, 'player_name'), f"PlayerGameStats object missing player_name: {type(first_player)}, available attributes: {dir(first_player)}"
            assert hasattr(first_player, 'passing_yards'), f"PlayerGameStats object missing stats: {type(first_player)}, available attributes: {dir(first_player)}"

        # Detect overtime from quarter number (Q5+ = overtime)
        overtime_played = game_state.quarter > REGULATION_QUARTERS
        overtime_periods = max(0, game_state.quarter - REGULATION_QUARTERS)

        game_result = GameResult(
            home_team=self.home_team,
            away_team=self.away_team,
            final_score=final_score_dict,
            quarter_scores=[],  # TODO: Implement quarter scoring
            drives=self.drive_results,
            total_plays=self.total_plays,
            game_duration_minutes=GAME_DURATION_MINUTES,  # TODO: Calculate actual duration
            overtime_played=overtime_played,
            overtime_periods=overtime_periods,
            date=self.game_date,
            season_type=self.season_type,  # ✅ FIX: Pass season_type to GameResult
            winner=winner,  # ✅ FIX: Pass calculated winner to GameResult
            # ✅ FIXED: Direct object access - guaranteed objects with attributes
            player_stats=player_stats,              # List[PlayerStats] - guaranteed objects
            home_team_stats=home_stats_dict,        # Dict with momentum info
            away_team_stats=away_stats_dict,        # Dict with momentum info
            final_statistics=comprehensive_stats    # Dict for serialization (includes momentum)
        )

        # Debug logging for GameResult
        logger.debug("GameResult created with winner: %s (team_id=%s)",
                     game_result.winner.full_name if game_result.winner else 'None',
                     game_result.winner.team_id if game_result.winner else None)

        return game_result
    
    def get_current_game_state(self) -> Dict[str, Any]:
        """Get current game state for external monitoring"""
        game_state = self.game_manager.get_game_state()
        return {
            "quarter": game_state.quarter,
            "time_remaining": game_state.time_remaining,
            "score": game_state.score,
            "phase": game_state.phase.value,
            "drives_completed": len(self.drive_results),
            "total_plays": self.total_plays
        }
    
    # Public API Methods for Statistics Access
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """
        Get all statistics in comprehensive format.
        
        Returns:
            Complete statistics package with player, team, and game data
        """
        return self.stats_aggregator.get_all_statistics()
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """
        Get game-level statistics summary.
        
        Returns:
            Game-level statistics including play counts, drive outcomes, etc.
        """
        return self.stats_aggregator.get_game_statistics()
    
    def get_player_statistics(self, team_id: Optional[int] = None, 
                            player_name: Optional[str] = None) -> List[Any]:
        """
        Get player statistics with optional filtering.
        
        Args:
            team_id: Filter by team (None = all teams)
            player_name: Filter by specific player (None = all players)
            
        Returns:
            List of PlayerStats objects matching the criteria
        """
        return self.stats_aggregator.get_player_statistics(team_id, player_name)
    
    def get_team_statistics(self, team_id: int) -> Optional[Any]:
        """
        Get team statistics for a specific team.
        
        Args:
            team_id: Team identifier (1-32)
            
        Returns:
            TeamStats object or None if team not found
        """
        return self.stats_aggregator.get_team_statistics(team_id)
    
    def is_statistics_complete(self) -> bool:
        """Check if any statistics have been recorded."""
        return self.stats_aggregator.is_statistics_complete()

    def _fix_player_team_assignments(self, player_stats: List[Any]) -> None:
        """
        Fix team_id assignments for PlayerStats objects based on player names.

        The PlayerStatsAccumulator doesn't properly assign team_id, so we fix it here
        by looking up real player names using the PlayerDataLoader.
        """
        try:
            # Use PlayerDataLoader for team lookups (supports both team-based and single file formats)
            from team_management.players.player_loader import get_player_loader

            player_loader = get_player_loader()

            # Create lookup dict: player_name -> team_id
            player_team_lookup = {}
            for player in player_loader._players_by_id.values():
                full_name = player.full_name
                team_id = player.team_id
                if full_name and team_id:
                    player_team_lookup[full_name] = team_id

            # Fix team_id for each PlayerStats object
            fixed_count = 0
            for player_stat in player_stats:
                if hasattr(player_stat, 'player_name') and hasattr(player_stat, 'team_id'):
                    player_name = player_stat.player_name
                    lookup_team_id = player_team_lookup.get(player_name)

                    if lookup_team_id and lookup_team_id in [self.home_team.team_id, self.away_team.team_id]:
                        # Only update if player belongs to one of the teams in this game
                        original_team_id = player_stat.team_id
                        player_stat.team_id = lookup_team_id
                        logger.debug("Fixed %s: Team %d -> Team %d",
                                     player_name, original_team_id, lookup_team_id)
                        fixed_count += 1
                    elif lookup_team_id:
                        logger.warning("Player %s belongs to Team %d, not in this game (%d vs %d)",
                                       player_name, lookup_team_id,
                                       self.home_team.team_id, self.away_team.team_id)

            logger.info("Fixed team assignments for %d/%d players", fixed_count, len(player_stats))

        except Exception as e:
            logger.exception("Error fixing player team assignments: %s", e)

    def _process_momentum_events(self, play_result: PlayResult, offensive_team_id: int,
                                 defensive_team_id: int, current_situation) -> None:
        """
        Detect and process momentum events from play result.

        Args:
            play_result: Result of the play
            offensive_team_id: ID of offensive team
            defensive_team_id: ID of defensive team
            current_situation: Current drive situation
        """
        # Determine home/away for momentum tracking
        offensive_team = TeamSide.HOME.value if offensive_team_id == self.home_team.team_id else TeamSide.AWAY.value
        defensive_team = TeamSide.AWAY.value if offensive_team_id == self.home_team.team_id else TeamSide.HOME.value

        # Touchdown
        if play_result.points == TOUCHDOWN_POINTS:
            self.momentum_tracker.add_event(offensive_team, MomentumEvent.TOUCHDOWN.value)

        # Turnover (interception, fumble)
        if hasattr(play_result, 'is_turnover') and play_result.is_turnover:
            self.momentum_tracker.add_event(defensive_team, MomentumEvent.TURNOVER_GAIN.value)
            self.momentum_tracker.add_event(offensive_team, MomentumEvent.TURNOVER_LOSS.value)

        # Big play (20+ yards)
        if play_result.yards >= BIG_PLAY_THRESHOLD_YARDS and not (hasattr(play_result, 'is_turnover') and play_result.is_turnover):
            self.momentum_tracker.add_event(offensive_team, MomentumEvent.BIG_PLAY_GAIN.value)

        # Sack (significant loss on pass play)
        if play_result.yards <= SACK_THRESHOLD_YARDS and hasattr(play_result, 'outcome') and 'sack' in str(play_result.outcome).lower():
            self.momentum_tracker.add_event(defensive_team, MomentumEvent.SACK.value)

        # Field goal made
        if play_result.points == FIELD_GOAL_POINTS:
            self.momentum_tracker.add_event(offensive_team, MomentumEvent.FIELD_GOAL_MADE.value)

        # Field goal blocked
        if hasattr(play_result, 'outcome') and 'blocked' in str(play_result.outcome).lower():
            self.momentum_tracker.add_event(defensive_team, MomentumEvent.FIELD_GOAL_BLOCKED.value)

    # ===== Environmental Parameter Methods (Tollgate 6) =====

    def _initialize_weather(self) -> str:
        """
        Initialize weather condition for the game (set once at game start).

        Weather probabilities:
        - 60% clear: Normal conditions
        - 20% rain: Reduced passing accuracy, slippery ball
        - 15% wind: Reduced deep pass success, affects kicks
        - 5% snow: Reduced visibility, reduced accuracy

        Returns:
            Weather condition string ("clear", "rain", "heavy_wind", "snow")
        """
        rand = random.random()
        if rand < WEATHER_PROBABILITY_CLEAR:
            return WeatherCondition.CLEAR.value
        elif rand < WEATHER_PROBABILITY_RAIN:
            return WeatherCondition.RAIN.value
        elif rand < WEATHER_PROBABILITY_WIND:
            return WeatherCondition.HEAVY_WIND.value
        else:
            return WeatherCondition.SNOW.value

    def _get_weather_condition(self) -> str:
        """Get the current game weather condition."""
        return self.game_weather

    def _get_crowd_noise_level(self, possessing_team_id: int) -> int:
        """
        Calculate crowd noise level (0-100) based on home/away and game situation.

        Crowd noise affects communication and snap timing for the offense.
        Rivalry games have amplified crowd noise through crowd_noise_boost.

        Args:
            possessing_team_id: Team ID of the team with possession

        Returns:
            Crowd noise level (0-100, where 0=quiet, 100=deafening)
        """
        # Determine if possessing team is home or away
        is_home_team_offense = (possessing_team_id == self.home_team.team_id)

        if is_home_team_offense:
            # Home team on offense: crowd is quiet to help their team
            base_noise = HOME_OFFENSE_BASE_NOISE
        else:
            # Away team on offense: crowd is loud to disrupt communication
            base_noise = AWAY_OFFENSE_BASE_NOISE

            # Get current scores
            home_score = self.game_manager.scoreboard.get_team_score(self.home_team.team_id)
            away_score = self.game_manager.scoreboard.get_team_score(self.away_team.team_id)
            quarter = self.game_manager.game_clock.quarter
            time_remaining = self.game_manager.game_clock.time_remaining_seconds

            # Bonus if home team is winning
            if home_score > away_score:
                base_noise += CROWD_LEAD_BONUS

            # Bonus if 4th quarter close game (within 7 points)
            if quarter == REGULATION_QUARTERS and abs(home_score - away_score) <= CLOSE_GAME_POINT_THRESHOLD and time_remaining < FIVE_MINUTES_SECONDS:
                base_noise += CROWD_FOURTH_QUARTER_BONUS

            # NEW: Rivalry crowd noise boost (Milestone 11, Tollgate 5)
            # Amplifies crowd noise in rivalry games (1.0-1.25 multiplier)
            base_noise = int(base_noise * self.rivalry_modifiers.crowd_noise_boost)

        return min(MAX_CROWD_NOISE, base_noise)

    def _calculate_clutch_factor(self, game_state: Dict[str, Any]) -> float:
        """
        Calculate clutch pressure factor (0.0-1.0) based on game situation.

        High clutch situations increase variance and affect player performance.

        Args:
            game_state: Dictionary with home_score, away_score, quarter, time_remaining

        Returns:
            Clutch factor (0.0=no pressure, 1.0=maximum pressure)
        """
        quarter = game_state.get('quarter', 1)
        time_remaining = game_state.get('time_remaining', QUARTER_DURATION_SECONDS)
        home_score = game_state.get('home_score', 0)
        away_score = game_state.get('away_score', 0)
        score_diff = abs(home_score - away_score)

        # No clutch pressure in early quarters
        if quarter < 3:
            return ClutchPressure.NONE

        # 3rd quarter: low clutch pressure
        if quarter == 3:
            if score_diff <= CLOSE_GAME_POINT_THRESHOLD and time_remaining < FIVE_MINUTES_SECONDS:
                return ClutchPressure.LOW
            return ClutchPressure.NONE

        # 4th quarter: moderate to high clutch pressure
        if quarter == REGULATION_QUARTERS:
            # Last 2 minutes, within 8 points
            if time_remaining < TWO_MINUTES_SECONDS and score_diff <= FOURTH_QUARTER_CLOSE_THRESHOLD:
                return ClutchPressure.MAXIMUM

            # Last 5 minutes, within 10 points
            if time_remaining < FIVE_MINUTES_SECONDS and score_diff <= FOURTH_QUARTER_MODERATE_THRESHOLD:
                return ClutchPressure.HIGH

            # Last 10 minutes, within 14 points
            if time_remaining < TEN_MINUTES_SECONDS and score_diff <= FOURTH_QUARTER_PRESSURE_THRESHOLD:
                return ClutchPressure.MODERATE

        return ClutchPressure.NONE

    def _get_primetime_variance(self) -> float:
        """
        Get primetime variance multiplier (0.0-0.15).

        Primetime games have additional outcome variance due to pressure and spotlight.

        Returns:
            Primetime variance (0.0=regular game, 0.15=primetime game)
        """
        return PRIMETIME_VARIANCE if self.is_primetime_game else 0.0

    def get_rivalry_turnover_variance(self) -> float:
        """
        Get turnover variance multiplier for rivalry games (Milestone 11).

        Rivalry games have more unpredictable outcomes with increased turnover risk.
        This multiplier should be applied to base turnover probability.

        Returns:
            Turnover variance (1.0=normal, 1.4=40% more turnovers for legendary rivalry)
        """
        return self.rivalry_modifiers.turnover_variance

    def get_rivalry_penalty_modifier(self) -> float:
        """
        Get penalty rate modifier for rivalry games (Milestone 11).

        Rivalry games have more chippy play resulting in more penalties.
        This multiplier should be applied to base penalty probability.

        Returns:
            Penalty modifier (1.0=normal, 1.35=35% more penalties for legendary rivalry)
        """
        return self.rivalry_modifiers.penalty_rate_modifier

    def is_rivalry_game(self) -> bool:
        """
        Check if this is a rivalry game with meaningful modifiers.

        Returns:
            True if this is a rivalry game (intensity > MINIMAL)
        """
        return self.rivalry_modifiers.is_rivalry_game

    def get_rivalry_game_description(self) -> str:
        """
        Get a human-readable description of the rivalry game atmosphere.

        For use in play-by-play commentary and game displays.

        Returns:
            Description string (empty if not a rivalry game)
        """
        return get_rivalry_game_description(self.rivalry_modifiers)