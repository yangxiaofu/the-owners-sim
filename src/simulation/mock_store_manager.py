"""
Mock Store Manager for Testing

Simplified store manager for Phase 1 testing without complex dependencies.
"""

from typing import Dict, Any, Optional
from datetime import date


class MockStoreManager:
    """
    Simplified store manager for testing Phase 1 components.
    
    This mock version avoids complex dependencies while providing
    the basic interface needed for season initialization.
    """
    
    def __init__(self):
        """Initialize mock stores."""
        self.game_results = {}
        self.player_stats = {}
        self.standings = {}
        self.box_scores = {}
    
    def add_game_result(self, game_id: str, result: Dict[str, Any]) -> None:
        """Add a game result to the store."""
        self.game_results[game_id] = result
    
    def get_games_for_date(self, game_date: date) -> Dict[str, Any]:
        """Get all games for a specific date."""
        results = {}
        for game_id, result in self.game_results.items():
            if result.get('date') == game_date:
                results[game_id] = result
        return results
    
    def clear_date(self, clear_date: date) -> None:
        """Clear all data for a specific date."""
        # Remove games for this date
        games_to_remove = []
        for game_id, result in self.game_results.items():
            if result.get('date') == clear_date:
                games_to_remove.append(game_id)
        
        for game_id in games_to_remove:
            del self.game_results[game_id]
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get a snapshot of all store data."""
        return {
            'game_results': self.game_results.copy(),
            'player_stats': self.player_stats.copy(),
            'standings': self.standings.copy(),
            'box_scores': self.box_scores.copy()
        }
    
    def __len__(self) -> int:
        """Get total number of stored items."""
        return (
            len(self.game_results) +
            len(self.player_stats) +
            len(self.standings) +
            len(self.box_scores)
        )
    
    def __repr__(self) -> str:
        """String representation."""
        return f"MockStoreManager(games={len(self.game_results)}, stats={len(self.player_stats)})"
