"""Tests for InjuryService."""

import os
import sqlite3
import tempfile

import pytest

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.models.injury_models import (
    BodyPart,
    Injury,
    InjurySeverity,
    InjuryType,
)
from src.game_cycle.services.injury_risk_profiles import (
    POSITION_INJURY_RISKS,
    get_risk_profile,
)
from src.game_cycle.services.injury_service import InjuryService


class TestInjuryServiceCRUD:
    """Test InjuryService CRUD methods."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with test data."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(path)
        conn = db.get_connection()

        # Create team
        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (22, 'Detroit Lions', 'DET', 'NFC', 'North')
        """)

        # Create dynasty
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        # Create test player
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 100, 'John', 'Doe', 21, 22,
            '["RB"]', '{"overall": 85, "durability": 70}'
        ))

        # Create second test player
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 101, 'Jane', 'Smith', 10, 22,
            '["QB"]', '{"overall": 90, "durability": 85}'
        ))

        conn.commit()
        db.close()

        yield path

        try:
            os.unlink(path)
        except OSError:
            pass

    def test_record_injury(self, temp_db):
        """Can record an injury."""
        service = InjuryService(temp_db, 'test', 2025)

        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=2,
            week_occurred=5,
            season=2025,
            occurred_during='game'
        )

        injury_id = service.record_injury(injury)
        assert injury_id > 0

    def test_get_active_injuries_empty(self, temp_db):
        """Returns empty list when no injuries."""
        service = InjuryService(temp_db, 'test', 2025)
        active = service.get_active_injuries(team_id=22)
        assert len(active) == 0

    def test_get_active_injuries(self, temp_db):
        """Can retrieve active injuries."""
        service = InjuryService(temp_db, 'test', 2025)

        # Record injury
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.HAMSTRING_STRAIN,
            body_part=BodyPart.THIGH,
            severity=InjurySeverity.MODERATE,
            weeks_out=3,
            week_occurred=4,
            season=2025,
            occurred_during='game'
        )
        service.record_injury(injury)

        # Get active
        active = service.get_active_injuries(team_id=22)
        assert len(active) == 1
        assert active[0].injury_type == InjuryType.HAMSTRING_STRAIN
        assert active[0].player_id == 100

    def test_get_active_injuries_filters_by_team(self, temp_db):
        """Active injuries filtered by team_id."""
        service = InjuryService(temp_db, 'test', 2025)

        # Add injury for team 22
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=2,
            week_occurred=5,
            season=2025,
            occurred_during='game'
        )
        service.record_injury(injury)

        # Check team 22 has injury
        active_22 = service.get_active_injuries(team_id=22)
        assert len(active_22) == 1

        # Check other team has no injuries
        active_other = service.get_active_injuries(team_id=1)
        assert len(active_other) == 0

    def test_get_player_injury_history(self, temp_db):
        """Can get player's full injury history."""
        service = InjuryService(temp_db, 'test', 2025)

        # Record two injuries for same player
        injury1 = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=1,
            week_occurred=3,
            season=2025,
            occurred_during='game'
        )
        injury2 = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.HAMSTRING_STRAIN,
            body_part=BodyPart.THIGH,
            severity=InjurySeverity.MODERATE,
            weeks_out=3,
            week_occurred=8,
            season=2025,
            occurred_during='practice'
        )
        service.record_injury(injury1)
        service.record_injury(injury2)

        # Get history
        history = service.get_player_injury_history(player_id=100)
        assert len(history) == 2

    def test_clear_injury(self, temp_db):
        """Can clear healed injury."""
        service = InjuryService(temp_db, 'test', 2025)

        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=1,
            week_occurred=3,
            season=2025,
            occurred_during='practice'
        )
        injury_id = service.record_injury(injury)

        # Clear it
        service.clear_injury(injury_id, actual_weeks=1)

        # Verify cleared
        active = service.get_active_injuries(team_id=22)
        assert len(active) == 0

        # But should still be in history
        history = service.get_player_injury_history(100)
        assert len(history) == 1
        assert history[0].is_active is False

    def test_check_injury_recovery(self, temp_db):
        """Returns injuries ready for recovery."""
        service = InjuryService(temp_db, 'test', 2025)

        # Record injury at week 5, 2 weeks out (ready at week 7)
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=2,
            week_occurred=5,
            season=2025,
            occurred_during='game'
        )
        service.record_injury(injury)

        # At week 6 - not ready
        ready = service.check_injury_recovery(current_week=6)
        assert len(ready) == 0

        # At week 7 - ready
        ready = service.check_injury_recovery(current_week=7)
        assert len(ready) == 1

        # At week 10 - still ready (past due)
        ready = service.check_injury_recovery(current_week=10)
        assert len(ready) == 1


class TestInjuryServiceAvailability:
    """Test player availability methods."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with test data."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (22, 'Detroit Lions', 'DET', 'NFC', 'North')
        """)

        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 100, 'John', 'Doe', 21, 22,
            '["RB"]', '{"overall": 85, "durability": 70}'
        ))

        conn.commit()
        db.close()

        yield path

        try:
            os.unlink(path)
        except OSError:
            pass

    def test_get_unavailable_players(self, temp_db):
        """Returns injured players as unavailable."""
        service = InjuryService(temp_db, 'test', 2025)

        # Initially available
        unavailable = service.get_unavailable_players(team_id=22)
        assert 100 not in unavailable

        # Add injury
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.KNEE_SPRAIN,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.MODERATE,
            weeks_out=4,
            week_occurred=6,
            season=2025,
            occurred_during='game'
        )
        service.record_injury(injury)

        # Now unavailable
        unavailable = service.get_unavailable_players(team_id=22)
        assert 100 in unavailable

    def test_is_player_available(self, temp_db):
        """Check individual player availability."""
        service = InjuryService(temp_db, 'test', 2025)

        # Initially available
        assert service.is_player_available(100) is True

        # Add injury
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.CONCUSSION,
            body_part=BodyPart.HEAD,
            severity=InjurySeverity.MINOR,
            weeks_out=1,
            week_occurred=8,
            season=2025,
            occurred_during='game'
        )
        service.record_injury(injury)

        # Now unavailable
        assert service.is_player_available(100) is False


class TestInjuryServiceProbability:
    """Test injury probability calculations."""

    @pytest.fixture
    def temp_db(self):
        """Create minimal database for service."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (22, 'Detroit Lions', 'DET', 'NFC', 'North')
        """)

        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        conn.commit()
        db.close()

        yield path

        try:
            os.unlink(path)
        except OSError:
            pass

    def test_injury_probability_durability_effect(self, temp_db):
        """Durability affects injury probability."""
        service = InjuryService(temp_db, 'test', 2025)

        # High durability
        prob_high = service.calculate_injury_probability(
            position='RB', durability=95, age=25,
            injury_history_count=0, context='game'
        )

        # Low durability
        prob_low = service.calculate_injury_probability(
            position='RB', durability=55, age=25,
            injury_history_count=0, context='game'
        )

        assert prob_low > prob_high

    def test_injury_probability_age_effect(self, temp_db):
        """Age affects injury probability."""
        service = InjuryService(temp_db, 'test', 2025)

        prob_young = service.calculate_injury_probability(
            position='RB', durability=75, age=24,
            injury_history_count=0, context='game'
        )

        prob_old = service.calculate_injury_probability(
            position='RB', durability=75, age=34,
            injury_history_count=0, context='game'
        )

        assert prob_old > prob_young

    def test_injury_probability_history_effect(self, temp_db):
        """Injury history increases probability."""
        service = InjuryService(temp_db, 'test', 2025)

        prob_no_history = service.calculate_injury_probability(
            position='RB', durability=75, age=28,
            injury_history_count=0, context='game'
        )

        prob_with_history = service.calculate_injury_probability(
            position='RB', durability=75, age=28,
            injury_history_count=5, context='game'
        )

        assert prob_with_history > prob_no_history

    def test_injury_probability_context_effect(self, temp_db):
        """Practice injuries less common than game injuries."""
        service = InjuryService(temp_db, 'test', 2025)

        prob_game = service.calculate_injury_probability(
            position='RB', durability=75, age=28,
            injury_history_count=0, context='game'
        )

        prob_practice = service.calculate_injury_probability(
            position='RB', durability=75, age=28,
            injury_history_count=0, context='practice'
        )

        assert prob_game > prob_practice
        assert prob_practice == pytest.approx(prob_game * 0.3)

    def test_injury_probability_position_effect(self, temp_db):
        """Different positions have different base risks."""
        service = InjuryService(temp_db, 'test', 2025)

        prob_rb = service.calculate_injury_probability(
            position='RB', durability=75, age=28,
            injury_history_count=0, context='game'
        )

        prob_qb = service.calculate_injury_probability(
            position='QB', durability=75, age=28,
            injury_history_count=0, context='game'
        )

        prob_k = service.calculate_injury_probability(
            position='K', durability=75, age=28,
            injury_history_count=0, context='game'
        )

        # RB > QB > K
        assert prob_rb > prob_qb > prob_k


class TestInjuryRiskProfiles:
    """Test injury risk profile data."""

    def test_all_positions_have_profiles(self):
        """All 25 positions have risk profiles."""
        expected_positions = {
            'QB', 'RB', 'FB', 'WR', 'TE',
            'LT', 'LG', 'C', 'RG', 'RT',
            'LE', 'DT', 'RE', 'EDGE',
            'LOLB', 'MLB', 'ROLB',
            'CB', 'FS', 'SS',
            'K', 'P', 'LS', 'KR', 'PR'
        }
        assert expected_positions.issubset(set(POSITION_INJURY_RISKS.keys()))

    def test_rb_highest_risk(self):
        """RB should have highest base injury chance."""
        rb_risk = POSITION_INJURY_RISKS['RB'].base_injury_chance
        qb_risk = POSITION_INJURY_RISKS['QB'].base_injury_chance
        k_risk = POSITION_INJURY_RISKS['K'].base_injury_chance

        assert rb_risk > qb_risk > k_risk

    def test_get_risk_profile_known_position(self):
        """get_risk_profile returns correct profile for known positions."""
        profile = get_risk_profile('RB')
        assert profile.position == 'RB'
        assert profile.base_injury_chance == 0.082

    def test_get_risk_profile_unknown_position(self):
        """get_risk_profile returns default for unknown positions."""
        profile = get_risk_profile('UNKNOWN')
        assert profile.position == 'UNKNOWN'
        assert profile.base_injury_chance == 0.05  # Default

    def test_get_risk_profile_case_insensitive(self):
        """get_risk_profile is case insensitive."""
        profile_lower = get_risk_profile('rb')
        profile_upper = get_risk_profile('RB')
        assert profile_lower.base_injury_chance == profile_upper.base_injury_chance

    def test_position_has_common_injuries(self):
        """Each position has at least one common injury."""
        for pos, profile in POSITION_INJURY_RISKS.items():
            assert len(profile.common_injuries) > 0, f"{pos} has no common injuries"

    def test_position_has_high_risk_body_parts(self):
        """Each position has at least one high-risk body part."""
        for pos, profile in POSITION_INJURY_RISKS.items():
            assert len(profile.high_risk_body_parts) > 0, f"{pos} has no high-risk body parts"


class TestInjuryServiceIR:
    """Test IR-related methods (basic functionality, full impl in Tollgate 5)."""

    @pytest.fixture
    def temp_db(self):
        """Create database with test data."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(path)
        conn = db.get_connection()

        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (22, 'Detroit Lions', 'DET', 'NFC', 'North')
        """)

        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 100, 'John', 'Doe', 21, 22,
            '["RB"]', '{"overall": 85, "durability": 70}'
        ))

        # Create team_rosters table (needed for IR placement)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_rosters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dynasty_id TEXT NOT NULL,
                team_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                roster_status TEXT DEFAULT 'active'
            )
        """)

        # Add player to roster
        conn.execute("""
            INSERT INTO team_rosters (dynasty_id, team_id, player_id, roster_status)
            VALUES ('test', 22, 100, 'active')
        """)

        conn.commit()
        db.close()

        yield path

        try:
            os.unlink(path)
        except OSError:
            pass

    def test_get_ir_return_slots_remaining_default(self, temp_db):
        """Returns 8 slots by default (no IR tracking record)."""
        service = InjuryService(temp_db, 'test', 2025)
        slots = service.get_ir_return_slots_remaining(team_id=22)
        assert slots == 8

    def test_place_on_ir(self, temp_db):
        """Can place player on IR."""
        service = InjuryService(temp_db, 'test', 2025)

        # First create an injury
        injury = Injury(
            player_id=100,
            player_name="John Doe",
            team_id=22,
            injury_type=InjuryType.ACL_TEAR,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.SEASON_ENDING,
            weeks_out=12,
            week_occurred=5,
            season=2025,
            occurred_during='game'
        )
        injury_id = service.record_injury(injury)

        # Place on IR
        result = service.place_on_ir(player_id=100, injury_id=injury_id)
        assert result is True

        # Verify player is on IR
        ir_players = service.get_players_on_ir(team_id=22)
        assert len(ir_players) == 1
        assert ir_players[0].player_id == 100

    def test_get_players_on_ir_empty(self, temp_db):
        """Returns empty list when no players on IR."""
        service = InjuryService(temp_db, 'test', 2025)
        ir_players = service.get_players_on_ir(team_id=22)
        assert len(ir_players) == 0
