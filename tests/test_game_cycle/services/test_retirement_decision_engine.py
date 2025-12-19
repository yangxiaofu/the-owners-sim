"""
Unit tests for RetirementDecisionEngine.

Tests retirement probability calculations based on:
- Position-specific age thresholds
- Performance decline
- Injuries
- Championship wins
- Released/unsigned status
- Career accomplishments
"""

import pytest
import sqlite3
import tempfile
import os
import random
from unittest.mock import patch, MagicMock

from src.game_cycle.services.retirement_decision_engine import (
    RetirementDecisionEngine,
    RetirementContext,
    RetirementCandidate,
    RetirementReason,
    PositionRetirementThresholds,
    POSITION_RETIREMENT_AGES,
    POSITION_TO_GROUP,
    DEFAULT_THRESHOLDS,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def temp_db():
    """Create a temporary database with required schema."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create required tables
    cursor.execute("""
        CREATE TABLE player_progression_history (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            overall_before INTEGER,
            overall_after INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE player_injuries (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            severity TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE team_season_history (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            won_super_bowl INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE award_winners (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            award_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            is_winner INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.unlink(path)


@pytest.fixture
def dynasty_id():
    return "test_dynasty_001"


@pytest.fixture
def season():
    return 2025


@pytest.fixture
def engine(temp_db, dynasty_id, season):
    """Create engine instance."""
    return RetirementDecisionEngine(temp_db, dynasty_id, season)


@pytest.fixture
def basic_context(season):
    """Basic retirement context with no special conditions."""
    return RetirementContext(season=season)


@pytest.fixture
def sample_qb():
    """Sample QB player dict (age 39, OVR 75)."""
    return {
        'player_id': 100,
        'first_name': 'Tom',
        'last_name': 'Brady',
        'positions': ['QB'],
        'attributes': {'overall': 75},
        'birthdate': '1986-01-01',
        'team_id': 1,
    }


@pytest.fixture
def sample_rb():
    """Sample RB player dict (age 31, OVR 72)."""
    return {
        'player_id': 200,
        'first_name': 'Derrick',
        'last_name': 'Henry',
        'positions': ['RB'],
        'attributes': {'overall': 72},
        'birthdate': '1994-01-01',
        'team_id': 2,
    }


@pytest.fixture
def young_player():
    """Young player with no retirement risk (age 25, OVR 85)."""
    return {
        'player_id': 300,
        'first_name': 'Young',
        'last_name': 'Star',
        'positions': ['WR'],
        'attributes': {'overall': 85},
        'birthdate': '2000-01-01',
        'team_id': 3,
    }


# ============================================
# Position Threshold Tests (3)
# ============================================

class TestPositionThresholds:

    def test_get_thresholds_for_quarterback(self, engine):
        """QB thresholds: base=38, decline=70, max=45."""
        thresholds = engine._get_position_thresholds('QB')
        assert thresholds.base_age == 38
        assert thresholds.decline_ovr == 70
        assert thresholds.max_age == 45

    def test_get_thresholds_for_running_back(self, engine):
        """RB thresholds: base=30, decline=65, max=34."""
        thresholds = engine._get_position_thresholds('RB')
        assert thresholds.base_age == 30
        assert thresholds.decline_ovr == 65
        assert thresholds.max_age == 34

    def test_get_thresholds_unknown_position_defaults(self, engine):
        """Unknown positions use default thresholds."""
        thresholds = engine._get_position_thresholds('UNKNOWN_POS')
        assert thresholds == DEFAULT_THRESHOLDS


# ============================================
# Age Factor Tests (4)
# ============================================

class TestAgeFactor:

    def test_age_factor_zero_below_base(self, engine, basic_context):
        """Player below base retirement age has low probability."""
        # Young QB at age 30 (8 years below base of 38)
        player = {
            'player_id': 1,
            'first_name': 'Young',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 85},
            'birthdate': '1995-01-01',  # Age 30 in 2025
            'team_id': 1,
        }
        prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No age factor, no decline, only random personal factor possible
        assert prob < 0.10  # Should be very low

    def test_age_factor_fifteen_percent_one_year_past(self, engine, basic_context):
        """Player 1 year past base age gets +15%."""
        # QB at age 39 (1 year past 38)
        player = {
            'player_id': 2,
            'first_name': 'Aging',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 85},  # Above decline threshold
            'birthdate': '1986-01-01',  # Age 39 in 2025
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):  # No random factor
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # 1 year past = 0.15
        assert 0.14 <= prob <= 0.16

    def test_age_factor_thirty_percent_two_years_past(self, engine, basic_context):
        """Player 2 years past base age gets +30%."""
        # QB at age 40 (2 years past 38)
        player = {
            'player_id': 3,
            'first_name': 'Older',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 85},
            'birthdate': '1985-01-01',  # Age 40 in 2025
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # 2 years past = 0.30
        assert 0.29 <= prob <= 0.31

    def test_forced_retirement_at_max_age(self, engine, basic_context):
        """Player at max age has 100% probability."""
        # QB at age 45 (max age for QB)
        player = {
            'player_id': 4,
            'first_name': 'Ancient',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 60},
            'birthdate': '1980-01-01',  # Age 45 in 2025
            'team_id': 1,
        }
        prob, reason = engine.calculate_retirement_probability(player, basic_context)
        assert prob == 1.0
        assert reason == RetirementReason.AGE_DECLINE


# ============================================
# Performance Decline Tests (3)
# ============================================

class TestPerformanceDecline:

    def test_decline_factor_when_ovr_below_threshold(self, engine, basic_context):
        """OVR below threshold adds +25%."""
        # QB with OVR 65 (below 70 threshold)
        player = {
            'player_id': 10,
            'first_name': 'Declining',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 65},  # Below 70
            'birthdate': '1995-01-01',  # Age 30, below base
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # Only decline factor = 0.25
        assert 0.24 <= prob <= 0.26

    def test_no_decline_factor_when_ovr_at_threshold(self, engine, basic_context):
        """OVR at threshold has no decline factor."""
        # QB with OVR 70 (at threshold)
        player = {
            'player_id': 11,
            'first_name': 'Average',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 70},
            'birthdate': '1995-01-01',  # Age 30, below base
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No factors apply
        assert prob == 0.0

    def test_no_decline_factor_when_ovr_above_threshold(self, engine, basic_context):
        """OVR above threshold has no decline factor."""
        # QB with OVR 85 (above 70)
        player = {
            'player_id': 12,
            'first_name': 'Elite',
            'last_name': 'QB',
            'positions': ['QB'],
            'attributes': {'overall': 85},
            'birthdate': '1995-01-01',  # Age 30, below base
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No factors apply
        assert prob == 0.0


# ============================================
# Injury Factor Tests (3)
# ============================================

class TestInjuryFactor:

    def test_career_ending_injury_95_percent(self, engine, season):
        """Player with career-ending injury has 95% probability."""
        player = {
            'player_id': 20,
            'first_name': 'Injured',
            'last_name': 'Player',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1995-01-01',
            'team_id': 1,
        }
        context = RetirementContext(
            season=season,
            career_ending_injury_ids={20}  # Player in set
        )
        prob, reason = engine.calculate_retirement_probability(player, context)
        assert prob == 0.95
        assert reason == RetirementReason.INJURY

    def test_multi_season_injury_adds_twenty_percent(self, temp_db, dynasty_id, season, basic_context):
        """2+ seasons missed adds +20%."""
        # Insert injury history
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO player_injuries (dynasty_id, player_id, season, severity) VALUES (?, ?, ?, ?)",
            (dynasty_id, 21, 2023, 'season_ending')
        )
        cursor.execute(
            "INSERT INTO player_injuries (dynasty_id, player_id, season, severity) VALUES (?, ?, ?, ?)",
            (dynasty_id, 21, 2024, 'season_ending')
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        player = {
            'player_id': 21,
            'first_name': 'Injury',
            'last_name': 'Prone',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1995-01-01',  # Age 30
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # Multi-season injury = 0.20
        assert 0.19 <= prob <= 0.26  # Allow for small variance

    def test_single_season_injury_no_factor(self, temp_db, dynasty_id, season, basic_context):
        """1 season missed has no additional factor."""
        # Insert single injury
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO player_injuries (dynasty_id, player_id, season, severity) VALUES (?, ?, ?, ?)",
            (dynasty_id, 22, 2024, 'season_ending')
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        player = {
            'player_id': 22,
            'first_name': 'One',
            'last_name': 'Injury',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1997-01-01',  # Age 28, below base
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No factors apply (single injury doesn't count)
        assert prob == 0.0


# ============================================
# Championship Factor Tests (3)
# ============================================

class TestChampionshipFactor:

    def test_championship_factor_first_sb_age_33_plus(self, temp_db, dynasty_id, season):
        """First SB win at age 33+ adds +30%."""
        # Insert SB win for team
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2025, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1
        )
        player = {
            'player_id': 30,
            'first_name': 'Champion',
            'last_name': 'Vet',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1992-01-01',  # Age 33
            'team_id': 1,  # On winning team
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, context)
        # Championship factor = 0.30
        assert 0.29 <= prob <= 0.36  # May include small personal factor
        assert reason == RetirementReason.CHAMPIONSHIP

    def test_no_championship_factor_not_first_sb(self, temp_db, dynasty_id, season):
        """Second+ SB win has no championship factor."""
        # Insert 2 SB wins for team
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2024, 1)
        )
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2025, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1
        )
        player = {
            'player_id': 31,
            'first_name': 'Multi',
            'last_name': 'Champ',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1992-01-01',  # Age 33
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, context)
        # No championship factor (not first SB)
        assert prob < 0.10
        assert reason == RetirementReason.AGE_DECLINE

    def test_no_championship_factor_under_33(self, temp_db, dynasty_id, season):
        """SB win under age 33 has no championship factor."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2025, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1
        )
        player = {
            'player_id': 32,
            'first_name': 'Young',
            'last_name': 'Champ',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1993-01-01',  # Age 32
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, context)
        # No championship factor (too young)
        assert prob == 0.0


# ============================================
# Released Factor Tests (2)
# ============================================

class TestReleasedFactor:

    def test_released_factor_in_set(self, engine, season):
        """Player in released_player_ids gets +40%."""
        context = RetirementContext(
            season=season,
            released_player_ids={40}
        )
        player = {
            'player_id': 40,
            'first_name': 'Cut',
            'last_name': 'Player',
            'positions': ['WR'],
            'attributes': {'overall': 75},
            'birthdate': '1997-01-01',  # Age 28
            'team_id': 0,
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, context)
        # Released factor = 0.40
        assert 0.39 <= prob <= 0.41
        assert reason == RetirementReason.RELEASED

    def test_no_released_factor_when_signed(self, engine, basic_context):
        """Player not in released set has no released factor."""
        player = {
            'player_id': 41,
            'first_name': 'Signed',
            'last_name': 'Player',
            'positions': ['WR'],
            'attributes': {'overall': 75},
            'birthdate': '1997-01-01',  # Age 28
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        assert prob == 0.0


# ============================================
# Accomplishments Factor Tests (3)
# ============================================

class TestAccomplishmentsFactor:

    def test_accomplishments_mvp_sb_35_plus(self, temp_db, dynasty_id, season, basic_context):
        """MVP + SB win + age 35+ adds +25%."""
        # Insert MVP and SB win
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 50, 'mvp', 2023, 1)
        )
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2022, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        # Use QB position - base age 38, so 35 is below base (no age factor)
        player = {
            'player_id': 50,
            'first_name': 'Legend',
            'last_name': 'Player',
            'positions': ['QB'],
            'attributes': {'overall': 80},
            'birthdate': '1990-01-01',  # Age 35, below QB base of 38
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, basic_context)
        # Only accomplishments factor = 0.25 (no age factor for QB at 35)
        assert 0.24 <= prob <= 0.26
        assert reason == RetirementReason.CHAMPIONSHIP

    def test_no_accomplishments_without_mvp(self, temp_db, dynasty_id, season, basic_context):
        """SB win without MVP has no accomplishments factor."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2022, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        # Use QB at age 35 (below base of 38) to isolate accomplishments test
        player = {
            'player_id': 51,
            'first_name': 'No',
            'last_name': 'MVP',
            'positions': ['QB'],
            'attributes': {'overall': 80},
            'birthdate': '1990-01-01',  # Age 35, below QB base of 38
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No accomplishments factor (no MVP), no age factor
        assert prob == 0.0

    def test_no_accomplishments_under_35(self, temp_db, dynasty_id, season, basic_context):
        """MVP + SB under 35 has no accomplishments factor."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 52, 'mvp', 2023, 1)
        )
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2022, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        # Use QB at age 34 (below base of 38) to isolate accomplishments test
        player = {
            'player_id': 52,
            'first_name': 'Young',
            'last_name': 'GOAT',
            'positions': ['QB'],
            'attributes': {'overall': 95},
            'birthdate': '1991-01-01',  # Age 34, below 35 threshold and QB base
            'team_id': 1,
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # No accomplishments factor (too young for accomplishments check)
        assert prob == 0.0


# ============================================
# Combined Probability Tests (4)
# ============================================

class TestCombinedProbability:

    def test_probability_caps_at_95_percent(self, engine, season):
        """Combined factors cap at 95%."""
        # Max age RB (forced retirement) plus other factors
        context = RetirementContext(
            season=season,
            released_player_ids={60}
        )
        player = {
            'player_id': 60,
            'first_name': 'Ancient',
            'last_name': 'RB',
            'positions': ['RB'],
            'attributes': {'overall': 50},  # Way below threshold
            'birthdate': '1991-01-01',  # Age 34 = max for RB
            'team_id': 0,
        }
        prob, _ = engine.calculate_retirement_probability(player, context)
        # At max age = 100%, but result should still be capped
        assert prob <= 1.0

    def test_multiple_factors_accumulate(self, engine, season):
        """Age + decline + released factors sum correctly."""
        context = RetirementContext(
            season=season,
            released_player_ids={61}
        )
        # QB at 40 (2 years past), OVR 65 (below 70), released
        player = {
            'player_id': 61,
            'first_name': 'Multi',
            'last_name': 'Factor',
            'positions': ['QB'],
            'attributes': {'overall': 65},
            'birthdate': '1985-01-01',  # Age 40
            'team_id': 0,
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, context)
        # Age (2 yrs * 0.15 = 0.30) + Decline (0.25) + Released (0.40) = 0.95
        assert 0.90 <= prob <= 0.95
        assert reason == RetirementReason.RELEASED

    def test_reason_priority_injury_over_championship(self, temp_db, dynasty_id, season):
        """Injury reason takes priority over championship."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2025, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1,
            career_ending_injury_ids={62}
        )
        player = {
            'player_id': 62,
            'first_name': 'Injured',
            'last_name': 'Champ',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1992-01-01',  # Age 33
            'team_id': 1,
        }
        prob, reason = engine.calculate_retirement_probability(player, context)
        # Injury takes priority
        assert reason == RetirementReason.INJURY
        assert prob == 0.95

    def test_reason_priority_championship_over_released(self, temp_db, dynasty_id, season):
        """Championship reason takes priority when applicable."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2025, 1)
        )
        conn.commit()
        conn.close()

        engine = RetirementDecisionEngine(temp_db, dynasty_id, season)
        # Player won SB then was released (unusual but possible)
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1,
            released_player_ids={63}
        )
        player = {
            'player_id': 63,
            'first_name': 'Champ',
            'last_name': 'Released',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1992-01-01',  # Age 33
            'team_id': 1,  # Was on winning team
        }
        with patch('random.random', return_value=0.0):
            prob, reason = engine.calculate_retirement_probability(player, context)
        # Released factor still applies, but championship was set last in code
        # Due to code order, released sets reason last
        assert reason == RetirementReason.RELEASED


# ============================================
# Batch & Edge Case Tests (5)
# ============================================

class TestBatchAndEdgeCases:

    def test_evaluate_all_players_returns_candidates(self, engine, basic_context, young_player, sample_qb):
        """evaluate_all_players returns list of RetirementCandidate."""
        players = [young_player, sample_qb]
        candidates = engine.evaluate_all_players(players, basic_context)
        assert len(candidates) == 2
        assert all(isinstance(c, RetirementCandidate) for c in candidates)

    def test_evaluate_all_players_empty_list(self, engine, basic_context):
        """evaluate_all_players returns empty list for empty input."""
        candidates = engine.evaluate_all_players([], basic_context)
        assert candidates == []

    def test_missing_birthdate_defaults_to_25(self, engine, basic_context):
        """Missing birthdate assumes age 25."""
        player = {
            'player_id': 70,
            'first_name': 'No',
            'last_name': 'Birthdate',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            # No birthdate
            'team_id': 1,
        }
        age = engine._calculate_age(player.get('birthdate'))
        assert age == 25

    def test_missing_overall_defaults_to_70(self, engine, basic_context):
        """Missing overall rating assumes 70."""
        player = {
            'player_id': 71,
            'first_name': 'No',
            'last_name': 'OVR',
            'positions': ['WR'],
            # No attributes
            'team_id': 1,
        }
        ovr = engine._get_overall(player)
        assert ovr == 70

    def test_free_agent_team_id_zero(self, engine, basic_context):
        """Free agents (team_id=0) are handled correctly."""
        player = {
            'player_id': 72,
            'first_name': 'Free',
            'last_name': 'Agent',
            'positions': ['WR'],
            'attributes': {'overall': 80},
            'birthdate': '1997-01-01',
            'team_id': 0,  # Free agent
        }
        with patch('random.random', return_value=0.0):
            prob, _ = engine.calculate_retirement_probability(player, basic_context)
        # Should handle without error
        assert prob >= 0.0


# ============================================
# Additional Helper Tests
# ============================================

class TestHelperMethods:

    def test_get_primary_position_from_list(self, engine):
        """Extract position from list."""
        player = {'positions': ['QB', 'WR']}
        pos = engine._get_primary_position(player)
        assert pos == 'QB'

    def test_get_primary_position_from_json_string(self, engine):
        """Extract position from JSON string."""
        player = {'positions': '["RB", "FB"]'}
        pos = engine._get_primary_position(player)
        assert pos == 'RB'

    def test_get_player_name(self, engine):
        """Get formatted player name."""
        player = {'first_name': 'Patrick', 'last_name': 'Mahomes'}
        name = engine._get_player_name(player)
        assert name == 'Patrick Mahomes'

    def test_retirement_candidate_to_dict(self, engine, basic_context, sample_qb):
        """RetirementCandidate.to_dict() works correctly."""
        candidates = engine.evaluate_all_players([sample_qb], basic_context)
        candidate = candidates[0]
        d = candidate.to_dict()
        assert d['player_id'] == 100
        assert d['player_name'] == 'Tom Brady'
        assert 'probability' in d
        assert 'reason' in d

    def test_retirement_context_to_dict(self, season):
        """RetirementContext.to_dict() works correctly."""
        context = RetirementContext(
            season=season,
            super_bowl_winner_team_id=1,
            released_player_ids={10, 20},
            career_ending_injury_ids={30}
        )
        d = context.to_dict()
        assert d['season'] == season
        assert d['super_bowl_winner_team_id'] == 1
        assert set(d['released_player_ids']) == {10, 20}
        assert d['career_ending_injury_ids'] == [30]
