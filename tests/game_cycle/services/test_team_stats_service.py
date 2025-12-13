"""
Tests for TeamStatsService.

Tests the service layer that combines TeamSeasonStatsAPI, BoxScoresAPI, and StandingsAPI.
"""

import pytest
import sqlite3
from unittest.mock import MagicMock, patch

from src.game_cycle.services.team_stats_service import (
    TeamStatsService,
    TeamOverview,
    LeagueRankings,
)


@pytest.fixture
def test_db(tmp_path) -> str:
    """Create a test database with required schema and sample data."""
    db_path = str(tmp_path / "test_team_stats.db")

    with sqlite3.connect(db_path) as conn:
        # Create dynasties table
        conn.execute("""
            CREATE TABLE dynasties (
                dynasty_id TEXT PRIMARY KEY,
                dynasty_name TEXT NOT NULL
            )
        """)

        # Create games table
        conn.execute("""
            CREATE TABLE games (
                game_id TEXT NOT NULL,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL,
                PRIMARY KEY (dynasty_id, game_id)
            )
        """)

        # Create standings table (matching production schema)
        conn.execute("""
            CREATE TABLE standings (
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                season_type TEXT DEFAULT 'regular_season',
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
                playoff_seed INTEGER DEFAULT NULL,
                PRIMARY KEY (dynasty_id, team_id, season, season_type)
            )
        """)

        # Create player_game_stats table
        conn.execute("""
            CREATE TABLE player_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                player_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                passing_yards INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                receiving_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0,
                interceptions INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0
            )
        """)

        # Create box_scores table
        conn.execute("""
            CREATE TABLE box_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                game_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                q1_score INTEGER DEFAULT 0,
                q2_score INTEGER DEFAULT 0,
                q3_score INTEGER DEFAULT 0,
                q4_score INTEGER DEFAULT 0,
                ot_score INTEGER DEFAULT 0,
                total_yards INTEGER DEFAULT 0,
                passing_yards INTEGER DEFAULT 0,
                rushing_yards INTEGER DEFAULT 0,
                turnovers INTEGER DEFAULT 0,
                UNIQUE(game_id, team_id)
            )
        """)

        # Insert test dynasty
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, dynasty_name) VALUES (?, ?)",
            ("test_dynasty", "Test Dynasty")
        )

        # Insert standings for 3 teams
        for team_id in [1, 2, 3]:
            wins = 10 - team_id  # Team 1: 9 wins, Team 2: 8 wins, Team 3: 7 wins
            losses = team_id + 5
            conn.execute("""
                INSERT INTO standings (dynasty_id, team_id, season, season_type, wins, losses, ties)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("test_dynasty", team_id, 2025, "regular_season", wins, losses, 0))

        # Insert sample games
        for week in range(1, 4):
            game_id = f"game_2025_{week}_1_2"
            conn.execute("""
                INSERT INTO games (game_id, dynasty_id, season, week, season_type,
                                 home_team_id, away_team_id, home_score, away_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, "test_dynasty", 2025, week, "regular_season", 1, 2, 24, 17))

        # Insert player stats for teams 1, 2, and 3
        # Team 1: Strong offense
        _insert_team_stats(conn, "test_dynasty", 2025, 1, passing=300, rushing=120, sacks=3, ints=2)
        # Team 2: Balanced
        _insert_team_stats(conn, "test_dynasty", 2025, 2, passing=250, rushing=100, sacks=2, ints=1)
        # Team 3: Weak
        _insert_team_stats(conn, "test_dynasty", 2025, 3, passing=200, rushing=80, sacks=1, ints=0)

        conn.commit()

    return db_path


def _insert_team_stats(conn, dynasty_id, season, team_id, passing, rushing, sacks, ints):
    """Insert sample player stats for a team across multiple games."""
    for week in range(1, 4):
        game_id = f"game_{season}_{week}_{team_id}_opponent"
        # Insert game if needed
        conn.execute("""
            INSERT OR IGNORE INTO games (game_id, dynasty_id, season, week, season_type,
                             home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (game_id, dynasty_id, season, week, "regular_season", team_id, team_id + 10, 24, 17))

        # Insert QB stats
        conn.execute("""
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, team_id, season, week, season_type,
                passing_yards, passing_tds, passing_interceptions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, game_id, f"qb_{team_id}", team_id, season, week, "regular_season",
              passing, 2, 1))

        # Insert RB stats
        conn.execute("""
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, team_id, season, week, season_type,
                rushing_yards, rushing_tds, rushing_fumbles
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, game_id, f"rb_{team_id}", team_id, season, week, "regular_season",
              rushing, 1, 0))

        # Insert defensive stats
        conn.execute("""
            INSERT INTO player_game_stats (
                dynasty_id, game_id, player_id, team_id, season, week, season_type,
                sacks, interceptions, passes_defended
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, game_id, f"lb_{team_id}", team_id, season, week, "regular_season",
              sacks, ints, 3))


@pytest.fixture
def service(test_db) -> TeamStatsService:
    """Create TeamStatsService with test database."""
    return TeamStatsService(test_db, "test_dynasty", 2025)


# -------------------- TeamOverview Tests --------------------

class TestGetTeamOverview:
    """Tests for get_team_overview method."""

    def test_returns_overview_with_stats_and_record(self, service, test_db):
        """Test that overview combines stats and standings."""
        overview = service.get_team_overview(1)

        assert overview is not None
        assert overview.team_id == 1
        assert overview.season == 2025

        # Verify record from standings
        assert overview.wins == 9
        assert overview.losses == 6
        assert overview.ties == 0

        # Verify stats are populated
        assert overview.total_yards > 0
        assert overview.passing_yards > 0
        assert overview.rushing_yards > 0

    def test_returns_none_for_team_without_stats(self, service):
        """Test returns None for team with no game data."""
        overview = service.get_team_overview(99)  # Non-existent team
        assert overview is None

    def test_overview_includes_rankings(self, service):
        """Test that overview includes league rankings."""
        overview = service.get_team_overview(1)

        assert overview is not None
        # Rankings should be 1-32 (or smaller if fewer teams have data)
        assert overview.offense_rank >= 1
        assert overview.defense_rank >= 1
        assert overview.points_rank >= 1

    def test_overview_to_dict(self, service):
        """Test serialization to dictionary."""
        overview = service.get_team_overview(1)

        assert overview is not None
        result = overview.to_dict()

        assert isinstance(result, dict)
        assert result['team_id'] == 1
        assert 'wins' in result
        assert 'total_yards' in result
        assert 'offense_rank' in result


# -------------------- League Rankings Tests --------------------

class TestGetLeagueRankings:
    """Tests for get_league_rankings method."""

    def test_returns_rankings_for_all_categories(self, service):
        """Test that rankings include all stat categories."""
        rankings = service.get_league_rankings()

        assert rankings is not None
        assert rankings.season == 2025

        # Should have all default categories
        assert 'total_yards' in rankings.categories
        assert 'points_scored' in rankings.categories
        assert 'yards_allowed' in rankings.categories

    def test_rankings_ordered_by_rank(self, service):
        """Test that teams are ordered by rank (1 to N)."""
        rankings = service.get_league_rankings()

        total_yards_rankings = rankings.categories.get('total_yards', [])
        assert len(total_yards_rankings) > 0

        # Verify ranks are sequential
        for i, entry in enumerate(total_yards_rankings):
            assert entry['rank'] == i + 1

    def test_filter_to_specific_categories(self, service):
        """Test filtering to specific stat categories."""
        rankings = service.get_league_rankings(categories=['total_yards', 'sacks'])

        assert 'total_yards' in rankings.categories
        assert 'sacks' in rankings.categories
        # Should not include categories not requested
        assert 'points_allowed' not in rankings.categories

    def test_rankings_include_display_names(self, service):
        """Test that rankings include human-readable display names."""
        rankings = service.get_league_rankings(categories=['total_yards'])

        entry = rankings.categories['total_yards'][0]
        assert 'display_name' in entry
        assert entry['display_name'] == 'Total Yards'


# -------------------- Team Comparison Tests --------------------

class TestGetTeamComparison:
    """Tests for get_team_comparison method."""

    def test_comparison_includes_both_teams(self, service):
        """Test that comparison includes stats for both teams."""
        comparison = service.get_team_comparison(1, 2)

        assert comparison['season'] == 2025
        assert comparison['team1'] is not None
        assert comparison['team2'] is not None
        assert comparison['team1']['team_id'] == 1
        assert comparison['team2']['team_id'] == 2

    def test_comparison_shows_advantages(self, service):
        """Test that comparison shows which team has advantage."""
        comparison = service.get_team_comparison(1, 2)

        assert comparison['comparison'] is not None
        assert 'total_yards' in comparison['comparison']

        total_yards_cmp = comparison['comparison']['total_yards']
        assert 'team1_value' in total_yards_cmp
        assert 'team2_value' in total_yards_cmp
        assert 'advantage' in total_yards_cmp

    def test_comparison_handles_missing_team(self, service):
        """Test comparison when one team has no data."""
        comparison = service.get_team_comparison(1, 99)

        assert comparison['team1'] is not None  # Team 1 has data
        assert comparison['team2'] is None  # Team 99 doesn't exist
        assert comparison['comparison'] is None


# -------------------- Service Layer Tests --------------------

class TestServiceLayerPattern:
    """Tests that verify service uses API classes, not direct SQL."""

    def test_uses_team_stats_api(self, test_db):
        """Test that service delegates to TeamSeasonStatsAPI."""
        service = TeamStatsService(test_db, "test_dynasty", 2025)

        with patch.object(service, '_get_team_stats_api') as mock_get_api:
            mock_api = MagicMock()
            mock_api.get_team_season_stats.return_value = None
            mock_get_api.return_value = mock_api

            service.get_team_overview(1)

            mock_api.get_team_season_stats.assert_called_once()

    def test_uses_standings_api(self, test_db):
        """Test that service delegates to StandingsAPI for records."""
        service = TeamStatsService(test_db, "test_dynasty", 2025)

        with patch.object(service, '_get_standings_api') as mock_get_api:
            mock_api = MagicMock()
            mock_standing = MagicMock()
            mock_standing.wins = 10
            mock_standing.losses = 6
            mock_standing.ties = 0
            mock_api.get_team_standing.return_value = mock_standing
            mock_get_api.return_value = mock_api

            # Also need to mock team stats api
            with patch.object(service, '_get_team_stats_api') as mock_stats:
                mock_stats_api = MagicMock()
                mock_stats_api.get_team_season_stats.return_value = MagicMock(
                    total_yards=1000,
                    passing_yards=600,
                    rushing_yards=400,
                    points_scored=200,
                    yards_per_game=250.0,
                    points_per_game=25.0,
                    points_allowed=150,
                    yards_allowed=800,
                    sacks=20,
                    interceptions=10,
                    points_allowed_per_game=18.75,
                    turnovers=15,
                    turnovers_forced=20,
                    turnover_margin=5,
                )
                mock_stats_api.calculate_rankings.return_value = []
                mock_stats.return_value = mock_stats_api

                service.get_team_overview(1)

                mock_api.get_team_standing.assert_called_once()

    def test_uses_box_scores_api(self, test_db):
        """Test that service delegates to BoxScoresAPI for game stats."""
        service = TeamStatsService(test_db, "test_dynasty", 2025)

        with patch.object(service, '_get_box_scores_api') as mock_get_api:
            mock_api = MagicMock()
            mock_api.get_team_box_scores.return_value = []
            mock_get_api.return_value = mock_api

            service.get_team_box_scores(1)

            mock_api.get_team_box_scores.assert_called_once()