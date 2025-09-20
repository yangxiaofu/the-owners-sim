"""
Mock Database Connection

Fake database implementation for testing persistence without a real database.
"""

from typing import List, Dict, Any, Optional
import sqlite3


class MockDatabaseConnection:
    """
    Mock database connection for testing.
    
    Stores data in memory instead of a real database.
    Allows testing of persistence logic without database dependencies.
    """
    
    def __init__(self, should_fail: bool = False):
        """
        Initialize mock database.
        
        Args:
            should_fail: If True, database operations will raise exceptions
        """
        self.should_fail = should_fail
        
        # Store data in memory
        self.saved_games = []
        self.saved_player_stats = []
        self.saved_standings = []
        
        # Track operations
        self.transaction_count = 0
        self.rollback_count = 0
        self.commit_count = 0
        self.queries_executed = []
        
        # Current transaction state
        self._in_transaction = False
        self._transaction_buffer = []
    
    def get_connection(self):
        """
        Get a mock connection object.
        
        Returns:
            Self, as the mock acts as its own connection
        """
        return self
    
    def execute(self, query: str, params: tuple = None):
        """
        Mock execute method for SQL queries.
        
        Args:
            query: SQL query string
            params: Query parameters
        """
        if self.should_fail:
            raise Exception("Mock database failure")
        
        # Track the query
        self.queries_executed.append((query, params))
        
        # Handle transaction commands
        if query == "BEGIN TRANSACTION":
            self._in_transaction = True
            self.transaction_count += 1
            self._transaction_buffer = []
            return
        
        elif query == "COMMIT":
            if self._in_transaction:
                # Apply buffered operations
                for buffered_query, buffered_params in self._transaction_buffer:
                    self._apply_query(buffered_query, buffered_params)
                self._in_transaction = False
                self._transaction_buffer = []
                self.commit_count += 1
            return
        
        elif query == "ROLLBACK":
            if self._in_transaction:
                # Discard buffered operations
                self._in_transaction = False
                self._transaction_buffer = []
                self.rollback_count += 1
            return
        
        # Buffer or apply regular queries
        if self._in_transaction:
            self._transaction_buffer.append((query, params))
        else:
            self._apply_query(query, params)
    
    def _apply_query(self, query: str, params: tuple = None):
        """
        Apply a query to the mock storage.
        
        Args:
            query: SQL query string
            params: Query parameters
        """
        if not query or not params:
            return
        
        # Parse query type and store data accordingly
        query_lower = query.lower()
        
        if 'games' in query_lower and ('insert' in query_lower or 'replace' in query_lower):
            # Save game data
            game_data = {
                'game_id': params[0] if len(params) > 0 else None,
                'dynasty_id': params[1] if len(params) > 1 else None,
                'season': params[2] if len(params) > 2 else None,
                'week': params[3] if len(params) > 3 else None,
                'home_team_id': params[4] if len(params) > 4 else None,
                'away_team_id': params[5] if len(params) > 5 else None,
                'home_score': params[6] if len(params) > 6 else None,
                'away_score': params[7] if len(params) > 7 else None,
                'query': query,
                'params': params
            }
            self.saved_games.append(game_data)
        
        elif 'player_game_stats' in query_lower and 'insert' in query_lower:
            # Save player stats
            stat_data = {
                'dynasty_id': params[0] if len(params) > 0 else None,
                'game_id': params[1] if len(params) > 1 else None,
                'player_id': params[2] if len(params) > 2 else None,
                'player_name': params[3] if len(params) > 3 else None,
                'team_id': params[4] if len(params) > 4 else None,
                'position': params[5] if len(params) > 5 else None,
                'query': query,
                'params': params
            }
            self.saved_player_stats.append(stat_data)
        
        elif 'standings' in query_lower and ('insert' in query_lower or 'replace' in query_lower):
            # Save standings
            standing_data = {
                'dynasty_id': params[0] if len(params) > 0 else None,
                'team_id': params[1] if len(params) > 1 else None,
                'season': params[2] if len(params) > 2 else None,
                'wins': params[3] if len(params) > 3 else None,
                'losses': params[4] if len(params) > 4 else None,
                'query': query,
                'params': params
            }
            self.saved_standings.append(standing_data)
    
    def close(self):
        """Mock close method - does nothing."""
        pass
    
    def row_factory(self):
        """Mock row factory - does nothing."""
        pass
    
    # Helper methods for testing
    
    def get_saved_game_ids(self) -> List[str]:
        """Get list of saved game IDs."""
        return [game['game_id'] for game in self.saved_games if game.get('game_id')]
    
    def get_saved_player_count(self) -> int:
        """Get count of saved player statistics."""
        return len(self.saved_player_stats)
    
    def get_saved_standings_count(self) -> int:
        """Get count of saved standings records."""
        return len(self.saved_standings)
    
    def was_transaction_used(self) -> bool:
        """Check if transactions were used."""
        return self.transaction_count > 0
    
    def was_committed(self) -> bool:
        """Check if transactions were committed."""
        return self.commit_count > 0
    
    def was_rolled_back(self) -> bool:
        """Check if any transactions were rolled back."""
        return self.rollback_count > 0
    
    def reset(self):
        """Reset all mock data."""
        self.saved_games = []
        self.saved_player_stats = []
        self.saved_standings = []
        self.transaction_count = 0
        self.rollback_count = 0
        self.commit_count = 0
        self.queries_executed = []
        self._in_transaction = False
        self._transaction_buffer = []
    
    def set_should_fail(self, should_fail: bool):
        """
        Set whether database operations should fail.
        
        Args:
            should_fail: If True, operations will raise exceptions
        """
        self.should_fail = should_fail