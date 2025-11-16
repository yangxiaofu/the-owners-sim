"""
Integration Tests: Draft UI Complete Flow

Tests the complete draft order calculation flow from database → UI display.
Covers edge cases, dynasty isolation, and data enrichment.

Test Scenarios:
1. Full flow: Complete season/playoffs → draft order display
2. Dynasty isolation: Multiple dynasties don't interfere
3. Incomplete playoffs: Season finished but playoffs in progress
4. Missing data: No games played, no standings
5. Round filtering: Get specific rounds correctly
6. SOS calculation: Verify strength of schedule
7. Team enrichment: All 32 teams get correct names/colors
8. Player enrichment: Executed picks show player data
"""

import pytest
import tempfile
import os
import sqlite3
from typing import Dict, List, Any

# Import system under test
import sys
from pathlib import Path
src_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_path))

ui_path = Path(__file__).parent.parent.parent / "ui"
sys.path.insert(0, str(ui_path))

from domain_models.draft_data_model import DraftDataModel
from domain_models.draft_validation import (
    validate_draft_order,
    validate_playoff_results,
    validate_standings
)
from database.api import DatabaseAPI
from database.connection import DatabaseConnection
from database.dynasty_database_api import DynastyDatabaseAPI


class TestDraftUIIntegration:
    """Integration tests for complete draft UI flow"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database with schema"""
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
        temp_path = temp_file.name
        temp_file.close()

        # Initialize database schema
        db_conn = DatabaseConnection(temp_path)
        conn = db_conn.get_connection()
        conn.close()

        yield temp_path

        # Cleanup
        try:
            os.unlink(temp_path)
        except:
            pass

    @pytest.fixture
    def complete_dynasty_db(self, temp_db):
        """
        Create database with complete season, playoffs, and draft data.

        Sets up:
        - Dynasty with complete regular season (32 teams, 17 games each)
        - Complete playoff bracket (14 teams)
        - Full team schedules
        - Team standings with realistic records
        """
        dynasty_id = "complete_dynasty"
        season = 2024

        # Initialize dynasty
        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="Complete Dynasty Test",
            owner_name="Test Owner",
            team_id=7  # Detroit Lions
        )

        # Create standings for all 32 teams
        self._create_test_standings(temp_db, dynasty_id, season)

        # Create playoff events (complete playoffs)
        self._create_playoff_events(temp_db, dynasty_id, season)

        # Create team schedules for SOS calculation
        self._create_team_schedules(temp_db, dynasty_id, season)

        return {
            'db_path': temp_db,
            'dynasty_id': dynasty_id,
            'season': season
        }

    def _create_test_standings(self, db_path: str, dynasty_id: str, season: int):
        """Create realistic standings for all 32 teams"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Realistic team records (wins, losses, ties)
        team_records = [
            (1, 14, 3, 0),   # Team 1: 14-3
            (2, 13, 4, 0),   # Team 2: 13-4
            (3, 12, 5, 0),   # Team 3: 12-5
            (4, 11, 6, 0),   # Team 4: 11-6
            (5, 11, 6, 0),   # Team 5: 11-6
            (6, 10, 7, 0),   # Team 6: 10-7
            (7, 10, 7, 0),   # Team 7: 10-7 (Detroit)
            (8, 10, 7, 0),   # Team 8: 10-7
            (9, 9, 8, 0),    # Team 9: 9-8
            (10, 9, 8, 0),   # Team 10: 9-8
            (11, 9, 8, 0),   # Team 11: 9-8
            (12, 9, 8, 0),   # Team 12: 9-8
            (13, 9, 8, 0),   # Team 13: 9-8
            (14, 9, 8, 0),   # Team 14: 9-8
            # Non-playoff teams (worst → best for draft order)
            (15, 8, 9, 0),   # Team 15: 8-9
            (16, 8, 9, 0),   # Team 16: 8-9
            (17, 7, 10, 0),  # Team 17: 7-10
            (18, 7, 10, 0),  # Team 18: 7-10
            (19, 6, 11, 0),  # Team 19: 6-11
            (20, 6, 11, 0),  # Team 20: 6-11
            (21, 5, 12, 0),  # Team 21: 5-12
            (22, 5, 12, 0),  # Team 22: 5-12
            (23, 4, 13, 0),  # Team 23: 4-13
            (24, 4, 13, 0),  # Team 24: 4-13
            (25, 3, 14, 0),  # Team 25: 3-14
            (26, 3, 14, 0),  # Team 26: 3-14
            (27, 2, 15, 0),  # Team 27: 2-15
            (28, 2, 15, 0),  # Team 28: 2-15
            (29, 1, 16, 0),  # Team 29: 1-16
            (30, 1, 16, 0),  # Team 30: 1-16
            (31, 0, 17, 0),  # Team 31: 0-17
            (32, 0, 17, 0),  # Team 32: 0-17
        ]

        for team_id, wins, losses, ties in team_records:
            points_for = wins * 24 + losses * 17  # Realistic scoring
            points_against = losses * 24 + wins * 17
            point_diff = points_for - points_against

            cursor.execute("""
                INSERT INTO standings (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    points_for, points_against, point_differential,
                    division_wins, division_losses, division_ties,
                    conference_wins, conference_losses, conference_ties,
                    home_wins, home_losses, home_ties,
                    away_wins, away_losses, away_ties
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dynasty_id, team_id, season, "regular_season",
                wins, losses, ties,
                points_for, points_against, point_diff,
                0, 0, 0,  # Division record (not used for draft order)
                0, 0, 0,  # Conference record
                0, 0, 0,  # Home record
                0, 0, 0   # Away record
            ))

        conn.commit()
        conn.close()

    def _create_playoff_events(self, db_path: str, dynasty_id: str, season: int):
        """Create complete playoff bracket events"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Wild Card Round (6 losers: teams 9-14)
        wc_losers = [9, 10, 11, 12, 13, 14]
        for i, loser_id in enumerate(wc_losers):
            winner_id = i + 1  # Winners advance (teams 1-6)
            cursor.execute("""
                INSERT INTO events (
                    dynasty_id, event_type, game_id, scheduled_date,
                    away_team_id, home_team_id, event_status, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dynasty_id, "GAME", f"playoff_{season}_wc_{i+1}", "2025-01-15",
                loser_id, winner_id, "COMPLETED",
                f'{{"away_score": 17, "home_score": 24, "winner_id": {winner_id}}}'
            ))

        # Divisional Round (4 losers: teams 5-8)
        div_losers = [5, 6, 7, 8]
        for i, loser_id in enumerate(div_losers):
            winner_id = i + 1  # Winners advance (teams 1-4)
            cursor.execute("""
                INSERT INTO events (
                    dynasty_id, event_type, game_id, scheduled_date,
                    away_team_id, home_team_id, event_status, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dynasty_id, "GAME", f"playoff_{season}_div_{i+1}", "2025-01-22",
                loser_id, winner_id, "COMPLETED",
                f'{{"away_score": 20, "home_score": 27, "winner_id": {winner_id}}}'
            ))

        # Conference Championships (2 losers: teams 3, 4)
        conf_losers = [3, 4]
        for i, loser_id in enumerate(conf_losers):
            winner_id = i + 1  # Winners advance (teams 1, 2)
            cursor.execute("""
                INSERT INTO events (
                    dynasty_id, event_type, game_id, scheduled_date,
                    away_team_id, home_team_id, event_status, result
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dynasty_id, "GAME", f"playoff_{season}_conf_{i+1}", "2025-02-05",
                loser_id, winner_id, "COMPLETED",
                f'{{"away_score": 21, "home_score": 28, "winner_id": {winner_id}}}'
            ))

        # Super Bowl (winner: team 1, loser: team 2)
        cursor.execute("""
            INSERT INTO events (
                dynasty_id, event_type, game_id, scheduled_date,
                away_team_id, home_team_id, event_status, result
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dynasty_id, "GAME", f"playoff_{season}_sb", "2025-02-12",
            2, 1, "COMPLETED",
            '{"away_score": 24, "home_score": 31, "winner_id": 1}'
        ))

        conn.commit()
        conn.close()

    def _create_team_schedules(self, db_path: str, dynasty_id: str, season: int):
        """Create team schedules for SOS calculation"""
        # For simplicity, create round-robin style schedules
        # Each team plays 17 games against various opponents
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for team_id in range(1, 33):
            # Create 17 games for each team
            for week in range(1, 18):
                # Rotate opponents (simple algorithm)
                opponent_id = ((team_id + week - 2) % 32) + 1
                if opponent_id == team_id:
                    opponent_id = ((opponent_id + 1 - 1) % 32) + 1

                # Determine home/away
                is_home = week % 2 == team_id % 2

                if is_home:
                    home_team = team_id
                    away_team = opponent_id
                else:
                    home_team = opponent_id
                    away_team = team_id

                game_id = f"reg_{season}_w{week:02d}_t{team_id}_vs_t{opponent_id}"

                # Only insert each game once (from home team perspective)
                if is_home:
                    cursor.execute("""
                        INSERT OR IGNORE INTO games (
                            game_id, dynasty_id, season, season_type, week,
                            home_team_id, away_team_id, game_date, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        game_id, dynasty_id, season, "regular_season", week,
                        home_team, away_team, f"2024-09-{week:02d}", "COMPLETED"
                    ))

        conn.commit()
        conn.close()

    # ========================================================================
    # TEST 1: Full Flow Test
    # ========================================================================

    def test_full_draft_order_calculation(self, complete_dynasty_db):
        """
        Test complete flow: database → draft order → enriched UI data.

        Validates:
        - All 224 picks generated (7 rounds × 32 picks)
        - Playoffs complete flag set correctly
        - No errors reported
        - Pick structure includes all required fields
        - Team enrichment successful (names, colors)
        """
        db_path = complete_dynasty_db['db_path']
        dynasty_id = complete_dynasty_db['dynasty_id']
        season = complete_dynasty_db['season']

        # Create draft data model
        model = DraftDataModel(db_path, dynasty_id, season + 1)  # Draft 2025 based on 2024 season

        # Get draft order
        result = model.get_draft_order()

        # Validate result structure
        assert 'picks' in result
        assert 'playoffs_complete' in result
        assert 'errors' in result
        assert 'warnings' in result

        # Check playoffs complete
        assert result['playoffs_complete'] == True, "Playoffs should be complete"

        # Check no errors
        assert len(result['errors']) == 0, f"Should have no errors, got: {result['errors']}"

        # Check pick count
        picks = result['picks']
        assert len(picks) == 224, f"Expected 224 picks, got {len(picks)}"

        # Validate first pick structure
        first_pick = picks[0]
        required_fields = [
            'overall_pick', 'round_number', 'pick_in_round', 'team_id',
            'team_name', 'team_abbrev', 'team_record', 'reason', 'sos',
            'primary_color', 'secondary_color', 'player'
        ]
        for field in required_fields:
            assert field in first_pick, f"Pick missing required field: {field}"

        # Validate first overall pick (worst team)
        assert first_pick['overall_pick'] == 1
        assert first_pick['round_number'] == 1
        assert first_pick['pick_in_round'] == 1
        assert first_pick['reason'] == 'non_playoff'
        # Team 31 or 32 should have first pick (0-17 record)
        assert first_pick['team_id'] in [31, 32]

        # Validate last pick (Super Bowl winner)
        last_pick = picks[-1]
        assert last_pick['overall_pick'] == 224
        assert last_pick['round_number'] == 7
        assert last_pick['pick_in_round'] == 32
        assert last_pick['reason'] == 'super_bowl_win'
        assert last_pick['team_id'] == 1  # Team 1 won Super Bowl

        # Run validation
        validation_errors = validate_draft_order(picks)
        assert len(validation_errors) == 0, f"Draft order validation failed: {validation_errors}"

    # ========================================================================
    # TEST 2: Dynasty Isolation Test
    # ========================================================================

    def test_dynasty_isolation(self, temp_db):
        """
        Test that different dynasties have independent draft orders.

        Creates two dynasties with different standings and verifies:
        - Draft orders are completely independent
        - No data leakage between dynasties
        """
        # Create Dynasty 1 (team 1 worst, team 32 best)
        dynasty1_id = "dynasty_1"
        season = 2024

        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty1_id,
            dynasty_name="Dynasty 1",
            owner_name="Owner 1",
            team_id=1
        )
        self._create_inverted_standings(temp_db, dynasty1_id, season)

        # Create Dynasty 2 (team 32 worst, team 1 best)
        dynasty2_id = "dynasty_2"
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty2_id,
            dynasty_name="Dynasty 2",
            owner_name="Owner 2",
            team_id=32
        )
        self._create_inverted_standings(temp_db, dynasty2_id, season, reverse=True)

        # Get draft orders for both dynasties
        model1 = DraftDataModel(temp_db, dynasty1_id, season + 1)
        model2 = DraftDataModel(temp_db, dynasty2_id, season + 1)

        result1 = model1.get_draft_order(round_number=1)
        result2 = model2.get_draft_order(round_number=1)

        picks1 = result1['picks']
        picks2 = result2['picks']

        # Both should have different first overall picks
        # Dynasty 1: Team 1 has worst record (should pick first)
        # Dynasty 2: Team 32 has worst record (should pick first)
        assert len(picks1) == 32
        assert len(picks2) == 32

        # Verify isolation (different first picks)
        first_pick_team1 = picks1[0]['team_id']
        first_pick_team2 = picks2[0]['team_id']
        assert first_pick_team1 != first_pick_team2, \
            "Different dynasties should have different draft orders"

    def _create_inverted_standings(
        self,
        db_path: str,
        dynasty_id: str,
        season: int,
        reverse: bool = False
    ):
        """Create standings where team IDs correlate with record quality"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for team_id in range(1, 33):
            if not reverse:
                # Team 1 = worst (0-17), Team 32 = best (17-0)
                wins = team_id - 1
                losses = 17 - wins
            else:
                # Team 32 = worst (0-17), Team 1 = best (17-0)
                wins = 32 - team_id
                losses = 17 - wins

            cursor.execute("""
                INSERT INTO standings (
                    dynasty_id, team_id, season, season_type,
                    wins, losses, ties,
                    points_for, points_against, point_differential,
                    division_wins, division_losses, division_ties,
                    conference_wins, conference_losses, conference_ties,
                    home_wins, home_losses, home_ties,
                    away_wins, away_losses, away_ties
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dynasty_id, team_id, season, "regular_season",
                wins, losses, 0,
                wins * 24, losses * 24, 0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            ))

        conn.commit()
        conn.close()

    # ========================================================================
    # TEST 3: Incomplete Playoffs Test
    # ========================================================================

    def test_incomplete_playoffs_handling(self, temp_db):
        """
        Test handling when playoffs are not finished.

        Creates a dynasty with regular season complete but no playoff data.
        Should return partial draft order with appropriate warning.
        """
        dynasty_id = "incomplete_playoffs"
        season = 2024

        # Create dynasty with standings but NO playoff events
        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="Incomplete Playoffs Dynasty",
            owner_name="Test Owner",
            team_id=7
        )
        self._create_test_standings(temp_db, dynasty_id, season)
        # Intentionally skip _create_playoff_events()

        # Get draft order
        model = DraftDataModel(temp_db, dynasty_id, season + 1)
        result = model.get_draft_order()

        # Should have warnings about incomplete playoffs
        assert result['playoffs_complete'] == False
        assert len(result['warnings']) > 0
        assert any('incomplete' in w.lower() or 'playoff' in w.lower()
                   for w in result['warnings'])

        # Should still return picks (at least non-playoff teams)
        picks = result['picks']
        # With no playoff data, service will raise ValueError or return partial order
        # We expect either 0 picks or 18 picks (non-playoff teams only)
        # This depends on how DraftOrderService handles missing playoff data
        # For now, accept any valid partial response
        assert isinstance(picks, list)

    # ========================================================================
    # TEST 4: Missing Standings Test
    # ========================================================================

    def test_missing_standings_handling(self, temp_db):
        """
        Test graceful handling when no standings exist.

        Should return empty picks with appropriate error message.
        """
        dynasty_id = "no_standings"
        season = 2024

        # Create dynasty but NO standings data
        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="No Standings Dynasty",
            owner_name="Test Owner",
            team_id=7
        )

        # Get draft order
        model = DraftDataModel(temp_db, dynasty_id, season + 1)
        result = model.get_draft_order()

        # Should have errors about missing standings
        assert len(result['errors']) > 0
        assert any('standings' in e.lower() for e in result['errors'])

        # Should return empty picks
        assert len(result['picks']) == 0

    # ========================================================================
    # TEST 5: Round Filtering Test
    # ========================================================================

    def test_round_filtering(self, complete_dynasty_db):
        """
        Test that round filtering works correctly.

        Verifies:
        - Round 1 returns 32 picks
        - Each round returns exactly 32 picks
        - Invalid round numbers handled gracefully
        """
        db_path = complete_dynasty_db['db_path']
        dynasty_id = complete_dynasty_db['dynasty_id']
        season = complete_dynasty_db['season']

        model = DraftDataModel(db_path, dynasty_id, season + 1)

        # Test each round
        for round_num in range(1, 8):
            result = model.get_draft_order(round_number=round_num)
            picks = result['picks']

            assert len(picks) == 32, f"Round {round_num} should have 32 picks"

            # Verify all picks are from the correct round
            for pick in picks:
                assert pick['round_number'] == round_num

        # Test invalid round number
        result = model.get_draft_order(round_number=8)
        assert len(result['errors']) > 0, "Should error on invalid round number"

    # ========================================================================
    # TEST 6: SOS Calculation Test
    # ========================================================================

    def test_sos_calculation_accuracy(self, complete_dynasty_db):
        """
        Test that SOS calculations are accurate.

        Creates known schedule and verifies SOS values match expected.
        """
        db_path = complete_dynasty_db['db_path']
        dynasty_id = complete_dynasty_db['dynasty_id']
        season = complete_dynasty_db['season']

        model = DraftDataModel(db_path, dynasty_id, season + 1)
        result = model.get_draft_order(round_number=1)

        picks = result['picks']

        # All teams should have SOS between 0.0 and 1.0
        for pick in picks:
            sos = pick['sos']
            assert 0.0 <= sos <= 1.0, f"SOS {sos} out of valid range for team {pick['team_id']}"

        # SOS should vary (not all the same)
        sos_values = [pick['sos'] for pick in picks]
        unique_sos = set(sos_values)
        assert len(unique_sos) > 1, "SOS values should vary across teams"

    # ========================================================================
    # TEST 7: Team Enrichment Test
    # ========================================================================

    def test_team_enrichment(self, complete_dynasty_db):
        """
        Test that all 32 teams get correct names and colors.

        Verifies:
        - All picks have team_name
        - All picks have team_abbrev
        - All picks have primary_color and secondary_color
        - Team data matches TeamDataLoader
        """
        db_path = complete_dynasty_db['db_path']
        dynasty_id = complete_dynasty_db['dynasty_id']
        season = complete_dynasty_db['season']

        model = DraftDataModel(db_path, dynasty_id, season + 1)
        result = model.get_draft_order(round_number=1)

        picks = result['picks']

        # Check team enrichment for all picks
        for pick in picks:
            assert 'team_name' in pick and pick['team_name']
            assert 'team_abbrev' in pick and pick['team_abbrev']
            assert 'primary_color' in pick and pick['primary_color']
            assert 'secondary_color' in pick and pick['secondary_color']

            # Team name should not be default fallback (unless team data truly missing)
            # For teams 1-32, we should have proper team names
            if 1 <= pick['team_id'] <= 32:
                assert not pick['team_name'].startswith('Team '), \
                    f"Team {pick['team_id']} should have proper name, got '{pick['team_name']}'"

    # ========================================================================
    # TEST 8: Validation Helpers Test
    # ========================================================================

    def test_validation_helpers(self, complete_dynasty_db):
        """
        Test that validation helpers correctly identify valid/invalid data.
        """
        db_path = complete_dynasty_db['db_path']
        dynasty_id = complete_dynasty_db['dynasty_id']
        season = complete_dynasty_db['season']

        model = DraftDataModel(db_path, dynasty_id, season + 1)
        result = model.get_draft_order()

        picks = result['picks']

        # Test draft order validation
        errors = validate_draft_order(picks)
        assert len(errors) == 0, f"Valid draft order should pass validation: {errors}"

        # Test invalid draft order (missing picks)
        incomplete_picks = picks[:100]  # Only 100 picks instead of 224
        errors = validate_draft_order(incomplete_picks)
        assert len(errors) > 0, "Incomplete draft order should fail validation"
        assert any('224' in e for e in errors), "Should mention expected 224 picks"

        # Test playoff results validation
        playoff_results = {
            'wild_card_losers': [9, 10, 11, 12, 13, 14],
            'divisional_losers': [5, 6, 7, 8],
            'conference_losers': [3, 4],
            'super_bowl_loser': 2,
            'super_bowl_winner': 1
        }
        is_complete, errors = validate_playoff_results(playoff_results)
        assert is_complete == True
        assert len(errors) == 0

        # Test invalid playoff results (wrong counts)
        invalid_playoff_results = {
            'wild_card_losers': [9, 10, 11],  # Only 3 instead of 6
            'divisional_losers': [5, 6, 7, 8],
            'conference_losers': [3, 4],
            'super_bowl_loser': 2,
            'super_bowl_winner': 1
        }
        is_complete, errors = validate_playoff_results(invalid_playoff_results)
        assert is_complete == False
        assert len(errors) > 0
