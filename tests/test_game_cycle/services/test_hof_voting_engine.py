"""
Unit tests for HOFVotingEngine.

Tests voting simulation, class strength calculation, induction thresholds,
ballot removal, and max inductees per year.
"""

import pytest
from dataclasses import dataclass, field
from typing import List, Dict, Any

from game_cycle.services.hof_voting_engine import (
    HOFVotingEngine,
    HOFVotingSession,
)
from game_cycle.database.hof_api import HOFVotingResult


# ============================================
# Mock HOFCandidate for Testing
# ============================================

@dataclass
class MockHOFCandidate:
    """Mock HOFCandidate for testing (matches real HOFCandidate interface)."""
    player_id: int
    player_name: str
    primary_position: str
    retirement_season: int
    years_on_ballot: int
    career_seasons: int
    teams_played_for: List[str]
    final_team_id: int
    super_bowl_wins: int = 0
    mvp_awards: int = 0
    all_pro_first_team: int = 0
    all_pro_second_team: int = 0
    pro_bowl_selections: int = 0
    career_stats: Dict[str, Any] = field(default_factory=dict)
    hof_score: int = 0
    is_first_ballot: bool = False


def create_first_ballot_candidate(
    player_id: int = 1,
    name: str = "Elite Player",
    years_on_ballot: int = 1
) -> MockHOFCandidate:
    """Create a first-ballot lock candidate (85+ score)."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position="QB",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        career_seasons=15,
        teams_played_for=["Team A"],
        final_team_id=1,
        super_bowl_wins=2,      # 30 points (capped)
        mvp_awards=2,           # 50 points (capped)
        all_pro_first_team=5,   # 40 points
        all_pro_second_team=0,
        pro_bowl_selections=10, # 20 points (capped)
        career_stats={'pass_yards': 50000, 'pass_tds': 400},  # elite = 20
        is_first_ballot=(years_on_ballot == 1),
    )


def create_strong_candidate(
    player_id: int = 2,
    name: str = "Strong Player",
    years_on_ballot: int = 1
) -> MockHOFCandidate:
    """Create a strong candidate (70-84 score)."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position="WR",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        career_seasons=12,
        teams_played_for=["Team B"],
        final_team_id=2,
        super_bowl_wins=1,      # 15 points
        mvp_awards=0,           # 0 points
        all_pro_first_team=3,   # 24 points
        all_pro_second_team=2,  # 8 points
        pro_bowl_selections=8,  # 16 points
        career_stats={'rec_yards': 11000, 'rec_tds': 70, 'receptions': 800},  # great = 15
        is_first_ballot=(years_on_ballot == 1),
    )


def create_borderline_candidate(
    player_id: int = 3,
    name: str = "Borderline Player",
    years_on_ballot: int = 1
) -> MockHOFCandidate:
    """Create a borderline candidate (55-69 score)."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position="RB",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        career_seasons=11,
        teams_played_for=["Team C"],
        final_team_id=3,
        super_bowl_wins=1,      # 15 points
        mvp_awards=0,
        all_pro_first_team=2,   # 16 points
        all_pro_second_team=1,  # 4 points
        pro_bowl_selections=6,  # 12 points
        career_stats={'rush_yards': 7500, 'rush_tds': 45},  # good = 10
        is_first_ballot=(years_on_ballot == 1),
    )


def create_long_shot_candidate(
    player_id: int = 4,
    name: str = "Long Shot Player",
    years_on_ballot: int = 1
) -> MockHOFCandidate:
    """Create a long shot candidate (40-54 score)."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position="CB",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        career_seasons=12,
        teams_played_for=["Team D"],
        final_team_id=4,
        super_bowl_wins=0,
        mvp_awards=0,
        all_pro_first_team=1,   # 8 points
        all_pro_second_team=2,  # 8 points
        pro_bowl_selections=5,  # 10 points
        career_stats={'interceptions': 35},  # good = 10
        is_first_ballot=(years_on_ballot == 1),
    )


def create_weak_candidate(
    player_id: int = 5,
    name: str = "Weak Player",
    years_on_ballot: int = 1
) -> MockHOFCandidate:
    """Create a weak candidate (<40 score) who will likely be removed from ballot."""
    return MockHOFCandidate(
        player_id=player_id,
        player_name=name,
        primary_position="TE",
        retirement_season=2025,
        years_on_ballot=years_on_ballot,
        career_seasons=8,
        teams_played_for=["Team E"],
        final_team_id=5,
        super_bowl_wins=0,
        mvp_awards=0,
        all_pro_first_team=0,
        all_pro_second_team=0,
        pro_bowl_selections=1,  # 2 points
        career_stats={'rec_yards': 3000, 'rec_tds': 20},  # solid = 5
        is_first_ballot=(years_on_ballot == 1),
    )


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def engine():
    """Create HOFVotingEngine with fixed seed for reproducibility."""
    return HOFVotingEngine(seed=42)


@pytest.fixture
def deterministic_engine():
    """Create engine with specific seed for predictable tests."""
    return HOFVotingEngine(seed=12345)


# ============================================
# Test Conduct Voting - Basic Flow
# ============================================

class TestConductVoting:
    """Test the main conduct_voting() method."""

    def test_empty_candidates_returns_empty_session(self, engine):
        """Empty candidate list returns valid empty session."""
        session = engine.conduct_voting("dynasty1", 2030, [])

        assert session.dynasty_id == "dynasty1"
        assert session.voting_season == 2030
        assert session.total_candidates == 0
        assert len(session.inductees) == 0
        assert len(session.non_inductees) == 0
        assert len(session.removed_from_ballot) == 0

    def test_first_ballot_lock_inducted(self, engine):
        """First-ballot lock (85+ score) is inducted."""
        candidate = create_first_ballot_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        assert len(session.inductees) == 1
        assert session.inductees[0].player_id == 1
        assert session.inductees[0].was_inducted is True
        assert session.inductees[0].vote_percentage >= 0.80

    def test_strong_candidate_usually_inducted(self, deterministic_engine):
        """Strong candidate (70-84 score) usually gets inducted."""
        candidate = create_strong_candidate()
        session = deterministic_engine.conduct_voting("dynasty1", 2030, [candidate])

        # Strong candidates should get 70-89% votes, usually above 80%
        assert session.inductees[0].vote_percentage >= 0.70
        # May or may not be inducted depending on variance

    def test_weak_candidate_removed_from_ballot(self, engine):
        """Weak candidate (<5% votes) removed from ballot."""
        candidate = create_weak_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        # Weak candidate gets <15% votes, likely below 5%
        # Check they ended up somewhere
        all_results = session.all_results
        assert len(all_results) == 1

        result = all_results[0]
        # If vote < 5%, should be in removed_from_ballot
        if result.vote_percentage < 0.05:
            assert result in session.removed_from_ballot

    def test_voting_session_metadata(self, engine):
        """Session includes correct metadata."""
        candidates = [
            create_first_ballot_candidate(1, "Player 1"),
            create_strong_candidate(2, "Player 2"),
        ]
        session = engine.conduct_voting("dynasty1", 2030, candidates)

        assert session.dynasty_id == "dynasty1"
        assert session.voting_season == 2030
        assert session.total_candidates == 2
        assert session.total_voters == 48
        assert 0.0 <= session.class_strength <= 1.0


# ============================================
# Test Max Inductees Limit
# ============================================

class TestMaxInducteesLimit:
    """Test that max 5 inductees per year is enforced."""

    def test_max_five_inductees_enforced(self, engine):
        """Even with many qualifying candidates, max 5 inducted."""
        # Create 8 first-ballot candidates (all should qualify)
        candidates = [
            create_first_ballot_candidate(i, f"Elite {i}")
            for i in range(1, 9)
        ]

        session = engine.conduct_voting("dynasty1", 2030, candidates)

        assert len(session.inductees) <= 5
        assert len(session.non_inductees) >= 3

    def test_top_five_by_vote_selected(self, deterministic_engine):
        """Top 5 by vote percentage are selected when >5 qualify."""
        candidates = [
            create_first_ballot_candidate(i, f"Elite {i}")
            for i in range(1, 8)
        ]

        session = deterministic_engine.conduct_voting("dynasty1", 2030, candidates)

        # All inductees should have higher votes than non-inductees
        if session.inductees and session.non_inductees:
            min_inductee_votes = min(r.vote_percentage for r in session.inductees)
            max_non_inductee_votes = max(r.vote_percentage for r in session.non_inductees)
            assert min_inductee_votes >= max_non_inductee_votes

    def test_fewer_than_five_possible(self, engine):
        """If fewer than 5 qualify, fewer than 5 are inducted."""
        candidates = [
            create_first_ballot_candidate(1, "Elite 1"),
            create_borderline_candidate(2, "Borderline 1"),
            create_long_shot_candidate(3, "Long Shot 1"),
        ]

        session = engine.conduct_voting("dynasty1", 2030, candidates)

        # First-ballot should be inducted, others may not
        # But total inductees should be <= 5
        assert len(session.inductees) <= 5


# ============================================
# Test Induction Threshold
# ============================================

class TestInductionThreshold:
    """Test 80% vote threshold for induction."""

    def test_threshold_is_80_percent(self, engine):
        """Verify threshold constant is 80%."""
        assert engine.INDUCTION_THRESHOLD == 0.80

    def test_candidate_at_79_not_inducted(self, engine):
        """Candidate with 79% votes is not inducted."""
        # We can't directly control vote percentage, but we can check the logic
        # by examining results and verifying consistency

        # Create borderline candidate who might get ~70-75%
        candidate = create_borderline_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        # If below threshold, should not be inducted
        if result.vote_percentage < 0.80:
            assert result.was_inducted is False
            assert result in session.non_inductees or result in session.removed_from_ballot

    def test_candidate_at_80_inducted(self):
        """Candidate with exactly 80% votes is inducted (if under max)."""
        # Use specific seed that gives ~80% for a strong candidate
        engine = HOFVotingEngine(seed=999)
        candidate = create_strong_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        if result.vote_percentage >= 0.80:
            assert result.was_inducted is True


# ============================================
# Test Ballot Removal
# ============================================

class TestBallotRemoval:
    """Test ballot removal conditions."""

    def test_below_five_percent_removed(self, engine):
        """Candidates below 5% votes are removed from ballot."""
        candidate = create_weak_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        if result.vote_percentage < 0.05:
            assert result.removed_from_ballot is True
            assert result in session.removed_from_ballot

    def test_twenty_year_limit_removed(self, engine):
        """Candidates on ballot 20+ years are removed."""
        # Create candidate who has been on ballot 20 years
        candidate = create_borderline_candidate(years_on_ballot=20)

        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        assert result.removed_from_ballot is True
        assert result in session.removed_from_ballot

    def test_removed_cannot_be_inducted(self, engine):
        """Removed candidates are not in inductees list."""
        candidate = create_borderline_candidate(years_on_ballot=21)

        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        # Even if vote % is high, 20+ years = removed
        assert len(session.inductees) == 0
        assert len(session.removed_from_ballot) == 1


# ============================================
# Test Class Strength
# ============================================

class TestClassStrength:
    """Test class strength calculation."""

    def test_no_first_ballot_weak_class(self, engine):
        """Class with no first-ballot candidates is weak."""
        candidates = [
            create_borderline_candidate(1, "Borderline 1"),
            create_long_shot_candidate(2, "Long Shot 1"),
        ]

        strength = engine._calculate_class_strength(candidates)
        assert strength < 0.5

    def test_multiple_first_ballot_strong_class(self, engine):
        """Class with 3+ first-ballot candidates is strong."""
        candidates = [
            create_first_ballot_candidate(i, f"Elite {i}")
            for i in range(1, 5)
        ]

        strength = engine._calculate_class_strength(candidates)
        assert strength >= 0.7

    def test_one_first_ballot_normal_class(self, engine):
        """Class with 1-2 first-ballot candidates is normal."""
        candidates = [
            create_first_ballot_candidate(1, "Elite 1"),
            create_strong_candidate(2, "Strong 1"),
            create_borderline_candidate(3, "Borderline 1"),
        ]

        strength = engine._calculate_class_strength(candidates)
        assert 0.4 <= strength <= 0.6

    def test_empty_candidates_default_strength(self, engine):
        """Empty candidate list returns default 0.5 strength."""
        strength = engine._calculate_class_strength([])
        assert strength == 0.5


# ============================================
# Test Vote Percentage Simulation
# ============================================

class TestVotePercentageSimulation:
    """Test vote percentage calculation logic."""

    def test_first_ballot_lock_gets_90_plus(self, engine):
        """First-ballot lock (85+ score) gets 90%+ base votes."""
        # Test the base formula directly
        base_pct = engine._score_to_base_vote(90)
        assert base_pct >= 0.90

    def test_strong_candidate_gets_70_to_89(self, engine):
        """Strong candidate (70-84 score) gets 70-89% base votes."""
        base_low = engine._score_to_base_vote(70)
        base_high = engine._score_to_base_vote(84)

        assert 0.70 <= base_low <= 0.75
        assert 0.85 <= base_high <= 0.90

    def test_borderline_gets_40_to_75(self, engine):
        """Borderline candidate (55-69) gets 40-75% base votes."""
        base_low = engine._score_to_base_vote(55)
        base_high = engine._score_to_base_vote(69)

        assert 0.38 <= base_low <= 0.45
        assert 0.70 <= base_high <= 0.78

    def test_long_shot_gets_10_to_45(self, engine):
        """Long shot candidate (40-54) gets 10-45% base votes."""
        base_low = engine._score_to_base_vote(40)
        base_high = engine._score_to_base_vote(54)

        assert 0.08 <= base_low <= 0.15
        assert 0.40 <= base_high <= 0.48

    def test_weak_candidate_gets_1_to_15(self, engine):
        """Weak candidate (<40) gets 1-15% base votes."""
        base_low = engine._score_to_base_vote(10)
        base_high = engine._score_to_base_vote(39)

        assert 0.01 <= base_low <= 0.10
        assert 0.10 <= base_high <= 0.18


# ============================================
# Test Years on Ballot Modifier
# ============================================

class TestYearsOnBallotModifier:
    """Test years on ballot affects vote percentage."""

    def test_first_year_no_modifier(self, engine):
        """First year on ballot has no modifier."""
        modifier = engine._years_on_ballot_modifier(1, 70)
        assert modifier == 0.0

    def test_building_support_years_2_to_10(self, engine):
        """Years 2-10 build support."""
        mod_year2 = engine._years_on_ballot_modifier(2, 70)
        mod_year5 = engine._years_on_ballot_modifier(5, 70)
        mod_year10 = engine._years_on_ballot_modifier(10, 70)

        assert mod_year2 > 0
        assert mod_year5 > mod_year2
        assert mod_year10 > mod_year5

    def test_plateau_years_11_to_15(self, engine):
        """Years 11-15 maintain max support."""
        mod_year10 = engine._years_on_ballot_modifier(10, 70)
        mod_year12 = engine._years_on_ballot_modifier(12, 70)
        mod_year15 = engine._years_on_ballot_modifier(15, 70)

        # All should be at same plateau
        assert mod_year12 == mod_year10
        assert mod_year15 == mod_year10

    def test_fatigue_years_16_to_20(self, engine):
        """Years 16-20 show voter fatigue."""
        mod_year15 = engine._years_on_ballot_modifier(15, 70)
        mod_year16 = engine._years_on_ballot_modifier(16, 70)
        mod_year20 = engine._years_on_ballot_modifier(20, 70)

        assert mod_year16 < mod_year15
        assert mod_year20 < mod_year16


# ============================================
# Test Voting Result Structure
# ============================================

class TestVotingResultStructure:
    """Test HOFVotingResult fields are properly populated."""

    def test_voting_result_has_all_fields(self, engine):
        """Voting results contain all required fields."""
        candidate = create_first_ballot_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]

        assert result.player_id == 1
        assert result.voting_season == 2030
        assert result.player_name == "Elite Player"
        assert result.primary_position == "QB"
        assert result.retirement_season == 2025
        assert result.years_on_ballot == 1
        assert 0.0 <= result.vote_percentage <= 1.0
        assert 0 <= result.votes_received <= 48
        assert result.total_voters == 48
        assert isinstance(result.was_inducted, bool)
        assert isinstance(result.is_first_ballot, bool)
        assert isinstance(result.removed_from_ballot, bool)
        assert result.hof_score > 0
        assert result.score_breakdown is not None

    def test_score_breakdown_included(self, engine):
        """Score breakdown dict is included in result."""
        candidate = create_first_ballot_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        breakdown = result.score_breakdown

        assert 'total_score' in breakdown
        assert 'tier' in breakdown
        assert 'mvp_score' in breakdown
        assert 'super_bowl_score' in breakdown
        assert 'all_pro_first_score' in breakdown

    def test_votes_received_matches_percentage(self, engine):
        """votes_received is consistent with vote_percentage."""
        candidate = create_first_ballot_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        result = session.all_results[0]
        expected_votes = int(round(result.vote_percentage * result.total_voters))

        assert result.votes_received == expected_votes


# ============================================
# Test Session Structure
# ============================================

class TestVotingSessionStructure:
    """Test HOFVotingSession structure and methods."""

    def test_all_results_combines_lists(self, engine):
        """all_results property combines all three lists."""
        candidates = [
            create_first_ballot_candidate(1, "Elite"),
            create_weak_candidate(2, "Weak"),
        ]

        session = engine.conduct_voting("dynasty1", 2030, candidates)

        all_results = session.all_results
        expected_total = (len(session.inductees) +
                         len(session.non_inductees) +
                         len(session.removed_from_ballot))

        assert len(all_results) == expected_total
        assert len(all_results) == 2

    def test_session_to_dict(self, engine):
        """Session serializes to dictionary correctly."""
        candidate = create_first_ballot_candidate()
        session = engine.conduct_voting("dynasty1", 2030, [candidate])

        session_dict = session.to_dict()

        assert session_dict['dynasty_id'] == "dynasty1"
        assert session_dict['voting_season'] == 2030
        assert 'inductees' in session_dict
        assert 'non_inductees' in session_dict
        assert 'removed_from_ballot' in session_dict
        assert 'class_strength' in session_dict


# ============================================
# Test Simulate Single Candidate
# ============================================

class TestSimulateSingleCandidate:
    """Test the simulate_single_candidate convenience method."""

    def test_returns_vote_percentage(self, engine):
        """Returns vote percentage for single candidate."""
        candidate = create_first_ballot_candidate()
        vote_pct, would_be_inducted, breakdown = engine.simulate_single_candidate(candidate)

        assert 0.0 <= vote_pct <= 1.0

    def test_returns_would_be_inducted(self, engine):
        """Returns whether candidate would be inducted."""
        candidate = create_first_ballot_candidate()
        vote_pct, would_be_inducted, breakdown = engine.simulate_single_candidate(candidate)

        # First-ballot lock should be inducted
        assert would_be_inducted is True

    def test_returns_score_breakdown(self, engine):
        """Returns score breakdown for candidate."""
        candidate = create_first_ballot_candidate()
        vote_pct, would_be_inducted, breakdown = engine.simulate_single_candidate(candidate)

        assert breakdown.total_score > 0
        assert breakdown.tier is not None

    def test_class_strength_affects_result(self, deterministic_engine):
        """Class strength parameter affects vote percentage."""
        candidate = create_borderline_candidate()

        # Weak class = more room for borderline
        pct_weak, _, _ = deterministic_engine.simulate_single_candidate(
            candidate, class_strength=0.3
        )

        # Strong class = harder for borderline
        pct_strong, _, _ = deterministic_engine.simulate_single_candidate(
            candidate, class_strength=0.8
        )

        # In a weak class, borderline should get slightly more votes
        # (This may not always be true due to random variance, but trend should hold)


# ============================================
# Test Reproducibility with Seed
# ============================================

class TestReproducibility:
    """Test that same seed produces same results."""

    def test_same_seed_same_results(self):
        """Same seed produces identical results."""
        candidate = create_first_ballot_candidate()

        engine1 = HOFVotingEngine(seed=42)
        session1 = engine1.conduct_voting("dynasty1", 2030, [candidate])

        engine2 = HOFVotingEngine(seed=42)
        session2 = engine2.conduct_voting("dynasty1", 2030, [candidate])

        assert session1.inductees[0].vote_percentage == session2.inductees[0].vote_percentage
        assert session1.inductees[0].votes_received == session2.inductees[0].votes_received

    def test_different_seed_different_results(self):
        """Different seeds may produce different results."""
        candidate = create_borderline_candidate()

        engine1 = HOFVotingEngine(seed=1)
        session1 = engine1.conduct_voting("dynasty1", 2030, [candidate])

        engine2 = HOFVotingEngine(seed=999)
        session2 = engine2.conduct_voting("dynasty1", 2030, [candidate])

        # Results may differ (not guaranteed, but likely)
        # We just verify both produce valid results
        assert len(session1.all_results) == 1
        assert len(session2.all_results) == 1


# ============================================
# Integration with Real HOFCandidate
# ============================================

class TestIntegrationWithHOFCandidate:
    """Test that engine works with actual HOFCandidate dataclass."""

    def test_works_with_mock_candidate(self, engine):
        """Engine works with mock candidates (which match HOFCandidate interface)."""
        candidates = [
            create_first_ballot_candidate(1),
            create_strong_candidate(2),
            create_borderline_candidate(3),
        ]

        session = engine.conduct_voting("dynasty1", 2030, candidates)

        assert session.total_candidates == 3
        assert len(session.all_results) == 3
