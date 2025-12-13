"""
Test penalty yardage calculation to ensure no double-counting

This test validates the fix for the penalty double-counting bug where
penalty yards were incorrectly added to play yards instead of replacing them.
"""

import pytest
from unittest.mock import Mock, patch

from play_engine.mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext
from play_engine.mechanics.penalties.penalty_data_structures import PenaltyInstance


class TestPenaltyYardageCalculation:
    """Test that penalty yardage is calculated correctly according to NFL rules"""

    def setup_method(self):
        """Set up test fixtures"""
        self.penalty_engine = PenaltyEngine()
        self.context = PlayContext(
            quarter=1,
            time_remaining="10:00",
            down=1,
            distance=10,
            field_position=50,
            score_differential=0,
            is_home_team=True,
            play_type="run"
        )

    def test_negated_play_uses_only_penalty_yards(self):
        """Test that pre-snap penalties (negated_play=True) use only penalty yards"""
        # Create a penalty instance that negates the play (e.g., false start)
        penalty = PenaltyInstance(
            penalty_type="false_start",
            penalized_player_name="Test Player",
            penalized_player_number=75,
            penalized_player_position="left_tackle",
            team_penalized="home",
            yards_assessed=-5,  # 5 yard penalty against offense
            automatic_first_down=False,
            automatic_loss_of_down=False,
            negated_play=True,  # Play is negated
            quarter=1,
            time_remaining="10:00",
            down=1,
            distance=10,
            field_position=50,
            score_differential=0
        )

        original_play_yards = 7  # Play gained 7 yards before penalty

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Should use ONLY penalty yards, not play yards + penalty yards
        assert result.modified_yards == -5, "Negated play should use only penalty yards"
        assert result.modified_yards != 2, "Should NOT add play yards to penalty yards (7 + (-5) = 2)"
        assert penalty.final_play_result == -5

    def test_accepted_defensive_penalty_uses_only_penalty_yards(self):
        """Test that accepted defensive penalties use only penalty yards from LOS"""
        # Create a defensive penalty that doesn't auto-negate (e.g., face mask)
        penalty = PenaltyInstance(
            penalty_type="face_mask",
            penalized_player_name="Test Player",
            penalized_player_number=52,
            penalized_player_position="linebacker",
            team_penalized="away",  # Defensive penalty
            yards_assessed=15,  # 15 yard penalty benefits offense
            automatic_first_down=True,
            automatic_loss_of_down=False,
            negated_play=False,  # Play is NOT auto-negated, team can choose
            quarter=1,
            time_remaining="10:00",
            down=1,
            distance=10,
            field_position=50,
            score_differential=0
        )

        original_play_yards = 3  # Play only gained 3 yards

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Penalty (15 yards) is better than play result (3 yards), so should accept
        assert result.modified_yards == 15, "Should accept penalty (15 yards) over play result (3 yards)"
        assert result.modified_yards != 18, "Should NOT double-count (3 + 15 = 18)"
        assert penalty.penalty_accepted == True, "Penalty should be marked as accepted"
        assert penalty.final_play_result == 15

    def test_declined_defensive_penalty_uses_play_yards(self):
        """Test that declined defensive penalties use the play result"""
        # Create a defensive penalty where play result is better
        penalty = PenaltyInstance(
            penalty_type="illegal_contact",
            penalized_player_name="Test Player",
            penalized_player_number=24,
            penalized_player_position="cornerback",
            team_penalized="away",  # Defensive penalty
            yards_assessed=5,  # Only 5 yard penalty
            automatic_first_down=True,
            automatic_loss_of_down=False,
            negated_play=False,  # Play is NOT auto-negated
            quarter=1,
            time_remaining="10:00",
            down=1,
            distance=10,
            field_position=50,
            score_differential=0
        )

        original_play_yards = 25  # Big play! 25 yard gain

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Play result (25 yards) is better than penalty (5 yards), so should decline
        assert result.modified_yards == 25, "Should decline penalty and use play result (25 yards)"
        assert result.modified_yards != 30, "Should NOT double-count (25 + 5 = 30)"
        assert penalty.penalty_accepted == False, "Penalty should be marked as declined"
        assert penalty.final_play_result == 25

    def test_offensive_holding_negates_big_play(self):
        """Test that offensive holding correctly negates a big play"""
        penalty = PenaltyInstance(
            penalty_type="offensive_holding",
            penalized_player_name="Test Player",
            penalized_player_number=73,
            penalized_player_position="right_guard",
            team_penalized="home",
            yards_assessed=-10,  # 10 yard penalty
            automatic_first_down=False,
            automatic_loss_of_down=False,
            negated_play=True,  # Holding negates the play
            quarter=1,
            time_remaining="10:00",
            down=2,
            distance=5,
            field_position=50,
            score_differential=0,
            original_play_result=35  # Would have been a touchdown!
        )

        original_play_yards = 35  # Big gain before penalty

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Should completely negate the 35 yard gain and only apply -10 yard penalty
        assert result.modified_yards == -10, "Holding should negate big play, use only penalty yards"
        assert result.modified_yards != 25, "Should NOT add 35 + (-10) = 25"
        assert penalty.final_play_result == -10

    def test_unnecessary_roughness_choice_accept(self):
        """Test unnecessary roughness penalty that should be accepted"""
        penalty = PenaltyInstance(
            penalty_type="unnecessary_roughness",
            penalized_player_name="Test Player",
            penalized_player_number=99,
            penalized_player_position="defensive_end",
            team_penalized="away",
            yards_assessed=15,  # 15 yard penalty
            automatic_first_down=True,
            automatic_loss_of_down=False,
            negated_play=False,  # Not auto-negated
            quarter=4,
            time_remaining="2:00",
            down=3,
            distance=12,
            field_position=75,  # At opponent's 25-yard line
            score_differential=-3
        )

        original_play_yards = -2  # Lost 2 yards on the play

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Should accept penalty over loss of 2 yards
        assert penalty.penalty_accepted == True
        assert result.automatic_first_down == True, "Should get automatic first down"

        # Verify enforcement result has correct ball placement
        # From yard 75 (opp 25), 15-yard penalty, but half-distance applies
        # Distance to goal = 25, half = 12, so only 12 yards enforced
        enforcement = result.enforcement_result
        assert enforcement is not None, "Should have enforcement result"
        assert enforcement.new_yard_line == 87, "Ball should be at opponent's 13 (yard 87)"
        assert enforcement.new_down == 1, "Should be 1st down"
        assert enforcement.is_first_down == True, "Should be a first down"

    def test_distance_change_only_when_penalty_accepted(self):
        """Test that distance changes only apply when penalty is accepted"""
        # Declined penalty scenario
        penalty = PenaltyInstance(
            penalty_type="illegal_contact",
            penalized_player_name="Test Player",
            penalized_player_number=21,
            penalized_player_position="safety",
            team_penalized="away",
            yards_assessed=5,
            automatic_first_down=True,
            automatic_loss_of_down=False,
            negated_play=False,
            quarter=1,
            time_remaining="10:00",
            down=2,
            distance=8,
            field_position=50,
            score_differential=0
        )

        original_play_yards = 20  # Big gain

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Penalty should be declined
        assert penalty.penalty_accepted == False
        # Distance change should be 0 since penalty was declined
        assert result.distance_change == 0, "Distance should not change when penalty is declined"

    def test_distance_change_when_penalty_accepted(self):
        """Test that penalty acceptance results in correct enforcement"""
        # Accepted penalty scenario
        penalty = PenaltyInstance(
            penalty_type="unnecessary_roughness",
            penalized_player_name="Test Player",
            penalized_player_number=55,
            penalized_player_position="linebacker",
            team_penalized="away",
            yards_assessed=15,
            automatic_first_down=True,
            automatic_loss_of_down=False,
            negated_play=False,
            quarter=1,
            time_remaining="10:00",
            down=3,
            distance=15,
            field_position=50,
            score_differential=0
        )

        original_play_yards = 2  # Short gain

        result = self.penalty_engine._apply_penalty_effects(penalty, original_play_yards)

        # Penalty should be accepted
        assert penalty.penalty_accepted == True

        # Verify enforcement result - the new correct way to check ball placement
        enforcement = result.enforcement_result
        assert enforcement is not None, "Should have enforcement result"
        assert enforcement.new_yard_line == 65, "Ball should be at yard 65 (50 + 15)"
        assert enforcement.new_down == 1, "Should be 1st down"
        assert enforcement.new_yards_to_go == 10, "Should be 1st & 10"
        assert enforcement.is_first_down == True, "Should be a first down"
