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
from pathlib import Path

from .game_manager import GameManager, GamePhase
from .overtime_manager import IOvertimeManager, RegularSeasonOvertimeManager
from ..play_engine.game_state.drive_manager import DriveManager, DriveResult as DriveManagerResult, DriveEndReason
from ..play_engine.play_calling.coaching_staff import CoachingStaff
from ..play_engine.play_calling.staff_factory import StaffFactory
from ..play_engine.play_calling.play_caller import PlayCaller, PlayCallContext
from ..play_engine.core.engine import simulate
from ..play_engine.core.params import PlayEngineParams
from ..play_engine.core.play_result import PlayResult
from ..play_engine.simulation.stats import PlayerStatsAccumulator, TeamStatsAccumulator
from ..team_management.teams.team_loader import Team
from .centralized_stats_aggregator import CentralizedStatsAggregator
from .scoreboard import ScoringType
from shared.game_result import GameResult


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
                 game_date=None):
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
        """
        self.game_manager = game_manager
        self.home_team = home_team
        self.away_team = away_team
        self.home_roster = home_roster
        self.away_roster = away_roster
        self.game_date = game_date
        
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
            playbook_name="balanced"
        )
        self.away_play_caller = PlayCaller(
            coaching_staff=self.away_coaching_staff,
            playbook_name="balanced"
        )
        
        # Game tracking
        self.drive_results: List[DriveResult] = []
        self.total_plays = 0
        
        # Drive transition tracking
        self.next_drive_field_position: Optional[int] = None
        self.next_drive_possessing_team_id: Optional[int] = None
        
        # Statistics tracking - use CentralizedStatsAggregator for comprehensive statistics
        self.stats_aggregator = CentralizedStatsAggregator(
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id,
            game_identifier=f"Game_{away_team.abbreviation}_at_{home_team.abbreviation}"
        )
        
        # Legacy statistics components (for backward compatibility if needed)
        self.player_stats = self.stats_aggregator.player_stats
        self.team_stats = self.stats_aggregator.team_stats
        
        # Drive transition manager for handling drive-to-drive transitions
        from .drive_transition_manager import DriveTransitionManager
        self.drive_transition_manager = DriveTransitionManager(
            possession_manager=self.game_manager.possession_manager,
            game_clock=self.game_manager.game_clock
        )
    
    def run_game(self) -> GameResult:
        """
        Main game simulation method that orchestrates complete NFL game
        
        Returns:
            GameResult with comprehensive game statistics and drive summaries
        """
        print(f"\n🏈 Starting Game Loop Simulation")
        print(f"   {self.away_team.abbreviation} @ {self.home_team.abbreviation}")
        
        # Initialize game with coin toss and opening setup
        self.game_manager.start_game()
        
        # Run all four quarters
        for quarter in range(1, 5):
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
        
        # Create DriveManager for this drive - need proper FieldPosition and DownState objects
        from ..play_engine.game_state.field_position import FieldPosition, FieldZone
        from ..play_engine.game_state.down_situation import DownState
        
        # Use transition field position if available, otherwise default to 25 (touchback)
        starting_yard_line = self.next_drive_field_position if self.next_drive_field_position is not None else 25
        
        starting_position = FieldPosition(
            yard_line=starting_yard_line,
            possession_team=possessing_team_id,
            field_zone=FieldZone.OWN_TERRITORY
        )
        
        # Clear transition data after using it
        self.next_drive_field_position = None
        self.next_drive_possessing_team_id = None
        starting_down_state = DownState(
            current_down=1,
            yards_to_go=10,
            first_down_line=30
        )
        
        drive_manager = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down_state,
            possessing_team_id=possessing_team_id
        )
        
        # Track drive statistics
        plays_in_drive: List[PlayResult] = []
        drive_total_yards = 0
        
        # Main drive loop - run plays until drive ends
        while not drive_manager.is_drive_over():
            # Run single play
            play_result = self._run_play(drive_manager, possessing_team_id)
            plays_in_drive.append(play_result)
            
            # Update drive state with play result
            drive_manager.process_play_result(play_result)
            
            # Update statistics
            self.total_plays += 1
            drive_total_yards += play_result.yards
        
        # Get final drive result from DriveManager
        drive_manager_result = drive_manager.get_drive_result()
        
        # Convert to our DriveResult format
        drive_result = DriveResult(
            possessing_team_id=possessing_team_id,
            starting_field_position=20,  # TODO: Get from drive_manager
            ending_field_position=drive_manager.current_position.yard_line,
            drive_outcome=drive_manager_result.end_reason,
            plays=plays_in_drive,
            total_plays=len(plays_in_drive),
            total_yards=drive_total_yards,
            time_elapsed=300,  # TODO: Calculate actual time
            points_scored=0  # TODO: Calculate from scoring plays
        )
        
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
        
        # Create play call context
        play_context = PlayCallContext(situation=current_situation)
        
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

        # Create PlayEngineParams
        play_params = PlayEngineParams(
            offensive_play_call=offensive_play_call,
            defensive_play_call=defensive_play_call,
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            offensive_team_id=offensive_team_id,
            defensive_team_id=defensive_team_id
        )
        
        # Execute play
        play_result = simulate(play_params)
        
        # Advance game clock by play time
        clock_result = self.game_manager.game_clock.advance_time(play_result.time_elapsed)
        
        # Record play statistics using CentralizedStatsAggregator
        current_situation = drive_manager.get_current_situation()
        self.stats_aggregator.record_play_result(
            play_result=play_result,
            possessing_team_id=possessing_team_id,
            down=current_situation.down,
            yards_to_go=current_situation.yards_to_go,
            field_position=current_situation.field_position
        )
        
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
        from ..play_engine.game_state.field_position import FieldPosition, FieldZone
        from ..play_engine.game_state.down_situation import DownState
        
        temp_drive_position = FieldPosition(
            yard_line=drive_result.ending_field_position,
            possession_team=drive_result.possessing_team_id,
            field_zone=FieldZone.OWN_TERRITORY  # Simplified
        )
        temp_drive_down = DownState(current_down=4, yards_to_go=1, first_down_line=drive_result.ending_field_position + 1)
        
        temp_drive_manager = DriveManager(
            starting_position=temp_drive_position,
            starting_down_state=temp_drive_down,
            possessing_team_id=drive_result.possessing_team_id
        )
        temp_drive_manager.drive_ended = True
        temp_drive_manager.end_reason = drive_result.drive_outcome
        
        # Use DriveTransitionManager to handle the transition
        transition_result = self.drive_transition_manager.handle_drive_transition(
            completed_drive=temp_drive_manager,
            home_team_id=self.home_team.team_id,
            away_team_id=self.away_team.team_id
        )
        
        # Handle scoring if applicable
        if drive_result.drive_outcome == DriveEndReason.TOUCHDOWN:
            self.game_manager.scoreboard.add_score(drive_result.possessing_team_id, ScoringType.TOUCHDOWN)
            # TODO: Handle extra point/2-point conversion
            
        elif drive_result.drive_outcome == DriveEndReason.FIELD_GOAL:
            self.game_manager.scoreboard.add_score(drive_result.possessing_team_id, ScoringType.FIELD_GOAL)
            
        elif drive_result.drive_outcome == DriveEndReason.SAFETY:
            # Safety scores 2 points for the opposing team
            opposing_team_id = self.away_team.team_id if drive_result.possessing_team_id == self.home_team.team_id else self.home_team.team_id
            self.game_manager.scoreboard.add_score(opposing_team_id, ScoringType.SAFETY)
        
        # Store transition information for next drive setup
        self.next_drive_field_position = transition_result.new_starting_field_position
        self.next_drive_possessing_team_id = transition_result.new_possessing_team_id
        
    
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
        
        return (game_state.quarter >= 4 and 
                home_score == away_score and 
                game_state.phase != GamePhase.FINAL)
    
    def _run_overtime(self) -> None:
        """
        Handle overtime using modular overtime manager
        
        This method delegates to the overtime manager for rule-specific logic
        and uses clean APIs to configure the game state.
        """
        print("\n🔥 OVERTIME!")
        
        # Handle overtime periods until resolution
        while True:
            game_state = self.game_manager.get_game_state()
            
            # Check if overtime should continue
            if not self.overtime_manager.should_enter_overtime(game_state) and \
               not self.overtime_manager.should_continue_overtime(game_state):
                break
            
            # Get configuration for next overtime period
            overtime_setup = self.overtime_manager.setup_overtime_period()
            
            # Execute the overtime period
            self._execute_overtime_period(overtime_setup)
            
            # Check if game should end after this period
            game_state = self.game_manager.get_game_state()
            if not self.overtime_manager.should_continue_overtime(game_state):
                print(f"✅ Overtime ended after {self.overtime_manager.periods_completed} period(s)")
                break
            else:
                print(f"🔄 Still tied after {self.overtime_manager.periods_completed} period(s), continuing...")
    
    def _execute_overtime_period(self, overtime_setup) -> None:
        """
        Execute a single overtime period using the provided configuration
        
        Args:
            overtime_setup: OvertimeSetup object with period configuration
        """
        print(f"\n⏰ {overtime_setup.description}")
        
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
        
        # Finalize statistics
        final_score_dict = {
            self.home_team.team_id: home_score,
            self.away_team.team_id: away_score
        }
        self.stats_aggregator.finalize_game(final_score_dict)
        
        # Generate comprehensive statistics for export/serialization
        comprehensive_stats = self.stats_aggregator.get_all_statistics()

        # Get PlayerGameStats objects ready for persistence - using new conversion method
        player_stats = self.stats_aggregator.get_player_game_statistics()              # Returns List[PlayerGameStats]

        # Note: PlayerGameStats already have correct team_id, no fixing needed

        home_team_stats = self.stats_aggregator.get_team_statistics(self.home_team.team_id)  # Must return TeamStats
        away_team_stats = self.stats_aggregator.get_team_statistics(self.away_team.team_id)  # Must return TeamStats

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

        return GameResult(
            home_team=self.home_team,
            away_team=self.away_team,
            final_score=final_score_dict,
            quarter_scores=[],  # TODO: Implement quarter scoring
            drives=self.drive_results,
            total_plays=self.total_plays,
            game_duration_minutes=240,  # TODO: Calculate actual duration
            overtime_played=False,  # TODO: Implement overtime detection
            date=self.game_date,
            # ✅ FIXED: Direct object access - guaranteed objects with attributes
            player_stats=player_stats,              # List[PlayerStats] - guaranteed objects
            home_team_stats=home_team_stats,        # TeamStats - guaranteed object
            away_team_stats=away_team_stats,        # TeamStats - guaranteed object
            final_statistics=comprehensive_stats    # Dict for serialization
        )
    
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
            from ..team_management.players.player_loader import get_player_loader

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
                        print(f"🔧 Fixed {player_name}: Team {original_team_id} → Team {lookup_team_id}")
                        fixed_count += 1
                    elif lookup_team_id:
                        print(f"⚠️ Player {player_name} belongs to Team {lookup_team_id}, not in this game ({self.home_team.team_id} vs {self.away_team.team_id})")

            print(f"✅ Fixed team assignments for {fixed_count}/{len(player_stats)} players")

        except Exception as e:
            print(f"❌ Error fixing player team assignments: {e}")
            import traceback
            traceback.print_exc()