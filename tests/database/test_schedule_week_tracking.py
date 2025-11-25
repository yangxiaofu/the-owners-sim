"""
Tests for Schedule Week Tracking API Methods

Tests the new get_week_for_date() method in DatabaseAPI including:
- Week number retrieval for valid dates
- Handling dates with no scheduled games
- Preseason weeks (1-3)
- Regular season weeks (1-18)
- Multiple games on same date (DISTINCT handling)
- Dynasty isolation
- Season type filtering
"""

import pytest
import sqlite3
from datetime import datetime, timedelta

from database.api import DatabaseAPI
from database.connection import DatabaseConnection


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def week_tracking_db_path(test_db_path):
    """
    Create test database with games table for week tracking tests.

    Returns:
        Path to test database with games table and dynasty setup
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

    # Create games table with week column
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
def week_api(week_tracking_db_path):
    """Create DatabaseAPI instance with test database."""
    return DatabaseAPI(week_tracking_db_path)


def create_game_on_date(
    conn: sqlite3.Connection,
    dynasty_id: str,
    season: int,
    week: int,
    season_type: str,
    game_date: str,
    home_team_id: int = 1,
    away_team_id: int = 2
):
    """
    Helper to create a game record on a specific date.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        season: Season year
        week: Week number
        season_type: "preseason" or "regular_season"
        game_date: Date string in YYYY-MM-DD format
        home_team_id: Home team ID (default 1)
        away_team_id: Away team ID (default 2)
    """
    game_id = f"{dynasty_id}_{season}_{season_type}_week{week}_{away_team_id}_at_{home_team_id}"

    # Convert date string to timestamp
    dt = datetime.strptime(game_date, "%Y-%m-%d")
    timestamp = int(dt.timestamp() * 1000)

    conn.execute('''
        INSERT INTO games (
            game_id, dynasty_id, season, week, season_type, game_type,
            game_date, home_team_id, away_team_id, home_score, away_score
        ) VALUES (?, ?, ?, ?, ?, 'regular', ?, ?, ?, 24, 17)
    ''', (
        game_id,
        dynasty_id,
        season,
        week,
        season_type,
        timestamp,
        home_team_id,
        away_team_id
    ))
    conn.commit()


# ============================================================================
# TESTS: get_week_for_date() - Basic Functionality
# ============================================================================


def test_get_week_for_date_returns_correct_week_regular_season(week_api, week_tracking_db_path):
    """Test that valid date in regular season returns correct week number."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create games for week 5 of regular season
    create_game_on_date(
        conn, "test_dynasty", 2025, 5, "regular_season",
        "2025-10-12", home_team_id=1, away_team_id=2
    )

    conn.close()

    # Query week for this date
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-10-12",
        season=2025,
        season_type="regular_season"
    )

    assert week == 5


def test_get_week_for_date_returns_correct_week_preseason(week_api, week_tracking_db_path):
    """Test that valid date in preseason returns correct week number."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create games for week 2 of preseason
    create_game_on_date(
        conn, "test_dynasty", 2025, 2, "preseason",
        "2025-08-18", home_team_id=3, away_team_id=4
    )

    conn.close()

    # Query week for this date
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-18",
        season=2025,
        season_type="preseason"
    )

    assert week == 2


def test_get_week_for_date_returns_none_for_no_games(week_api):
    """Test that date with no scheduled games returns None."""
    # Query week for date with no games
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-12-25",
        season=2025,
        season_type="regular_season"
    )

    assert week is None


# ============================================================================
# TESTS: get_week_for_date() - Preseason Weeks
# ============================================================================


def test_get_week_for_date_preseason_week_1(week_api, week_tracking_db_path):
    """Test preseason week 1 tracking."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 1, "preseason",
        "2025-08-10", home_team_id=7, away_team_id=9
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-10",
        season=2025,
        season_type="preseason"
    )

    assert week == 1


def test_get_week_for_date_preseason_week_2(week_api, week_tracking_db_path):
    """Test preseason week 2 tracking."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 2, "preseason",
        "2025-08-17", home_team_id=12, away_team_id=15
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-17",
        season=2025,
        season_type="preseason"
    )

    assert week == 2


def test_get_week_for_date_preseason_week_3(week_api, week_tracking_db_path):
    """Test preseason week 3 tracking."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 3, "preseason",
        "2025-08-24", home_team_id=20, away_team_id=22
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-24",
        season=2025,
        season_type="preseason"
    )

    assert week == 3


# ============================================================================
# TESTS: get_week_for_date() - Regular Season Weeks
# ============================================================================


def test_get_week_for_date_regular_season_week_1(week_api, week_tracking_db_path):
    """Test regular season week 1 tracking."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 1, "regular_season",
        "2025-09-07", home_team_id=5, away_team_id=8
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-09-07",
        season=2025,
        season_type="regular_season"
    )

    assert week == 1


def test_get_week_for_date_regular_season_week_18(week_api, week_tracking_db_path):
    """Test regular season week 18 tracking (final week)."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 18, "regular_season",
        "2026-01-04", home_team_id=14, away_team_id=16
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2026-01-04",
        season=2025,
        season_type="regular_season"
    )

    assert week == 18


def test_get_week_for_date_regular_season_mid_season(week_api, week_tracking_db_path):
    """Test regular season mid-season week tracking (week 10)."""
    conn = sqlite3.connect(week_tracking_db_path)

    create_game_on_date(
        conn, "test_dynasty", 2025, 10, "regular_season",
        "2025-11-16", home_team_id=25, away_team_id=28
    )

    conn.close()

    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-11-16",
        season=2025,
        season_type="regular_season"
    )

    assert week == 10


# ============================================================================
# TESTS: get_week_for_date() - Multiple Games Same Date
# ============================================================================


def test_get_week_for_date_handles_multiple_games_same_date(week_api, week_tracking_db_path):
    """Test that DISTINCT works when multiple games scheduled on same date."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create multiple games on same date (week 7)
    create_game_on_date(
        conn, "test_dynasty", 2025, 7, "regular_season",
        "2025-10-26", home_team_id=1, away_team_id=2
    )
    create_game_on_date(
        conn, "test_dynasty", 2025, 7, "regular_season",
        "2025-10-26", home_team_id=3, away_team_id=4
    )
    create_game_on_date(
        conn, "test_dynasty", 2025, 7, "regular_season",
        "2025-10-26", home_team_id=5, away_team_id=6
    )

    conn.close()

    # Query should return single week value (7), not multiple rows
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-10-26",
        season=2025,
        season_type="regular_season"
    )

    assert week == 7


def test_get_week_for_date_sunday_doubleheader(week_api, week_tracking_db_path):
    """Test week tracking when 16 games scheduled on same Sunday (typical NFL Sunday)."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create 16 games on same Sunday (week 12)
    game_date = "2025-11-23"
    for home_id in range(1, 32, 2):  # 16 home teams
        away_id = home_id + 1
        create_game_on_date(
            conn, "test_dynasty", 2025, 12, "regular_season",
            game_date, home_team_id=home_id, away_team_id=away_id
        )

    conn.close()

    # Should return week 12 despite many games
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date=game_date,
        season=2025,
        season_type="regular_season"
    )

    assert week == 12


# ============================================================================
# TESTS: get_week_for_date() - Dynasty Isolation
# ============================================================================


def test_get_week_for_date_dynasty_isolation(week_api, week_tracking_db_path):
    """Test that dynasties are properly isolated in week queries."""
    conn = sqlite3.connect(week_tracking_db_path)

    # test_dynasty: Week 5 game on Oct 12
    create_game_on_date(
        conn, "test_dynasty", 2025, 5, "regular_season",
        "2025-10-12", home_team_id=1, away_team_id=2
    )

    # other_dynasty: Week 8 game on same date (different week!)
    create_game_on_date(
        conn, "other_dynasty", 2025, 8, "regular_season",
        "2025-10-12", home_team_id=3, away_team_id=4
    )

    conn.close()

    # Query test_dynasty - should get week 5
    test_week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-10-12",
        season=2025,
        season_type="regular_season"
    )
    assert test_week == 5

    # Query other_dynasty - should get week 8
    other_week = week_api.get_week_for_date(
        dynasty_id="other_dynasty",
        game_date="2025-10-12",
        season=2025,
        season_type="regular_season"
    )
    assert other_week == 8


def test_get_week_for_date_different_dynasties_different_seasons(week_api, week_tracking_db_path):
    """Test dynasty isolation across different seasons."""
    conn = sqlite3.connect(week_tracking_db_path)

    # test_dynasty 2025: Week 3 on specific date
    create_game_on_date(
        conn, "test_dynasty", 2025, 3, "regular_season",
        "2025-09-21", home_team_id=7, away_team_id=9
    )

    # other_dynasty 2026: Week 1 on same calendar date (different year)
    create_game_on_date(
        conn, "other_dynasty", 2026, 1, "regular_season",
        "2026-09-21", home_team_id=12, away_team_id=15
    )

    conn.close()

    # Query test_dynasty 2025
    test_week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-09-21",
        season=2025,
        season_type="regular_season"
    )
    assert test_week == 3

    # Query other_dynasty 2026
    other_week = week_api.get_week_for_date(
        dynasty_id="other_dynasty",
        game_date="2026-09-21",
        season=2026,
        season_type="regular_season"
    )
    assert other_week == 1


# ============================================================================
# TESTS: get_week_for_date() - Season Type Filtering
# ============================================================================


def test_get_week_for_date_season_type_filtering(week_api, week_tracking_db_path):
    """Test that season_type parameter correctly filters preseason vs regular season."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create preseason week 3 game on Aug 24
    create_game_on_date(
        conn, "test_dynasty", 2025, 3, "preseason",
        "2025-08-24", home_team_id=1, away_team_id=2
    )

    # Create regular season week 1 game on Sep 7
    create_game_on_date(
        conn, "test_dynasty", 2025, 1, "regular_season",
        "2025-09-07", home_team_id=3, away_team_id=4
    )

    conn.close()

    # Query preseason
    preseason_week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-24",
        season=2025,
        season_type="preseason"
    )
    assert preseason_week == 3

    # Query regular season
    regular_week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-09-07",
        season=2025,
        season_type="regular_season"
    )
    assert regular_week == 1

    # Query wrong season_type for preseason date - should return None
    wrong_week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-08-24",
        season=2025,
        season_type="regular_season"
    )
    assert wrong_week is None


# ============================================================================
# TESTS: get_week_for_date() - Edge Cases
# ============================================================================


def test_get_week_for_date_invalid_dynasty(week_api, week_tracking_db_path):
    """Test querying week for non-existent dynasty returns None."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create game for test_dynasty
    create_game_on_date(
        conn, "test_dynasty", 2025, 5, "regular_season",
        "2025-10-12", home_team_id=1, away_team_id=2
    )

    conn.close()

    # Query with wrong dynasty
    week = week_api.get_week_for_date(
        dynasty_id="nonexistent_dynasty",
        game_date="2025-10-12",
        season=2025,
        season_type="regular_season"
    )

    assert week is None


def test_get_week_for_date_invalid_season(week_api, week_tracking_db_path):
    """Test querying week for wrong season returns None."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create game for 2025 season
    create_game_on_date(
        conn, "test_dynasty", 2025, 5, "regular_season",
        "2025-10-12", home_team_id=1, away_team_id=2
    )

    conn.close()

    # Query with wrong season
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-10-12",
        season=2026,  # Wrong season
        season_type="regular_season"
    )

    assert week is None


def test_get_week_for_date_date_format_validation(week_api, week_tracking_db_path):
    """Test that method handles date format correctly."""
    conn = sqlite3.connect(week_tracking_db_path)

    # Create game on specific date
    create_game_on_date(
        conn, "test_dynasty", 2025, 7, "regular_season",
        "2025-10-26", home_team_id=1, away_team_id=2
    )

    conn.close()

    # Query with exact date format YYYY-MM-DD
    week = week_api.get_week_for_date(
        dynasty_id="test_dynasty",
        game_date="2025-10-26",
        season=2025,
        season_type="regular_season"
    )

    assert week == 7
