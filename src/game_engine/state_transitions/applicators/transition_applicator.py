"""
Transition Applicator - Main Application Coordinator

This module provides the main coordinator for applying state transitions atomically.
It orchestrates the application of changes to GameState, FieldState, GameClock, and Scoreboard
while ensuring transaction-like behavior with rollback capability.

Key Features:
- Atomic application of all changes (all or nothing)
- Rollback on any failure  
- Detailed logging of applied changes
- Support for complex multi-step state transitions
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

from ...plays.data_structures import PlayResult
from ...field.game_state import GameState
from .atomic_state_changer import AtomicStateChanger
from .state_rollback_manager import StateRollbackManager


@dataclass
class TransitionContext:
    """Context information for a state transition"""
    play_result: PlayResult
    game_state: GameState
    applying_team_id: int
    opposing_team_id: int
    transition_id: str = ""  # Unique identifier for this transition
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass  
class TransitionResult:
    """Result of applying a state transition"""
    success: bool
    changes_applied: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None
    rollback_performed: bool = False
    transition_id: str = ""


class TransitionApplicator:
    """
    Main coordinator for applying atomic state transitions.
    
    This class orchestrates the application of complex state changes that may involve
    multiple state components (field, clock, scoreboard). All changes are applied
    atomically - if any step fails, all changes are rolled back to maintain
    consistent game state.
    """
    
    def __init__(self, enable_logging: bool = True):
        """
        Initialize the transition applicator.
        
        Args:
            enable_logging: Whether to enable detailed logging of state changes
        """
        self.logger = logging.getLogger(__name__) if enable_logging else None
        self.atomic_changer = AtomicStateChanger()
        self.rollback_manager = StateRollbackManager()
        self._transition_counter = 0
    
    def apply_play_result(self, play_result: PlayResult, game_state: GameState) -> TransitionResult:
        """
        Apply a play result to the game state atomically.
        
        This is the main entry point for applying play results. It coordinates
        all the individual state changes required and ensures they are applied
        atomically.
        
        Args:
            play_result: The result of the play execution
            game_state: The current game state to update
            
        Returns:
            TransitionResult indicating success/failure and details
        """
        self._transition_counter += 1
        transition_id = f"transition_{self._transition_counter}"
        
        # Create transition context
        context = TransitionContext(
            play_result=play_result,
            game_state=game_state,
            applying_team_id=game_state.field.possession_team_id,
            opposing_team_id=self._get_opposing_team_id(game_state),
            transition_id=transition_id
        )
        
        if self.logger:
            self.logger.info(f"Starting transition {transition_id} for {play_result.play_type} play")
        
        try:
            # Begin atomic transaction
            self.atomic_changer.begin_transaction(game_state)
            
            # Apply all state changes in sequence
            changes_applied = []
            
            # 1. Apply basic field and clock changes
            field_changes = self._apply_basic_field_changes(context)
            changes_applied.extend(field_changes)
            
            # 2. Apply scoring changes
            if play_result.is_score:
                score_changes = self._apply_scoring_changes(context)
                changes_applied.extend(score_changes)
            
            # 3. Handle special situations (turnovers, punts, kickoffs)
            special_changes = self._apply_special_situation_changes(context)
            changes_applied.extend(special_changes)
            
            # 4. Handle possession changes
            possession_changes = self._apply_possession_changes(context)
            changes_applied.extend(possession_changes)
            
            # 5. Handle quarter advancement
            quarter_changes = self._apply_quarter_advancement(context)
            changes_applied.extend(quarter_changes)
            
            # Commit all changes
            self.atomic_changer.commit_transaction()
            
            if self.logger:
                self.logger.info(f"Successfully applied transition {transition_id} with {len(changes_applied)} changes")
            
            return TransitionResult(
                success=True,
                changes_applied=changes_applied,
                transition_id=transition_id
            )
            
        except Exception as e:
            # Rollback all changes
            if self.logger:
                self.logger.error(f"Error in transition {transition_id}: {str(e)}")
            
            rollback_success = self.atomic_changer.rollback_transaction()
            
            return TransitionResult(
                success=False,
                error_message=str(e),
                rollback_performed=rollback_success,
                transition_id=transition_id
            )
    
    def _apply_basic_field_changes(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Apply basic field position and clock changes"""
        changes = []
        play_result = context.play_result
        game_state = context.game_state
        
        # Update field position and downs
        old_field_pos = game_state.field.field_position
        old_down = game_state.field.down
        old_yards_to_go = game_state.field.yards_to_go
        
        field_result = game_state.field.update_down(play_result.yards_gained)
        
        changes.append({
            'type': 'field_update',
            'old_field_position': old_field_pos,
            'new_field_position': game_state.field.field_position,
            'old_down': old_down,
            'new_down': game_state.field.down,
            'old_yards_to_go': old_yards_to_go,
            'new_yards_to_go': game_state.field.yards_to_go,
            'field_result': field_result
        })
        
        # Update clock
        old_clock = game_state.clock.clock
        game_state.clock.run_time(play_result.time_elapsed)
        
        changes.append({
            'type': 'clock_update',
            'old_clock': old_clock,
            'new_clock': game_state.clock.clock,
            'time_elapsed': play_result.time_elapsed
        })
        
        # Handle clock stoppage
        if play_result.outcome in ["incomplete", "out_of_bounds", "penalty"]:
            game_state.clock.stop_clock()
            changes.append({
                'type': 'clock_stoppage',
                'reason': play_result.outcome
            })
        
        return changes
    
    def _apply_scoring_changes(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Apply scoring changes to the scoreboard"""
        changes = []
        play_result = context.play_result
        game_state = context.game_state
        
        if not play_result.is_score:
            return changes
        
        old_home_score = game_state.scoreboard.home_score
        old_away_score = game_state.scoreboard.away_score
        
        scoring_team_id = context.applying_team_id
        
        if play_result.outcome == "touchdown":
            game_state.scoreboard.add_touchdown(scoring_team_id)
            changes.append({
                'type': 'touchdown',
                'scoring_team_id': scoring_team_id,
                'points': 6
            })
            
            # Handle conversion attempt based on PlayResult decision
            conversion_changes = self._handle_conversion_attempt(scoring_team_id, game_state, play_result)
            changes.extend(conversion_changes)
        elif play_result.outcome == "field_goal":
            game_state.scoreboard.add_field_goal(scoring_team_id)
            changes.append({
                'type': 'field_goal',
                'scoring_team_id': scoring_team_id,
                'points': 3
            })
        elif play_result.outcome == "safety":
            # Safety goes to the opposing team
            game_state.scoreboard.add_safety(context.opposing_team_id)
            changes.append({
                'type': 'safety',
                'scoring_team_id': context.opposing_team_id,
                'points': 2
            })
        
        # Record score change summary
        changes.append({
            'type': 'score_change',
            'old_home_score': old_home_score,
            'new_home_score': game_state.scoreboard.home_score,
            'old_away_score': old_away_score,
            'new_away_score': game_state.scoreboard.away_score
        })
        
        return changes
    
    def _apply_special_situation_changes(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle special situations like turnovers, punts, etc."""
        changes = []
        play_result = context.play_result
        game_state = context.game_state
        
        # Handle turnovers
        if play_result.is_turnover:
            changes.extend(self._handle_turnover(context))
        
        # Handle punts
        elif play_result.play_type == "punt":
            changes.extend(self._handle_punt(context))
        
        # Handle post-score situations
        elif play_result.is_score and play_result.outcome in ["touchdown", "field_goal"]:
            changes.extend(self._handle_post_score_kickoff(context))
        
        return changes
    
    def _apply_possession_changes(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle possession changes including turnover on downs"""
        changes = []
        game_state = context.game_state
        
        # Check for turnover on downs
        if game_state.field.down > 4:
            old_possession = game_state.field.possession_team_id
            game_state.field.possession_team_id = context.opposing_team_id
            game_state.field.down = 1
            game_state.field.yards_to_go = 10
            
            changes.append({
                'type': 'turnover_on_downs',
                'old_possession_team_id': old_possession,
                'new_possession_team_id': game_state.field.possession_team_id
            })
        
        return changes
    
    def _apply_quarter_advancement(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle quarter advancement if needed"""
        changes = []
        game_state = context.game_state
        
        old_quarter = game_state.clock.quarter
        
        # Clock advancement is already handled in field changes, but we need to check
        # if quarter actually changed
        if game_state.clock.quarter != old_quarter:
            changes.append({
                'type': 'quarter_advancement',
                'old_quarter': old_quarter,
                'new_quarter': game_state.clock.quarter
            })
        
        return changes
    
    def _handle_turnover(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle turnover situations"""
        changes = []
        game_state = context.game_state
        
        old_possession = game_state.field.possession_team_id
        game_state.field.possession_team_id = context.opposing_team_id
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        
        # Simplified field position - in reality this would be based on turnover location
        game_state.field.field_position = 50
        
        changes.append({
            'type': 'turnover',
            'old_possession_team_id': old_possession,
            'new_possession_team_id': game_state.field.possession_team_id,
            'turnover_type': context.play_result.outcome
        })
        
        return changes
    
    def _handle_punt(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle punt situations"""
        changes = []
        game_state = context.game_state
        play_result = context.play_result
        
        old_possession = game_state.field.possession_team_id
        game_state.field.possession_team_id = context.opposing_team_id
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        
        # Calculate punt field position
        new_field_position = max(20, 100 - play_result.yards_gained)
        game_state.field.field_position = new_field_position
        
        changes.append({
            'type': 'punt',
            'old_possession_team_id': old_possession,
            'new_possession_team_id': game_state.field.possession_team_id,
            'punt_distance': play_result.yards_gained,
            'final_field_position': new_field_position
        })
        
        return changes
    
    def _handle_post_score_kickoff(self, context: TransitionContext) -> List[Dict[str, Any]]:
        """Handle possession change after scoring"""
        changes = []
        game_state = context.game_state
        
        old_possession = game_state.field.possession_team_id
        receiving_team_id = context.opposing_team_id
        
        # Switch possession to receiving team
        game_state.field.possession_team_id = receiving_team_id
        game_state.field.down = 1
        game_state.field.yards_to_go = 10
        game_state.field.field_position = 25  # Standard kickoff return position
        
        changes.append({
            'type': 'post_score_kickoff',
            'old_possession_team_id': old_possession,
            'new_possession_team_id': receiving_team_id,
            'kickoff_return_position': 25
        })
        
        return changes
    
    def _handle_conversion_attempt(self, scoring_team_id: int, game_state: GameState, play_result: PlayResult = None) -> List[Dict[str, Any]]:
        """
        Handle extra point/two-point conversion attempt after touchdown.
        
        Now integrated with coaching decision logic from PlayResult.
        If no PlayResult provided, defaults to extra point (backward compatibility).
        """
        import random
        
        changes = []
        
        # Determine conversion type from play result
        conversion_type = "extra_point"  # Default fallback
        if play_result and hasattr(play_result, 'conversion_attempt') and play_result.conversion_attempt:
            conversion_type = play_result.conversion_attempt
        
        if conversion_type == "two_point":
            # Two-point conversion attempt
            two_point_success_rate = 0.48  # NFL average ~48% success rate
            conversion_successful = random.random() < two_point_success_rate
            
            if conversion_successful:
                game_state.scoreboard.add_two_point_conversion(scoring_team_id)
                changes.append({
                    'type': 'two_point_conversion_good',
                    'scoring_team_id': scoring_team_id,
                    'points': 2,
                    'decision_factors': getattr(play_result, 'conversion_decision_factors', [])
                })
                if play_result:
                    play_result.conversion_result = "good"
            else:
                changes.append({
                    'type': 'two_point_conversion_missed',
                    'scoring_team_id': scoring_team_id,
                    'points': 0,
                    'decision_factors': getattr(play_result, 'conversion_decision_factors', [])
                })
                if play_result:
                    play_result.conversion_result = "missed"
        else:
            # Extra point attempt (default)
            extra_point_success_rate = 0.95  # NFL average ~95% success rate
            conversion_successful = random.random() < extra_point_success_rate
            
            if conversion_successful:
                game_state.scoreboard.add_extra_point(scoring_team_id)
                changes.append({
                    'type': 'extra_point_good',
                    'scoring_team_id': scoring_team_id,
                    'points': 1
                })
                if play_result:
                    play_result.conversion_result = "good"
            else:
                changes.append({
                    'type': 'extra_point_missed',
                    'scoring_team_id': scoring_team_id,
                    'points': 0
                })
                if play_result:
                    play_result.conversion_result = "missed"
        
        return changes
    
    def _get_opposing_team_id(self, game_state: GameState) -> int:
        """Get the ID of the team that doesn't have possession"""
        possession_team = game_state.field.possession_team_id
        if possession_team == game_state.scoreboard.home_team_id:
            return game_state.scoreboard.away_team_id
        return game_state.scoreboard.home_team_id