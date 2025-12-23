"""
Tests for FranchiseTagProposalGenerator.

Part of Tollgate 5: Franchise Tag Integration.
"""

import pytest
from unittest.mock import MagicMock, patch

from game_cycle.services.proposal_generators import FranchiseTagProposalGenerator
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
        protected_player_ids=[100],
        expendable_player_ids=[200],
        trust_gm=False,
    )


@pytest.fixture
def mock_taggable_players():
    """Create mock taggable players list."""
    return [
        {
            "player_id": 100,
            "name": "Elite QB",
            "position": "QB",
            "overall": 92,
            "age": 28,
            "franchise_tag_cost": 35_000_000,
            "transition_tag_cost": 30_000_000,
        },
        {
            "player_id": 101,
            "name": "Good WR",
            "position": "WR",
            "overall": 85,
            "age": 26,
            "franchise_tag_cost": 22_000_000,
            "transition_tag_cost": 19_000_000,
        },
        {
            "player_id": 200,
            "name": "Expendable RB",
            "position": "RB",
            "overall": 78,
            "age": 29,
            "franchise_tag_cost": 12_000_000,
            "transition_tag_cost": 10_000_000,
        },
    ]


class TestFranchiseTagProposalGenerator:
    """Tests for the FranchiseTagProposalGenerator class."""

    def test_generator_returns_none_when_tag_already_used(
        self, mock_directives
    ):
        """Generator should return None if team already used tag."""
        with patch.object(
            FranchiseTagProposalGenerator, "_tag_service", create=True
        ) as mock_service:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = True

            with patch(
                "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService",
                return_value=mock_service_instance,
            ):
                generator = FranchiseTagProposalGenerator(
                    db_path="test.db",
                    dynasty_id="test_dynasty",
                    season=2025,
                    team_id=1,
                    directives=mock_directives,
                )

                result = generator.generate_proposal()
                assert result is None

    def test_generator_returns_none_when_no_taggable_players(
        self, mock_directives
    ):
        """Generator should return None if no taggable players."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = []
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            result = generator.generate_proposal()
            assert result is None

    def test_protected_player_gets_bonus(
        self, mock_directives, mock_taggable_players
    ):
        """Protected players should get +25 bonus score."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            # Score protected player (id=100)
            protected_player = mock_taggable_players[0]
            score = generator._score_candidate(protected_player)

            # Score same player without protected status
            mock_directives.protected_player_ids = []
            unprotected_score = generator._score_candidate(protected_player)

            # Protected should be +25 higher
            assert score == unprotected_score + 25

    def test_expendable_player_gets_penalty(
        self, mock_directives, mock_taggable_players
    ):
        """Expendable players should get -30 penalty score."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            # Score expendable player (id=200)
            expendable_player = mock_taggable_players[2]
            score = generator._score_candidate(expendable_player)

            # Score same player without expendable status
            mock_directives.expendable_player_ids = []
            normal_score = generator._score_candidate(expendable_player)

            # Expendable should be -30 lower
            assert score == normal_score - 30

    def test_win_now_philosophy_bonus(
        self, mock_directives, mock_taggable_players
    ):
        """Win-now philosophy should add +10 bonus."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            player = mock_taggable_players[1]  # WR player
            win_now_score = generator._score_candidate(player)

            # Change philosophy
            mock_directives.team_philosophy = "maintain"
            maintain_score = generator._score_candidate(player)

            # Win-now should be +10 higher
            assert win_now_score == maintain_score + 10

    def test_conservative_budget_penalty(
        self, mock_taggable_players
    ):
        """Conservative budget stance should add -15 penalty."""
        conservative_directives = OwnerDirectives(
            dynasty_id="test_dynasty",
            team_id=1,
            season=2025,
            team_philosophy="maintain",
            budget_stance="conservative",
            priority_positions=[],
            protected_player_ids=[],
            expendable_player_ids=[],
            trust_gm=False,
        )

        moderate_directives = OwnerDirectives(
            dynasty_id="test_dynasty",
            team_id=1,
            season=2025,
            team_philosophy="maintain",
            budget_stance="moderate",
            priority_positions=[],
            protected_player_ids=[],
            expendable_player_ids=[],
            trust_gm=False,
        )

        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            conservative_gen = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=conservative_directives,
            )

            moderate_gen = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=moderate_directives,
            )

            # Use RB player (non-premium position) to avoid extra -10 penalty
            player = mock_taggable_players[2]
            conservative_score = conservative_gen._score_candidate(player)
            moderate_score = moderate_gen._score_candidate(player)

            # Conservative should be -15 lower
            assert conservative_score == moderate_score - 15

    def test_generator_creates_proposal_for_high_scoring_player(
        self, mock_directives, mock_taggable_players
    ):
        """Generator should create proposal for player scoring above threshold."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            result = generator.generate_proposal()

            # Should return a proposal for the protected QB
            assert result is not None
            assert result.proposal_type == ProposalType.FRANCHISE_TAG
            assert result.subject_player_id == "100"
            assert "Elite QB" in result.gm_reasoning

    def test_reasoning_includes_directive_context(
        self, mock_directives, mock_taggable_players
    ):
        """Reasoning should reference owner directives."""
        with patch(
            "game_cycle.services.proposal_generators.franchise_tag_generator.FranchiseTagService"
        ) as MockService:
            mock_service_instance = MagicMock()
            mock_service_instance.has_team_used_tag.return_value = False
            mock_service_instance.get_taggable_players.return_value = mock_taggable_players
            MockService.return_value = mock_service_instance

            generator = FranchiseTagProposalGenerator(
                db_path="test.db",
                dynasty_id="test_dynasty",
                season=2025,
                team_id=1,
                directives=mock_directives,
            )

            result = generator.generate_proposal()

            # Should reference Win-Now philosophy
            assert "Win-Now" in result.gm_reasoning or "win_now" in result.gm_reasoning.lower()
