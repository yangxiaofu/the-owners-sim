"""
Transition Utility Functions

Helper functions for managing transitions between BaseGameStateTransition
and the full GameStateTransition with metadata.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from ...plays.data_structures import PlayResult
from .game_state_transition import BaseGameStateTransition, GameStateTransition


def enhance_base_transition(
    base_transition: BaseGameStateTransition,
    play_result: PlayResult,
    possession_team_id: str,
    transition_reason: str = ""
) -> GameStateTransition:
    """
    Convert a BaseGameStateTransition to a full GameStateTransition with metadata.
    
    Args:
        base_transition: Lightweight transition from calculator
        play_result: Original play result that caused this transition
        possession_team_id: ID of the team that had possession
        transition_reason: Human-readable description of the transition
        
    Returns:
        Full GameStateTransition with all metadata
    """
    # Convert play_result to dictionary for storage
    play_result_dict = {
        'play_type': play_result.play_type,
        'outcome': play_result.outcome,
        'yards_gained': play_result.yards_gained,
        'time_elapsed': play_result.time_elapsed,
        'is_turnover': play_result.is_turnover,
        'is_score': play_result.is_score,
        'score_points': play_result.score_points,
        'final_field_position': play_result.final_field_position,
        'primary_player': play_result.primary_player,
        'play_description': play_result.play_description
    }
    
    # Generate transition metadata
    transition_id = create_transition_id()
    created_at = datetime.now()
    play_id = f"play_{possession_team_id}_{transition_id[:8]}"
    
    # Determine transition reason if not provided
    if not transition_reason:
        transition_reason = f"{play_result.play_type} for {play_result.yards_gained} yards"
    
    # Create enhanced transition
    return GameStateTransition(
        # Inherit all core transition fields
        field_transition=base_transition.field_transition,
        possession_transition=base_transition.possession_transition,
        score_transition=base_transition.score_transition,
        clock_transition=base_transition.clock_transition,
        special_situation_transition=base_transition.special_situation_transition,
        
        # Add metadata
        transition_id=transition_id,
        created_at=created_at,
        play_id=play_id,
        transition_reason=transition_reason,
        original_play_result=play_result_dict,
        
        # Initialize with empty collections
        validation_errors=[],
        statistics_updates={},
        audit_trail={
            'possession_team_id': possession_team_id,
            'created_timestamp': created_at.isoformat(),
            'play_summary': play_result.play_description or f"{play_result.play_type} play"
        }
    )


def extract_base_transition(full_transition: GameStateTransition) -> BaseGameStateTransition:
    """
    Extract the core transition data from a full GameStateTransition.
    
    Args:
        full_transition: Full transition with metadata
        
    Returns:
        BaseGameStateTransition with just the core transition data
    """
    return BaseGameStateTransition(
        field_transition=full_transition.field_transition,
        possession_transition=full_transition.possession_transition,
        score_transition=full_transition.score_transition,
        clock_transition=full_transition.clock_transition,
        special_situation_transition=full_transition.special_situation_transition
    )


def create_transition_id() -> str:
    """
    Generate a unique transition ID for tracking and debugging.
    
    Returns:
        Unique string identifier
    """
    return str(uuid.uuid4())


def validate_transition_compatibility(
    base_transition: BaseGameStateTransition,
    full_transition: GameStateTransition
) -> bool:
    """
    Validate that a BaseGameStateTransition matches the core data in a GameStateTransition.
    
    Args:
        base_transition: Base transition to compare
        full_transition: Full transition to compare against
        
    Returns:
        True if the core transition data matches
    """
    extracted_base = extract_base_transition(full_transition)
    
    return (
        base_transition.field_transition == extracted_base.field_transition and
        base_transition.possession_transition == extracted_base.possession_transition and
        base_transition.score_transition == extracted_base.score_transition and
        base_transition.clock_transition == extracted_base.clock_transition and
        base_transition.special_situation_transition == extracted_base.special_situation_transition
    )


def create_empty_base_transition() -> BaseGameStateTransition:
    """
    Create an empty BaseGameStateTransition with all fields set to None.
    
    Useful for testing or as a starting point for building transitions.
    
    Returns:
        Empty BaseGameStateTransition
    """
    return BaseGameStateTransition()


def create_empty_full_transition(transition_reason: str = "Empty transition") -> GameStateTransition:
    """
    Create an empty GameStateTransition with metadata but no actual transitions.
    
    Args:
        transition_reason: Reason for creating this empty transition
        
    Returns:
        Empty GameStateTransition with metadata
    """
    return GameStateTransition(
        transition_id=create_transition_id(),
        created_at=datetime.now(),
        transition_reason=transition_reason,
        validation_errors=[],
        statistics_updates={},
        audit_trail={}
    )