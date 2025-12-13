"""
Tests for database performance indices.

Verifies that performance indices exist in the schema files and that the
migration script correctly adds them to existing databases.
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path


# Import the migration script functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "scripts"))
from migrate_add_indices import (
    add_indices,
    table_exists,
    index_exists,
    ALL_INDICES,
)


@pytest.fixture
def temp_db_with_tables():
    """Create a temporary database with the relevant tables but no indices."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    conn = sqlite3.connect(db_path)

    # Create player_game_stats table
    conn.execute("""
        CREATE TABLE player_game_stats (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            player_id TEXT NOT NULL,
            team_id INTEGER NOT NULL
        )
    """)

    # Create player_game_grades table
    conn.execute("""
        CREATE TABLE player_game_grades (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL
        )
    """)

    # Create box_scores table
    conn.execute("""
        CREATE TABLE box_scores (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            team_id INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_db_empty():
    """Create a temporary empty database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Just create the file, don't add any tables
    conn = sqlite3.connect(db_path)
    conn.close()

    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


class TestTableAndIndexHelpers:
    """Tests for helper functions."""

    def test_table_exists_returns_true_for_existing_table(self, temp_db_with_tables):
        conn = sqlite3.connect(temp_db_with_tables)
        assert table_exists(conn, "player_game_stats") is True
        conn.close()

    def test_table_exists_returns_false_for_missing_table(self, temp_db_with_tables):
        conn = sqlite3.connect(temp_db_with_tables)
        assert table_exists(conn, "nonexistent_table") is False
        conn.close()

    def test_index_exists_returns_false_initially(self, temp_db_with_tables):
        conn = sqlite3.connect(temp_db_with_tables)
        assert index_exists(conn, "idx_player_stats_team_game") is False
        conn.close()


class TestMigrationScript:
    """Tests for the migration script."""

    def test_adds_indices_to_database(self, temp_db_with_tables):
        """Test that migration creates all expected indices."""
        results = add_indices(temp_db_with_tables)

        assert results["created"] == len(ALL_INDICES)
        assert results["skipped"] == 0
        assert results["table_missing"] == 0
        assert len(results["errors"]) == 0

        # Verify indices were created
        conn = sqlite3.connect(temp_db_with_tables)
        for index_name, _, _ in ALL_INDICES:
            assert index_exists(conn, index_name), f"Index {index_name} should exist"
        conn.close()

    def test_migration_is_idempotent(self, temp_db_with_tables):
        """Test that running migration twice doesn't fail or duplicate indices."""
        # First run
        results1 = add_indices(temp_db_with_tables)
        assert results1["created"] == len(ALL_INDICES)

        # Second run
        results2 = add_indices(temp_db_with_tables)
        assert results2["created"] == 0
        assert results2["skipped"] == len(ALL_INDICES)
        assert len(results2["errors"]) == 0

    def test_handles_missing_tables_gracefully(self, temp_db_empty):
        """Test that migration handles missing tables without errors."""
        results = add_indices(temp_db_empty)

        assert results["created"] == 0
        assert results["table_missing"] == len(ALL_INDICES)
        assert len(results["errors"]) == 0

    def test_handles_missing_database(self):
        """Test that migration handles nonexistent database path."""
        results = add_indices("/nonexistent/path/to/db.db")

        assert results["created"] == 0
        assert len(results["errors"]) > 0
        assert "not found" in results["errors"][0].lower()

    def test_dry_run_does_not_modify_database(self, temp_db_with_tables):
        """Test that dry run mode doesn't actually create indices."""
        results = add_indices(temp_db_with_tables, dry_run=True)

        assert results["created"] == len(ALL_INDICES)  # Reports what would be created

        # But indices should not actually exist
        conn = sqlite3.connect(temp_db_with_tables)
        for index_name, _, _ in ALL_INDICES:
            assert not index_exists(conn, index_name), f"Index {index_name} should NOT exist in dry run"
        conn.close()


class TestIndicesInSchemaFiles:
    """Tests that verify indices are defined in schema files."""

    def test_indices_in_schema_sql(self):
        """Test that player_game_grades index is in schema.sql."""
        schema_path = Path(__file__).parent.parent.parent.parent / "src" / "game_cycle" / "database" / "schema.sql"
        schema_content = schema_path.read_text()

        # Check for the new game grades index
        assert "idx_game_grades_game" in schema_content
        assert "player_game_grades(dynasty_id, game_id)" in schema_content

    def test_indices_in_full_schema_sql(self):
        """Test that all new indices are in full_schema.sql."""
        schema_path = Path(__file__).parent.parent.parent.parent / "src" / "game_cycle" / "database" / "full_schema.sql"
        schema_content = schema_path.read_text()

        # Check for player_game_stats indices
        assert "idx_player_stats_team_game" in schema_content
        assert "idx_player_stats_team" in schema_content
        assert "idx_player_stats_season_type" in schema_content

        # Check for box_scores indices
        assert "idx_box_scores_team" in schema_content
        assert "idx_box_scores_game_team" in schema_content