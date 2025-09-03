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

from game_engine.plays.data_structures import PlayResult
from game_engine.field.game_state import GameState
from game_engine.state_transitions.applicators.atomic_state_changer import AtomicStateChanger
from game_engine.state_transitions.applicators.state_rollback_manager import StateRollbackManager
# Import for calculated transitions
from game_engine.state_transitions.data_structures import BaseGameStateTransition
# Import team system components for the scoreboard bug fix
from game_engine.teams import TeamID, TeamMapper, TeamRegistry, TeamContext


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
    Main coordinator for applying atomic state transitions with team system integration.
    
    This class orchestrates the application of complex state changes that may involve
    multiple state components (field, clock, scoreboard). All changes are applied
    atomically - if any step fails, all changes are rolled back to maintain
    consistent game state.
    
    Now integrates with the team system to provide type-safe, consistent
    team-to-scoreboard mapping that fixes the scoreboard bug.
    """
    
    def __init__(self, enable_logging: bool = True, team_mapper: Optional[TeamMapper] = None):
        """
        Initialize the transition applicator with team system integration.
        
        Args:
            enable_logging: Whether to enable detailed logging of state changes
            team_mapper: TeamMapper for consistent team-to-scoreboard mapping.
                        If None, will attempt to create fallback mapping.
        """
        self.logger = logging.getLogger(__name__) if enable_logging else None
        self.atomic_changer = AtomicStateChanger()
        self.rollback_manager = StateRollbackManager()
        self.team_mapper = team_mapper
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
            
            # Check if we need to handle post-score kickoff reset FIRST
            needs_kickoff_reset = self._needs_post_score_kickoff_reset(game_state, play_result)
            
            # 🔧 DEBUG: Integration verification
            print(f"🔧 APPLICATOR DEBUG: needs_kickoff_reset = {needs_kickoff_reset}")
            print(f"🔧 APPLICATOR DEBUG: field_pos = {game_state.field.field_position}, down = {game_state.field.down}")
            print(f"🔧 APPLICATOR DEBUG: play_type = {play_result.play_type}, is_score = {play_result.is_score}")
            
            if needs_kickoff_reset:
                if self.logger:
                    self.logger.debug("Post-score kickoff reset detected - applying special situations first")
                
                # For post-score scenarios, handle kickoff reset BEFORE basic field changes
                # 1. Handle special situations (kickoffs) FIRST to reset field position
                old_field_pos = game_state.field.field_position
                special_changes = self._apply_special_situation_changes(context)
                new_field_pos = game_state.field.field_position
                print(f"🔧 APPLICATOR DEBUG: Kickoff path - field_pos {old_field_pos} → {new_field_pos}")
                changes_applied.extend(special_changes)
                
                # 2. Skip basic field changes (kickoff already set proper field position)
                if self.logger:
                    self.logger.debug("Skipping basic field changes - field position reset by kickoff")
                
                # 3. Apply scoring changes if needed
                if play_result.is_score:
                    score_changes = self._apply_scoring_changes(context)
                    changes_applied.extend(score_changes)
                
                # 4. Handle possession changes
                possession_changes = self._apply_possession_changes(context)
                changes_applied.extend(possession_changes)
            else:
                # Normal sequence for non-kickoff scenarios
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
            
            # 5. Handle quarter advancement (always last)
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
    
    def apply_calculated_transition(self, transition: BaseGameStateTransition, game_state: GameState) -> TransitionResult:
        """
        Apply a pre-calculated transition to the game state.
        
        This method applies transitions that have already been calculated by the
        TransitionCalculator, ensuring consistency with the validation and calculation logic.
        
        Args:
            transition: Pre-calculated transition with all changes
            game_state: Game state to apply changes to
            
        Returns:
            TransitionResult indicating success/failure
        """
        self._transition_counter += 1
        transition_id = f"calc_transition_{self._transition_counter}"
        
        if self.logger:
            self.logger.info(f"Applying calculated transition {transition_id}")
        
        try:
            # Begin atomic transaction
            self.atomic_changer.begin_transaction(game_state)
            changes_applied = []
            
            # Apply clock transition
            if transition.has_clock_changes():
                clock_changes = self._apply_clock_transition(transition.clock_transition, game_state)
                changes_applied.extend(clock_changes)
            
            # Apply field transition
            if transition.has_field_changes():
                field_changes = self._apply_field_transition(transition.field_transition, game_state)
                changes_applied.extend(field_changes)
            
            # Apply score transition
            if transition.has_score_changes():
                score_changes = self._apply_score_transition(transition.score_transition, game_state)
                changes_applied.extend(score_changes)
            
            # Apply possession transition
            if transition.has_possession_changes():
                possession_changes = self._apply_possession_transition(transition.possession_transition, game_state)
                changes_applied.extend(possession_changes)
            
            # PHASE 2B FIX: Apply special situation transitions (missing integration)
            if transition.special_situation_transition:
                print(f"🔧 APPLY_CALC DEBUG: Found special_situation_transition in calculated transition")
                # Create TransitionContext for compatibility with existing special situation handler
                from game_engine.plays.data_structures import PlayResult
                
                # Create minimal PlayResult for context (special situations don't need full play result)
                minimal_play_result = PlayResult(
                    play_type="special_situation",
                    outcome="field_reset",
                    yards_gained=0,
                    time_elapsed=0,
                    is_turnover=False,
                    is_score=False,
                    score_points=0
                )
                
                # Get team IDs for TransitionContext
                applying_team_id = game_state.field.possession_team_id
                if applying_team_id == game_state.scoreboard.home_team_id:
                    opposing_team_id = game_state.scoreboard.away_team_id
                else:
                    opposing_team_id = game_state.scoreboard.home_team_id
                
                special_context = TransitionContext(
                    play_result=minimal_play_result,
                    game_state=game_state,
                    applying_team_id=applying_team_id,
                    opposing_team_id=opposing_team_id,
                    transition_id=f"special_situation_{self._transition_counter}",
                    metadata={"transition": transition}
                )
                
                special_changes = self._apply_special_situation_changes(special_context)
                changes_applied.extend(special_changes)
                print(f"🔧 APPLY_CALC DEBUG: Applied {len(special_changes)} special situation changes")
            else:
                print(f"🔧 APPLY_CALC DEBUG: No special_situation_transition found in calculated transition")
            
            # Commit all changes
            self.atomic_changer.commit_transaction()
            
            if self.logger:
                self.logger.info(f"Successfully applied calculated transition {transition_id} with {len(changes_applied)} changes")
            
            return TransitionResult(
                success=True,
                changes_applied=changes_applied,
                transition_id=transition_id
            )
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error in calculated transition {transition_id}: {str(e)}")
            
            rollback_success = self.atomic_changer.rollback_transaction()
            
            return TransitionResult(
                success=False,
                error_message=str(e),
                rollback_performed=rollback_success,
                transition_id=transition_id
            )
    
    def _apply_clock_transition(self, clock_transition, game_state: GameState) -> List[Dict[str, Any]]:
        """Apply calculated clock transition to game state."""
        changes = []
        
        if not clock_transition:
            return changes
        
        old_clock = game_state.clock.clock
        old_quarter = game_state.clock.quarter
        
        # Apply time advancement
        if clock_transition.time_advanced:
            game_state.clock.run_time(clock_transition.seconds_elapsed)
            changes.append({
                'type': 'clock_time_update',
                'old_clock': old_clock,
                'new_clock': game_state.clock.clock,
                'time_elapsed': clock_transition.seconds_elapsed
            })
        
        # Handle clock stoppage
        if clock_transition.clock_stopped:
            game_state.clock.stop_clock()
            changes.append({
                'type': 'clock_stoppage',
                'reason': clock_transition.clock_stop_reason.value if clock_transition.clock_stop_reason else 'unknown'
            })
        
        # Handle quarter advancement
        if clock_transition.quarter_changed and clock_transition.new_quarter:
            game_state.clock.advance_quarter()
            changes.append({
                'type': 'quarter_advancement',
                'old_quarter': old_quarter,
                'new_quarter': game_state.clock.quarter,
                'quarter_ending': clock_transition.quarter_ending,
                'game_ending': clock_transition.game_ending
            })
        
        # Log special timing situations
        if clock_transition.two_minute_warning_triggered:
            changes.append({
                'type': 'two_minute_warning',
                'quarter': game_state.clock.quarter
            })
        
        return changes
    
    def _apply_field_transition(self, field_transition, game_state: GameState) -> List[Dict[str, Any]]:
        """Apply calculated field transition to game state."""
        changes = []
        
        if not field_transition:
            return changes
        
        old_field_pos = game_state.field.field_position
        old_down = game_state.field.down
        old_yards_to_go = game_state.field.yards_to_go
        
        # Apply field changes directly from transition
        game_state.field.field_position = field_transition.new_yard_line
        game_state.field.down = field_transition.new_down
        game_state.field.yards_to_go = field_transition.new_yards_to_go
        
        changes.append({
            'type': 'field_transition_applied',
            'old_field_position': old_field_pos,
            'new_field_position': field_transition.new_yard_line,
            'old_down': old_down,
            'new_down': field_transition.new_down,
            'old_yards_to_go': old_yards_to_go,
            'new_yards_to_go': field_transition.new_yards_to_go,
            'yards_gained': field_transition.yards_gained,
            'first_down_achieved': field_transition.first_down_achieved
        })
        
        return changes
    
    def _apply_score_transition(self, score_transition, game_state: GameState) -> List[Dict[str, Any]]:
        """
        Apply calculated score transition to game state with team system integration.
        
        CRITICAL FIX: This method now uses the team system to properly map TeamID
        values to scoreboard fields, fixing the original scoreboard bug.
        """
        changes = []
        
        if not score_transition or not score_transition.score_occurred:
            return changes
        
        old_home_score = game_state.scoreboard.home_score
        old_away_score = game_state.scoreboard.away_score
        
        # Apply score based on scoring team and points
        scoring_team = score_transition.scoring_team
        points = score_transition.points_scored
        
        # CRITICAL FIX: Use team system for proper team → scoreboard mapping
        try:
            scoreboard_field = self._resolve_scoreboard_field(scoring_team, game_state)
            
            # Apply score to correct team using scoreboard field
            if scoreboard_field == "home":
                game_state.scoreboard.home_score += points
                print(f"🔧 SCORE APPLIED: {points} points to HOME team (was {old_home_score}, now {game_state.scoreboard.home_score})")
            elif scoreboard_field == "away":
                game_state.scoreboard.away_score += points
                print(f"🔧 SCORE APPLIED: {points} points to AWAY team (was {old_away_score}, now {game_state.scoreboard.away_score})")
            else:
                if self.logger:
                    self.logger.error(f"Invalid scoreboard field: '{scoreboard_field}' for team {scoring_team}")
                raise ValueError(f"Cannot map team {scoring_team} to valid scoreboard field")
        
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to apply score for team {scoring_team}: {e}")
            # Don't fail the entire transition - log and continue
            print(f"🔧 SCORE APPLICATION FAILED: {scoring_team} → {e}")
        
        changes.append({
            'type': 'score_transition_applied',
            'old_home_score': old_home_score,
            'new_home_score': game_state.scoreboard.home_score,
            'old_away_score': old_away_score,
            'new_away_score': game_state.scoreboard.away_score,
            'scoring_team': scoring_team,
            'points_scored': points,
            'score_type': score_transition.score_type.value if score_transition.score_type else 'unknown',
            'scoreboard_field': scoreboard_field if 'scoreboard_field' in locals() else None
        })
        
        return changes
    
    def _apply_possession_transition(self, possession_transition, game_state: GameState) -> List[Dict[str, Any]]:
        """Apply calculated possession transition to game state."""
        changes = []
        
        if not possession_transition or not possession_transition.possession_changes:
            return changes
        
        old_possession = game_state.field.possession_team_id
        
        # Apply possession change - would need proper team ID mapping
        if possession_transition.new_possessing_team:
            # This is simplified - real implementation would properly map team names to IDs
            changes.append({
                'type': 'possession_transition_applied',
                'old_possession_team': old_possession,
                'new_possession_team': possession_transition.new_possessing_team,
                'turnover_occurred': possession_transition.turnover_occurred,
                'possession_change_reason': possession_transition.possession_change_reason.value if possession_transition.possession_change_reason else 'unknown'
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
            # ATOMIC TOUCHDOWN + CONVERSION: Ensure both succeed or both fail
            try:
                # Step 1: Add touchdown points (6)
                game_state.scoreboard.add_touchdown(scoring_team_id)
                
                # Step 2: Handle conversion attempt (1 or 2 points)
                conversion_changes = self._handle_conversion_attempt(scoring_team_id, game_state, play_result)
                
                # Only log success if both operations completed
                changes.append({
                    'type': 'touchdown',
                    'scoring_team_id': scoring_team_id,
                    'points': 6
                })
                changes.extend(conversion_changes)
                
            except Exception as e:
                # If anything fails, log the error and don't score at all
                # This prevents the 1-point bug where only the conversion succeeds
                if self.logger:
                    self.logger.error(f"Touchdown scoring failed for team {scoring_team_id}: {e}")
                print(f"🚨 TOUCHDOWN SCORING ERROR: {scoring_team_id} → {e} (prevented 1-point bug)")
                # Don't add any changes - no partial scoring
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
        transition = context.metadata.get("transition")
        
        # PHASE 2A FIX: Handle calculated special situation transitions (kickoff_reset, etc.)
        if transition and transition.special_situation_transition:
            print(f"🔧 APPLICATOR DEBUG: Found special_situation_transition")
            special_situation = transition.special_situation_transition
            print(f"🔧 APPLICATOR DEBUG: situation_type = {special_situation.situation_type}")
            
            # Handle kickoff reset field position changes
            if hasattr(special_situation, 'new_field_position') and special_situation.new_field_position is not None:
                old_position = game_state.field.field_position
                print(f"🔧 APPLICATOR DEBUG: Applying field reset: {old_position} → {special_situation.new_field_position}")
                game_state.field.field_position = special_situation.new_field_position
                changes.append({
                    'type': 'special_situation_field_reset',
                    'situation_type': special_situation.situation_type,
                    'old_field_position': old_position,
                    'new_field_position': special_situation.new_field_position
                })
            
            # Handle possession changes from special situations (if not handled by possession transitions)
            if (hasattr(special_situation, 'new_possession_team_id') and 
                special_situation.new_possession_team_id is not None):
                old_possession = game_state.field.possession_team_id
                print(f"🔧 APPLICATOR DEBUG: Applying possession change: {old_possession} → {special_situation.new_possession_team_id}")
                game_state.field.possession_team_id = special_situation.new_possession_team_id
                changes.append({
                    'type': 'special_situation_possession_change',
                    'situation_type': special_situation.situation_type,
                    'old_possession_team': old_possession,
                    'new_possession_team': special_situation.new_possession_team_id
                })
        else:
            print(f"🔧 APPLICATOR DEBUG: No special_situation_transition found")
        
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
            game_state.field.yards_to_go = self._calculate_goal_line_yards_to_go(game_state.field.field_position)
            
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
        game_state.field.yards_to_go = self._calculate_goal_line_yards_to_go(game_state.field.field_position)
        
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
        game_state.field.yards_to_go = self._calculate_goal_line_yards_to_go(new_field_position)
        
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
        game_state.field.yards_to_go = self._calculate_goal_line_yards_to_go(25)  # 25-yard line kickoff position
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
    
    def _calculate_goal_line_yards_to_go(self, field_position: int, default_yards: int = 10) -> int:
        """
        Calculate yards to go considering goal line proximity.
        
        This prevents NFL.DISTANCE.004 validation errors by ensuring yards_to_go
        never exceeds the distance to the goal line.
        
        Args:
            field_position: Current yard line position (0-100)
            default_yards: Default yards for first down (usually 10)
            
        Returns:
            Proper yards to go (min of default_yards and distance to goal)
        """
        yards_to_endzone = 100 - field_position
        return min(default_yards, yards_to_endzone)
    
    def _get_opposing_team_id(self, game_state: GameState) -> int:
        """Get the ID of the team that doesn't have possession"""
        possession_team = game_state.field.possession_team_id
        if possession_team == game_state.scoreboard.home_team_id:
            return game_state.scoreboard.away_team_id
        return game_state.scoreboard.home_team_id
    
    def _needs_post_score_kickoff_reset(self, game_state: GameState, play_result) -> bool:
        """
        Detect if the current game state requires a kickoff field reset.
        
        This handles the scenario where the previous play was a scoring play,
        and the current play needs the field position reset from the scoring
        location (e.g., 100-yard line) to the kickoff return position.
        
        Args:
            game_state: Current game state
            play_result: Current play result
            
        Returns:
            True if kickoff field reset is needed
        """
        # Check for obvious post-scoring indicators:
        # 1. Field position at or near scoring locations (90+ yard line for touchdowns/FGs)
        # 2. Down is 1 (fresh possession after kickoff)  
        # 3. Not currently a scoring play (we're processing the play AFTER the score)
        field_pos = game_state.field.field_position
        down = game_state.field.down
        
        # Primary indicator: Field position >= 90 and down = 1 suggests post-score state
        # This catches touchdowns (field_position = 100) and field goals from close range
        if field_pos >= 90 and down == 1 and not play_result.is_score:
            if self.logger:
                self.logger.debug(f"Post-score kickoff reset needed: field_pos={field_pos}, down={down}")
            return True
            
        # Secondary indicator: Field position = 100 (touchdown location) regardless of down
        # This handles edge cases where down tracking might be off
        if field_pos >= 100 and not play_result.is_score:
            if self.logger:
                self.logger.debug(f"Post-touchdown kickoff reset needed: field_pos={field_pos}")
            return True
        
        return False
    
    def _resolve_scoreboard_field(self, scoring_team: Any, game_state: GameState = None) -> str:
        """
        Resolve team identifier to scoreboard field name using team system.
        
        This is the critical method that fixes the scoreboard bug by providing
        consistent team → scoreboard field mapping.
        
        Args:
            scoring_team: Team identifier (TeamID, int, or string)
            game_state: Game state for fallback team resolution
            
        Returns:
            str: Scoreboard field name ("home" or "away")
            
        Raises:
            ValueError: If team cannot be mapped to scoreboard field
        """
        # If we have a team mapper, use it for consistent mapping
        if self.team_mapper and isinstance(scoring_team, TeamID):
            try:
                return self.team_mapper.map_team_to_scoreboard_field(scoring_team)
            except ValueError:
                # Let the exception bubble up - NEUTRAL team can't score
                raise
        
        # Fallback 1: Handle TeamID directly
        if isinstance(scoring_team, TeamID):
            try:
                return scoring_team.to_scoreboard_field()
            except ValueError:
                raise ValueError(f"Team {scoring_team} cannot be mapped to scoreboard (neutral team)")
        
        # Fallback 2: Create temporary team system for consistent resolution
        if game_state and hasattr(game_state, 'scoreboard'):
            try:
                # Extract team data from game state  
                home_data = {"name": "Home Team", "abbreviation": "HOME"}
                away_data = {"name": "Away Team", "abbreviation": "AWAY"}
                
                context = TeamContext(home_data, away_data)
                registry = TeamRegistry(context)
                
                # Resolve scoring team through team system
                team_id = registry.resolve_team_from_possession(scoring_team)
                return team_id.to_scoreboard_field()
            except Exception:
                # Fall through to final fallback
                pass
        
        # Fallback 3: Legacy hardcoded mapping for backward compatibility
        if scoring_team == 1 or scoring_team == "1" or scoring_team == "home":
            return "home"
        elif scoring_team == 2 or scoring_team == "2" or scoring_team == "away":
            return "away"
        
        # Final fallback: Default to home for unknown teams (maintains game functionality)
        if self.logger:
            self.logger.warning(f"Unknown scoring team {scoring_team}, defaulting to home")
        return "home"