"""
Integration tests for Training Camp progression history.

Part of Tollgate 6: Career History Tracking.
Tests the integration between TrainingCampService and ProgressionHistoryAPI.
"""
import json
import pytest
import sqlite3
import tempfile
import os
import sys
import importlib.util
from pathlib import Path


def _import_module_directly(module_name: str, relative_path: str):
    """Import a module directly without going through __init__.py."""
    src_path = Path(__file__).parent.parent.parent.parent / 'src'
    module_path = src_path / relative_path

    # Add src to path for nested imports
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Import modules directly to avoid __init__.py import chain issues
_tcs = _import_module_directly(
    "training_camp_service",
    "game_cycle/services/training_camp_service.py"
)
_phapi = _import_module_directly(
    "progression_history_api",
    "game_cycle/database/progression_history_api.py"
)

TrainingCampService = _tcs.TrainingCampService
AgeWeightedDevelopment = _tcs.AgeWeightedDevelopment
PlayerDevelopmentResult = _tcs.PlayerDevelopmentResult
AttributeChange = _tcs.AttributeChange
ProgressionHistoryAPI = _phapi.ProgressionHistoryAPI


@pytest.fixture
def db_with_players():
    """Create a test database with schema and sample players."""
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

        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            number INTEGER NOT NULL DEFAULT 1,
            team_id INTEGER NOT NULL,
            positions TEXT NOT NULL,
            attributes TEXT NOT NULL,
            birthdate TEXT,
            status TEXT DEFAULT 'active',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id)
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

    # Insert test players
    players = [
        (1, 'Young', 'Quarterback', '["quarterback"]', '{"overall": 75, "accuracy": 70, "arm_strength": 75, "awareness": 70, "mobility": 72, "pocket_presence": 68}', '2002-01-01'),
        (2, 'Prime', 'Receiver', '["wide_receiver"]', '{"overall": 85, "speed": 88, "hands": 85, "route_running": 86, "agility": 84, "awareness": 82, "catching": 85}', '1996-06-15'),
        (3, 'Veteran', 'Linebacker', '["linebacker"]', '{"overall": 80, "coverage": 78, "run_defense": 82, "tackling": 80, "speed": 75, "awareness": 85}', '1991-03-20'),
    ]

    for player_id, first, last, positions, attrs, birthdate in players:
        conn.execute('''
            INSERT INTO players (dynasty_id, player_id, first_name, last_name, team_id, positions, attributes, birthdate)
            VALUES ('test-dynasty', ?, ?, ?, 1, ?, ?, ?)
        ''', (player_id, first, last, positions, attrs, birthdate))

    conn.commit()
    conn.close()

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def service(db_with_players):
    """Create a TrainingCampService instance."""
    return TrainingCampService(
        db_path=db_with_players,
        dynasty_id='test-dynasty',
        season=2025
    )


class TestTrainingCampHistoryIntegration:
    """Integration tests for training camp history persistence."""

    def test_service_has_history_api(self, service):
        """Service should initialize with a ProgressionHistoryAPI."""
        assert hasattr(service, '_history_api')
        # Check class name since direct isinstance may fail due to import mechanism
        assert service._history_api.__class__.__name__ == 'ProgressionHistoryAPI'

    def test_process_all_creates_history_records(self, service, db_with_players):
        """Processing all players should create history records."""
        # Process training camp
        result = service.process_all_players()

        # Verify history records were created
        history_api = ProgressionHistoryAPI(db_with_players)

        # Check player 1 (young QB)
        history = history_api.get_player_history('test-dynasty', 1)
        assert len(history) == 1
        assert history[0]['season'] == 2025
        assert history[0]['position'] == 'quarterback'
        assert history[0]['age_category'] == 'YOUNG'

    def test_history_records_match_development_results(self, service, db_with_players):
        """History records should match the development results."""
        result = service.process_all_players()

        history_api = ProgressionHistoryAPI(db_with_players)

        # Get all player results
        for player_result in result['results']:
            player_id = player_result.player_id

            # Skip if no changes
            if not player_result.attribute_changes and player_result.overall_change == 0:
                continue

            history = history_api.get_player_history('test-dynasty', player_id)

            if history:
                record = history[0]
                assert record['overall_before'] == player_result.old_overall
                assert record['overall_after'] == player_result.new_overall
                assert record['overall_change'] == player_result.overall_change
                assert record['age'] == player_result.age

    def test_get_player_progression_history_wrapper(self, service, db_with_players):
        """Service wrapper should retrieve history correctly."""
        # First process players to create history
        service.process_all_players()

        # Use wrapper method
        history = service.get_player_progression_history(player_id=1)

        assert isinstance(history, list)
        assert len(history) >= 1
        assert history[0]['season'] == 2025

    def test_multi_year_history_trend(self, db_with_players):
        """Should track multiple years of progression."""
        # Simulate multiple seasons
        for season in [2024, 2025, 2026]:
            svc = TrainingCampService(
                db_path=db_with_players,
                dynasty_id='test-dynasty',
                season=season
            )
            svc.process_all_players()

        # Check multi-year history
        history_api = ProgressionHistoryAPI(db_with_players)
        history = history_api.get_player_history('test-dynasty', 1, limit=5)

        assert len(history) == 3
        # Newest first
        assert history[0]['season'] == 2026
        assert history[1]['season'] == 2025
        assert history[2]['season'] == 2024

    def test_history_attribute_changes_stored_correctly(self, service, db_with_players):
        """Attribute changes should be stored as proper JSON."""
        service.process_all_players()

        history_api = ProgressionHistoryAPI(db_with_players)

        # Get any player with changes
        for player_id in [1, 2, 3]:
            history = history_api.get_player_history('test-dynasty', player_id)
            if history and history[0]['attribute_changes']:
                changes = history[0]['attribute_changes']
                assert isinstance(changes, list)
                for change in changes:
                    assert 'attr' in change
                    assert 'old' in change
                    assert 'new' in change
                    assert 'change' in change
                break

    def test_history_survives_reprocessing_same_season(self, service, db_with_players):
        """Re-running training camp should update (not duplicate) history."""
        # Process twice
        service.process_all_players()
        service.process_all_players()

        history_api = ProgressionHistoryAPI(db_with_players)
        history = history_api.get_player_history('test-dynasty', 1)

        # Should have exactly one record for 2025 (INSERT OR REPLACE)
        season_2025_records = [h for h in history if h['season'] == 2025]
        assert len(season_2025_records) == 1


class TestHistoryByAgeCategory:
    """Tests for history records by age category."""

    def test_young_player_history_has_young_category(self, service, db_with_players):
        """Young player should have YOUNG age category in history."""
        service.process_all_players()

        history_api = ProgressionHistoryAPI(db_with_players)
        history = history_api.get_player_history('test-dynasty', 1)  # Young QB

        assert history[0]['age_category'] == 'YOUNG'

    def test_veteran_player_history_has_veteran_category(self, service, db_with_players):
        """Veteran player should have VETERAN age category in history."""
        service.process_all_players()

        # Use direct API import for querying
        _phapi_local = _import_module_directly(
            "progression_history_api_local",
            "game_cycle/database/progression_history_api.py"
        )
        history_api = _phapi_local.ProgressionHistoryAPI(db_with_players)
        history = history_api.get_player_history('test-dynasty', 3)  # Veteran LB

        # Only check if there was a record (veteran may have no changes some runs)
        if history:
            assert history[0]['age_category'] == 'VETERAN'
        else:
            # No changes means no history record, but we can verify the service
            # would categorize correctly by checking the results
            result = service.process_all_players()
            veteran_result = [r for r in result['results'] if r.player_id == 3][0]
            assert veteran_result.age_category.name == 'VETERAN'


class TestSeasonHistoryAggregation:
    """Tests for season-wide history queries."""

    def test_get_season_history_returns_all_processed(self, service, db_with_players):
        """Season history should include all players processed."""
        result = service.process_all_players()

        # Count players with changes
        players_with_changes = sum(
            1 for r in result['results']
            if r.attribute_changes or r.overall_change != 0
        )

        history_api = ProgressionHistoryAPI(db_with_players)
        season_history = history_api.get_season_history('test-dynasty', 2025)

        assert len(season_history) == players_with_changes
