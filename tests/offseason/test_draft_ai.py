"""
Tests for DraftManager AI draft simulation.

Validates needs-based draft AI implementation.
"""

import pytest
from offseason.draft_manager import DraftManager


class TestDraftAI:
    """Test suite for draft AI functionality."""

    @pytest.fixture
    def draft_manager(self):
        """Create DraftManager instance for testing."""
        return DraftManager(
            database_path=":memory:",
            dynasty_id="test_draft_ai",
            season_year=2025,
            enable_persistence=False
        )

    def test_evaluate_prospect_base_value(self, draft_manager):
        """Test prospect evaluation returns base overall when no needs."""
        prospect = {
            'player_id': 1,
            'position': 'quarterback',
            'overall': 85,
            'projected_pick_min': 10,
            'projected_pick_max': 20
        }

        team_needs = []  # No needs

        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=15
        )

        assert score == 85  # Base value, no bonuses

    def test_evaluate_prospect_critical_need_bonus(self, draft_manager):
        """Test CRITICAL need adds +15 bonus."""
        prospect = {
            'player_id': 1,
            'position': 'quarterback',
            'overall': 85,
            'projected_pick_min': 10,
            'projected_pick_max': 20
        }

        team_needs = [
            {'position': 'quarterback', 'urgency_score': 5}  # CRITICAL
        ]

        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=15
        )

        assert score == 100  # 85 + 15 (CRITICAL bonus)

    def test_evaluate_prospect_high_need_bonus(self, draft_manager):
        """Test HIGH need adds +8 bonus."""
        prospect = {
            'player_id': 1,
            'position': 'wide_receiver',
            'overall': 80,
            'projected_pick_min': 20,
            'projected_pick_max': 40
        }

        team_needs = [
            {'position': 'wide_receiver', 'urgency_score': 4}  # HIGH
        ]

        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=25
        )

        assert score == 88  # 80 + 8 (HIGH bonus)

    def test_evaluate_prospect_medium_need_bonus(self, draft_manager):
        """Test MEDIUM need adds +3 bonus."""
        prospect = {
            'player_id': 1,
            'position': 'linebacker',
            'overall': 75,
            'projected_pick_min': 50,
            'projected_pick_max': 80
        }

        team_needs = [
            {'position': 'linebacker', 'urgency_score': 3}  # MEDIUM
        ]

        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=60
        )

        assert score == 78  # 75 + 3 (MEDIUM bonus)

    def test_evaluate_prospect_reach_penalty(self, draft_manager):
        """Test reaching too far above projection incurs -5 penalty."""
        prospect = {
            'player_id': 1,
            'position': 'running_back',
            'overall': 70,
            'projected_pick_min': 50,  # Projected at pick 50
            'projected_pick_max': 80
        }

        team_needs = []

        # Drafting at pick 10 (way above projection)
        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=10
        )

        assert score == 65  # 70 - 5 (reach penalty)

    def test_evaluate_prospect_need_beats_reach_penalty(self, draft_manager):
        """Test need bonus outweighs reach penalty."""
        prospect = {
            'player_id': 1,
            'position': 'quarterback',
            'overall': 85,
            'projected_pick_min': 50,  # Projected much later
            'projected_pick_max': 80
        }

        team_needs = [
            {'position': 'quarterback', 'urgency_score': 5}  # CRITICAL
        ]

        # Drafting at pick 10 (way above projection)
        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=10
        )

        assert score == 95  # 85 + 15 (CRITICAL) - 5 (reach) = 95

    def test_evaluate_prospect_ignores_non_matching_needs(self, draft_manager):
        """Test that only matching position needs apply bonuses."""
        prospect = {
            'player_id': 1,
            'position': 'quarterback',
            'overall': 85,
            'projected_pick_min': 10,
            'projected_pick_max': 20
        }

        # Team needs WR, not QB
        team_needs = [
            {'position': 'wide_receiver', 'urgency_score': 5}  # CRITICAL (but wrong position)
        ]

        score = draft_manager._evaluate_prospect(
            prospect=prospect,
            team_needs=team_needs,
            pick_position=15
        )

        assert score == 85  # No bonus for non-matching position


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
