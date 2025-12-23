"""
Tests for CoachCutsProposalGenerator.

Part of Tollgate 10: Roster Cuts Integration.

Tests the performance-based cut proposal generator from Head Coach perspective.
"""

import pytest
from unittest.mock import MagicMock, patch

from game_cycle.services.proposal_generators.coach_cuts_generator import CoachCutsProposalGenerator
from game_cycle.models.owner_directives import OwnerDirectives
from game_cycle.models.proposal_enums import ProposalType


@pytest.fixture
def mock_directives():
    """Create mock owner directives for testing."""
    return OwnerDirectives(
        dynasty_id="test_dynasty",
        team_id=1,
        season=2025,
        team_philosophy="win_now",
        budget_stance="moderate",
        priority_positions=["QB", "EDGE", "WR"],
        protected_player_ids=[100],  # List of player IDs as ints
        expendable_player_ids=[200],  # List of player IDs as ints
        trust_gm=False,
    )


@pytest.fixture
def mock_roster():
    """Create mock roster for testing."""
    return [
        {
            "player_id": 100,
            "name": "Protected Star QB",
            "position": "QB",
            "overall": 92,
            "potential": 95,
            "age": 28,
            "cap_hit": 35_000_000,
            "dead_money": 15_000_000,
            "season_grade": 90.0,
            "injury_prone_rating": 2,
            "special_teams_ability": 0,
        },
        {
            "player_id": 101,
            "name": "Poor Performer",
            "position": "WR",
            "overall": 65,
            "potential": 68,
            "age": 27,
            "cap_hit": 5_000_000,
            "dead_money": 1_000_000,
            "season_grade": 58.0,  # Below LOW_PERFORMANCE_THRESHOLD (65)
            "injury_prone_rating": 7,  # Above HIGH_INJURY_RISK_THRESHOLD (5)
            "special_teams_ability": 30,
        },
        {
            "player_id": 102,
            "name": "Young Talent",
            "position": "CB",
            "overall": 70,
            "potential": 85,  # High upside (15 points)
            "age": 22,
            "cap_hit": 2_000_000,
            "dead_money": 500_000,
            "season_grade": 72.0,
            "injury_prone_rating": 1,
            "special_teams_ability": 75,  # Good ST value
        },
        {
            "player_id": 103,
            "name": "Aging Veteran",
            "position": "RB",
            "overall": 75,
            "potential": 76,  # Low upside (1 point)
            "age": 33,
            "cap_hit": 8_000_000,
            "dead_money": 3_000_000,
            "season_grade": 76.0,
            "injury_prone_rating": 4,
            "special_teams_ability": 20,
        },
        {
            "player_id": 200,
            "name": "Expendable Depth",
            "position": "OL",
            "overall": 68,
            "potential": 70,
            "age": 26,
            "cap_hit": 3_000_000,
            "dead_money": 800_000,
            "season_grade": 68.0,
            "injury_prone_rating": 3,
            "special_teams_ability": 40,
        },
    ]


class TestCoachCutsProposalGenerator:
    """Tests for the CoachCutsProposalGenerator class."""

    def test_generator_returns_empty_list_when_no_cuts_needed(
        self, mock_directives, mock_roster
    ):
        """Generator should return empty list if no cuts needed."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        result = generator.generate_proposals(roster=mock_roster, cuts_needed=0)
        assert result == []

    def test_generator_raises_error_when_all_players_protected(
        self, mock_roster
    ):
        """Generator should raise error if all players are protected."""
        # Create directives with all players protected
        protected_directives = OwnerDirectives(
            dynasty_id="test_dynasty",
            team_id=1,
            season=2025,
            team_philosophy="maintain",
            budget_stance="moderate",
            priority_positions=[],
            protected_player_ids=[100, 101, 102, 103, 200],
            expendable_player_ids=[],
            trust_gm=False,
        )

        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=protected_directives,
        )

        with pytest.raises(ValueError, match="No cuttable players available"):
            generator.generate_proposals(roster=mock_roster, cuts_needed=2)

    def test_poor_performer_gets_high_cut_score(
        self, mock_directives, mock_roster
    ):
        """Player with poor performance and injury issues should get high cut score."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 101: Poor performer with low season grade (58) and high injury risk (7)
        poor_performer = mock_roster[1]
        score = generator._score_cut_candidate(poor_performer)

        # Should have high cut score (performance score + injury penalty)
        # Performance: 100 - 58 = 42
        # Injury: 7 * 5 = 35
        # Total should be >= 75
        assert score >= 75

    def test_young_talent_gets_low_cut_score(
        self, mock_directives, mock_roster
    ):
        """Young player with high upside should get low cut score (protected)."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 102: Young (22) with high upside (85-70=15) and good ST
        young_talent = mock_roster[2]
        score = generator._score_cut_candidate(young_talent)

        # Should have low cut score due to:
        # - Age < 25 and upside > 10: -30 adjustment
        # - Good ST ability (75 > 70): -10 adjustment
        # Even with base performance score, should be low or negative
        assert score < 30

    def test_aging_veteran_gets_moderate_cut_score(
        self, mock_directives, mock_roster
    ):
        """Aging veteran past prime should get moderate-to-high cut score."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 103: Age 33 with low upside (1)
        aging_vet = mock_roster[3]
        score = generator._score_cut_candidate(aging_vet)

        # Should have moderate cut score due to:
        # - Age > 32: +15 adjustment (or age > 30 with upside < 3: +20)
        assert score >= 20

    def test_expendable_player_gets_bonus_cut_score(
        self, mock_directives, mock_roster
    ):
        """Expendable players should get +20 bonus to cut score."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 200: Expendable
        expendable_player = mock_roster[4]
        score_with_expendable = generator._score_cut_candidate(expendable_player)

        # Remove expendable status
        mock_directives.expendable_player_ids = []
        score_without_expendable = generator._score_cut_candidate(expendable_player)

        # Expendable should be +20 higher
        assert score_with_expendable == score_without_expendable + 20

    def test_priority_position_gets_penalty(
        self, mock_directives, mock_roster
    ):
        """Players at priority positions should get -10 penalty (harder to cut)."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 101 is WR (in priority_positions)
        # Create a copy without WR in priorities
        non_priority_directives = OwnerDirectives(
            dynasty_id="test_dynasty",
            team_id=1,
            season=2025,
            team_philosophy="win_now",
            budget_stance="moderate",
            priority_positions=["QB", "EDGE"],  # No WR
            protected_player_ids=[100],
            expendable_player_ids=[200],
            trust_gm=False,
        )

        gen_non_priority = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=non_priority_directives,
        )

        priority_score = generator._score_cut_candidate(mock_roster[1])
        non_priority_score = gen_non_priority._score_cut_candidate(mock_roster[1])

        # Priority position should be -10 lower
        assert priority_score == non_priority_score - 10

    def test_tier_performance_assigned_correctly(
        self, mock_directives, mock_roster
    ):
        """Poor performer should be assigned TIER_PERFORMANCE."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 101: season_grade=58 (< 60) → TIER_PERFORMANCE
        poor_performer = mock_roster[1]
        cut_score = generator._score_cut_candidate(poor_performer)
        tier = generator._get_priority_tier(poor_performer, cut_score)

        assert tier == generator.TIER_PERFORMANCE

    def test_tier_age_assigned_correctly(
        self, mock_directives, mock_roster
    ):
        """Aging veteran (>= 32) should be assigned TIER_AGE."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 103: age=33 (>= 32) → TIER_AGE
        aging_vet = mock_roster[3]
        cut_score = generator._score_cut_candidate(aging_vet)
        tier = generator._get_priority_tier(aging_vet, cut_score)

        assert tier == generator.TIER_AGE

    def test_tier_depth_assigned_for_expendable(
        self, mock_directives, mock_roster
    ):
        """Expendable players should be assigned TIER_DEPTH."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Player 200: expendable → TIER_DEPTH
        expendable = mock_roster[4]
        cut_score = generator._score_cut_candidate(expendable)
        tier = generator._get_priority_tier(expendable, cut_score)

        assert tier == generator.TIER_DEPTH

    def test_confidence_varies_by_tier(
        self, mock_directives
    ):
        """Confidence should vary based on priority tier."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # TIER_PERFORMANCE (1) should have higher confidence (0.75-0.90)
        conf_performance = generator._calculate_confidence(50.0, generator.TIER_PERFORMANCE)
        assert 0.75 <= conf_performance <= 0.90

        # TIER_DEPTH (2) should have moderate confidence (0.60-0.75)
        conf_depth = generator._calculate_confidence(50.0, generator.TIER_DEPTH)
        assert 0.60 <= conf_depth <= 0.75

        # TIER_AGE (3) should have lower confidence (0.50-0.65)
        conf_age = generator._calculate_confidence(50.0, generator.TIER_AGE)
        assert 0.50 <= conf_age <= 0.65

        # TIER_ROTATION (4) should have lowest confidence (0.40-0.55)
        conf_rotation = generator._calculate_confidence(50.0, generator.TIER_ROTATION)
        assert 0.40 <= conf_rotation <= 0.55

    def test_generator_creates_proposals_with_correct_count(
        self, mock_directives, mock_roster
    ):
        """Generator should create exactly the number of proposals requested."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Request 2 cuts (protected player 100 should be skipped)
        proposals = generator.generate_proposals(roster=mock_roster, cuts_needed=2)

        assert len(proposals) == 2

    def test_proposals_sorted_by_priority_tier(
        self, mock_directives, mock_roster
    ):
        """Proposals should be sorted by priority tier (ascending)."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        proposals = generator.generate_proposals(roster=mock_roster, cuts_needed=3)

        # Verify sorted by priority (lower tier = higher priority)
        for i in range(len(proposals) - 1):
            assert proposals[i].priority <= proposals[i + 1].priority

    def test_proposal_contains_correct_fields(
        self, mock_directives, mock_roster
    ):
        """Proposal should contain all required fields with correct values."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        proposals = generator.generate_proposals(roster=mock_roster, cuts_needed=1)
        proposal = proposals[0]

        # Check basic proposal fields
        assert proposal.dynasty_id == "test_dynasty"
        assert proposal.team_id == 1
        assert proposal.season == 2025
        assert proposal.stage == "OFFSEASON_ROSTER_CUTS"
        assert proposal.proposal_type == ProposalType.CUT
        assert proposal.status.value == "PENDING"

        # Check details
        assert "player_id" in proposal.details
        assert "player_name" in proposal.details
        assert "position" in proposal.details
        assert "cap_savings" in proposal.details
        assert "dead_money" in proposal.details

        # Check reasoning exists and mentions performance
        assert proposal.gm_reasoning
        assert len(proposal.gm_reasoning) > 50
        assert "performance" in proposal.gm_reasoning.lower() or "PERFORMANCE" in proposal.gm_reasoning

    def test_reasoning_includes_performance_score(
        self, mock_directives, mock_roster
    ):
        """Reasoning should include the performance cut score."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        proposals = generator.generate_proposals(roster=mock_roster, cuts_needed=1)
        proposal = proposals[0]

        # Reasoning should include "Performance Cut Score: X.X"
        assert "Performance Cut Score:" in proposal.gm_reasoning
        assert "Cap Impact:" in proposal.gm_reasoning

    def test_protected_players_excluded_from_cuts(
        self, mock_directives, mock_roster
    ):
        """Protected players should never be in cut proposals."""
        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Request all possible cuts
        proposals = generator.generate_proposals(roster=mock_roster, cuts_needed=4)

        # Protected player (100) should not be in any proposal
        protected_player_ids = [p.subject_player_id for p in proposals]
        assert "100" not in protected_player_ids

    def test_only_players_above_min_score_proposed(
        self, mock_directives
    ):
        """Only players with cut score >= MIN_CUT_SCORE should be proposed."""
        # Create roster with only excellent players (low cut scores)
        excellent_roster = [
            {
                "player_id": i,
                "name": f"Star Player {i}",
                "position": "QB",
                "overall": 90,
                "potential": 92,
                "age": 26,
                "cap_hit": 10_000_000,
                "dead_money": 2_000_000,
                "season_grade": 92.0,  # Excellent grade
                "injury_prone_rating": 0,
                "special_teams_ability": 0,
            }
            for i in range(1, 6)
        ]

        generator = CoachCutsProposalGenerator(
            db_path="test.db",
            dynasty_id="test_dynasty",
            season=2025,
            team_id=1,
            directives=mock_directives,
        )

        # Request 3 cuts - but no players should score above MIN_CUT_SCORE (10.0)
        proposals = generator.generate_proposals(roster=excellent_roster, cuts_needed=3)

        # Generator correctly returns 0 proposals when no one meets MIN_CUT_SCORE threshold
        # (Performance score: 100 - 92 = 8, which is < 10.0)
        assert len(proposals) == 0
