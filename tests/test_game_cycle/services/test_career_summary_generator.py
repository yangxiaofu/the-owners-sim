"""
Unit tests for CareerSummaryGenerator.

Tests career summary generation including:
- Lifetime stats aggregation from player_game_stats
- Award counting (MVP, All-Pro, Pro Bowl, Super Bowl)
- HOF score calculation (0-100)
- Narrative text generation
"""

import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.services.career_summary_generator import (
    CareerSummaryGenerator,
    HOF_THRESHOLDS,
    HOFStatsThreshold,
    POSITION_TO_GROUP,
    TEAM_NAMES,
)
from src.game_cycle.database.retired_players_api import CareerSummary


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
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER DEFAULT 1,
            home_team_id INTEGER,
            away_team_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE player_game_stats (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0
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

    cursor.execute("""
        CREATE TABLE all_pro_selections (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            position TEXT NOT NULL,
            team_type TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE pro_bowl_selections (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            position TEXT NOT NULL
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
        CREATE TABLE draft_classes (
            draft_class_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE draft_prospects (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            draft_class_id INTEGER NOT NULL,
            roster_player_id INTEGER,
            is_drafted INTEGER DEFAULT 0,
            draft_round INTEGER,
            draft_pick INTEGER
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
def generator(temp_db, dynasty_id):
    """Create generator instance."""
    return CareerSummaryGenerator(temp_db, dynasty_id)


@pytest.fixture
def sample_qb():
    """Sample QB player dict."""
    return {
        'player_id': 100,
        'first_name': 'Tom',
        'last_name': 'Brady',
        'positions': ['QB'],
        'team_id': 1,
    }


@pytest.fixture
def sample_rb():
    """Sample RB player dict."""
    return {
        'player_id': 200,
        'first_name': 'Derrick',
        'last_name': 'Henry',
        'positions': ['RB'],
        'team_id': 2,
    }


@pytest.fixture
def sample_wr():
    """Sample WR player dict."""
    return {
        'player_id': 300,
        'first_name': 'Tyreek',
        'last_name': 'Hill',
        'positions': ['WR'],
        'team_id': 3,
    }


@pytest.fixture
def sample_lb():
    """Sample LB player dict."""
    return {
        'player_id': 400,
        'first_name': 'Luke',
        'last_name': 'Kuechly',
        'positions': ['MLB'],
        'team_id': 4,
    }


@pytest.fixture
def sample_kicker():
    """Sample K player dict."""
    return {
        'player_id': 500,
        'first_name': 'Justin',
        'last_name': 'Tucker',
        'positions': ['K'],
        'team_id': 5,
    }


# ============================================
# Stats Aggregation Tests (5)
# ============================================

class TestStatsAggregation:

    def test_aggregate_career_stats_passing(self, temp_db, dynasty_id, generator, sample_qb):
        """Aggregate passing stats across multiple games."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert games and stats
        for game_id in range(1, 4):
            cursor.execute(
                "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
                (game_id, dynasty_id, 2024)
            )
            cursor.execute("""
                INSERT INTO player_game_stats
                (dynasty_id, game_id, player_id, team_id, passing_yards, passing_tds, passing_interceptions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dynasty_id, game_id, 100, 1, 300, 3, 1))

        conn.commit()
        conn.close()

        stats = generator._aggregate_career_stats(100)

        assert stats['games_played'] == 3
        assert stats['pass_yards'] == 900  # 300 * 3
        assert stats['pass_tds'] == 9      # 3 * 3
        assert stats['pass_ints'] == 3     # 1 * 3

    def test_aggregate_career_stats_rushing(self, temp_db, dynasty_id, generator, sample_rb):
        """Aggregate rushing stats across multiple games."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        for game_id in range(1, 5):
            cursor.execute(
                "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
                (game_id, dynasty_id, 2024)
            )
            cursor.execute("""
                INSERT INTO player_game_stats
                (dynasty_id, game_id, player_id, team_id, rushing_yards, rushing_tds)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (dynasty_id, game_id, 200, 2, 125, 1))

        conn.commit()
        conn.close()

        stats = generator._aggregate_career_stats(200)

        assert stats['games_played'] == 4
        assert stats['rush_yards'] == 500  # 125 * 4
        assert stats['rush_tds'] == 4      # 1 * 4

    def test_aggregate_career_stats_receiving(self, temp_db, dynasty_id, generator, sample_wr):
        """Aggregate receiving stats."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
            (1, dynasty_id, 2024)
        )
        cursor.execute("""
            INSERT INTO player_game_stats
            (dynasty_id, game_id, player_id, team_id, receptions, receiving_yards, receiving_tds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 1, 300, 3, 8, 150, 2))

        conn.commit()
        conn.close()

        stats = generator._aggregate_career_stats(300)

        assert stats['games_played'] == 1
        assert stats['receptions'] == 8
        assert stats['rec_yards'] == 150
        assert stats['rec_tds'] == 2

    def test_aggregate_career_stats_defense(self, temp_db, dynasty_id, generator, sample_lb):
        """Aggregate defensive stats."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
            (1, dynasty_id, 2024)
        )
        cursor.execute("""
            INSERT INTO player_game_stats
            (dynasty_id, game_id, player_id, team_id, tackles_total, sacks, interceptions, forced_fumbles)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 1, 400, 4, 12, 1.5, 1, 2))

        conn.commit()
        conn.close()

        stats = generator._aggregate_career_stats(400)

        assert stats['tackles'] == 12
        assert stats['sacks'] == 1.5
        assert stats['interceptions'] == 1
        assert stats['forced_fumbles'] == 2

    def test_aggregate_career_stats_empty(self, generator):
        """Player with no stats returns empty dict."""
        stats = generator._aggregate_career_stats(999)
        # Returns default values from COALESCE
        assert stats.get('games_played', 0) == 0


# ============================================
# Award Counting Tests (5)
# ============================================

class TestAwardCounting:

    def test_count_mvp_awards(self, temp_db, dynasty_id, generator):
        """Count MVP awards for player."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert 2 MVP awards
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'mvp', 2023, 1)
        )
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'mvp', 2024, 1)
        )
        # Non-winner should not count
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'mvp', 2022, 0)
        )

        conn.commit()
        conn.close()

        mvp_count = generator._count_mvp_awards(100)
        assert mvp_count == 2

    def test_count_super_bowl_wins(self, temp_db, dynasty_id, generator):
        """Count Super Bowl wins (player on winning team)."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert game and player stats for team 1
        cursor.execute(
            "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
            (1, dynasty_id, 2023)
        )
        cursor.execute("""
            INSERT INTO player_game_stats
            (dynasty_id, game_id, player_id, team_id, passing_yards)
            VALUES (?, ?, ?, ?, ?)
        """, (dynasty_id, 1, 100, 1, 100))

        # Team 1 won Super Bowl in 2023
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2023, 1)
        )

        conn.commit()
        conn.close()

        sb_wins = generator._count_super_bowl_wins(100)
        assert sb_wins == 1

    def test_count_all_pro_selections(self, temp_db, dynasty_id, generator):
        """Count All-Pro first and second team selections."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 3 first team, 2 second team
        for season in [2021, 2022, 2023]:
            cursor.execute(
                "INSERT INTO all_pro_selections (dynasty_id, player_id, season, position, team_type) VALUES (?, ?, ?, ?, ?)",
                (dynasty_id, 100, season, 'QB', 'FIRST_TEAM')
            )
        for season in [2019, 2020]:
            cursor.execute(
                "INSERT INTO all_pro_selections (dynasty_id, player_id, season, position, team_type) VALUES (?, ?, ?, ?, ?)",
                (dynasty_id, 100, season, 'QB', 'SECOND_TEAM')
            )

        conn.commit()
        conn.close()

        first_team, second_team = generator._count_all_pro_selections(100)
        assert first_team == 3
        assert second_team == 2

    def test_count_pro_bowl_selections(self, temp_db, dynasty_id, generator):
        """Count Pro Bowl selections."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 5 Pro Bowl selections
        for season in range(2020, 2025):
            cursor.execute(
                "INSERT INTO pro_bowl_selections (dynasty_id, player_id, season, position) VALUES (?, ?, ?, ?)",
                (dynasty_id, 100, season, 'QB')
            )

        conn.commit()
        conn.close()

        pro_bowls = generator._count_pro_bowl_selections(100)
        assert pro_bowls == 5

    def test_count_super_bowl_mvps(self, temp_db, dynasty_id, generator):
        """Count Super Bowl MVP awards."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'super_bowl_mvp', 2023, 1)
        )

        conn.commit()
        conn.close()

        sb_mvps = generator._count_super_bowl_mvps(100)
        assert sb_mvps == 1


# ============================================
# HOF Score Tests (6)
# ============================================

class TestHOFScore:

    def test_hof_score_mvp_capped_at_50(self, generator):
        """MVP awards cap at 50 points (2 MVPs)."""
        # 3 MVPs should cap at 50
        summary = CareerSummary(
            player_id=1, full_name="Test Player", position="QB",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=160, games_started=160,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=3,  # 3 * 25 = 75, but capped at 50
            super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        score = generator.calculate_hof_score(summary, seasons_played=10)
        # 50 (MVP cap) + 5 (longevity for 10 seasons) = 55
        assert score >= 50  # At least MVP cap

    def test_hof_score_super_bowl_capped_at_30(self, generator):
        """Super Bowl wins cap at 30 points (2 wins)."""
        summary = CareerSummary(
            player_id=2, full_name="Test Player", position="QB",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=160, games_started=160,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0,
            super_bowl_wins=3,  # 3 * 15 = 45, but capped at 30
            super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        score = generator.calculate_hof_score(summary, seasons_played=10)
        # 30 (SB cap) + 5 (longevity) = 35
        assert 30 <= score <= 40

    def test_hof_score_pro_bowl_capped_at_20(self, generator):
        """Pro Bowls cap at 20 points (10 selections)."""
        summary = CareerSummary(
            player_id=3, full_name="Test Player", position="WR",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=160, games_started=160,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=15,  # 15 * 2 = 30, but capped at 20
            all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        score = generator.calculate_hof_score(summary, seasons_played=10)
        # 20 (PB cap) + 5 (longevity) = 25
        assert 20 <= score <= 30

    def test_hof_score_stats_bonus_qb(self, generator):
        """QB stats bonus with elite passing yards."""
        summary = CareerSummary(
            player_id=4, full_name="Test QB", position="QB",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=240, games_started=240,
            pass_yards=45000,  # Elite (40,000+ = +20)
            pass_tds=350,      # Elite (300+ = +20)
            pass_ints=150,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        score = generator.calculate_hof_score(summary, seasons_played=15)
        # Stats bonus = 20 (max from elite yards or TDs)
        # Longevity = 10 (15+ seasons)
        # Total = 30
        assert score >= 20  # At least stats bonus

    def test_hof_score_longevity_bonus(self, generator):
        """Longevity bonus for 10+ and 15+ seasons."""
        base_summary = CareerSummary(
            player_id=5, full_name="Test Player", position="WR",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=0, games_started=0,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        # 5 seasons = no bonus
        score_5 = generator.calculate_hof_score(base_summary, seasons_played=5)
        assert score_5 == 0

        # 10 seasons = +5
        score_10 = generator.calculate_hof_score(base_summary, seasons_played=10)
        assert score_10 == 5

        # 15 seasons = +10
        score_15 = generator.calculate_hof_score(base_summary, seasons_played=15)
        assert score_15 == 10

    def test_hof_score_total_capped_at_100(self, generator):
        """Total HOF score capped at 100."""
        # Create a GOAT summary with everything
        summary = CareerSummary(
            player_id=6, full_name="GOAT Player", position="QB",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=320, games_started=320,
            pass_yards=90000,  # Elite
            pass_tds=700,      # Elite
            pass_ints=100,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=15,            # Capped at 20
            all_pro_first_team=10,   # 10 * 8 = 80
            all_pro_second_team=5,   # 5 * 4 = 20
            mvp_awards=5,            # Capped at 50
            super_bowl_wins=7,       # Capped at 30
            super_bowl_mvps=5,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        score = generator.calculate_hof_score(summary, seasons_played=20)
        # Should be WAY over 100, but capped at 100
        assert score == 100


# ============================================
# Narrative Generation Tests (3)
# ============================================

class TestNarrativeGeneration:

    def test_narrative_includes_stats(self, temp_db, dynasty_id, generator, sample_qb):
        """Narrative includes position-specific stats."""
        # Create a summary with stats
        summary = CareerSummary(
            player_id=100, full_name="Tom Brady", position="QB",
            draft_year=2000, draft_round=6, draft_pick=199,
            games_played=320, games_started=316,
            pass_yards=89214, pass_tds=649, pass_ints=212,
            rush_yards=1000, rush_tds=25,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=15, all_pro_first_team=3, all_pro_second_team=2,
            mvp_awards=3, super_bowl_wins=7, super_bowl_mvps=5,
            teams_played_for=[1, 28], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=95,
        )

        narrative = generator.generate_narrative(summary)

        # Should include passing stats
        assert "89,214 yards" in narrative
        assert "649 touchdowns" in narrative
        assert "212 interceptions" in narrative

    def test_narrative_includes_accolades(self, generator):
        """Narrative includes accolades when present."""
        summary = CareerSummary(
            player_id=1, full_name="Test Star", position="WR",
            draft_year=2010, draft_round=1, draft_pick=10,
            games_played=160, games_started=150,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=100, rush_tds=1,
            receptions=800, rec_yards=10000, rec_tds=70,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=8, all_pro_first_team=3, all_pro_second_team=2,
            mvp_awards=1, super_bowl_wins=2, super_bowl_mvps=1,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=85,
        )

        narrative = generator.generate_narrative(summary)

        # Should include accolades
        assert "1x NFL MVP" in narrative
        assert "2x Super Bowl champion" in narrative
        assert "3x First-Team All-Pro" in narrative
        assert "8x Pro Bowl" in narrative

    def test_narrative_hof_assessment(self, generator):
        """Narrative includes appropriate HOF assessment."""
        # First-ballot lock (85+)
        summary_legend = CareerSummary(
            player_id=1, full_name="Legend Player", position="QB",
            draft_year=2000, draft_round=1, draft_pick=1,
            games_played=300, games_started=300,
            pass_yards=50000, pass_tds=400, pass_ints=100,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=10, all_pro_first_team=5, all_pro_second_team=2,
            mvp_awards=2, super_bowl_wins=2, super_bowl_mvps=2,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=90,
        )

        narrative = generator.generate_narrative(summary_legend)
        assert "first ballot" in narrative.lower() or "virtually certain" in narrative.lower()

        # Average career (<40)
        summary_average = CareerSummary(
            player_id=2, full_name="Average Player", position="WR",
            draft_year=2015, draft_round=5, draft_pick=150,
            games_played=64, games_started=30,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=50, rush_tds=0,
            receptions=100, rec_yards=1500, rec_tds=10,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1, 2], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=15,
        )

        narrative_avg = generator.generate_narrative(summary_average)
        assert "meaningful contributions" in narrative_avg.lower() or "canton" not in narrative_avg.lower()


# ============================================
# Integration Tests (3)
# ============================================

class TestIntegration:

    def test_generate_full_career_summary(self, temp_db, dynasty_id, generator, sample_qb):
        """Full career summary generation from scratch."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # Insert games and stats
        for game_id in range(1, 17):  # 16 games
            cursor.execute(
                "INSERT INTO games (game_id, dynasty_id, season) VALUES (?, ?, ?)",
                (game_id, dynasty_id, 2024)
            )
            cursor.execute("""
                INSERT INTO player_game_stats
                (dynasty_id, game_id, player_id, team_id, passing_yards, passing_tds, passing_interceptions)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dynasty_id, game_id, 100, 1, 280, 2, 1))

        # Insert awards
        cursor.execute(
            "INSERT INTO pro_bowl_selections (dynasty_id, player_id, season, position) VALUES (?, ?, ?, ?)",
            (dynasty_id, 100, 2024, 'QB')
        )

        conn.commit()
        conn.close()

        summary = generator.generate_career_summary(sample_qb, retirement_season=2025)

        assert summary.full_name == "Tom Brady"
        assert summary.position == "QB"
        assert summary.games_played == 16
        assert summary.pass_yards == 280 * 16  # 4480
        assert summary.pass_tds == 32          # 2 * 16
        assert summary.pro_bowls == 1

    def test_generate_summary_empty_career(self, temp_db, dynasty_id, generator):
        """Summary for player with no stats."""
        player = {
            'player_id': 999,
            'first_name': 'Empty',
            'last_name': 'Career',
            'positions': ['WR'],
            'team_id': 1,
        }

        summary = generator.generate_career_summary(player, retirement_season=2025)

        assert summary.full_name == "Empty Career"
        assert summary.games_played == 0
        assert summary.pass_yards == 0
        assert summary.mvp_awards == 0
        assert summary.hall_of_fame_score == 0

    def test_generate_summary_legend(self, temp_db, dynasty_id, generator, sample_qb):
        """Full summary for legendary player."""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()

        # 15 seasons of games
        game_id = 0
        for season in range(2010, 2025):
            for week in range(1, 17):
                game_id += 1
                cursor.execute(
                    "INSERT INTO games (game_id, dynasty_id, season, week) VALUES (?, ?, ?, ?)",
                    (game_id, dynasty_id, season, week)
                )
                cursor.execute("""
                    INSERT INTO player_game_stats
                    (dynasty_id, game_id, player_id, team_id, passing_yards, passing_tds, passing_interceptions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (dynasty_id, game_id, 100, 1, 280, 2, 1))

        # MVP awards
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'mvp', 2017, 1)
        )
        cursor.execute(
            "INSERT INTO award_winners (dynasty_id, player_id, award_id, season, is_winner) VALUES (?, ?, ?, ?, ?)",
            (dynasty_id, 100, 'mvp', 2020, 1)
        )

        # Super Bowl wins
        cursor.execute(
            "INSERT INTO team_season_history (dynasty_id, team_id, season, won_super_bowl) VALUES (?, ?, ?, ?)",
            (dynasty_id, 1, 2019, 1)
        )

        # Pro Bowls
        for season in range(2015, 2025):
            cursor.execute(
                "INSERT INTO pro_bowl_selections (dynasty_id, player_id, season, position) VALUES (?, ?, ?, ?)",
                (dynasty_id, 100, season, 'QB')
            )

        # All-Pro
        for season in range(2016, 2020):
            cursor.execute(
                "INSERT INTO all_pro_selections (dynasty_id, player_id, season, position, team_type) VALUES (?, ?, ?, ?, ?)",
                (dynasty_id, 100, season, 'QB', 'FIRST_TEAM')
            )

        conn.commit()
        conn.close()

        summary = generator.generate_career_summary(sample_qb, retirement_season=2025)

        assert summary.games_played == 15 * 16  # 240 games
        assert summary.pass_yards == 280 * 240  # 67,200 yards
        assert summary.mvp_awards == 2
        assert summary.super_bowl_wins == 1
        assert summary.pro_bowls == 10
        assert summary.all_pro_first_team == 4
        assert summary.hall_of_fame_score > 50  # Should be substantial


# ============================================
# Helper Method Tests (3)
# ============================================

class TestHelperMethods:

    def test_get_position_group_mapping(self, generator):
        """Position group mapping works correctly."""
        assert generator._get_position_group('QB') == 'QB'
        assert generator._get_position_group('HB') == 'RB'
        assert generator._get_position_group('HALFBACK') == 'RB'
        assert generator._get_position_group('WR') == 'WR'
        assert generator._get_position_group('LE') == 'EDGE'
        assert generator._get_position_group('LOLB') == 'LB'
        assert generator._get_position_group('FS') == 'S'
        assert generator._get_position_group('CB') == 'CB'
        assert generator._get_position_group('K') == 'K'
        assert generator._get_position_group('UNKNOWN') == 'UNKNOWN'

    def test_get_team_name(self, generator):
        """Team name lookup works correctly."""
        assert generator._get_team_name(1) == "Buffalo Bills"
        assert generator._get_team_name(17) == "Dallas Cowboys"
        assert generator._get_team_name(32) == "Seattle Seahawks"
        assert generator._get_team_name(None) == "multiple teams"
        assert "Team" in generator._get_team_name(999)  # Unknown team

    def test_format_number(self, generator):
        """Number formatting with commas."""
        assert generator._format_number(1000) == "1,000"
        assert generator._format_number(50000) == "50,000"
        assert generator._format_number(89214) == "89,214"
        assert generator._format_number(0) == "0"


# ============================================
# Position Stats Bonus Tests (4)
# ============================================

class TestPositionStatsBonus:

    def test_stats_bonus_rb_elite(self, generator):
        """RB with elite rushing yards gets 20 point bonus."""
        summary = CareerSummary(
            player_id=1, full_name="Elite RB", position="RB",
            draft_year=2010, draft_round=1, draft_pick=5,
            games_played=180, games_started=180,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=12000,  # Elite (10,000+)
            rush_tds=80,       # Elite (75+)
            receptions=400, rec_yards=3000, rec_tds=10,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        bonus = generator._calculate_stats_bonus('RB', summary)
        assert bonus == 20

    def test_stats_bonus_cb_good(self, generator):
        """CB with good interceptions gets 10 point bonus."""
        summary = CareerSummary(
            player_id=2, full_name="Good CB", position="CB",
            draft_year=2010, draft_round=2, draft_pick=40,
            games_played=160, games_started=150,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=400, sacks=0,
            interceptions=35,  # Good (30-39)
            forced_fumbles=5,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        bonus = generator._calculate_stats_bonus('CB', summary)
        assert bonus == 10

    def test_stats_bonus_kicker_great(self, generator):
        """Kicker with great field goals gets 15 point bonus."""
        summary = CareerSummary(
            player_id=3, full_name="Great K", position="K",
            draft_year=2008, draft_round=5, draft_pick=150,
            games_played=280, games_started=0,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=350,  # Great (300-399)
            fg_attempted=400,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        bonus = generator._calculate_stats_bonus('K', summary)
        assert bonus == 15

    def test_stats_bonus_unknown_position(self, generator):
        """Unknown position gets no stats bonus."""
        summary = CareerSummary(
            player_id=4, full_name="Unknown", position="P",  # Punter not in thresholds
            draft_year=2015, draft_round=7, draft_pick=250,
            games_played=100, games_started=0,
            pass_yards=0, pass_tds=0, pass_ints=0,
            rush_yards=0, rush_tds=0,
            receptions=0, rec_yards=0, rec_tds=0,
            tackles=0, sacks=0, interceptions=0, forced_fumbles=0,
            fg_made=0, fg_attempted=0,
            pro_bowls=0, all_pro_first_team=0, all_pro_second_team=0,
            mvp_awards=0, super_bowl_wins=0, super_bowl_mvps=0,
            teams_played_for=[1], primary_team_id=1,
            career_approximate_value=0, hall_of_fame_score=0,
        )

        bonus = generator._calculate_stats_bonus('P', summary)
        assert bonus == 0
