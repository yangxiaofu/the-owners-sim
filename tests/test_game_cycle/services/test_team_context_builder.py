"""
Tests for TeamContextBuilder service.

Verifies team context building with record, rankings, playoff position,
season phase, recent activity, and streaks.
"""

import pytest
import sqlite3
from datetime import datetime, timedelta

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.standings_api import StandingsAPI
from src.game_cycle.services.team_context_builder import (
    TeamContextBuilder,
    TeamContext,
    PlayoffPosition,
    SeasonPhase
)


@pytest.fixture
def db_conn(tmp_path):
    """Create test database with schema."""
    db_path = tmp_path / "test_team_context.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Create minimal schema
    conn.executescript("""
        CREATE TABLE standings (
            dynasty_id TEXT,
            team_id INTEGER,
            season INTEGER,
            season_type TEXT DEFAULT 'regular_season',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            division_ties INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            conference_ties INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            home_ties INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            away_ties INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            point_differential INTEGER DEFAULT 0,
            made_playoffs BOOLEAN DEFAULT 0,
            made_wild_card BOOLEAN DEFAULT 0,
            won_wild_card BOOLEAN DEFAULT 0,
            won_division_round BOOLEAN DEFAULT 0,
            won_conference BOOLEAN DEFAULT 0,
            won_super_bowl BOOLEAN DEFAULT 0,
            PRIMARY KEY (dynasty_id, team_id, season, season_type)
        );

        CREATE TABLE box_scores (
            dynasty_id TEXT,
            season INTEGER,
            week INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            game_status TEXT DEFAULT 'final',
            PRIMARY KEY (dynasty_id, season, week, home_team_id, away_team_id)
        );

        CREATE TABLE player_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT,
            season INTEGER,
            transaction_type TEXT,
            player_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transaction_date TEXT,
            details TEXT
        );
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def game_cycle_db(db_conn, tmp_path):
    """Create GameCycleDatabase wrapper."""
    db_path = tmp_path / "test_team_context.db"
    return GameCycleDatabase(str(db_path))


@pytest.fixture
def standings_api(game_cycle_db):
    """Create StandingsAPI."""
    return StandingsAPI(game_cycle_db)


@pytest.fixture
def context_builder(game_cycle_db):
    """Create TeamContextBuilder."""
    return TeamContextBuilder(game_cycle_db)


def create_division_standings(db_conn, dynasty_id, season, division_teams):
    """
    Create standings for a division.

    Args:
        db_conn: Database connection
        dynasty_id: Dynasty ID
        season: Season year
        division_teams: List of (team_id, wins, losses) tuples
    """
    for team_id, wins, losses in division_teams:
        db_conn.execute("""
            INSERT INTO standings (
                dynasty_id, team_id, season, season_type,
                wins, losses, ties,
                points_for, points_against,
                point_differential
            ) VALUES (?, ?, ?, 'regular_season', ?, ?, 0, ?, ?, ?)
        """, (
            dynasty_id, team_id, season,
            wins, losses,
            wins * 24 + 100,  # points_for
            losses * 24 + 100,  # points_against
            (wins - losses) * 24  # point_differential
        ))
    db_conn.commit()


# ============================================================================
# Basic Context Building
# ============================================================================

def test_build_basic_context(context_builder, db_conn):
    """Test building basic team context."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22  # Detroit Lions

    # Create standings for Lions
    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 10, 4, 0, 350, 280, 70)
    """, (dynasty_id, team_id, season))
    db_conn.commit()

    # Build context
    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=10
    )

    assert isinstance(context, TeamContext)
    assert context.team_id == team_id
    assert context.season == season
    assert context.week == 10
    assert context.wins == 10
    assert context.losses == 4
    assert context.ties == 0
    assert context.win_pct == pytest.approx(0.714, rel=0.01)


def test_context_record_string(context_builder, db_conn):
    """Test record string formatting."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 8, 7, 1, 300, 290, 10)
    """, (dynasty_id, team_id, season))
    db_conn.commit()

    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=16
    )

    assert context.get_record_string() == "8-7-1"
    assert context.is_winning_record() is False  # 8.5 / 16 = 0.531, but with tie it's borderline


# ============================================================================
# Division Rankings
# ============================================================================

def test_division_ranking(context_builder, db_conn):
    """Test division rank calculation."""
    dynasty_id = "test_dynasty"
    season = 2025

    # NFC North standings (team_ids: 21-24)
    # Bears, Lions, Packers, Vikings
    division_teams = [
        (22, 12, 2),  # Lions - 1st
        (23, 10, 4),  # Packers - 2nd
        (24, 8, 6),   # Vikings - 3rd
        (21, 5, 9)    # Bears - 4th
    ]
    create_division_standings(db_conn, dynasty_id, season, division_teams)

    # Build context for Lions (should be rank 1)
    context_lions = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=22,
        week=14
    )
    assert context_lions.division_rank == 1

    # Build context for Packers (should be rank 2)
    context_packers = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=23,
        week=14
    )
    assert context_packers.division_rank == 2


# ============================================================================
# Playoff Position
# ============================================================================

def test_playoff_position_early_season(context_builder, db_conn):
    """Test playoff position in early season (week 1-6)."""
    dynasty_id = "test_dynasty"
    season = 2025

    # Create standings for a division leader
    create_division_standings(db_conn, dynasty_id, season, [
        (22, 4, 1),  # Lions - 1st
        (23, 3, 2),  # Packers - 2nd
    ])

    # Week 5 - division leader should be LEADER
    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=22,
        week=5
    )
    assert context.playoff_position == PlayoffPosition.LEADER


def test_playoff_position_late_season_clinched(context_builder, db_conn):
    """Test playoff position late season with clinch."""
    dynasty_id = "test_dynasty"
    season = 2025

    # Create standings for division leader with dominant record
    create_division_standings(db_conn, dynasty_id, season, [
        (22, 13, 1),  # Lions - dominant
        (23, 8, 6),
    ])

    # Week 15 - should be CLINCHED (12+ wins, division leader)
    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=22,
        week=15
    )
    assert context.playoff_position == PlayoffPosition.CLINCHED


# ============================================================================
# Season Phase
# ============================================================================

def test_season_phase_determination(context_builder, db_conn):
    """Test season phase calculation."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    # Create standings
    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 8, 8, 0, 300, 300, 0)
    """, (dynasty_id, team_id, season))
    db_conn.commit()

    # Early season (week 3)
    context_early = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=3
    )
    assert context_early.season_phase == SeasonPhase.EARLY

    # Mid season (week 10)
    context_mid = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=10
    )
    assert context_mid.season_phase == SeasonPhase.MID

    # Late season (week 16)
    context_late = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=16
    )
    assert context_late.season_phase == SeasonPhase.LATE

    # Playoffs (week = None)
    context_playoffs = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=None
    )
    assert context_playoffs.season_phase == SeasonPhase.PLAYOFFS


# ============================================================================
# Recent Activity
# ============================================================================

def test_recent_activity_trades(context_builder, db_conn):
    """Test recent trade activity."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    # Create standings
    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 8, 8, 0, 300, 300, 0)
    """, (dynasty_id, team_id, season))

    # Add recent trade (within 2 weeks)
    recent_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    db_conn.execute("""
        INSERT INTO player_transactions (
            dynasty_id, season, transaction_type,
            player_id, first_name, last_name, position,
            from_team_id, to_team_id, transaction_date
        ) VALUES (?, ?, 'TRADE', 12345, 'Test', 'Player', 'WR', ?, 23, ?)
    """, (dynasty_id, season, team_id, recent_date))
    db_conn.commit()

    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=10
    )

    assert len(context.recent_trades) == 1
    assert context.recent_trades[0]['type'] == 'TRADE'
    assert context.recent_trades[0]['player_name'] == 'Test Player'
    assert context.has_recent_activity() is True


# ============================================================================
# Streak Calculation
# ============================================================================

def test_win_streak(context_builder, db_conn):
    """Test win streak calculation."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    # Create standings
    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 6, 2, 0, 240, 160, 80)
    """, (dynasty_id, team_id, season))

    # Create 3-game win streak (weeks 6, 7, 8 - most recent)
    for week, home_score, away_score in [
        (6, 24, 20),  # Win
        (7, 27, 17),  # Win
        (8, 31, 21)   # Win (most recent)
    ]:
        db_conn.execute("""
            INSERT INTO box_scores (
                dynasty_id, season, week,
                home_team_id, away_team_id,
                home_score, away_score,
                game_status
            ) VALUES (?, ?, ?, ?, 23, ?, ?, 'final')
        """, (dynasty_id, season, week, team_id, home_score, away_score))
    db_conn.commit()

    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=8
    )

    assert context.current_streak == 3
    assert context.streak_type == 'W'
    assert context.get_streak_string() == 'W3'


def test_loss_streak(context_builder, db_conn):
    """Test loss streak calculation."""
    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    # Create standings
    db_conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 2, 4, 0, 120, 180, -60)
    """, (dynasty_id, team_id, season))

    # Create 2-game loss streak
    for week, home_score, away_score in [
        (5, 17, 24),  # Loss
        (6, 14, 28)   # Loss (most recent)
    ]:
        db_conn.execute("""
            INSERT INTO box_scores (
                dynasty_id, season, week,
                home_team_id, away_team_id,
                home_score, away_score,
                game_status
            ) VALUES (?, ?, ?, ?, 23, ?, ?, 'final')
        """, (dynasty_id, season, week, team_id, home_score, away_score))
    db_conn.commit()

    context = context_builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=6
    )

    assert context.current_streak == 2
    assert context.streak_type == 'L'
    assert context.get_streak_string() == 'L2'


# ============================================================================
# Error Handling
# ============================================================================

def test_build_context_missing_standings(context_builder):
    """Test error when standings not found."""
    with pytest.raises(ValueError, match="No standings found"):
        context_builder.build_context(
            dynasty_id="nonexistent",
            season=2025,
            team_id=22,
            week=10
        )
