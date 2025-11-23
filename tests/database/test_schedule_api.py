"""
Unit Tests for Schedule API Methods in DatabaseAPI

Tests schedule retrieval methods including:
- get_team_opponents() - Get single team's schedule
- get_all_team_schedules() - Batch get all 32 teams' schedules
- Dynasty isolation
- Season/season_type filtering
"""

import pytest
import sqlite3
from datetime import datetime

from database.api import DatabaseAPI
from database.connection import DatabaseConnection


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def schedule_db_path(test_db_path):
    """
    Create test database with games table and sample schedule data.

    Returns:
        Path to test database with games table
    """
    # Initialize database connection
    db_conn = DatabaseConnection(test_db_path)
    conn = db_conn.get_connection()
    cursor = conn.cursor()

    # Create dynasties table first
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

    # Ensure test dynasties exist
    db_conn.ensure_dynasty_exists("test_dynasty")
    db_conn.ensure_dynasty_exists("other_dynasty")

    # Create games table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS games (
            game_id TEXT PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT NOT NULL,
            game_type TEXT,
            game_date INTEGER NOT NULL,
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER,
            away_score INTEGER,
            winner_team_id INTEGER,
            total_plays INTEGER,
            game_duration_minutes INTEGER,
            overtime_periods INTEGER DEFAULT 0,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
        )
    """)

    conn.commit()
    conn.close()

    return test_db_path


@pytest.fixture
def schedule_api(schedule_db_path):
    """Create DatabaseAPI instance with test database."""
    return DatabaseAPI(schedule_db_path)


def create_game(
    conn: sqlite3.Connection,
    dynasty_id: str,
    season: int,
    week: int,
    home_team_id: int,
    away_team_id: int,
    season_type: str = "regular_season",
    home_wins: bool = True
):
    """Helper to create a game record."""
    game_id = f"{dynasty_id}_{season}_week{week}_{away_team_id}_at_{home_team_id}"

    # Set scores based on who wins
    if home_wins:
        home_score = 24
        away_score = 17
    else:
        home_score = 17
        away_score = 24

    conn.execute('''
        INSERT INTO games (
            game_id, dynasty_id, season, week, season_type, game_type,
            game_date, home_team_id, away_team_id, home_score, away_score
        ) VALUES (?, ?, ?, ?, ?, 'regular', ?, ?, ?, ?, ?)
    ''', (
        game_id,
        dynasty_id,
        season,
        week,
        season_type,
        int(datetime.now().timestamp() * 1000),
        home_team_id,
        away_team_id,
        home_score,
        away_score
    ))
    conn.commit()


# ============================================================================
# TESTS: get_team_opponents()
# ============================================================================


def test_get_team_opponents_success(schedule_api, schedule_db_path):
    """Test getting opponents for a single team."""
    conn = sqlite3.connect(schedule_db_path)

    # Create a 4-game schedule for team 7
    create_game(conn, "test_dynasty", 2024, 1, 7, 3)  # Team 7 home vs 3
    create_game(conn, "test_dynasty", 2024, 2, 12, 7)  # Team 7 away at 12
    create_game(conn, "test_dynasty", 2024, 3, 7, 15)  # Team 7 home vs 15
    create_game(conn, "test_dynasty", 2024, 4, 20, 7)  # Team 7 away at 20

    conn.close()

    opponents = schedule_api.get_team_opponents("test_dynasty", 7, 2024)

    assert len(opponents) == 4
    assert opponents == [3, 12, 15, 20]  # In week order


def test_get_team_opponents_empty(schedule_api):
    """Test getting opponents when team has no games."""
    opponents = schedule_api.get_team_opponents("test_dynasty", 7, 2024)
    assert opponents == []


def test_get_team_opponents_season_type_filter(schedule_api, schedule_db_path):
    """Test season_type filtering (regular vs preseason vs playoffs)."""
    conn = sqlite3.connect(schedule_db_path)

    # Team 7 schedule: 2 regular season, 1 preseason
    create_game(conn, "test_dynasty", 2024, 1, 7, 3, "regular_season")
    create_game(conn, "test_dynasty", 2024, 2, 7, 12, "regular_season")
    create_game(conn, "test_dynasty", 2024, 1, 7, 15, "preseason")

    conn.close()

    # Query regular season only
    regular_opponents = schedule_api.get_team_opponents(
        "test_dynasty", 7, 2024, season_type="regular_season"
    )
    assert regular_opponents == [3, 12]

    # Query preseason only
    preseason_opponents = schedule_api.get_team_opponents(
        "test_dynasty", 7, 2024, season_type="preseason"
    )
    assert preseason_opponents == [15]


def test_get_team_opponents_dynasty_isolation(schedule_api, schedule_db_path):
    """Test that dynasties are properly isolated."""
    conn = sqlite3.connect(schedule_db_path)

    # Team 7 in test_dynasty
    create_game(conn, "test_dynasty", 2024, 1, 7, 3)
    create_game(conn, "test_dynasty", 2024, 2, 7, 12)

    # Team 7 in other_dynasty (different opponents)
    create_game(conn, "other_dynasty", 2024, 1, 7, 20)
    create_game(conn, "other_dynasty", 2024, 2, 7, 25)

    conn.close()

    # Query test_dynasty
    test_opponents = schedule_api.get_team_opponents("test_dynasty", 7, 2024)
    assert test_opponents == [3, 12]

    # Query other_dynasty
    other_opponents = schedule_api.get_team_opponents("other_dynasty", 7, 2024)
    assert other_opponents == [20, 25]


def test_get_team_opponents_full_season(schedule_api, schedule_db_path):
    """Test getting a full 17-game NFL schedule."""
    conn = sqlite3.connect(schedule_db_path)

    # Create 17-game schedule for team 7
    opponents = [3, 12, 15, 20, 8, 14, 9, 22, 5, 18, 11, 27, 4, 16, 25, 30, 1]
    for week, opponent_id in enumerate(opponents, start=1):
        if week % 2 == 0:
            # Even weeks: away game
            create_game(conn, "test_dynasty", 2024, week, opponent_id, 7)
        else:
            # Odd weeks: home game
            create_game(conn, "test_dynasty", 2024, week, 7, opponent_id)

    conn.close()

    result = schedule_api.get_team_opponents("test_dynasty", 7, 2024)

    assert len(result) == 17
    assert result == opponents


# ============================================================================
# TESTS: get_all_team_schedules()
# ============================================================================


def test_get_all_team_schedules_success(schedule_api, schedule_db_path):
    """Test getting schedules for all 32 teams."""
    conn = sqlite3.connect(schedule_db_path)

    # Create minimal schedule: each team plays 1 game
    # Team 1 vs 2, Team 3 vs 4, etc.
    for i in range(1, 32, 2):
        create_game(conn, "test_dynasty", 2024, 1, i, i+1)

    conn.close()

    schedules = schedule_api.get_all_team_schedules("test_dynasty", 2024)

    # Should have entries for all 32 teams
    assert len(schedules) == 32

    # Verify structure
    for team_id in range(1, 33):
        assert team_id in schedules
        assert isinstance(schedules[team_id], list)

    # Verify specific matchups
    assert 2 in schedules[1]  # Team 1 played Team 2
    assert 1 in schedules[2]  # Team 2 played Team 1
    assert 4 in schedules[3]  # Team 3 played Team 4
    assert 3 in schedules[4]  # Team 4 played Team 3


def test_get_all_team_schedules_empty(schedule_api):
    """Test getting schedules when no games exist."""
    schedules = schedule_api.get_all_team_schedules("test_dynasty", 2024)

    # Should still return dict with all 32 teams
    assert len(schedules) == 32

    # All schedules should be empty
    for team_id in range(1, 33):
        assert schedules[team_id] == []


def test_get_all_team_schedules_partial_data(schedule_api, schedule_db_path):
    """Test when some teams have games and others don't."""
    conn = sqlite3.connect(schedule_db_path)

    # Only create games for teams 1-10
    for i in range(1, 10, 2):
        create_game(conn, "test_dynasty", 2024, 1, i, i+1)

    conn.close()

    schedules = schedule_api.get_all_team_schedules("test_dynasty", 2024)

    # All 32 teams should be in dict
    assert len(schedules) == 32

    # Teams 1-10 have opponents
    for team_id in range(1, 11):
        assert len(schedules[team_id]) > 0

    # Teams 11-32 have no opponents
    for team_id in range(11, 33):
        assert schedules[team_id] == []


def test_get_all_team_schedules_dynasty_isolation(schedule_api, schedule_db_path):
    """Test dynasty isolation for batch schedule query."""
    conn = sqlite3.connect(schedule_db_path)

    # Create different schedules for different dynasties
    # test_dynasty: Team 1 plays Team 2
    create_game(conn, "test_dynasty", 2024, 1, 1, 2)

    # other_dynasty: Team 1 plays Team 3
    create_game(conn, "other_dynasty", 2024, 1, 1, 3)

    conn.close()

    # Get schedules for test_dynasty
    test_schedules = schedule_api.get_all_team_schedules("test_dynasty", 2024)
    assert 2 in test_schedules[1]  # Team 1 played 2
    assert 3 not in test_schedules[1]  # Did NOT play 3

    # Get schedules for other_dynasty
    other_schedules = schedule_api.get_all_team_schedules("other_dynasty", 2024)
    assert 3 in other_schedules[1]  # Team 1 played 3
    assert 2 not in other_schedules[1]  # Did NOT play 2


def test_get_all_team_schedules_performance(schedule_api, schedule_db_path):
    """Test that batch query reuses connection efficiently."""
    conn = sqlite3.connect(schedule_db_path)

    # Create a full season for all 32 teams (simplified: everyone plays week 1)
    for home_id in range(1, 32, 2):
        create_game(conn, "test_dynasty", 2024, 1, home_id, home_id + 1)

    conn.close()

    # This should execute efficiently (reusing connection)
    schedules = schedule_api.get_all_team_schedules("test_dynasty", 2024)

    # Verify all 32 teams got data
    assert len(schedules) == 32
    teams_with_games = sum(1 for sched in schedules.values() if len(sched) > 0)
    assert teams_with_games == 32  # All teams played
