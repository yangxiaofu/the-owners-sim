"""
Test fixtures for awards package.

Provides mock player data, grades, and team standings for testing
eligibility and award criteria.
"""

import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.services.awards.models import (
    AwardType,
    PlayerCandidate,
    AwardScore,
    EligibilityResult,
)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def season():
    """Standard test season."""
    return 2025


@pytest.fixture
def db_path():
    """Create a temporary database with required schema for awards testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        -- Dynasties table
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Players table with years_pro for rookie detection
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            number INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            positions TEXT NOT NULL,
            attributes TEXT NOT NULL DEFAULT '{}',
            status TEXT DEFAULT 'active',
            years_pro INTEGER DEFAULT 0,
            UNIQUE(dynasty_id, player_id)
        );

        -- Standings table
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            season_type TEXT NOT NULL DEFAULT 'regular_season',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            UNIQUE(dynasty_id, season, team_id, season_type)
        );

        -- Playoff bracket for conference champions
        CREATE TABLE IF NOT EXISTS playoff_bracket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            round_name TEXT NOT NULL,
            conference TEXT NOT NULL,
            game_number INTEGER NOT NULL,
            higher_seed INTEGER,
            lower_seed INTEGER,
            winner INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            UNIQUE(dynasty_id, season, round_name, conference, game_number)
        );

        -- Player season grades (from AnalyticsAPI)
        CREATE TABLE IF NOT EXISTS player_season_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT NOT NULL,
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
            total_snaps INTEGER DEFAULT 0,
            games_graded INTEGER DEFAULT 0,
            total_plays_graded INTEGER DEFAULT 0,
            positive_play_rate REAL,
            epa_total REAL DEFAULT 0.0,
            epa_per_play REAL,
            position_rank INTEGER,
            overall_rank INTEGER,
            UNIQUE(dynasty_id, season, player_id)
        );

        -- Player game stats (simplified for testing)
        CREATE TABLE IF NOT EXISTS player_game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            game_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            position TEXT,
            passing_yards INTEGER DEFAULT 0,
            passing_completions INTEGER DEFAULT 0,
            passing_attempts INTEGER DEFAULT 0,
            passing_touchdowns INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_attempts INTEGER DEFAULT 0,
            rushing_touchdowns INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            targets INTEGER DEFAULT 0,
            receiving_touchdowns INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            tackles_solo INTEGER DEFAULT 0,
            tackles_assist INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0.0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            UNIQUE(dynasty_id, game_id, player_id)
        );

        -- Insert test dynasty
        INSERT INTO dynasties (dynasty_id, name, team_id)
        VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def mock_elite_qb():
    """Elite QB candidate - MVP-caliber stats."""
    return PlayerCandidate(
        player_id=100,
        player_name="Patrick Mahomes",
        team_id=1,
        position='QB',
        season=2025,
        games_played=17,
        passing_yards=5000,
        passing_tds=40,
        passing_interceptions=10,
        passer_rating=110.5,
        rushing_yards=300,
        rushing_tds=2,
        overall_grade=95.0,
        position_grade=94.0,
        position_rank=1,
        overall_rank=1,
        epa_total=180.0,
        total_snaps=1100,
        team_wins=14,
        team_losses=3,
        win_percentage=0.824,
        playoff_seed=1,
        is_division_winner=True,
        is_conference_champion=True,
        years_pro=7,
    )


@pytest.fixture
def mock_elite_rb():
    """Elite RB candidate - OPOY-caliber stats."""
    return PlayerCandidate(
        player_id=101,
        player_name="Derrick Henry",
        team_id=2,
        position='RB',
        season=2025,
        games_played=17,
        rushing_yards=1800,
        rushing_tds=15,
        receiving_yards=400,
        receiving_tds=3,
        receptions=35,
        overall_grade=92.0,
        position_grade=93.0,
        position_rank=1,
        overall_rank=5,
        epa_total=120.0,
        total_snaps=800,
        team_wins=12,
        team_losses=5,
        win_percentage=0.706,
        playoff_seed=3,
        is_division_winner=True,
        years_pro=8,
    )


@pytest.fixture
def mock_elite_edge():
    """Elite EDGE rusher - DPOY-caliber stats."""
    return PlayerCandidate(
        player_id=102,
        player_name="Myles Garrett",
        team_id=3,
        position='EDGE',
        season=2025,
        games_played=17,
        sacks=16.0,
        tackles_total=55,
        forced_fumbles=4,
        overall_grade=94.0,
        position_grade=95.0,
        position_rank=1,
        overall_rank=2,
        epa_total=80.0,
        total_snaps=850,
        team_wins=10,
        team_losses=7,
        win_percentage=0.588,
        playoff_seed=5,
        years_pro=7,
    )


@pytest.fixture
def mock_rookie_qb():
    """Rookie QB - OROY candidate."""
    return PlayerCandidate(
        player_id=103,
        player_name="Caleb Williams",
        team_id=4,
        position='QB',
        season=2025,
        games_played=17,
        passing_yards=3800,
        passing_tds=28,
        passing_interceptions=12,
        passer_rating=92.5,
        rushing_yards=400,
        rushing_tds=5,
        overall_grade=82.0,
        position_grade=80.0,
        position_rank=10,
        overall_rank=25,
        epa_total=65.0,
        total_snaps=1050,
        team_wins=9,
        team_losses=8,
        win_percentage=0.529,
        years_pro=0,  # ROOKIE
    )


@pytest.fixture
def mock_rookie_cb():
    """Rookie CB - DROY candidate."""
    return PlayerCandidate(
        player_id=104,
        player_name="Quinyon Mitchell",
        team_id=5,
        position='CB',
        season=2025,
        games_played=17,
        interceptions=5,
        tackles_total=60,
        overall_grade=85.0,
        position_grade=86.0,
        position_rank=5,
        overall_rank=15,
        epa_total=45.0,
        total_snaps=900,
        team_wins=11,
        team_losses=6,
        win_percentage=0.647,
        playoff_seed=4,
        years_pro=0,  # ROOKIE
    )


@pytest.fixture
def mock_comeback_player():
    """Comeback player - CPOY candidate (missed previous season with injury)."""
    return PlayerCandidate(
        player_id=105,
        player_name="Joe Burrow",
        team_id=6,
        position='QB',
        season=2025,
        games_played=17,
        passing_yards=4500,
        passing_tds=35,
        passing_interceptions=8,
        passer_rating=105.0,
        overall_grade=90.0,
        position_grade=89.0,
        position_rank=3,
        overall_rank=3,
        epa_total=150.0,
        total_snaps=1080,
        team_wins=13,
        team_losses=4,
        win_percentage=0.765,
        playoff_seed=2,
        is_division_winner=True,
        years_pro=5,
        previous_season_grade=72.0,  # Lower grade last year
        games_missed_previous=10,  # Missed most of last season
    )


@pytest.fixture
def mock_below_minimum_games():
    """Player who didn't play enough games to qualify."""
    return PlayerCandidate(
        player_id=106,
        player_name="Injured Player",
        team_id=7,
        position='WR',
        season=2025,
        games_played=8,  # Below 12-game minimum
        receiving_yards=600,
        receiving_tds=5,
        overall_grade=78.0,
        position_grade=77.0,
        total_snaps=400,
        years_pro=3,
    )


@pytest.fixture
def mock_average_qb():
    """Average QB for comparison."""
    return PlayerCandidate(
        player_id=107,
        player_name="Average QB",
        team_id=8,
        position='QB',
        season=2025,
        games_played=17,
        passing_yards=3500,
        passing_tds=22,
        passing_interceptions=14,
        passer_rating=88.0,
        overall_grade=70.0,
        position_grade=68.0,
        position_rank=18,
        overall_rank=75,
        epa_total=30.0,
        total_snaps=1000,
        team_wins=7,
        team_losses=10,
        win_percentage=0.412,
        years_pro=6,
    )


@pytest.fixture
def mock_candidates_list(
    mock_elite_qb,
    mock_elite_rb,
    mock_elite_edge,
    mock_rookie_qb,
    mock_rookie_cb,
    mock_comeback_player,
    mock_average_qb,
):
    """List of all mock candidates for testing."""
    return [
        mock_elite_qb,
        mock_elite_rb,
        mock_elite_edge,
        mock_rookie_qb,
        mock_rookie_cb,
        mock_comeback_player,
        mock_average_qb,
    ]


@pytest.fixture
def mock_offensive_candidates(mock_elite_qb, mock_elite_rb, mock_rookie_qb, mock_comeback_player, mock_average_qb):
    """Offensive candidates only."""
    return [
        mock_elite_qb,
        mock_elite_rb,
        mock_rookie_qb,
        mock_comeback_player,
        mock_average_qb,
    ]


@pytest.fixture
def mock_defensive_candidates(mock_elite_edge, mock_rookie_cb):
    """Defensive candidates only."""
    return [mock_elite_edge, mock_rookie_cb]


@pytest.fixture
def mock_rookie_candidates(mock_rookie_qb, mock_rookie_cb):
    """Rookie candidates only."""
    return [mock_rookie_qb, mock_rookie_cb]
