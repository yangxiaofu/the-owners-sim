"""
Unit tests for TeamSeasonStatsAPI.

Part of Milestone 8: Team Statistics - Tollgate 1.
"""

import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.team_stats_api import (
    TeamSeasonStatsAPI,
    TeamSeasonStats,
    TeamRanking
)


@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025
        );

        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            game_type TEXT DEFAULT 'regular',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        );

        CREATE TABLE IF NOT EXISTS player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            player_id TEXT NOT NULL,
            player_name TEXT,
            team_id INTEGER NOT NULL,
            position TEXT,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            rushing_fumbles INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            fumbles_recovered INTEGER DEFAULT 0,
            passes_defended INTEGER DEFAULT 0,
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0,
            extra_points_made INTEGER DEFAULT 0,
            extra_points_attempted INTEGER DEFAULT 0,
            FOREIGN KEY (game_id) REFERENCES games(game_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        );

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def api(db_path):
    """Create a TeamSeasonStatsAPI instance."""
    return TeamSeasonStatsAPI(db_path)


@pytest.fixture
def populated_db(db_path):
    """Populate database with sample game and stats data."""
    conn = sqlite3.connect(db_path)

    # Insert games for week 1 and week 2
    conn.executescript('''
        INSERT INTO games (game_id, dynasty_id, season, week, season_type, home_team_id, away_team_id, home_score, away_score)
        VALUES
            ('game_1', 'test-dynasty', 2025, 1, 'regular_season', 1, 2, 28, 21),
            ('game_2', 'test-dynasty', 2025, 2, 'regular_season', 2, 1, 17, 24),
            ('game_3', 'test-dynasty', 2025, 1, 'regular_season', 3, 4, 35, 14);

        -- Team 1 player stats (home game 1, away game 2)
        INSERT INTO player_game_stats
            (dynasty_id, game_id, season_type, player_id, team_id, position,
             passing_yards, passing_tds, passing_interceptions, rushing_yards, rushing_tds, rushing_fumbles,
             sacks, interceptions, forced_fumbles, fumbles_recovered, passes_defended,
             field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted)
        VALUES
            ('test-dynasty', 'game_1', 'regular_season', 'qb1', 1, 'QB', 300, 3, 1, 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 4),
            ('test-dynasty', 'game_1', 'regular_season', 'rb1', 1, 'RB', 0, 0, 0, 100, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            ('test-dynasty', 'game_1', 'regular_season', 'def1', 1, 'LB', 0, 0, 0, 0, 0, 0, 2, 1, 1, 0, 2, 0, 0, 0, 0),
            ('test-dynasty', 'game_2', 'regular_season', 'qb1', 1, 'QB', 280, 2, 0, 15, 0, 1, 0, 0, 0, 0, 0, 0, 0, 3, 3),
            ('test-dynasty', 'game_2', 'regular_season', 'rb1', 1, 'RB', 0, 0, 0, 85, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            ('test-dynasty', 'game_2', 'regular_season', 'def1', 1, 'LB', 0, 0, 0, 0, 0, 0, 1, 0, 0, 1, 1, 0, 0, 0, 0),
            ('test-dynasty', 'game_2', 'regular_season', 'k1', 1, 'K', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0);

        -- Team 2 player stats (away game 1, home game 2)
        INSERT INTO player_game_stats
            (dynasty_id, game_id, season_type, player_id, team_id, position,
             passing_yards, passing_tds, passing_interceptions, rushing_yards, rushing_tds, rushing_fumbles,
             sacks, interceptions, forced_fumbles, fumbles_recovered, passes_defended,
             field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted)
        VALUES
            ('test-dynasty', 'game_1', 'regular_season', 'qb2', 2, 'QB', 250, 2, 1, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3),
            ('test-dynasty', 'game_1', 'regular_season', 'rb2', 2, 'RB', 0, 0, 0, 80, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            ('test-dynasty', 'game_1', 'regular_season', 'def2', 2, 'LB', 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0),
            ('test-dynasty', 'game_2', 'regular_season', 'qb2', 2, 'QB', 200, 1, 0, 5, 0, 1, 0, 0, 0, 0, 0, 0, 0, 2, 2),
            ('test-dynasty', 'game_2', 'regular_season', 'rb2', 2, 'RB', 0, 0, 0, 60, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
            ('test-dynasty', 'game_2', 'regular_season', 'def2', 2, 'LB', 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0);

        -- Team 3 and 4 stats (game_3)
        INSERT INTO player_game_stats
            (dynasty_id, game_id, season_type, player_id, team_id, position,
             passing_yards, passing_tds, rushing_yards, rushing_tds, passing_interceptions,
             sacks, interceptions, field_goals_made, field_goals_attempted, extra_points_made, extra_points_attempted)
        VALUES
            ('test-dynasty', 'game_3', 'regular_season', 'qb3', 3, 'QB', 400, 4, 30, 1, 0, 0, 0, 0, 0, 5, 5),
            ('test-dynasty', 'game_3', 'regular_season', 'def3', 3, 'LB', 0, 0, 0, 0, 0, 3, 2, 0, 0, 0, 0),
            ('test-dynasty', 'game_3', 'regular_season', 'qb4', 4, 'QB', 180, 1, 20, 0, 2, 0, 0, 0, 0, 2, 2),
            ('test-dynasty', 'game_3', 'regular_season', 'def4', 4, 'LB', 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
    ''')
    conn.commit()
    conn.close()

    return db_path


class TestTeamSeasonStats:
    """Tests for the TeamSeasonStats dataclass."""

    def test_yards_per_game_calculation(self):
        """Should calculate yards per game correctly."""
        stats = TeamSeasonStats(
            team_id=1, season=2025, games_played=2,
            total_yards=800, passing_yards=600, rushing_yards=200,
            first_downs=0, third_down_attempts=0, third_down_conversions=0,
            points_scored=56,
            points_allowed=38, yards_allowed=700, passing_yards_allowed=500, rushing_yards_allowed=200,
            sacks=3, tackles_for_loss=0, interceptions=2, passes_defended=4,
            forced_fumbles=1, fumbles_recovered=1, defensive_tds=0,
            field_goals_made=2, field_goals_attempted=3,
            extra_points_made=6, extra_points_attempted=6,
            punt_return_yards=0, punt_return_tds=0, kick_return_yards=0, kick_return_tds=0,
            interceptions_thrown=1, fumbles_lost=1, turnovers=2,
            turnovers_forced=3, turnover_margin=1
        )
        assert stats.yards_per_game == 400.0
        assert stats.points_per_game == 28.0

    def test_field_goal_percentage(self):
        """Should calculate field goal percentage correctly."""
        stats = TeamSeasonStats(
            team_id=1, season=2025, games_played=2,
            total_yards=0, passing_yards=0, rushing_yards=0,
            first_downs=0, third_down_attempts=0, third_down_conversions=0,
            points_scored=0,
            points_allowed=0, yards_allowed=0, passing_yards_allowed=0, rushing_yards_allowed=0,
            sacks=0, tackles_for_loss=0, interceptions=0, passes_defended=0,
            forced_fumbles=0, fumbles_recovered=0, defensive_tds=0,
            field_goals_made=3, field_goals_attempted=4,
            extra_points_made=0, extra_points_attempted=0,
            punt_return_yards=0, punt_return_tds=0, kick_return_yards=0, kick_return_tds=0,
            interceptions_thrown=0, fumbles_lost=0, turnovers=0,
            turnovers_forced=0, turnover_margin=0
        )
        assert stats.field_goal_pct == 75.0

    def test_zero_games_played_returns_zero_averages(self):
        """Should return 0 for per-game stats when games_played is 0."""
        stats = TeamSeasonStats(
            team_id=1, season=2025, games_played=0,
            total_yards=0, passing_yards=0, rushing_yards=0,
            first_downs=0, third_down_attempts=0, third_down_conversions=0,
            points_scored=0,
            points_allowed=0, yards_allowed=0, passing_yards_allowed=0, rushing_yards_allowed=0,
            sacks=0, tackles_for_loss=0, interceptions=0, passes_defended=0,
            forced_fumbles=0, fumbles_recovered=0, defensive_tds=0,
            field_goals_made=0, field_goals_attempted=0,
            extra_points_made=0, extra_points_attempted=0,
            punt_return_yards=0, punt_return_tds=0, kick_return_yards=0, kick_return_tds=0,
            interceptions_thrown=0, fumbles_lost=0, turnovers=0,
            turnovers_forced=0, turnover_margin=0
        )
        assert stats.yards_per_game == 0.0
        assert stats.points_per_game == 0.0


class TestGetTeamSeasonStats:
    """Tests for get_team_season_stats method."""

    def test_returns_correct_totals(self, api, populated_db):
        """Should return correct aggregated stats for team."""
        api = TeamSeasonStatsAPI(populated_db)
        stats = api.get_team_season_stats('test-dynasty', 1, 2025)

        assert stats is not None
        assert stats.team_id == 1
        assert stats.games_played == 2
        # Total passing yards: 300 + 280 = 580
        assert stats.passing_yards == 580
        # Total rushing yards: 100 + 20 + 85 + 15 = 220
        assert stats.rushing_yards == 220
        assert stats.total_yards == 800
        # Points: 28 (home) + 24 (away) = 52
        assert stats.points_scored == 52
        # Points allowed: 21 (home) + 17 (away) = 38
        assert stats.points_allowed == 38

    def test_returns_none_for_no_games(self, api):
        """Should return None when team has no games."""
        stats = api.get_team_season_stats('test-dynasty', 99, 2025)
        assert stats is None

    def test_turnovers_calculated_correctly(self, api, populated_db):
        """Should calculate turnovers correctly."""
        api = TeamSeasonStatsAPI(populated_db)
        stats = api.get_team_season_stats('test-dynasty', 1, 2025)

        # INTs thrown: 1 + 0 = 1
        assert stats.interceptions_thrown == 1
        # Fumbles lost: 0 + 1 = 1
        assert stats.fumbles_lost == 1
        # Total turnovers: 2
        assert stats.turnovers == 2
        # Turnovers forced: INTs (1 + 0) + fumbles recovered (0 + 1) = 2
        assert stats.turnovers_forced == 2
        # Turnover margin: 2 - 2 = 0
        assert stats.turnover_margin == 0

    def test_defensive_stats_from_own_players(self, api, populated_db):
        """Should get defensive stats from team's own defensive players."""
        api = TeamSeasonStatsAPI(populated_db)
        stats = api.get_team_season_stats('test-dynasty', 1, 2025)

        # Sacks: 2 + 1 = 3
        assert stats.sacks == 3
        # Interceptions: 1 + 0 = 1
        assert stats.interceptions == 1
        # Passes defended: 2 + 1 = 3
        assert stats.passes_defended == 3


class TestGetAllTeamsSeasonStats:
    """Tests for get_all_teams_season_stats method."""

    def test_returns_all_teams_with_games(self, api, populated_db):
        """Should return stats for all teams that played games."""
        api = TeamSeasonStatsAPI(populated_db)
        all_stats = api.get_all_teams_season_stats('test-dynasty', 2025)

        # Teams 1, 2, 3, 4 all have games
        assert len(all_stats) == 4

    def test_sorted_by_total_yards(self, api, populated_db):
        """Should sort teams by total yards descending."""
        api = TeamSeasonStatsAPI(populated_db)
        all_stats = api.get_all_teams_season_stats('test-dynasty', 2025)

        yards = [s.total_yards for s in all_stats]
        assert yards == sorted(yards, reverse=True)


class TestDynastyIsolation:
    """Tests for dynasty isolation."""

    def test_dynasty_isolation(self, db_path):
        """Should only return stats for specified dynasty."""
        conn = sqlite3.connect(db_path)
        conn.executescript('''
            INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other-dynasty', 'Other Dynasty', 2);

            INSERT INTO games (game_id, dynasty_id, season, week, season_type, home_team_id, away_team_id, home_score, away_score)
            VALUES ('other_game', 'other-dynasty', 2025, 1, 'regular_season', 1, 2, 10, 7);

            INSERT INTO player_game_stats
                (dynasty_id, game_id, season_type, player_id, team_id, passing_yards)
            VALUES
                ('other-dynasty', 'other_game', 'regular_season', 'qb_other', 1, 999);
        ''')
        conn.commit()
        conn.close()

        api = TeamSeasonStatsAPI(db_path)
        stats = api.get_team_season_stats('test-dynasty', 1, 2025)

        # Should be None because test-dynasty has no game data
        assert stats is None


class TestCalculateRankings:
    """Tests for calculate_rankings method."""

    def test_rankings_return_correct_order(self, api, populated_db):
        """Should return rankings in correct order."""
        api = TeamSeasonStatsAPI(populated_db)
        rankings = api.calculate_rankings('test-dynasty', 2025, 'total_yards')

        assert len(rankings) == 4
        assert rankings[0].rank == 1
        assert rankings[1].rank == 2
        assert rankings[2].rank == 3
        assert rankings[3].rank == 4
        # Verify descending order for total_yards
        values = [r.value for r in rankings]
        assert values == sorted(values, reverse=True)

    def test_rankings_ascending_for_defensive_stats(self, api, populated_db):
        """Should rank lower values higher for defensive stats."""
        api = TeamSeasonStatsAPI(populated_db)
        rankings = api.calculate_rankings(
            'test-dynasty', 2025, 'points_allowed', ascending=True
        )

        assert len(rankings) == 4
        # First place should have lowest points allowed
        values = [r.value for r in rankings]
        assert values == sorted(values)  # ascending = lower is better

    def test_empty_season_returns_empty_rankings(self, api):
        """Should return empty list for season with no games."""
        rankings = api.calculate_rankings('test-dynasty', 2030, 'total_yards')
        assert rankings == []


class TestGetTeamGameStats:
    """Tests for get_team_game_stats method."""

    def test_returns_correct_game_stats(self, api, populated_db):
        """Should return correct stats for a single game."""
        api = TeamSeasonStatsAPI(populated_db)
        stats = api.get_team_game_stats('test-dynasty', 1, 'game_1')

        assert stats is not None
        assert stats['game_id'] == 'game_1'
        assert stats['team_id'] == 1
        # QB: 300 pass yards, RB: 100 rush yards, 20 rush yards
        assert stats['passing_yards'] == 300
        assert stats['rushing_yards'] == 120  # 100 + 20
        assert stats['total_yards'] == 420

    def test_returns_none_for_nonexistent_game(self, api):
        """Should return None for game that doesn't exist."""
        stats = api.get_team_game_stats('test-dynasty', 1, 'nonexistent_game')
        assert stats is None
