"""
Unit tests for HOFAPI.

Tests covering Hall of Fame inductee and voting history operations.
Target: 15+ tests covering all API methods.
"""
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.database.hof_api import HOFAPI, HOFInductee, HOFVotingResult
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

        -- Hall of Fame inductees
        CREATE TABLE IF NOT EXISTS hall_of_fame (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            induction_season INTEGER NOT NULL,
            years_on_ballot INTEGER NOT NULL DEFAULT 1,
            is_first_ballot INTEGER NOT NULL DEFAULT 0,
            vote_percentage REAL NOT NULL,
            player_name TEXT NOT NULL,
            primary_position TEXT NOT NULL,
            career_seasons INTEGER NOT NULL,
            final_team_id INTEGER NOT NULL,
            teams_played_for TEXT NOT NULL,
            super_bowl_wins INTEGER NOT NULL DEFAULT 0,
            mvp_awards INTEGER NOT NULL DEFAULT 0,
            all_pro_first_team INTEGER NOT NULL DEFAULT 0,
            all_pro_second_team INTEGER NOT NULL DEFAULT 0,
            pro_bowl_selections INTEGER NOT NULL DEFAULT 0,
            career_stats TEXT NOT NULL,
            hof_score INTEGER NOT NULL,
            presenter_name TEXT,
            presenter_relationship TEXT,
            speech_highlights TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        CREATE INDEX IF NOT EXISTS idx_hof_dynasty ON hall_of_fame(dynasty_id);
        CREATE INDEX IF NOT EXISTS idx_hof_induction_season ON hall_of_fame(dynasty_id, induction_season);
        CREATE INDEX IF NOT EXISTS idx_hof_position ON hall_of_fame(dynasty_id, primary_position);

        -- HOF voting history
        CREATE TABLE IF NOT EXISTS hof_voting_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            voting_season INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            primary_position TEXT NOT NULL,
            retirement_season INTEGER NOT NULL,
            years_on_ballot INTEGER NOT NULL,
            vote_percentage REAL NOT NULL,
            votes_received INTEGER NOT NULL,
            total_voters INTEGER NOT NULL,
            was_inducted INTEGER NOT NULL DEFAULT 0,
            is_first_ballot INTEGER NOT NULL DEFAULT 0,
            removed_from_ballot INTEGER NOT NULL DEFAULT 0,
            hof_score INTEGER NOT NULL,
            score_breakdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, voting_season, player_id)
        );

        CREATE INDEX IF NOT EXISTS idx_hof_voting_dynasty ON hof_voting_history(dynasty_id);
        CREATE INDEX IF NOT EXISTS idx_hof_voting_season ON hof_voting_history(dynasty_id, voting_season);
        CREATE INDEX IF NOT EXISTS idx_hof_voting_player ON hof_voting_history(dynasty_id, player_id);

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test-dynasty', 'Test Dynasty', 1);
        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other-dynasty', 'Other Dynasty', 2);
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
    """Create a HOFAPI instance for test-dynasty."""
    return HOFAPI(db, 'test-dynasty')


@pytest.fixture
def other_api(db):
    """Create a HOFAPI instance for other-dynasty."""
    return HOFAPI(db, 'other-dynasty')


@pytest.fixture
def sample_player_data():
    """Sample player data for inductee testing."""
    return {
        'player_name': 'Tom Brady',
        'primary_position': 'QB',
        'career_seasons': 23,
        'final_team_id': 1,
        'teams_played_for': ['Patriots', 'Buccaneers'],
        'super_bowl_wins': 7,
        'mvp_awards': 3,
        'all_pro_first_team': 3,
        'all_pro_second_team': 2,
        'pro_bowl_selections': 15,
        'career_stats': {'passing_yards': 89000, 'passing_tds': 649},
        'hof_score': 95,
    }


@pytest.fixture
def sample_ceremony_data():
    """Sample ceremony data for inductee testing."""
    return {
        'presenter_name': 'Bill Belichick',
        'presenter_relationship': 'Former Coach',
        'speech_highlights': {
            'opening': 'Standing here in Canton...',
            'thank_yous': 'To my teammates...',
            'closing': 'God bless you all.',
        }
    }


# ============================================
# Inductee Tests
# ============================================

class TestAddAndGetInductee:
    """Tests for add_inductee and get_inductee methods."""

    def test_add_and_get_inductee(self, api, sample_player_data, sample_ceremony_data):
        """Verify inductee can be added and retrieved."""
        row_id = api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=sample_player_data,
            ceremony_data=sample_ceremony_data
        )

        assert row_id > 0

        inductee = api.get_inductee(12)
        assert inductee is not None
        assert inductee['player_name'] == 'Tom Brady'
        assert inductee['primary_position'] == 'QB'
        assert inductee['induction_season'] == 2030
        assert inductee['is_first_ballot'] is True
        assert inductee['vote_percentage'] == 0.97
        assert inductee['super_bowl_wins'] == 7
        assert inductee['mvp_awards'] == 3
        assert inductee['hof_score'] == 95
        assert 'Patriots' in inductee['teams_played_for']
        assert 'Buccaneers' in inductee['teams_played_for']
        assert inductee['career_stats']['passing_yards'] == 89000
        assert inductee['presenter_name'] == 'Bill Belichick'
        assert inductee['speech_highlights']['opening'] == 'Standing here in Canton...'

    def test_add_inductee_without_ceremony(self, api, sample_player_data):
        """Verify inductee can be added without ceremony data."""
        row_id = api.add_inductee(
            player_id=18,
            induction_season=2035,
            years_on_ballot=3,
            vote_percentage=0.82,
            player_data=sample_player_data
        )

        inductee = api.get_inductee(18)
        assert inductee is not None
        assert inductee['is_first_ballot'] is False
        assert inductee['years_on_ballot'] == 3
        assert inductee['presenter_name'] is None
        assert inductee['speech_highlights'] is None

    def test_get_nonexistent_inductee(self, api):
        """Verify get_inductee returns None for nonexistent player."""
        inductee = api.get_inductee(9999)
        assert inductee is None

    def test_inductee_unique_constraint(self, api, sample_player_data):
        """Verify same player cannot be inducted twice."""
        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=sample_player_data
        )

        with pytest.raises(Exception):  # sqlite3.IntegrityError
            api.add_inductee(
                player_id=12,
                induction_season=2031,
                years_on_ballot=2,
                vote_percentage=0.85,
                player_data=sample_player_data
            )


class TestDynastyIsolation:
    """Tests for dynasty isolation."""

    def test_dynasty_isolation(self, api, other_api, sample_player_data):
        """Verify inductees are isolated by dynasty_id."""
        # Add inductee to test-dynasty
        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=sample_player_data
        )

        # Should find in test-dynasty
        assert api.get_inductee(12) is not None

        # Should NOT find in other-dynasty
        assert other_api.get_inductee(12) is None

        # other-dynasty can add same player_id
        other_api.add_inductee(
            player_id=12,
            induction_season=2032,
            years_on_ballot=2,
            vote_percentage=0.88,
            player_data=sample_player_data
        )

        assert other_api.get_inductee(12) is not None
        assert api.get_inductee(12)['induction_season'] == 2030
        assert other_api.get_inductee(12)['induction_season'] == 2032


class TestGetAllInductees:
    """Tests for get_all_inductees method."""

    def test_get_all_inductees(self, api, sample_player_data):
        """Verify get_all_inductees returns all members."""
        # Add 3 inductees
        for i, (pid, pos, season) in enumerate([
            (12, 'QB', 2030), (55, 'LB', 2028), (80, 'WR', 2031)
        ]):
            data = sample_player_data.copy()
            data['primary_position'] = pos
            data['hof_score'] = 90 - i * 5
            api.add_inductee(
                player_id=pid,
                induction_season=season,
                years_on_ballot=1,
                vote_percentage=0.95,
                player_data=data
            )

        inductees = api.get_all_inductees()
        assert len(inductees) == 3

    def test_get_all_inductees_with_position_filter(self, api, sample_player_data):
        """Verify position filtering works."""
        for pid, pos in [(12, 'QB'), (55, 'LB'), (80, 'WR')]:
            data = sample_player_data.copy()
            data['primary_position'] = pos
            api.add_inductee(
                player_id=pid,
                induction_season=2030,
                years_on_ballot=1,
                vote_percentage=0.95,
                player_data=data
            )

        qbs = api.get_all_inductees(position_filter='QB')
        assert len(qbs) == 1
        assert qbs[0]['player_id'] == 12

        lbs = api.get_all_inductees(position_filter='LB')
        assert len(lbs) == 1
        assert lbs[0]['player_id'] == 55


class TestGetInducteesBySeason:
    """Tests for get_inductees_by_season method."""

    def test_get_inductees_by_season(self, api, sample_player_data):
        """Verify filtering by induction season works."""
        for pid, season in [(12, 2030), (55, 2030), (80, 2031)]:
            api.add_inductee(
                player_id=pid,
                induction_season=season,
                years_on_ballot=1,
                vote_percentage=0.95,
                player_data=sample_player_data
            )

        class_2030 = api.get_inductees_by_season(2030)
        assert len(class_2030) == 2

        class_2031 = api.get_inductees_by_season(2031)
        assert len(class_2031) == 1


class TestGetTeamInductees:
    """Tests for get_team_inductees method."""

    def test_team_inductees_json_search(self, api, sample_player_data):
        """Verify teams_played_for JSON search works."""
        # Patriots inductee
        data1 = sample_player_data.copy()
        data1['teams_played_for'] = ['Patriots', 'Buccaneers']
        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=data1
        )

        # Giants inductee
        data2 = sample_player_data.copy()
        data2['teams_played_for'] = ['Giants']
        api.add_inductee(
            player_id=10,
            induction_season=2028,
            years_on_ballot=1,
            vote_percentage=0.95,
            player_data=data2
        )

        patriots_hof = api.get_team_inductees('Patriots')
        assert len(patriots_hof) == 1
        assert patriots_hof[0]['player_id'] == 12

        giants_hof = api.get_team_inductees('Giants')
        assert len(giants_hof) == 1
        assert giants_hof[0]['player_id'] == 10

        bucs_hof = api.get_team_inductees('Buccaneers')
        assert len(bucs_hof) == 1


class TestIsInducted:
    """Tests for is_inducted method."""

    def test_is_inducted(self, api, sample_player_data):
        """Verify is_inducted returns correct status."""
        assert api.is_inducted(12) is False

        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=sample_player_data
        )

        assert api.is_inducted(12) is True
        assert api.is_inducted(9999) is False


class TestInducteeCount:
    """Tests for get_inductee_count method."""

    def test_inductee_count(self, api, sample_player_data):
        """Verify count is accurate."""
        assert api.get_inductee_count() == 0

        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=sample_player_data
        )
        assert api.get_inductee_count() == 1

        api.add_inductee(
            player_id=55,
            induction_season=2031,
            years_on_ballot=1,
            vote_percentage=0.92,
            player_data=sample_player_data
        )
        assert api.get_inductee_count() == 2


# ============================================
# Voting History Tests
# ============================================

class TestVotingHistory:
    """Tests for voting history operations."""

    def test_save_and_get_voting_result(self, api):
        """Verify voting results are persisted correctly."""
        row_id = api.save_voting_result(
            voting_season=2030,
            player_id=12,
            player_name='Tom Brady',
            position='QB',
            retirement_season=2025,
            years_on_ballot=1,
            vote_percentage=0.97,
            votes_received=48,
            total_voters=50,
            was_inducted=True,
            is_first_ballot=True,
            removed_from_ballot=False,
            hof_score=95,
            score_breakdown={'awards': 28, 'stats': 24, 'championships': 15}
        )

        assert row_id > 0

        results = api.get_voting_history_by_season(2030)
        assert len(results) == 1
        assert results[0]['player_name'] == 'Tom Brady'
        assert results[0]['vote_percentage'] == 0.97
        assert results[0]['was_inducted'] is True
        assert results[0]['is_first_ballot'] is True
        assert results[0]['score_breakdown']['awards'] == 28

    def test_get_player_voting_history(self, api):
        """Verify complete voting history for a player."""
        # Year 1: Borderline
        api.save_voting_result(
            voting_season=2030,
            player_id=55,
            player_name='Lawrence Taylor',
            position='LB',
            retirement_season=2025,
            years_on_ballot=1,
            vote_percentage=0.65,
            votes_received=32,
            total_voters=50,
            was_inducted=False,
            is_first_ballot=False,
            removed_from_ballot=False,
            hof_score=75
        )

        # Year 2: Strong
        api.save_voting_result(
            voting_season=2031,
            player_id=55,
            player_name='Lawrence Taylor',
            position='LB',
            retirement_season=2025,
            years_on_ballot=2,
            vote_percentage=0.82,
            votes_received=41,
            total_voters=50,
            was_inducted=True,
            is_first_ballot=False,
            removed_from_ballot=False,
            hof_score=75
        )

        history = api.get_player_voting_history(55)
        assert len(history) == 2
        assert history[0]['voting_season'] == 2030
        assert history[0]['vote_percentage'] == 0.65
        assert history[1]['voting_season'] == 2031
        assert history[1]['was_inducted'] is True


class TestYearsOnBallot:
    """Tests for years_on_ballot tracking."""

    def test_years_on_ballot_tracking(self, api):
        """Verify ballot year counting works."""
        assert api.get_years_on_ballot(55) == 0

        api.save_voting_result(
            voting_season=2030,
            player_id=55,
            player_name='Test Player',
            position='LB',
            retirement_season=2025,
            years_on_ballot=1,
            vote_percentage=0.60,
            votes_received=30,
            total_voters=50,
            was_inducted=False,
            is_first_ballot=False,
            removed_from_ballot=False,
            hof_score=60
        )

        assert api.get_years_on_ballot(55) == 1

        api.save_voting_result(
            voting_season=2031,
            player_id=55,
            player_name='Test Player',
            position='LB',
            retirement_season=2025,
            years_on_ballot=2,
            vote_percentage=0.65,
            votes_received=32,
            total_voters=50,
            was_inducted=False,
            is_first_ballot=False,
            removed_from_ballot=False,
            hof_score=60
        )

        assert api.get_years_on_ballot(55) == 2


class TestRemovedFromBallot:
    """Tests for ballot removal tracking."""

    def test_was_removed_from_ballot(self, api):
        """Verify removed_from_ballot tracking."""
        # Add player who was NOT removed
        api.save_voting_result(
            voting_season=2030,
            player_id=55,
            player_name='Strong Candidate',
            position='LB',
            retirement_season=2025,
            years_on_ballot=1,
            vote_percentage=0.82,
            votes_received=41,
            total_voters=50,
            was_inducted=True,
            is_first_ballot=True,
            removed_from_ballot=False,
            hof_score=80
        )

        assert api.was_removed_from_ballot(55) is False

        # Add player who WAS removed
        api.save_voting_result(
            voting_season=2030,
            player_id=99,
            player_name='Weak Candidate',
            position='FB',
            retirement_season=2025,
            years_on_ballot=20,
            vote_percentage=0.03,
            votes_received=1,
            total_voters=50,
            was_inducted=False,
            is_first_ballot=False,
            removed_from_ballot=True,
            hof_score=35
        )

        assert api.was_removed_from_ballot(99) is True


# ============================================
# Statistics Tests
# ============================================

class TestHOFStats:
    """Tests for get_hof_stats method."""

    def test_hof_stats_calculation(self, api, sample_player_data):
        """Verify statistics are calculated correctly."""
        # Empty stats
        stats = api.get_hof_stats()
        assert stats['total_members'] == 0
        assert stats['first_ballot_count'] == 0
        assert stats['first_ballot_percentage'] == 0.0
        assert stats['average_wait_years'] == 0.0

        # Add first-ballot QB
        data1 = sample_player_data.copy()
        data1['primary_position'] = 'QB'
        api.add_inductee(
            player_id=12,
            induction_season=2030,
            years_on_ballot=1,
            vote_percentage=0.97,
            player_data=data1
        )

        # Add 2nd-year WR
        data2 = sample_player_data.copy()
        data2['primary_position'] = 'WR'
        api.add_inductee(
            player_id=80,
            induction_season=2031,
            years_on_ballot=2,
            vote_percentage=0.85,
            player_data=data2
        )

        # Add 3rd-year LB
        data3 = sample_player_data.copy()
        data3['primary_position'] = 'LB'
        api.add_inductee(
            player_id=55,
            induction_season=2032,
            years_on_ballot=3,
            vote_percentage=0.82,
            player_data=data3
        )

        stats = api.get_hof_stats()
        assert stats['total_members'] == 3
        assert stats['first_ballot_count'] == 1
        assert stats['first_ballot_percentage'] == pytest.approx(33.33, rel=0.1)
        assert stats['average_wait_years'] == 2.0  # (1+2+3)/3
        assert stats['by_position']['QB'] == 1
        assert stats['by_position']['WR'] == 1
        assert stats['by_position']['LB'] == 1
