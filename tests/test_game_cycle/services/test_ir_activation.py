"""Tests for InjuryService IR activation roster management methods."""

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
from src.game_cycle.services.injury_service import InjuryService


class TestIRActivationMethods:
    """Test IR activation roster management methods."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with comprehensive test data."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)

        db = GameCycleDatabase(path)
        conn = db.get_connection()

        # Create teams
        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES
                (22, 'Detroit Lions', 'DET', 'NFC', 'North'),
                (23, 'Green Bay Packers', 'GB', 'NFC', 'North')
        """)

        # Create dynasty
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('test', 'Test Dynasty', 22)
        """)

        # Create IR return slots tracking
        conn.execute("""
            INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
            VALUES
                ('test', 22, 2025, 3),
                ('test', 23, 2025, 0)
        """)

        # Create test players - Detroit Lions (Team 22)
        # Player 100: QB (Starter, high value, on IR for 5 weeks - eligible)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 100, 'Star', 'Quarterback', 9, 22,
            '["QB"]', '{"overall": 88, "durability": 70}'
        ))

        # Player 101: RB (Backup, low value, on IR for 3 weeks - NOT eligible yet)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 101, 'Backup', 'Runner', 28, 22,
            '["RB"]', '{"overall": 72, "durability": 65}'
        ))

        # Player 102: WR (Starter, on IR for 6 weeks - eligible)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 102, 'Elite', 'Receiver', 11, 22,
            '["WR"]', '{"overall": 90, "durability": 75}'
        ))

        # Player 103: LB (Roster player - low value cut candidate)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 103, 'Depth', 'Linebacker', 54, 22,
            '["LB"]', '{"overall": 68, "durability": 80}'
        ))

        # Player 104: CB (Roster player - medium value)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 104, 'Solid', 'Corner', 25, 22,
            '["CB"]', '{"overall": 75, "durability": 70}'
        ))

        # Player 105: QB (Protected position - should not be cut candidate)
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 105, 'Backup', 'QuarterbackTwo', 12, 22,
            '["QB"]', '{"overall": 70, "durability": 75}'
        ))

        # Green Bay players (Team 23) - for AI testing
        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 200, 'GB', 'Quarterback', 12, 23,
            '["QB"]', '{"overall": 85, "durability": 70}'
        ))

        conn.execute("""
            INSERT INTO players (
                dynasty_id, player_id, first_name, last_name,
                number, team_id, positions, attributes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 201, 'GB', 'Linebacker', 52, 23,
            '["LB"]', '{"overall": 65, "durability": 75}'
        ))

        # Create injuries for IR players
        # Player 100: On IR for 5 weeks (eligible)
        conn.execute("""
            INSERT INTO player_injuries (
                dynasty_id, player_id, season, week_occurred,
                injury_type, body_part, severity, estimated_weeks_out,
                occurred_during, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 100, 2025, 5,
            'KNEE_SPRAIN', 'KNEE', 'MODERATE', 6, 'game', 1
        ))

        # Player 101: On IR for 3 weeks (NOT eligible yet)
        conn.execute("""
            INSERT INTO player_injuries (
                dynasty_id, player_id, season, week_occurred,
                injury_type, body_part, severity, estimated_weeks_out,
                occurred_during, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 101, 2025, 7,
            'ANKLE_SPRAIN', 'ANKLE', 'MINOR', 4, 'game', 1
        ))

        # Player 102: On IR for 6 weeks (eligible)
        conn.execute("""
            INSERT INTO player_injuries (
                dynasty_id, player_id, season, week_occurred,
                injury_type, body_part, severity, estimated_weeks_out,
                occurred_during, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 102, 2025, 4,
            'HAMSTRING_STRAIN', 'HAMSTRING', 'MODERATE', 5, 'game', 1
        ))

        # Player 200 (GB): On IR for 5 weeks (eligible)
        conn.execute("""
            INSERT INTO player_injuries (
                dynasty_id, player_id, season, week_occurred,
                injury_type, body_part, severity, estimated_weeks_out,
                occurred_during, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            'test', 200, 2025, 5,
            'SHOULDER_INJURY', 'SHOULDER', 'MODERATE', 5, 'game', 1
        ))

        # Mark IR players as on IR
        for player_id in [100, 101, 102, 200]:
            conn.execute("""
                UPDATE players
                SET team_id = 0
                WHERE dynasty_id = 'test' AND player_id = ?
            """, (player_id,))

        conn.commit()
        db.close()

        yield path

        try:
            os.unlink(path)
        except OSError:
            pass

    def test_get_weekly_ir_eligible_players_returns_eligible(self, temp_db):
        """Returns players on IR for 4+ weeks with IR slots remaining."""
        service = InjuryService(temp_db, 'test', 2025)

        # Week 10: Players 100 (5 weeks) and 102 (6 weeks) should be eligible
        eligible = service.get_weekly_ir_eligible_players(22, 10)

        assert len(eligible) == 2
        player_ids = [p['player_id'] for p in eligible]
        assert 100 in player_ids  # QB, 5 weeks on IR
        assert 102 in player_ids  # WR, 6 weeks on IR
        assert 101 not in player_ids  # Only 3 weeks on IR

    def test_get_weekly_ir_eligible_players_respects_4_week_minimum(self, temp_db):
        """Does not return players under 4 weeks on IR."""
        service = InjuryService(temp_db, 'test', 2025)

        # Week 9: Player 101 has only been on IR for 2 weeks
        eligible = service.get_weekly_ir_eligible_players(22, 9)

        player_ids = [p['player_id'] for p in eligible]
        assert 101 not in player_ids

    def test_get_weekly_ir_eligible_players_empty_when_no_slots(self, temp_db):
        """Returns empty list when no IR return slots remaining."""
        service = InjuryService(temp_db, 'test', 2025)

        # Exhaust IR slots for team 22
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            UPDATE ir_tracking
            SET ir_return_slots_used = 8
            WHERE dynasty_id = 'test' AND team_id = 22
        """)
        conn.commit()
        conn.close()

        eligible = service.get_weekly_ir_eligible_players(22, 10)
        assert len(eligible) == 0

    def test_get_weekly_ir_eligible_players_includes_injury_details(self, temp_db):
        """Returns detailed injury information for each eligible player."""
        service = InjuryService(temp_db, 'test', 2025)

        eligible = service.get_weekly_ir_eligible_players(22, 10)

        qb_player = next(p for p in eligible if p['player_id'] == 100)
        assert qb_player['player_name'] == 'Star Quarterback'
        assert qb_player['position'] == 'QB'
        assert qb_player['overall'] == 88
        assert qb_player['injury_type'] == 'KNEE_SPRAIN'
        assert qb_player['weeks_on_ir'] >= 4

    def test_get_cut_candidates_for_activation_excludes_protected(self, temp_db):
        """Does not return protected position players as cut candidates."""
        service = InjuryService(temp_db, 'test', 2025)

        candidates = service.get_cut_candidates_for_activation(22, num_activations=1)

        # Should not include Player 105 (backup QB - protected position)
        player_ids = [p['player_id'] for p in candidates]
        assert 105 not in player_ids

    def test_get_cut_candidates_for_activation_sorted_by_value(self, temp_db):
        """Returns cut candidates sorted by value (lowest first)."""
        service = InjuryService(temp_db, 'test', 2025)

        candidates = service.get_cut_candidates_for_activation(22, num_activations=1)

        # Should be sorted with lowest value first
        # Player 103 (LB, 68 OVR) should rank lower than Player 104 (CB, 75 OVR)
        assert len(candidates) >= 2

        lb_idx = next(i for i, p in enumerate(candidates) if p['player_id'] == 103)
        cb_idx = next(i for i, p in enumerate(candidates) if p['player_id'] == 104)

        # LB (lower OVR) should come before CB (higher OVR) in cut candidate list
        assert lb_idx < cb_idx

    def test_get_cut_candidates_for_activation_includes_value_calculation(self, temp_db):
        """Includes calculated value score for each candidate."""
        service = InjuryService(temp_db, 'test', 2025)

        candidates = service.get_cut_candidates_for_activation(22, num_activations=1)

        for candidate in candidates:
            assert 'value_score' in candidate
            assert isinstance(candidate['value_score'], (int, float))

    def test_execute_batch_ir_activations_success(self, temp_db):
        """Successfully executes batch IR activations with cuts."""
        service = InjuryService(temp_db, 'test', 2025)

        activations = [
            {'player_to_activate': 100, 'player_to_cut': 103}  # Activate QB, cut LB
        ]

        result = service.execute_batch_ir_activations(22, activations, 10)

        assert result['success'] is True
        assert len(result['activations']) == 1
        assert len(result['cuts']) == 1
        assert result['activations'][0]['player_id'] == 100
        assert result['cuts'][0]['player_id'] == 103

        # Verify database state
        conn = sqlite3.connect(temp_db)

        # Player 100 should be back on team 22
        cursor = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = 'test' AND player_id = 100"
        )
        assert cursor.fetchone()[0] == 22

        # Player 103 should be on team 0 (free agent)
        cursor = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = 'test' AND player_id = 103"
        )
        assert cursor.fetchone()[0] == 0

        # IR slots should be incremented
        cursor = conn.execute("""
            SELECT ir_return_slots_used FROM ir_tracking
            WHERE dynasty_id = 'test' AND team_id = 22
        """)
        assert cursor.fetchone()[0] == 4  # Was 3, now 4

        conn.close()

    def test_execute_batch_ir_activations_multiple(self, temp_db):
        """Handles multiple simultaneous activations."""
        service = InjuryService(temp_db, 'test', 2025)

        activations = [
            {'player_to_activate': 100, 'player_to_cut': 103},  # QB -> cut LB
            {'player_to_activate': 102, 'player_to_cut': 104}   # WR -> cut CB
        ]

        result = service.execute_batch_ir_activations(22, activations, 10)

        assert result['success'] is True
        assert len(result['activations']) == 2
        assert len(result['cuts']) == 2

        # Verify IR slots incremented by 2
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT ir_return_slots_used FROM ir_tracking
            WHERE dynasty_id = 'test' AND team_id = 22
        """)
        assert cursor.fetchone()[0] == 5  # Was 3, now 5
        conn.close()

    def test_execute_batch_ir_activations_atomic_rollback(self, temp_db):
        """Rolls back entire transaction on any error."""
        service = InjuryService(temp_db, 'test', 2025)

        # Include one invalid activation (player not on IR)
        activations = [
            {'player_to_activate': 100, 'player_to_cut': 103},  # Valid
            {'player_to_activate': 999, 'player_to_cut': 104}   # Invalid player ID
        ]

        result = service.execute_batch_ir_activations(22, activations, 10)

        assert result['success'] is False
        assert 'errors' in result

        # Verify no changes were made (atomic rollback)
        conn = sqlite3.connect(temp_db)

        # Player 100 should still be on IR (team_id = 0)
        cursor = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = 'test' AND player_id = 100"
        )
        assert cursor.fetchone()[0] == 0

        # Player 103 should still be on team 22
        cursor = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = 'test' AND player_id = 103"
        )
        assert cursor.fetchone()[0] == 22

        # IR slots should not have changed
        cursor = conn.execute("""
            SELECT ir_return_slots_used FROM ir_tracking
            WHERE dynasty_id = 'test' AND team_id = 22
        """)
        assert cursor.fetchone()[0] == 3  # Still 3

        conn.close()

    def test_should_ai_activate_player_high_overall(self, temp_db):
        """AI activates high-value starters (75+ OVR)."""
        service = InjuryService(temp_db, 'test', 2025)

        ir_player = {
            'player_id': 100,
            'position': 'QB',
            'overall': 88,
            'weeks_on_ir': 5
        }

        team_roster = []  # Empty roster for simplicity
        weeks_remaining = 8

        should_activate = service.should_ai_activate_player(
            ir_player, team_roster, weeks_remaining
        )

        assert should_activate is True  # High OVR, plenty of weeks

    def test_should_ai_activate_player_low_overall(self, temp_db):
        """AI does not activate low-value backups (<75 OVR)."""
        service = InjuryService(temp_db, 'test', 2025)

        ir_player = {
            'player_id': 101,
            'position': 'RB',
            'overall': 72,
            'weeks_on_ir': 5
        }

        team_roster = []
        weeks_remaining = 8

        should_activate = service.should_ai_activate_player(
            ir_player, team_roster, weeks_remaining
        )

        assert should_activate is False  # Below 75 OVR threshold

    def test_should_ai_activate_player_insufficient_weeks(self, temp_db):
        """AI does not activate if less than 4 weeks remaining."""
        service = InjuryService(temp_db, 'test', 2025)

        ir_player = {
            'player_id': 100,
            'position': 'QB',
            'overall': 88,
            'weeks_on_ir': 5
        }

        team_roster = []
        weeks_remaining = 3  # Only 3 weeks left

        should_activate = service.should_ai_activate_player(
            ir_player, team_roster, weeks_remaining
        )

        assert should_activate is False  # Not enough weeks to justify

    def test_should_ai_activate_player_critical_position_need(self, temp_db):
        """AI activates even medium players if position depth is critical."""
        service = InjuryService(temp_db, 'test', 2025)

        ir_player = {
            'player_id': 102,
            'position': 'WR',
            'overall': 76,  # Just above threshold
            'weeks_on_ir': 5
        }

        # Team has only 2 WRs (critical depth)
        team_roster = [
            {'position': 'WR', 'overall': 80},
            {'position': 'WR', 'overall': 75}
        ]
        weeks_remaining = 8

        should_activate = service.should_ai_activate_player(
            ir_player, team_roster, weeks_remaining
        )

        assert should_activate is True  # Critical position need

    def test_process_ai_ir_activations_single_team(self, temp_db):
        """Processes AI IR activations for single team."""
        service = InjuryService(temp_db, 'test', 2025)

        result = service.process_ai_ir_activations([23], 10)

        assert 'teams_processed' in result
        assert 23 in result['teams_processed']

        # Check if team 23's player was evaluated
        team_result = result['teams_processed'][23]
        assert 'eligible_count' in team_result
        assert 'activated_count' in team_result

    def test_process_ai_ir_activations_multiple_teams(self, temp_db):
        """Processes multiple AI teams in batch."""
        service = InjuryService(temp_db, 'test', 2025)

        # Add another team with IR player
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO teams (team_id, name, abbreviation, conference, division)
            VALUES (24, 'Test Team', 'TST', 'NFC', 'North')
        """)
        conn.execute("""
            INSERT INTO ir_tracking (dynasty_id, team_id, season, ir_return_slots_used)
            VALUES ('test', 24, 2025, 0)
        """)
        conn.commit()
        conn.close()

        result = service.process_ai_ir_activations([23, 24], 10)

        assert len(result['teams_processed']) == 2
        assert 23 in result['teams_processed']
        assert 24 in result['teams_processed']

    def test_process_ai_ir_activations_empty_when_no_eligible(self, temp_db):
        """Returns zero activations when no eligible players."""
        service = InjuryService(temp_db, 'test', 2025)

        # Use team 22 but at week 5 (before players are eligible)
        result = service.process_ai_ir_activations([22], 5)

        team_result = result['teams_processed'][22]
        assert team_result['activated_count'] == 0

    def test_get_weekly_ir_eligible_players_dynasty_isolation(self, temp_db):
        """Only returns players from current dynasty."""
        # Create a second dynasty
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO dynasties (dynasty_id, name, team_id)
            VALUES ('other', 'Other Dynasty', 23)
        """)
        conn.commit()
        conn.close()

        service = InjuryService(temp_db, 'test', 2025)
        eligible = service.get_weekly_ir_eligible_players(22, 10)

        # Should only get players from 'test' dynasty
        for player in eligible:
            # Verify by checking team_id matches expected dynasty teams
            assert player['team_id'] in [0, 22]  # IR or Detroit

    def test_execute_batch_ir_activations_logs_transactions(self, temp_db):
        """Logs both cut and activation transactions."""
        service = InjuryService(temp_db, 'test', 2025)

        activations = [
            {'player_to_activate': 100, 'player_to_cut': 103}
        ]

        result = service.execute_batch_ir_activations(22, activations, 10)

        assert result['success'] is True

        # Verify transaction logs exist
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT COUNT(*) FROM transactions
            WHERE dynasty_id = 'test' AND team_id = 22
        """)
        transaction_count = cursor.fetchone()[0]
        assert transaction_count >= 2  # At least cut + activation

        conn.close()
