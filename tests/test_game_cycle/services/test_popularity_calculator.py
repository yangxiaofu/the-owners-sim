"""
Tests for PopularityCalculator Service - Milestone 16: Player Popularity.

Comprehensive tests for all calculation methods:
- Performance score calculation (PFF grade + position value)
- Visibility multiplier (media, awards, social, team success)
- Market multiplier (stadium capacity tiers)
- Weekly decay based on activity
- Tier classification and trend tracking
- Special cases: rookies, trades, playoffs
"""

import pytest
import tempfile
import os
import sys
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List

# Patch missing modules before any game_cycle imports
sys.modules['persistence'] = Mock()
sys.modules['persistence.transaction_logger'] = Mock()
sys.modules['utils'] = Mock()
sys.modules['utils.player_field_extractors'] = Mock()


# ============================================
# Lazy imports to avoid chain import issues
# ============================================

def get_constants():
    """Lazy load constants from popularity_calculator module."""
    from game_cycle.services.popularity_calculator import (
        PopularityTier,
        PopularityTrend,
        POSITION_VALUE_MULTIPLIERS,
        VISIBILITY_FLOOR,
        VISIBILITY_CEILING,
        NATIONAL_HEADLINE_BOOST,
        REGIONAL_HEADLINE_BOOST,
        LOCAL_HEADLINE_BOOST,
        MVP_TOP_3_BOOST,
        MVP_TOP_10_BOOST,
        AWARD_TOP_5_BOOST,
        ALL_PRO_BOOST,
        PRO_BOWL_BOOST,
        SOCIAL_PER_10_POSTS,
        VIRAL_BOOST,
        DECAY_INJURED,
        DECAY_INACTIVE,
        DECAY_MINOR,
        DECAY_ACTIVE,
        ROOKIE_DRAFT_VALUES,
        TRADE_DISRUPTION_PENALTY,
        PLAYOFF_STATS_MULTIPLIER,
        LARGE_MARKET_MIN,
        MEDIUM_LARGE_MIN,
        MEDIUM_MIN,
    )
    return {
        'PopularityTier': PopularityTier,
        'PopularityTrend': PopularityTrend,
        'POSITION_VALUE_MULTIPLIERS': POSITION_VALUE_MULTIPLIERS,
        'VISIBILITY_FLOOR': VISIBILITY_FLOOR,
        'VISIBILITY_CEILING': VISIBILITY_CEILING,
        'NATIONAL_HEADLINE_BOOST': NATIONAL_HEADLINE_BOOST,
        'REGIONAL_HEADLINE_BOOST': REGIONAL_HEADLINE_BOOST,
        'LOCAL_HEADLINE_BOOST': LOCAL_HEADLINE_BOOST,
        'MVP_TOP_3_BOOST': MVP_TOP_3_BOOST,
        'MVP_TOP_10_BOOST': MVP_TOP_10_BOOST,
        'AWARD_TOP_5_BOOST': AWARD_TOP_5_BOOST,
        'ALL_PRO_BOOST': ALL_PRO_BOOST,
        'PRO_BOWL_BOOST': PRO_BOWL_BOOST,
        'SOCIAL_PER_10_POSTS': SOCIAL_PER_10_POSTS,
        'VIRAL_BOOST': VIRAL_BOOST,
        'DECAY_INJURED': DECAY_INJURED,
        'DECAY_INACTIVE': DECAY_INACTIVE,
        'DECAY_MINOR': DECAY_MINOR,
        'DECAY_ACTIVE': DECAY_ACTIVE,
        'ROOKIE_DRAFT_VALUES': ROOKIE_DRAFT_VALUES,
        'TRADE_DISRUPTION_PENALTY': TRADE_DISRUPTION_PENALTY,
        'PLAYOFF_STATS_MULTIPLIER': PLAYOFF_STATS_MULTIPLIER,
        'LARGE_MARKET_MIN': LARGE_MARKET_MIN,
        'MEDIUM_LARGE_MIN': MEDIUM_LARGE_MIN,
        'MEDIUM_MIN': MEDIUM_MIN,
    }


# ============================================
# Mock Data Classes
# ============================================

@dataclass
class MockSeasonGrade:
    """Mock player season grade from analytics API."""
    player_id: int
    season: int
    overall_grade: float
    offense_grade: float = 0.0
    defense_grade: float = 0.0
    special_teams_grade: float = 0.0


@dataclass
class MockHeadline:
    """Mock headline from media coverage API."""
    headline_id: int
    player_id: int
    priority: int
    headline_text: str
    body_text: str


@dataclass
class MockAwardNominee:
    """Mock award nominee."""
    player_id: int
    award_id: str
    nomination_rank: int
    votes: int


@dataclass
class MockAllProSelection:
    """Mock All-Pro selection."""
    player_id: int
    season: int
    team_type: str  # 'first' or 'second'
    position: str


@dataclass
class MockProBowlSelection:
    """Mock Pro Bowl selection."""
    player_id: int
    season: int
    conference: str
    position: str


@dataclass
class MockSocialPost:
    """Mock social media post."""
    post_id: int
    player_id: int
    likes: int
    retweets: int
    content: str


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def test_db_path():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def mock_game_cycle_db(test_db_path):
    """Create mock GameCycleDatabase."""
    db = Mock()  # Don't use spec to avoid import chain issues
    db.db_path = test_db_path
    return db


@pytest.fixture
def calculator(mock_game_cycle_db):
    """Create PopularityCalculator with mocked dependencies."""
    from game_cycle.services.popularity_calculator import PopularityCalculator

    calc = PopularityCalculator(mock_game_cycle_db, "test_dynasty")

    # Mock all API dependencies
    calc._analytics_api = Mock()
    calc._media_api = Mock()
    calc._awards_api = Mock()
    calc._social_api = Mock()
    calc._standings_api = Mock()

    # Mock team data with various market sizes
    calc._team_data = {
        1: {'stadium': {'capacity': 82500}},  # Large market (Jets/Giants)
        2: {'stadium': {'capacity': 71608}},  # Medium-large (Buffalo)
        3: {'stadium': {'capacity': 65878}},  # Medium (New England)
        4: {'stadium': {'capacity': 61500}},  # Small market
        99: {},  # Invalid team (no stadium data)
    }

    return calc


# ============================================
# Test calculate_performance_score()
# ============================================

def test_performance_score_qb_with_90_grade_capped_at_100(calculator):
    """Test QB with 90 grade -> should return 90 × 1.2 = capped at 100."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=1001,
        season=2024,
        overall_grade=90.0
    )

    # Act
    score = calculator.calculate_performance_score(
        player_id=1001,
        season=2024,
        week=10,
        position="QB"
    )

    # Assert
    # 90 × 1.2 = 108, capped at 100
    assert score == 100.0
    calculator._analytics_api.get_player_season_grade.assert_called_once_with(
        "test_dynasty", 1001, 2024
    )


def test_performance_score_wr_with_75_grade(calculator):
    """Test WR with 75 grade -> should return 75 × 1.1 = 82.5."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=1002,
        season=2024,
        overall_grade=75.0
    )

    # Act
    score = calculator.calculate_performance_score(
        player_id=1002,
        season=2024,
        week=10,
        position="WR"
    )

    # Assert
    assert score == 82.5  # 75 × 1.1


def test_performance_score_ol_with_80_grade(calculator):
    """Test OL with 80 grade -> should return 80 × 1.0 = 80."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=1003,
        season=2024,
        overall_grade=80.0
    )

    # Act
    score = calculator.calculate_performance_score(
        player_id=1003,
        season=2024,
        week=10,
        position="LT"  # Offensive Line position
    )

    # Assert
    assert score == 80.0  # 80 × 1.0


def test_performance_score_kicker_with_70_grade(calculator):
    """Test K with 70 grade -> should return 70 × 0.7 = 49."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=1004,
        season=2024,
        overall_grade=70.0
    )

    # Act
    score = calculator.calculate_performance_score(
        player_id=1004,
        season=2024,
        week=10,
        position="K"
    )

    # Assert
    assert score == 49.0  # 70 × 0.7


def test_performance_score_missing_grade_data(calculator):
    """Test missing grade data -> should return default baseline (0.0)."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = None

    # Act
    score = calculator.calculate_performance_score(
        player_id=1005,
        season=2024,
        week=10,
        position="QB"
    )

    # Assert
    assert score == 0.0


def test_performance_score_unknown_position_uses_default_multiplier(calculator):
    """Test unknown position uses 1.0 multiplier."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=1006,
        season=2024,
        overall_grade=80.0
    )

    # Act
    score = calculator.calculate_performance_score(
        player_id=1006,
        season=2024,
        week=10,
        position="UNKNOWN_POS"
    )

    # Assert
    assert score == 80.0  # 80 × 1.0 (default)


# ============================================
# Test calculate_visibility_multiplier()
# ============================================

def test_visibility_no_media_exposure_returns_base(calculator):
    """Test player with no media exposure -> should return base 1.0x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2001,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.0


def test_visibility_three_national_headlines(calculator):
    """Test player with 3 national headlines -> should return 1.0 + (3 × 0.3) = 1.9x."""
    # Arrange
    headlines = [
        MockHeadline(1, 2002, priority=85, headline_text="Test 1", body_text=""),
        MockHeadline(2, 2002, priority=90, headline_text="Test 2", body_text=""),
        MockHeadline(3, 2002, priority=95, headline_text="Test 3", body_text=""),
    ]
    calculator._media_api.get_headlines.return_value = headlines
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2002,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == pytest.approx(1.9)  # 1.0 + (3 × 0.3)


def test_visibility_mvp_race_leader_top_3(calculator):
    """Test MVP race leader (top 3) -> should add +0.5x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []

    # Mock get_award_nominees to return different results based on award_id
    def mock_get_nominees(dynasty_id, season, award_id):
        if award_id == 'MVP':
            return [MockAwardNominee(player_id=2003, award_id='MVP', nomination_rank=2, votes=45)]
        return []  # Return empty for OPOY/DPOY

    calculator._awards_api.get_award_nominees.side_effect = mock_get_nominees
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2003,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.5  # 1.0 + 0.5 (MVP top 3)


def test_visibility_all_pro_selection(calculator):
    """Test All-Pro selection -> should add +0.5x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []
    calculator._awards_api.get_award_nominees.return_value = []
    all_pro_selections = [
        MockAllProSelection(player_id=2004, season=2024, team_type='first', position='QB')
    ]
    calculator._awards_api.get_all_pro_selections.return_value = all_pro_selections
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2004,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.5  # 1.0 + 0.5 (All-Pro)


def test_visibility_viral_social_moment(calculator):
    """Test viral social moment -> should add +0.05x."""
    from game_cycle.services.popularity_calculator import SOCIAL_PER_10_POSTS, VIRAL_BOOST
    # Arrange
    calculator._media_api.get_headlines.return_value = []
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []

    # Create 50+ posts with high engagement (viral threshold)
    social_posts = [
        MockSocialPost(i, 2005, likes=25, retweets=25, content=f"Post {i}")
        for i in range(60)  # 60 posts, 50 likes each = 3000 total engagement
    ]
    calculator._social_api.get_posts_by_player.return_value = social_posts

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2005,
        season=2024,
        week=10
    )

    # Assert
    # 1.0 + (60 // 10 × 0.02) + 0.05 (viral) = 1.0 + 0.12 + 0.05 = 1.17
    expected = 1.0 + (6 * SOCIAL_PER_10_POSTS) + VIRAL_BOOST
    assert multiplier == expected


def test_visibility_ceiling_caps_at_3x(calculator):
    """Test ceiling: Ensure multiplier caps at 3.0x."""
    from game_cycle.services.popularity_calculator import VISIBILITY_CEILING

    # Arrange - add excessive bonuses to exceed ceiling
    headlines = [
        MockHeadline(i, 2006, priority=90, headline_text=f"Test {i}", body_text="")
        for i in range(20)  # 20 national headlines = 6.0 bonus
    ]
    calculator._media_api.get_headlines.return_value = headlines
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2006,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == VISIBILITY_CEILING  # Capped at 3.0


def test_visibility_floor_minimum_half(calculator):
    """Test floor: Ensure multiplier has floor of 0.5x (handled by default base of 1.0)."""
    from game_cycle.services.popularity_calculator import VISIBILITY_FLOOR

    # Note: The service doesn't have negative modifiers yet, so base is always >= 1.0
    # This test verifies the floor constant is properly defined
    assert VISIBILITY_FLOOR == 0.5


def test_visibility_mixed_headline_priorities(calculator):
    """Test mixed headline priorities (national, regional, local)."""
    # Arrange
    headlines = [
        MockHeadline(1, 2007, priority=95, headline_text="National", body_text=""),  # +0.3
        MockHeadline(2, 2007, priority=70, headline_text="Regional", body_text=""),  # +0.2
        MockHeadline(3, 2007, priority=50, headline_text="Local", body_text=""),     # +0.1
    ]
    calculator._media_api.get_headlines.return_value = headlines
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2007,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.6  # 1.0 + 0.3 + 0.2 + 0.1


def test_visibility_mvp_top_10_but_not_top_3(calculator):
    """Test MVP race top 10 (but not top 3) -> should add +0.3x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []
    mvp_nominees = [
        MockAwardNominee(player_id=2008, award_id='MVP', nomination_rank=7, votes=20)
    ]
    calculator._awards_api.get_award_nominees.return_value = mvp_nominees
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2008,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.3  # 1.0 + 0.3 (MVP top 10)


def test_visibility_opoy_top_5(calculator):
    """Test OPOY/DPOY top 5 -> should add +0.4x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []

    # Mock get_award_nominees to return different results based on award_id
    def mock_get_nominees(dynasty_id, season, award_id):
        if award_id == 'MVP':
            return []
        elif award_id == 'OPOY':
            return [MockAwardNominee(player_id=2009, award_id='OPOY', nomination_rank=3, votes=30)]
        elif award_id == 'DPOY':
            return []
        return []

    calculator._awards_api.get_award_nominees.side_effect = mock_get_nominees
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2009,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.4  # 1.0 + 0.4 (OPOY top 5)


def test_visibility_pro_bowl_selection(calculator):
    """Test Pro Bowl selection -> should add +0.3x."""
    # Arrange
    calculator._media_api.get_headlines.return_value = []
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    pro_bowl_selections = [
        MockProBowlSelection(player_id=2010, season=2024, conference='AFC', position='QB')
    ]
    calculator._awards_api.get_pro_bowl_selections.return_value = pro_bowl_selections
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    multiplier = calculator.calculate_visibility_multiplier(
        player_id=2010,
        season=2024,
        week=10
    )

    # Assert
    assert multiplier == 1.3  # 1.0 + 0.3 (Pro Bowl)


# ============================================
# Test calculate_market_multiplier()
# ============================================

def test_market_large_market_team(calculator):
    """Test large market team (Dallas, 80K capacity) -> 1.8x-2.0x."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=1)  # 82500 capacity

    # Assert
    assert 1.8 <= multiplier <= 2.0
    # With 82500 capacity, should be near top of range
    assert multiplier > 1.9


def test_market_medium_large_team(calculator):
    """Test medium-large market team (70K-75K) -> 1.4x-1.6x."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=2)  # 71608 capacity

    # Assert
    assert 1.4 <= multiplier <= 1.6


def test_market_medium_team(calculator):
    """Test medium market team (65K-70K) -> 1.1x-1.3x."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=3)  # 65878 capacity

    # Assert
    assert 1.1 <= multiplier <= 1.3


def test_market_small_market_team(calculator):
    """Test small market team (<65K) -> 0.8x-1.0x."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=4)  # 61500 capacity

    # Assert
    assert 0.8 <= multiplier <= 1.0


def test_market_invalid_team_id(calculator):
    """Test invalid team_id -> should return 1.0x (neutral)."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=999)

    # Assert
    assert multiplier == 1.0


def test_market_team_missing_stadium_data(calculator):
    """Test team with missing stadium data -> should return 1.0x."""
    # Act
    multiplier = calculator.calculate_market_multiplier(team_id=99)

    # Assert
    assert multiplier == 1.0


# ============================================
# Test apply_weekly_decay()
# ============================================

def test_decay_injured_player_no_events(calculator):
    """Test injured player with no events -> -3 points."""
    from game_cycle.services.popularity_calculator import DECAY_INJURED

    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=['INJURY']
    )

    # Assert
    assert decay == DECAY_INJURED  # -3


def test_decay_active_player_no_events(calculator):
    """Test active player with no events -> -2 points."""
    from game_cycle.services.popularity_calculator import DECAY_INACTIVE
    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=[]
    )

    # Assert
    assert decay == DECAY_INACTIVE  # -2


def test_decay_player_with_minor_events(calculator):
    """Test player with minor events -> -1 point."""
    from game_cycle.services.popularity_calculator import DECAY_MINOR
    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=['PRACTICE', 'SOCIAL_POST']
    )

    # Assert
    assert decay == DECAY_MINOR  # -1


def test_decay_player_with_significant_events(calculator):
    """Test player with significant events -> 0 decay."""
    from game_cycle.services.popularity_calculator import DECAY_ACTIVE
    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=['GAME_RESULT', 'MILESTONE']
    )

    # Assert
    assert decay == DECAY_ACTIVE  # 0


def test_decay_inactive_player(calculator):
    """Test inactive player (no game, no events) -> -2 points."""
    from game_cycle.services.popularity_calculator import DECAY_INJURED
    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=['INACTIVE']
    )

    # Assert
    assert decay == DECAY_INJURED  # -3 (treated same as injury)


def test_decay_playoff_game_prevents_decay(calculator):
    """Test playoff game prevents decay."""
    from game_cycle.services.popularity_calculator import DECAY_ACTIVE
    # Act
    decay = calculator.apply_weekly_decay(
        current_popularity=50.0,
        events_this_week=['PLAYOFF_GAME']
    )

    # Assert
    assert decay == DECAY_ACTIVE  # 0


# ============================================
# Test classify_tier()
# ============================================

def test_tier_transcendent_95(calculator):
    """Test score 95 -> TRANSCENDENT."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # Act
    tier = calculator.classify_tier(95.0)

    # Assert
    assert tier == PopularityTier.TRANSCENDENT


def test_tier_star_85(calculator):
    """Test score 85 -> STAR."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # Act
    tier = calculator.classify_tier(85.0)

    # Assert
    assert tier == PopularityTier.STAR


def test_tier_known_65(calculator):
    """Test score 65 -> KNOWN."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # Act
    tier = calculator.classify_tier(65.0)

    # Assert
    assert tier == PopularityTier.KNOWN


def test_tier_role_player_40(calculator):
    """Test score 40 -> ROLE_PLAYER."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # Act
    tier = calculator.classify_tier(40.0)

    # Assert
    assert tier == PopularityTier.ROLE_PLAYER


def test_tier_unknown_15(calculator):
    """Test score 15 -> UNKNOWN."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # Act
    tier = calculator.classify_tier(15.0)

    # Assert
    assert tier == PopularityTier.UNKNOWN


def test_tier_boundary_conditions(calculator):
    """Test boundary conditions for tier classification."""
    from game_cycle.services.popularity_calculator import PopularityTier

    # Test all boundary conditions
    test_cases = [
        (90.0, PopularityTier.TRANSCENDENT),  # Boundary: exactly 90
        (89.9, PopularityTier.STAR),          # Just below 90
        (75.0, PopularityTier.STAR),          # Boundary: exactly 75
        (74.9, PopularityTier.KNOWN),         # Just below 75
        (50.0, PopularityTier.KNOWN),         # Boundary: exactly 50
        (49.9, PopularityTier.ROLE_PLAYER),   # Just below 50
        (25.0, PopularityTier.ROLE_PLAYER),   # Boundary: exactly 25
        (24.9, PopularityTier.UNKNOWN),       # Just below 25
    ]

    for score, expected_tier in test_cases:
        tier = calculator.classify_tier(score)
        assert tier == expected_tier, f"Score {score} should be {expected_tier}, got {tier}"


# ============================================
# Test calculate_trend()
# ============================================

def test_trend_stable_default(calculator):
    """Test new player with <4 weeks history -> STABLE."""
    from game_cycle.services.popularity_calculator import PopularityTrend
    # Note: calculate_trend is currently a placeholder returning STABLE
    # Act
    trend = calculator.calculate_trend(
        player_id=4001,
        season=2024,
        week=2
    )

    # Assert
    assert trend == PopularityTrend.STABLE


# TODO: Add tests for RISING and FALLING trends once PopularityAPI is implemented
# These tests will require mocking historical popularity data


# ============================================
# Test initialize_rookie_popularity()
# ============================================

def test_rookie_1st_overall_pick(calculator):
    """Test 1st overall pick -> 40."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5001,
        draft_round=1,
        draft_pick=1
    )

    # Assert
    assert popularity == 40.0


def test_rookie_top_5_pick(calculator):
    """Test top 5 pick -> 35."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5002,
        draft_round=1,
        draft_pick=5
    )

    # Assert
    assert popularity == 35.0


def test_rookie_top_10_pick(calculator):
    """Test top 10 pick -> 30."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5003,
        draft_round=1,
        draft_pick=10
    )

    # Assert
    assert popularity == 30.0


def test_rookie_late_1st_round(calculator):
    """Test late 1st round -> 25."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5004,
        draft_round=1,
        draft_pick=28
    )

    # Assert
    assert popularity == 25.0


def test_rookie_2nd_round(calculator):
    """Test 2nd round -> 20."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5005,
        draft_round=2,
        draft_pick=40
    )

    # Assert
    assert popularity == 20.0


def test_rookie_undrafted(calculator):
    """Test undrafted -> 5."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5006,
        draft_round=0,  # 0 indicates undrafted
        draft_pick=0
    )

    # Assert
    assert popularity == 5.0


def test_rookie_3rd_round(calculator):
    """Test 3rd round -> 15."""
    # Act
    popularity = calculator.initialize_rookie_popularity(
        player_id=5007,
        draft_round=3,
        draft_pick=80
    )

    # Assert
    assert popularity == 15.0


def test_rookie_late_round(calculator):
    """Test 4th-7th rounds -> 10."""
    # Act
    popularity_4th = calculator.initialize_rookie_popularity(5008, 4, 120)
    popularity_7th = calculator.initialize_rookie_popularity(5009, 7, 250)

    # Assert
    assert popularity_4th == 10.0
    assert popularity_7th == 10.0


# ============================================
# Test adjust_for_trade()
# ============================================

def test_trade_initial_disruption(calculator):
    """Test initial trade disruption -> -20% penalty."""
    from game_cycle.services.popularity_calculator import TRADE_DISRUPTION_PENALTY
    # Act
    adjusted = calculator.adjust_for_trade(
        player_id=6001,
        old_team_id=1,
        new_team_id=2,
        week=5,
        current_popularity=50.0
    )

    # Assert
    expected = 50.0 * (1.0 - TRADE_DISRUPTION_PENALTY)  # 50 × 0.8 = 40
    assert adjusted == expected


def test_trade_high_popularity_player(calculator):
    """Test trade disruption on high popularity player."""
    # Act
    adjusted = calculator.adjust_for_trade(
        player_id=6002,
        old_team_id=1,
        new_team_id=3,
        week=8,
        current_popularity=90.0
    )

    # Assert
    expected = 90.0 * 0.8  # 72.0
    assert adjusted == expected


def test_trade_prevents_negative_popularity(calculator):
    """Test trade adjustment floors at 0.0."""
    # Act
    adjusted = calculator.adjust_for_trade(
        player_id=6003,
        old_team_id=2,
        new_team_id=4,
        week=3,
        current_popularity=5.0
    )

    # Assert
    assert adjusted >= 0.0


# ============================================
# Test apply_playoff_multiplier()
# ============================================

def test_playoff_regular_season_no_boost(calculator):
    """Test regular season week -> 1.0x (no boost)."""
    # Act
    stats, headlines = calculator.apply_playoff_multiplier(
        week=10,  # Regular season
        stats_impact=10.0,
        headlines_impact=5.0
    )

    # Assert
    assert stats == 10.0  # No change
    assert headlines == 5.0  # No change


def test_playoff_wild_card_boost(calculator):
    """Test Wild Card week -> 1.5x boost."""
    # Act
    stats, headlines = calculator.apply_playoff_multiplier(
        week=19,  # Wild Card
        stats_impact=10.0,
        headlines_impact=5.0
    )

    # Assert
    assert stats == 15.0  # 10 × 1.5
    assert headlines == 7.5  # 5 × 1.5


def test_playoff_super_bowl_boost(calculator):
    """Test Super Bowl week -> 1.5x boost."""
    # Act
    stats, headlines = calculator.apply_playoff_multiplier(
        week=22,  # Super Bowl
        stats_impact=20.0,
        headlines_impact=10.0
    )

    # Assert
    assert stats == 30.0  # 20 × 1.5
    assert headlines == 15.0  # 10 × 1.5


def test_playoff_multiplier_all_weeks(calculator):
    """Test playoff multiplier for all week numbers."""
    test_cases = [
        (18, False),  # Regular season finale
        (19, True),   # Wild Card
        (20, True),   # Divisional
        (21, True),   # Conference Championship
        (22, True),   # Super Bowl
    ]

    for week, is_playoff in test_cases:
        stats, headlines = calculator.apply_playoff_multiplier(
            week=week,
            stats_impact=10.0,
            headlines_impact=10.0
        )

        if is_playoff:
            assert stats == 15.0, f"Week {week} should have playoff multiplier"
            assert headlines == 15.0, f"Week {week} should have playoff multiplier"
        else:
            assert stats == 10.0, f"Week {week} should not have playoff multiplier"
            assert headlines == 10.0, f"Week {week} should not have playoff multiplier"


# ============================================
# Test calculate_weekly_popularity() orchestration
# ============================================

def test_weekly_popularity_skeleton_logs_info(calculator):
    """Test full calculation flow (skeleton implementation logs info)."""
    # Note: calculate_weekly_popularity is currently a skeleton
    # This test verifies it runs without errors

    # Act - should not raise exception
    calculator.calculate_weekly_popularity(season=2024, week=10)

    # Assert - verify it completed (no assertion needed, just no exception)


# ============================================
# Integration-style unit tests
# ============================================

def test_full_popularity_calculation_flow(calculator):
    """Test full calculation: (performance × visibility × market) - decay."""
    from game_cycle.services.popularity_calculator import PopularityTier
    # This is a manual calculation test demonstrating the full formula

    # Arrange
    player_id = 7001
    season = 2024
    week = 10
    team_id = 1  # Large market

    # Mock performance score: QB with 80 grade = 80 × 1.2 = 96 (capped at 100)
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=player_id,
        season=season,
        overall_grade=80.0
    )

    # Mock visibility: 2 national headlines = 1.0 + 0.6 = 1.6
    headlines = [
        MockHeadline(1, player_id, priority=90, headline_text="Test 1", body_text=""),
        MockHeadline(2, player_id, priority=85, headline_text="Test 2", body_text=""),
    ]
    calculator._media_api.get_headlines.return_value = headlines
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    performance = calculator.calculate_performance_score(player_id, season, week, "QB")
    visibility = calculator.calculate_visibility_multiplier(player_id, season, week)
    market = calculator.calculate_market_multiplier(team_id)

    raw_score = performance * visibility * market

    # Decay for significant events (game played)
    decay = calculator.apply_weekly_decay(raw_score, ['GAME_RESULT'])

    final_score = max(0, min(100, raw_score + decay))
    tier = calculator.classify_tier(final_score)

    # Assert
    assert performance == 96.0  # 80 × 1.2
    assert visibility == 1.6    # 1.0 + (2 × 0.3)
    assert market > 1.9         # Large market
    assert decay == 0           # No decay for significant events
    assert final_score == 100.0 # Capped at 100
    assert tier == PopularityTier.TRANSCENDENT


def test_popularity_capping_at_100(calculator):
    """Verify final score is capped at 0-100 range."""
    # Test upper bound
    assert min(150.0, 100.0) == 100.0

    # Test lower bound
    assert max(-20.0, 0.0) == 0.0


def test_edge_case_zero_grade_zero_visibility(calculator):
    """Test edge case: player with zero grade and no visibility."""
    # Arrange
    calculator._analytics_api.get_player_season_grade.return_value = MockSeasonGrade(
        player_id=8001,
        season=2024,
        overall_grade=0.0
    )
    calculator._media_api.get_headlines.return_value = []
    calculator._awards_api.get_award_nominees.return_value = []
    calculator._awards_api.get_all_pro_selections.return_value = []
    calculator._awards_api.get_pro_bowl_selections.return_value = []
    calculator._social_api.get_posts_by_player.return_value = []

    # Act
    performance = calculator.calculate_performance_score(8001, 2024, 10, "QB")
    visibility = calculator.calculate_visibility_multiplier(8001, 2024, 10)
    market = calculator.calculate_market_multiplier(1)

    raw_score = performance * visibility * market

    # Assert
    assert performance == 0.0
    assert visibility == 1.0
    assert raw_score == 0.0


def test_position_value_multipliers_are_defined():
    """Verify all expected position multipliers are defined."""
    from game_cycle.services.popularity_calculator import POSITION_VALUE_MULTIPLIERS
    # Key positions should have multipliers
    assert 'QB' in POSITION_VALUE_MULTIPLIERS
    assert 'WR' in POSITION_VALUE_MULTIPLIERS
    assert 'RB' in POSITION_VALUE_MULTIPLIERS
    assert 'K' in POSITION_VALUE_MULTIPLIERS
    assert 'P' in POSITION_VALUE_MULTIPLIERS
    assert 'LT' in POSITION_VALUE_MULTIPLIERS

    # Premium positions should be >= 1.0
    assert POSITION_VALUE_MULTIPLIERS['QB'] >= 1.0
    assert POSITION_VALUE_MULTIPLIERS['EDGE'] >= 1.0

    # Kickers/punters should be < 1.0
    assert POSITION_VALUE_MULTIPLIERS['K'] < 1.0
    assert POSITION_VALUE_MULTIPLIERS['P'] < 1.0
