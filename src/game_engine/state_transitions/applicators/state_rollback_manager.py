"""
State Rollback Manager - Error Recovery and Undo Operations

This module provides advanced error recovery and undo operations for state transitions.
It maintains a history of state changes and can perform selective rollbacks,
complete transaction reversals, and error analysis.

Key Features:
- Multi-level rollback with selective undo
- Complete transaction history tracking  
- Error analysis and reporting
- State consistency validation
- Debug and audit trail capabilities
"""

import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ...field.game_state import GameState
from .atomic_state_changer import StateSnapshot


class RollbackLevel(Enum):
    """Different levels of rollback operations"""
    SINGLE_CHANGE = "single_change"      # Undo one specific change
    TRANSACTION = "transaction"          # Undo entire transaction
    MULTI_TRANSACTION = "multi_transaction" # Undo multiple transactions
    CHECKPOINT = "checkpoint"            # Rollback to named checkpoint


@dataclass
class StateChange:
    """Record of a single state change"""
    change_id: str
    change_type: str
    component: str  # 'field', 'clock', 'scoreboard'
    old_value: Any
    new_value: Any
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class TransactionRecord:
    """Record of a complete transaction with all its changes"""
    transaction_id: str
    start_snapshot: StateSnapshot
    end_snapshot: Optional[StateSnapshot]
    changes: List[StateChange]
    start_time: float
    end_time: Optional[float]
    success: bool
    error_message: Optional[str] = None


@dataclass
class RollbackOperation:
    """Record of a rollback operation"""
    rollback_id: str
    rollback_level: RollbackLevel
    target_transaction_id: Optional[str]
    target_change_id: Optional[str]
    affected_changes: List[str]
    timestamp: float
    success: bool
    error_message: Optional[str] = None


class StateRollbackManager:
    """
    Advanced error recovery and undo operations manager.
    
    This class maintains a complete audit trail of state changes and provides
    sophisticated rollback capabilities including selective undo, multi-level
    rollbacks, and error analysis.
    """
    
    def __init__(self, max_history: int = 100, enable_logging: bool = True):
        """
        Initialize the rollback manager.
        
        Args:
            max_history: Maximum number of transactions to keep in history
            enable_logging: Whether to enable detailed logging
        """
        self.logger = logging.getLogger(__name__) if enable_logging else None
        self.max_history = max_history
        
        # Transaction and change tracking
        self._transaction_history: List[TransactionRecord] = []
        self._rollback_history: List[RollbackOperation] = []
        self._checkpoints: Dict[str, StateSnapshot] = {}
        self._change_counter = 0
        self._rollback_counter = 0
    
    def record_transaction_start(self, transaction_id: str, game_state: GameState) -> TransactionRecord:
        """
        Record the start of a new transaction.
        
        Args:
            transaction_id: Unique identifier for the transaction
            game_state: Current game state
            
        Returns:
            TransactionRecord for this transaction
        """
        snapshot = StateSnapshot.capture(game_state)
        
        transaction = TransactionRecord(
            transaction_id=transaction_id,
            start_snapshot=snapshot,
            end_snapshot=None,
            changes=[],
            start_time=time.time(),
            end_time=None,
            success=False
        )
        
        self._transaction_history.append(transaction)
        self._cleanup_old_history()
        
        if self.logger:
            self.logger.debug(f"Started recording transaction {transaction_id}")
        
        return transaction
    
    def record_state_change(self, transaction_id: str, change_type: str, 
                          component: str, old_value: Any, new_value: Any,
                          metadata: Optional[Dict[str, Any]] = None) -> StateChange:
        """
        Record a single state change within a transaction.
        
        Args:
            transaction_id: ID of the transaction this change belongs to
            change_type: Type of change (e.g., 'field_update', 'score_change')
            component: Component being changed ('field', 'clock', 'scoreboard')
            old_value: Value before the change
            new_value: Value after the change
            metadata: Additional information about the change
            
        Returns:
            StateChange record
        """
        self._change_counter += 1
        change_id = f"change_{self._change_counter}"
        
        change = StateChange(
            change_id=change_id,
            change_type=change_type,
            component=component,
            old_value=old_value,
            new_value=new_value,
            timestamp=time.time(),
            metadata=metadata or {}
        )
        
        # Find the transaction and add this change
        transaction = self._find_transaction(transaction_id)
        if transaction:
            transaction.changes.append(change)
        else:
            if self.logger:
                self.logger.warning(f"Cannot record change for unknown transaction {transaction_id}")
        
        return change
    
    def record_transaction_end(self, transaction_id: str, game_state: GameState, 
                             success: bool, error_message: Optional[str] = None) -> bool:
        """
        Record the end of a transaction.
        
        Args:
            transaction_id: ID of the transaction
            game_state: Final game state after transaction
            success: Whether the transaction succeeded
            error_message: Error message if transaction failed
            
        Returns:
            bool: True if transaction was found and updated
        """
        transaction = self._find_transaction(transaction_id)
        if not transaction:
            if self.logger:
                self.logger.warning(f"Cannot end unknown transaction {transaction_id}")
            return False
        
        transaction.end_snapshot = StateSnapshot.capture(game_state)
        transaction.end_time = time.time()
        transaction.success = success
        transaction.error_message = error_message
        
        if self.logger:
            duration = transaction.end_time - transaction.start_time
            status = "succeeded" if success else "failed"
            self.logger.debug(f"Transaction {transaction_id} {status} after {duration:.3f}s with {len(transaction.changes)} changes")
        
        return True
    
    def create_checkpoint(self, checkpoint_name: str, game_state: GameState) -> bool:
        """
        Create a named checkpoint of the current game state.
        
        Args:
            checkpoint_name: Name for this checkpoint
            game_state: Current game state to checkpoint
            
        Returns:
            bool: True if checkpoint was created successfully
        """
        try:
            self._checkpoints[checkpoint_name] = StateSnapshot.capture(game_state)
            
            if self.logger:
                self.logger.info(f"Created checkpoint '{checkpoint_name}'")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create checkpoint '{checkpoint_name}': {str(e)}")
            return False
    
    def rollback_to_checkpoint(self, checkpoint_name: str, game_state: GameState) -> bool:
        """
        Rollback to a named checkpoint.
        
        Args:
            checkpoint_name: Name of checkpoint to rollback to
            game_state: Game state to restore to checkpoint
            
        Returns:
            bool: True if rollback succeeded
        """
        if checkpoint_name not in self._checkpoints:
            if self.logger:
                self.logger.error(f"Checkpoint '{checkpoint_name}' not found")
            return False
        
        try:
            snapshot = self._checkpoints[checkpoint_name]
            snapshot.restore(game_state)
            
            # Record the rollback operation
            self._rollback_counter += 1
            rollback = RollbackOperation(
                rollback_id=f"rollback_{self._rollback_counter}",
                rollback_level=RollbackLevel.CHECKPOINT,
                target_transaction_id=None,
                target_change_id=None,
                affected_changes=[],
                timestamp=time.time(),
                success=True
            )
            self._rollback_history.append(rollback)
            
            if self.logger:
                self.logger.info(f"Successfully rolled back to checkpoint '{checkpoint_name}'")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to rollback to checkpoint '{checkpoint_name}': {str(e)}")
            return False
    
    def rollback_transaction(self, transaction_id: str, game_state: GameState) -> bool:
        """
        Rollback a specific transaction.
        
        Args:
            transaction_id: ID of transaction to rollback
            game_state: Game state to restore
            
        Returns:
            bool: True if rollback succeeded
        """
        transaction = self._find_transaction(transaction_id)
        if not transaction:
            if self.logger:
                self.logger.error(f"Transaction {transaction_id} not found for rollback")
            return False
        
        if not transaction.start_snapshot:
            if self.logger:
                self.logger.error(f"No start snapshot available for transaction {transaction_id}")
            return False
        
        try:
            transaction.start_snapshot.restore(game_state)
            
            # Record the rollback operation
            self._rollback_counter += 1
            rollback = RollbackOperation(
                rollback_id=f"rollback_{self._rollback_counter}",
                rollback_level=RollbackLevel.TRANSACTION,
                target_transaction_id=transaction_id,
                target_change_id=None,
                affected_changes=[change.change_id for change in transaction.changes],
                timestamp=time.time(),
                success=True
            )
            self._rollback_history.append(rollback)
            
            if self.logger:
                self.logger.info(f"Successfully rolled back transaction {transaction_id} with {len(transaction.changes)} changes")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to rollback transaction {transaction_id}: {str(e)}")
            return False
    
    def get_transaction_history(self, limit: Optional[int] = None) -> List[TransactionRecord]:
        """
        Get transaction history.
        
        Args:
            limit: Maximum number of transactions to return (most recent first)
            
        Returns:
            List of transaction records
        """
        history = list(reversed(self._transaction_history))  # Most recent first
        return history[:limit] if limit else history
    
    def get_rollback_history(self, limit: Optional[int] = None) -> List[RollbackOperation]:
        """
        Get rollback operation history.
        
        Args:
            limit: Maximum number of rollbacks to return (most recent first)
            
        Returns:
            List of rollback operations
        """
        history = list(reversed(self._rollback_history))  # Most recent first
        return history[:limit] if limit else history
    
    def analyze_transaction_failures(self, lookback_count: int = 10) -> Dict[str, Any]:
        """
        Analyze recent transaction failures to identify patterns.
        
        Args:
            lookback_count: Number of recent transactions to analyze
            
        Returns:
            Dict with failure analysis
        """
        recent_transactions = self.get_transaction_history(lookback_count)
        failed_transactions = [t for t in recent_transactions if not t.success]
        
        if not failed_transactions:
            return {
                'total_analyzed': len(recent_transactions),
                'failures_found': 0,
                'failure_rate': 0.0,
                'common_errors': {},
                'failure_patterns': []
            }
        
        # Analyze error patterns
        error_counts = {}
        for transaction in failed_transactions:
            if transaction.error_message:
                error_counts[transaction.error_message] = error_counts.get(transaction.error_message, 0) + 1
        
        # Calculate failure rate
        failure_rate = len(failed_transactions) / len(recent_transactions)
        
        return {
            'total_analyzed': len(recent_transactions),
            'failures_found': len(failed_transactions),
            'failure_rate': failure_rate,
            'common_errors': error_counts,
            'failure_patterns': self._identify_failure_patterns(failed_transactions)
        }
    
    def validate_state_consistency(self, game_state: GameState) -> Tuple[bool, List[str]]:
        """
        Validate that the current game state is consistent.
        
        Args:
            game_state: Game state to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate field state
        if game_state.field.field_position < 0 or game_state.field.field_position > 100:
            errors.append(f"Invalid field position: {game_state.field.field_position}")
        
        if game_state.field.down < 1 or game_state.field.down > 4:
            errors.append(f"Invalid down: {game_state.field.down}")
            
        if game_state.field.yards_to_go < 0:
            errors.append(f"Invalid yards to go: {game_state.field.yards_to_go}")
        
        # Validate clock state
        if game_state.clock.quarter < 1:
            errors.append(f"Invalid quarter: {game_state.clock.quarter}")
            
        if game_state.clock.clock < 0:
            errors.append(f"Invalid clock time: {game_state.clock.clock}")
        
        # Validate scoreboard state
        if game_state.scoreboard.home_score < 0:
            errors.append(f"Invalid home score: {game_state.scoreboard.home_score}")
            
        if game_state.scoreboard.away_score < 0:
            errors.append(f"Invalid away score: {game_state.scoreboard.away_score}")
        
        # Validate possession consistency
        if (game_state.field.possession_team_id not in [game_state.scoreboard.home_team_id, game_state.scoreboard.away_team_id]):
            errors.append(f"Invalid possession team: {game_state.field.possession_team_id}")
        
        return len(errors) == 0, errors
    
    def _find_transaction(self, transaction_id: str) -> Optional[TransactionRecord]:
        """Find a transaction by ID"""
        for transaction in reversed(self._transaction_history):
            if transaction.transaction_id == transaction_id:
                return transaction
        return None
    
    def _identify_failure_patterns(self, failed_transactions: List[TransactionRecord]) -> List[str]:
        """Identify common patterns in transaction failures"""
        patterns = []
        
        # Check for rapid failures
        if len(failed_transactions) >= 3:
            time_diffs = []
            for i in range(1, len(failed_transactions)):
                time_diff = failed_transactions[i-1].start_time - failed_transactions[i].start_time
                time_diffs.append(time_diff)
            
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            if avg_time_diff < 1.0:  # Less than 1 second between failures
                patterns.append("Rapid consecutive failures detected")
        
        # Check for common error types
        error_types = set()
        for transaction in failed_transactions:
            if transaction.error_message:
                if "field_position" in transaction.error_message.lower():
                    error_types.add("field_position_errors")
                elif "score" in transaction.error_message.lower():
                    error_types.add("scoring_errors")
                elif "clock" in transaction.error_message.lower():
                    error_types.add("clock_errors")
        
        if error_types:
            patterns.append(f"Common error types: {', '.join(error_types)}")
        
        return patterns
    
    def _cleanup_old_history(self) -> None:
        """Remove old transactions beyond max_history limit"""
        if len(self._transaction_history) > self.max_history:
            excess = len(self._transaction_history) - self.max_history
            self._transaction_history = self._transaction_history[excess:]
            
            if self.logger:
                self.logger.debug(f"Cleaned up {excess} old transaction records")
    
    def clear_history(self) -> None:
        """Clear all history (for testing or reset purposes)"""
        self._transaction_history.clear()
        self._rollback_history.clear()
        self._checkpoints.clear()
        self._change_counter = 0
        self._rollback_counter = 0
        
        if self.logger:
            self.logger.info("Cleared all rollback manager history")