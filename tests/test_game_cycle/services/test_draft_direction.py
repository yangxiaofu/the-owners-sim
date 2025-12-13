"""
Unit tests for Draft Direction (Phase 1 MVP).

Tests the three basic strategies:
- Best Player Available (BPA)
- Balanced
- Needs-Based
"""

import pytest
from src.game_cycle.models import DraftStrategy, DraftDirection, DraftDirectionResult


class TestDraftDirectionModel:
    """Test the DraftDirection data model."""

    def test_default_direction_is_balanced(self):
        """Default strategy should be Balanced."""
        direction = DraftDirection()
        assert direction.strategy == DraftStrategy.BALANCED
        assert direction.priority_positions == []
        assert direction.watchlist_prospect_ids == []

    def test_validation_passes_for_valid_direction(self):
        """Validation should pass for valid configurations."""
        direction = DraftDirection(strategy=DraftStrategy.BEST_PLAYER_AVAILABLE)
        is_valid, error_msg = direction.validate()
        assert is_valid is True
        assert error_msg == ""

    def test_validation_fails_for_too_many_priorities(self):
        """Validation should fail if more than 5 priorities."""
        direction = DraftDirection(
            strategy=DraftStrategy.BALANCED,
            priority_positions=["QB", "WR", "OT", "CB", "EDGE", "DT"]  # 6 positions
        )
        is_valid, error_msg = direction.validate()
        assert is_valid is False
        assert "Maximum 5 priority positions" in error_msg


class TestDraftDirectionResult:
    """Test the DraftDirectionResult data model."""

    def test_result_string_format(self):
        """Test __str__ method formats correctly."""
        result = DraftDirectionResult(
            prospect_id=1,
            prospect_name="John Smith",
            original_score=75.0,
            adjusted_score=90.0,
            strategy_bonus=15.0,
            position_bonus=0.0,
            watchlist_bonus=0.0,
            reach_penalty=0.0,
            reason="Balanced: CRITICAL need (+15)"
        )

        result_str = str(result)
        assert "John Smith" in result_str
        assert "75.0" in result_str
        assert "90.0" in result_str
        assert "+15.0" in result_str


class MockDraftService:
    """Mock draft service with only the evaluation methods for testing."""

    def __init__(self):
        # Import the methods from the real service
        from src.game_cycle.services.draft_service import DraftService

        # Bind the evaluation methods
        self._evaluate_prospect_with_direction = DraftService._evaluate_prospect_with_direction.__get__(self)
        self._evaluate_bpa = DraftService._evaluate_bpa.__get__(self)
        self._evaluate_balanced = DraftService._evaluate_balanced.__get__(self)
        self._evaluate_needs_based = DraftService._evaluate_needs_based.__get__(self)
        self._evaluate_position_focus = DraftService._evaluate_position_focus.__get__(self)


class TestBPAStrategy:
    """Test Best Player Available strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()
        self.prospect = {
            "player_id": 1,
            "name": "John Smith",
            "position": "QB",
            "overall": 75,
            "projected_pick_min": 20
        }
        self.team_needs = [
            {"position": "QB", "urgency_score": 5},  # CRITICAL need
            {"position": "WR", "urgency_score": 4},  # HIGH need
        ]

    def test_bpa_ignores_team_needs(self):
        """BPA should ignore team needs completely."""
        direction = DraftDirection(strategy=DraftStrategy.BEST_PLAYER_AVAILABLE)

        result = self.service._evaluate_prospect_with_direction(
            self.prospect,
            self.team_needs,
            pick_position=15,
            direction=direction
        )

        assert result.adjusted_score == 75.0  # No boost
        assert result.strategy_bonus == 0
        assert result.reach_penalty == 0
        assert "BPA" in result.reason

    def test_bpa_same_score_for_all_positions(self):
        """BPA should give same score regardless of need."""
        direction = DraftDirection(strategy=DraftStrategy.BEST_PLAYER_AVAILABLE)

        # QB (CRITICAL need)
        qb_prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 80}
        qb_result = self.service._evaluate_prospect_with_direction(
            qb_prospect, self.team_needs, 10, direction
        )

        # CB (NO need)
        cb_prospect = {"player_id": 2, "name": "CB", "position": "CB", "overall": 80}
        cb_result = self.service._evaluate_prospect_with_direction(
            cb_prospect, self.team_needs, 10, direction
        )

        # Both should have same score
        assert qb_result.adjusted_score == cb_result.adjusted_score == 80.0


class TestBalancedStrategy:
    """Test Balanced strategy (current system behavior)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()

    def test_balanced_applies_critical_need_boost(self):
        """Balanced should apply +15 for CRITICAL needs."""
        prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 75}
        team_needs = [{"position": "QB", "urgency_score": 5}]  # CRITICAL
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.strategy_bonus == 15
        assert result.adjusted_score == 90.0  # 75 + 15
        assert "CRITICAL" in result.reason

    def test_balanced_applies_high_need_boost(self):
        """Balanced should apply +8 for HIGH needs."""
        prospect = {"player_id": 1, "name": "WR", "position": "WR", "overall": 75}
        team_needs = [{"position": "WR", "urgency_score": 4}]  # HIGH
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.strategy_bonus == 8
        assert result.adjusted_score == 83.0  # 75 + 8

    def test_balanced_applies_medium_need_boost(self):
        """Balanced should apply +3 for MEDIUM needs."""
        prospect = {"player_id": 1, "name": "OT", "position": "OT", "overall": 75}
        team_needs = [{"position": "OT", "urgency_score": 3}]  # MEDIUM
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.strategy_bonus == 3
        assert result.adjusted_score == 78.0  # 75 + 3

    def test_balanced_applies_reach_penalty(self):
        """Balanced should apply -5 reach penalty when picking 20+ spots early."""
        prospect = {
            "player_id": 1,
            "name": "CB",
            "position": "CB",
            "overall": 75,
            "projected_pick_min": 50  # Projected to go at pick 50
        }
        team_needs = []
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        # Picking at #15 when projected at #50 = 35 spot reach
        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.reach_penalty == -5
        assert result.adjusted_score == 70.0  # 75 - 5

    def test_balanced_no_penalty_for_small_reach(self):
        """Balanced should NOT apply reach penalty for <20 spot reach."""
        prospect = {
            "player_id": 1,
            "name": "CB",
            "position": "CB",
            "overall": 75,
            "projected_pick_min": 30  # Projected at pick 30
        }
        team_needs = []
        direction = DraftDirection(strategy=DraftStrategy.BALANCED)

        # Picking at #15 when projected at #30 = 15 spot reach (no penalty)
        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.reach_penalty == 0
        assert result.adjusted_score == 75.0  # No penalty


class TestNeedsBasedStrategy:
    """Test Needs-Based strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()

    def test_needs_based_applies_double_boost_for_critical(self):
        """Needs-Based should apply +30 (2x) for CRITICAL needs."""
        prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 70}
        team_needs = [{"position": "QB", "urgency_score": 5}]  # CRITICAL
        direction = DraftDirection(strategy=DraftStrategy.NEEDS_BASED)

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.strategy_bonus == 30  # 2x normal
        assert result.adjusted_score == 100.0  # 70 + 30

    def test_needs_based_applies_double_boost_for_high(self):
        """Needs-Based should apply +18 for HIGH needs."""
        prospect = {"player_id": 1, "name": "WR", "position": "WR", "overall": 70}
        team_needs = [{"position": "WR", "urgency_score": 4}]  # HIGH
        direction = DraftDirection(strategy=DraftStrategy.NEEDS_BASED)

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.strategy_bonus == 18
        assert result.adjusted_score == 88.0  # 70 + 18

    def test_needs_based_no_reach_penalty(self):
        """Needs-Based should NOT apply reach penalty (willing to reach)."""
        prospect = {
            "player_id": 1,
            "name": "QB",
            "position": "QB",
            "overall": 70,
            "projected_pick_min": 100  # Massive reach (projected in round 4)
        }
        team_needs = [{"position": "QB", "urgency_score": 5}]  # CRITICAL
        direction = DraftDirection(strategy=DraftStrategy.NEEDS_BASED)

        # Picking at #15 when projected at #100 (huge reach)
        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction
        )

        assert result.reach_penalty == 0  # NO penalty
        assert result.adjusted_score == 100.0  # 70 + 30 (no reach penalty)
        assert "willing to reach" in result.reason


class TestWatchlistBonus:
    """Test watchlist bonus (Phase 3 feature, but framework exists)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()

    def test_watchlist_bonus_applies_to_all_strategies(self):
        """Watchlist +10 bonus should work with any strategy."""
        prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 75}
        team_needs = []

        for strategy in [DraftStrategy.BEST_PLAYER_AVAILABLE, DraftStrategy.BALANCED, DraftStrategy.NEEDS_BASED]:
            direction = DraftDirection(
                strategy=strategy,
                watchlist_prospect_ids=[1]  # Watchlist this prospect
            )

            result = self.service._evaluate_prospect_with_direction(
                prospect, team_needs, 15, direction
            )

            assert result.watchlist_bonus == 10
            assert "Watchlist target" in result.reason


class TestDefaultDirection:
    """Test behavior when no direction is provided."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()

    def test_none_direction_defaults_to_balanced(self):
        """When direction=None, should default to Balanced."""
        prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 75}
        team_needs = [{"position": "QB", "urgency_score": 5}]  # CRITICAL

        result = self.service._evaluate_prospect_with_direction(
            prospect, team_needs, 15, direction=None  # No direction provided
        )

        # Should behave like Balanced (apply need boost)
        assert result.strategy_bonus == 15
        assert result.adjusted_score == 90.0


class TestPositionFocusStrategy:
    """Test Position Focus strategy (Phase 2)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = MockDraftService()
        self.team_needs = [
            {"position": "QB", "urgency_score": 5},  # CRITICAL
            {"position": "WR", "urgency_score": 4},  # HIGH
            {"position": "OT", "urgency_score": 3},  # MEDIUM
        ]

    def test_position_focus_excludes_non_priority_positions(self):
        """Position Focus should exclude positions not in priority list."""
        cb_prospect = {"player_id": 1, "name": "CB", "position": "CB", "overall": 90}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT"]
        )

        result = self.service._evaluate_prospect_with_direction(
            cb_prospect, self.team_needs, 15, direction
        )

        assert result.adjusted_score == -100  # Excluded
        assert "not in priorities" in result.reason

    def test_position_focus_first_priority_gets_25_bonus(self):
        """1st priority position gets +25 bonus."""
        qb_prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT"]
        )

        result = self.service._evaluate_prospect_with_direction(
            qb_prospect, self.team_needs, 15, direction
        )

        assert result.position_bonus == 25  # 1st priority
        assert result.strategy_bonus == 20  # CRITICAL need
        assert result.adjusted_score == 115.0  # 70 + 25 + 20

    def test_position_focus_second_priority_gets_20_bonus(self):
        """2nd priority position gets +20 bonus."""
        wr_prospect = {"player_id": 1, "name": "WR", "position": "WR", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT"]
        )

        result = self.service._evaluate_prospect_with_direction(
            wr_prospect, self.team_needs, 15, direction
        )

        assert result.position_bonus == 20  # 2nd priority
        assert result.strategy_bonus == 12  # HIGH need
        assert result.adjusted_score == 102.0  # 70 + 20 + 12

    def test_position_focus_third_priority_gets_15_bonus(self):
        """3rd priority position gets +15 bonus."""
        ot_prospect = {"player_id": 1, "name": "OT", "position": "OT", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT"]
        )

        result = self.service._evaluate_prospect_with_direction(
            ot_prospect, self.team_needs, 15, direction
        )

        assert result.position_bonus == 15  # 3rd priority
        assert result.strategy_bonus == 6  # MEDIUM need
        assert result.adjusted_score == 91.0  # 70 + 15 + 6

    def test_position_focus_fourth_priority_gets_10_bonus(self):
        """4th priority position gets +10 bonus."""
        cb_prospect = {"player_id": 1, "name": "CB", "position": "CB", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT", "CB"]
        )

        result = self.service._evaluate_prospect_with_direction(
            cb_prospect, self.team_needs, 15, direction
        )

        assert result.position_bonus == 10  # 4th priority
        assert result.adjusted_score == 80.0  # 70 + 10

    def test_position_focus_fifth_priority_gets_5_bonus(self):
        """5th priority position gets +5 bonus."""
        edge_prospect = {"player_id": 1, "name": "EDGE", "position": "EDGE", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT", "CB", "EDGE"]
        )

        result = self.service._evaluate_prospect_with_direction(
            edge_prospect, self.team_needs, 15, direction
        )

        assert result.position_bonus == 5  # 5th priority
        assert result.adjusted_score == 75.0  # 70 + 5

    def test_position_focus_adds_critical_need_boost(self):
        """Position Focus applies +20 for CRITICAL needs."""
        qb_prospect = {"player_id": 1, "name": "QB", "position": "QB", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB"]
        )

        result = self.service._evaluate_prospect_with_direction(
            qb_prospect, self.team_needs, 15, direction
        )

        assert result.strategy_bonus == 20  # CRITICAL
        assert "CRITICAL" in result.reason

    def test_position_focus_adds_high_need_boost(self):
        """Position Focus applies +12 for HIGH needs."""
        wr_prospect = {"player_id": 1, "name": "WR", "position": "WR", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["WR"]
        )

        result = self.service._evaluate_prospect_with_direction(
            wr_prospect, self.team_needs, 15, direction
        )

        assert result.strategy_bonus == 12  # HIGH
        assert "HIGH" in result.reason

    def test_position_focus_adds_medium_need_boost(self):
        """Position Focus applies +6 for MEDIUM needs."""
        ot_prospect = {"player_id": 1, "name": "OT", "position": "OT", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["OT"]
        )

        result = self.service._evaluate_prospect_with_direction(
            ot_prospect, self.team_needs, 15, direction
        )

        assert result.strategy_bonus == 6  # MEDIUM
        assert "MEDIUM" in result.reason

    def test_position_focus_no_boost_for_low_need(self):
        """Position Focus applies 0 for LOW needs."""
        rb_prospect = {"player_id": 1, "name": "RB", "position": "RB", "overall": 70}
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["RB"]
        )

        result = self.service._evaluate_prospect_with_direction(
            rb_prospect, self.team_needs, 15, direction
        )

        assert result.strategy_bonus == 0  # LOW need
        assert result.adjusted_score == 95.0  # 70 + 25 (1st priority) + 0


class TestPositionFocusValidation:
    """Test Position Focus validation rules."""

    def test_validation_fails_without_priorities(self):
        """Position Focus requires at least 1 priority position."""
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=[]
        )

        is_valid, error_msg = direction.validate()
        assert is_valid is False
        assert "at least 1 priority position" in error_msg

    def test_validation_passes_with_one_priority(self):
        """Position Focus is valid with 1 priority."""
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB"]
        )

        is_valid, error_msg = direction.validate()
        assert is_valid is True
        assert error_msg == ""

    def test_validation_passes_with_five_priorities(self):
        """Position Focus is valid with 5 priorities (maximum)."""
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT", "CB", "EDGE"]
        )

        is_valid, error_msg = direction.validate()
        assert is_valid is True
        assert error_msg == ""

    def test_validation_fails_with_six_priorities(self):
        """Position Focus fails with 6 priorities (over maximum)."""
        direction = DraftDirection(
            strategy=DraftStrategy.POSITION_FOCUS,
            priority_positions=["QB", "WR", "OT", "CB", "EDGE", "DT"]
        )

        is_valid, error_msg = direction.validate()
        assert is_valid is False
        assert "Maximum 5 priority positions" in error_msg
