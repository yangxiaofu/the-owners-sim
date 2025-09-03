"""
Possession Validator

Validates possession changes to ensure they follow NFL rules for
turnovers, punts, kickoffs, and other possession transfer scenarios.
"""

from typing import Any, Dict, Optional, List
from enum import Enum
from game_engine.state_transitions.validators.validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)


class PossessionChangeReason(Enum):
    """Valid reasons for possession changes in NFL"""
    KICKOFF = "kickoff"                    # Start of game/half, after score
    PUNT = "punt"                         # Voluntary punt on 4th down  
    TURNOVER_ON_DOWNS = "turnover_on_downs"  # Failed 4th down conversion
    INTERCEPTION = "interception"         # Pass intercepted
    FUMBLE = "fumble"                    # Ball fumbled and recovered by defense
    BLOCKED_KICK = "blocked_kick"        # Kick blocked and recovered
    ONSIDE_KICK = "onside_kick"          # Special kickoff type
    SAFETY = "safety"                    # Safety scored, possession flips
    MUFFED_PUNT = "muffed_punt"          # Punt muffed by receiving team
    FIELD_GOAL_MISS = "field_goal_miss"  # Missed field goal, defense takes over
    TOUCHDOWN = "touchdown"              # After touchdown, kickoff to other team
    HALF_TIME = "half_time"              # Possession change at half
    OVERTIME = "overtime"                # Overtime possession rules
    

class PossessionValidator:
    """Validates possession transfer scenarios according to NFL rules"""
    
    def validate_possession_change(self, current_team: int, new_team: int,
                                   reason: PossessionChangeReason, down: int,
                                   field_position: int, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate that a possession change is legal given the circumstances
        
        Args:
            current_team: Team ID currently in possession
            new_team: Team ID taking possession  
            reason: Reason for the possession change
            down: Down on which possession changed
            field_position: Field position where change occurred
            context: Additional context (play_result, game_state, etc.)
            
        Returns:
            ValidationResult with possession change violations
        """
        builder = ValidationResultBuilder()
        
        # Basic validation
        if current_team == new_team and reason != PossessionChangeReason.ONSIDE_KICK:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                "Possession cannot change to the same team (except onside kicks)",
                field_name="new_team",
                current_value=new_team,
                expected_value=f"different from {current_team}",
                rule_reference="NFL.POSSESSION.001"
            )
        
        if current_team is None or new_team is None:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                "Team IDs must be specified for possession changes",
                field_name="team_ids",
                current_value=f"current: {current_team}, new: {new_team}",
                expected_value="both non-null",
                rule_reference="NFL.POSSESSION.002"
            )
        
        # Validate possession change based on reason
        reason_result = self._validate_possession_reason(reason, down, field_position, context)
        for issue in reason_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        return builder.build()
    
    def _validate_possession_reason(self, reason: PossessionChangeReason, down: int, 
                                    field_position: int, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate that the reason for possession change is appropriate"""
        builder = ValidationResultBuilder()
        
        if reason == PossessionChangeReason.TURNOVER_ON_DOWNS:
            return self._validate_turnover_on_downs(down, field_position, context)
        
        elif reason == PossessionChangeReason.PUNT:
            return self._validate_punt_possession(down, field_position, context)
        
        elif reason == PossessionChangeReason.KICKOFF:
            return self._validate_kickoff_possession(context)
        
        elif reason == PossessionChangeReason.INTERCEPTION:
            return self._validate_interception_possession(context)
        
        elif reason == PossessionChangeReason.FUMBLE:
            return self._validate_fumble_possession(context)
        
        elif reason == PossessionChangeReason.FIELD_GOAL_MISS:
            return self._validate_field_goal_miss_possession(down, field_position, context)
        
        elif reason == PossessionChangeReason.SAFETY:
            return self._validate_safety_possession(field_position, context)
        
        elif reason == PossessionChangeReason.TOUCHDOWN:
            return self._validate_touchdown_possession(field_position, context)
        
        else:
            # Handle both enum and string values for robustness
            reason_display = reason.value if hasattr(reason, 'value') else str(reason)
            builder.add_info(
                ValidationCategory.POSSESSION_CHANGE,
                f"Possession change reason '{reason_display}' - assuming valid for special situations",
                rule_reference="NFL.POSSESSION.003"
            )
        
        return builder.build()
    
    def _validate_turnover_on_downs(self, down: int, field_position: int, 
                                    context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate turnover on downs is appropriate"""
        builder = ValidationResultBuilder()
        
        if down != 4:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                "Turnover on downs can only occur on 4th down",
                field_name="down",
                current_value=down,
                expected_value=4,
                rule_reference="NFL.POSSESSION.004"
            )
        
        # Check if conversion was attempted and failed
        if context and "yards_gained" in context and "yards_to_go" in context:
            yards_gained = context["yards_gained"]
            yards_to_go = context["yards_to_go"]
            
            if yards_gained >= yards_to_go:
                builder.add_error(
                    ValidationCategory.POSSESSION_CHANGE,
                    "Cannot have turnover on downs when conversion was successful",
                    field_name="yards_gained",
                    current_value=yards_gained,
                    expected_value=f"< {yards_to_go}",
                    rule_reference="NFL.POSSESSION.005"
                )
        
        return builder.build()
    
    def _validate_punt_possession(self, down: int, field_position: int,
                                  context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate punt possession change"""
        builder = ValidationResultBuilder()
        
        # Punts typically occur on 4th down
        if down != 4:
            builder.add_warning(
                ValidationCategory.POSSESSION_CHANGE,
                f"Punt on {down} down is unusual - typically occurs on 4th down",
                field_name="down", 
                current_value=down,
                expected_value=4,
                rule_reference="NFL.POSSESSION.006"
            )
        
        # Check if punt makes strategic sense
        if field_position is not None and field_position > 70:
            builder.add_warning(
                ValidationCategory.POSSESSION_CHANGE,
                f"Punt from {field_position}-yard line is unusual - typically field goal territory",
                field_name="field_position",
                current_value=field_position,
                rule_reference="NFL.POSSESSION.007"
            )
        
        return builder.build()
    
    def _validate_kickoff_possession(self, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate kickoff possession change"""
        builder = ValidationResultBuilder()
        
        # Kickoffs should occur after scores or at start of game/half
        valid_kickoff_situations = [
            "game_start", "second_half_start", "overtime_start",
            "after_touchdown", "after_field_goal", "after_safety"
        ]
        
        if context and "situation" in context:
            situation = context["situation"]
            if situation not in valid_kickoff_situations:
                builder.add_warning(
                    ValidationCategory.POSSESSION_CHANGE,
                    f"Kickoff in situation '{situation}' may not be appropriate",
                    field_name="situation",
                    current_value=situation,
                    expected_value=f"one of {valid_kickoff_situations}",
                    rule_reference="NFL.POSSESSION.008"
                )
        
        return builder.build()
    
    def _validate_interception_possession(self, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate interception possession change"""
        builder = ValidationResultBuilder()
        
        # Interceptions can only occur on pass plays
        if context and "play_type" in context:
            play_type = context["play_type"]
            if play_type != "pass":
                builder.add_error(
                    ValidationCategory.POSSESSION_CHANGE,
                    "Interception can only occur on passing plays",
                    field_name="play_type",
                    current_value=play_type,
                    expected_value="pass",
                    rule_reference="NFL.POSSESSION.009"
                )
        
        return builder.build()
    
    def _validate_fumble_possession(self, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate fumble possession change"""
        builder = ValidationResultBuilder()
        
        # Fumbles can occur on any play type - no specific restrictions
        # Could add context-specific validations here if needed
        
        if context and "recovered_by" in context and "fumbled_by" in context:
            fumbled_by = context["fumbled_by"] 
            recovered_by = context["recovered_by"]
            
            if fumbled_by == recovered_by:
                builder.add_info(
                    ValidationCategory.POSSESSION_CHANGE,
                    "Fumble recovered by same team - no possession change should occur",
                    rule_reference="NFL.POSSESSION.010"
                )
        
        return builder.build()
    
    def _validate_field_goal_miss_possession(self, down: int, field_position: int,
                                             context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate field goal miss possession change"""
        builder = ValidationResultBuilder()
        
        # Field goal attempts typically on 4th down
        if down != 4:
            builder.add_warning(
                ValidationCategory.POSSESSION_CHANGE,
                f"Field goal attempt on {down} down is unusual",
                field_name="down",
                current_value=down,
                expected_value=4,
                rule_reference="NFL.POSSESSION.011"
            )
        
        # Field goals typically attempted within reasonable range
        if field_position is not None and field_position < 50:
            builder.add_warning(
                ValidationCategory.POSSESSION_CHANGE,
                f"Field goal attempt from {field_position}-yard line is very long range",
                field_name="field_position",
                current_value=field_position,
                rule_reference="NFL.POSSESSION.012"
            )
        
        return builder.build()
    
    def _validate_safety_possession(self, field_position: int, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate safety possession change"""
        builder = ValidationResultBuilder()
        
        # Safeties occur in the end zone (position 0)
        if field_position != 0:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                "Safety can only occur at the 0-yard line (in end zone)",
                field_name="field_position",
                current_value=field_position,
                expected_value=0,
                rule_reference="NFL.POSSESSION.013"
            )
        
        return builder.build()
    
    def _validate_touchdown_possession(self, field_position: int, context: Optional[Dict[str, Any]]) -> ValidationResult:
        """Validate touchdown possession change (subsequent kickoff)"""
        builder = ValidationResultBuilder()
        
        # Touchdowns occur at the 100-yard line
        if field_position != 100:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                "Touchdown can only occur at the 100-yard line (in end zone)",
                field_name="field_position",
                current_value=field_position,
                expected_value=100,
                rule_reference="NFL.POSSESSION.014"
            )
        
        return builder.build()
    
    def validate_no_possession_change(self, current_team: int, new_team: int,
                                      play_outcome: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate that possession correctly remains with the same team
        
        Args:
            current_team: Team currently in possession
            new_team: Team that should still have possession
            play_outcome: Outcome of the play
            context: Additional context
            
        Returns:
            ValidationResult for possession continuity
        """
        builder = ValidationResultBuilder()
        
        if current_team != new_team:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                f"Possession should not change on play outcome '{play_outcome}'",
                field_name="possession_team",
                current_value=new_team,
                expected_value=current_team,
                rule_reference="NFL.POSSESSION.015"
            )
        
        # Check for outcomes that should never cause possession change
        non_turnover_outcomes = [
            "complete", "incomplete", "run", "sack", "penalty_accepted",
            "first_down", "short_gain", "no_gain"
        ]
        
        if play_outcome in non_turnover_outcomes and current_team != new_team:
            builder.add_error(
                ValidationCategory.POSSESSION_CHANGE,
                f"Play outcome '{play_outcome}' should never cause possession change",
                field_name="play_outcome",
                current_value=play_outcome,
                rule_reference="NFL.POSSESSION.016"
            )
        
        return builder.build()
    
    def validate_possession_transition_sequence(self, transitions: List[Dict[str, Any]]) -> ValidationResult:
        """
        Validate a sequence of possession transitions for logical consistency
        
        Args:
            transitions: List of possession transition dictionaries
            
        Returns:
            ValidationResult for the entire sequence
        """
        builder = ValidationResultBuilder()
        
        if not transitions:
            return create_success_result()
        
        # Track possession flow
        previous_team = None
        
        for i, transition in enumerate(transitions):
            current_team = transition.get("current_team")
            new_team = transition.get("new_team") 
            reason = transition.get("reason")
            
            if previous_team is not None and current_team != previous_team:
                builder.add_error(
                    ValidationCategory.POSSESSION_CHANGE,
                    f"Possession sequence broken at transition {i}: expected current_team {previous_team}, got {current_team}",
                    field_name=f"transition_{i}_current_team",
                    current_value=current_team,
                    expected_value=previous_team,
                    rule_reference="NFL.POSSESSION.017"
                )
            
            # Validate individual transition
            if "down" in transition and "field_position" in transition:
                transition_result = self.validate_possession_change(
                    current_team, new_team, reason,
                    transition["down"], transition["field_position"],
                    transition.get("context")
                )
                
                for issue in transition_result.issues:
                    builder.issues.append(issue)
                    if issue.severity.value == "error":
                        builder._is_valid = False
            
            previous_team = new_team
        
        return builder.build()


# Convenience functions
def validate_turnover(current_team: int, new_team: int, reason: str) -> ValidationResult:
    """Quick turnover validation"""
    validator = PossessionValidator()
    try:
        reason_enum = PossessionChangeReason(reason.lower())
        return validator.validate_possession_change(current_team, new_team, reason_enum, 4, 50)
    except ValueError:
        builder = ValidationResultBuilder()
        builder.add_error(
            ValidationCategory.POSSESSION_CHANGE,
            f"Invalid possession change reason: {reason}",
            field_name="reason",
            current_value=reason
        )
        return builder.build()


def validate_fourth_down_outcome(down: int, yards_gained: int, yards_to_go: int,
                                 possession_changed: bool) -> ValidationResult:
    """Quick 4th down possession validation"""
    builder = ValidationResultBuilder()
    
    if down != 4:
        builder.add_error(
            ValidationCategory.POSSESSION_CHANGE,
            "This validation is only for 4th down plays",
            field_name="down",
            current_value=down,
            expected_value=4
        )
        return builder.build()
    
    conversion_successful = yards_gained >= yards_to_go
    
    if conversion_successful and possession_changed:
        builder.add_error(
            ValidationCategory.POSSESSION_CHANGE,
            "Possession should not change on successful 4th down conversion",
            field_name="possession_changed",
            current_value=possession_changed,
            expected_value=False
        )
    elif not conversion_successful and not possession_changed:
        builder.add_error(
            ValidationCategory.POSSESSION_CHANGE,
            "Possession should change on failed 4th down conversion",
            field_name="possession_changed", 
            current_value=possession_changed,
            expected_value=True
        )
    
    return builder.build()