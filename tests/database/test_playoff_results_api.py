"""
Unit Tests for PlayoffResultsAPI

Tests playoff results extraction for draft order calculation including:
- Wild card losers extraction (6 teams)
- Divisional losers extraction (4 teams)
- Conference losers extraction (2 teams)
- Super Bowl winner/loser extraction
- Complete results structure
- Dynasty isolation
- Validation and error handling
"""

import pytest
import sqlite3
import json
from datetime import datetime

from database.playoff_results_api import PlayoffResultsAPI
from database.connection import DatabaseConnection
from events.event_database_api import EventDatabaseAPI


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def playoff_results_db_path(test_db_path):
    """
    Create test database with playoff events schema initialized.

    Returns:
        Path to test database with events table
    """
    # Initialize database connection
    db_conn = DatabaseConnection(test_db_path)
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Create dynasties table first (required for foreign keys)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            dynasty_name TEXT NOT NULL,
            owner_name TEXT,
            team_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        )
    """)

    # Ensure test dynasty exists
    db_conn.ensure_dynasty_exists("test_dynasty")
    db_conn.ensure_dynasty_exists("other_dynasty")

    # Initialize events table via EventDatabaseAPI
    EventDatabaseAPI(test_db_path)

    conn.commit()
    conn.close()

    return test_db_path


@pytest.fixture
def playoff_api(playoff_results_db_path):
    """
    Create PlayoffResultsAPI instance with test database.

    Returns:
        PlayoffResultsAPI instance
    """
    return PlayoffResultsAPI(playoff_results_db_path)


def create_playoff_game_event(
    conn: sqlite3.Connection,
    dynasty_id: str,
    season: int,
    game_type: str,
    away_team_id: int,
    home_team_id: int,
    winner_team_id: int,
    event_id: str = None
):
    """
    Helper to create a playoff game event in the database.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        season: Season year
        game_type: 'wildcard', 'divisional', 'conference', 'super_bowl'
        away_team_id: Away team ID
        home_team_id: Home team ID
        winner_team_id: Winning team ID
        event_id: Optional event ID (auto-generated if None)
    """
    if event_id is None:
        event_id = f"playoff_{game_type}_{away_team_id}_vs_{home_team_id}"

    # Generate game_id (same as event_id for simplicity)
    game_id = event_id

    # Create event data structure (matches GameEvent format)
    data = {
        'parameters': {
            'away_team_id': away_team_id,
            'home_team_id': home_team_id,
            'season': season,
            'season_type': 'playoffs',
            'game_type': game_type
        },
        'results': {
            'winner_team_id': winner_team_id,
            'away_score': 24 if winner_team_id == away_team_id else 17,
            'home_score': 24 if winner_team_id == home_team_id else 17
        }
    }

    # Insert event (include game_id - required field)
    cursor = conn.execute('''
        INSERT INTO events (event_id, game_id, dynasty_id, event_type, timestamp, data)
        VALUES (?, ?, ?, 'GAME', ?, ?)
    ''', (
        event_id,
        game_id,
        dynasty_id,
        int(datetime.now().timestamp() * 1000),
        json.dumps(data)
    ))

    conn.commit()


# ============================================================================
# TESTS: Wild Card Round Extraction
# ============================================================================


def test_get_wild_card_losers_success(playoff_api, playoff_results_db_path):
    """Test extracting 6 wild card losers."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create 6 wild card games (3 AFC, 3 NFC)
    # AFC games: lower seed loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 7, 2, 2)  # 7 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 6, 3, 3)  # 6 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 5, 4, 4)  # 5 loses

    # NFC games: higher seed loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 23, 18, 23)  # 18 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 24, 19, 24)  # 19 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 25, 20, 25)  # 20 loses

    conn.close()

    # Extract wild card losers
    losers = playoff_api._get_round_losers("test_dynasty", 2024, "wild_card")

    assert len(losers) == 6
    assert set(losers) == {5, 6, 7, 18, 19, 20}


def test_get_wild_card_losers_empty(playoff_api):
    """Test extracting wild card losers when no games exist."""
    losers = playoff_api._get_round_losers("test_dynasty", 2024, "wild_card")
    assert losers == []


# ============================================================================
# TESTS: Divisional Round Extraction
# ============================================================================


def test_get_divisional_losers_success(playoff_api, playoff_results_db_path):
    """Test extracting 4 divisional losers."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create 4 divisional games (2 AFC, 2 NFC)
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 4, 1, 1)  # 4 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 3, 2, 2)  # 3 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 21, 17, 17)  # 21 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 22, 18, 18)  # 22 loses

    conn.close()

    losers = playoff_api._get_round_losers("test_dynasty", 2024, "divisional")

    assert len(losers) == 4
    assert set(losers) == {3, 4, 21, 22}


# ============================================================================
# TESTS: Conference Championship Extraction
# ============================================================================


def test_get_conference_losers_success(playoff_api, playoff_results_db_path):
    """Test extracting 2 conference championship losers."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create 2 conference championship games (AFC, NFC)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 2, 1, 1)  # 2 loses (AFC)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 18, 17, 17)  # 18 loses (NFC)

    conn.close()

    losers = playoff_api._get_round_losers("test_dynasty", 2024, "conference")

    assert len(losers) == 2
    assert set(losers) == {2, 18}


# ============================================================================
# TESTS: Super Bowl Extraction
# ============================================================================


def test_get_super_bowl_teams_success(playoff_api, playoff_results_db_path):
    """Test extracting Super Bowl winner and loser."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create Super Bowl game: Team 1 (AFC) beats Team 17 (NFC)
    create_playoff_game_event(conn, "test_dynasty", 2024, "super_bowl", 17, 1, 1)

    conn.close()

    teams = playoff_api._get_super_bowl_teams("test_dynasty", 2024)

    assert teams['winner'] == 1
    assert teams['loser'] == 17


def test_get_super_bowl_teams_not_found(playoff_api):
    """Test error when Super Bowl not found."""
    with pytest.raises(ValueError, match="Super Bowl not found"):
        playoff_api._get_super_bowl_teams("test_dynasty", 2024)


def test_get_super_bowl_teams_incomplete_data(playoff_api, playoff_results_db_path):
    """Test error when Super Bowl data is incomplete."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create incomplete Super Bowl event (missing winner)
    data = {
        'parameters': {
            'away_team_id': 17,
            'home_team_id': 1,
            'season': 2024,
            'season_type': 'playoffs',
            'game_type': 'super_bowl'
        },
        'results': {}  # Missing winner_team_id
    }

    conn.execute('''
        INSERT INTO events (event_id, game_id, dynasty_id, event_type, timestamp, data)
        VALUES (?, ?, ?, 'GAME', ?, ?)
    ''', (
        "incomplete_sb",
        "incomplete_sb_game",  # Add game_id
        "test_dynasty",
        int(datetime.now().timestamp() * 1000),
        json.dumps(data)
    ))

    conn.commit()
    conn.close()

    with pytest.raises(ValueError, match="Incomplete Super Bowl data"):
        playoff_api._get_super_bowl_teams("test_dynasty", 2024)


# ============================================================================
# TESTS: Complete Playoff Results
# ============================================================================


def test_get_playoff_results_complete_playoffs(playoff_api, playoff_results_db_path):
    """Test extracting complete playoff results (all rounds)."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Realistic playoff progression:
    # AFC: Seeds 1-7, NFC: Seeds 17-23 (offset by 16)
    # Wild Card winners: 2, 3, 4, 18, 19, 20
    # Divisional winners: 1, 2, 17, 18
    # Conference winners: 1, 17
    # Super Bowl winner: 1

    # Wild Card (6 games) - losers: 5, 6, 7, 21, 22, 23
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 7, 2, 2)  # 7 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 6, 3, 3)  # 6 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 5, 4, 4)  # 5 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 23, 18, 18)  # 23 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 22, 19, 19)  # 22 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", 21, 20, 20)  # 21 loses

    # Divisional (4 games) - losers: 3, 4, 19, 20
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 4, 1, 1)  # 4 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 3, 2, 2)  # 3 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 20, 17, 17)  # 20 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", 19, 18, 18)  # 19 loses

    # Conference (2 games) - losers: 2, 18
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 2, 1, 1)  # 2 loses
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 18, 17, 17)  # 18 loses

    # Super Bowl (1 game) - loser: 17, winner: 1
    create_playoff_game_event(conn, "test_dynasty", 2024, "super_bowl", 17, 1, 1)  # 17 loses, 1 wins

    conn.close()

    # Get complete results
    results = playoff_api.get_playoff_results("test_dynasty", 2024)

    # Validate structure
    assert 'wild_card_losers' in results
    assert 'divisional_losers' in results
    assert 'conference_losers' in results
    assert 'super_bowl_loser' in results
    assert 'super_bowl_winner' in results

    # Validate counts
    assert len(results['wild_card_losers']) == 6
    assert len(results['divisional_losers']) == 4
    assert len(results['conference_losers']) == 2

    # Validate teams (fixed to avoid duplicates)
    assert set(results['wild_card_losers']) == {5, 6, 7, 21, 22, 23}
    assert set(results['divisional_losers']) == {3, 4, 19, 20}
    assert set(results['conference_losers']) == {2, 18}
    assert results['super_bowl_loser'] == 17
    assert results['super_bowl_winner'] == 1


# ============================================================================
# TESTS: Validation
# ============================================================================


def test_validate_playoff_results_success(playoff_api, playoff_results_db_path):
    """Test validation passes for correct playoff results."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create complete playoffs
    for i in range(6):
        create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", i+5, i+1, i+1)
    for i in range(4):
        create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", i+11, i+1, i+1)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 2, 1, 1)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 18, 17, 17)
    create_playoff_game_event(conn, "test_dynasty", 2024, "super_bowl", 17, 1, 1)

    conn.close()

    # Should not raise
    results = playoff_api.get_playoff_results("test_dynasty", 2024)
    assert results is not None


def test_validate_playoff_results_wrong_wild_card_count(playoff_api):
    """Test validation fails with wrong wild card loser count."""
    results = {
        'wild_card_losers': [1, 2, 3],  # Only 3, should be 6
        'divisional_losers': [4, 5, 6, 7],
        'conference_losers': [8, 9],
        'super_bowl_loser': 10,
        'super_bowl_winner': 11
    }

    with pytest.raises(ValueError, match="Expected 6 wild card losers"):
        playoff_api._validate_playoff_results(results)


def test_validate_playoff_results_duplicate_teams(playoff_api):
    """Test validation fails with duplicate teams."""
    results = {
        'wild_card_losers': [1, 2, 3, 4, 5, 6],
        'divisional_losers': [7, 8, 9, 10],
        'conference_losers': [11, 1],  # 1 is duplicate
        'super_bowl_loser': 12,
        'super_bowl_winner': 13
    }

    with pytest.raises(ValueError, match="Duplicate teams found"):
        playoff_api._validate_playoff_results(results)


# ============================================================================
# TESTS: Dynasty Isolation
# ============================================================================


def test_dynasty_isolation(playoff_api, playoff_results_db_path):
    """Test that dynasties are properly isolated."""
    conn = sqlite3.connect(playoff_results_db_path)

    # Create playoffs for test_dynasty
    for i in range(6):
        create_playoff_game_event(conn, "test_dynasty", 2024, "wildcard", i+5, i+1, i+1)
    for i in range(4):
        create_playoff_game_event(conn, "test_dynasty", 2024, "divisional", i+11, i+1, i+1)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 2, 1, 1)
    create_playoff_game_event(conn, "test_dynasty", 2024, "conference", 18, 17, 17)
    create_playoff_game_event(conn, "test_dynasty", 2024, "super_bowl", 17, 1, 1)

    # Create different playoffs for other_dynasty
    for i in range(6):
        create_playoff_game_event(conn, "other_dynasty", 2024, "wildcard", i+15, i+10, i+10)
    for i in range(4):
        create_playoff_game_event(conn, "other_dynasty", 2024, "divisional", i+21, i+10, i+10)
    create_playoff_game_event(conn, "other_dynasty", 2024, "conference", 11, 10, 10)
    create_playoff_game_event(conn, "other_dynasty", 2024, "conference", 28, 27, 27)
    create_playoff_game_event(conn, "other_dynasty", 2024, "super_bowl", 27, 10, 10)

    conn.close()

    # Get results for test_dynasty
    results_test = playoff_api.get_playoff_results("test_dynasty", 2024)
    results_other = playoff_api.get_playoff_results("other_dynasty", 2024)

    # Verify they're different
    assert results_test['super_bowl_winner'] == 1
    assert results_other['super_bowl_winner'] == 10

    # Verify no overlap in wild card losers
    assert not set(results_test['wild_card_losers']).intersection(set(results_other['wild_card_losers']))


# ============================================================================
# TESTS: Playoffs Complete Check
# ============================================================================


def test_playoffs_complete_true(playoff_api, playoff_results_db_path):
    """Test playoffs_complete returns True when Super Bowl exists."""
    conn = sqlite3.connect(playoff_results_db_path)
    create_playoff_game_event(conn, "test_dynasty", 2024, "super_bowl", 17, 1, 1)
    conn.close()

    assert playoff_api.playoffs_complete("test_dynasty", 2024) is True


def test_playoffs_complete_false(playoff_api):
    """Test playoffs_complete returns False when Super Bowl missing."""
    assert playoff_api.playoffs_complete("test_dynasty", 2024) is False
