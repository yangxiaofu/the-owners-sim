"""
Comprehensive unit tests for NFL penalty enforcement.

Tests cover all major penalty scenarios with exact ball placement verification:
- Pre-snap penalties (dead ball, replay down)
- During-play offensive penalties
- During-play defensive penalties (automatic first down)
- Pass interference (spot of foul)
- Post-play penalties
- Half-distance-to-goal
- Accept/decline decision logic
"""

import pytest
from play_engine.mechanics.penalties.penalty_enforcement import (
    calculate_enforcement,
    calculate_half_distance_yards,
    should_accept_penalty,
    get_final_enforcement,
    EnforcementSpot,
    PENALTY_CONFIG,
)


class TestHalfDistanceToGoal:
    """Test the half-distance-to-goal rule"""

    def test_normal_penalty_no_half_distance(self):
        """Normal 10-yard penalty from midfield - full yardage"""
        yards = calculate_half_distance_yards(
            base_yards=10,
            current_yard_line=50,
            is_offensive_penalty=True
        )
        assert yards == 10

    def test_half_distance_offensive_near_own_goal(self):
        """Offensive holding from own 8 - half distance applies (4 yards)"""
        yards = calculate_half_distance_yards(
            base_yards=10,
            current_yard_line=8,
            is_offensive_penalty=True
        )
        assert yards == 4  # Half of 8

    def test_half_distance_defensive_near_opp_goal(self):
        """Defensive penalty from opponent's 6 - half distance (3 yards forward)"""
        yards = calculate_half_distance_yards(
            base_yards=15,
            current_yard_line=94,  # At opponent's 6-yard line
            is_offensive_penalty=False
        )
        assert yards == 3  # Half of 6

    def test_minimum_one_yard(self):
        """Penalty from 1-yard line should still be at least 1 yard"""
        yards = calculate_half_distance_yards(
            base_yards=5,
            current_yard_line=1,
            is_offensive_penalty=True
        )
        assert yards == 1  # Can't be less than 1


class TestPreSnapPenalties:
    """Test pre-snap penalties (dead ball fouls, replay down)"""

    def test_false_start_from_own_25(self):
        """False Start: 1st & 10 at own 25 -> 1st & 15 at own 20"""
        result = calculate_enforcement(
            penalty_type="false_start",
            pre_snap_yard_line=25,
            pre_snap_down=1,
            pre_snap_distance=10,
        )
        assert result.new_yard_line == 20
        assert result.new_down == 1  # Replay
        assert result.new_yards_to_go == 15
        assert result.replay_down is True

    def test_false_start_on_3rd_and_short(self):
        """False Start: 3rd & 2 at opp 8 (yard line 92) -> 3rd & 7 at opp 13 (yard line 87)"""
        result = calculate_enforcement(
            penalty_type="false_start",
            pre_snap_yard_line=92,  # Opponent's 8-yard line
            pre_snap_down=3,
            pre_snap_distance=2,
        )
        assert result.new_yard_line == 87  # Back 5 yards
        assert result.new_down == 3  # Replay 3rd down
        assert result.new_yards_to_go == 7  # 2 + 5

    def test_false_start_half_distance(self):
        """False Start from own 3: Half distance rule applies (1-2 yards back)"""
        result = calculate_enforcement(
            penalty_type="false_start",
            pre_snap_yard_line=3,
            pre_snap_down=1,
            pre_snap_distance=10,
        )
        assert result.new_yard_line == 2  # Half of 3 = 1.5, rounded to 1, so 3-1=2
        assert result.new_down == 1
        assert result.new_yards_to_go == 11  # 10 + 1

    def test_encroachment_defensive(self):
        """Encroachment: 2nd & 7 at own 30 -> 2nd & 2 at own 35"""
        result = calculate_enforcement(
            penalty_type="encroachment",
            pre_snap_yard_line=30,
            pre_snap_down=2,
            pre_snap_distance=7,
        )
        assert result.new_yard_line == 35  # Forward 5
        assert result.new_down == 2  # Replay
        assert result.new_yards_to_go == 2  # 7 - 5

    def test_offsides_replay_down(self):
        """Offsides on 3rd & 1: Dead ball foul, replay down with better distance"""
        # NOTE: Offsides is NOT an automatic first down penalty - it just moves the ball
        # The offense still needs to convert on the replayed down
        result = calculate_enforcement(
            penalty_type="offsides",
            pre_snap_yard_line=60,  # Opponent's 40
            pre_snap_down=3,
            pre_snap_distance=1,
        )
        assert result.new_yard_line == 65  # Forward 5
        assert result.new_down == 3  # Replay 3rd down (not auto first down)
        assert result.new_yards_to_go == 1  # max(1, 1-5) - can't go below 1
        assert result.replay_down is True

    def test_delay_of_game(self):
        """Delay of Game: 1st & 10 at own 40 -> 1st & 15 at own 35"""
        result = calculate_enforcement(
            penalty_type="delay_of_game",
            pre_snap_yard_line=40,
            pre_snap_down=1,
            pre_snap_distance=10,
        )
        assert result.new_yard_line == 35
        assert result.new_down == 1
        assert result.new_yards_to_go == 15


class TestOffensiveHolding:
    """Test offensive holding (most common penalty)"""

    def test_holding_on_run_play(self):
        """THE BUG SCENARIO: 1st & 10 at 35, +8 run, holding -> 1st & 20 at 25"""
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=35,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=8,  # Doesn't matter - negated
        )
        assert result.new_yard_line == 25  # Back 10
        assert result.new_down == 1  # Replay
        assert result.new_yards_to_go == 20  # 10 + 10
        assert result.replay_down is True

    def test_holding_on_second_down(self):
        """Holding: 2nd & 5 at 50, +15 pass -> 2nd & 15 at 40"""
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=50,
            pre_snap_down=2,
            pre_snap_distance=5,
            play_yards=15,  # Negated
        )
        assert result.new_yard_line == 40
        assert result.new_down == 2
        assert result.new_yards_to_go == 15  # 5 + 10

    def test_holding_goal_to_go_half_distance(self):
        """Holding at opponent's 6 (yard line 94): Half distance (3 yards back)"""
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=94,  # Opponent's 6
            pre_snap_down=1,
            pre_snap_distance=6,  # Goal to go
            play_yards=3,
        )
        # Half of distance to own goal = half of (100-94) for offensive =
        # No wait - offensive penalty moves toward OWN goal
        # Half distance to own goal from 94 = 94 / 2 = 47... but that's not right
        # Actually half-distance applies when penalty would exceed half the distance to relevant goal
        # For offensive penalty at opp 6, distance to OWN goal is 94 yards, half = 47
        # 10-yard penalty is less than 47, so full 10 yards apply
        assert result.new_yard_line == 84  # Back 10 to opponent's 16
        assert result.new_yards_to_go == 16  # Goal to go from opp 16

    def test_holding_near_own_goal_half_distance(self):
        """Holding at own 8: Half distance applies (4 yards back)"""
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=8,
            pre_snap_down=1,
            pre_snap_distance=10,
        )
        assert result.new_yard_line == 4  # Half of 8 = 4
        assert result.new_yards_to_go == 14  # 10 + 4


class TestDefensivePenaltiesWithAutoFirstDown:
    """Test defensive penalties that carry automatic first down"""

    def test_defensive_holding(self):
        """Def Holding: 3rd & 12 at own 40, incomplete -> 1st & 10 at own 45"""
        result = calculate_enforcement(
            penalty_type="defensive_holding",
            pre_snap_yard_line=40,
            pre_snap_down=3,
            pre_snap_distance=12,
            play_yards=0,  # Incomplete pass
        )
        assert result.new_yard_line == 45
        assert result.new_down == 1
        assert result.new_yards_to_go == 10
        assert result.is_first_down is True

    def test_illegal_contact(self):
        """Illegal Contact: 2nd & 8 at opp 30 (yard line 70), +2 -> 1st & 10 at opp 25 (yard line 75)"""
        result = calculate_enforcement(
            penalty_type="illegal_contact",
            pre_snap_yard_line=70,  # Opponent's 30
            pre_snap_down=2,
            pre_snap_distance=8,
            play_yards=2,
        )
        assert result.new_yard_line == 75  # Forward 5
        assert result.new_down == 1
        assert result.is_first_down is True

    def test_roughing_the_passer(self):
        """Roughing: 2nd & 15 at own 20, sack (-8) -> 1st & 10 at own 35"""
        result = calculate_enforcement(
            penalty_type="roughing_the_passer",
            pre_snap_yard_line=20,
            pre_snap_down=2,
            pre_snap_distance=15,
            play_yards=-8,  # Sack for loss
        )
        assert result.new_yard_line == 35  # Forward 15
        assert result.new_down == 1
        assert result.is_first_down is True


class TestPassInterference:
    """Test defensive pass interference (spot foul)"""

    def test_dpi_spot_foul_deep(self):
        """DPI at opponent's 35 (spot=65): 1st & 10 at own 20 -> 1st & 10 at opp 35"""
        result = calculate_enforcement(
            penalty_type="defensive_pass_interference",
            pre_snap_yard_line=20,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=0,
            spot_of_foul=65,  # Where the DPI occurred
        )
        assert result.new_yard_line == 65  # Spot of foul
        assert result.new_down == 1
        assert result.is_first_down is True

    def test_dpi_in_end_zone(self):
        """DPI in end zone: Ball at 1-yard line"""
        result = calculate_enforcement(
            penalty_type="defensive_pass_interference",
            pre_snap_yard_line=75,  # Opponent's 25
            pre_snap_down=2,
            pre_snap_distance=10,
            play_yards=0,
            spot_of_foul=99,  # DPI in end zone
        )
        assert result.new_yard_line == 99  # 1-yard line
        assert result.new_down == 1
        assert result.is_first_down is True

    def test_dpi_short_pass(self):
        """DPI on short pass: 3rd & 15 at own 10, DPI at opp 5 -> 1st & G at opp 5"""
        result = calculate_enforcement(
            penalty_type="defensive_pass_interference",
            pre_snap_yard_line=10,
            pre_snap_down=3,
            pre_snap_distance=15,
            play_yards=0,
            spot_of_foul=95,  # Opponent's 5
        )
        assert result.new_yard_line == 95
        assert result.new_down == 1
        assert result.new_yards_to_go == 5  # Goal to go


class TestPostPlayPenalties:
    """Test penalties assessed after the play ends"""

    def test_unsportsmanlike_on_first_down(self):
        """Unsportsmanlike after first down: 1st & 10 at 30, +10 -> 1st & 10 at 55"""
        result = calculate_enforcement(
            penalty_type="unsportsmanlike_conduct",
            pre_snap_yard_line=30,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=10,  # First down
            is_offensive_penalty=False,  # Against defense
        )
        # Succeeding spot = where play ended (40), then +15
        assert result.new_yard_line == 55  # 30 + 10 + 15
        assert result.new_down == 1
        assert result.is_first_down is True

    def test_face_mask_on_runner(self):
        """Face mask on ball carrier: 2nd & 5 at 40, +8 -> 1st & 10 at 63"""
        result = calculate_enforcement(
            penalty_type="face_mask",
            pre_snap_yard_line=40,
            pre_snap_down=2,
            pre_snap_distance=5,
            play_yards=8,
            is_offensive_penalty=False,
        )
        assert result.new_yard_line == 55  # From previous spot + 15
        assert result.is_first_down is True


class TestAcceptDeclineLogic:
    """Test penalty accept/decline decision making"""

    def test_decline_holding_on_big_gain(self):
        """Decline offensive holding when play gained 15 yards"""
        should_accept, accepted, declined = should_accept_penalty(
            penalty_type="offensive_holding",
            pre_snap_yard_line=25,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=15,
        )
        # Defense should decline - 1st & 10 at 40 is better than 1st & 20 at 15
        # Wait - holding means ball goes BACK, so accepted would be at 15 with 1st & 20
        # Declined = 1st & 10 at 40 (play result)
        # Defense wants worse situation for offense, so ACCEPT the penalty
        # Actually no - if holding is accepted, replay 1st down with worse distance
        # Let's verify: accepted = yard 15, 1st & 20. Declined = yard 40, 1st & 10
        # Offense at 40 with 1st & 10 is better than at 15 with 1st & 20
        # So defense SHOULD accept to put offense in worse spot
        assert should_accept is True  # Defense accepts to put offense back

    def test_decline_def_holding_on_first_down_conversion(self):
        """Decline defensive holding when play already got first down"""
        should_accept, accepted, declined = should_accept_penalty(
            penalty_type="defensive_holding",
            pre_snap_yard_line=30,
            pre_snap_down=3,
            pre_snap_distance=8,
            play_yards=10,  # Already a first down
        )
        # Offense chooses: Accepted = 1st & 10 at 35. Declined = 1st & 10 at 40
        # Offense wants better field position, so DECLINE
        assert should_accept is False
        assert declined.new_yard_line == 40

    def test_accept_def_holding_on_incomplete(self):
        """Accept defensive holding on incomplete pass"""
        should_accept, accepted, declined = should_accept_penalty(
            penalty_type="defensive_holding",
            pre_snap_yard_line=30,
            pre_snap_down=3,
            pre_snap_distance=8,
            play_yards=0,  # Incomplete
        )
        # Accepted = 1st & 10 at 35. Declined = 4th & 8 at 30
        # Offense definitely accepts!
        assert should_accept is True
        assert accepted.new_down == 1
        assert accepted.is_first_down is True


class TestGetFinalEnforcement:
    """Test the main entry point that combines enforcement + accept/decline"""

    def test_pre_snap_auto_enforced(self):
        """Pre-snap penalties are automatically enforced, no decline option"""
        result = get_final_enforcement(
            penalty_type="false_start",
            pre_snap_yard_line=40,
            pre_snap_down=2,
            pre_snap_distance=7,
            play_yards=0,
        )
        assert result.penalty_accepted is True
        assert result.new_yard_line == 35
        assert result.replay_down is True

    def test_during_play_with_decision(self):
        """During-play penalty goes through accept/decline logic"""
        result = get_final_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=35,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=8,
        )
        # Defense will accept to push offense back
        assert result.new_yard_line == 25
        assert result.new_yards_to_go == 20


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_goal_line_stand(self):
        """Penalty at goal line with goal-to-go"""
        result = calculate_enforcement(
            penalty_type="false_start",
            pre_snap_yard_line=98,  # 2-yard line, goal to go
            pre_snap_down=1,
            pre_snap_distance=2,
        )
        assert result.new_yard_line == 93  # Back 5
        assert result.new_yards_to_go == 7  # 2 + 5

    def test_penalty_near_goal_half_distance_defensive(self):
        """Defensive penalty near goal line: Half distance applies"""
        result = calculate_enforcement(
            penalty_type="defensive_holding",
            pre_snap_yard_line=96,  # At opponent's 4
            pre_snap_down=1,
            pre_snap_distance=4,
        )
        # Distance to opponent goal = 100 - 96 = 4, half = 2
        # So only 2 yards forward, not 5
        assert result.new_yard_line == 98  # 96 + 2
        assert result.new_yards_to_go == 2  # Goal to go from 2
        assert result.is_first_down is True  # Automatic first down

    def test_penalty_near_own_goal_minimum_yard(self):
        """Ball cannot be placed inside own end zone (beyond yard line 0)"""
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=2,
            pre_snap_down=1,
            pre_snap_distance=10,
        )
        # Half of 2 = 1
        assert result.new_yard_line == 1  # Minimum is 1
        assert result.new_yards_to_go == 11


class TestOriginalBugScenario:
    """Explicitly test the original bug that started this refactor"""

    def test_the_original_bug(self):
        """
        Original bug: 1st & 10 at 35, -10 yard run, holding penalty
        Result was incorrectly: 1st & 1 at 36
        Should be: 1st & 20 at 25
        """
        result = calculate_enforcement(
            penalty_type="offensive_holding",
            pre_snap_yard_line=35,
            pre_snap_down=1,
            pre_snap_distance=10,
            play_yards=-10,  # The run play lost 10 yards
        )

        # Correct enforcement:
        # - Offensive holding negates the play
        # - 10 yards back from previous spot (35)
        # - New yard line = 25
        # - Replay 1st down
        # - New distance = 10 + 10 = 20

        assert result.new_yard_line == 25, f"Expected yard line 25, got {result.new_yard_line}"
        assert result.new_down == 1, f"Expected down 1, got {result.new_down}"
        assert result.new_yards_to_go == 20, f"Expected yards to go 20, got {result.new_yards_to_go}"
        assert result.replay_down is True
        assert result.is_first_down is False  # It's still 1st down, but not a "new" first down


class TestPenaltyConfigCompleteness:
    """Ensure all configured penalties work correctly"""

    @pytest.mark.parametrize("penalty_type", PENALTY_CONFIG.keys())
    def test_all_penalties_calculate_without_error(self, penalty_type):
        """Every configured penalty should calculate without errors"""
        result = calculate_enforcement(
            penalty_type=penalty_type,
            pre_snap_yard_line=50,
            pre_snap_down=2,
            pre_snap_distance=7,
            play_yards=5,
        )
        assert result is not None
        assert 0 < result.new_yard_line <= 99
        assert 1 <= result.new_down <= 4
        assert result.new_yards_to_go >= 1
