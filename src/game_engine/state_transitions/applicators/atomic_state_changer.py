"""
Atomic State Changer - Low-Level Atomic Operations

This module provides low-level atomic operations with rollback support.
It captures the state before changes and can restore it if any operation fails,
ensuring transaction-like behavior for game state modifications.

Key Features:
- Captures complete state snapshots before changes
- Atomic operations with rollback capability
- Deep copying of complex state objects
- Transaction boundaries with begin/commit/rollback
"""

import copy
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass

from game_engine.field.game_state import GameState


@dataclass
class StateSnapshot:
    """Complete snapshot of game state at a point in time"""
    field_state: Dict[str, Any]
    clock_state: Dict[str, Any]  
    scoreboard_state: Dict[str, Any]
    timestamp: float
    
    @classmethod
    def capture(cls, game_state: GameState) -> 'StateSnapshot':
        """Capture a complete snapshot of the current game state"""
        import time
        
        return cls(
            field_state={
                'down': game_state.field.down,
                'yards_to_go': game_state.field.yards_to_go,
                'field_position': game_state.field.field_position,
                'possession_team_id': game_state.field.possession_team_id,
                'quarter': game_state.field.quarter,
                'game_clock': game_state.field.game_clock
            },
            clock_state={
                'quarter': game_state.clock.quarter,
                'clock': game_state.clock.clock,
                'play_clock': game_state.clock.play_clock
            },
            scoreboard_state={
                'home_score': game_state.scoreboard.home_score,
                'away_score': game_state.scoreboard.away_score,
                'home_team_id': game_state.scoreboard.home_team_id,
                'away_team_id': game_state.scoreboard.away_team_id
            },
            timestamp=time.time()
        )
    
    def restore(self, game_state: GameState) -> None:
        """Restore the game state from this snapshot"""
        # Restore field state
        game_state.field.down = self.field_state['down']
        game_state.field.yards_to_go = self.field_state['yards_to_go']
        game_state.field.field_position = self.field_state['field_position']
        game_state.field.possession_team_id = self.field_state['possession_team_id']
        game_state.field.quarter = self.field_state['quarter']
        game_state.field.game_clock = self.field_state['game_clock']
        
        # Restore clock state
        game_state.clock.quarter = self.clock_state['quarter']
        game_state.clock.clock = self.clock_state['clock']
        game_state.clock.play_clock = self.clock_state['play_clock']
        
        # Restore scoreboard state
        game_state.scoreboard.home_score = self.scoreboard_state['home_score']
        game_state.scoreboard.away_score = self.scoreboard_state['away_score']
        game_state.scoreboard.home_team_id = self.scoreboard_state['home_team_id']
        game_state.scoreboard.away_team_id = self.scoreboard_state['away_team_id']


class AtomicStateChanger:
    """
    Provides atomic operations on game state with rollback capability.
    
    This class manages the low-level mechanics of state changes, ensuring that
    modifications can be rolled back if any error occurs. It uses snapshot-based
    rollback rather than operation logging for simplicity and reliability.
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize the atomic state changer.
        
        Args:
            enable_logging: Whether to enable detailed logging of operations
        """
        self.logger = logging.getLogger(__name__) if enable_logging else None
        self._transaction_active = False
        self._snapshot: Optional[StateSnapshot] = None
        self._game_state: Optional[GameState] = None
    
    def begin_transaction(self, game_state: GameState) -> None:
        """
        Begin an atomic transaction.
        
        This captures the current state so it can be restored if needed.
        
        Args:
            game_state: The game state to operate on
            
        Raises:
            RuntimeError: If a transaction is already active
        """
        if self._transaction_active:
            raise RuntimeError("Cannot begin transaction: another transaction is already active")
        
        self._game_state = game_state
        self._snapshot = StateSnapshot.capture(game_state)
        self._transaction_active = True
        
        if self.logger:
            self.logger.debug(f"Transaction begun - captured state at Q{self._snapshot.clock_state['quarter']} {self._snapshot.clock_state['clock']}s")
    
    def commit_transaction(self) -> None:
        """
        Commit the current transaction.
        
        This finalizes all changes and clears the rollback snapshot.
        
        Raises:
            RuntimeError: If no transaction is active
        """
        if not self._transaction_active:
            raise RuntimeError("Cannot commit: no active transaction")
        
        if self.logger:
            final_snapshot = StateSnapshot.capture(self._game_state)
            self.logger.debug(f"Transaction committed - final state at Q{final_snapshot.clock_state['quarter']} {final_snapshot.clock_state['clock']}s")
        
        self._cleanup_transaction()
    
    def rollback_transaction(self) -> bool:
        """
        Rollback the current transaction.
        
        This restores the game state to the snapshot taken at transaction start.
        
        Returns:
            bool: True if rollback was successful, False if no transaction was active
        """
        if not self._transaction_active:
            if self.logger:
                self.logger.warning("Attempted rollback with no active transaction")
            return False
        
        try:
            self._snapshot.restore(self._game_state)
            
            if self.logger:
                self.logger.info(f"Transaction rolled back - restored state to Q{self._snapshot.clock_state['quarter']} {self._snapshot.clock_state['clock']}s")
            
            self._cleanup_transaction()
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error during rollback: {str(e)}")
            self._cleanup_transaction()
            return False
    
    def is_transaction_active(self) -> bool:
        """Check if a transaction is currently active"""
        return self._transaction_active
    
    def get_transaction_snapshot(self) -> Optional[StateSnapshot]:
        """Get the current transaction's snapshot (for debugging/auditing)"""
        return copy.deepcopy(self._snapshot) if self._snapshot else None
    
    def atomic_field_update(self, field_position: Optional[int] = None, 
                           down: Optional[int] = None,
                           yards_to_go: Optional[int] = None,
                           possession_team_id: Optional[int] = None) -> None:
        """
        Atomically update field state properties.
        
        Args:
            field_position: New field position (1-100)
            down: New down number (1-4)
            yards_to_go: New yards to go for first down
            possession_team_id: New team with possession
            
        Raises:
            RuntimeError: If no transaction is active
            ValueError: If values are invalid
        """
        if not self._transaction_active:
            raise RuntimeError("Cannot perform atomic update: no active transaction")
        
        # Validate inputs
        if field_position is not None and (field_position < 0 or field_position > 100):
            raise ValueError(f"Invalid field position: {field_position}")
        
        if down is not None and (down < 1 or down > 4):
            raise ValueError(f"Invalid down: {down}")
        
        if yards_to_go is not None and yards_to_go < 0:
            raise ValueError(f"Invalid yards to go: {yards_to_go}")
        
        # Apply updates
        if field_position is not None:
            self._game_state.field.field_position = field_position
        
        if down is not None:
            self._game_state.field.down = down
            
        if yards_to_go is not None:
            self._game_state.field.yards_to_go = yards_to_go
            
        if possession_team_id is not None:
            self._game_state.field.possession_team_id = possession_team_id
    
    def atomic_clock_update(self, quarter: Optional[int] = None,
                           clock: Optional[int] = None,
                           play_clock: Optional[int] = None) -> None:
        """
        Atomically update clock state properties.
        
        Args:
            quarter: New quarter (1-4+)
            clock: New game clock in seconds
            play_clock: New play clock in seconds
            
        Raises:
            RuntimeError: If no transaction is active  
            ValueError: If values are invalid
        """
        if not self._transaction_active:
            raise RuntimeError("Cannot perform atomic update: no active transaction")
        
        # Validate inputs
        if quarter is not None and quarter < 1:
            raise ValueError(f"Invalid quarter: {quarter}")
        
        if clock is not None and clock < 0:
            raise ValueError(f"Invalid clock: {clock}")
            
        if play_clock is not None and play_clock < 0:
            raise ValueError(f"Invalid play clock: {play_clock}")
        
        # Apply updates
        if quarter is not None:
            self._game_state.clock.quarter = quarter
            
        if clock is not None:
            self._game_state.clock.clock = clock
            
        if play_clock is not None:
            self._game_state.clock.play_clock = play_clock
    
    def atomic_score_update(self, home_score: Optional[int] = None,
                           away_score: Optional[int] = None) -> None:
        """
        Atomically update scoreboard state.
        
        Args:
            home_score: New home team score
            away_score: New away team score
            
        Raises:
            RuntimeError: If no transaction is active
            ValueError: If scores are negative
        """
        if not self._transaction_active:
            raise RuntimeError("Cannot perform atomic update: no active transaction")
        
        # Validate inputs
        if home_score is not None and home_score < 0:
            raise ValueError(f"Invalid home score: {home_score}")
            
        if away_score is not None and away_score < 0:
            raise ValueError(f"Invalid away score: {away_score}")
        
        # Apply updates
        if home_score is not None:
            self._game_state.scoreboard.home_score = home_score
            
        if away_score is not None:
            self._game_state.scoreboard.away_score = away_score
    
    def _cleanup_transaction(self) -> None:
        """Clean up transaction state"""
        self._transaction_active = False
        self._snapshot = None
        self._game_state = None