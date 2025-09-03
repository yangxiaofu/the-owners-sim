"""
Field Validator

Validates field position bounds, down/distance rules, and field-related 
game state transitions to ensure they conform to NFL field dimensions
and down/distance progression rules.
"""

from typing import Any, Dict, Optional
import logging
from game_engine.state_transitions.validators.validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)


class FieldValidator:
    """Validates field position and down/distance state transitions"""
    
    def __init__(self):
        """Initialize field validator with debug logging."""
        self.logger = logging.getLogger(__name__)
    
    # NFL Field Constants
    FIELD_MIN_POSITION = 0    # Goal line (safety/touchback zone)
    FIELD_MAX_POSITION = 100  # Opposite goal line (touchdown zone)
    MIN_DOWN = 1
    MAX_DOWN = 4
    STANDARD_YARDS_TO_GO = 10
    MIN_YARDS_TO_GO = 0
    MAX_YARDS_TO_GO = 99      # Theoretical maximum (99-yard line, 1st down)
    
    # Field zones for contextual validation
    SAFETY_ZONE = 0
    TOUCHBACK_ZONE_START = 1
    TOUCHBACK_ZONE_END = 25
    RED_ZONE_START = 80
    TOUCHDOWN_ZONE = 100
    
    def validate_field_position(self, position: int, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate field position is within legal bounds
        
        Args:
            position: Field position (0-100 yard line)
            context: Additional context for validation
            
        Returns:
            ValidationResult with any field position violations
        """
        builder = ValidationResultBuilder()
        
        # Basic bounds checking
        if not isinstance(position, int):
            builder.add_error(
                ValidationCategory.FIELD_BOUNDS,
                "Field position must be an integer",
                field_name="field_position",
                current_value=position,
                expected_value="integer between 0-100",
                rule_reference="NFL.FIELD.001"
            )
        elif position < self.FIELD_MIN_POSITION:
            builder.add_error(
                ValidationCategory.FIELD_BOUNDS,
                "Field position cannot be less than 0 (behind goal line)",
                field_name="field_position", 
                current_value=position,
                expected_value=f">= {self.FIELD_MIN_POSITION}",
                rule_reference="NFL.FIELD.002"
            )
        elif position > self.FIELD_MAX_POSITION:
            builder.add_error(
                ValidationCategory.FIELD_BOUNDS,
                "Field position cannot exceed 100 (beyond goal line)",
                field_name="field_position",
                current_value=position,
                expected_value=f"<= {self.FIELD_MAX_POSITION}",
                rule_reference="NFL.FIELD.003"
            )
        
        # Contextual warnings for unusual field positions
        if position == self.SAFETY_ZONE:
            builder.add_warning(
                ValidationCategory.FIELD_BOUNDS,
                "Field position at 0-yard line (safety zone) - verify intentional",
                field_name="field_position",
                current_value=position,
                rule_reference="NFL.FIELD.004"
            )
        elif position == self.TOUCHDOWN_ZONE:
            builder.add_warning(
                ValidationCategory.FIELD_BOUNDS, 
                "Field position at 100-yard line (touchdown zone) - verify intentional",
                field_name="field_position",
                current_value=position,
                rule_reference="NFL.FIELD.005"
            )
        
        return builder.build()
    
    def validate_down_progression(self, current_down: int, new_down: int, 
                                  yards_gained: int, yards_to_go: int,
                                  context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate down progression follows NFL rules
        
        Args:
            current_down: Current down (1-4)
            new_down: Proposed new down (1-4)  
            yards_gained: Yards gained on the play
            yards_to_go: Yards needed for first down
            context: Additional validation context
            
        Returns:
            ValidationResult with down progression violations
        """
        # Validation with scoring context support
        self.logger.debug(
            f"Validating down progression: {current_down} -> {new_down}, "
            f"yards: {yards_gained}, context: {bool(context)}"
        )
        
        builder = ValidationResultBuilder()
        
        # Validate current down is legal
        if not isinstance(current_down, int) or current_down < self.MIN_DOWN or current_down > self.MAX_DOWN:
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                f"Current down must be between {self.MIN_DOWN} and {self.MAX_DOWN}",
                field_name="current_down",
                current_value=current_down,
                expected_value=f"{self.MIN_DOWN}-{self.MAX_DOWN}",
                rule_reference="NFL.DOWN.001"
            )
        
        # Validate new down is legal  
        if not isinstance(new_down, int) or new_down < self.MIN_DOWN or new_down > self.MAX_DOWN:
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                f"New down must be between {self.MIN_DOWN} and {self.MAX_DOWN}",
                field_name="new_down",
                current_value=new_down,
                expected_value=f"{self.MIN_DOWN}-{self.MAX_DOWN}",
                rule_reference="NFL.DOWN.002"
            )
        
        # If basic validation passed, check progression logic
        if (self.MIN_DOWN <= current_down <= self.MAX_DOWN and 
            self.MIN_DOWN <= new_down <= self.MAX_DOWN):
            
            # CHECK FOR SCORING CONTEXT FIRST
            scoring_context = self._detect_scoring_context(context)
            self.logger.debug(f"SCORING DETECTION - {scoring_context}")
            
            if scoring_context['is_scoring_play']:
                # Scoring plays reset downs to 1st down
                if new_down == 1:
                    self.logger.debug(f"VALID SCORING PLAY - {scoring_context['score_type']} resets down to 1")
                    return create_success_result()
                else:
                    builder.add_error(
                        ValidationCategory.DOWN_DISTANCE,
                        f"{scoring_context['score_type']} should reset down to 1st",
                        field_name="new_down",
                        current_value=new_down,
                        expected_value=1,
                        rule_reference="NFL.SCORE.DOWN.001"
                    )
            elif yards_gained >= yards_to_go:
                # First down achieved (non-scoring)
                self.logger.debug(f"FIRST DOWN ACHIEVED - {yards_gained} >= {yards_to_go}")
                if new_down != 1:
                    builder.add_error(
                        ValidationCategory.DOWN_DISTANCE,
                        "First down achieved but new down is not 1st",
                        field_name="new_down",
                        current_value=new_down,
                        expected_value=1,
                        rule_reference="NFL.DOWN.003"
                    )
            else:
                # Down should advance (normal progression)
                expected_down = current_down + 1
                self.logger.debug(f"NORMAL DOWN ADVANCE - expected {expected_down}")
                if current_down == 4:
                    # 4th down failure should result in turnover (handled elsewhere)
                    builder.add_info(
                        ValidationCategory.DOWN_DISTANCE,
                        "4th down failed - turnover on downs expected",
                        field_name="current_down",
                        current_value=current_down,
                        rule_reference="NFL.DOWN.004"
                    )
                elif new_down != expected_down:
                    builder.add_error(
                        ValidationCategory.DOWN_DISTANCE,
                        f"Down progression incorrect - expected {expected_down}",
                        field_name="new_down", 
                        current_value=new_down,
                        expected_value=expected_down,
                        rule_reference="NFL.DOWN.005"
                    )
        
        return builder.build()
    
    def _detect_scoring_context(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Detect if this is a scoring play based on context information.
        
        Args:
            context: Validation context that may contain scoring information
            
        Returns:
            Dictionary with scoring detection results:
            {
                'is_scoring_play': bool,
                'score_type': str or None,
                'detection_method': str
            }
        """
        default_result = {
            'is_scoring_play': False,
            'score_type': None,
            'detection_method': 'no_context'
        }
        
        if not context:
            self.logger.debug("No context provided for scoring detection")
            return default_result
        
        # Method 1: Check for explicit scoring flags in context
        if context.get('is_scoring_play'):
            score_type = context.get('score_type', 'unknown_score')
            self.logger.debug(f"Scoring detected via context flag: {score_type}")
            return {
                'is_scoring_play': True,
                'score_type': score_type,
                'detection_method': 'context_flag'
            }
        
        # Method 2: Check for play_result in context
        play_result = context.get('play_result')
        if play_result:
            if hasattr(play_result, 'is_score') and play_result.is_score:
                score_type = getattr(play_result, 'outcome', 'unknown_score')
                self.logger.debug(f"Scoring detected via play_result: {score_type}")
                return {
                    'is_scoring_play': True,
                    'score_type': score_type,
                    'detection_method': 'play_result'
                }
        
        # Method 3: Check for scoring outcomes in context
        outcome = context.get('outcome')
        scoring_outcomes = ['touchdown', 'safety', 'field_goal']
        if outcome in scoring_outcomes:
            self.logger.debug(f"Scoring detected via outcome: {outcome}")
            return {
                'is_scoring_play': True,
                'score_type': outcome,
                'detection_method': 'outcome'
            }
        
        # Method 4: Check field position transitions for touchdown
        field_position = context.get('field_position')
        new_field_position = context.get('new_field_position')
        if new_field_position == self.TOUCHDOWN_ZONE:
            self.logger.debug(f"Touchdown detected via field position: {field_position} -> {new_field_position}")
            return {
                'is_scoring_play': True,
                'score_type': 'touchdown',
                'detection_method': 'field_position'
            }
        elif new_field_position == self.SAFETY_ZONE:
            self.logger.debug(f"Safety detected via field position: {field_position} -> {new_field_position}")
            return {
                'is_scoring_play': True,
                'score_type': 'safety',
                'detection_method': 'field_position'
            }
        
        # Method 5: Check for score_transition in context
        if context.get('score_transition'):
            score_transition = context['score_transition']
            if hasattr(score_transition, 'score_occurred') and score_transition.score_occurred:
                score_type = getattr(score_transition, 'score_type', 'unknown_score')
                self.logger.debug(f"Scoring detected via score_transition: {score_type}")
                return {
                    'is_scoring_play': True,
                    'score_type': str(score_type),
                    'detection_method': 'score_transition'
                }
        
        # Method 6: Check for possession change reasons that indicate scoring
        # Prioritize context over transition property for current play accuracy
        possession_change_reason = context.get('possession_change_reason')
        
        # Only proceed if this is actually a scoring play (not aftermath)
        is_current_score = context.get('is_scoring_play', False) or context.get('outcome') in ['touchdown', 'field_goal', 'safety']
        
        if possession_change_reason and is_current_score:
            scoring_possession_reasons = [
                'TOUCHDOWN_SCORED',
                'FIELD_GOAL_SCORED', 
                'SAFETY_SCORED'
            ]
            
            # Handle both string and enum values
            reason_str = str(possession_change_reason)
            if any(scoring_reason in reason_str for scoring_reason in scoring_possession_reasons):
                if 'TOUCHDOWN' in reason_str:
                    score_type = 'touchdown'
                elif 'FIELD_GOAL' in reason_str:
                    score_type = 'field_goal'
                elif 'SAFETY' in reason_str:
                    score_type = 'safety'
                else:
                    score_type = 'unknown_score'
                    
                self.logger.debug(f"Scoring detected via possession change reason: {reason_str} -> {score_type}")
                return {
                    'is_scoring_play': True,
                    'score_type': score_type,
                    'detection_method': 'possession_change_reason'
                }
        
        self.logger.debug("No scoring context detected")
        return default_result
    
    def validate_yards_to_go(self, yards_to_go: int, field_position: int,
                             context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate yards to go is logical given field position
        
        Args:
            yards_to_go: Yards needed for first down
            field_position: Current field position
            context: Additional validation context
            
        Returns:
            ValidationResult with yards to go violations
        """
        builder = ValidationResultBuilder()
        
        # Basic validation
        if not isinstance(yards_to_go, int):
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                "Yards to go must be an integer",
                field_name="yards_to_go",
                current_value=yards_to_go,
                expected_value="integer",
                rule_reference="NFL.DISTANCE.001"
            )
            return builder.build()
        
        if yards_to_go < self.MIN_YARDS_TO_GO:
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                "Yards to go cannot be negative",
                field_name="yards_to_go",
                current_value=yards_to_go,
                expected_value=f">= {self.MIN_YARDS_TO_GO}",
                rule_reference="NFL.DISTANCE.002"
            )
        
        if yards_to_go > self.MAX_YARDS_TO_GO:
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                "Yards to go exceeds field length",
                field_name="yards_to_go",
                current_value=yards_to_go,
                expected_value=f"<= {self.MAX_YARDS_TO_GO}",
                rule_reference="NFL.DISTANCE.003"
            )
        
        # Goal line logic - yards to go should not exceed distance to goal
        if field_position is not None and isinstance(field_position, int):
            distance_to_goal = self.TOUCHDOWN_ZONE - field_position
            if distance_to_goal > 0 and yards_to_go > distance_to_goal:
                builder.add_error(
                    ValidationCategory.DOWN_DISTANCE,
                    f"Yards to go ({yards_to_go}) exceeds distance to goal line ({distance_to_goal})",
                    field_name="yards_to_go",
                    current_value=yards_to_go,
                    expected_value=f"<= {distance_to_goal}",
                    rule_reference="NFL.DISTANCE.004"
                )
        
        # Warning for unusual yards to go values
        if yards_to_go > 20:
            builder.add_warning(
                ValidationCategory.DOWN_DISTANCE,
                f"Unusual yards to go distance ({yards_to_go}) - verify penalty or unusual situation",
                field_name="yards_to_go",
                current_value=yards_to_go,
                rule_reference="NFL.DISTANCE.005"
            )
        
        return builder.build()
    
    def validate_field_transition(self, current_position: int, new_position: int,
                                  yards_gained: int, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate field position change is consistent with yards gained
        
        Args:
            current_position: Current field position
            new_position: New field position after play
            yards_gained: Reported yards gained
            context: Additional validation context
            
        Returns:
            ValidationResult with field transition violations
        """
        builder = ValidationResultBuilder()
        
        # Validate both positions individually first
        current_result = self.validate_field_position(current_position, context)
        new_result = self.validate_field_position(new_position, context)
        
        # Merge results
        for issue in current_result.issues + new_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        # If basic positions are valid, check transition logic
        if current_result.is_valid and new_result.is_valid:
            expected_position = current_position + yards_gained
            
            # Handle boundary conditions (safeties and touchdowns handled elsewhere)
            if expected_position < self.FIELD_MIN_POSITION:
                expected_position = self.FIELD_MIN_POSITION
            elif expected_position > self.FIELD_MAX_POSITION:
                expected_position = self.FIELD_MAX_POSITION
            
            if new_position != expected_position:
                builder.add_error(
                    ValidationCategory.FIELD_BOUNDS,
                    f"Field position change inconsistent with yards gained",
                    field_name="new_position",
                    current_value=new_position,
                    expected_value=expected_position,
                    rule_reference="NFL.FIELD.006"
                )
                builder.add_metadata("current_position", current_position)
                builder.add_metadata("yards_gained", yards_gained)
                builder.add_metadata("calculated_position", expected_position)
        
        return builder.build()
    
    def validate_complete_field_state(self, field_position: int, down: int, 
                                      yards_to_go: int, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Comprehensive validation of complete field state
        
        Args:
            field_position: Current field position (0-100)
            down: Current down (1-4)
            yards_to_go: Yards needed for first down
            context: Additional validation context
            
        Returns:
            ValidationResult with all field state violations
        """
        builder = ValidationResultBuilder()
        
        # Individual validations
        position_result = self.validate_field_position(field_position, context)
        yards_result = self.validate_yards_to_go(yards_to_go, field_position, context)
        
        # Add all issues
        for result in [position_result, yards_result]:
            for issue in result.issues:
                builder.issues.append(issue) 
                if issue.severity.value == "error":
                    builder._is_valid = False
        
        # Down validation
        if not isinstance(down, int) or down < self.MIN_DOWN or down > self.MAX_DOWN:
            builder.add_error(
                ValidationCategory.DOWN_DISTANCE,
                f"Down must be between {self.MIN_DOWN} and {self.MAX_DOWN}",
                field_name="down",
                current_value=down,
                expected_value=f"{self.MIN_DOWN}-{self.MAX_DOWN}",
                rule_reference="NFL.DOWN.006"
            )
        
        # Cross-field validation - check for logical consistency
        if (isinstance(field_position, int) and isinstance(yards_to_go, int) and 
            field_position > self.RED_ZONE_START and yards_to_go == self.STANDARD_YARDS_TO_GO):
            
            # In red zone, standard 10 yards to go might put them past goal line
            distance_to_goal = self.TOUCHDOWN_ZONE - field_position
            if distance_to_goal < self.STANDARD_YARDS_TO_GO:
                builder.add_info(
                    ValidationCategory.DOWN_DISTANCE,
                    f"In red zone - yards to goal ({distance_to_goal}) less than standard first down distance",
                    rule_reference="NFL.REDZONE.001"
                )
        
        return builder.build()


# Convenience functions for common validations
def validate_field_position(position: int) -> ValidationResult:
    """Quick field position validation"""
    validator = FieldValidator()
    return validator.validate_field_position(position)


def validate_down_and_distance(down: int, yards_to_go: int, field_position: int = None) -> ValidationResult:
    """Quick down and distance validation"""
    validator = FieldValidator()
    builder = ValidationResultBuilder()
    
    # Validate down
    if not isinstance(down, int) or down < 1 or down > 4:
        builder.add_error(
            ValidationCategory.DOWN_DISTANCE,
            "Down must be between 1 and 4",
            field_name="down",
            current_value=down,
            expected_value="1-4"
        )
    
    # Validate yards to go
    yards_result = validator.validate_yards_to_go(yards_to_go, field_position)
    for issue in yards_result.issues:
        builder.issues.append(issue)
        if issue.severity.value == "error":
            builder._is_valid = False
    
    return builder.build()