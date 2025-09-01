"""
Field Validator

Validates field position bounds, down/distance rules, and field-related 
game state transitions to ensure they conform to NFL field dimensions
and down/distance progression rules.
"""

from typing import Any, Dict, Optional
from .validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)


class FieldValidator:
    """Validates field position and down/distance state transitions"""
    
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
            
            if yards_gained >= yards_to_go:
                # First down achieved
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
                # Down should advance
                expected_down = current_down + 1
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