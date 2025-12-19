"""
Unit tests for RetiredPlayersAPI.

Tests covering retired player tracking and career summary management.
Target: 18 tests covering all API methods and dataclasses.
"""
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.retired_players_api import (
    RetiredPlayersAPI, RetiredPlayer, CareerSummary
)
from src.game_cycle.database.connection import GameCycleDatabase


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    # Create tables matching full_schema.sql
    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS retired_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            retirement_season INTEGER NOT NULL,
            retirement_reason TEXT NOT NULL CHECK(retirement_reason IN (
                'age_decline', 'injury', 'championship', 'contract', 'personal', 'released'
            )),
            final_team_id INTEGER NOT NULL,
            years_played INTEGER NOT NULL,
            age_at_retirement INTEGER NOT NULL,
            one_day_contract_team_id INTEGER,
            hall_of_fame_eligible_season INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        CREATE TABLE IF NOT EXISTS career_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_pick INTEGER,
            seasons_played INTEGER DEFAULT 0,
            games_played INTEGER DEFAULT 0,
            games_started INTEGER DEFAULT 0,
            pass_yards INTEGER DEFAULT 0,
            pass_tds INTEGER DEFAULT 0,
            pass_ints INTEGER DEFAULT 0,
            pass_attempts INTEGER DEFAULT 0,
            pass_completions INTEGER DEFAULT 0,
            rush_yards INTEGER DEFAULT 0,
            rush_tds INTEGER DEFAULT 0,
            rush_attempts INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            rec_yards INTEGER DEFAULT 0,
            rec_tds INTEGER DEFAULT 0,
            targets INTEGER DEFAULT 0,
            tackles INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            passes_defended INTEGER DEFAULT 0,
            fg_made INTEGER DEFAULT 0,
            fg_attempted INTEGER DEFAULT 0,
            xp_made INTEGER DEFAULT 0,
            xp_attempted INTEGER DEFAULT 0,
            pro_bowls INTEGER DEFAULT 0,
            all_pro_first_team INTEGER DEFAULT 0,
            all_pro_second_team INTEGER DEFAULT 0,
            mvp_awards INTEGER DEFAULT 0,
            other_major_awards INTEGER DEFAULT 0,
            super_bowl_wins INTEGER DEFAULT 0,
            super_bowl_mvps INTEGER DEFAULT 0,
            teams_played_for TEXT,
            primary_team_id INTEGER,
            career_approximate_value INTEGER DEFAULT 0,
            hall_of_fame_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        CREATE INDEX IF NOT EXISTS idx_retired_players_dynasty ON retired_players(dynasty_id);
        CREATE INDEX IF NOT EXISTS idx_retired_players_season ON retired_players(dynasty_id, retirement_season);
        CREATE INDEX IF NOT EXISTS idx_retired_players_team ON retired_players(dynasty_id, final_team_id);
        CREATE INDEX IF NOT EXISTS idx_career_summaries_dynasty ON career_summaries(dynasty_id);
        CREATE INDEX IF NOT EXISTS idx_career_summaries_player ON career_summaries(dynasty_id, player_id);
        CREATE INDEX IF NOT EXISTS idx_career_summaries_hof ON career_summaries(dynasty_id, hall_of_fame_score DESC);

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield temp_path

    # Cleanup
    for suffix in ['', '-wal', '-shm']:
        try:
            os.unlink(temp_path + suffix)
        except FileNotFoundError:
            pass


@pytest.fixture
def db(db_path):
    """Create a GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create a RetiredPlayersAPI instance."""
    return RetiredPlayersAPI(db)


@pytest.fixture
def dynasty_id():
    """Standard test dynasty ID."""
    return 'test-dynasty'


@pytest.fixture
def sample_retired_player():
    """Sample retired player for testing."""
    return RetiredPlayer(
        player_id=100,
        retirement_season=2025,
        retirement_reason='age_decline',
        final_team_id=1,
        years_played=15,
        age_at_retirement=38
    )


@pytest.fixture
def sample_career_summary():
    """Sample career summary for testing."""
    return CareerSummary(
        player_id=100,
        full_name='John Smith',
        position='QB',
        games_played=240,
        pass_yards=55000,
        pass_tds=400,
        pro_bowls=8,
        all_pro_first_team=3,
        mvp_awards=2,
        super_bowl_wins=2,
        hall_of_fame_score=85,
        teams_played_for=[1, 5]
    )


# ============================================
# Fixture Tests
# ============================================

class TestFixtures:
    """Tests for fixture setup and table creation."""

    def test_fixture_creates_tables(self, api, db):
        """Database should have retired_players and career_summaries tables."""
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        assert 'retired_players' in tables
        assert 'career_summaries' in tables
        assert 'dynasties' in tables

    def test_dynasty_isolation(self, api, db, dynasty_id, sample_retired_player):
        """Different dynasties should not see each other's data."""
        # Create another dynasty
        db.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES (?, ?, ?)",
            ('other-dynasty', 'Other Dynasty', 2)
        )

        # Insert retired player in test dynasty
        api.insert_retired_player(dynasty_id, sample_retired_player)

        # Insert in other dynasty
        other_player = RetiredPlayer(
            player_id=200,
            retirement_season=2025,
            retirement_reason='injury',
            final_team_id=2,
            years_played=8,
            age_at_retirement=30
        )
        api.insert_retired_player('other-dynasty', other_player)

        # Verify isolation
        player1 = api.get_retired_player(dynasty_id, 100)
        player2 = api.get_retired_player('other-dynasty', 200)
        player_cross = api.get_retired_player(dynasty_id, 200)

        assert player1 is not None
        assert player1['player_id'] == 100
        assert player2 is not None
        assert player2['player_id'] == 200
        assert player_cross is None


# ============================================
# Retired Players CRUD Tests
# ============================================

class TestRetiredPlayersCRUD:
    """Tests for retired player CRUD operations."""

    def test_insert_retired_player(self, api, dynasty_id, sample_retired_player):
        """insert_retired_player should store player data."""
        result = api.insert_retired_player(dynasty_id, sample_retired_player)
        assert result > 0  # Returns row ID

        # Verify stored
        player = api.get_retired_player(dynasty_id, 100)
        assert player is not None
        assert player['player_id'] == 100
        assert player['retirement_season'] == 2025
        assert player['retirement_reason'] == 'age_decline'
        assert player['final_team_id'] == 1
        assert player['years_played'] == 15
        assert player['age_at_retirement'] == 38

    def test_insert_retired_player_calculates_hof_eligible(self, api, dynasty_id, sample_retired_player):
        """insert_retired_player should calculate HOF eligible year (retirement + 5)."""
        api.insert_retired_player(dynasty_id, sample_retired_player)

        player = api.get_retired_player(dynasty_id, 100)
        assert player['hall_of_fame_eligible_season'] == 2030  # 2025 + 5

    def test_insert_duplicate_player_fails(self, api, dynasty_id, sample_retired_player):
        """Inserting same player twice should fail (UNIQUE constraint)."""
        api.insert_retired_player(dynasty_id, sample_retired_player)

        # Attempt duplicate insert
        with pytest.raises(sqlite3.IntegrityError):
            api.insert_retired_player(dynasty_id, sample_retired_player)

    def test_get_retired_player_exists(self, api, dynasty_id, sample_retired_player):
        """get_retired_player should return player if exists."""
        api.insert_retired_player(dynasty_id, sample_retired_player)

        player = api.get_retired_player(dynasty_id, 100)
        assert player is not None
        assert player['player_id'] == 100

    def test_get_retired_player_not_found(self, api, dynasty_id):
        """get_retired_player should return None for non-existent player."""
        player = api.get_retired_player(dynasty_id, 999)
        assert player is None

    def test_get_retirements_by_season(self, api, dynasty_id):
        """get_retirements_by_season should filter by retirement season."""
        player1 = RetiredPlayer(100, 2025, 'age_decline', 1, 15, 38)
        player2 = RetiredPlayer(101, 2025, 'injury', 2, 8, 30)
        player3 = RetiredPlayer(102, 2026, 'age_decline', 3, 12, 35)

        api.insert_retired_player(dynasty_id, player1)
        api.insert_retired_player(dynasty_id, player2)
        api.insert_retired_player(dynasty_id, player3)

        players_2025 = api.get_retirements_by_season(dynasty_id, 2025)
        assert len(players_2025) == 2
        player_ids = {p['player_id'] for p in players_2025}
        assert 100 in player_ids
        assert 101 in player_ids
        assert 102 not in player_ids

    def test_get_retirements_by_team(self, api, dynasty_id):
        """get_retirements_by_team should filter by final team."""
        player1 = RetiredPlayer(100, 2025, 'age_decline', 1, 15, 38)
        player2 = RetiredPlayer(101, 2025, 'injury', 1, 8, 30)
        player3 = RetiredPlayer(102, 2025, 'age_decline', 2, 12, 35)

        api.insert_retired_player(dynasty_id, player1)
        api.insert_retired_player(dynasty_id, player2)
        api.insert_retired_player(dynasty_id, player3)

        team1_retirements = api.get_retirements_by_team(dynasty_id, 1)
        assert len(team1_retirements) == 2
        player_ids = {p['player_id'] for p in team1_retirements}
        assert 100 in player_ids
        assert 101 in player_ids
        assert 102 not in player_ids

    def test_is_player_retired(self, api, dynasty_id, sample_retired_player):
        """is_player_retired should return True/False correctly."""
        api.insert_retired_player(dynasty_id, sample_retired_player)

        assert api.is_player_retired(dynasty_id, 100) is True
        assert api.is_player_retired(dynasty_id, 999) is False


# ============================================
# Career Summaries CRUD Tests
# ============================================

class TestCareerSummariesCRUD:
    """Tests for career summary CRUD operations."""

    def test_insert_career_summary(self, api, dynasty_id, sample_career_summary):
        """insert_career_summary should store career data."""
        result = api.insert_career_summary(dynasty_id, sample_career_summary)
        assert result > 0

        summary = api.get_career_summary(dynasty_id, 100)
        assert summary is not None
        assert summary['player_id'] == 100
        assert summary['full_name'] == 'John Smith'
        assert summary['position'] == 'QB'
        assert summary['pass_yards'] == 55000
        assert summary['pass_tds'] == 400

    def test_insert_career_summary_with_json_teams(self, api, dynasty_id, sample_career_summary):
        """teams_played_for should serialize and deserialize correctly."""
        api.insert_career_summary(dynasty_id, sample_career_summary)

        summary = api.get_career_summary(dynasty_id, 100)
        assert summary['teams_played_for'] == [1, 5]

    def test_get_career_summary(self, api, dynasty_id, sample_career_summary):
        """get_career_summary should return full career data."""
        api.insert_career_summary(dynasty_id, sample_career_summary)

        summary = api.get_career_summary(dynasty_id, 100)
        assert summary is not None
        assert summary['pro_bowls'] == 8
        assert summary['all_pro_first_team'] == 3
        assert summary['mvp_awards'] == 2
        assert summary['super_bowl_wins'] == 2
        assert summary['hall_of_fame_score'] == 85

    def test_get_top_careers_by_position(self, api, dynasty_id):
        """get_top_careers_by_position should return ranked by HOF score."""
        # Insert QBs with different HOF scores
        qb1 = CareerSummary(100, 'Tom Brady', 'QB', hall_of_fame_score=95)
        qb2 = CareerSummary(101, 'Joe Montana', 'QB', hall_of_fame_score=92)
        qb3 = CareerSummary(102, 'Dan Marino', 'QB', hall_of_fame_score=88)
        wr1 = CareerSummary(200, 'Jerry Rice', 'WR', hall_of_fame_score=98)

        api.insert_career_summary(dynasty_id, qb1)
        api.insert_career_summary(dynasty_id, qb2)
        api.insert_career_summary(dynasty_id, qb3)
        api.insert_career_summary(dynasty_id, wr1)

        top_qbs = api.get_top_careers_by_position(dynasty_id, 'QB', limit=10)
        assert len(top_qbs) == 3
        assert top_qbs[0]['player_id'] == 100  # Brady (95)
        assert top_qbs[1]['player_id'] == 101  # Montana (92)
        assert top_qbs[2]['player_id'] == 102  # Marino (88)

    def test_get_hof_candidates(self, api, dynasty_id):
        """get_hof_candidates should filter by minimum HOF score."""
        low_score = CareerSummary(100, 'Average Joe', 'QB', hall_of_fame_score=30)
        mid_score = CareerSummary(101, 'Good Player', 'RB', hall_of_fame_score=55)
        high_score = CareerSummary(102, 'Great Player', 'WR', hall_of_fame_score=85)

        api.insert_career_summary(dynasty_id, low_score)
        api.insert_career_summary(dynasty_id, mid_score)
        api.insert_career_summary(dynasty_id, high_score)

        candidates = api.get_hof_candidates(dynasty_id, min_score=50)
        assert len(candidates) == 2
        player_ids = {c['player_id'] for c in candidates}
        assert 101 in player_ids
        assert 102 in player_ids
        assert 100 not in player_ids

    def test_update_hof_score(self, api, dynasty_id, sample_career_summary):
        """update_hof_score should update the score."""
        api.insert_career_summary(dynasty_id, sample_career_summary)

        assert api.update_hof_score(dynasty_id, 100, 95) is True

        summary = api.get_career_summary(dynasty_id, 100)
        assert summary['hall_of_fame_score'] == 95


# ============================================
# HOF Eligibility Tests
# ============================================

class TestHOFEligibility:
    """Tests for Hall of Fame eligibility features."""

    def test_get_hof_eligible_players(self, api, dynasty_id):
        """get_hof_eligible_players should return players eligible in given season."""
        # Player retiring in 2025 is eligible in 2030
        player1 = RetiredPlayer(100, 2025, 'age_decline', 1, 15, 38)
        # Player retiring in 2024 is eligible in 2029
        player2 = RetiredPlayer(101, 2024, 'championship', 2, 12, 35)

        api.insert_retired_player(dynasty_id, player1)
        api.insert_retired_player(dynasty_id, player2)

        eligible_2030 = api.get_hof_eligible_players(dynasty_id, 2030)
        assert len(eligible_2030) == 1
        assert eligible_2030[0]['player_id'] == 100

        eligible_2029 = api.get_hof_eligible_players(dynasty_id, 2029)
        assert len(eligible_2029) == 1
        assert eligible_2029[0]['player_id'] == 101

    def test_update_one_day_contract(self, api, dynasty_id, sample_retired_player):
        """update_one_day_contract should set ceremony team."""
        api.insert_retired_player(dynasty_id, sample_retired_player)

        assert api.update_one_day_contract(dynasty_id, 100, 5) is True

        player = api.get_retired_player(dynasty_id, 100)
        assert player['one_day_contract_team_id'] == 5
