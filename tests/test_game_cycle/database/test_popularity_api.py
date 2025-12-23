"""
Tests for PopularityAPI.

Tests database operations for the Player Popularity System.
"""

import pytest
import tempfile
import os
import sqlite3

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.popularity_api import (
    PopularityAPI,
    PopularityTier,
    PopularityTrend,
    PopularityScore,
    PopularityEvent
)


@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables directly with sqlite3
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL DEFAULT 1,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS player_popularity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            popularity_score REAL NOT NULL CHECK(popularity_score BETWEEN 0 AND 100),
            performance_score REAL NOT NULL CHECK(performance_score BETWEEN 0 AND 100),
            visibility_multiplier REAL NOT NULL CHECK(visibility_multiplier BETWEEN 0.5 AND 3.0),
            market_multiplier REAL NOT NULL CHECK(market_multiplier BETWEEN 0.8 AND 2.0),
            week_change REAL,
            trend TEXT CHECK(trend IN ('RISING', 'FALLING', 'STABLE')),
            tier TEXT NOT NULL CHECK(tier IN ('TRANSCENDENT', 'STAR', 'KNOWN', 'ROLE_PLAYER', 'UNKNOWN')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id, season, week)
        );

        CREATE TABLE IF NOT EXISTS player_popularity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            impact REAL NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        );

        CREATE INDEX idx_popularity_dynasty_season_week ON player_popularity(dynasty_id, season, week);
        CREATE INDEX idx_popularity_score ON player_popularity(dynasty_id, season, week, popularity_score DESC);
        CREATE INDEX idx_popularity_tier ON player_popularity(dynasty_id, season, week, tier);
        CREATE INDEX idx_popularity_player ON player_popularity(dynasty_id, player_id, season);
        CREATE INDEX idx_popularity_events_dynasty ON player_popularity_events(dynasty_id);
        CREATE INDEX idx_popularity_events_player ON player_popularity_events(dynasty_id, player_id, season, week);
        CREATE INDEX idx_popularity_events_type ON player_popularity_events(event_type);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def db(db_path):
    """Create GameCycleDatabase instance."""
    database = GameCycleDatabase(db_path)
    yield database
    database.close()


@pytest.fixture
def api(db):
    """Create PopularityAPI instance."""
    return PopularityAPI(db)


@pytest.fixture
def sample_dynasty_id():
    """Sample dynasty ID for testing."""
    return "test_dynasty_123"


def test_save_and_retrieve_popularity_score(api, sample_dynasty_id):
    """Test saving and retrieving a popularity score."""
    # Save score
    score_id = api.save_popularity_score(
        dynasty_id=sample_dynasty_id,
        player_id=1001,
        season=2025,
        week=5,
        popularity_score=85.5,
        performance_score=90.0,
        visibility_multiplier=2.5,
        market_multiplier=1.8,
        week_change=5.2,
        trend="RISING",
        tier="STAR"
    )

    assert score_id > 0

    # Retrieve score
    score = api.get_popularity_score(
        dynasty_id=sample_dynasty_id,
        player_id=1001,
        season=2025,
        week=5
    )

    assert score is not None
    assert score.player_id == 1001
    assert score.season == 2025
    assert score.week == 5
    assert score.popularity_score == 85.5
    assert score.performance_score == 90.0
    assert score.visibility_multiplier == 2.5
    assert score.market_multiplier == 1.8
    assert score.week_change == 5.2
    assert score.trend == "RISING"
    assert score.tier == "STAR"


def test_auto_calculate_tier(api, sample_dynasty_id):
    """Test automatic tier calculation from score."""
    # Save score without explicit tier
    api.save_popularity_score(
        dynasty_id=sample_dynasty_id,
        player_id=2001,
        season=2025,
        week=1,
        popularity_score=95.0,
        performance_score=95.0,
        visibility_multiplier=2.0,
        market_multiplier=1.5
    )

    score = api.get_popularity_score(sample_dynasty_id, 2001, 2025, 1)
    assert score.tier == "TRANSCENDENT"  # 95 should be TRANSCENDENT


def test_get_top_players(api, sample_dynasty_id):
    """Test retrieving top popular players."""
    # Save multiple scores
    players = [
        (1001, 95.0),
        (1002, 85.0),
        (1003, 75.0),
        (1004, 65.0),
        (1005, 55.0),
    ]

    for player_id, score in players:
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=player_id,
            season=2025,
            week=5,
            popularity_score=score,
            performance_score=score,
            visibility_multiplier=1.5,
            market_multiplier=1.2
        )

    # Get top 3
    top_players = api.get_top_players(sample_dynasty_id, 2025, 5, limit=3)

    assert len(top_players) == 3
    assert top_players[0].player_id == 1001  # Highest score
    assert top_players[0].popularity_score == 95.0
    assert top_players[1].player_id == 1002
    assert top_players[2].player_id == 1003


def test_get_popularity_trend(api, sample_dynasty_id):
    """Test retrieving popularity trend over multiple weeks."""
    player_id = 3001
    season = 2025

    # Save scores for 4 weeks
    for week in range(1, 5):
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=player_id,
            season=season,
            week=week,
            popularity_score=70.0 + (week * 5),  # Increasing trend
            performance_score=75.0,
            visibility_multiplier=1.8,
            market_multiplier=1.2
        )

    # Get trend
    trend = api.get_popularity_trend(sample_dynasty_id, player_id, season, weeks=4)

    assert len(trend) == 4
    # Should be in ascending order (oldest to newest)
    assert trend[0].week == 1
    assert trend[1].week == 2
    assert trend[2].week == 3
    assert trend[3].week == 4
    # Verify increasing scores
    assert trend[0].popularity_score == 75.0
    assert trend[3].popularity_score == 90.0


def test_get_players_by_tier(api, sample_dynasty_id):
    """Test filtering players by tier."""
    # Save players in different tiers
    players = [
        (1001, 95.0, "TRANSCENDENT"),
        (1002, 80.0, "STAR"),
        (1003, 60.0, "KNOWN"),
        (1004, 78.0, "STAR"),
    ]

    for player_id, score, tier in players:
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=player_id,
            season=2025,
            week=10,
            popularity_score=score,
            performance_score=score,
            visibility_multiplier=1.5,
            market_multiplier=1.0,
            tier=tier
        )

    # Get STAR tier players
    stars = api.get_players_by_tier(sample_dynasty_id, 2025, 10, "STAR")

    assert len(stars) == 2
    assert all(s.tier == "STAR" for s in stars)
    # Should be sorted by score descending
    assert stars[0].player_id == 1002  # 80.0
    assert stars[1].player_id == 1004  # 78.0


def test_save_and_retrieve_popularity_event(api, sample_dynasty_id):
    """Test saving and retrieving popularity events."""
    # Save event
    event_id = api.save_popularity_event(
        dynasty_id=sample_dynasty_id,
        player_id=4001,
        season=2025,
        week=7,
        event_type="HEADLINE",
        impact=5.5,
        description="Featured in national headline after 4 TD performance"
    )

    assert event_id > 0

    # Retrieve events
    events = api.get_popularity_events(sample_dynasty_id, 4001, 2025, week=7)

    assert len(events) == 1
    assert events[0].player_id == 4001
    assert events[0].event_type == "HEADLINE"
    assert events[0].impact == 5.5
    assert "national headline" in events[0].description


def test_get_weekly_events_summary(api, sample_dynasty_id):
    """Test getting summary of weekly events."""
    # Save multiple events
    events = [
        ("HEADLINE", 5.0),
        ("HEADLINE", 3.0),
        ("AWARD", 10.0),
        ("MILESTONE", 8.0),
        ("INJURY", -5.0),
    ]

    for event_type, impact in events:
        api.save_popularity_event(
            dynasty_id=sample_dynasty_id,
            player_id=5001,
            season=2025,
            week=12,
            event_type=event_type,
            impact=impact
        )

    # Get summary
    summary = api.get_weekly_events_summary(sample_dynasty_id, 2025, 12)

    assert summary["HEADLINE"] == 2
    assert summary["AWARD"] == 1
    assert summary["MILESTONE"] == 1
    assert summary["INJURY"] == 1


def test_clear_player_popularity(api, sample_dynasty_id):
    """Test clearing all popularity data for a player."""
    player_id = 6001

    # Save score and events
    api.save_popularity_score(
        dynasty_id=sample_dynasty_id,
        player_id=player_id,
        season=2025,
        week=5,
        popularity_score=80.0,
        performance_score=80.0,
        visibility_multiplier=1.5,
        market_multiplier=1.2
    )
    api.save_popularity_event(
        dynasty_id=sample_dynasty_id,
        player_id=player_id,
        season=2025,
        week=5,
        event_type="HEADLINE",
        impact=5.0
    )

    # Clear
    counts = api.clear_player_popularity(sample_dynasty_id, player_id)

    assert counts['popularity_scores'] == 1
    assert counts['popularity_events'] == 1

    # Verify cleared
    score = api.get_popularity_score(sample_dynasty_id, player_id, 2025, 5)
    assert score is None


def test_clear_season_popularity(api, sample_dynasty_id):
    """Test clearing all popularity data for a season."""
    # Save multiple players
    for player_id in [7001, 7002, 7003]:
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=player_id,
            season=2025,
            week=10,
            popularity_score=75.0,
            performance_score=75.0,
            visibility_multiplier=1.5,
            market_multiplier=1.0
        )

    # Clear season
    counts = api.clear_season_popularity(sample_dynasty_id, 2025)

    assert counts['popularity_scores'] == 3

    # Verify cleared
    top_players = api.get_top_players(sample_dynasty_id, 2025, 10)
    assert len(top_players) == 0


def test_dynasty_isolation(api):
    """Test that dynasties are properly isolated."""
    # Save to dynasty 1
    api.save_popularity_score(
        dynasty_id="dynasty_1",
        player_id=8001,
        season=2025,
        week=5,
        popularity_score=90.0,
        performance_score=90.0,
        visibility_multiplier=2.0,
        market_multiplier=1.5
    )

    # Save to dynasty 2
    api.save_popularity_score(
        dynasty_id="dynasty_2",
        player_id=8001,
        season=2025,
        week=5,
        popularity_score=50.0,
        performance_score=50.0,
        visibility_multiplier=1.0,
        market_multiplier=1.0
    )

    # Verify isolation
    score_1 = api.get_popularity_score("dynasty_1", 8001, 2025, 5)
    score_2 = api.get_popularity_score("dynasty_2", 8001, 2025, 5)

    assert score_1.popularity_score == 90.0
    assert score_2.popularity_score == 50.0


def test_popularity_tier_from_score():
    """Test PopularityTier.from_score classification."""
    assert PopularityTier.from_score(95) == PopularityTier.TRANSCENDENT
    assert PopularityTier.from_score(90) == PopularityTier.TRANSCENDENT
    assert PopularityTier.from_score(85) == PopularityTier.STAR
    assert PopularityTier.from_score(75) == PopularityTier.STAR
    assert PopularityTier.from_score(65) == PopularityTier.KNOWN
    assert PopularityTier.from_score(50) == PopularityTier.KNOWN
    assert PopularityTier.from_score(35) == PopularityTier.ROLE_PLAYER
    assert PopularityTier.from_score(25) == PopularityTier.ROLE_PLAYER
    assert PopularityTier.from_score(15) == PopularityTier.UNKNOWN
    assert PopularityTier.from_score(0) == PopularityTier.UNKNOWN


def test_validation_ranges(api, sample_dynasty_id):
    """Test that score ranges are validated."""
    # Test invalid popularity_score
    with pytest.raises(ValueError, match="popularity_score must be 0-100"):
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=9001,
            season=2025,
            week=1,
            popularity_score=150.0,  # Invalid
            performance_score=80.0,
            visibility_multiplier=1.5,
            market_multiplier=1.2
        )

    # Test invalid performance_score
    with pytest.raises(ValueError, match="performance_score must be 0-100"):
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=9002,
            season=2025,
            week=1,
            popularity_score=80.0,
            performance_score=-10.0,  # Invalid
            visibility_multiplier=1.5,
            market_multiplier=1.2
        )

    # Test invalid visibility_multiplier
    with pytest.raises(ValueError, match="visibility_multiplier must be 0.5-3.0"):
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=9003,
            season=2025,
            week=1,
            popularity_score=80.0,
            performance_score=80.0,
            visibility_multiplier=5.0,  # Invalid
            market_multiplier=1.2
        )

    # Test invalid market_multiplier
    with pytest.raises(ValueError, match="market_multiplier must be 0.8-2.0"):
        api.save_popularity_score(
            dynasty_id=sample_dynasty_id,
            player_id=9004,
            season=2025,
            week=1,
            popularity_score=80.0,
            performance_score=80.0,
            visibility_multiplier=1.5,
            market_multiplier=3.0  # Invalid
        )
