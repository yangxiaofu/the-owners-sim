#!/usr/bin/env python3
"""
Test Daily Data Persister

Tests for the daily persistence pipeline from stores to database.
"""

import sys
import unittest
from datetime import date, datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from persistence.daily_persister import DailyDataPersister
from stores.store_manager import StoreManager
# DaySimulationResult removed with calendar system
# from simulation.calendar_manager import DaySimulationResult

# Import the mock from the proper location
sys.path.insert(0, str(Path(__file__).parent))
from mocks.mock_database import MockDatabaseConnection


# Test data classes
@dataclass
class MockGameResult:
    """Mock game result for testing"""
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    total_plays: int = 125
    game_duration_minutes: int = 180
    
@dataclass
class MockPlayerStat:
    """Mock player stat for testing"""
    player_id: str
    player_name: str
    team_id: int
    position: str
    passing_yards: int = 0
    passing_tds: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0

@dataclass
class MockStanding:
    """Mock standing for testing"""
    team_id: int
    season: int
    wins: int
    losses: int
    ties: int = 0
    division_wins: int = 0
    division_losses: int = 0
    conference_wins: int = 0
    conference_losses: int = 0
    points_for: int = 0
    points_against: int = 0


class TestDailyDataPersister(unittest.TestCase):
    """Test suite for DailyDataPersister"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock database
        self.mock_db = MockDatabaseConnection()
        
        # Create store manager
        self.store_manager = StoreManager()
        
        # Create persister
        self.dynasty_id = "test-dynasty-123"
        self.persister = DailyDataPersister(
            self.store_manager,
            self.mock_db,
            self.dynasty_id
        )
        
        # Test date
        self.test_date = date(2024, 9, 15)
    
    def test_persist_empty_day(self):
        """Test persisting a day with no events"""
        # Create day result with no events
        day_result = DaySimulationResult(
            date=self.test_date,
            events_scheduled=0,
            events_executed=0,
            successful_events=0,
            failed_events=0
        )
        
        # Persist
        success = self.persister.persist_day(day_result)
        
        # Should succeed but not save anything
        self.assertTrue(success)
        self.assertEqual(len(self.mock_db.saved_games), 0)
        self.assertEqual(self.mock_db.transaction_count, 0)
    
    def test_persist_game_day(self):
        """Test persisting a day with game results"""
        # Add game to store
        game_id = "2024_week2_DET_KC"
        game_result = MockGameResult(
            home_team_id=22,  # Lions
            away_team_id=16,   # Chiefs
            home_score=24,
            away_score=21
        )
        self.store_manager.game_result_store.data[game_id] = game_result
        
        # Add player stats
        qb_stat = MockPlayerStat(
            player_id="DET_QB_001",
            player_name="Test QB",
            team_id=22,
            position="QB",
            passing_yards=325,
            passing_tds=3
        )
        self.store_manager.player_stats_store.data[game_id] = [qb_stat]
        
        # Add standings
        standing = MockStanding(
            team_id=22,
            season=2024,
            wins=1,
            losses=0
        )
        self.store_manager.standings_store.data[22] = standing
        
        # Create day result
        day_result = DaySimulationResult(
            date=self.test_date,
            events_scheduled=1,
            events_executed=1,
            successful_events=1,
            failed_events=0
        )
        
        # Persist
        success = self.persister.persist_day(day_result)
        
        # Verify success
        self.assertTrue(success)
        
        # Verify data was saved
        self.assertEqual(len(self.mock_db.saved_games), 1)
        self.assertEqual(self.mock_db.saved_games[0]['game_id'], game_id)
        self.assertEqual(self.mock_db.saved_games[0]['dynasty_id'], self.dynasty_id)
        self.assertEqual(self.mock_db.saved_games[0]['home_score'], 24)
        
        # Verify player stats saved
        self.assertEqual(len(self.mock_db.saved_player_stats), 1)
        self.assertEqual(self.mock_db.saved_player_stats[0]['player_name'], "Test QB")
        
        # Verify standings saved
        self.assertEqual(len(self.mock_db.saved_standings), 1)
        self.assertEqual(self.mock_db.saved_standings[0]['wins'], 1)
        
        # Verify transaction was used
        self.assertTrue(self.mock_db.was_transaction_used())
        self.assertTrue(self.mock_db.was_committed())
        
        # Verify stores were cleared
        self.assertEqual(len(self.store_manager.game_result_store.data), 0)
        self.assertEqual(len(self.store_manager.player_stats_store.data), 0)
    
    def test_persist_multiple_games(self):
        """Test persisting multiple games in one day"""
        # Add multiple games
        games = [
            ("2024_week2_DET_KC", MockGameResult(22, 16, 24, 21)),
            ("2024_week2_DAL_NYG", MockGameResult(9, 24, 31, 28)),
            ("2024_week2_GB_CHI", MockGameResult(12, 6, 21, 17))
        ]
        
        for game_id, result in games:
            self.store_manager.game_result_store.data[game_id] = result
        
        # Create day result
        day_result = DaySimulationResult(
            date=self.test_date,
            events_scheduled=3,
            events_executed=3,
            successful_events=3,
            failed_events=0
        )
        
        # Persist
        success = self.persister.persist_day(day_result)
        
        # Verify success
        self.assertTrue(success)
        self.assertEqual(len(self.mock_db.saved_games), 3)
        
        # Verify all games were saved
        saved_game_ids = self.mock_db.get_saved_game_ids()
        for game_id, _ in games:
            self.assertIn(game_id, saved_game_ids)
    
    def test_database_failure_preserves_stores(self):
        """Test that stores are not cleared when database fails"""
        # Add game to store
        game_id = "2024_week2_DET_KC"
        game_result = MockGameResult(22, 16, 24, 21)
        self.store_manager.game_result_store.data[game_id] = game_result
        
        # Set database to fail
        self.mock_db.set_should_fail(True)
        
        # Create day result
        day_result = DaySimulationResult(
            date=self.test_date,
            events_scheduled=1,
            events_executed=1,
            successful_events=1,
            failed_events=0
        )
        
        # Persist (should fail)
        success = self.persister.persist_day(day_result)
        
        # Verify failure
        self.assertFalse(success)
        
        # Verify stores were NOT cleared
        self.assertEqual(len(self.store_manager.game_result_store.data), 1)
        self.assertIn(game_id, self.store_manager.game_result_store.data)
        
        # Verify no data was committed
        self.assertEqual(len(self.mock_db.saved_games), 0)
    
    def test_persistence_statistics(self):
        """Test that persistence statistics are tracked"""
        # Add games for multiple days
        for day in range(3):
            game_id = f"2024_week{day+1}_DET_KC"
            self.store_manager.game_result_store.data[game_id] = MockGameResult(22, 16, 24, 21)
            
            # Create and persist day result
            day_result = DaySimulationResult(
                date=date(2024, 9, 15 + day),
                events_scheduled=1,
                events_executed=1,
                successful_events=1,
                failed_events=0
            )
            self.persister.persist_day(day_result)
        
        # Get statistics
        stats = self.persister.get_statistics()
        
        # Verify statistics
        self.assertEqual(stats['dynasty_id'], self.dynasty_id)
        self.assertEqual(stats['total_days_persisted'], 3)
        self.assertEqual(stats['total_games_persisted'], 3)
    
    def test_transaction_rollback_on_error(self):
        """Test that transaction rolls back on error"""
        # Create a persister with a database that fails mid-transaction
        # This is a more complex test that would require modifying the mock
        # to fail at a specific point in the transaction
        
        # Add game to store
        game_id = "2024_week2_DET_KC"
        game_result = MockGameResult(22, 16, 24, 21)
        self.store_manager.game_result_store.data[game_id] = game_result
        
        # Create a custom mock that fails during commit
        class FailOnCommitMock(MockDatabaseConnection):
            def execute(self, query, params=None):
                if query == "COMMIT":
                    raise Exception("Commit failed!")
                return super().execute(query, params)
        
        fail_db = FailOnCommitMock()
        fail_persister = DailyDataPersister(
            self.store_manager,
            fail_db,
            self.dynasty_id
        )
        
        # Create day result
        day_result = DaySimulationResult(
            date=self.test_date,
            events_scheduled=1,
            events_executed=1,
            successful_events=1,
            failed_events=0
        )
        
        # Persist (should fail)
        success = fail_persister.persist_day(day_result)
        
        # Verify failure
        self.assertFalse(success)
        
        # Verify transaction was started but not committed
        self.assertTrue(fail_db.was_transaction_used())
        self.assertFalse(fail_db.was_committed())


class TestMockDatabase(unittest.TestCase):
    """Test the mock database itself"""
    
    def test_transaction_buffering(self):
        """Test that mock properly buffers transactions"""
        mock_db = MockDatabaseConnection()
        conn = mock_db.get_connection()
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Execute queries
        conn.execute("INSERT INTO games VALUES (?)", ("game1",))
        conn.execute("INSERT INTO games VALUES (?)", ("game2",))
        
        # Nothing should be saved yet
        self.assertEqual(len(mock_db.saved_games), 0)
        
        # Commit
        conn.execute("COMMIT")
        
        # Now data should be saved
        self.assertEqual(len(mock_db.saved_games), 2)
    
    def test_transaction_rollback(self):
        """Test that mock properly handles rollback"""
        mock_db = MockDatabaseConnection()
        conn = mock_db.get_connection()
        
        # Start transaction
        conn.execute("BEGIN TRANSACTION")
        
        # Execute queries
        conn.execute("INSERT INTO games VALUES (?)", ("game1",))
        
        # Rollback
        conn.execute("ROLLBACK")
        
        # Nothing should be saved
        self.assertEqual(len(mock_db.saved_games), 0)
        self.assertTrue(mock_db.was_rolled_back())


if __name__ == "__main__":
    unittest.main()