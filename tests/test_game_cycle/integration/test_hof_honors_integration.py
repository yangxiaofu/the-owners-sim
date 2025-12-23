"""
Integration tests for Hall of Fame in OFFSEASON_HONORS (Milestone 18, Tollgate 7).

Tests the complete HOF voting flow within the honors stage:
1. Eligible candidates identified from retired_players
2. Voting simulation with realistic results
3. Inductees persisted to hof_inductees
4. Headlines generated for inductees
5. Results returned in stage result
6. Idempotent (re-running doesn't duplicate)
"""

import json
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock

from src.game_cycle.handlers.offseason import OffseasonHandler
from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.hof_api import HOFAPI
from src.game_cycle.services.hof_eligibility_service import (
    HOFEligibilityService,
    HOFCandidate,
)
from src.game_cycle.services.hof_voting_engine import (
    HOFVotingEngine,
    HOFVotingSession,
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_dynasty_id():
    """Test dynasty identifier."""
    return "test-dynasty-hof-001"


@pytest.fixture
def test_season():
    """Test voting season (candidates retired 5+ years ago)."""
    return 2030


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


@pytest.fixture
def game_cycle_db(temp_db_path, test_dynasty_id, test_season):
    """
    Create game cycle database with HOF schema and test data.
    """
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Create all required tables
    _create_schema(cursor)

    # Insert test dynasty
    cursor.execute("""
        INSERT INTO dynasties (dynasty_id, name, created_at)
        VALUES (?, 'Test Dynasty', datetime('now'))
    """, (test_dynasty_id,))

    conn.commit()

    yield (temp_db_path, conn)

    conn.close()


def _create_schema(cursor):
    """Create all required database tables."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT,
            created_at TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS retired_players (
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
        CREATE TABLE IF NOT EXISTS career_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            primary_position TEXT NOT NULL,
            career_seasons INTEGER DEFAULT 0,
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
        CREATE TABLE IF NOT EXISTS hof_inductees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            induction_season INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            primary_position TEXT NOT NULL,
            years_on_ballot INTEGER NOT NULL,
            vote_percentage REAL NOT NULL,
            is_first_ballot INTEGER NOT NULL DEFAULT 0,
            career_stats TEXT,
            achievements TEXT,
            teams_played_for TEXT,
            final_team_id INTEGER,
            career_seasons INTEGER DEFAULT 0,
            presenter_name TEXT,
            presenter_relationship TEXT,
            speech_highlights TEXT,
            bust_description TEXT,
            jacket_moment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hof_voting_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            voting_season INTEGER NOT NULL,
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
            hof_score INTEGER NOT NULL DEFAULT 0,
            score_breakdown TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id, voting_season)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_headlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            headline_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            subheadline TEXT,
            body_text TEXT,
            sentiment TEXT,
            priority INTEGER,
            team_ids TEXT,
            player_ids TEXT,
            metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def _insert_retired_player(
    cursor,
    dynasty_id: str,
    player_id: int,
    name: str,
    position: str,
    retirement_season: int,
    team_id: int = 1,
    years_played: int = 15,
    mvp_awards: int = 0,
    super_bowl_wins: int = 0,
    all_pro_first: int = 0,
    all_pro_second: int = 0,
    pro_bowls: int = 0,
    pass_yards: int = 0,
    rush_yards: int = 0,
    rec_yards: int = 0,
    sacks: float = 0,
    interceptions: int = 0,
    hof_score: int = 50
):
    """Insert a retired player with career summary for HOF testing."""
    # Insert retired player
    cursor.execute("""
        INSERT INTO retired_players
        (dynasty_id, player_id, retirement_season, retirement_reason,
         final_team_id, years_played, age_at_retirement, hall_of_fame_eligible_season)
        VALUES (?, ?, ?, 'AGE_DECLINE', ?, ?, 38, ?)
    """, (dynasty_id, player_id, retirement_season, team_id, years_played, retirement_season + 5))

    # Insert career summary
    # teams_played_for should be a list of team names (strings)
    team_name = f"Team {team_id}"  # Simplified team name
    teams_json = json.dumps([team_name])
    cursor.execute("""
        INSERT INTO career_summaries
        (dynasty_id, player_id, player_name, primary_position, career_seasons,
         games_played, games_started,
         pass_yards, pass_tds, rush_yards, rush_tds, rec_yards, rec_tds,
         sacks, interceptions, pro_bowls, all_pro_first_team, all_pro_second_team,
         mvp_awards, super_bowl_wins, teams_played_for, primary_team_id,
         hall_of_fame_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dynasty_id, player_id, name, position, years_played,
        years_played * 16, years_played * 16,  # games played/started
        pass_yards, pass_yards // 200,  # pass yards/TDs
        rush_yards, rush_yards // 100,  # rush yards/TDs
        rec_yards, rec_yards // 100,    # rec yards/TDs
        sacks, interceptions,
        pro_bowls, all_pro_first, all_pro_second,
        mvp_awards, super_bowl_wins,
        teams_json, team_id, hof_score
    ))


# ============================================================================
# TEST CLASSES
# ============================================================================

class TestHOFEligibilityInHonors:
    """Test that eligible candidates are identified correctly."""

    def test_finds_eligible_candidates(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """Candidates who retired 5+ years ago are eligible."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert player who retired 5 years ago (eligible)
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=100,
            name="Tom Eligible",
            position="QB",
            retirement_season=test_season - 5,  # 5-year wait satisfied
            mvp_awards=2,
            super_bowl_wins=3,
            all_pro_first=3,
            pro_bowls=10,
            pass_yards=50000,
            hof_score=90
        )
        conn.commit()
        conn.close()

        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        assert len(candidates) == 1
        assert candidates[0].player_name == "Tom Eligible"
        assert candidates[0].hof_score >= 85  # First-ballot caliber

    def test_excludes_recent_retirees(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """Candidates who retired less than 5 years ago are not eligible."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert player who retired 3 years ago (not eligible)
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=101,
            name="Joe Recent",
            position="RB",
            retirement_season=test_season - 3,  # Only 3 years wait
            pro_bowls=5,
            rush_yards=8000,
            hof_score=60
        )
        conn.commit()
        conn.close()

        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        assert len(candidates) == 0


class TestHOFVotingInHonors:
    """Test the voting simulation within honors flow."""

    def test_first_ballot_lock_inducted(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """First-ballot candidates (85+ score) should be inducted."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert first-ballot caliber player
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=200,
            name="Jerry First-Ballot",
            position="WR",
            retirement_season=test_season - 5,
            mvp_awards=1,
            super_bowl_wins=2,
            all_pro_first=5,
            pro_bowls=10,
            rec_yards=15000,
            hof_score=92
        )
        conn.commit()
        conn.close()

        # Get candidates and run voting
        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        engine = HOFVotingEngine()
        session = engine.conduct_voting(test_dynasty_id, test_season, candidates)

        assert len(session.inductees) == 1
        assert session.inductees[0].player_name == "Jerry First-Ballot"
        assert session.inductees[0].is_first_ballot is True
        assert session.inductees[0].vote_percentage >= 0.80

    def test_weak_candidate_not_inducted(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """Weak candidates should not be inducted."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert weak candidate
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=201,
            name="Bob Average",
            position="LB",
            retirement_season=test_season - 5,
            pro_bowls=2,
            hof_score=35
        )
        conn.commit()
        conn.close()

        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        engine = HOFVotingEngine()
        session = engine.conduct_voting(test_dynasty_id, test_season, candidates)

        assert len(session.inductees) == 0
        # Weak candidate either stays on ballot (vote % > 5%)
        # or gets removed (vote % < 5%) - randomness determines outcome
        # Either way, they're not inducted
        total_not_inducted = len(session.non_inductees) + len(session.removed_from_ballot)
        assert total_not_inducted == 1


class TestHOFPersistenceInHonors:
    """Test that voting results and inductees are persisted."""

    def test_voting_results_saved(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """All voting results should be saved to hof_voting_history."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert two candidates
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=300,
            name="Hall Star",
            position="QB",
            retirement_season=test_season - 5,
            mvp_awards=2,
            super_bowl_wins=1,
            all_pro_first=3,
            pro_bowls=8,
            pass_yards=45000,
            hof_score=88
        )
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=301,
            name="Solid Player",
            position="RB",
            retirement_season=test_season - 5,
            pro_bowls=3,
            rush_yards=6000,
            hof_score=45
        )
        conn.commit()
        conn.close()

        # Run voting
        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        engine = HOFVotingEngine()
        session = engine.conduct_voting(test_dynasty_id, test_season, candidates)

        # Save results
        with GameCycleDatabase(db_path) as db:
            hof_api = HOFAPI(db, test_dynasty_id)

            for result in session.all_results:
                hof_api.save_voting_result(
                    voting_season=test_season,
                    player_id=result.player_id,
                    player_name=result.player_name,
                    position=result.primary_position,
                    retirement_season=result.retirement_season,
                    years_on_ballot=result.years_on_ballot,
                    vote_percentage=result.vote_percentage,
                    votes_received=result.votes_received,
                    total_voters=result.total_voters,
                    was_inducted=result.was_inducted,
                    is_first_ballot=result.is_first_ballot,
                    removed_from_ballot=result.removed_from_ballot,
                    hof_score=result.hof_score,
                    score_breakdown=result.score_breakdown
                )

        # Verify saved
        with GameCycleDatabase(db_path) as db:
            hof_api = HOFAPI(db, test_dynasty_id)
            history = hof_api.get_voting_history_by_season(test_season)

        assert len(history) == 2
        names = [h['player_name'] for h in history]
        assert "Hall Star" in names
        assert "Solid Player" in names


class TestHOFIdempotency:
    """Test that re-running HOF voting doesn't duplicate results."""

    def test_already_processed_skipped(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """If voting already done for season, skip and return existing counts."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert candidate
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=400,
            name="Already Voted",
            position="CB",
            retirement_season=test_season - 5,
            all_pro_first=2,
            pro_bowls=5,
            interceptions=40,
            hof_score=70
        )

        # Pre-insert voting result (already processed)
        cursor.execute("""
            INSERT INTO hof_voting_history
            (dynasty_id, player_id, voting_season, player_name, primary_position,
             retirement_season, years_on_ballot, vote_percentage, votes_received,
             total_voters, was_inducted, is_first_ballot, removed_from_ballot,
             hof_score)
            VALUES (?, 400, ?, 'Already Voted', 'CB', ?, 1, 0.75, 36, 48, 0, 0, 0, 70)
        """, (test_dynasty_id, test_season, test_season - 5))
        conn.commit()
        conn.close()

        # Check that existing voting is detected
        with GameCycleDatabase(db_path) as db:
            hof_api = HOFAPI(db, test_dynasty_id)
            existing = hof_api.get_voting_history_by_season(test_season)

        assert len(existing) == 1
        assert existing[0]['player_name'] == "Already Voted"


class TestHOFMaxInductees:
    """Test the max 5 inductees limit."""

    def test_max_five_inducted(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """Even with many eligible, only 5 can be inducted."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert 7 first-ballot caliber players
        for i in range(7):
            _insert_retired_player(
                cursor, test_dynasty_id,
                player_id=500 + i,
                name=f"Legend {i+1}",
                position="QB",
                retirement_season=test_season - 5,
                mvp_awards=2,
                super_bowl_wins=2,
                all_pro_first=4,
                pro_bowls=10,
                pass_yards=50000,
                hof_score=90 + i  # 90-96 scores
            )
        conn.commit()
        conn.close()

        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        engine = HOFVotingEngine()
        session = engine.conduct_voting(test_dynasty_id, test_season, candidates)

        # Only 5 inducted despite 7 eligible
        assert len(session.inductees) == 5
        # Others remain as non-inductees (not removed, just didn't make cut)
        assert len(session.non_inductees) == 2


class TestHOFClassStrength:
    """Test class strength affects borderline candidates."""

    def test_weak_class_helps_borderline(
        self, game_cycle_db, test_dynasty_id, test_season
    ):
        """In a weak class, borderline candidates have better chance."""
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert only borderline candidates (no first-ballot)
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=600,
            name="Borderline Joe",
            position="TE",
            retirement_season=test_season - 5,
            pro_bowls=5,
            all_pro_second=2,
            rec_yards=7000,
            hof_score=62  # Borderline
        )
        conn.commit()
        conn.close()

        with GameCycleDatabase(db_path) as db:
            service = HOFEligibilityService(db, test_dynasty_id)
            candidates = service.get_eligible_candidates(test_season)

        engine = HOFVotingEngine()
        session = engine.conduct_voting(test_dynasty_id, test_season, candidates)

        # Weak class (no first-ballot locks)
        assert session.class_strength < 0.5

        # Borderline candidate still has a chance
        # (may or may not be inducted, but shouldn't be removed)
        total_results = len(session.inductees) + len(session.non_inductees)
        assert total_results >= 1  # Still on ballot


# ============================================================================
# HANDLER INTEGRATION TESTS
# ============================================================================

class TestOffseasonHandlerHOFIntegration:
    """Test HOF integration with the actual OffseasonHandler."""

    @patch('src.game_cycle.handlers.offseason.OffseasonHandler._get_team_name')
    def test_conduct_hof_voting_returns_results(
        self, mock_get_team_name, game_cycle_db, test_dynasty_id, test_season
    ):
        """The _conduct_hof_voting method returns proper results dict."""
        mock_get_team_name.return_value = "Test Team"
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        # Insert HOF-caliber player
        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=700,
            name="Handler Test Star",
            position="DE",
            retirement_season=test_season - 5,
            all_pro_first=4,
            pro_bowls=8,
            sacks=100,
            hof_score=85
        )
        conn.commit()
        conn.close()

        handler = OffseasonHandler(db_path)
        events = []
        context = {"user_team_id": 1}

        results = handler._conduct_hof_voting(
            db_path, test_dynasty_id, test_season, context, events
        )

        assert "inductee_count" in results
        assert "candidates_count" in results
        assert "first_ballot_count" in results
        assert results["candidates_count"] >= 1

        # Check events logged
        assert any("HOF" in e for e in events)

    @patch('src.game_cycle.handlers.offseason.OffseasonHandler._get_team_name')
    def test_conduct_hof_voting_handles_no_candidates(
        self, mock_get_team_name, game_cycle_db, test_dynasty_id, test_season
    ):
        """Handles case when no candidates are eligible."""
        mock_get_team_name.return_value = "Test Team"
        db_path, conn = game_cycle_db
        conn.close()

        handler = OffseasonHandler(db_path)
        events = []
        context = {"user_team_id": 1}

        results = handler._conduct_hof_voting(
            db_path, test_dynasty_id, test_season, context, events
        )

        assert results["inductee_count"] == 0
        assert results["candidates_count"] == 0
        assert any("No HOF-eligible candidates" in e for e in events)

    @patch('src.game_cycle.handlers.offseason.OffseasonHandler._get_team_name')
    def test_conduct_hof_voting_is_idempotent(
        self, mock_get_team_name, game_cycle_db, test_dynasty_id, test_season
    ):
        """Running twice returns same results without duplicating."""
        mock_get_team_name.return_value = "Test Team"
        db_path, conn = game_cycle_db
        cursor = conn.cursor()

        _insert_retired_player(
            cursor, test_dynasty_id,
            player_id=800,
            name="Idempotent Star",
            position="LB",
            retirement_season=test_season - 5,
            all_pro_first=3,
            pro_bowls=6,
            hof_score=80
        )
        conn.commit()
        conn.close()

        handler = OffseasonHandler(db_path)
        context = {"user_team_id": 1}

        # First run
        events1 = []
        results1 = handler._conduct_hof_voting(
            db_path, test_dynasty_id, test_season, context, events1
        )

        # Second run
        events2 = []
        results2 = handler._conduct_hof_voting(
            db_path, test_dynasty_id, test_season, context, events2
        )

        # Should detect already processed
        assert any("already processed" in e for e in events2)
        assert results1["candidates_count"] == results2["candidates_count"]
