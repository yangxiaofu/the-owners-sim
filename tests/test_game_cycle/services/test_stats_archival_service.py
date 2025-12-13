"""
Tests for Stats Archival Service.

Tests the season-end statistics archival including:
- Immediate deletion of play-by-play grades (Tollgate 3)
- CSV export and deletion of old game data (Tollgate 4)
- Full season archival pipeline (Tollgate 5)
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path

from src.game_cycle.services.stats_archival_service import (
    StatsArchivalService,
    ArchivalResult,
    SeasonArchivalSummary,
)


def create_test_database(db_path: str, seasons: list = None):
    """Create a test database with play grades and game data."""
    if seasons is None:
        seasons = [2024, 2025, 2026]

    conn = sqlite3.connect(db_path)

    # Create games table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER NOT NULL,
            away_score INTEGER NOT NULL
        )
    """)

    # Create player_play_grades table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_play_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            play_number INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT NOT NULL,
            play_grade REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create player_game_stats table
    conn.execute("""
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
            passing_sacks INTEGER DEFAULT 0,
            passing_sack_yards INTEGER DEFAULT 0,
            passing_rating REAL DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            rushing_long INTEGER DEFAULT 0,
            rushing_fumbles INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            targets INTEGER DEFAULT 0,
            receiving_long INTEGER DEFAULT 0,
            receiving_drops INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            tackles_solo INTEGER DEFAULT 0,
            tackles_assist INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            fumbles_recovered INTEGER DEFAULT 0,
            passes_defended INTEGER DEFAULT 0,
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0,
            extra_points_made INTEGER DEFAULT 0,
            extra_points_attempted INTEGER DEFAULT 0,
            punts INTEGER DEFAULT 0,
            punt_yards INTEGER DEFAULT 0,
            pass_blocks INTEGER DEFAULT 0,
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
            snap_counts_offense INTEGER DEFAULT 0,
            snap_counts_defense INTEGER DEFAULT 0,
            snap_counts_special_teams INTEGER DEFAULT 0,
            fantasy_points REAL DEFAULT 0
        )
    """)

    # Create player_game_grades table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_game_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT,
            overall_grade REAL NOT NULL,
            passing_grade REAL,
            rushing_grade REAL,
            receiving_grade REAL,
            pass_blocking_grade REAL,
            run_blocking_grade REAL,
            pass_rush_grade REAL,
            run_defense_grade REAL,
            coverage_grade REAL,
            tackling_grade REAL,
            offensive_snaps INTEGER DEFAULT 0,
            defensive_snaps INTEGER DEFAULT 0,
            special_teams_snaps INTEGER DEFAULT 0,
            epa_total REAL DEFAULT 0.0,
            success_rate REAL,
            play_count INTEGER DEFAULT 0,
            positive_plays INTEGER DEFAULT 0,
            negative_plays INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create box_scores table
    conn.execute("""
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
            time_of_possession INTEGER
        )
    """)

    dynasty_id = "test_dynasty"

    for season in seasons:
        for week in range(1, 4):
            game_id = f"game_{season}_{week}_1_2"

            # Insert game
            conn.execute("""
                INSERT INTO games (game_id, dynasty_id, season, week, season_type,
                                 home_team_id, away_team_id, home_score, away_score)
                VALUES (?, ?, ?, ?, 'regular_season', 1, 2, 24, 17)
            """, (game_id, dynasty_id, season, week))

            # Insert play grades (50 plays * 11 players = 550 per game)
            for play_num in range(1, 51):
                for player_id in range(1, 12):
                    conn.execute("""
                        INSERT INTO player_play_grades (dynasty_id, game_id, play_number,
                            player_id, team_id, position, play_grade)
                        VALUES (?, ?, ?, ?, 1, 'QB', 65.0)
                    """, (dynasty_id, game_id, play_num, player_id))

            # Insert game stats (5 players per game)
            for player_id in range(1, 6):
                conn.execute("""
                    INSERT INTO player_game_stats (dynasty_id, game_id, season_type,
                        player_id, player_name, team_id, position, passing_yards)
                    VALUES (?, ?, 'regular_season', ?, ?, 1, 'QB', 250)
                """, (dynasty_id, game_id, f"player_{player_id}", f"Player {player_id}"))

            # Insert game grades (5 players per game)
            for player_id in range(1, 6):
                conn.execute("""
                    INSERT INTO player_game_grades (dynasty_id, game_id, season, week,
                        player_id, team_id, position, overall_grade)
                    VALUES (?, ?, ?, ?, ?, 1, 'QB', 72.5)
                """, (dynasty_id, game_id, season, week, player_id))

            # Insert box scores (2 teams per game)
            for team_id in [1, 2]:
                conn.execute("""
                    INSERT INTO box_scores (dynasty_id, game_id, team_id,
                        total_yards, passing_yards, rushing_yards)
                    VALUES (?, ?, ?, 350, 250, 100)
                """, (dynasty_id, game_id, team_id))

    conn.commit()
    conn.close()


@pytest.fixture
def temp_db_with_play_grades():
    """Create a temporary database with play grades data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    create_test_database(db_path, seasons=[2024, 2025, 2026])

    yield db_path

    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_archives_dir():
    """Create a temporary archives directory."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def archival_service(temp_db_with_play_grades, temp_archives_dir):
    """Create archival service with test database."""
    return StatsArchivalService(
        temp_db_with_play_grades,
        "test_dynasty",
        retention_seasons=2,
        archives_root=temp_archives_dir
    )


# ============================================================================
# TOLLGATE 3: Play Grades Deletion Tests
# ============================================================================

class TestDeletePlayGradesForSeason:
    """Tests for immediate play grades deletion."""

    def test_deletes_all_play_grades_for_season(self, archival_service, temp_db_with_play_grades):
        """Test that all play grades for a season are deleted."""
        # Count before
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades ppg
            JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
            WHERE ppg.dynasty_id = 'test_dynasty' AND g.season = 2025
        """)
        count_before = cursor.fetchone()[0]
        conn.close()

        assert count_before > 0, "Should have play grades before deletion"

        # Delete
        result = archival_service.delete_play_grades_for_season(2025)

        assert result.success is True
        assert result.rows_deleted == count_before
        assert result.operation == 'delete_play_grades'

        # Verify deletion
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades ppg
            JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
            WHERE ppg.dynasty_id = 'test_dynasty' AND g.season = 2025
        """)
        count_after = cursor.fetchone()[0]
        conn.close()

        assert count_after == 0

    def test_preserves_other_seasons(self, archival_service, temp_db_with_play_grades):
        """Test that play grades from other seasons are preserved."""
        # Count 2024 before
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades ppg
            JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
            WHERE ppg.dynasty_id = 'test_dynasty' AND g.season = 2024
        """)
        count_2024_before = cursor.fetchone()[0]
        conn.close()

        # Delete 2025
        archival_service.delete_play_grades_for_season(2025)

        # Check 2024 preserved
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades ppg
            JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
            WHERE ppg.dynasty_id = 'test_dynasty' AND g.season = 2024
        """)
        count_2024_after = cursor.fetchone()[0]
        conn.close()

        assert count_2024_after == count_2024_before

    def test_dynasty_isolation(self, temp_db_with_play_grades, temp_archives_dir):
        """Test that deletion only affects the specified dynasty."""
        # Add data for another dynasty
        conn = sqlite3.connect(temp_db_with_play_grades)
        conn.execute("""
            INSERT INTO games (game_id, dynasty_id, season, week, season_type,
                             home_team_id, away_team_id, home_score, away_score)
            VALUES ('other_game', 'other_dynasty', 2025, 1, 'regular_season', 1, 2, 24, 17)
        """)
        conn.execute("""
            INSERT INTO player_play_grades (dynasty_id, game_id, play_number,
                player_id, team_id, position, play_grade)
            VALUES ('other_dynasty', 'other_game', 1, 1, 1, 'QB', 65.0)
        """)
        conn.commit()
        conn.close()

        # Delete for test_dynasty
        service = StatsArchivalService(
            temp_db_with_play_grades,
            "test_dynasty",
            archives_root=temp_archives_dir
        )
        service.delete_play_grades_for_season(2025)

        # Check other_dynasty preserved
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades
            WHERE dynasty_id = 'other_dynasty'
        """)
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_handles_missing_table(self, temp_archives_dir):
        """Test graceful handling when player_play_grades table doesn't exist."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create database with only games table (no player_play_grades)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE games (
                game_id TEXT PRIMARY KEY,
                dynasty_id TEXT NOT NULL,
                season INTEGER NOT NULL,
                week INTEGER NOT NULL,
                season_type TEXT NOT NULL DEFAULT 'regular_season',
                home_team_id INTEGER NOT NULL,
                away_team_id INTEGER NOT NULL,
                home_score INTEGER NOT NULL,
                away_score INTEGER NOT NULL
            )
        """)
        conn.commit()
        conn.close()

        service = StatsArchivalService(db_path, "test_dynasty", archives_root=temp_archives_dir)
        result = service.delete_play_grades_for_season(2025)

        assert result.success is True
        assert result.rows_deleted == 0

        Path(db_path).unlink(missing_ok=True)

    def test_handles_empty_season(self, archival_service):
        """Test handling season with no play grades."""
        result = archival_service.delete_play_grades_for_season(2020)  # No data for 2020

        assert result.success is True
        assert result.rows_deleted == 0


# ============================================================================
# TOLLGATE 4: Game Data Archival Tests
# ============================================================================

class TestArchiveOldGameData:
    """Tests for game data archival with retention window."""

    def test_archives_seasons_beyond_retention(self, temp_archives_dir):
        """Test that seasons beyond retention window are archived."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create DB with seasons 2023, 2024, 2025 (to test archiving 2023)
        create_test_database(db_path, seasons=[2023, 2024, 2025])

        service = StatsArchivalService(
            db_path, "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        # With retention=2 and current_season=2026:
        # Keep 2025, 2026 (but 2026 doesn't exist)
        # Archive 2024 and earlier (2023, 2024)
        # Cutoff = 2026 - 2 = 2024, archive seasons <= 2024
        results = service.archive_old_game_data(current_season=2026)

        # Should archive 2023 and 2024
        assert len(results) == 2
        assert results[0].season == 2023
        assert results[1].season == 2024
        assert all(r.success for r in results)
        assert all(r.rows_exported > 0 for r in results)

        # Verify CSVs were created
        for season in [2023, 2024]:
            export_dir = Path(temp_archives_dir) / "test_dynasty" / f"season_{season}"
            assert (export_dir / "player_game_stats.csv").exists()
            assert (export_dir / "manifest.json").exists()

        Path(db_path).unlink(missing_ok=True)

    def test_preserves_recent_seasons(self, temp_archives_dir):
        """Test that seasons within retention window are preserved."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        create_test_database(db_path, seasons=[2024, 2025, 2026])

        service = StatsArchivalService(
            db_path, "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        # Archive with current=2027 (archive 2024 and 2025, keep 2026)
        service.archive_old_game_data(current_season=2027)

        conn = sqlite3.connect(db_path)

        # Check 2026 preserved
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_game_stats pgs
            JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
            WHERE pgs.dynasty_id = 'test_dynasty' AND g.season = 2026
        """)
        count_2026 = cursor.fetchone()[0]

        conn.close()

        assert count_2026 > 0, "Season 2026 should be preserved"

        Path(db_path).unlink(missing_ok=True)

    def test_no_archive_when_all_within_retention(self, temp_archives_dir):
        """Test no archival when all seasons within retention."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create DB with only 2025 and 2026
        create_test_database(db_path, seasons=[2025, 2026])

        service = StatsArchivalService(
            db_path, "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        # With retention=2 and current=2026, cutoff=2024
        # 2025 and 2026 are both > 2024, so nothing archived
        results = service.archive_old_game_data(current_season=2026)

        assert len(results) == 0

        Path(db_path).unlink(missing_ok=True)

    def test_validates_before_delete(self, temp_archives_dir):
        """Test that export is validated before deletion."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        create_test_database(db_path, seasons=[2023, 2025])

        service = StatsArchivalService(
            db_path, "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        # Archive 2023 with current=2026
        results = service.archive_old_game_data(current_season=2026)

        assert len(results) == 1
        assert results[0].success is True

        # Verify manifest exists (indicates validation passed)
        manifest_path = Path(temp_archives_dir) / "test_dynasty" / "season_2023" / "manifest.json"
        assert manifest_path.exists()

        Path(db_path).unlink(missing_ok=True)


# ============================================================================
# TOLLGATE 5: Full Season Archival Tests
# ============================================================================

class TestArchiveCompletedSeason:
    """Tests for full season archival pipeline."""

    def test_full_archival_pipeline(self, temp_db_with_play_grades, temp_archives_dir):
        """Test complete archival pipeline during season rollover."""
        service = StatsArchivalService(
            temp_db_with_play_grades,
            "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        summary = service.archive_completed_season(
            completed_season=2026,
            current_season=2027
        )

        assert summary.success is True
        assert summary.completed_season == 2026
        assert summary.current_season == 2027

        # Should have deleted play grades for 2026
        assert summary.play_grades_deleted > 0

        # Should have archived 2024 and 2025 (beyond retention with current=2027)
        assert 2024 in summary.seasons_archived
        assert 2025 in summary.seasons_archived

        # Verify 2026 play grades deleted
        conn = sqlite3.connect(temp_db_with_play_grades)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM player_play_grades ppg
            JOIN games g ON ppg.game_id = g.game_id AND ppg.dynasty_id = g.dynasty_id
            WHERE ppg.dynasty_id = 'test_dynasty' AND g.season = 2026
        """)
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 0

    def test_play_grades_deletion_with_no_old_seasons(self, temp_archives_dir):
        """Test that play grades deletion works even when no old seasons to archive."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Only have current season data
        create_test_database(db_path, seasons=[2026])

        service = StatsArchivalService(
            db_path, "test_dynasty",
            retention_seasons=2,
            archives_root=temp_archives_dir
        )

        summary = service.archive_completed_season(
            completed_season=2026,
            current_season=2027
        )

        # Play grades should be deleted
        assert summary.play_grades_deleted > 0

        # No seasons to archive (2026 is within retention)
        assert len(summary.seasons_archived) == 0

        Path(db_path).unlink(missing_ok=True)


class TestGetArchivalStatus:
    """Tests for archival status reporting."""

    def test_returns_status_info(self, archival_service):
        """Test that status returns expected information."""
        status = archival_service.get_archival_status()

        assert status['dynasty_id'] == 'test_dynasty'
        assert status['retention_seasons'] == 2
        assert 2024 in status['seasons_with_game_data']
        assert 2025 in status['seasons_with_game_data']
        assert 2026 in status['seasons_with_game_data']
        assert status['play_grades_count'] > 0
        assert status['game_stats_count'] > 0