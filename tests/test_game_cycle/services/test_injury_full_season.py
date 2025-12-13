"""
Full-season integration test for injury system.

Validates end-to-end injury processing over simulated weeks.

Run with:
    python -m pytest tests/game_cycle/services/test_injury_full_season.py -v
"""

import random
import sqlite3
from typing import Dict, List

import pytest

from src.game_cycle.models.injury_models import (
    BodyPart,
    Injury,
    InjurySeverity,
    InjuryType,
)
from src.game_cycle.services.injury_risk_profiles import POSITION_INJURY_RISKS
from src.game_cycle.services.injury_service import InjuryService


@pytest.fixture
def season_db(tmp_path) -> str:
    """Create database with schema for full season test."""
    db_path = tmp_path / "season_test.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create required tables
    cursor.executescript("""
        -- Dynasties
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT,
            created_at TEXT
        );

        -- Dynasty state
        CREATE TABLE IF NOT EXISTS dynasty_state (
            dynasty_id TEXT PRIMARY KEY,
            season INTEGER DEFAULT 2025,
            current_phase TEXT DEFAULT 'REGULAR_SEASON'
        );

        -- Player transactions
        CREATE TABLE IF NOT EXISTS player_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transaction_date TEXT,
            details TEXT,
            contract_id INTEGER,
            event_id TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
        );

        -- Players
        CREATE TABLE IF NOT EXISTS players (
            player_id INTEGER PRIMARY KEY,
            dynasty_id TEXT,
            first_name TEXT,
            last_name TEXT,
            team_id INTEGER,
            primary_position TEXT,
            overall INTEGER DEFAULT 75,
            birthdate TEXT,
            durability INTEGER DEFAULT 75,
            attributes TEXT
        );

        -- Team rosters
        CREATE TABLE IF NOT EXISTS team_rosters (
            dynasty_id TEXT,
            player_id INTEGER,
            team_id INTEGER,
            roster_status TEXT DEFAULT 'active',
            PRIMARY KEY (dynasty_id, player_id)
        );

        -- Injury tables
        CREATE TABLE IF NOT EXISTS player_injuries (
            injury_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week_occurred INTEGER NOT NULL,
            injury_type TEXT NOT NULL,
            body_part TEXT NOT NULL,
            severity TEXT NOT NULL,
            estimated_weeks_out INTEGER NOT NULL,
            actual_weeks_out INTEGER,
            occurred_during TEXT NOT NULL,
            game_id TEXT,
            play_description TEXT,
            is_active INTEGER DEFAULT 1,
            ir_placement_date TEXT,
            ir_return_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ir_tracking (
            dynasty_id TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            ir_return_slots_used INTEGER DEFAULT 0,
            PRIMARY KEY (dynasty_id, team_id, season)
        );
    """)

    # Insert dynasty
    cursor.execute("""
        INSERT INTO dynasties (dynasty_id, name, created_at)
        VALUES ('test_dynasty', 'Test Dynasty', datetime('now'))
    """)
    cursor.execute("""
        INSERT INTO dynasty_state (dynasty_id, season, current_phase)
        VALUES ('test_dynasty', 2025, 'REGULAR_SEASON')
    """)

    # Insert test players (10 per team for 2 teams)
    positions = ['QB', 'RB', 'WR', 'WR', 'TE', 'LT', 'CB', 'SS', 'K', 'P']
    player_id = 1

    for team_id in [1, 2]:
        for i, position in enumerate(positions):
            cursor.execute("""
                INSERT INTO players (
                    player_id, dynasty_id, first_name, last_name,
                    team_id, primary_position, overall, birthdate,
                    durability, attributes
                ) VALUES (?, 'test_dynasty', ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                player_id,
                f"Player{player_id}",
                f"Last{player_id}",
                team_id,
                position,
                75,
                "1997-06-15",
                75,
                '{}'
            ))

            cursor.execute("""
                INSERT INTO team_rosters (dynasty_id, player_id, team_id, roster_status)
                VALUES ('test_dynasty', ?, ?, 'active')
            """, (player_id, team_id))

            player_id += 1

    conn.commit()
    conn.close()

    return str(db_path)


class TestFullSeasonIntegration:
    """Test injury system across a full season."""

    def test_injuries_accumulate_over_season(self, season_db):
        """Verify injuries accumulate correctly over multiple weeks."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Record injuries for weeks 1-4
        for week in range(1, 5):
            injury = Injury(
                player_id=week,
                player_name=f"Player{week}",
                team_id=1,
                injury_type=InjuryType.ANKLE_SPRAIN,
                body_part=BodyPart.ANKLE,
                severity=InjurySeverity.MINOR,
                weeks_out=2,
                week_occurred=week,
                season=2025,
                occurred_during='game',
                game_id=f"game_1_{week}"
            )
            injury_service.record_injury(injury)

        # Verify 4 active injuries
        active = injury_service.get_active_injuries()
        assert len(active) == 4

    def test_injured_players_excluded_correctly(self, season_db):
        """Verify injured players are marked unavailable."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Injure player 1
        injury = Injury(
            player_id=1,
            player_name="Player1",
            team_id=1,
            injury_type=InjuryType.HAMSTRING_STRAIN,
            body_part=BodyPart.THIGH,
            severity=InjurySeverity.MODERATE,
            weeks_out=4,
            week_occurred=1,
            season=2025,
            occurred_during='game',
            game_id="game_1_1"
        )
        injury_service.record_injury(injury)

        # Player 1 should be unavailable, player 2 should be available
        assert not injury_service.is_player_available(1)
        assert injury_service.is_player_available(2)

    def test_recovery_timing_accuracy(self, season_db):
        """Verify players recover within expected timeframe."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Create injury with 2 weeks out at week 1
        injury = Injury(
            player_id=1,
            player_name="Player1",
            team_id=1,
            injury_type=InjuryType.ANKLE_SPRAIN,
            body_part=BodyPart.ANKLE,
            severity=InjurySeverity.MINOR,
            weeks_out=2,
            week_occurred=1,
            season=2025,
            occurred_during='game',
            game_id="game_1_1"
        )
        injury_service.record_injury(injury)

        # Week 2: Should not be recovered yet
        recovered_week_2 = injury_service.check_injury_recovery(2)
        assert len(recovered_week_2) == 0

        # Week 3: Should be recovered (week 1 + 2 weeks = week 3)
        recovered_week_3 = injury_service.check_injury_recovery(3)
        assert len(recovered_week_3) == 1
        assert recovered_week_3[0].player_id == 1

    def test_ir_slot_limits_enforced(self, season_db):
        """Verify teams can't exceed 8 IR return slots."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Place 8 players on IR and activate them
        for i in range(1, 9):
            # Create injury eligible for IR (4+ weeks)
            injury = Injury(
                player_id=i,
                player_name=f"Player{i}",
                team_id=1,
                injury_type=InjuryType.KNEE_SPRAIN,
                body_part=BodyPart.KNEE,
                severity=InjurySeverity.SEVERE,
                weeks_out=6,
                week_occurred=1,
                season=2025,
                occurred_during='game',
                game_id=f"game_1_1"
            )
            injury_id = injury_service.record_injury(injury)

            # Place on IR
            success = injury_service.place_on_ir(i, injury_id)
            assert success, f"Failed to place player {i} on IR"

            # Activate from IR (at week 5, after 4-game minimum)
            success = injury_service.activate_from_ir(i, current_week=5)
            assert success, f"Failed to activate player {i} from IR"

        # Verify 8 slots used
        slots = injury_service.get_ir_return_slots_remaining(1)
        assert slots == 0

        # Try to use a 9th slot - create new injury
        injury9 = Injury(
            player_id=9,
            player_name="Player9",
            team_id=1,
            injury_type=InjuryType.KNEE_SPRAIN,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.SEVERE,
            weeks_out=6,
            week_occurred=6,
            season=2025,
            occurred_during='game',
            game_id="game_1_6"
        )
        injury9_id = injury_service.record_injury(injury9)
        injury_service.place_on_ir(9, injury9_id)

        # This activation should fail (no slots remaining)
        success = injury_service.activate_from_ir(9, current_week=10)
        assert not success

    def test_season_ending_injuries_persist(self, season_db):
        """Verify season-ending injuries remain active all season."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Create ACL tear (season-ending) at week 1
        injury = Injury(
            player_id=1,
            player_name="Player1",
            team_id=1,
            injury_type=InjuryType.ACL_TEAR,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.SEASON_ENDING,
            weeks_out=20,  # Out for full season
            week_occurred=1,
            season=2025,
            occurred_during='game',
            game_id="game_1_1"
        )
        injury_service.record_injury(injury)

        # Check that player is still injured at week 18
        recovered = injury_service.check_injury_recovery(18)
        assert len(recovered) == 0  # Not recovered yet
        assert not injury_service.is_player_available(1)

    def test_ai_ir_management_works(self, season_db):
        """Verify AI teams manage IR correctly."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Create a severe injury for team 2 (AI team, user is team 1)
        injury = Injury(
            player_id=11,  # Team 2 player
            player_name="Player11",
            team_id=2,
            injury_type=InjuryType.KNEE_SPRAIN,
            body_part=BodyPart.KNEE,
            severity=InjurySeverity.SEVERE,
            weeks_out=6,
            week_occurred=1,
            season=2025,
            occurred_during='game',
            game_id="game_2_1"
        )
        injury_service.record_injury(injury)

        # Run AI IR management (user team is 1)
        results = injury_service.process_ai_ir_management(
            user_team_id=1,
            current_week=2
        )

        # Should have placed the severe injury on IR
        assert results['total_placements'] >= 1


class TestInjuryRateValidation:
    """Validate injury rates match expected ranges."""

    def test_injury_rate_per_team_reasonable(self, season_db):
        """Verify injury rates are within expected range."""
        # Check that injury probability calculation works
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Calculate probability for a typical RB in game context
        prob = injury_service.calculate_injury_probability(
            position='RB',
            durability=75,
            age=27,
            injury_history_count=0,
            context='game'
        )

        # RB base rate is 8.2%, should be adjusted by durability
        assert 0.05 <= prob <= 0.15  # Within reasonable range

    def test_rb_highest_injury_rate(self, season_db):
        """Running backs should have highest injury rate."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Get base probabilities (in game context)
        rb_prob = injury_service.calculate_injury_probability('RB', 75, 27, 0, 'game')
        qb_prob = injury_service.calculate_injury_probability('QB', 75, 27, 0, 'game')
        k_prob = injury_service.calculate_injury_probability('K', 75, 27, 0, 'game')

        # RB should be higher than QB and K
        assert rb_prob > qb_prob
        assert rb_prob > k_prob

    def test_kicker_punter_lowest_rate(self, season_db):
        """K/P should have lowest injury rate."""
        injury_service = InjuryService(season_db, 'test_dynasty', 2025)

        # Get base probabilities for all positions (in game context)
        k_prob = injury_service.calculate_injury_probability('K', 75, 27, 0, 'game')
        p_prob = injury_service.calculate_injury_probability('P', 75, 27, 0, 'game')

        # Compare with other positions
        for position in ['RB', 'WR', 'QB', 'CB', 'MLB']:
            pos_prob = injury_service.calculate_injury_probability(position, 75, 27, 0, 'game')
            assert k_prob < pos_prob, f"K should have lower rate than {position}"
            assert p_prob < pos_prob, f"P should have lower rate than {position}"

    def test_all_positions_have_risk_profiles(self):
        """Verify all 25 positions have injury risk profiles."""
        expected_positions = [
            'QB', 'RB', 'FB', 'WR', 'TE',
            'LT', 'LG', 'C', 'RG', 'RT',
            'LE', 'DT', 'RE', 'EDGE',
            'LOLB', 'MLB', 'ROLB',
            'CB', 'FS', 'SS',
            'K', 'P', 'LS', 'KR', 'PR'
        ]

        for position in expected_positions:
            assert position in POSITION_INJURY_RISKS, f"Missing risk profile for {position}"


class TestSeverityDistribution:
    """Test injury severity distribution."""

    def test_severity_weeks_reasonable(self):
        """Verify severity classifications have reasonable week ranges."""
        from src.game_cycle.models.injury_models import INJURY_SEVERITY_WEEKS

        # Minor: 1-2 weeks
        assert INJURY_SEVERITY_WEEKS[InjurySeverity.MINOR] == (1, 2)

        # Moderate: 3-4 weeks
        assert INJURY_SEVERITY_WEEKS[InjurySeverity.MODERATE] == (3, 4)

        # Severe: 5-8 weeks
        assert INJURY_SEVERITY_WEEKS[InjurySeverity.SEVERE] == (5, 8)

        # Season-ending: 10+ weeks
        min_weeks, max_weeks = INJURY_SEVERITY_WEEKS[InjurySeverity.SEASON_ENDING]
        assert min_weeks >= 10

    def test_acl_tear_is_season_ending(self, season_db):
        """ACL tears should always be season-ending."""
        from src.game_cycle.models.injury_models import INJURY_TYPE_SEVERITY_RANGE

        # INJURY_TYPE_SEVERITY_RANGE returns a list of possible severities
        acl_severities = INJURY_TYPE_SEVERITY_RANGE.get(
            InjuryType.ACL_TEAR,
            [InjurySeverity.SEASON_ENDING]
        )

        # ACL tear should only have season-ending severity (always season-ending)
        assert InjurySeverity.SEASON_ENDING in acl_severities
        assert len(acl_severities) == 1  # Only season-ending
