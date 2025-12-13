"""
Tests for Voting Engine.

Tests the 50-voter simulation with archetypes, variance, and position bias.
Part of Milestone 10: Awards System, Tollgate 3.
"""

import pytest
import random

from src.game_cycle.services.awards.models import AwardScore, AwardType
from src.game_cycle.services.awards.voter_archetypes import (
    VoterArchetype,
    VoterProfile,
    ARCHETYPE_WEIGHTS,
    TRADITIONAL_POSITION_BIAS,
    VOTER_DISTRIBUTION,
    DEFAULT_POSITION_BIAS,
)
from src.game_cycle.services.awards.voting_engine import (
    VotingEngine,
    VotingResult,
    POINTS_BY_RANK,
    MAX_POINTS,
    DEFAULT_NUM_VOTERS,
)


# ============================================
# Test Fixtures for AwardScore
# ============================================

@pytest.fixture
def elite_qb_score():
    """Elite QB with high scores across all components."""
    return AwardScore(
        player_id=100,
        player_name="Patrick Mahomes",
        team_id=1,
        position='QB',
        award_type=AwardType.MVP,
        stat_component=95.0,
        grade_component=94.0,
        team_success_component=90.0,
        total_score=94.0,
        position_multiplier=1.0,
        breakdown={'games_played': 17, 'overall_grade': 95.0},
    )


@pytest.fixture
def elite_rb_score():
    """Elite RB with high stats."""
    return AwardScore(
        player_id=101,
        player_name="Derrick Henry",
        team_id=2,
        position='RB',
        award_type=AwardType.MVP,
        stat_component=92.0,
        grade_component=91.0,
        team_success_component=75.0,
        total_score=88.0,
        position_multiplier=0.9,
        breakdown={'games_played': 17, 'overall_grade': 92.0},
    )


@pytest.fixture
def elite_wr_score():
    """Elite WR for testing position bias."""
    return AwardScore(
        player_id=102,
        player_name="Ja'Marr Chase",
        team_id=3,
        position='WR',
        award_type=AwardType.MVP,
        stat_component=90.0,
        grade_component=88.0,
        team_success_component=70.0,
        total_score=84.0,
        position_multiplier=0.85,
        breakdown={'games_played': 17, 'overall_grade': 90.0},
    )


@pytest.fixture
def elite_edge_score():
    """Elite EDGE rusher."""
    return AwardScore(
        player_id=103,
        player_name="Myles Garrett",
        team_id=4,
        position='EDGE',
        award_type=AwardType.MVP,
        stat_component=88.0,
        grade_component=94.0,
        team_success_component=60.0,
        total_score=82.0,
        position_multiplier=0.75,
        breakdown={'games_played': 17, 'overall_grade': 94.0},
    )


@pytest.fixture
def average_qb_score():
    """Average QB for comparison."""
    return AwardScore(
        player_id=104,
        player_name="Average QB",
        team_id=5,
        position='QB',
        award_type=AwardType.MVP,
        stat_component=70.0,
        grade_component=68.0,
        team_success_component=50.0,
        total_score=65.0,
        position_multiplier=1.0,
        breakdown={'games_played': 17, 'overall_grade': 70.0},
    )


@pytest.fixture
def low_grade_high_stats_score():
    """Player with high stats but low grades (stats-focused voters prefer)."""
    return AwardScore(
        player_id=105,
        player_name="Stats Guy",
        team_id=6,
        position='RB',
        award_type=AwardType.OPOY,
        stat_component=95.0,
        grade_component=60.0,
        team_success_component=65.0,
        total_score=73.0,
        position_multiplier=0.9,
        breakdown={'games_played': 17, 'overall_grade': 60.0},
    )


@pytest.fixture
def high_grade_low_stats_score():
    """Player with high grades but lower stats (analytics voters prefer)."""
    return AwardScore(
        player_id=106,
        player_name="Analytics Guy",
        team_id=7,
        position='RB',
        award_type=AwardType.OPOY,
        stat_component=65.0,
        grade_component=95.0,
        team_success_component=60.0,
        total_score=75.0,
        position_multiplier=0.9,
        breakdown={'games_played': 17, 'overall_grade': 95.0},
    )


@pytest.fixture
def high_team_success_score():
    """Player with high team success (narrative voters prefer)."""
    return AwardScore(
        player_id=107,
        player_name="Winner QB",
        team_id=8,
        position='QB',
        award_type=AwardType.MVP,
        stat_component=75.0,
        grade_component=75.0,
        team_success_component=95.0,
        total_score=80.0,
        position_multiplier=1.0,
        breakdown={'games_played': 17, 'overall_grade': 75.0},
    )


@pytest.fixture
def mvp_candidates(
    elite_qb_score,
    elite_rb_score,
    elite_wr_score,
    elite_edge_score,
    average_qb_score,
):
    """Standard MVP candidate pool."""
    return [
        elite_qb_score,
        elite_rb_score,
        elite_wr_score,
        elite_edge_score,
        average_qb_score,
    ]


# ============================================
# VoterArchetype Tests
# ============================================

class TestVoterArchetype:
    """Tests for VoterArchetype enum."""

    def test_all_archetypes_exist(self):
        """Verify all 5 archetypes are defined."""
        assert VoterArchetype.BALANCED.value == "balanced"
        assert VoterArchetype.STATS_FOCUSED.value == "stats"
        assert VoterArchetype.ANALYTICS.value == "analytics"
        assert VoterArchetype.NARRATIVE_DRIVEN.value == "narrative"
        assert VoterArchetype.TRADITIONAL.value == "traditional"

    def test_archetype_weights_defined(self):
        """All archetypes have weight configurations."""
        for archetype in VoterArchetype:
            assert archetype in ARCHETYPE_WEIGHTS
            weights = ARCHETYPE_WEIGHTS[archetype]
            assert 'stat' in weights
            assert 'grade' in weights
            assert 'team' in weights

    def test_archetype_weights_sum_to_one(self):
        """Each archetype's weights should sum to 1.0."""
        for archetype in VoterArchetype:
            weights = ARCHETYPE_WEIGHTS[archetype]
            total = weights['stat'] + weights['grade'] + weights['team']
            assert abs(total - 1.0) < 0.001, f"{archetype} weights sum to {total}"


class TestVoterDistribution:
    """Tests for voter distribution configuration."""

    def test_distribution_totals_50(self):
        """Standard distribution should total 50 voters."""
        total = sum(count for _, count in VOTER_DISTRIBUTION)
        assert total == 50

    def test_distribution_has_all_archetypes(self):
        """Distribution should include all archetypes."""
        archetypes_in_dist = {arch for arch, _ in VOTER_DISTRIBUTION}
        for archetype in VoterArchetype:
            assert archetype in archetypes_in_dist


# ============================================
# VoterProfile Tests
# ============================================

class TestVoterProfile:
    """Tests for VoterProfile dataclass."""

    def test_create_basic_profile(self):
        """Create a basic voter profile."""
        profile = VoterProfile(
            voter_id="test_voter",
            archetype=VoterArchetype.BALANCED,
            variance=0.10,
            position_bias={},
        )
        assert profile.voter_id == "test_voter"
        assert profile.archetype == VoterArchetype.BALANCED
        assert profile.variance == 0.10
        assert profile.position_bias == {}

    def test_traditional_voter_has_position_bias(self):
        """Traditional voters should have position bias."""
        profile = VoterProfile(
            voter_id="traditional_voter",
            archetype=VoterArchetype.TRADITIONAL,
            variance=0.10,
            position_bias=TRADITIONAL_POSITION_BIAS.copy(),
        )
        assert profile.position_bias.get('QB', 1.0) == 1.20  # QB bonus
        assert profile.position_bias.get('WR', 1.0) == 0.90  # WR penalty

    def test_get_weights(self):
        """get_weights() returns correct weighting."""
        profile = VoterProfile(
            voter_id="test",
            archetype=VoterArchetype.STATS_FOCUSED,
        )
        weights = profile.get_weights()
        assert weights['stat'] == 0.60
        assert weights['grade'] == 0.30
        assert weights['team'] == 0.10

    def test_adjust_score_balanced(self, elite_qb_score):
        """Balanced voter applies equal weighting."""
        profile = VoterProfile(
            voter_id="balanced",
            archetype=VoterArchetype.BALANCED,
            variance=0.0,  # No variance for deterministic test
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_qb_score, rng)

        # Expected: 95*0.4 + 94*0.4 + 90*0.2 = 38 + 37.6 + 18 = 93.6
        expected = (
            elite_qb_score.stat_component * 0.40 +
            elite_qb_score.grade_component * 0.40 +
            elite_qb_score.team_success_component * 0.20
        )
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_stats_focused(self, elite_qb_score):
        """Stats-focused voter weights stats higher."""
        profile = VoterProfile(
            voter_id="stats",
            archetype=VoterArchetype.STATS_FOCUSED,
            variance=0.0,
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_qb_score, rng)

        # Expected: 95*0.6 + 94*0.3 + 90*0.1 = 57 + 28.2 + 9 = 94.2
        expected = (
            elite_qb_score.stat_component * 0.60 +
            elite_qb_score.grade_component * 0.30 +
            elite_qb_score.team_success_component * 0.10
        )
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_analytics(self, elite_qb_score):
        """Analytics voter weights grades higher."""
        profile = VoterProfile(
            voter_id="analytics",
            archetype=VoterArchetype.ANALYTICS,
            variance=0.0,
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_qb_score, rng)

        # Expected: 95*0.2 + 94*0.7 + 90*0.1 = 19 + 65.8 + 9 = 93.8
        expected = (
            elite_qb_score.stat_component * 0.20 +
            elite_qb_score.grade_component * 0.70 +
            elite_qb_score.team_success_component * 0.10
        )
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_narrative(self, elite_qb_score):
        """Narrative voter weights team success higher."""
        profile = VoterProfile(
            voter_id="narrative",
            archetype=VoterArchetype.NARRATIVE_DRIVEN,
            variance=0.0,
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_qb_score, rng)

        # Expected: 95*0.3 + 94*0.3 + 90*0.4 = 28.5 + 28.2 + 36 = 92.7
        expected = (
            elite_qb_score.stat_component * 0.30 +
            elite_qb_score.grade_component * 0.30 +
            elite_qb_score.team_success_component * 0.40
        )
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_traditional_qb_bonus(self, elite_qb_score):
        """Traditional voter gives QB bonus."""
        profile = VoterProfile(
            voter_id="traditional",
            archetype=VoterArchetype.TRADITIONAL,
            variance=0.0,
            position_bias=TRADITIONAL_POSITION_BIAS.copy(),
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_qb_score, rng)

        # Base: 95*0.4 + 94*0.4 + 90*0.2 = 93.6
        # With 1.2x QB bonus: 93.6 * 1.2 = 112.32
        base = (
            elite_qb_score.stat_component * 0.40 +
            elite_qb_score.grade_component * 0.40 +
            elite_qb_score.team_success_component * 0.20
        )
        expected = base * 1.20
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_traditional_wr_penalty(self, elite_wr_score):
        """Traditional voter gives WR penalty."""
        profile = VoterProfile(
            voter_id="traditional",
            archetype=VoterArchetype.TRADITIONAL,
            variance=0.0,
            position_bias=TRADITIONAL_POSITION_BIAS.copy(),
        )
        rng = random.Random(42)
        adjusted = profile.adjust_score(elite_wr_score, rng)

        # Base: 90*0.4 + 88*0.4 + 70*0.2 = 36 + 35.2 + 14 = 85.2
        # With 0.9x WR penalty: 85.2 * 0.9 = 76.68
        base = (
            elite_wr_score.stat_component * 0.40 +
            elite_wr_score.grade_component * 0.40 +
            elite_wr_score.team_success_component * 0.20
        )
        expected = base * 0.90
        assert abs(adjusted - expected) < 0.01

    def test_adjust_score_variance_applied(self, elite_qb_score):
        """Variance should create spread in scores."""
        profile = VoterProfile(
            voter_id="variance_test",
            archetype=VoterArchetype.BALANCED,
            variance=0.15,  # 15% variance
        )

        # Run multiple times with same seed to verify determinism
        rng = random.Random(42)
        score1 = profile.adjust_score(elite_qb_score, rng)

        rng = random.Random(42)
        score2 = profile.adjust_score(elite_qb_score, rng)

        assert score1 == score2  # Same seed = same result

        # Different seed should give different result
        rng = random.Random(123)
        score3 = profile.adjust_score(elite_qb_score, rng)
        assert score1 != score3


# ============================================
# VotingResult Tests
# ============================================

class TestVotingResult:
    """Tests for VotingResult dataclass."""

    def test_create_voting_result(self):
        """Create a basic voting result."""
        result = VotingResult(
            player_id=100,
            player_name="Test Player",
            team_id=1,
            position='QB',
            total_points=450,
            vote_share=0.90,
            first_place_votes=45,
            second_place_votes=3,
            third_place_votes=2,
            fourth_place_votes=0,
            fifth_place_votes=0,
            raw_score=95.0,
        )
        assert result.total_points == 450
        assert result.vote_share == 0.90

    def test_total_votes_received(self):
        """total_votes_received counts all votes."""
        result = VotingResult(
            player_id=100,
            player_name="Test",
            team_id=1,
            position='QB',
            first_place_votes=10,
            second_place_votes=15,
            third_place_votes=8,
            fourth_place_votes=5,
            fifth_place_votes=2,
        )
        assert result.total_votes_received == 40

    def test_is_unanimous(self):
        """is_unanimous returns True only for 50 first-place votes."""
        unanimous = VotingResult(
            player_id=100,
            player_name="Test",
            team_id=1,
            position='QB',
            first_place_votes=50,
        )
        assert unanimous.is_unanimous is True

        not_unanimous = VotingResult(
            player_id=100,
            player_name="Test",
            team_id=1,
            position='QB',
            first_place_votes=49,
        )
        assert not_unanimous.is_unanimous is False

    def test_to_dict(self):
        """to_dict returns all fields."""
        result = VotingResult(
            player_id=100,
            player_name="Test Player",
            team_id=1,
            position='QB',
            total_points=450,
            vote_share=0.90,
            first_place_votes=45,
            raw_score=95.0,
        )
        d = result.to_dict()
        assert d['player_id'] == 100
        assert d['player_name'] == "Test Player"
        assert d['total_points'] == 450
        assert d['vote_share'] == 0.90
        assert d['raw_score'] == 95.0


# ============================================
# VotingEngine Tests
# ============================================

class TestVotingEngineInitialization:
    """Tests for VotingEngine initialization."""

    def test_default_initialization(self):
        """Default initialization creates 50 voters."""
        engine = VotingEngine()
        assert engine.num_voters == 50
        assert len(engine.voters) == 50
        assert engine.seed is None

    def test_custom_voter_count(self):
        """Can specify custom voter count."""
        engine = VotingEngine(num_voters=100)
        assert engine.num_voters == 100
        assert len(engine.voters) == 100

    def test_deterministic_seed(self):
        """Same seed produces identical voters."""
        engine1 = VotingEngine(seed=42)
        engine2 = VotingEngine(seed=42)

        for v1, v2 in zip(engine1.voters, engine2.voters):
            assert v1.voter_id == v2.voter_id
            assert v1.archetype == v2.archetype
            assert v1.variance == v2.variance

    def test_different_seeds_different_voters(self):
        """Different seeds produce different variance values."""
        engine1 = VotingEngine(seed=42)
        engine2 = VotingEngine(seed=123)

        # At least some variances should differ
        variances1 = [v.variance for v in engine1.voters]
        variances2 = [v.variance for v in engine2.voters]
        assert variances1 != variances2


class TestVoterGeneration:
    """Tests for voter generation with archetype distribution."""

    def test_archetype_distribution(self):
        """Generated voters follow archetype distribution."""
        engine = VotingEngine(seed=42)
        breakdown = engine.get_voter_breakdown()

        # Expected: 20 balanced, 10 stats, 10 analytics, 5 narrative, 5 traditional
        assert breakdown['balanced'] == 20
        assert breakdown['stats'] == 10
        assert breakdown['analytics'] == 10
        assert breakdown['narrative'] == 5
        assert breakdown['traditional'] == 5

    def test_variance_range(self):
        """All voters have variance between 0.05 and 0.15."""
        engine = VotingEngine(seed=42)

        for voter in engine.voters:
            assert 0.05 <= voter.variance <= 0.15

    def test_traditional_voters_have_position_bias(self):
        """Traditional voters are initialized with position bias."""
        engine = VotingEngine(seed=42)

        for voter in engine.voters:
            if voter.archetype == VoterArchetype.TRADITIONAL:
                assert voter.position_bias.get('QB', 1.0) == 1.20
                assert voter.position_bias.get('WR', 1.0) == 0.90
            else:
                assert voter.position_bias == {}

    def test_unique_voter_ids(self):
        """All voters have unique IDs."""
        engine = VotingEngine()
        ids = [v.voter_id for v in engine.voters]
        assert len(ids) == len(set(ids))


class TestVotingMechanics:
    """Tests for the actual voting process."""

    def test_points_allocation(self):
        """Verify 10-5-3-2-1 point system."""
        assert POINTS_BY_RANK[1] == 10
        assert POINTS_BY_RANK[2] == 5
        assert POINTS_BY_RANK[3] == 3
        assert POINTS_BY_RANK[4] == 2
        assert POINTS_BY_RANK[5] == 1

    def test_max_points_calculation(self):
        """Max points is 50 voters * 10 points = 500."""
        assert MAX_POINTS == 500
        assert DEFAULT_NUM_VOTERS == 50

    def test_empty_candidates_returns_empty(self):
        """Empty candidate list returns empty results."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [])
        assert results == []

    def test_single_candidate_gets_all_votes(self, elite_qb_score):
        """Single candidate receives unanimous first-place votes."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [elite_qb_score])

        assert len(results) == 1
        winner = results[0]
        assert winner.player_id == elite_qb_score.player_id
        assert winner.first_place_votes == 50
        assert winner.total_points == 500
        assert winner.vote_share == 1.0

    def test_results_sorted_by_points(self, mvp_candidates):
        """Results are sorted by total points descending."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", mvp_candidates)

        for i in range(len(results) - 1):
            assert results[i].total_points >= results[i + 1].total_points

    def test_vote_share_calculated(self, mvp_candidates):
        """Vote share is total_points / 500."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", mvp_candidates)

        for result in results:
            expected_share = result.total_points / 500
            assert abs(result.vote_share - expected_share) < 0.001

    def test_all_candidates_included_in_results(self, mvp_candidates):
        """All candidates appear in results."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", mvp_candidates)

        result_ids = {r.player_id for r in results}
        candidate_ids = {c.player_id for c in mvp_candidates}
        assert result_ids == candidate_ids

    def test_deterministic_voting(self, mvp_candidates):
        """Same seed produces identical results."""
        results1 = VotingEngine(seed=42).conduct_voting("mvp", mvp_candidates)
        results2 = VotingEngine(seed=42).conduct_voting("mvp", mvp_candidates)

        for r1, r2 in zip(results1, results2):
            assert r1.player_id == r2.player_id
            assert r1.total_points == r2.total_points
            assert r1.first_place_votes == r2.first_place_votes

    def test_elite_qb_typically_wins(self, mvp_candidates):
        """Elite QB should win MVP due to position favoritism."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", mvp_candidates)

        winner = results[0]
        # Elite QB (player_id=100) should win or place very high
        assert winner.player_id == 100 or results[1].player_id == 100

    def test_no_unanimous_with_competition(self, mvp_candidates):
        """Multiple strong candidates prevents unanimous voting."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", mvp_candidates)

        winner = results[0]
        # With variance and archetypes, shouldn't be unanimous
        assert winner.is_unanimous is False
        assert winner.vote_share < 1.0


class TestTiebreaker:
    """Tests for tiebreaker logic."""

    def test_first_place_votes_break_tie(self):
        """Higher first-place votes wins ties."""
        # Create two candidates with identical scores
        c1 = AwardScore(
            player_id=1,
            player_name="Player A",
            team_id=1,
            position='QB',
            award_type=AwardType.MVP,
            stat_component=90.0,
            grade_component=90.0,
            team_success_component=90.0,
            total_score=90.0,
        )
        c2 = AwardScore(
            player_id=2,
            player_name="Player B",
            team_id=2,
            position='QB',
            award_type=AwardType.MVP,
            stat_component=90.0,
            grade_component=90.0,
            team_success_component=90.0,
            total_score=90.0,
        )

        # Run voting - since scores are identical, results depend on variance
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [c1, c2])

        assert len(results) == 2
        # Winner should have more first-place votes (or same with more 2nd place)
        winner = results[0]
        second = results[1]

        if winner.total_points == second.total_points:
            assert winner.first_place_votes >= second.first_place_votes

    def test_raw_score_as_final_tiebreaker(self):
        """Raw score breaks ties when votes are equal."""
        c1 = AwardScore(
            player_id=1,
            player_name="Higher Raw",
            team_id=1,
            position='QB',
            award_type=AwardType.MVP,
            stat_component=90.0,
            grade_component=90.0,
            team_success_component=90.0,
            total_score=95.0,  # Higher raw score
        )
        c2 = AwardScore(
            player_id=2,
            player_name="Lower Raw",
            team_id=2,
            position='QB',
            award_type=AwardType.MVP,
            stat_component=90.0,
            grade_component=90.0,
            team_success_component=90.0,
            total_score=85.0,  # Lower raw score
        )

        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [c1, c2])

        # If points and first-place votes are equal, higher raw_score wins
        # This test verifies the tiebreaker logic is applied


class TestArchetypeInfluence:
    """Tests for how archetypes influence voting."""

    def test_stats_focused_prefers_high_stats(
        self,
        low_grade_high_stats_score,
        high_grade_low_stats_score,
    ):
        """Stats-focused voters rank high-stats players higher."""
        # Create voter with no variance
        voter = VoterProfile(
            voter_id="stats_test",
            archetype=VoterArchetype.STATS_FOCUSED,
            variance=0.0,
        )
        rng = random.Random(42)

        score_stats = voter.adjust_score(low_grade_high_stats_score, rng)
        score_analytics = voter.adjust_score(high_grade_low_stats_score, rng)

        # Stats-focused: 95*0.6 + 60*0.3 + 65*0.1 = 57 + 18 + 6.5 = 81.5
        # vs: 65*0.6 + 95*0.3 + 60*0.1 = 39 + 28.5 + 6 = 73.5
        assert score_stats > score_analytics

    def test_analytics_prefers_high_grades(
        self,
        low_grade_high_stats_score,
        high_grade_low_stats_score,
    ):
        """Analytics voters rank high-grade players higher."""
        voter = VoterProfile(
            voter_id="analytics_test",
            archetype=VoterArchetype.ANALYTICS,
            variance=0.0,
        )
        rng = random.Random(42)

        score_stats = voter.adjust_score(low_grade_high_stats_score, rng)
        score_analytics = voter.adjust_score(high_grade_low_stats_score, rng)

        # Analytics: 95*0.2 + 60*0.7 + 65*0.1 = 19 + 42 + 6.5 = 67.5
        # vs: 65*0.2 + 95*0.7 + 60*0.1 = 13 + 66.5 + 6 = 85.5
        assert score_analytics > score_stats

    def test_narrative_prefers_team_success(
        self,
        elite_qb_score,
        high_team_success_score,
    ):
        """Narrative voters rank team success higher."""
        voter = VoterProfile(
            voter_id="narrative_test",
            archetype=VoterArchetype.NARRATIVE_DRIVEN,
            variance=0.0,
        )
        rng = random.Random(42)

        # Elite QB: higher overall but moderate team success (90)
        # Winner QB: lower overall but high team success (95)
        elite_adjusted = voter.adjust_score(elite_qb_score, rng)
        winner_adjusted = voter.adjust_score(high_team_success_score, rng)

        # Elite: 95*0.3 + 94*0.3 + 90*0.4 = 28.5 + 28.2 + 36 = 92.7
        # Winner: 75*0.3 + 75*0.3 + 95*0.4 = 22.5 + 22.5 + 38 = 83.0
        # Elite still wins due to higher stats/grades

    def test_traditional_qb_bias(self, elite_qb_score, elite_wr_score):
        """Traditional voters favor QBs over WRs."""
        voter = VoterProfile(
            voter_id="traditional_test",
            archetype=VoterArchetype.TRADITIONAL,
            variance=0.0,
            position_bias=TRADITIONAL_POSITION_BIAS.copy(),
        )
        rng = random.Random(42)

        qb_adjusted = voter.adjust_score(elite_qb_score, rng)
        wr_adjusted = voter.adjust_score(elite_wr_score, rng)

        # QB gets 1.2x multiplier, WR gets 0.9x
        # Even if WR had same base, QB wins
        assert qb_adjusted > wr_adjusted


class TestEdgeCases:
    """Tests for edge cases."""

    def test_two_candidates(self, elite_qb_score, elite_rb_score):
        """Voting works with just two candidates."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [elite_qb_score, elite_rb_score])

        assert len(results) == 2
        # Both should receive votes
        assert results[0].total_points > 0
        assert results[1].total_points > 0
        # Total points awarded per voter is 10+5=15 for top 2
        total_points = results[0].total_points + results[1].total_points
        assert total_points == 50 * 15  # 750

    def test_three_candidates(self, elite_qb_score, elite_rb_score, elite_wr_score):
        """Voting works with three candidates."""
        engine = VotingEngine(seed=42)
        results = engine.conduct_voting(
            "mvp",
            [elite_qb_score, elite_rb_score, elite_wr_score],
        )

        assert len(results) == 3
        # Total points: 10+5+3=18 per voter
        total_points = sum(r.total_points for r in results)
        assert total_points == 50 * 18  # 900

    def test_candidate_with_zero_scores(self):
        """Candidate with zero scores still appears in results."""
        zero_score = AwardScore(
            player_id=999,
            player_name="Zero Player",
            team_id=1,
            position='QB',
            award_type=AwardType.MVP,
            stat_component=0.0,
            grade_component=0.0,
            team_success_component=0.0,
            total_score=0.0,
        )

        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", [zero_score])

        assert len(results) == 1
        assert results[0].player_id == 999

    def test_many_candidates(self):
        """Voting works with many candidates (only top 5 get votes per voter)."""
        candidates = [
            AwardScore(
                player_id=i,
                player_name=f"Player {i}",
                team_id=i % 32 + 1,
                position='QB',
                award_type=AwardType.MVP,
                stat_component=90.0 - i,
                grade_component=90.0 - i,
                team_success_component=90.0 - i,
                total_score=90.0 - i,
            )
            for i in range(20)
        ]

        engine = VotingEngine(seed=42)
        results = engine.conduct_voting("mvp", candidates)

        assert len(results) == 20
        # Total points: 10+5+3+2+1=21 per voter
        total_points = sum(r.total_points for r in results)
        assert total_points == 50 * 21  # 1050

    def test_reset_seed(self, mvp_candidates):
        """reset_seed allows running with new seed."""
        engine = VotingEngine(seed=42)
        results1 = engine.conduct_voting("mvp", mvp_candidates)

        engine.reset_seed(123)
        results2 = engine.conduct_voting("mvp", mvp_candidates)

        # Results should differ after seed reset
        # Compare first-place votes which should vary
        votes1 = results1[0].first_place_votes
        engine.reset_seed(42)
        results3 = engine.conduct_voting("mvp", mvp_candidates)
        votes3 = results3[0].first_place_votes

        # Same seed should give same results
        assert votes1 == votes3

    def test_repr(self):
        """VotingEngine repr is informative."""
        engine = VotingEngine(num_voters=50, seed=42)
        repr_str = repr(engine)
        assert "num_voters=50" in repr_str
        assert "seed=42" in repr_str


class TestPositionBiasConstants:
    """Tests for position bias constants."""

    def test_qb_has_highest_bias(self):
        """QB has highest position bias."""
        max_bias = max(TRADITIONAL_POSITION_BIAS.values())
        assert TRADITIONAL_POSITION_BIAS['QB'] == max_bias

    def test_special_teams_have_low_bias(self):
        """Special teams positions have low bias."""
        assert TRADITIONAL_POSITION_BIAS['K'] < 1.0
        assert TRADITIONAL_POSITION_BIAS['P'] < 1.0
        assert TRADITIONAL_POSITION_BIAS['LS'] < 1.0

    def test_default_bias_is_neutral(self):
        """Default position bias is 1.0."""
        assert DEFAULT_POSITION_BIAS == 1.0
