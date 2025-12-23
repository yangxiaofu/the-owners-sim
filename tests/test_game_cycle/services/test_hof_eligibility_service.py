"""
Unit tests for HOFEligibilityService.

Tests covering HOF eligibility determination including:
- Eligible candidate retrieval
- 5-year waiting period (via DB)
- Already-inducted exclusion
- Removed-from-ballot exclusion
- 20-year ballot limit
- Dynasty isolation
"""
import pytest
import sqlite3
import tempfile
import os
import json

from src.game_cycle.services.hof_eligibility_service import (
    HOFEligibilityService,
    HOFCandidate,
    EligibilityStatus,
)
from src.game_cycle.database.hof_api import HOFAPI
from src.game_cycle.database.connection import GameCycleDatabase


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def db_path():
    """Create a temporary database with required schema."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_path = f.name

    conn = sqlite3.connect(temp_path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Retired players table
        CREATE TABLE IF NOT EXISTS retired_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            retirement_season INTEGER NOT NULL,
            retirement_reason TEXT NOT NULL DEFAULT 'age',
            final_team_id INTEGER NOT NULL,
            years_played INTEGER NOT NULL DEFAULT 1,
            age_at_retirement INTEGER NOT NULL DEFAULT 35,
            one_day_contract_team_id INTEGER,
            hall_of_fame_eligible_season INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
        );

        -- Career summaries table
        CREATE TABLE IF NOT EXISTS career_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            primary_position TEXT NOT NULL,
            career_seasons INTEGER NOT NULL DEFAULT 1,
            teams_played_for TEXT,
            primary_team_id INTEGER,
            pro_bowls INTEGER NOT NULL DEFAULT 0,
            all_pro_first_team INTEGER NOT NULL DEFAULT 0,
            all_pro_second_team INTEGER NOT NULL DEFAULT 0,
            mvp_awards INTEGER NOT NULL DEFAULT 0,
            super_bowl_wins INTEGER NOT NULL DEFAULT 0,
            super_bowl_mvps INTEGER NOT NULL DEFAULT 0,
            hall_of_fame_score INTEGER NOT NULL DEFAULT 0,
            pass_yards INTEGER DEFAULT 0,
            pass_tds INTEGER DEFAULT 0,
            rush_yards INTEGER DEFAULT 0,
            rush_tds INTEGER DEFAULT 0,
            receptions INTEGER DEFAULT 0,
            rec_yards INTEGER DEFAULT 0,
            rec_tds INTEGER DEFAULT 0,
            tackles INTEGER DEFAULT 0,
            sacks REAL DEFAULT 0,
            interceptions INTEGER DEFAULT 0,
            fg_made INTEGER DEFAULT 0,
            fg_attempted INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, player_id)
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
def service(db):
    """Create HOFEligibilityService for test-dynasty."""
    return HOFEligibilityService(db, 'test-dynasty')


@pytest.fixture
def hof_api(db):
    """Create HOFAPI for test-dynasty."""
    return HOFAPI(db, 'test-dynasty')


def insert_retired_player(db, dynasty_id, player_id, retirement_season, final_team_id=1, years_played=10):
    """Helper to insert a retired player."""
    hof_eligible = retirement_season + 5
    db.execute(
        """INSERT INTO retired_players
           (dynasty_id, player_id, retirement_season, final_team_id,
            years_played, hall_of_fame_eligible_season)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (dynasty_id, player_id, retirement_season, final_team_id, years_played, hof_eligible)
    )


def insert_career_summary(
    db, dynasty_id, player_id, player_name, position,
    hof_score=50, career_seasons=10, teams=None, pro_bowls=0,
    all_pro_first=0, all_pro_second=0, mvp_awards=0, super_bowl_wins=0
):
    """Helper to insert a career summary."""
    teams_json = json.dumps(teams or ["Bears"])
    db.execute(
        """INSERT INTO career_summaries
           (dynasty_id, player_id, player_name, primary_position,
            career_seasons, teams_played_for, hall_of_fame_score,
            pro_bowls, all_pro_first_team, all_pro_second_team,
            mvp_awards, super_bowl_wins)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (dynasty_id, player_id, player_name, position, career_seasons,
         teams_json, hof_score, pro_bowls, all_pro_first, all_pro_second,
         mvp_awards, super_bowl_wins)
    )


# ============================================
# TestGetEligibleCandidates
# ============================================

class TestGetEligibleCandidates:
    """Tests for get_eligible_candidates()."""

    def test_returns_eligible_candidates(self, db, service):
        """Players eligible for HOF voting are returned."""
        # Player retired in 2020, eligible in 2025
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Tom Brady", "QB", hof_score=95)

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 1
        assert candidates[0].player_id == 1001
        assert candidates[0].player_name == "Tom Brady"
        assert candidates[0].primary_position == "QB"
        assert candidates[0].hof_score == 95

    def test_filters_out_already_inducted(self, db, service, hof_api):
        """Players already in HOF are excluded."""
        # Player retired in 2020, eligible in 2025
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Tom Brady", "QB", hof_score=95)

        # Induct the player
        hof_api.add_inductee(
            player_id=1001,
            induction_season=2025,
            years_on_ballot=1,
            vote_percentage=0.95,
            player_data={
                'player_name': "Tom Brady",
                'primary_position': "QB",
                'career_seasons': 23,
                'final_team_id': 1,
                'teams_played_for': ["Patriots", "Buccaneers"],
                'career_stats': {},
                'hof_score': 95,
            }
        )

        candidates = service.get_eligible_candidates(2026)

        assert len(candidates) == 0

    def test_filters_out_removed_from_ballot(self, db, service, hof_api):
        """Players removed from ballot are excluded."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Mediocre Player", "WR", hof_score=30)

        # Save voting result with removed_from_ballot=True
        hof_api.save_voting_result(
            voting_season=2025,
            player_id=1001,
            player_name="Mediocre Player",
            position="WR",
            retirement_season=2020,
            years_on_ballot=1,
            vote_percentage=0.03,  # Below 5%
            votes_received=3,
            total_voters=100,
            was_inducted=False,
            is_first_ballot=True,
            removed_from_ballot=True,  # Removed from ballot
            hof_score=30,
        )

        candidates = service.get_eligible_candidates(2026)

        assert len(candidates) == 0

    def test_twenty_year_limit(self, db, service):
        """Players on ballot > 20 years are excluded."""
        # Player retired in 2000, eligible in 2005
        # In 2026, that's 22 years on ballot (2005-2026 = 22 years)
        insert_retired_player(db, 'test-dynasty', 1001, 2000)
        insert_career_summary(db, 'test-dynasty', 1001, "Old Candidate", "LB", hof_score=55)

        candidates = service.get_eligible_candidates(2026)

        # 2026 - 2005 + 1 = 22 years, exceeds 20
        assert len(candidates) == 0

    def test_sorted_by_hof_score(self, db, service):
        """Candidates returned in descending HOF score order."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Player A", "QB", hof_score=70)

        insert_retired_player(db, 'test-dynasty', 1002, 2020)
        insert_career_summary(db, 'test-dynasty', 1002, "Player B", "WR", hof_score=90)

        insert_retired_player(db, 'test-dynasty', 1003, 2020)
        insert_career_summary(db, 'test-dynasty', 1003, "Player C", "RB", hof_score=50)

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 3
        assert candidates[0].hof_score == 90  # Player B first
        assert candidates[1].hof_score == 70  # Player A second
        assert candidates[2].hof_score == 50  # Player C last

    def test_first_ballot_flag(self, db, service):
        """is_first_ballot=True when years_on_ballot=1."""
        # Player retired in 2020, first eligible in 2025
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "First Ballot Player", "QB", hof_score=95)

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 1
        assert candidates[0].is_first_ballot is True
        assert candidates[0].years_on_ballot == 1

    def test_second_year_ballot_flag(self, db, service):
        """is_first_ballot=False for players in second year on ballot."""
        # Player retired in 2020, eligible in 2025
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Returning Candidate", "LB", hof_score=65)

        # Check in 2026 (second year on ballot)
        candidates = service.get_eligible_candidates(2026)

        assert len(candidates) == 1
        assert candidates[0].is_first_ballot is False
        assert candidates[0].years_on_ballot == 2

    def test_dynasty_isolation(self, db, service):
        """Only returns candidates for specified dynasty."""
        # Player in test-dynasty
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Test Player", "QB", hof_score=80)

        # Player in other-dynasty
        insert_retired_player(db, 'other-dynasty', 2001, 2020)
        insert_career_summary(db, 'other-dynasty', 2001, "Other Player", "QB", hof_score=85)

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 1
        assert candidates[0].player_id == 1001

    def test_no_career_summary_excluded(self, db, service):
        """Players without career summary are excluded."""
        # Retired player with NO career summary
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        # No career_summary inserted

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 0

    def test_too_recent_retirement(self, db, service):
        """Players retired < 5 years ago are not yet eligible."""
        # Player retired in 2022, eligible in 2027
        insert_retired_player(db, 'test-dynasty', 1001, 2022)
        insert_career_summary(db, 'test-dynasty', 1001, "Recent Retiree", "RB", hof_score=75)

        # Check in 2025 - not yet eligible
        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 0


# ============================================
# TestCheckEligibility
# ============================================

class TestCheckEligibility:
    """Tests for check_eligibility()."""

    def test_eligible_status(self, db, service):
        """Returns ELIGIBLE for valid candidate."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Eligible Player", "QB", hof_score=85)

        status = service.check_eligibility(1001, 2025)

        assert status == EligibilityStatus.ELIGIBLE

    def test_too_recent(self, db, service):
        """Returns TOO_RECENT for <5 years retired."""
        insert_retired_player(db, 'test-dynasty', 1001, 2022)  # Eligible in 2027
        insert_career_summary(db, 'test-dynasty', 1001, "Recent Retiree", "RB", hof_score=75)

        status = service.check_eligibility(1001, 2025)

        assert status == EligibilityStatus.TOO_RECENT

    def test_already_inducted(self, db, service, hof_api):
        """Returns ALREADY_INDUCTED for HOF members."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "HOF Player", "QB", hof_score=95)

        # Induct the player
        hof_api.add_inductee(
            player_id=1001,
            induction_season=2025,
            years_on_ballot=1,
            vote_percentage=0.98,
            player_data={
                'player_name': "HOF Player",
                'primary_position': "QB",
                'career_seasons': 20,
                'final_team_id': 1,
                'teams_played_for': ["Bears"],
                'career_stats': {},
                'hof_score': 95,
            }
        )

        status = service.check_eligibility(1001, 2026)

        assert status == EligibilityStatus.ALREADY_INDUCTED

    def test_removed_from_ballot(self, db, service, hof_api):
        """Returns REMOVED_FROM_BALLOT for removed players."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "Removed Player", "WR", hof_score=25)

        # Mark as removed from ballot
        hof_api.save_voting_result(
            voting_season=2025,
            player_id=1001,
            player_name="Removed Player",
            position="WR",
            retirement_season=2020,
            years_on_ballot=1,
            vote_percentage=0.02,
            votes_received=2,
            total_voters=100,
            was_inducted=False,
            is_first_ballot=True,
            removed_from_ballot=True,
            hof_score=25,
        )

        status = service.check_eligibility(1001, 2026)

        assert status == EligibilityStatus.REMOVED_FROM_BALLOT

    def test_not_retired(self, db, service):
        """Returns NOT_RETIRED for players not in retired_players."""
        # No retired player record
        status = service.check_eligibility(9999, 2025)

        assert status == EligibilityStatus.NOT_RETIRED

    def test_no_career_summary(self, db, service):
        """Returns NO_CAREER_SUMMARY for players without career summary."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        # No career summary

        status = service.check_eligibility(1001, 2025)

        assert status == EligibilityStatus.NO_CAREER_SUMMARY


# ============================================
# TestYearsOnBallot
# ============================================

class TestYearsOnBallot:
    """Tests for years_on_ballot calculation."""

    def test_first_year_eligible(self, db, service):
        """Returns 1 for first year of eligibility."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)  # Eligible in 2025
        insert_career_summary(db, 'test-dynasty', 1001, "New Candidate", "QB", hof_score=80)

        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 1
        assert candidates[0].years_on_ballot == 1

    def test_multi_year_calculation(self, db, service):
        """Correctly calculates years on ballot for multi-year candidates."""
        insert_retired_player(db, 'test-dynasty', 1001, 2015)  # Eligible in 2020
        insert_career_summary(db, 'test-dynasty', 1001, "Veteran Candidate", "LB", hof_score=60)

        # Check in 2025 - should be 6th year (2020, 2021, 2022, 2023, 2024, 2025)
        candidates = service.get_eligible_candidates(2025)

        assert len(candidates) == 1
        assert candidates[0].years_on_ballot == 6


# ============================================
# TestGetCandidate
# ============================================

class TestGetCandidate:
    """Tests for get_candidate()."""

    def test_returns_candidate_if_eligible(self, db, service):
        """Returns HOFCandidate for eligible player."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(
            db, 'test-dynasty', 1001, "Great Player", "WR",
            hof_score=85, career_seasons=14,
            teams=["Cowboys", "Eagles"],
            pro_bowls=8, all_pro_first=3, all_pro_second=2,
            mvp_awards=0, super_bowl_wins=1
        )

        candidate = service.get_candidate(1001, 2025)

        assert candidate is not None
        assert candidate.player_id == 1001
        assert candidate.player_name == "Great Player"
        assert candidate.primary_position == "WR"
        assert candidate.hof_score == 85
        assert candidate.career_seasons == 14
        assert candidate.pro_bowl_selections == 8
        assert candidate.all_pro_first_team == 3
        assert candidate.super_bowl_wins == 1
        assert "Cowboys" in candidate.teams_played_for
        assert "Eagles" in candidate.teams_played_for

    def test_returns_none_if_not_eligible(self, db, service):
        """Returns None for ineligible player."""
        insert_retired_player(db, 'test-dynasty', 1001, 2022)  # Too recent
        insert_career_summary(db, 'test-dynasty', 1001, "Recent Player", "QB", hof_score=70)

        candidate = service.get_candidate(1001, 2025)

        assert candidate is None


# ============================================
# TestFirstBallotCandidates
# ============================================

class TestFirstBallotCandidates:
    """Tests for get_first_ballot_candidates()."""

    def test_returns_only_first_ballot(self, db, service):
        """Only returns candidates in their first year of eligibility."""
        # First ballot candidate (retired 2020, eligible 2025)
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(db, 'test-dynasty', 1001, "First Ballot", "QB", hof_score=90)

        # Returning candidate (retired 2018, eligible 2023, now on ballot 3 years)
        insert_retired_player(db, 'test-dynasty', 1002, 2018)
        insert_career_summary(db, 'test-dynasty', 1002, "Returning", "RB", hof_score=65)

        first_ballot = service.get_first_ballot_candidates(2025)

        assert len(first_ballot) == 1
        assert first_ballot[0].player_id == 1001
        assert first_ballot[0].is_first_ballot is True


# ============================================
# TestCandidateDataIntegrity
# ============================================

class TestCandidateDataIntegrity:
    """Tests for data integrity in HOFCandidate."""

    def test_to_dict_serialization(self, db, service):
        """HOFCandidate.to_dict() returns complete data."""
        insert_retired_player(db, 'test-dynasty', 1001, 2020)
        insert_career_summary(
            db, 'test-dynasty', 1001, "Complete Player", "QB",
            hof_score=85, career_seasons=15,
            teams=["Bears", "Packers"],
            pro_bowls=10, all_pro_first=5, all_pro_second=2,
            mvp_awards=2, super_bowl_wins=3
        )

        candidates = service.get_eligible_candidates(2025)
        candidate_dict = candidates[0].to_dict()

        assert candidate_dict['player_id'] == 1001
        assert candidate_dict['player_name'] == "Complete Player"
        assert candidate_dict['primary_position'] == "QB"
        assert candidate_dict['hof_score'] == 85
        assert candidate_dict['career_seasons'] == 15
        assert candidate_dict['pro_bowl_selections'] == 10
        assert candidate_dict['all_pro_first_team'] == 5
        assert candidate_dict['mvp_awards'] == 2
        assert candidate_dict['super_bowl_wins'] == 3
        assert candidate_dict['is_first_ballot'] is True
        assert candidate_dict['eligibility_status'] == 'ELIGIBLE'
