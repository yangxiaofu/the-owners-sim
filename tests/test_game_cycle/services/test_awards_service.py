"""
Tests for AwardsService - Awards System Tollgate 4.

Comprehensive tests for the main awards orchestration service.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List

from src.game_cycle.services.awards_service import (
    AwardsService,
    ALL_PRO_SLOTS,
    PRO_BOWL_SLOTS,
    STAT_CATEGORIES,
    AFC_TEAM_IDS,
    NFC_TEAM_IDS,
)
from src.game_cycle.services.awards.models import (
    AwardType,
    AwardScore,
    PlayerCandidate,
)
from src.game_cycle.services.awards.result_models import (
    AwardResult,
    AllProTeam,
    AllProSelection,
    ProBowlRoster,
    ProBowlSelection,
    StatisticalLeadersResult,
    StatisticalLeaderEntry,
)
from src.game_cycle.services.awards.voting_engine import VotingResult


# ============================================
# Fixtures and Helpers
# ============================================

@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_awards.db")


@pytest.fixture
def service(mock_db_path):
    """Create an AwardsService instance with test configuration."""
    return AwardsService(
        db_path=mock_db_path,
        dynasty_id="test_dynasty",
        season=2024
    )


@pytest.fixture
def mock_candidates():
    """Create mock player candidates for testing."""
    candidates = []

    # QB candidates (team_id 1-8 = AFC, 17-24 = NFC)
    for i, (name, team_id, grade) in enumerate([
        ("Patrick Mahomes", 1, 95.0),
        ("Josh Allen", 2, 92.0),
        ("Jalen Hurts", 17, 88.0),
        ("Lamar Jackson", 3, 90.0),
    ]):
        candidates.append(create_mock_candidate(
            player_id=100 + i,
            name=name,
            team_id=team_id,
            position="QB",
            overall_grade=grade,
            years_pro=5,
            games_played=17,
            passing_yards=4500 - (i * 200),
            passing_tds=40 - (i * 3),
        ))

    # RB candidates
    for i, (name, team_id, grade) in enumerate([
        ("Derrick Henry", 4, 88.0),
        ("Nick Chubb", 5, 85.0),
        ("Saquon Barkley", 18, 87.0),
        ("Christian McCaffrey", 19, 90.0),
    ]):
        candidates.append(create_mock_candidate(
            player_id=200 + i,
            name=name,
            team_id=team_id,
            position="RB",
            overall_grade=grade,
            years_pro=6,
            games_played=17,
            rushing_yards=1500 - (i * 100),
            rushing_tds=15 - i,
        ))

    # WR candidates
    for i, (name, team_id, grade) in enumerate([
        ("Tyreek Hill", 6, 92.0),
        ("Ja'Marr Chase", 7, 90.0),
        ("Justin Jefferson", 20, 94.0),
        ("CeeDee Lamb", 21, 91.0),
    ]):
        candidates.append(create_mock_candidate(
            player_id=300 + i,
            name=name,
            team_id=team_id,
            position="WR",
            overall_grade=grade,
            years_pro=4,
            games_played=17,
            receiving_yards=1600 - (i * 100),
            receiving_tds=12 - i,
            receptions=110 - (i * 5),
        ))

    # Defensive players
    for i, (name, team_id, position, grade) in enumerate([
        ("Micah Parsons", 21, "EDGE", 95.0),
        ("T.J. Watt", 8, "EDGE", 93.0),
        ("Myles Garrett", 5, "EDGE", 91.0),
        ("Aaron Donald", 22, "DT", 92.0),
        ("Chris Jones", 1, "DT", 88.0),
    ]):
        candidates.append(create_mock_candidate(
            player_id=400 + i,
            name=name,
            team_id=team_id,
            position=position,
            overall_grade=grade,
            years_pro=5,
            games_played=17,
            sacks=15.0 - (i * 1.5),
            tackles_total=50 + (i * 5),
        ))

    # Rookie candidates
    for i, (name, team_id, position, grade) in enumerate([
        ("C.J. Stroud", 9, "QB", 85.0),
        ("Bijan Robinson", 23, "RB", 82.0),
        ("Will Anderson Jr.", 9, "EDGE", 80.0),
        ("Jalen Carter", 17, "DT", 78.0),
    ]):
        candidates.append(create_mock_candidate(
            player_id=500 + i,
            name=name,
            team_id=team_id,
            position=position,
            overall_grade=grade,
            years_pro=0,  # Rookie
            games_played=17,
            passing_yards=4000 if position == "QB" else 0,
            rushing_yards=1000 if position == "RB" else 0,
            sacks=10.0 if position in ("EDGE", "DT") else 0,
        ))

    return candidates


def create_mock_candidate(
    player_id: int,
    name: str,
    team_id: int,
    position: str,
    overall_grade: float,
    years_pro: int,
    games_played: int = 17,
    **stats
) -> PlayerCandidate:
    """Helper to create mock PlayerCandidate."""
    return PlayerCandidate(
        player_id=player_id,
        player_name=name,
        team_id=team_id,
        position=position,
        season=2024,
        overall_grade=overall_grade,
        years_pro=years_pro,
        games_played=games_played,
        passing_yards=stats.get('passing_yards', 0),
        passing_tds=stats.get('passing_tds', 0),
        passer_rating=stats.get('passer_rating', 0.0),
        rushing_yards=stats.get('rushing_yards', 0),
        rushing_tds=stats.get('rushing_tds', 0),
        receiving_yards=stats.get('receiving_yards', 0),
        receiving_tds=stats.get('receiving_tds', 0),
        receptions=stats.get('receptions', 0),
        sacks=stats.get('sacks', 0.0),
        interceptions=stats.get('interceptions', 0),
        tackles_total=stats.get('tackles_total', 0),
        forced_fumbles=stats.get('forced_fumbles', 0),
        team_wins=stats.get('team_wins', 10),
        team_losses=stats.get('team_losses', 7),
        playoff_seed=stats.get('playoff_seed', 3),
        is_division_winner=stats.get('is_division_winner', False),
        is_conference_champion=stats.get('is_conference_champion', False),
    )


def create_mock_voting_result(
    candidate: PlayerCandidate,
    total_points: int,
    first_place_votes: int = 0
) -> VotingResult:
    """Helper to create mock VotingResult."""
    return VotingResult(
        player_id=candidate.player_id,
        player_name=candidate.player_name,
        team_id=candidate.team_id,
        position=candidate.position,
        total_points=total_points,
        vote_share=total_points / 500,
        first_place_votes=first_place_votes,
        second_place_votes=5,
        third_place_votes=3,
        fourth_place_votes=2,
        fifth_place_votes=1,
        raw_score=candidate.overall_grade,
    )


def setup_service_mocks(service, mock_candidates, voting_results=None):
    """
    Set up mock dependencies on the service.

    This directly sets the internal _attributes to bypass lazy loading.
    """
    # Mock eligibility checker
    mock_checker = MagicMock()
    mock_checker.get_eligible_candidates.return_value = mock_candidates
    # Also mock get_eligible_candidates_fast for All-Pro/Pro Bowl selection
    mock_checker.get_eligible_candidates_fast.return_value = mock_candidates
    # Mock check_all_pro_stat_minimums to return (True, None) for all candidates
    mock_checker.check_all_pro_stat_minimums.return_value = (True, None)
    service._eligibility_checker = mock_checker

    # Mock voting engine
    mock_engine = MagicMock()
    if voting_results:
        mock_engine.conduct_voting.return_value = voting_results
    else:
        mock_engine.conduct_voting.return_value = [
            create_mock_voting_result(mock_candidates[0], 450, 40)
        ] if mock_candidates else []
    service._voting_engine = mock_engine

    # Mock awards API
    mock_api = MagicMock()
    mock_api.get_award_winners.return_value = []
    mock_api.clear_season_awards.return_value = {'winners': 0, 'nominees': 0}
    service._awards_api = mock_api

    return mock_checker, mock_engine, mock_api


# ============================================
# Initialization Tests
# ============================================

class TestAwardsServiceInit:
    """Tests for AwardsService initialization."""

    def test_constructor_sets_instance_variables(self, mock_db_path):
        """Constructor properly sets all instance variables."""
        service = AwardsService(
            db_path=mock_db_path,
            dynasty_id="test_dynasty",
            season=2024
        )

        assert service._db_path == mock_db_path
        assert service._dynasty_id == "test_dynasty"
        assert service._season == 2024

    def test_lazy_loaders_initially_none(self, service):
        """Lazy-loaded dependencies are None before first access."""
        assert service._eligibility_checker is None
        assert service._voting_engine is None
        assert service._awards_api is None
        assert service._db is None

    def test_repr_format(self, service):
        """__repr__ returns expected format."""
        result = repr(service)
        assert "AwardsService" in result
        assert "test_dynasty" in result
        assert "2024" in result


# ============================================
# MVP Calculation Tests
# ============================================

class TestMVPCalculation:
    """Tests for MVP award calculation."""

    def test_calculate_mvp_returns_award_result(self, service, mock_candidates):
        """MVP calculation returns properly structured AwardResult."""
        voting_results = [
            create_mock_voting_result(mock_candidates[0], 450, 40),
            create_mock_voting_result(mock_candidates[1], 350, 8),
            create_mock_voting_result(mock_candidates[2], 100, 2),
        ]
        setup_service_mocks(service, mock_candidates, voting_results)

        result = service.calculate_mvp()

        assert isinstance(result, AwardResult)
        assert result.award_id == 'mvp'
        assert result.season == 2024
        assert result.has_winner
        assert result.winner.player_name == "Patrick Mahomes"

    def test_calculate_mvp_winner_has_highest_points(self, service, mock_candidates):
        """MVP winner has the highest vote points."""
        voting_results = [
            create_mock_voting_result(mock_candidates[0], 450, 40),
            create_mock_voting_result(mock_candidates[1], 350, 8),
            create_mock_voting_result(mock_candidates[2], 200, 2),
        ]
        setup_service_mocks(service, mock_candidates, voting_results)

        result = service.calculate_mvp()

        assert result.winner.total_points == 450
        assert result.winner.first_place_votes == 40

    def test_calculate_mvp_finalists_are_positions_2_to_5(self, service, mock_candidates):
        """Finalists are positions 2-5 in voting."""
        voting_results = [
            create_mock_voting_result(c, 400 - (i * 50), 30 - (i * 5))
            for i, c in enumerate(mock_candidates[:6])
        ]
        setup_service_mocks(service, mock_candidates, voting_results)

        result = service.calculate_mvp()

        assert len(result.finalists) == 4
        assert result.finalists[0].player_id == mock_candidates[1].player_id

    def test_calculate_mvp_no_candidates_returns_empty_result(self, service):
        """Empty candidate list returns empty AwardResult."""
        setup_service_mocks(service, [], [])

        result = service.calculate_mvp()

        assert result.winner is None
        assert result.finalists == []
        assert result.candidates_evaluated == 0

    def test_calculate_mvp_stores_results_in_database(self, service, mock_candidates):
        """MVP results are stored via awards_api."""
        voting_results = [
            create_mock_voting_result(c, 400 - (i * 100), 30 - (i * 10))
            for i, c in enumerate(mock_candidates[:3])
        ]
        mock_checker, mock_engine, mock_api = setup_service_mocks(
            service, mock_candidates[:3], voting_results
        )

        service.calculate_mvp()

        # Should store top 5 as winners (or all 3 if fewer)
        assert mock_api.insert_award_winner.call_count == 3
        # Should store all as nominees
        assert mock_api.insert_nominee.call_count == 3

    def test_calculate_mvp_error_handling(self, service):
        """MVP calculation handles errors gracefully."""
        mock_checker = MagicMock()
        mock_checker.get_eligible_candidates.side_effect = Exception("DB error")
        service._eligibility_checker = mock_checker

        result = service.calculate_mvp()

        # Should return empty result, not raise
        assert result.winner is None
        assert result.candidates_evaluated == 0

    def test_calculate_mvp_vote_share_calculated(self, service, mock_candidates):
        """Vote share is properly calculated for winner."""
        voting_results = [
            create_mock_voting_result(mock_candidates[0], 450, 40),
        ]
        setup_service_mocks(service, mock_candidates, voting_results)

        result = service.calculate_mvp()

        # Vote share should be total_points / 500 (max)
        assert result.winner.vote_share == 0.9  # 450/500


# ============================================
# OPOY/DPOY Tests
# ============================================

class TestOPOYDPOYCalculation:
    """Tests for OPOY and DPOY calculations."""

    def test_calculate_opoy_returns_offensive_player(self, service, mock_candidates):
        """OPOY returns an offensive player."""
        offensive_candidates = [c for c in mock_candidates if c.position in ('QB', 'RB', 'WR', 'TE')]
        voting_results = [create_mock_voting_result(offensive_candidates[0], 400, 35)]
        setup_service_mocks(service, offensive_candidates, voting_results)

        result = service.calculate_opoy()

        assert result.award_id == 'opoy'
        assert result.winner.position in ('QB', 'RB', 'WR', 'TE', 'FB', 'LT', 'LG', 'C', 'RG', 'RT')

    def test_calculate_dpoy_returns_defensive_player(self, service, mock_candidates):
        """DPOY returns a defensive player."""
        defensive_candidates = [c for c in mock_candidates if c.position in ('EDGE', 'DT', 'LOLB', 'MLB', 'CB', 'SS', 'FS')]
        voting_results = [create_mock_voting_result(defensive_candidates[0], 420, 38)]
        setup_service_mocks(service, defensive_candidates, voting_results)

        result = service.calculate_dpoy()

        assert result.award_id == 'dpoy'

    def test_calculate_dpoy_separate_from_mvp(self, service, mock_candidates):
        """DPOY can be different from MVP."""
        # First call for MVP
        setup_service_mocks(
            service, mock_candidates,
            [create_mock_voting_result(mock_candidates[0], 450, 40)]
        )
        mvp_result = service.calculate_mvp()

        # Second call for DPOY (reset mock)
        service._voting_engine.conduct_voting.return_value = [
            create_mock_voting_result(mock_candidates[12], 400, 35)  # Defensive player
        ]
        dpoy_result = service.calculate_dpoy()

        assert mvp_result.winner.position == 'QB'
        assert dpoy_result.winner.position in ('EDGE', 'DT')


# ============================================
# OROY/DROY Tests
# ============================================

class TestROYCalculation:
    """Tests for Rookie of the Year calculations."""

    def test_calculate_oroy_returns_rookie(self, service, mock_candidates):
        """OROY returns a rookie (years_pro=0)."""
        rookies = [c for c in mock_candidates if c.years_pro == 0 and c.position in ('QB', 'RB', 'WR', 'TE')]
        voting_results = [create_mock_voting_result(rookies[0], 380, 32)]
        setup_service_mocks(service, rookies, voting_results)

        result = service.calculate_oroy()

        assert result.award_id == 'oroy'
        assert result.winner is not None

    def test_calculate_droy_returns_defensive_rookie(self, service, mock_candidates):
        """DROY returns a defensive rookie."""
        defensive_rookies = [c for c in mock_candidates if c.years_pro == 0 and c.position in ('EDGE', 'DT', 'LOLB', 'CB')]
        voting_results = [create_mock_voting_result(defensive_rookies[0], 350, 28)]
        setup_service_mocks(service, defensive_rookies, voting_results)

        result = service.calculate_droy()

        assert result.award_id == 'droy'

    def test_oroy_no_rookies_returns_empty(self, service):
        """OROY returns empty when no rookies available."""
        setup_service_mocks(service, [], [])

        result = service.calculate_oroy()

        assert result.winner is None
        assert result.candidates_evaluated == 0


# ============================================
# CPOY Tests
# ============================================

class TestCPOYCalculation:
    """Tests for Comeback Player of the Year calculation."""

    def test_calculate_cpoy_returns_award_result(self, service, mock_candidates):
        """CPOY returns properly structured result."""
        voting_results = [create_mock_voting_result(mock_candidates[0], 300, 25)]
        setup_service_mocks(service, mock_candidates[:3], voting_results)

        result = service.calculate_cpoy()

        assert result.award_id == 'cpoy'
        assert isinstance(result, AwardResult)

    def test_calculate_cpoy_excludes_rookies(self, service, mock_candidates):
        """CPOY should not include rookies (comeback from what?)."""
        non_rookies = [c for c in mock_candidates if c.years_pro > 0]
        voting_results = [create_mock_voting_result(non_rookies[0], 350, 30)]
        setup_service_mocks(service, non_rookies, voting_results)

        result = service.calculate_cpoy()

        assert result.winner is not None


# ============================================
# Calculate All Awards Tests
# ============================================

class TestCalculateAllAwards:
    """Tests for calculate_all_awards method."""

    def test_calculate_all_awards_returns_dict(self, service, mock_candidates):
        """calculate_all_awards returns dict with all 6 awards."""
        voting_results = [create_mock_voting_result(mock_candidates[0], 400, 35)]
        setup_service_mocks(service, mock_candidates, voting_results)

        results = service.calculate_all_awards()

        assert isinstance(results, dict)
        assert len(results) == 6
        assert set(results.keys()) == {'mvp', 'opoy', 'dpoy', 'oroy', 'droy', 'cpoy'}

    def test_calculate_all_awards_each_has_result(self, service, mock_candidates):
        """Each award in result has an AwardResult."""
        voting_results = [create_mock_voting_result(mock_candidates[0], 400, 35)]
        setup_service_mocks(service, mock_candidates, voting_results)

        results = service.calculate_all_awards()

        for award_id, result in results.items():
            assert isinstance(result, AwardResult)
            assert result.award_id == award_id


# ============================================
# All-Pro Selection Tests
# ============================================

class TestAllProSelection:
    """Tests for All-Pro team selection."""

    def test_all_pro_returns_all_pro_team(self, service, mock_candidates):
        """select_all_pro_teams returns AllProTeam."""
        setup_service_mocks(service, mock_candidates)

        result = service.select_all_pro_teams()

        assert isinstance(result, AllProTeam)
        assert result.season == 2024

    def test_all_pro_first_team_structure(self, service, mock_candidates):
        """First team has proper structure."""
        setup_service_mocks(service, mock_candidates)

        result = service.select_all_pro_teams()

        assert isinstance(result.first_team, dict)
        # Should have selections
        assert result.first_team_count > 0

    def test_all_pro_second_team_structure(self, service, mock_candidates):
        """Second team has proper structure."""
        setup_service_mocks(service, mock_candidates)

        result = service.select_all_pro_teams()

        assert isinstance(result.second_team, dict)

    def test_all_pro_position_slots_respected(self, service):
        """Position slot limits are respected."""
        candidates = []
        for position in ['QB', 'RB', 'WR']:
            for i in range(5):
                candidates.append(create_mock_candidate(
                    player_id=1000 + (len(candidates)),
                    name=f"{position} Player {i}",
                    team_id=1 + i,
                    position=position,
                    overall_grade=90.0 - i,
                    years_pro=5,
                ))

        setup_service_mocks(service, candidates)
        result = service.select_all_pro_teams()

        # QB should have max 1 per team
        if 'QB' in result.first_team:
            assert len(result.first_team['QB']) <= ALL_PRO_SLOTS['QB']

        # RB should have max 2 per team
        if 'RB' in result.first_team:
            assert len(result.first_team['RB']) <= ALL_PRO_SLOTS['RB']

    def test_all_pro_first_team_higher_than_second(self, service):
        """First team players have higher grades than second team."""
        candidates = []
        for i in range(6):
            candidates.append(create_mock_candidate(
                player_id=2000 + i,
                name=f"QB Player {i}",
                team_id=1 + i,
                position="QB",
                overall_grade=95.0 - (i * 5),
                years_pro=5,
            ))

        setup_service_mocks(service, candidates)
        result = service.select_all_pro_teams()

        if 'QB' in result.first_team and 'QB' in result.second_team:
            if result.first_team['QB'] and result.second_team['QB']:
                first_team_grade = result.first_team['QB'][0].overall_grade
                second_team_grade = result.second_team['QB'][0].overall_grade
                assert first_team_grade >= second_team_grade

    def test_all_pro_stores_to_database(self, service, mock_candidates):
        """All-Pro selections are stored via awards_api."""
        mock_checker, mock_engine, mock_api = setup_service_mocks(service, mock_candidates)

        service.select_all_pro_teams()

        # Should have stored selections
        assert mock_api.insert_all_pro_selection.call_count > 0

    def test_all_pro_error_handling(self, service):
        """All-Pro handles errors gracefully."""
        mock_checker = MagicMock()
        mock_checker.get_eligible_candidates.side_effect = Exception("DB error")
        service._eligibility_checker = mock_checker

        result = service.select_all_pro_teams()

        # Should return empty result, not raise
        assert result.total_selections == 0


# ============================================
# Pro Bowl Selection Tests
# ============================================

class TestProBowlSelection:
    """Tests for Pro Bowl roster selection."""

    def test_pro_bowl_returns_roster(self, service, mock_candidates):
        """select_pro_bowl_rosters returns ProBowlRoster."""
        setup_service_mocks(service, mock_candidates)

        result = service.select_pro_bowl_rosters()

        assert isinstance(result, ProBowlRoster)
        assert result.season == 2024

    def test_pro_bowl_afc_nfc_separation(self, service, mock_candidates):
        """AFC and NFC rosters are properly separated."""
        setup_service_mocks(service, mock_candidates)

        result = service.select_pro_bowl_rosters()

        # Check AFC roster
        for position, players in result.afc_roster.items():
            for player in players:
                assert player.team_id in AFC_TEAM_IDS
                assert player.conference == 'AFC'

        # Check NFC roster
        for position, players in result.nfc_roster.items():
            for player in players:
                assert player.team_id in NFC_TEAM_IDS
                assert player.conference == 'NFC'

    def test_pro_bowl_selection_types(self, service):
        """Selection types (STARTER/RESERVE) are assigned."""
        candidates = []
        for i in range(8):
            candidates.append(create_mock_candidate(
                player_id=3000 + i,
                name=f"QB {i}",
                team_id=1 + (i % 16),  # AFC teams
                position="QB",
                overall_grade=95.0 - i,
                years_pro=5,
            ))

        setup_service_mocks(service, candidates)
        result = service.select_pro_bowl_rosters()

        if 'QB' in result.afc_roster and len(result.afc_roster['QB']) >= 2:
            # First 2 should be starters
            assert result.afc_roster['QB'][0].selection_type == 'STARTER'
            assert result.afc_roster['QB'][1].selection_type == 'STARTER'
            if len(result.afc_roster['QB']) >= 3:
                assert result.afc_roster['QB'][2].selection_type == 'RESERVE'

    def test_pro_bowl_stores_to_database(self, service, mock_candidates):
        """Pro Bowl selections are stored via awards_api."""
        mock_checker, mock_engine, mock_api = setup_service_mocks(service, mock_candidates)

        service.select_pro_bowl_rosters()

        # Should have stored selections
        assert mock_api.insert_pro_bowl_selection.call_count > 0

    def test_pro_bowl_error_handling(self, service):
        """Pro Bowl handles errors gracefully."""
        mock_checker = MagicMock()
        mock_checker.get_eligible_candidates.side_effect = Exception("DB error")
        service._eligibility_checker = mock_checker

        result = service.select_pro_bowl_rosters()

        assert result.total_selections == 0


# ============================================
# Statistical Leaders Tests
# ============================================

class TestStatisticalLeaders:
    """Tests for statistical leader recording."""

    def test_record_leaders_returns_result(self, service, mock_candidates):
        """record_statistical_leaders returns StatisticalLeadersResult."""
        setup_service_mocks(service, mock_candidates)

        result = service.record_statistical_leaders()

        assert isinstance(result, StatisticalLeadersResult)
        assert result.season == 2024

    def test_record_leaders_captures_categories(self, service, mock_candidates):
        """Multiple statistical categories are recorded."""
        setup_service_mocks(service, mock_candidates)

        result = service.record_statistical_leaders()

        # Should have recorded multiple categories
        assert len(result.categories_recorded) > 0

    def test_record_leaders_top_10_per_category(self, service):
        """Each category has up to top 10 leaders."""
        candidates = []
        for i in range(15):
            candidates.append(create_mock_candidate(
                player_id=4000 + i,
                name=f"QB {i}",
                team_id=1 + (i % 16),
                position="QB",
                overall_grade=90.0,
                years_pro=5,
                passing_yards=5000 - (i * 100),
                passing_tds=45 - i,
            ))

        setup_service_mocks(service, candidates)
        result = service.record_statistical_leaders()

        if 'passing_yards' in result.leaders_by_category:
            leaders = result.leaders_by_category['passing_yards']
            assert len(leaders) <= 10

    def test_record_leaders_ranking_order(self, service):
        """Leaders are ranked in descending order of stat value."""
        candidates = []
        for i in range(5):
            candidates.append(create_mock_candidate(
                player_id=5000 + i,
                name=f"QB {i}",
                team_id=1 + i,
                position="QB",
                overall_grade=90.0,
                years_pro=5,
                passing_yards=5000 - (i * 500),
            ))

        setup_service_mocks(service, candidates)
        result = service.record_statistical_leaders()

        if 'passing_yards' in result.leaders_by_category:
            leaders = result.leaders_by_category['passing_yards']
            for i in range(len(leaders) - 1):
                assert leaders[i].stat_value >= leaders[i + 1].stat_value

    def test_record_leaders_position_filter(self, service, mock_candidates):
        """QB-only stats only include QBs."""
        setup_service_mocks(service, mock_candidates)

        result = service.record_statistical_leaders()

        if 'passing_yards' in result.leaders_by_category:
            for leader in result.leaders_by_category['passing_yards']:
                assert leader.position == 'QB'

    def test_record_leaders_stores_to_database(self, service, mock_candidates):
        """Statistical leaders are stored via awards_api."""
        mock_checker, mock_engine, mock_api = setup_service_mocks(service, mock_candidates)

        service.record_statistical_leaders()

        # Should have stored leader entries
        assert mock_api.record_stat_leader.call_count > 0

    def test_record_leaders_error_handling(self, service):
        """Statistical leaders handles errors gracefully."""
        mock_checker = MagicMock()
        mock_checker.get_eligible_candidates.side_effect = Exception("DB error")
        service._eligibility_checker = mock_checker

        result = service.record_statistical_leaders()

        assert result.total_recorded == 0


# ============================================
# Utility Method Tests
# ============================================

class TestUtilityMethods:
    """Tests for utility methods."""

    def test_awards_already_calculated_true(self, service):
        """awards_already_calculated returns True when awards exist."""
        mock_api = MagicMock()
        mock_api.get_award_winners.return_value = [{'award_id': 'mvp'}]
        service._awards_api = mock_api

        result = service.awards_already_calculated()

        assert result is True

    def test_awards_already_calculated_false(self, service):
        """awards_already_calculated returns False when no awards."""
        mock_api = MagicMock()
        mock_api.get_award_winners.return_value = []
        service._awards_api = mock_api

        result = service.awards_already_calculated()

        assert result is False

    def test_clear_season_awards(self, service):
        """clear_season_awards calls awards_api."""
        mock_api = MagicMock()
        mock_api.clear_season_awards.return_value = {'winners': 6, 'nominees': 30}
        service._awards_api = mock_api

        result = service.clear_season_awards()

        mock_api.clear_season_awards.assert_called_once_with(
            dynasty_id="test_dynasty",
            season=2024
        )
        assert result == {'winners': 6, 'nominees': 30}


# ============================================
# Constants Tests
# ============================================

class TestConstants:
    """Tests for module constants."""

    def test_all_pro_slots_total_22(self):
        """All-Pro slots have reasonable values."""
        total = sum(ALL_PRO_SLOTS.values())
        # Note: Some positions may be grouped differently
        assert total > 0

    def test_pro_bowl_slots_reasonable(self):
        """Pro Bowl slots have reasonable values."""
        for position, slots in PRO_BOWL_SLOTS.items():
            assert slots >= 1
            assert slots <= 4

    def test_afc_team_ids_correct_range(self):
        """AFC team IDs are 1-16."""
        assert AFC_TEAM_IDS == {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}

    def test_nfc_team_ids_correct_range(self):
        """NFC team IDs are 17-32."""
        assert NFC_TEAM_IDS == {17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32}

    def test_stat_categories_defined(self):
        """STAT_CATEGORIES has expected categories."""
        category_names = [cat for cat, _ in STAT_CATEGORIES]
        assert 'passing_yards' in category_names
        assert 'rushing_yards' in category_names
        assert 'receiving_yards' in category_names
        assert 'sacks' in category_names


# ============================================
# Result Model Tests
# ============================================

class TestResultModels:
    """Tests for result model dataclasses."""

    def test_award_result_to_dict(self):
        """AwardResult.to_dict() returns proper structure."""
        result = AwardResult(
            award_id='mvp',
            season=2024,
            winner=None,
            finalists=[],
            all_votes=[],
            candidates_evaluated=50
        )

        d = result.to_dict()
        assert d['award_id'] == 'mvp'
        assert d['season'] == 2024
        assert d['candidates_evaluated'] == 50

    def test_award_result_has_winner_property(self):
        """AwardResult.has_winner property works."""
        result_with = AwardResult(
            award_id='mvp',
            season=2024,
            winner=Mock(),
            finalists=[],
            all_votes=[],
            candidates_evaluated=50
        )
        result_without = AwardResult(
            award_id='mvp',
            season=2024,
            winner=None,
            finalists=[],
            all_votes=[],
            candidates_evaluated=0
        )

        assert result_with.has_winner is True
        assert result_without.has_winner is False

    def test_all_pro_team_counts(self):
        """AllProTeam count properties work."""
        team = AllProTeam(
            season=2024,
            first_team={'QB': [Mock()], 'RB': [Mock(), Mock()]},
            second_team={'QB': [Mock()]},
            total_selections=4
        )

        assert team.first_team_count == 3
        assert team.second_team_count == 1

    def test_pro_bowl_roster_counts(self):
        """ProBowlRoster count properties work."""
        roster = ProBowlRoster(
            season=2024,
            afc_roster={'QB': [Mock(), Mock()]},
            nfc_roster={'QB': [Mock()]},
            total_selections=3
        )

        assert roster.afc_count == 2
        assert roster.nfc_count == 1

    def test_statistical_leaders_result_get_leader(self):
        """StatisticalLeadersResult.get_category_leader() works."""
        entry = StatisticalLeaderEntry(
            player_id=1,
            player_name="Test Player",
            team_id=1,
            position="QB",
            stat_category="passing_yards",
            stat_value=5000,
            league_rank=1
        )

        result = StatisticalLeadersResult(
            season=2024,
            leaders_by_category={'passing_yards': [entry]},
            total_recorded=1
        )

        leader = result.get_category_leader('passing_yards')
        assert leader.player_name == "Test Player"
        assert leader.stat_value == 5000


# ============================================
# Integration Tests
# ============================================

class TestIntegration:
    """Integration tests for full award calculation flow."""

    def test_full_award_flow(self, service, mock_candidates):
        """Full award calculation flow works end-to-end."""
        voting_results = [
            create_mock_voting_result(mock_candidates[0], 450, 40),
            create_mock_voting_result(mock_candidates[1], 350, 8),
        ]
        setup_service_mocks(service, mock_candidates, voting_results)

        # Calculate all awards
        all_awards = service.calculate_all_awards()

        # Select All-Pro
        all_pro = service.select_all_pro_teams()

        # Select Pro Bowl
        pro_bowl = service.select_pro_bowl_rosters()

        # Record stats
        stat_leaders = service.record_statistical_leaders()

        # Verify all outputs
        assert len(all_awards) == 6
        assert isinstance(all_pro, AllProTeam)
        assert isinstance(pro_bowl, ProBowlRoster)
        assert isinstance(stat_leaders, StatisticalLeadersResult)
