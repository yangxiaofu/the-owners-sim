"""
Unit tests for ProgressionHistoryAPI.

Part of Tollgate 6: Career History Tracking.
"""
import json
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path

from src.game_cycle.database.progression_history_api import (
    ProgressionHistoryAPI,
    ProgressionHistoryRecord
)


@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS player_progression_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            age INTEGER NOT NULL,
            position TEXT,
            team_id INTEGER,
            age_category TEXT,
            overall_before INTEGER NOT NULL,
            overall_after INTEGER NOT NULL,
            overall_change INTEGER NOT NULL,
            attribute_changes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id, season)
        );

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def api(db_path):
    """Create a ProgressionHistoryAPI instance."""
    return ProgressionHistoryAPI(db_path)


@pytest.fixture
def sample_record():
    """Create a sample progression history record."""
    return ProgressionHistoryRecord(
        player_id=100,
        season=2025,
        age=24,
        position='quarterback',
        team_id=1,
        age_category='YOUNG',
        overall_before=78,
        overall_after=81,
        overall_change=3,
        attribute_changes=[
            {"attr": "accuracy", "old": 75, "new": 78, "change": 3},
            {"attr": "arm_strength", "old": 80, "new": 82, "change": 2}
        ]
    )


class TestProgressionHistoryRecord:
    """Tests for the ProgressionHistoryRecord dataclass."""

    def test_record_creation_with_all_fields(self):
        """Record should store all required fields."""
        record = ProgressionHistoryRecord(
            player_id=1,
            season=2025,
            age=25,
            position='running_back',
            team_id=5,
            age_category='YOUNG',
            overall_before=70,
            overall_after=72,
            overall_change=2,
            attribute_changes=[{"attr": "speed", "old": 85, "new": 87, "change": 2}]
        )
        assert record.player_id == 1
        assert record.season == 2025
        assert record.age == 25
        assert record.position == 'running_back'
        assert record.team_id == 5
        assert record.age_category == 'YOUNG'
        assert record.overall_before == 70
        assert record.overall_after == 72
        assert record.overall_change == 2
        assert len(record.attribute_changes) == 1

    def test_record_with_empty_attribute_changes(self):
        """Record should allow empty attribute changes list."""
        record = ProgressionHistoryRecord(
            player_id=2,
            season=2025,
            age=30,
            position='center',
            team_id=10,
            age_category='PRIME',
            overall_before=80,
            overall_after=80,
            overall_change=0,
            attribute_changes=[]
        )
        assert record.attribute_changes == []


class TestInsertProgressionRecord:
    """Tests for insert_progression_record method."""

    def test_insert_single_record(self, api, sample_record):
        """Should insert a single progression record."""
        api.insert_progression_record('test-dynasty', sample_record)

        # Verify insertion
        history = api.get_player_history('test-dynasty', 100)
        assert len(history) == 1
        assert history[0]['season'] == 2025
        assert history[0]['overall_change'] == 3

    def test_insert_replaces_existing_record_same_season(self, api, sample_record):
        """INSERT OR REPLACE should update existing record for same player/season."""
        api.insert_progression_record('test-dynasty', sample_record)

        # Insert updated record for same player/season
        updated_record = ProgressionHistoryRecord(
            player_id=100,
            season=2025,
            age=24,
            position='quarterback',
            team_id=1,
            age_category='YOUNG',
            overall_before=78,
            overall_after=85,  # Different
            overall_change=7,  # Different
            attribute_changes=[]
        )
        api.insert_progression_record('test-dynasty', updated_record)

        # Verify only one record exists with updated values
        history = api.get_player_history('test-dynasty', 100)
        assert len(history) == 1
        assert history[0]['overall_change'] == 7

    def test_insert_different_players_same_season(self, api):
        """Should allow records for different players in same season."""
        record1 = ProgressionHistoryRecord(
            player_id=1, season=2025, age=24, position='qb',
            team_id=1, age_category='YOUNG',
            overall_before=70, overall_after=72, overall_change=2,
            attribute_changes=[]
        )
        record2 = ProgressionHistoryRecord(
            player_id=2, season=2025, age=28, position='wr',
            team_id=1, age_category='PRIME',
            overall_before=80, overall_after=80, overall_change=0,
            attribute_changes=[]
        )

        api.insert_progression_record('test-dynasty', record1)
        api.insert_progression_record('test-dynasty', record2)

        history1 = api.get_player_history('test-dynasty', 1)
        history2 = api.get_player_history('test-dynasty', 2)
        assert len(history1) == 1
        assert len(history2) == 1


class TestInsertProgressionRecordsBatch:
    """Tests for insert_progression_records_batch method."""

    def test_batch_insert_multiple_records(self, api):
        """Should insert multiple records in a single transaction."""
        records = [
            ProgressionHistoryRecord(
                player_id=i, season=2025, age=25, position='lb',
                team_id=1, age_category='YOUNG',
                overall_before=70, overall_after=72, overall_change=2,
                attribute_changes=[]
            )
            for i in range(1, 11)  # 10 records
        ]

        count = api.insert_progression_records_batch('test-dynasty', records)
        assert count == 10

    def test_batch_insert_empty_list(self, api):
        """Should handle empty list gracefully."""
        count = api.insert_progression_records_batch('test-dynasty', [])
        assert count == 0

    def test_batch_insert_returns_count(self, api):
        """Should return count of inserted records."""
        records = [
            ProgressionHistoryRecord(
                player_id=100+i, season=2025, age=25, position='cb',
                team_id=1, age_category='YOUNG',
                overall_before=75, overall_after=77, overall_change=2,
                attribute_changes=[]
            )
            for i in range(5)
        ]

        count = api.insert_progression_records_batch('test-dynasty', records)
        assert count == 5


class TestGetPlayerHistory:
    """Tests for get_player_history method."""

    def test_get_history_returns_newest_first(self, api):
        """Should return records ordered by season descending."""
        for season in [2023, 2024, 2025]:
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=50, season=season, age=24+(season-2023),
                position='qb', team_id=1, age_category='YOUNG',
                overall_before=70+season-2023, overall_after=72+season-2023,
                overall_change=2, attribute_changes=[]
            ))

        history = api.get_player_history('test-dynasty', 50)
        assert len(history) == 3
        assert history[0]['season'] == 2025
        assert history[1]['season'] == 2024
        assert history[2]['season'] == 2023

    def test_get_history_respects_limit(self, api):
        """Should limit results to specified count."""
        for season in range(2020, 2026):
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=60, season=season, age=20+season-2020,
                position='rb', team_id=1, age_category='YOUNG',
                overall_before=70, overall_after=72, overall_change=2,
                attribute_changes=[]
            ))

        history = api.get_player_history('test-dynasty', 60, limit=3)
        assert len(history) == 3
        assert history[0]['season'] == 2025  # Most recent

    def test_get_history_nonexistent_player(self, api):
        """Should return empty list for player with no history."""
        history = api.get_player_history('test-dynasty', 99999)
        assert history == []

    def test_get_history_parses_attribute_changes_json(self, api, sample_record):
        """Should parse attribute_changes JSON correctly."""
        api.insert_progression_record('test-dynasty', sample_record)

        history = api.get_player_history('test-dynasty', 100)
        assert len(history) == 1
        changes = history[0]['attribute_changes']
        assert isinstance(changes, list)
        assert len(changes) == 2
        assert changes[0]['attr'] == 'accuracy'
        assert changes[0]['change'] == 3


class TestGetSeasonHistory:
    """Tests for get_season_history method."""

    def test_get_season_history_returns_all_players(self, api):
        """Should return all progression records for a season."""
        for player_id in range(1, 6):
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=player_id, season=2025, age=25,
                position='wr', team_id=1, age_category='YOUNG',
                overall_before=70, overall_after=72, overall_change=2,
                attribute_changes=[]
            ))

        history = api.get_season_history('test-dynasty', 2025)
        assert len(history) == 5

    def test_get_season_history_ordered_by_change(self, api):
        """Should order by overall_change descending (biggest gainers first)."""
        changes = [5, -2, 0, 3, -1]
        for i, change in enumerate(changes):
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=200+i, season=2025, age=25,
                position='te', team_id=1, age_category='YOUNG',
                overall_before=70, overall_after=70+change, overall_change=change,
                attribute_changes=[]
            ))

        history = api.get_season_history('test-dynasty', 2025)
        history_changes = [h['overall_change'] for h in history]
        assert history_changes == sorted(changes, reverse=True)


class TestDeletePlayerHistory:
    """Tests for delete_player_history method."""

    def test_delete_removes_all_player_history(self, api):
        """Should delete all history records for a player."""
        for season in [2023, 2024, 2025]:
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=300, season=season, age=25,
                position='c', team_id=1, age_category='PRIME',
                overall_before=75, overall_after=75, overall_change=0,
                attribute_changes=[]
            ))

        # Verify records exist
        assert len(api.get_player_history('test-dynasty', 300)) == 3

        # Delete
        deleted = api.delete_player_history('test-dynasty', 300)
        assert deleted == 3

        # Verify gone
        assert len(api.get_player_history('test-dynasty', 300)) == 0

    def test_delete_returns_zero_for_nonexistent(self, api):
        """Should return 0 when deleting nonexistent player history."""
        deleted = api.delete_player_history('test-dynasty', 99999)
        assert deleted == 0

    def test_delete_only_affects_specified_player(self, api):
        """Should not affect other players' history."""
        for player_id in [400, 401]:
            api.insert_progression_record('test-dynasty', ProgressionHistoryRecord(
                player_id=player_id, season=2025, age=25,
                position='s', team_id=1, age_category='YOUNG',
                overall_before=70, overall_after=72, overall_change=2,
                attribute_changes=[]
            ))

        api.delete_player_history('test-dynasty', 400)

        assert len(api.get_player_history('test-dynasty', 400)) == 0
        assert len(api.get_player_history('test-dynasty', 401)) == 1
