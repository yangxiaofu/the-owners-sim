"""
GameStateTransition - Main Container for All State Changes

This is the primary data structure that contains all the individual state transitions
that need to be applied atomically to update the game state. It serves as the
complete specification of how the game state should change after a play.

The GameStateTransition ensures that all related state changes happen together
or not at all, maintaining game state consistency.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from datetime import datetime

from .field_transition import FieldTransition
from .possession_transition import PossessionTransition
from .score_transition import ScoreTransition
from .clock_transition import ClockTransition
from .special_situation_transition import SpecialSituationTransition


@dataclass(frozen=True)
class GameStateTransition:
    """
    Immutable container for all state changes that need to be applied atomically.
    
    This is the main transition object that orchestrates all individual transitions
    to ensure they are applied together as a single atomic operation.
    
    Attributes:
        transition_id: Unique identifier for this transition (for auditing)
        created_at: Timestamp when this transition was created
        play_id: ID of the play that caused this transition
        
        # Core State Transitions
        field_transition: Changes to field position, downs, and yards to go
        possession_transition: Changes to team possession and turnover status
        score_transition: Changes to game score and scoring plays
        clock_transition: Changes to game time and quarter progression
        special_situation_transition: Complex scenarios (kickoffs, punts, etc.)
        
        # Metadata
        transition_reason: Human-readable description of why this transition occurred
        original_play_result: Reference to the play result that caused this transition
        validation_errors: Any validation errors encountered (empty if valid)
        
        # Flags
        requires_kickoff: Whether this transition requires a kickoff to follow
        game_ending: Whether this transition ends the game
        quarter_ending: Whether this transition ends the current quarter
        requires_special_teams: Whether special teams units should take the field
        
        # Statistics and Tracking
        statistics_updates: Key-value pairs of statistics that should be updated
        audit_trail: Additional data for debugging and analysis
    """
    
    # Unique identification
    transition_id: str
    created_at: datetime
    play_id: Optional[str] = None
    
    # Core State Transitions (all optional - only set if that type of change is needed)
    field_transition: Optional[FieldTransition] = None
    possession_transition: Optional[PossessionTransition] = None
    score_transition: Optional[ScoreTransition] = None
    clock_transition: Optional[ClockTransition] = None
    special_situation_transition: Optional[SpecialSituationTransition] = None
    
    # Metadata
    transition_reason: str = ""
    original_play_result: Optional[Dict[str, Any]] = None
    validation_errors: List[str] = None
    
    # Control Flags
    requires_kickoff: bool = False
    game_ending: bool = False
    quarter_ending: bool = False
    requires_special_teams: bool = False
    
    # Statistics and Tracking
    statistics_updates: Dict[str, Any] = None
    audit_trail: Dict[str, Any] = None
    
    def __post_init__(self):
        """Initialize default empty collections to avoid mutable default arguments."""
        if self.validation_errors is None:
            object.__setattr__(self, 'validation_errors', [])
        if self.statistics_updates is None:
            object.__setattr__(self, 'statistics_updates', {})
        if self.audit_trail is None:
            object.__setattr__(self, 'audit_trail', {})
    
    def has_field_changes(self) -> bool:
        """Return True if this transition includes field position changes."""
        return self.field_transition is not None
    
    def has_possession_changes(self) -> bool:
        """Return True if this transition includes possession changes."""
        return self.possession_transition is not None
    
    def has_score_changes(self) -> bool:
        """Return True if this transition includes score changes."""
        return self.score_transition is not None
    
    def has_clock_changes(self) -> bool:
        """Return True if this transition includes clock/time changes."""
        return self.clock_transition is not None
    
    def has_special_situation(self) -> bool:
        """Return True if this transition includes special situations."""
        return self.special_situation_transition is not None
    
    def is_valid(self) -> bool:
        """Return True if this transition has no validation errors."""
        return len(self.validation_errors) == 0
    
    def is_scoring_play(self) -> bool:
        """Return True if this transition represents a scoring play."""
        return (self.score_transition is not None and 
                self.score_transition.points_scored > 0)
    
    def is_turnover(self) -> bool:
        """Return True if this transition represents a turnover."""
        return (self.possession_transition is not None and 
                self.possession_transition.turnover_occurred)
    
    def is_change_of_possession(self) -> bool:
        """Return True if this transition changes possession (turnover or normal)."""
        return (self.possession_transition is not None and 
                self.possession_transition.possession_changes)
    
    def get_total_points_scored(self) -> int:
        """Return the total points scored in this transition."""
        if self.score_transition is None:
            return 0
        return self.score_transition.points_scored
    
    def get_new_field_position(self) -> Optional[int]:
        """Return the new field position after this transition."""
        if self.field_transition is None:
            return None
        return self.field_transition.new_yard_line
    
    def get_new_down(self) -> Optional[int]:
        """Return the new down after this transition."""
        if self.field_transition is None:
            return None
        return self.field_transition.new_down
    
    def requires_post_play_kickoff(self) -> bool:
        """Return True if a kickoff should occur after this transition."""
        return self.requires_kickoff or (self.score_transition is not None and 
                                       self.score_transition.requires_kickoff)
    
    def get_summary(self) -> str:
        """Return a human-readable summary of this transition."""
        summary_parts = []
        
        if self.has_field_changes():
            summary_parts.append(f"Field: {self.field_transition.get_summary()}")
            
        if self.has_score_changes():
            summary_parts.append(f"Score: {self.score_transition.get_summary()}")
            
        if self.has_possession_changes():
            summary_parts.append(f"Possession: {self.possession_transition.get_summary()}")
            
        if self.has_clock_changes():
            summary_parts.append(f"Clock: {self.clock_transition.get_summary()}")
            
        if self.has_special_situation():
            summary_parts.append(f"Special: {self.special_situation_transition.get_summary()}")
        
        return " | ".join(summary_parts) if summary_parts else "No changes"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this transition to a dictionary for serialization/logging."""
        return {
            'transition_id': self.transition_id,
            'created_at': self.created_at.isoformat(),
            'play_id': self.play_id,
            'transition_reason': self.transition_reason,
            'field_changes': self.field_transition.to_dict() if self.field_transition else None,
            'possession_changes': self.possession_transition.to_dict() if self.possession_transition else None,
            'score_changes': self.score_transition.to_dict() if self.score_transition else None,
            'clock_changes': self.clock_transition.to_dict() if self.clock_transition else None,
            'special_situation': self.special_situation_transition.to_dict() if self.special_situation_transition else None,
            'requires_kickoff': self.requires_kickoff,
            'game_ending': self.game_ending,
            'quarter_ending': self.quarter_ending,
            'requires_special_teams': self.requires_special_teams,
            'statistics_updates': dict(self.statistics_updates),
            'validation_errors': list(self.validation_errors),
            'is_valid': self.is_valid(),
            'summary': self.get_summary()
        }