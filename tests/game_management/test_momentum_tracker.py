"""Tests for MomentumTracker - game momentum tracking system."""

import pytest
from src.game_management.momentum_tracker import MomentumTracker


class TestMomentumTrackerInitialization:
    """Test momentum tracker initialization."""

    def test_momentum_initializes_to_zero(self):
        """Test momentum starts at 0.0 for both teams."""
        tracker = MomentumTracker()

        assert tracker.home_momentum == 0.0
        assert tracker.away_momentum == 0.0

    def test_decay_rate_is_10_percent(self):
        """Test decay rate is set to 10%."""
        tracker = MomentumTracker()

        assert tracker.decay_rate == 0.10


class TestMomentumEvents:
    """Test momentum event handling."""

    def test_touchdown_adds_8_momentum(self):
        """Test touchdown adds +8 momentum."""
        tracker = MomentumTracker()

        tracker.add_event('home', 'touchdown')

        assert tracker.home_momentum == 8.0
        assert tracker.away_momentum == 0.0

    def test_turnover_adds_10_to_defense_minus_10_to_offense(self):
        """Test turnover adds +10 to defense, -10 to offense."""
        tracker = MomentumTracker()

        # Offense (home) loses turnover, defense (away) gains
        tracker.add_event('away', 'turnover_gain')
        tracker.add_event('home', 'turnover_loss')

        assert tracker.home_momentum == -10.0
        assert tracker.away_momentum == 10.0

    def test_big_play_adds_5_momentum(self):
        """Test big play (20+ yards) adds +5 momentum."""
        tracker = MomentumTracker()

        tracker.add_event('home', 'big_play_gain')

        assert tracker.home_momentum == 5.0

    def test_sack_adds_3_momentum_to_defense(self):
        """Test sack adds +3 momentum to defense."""
        tracker = MomentumTracker()

        tracker.add_event('away', 'sack')

        assert tracker.away_momentum == 3.0

    def test_field_goal_made_adds_3_momentum(self):
        """Test field goal made adds +3 momentum."""
        tracker = MomentumTracker()

        tracker.add_event('home', 'field_goal_made')

        assert tracker.home_momentum == 3.0

    def test_field_goal_blocked_adds_8_momentum_to_defense(self):
        """Test field goal blocked adds +8 momentum to defense."""
        tracker = MomentumTracker()

        tracker.add_event('away', 'field_goal_blocked')

        assert tracker.away_momentum == 8.0


class TestMomentumDecay:
    """Test momentum decay mechanism."""

    def test_momentum_decay_10_percent_per_play(self):
        """Test momentum decays by 10% after each play."""
        tracker = MomentumTracker()

        # Start with touchdown (+8)
        tracker.add_event('home', 'touchdown')
        assert tracker.home_momentum == 8.0

        # After 1 decay: 8.0 * 0.9 = 7.2
        tracker.decay()
        assert abs(tracker.home_momentum - 7.2) < 0.01

        # After 2 decays: 7.2 * 0.9 = 6.48
        tracker.decay()
        assert abs(tracker.home_momentum - 6.48) < 0.01

    def test_momentum_decays_for_both_teams(self):
        """Test decay applies to both teams independently."""
        tracker = MomentumTracker()

        tracker.add_event('home', 'touchdown')  # +8
        tracker.add_event('away', 'field_goal_made')  # +3

        tracker.decay()

        assert abs(tracker.home_momentum - 7.2) < 0.01  # 8.0 * 0.9
        assert abs(tracker.away_momentum - 2.7) < 0.01  # 3.0 * 0.9

    def test_momentum_zeros_out_when_very_small(self):
        """Test momentum zeros out when < 0.1."""
        tracker = MomentumTracker()

        tracker.home_momentum = 0.09
        tracker.decay()

        assert tracker.home_momentum == 0.0


class TestMomentumClamping:
    """Test momentum clamping to valid range."""

    def test_momentum_clamped_to_plus_20_max(self):
        """Test momentum clamped at +20 maximum."""
        tracker = MomentumTracker()

        # Add multiple touchdowns to exceed max
        for _ in range(5):
            tracker.add_event('home', 'touchdown')  # 5 * 8 = 40

        assert tracker.home_momentum == 20.0  # Clamped to max

    def test_momentum_clamped_to_minus_20_min(self):
        """Test momentum clamped at -20 minimum."""
        tracker = MomentumTracker()

        # Add multiple turnover losses to go below min
        for _ in range(5):
            tracker.add_event('home', 'turnover_loss')  # 5 * -10 = -50

        assert tracker.home_momentum == -20.0  # Clamped to min


class TestMomentumModifiers:
    """Test momentum modifier calculations."""

    def test_performance_modifier_at_max_momentum(self):
        """Test performance modifier at +20 momentum is 1.05."""
        tracker = MomentumTracker()

        tracker.home_momentum = 20.0
        modifier = tracker.get_momentum_modifier('home')

        # Formula: 1.0 + (20 / 400) = 1.05
        assert abs(modifier - 1.05) < 0.001

    def test_performance_modifier_at_min_momentum(self):
        """Test performance modifier at -20 momentum is 0.95."""
        tracker = MomentumTracker()

        tracker.home_momentum = -20.0
        modifier = tracker.get_momentum_modifier('home')

        # Formula: 1.0 + (-20 / 400) = 0.95
        assert abs(modifier - 0.95) < 0.001

    def test_performance_modifier_at_zero_momentum(self):
        """Test performance modifier at 0 momentum is 1.0."""
        tracker = MomentumTracker()

        modifier = tracker.get_momentum_modifier('home')

        assert modifier == 1.0

    def test_aggression_modifier_at_max_momentum(self):
        """Test aggression modifier at +20 momentum is 1.15."""
        tracker = MomentumTracker()

        tracker.home_momentum = 20.0
        modifier = tracker.get_aggression_modifier('home')

        # Formula: 1.0 + (20 / 133.33) = 1.15
        assert abs(modifier - 1.15) < 0.01

    def test_aggression_modifier_at_min_momentum(self):
        """Test aggression modifier at -20 momentum is 0.85."""
        tracker = MomentumTracker()

        tracker.home_momentum = -20.0
        modifier = tracker.get_aggression_modifier('home')

        # Formula: 1.0 + (-20 / 133.33) = 0.85
        assert abs(modifier - 0.85) < 0.01


class TestMomentumSummary:
    """Test momentum summary generation."""

    def test_get_summary_returns_correct_format(self):
        """Test get_summary returns all required fields."""
        tracker = MomentumTracker()

        tracker.add_event('home', 'touchdown')  # +8
        summary = tracker.get_summary()

        assert 'home_momentum' in summary
        assert 'away_momentum' in summary
        assert 'home_modifier' in summary
        assert 'away_modifier' in summary
        assert 'home_level' in summary
        assert 'away_level' in summary
        assert 'home_aggression' in summary
        assert 'away_aggression' in summary

        assert summary['home_momentum'] == 8.0
        assert summary['away_momentum'] == 0.0

    def test_get_momentum_level_hot_at_plus_15(self):
        """Test momentum level 'Hot' at +15."""
        tracker = MomentumTracker()

        tracker.home_momentum = 15.0
        level = tracker.get_momentum_level('home')

        assert level == 'Hot'

    def test_get_momentum_level_warm_at_plus_8(self):
        """Test momentum level 'Warm' at +8."""
        tracker = MomentumTracker()

        tracker.home_momentum = 8.0
        level = tracker.get_momentum_level('home')

        assert level == 'Warm'

    def test_get_momentum_level_neutral_at_zero(self):
        """Test momentum level 'Neutral' at 0."""
        tracker = MomentumTracker()

        level = tracker.get_momentum_level('home')

        assert level == 'Neutral'

    def test_get_momentum_level_cool_at_minus_8(self):
        """Test momentum level 'Cool' at -8."""
        tracker = MomentumTracker()

        tracker.home_momentum = -8.0
        level = tracker.get_momentum_level('home')

        assert level == 'Cool'

    def test_get_momentum_level_cold_at_minus_15(self):
        """Test momentum level 'Cold' at -15."""
        tracker = MomentumTracker()

        tracker.home_momentum = -15.0
        level = tracker.get_momentum_level('home')

        assert level == 'Cold'


class TestRealisticGameScenarios:
    """Test realistic game scenarios."""

    def test_back_and_forth_scoring(self):
        """Test momentum in a back-and-forth scoring game."""
        tracker = MomentumTracker()

        # Home scores TD
        tracker.add_event('home', 'touchdown')
        assert tracker.home_momentum == 8.0

        # 5 plays decay
        for _ in range(5):
            tracker.decay()
        # 8.0 * (0.9^5) = 4.72
        assert 4.6 < tracker.home_momentum < 4.8

        # Away scores TD
        tracker.add_event('away', 'touchdown')
        assert tracker.away_momentum == 8.0

        # Both teams have positive momentum
        assert tracker.home_momentum > 0
        assert tracker.away_momentum > 0

    def test_momentum_swing_from_turnover(self):
        """Test dramatic momentum swing from turnover."""
        tracker = MomentumTracker()

        # Home has momentum from scoring drive
        tracker.add_event('home', 'touchdown')
        tracker.add_event('home', 'big_play_gain')
        # Home momentum: 8 + 5 = 13

        # Away forces turnover
        tracker.add_event('away', 'turnover_gain')
        tracker.add_event('home', 'turnover_loss')
        # Home: 13 - 10 = 3
        # Away: 0 + 10 = 10

        assert tracker.home_momentum == 3.0
        assert tracker.away_momentum == 10.0

        # Momentum has swung to away team
        assert tracker.away_momentum > tracker.home_momentum

    def test_blowout_game_momentum_maxes_out(self):
        """Test blowout game hits momentum ceiling."""
        tracker = MomentumTracker()

        # Winning team scores multiple TDs
        for _ in range(4):
            tracker.add_event('home', 'touchdown')

        # Should hit +20 ceiling
        assert tracker.home_momentum == 20.0

        # Losing team has turnovers
        for _ in range(3):
            tracker.add_event('away', 'turnover_loss')

        # Should hit -20 floor
        assert tracker.away_momentum == -20.0