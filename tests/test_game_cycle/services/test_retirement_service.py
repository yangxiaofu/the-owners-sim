"""
Unit tests for RetirementService.

Tests retirement service integration including:
- Player collection across all teams
- Retirement context building
- Single and batch retirement processing
- Notable retirement identification
- Idempotency checks
- One-day contract processing
- Headline generation
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import patch, MagicMock

from src.game_cycle.services.retirement_service import (
    RetirementService,
    RetirementResult,
    SeasonRetirementSummary,
)
from src.game_cycle.services.retirement_decision_engine import (
    RetirementReason,
    RetirementContext,
    RetirementCandidate,
)
from src.game_cycle.database.retired_players_api import (
    RetiredPlayer,
    CareerSummary,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def temp_db():
    """Create a temporary database with required schema."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(path)
    cursor = conn.cursor()

    # Create required tables
    cursor.execute("""
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            number INTEGER,
            team_id INTEGER DEFAULT 0,
            positions TEXT,
            attributes TEXT,
            status TEXT DEFAULT 'active',
            years_pro INTEGER DEFAULT 1,
            birthdate TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE team_rosters (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            depth_chart_order INTEGER DEFAULT 1,
            roster_status TEXT DEFAULT 'active'
        )
    """)

    cursor.execute("""
        CREATE TABLE retired_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            retirement_season INTEGER NOT NULL,
            retirement_reason TEXT NOT NULL,
            final_team_id INTEGER NOT NULL,
            years_played INTEGER NOT NULL,
            age_at_retirement INTEGER NOT NULL,
            one_day_contract_team_id INTEGER,
            hall_of_fame_eligible_season INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE career_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            position TEXT NOT NULL,
            draft_year INTEGER,
            draft_round INTEGER,
            draft_pick INTEGER,
            games_played INTEGER DEFAULT 0,
            games_started INTEGER DEFAULT 0,
            pass_yards INTEGER DEFAULT 0,
            pass_tds INTEGER DEFAULT 0,
            pass_ints INTEGER DEFAULT 0,
            rush_yards INTEGER DEFAULT 0,
            rush_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            rec_yards INTEGER DEFAULT 0,
            rec_tds INTEGER DEFAULT 0,
            tackles INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            fg_made INTEGER DEFAULT 0,
            fg_attempted INTEGER DEFAULT 0,
            pro_bowls INTEGER DEFAULT 0,
            all_pro_first_team INTEGER DEFAULT 0,
            all_pro_second_team INTEGER DEFAULT 0,
            mvp_awards INTEGER DEFAULT 0,
            super_bowl_wins INTEGER DEFAULT 0,
            super_bowl_mvps INTEGER DEFAULT 0,
            teams_played_for TEXT,
            primary_team_id INTEGER,
            career_approximate_value INTEGER DEFAULT 0,
            hall_of_fame_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE player_injuries (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            severity TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE team_season_history (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            won_super_bowl INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE player_progression_history (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            overall_before INTEGER,
            overall_after INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE games (
            game_id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE player_game_stats (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            game_id INTEGER NOT NULL,
            player_id INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            passing_yards INTEGER DEFAULT 0,
            passing_tds INTEGER DEFAULT 0,
            passing_interceptions INTEGER DEFAULT 0,
            rushing_yards INTEGER DEFAULT 0,
            rushing_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            receiving_yards INTEGER DEFAULT 0,
            receiving_tds INTEGER DEFAULT 0,
            tackles_total INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            forced_fumbles INTEGER DEFAULT 0,
            field_goals_made INTEGER DEFAULT 0,
            field_goals_attempted INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE award_winners (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            award_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            is_winner INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE all_pro_selections (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            position TEXT NOT NULL,
            team_type TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE pro_bowl_selections (
            id INTEGER PRIMARY KEY,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            position TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    yield path

    # Cleanup
    os.unlink(path)


@pytest.fixture
def dynasty_id():
    return "test_dynasty_001"


@pytest.fixture
def season():
    return 2025


@pytest.fixture
def service(temp_db, dynasty_id, season):
    """Create service instance."""
    return RetirementService(temp_db, dynasty_id, season)


@pytest.fixture
def sample_old_qb():
    """Sample old QB player dict (age 42, high probability)."""
    return {
        'player_id': 100,
        'first_name': 'Tom',
        'last_name': 'Brady',
        'positions': '["QB"]',
        'attributes': '{"overall": 75}',
        'birthdate': '1983-01-01',
        'team_id': 1,
        'years_pro': 20,
    }


@pytest.fixture
def sample_young_wr():
    """Sample young WR player dict (age 25, low probability)."""
    return {
        'player_id': 200,
        'first_name': 'Young',
        'last_name': 'Receiver',
        'positions': '["WR"]',
        'attributes': '{"overall": 85}',
        'birthdate': '2000-01-01',
        'team_id': 2,
        'years_pro': 3,
    }


@pytest.fixture
def mock_career_summary():
    """Mock career summary for testing."""
    return CareerSummary(
        player_id=100,
        full_name="Tom Brady",
        position="QB",
        draft_year=2000,
        draft_round=6,
        draft_pick=199,
        games_played=320,
        games_started=316,
        pass_yards=89214,
        pass_tds=649,
        pass_ints=212,
        pro_bowls=15,
        all_pro_first_team=3,
        all_pro_second_team=2,
        mvp_awards=3,
        super_bowl_wins=7,
        super_bowl_mvps=5,
        teams_played_for=[1, 28],
        primary_team_id=1,
        hall_of_fame_score=95,
    )


# ============================================
# Service Initialization Tests (3)
# ============================================

class TestServiceInitialization:

    def test_init_creates_decision_engine(self, temp_db, dynasty_id, season):
        """Service initializes with RetirementDecisionEngine."""
        service = RetirementService(temp_db, dynasty_id, season)
        assert service._decision_engine is not None
        assert service._decision_engine._season == season

    def test_init_creates_summary_generator(self, temp_db, dynasty_id, season):
        """Service initializes with CareerSummaryGenerator."""
        service = RetirementService(temp_db, dynasty_id, season)
        assert service._summary_generator is not None
        assert service._summary_generator._dynasty_id == dynasty_id

    def test_init_with_valid_parameters(self, temp_db, dynasty_id, season):
        """Service stores initialization parameters."""
        service = RetirementService(temp_db, dynasty_id, season)
        assert service._db_path == temp_db
        assert service._dynasty_id == dynasty_id
        assert service._season == season


# ============================================
# Idempotency Tests (3)
# ============================================

class TestIdempotency:

    def test_retirements_already_processed_false(self, temp_db, dynasty_id, season):
        """Returns False when no retirements exist for season."""
        service = RetirementService(temp_db, dynasty_id, season)
        assert service.retirements_already_processed() is False

    def test_retirements_already_processed_true(self, temp_db, dynasty_id, season):
        """Returns True when retirements exist for season."""
        # Insert a retirement record
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retired_players
            (dynasty_id, player_id, retirement_season, retirement_reason,
             final_team_id, years_played, age_at_retirement)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, season, 'age_decline', 1, 20, 42))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        assert service.retirements_already_processed() is True

    def test_process_twice_is_idempotent(self, temp_db, dynasty_id, season):
        """Processing twice doesn't create duplicates."""
        # Insert a retirement record
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retired_players
            (dynasty_id, player_id, retirement_season, retirement_reason,
             final_team_id, years_played, age_at_retirement)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, season, 'age_decline', 1, 20, 42))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)

        # Second call should skip processing
        assert service.retirements_already_processed() is True


# ============================================
# Retirement Context Tests (3)
# ============================================

class TestRetirementContext:

    def test_build_context_with_sb_winner(self, service):
        """Context includes Super Bowl winner team ID."""
        context = service._build_retirement_context(super_bowl_winner_team_id=17)
        assert context.super_bowl_winner_team_id == 17

    def test_build_context_includes_released_players(self, temp_db, dynasty_id, season):
        """Context includes released player IDs."""
        # Insert a free agent
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players
            (dynasty_id, player_id, first_name, last_name, team_id, positions, attributes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 500, 'Free', 'Agent', 0, '["WR"]', '{"overall": 70}'))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        context = service._build_retirement_context(None)

        assert 500 in context.released_player_ids

    def test_build_context_includes_career_ending_injuries(self, temp_db, dynasty_id, season):
        """Context includes career-ending injury IDs."""
        # Insert a career-ending injury
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO player_injuries
            (dynasty_id, player_id, season, severity)
            VALUES (?, ?, ?, ?)
        """, (dynasty_id, 600, season, 'career_ending'))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        context = service._build_retirement_context(None)

        assert 600 in context.career_ending_injury_ids


# ============================================
# Notable Retirement Tests (4)
# ============================================

class TestNotableRetirement:

    def test_is_notable_mvp_winner(self, service):
        """MVP winner is notable."""
        summary = CareerSummary(
            player_id=1, full_name="Test", position="QB",
            mvp_awards=1, super_bowl_wins=0, pro_bowls=1,
            all_pro_first_team=0, all_pro_second_team=0,
            hall_of_fame_score=30,
        )
        assert service._is_notable_retirement(summary) is True

    def test_is_notable_super_bowl_champion(self, service):
        """Super Bowl champion is notable."""
        summary = CareerSummary(
            player_id=2, full_name="Test", position="RB",
            mvp_awards=0, super_bowl_wins=1, pro_bowls=0,
            all_pro_first_team=0, all_pro_second_team=0,
            hall_of_fame_score=25,
        )
        assert service._is_notable_retirement(summary) is True

    def test_is_notable_pro_bowler(self, service):
        """3+ Pro Bowls is notable."""
        summary = CareerSummary(
            player_id=3, full_name="Test", position="WR",
            mvp_awards=0, super_bowl_wins=0, pro_bowls=5,
            all_pro_first_team=0, all_pro_second_team=0,
            hall_of_fame_score=35,
        )
        assert service._is_notable_retirement(summary) is True

    def test_is_not_notable_average_player(self, service):
        """Average player is not notable."""
        summary = CareerSummary(
            player_id=4, full_name="Test", position="TE",
            mvp_awards=0, super_bowl_wins=0, pro_bowls=1,
            all_pro_first_team=0, all_pro_second_team=0,
            hall_of_fame_score=15,
        )
        assert service._is_notable_retirement(summary) is False


# ============================================
# Headline Generation Tests (3)
# ============================================

class TestHeadlineGeneration:

    def test_headline_hof_player(self, service, mock_career_summary):
        """HOF-caliber player gets appropriate headline."""
        headline = service._generate_retirement_headline(
            "Tom Brady", "QB", "age_decline", mock_career_summary
        )
        assert "Hall of Famer" in headline

    def test_headline_mvp_winner(self, service):
        """MVP winner gets MVP-focused headline."""
        summary = CareerSummary(
            player_id=1, full_name="Test MVP", position="QB",
            mvp_awards=2, super_bowl_wins=0, pro_bowls=5,
            all_pro_first_team=1, all_pro_second_team=0,
            hall_of_fame_score=60,
        )
        headline = service._generate_retirement_headline(
            "Test MVP", "QB", "age_decline", summary
        )
        assert "MVP" in headline
        assert "2x" in headline

    def test_headline_injury_retirement(self, service):
        """Injury retirement gets injury-focused headline."""
        summary = CareerSummary(
            player_id=2, full_name="Injured Player", position="RB",
            mvp_awards=0, super_bowl_wins=0, pro_bowls=1,
            all_pro_first_team=0, all_pro_second_team=0,
            hall_of_fame_score=20,
        )
        headline = service._generate_retirement_headline(
            "Injured Player", "RB", "injury", summary
        )
        assert "injury" in headline.lower()


# ============================================
# One-Day Contract Tests (2)
# ============================================

class TestOneDayContract:

    def test_process_one_day_contract(self, temp_db, dynasty_id, season):
        """One-day contract updates record."""
        # Insert a retirement record first
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retired_players
            (dynasty_id, player_id, retirement_season, retirement_reason,
             final_team_id, years_played, age_at_retirement)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, season, 'age_decline', 28, 20, 42))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        success = service.process_one_day_contract(100, 1)  # Sign with team 1

        assert success is True

    def test_one_day_contract_updates_record(self, temp_db, dynasty_id, season):
        """One-day contract value persisted to database."""
        # Insert a retirement record
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO retired_players
            (dynasty_id, player_id, retirement_season, retirement_reason,
             final_team_id, years_played, age_at_retirement)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, season, 'age_decline', 28, 20, 42))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        service.process_one_day_contract(100, 1)

        # Verify the update
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT one_day_contract_team_id
            FROM retired_players
            WHERE dynasty_id = ? AND player_id = ?
        """, (dynasty_id, 100))
        row = cursor.fetchone()
        conn.close()

        assert row[0] == 1


# ============================================
# Get Season Retirements Tests (2)
# ============================================

class TestGetSeasonRetirements:

    def test_get_season_retirements_empty(self, service):
        """Returns empty list when no retirements."""
        retirements = service.get_season_retirements()
        assert retirements == []

    def test_get_season_retirements_with_data(self, temp_db, dynasty_id, season):
        """Returns retirements for the season."""
        # Insert retirement records
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        for i in range(3):
            cursor.execute("""
                INSERT INTO retired_players
                (dynasty_id, player_id, retirement_season, retirement_reason,
                 final_team_id, years_played, age_at_retirement)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (dynasty_id, 100 + i, season, 'age_decline', 1, 10, 35 + i))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        retirements = service.get_season_retirements()

        assert len(retirements) == 3


# ============================================
# Get Career Summary Tests (2)
# ============================================

class TestGetCareerSummary:

    def test_get_player_career_summary_not_found(self, service):
        """Returns None for non-existent player."""
        summary = service.get_player_career_summary(999)
        assert summary is None

    def test_get_player_career_summary_found(self, temp_db, dynasty_id, season):
        """Returns career summary for retired player."""
        # Insert career summary
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO career_summaries
            (dynasty_id, player_id, full_name, position, games_played,
             pro_bowls, hall_of_fame_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, 'Test Player', 'QB', 200, 5, 50))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)
        summary = service.get_player_career_summary(100)

        assert summary is not None
        assert summary['full_name'] == 'Test Player'
        assert summary['pro_bowls'] == 5


# ============================================
# Dataclass Tests (2)
# ============================================

class TestDataclasses:

    def test_retirement_result_to_dict(self, mock_career_summary):
        """RetirementResult.to_dict() works correctly."""
        result = RetirementResult(
            player_id=100,
            player_name="Tom Brady",
            position="QB",
            age=42,
            reason="age_decline",
            years_played=20,
            final_team_id=1,
            career_summary=mock_career_summary,
            is_notable=True,
            headline="Future Hall of Famer Tom Brady announces retirement"
        )

        d = result.to_dict()

        assert d['player_id'] == 100
        assert d['player_name'] == "Tom Brady"
        assert d['is_notable'] is True
        assert 'career_summary' in d

    def test_season_retirement_summary_to_dict(self, mock_career_summary):
        """SeasonRetirementSummary.to_dict() works correctly."""
        result = RetirementResult(
            player_id=100,
            player_name="Tom Brady",
            position="QB",
            age=42,
            reason="age_decline",
            years_played=20,
            final_team_id=1,
            career_summary=mock_career_summary,
            is_notable=True,
            headline="Test"
        )

        summary = SeasonRetirementSummary(
            season=2025,
            total_retirements=1,
            notable_retirements=[result],
            other_retirements=[],
            user_team_retirements=[],
            events=["Test event"]
        )

        d = summary.to_dict()

        assert d['season'] == 2025
        assert d['total_retirements'] == 1
        assert len(d['notable_retirements']) == 1
        assert d['events'] == ["Test event"]


# ============================================
# Helper Method Tests (2)
# ============================================

class TestHelperMethods:

    def test_get_player_name(self, service):
        """Player name formatted correctly."""
        player = {'first_name': 'Patrick', 'last_name': 'Mahomes'}
        name = service._get_player_name(player)
        assert name == 'Patrick Mahomes'

    def test_get_player_name_missing(self, service):
        """Missing name returns default."""
        player = {}
        name = service._get_player_name(player)
        assert name == 'Unknown Player'


# ============================================
# Integration Tests (2)
# ============================================

class TestIntegration:

    def test_full_retirement_flow_with_mock(self, temp_db, dynasty_id, season):
        """Full flow with mocked decision engine."""
        # Create a player
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO players
            (dynasty_id, player_id, first_name, last_name, team_id, positions,
             attributes, birthdate, years_pro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (dynasty_id, 100, 'Old', 'Veteran', 1, '["QB"]',
              '{"overall": 65}', '1983-01-01', 20))
        cursor.execute("""
            INSERT INTO team_rosters
            (dynasty_id, player_id, team_id, roster_status)
            VALUES (?, ?, ?, ?)
        """, (dynasty_id, 100, 1, 'active'))
        conn.commit()
        conn.close()

        service = RetirementService(temp_db, dynasty_id, season)

        # Mock the decision engine to force retirement
        mock_candidate = RetirementCandidate(
            player_id=100,
            player_name="Old Veteran",
            position="QB",
            age=42,
            team_id=1,
            probability=0.90,
            reason=RetirementReason.AGE_DECLINE,
            will_retire=True,
            ovr_current=65
        )

        # Mock the player data to avoid PlayerRosterAPI dependency
        mock_player = {
            'player_id': 100,
            'first_name': 'Old',
            'last_name': 'Veteran',
            'team_id': 1,
            'positions': ['QB'],
            'attributes': {'overall': 65},
            'birthdate': '1983-01-01',
            'years_pro': 20
        }

        with patch.object(service, '_get_all_active_players', return_value=[mock_player]):
            with patch.object(
                service._decision_engine, 'get_retiring_players',
                return_value=[mock_candidate]
            ):
                # Also mock the summary generator to avoid complex db setup
                with patch.object(
                    service._summary_generator, 'generate_career_summary',
                    return_value=CareerSummary(
                        player_id=100,
                        full_name='Old Veteran',
                        position='QB',
                        games_played=200,
                        pro_bowls=3,
                        hall_of_fame_score=45
                    )
                ):
                    summary = service.process_post_season_retirements(
                        super_bowl_winner_team_id=None,
                        user_team_id=1
                    )

        assert summary.total_retirements == 1
        assert len(summary.events) > 0
        assert len(summary.user_team_retirements) == 1

    def test_batch_processing_no_retirees(self, temp_db, dynasty_id, season):
        """Batch processing handles empty retiree list."""
        service = RetirementService(temp_db, dynasty_id, season)

        # Mock empty retiring players
        with patch.object(
            service._decision_engine, 'get_retiring_players',
            return_value=[]
        ):
            with patch.object(
                service, '_get_all_active_players',
                return_value=[]
            ):
                summary = service.process_post_season_retirements()

        assert summary.total_retirements == 0
        assert summary.notable_retirements == []
        assert summary.other_retirements == []
