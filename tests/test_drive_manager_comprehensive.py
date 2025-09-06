"""
Comprehensive Unit Tests for DriveManager State Machine

Tests the new DriveManager architecture that acts as a focused state machine
with external play caller injection and internal statistics tracking.
"""

import pytest
from src.play_engine.game_state.drive_manager import (
    DriveManager, DriveManagerError, DriveEndReason,
    DriveSituation, DriveStats, DriveResult
)
from src.play_engine.core.play_result import PlayResult
from src.play_engine.game_state.field_position import FieldPosition, FieldZone
from src.play_engine.game_state.down_situation import DownState


class TestDriveManagerInitialization:
    """Test DriveManager initialization and setup"""
    
    def test_valid_initialization(self):
        """Test proper initialization with valid parameters"""
        starting_position = FieldPosition(
            yard_line=25, 
            possession_team="Lions",
            field_zone=FieldZone.OWN_GOAL_LINE
        )
        starting_down = DownState(
            current_down=1,
            yards_to_go=10, 
            first_down_line=35
        )
        
        drive_manager = DriveManager(
            starting_position=starting_position,
            starting_down_state=starting_down,
            possessing_team="Lions"
        )
        
        # Verify initialization
        assert drive_manager.starting_position == starting_position
        assert drive_manager.current_position == starting_position
        assert drive_manager.current_down_state == starting_down
        assert drive_manager.possessing_team == "Lions"
        assert drive_manager.drive_ended == False
        assert drive_manager.end_reason is None
        
        # Verify stats initialization
        stats = drive_manager.get_current_stats()
        assert stats.plays_run == 0
        assert stats.total_yards == 0
        assert stats.first_downs_achieved == 0
        assert stats.time_of_possession_seconds == 0.0
        
    def test_invalid_initialization_parameters(self):
        """Test that invalid parameters raise appropriate errors"""
        valid_position = FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE)
        valid_down = DownState(1, 10, 35)
        
        # Test missing starting position
        with pytest.raises(DriveManagerError, match="starting_position is required"):
            DriveManager(None, valid_down, "Lions")
            
        # Test missing down state
        with pytest.raises(DriveManagerError, match="starting_down_state is required"):
            DriveManager(valid_position, None, "Lions")
            
        # Test missing possessing team
        with pytest.raises(DriveManagerError, match="possessing_team is required"):
            DriveManager(valid_position, valid_down, "")
    
    def test_initial_drive_not_over(self):
        """Test that newly initialized drive is not over"""
        drive_manager = self._create_test_drive_manager()
        
        assert drive_manager.is_drive_over() == False
        assert drive_manager.get_drive_end_reason() is None
    
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestCurrentSituationGeneration:
    """Test generation of current drive situation for external play callers"""
    
    def test_basic_situation_generation(self):
        """Test basic situation without game context"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(45, "Lions", FieldZone.OWN_TERRITORY),
            starting_down_state=DownState(2, 7, 52),
            possessing_team="Lions"
        )
        
        situation = drive_manager.get_current_situation()
        
        assert situation.down == 2
        assert situation.yards_to_go == 7
        assert situation.field_position == 45
        assert situation.possessing_team == "Lions"
        assert situation.time_remaining is None
        assert situation.score_differential is None
        assert situation.quarter is None
        
    def test_situation_with_game_context(self):
        """Test situation generation with injected game context"""
        drive_manager = self._create_test_drive_manager()
        
        game_context = {
            'time_remaining': 180,  # 3:00
            'score_differential': -7,  # Down by 7
            'quarter': 4
        }
        
        situation = drive_manager.get_current_situation(game_context)
        
        assert situation.time_remaining == 180
        assert situation.score_differential == -7
        assert situation.quarter == 4
        
    def test_situational_flags(self):
        """Test derived situational flags"""
        # Test red zone situation
        drive_manager = DriveManager(
            starting_position=FieldPosition(85, "Lions", FieldZone.RED_ZONE),
            starting_down_state=DownState(3, 8, 93),
            possessing_team="Lions"
        )
        
        situation = drive_manager.get_current_situation()
        
        assert situation.is_red_zone == True
        assert situation.is_third_down == True
        assert situation.is_long_yardage == True
        assert situation.is_goal_to_go == True
        
        # Test short yardage situation
        drive_manager_short = DriveManager(
            starting_position=FieldPosition(50, "Lions", FieldZone.MIDFIELD),
            starting_down_state=DownState(4, 2, 52),
            possessing_team="Lions"
        )
        
        situation_short = drive_manager_short.get_current_situation()
        
        assert situation_short.is_fourth_down == True
        assert situation_short.is_short_yardage == True
        
    def test_two_minute_warning_detection(self):
        """Test two minute warning situational flag"""
        drive_manager = self._create_test_drive_manager()
        
        # Before two minute warning
        game_context = {'time_remaining': 150}  # 2:30
        situation = drive_manager.get_current_situation(game_context)
        assert situation.is_two_minute_warning == False
        
        # At two minute warning
        game_context = {'time_remaining': 120}  # 2:00
        situation = drive_manager.get_current_situation(game_context)
        assert situation.is_two_minute_warning == True
        
        # After two minute warning
        game_context = {'time_remaining': 90}   # 1:30
        situation = drive_manager.get_current_situation(game_context)
        assert situation.is_two_minute_warning == True
        
    def test_situation_for_ended_drive_raises_error(self):
        """Test that getting situation for ended drive raises error"""
        drive_manager = self._create_test_drive_manager()
        
        # End the drive
        touchdown_result = PlayResult(
            outcome="rushing_touchdown",
            yards=5,
            points=6,
            is_scoring_play=True
        )
        drive_manager.process_play_result(touchdown_result)
        
        with pytest.raises(DriveManagerError, match="Cannot get situation for ended drive"):
            drive_manager.get_current_situation()
    
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestPlayResultProcessing:
    """Test processing of external play results"""
    
    def test_successful_rush_play(self):
        """Test processing a successful running play"""
        drive_manager = self._create_test_drive_manager()
        
        play_result = PlayResult(
            outcome="rush",
            yards=5,
            time_elapsed=28.0
        )
        
        drive_manager.process_play_result(play_result)
        
        # Check field position update
        situation = drive_manager.get_current_situation()
        assert situation.field_position == 30  # 25 + 5
        assert situation.down == 2  # Advanced down
        assert situation.yards_to_go == 5  # 10 - 5
        
        # Check stats update
        stats = drive_manager.get_current_stats()
        assert stats.plays_run == 1
        assert stats.total_yards == 5
        assert stats.net_yards == 5
        assert stats.time_of_possession_seconds == 28.0
        
        # Drive should continue
        assert drive_manager.is_drive_over() == False
        
    def test_first_down_achievement(self):
        """Test first down reset logic"""
        drive_manager = self._create_test_drive_manager()
        
        play_result = PlayResult(
            outcome="pass_completion",
            yards=12,
            time_elapsed=25.0,
            achieved_first_down=True
        )
        
        drive_manager.process_play_result(play_result)
        
        situation = drive_manager.get_current_situation()
        assert situation.field_position == 37  # 25 + 12
        assert situation.down == 1  # Reset to first down
        assert situation.yards_to_go == 10  # Reset to 10 yards
        
        stats = drive_manager.get_current_stats()
        assert stats.first_downs_achieved == 1
        
    def test_negative_yards_play(self):
        """Test handling of negative yardage plays"""
        drive_manager = self._create_test_drive_manager()
        
        play_result = PlayResult(
            outcome="sack",
            yards=-7,
            time_elapsed=30.0
        )
        
        drive_manager.process_play_result(play_result)
        
        situation = drive_manager.get_current_situation()
        assert situation.field_position == 18  # 25 - 7
        assert situation.down == 2
        assert situation.yards_to_go == 17  # 10 + 7
        
        stats = drive_manager.get_current_stats()
        assert stats.total_yards == -7
        assert stats.net_yards == -7
        
    def test_play_with_penalty(self):
        """Test play with penalty effects"""
        drive_manager = self._create_test_drive_manager()
        
        play_result = PlayResult(
            outcome="rush",
            yards=3,
            time_elapsed=25.0,
            penalty_occurred=True,
            penalty_yards=5  # Beneficial penalty
        )
        
        drive_manager.process_play_result(play_result)
        
        situation = drive_manager.get_current_situation()
        assert situation.field_position == 33  # 25 + 3 + 5
        assert situation.yards_to_go == 2   # 10 - 8 (net yards)
        
        stats = drive_manager.get_current_stats()
        assert stats.total_yards == 3  # Original yards
        assert stats.net_yards == 8    # With penalty
        assert stats.penalties_committed == 1
        assert stats.penalty_yards == 5
        
    def test_process_play_for_ended_drive_raises_error(self):
        """Test that processing play for ended drive raises error"""
        drive_manager = self._create_test_drive_manager()
        
        # End the drive first
        touchdown_result = PlayResult(
            outcome="rushing_touchdown",
            yards=75,
            points=6,
            is_scoring_play=True
        )
        drive_manager.process_play_result(touchdown_result)
        
        # Try to process another play
        with pytest.raises(DriveManagerError, match="Cannot process play result for ended drive"):
            drive_manager.process_play_result(PlayResult("rush", 5, 25.0))
    
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestDriveEndingDetection:
    """Test detection of drive ending conditions"""
    
    def test_touchdown_detection(self):
        """Test drive ends on touchdown"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(95, "Lions", FieldZone.RED_ZONE),
            starting_down_state=DownState(1, 10, 100),
            possessing_team="Lions"
        )
        
        touchdown_result = PlayResult(
            outcome="rushing_touchdown",
            yards=5,
            points=6,
            time_elapsed=22.0,
            is_scoring_play=True
        )
        
        drive_manager.process_play_result(touchdown_result)
        
        # Drive should be over
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TOUCHDOWN
        
        # Check drive result
        drive_result = drive_manager.get_drive_result()
        assert drive_result.drive_ended == True
        assert drive_result.possession_should_change == True
        assert drive_result.points_scored == 6
        assert drive_result.scoring_type == "touchdown"
        
    def test_field_goal_detection(self):
        """Test drive ends on field goal"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(72, "Lions", FieldZone.OPPONENT_TERRITORY),
            starting_down_state=DownState(4, 8, 80),
            possessing_team="Lions"
        )
        
        field_goal_result = PlayResult(
            outcome="field_goal",
            yards=0,
            points=3,
            time_elapsed=15.0,
            is_scoring_play=True
        )
        
        drive_manager.process_play_result(field_goal_result)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.FIELD_GOAL
        
        drive_result = drive_manager.get_drive_result()
        assert drive_result.points_scored == 3
        assert drive_result.scoring_type == "field_goal"
        
    def test_turnover_on_downs_detection(self):
        """Test drive ends on failed 4th down conversion"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(50, "Lions", FieldZone.MIDFIELD),
            starting_down_state=DownState(4, 8, 58),
            possessing_team="Lions"
        )
        
        failed_conversion = PlayResult(
            outcome="incomplete_pass",
            yards=0,
            time_elapsed=18.0
        )
        
        drive_manager.process_play_result(failed_conversion)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TURNOVER_ON_DOWNS
        
        drive_result = drive_manager.get_drive_result()
        assert drive_result.possession_should_change == True
        assert drive_result.recommended_next_position == 50  # 100 - 50 (field flip)
        
    def test_interception_detection(self):
        """Test drive ends on interception"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(40, "Lions", FieldZone.OWN_TERRITORY),
            starting_down_state=DownState(2, 8, 48),
            possessing_team="Lions"
        )
        
        interception_result = PlayResult(
            outcome="interception",
            yards=-5,  # Return yards
            time_elapsed=20.0,
            is_turnover=True,
            turnover_type="interception"
        )
        
        drive_manager.process_play_result(interception_result)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TURNOVER_INTERCEPTION
        
        drive_result = drive_manager.get_drive_result()
        assert drive_result.possession_should_change == True
        assert drive_result.recommended_next_position == 65  # 100 - 35 (40 - 5 return)
        
    def test_fumble_detection(self):
        """Test drive ends on fumble"""
        drive_manager = self._create_test_drive_manager()
        
        fumble_result = PlayResult(
            outcome="fumble",
            yards=2,
            time_elapsed=15.0,
            is_turnover=True,
            turnover_type="fumble"
        )
        
        drive_manager.process_play_result(fumble_result)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TURNOVER_FUMBLE
        
    def test_punt_detection(self):
        """Test drive ends on punt"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(35, "Lions", FieldZone.OWN_TERRITORY),
            starting_down_state=DownState(4, 12, 47),
            possessing_team="Lions"
        )
        
        punt_result = PlayResult(
            outcome="punt",
            yards=40,
            time_elapsed=15.0,
            is_punt=True
        )
        
        drive_manager.process_play_result(punt_result)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.PUNT
        
        drive_result = drive_manager.get_drive_result()
        assert drive_result.recommended_next_position == 25  # max(20, 100 - 35 - 40)
        
    def test_safety_detection(self):
        """Test drive ends on safety"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(2, "Lions", FieldZone.OWN_END_ZONE),
            starting_down_state=DownState(1, 10, 12),
            possessing_team="Lions"
        )
        
        safety_result = PlayResult(
            outcome="safety",
            yards=-2,
            points=2,
            time_elapsed=20.0,
            is_safety=True
        )
        
        drive_manager.process_play_result(safety_result)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.SAFETY
        
        drive_result = drive_manager.get_drive_result()
        assert drive_result.points_scored == 2
        assert drive_result.scoring_type == "safety"
        assert drive_result.recommended_next_position == 20  # Free kick
        
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestStatisticsTracking:
    """Test comprehensive drive statistics tracking"""
    
    def test_basic_stats_accumulation(self):
        """Test basic drive statistics tracking"""
        drive_manager = self._create_test_drive_manager()
        
        plays = [
            PlayResult("rush", yards=3, time_elapsed=28.0),
            PlayResult("pass_completion", yards=12, time_elapsed=22.0, achieved_first_down=True),
            PlayResult("rush", yards=1, time_elapsed=25.0),
            PlayResult("pass_completion", yards=15, time_elapsed=18.0, achieved_first_down=True)
        ]
        
        for play in plays:
            drive_manager.process_play_result(play)
            
        stats = drive_manager.get_current_stats()
        assert stats.plays_run == 4
        assert stats.total_yards == 31  # 3 + 12 + 1 + 15
        assert stats.net_yards == 31
        assert stats.time_of_possession_seconds == 93.0
        assert stats.first_downs_achieved == 2
        
    def test_third_down_efficiency_tracking(self):
        """Test third down conversion efficiency"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(30, "Lions", FieldZone.OWN_TERRITORY),
            starting_down_state=DownState(3, 5, 35),  # 3rd and 5
            possessing_team="Lions"
        )
        
        # First third down - conversion
        conversion_play = PlayResult(
            outcome="pass_completion",
            yards=8,
            time_elapsed=20.0,
            achieved_first_down=True
        )
        drive_manager.process_play_result(conversion_play)
        
        # Move to another third down
        drive_manager.current_down_state = DownState(3, 7, 45)  # Simulate 3rd and 7
        
        # Second third down - failure
        failure_play = PlayResult(
            outcome="incomplete_pass",
            yards=0,
            time_elapsed=18.0
        )
        drive_manager.process_play_result(failure_play)
        
        stats = drive_manager.get_current_stats()
        assert stats.third_down_attempts == 2
        assert stats.third_down_conversions == 1
        assert stats.third_down_percentage == 50.0
        
    def test_red_zone_efficiency_tracking(self):
        """Test red zone touchdown efficiency"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(85, "Lions", FieldZone.RED_ZONE),
            starting_down_state=DownState(1, 10, 95),
            possessing_team="Lions"
        )
        
        # Play in red zone
        red_zone_play = PlayResult(
            outcome="rush",
            yards=8,
            time_elapsed=26.0
        )
        drive_manager.process_play_result(red_zone_play)
        
        # Touchdown play
        touchdown_play = PlayResult(
            outcome="rushing_touchdown",
            yards=7,
            points=6,
            time_elapsed=24.0,
            is_scoring_play=True
        )
        drive_manager.process_play_result(touchdown_play)
        
        stats = drive_manager.get_current_stats()
        assert stats.red_zone_attempts == 1
        assert stats.red_zone_touchdowns == 1
        assert stats.red_zone_efficiency == 100.0
        
    def test_penalty_tracking(self):
        """Test penalty statistics tracking"""
        drive_manager = self._create_test_drive_manager()
        
        plays_with_penalties = [
            PlayResult("rush", yards=5, time_elapsed=25.0, penalty_occurred=True, penalty_yards=-5),
            PlayResult("pass", yards=10, time_elapsed=20.0, penalty_occurred=True, penalty_yards=10),
            PlayResult("rush", yards=3, time_elapsed=22.0)  # No penalty
        ]
        
        for play in plays_with_penalties:
            drive_manager.process_play_result(play)
            
        stats = drive_manager.get_current_stats()
        assert stats.penalties_committed == 2
        assert stats.penalty_yards == 15  # 5 + 10 (absolute values)
        assert stats.total_yards == 18  # Original yards
        assert stats.net_yards == 23   # After penalty effects
        
    def test_fourth_down_tracking(self):
        """Test fourth down attempt and conversion tracking"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(50, "Lions", FieldZone.MIDFIELD),
            starting_down_state=DownState(4, 2, 52),  # 4th and 2
            possessing_team="Lions"
        )
        
        conversion_play = PlayResult(
            outcome="rush",
            yards=5,
            time_elapsed=25.0,
            achieved_first_down=True
        )
        
        drive_manager.process_play_result(conversion_play)
        
        stats = drive_manager.get_current_stats()
        assert stats.fourth_down_attempts == 1
        assert stats.fourth_down_conversions == 1
        
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestDriveResultGeneration:
    """Test comprehensive drive result generation"""
    
    def test_ongoing_drive_result(self):
        """Test drive result for ongoing drive"""
        drive_manager = self._create_test_drive_manager()
        
        # Execute a few plays
        plays = [
            PlayResult("rush", yards=5, time_elapsed=28.0),
            PlayResult("pass", yards=8, time_elapsed=20.0)
        ]
        
        for play in plays:
            drive_manager.process_play_result(play)
            
        drive_result = drive_manager.get_drive_result()
        
        assert drive_result.drive_ended == False
        assert drive_result.end_reason is None
        assert drive_result.possessing_team == "Lions"
        assert drive_result.drive_stats.plays_run == 2
        assert drive_result.drive_stats.total_yards == 13
        assert drive_result.possession_should_change == False
        assert len(drive_result.play_by_play) == 2
        
    def test_completed_drive_result(self):
        """Test drive result for completed drive"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(75, "Lions", FieldZone.OPPONENT_TERRITORY),
            starting_down_state=DownState(1, 10, 85),
            possessing_team="Lions"
        )
        
        # Execute plays leading to touchdown
        plays = [
            PlayResult("rush", yards=10, time_elapsed=25.0, achieved_first_down=True),
            PlayResult("pass", yards=15, time_elapsed=18.0, points=6, is_scoring_play=True)
        ]
        
        for play in plays:
            drive_manager.process_play_result(play)
            
        drive_result = drive_manager.get_drive_result()
        
        assert drive_result.drive_ended == True
        assert drive_result.end_reason == DriveEndReason.TOUCHDOWN
        assert drive_result.points_scored == 6
        assert drive_result.scoring_type == "touchdown"
        assert drive_result.possession_should_change == True
        assert drive_result.recommended_next_position == 25  # Kickoff
        assert drive_result.final_field_position.yard_line == 100
        
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions"""
    
    def test_goal_line_boundary_touchdown(self):
        """Test touchdown when play reaches exactly goal line"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(98, "Lions", FieldZone.RED_ZONE),
            starting_down_state=DownState(1, 10, 100),
            possessing_team="Lions"
        )
        
        goal_line_play = PlayResult(
            outcome="rush",
            yards=2,
            time_elapsed=25.0,
            points=6,
            is_scoring_play=True
        )
        
        drive_manager.process_play_result(goal_line_play)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TOUCHDOWN
        
    def test_own_end_zone_safety(self):
        """Test safety when tackled in own end zone"""
        drive_manager = DriveManager(
            starting_position=FieldPosition(1, "Lions", FieldZone.OWN_END_ZONE),
            starting_down_state=DownState(1, 10, 11),
            possessing_team="Lions"
        )
        
        safety_play = PlayResult(
            outcome="safety",
            yards=-1,
            time_elapsed=20.0,
            is_safety=True,
            points=2
        )
        
        drive_manager.process_play_result(safety_play)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.SAFETY
        
    def test_large_gain_touchdown(self):
        """Test touchdown on very long play"""
        drive_manager = self._create_test_drive_manager()
        
        long_touchdown = PlayResult(
            outcome="passing_touchdown",
            yards=75,  # 25 + 75 = 100
            time_elapsed=30.0,
            points=6,
            is_scoring_play=True
        )
        
        drive_manager.process_play_result(long_touchdown)
        
        assert drive_manager.is_drive_over() == True
        assert drive_manager.get_drive_end_reason() == DriveEndReason.TOUCHDOWN
        
    def test_multiple_penalty_effects(self):
        """Test multiple penalties in sequence"""
        drive_manager = self._create_test_drive_manager()
        
        plays = [
            PlayResult("rush", yards=5, time_elapsed=25.0, penalty_occurred=True, penalty_yards=-10),  # Holding
            PlayResult("pass", yards=15, time_elapsed=20.0, penalty_occurred=True, penalty_yards=5),   # Defensive penalty
            PlayResult("rush", yards=3, time_elapsed=22.0)
        ]
        
        for play in plays:
            drive_manager.process_play_result(play)
            
        stats = drive_manager.get_current_stats()
        assert stats.penalties_committed == 2
        assert stats.penalty_yards == 15  # 10 + 5 (absolute)
        assert stats.total_yards == 23    # 5 + 15 + 3
        assert stats.net_yards == 18      # 23 + (-10) + 5 = 18
        
    def _create_test_drive_manager(self):
        """Helper method to create standard test drive manager"""
        return DriveManager(
            starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
            starting_down_state=DownState(1, 10, 35),
            possessing_team="Lions"
        )


# Test utilities and fixtures
@pytest.fixture
def standard_drive_manager():
    """Pytest fixture for standard test drive manager"""
    return DriveManager(
        starting_position=FieldPosition(25, "Lions", FieldZone.OWN_GOAL_LINE),
        starting_down_state=DownState(1, 10, 35),
        possessing_team="Lions"
    )


@pytest.fixture
def red_zone_drive_manager():
    """Pytest fixture for red zone drive manager"""
    return DriveManager(
        starting_position=FieldPosition(85, "Lions", FieldZone.RED_ZONE),
        starting_down_state=DownState(1, 10, 95),
        possessing_team="Lions"
    )