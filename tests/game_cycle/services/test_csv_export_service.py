"""
Tests for CSV Export Service.

Tests the streaming CSV export functionality for season-end statistics archival.
"""

import pytest
import sqlite3
import json
import tempfile
from pathlib import Path

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.export_data_api import ExportDataAPI
from src.game_cycle.services.csv_export_service import (
    CSVExportService,
    ExportResult,
    SeasonExportResult,
)


@pytest.fixture
def temp_db_with_data():
    """Create a temporary database with game-level statistics data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)

    # Create games table
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

    # Create player_game_stats table (simplified)
    conn.execute("""
        CREATE TABLE player_game_stats (
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
        CREATE TABLE player_game_grades (
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

    # Insert test data
    dynasty_id = "test_dynasty"
    season = 2025

    # Insert games
    for week in range(1, 4):
        game_id = f"game_{season}_{week}_1_2"
        conn.execute("""
            INSERT INTO games (game_id, dynasty_id, season, week, season_type,
                             home_team_id, away_team_id, home_score, away_score)
            VALUES (?, ?, ?, ?, 'regular_season', 1, 2, 24, 17)
        """, (game_id, dynasty_id, season, week))

        # Insert player stats for each game
        for player_num in range(1, 6):
            conn.execute("""
                INSERT INTO player_game_stats (dynasty_id, game_id, season_type,
                    player_id, player_name, team_id, position, passing_yards)
                VALUES (?, ?, 'regular_season', ?, ?, 1, 'QB', ?)
            """, (dynasty_id, game_id, f"player_{player_num}",
                  f"Player {player_num}", 250 + player_num * 10))

        # Insert player grades for each game
        for player_num in range(1, 6):
            conn.execute("""
                INSERT INTO player_game_grades (dynasty_id, game_id, season, week,
                    player_id, team_id, position, overall_grade)
                VALUES (?, ?, ?, ?, ?, 1, 'QB', ?)
            """, (dynasty_id, game_id, season, week, player_num, 70.0 + player_num))

        # Insert box scores for each game (2 teams)
        for team_id in [1, 2]:
            conn.execute("""
                INSERT INTO box_scores (dynasty_id, game_id, team_id,
                    total_yards, passing_yards, rushing_yards)
                VALUES (?, ?, ?, 350, 250, 100)
            """, (dynasty_id, game_id, team_id))

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_archives_dir():
    """Create a temporary archives directory."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def export_service(temp_db_with_data, temp_archives_dir):
    """Create export service with test database and temp archives."""
    return CSVExportService(temp_db_with_data, archives_root=temp_archives_dir)


class TestExportDataAPI:
    """Tests for the ExportDataAPI class."""

    def test_get_row_count_player_game_stats(self, temp_db_with_data):
        """Test row count for player_game_stats."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        count = api.get_row_count("player_game_stats", "test_dynasty", 2025)
        # 3 weeks * 5 players = 15
        assert count == 15

    def test_get_row_count_player_game_grades(self, temp_db_with_data):
        """Test row count for player_game_grades."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        count = api.get_row_count("player_game_grades", "test_dynasty", 2025)
        # 3 weeks * 5 players = 15
        assert count == 15

    def test_get_row_count_box_scores(self, temp_db_with_data):
        """Test row count for box_scores."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        count = api.get_row_count("box_scores", "test_dynasty", 2025)
        # 3 weeks * 2 teams = 6
        assert count == 6

    def test_stream_player_game_stats(self, temp_db_with_data):
        """Test streaming player_game_stats."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        rows = []
        for batch in api.stream_player_game_stats("test_dynasty", 2025, batch_size=10):
            rows.extend(batch)

        assert len(rows) == 15

    def test_get_seasons_with_data(self, temp_db_with_data):
        """Test getting seasons with data."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        seasons = api.get_seasons_with_data("test_dynasty")
        assert seasons == [2025]

    def test_dynasty_isolation(self, temp_db_with_data):
        """Test that queries are isolated by dynasty."""
        db = GameCycleDatabase(temp_db_with_data)
        api = ExportDataAPI(db)

        # Non-existent dynasty should return 0
        count = api.get_row_count("player_game_stats", "other_dynasty", 2025)
        assert count == 0


class TestCSVExportService:
    """Tests for the CSVExportService class."""

    def test_export_creates_valid_csv(self, export_service, temp_archives_dir):
        """Test that export creates valid CSV files."""
        result = export_service.export_season("test_dynasty", 2025)

        assert result.success is True
        assert result.total_rows > 0
        assert len(result.exports) == 3  # 3 tables

        # Check files exist
        export_dir = Path(temp_archives_dir) / "test_dynasty" / "season_2025"
        assert (export_dir / "player_game_stats.csv").exists()
        assert (export_dir / "player_game_grades.csv").exists()
        assert (export_dir / "box_scores.csv").exists()
        assert (export_dir / "manifest.json").exists()

    def test_export_row_counts(self, export_service):
        """Test that export row counts match expected values."""
        result = export_service.export_season("test_dynasty", 2025)

        # Find each table's export result
        stats_export = next(e for e in result.exports if e.table_name == "player_game_stats")
        grades_export = next(e for e in result.exports if e.table_name == "player_game_grades")
        box_export = next(e for e in result.exports if e.table_name == "box_scores")

        assert stats_export.rows_exported == 15  # 3 weeks * 5 players
        assert grades_export.rows_exported == 15  # 3 weeks * 5 players
        assert box_export.rows_exported == 6  # 3 weeks * 2 teams

    def test_manifest_contains_checksums(self, export_service, temp_archives_dir):
        """Test that manifest contains file checksums."""
        result = export_service.export_season("test_dynasty", 2025)

        # Read manifest
        manifest_path = Path(temp_archives_dir) / "test_dynasty" / "season_2025" / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["dynasty_id"] == "test_dynasty"
        assert manifest["season"] == 2025
        assert manifest["success"] is True
        assert len(manifest["exports"]) == 3

        # Each export should have a checksum
        for export in manifest["exports"]:
            assert "checksum" in export
            assert len(export["checksum"]) == 64  # SHA256 hex digest

    def test_validate_export(self, export_service):
        """Test export validation."""
        result = export_service.export_season("test_dynasty", 2025)
        assert export_service.validate_export(result) is True

    def test_validate_against_database(self, export_service):
        """Test validation against database row counts."""
        result = export_service.export_season("test_dynasty", 2025)
        assert export_service.validate_against_database("test_dynasty", 2025, result) is True

    def test_export_exists(self, export_service):
        """Test checking if export exists."""
        assert export_service.export_exists("test_dynasty", 2025) is False

        export_service.export_season("test_dynasty", 2025)

        assert export_service.export_exists("test_dynasty", 2025) is True

    def test_load_manifest(self, export_service):
        """Test loading manifest from existing export."""
        # Before export
        assert export_service.load_manifest("test_dynasty", 2025) is None

        # After export
        export_service.export_season("test_dynasty", 2025)
        manifest = export_service.load_manifest("test_dynasty", 2025)

        assert manifest is not None
        assert manifest["dynasty_id"] == "test_dynasty"
        assert manifest["season"] == 2025

    def test_export_empty_season(self, export_service):
        """Test exporting a season with no data."""
        result = export_service.export_season("test_dynasty", 2020)

        assert result.success is True
        assert result.total_rows == 0

        for export in result.exports:
            assert export.rows_exported == 0


class TestCSVContent:
    """Tests for CSV file content."""

    def test_csv_has_header(self, export_service, temp_archives_dir):
        """Test that CSV files have a header row."""
        export_service.export_season("test_dynasty", 2025)

        csv_path = Path(temp_archives_dir) / "test_dynasty" / "season_2025" / "player_game_stats.csv"
        with open(csv_path) as f:
            header = f.readline().strip()

        assert "dynasty_id" in header
        assert "player_id" in header
        assert "passing_yards" in header

    def test_csv_data_rows(self, export_service, temp_archives_dir):
        """Test that CSV files contain data rows."""
        export_service.export_season("test_dynasty", 2025)

        csv_path = Path(temp_archives_dir) / "test_dynasty" / "season_2025" / "player_game_stats.csv"
        with open(csv_path) as f:
            lines = f.readlines()

        # Header + 15 data rows
        assert len(lines) == 16