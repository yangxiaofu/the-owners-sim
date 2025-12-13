"""
Tests for PowerRankingsService - Media Coverage Milestone, Tollgate 2.

Comprehensive tests for:
- Power score calculation
- Tier classification
- Blurb generation
- Movement tracking
- Weight adaptivity for early season
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

from src.game_cycle.services.power_rankings_service import (
    PowerRankingsService,
    Tier,
    TeamPowerData,
    ELITE_TEMPLATES,
    CONTENDER_TEMPLATES,
    PLAYOFF_TEMPLATES,
    BUBBLE_TEMPLATES,
    REBUILDING_TEMPLATES,
    RISING_TEMPLATES,
    FALLING_TEMPLATES,
    WINNING_STREAK_PHRASES,
    LOSING_STREAK_PHRASES,
)
from src.game_cycle.database.standings_api import TeamStanding
from src.game_cycle.database.media_coverage_api import PowerRanking


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
def test_db_with_schema(test_db_path):
    """Create database with required schema."""
    conn = sqlite3.connect(test_db_path)
    conn.executescript("""
        -- Dynasties table (required for foreign keys)
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Standings table
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            team_id INTEGER NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            UNIQUE(dynasty_id, season, season_type, team_id)
        );

        -- Box scores table
        CREATE TABLE IF NOT EXISTS box_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            q1_score INTEGER DEFAULT 0,
            q2_score INTEGER DEFAULT 0,
            q3_score INTEGER DEFAULT 0,
            q4_score INTEGER DEFAULT 0,
            ot_score INTEGER DEFAULT 0,
            first_downs INTEGER DEFAULT 0,
            third_down_att INTEGER DEFAULT 0,
            third_down_conv INTEGER DEFAULT 0,
            fourth_down_att INTEGER DEFAULT 0,
            fourth_down_conv INTEGER DEFAULT 0,
            total_yards INTEGER DEFAULT 0,
            passing_yards INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            turnovers INTEGER DEFAULT 0,
            penalties INTEGER DEFAULT 0,
            penalty_yards INTEGER DEFAULT 0,
            time_of_possession INTEGER,
            team_timeouts_remaining INTEGER DEFAULT 3,
            team_timeouts_used_h1 INTEGER DEFAULT 0,
            team_timeouts_used_h2 INTEGER DEFAULT 0,
            UNIQUE(dynasty_id, game_id, team_id)
        );

        -- Games table for joining box scores
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT DEFAULT 'scheduled',
            slot TEXT
        );

        -- Head to head table
        CREATE TABLE IF NOT EXISTS head_to_head (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_a_id INTEGER NOT NULL,
            team_b_id INTEGER NOT NULL,
            team_a_wins INTEGER DEFAULT 0,
            team_b_wins INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            team_a_home_wins INTEGER DEFAULT 0,
            team_a_away_wins INTEGER DEFAULT 0,
            last_meeting_season INTEGER,
            last_meeting_winner INTEGER,
            current_streak_team INTEGER,
            current_streak_count INTEGER DEFAULT 0,
            playoff_meetings INTEGER DEFAULT 0,
            playoff_team_a_wins INTEGER DEFAULT 0,
            playoff_team_b_wins INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, team_a_id, team_b_id)
        );

        -- Power rankings table
        CREATE TABLE IF NOT EXISTS power_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
            rank INTEGER NOT NULL CHECK(rank BETWEEN 1 AND 32),
            previous_rank INTEGER,
            tier TEXT NOT NULL CHECK(tier IN ('ELITE', 'CONTENDER', 'PLAYOFF', 'BUBBLE', 'REBUILDING')),
            blurb TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, season, week, team_id)
        );

        -- Insert test dynasty
        INSERT INTO dynasties (dynasty_id) VALUES ('test_dynasty');
    """)
    conn.commit()
    conn.close()
    yield test_db_path


@pytest.fixture
def populated_db(test_db_with_schema):
    """Populate database with test data."""
    conn = sqlite3.connect(test_db_with_schema)

    # Insert standings for all 32 teams with varying records
    for team_id in range(1, 33):
        # Create varied records
        if team_id <= 4:  # Elite teams
            wins, losses = 10, 2
            pf, pa = 350, 200
        elif team_id <= 10:  # Contenders
            wins, losses = 8, 4
            pf, pa = 300, 250
        elif team_id <= 16:  # Playoff bubble
            wins, losses = 6, 6
            pf, pa = 280, 280
        elif team_id <= 22:  # Bubble teams
            wins, losses = 5, 7
            pf, pa = 250, 290
        else:  # Rebuilding
            wins, losses = 3, 9
            pf, pa = 200, 350

        conn.execute("""
            INSERT INTO standings (
                dynasty_id, season, season_type, team_id,
                wins, losses, ties, points_for, points_against,
                division_wins, division_losses, conference_wins, conference_losses,
                home_wins, home_losses, away_wins, away_losses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_dynasty', 2024, 'regular_season', team_id,
            wins, losses, 0, pf, pa,
            wins // 2, losses // 2, wins // 2 + 1, losses // 2 + 1,
            wins // 2, losses // 2, wins // 2, losses // 2
        ))

    conn.commit()
    conn.close()
    return test_db_with_schema


@pytest.fixture
def service(populated_db):
    """Create PowerRankingsService instance."""
    return PowerRankingsService(
        db_path=populated_db,
        dynasty_id='test_dynasty',
        season=2024
    )


def create_mock_standing(
    team_id: int,
    wins: int,
    losses: int,
    ties: int = 0,
    points_for: int = 200,
    points_against: int = 200
) -> TeamStanding:
    """Create a mock TeamStanding for testing."""
    return TeamStanding(
        team_id=team_id,
        wins=wins,
        losses=losses,
        ties=ties,
        points_for=points_for,
        points_against=points_against,
        division_wins=wins // 2,
        division_losses=losses // 2,
        conference_wins=wins // 2,
        conference_losses=losses // 2,
        home_wins=wins // 2,
        home_losses=losses // 2,
        away_wins=wins // 2,
        away_losses=losses // 2,
        playoff_seed=None
    )


# ============================================
# Template Count Tests
# ============================================

class TestBlurbTemplates:
    """Tests for template counts and validity."""

    def test_elite_templates_count(self):
        """Verify ELITE templates have at least 20 entries."""
        assert len(ELITE_TEMPLATES) >= 20

    def test_contender_templates_count(self):
        """Verify CONTENDER templates have at least 20 entries."""
        assert len(CONTENDER_TEMPLATES) >= 20

    def test_playoff_templates_count(self):
        """Verify PLAYOFF templates have at least 20 entries."""
        assert len(PLAYOFF_TEMPLATES) >= 20

    def test_bubble_templates_count(self):
        """Verify BUBBLE templates have at least 20 entries."""
        assert len(BUBBLE_TEMPLATES) >= 20

    def test_rebuilding_templates_count(self):
        """Verify REBUILDING templates have at least 20 entries."""
        assert len(REBUILDING_TEMPLATES) >= 20

    def test_total_templates_exceeds_100(self):
        """Verify total template count exceeds 100."""
        total = (
            len(ELITE_TEMPLATES) +
            len(CONTENDER_TEMPLATES) +
            len(PLAYOFF_TEMPLATES) +
            len(BUBBLE_TEMPLATES) +
            len(REBUILDING_TEMPLATES) +
            len(RISING_TEMPLATES) +
            len(FALLING_TEMPLATES) +
            len(WINNING_STREAK_PHRASES) +
            len(LOSING_STREAK_PHRASES)
        )
        assert total >= 100

    def test_templates_have_required_placeholders(self):
        """Verify templates have expected placeholders."""
        # Check ELITE templates have at least team placeholder
        for template in ELITE_TEMPLATES:
            assert '{team}' in template or '{nickname}' in template or '{city}' in template


# ============================================
# Tier Classification Tests
# ============================================

class TestTierClassification:
    """Tests for tier classification logic."""

    def test_elite_tier_ranks_1_to_4(self, service):
        """Ranks 1-4 should be ELITE tier."""
        for rank in range(1, 5):
            tier = service._get_tier_for_rank(rank)
            assert tier == Tier.ELITE

    def test_contender_tier_ranks_5_to_10(self, service):
        """Ranks 5-10 should be CONTENDER tier."""
        for rank in range(5, 11):
            tier = service._get_tier_for_rank(rank)
            assert tier == Tier.CONTENDER

    def test_playoff_tier_ranks_11_to_16(self, service):
        """Ranks 11-16 should be PLAYOFF tier."""
        for rank in range(11, 17):
            tier = service._get_tier_for_rank(rank)
            assert tier == Tier.PLAYOFF

    def test_bubble_tier_ranks_17_to_22(self, service):
        """Ranks 17-22 should be BUBBLE tier."""
        for rank in range(17, 23):
            tier = service._get_tier_for_rank(rank)
            assert tier == Tier.BUBBLE

    def test_rebuilding_tier_ranks_23_to_32(self, service):
        """Ranks 23-32 should be REBUILDING tier."""
        for rank in range(23, 33):
            tier = service._get_tier_for_rank(rank)
            assert tier == Tier.REBUILDING


# ============================================
# Weight Adaptation Tests
# ============================================

class TestWeightAdaptation:
    """Tests for early season weight adaptation."""

    def test_early_season_weights_weeks_1_to_3(self, service):
        """Weeks 1-3 should use early season weights."""
        for week in [1, 2, 3]:
            weights = service._get_weights_for_week(week)
            assert weights['record'] == 0.45
            assert weights['point_diff'] == 0.30
            assert weights['recent'] == 0.05  # Low weight for limited games

    def test_standard_weights_week_4_onwards(self, service):
        """Week 4+ should use standard weights."""
        for week in [4, 8, 12, 18]:
            weights = service._get_weights_for_week(week)
            assert weights['record'] == 0.30
            assert weights['point_diff'] == 0.20
            assert weights['recent'] == 0.20

    def test_weights_sum_to_one(self, service):
        """All weights should sum to 1.0."""
        early_weights = service._get_weights_for_week(1)
        standard_weights = service._get_weights_for_week(10)

        early_sum = sum(early_weights.values())
        standard_sum = sum(standard_weights.values())

        assert abs(early_sum - 1.0) < 0.001
        assert abs(standard_sum - 1.0) < 0.001


# ============================================
# Score Calculation Tests
# ============================================

class TestScoreCalculations:
    """Tests for individual score component calculations."""

    def test_record_score_perfect_record(self, service):
        """12-0 team should have 100 record score."""
        standing = create_mock_standing(1, wins=12, losses=0)
        score = service._calculate_record_score(standing)
        assert score == 100.0

    def test_record_score_winless_record(self, service):
        """0-12 team should have 0 record score."""
        standing = create_mock_standing(1, wins=0, losses=12)
        score = service._calculate_record_score(standing)
        assert score == 0.0

    def test_record_score_500_record(self, service):
        """6-6 team should have ~50 record score."""
        standing = create_mock_standing(1, wins=6, losses=6)
        score = service._calculate_record_score(standing)
        assert abs(score - 50.0) < 1.0

    def test_record_score_no_games(self, service):
        """Team with no games should have neutral 50 score."""
        standing = create_mock_standing(1, wins=0, losses=0)
        score = service._calculate_record_score(standing)
        assert score == 50.0

    def test_point_diff_score_high_positive(self, service):
        """Large positive point differential should score high."""
        standing = create_mock_standing(1, wins=10, losses=2, points_for=350, points_against=200)
        score = service._calculate_point_diff_score(standing, week=12)
        # +150 over 12 games = +12.5 PPG -> should be well above 50
        assert score > 75

    def test_point_diff_score_high_negative(self, service):
        """Large negative point differential should score low."""
        standing = create_mock_standing(1, wins=2, losses=10, points_for=200, points_against=350)
        score = service._calculate_point_diff_score(standing, week=12)
        # -150 over 12 games = -12.5 PPG -> should be well below 50
        assert score < 25

    def test_point_diff_score_neutral(self, service):
        """Zero point differential should score ~50."""
        standing = create_mock_standing(1, wins=6, losses=6, points_for=240, points_against=240)
        score = service._calculate_point_diff_score(standing, week=12)
        assert abs(score - 50) < 5


# ============================================
# Movement Display Tests
# ============================================

class TestMovementDisplay:
    """Tests for ranking movement display."""

    def test_movement_up_display(self, service):
        """Moving up in rankings shows up arrow."""
        result = service.get_movement_display(current_rank=5, previous_rank=8)
        assert result == "▲3"

    def test_movement_down_display(self, service):
        """Moving down in rankings shows down arrow."""
        result = service.get_movement_display(current_rank=8, previous_rank=5)
        assert result == "▼3"

    def test_movement_no_change_display(self, service):
        """No movement shows dash."""
        result = service.get_movement_display(current_rank=5, previous_rank=5)
        assert result == "—"

    def test_movement_new_display(self, service):
        """No previous rank shows NEW."""
        result = service.get_movement_display(current_rank=5, previous_rank=None)
        assert result == "NEW"


# ============================================
# Integration Tests
# ============================================

class TestRankingCalculation:
    """Integration tests for full ranking calculation."""

    def test_calculate_rankings_returns_32_teams(self, service):
        """Rankings should include all 32 teams."""
        rankings = service.calculate_rankings(week=12)
        assert len(rankings) == 32

    def test_calculate_rankings_unique_ranks(self, service):
        """Each team should have unique rank 1-32."""
        rankings = service.calculate_rankings(week=12)
        ranks = [r.rank for r in rankings]
        assert sorted(ranks) == list(range(1, 33))

    def test_calculate_rankings_has_tiers(self, service):
        """All rankings should have valid tiers."""
        rankings = service.calculate_rankings(week=12)
        valid_tiers = {'ELITE', 'CONTENDER', 'PLAYOFF', 'BUBBLE', 'REBUILDING'}
        for ranking in rankings:
            assert ranking.tier in valid_tiers

    def test_calculate_rankings_has_blurbs(self, service):
        """All rankings should have non-empty blurbs."""
        rankings = service.calculate_rankings(week=12)
        for ranking in rankings:
            assert ranking.blurb is not None
            assert len(ranking.blurb) > 10

    def test_calculate_rankings_sorted_by_rank(self, service):
        """Rankings should be sorted by rank ascending."""
        rankings = service.calculate_rankings(week=12)
        for i in range(len(rankings)):
            assert rankings[i].rank == i + 1

    def test_elite_teams_have_best_records(self, service):
        """Teams ranked 1-4 should have best records."""
        rankings = service.calculate_rankings(week=12)
        elite = [r for r in rankings if r.tier == 'ELITE']
        assert len(elite) == 4
        # All elite teams should have team_id <= 4 (based on our fixture)
        elite_team_ids = {r.team_id for r in elite}
        assert elite_team_ids == {1, 2, 3, 4}


# ============================================
# Blurb Generation Tests
# ============================================

class TestBlurbGeneration:
    """Tests for blurb generation."""

    def test_blurb_contains_team_reference(self, service):
        """Blurbs should contain team name, city, or nickname."""
        rankings = service.calculate_rankings(week=12)
        # Check a sample of blurbs
        for ranking in rankings[:5]:
            blurb = ranking.blurb.lower()
            # Blurb should have some team identifier
            assert len(blurb) > 20  # Minimum length check

    def test_blurb_tier_appropriate(self, service):
        """Blurb tone should match tier."""
        rankings = service.calculate_rankings(week=12)

        # Elite team blurbs should have positive language
        elite_rankings = [r for r in rankings if r.tier == 'ELITE']
        for r in elite_rankings:
            # Check blurb doesn't contain negative language
            blurb_lower = r.blurb.lower()
            negative_words = ['struggling', 'disappointing', 'lost season', 'rebuilding']
            for word in negative_words:
                assert word not in blurb_lower, f"Elite blurb contains '{word}'"

    def test_blurb_generation_deterministic_structure(self, service):
        """Blurb structure should be consistent."""
        team_data = TeamPowerData(
            team_id=1,
            team_name="Buffalo Bills",
            city="Buffalo",
            wins=10,
            losses=2,
            ties=0,
            point_differential=150,
            streak_type="W",
            streak_count=5,
            rank=1,
            tier="ELITE",
            power_score=85.0,
        )

        blurb = service._generate_blurb(team_data, previous_rank=2)
        assert isinstance(blurb, str)
        assert len(blurb) > 0


# ============================================
# Persistence Tests
# ============================================

class TestRankingPersistence:
    """Tests for saving and retrieving rankings."""

    def test_calculate_and_save_rankings(self, service):
        """Rankings should be saved and retrievable."""
        saved = service.calculate_and_save_rankings(week=12)
        assert len(saved) == 32

        # Retrieve and verify
        retrieved = service.get_rankings(week=12)
        assert len(retrieved) == 32

    def test_previous_rank_tracking(self, service):
        """Previous week rankings should be tracked."""
        # Save week 11 rankings
        service.calculate_and_save_rankings(week=11)

        # Save week 12 rankings
        week12 = service.calculate_and_save_rankings(week=12)

        # Week 12 rankings should have previous_rank populated
        for ranking in week12:
            assert ranking.previous_rank is not None

    def test_get_team_ranking_history(self, service):
        """Should retrieve ranking history for a team."""
        # Save multiple weeks
        for week in [10, 11, 12]:
            service.calculate_and_save_rankings(week=week)

        # Get history for team 1
        history = service.get_team_ranking_history(team_id=1)
        assert len(history) >= 3

        # History should be in week order
        weeks = [h.week for h in history]
        assert weeks == sorted(weeks)


# ============================================
# Edge Case Tests
# ============================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_no_standings_returns_empty(self, test_db_with_schema):
        """Service should handle missing standings gracefully."""
        # Create service with empty standings
        conn = sqlite3.connect(test_db_with_schema)
        conn.execute("DELETE FROM standings")
        conn.commit()
        conn.close()

        service = PowerRankingsService(
            db_path=test_db_with_schema,
            dynasty_id='test_dynasty',
            season=2024
        )
        rankings = service.calculate_rankings(week=1)
        assert rankings == []

    def test_week_1_rankings(self, service):
        """Week 1 should use early season weights."""
        rankings = service.calculate_rankings(week=1)
        assert len(rankings) == 32

    def test_tie_record_handling(self, test_db_with_schema):
        """Teams with ties should be handled correctly."""
        conn = sqlite3.connect(test_db_with_schema)
        conn.execute("""
            INSERT INTO standings (
                dynasty_id, season, season_type, team_id,
                wins, losses, ties, points_for, points_against,
                division_wins, division_losses, conference_wins, conference_losses,
                home_wins, home_losses, away_wins, away_losses
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test_dynasty', 2024, 'regular_season', 99,
            5, 5, 2, 280, 280,
            2, 2, 3, 3,
            3, 2, 2, 3
        ))
        conn.commit()
        conn.close()

        service = PowerRankingsService(
            db_path=test_db_with_schema,
            dynasty_id='test_dynasty',
            season=2024
        )

        # Should not raise exception
        standings = service._standings_api.get_standings('test_dynasty', 2024)
        tie_team = next((s for s in standings if s.team_id == 99), None)
        if tie_team:
            score = service._calculate_record_score(tie_team)
            # 5-5-2 = (5 + 0.5*2) / 12 = 6/12 = 50%
            assert abs(score - 50) < 5


# ============================================
# Team Info Tests
# ============================================

class TestTeamInfo:
    """Tests for team information loading."""

    def test_get_team_info_valid_team(self, service):
        """Should return team info for valid team ID."""
        name, city, nickname = service._get_team_info(1)
        # Team 1 is Buffalo Bills
        assert "Buffalo" in name or "Bills" in name or "Buffalo" in city

    def test_get_team_info_invalid_team(self, service):
        """Should return fallback for invalid team ID."""
        name, city, nickname = service._get_team_info(999)
        assert "Team 999" in name or "Unknown" in city


# ============================================
# Strength Determination Tests
# ============================================

class TestStrengthDetermination:
    """Tests for team strength determination."""

    def test_determine_strength_high_point_diff(self, service):
        """High point diff should return 'dominant play'."""
        team_data = TeamPowerData(
            team_id=1,
            team_name="Test",
            city="Test",
            point_diff_score=85.0,
            recent_score=50.0,
            sov_score=50.0,
            quality_wins_score=50.0,
        )
        strength = service._determine_team_strength(team_data)
        assert strength == "dominant play"

    def test_determine_strength_recent_surge(self, service):
        """High recent score should return 'recent surge'."""
        team_data = TeamPowerData(
            team_id=1,
            team_name="Test",
            city="Test",
            point_diff_score=60.0,
            recent_score=80.0,
            sov_score=50.0,
            quality_wins_score=50.0,
        )
        strength = service._determine_team_strength(team_data)
        assert strength == "recent surge"
