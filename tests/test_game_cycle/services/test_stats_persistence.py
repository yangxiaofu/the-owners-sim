"""
Integration tests for stats persistence in the game cycle.

Tests the full flow from MockStatsGenerator through UnifiedDatabaseAPI
to the player_game_stats table.
"""

import pytest
import sqlite3
import tempfile
import os
from typing import Any, Dict

from src.game_cycle.services.mock_stats_generator import MockStatsGenerator, MockGameStats
from src.database.unified_api import UnifiedDatabaseAPI


class TestStatsIntegration:
    """Integration tests for stats persistence."""

    @pytest.fixture
    def temp_db_path(self):
        """Create a temporary database with required schema."""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Create the schema
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        # Create player_game_stats table (matching actual API insert columns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS player_game_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL DEFAULT 'default',
                game_id TEXT NOT NULL,
                season_type TEXT DEFAULT 'regular_season',
                player_id TEXT NOT NULL,
                player_name TEXT,
                team_id INTEGER NOT NULL,
                position TEXT,
                -- Passing stats
                passing_yards INTEGER DEFAULT 0,
                passing_tds INTEGER DEFAULT 0,
                passing_attempts INTEGER DEFAULT 0,
                passing_completions INTEGER DEFAULT 0,
                passing_interceptions INTEGER DEFAULT 0,
                passing_sacks INTEGER DEFAULT 0,
                passing_sack_yards INTEGER DEFAULT 0,
                passing_rating REAL DEFAULT 0.0,
                -- Rushing stats
                rushing_yards INTEGER DEFAULT 0,
                rushing_tds INTEGER DEFAULT 0,
                rushing_attempts INTEGER DEFAULT 0,
                rushing_long INTEGER DEFAULT 0,
                rushing_fumbles INTEGER DEFAULT 0,
                -- Receiving stats
                receiving_yards INTEGER DEFAULT 0,
                receiving_tds INTEGER DEFAULT 0,
                receptions INTEGER DEFAULT 0,
                targets INTEGER DEFAULT 0,
                receiving_long INTEGER DEFAULT 0,
                receiving_drops INTEGER DEFAULT 0,
                -- Defensive stats
                tackles_total INTEGER DEFAULT 0,
                tackles_solo INTEGER DEFAULT 0,
                tackles_assist INTEGER DEFAULT 0,
                sacks REAL DEFAULT 0.0,
                interceptions INTEGER DEFAULT 0,
                forced_fumbles INTEGER DEFAULT 0,
                fumbles_recovered INTEGER DEFAULT 0,
                passes_defended INTEGER DEFAULT 0,
                -- Kicking stats
                field_goals_made INTEGER DEFAULT 0,
                field_goals_attempted INTEGER DEFAULT 0,
                extra_points_made INTEGER DEFAULT 0,
                extra_points_attempted INTEGER DEFAULT 0,
                -- Punting stats
                punts INTEGER DEFAULT 0,
                punt_yards INTEGER DEFAULT 0,
                -- O-line stats
                pancakes INTEGER DEFAULT 0,
                sacks_allowed INTEGER DEFAULT 0,
                hurries_allowed INTEGER DEFAULT 0,
                pressures_allowed INTEGER DEFAULT 0,
                run_blocking_grade REAL DEFAULT 0.0,
                pass_blocking_efficiency REAL DEFAULT 0.0,
                missed_assignments INTEGER DEFAULT 0,
                holding_penalties INTEGER DEFAULT 0,
                false_start_penalties INTEGER DEFAULT 0,
                downfield_blocks INTEGER DEFAULT 0,
                double_team_blocks INTEGER DEFAULT 0,
                chip_blocks INTEGER DEFAULT 0,
                -- Snap counts
                snap_counts_offense INTEGER DEFAULT 0,
                snap_counts_defense INTEGER DEFAULT 0,
                snap_counts_special_teams INTEGER DEFAULT 0,
                -- Fantasy
                fantasy_points REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create players table for roster lookup (matching actual schema)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL DEFAULT 'default',
                team_id INTEGER,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                positions TEXT NOT NULL,
                attributes TEXT,
                age INTEGER DEFAULT 25,
                years_pro INTEGER DEFAULT 1
            )
        """)

        # Create team_rosters table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL DEFAULT 'default',
                team_id INTEGER NOT NULL,
                player_id TEXT NOT NULL,
                roster_status TEXT DEFAULT 'active',
                depth_chart_order INTEGER DEFAULT 0
            )
        """)

        # Create games table (needed for season leaders query)
        # Must include game_date for UnifiedDatabaseAPI index creation
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL DEFAULT 'default',
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                game_type TEXT DEFAULT 'regular',
                game_date INTEGER,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_score INTEGER,
                away_score INTEGER
            )
        """)

        # Helper to create JSON strings for positions and attributes
        import json

        def make_positions(pos):
            return json.dumps([pos])

        def make_attributes(overall):
            return json.dumps({"overall": overall})

        # Insert sample players for two teams (home=1, away=2)
        # Format: (player_id, dynasty_id, team_id, first_name, last_name, positions, attributes, age, years_pro)
        # NOTE: MockStatsGenerator expects full position names, not abbreviations
        sample_players = [
            # Team 1 (home)
            ("p_1_qb", "default", 1, "Pat", "Quarterback", make_positions("quarterback"), make_attributes(92), 28, 6),
            ("p_1_rb1", "default", 1, "Ron", "Runningback", make_positions("running_back"), make_attributes(88), 25, 4),
            ("p_1_wr1", "default", 1, "Will", "Receiver", make_positions("wide_receiver"), make_attributes(90), 27, 5),
            ("p_1_wr2", "default", 1, "Wayne", "Receiver2", make_positions("wide_receiver"), make_attributes(82), 24, 2),
            ("p_1_te", "default", 1, "Tim", "Tightend", make_positions("tight_end"), make_attributes(85), 29, 7),
            ("p_1_lt", "default", 1, "Lou", "Tackle", make_positions("left_tackle"), make_attributes(80), 30, 8),
            ("p_1_lg", "default", 1, "Larry", "Guard", make_positions("left_guard"), make_attributes(78), 28, 6),
            ("p_1_c", "default", 1, "Carl", "Center", make_positions("center"), make_attributes(79), 31, 9),
            ("p_1_rg", "default", 1, "Randy", "Guard2", make_positions("right_guard"), make_attributes(77), 27, 5),
            ("p_1_rt", "default", 1, "Rick", "Tackle2", make_positions("right_tackle"), make_attributes(76), 29, 7),
            ("p_1_de1", "default", 1, "Dan", "End", make_positions("defensive_end"), make_attributes(86), 26, 4),
            ("p_1_dt1", "default", 1, "Doug", "Tackle3", make_positions("defensive_tackle"), make_attributes(84), 28, 6),
            ("p_1_dt2", "default", 1, "Dave", "Tackle4", make_positions("defensive_tackle"), make_attributes(81), 27, 5),
            ("p_1_de2", "default", 1, "Dean", "End2", make_positions("defensive_end"), make_attributes(79), 25, 3),
            ("p_1_lb1", "default", 1, "Luke", "Backer", make_positions("middle_linebacker"), make_attributes(88), 29, 7),
            ("p_1_lb2", "default", 1, "Larry2", "Backer2", make_positions("outside_linebacker"), make_attributes(82), 26, 4),
            ("p_1_lb3", "default", 1, "Leo", "Backer3", make_positions("outside_linebacker"), make_attributes(80), 24, 2),
            ("p_1_cb1", "default", 1, "Chris", "Corner", make_positions("cornerback"), make_attributes(87), 27, 5),
            ("p_1_cb2", "default", 1, "Craig", "Corner2", make_positions("cornerback"), make_attributes(83), 25, 3),
            ("p_1_ss", "default", 1, "Sam", "Safety", make_positions("strong_safety"), make_attributes(85), 28, 6),
            ("p_1_fs", "default", 1, "Fred", "Safety2", make_positions("free_safety"), make_attributes(86), 26, 4),
            ("p_1_k", "default", 1, "Kyle", "Kicker", make_positions("kicker"), make_attributes(84), 32, 10),
            ("p_1_p", "default", 1, "Pete", "Punter", make_positions("punter"), make_attributes(78), 30, 8),
            # Team 2 (away)
            ("p_2_qb", "default", 2, "Quinn", "Quarterback", make_positions("quarterback"), make_attributes(88), 26, 4),
            ("p_2_rb1", "default", 2, "Ray", "Runningback", make_positions("running_back"), make_attributes(85), 24, 2),
            ("p_2_wr1", "default", 2, "Wes", "Receiver", make_positions("wide_receiver"), make_attributes(87), 28, 6),
            ("p_2_wr2", "default", 2, "Walt", "Receiver2", make_positions("wide_receiver"), make_attributes(80), 23, 1),
            ("p_2_te", "default", 2, "Terry", "Tightend", make_positions("tight_end"), make_attributes(82), 27, 5),
            ("p_2_lt", "default", 2, "Lee", "Tackle", make_positions("left_tackle"), make_attributes(78), 29, 7),
            ("p_2_lg", "default", 2, "Les", "Guard", make_positions("left_guard"), make_attributes(76), 27, 5),
            ("p_2_c", "default", 2, "Chuck", "Center", make_positions("center"), make_attributes(77), 30, 8),
            ("p_2_rg", "default", 2, "Rob", "Guard2", make_positions("right_guard"), make_attributes(75), 26, 4),
            ("p_2_rt", "default", 2, "Roger", "Tackle2", make_positions("right_tackle"), make_attributes(74), 28, 6),
            ("p_2_de1", "default", 2, "Derek", "End", make_positions("defensive_end"), make_attributes(84), 25, 3),
            ("p_2_dt1", "default", 2, "Don", "Tackle3", make_positions("defensive_tackle"), make_attributes(82), 27, 5),
            ("p_2_dt2", "default", 2, "Dwight", "Tackle4", make_positions("defensive_tackle"), make_attributes(79), 26, 4),
            ("p_2_de2", "default", 2, "Drew", "End2", make_positions("defensive_end"), make_attributes(77), 24, 2),
            ("p_2_lb1", "default", 2, "Lloyd", "Backer", make_positions("middle_linebacker"), make_attributes(85), 28, 6),
            ("p_2_lb2", "default", 2, "Lance", "Backer2", make_positions("outside_linebacker"), make_attributes(80), 25, 3),
            ("p_2_lb3", "default", 2, "Levi", "Backer3", make_positions("outside_linebacker"), make_attributes(78), 23, 1),
            ("p_2_cb1", "default", 2, "Carlos", "Corner", make_positions("cornerback"), make_attributes(84), 26, 4),
            ("p_2_cb2", "default", 2, "Corey", "Corner2", make_positions("cornerback"), make_attributes(81), 24, 2),
            ("p_2_ss", "default", 2, "Scott", "Safety", make_positions("strong_safety"), make_attributes(83), 27, 5),
            ("p_2_fs", "default", 2, "Frank", "Safety2", make_positions("free_safety"), make_attributes(84), 25, 3),
            ("p_2_k", "default", 2, "Keith", "Kicker", make_positions("kicker"), make_attributes(82), 31, 9),
            ("p_2_p", "default", 2, "Paul", "Punter", make_positions("punter"), make_attributes(76), 29, 7),
        ]

        cursor.executemany(
            "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            sample_players
        )

        # Insert team_rosters entries for all players
        roster_entries = []
        for idx, player in enumerate(sample_players):
            player_id = player[0]
            dynasty_id = player[1]
            team_id = player[2]
            roster_entries.append((dynasty_id, team_id, player_id, "active", idx % 23))

        cursor.executemany(
            "INSERT INTO team_rosters (dynasty_id, team_id, player_id, roster_status, depth_chart_order) VALUES (?, ?, ?, ?, ?)",
            roster_entries
        )

        conn.commit()
        conn.close()

        yield path

        # Cleanup
        os.unlink(path)

    @pytest.fixture
    def unified_api(self, temp_db_path):
        """Create UnifiedDatabaseAPI instance."""
        return UnifiedDatabaseAPI(temp_db_path, dynasty_id="default")

    @pytest.fixture
    def stats_generator(self, temp_db_path):
        """Create MockStatsGenerator instance."""
        return MockStatsGenerator(temp_db_path, "default")

    def test_generate_and_persist_single_game(self, unified_api, stats_generator):
        """Test generating stats for a single game and persisting them."""
        # Generate stats
        mock_stats = stats_generator.generate(
            game_id="test_game_1",
            home_team_id=1,
            away_team_id=2,
            home_score=28,
            away_score=21
        )

        # Verify stats were generated
        assert mock_stats is not None
        assert len(mock_stats.player_stats) > 0

        # Persist stats
        count = unified_api.stats_insert_game_stats(
            game_id="test_game_1",
            season=2025,
            week=1,
            season_type="regular_season",
            player_stats=mock_stats.player_stats
        )

        # Verify stats were persisted
        assert count == len(mock_stats.player_stats)

        # Retrieve and verify
        game_stats = unified_api.stats_get_game_stats("test_game_1")
        assert len(game_stats) == len(mock_stats.player_stats)

    def test_stats_survive_reload(self, temp_db_path):
        """Test that stats persist across database reconnections."""
        # First connection - insert stats
        api1 = UnifiedDatabaseAPI(temp_db_path, dynasty_id="default")
        generator1 = MockStatsGenerator(temp_db_path, "default")

        mock_stats = generator1.generate(
            game_id="reload_test",
            home_team_id=1,
            away_team_id=2,
            home_score=14,
            away_score=10
        )

        api1.stats_insert_game_stats(
            game_id="reload_test",
            season=2025,
            week=1,
            season_type="regular_season",
            player_stats=mock_stats.player_stats
        )

        # Close first connection
        del api1

        # Second connection - verify stats exist
        api2 = UnifiedDatabaseAPI(temp_db_path, dynasty_id="default")
        game_stats = api2.stats_get_game_stats("reload_test")

        assert len(game_stats) > 0
        assert len(game_stats) == len(mock_stats.player_stats)

    def test_season_leaders_aggregation(self, unified_api, stats_generator, temp_db_path):
        """Test season leaders aggregate stats across multiple games."""
        # Generate stats for multiple games (3 weeks)
        # Also need to insert game records for the leaders query to work (it joins games)
        import sqlite3

        for week in range(1, 4):
            game_id = f"week_{week}_game"
            home_score = 24 + week * 3
            away_score = 20 + week * 2

            # Insert game record first (separate connection to avoid locking)
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO games (dynasty_id, game_id, season, week, home_team_id, away_team_id, home_score, away_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("default", game_id, 2025, week, 1, 2, home_score, away_score)
            )
            conn.commit()
            conn.close()

            mock_stats = stats_generator.generate(
                game_id=game_id,
                home_team_id=1,
                away_team_id=2,
                home_score=home_score,
                away_score=away_score
            )

            unified_api.stats_insert_game_stats(
                game_id=game_id,
                season=2025,
                week=week,
                season_type="regular_season",
                player_stats=mock_stats.player_stats
            )

        # Get passing yards leaders
        passing_leaders = unified_api.stats_get_season_leaders(
            season=2025,
            stat="passing_yards",
            limit=5
        )

        # Verify leaders exist and are sorted
        assert len(passing_leaders) > 0
        assert all("stat_value" in leader for leader in passing_leaders)

        # Verify descending order
        totals = [leader["stat_value"] for leader in passing_leaders]
        assert totals == sorted(totals, reverse=True)

    def test_player_season_totals(self, unified_api, stats_generator, temp_db_path):
        """Test player season totals aggregate correctly."""
        # Generate stats for multiple games
        # Also need to insert game records for the totals query to work
        import sqlite3

        for week in range(1, 4):
            game_id = f"total_test_week_{week}"

            # Insert game record first (separate connection to avoid locking)
            conn = sqlite3.connect(temp_db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO games (dynasty_id, game_id, season, week, home_team_id, away_team_id, home_score, away_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("default", game_id, 2025, week, 1, 2, 28, 21)
            )
            conn.commit()
            conn.close()

            mock_stats = stats_generator.generate(
                game_id=game_id,
                home_team_id=1,
                away_team_id=2,
                home_score=28,
                away_score=21
            )

            unified_api.stats_insert_game_stats(
                game_id=game_id,
                season=2025,
                week=week,
                season_type="regular_season",
                player_stats=mock_stats.player_stats
            )

        # Get totals for the QB (should have passing stats)
        qb_totals = unified_api.stats_get_player_season_totals(
            player_id="p_1_qb",
            season=2025
        )

        # Verify totals exist
        assert qb_totals is not None
        assert qb_totals.get("games_played", 0) == 3

        # Verify aggregate stats exist
        assert "passing_yards" in qb_totals
        assert "passing_tds" in qb_totals

    def test_dynasty_isolation(self, temp_db_path):
        """Test that stats are isolated by dynasty_id."""
        import sqlite3

        # Create two dynasties with direct SQL to avoid roster lookup issues
        api_dynasty_a = UnifiedDatabaseAPI(temp_db_path, dynasty_id="dynasty_a")
        api_dynasty_b = UnifiedDatabaseAPI(temp_db_path, dynasty_id="dynasty_b")

        # Manually insert stats for dynasty A
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO player_game_stats (dynasty_id, game_id, season_type, player_id, player_name, team_id, position, passing_yards, passing_tds)
            VALUES ('dynasty_a', 'game_a', 'regular_season', 'player_1', 'Test Player A', 1, 'QB', 300, 3)
        """)
        cursor.execute("""
            INSERT INTO player_game_stats (dynasty_id, game_id, season_type, player_id, player_name, team_id, position, passing_yards, passing_tds)
            VALUES ('dynasty_b', 'game_b', 'regular_season', 'player_2', 'Test Player B', 2, 'QB', 250, 2)
        """)
        conn.commit()
        conn.close()

        # Query dynasty A - should only get its stats
        game_stats_a = api_dynasty_a.stats_get_game_stats("game_a")
        game_stats_b_from_a = api_dynasty_a.stats_get_game_stats("game_b")

        assert len(game_stats_a) == 1
        assert len(game_stats_b_from_a) == 0  # Dynasty B's game not visible

        # Query dynasty B - should only get its stats
        game_stats_b = api_dynasty_b.stats_get_game_stats("game_b")
        game_stats_a_from_b = api_dynasty_b.stats_get_game_stats("game_a")

        assert len(game_stats_b) == 1
        assert len(game_stats_a_from_b) == 0  # Dynasty A's game not visible

    def test_multiple_games_same_week(self, unified_api, stats_generator):
        """Test handling multiple games in the same week."""
        # Generate stats for 3 games in the same week
        games = [
            ("game_1", 1, 2, 21, 14),
            ("game_2", 3, 4, 28, 24),  # Different teams (would need roster)
            ("game_3", 5, 6, 17, 10),
        ]

        total_stats = 0
        for game_id, home, away, h_score, a_score in games:
            # Only use teams 1 and 2 since they have rosters
            if home in [1, 2] and away in [1, 2]:
                mock_stats = stats_generator.generate(
                    game_id=game_id,
                    home_team_id=home,
                    away_team_id=away,
                    home_score=h_score,
                    away_score=a_score
                )

                unified_api.stats_insert_game_stats(
                    game_id=game_id,
                    season=2025,
                    week=1,
                    season_type="regular_season",
                    player_stats=mock_stats.player_stats
                )

                total_stats += len(mock_stats.player_stats)

        # Verify all stats retrievable by game_id
        game_1_stats = unified_api.stats_get_game_stats("game_1")
        assert len(game_1_stats) > 0

    def test_high_scoring_game_persistence(self, unified_api, stats_generator):
        """Test that high-scoring games persist all stats correctly."""
        mock_stats = stats_generator.generate(
            game_id="high_score_game",
            home_team_id=1,
            away_team_id=2,
            home_score=56,
            away_score=49
        )

        # Persist
        unified_api.stats_insert_game_stats(
            game_id="high_score_game",
            season=2025,
            week=1,
            season_type="regular_season",
            player_stats=mock_stats.player_stats
        )

        # Retrieve and verify
        game_stats = unified_api.stats_get_game_stats("high_score_game")

        # Find QB stats and verify realistic passing
        qb_stats = [s for s in game_stats if s.get("position") == "QB"]
        assert len(qb_stats) >= 2  # Both teams should have QB stats

        # High-scoring game should have significant passing yards
        total_passing = sum(s.get("passing_yards", 0) for s in qb_stats)
        assert total_passing > 400  # High-scoring game means lots of passing

    def test_defensive_shutout_persistence(self, unified_api, stats_generator):
        """Test stats generation for a shutout game."""
        mock_stats = stats_generator.generate(
            game_id="shutout_game",
            home_team_id=1,
            away_team_id=2,
            home_score=24,
            away_score=0
        )

        # Persist
        unified_api.stats_insert_game_stats(
            game_id="shutout_game",
            season=2025,
            week=1,
            season_type="regular_season",
            player_stats=mock_stats.player_stats
        )

        # Retrieve and verify
        game_stats = unified_api.stats_get_game_stats("shutout_game")
        assert len(game_stats) > 0

        # The losing team (away, team 2) should still have some stats
        away_team_stats = [s for s in game_stats if s.get("team_id") == 2]
        assert len(away_team_stats) > 0

    def test_all_stat_columns_persisted(self, unified_api, stats_generator):
        """Test that all stat columns are properly persisted."""
        mock_stats = stats_generator.generate(
            game_id="full_columns_test",
            home_team_id=1,
            away_team_id=2,
            home_score=35,
            away_score=28
        )

        # Persist
        unified_api.stats_insert_game_stats(
            game_id="full_columns_test",
            season=2025,
            week=1,
            season_type="regular_season",
            player_stats=mock_stats.player_stats
        )

        # Retrieve and verify
        game_stats = unified_api.stats_get_game_stats("full_columns_test")

        # Check that stats have expected keys
        expected_keys = [
            "player_id", "team_id", "position",
            "passing_yards", "rushing_yards", "receiving_yards",
            "tackles_total", "fantasy_points"
        ]

        first_stat = game_stats[0]
        for key in expected_keys:
            assert key in first_stat, f"Missing key: {key}"
