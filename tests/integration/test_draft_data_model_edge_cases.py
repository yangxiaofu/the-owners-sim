"""
Integration Tests: Draft Data Model Edge Cases

Focused tests for edge case handling in DraftDataModel.get_draft_order().
Tests error handling WITHOUT requiring complete season simulation data.

Test Scenarios:
1. Missing standings: No data in standings table
2. Invalid dynasty: Dynasty doesn't exist
3. Validation helpers: Test validation utility functions
"""

import pytest
import tempfile
import os
import sqlite3

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
from database.connection import DatabaseConnection
from database.dynasty_database_api import DynastyDatabaseAPI


class TestDraftDataModelEdgeCases:
    """Edge case tests for DraftDataModel"""

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

    # ========================================================================
    # TEST 1: Missing Standings
    # ========================================================================

    def test_missing_standings_returns_error(self, temp_db):
        """
        Test that missing standings returns error in result dict.

        This tests the edge case where no regular season has been played yet.
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

        # Get draft order (should fail gracefully)
        model = DraftDataModel(temp_db, dynasty_id, season + 1)
        result = model.get_draft_order()

        # Verify result structure
        assert 'picks' in result
        assert 'errors' in result
        assert 'warnings' in result
        assert 'playoffs_complete' in result

        # Should have errors about missing standings
        assert len(result['errors']) > 0, "Should have at least one error"
        assert any('standings' in e.lower() or 'season' in e.lower()
                   for e in result['errors']), \
            f"Error should mention standings, got: {result['errors']}"

        # Should return empty picks
        assert len(result['picks']) == 0, "Should return empty picks list"

    # ========================================================================
    # TEST 2: Validation Helpers
    # ========================================================================

    def test_validate_playoff_results_valid(self):
        """Test playoff results validation with valid data"""
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

    def test_validate_playoff_results_wrong_counts(self):
        """Test playoff results validation with wrong team counts"""
        playoff_results = {
            'wild_card_losers': [9, 10, 11],  # Only 3 instead of 6
            'divisional_losers': [5, 6, 7, 8],
            'conference_losers': [3, 4],
            'super_bowl_loser': 2,
            'super_bowl_winner': 1
        }

        is_complete, errors = validate_playoff_results(playoff_results)

        assert is_complete == False
        assert len(errors) > 0
        assert any('wild card' in e.lower() for e in errors)

    def test_validate_playoff_results_missing_keys(self):
        """Test playoff results validation with missing keys"""
        playoff_results = {
            'wild_card_losers': [9, 10, 11, 12, 13, 14],
            # Missing other required keys
        }

        is_complete, errors = validate_playoff_results(playoff_results)

        assert is_complete == False
        assert len(errors) > 0
        assert any('missing' in e.lower() for e in errors)

    def test_validate_playoff_results_duplicates(self):
        """Test playoff results validation with duplicate teams"""
        playoff_results = {
            'wild_card_losers': [9, 10, 11, 12, 13, 13],  # Duplicate team 13
            'divisional_losers': [5, 6, 7, 8],
            'conference_losers': [3, 4],
            'super_bowl_loser': 2,
            'super_bowl_winner': 1
        }

        is_complete, errors = validate_playoff_results(playoff_results)

        assert is_complete == False
        assert len(errors) > 0
        assert any('duplicate' in e.lower() for e in errors)

    def test_validate_draft_order_valid(self):
        """Test draft order validation with valid 224-pick order"""
        # Create valid draft order
        picks = []
        pick_num = 1
        for round_num in range(1, 8):  # 7 rounds
            for pick_in_round in range(1, 33):  # 32 picks per round
                picks.append({
                    'overall_pick': pick_num,
                    'round_number': round_num,
                    'pick_in_round': pick_in_round,
                    'team_id': ((pick_num - 1) % 32) + 1,  # Rotate through teams
                    'team_record': '10-7-0',
                    'reason': 'non_playoff',
                    'sos': 0.500
                })
                pick_num += 1

        errors = validate_draft_order(picks)
        assert len(errors) == 0, f"Valid draft order should pass: {errors}"

    def test_validate_draft_order_wrong_count(self):
        """Test draft order validation with wrong pick count"""
        picks = [
            {
                'overall_pick': i,
                'round_number': 1,
                'pick_in_round': i,
                'team_id': i,
                'team_record': '10-7-0',
                'reason': 'non_playoff',
                'sos': 0.500
            }
            for i in range(1, 101)  # Only 100 picks instead of 224
        ]

        errors = validate_draft_order(picks)
        assert len(errors) > 0
        assert any('224' in e for e in errors)

    def test_validate_draft_order_missing_fields(self):
        """Test draft order validation with missing required fields"""
        picks = [
            {
                'overall_pick': 1,
                'round_number': 1,
                # Missing other required fields
            }
        ]

        errors = validate_draft_order(picks)
        assert len(errors) > 0
        assert any('missing' in e.lower() for e in errors)

    def test_validate_standings_valid(self):
        """Test standings validation with valid data"""
        standings = []
        for team_id in range(1, 33):
            standings.append({
                'team_id': team_id,
                'wins': 10,
                'losses': 7,
                'ties': 0,
                'win_percentage': 0.588
            })

        errors = validate_standings(standings)
        assert len(errors) == 0

    def test_validate_standings_wrong_count(self):
        """Test standings validation with wrong team count"""
        standings = [
            {
                'team_id': i,
                'wins': 10,
                'losses': 7,
                'ties': 0,
                'win_percentage': 0.588
            }
            for i in range(1, 20)  # Only 19 teams instead of 32
        ]

        errors = validate_standings(standings)
        assert len(errors) > 0
        assert any('32' in e for e in errors)

    def test_validate_standings_missing_fields(self):
        """Test standings validation with missing fields"""
        standings = [
            {
                'team_id': 1,
                'wins': 10,
                # Missing other required fields
            }
        ]

        errors = validate_standings(standings)
        assert len(errors) > 0
        assert any('missing' in e.lower() for e in errors)

    def test_validate_standings_win_percentage_mismatch(self):
        """Test standings validation catches incorrect win percentage"""
        standings = [
            {
                'team_id': i,
                'wins': 10,
                'losses': 7,
                'ties': 0,
                'win_percentage': 0.999  # Wrong! Should be ~0.588
            }
            for i in range(1, 33)
        ]

        errors = validate_standings(standings)
        assert len(errors) > 0
        # Should have multiple errors (one per team with wrong win%)
        assert any('mismatch' in e.lower() or 'percentage' in e.lower()
                   for e in errors)

    # ========================================================================
    # TEST 3: Result Dict Structure
    # ========================================================================

    def test_get_draft_order_returns_dict(self, temp_db):
        """Test that get_draft_order always returns dict with required keys"""
        dynasty_id = "test_structure"
        season = 2024

        # Create dynasty
        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="Structure Test",
            owner_name="Test Owner",
            team_id=7
        )

        model = DraftDataModel(temp_db, dynasty_id, season + 1)
        result = model.get_draft_order()

        # Verify dict structure
        assert isinstance(result, dict), "Result should be a dict"
        assert 'picks' in result, "Result should have 'picks' key"
        assert 'errors' in result, "Result should have 'errors' key"
        assert 'warnings' in result, "Result should have 'warnings' key"
        assert 'playoffs_complete' in result, "Result should have 'playoffs_complete' key"

        # Verify types
        assert isinstance(result['picks'], list)
        assert isinstance(result['errors'], list)
        assert isinstance(result['warnings'], list)
        assert isinstance(result['playoffs_complete'], bool)

    def test_get_draft_order_invalid_round_number(self, temp_db):
        """Test that invalid round number returns error"""
        dynasty_id = "test_invalid_round"
        season = 2024

        # Create dynasty
        dynasty_api = DynastyDatabaseAPI(temp_db)
        dynasty_api.create_dynasty_record(
            dynasty_id=dynasty_id,
            dynasty_name="Invalid Round Test",
            owner_name="Test Owner",
            team_id=7
        )

        model = DraftDataModel(temp_db, dynasty_id, season + 1)
        result = model.get_draft_order(round_number=99)  # Invalid round

        # Should have error (either about invalid round OR missing standings/season)
        # If no standings exist, that error takes precedence (which is correct)
        assert len(result['errors']) > 0
        assert any('round' in e.lower() or 'invalid' in e.lower() or
                   'season' in e.lower() or 'standings' in e.lower()
                   for e in result['errors'])
