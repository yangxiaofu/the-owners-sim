"""
Transition Validator

Main validation orchestrator that coordinates all validator components
to ensure state transitions are comprehensive and consistent with NFL rules.
"""

from typing import Any, Dict, Optional, List, Tuple
from dataclasses import dataclass
from .validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)
from .field_validator import FieldValidator
from .possession_validator import PossessionValidator, PossessionChangeReason
from .score_validator import ScoreValidator, ScoreType
from .nfl_rules_validator import NFLRulesValidator


@dataclass
class GameStateTransition:
    """
    Represents a complete game state transition with all relevant data
    This is the main object that gets validated by the TransitionValidator
    """
    
    # Field state changes (required fields)
    current_field_position: int
    new_field_position: int
    current_down: int
    new_down: int
    current_yards_to_go: int
    new_yards_to_go: int
    yards_gained: int
    
    # Possession changes (required fields)
    current_possession_team: Optional[int]
    new_possession_team: Optional[int]
    
    # Score changes (required fields)
    current_score: Tuple[int, int]  # (home, away)
    new_score: Tuple[int, int]      # (home, away)
    
    # Clock and game state (required fields)
    current_quarter: int
    new_quarter: int
    current_time_remaining: int
    new_time_remaining: int
    time_elapsed: int
    
    # Play context (required fields)
    play_type: str
    play_outcome: str
    
    # Optional fields with defaults (must come last)
    possession_changed: bool = False
    possession_change_reason: Optional[PossessionChangeReason] = None
    scoring_occurred: bool = False
    scoring_team: Optional[int] = None
    score_type: Optional[ScoreType] = None
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Initialize computed fields"""
        if self.context is None:
            self.context = {}
        
        # Auto-detect possession change if not explicitly set
        if not self.possession_changed and self.current_possession_team != self.new_possession_team:
            self.possession_changed = True
        
        # Auto-detect scoring if not explicitly set
        if not self.scoring_occurred and self.current_score != self.new_score:
            self.scoring_occurred = True


class TransitionValidator:
    """
    Main validation orchestrator that coordinates all validation components
    to ensure complete state transition validity
    """
    
    def __init__(self):
        """Initialize all validator components"""
        self.field_validator = FieldValidator()
        self.possession_validator = PossessionValidator()  
        self.score_validator = ScoreValidator()
        self.nfl_rules_validator = NFLRulesValidator()
    
    def validate_transition(self, transition: GameStateTransition) -> ValidationResult:
        """
        Perform comprehensive validation of a complete state transition
        
        Args:
            transition: Complete game state transition to validate
            
        Returns:
            ValidationResult with all validation issues across all categories
        """
        builder = ValidationResultBuilder()
        
        # Add metadata about the transition
        builder.add_metadata("transition_type", "complete_state_change")
        builder.add_metadata("play_type", transition.play_type)
        builder.add_metadata("play_outcome", transition.play_outcome)
        
        # 1. Validate field state changes
        field_result = self._validate_field_changes(transition)
        self._merge_result(builder, field_result, "field_validation")
        
        # 2. Validate possession changes (if any)
        possession_result = self._validate_possession_changes(transition)
        self._merge_result(builder, possession_result, "possession_validation")
        
        # 3. Validate scoring changes (if any)
        score_result = self._validate_score_changes(transition)
        self._merge_result(builder, score_result, "score_validation")
        
        # 4. Validate NFL rule compliance  
        rules_result = self._validate_nfl_rules(transition)
        self._merge_result(builder, rules_result, "nfl_rules_validation")
        
        # 5. Cross-validation between different aspects
        cross_result = self._validate_cross_dependencies(transition)
        self._merge_result(builder, cross_result, "cross_validation")
        
        return builder.build()
    
    def _validate_field_changes(self, transition: GameStateTransition) -> ValidationResult:
        """Validate all field-related state changes"""
        builder = ValidationResultBuilder()
        
        # Validate individual field positions
        current_pos_result = self.field_validator.validate_field_position(
            transition.current_field_position, transition.context
        )
        new_pos_result = self.field_validator.validate_field_position(
            transition.new_field_position, transition.context
        )
        
        # Merge position results
        for result in [current_pos_result, new_pos_result]:
            for issue in result.issues:
                builder.issues.append(issue)
                if issue.severity.value == "error":
                    builder._is_valid = False
        
        # Validate field position transition
        field_transition_result = self.field_validator.validate_field_transition(
            transition.current_field_position,
            transition.new_field_position, 
            transition.yards_gained,
            transition.context
        )
        
        for issue in field_transition_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        # Validate down progression
        down_result = self.field_validator.validate_down_progression(
            transition.current_down,
            transition.new_down,
            transition.yards_gained,
            transition.current_yards_to_go,
            transition.context
        )
        
        for issue in down_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        # Validate yards to go
        yards_result = self.field_validator.validate_yards_to_go(
            transition.new_yards_to_go,
            transition.new_field_position,
            transition.context
        )
        
        for issue in yards_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        return builder.build()
    
    def _validate_possession_changes(self, transition: GameStateTransition) -> ValidationResult:
        """Validate possession change logic"""
        if not transition.possession_changed:
            # Validate that possession correctly stayed the same
            return self.possession_validator.validate_no_possession_change(
                transition.current_possession_team,
                transition.new_possession_team,
                transition.play_outcome,
                transition.context
            )
        else:
            # Validate that possession change is legal
            if transition.possession_change_reason is None:
                builder = ValidationResultBuilder()
                builder.add_error(
                    ValidationCategory.POSSESSION_CHANGE,
                    "Possession changed but no reason provided",
                    field_name="possession_change_reason",
                    current_value=None,
                    expected_value="valid PossessionChangeReason",
                    rule_reference="TRANSITION.001"
                )
                return builder.build()
            
            return self.possession_validator.validate_possession_change(
                transition.current_possession_team,
                transition.new_possession_team,
                transition.possession_change_reason,
                transition.current_down,
                transition.current_field_position,
                transition.context
            )
    
    def _validate_score_changes(self, transition: GameStateTransition) -> ValidationResult:
        """Validate scoring state changes"""
        if not transition.scoring_occurred:
            # Verify scores didn't change inappropriately
            if transition.current_score != transition.new_score:
                builder = ValidationResultBuilder()
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Score changed but scoring_occurred flag is False",
                    field_name="scoring_occurred",
                    current_value=False,
                    expected_value=True,
                    rule_reference="TRANSITION.002"
                )
                return builder.build()
            
            return create_success_result()
        else:
            # Validate scoring rules
            if transition.score_type is None or transition.scoring_team is None:
                builder = ValidationResultBuilder()
                if transition.score_type is None:
                    builder.add_error(
                        ValidationCategory.SCORING_RULES,
                        "Scoring occurred but no score type specified",
                        field_name="score_type",
                        current_value=None,
                        rule_reference="TRANSITION.003"
                    )
                if transition.scoring_team is None:
                    builder.add_error(
                        ValidationCategory.SCORING_RULES,
                        "Scoring occurred but no scoring team specified",
                        field_name="scoring_team", 
                        current_value=None,
                        rule_reference="TRANSITION.004"
                    )
                return builder.build()
            
            # Validate the specific score type
            return self.score_validator.validate_score_transition(
                transition.score_type,
                transition.new_field_position,  # Use new position (where scoring occurred)
                transition.scoring_team,
                transition.current_score,
                transition.new_score,
                transition.context
            )
    
    def _validate_nfl_rules(self, transition: GameStateTransition) -> ValidationResult:
        """Validate NFL rule compliance"""
        builder = ValidationResultBuilder()
        
        # Validate clock transition
        clock_result = self.nfl_rules_validator.validate_clock_transition(
            transition.current_time_remaining,
            transition.new_time_remaining,
            transition.current_quarter,
            transition.time_elapsed,
            transition.context
        )
        
        for issue in clock_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        # Validate quarter progression (if changed)
        if transition.current_quarter != transition.new_quarter:
            quarter_result = self.nfl_rules_validator.validate_quarter_progression(
                transition.current_quarter,
                transition.new_quarter,
                transition.current_time_remaining,
                transition.new_time_remaining,
                transition.context
            )
            
            for issue in quarter_result.issues:
                builder.issues.append(issue)
                if issue.severity.value == "error":
                    builder._is_valid = False
        
        # Validate two-minute warning if applicable
        warning_result = self.nfl_rules_validator.validate_two_minute_warning(
            transition.current_quarter,
            transition.current_time_remaining,
            transition.context
        )
        
        for issue in warning_result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
        
        # Validate timeout usage if applicable
        if transition.context and "timeout_used" in transition.context:
            timeout_result = self.nfl_rules_validator.validate_timeout_usage(
                transition.context.get("team_timeouts", {}),
                transition.context.get("timeout_used", False),
                transition.context.get("using_team"),
                transition.current_quarter,
                transition.context
            )
            
            for issue in timeout_result.issues:
                builder.issues.append(issue)
                if issue.severity.value == "error":
                    builder._is_valid = False
        
        return builder.build()
    
    def _validate_cross_dependencies(self, transition: GameStateTransition) -> ValidationResult:
        """
        Validate dependencies between different aspects of the transition
        These are validations that require checking multiple components together
        """
        builder = ValidationResultBuilder()
        
        # 1. Scoring and field position consistency
        if transition.scoring_occurred:
            if transition.score_type == ScoreType.TOUCHDOWN:
                if transition.new_field_position != 100:
                    builder.add_error(
                        ValidationCategory.GAME_STATE,
                        "Touchdown scored but field position is not at goal line",
                        field_name="field_position_score_consistency",
                        current_value=transition.new_field_position,
                        expected_value=100,
                        rule_reference="CROSS.001"
                    )
            elif transition.score_type == ScoreType.SAFETY:
                if transition.new_field_position != 0:
                    builder.add_error(
                        ValidationCategory.GAME_STATE,
                        "Safety scored but field position is not at goal line",
                        field_name="field_position_score_consistency",
                        current_value=transition.new_field_position,
                        expected_value=0,
                        rule_reference="CROSS.002"
                    )
        
        # 2. Possession and scoring consistency
        if transition.scoring_occurred and transition.score_type in [ScoreType.TOUCHDOWN, ScoreType.FIELD_GOAL]:
            # After offensive scoring, possession should change via kickoff
            expected_possession_reason = PossessionChangeReason.TOUCHDOWN if transition.score_type == ScoreType.TOUCHDOWN else PossessionChangeReason.KICKOFF
            
            if not transition.possession_changed:
                builder.add_warning(
                    ValidationCategory.GAME_STATE,
                    f"Scoring occurred but possession didn't change - kickoff expected",
                    field_name="possession_after_score",
                    rule_reference="CROSS.003"
                )
        
        # 3. Fourth down and possession consistency
        if transition.current_down == 4:
            conversion_successful = transition.yards_gained >= transition.current_yards_to_go
            
            if not conversion_successful and not transition.possession_changed:
                builder.add_error(
                    ValidationCategory.GAME_STATE,
                    "Failed 4th down conversion should result in possession change",
                    field_name="fourth_down_possession",
                    current_value=transition.possession_changed,
                    expected_value=True,
                    rule_reference="CROSS.004"
                )
            elif conversion_successful and transition.possession_changed:
                # Exception: if scoring occurred, possession change is expected
                if not transition.scoring_occurred:
                    builder.add_error(
                        ValidationCategory.GAME_STATE,
                        "Successful 4th down conversion should not change possession",
                        field_name="fourth_down_possession",
                        current_value=transition.possession_changed,
                        expected_value=False,
                        rule_reference="CROSS.005"
                    )
        
        # 4. Time and quarter consistency
        if transition.current_quarter != transition.new_quarter:
            # Quarter advanced - validate time reset
            if transition.new_time_remaining != 900:  # 15 minutes
                builder.add_error(
                    ValidationCategory.GAME_STATE,
                    "Quarter advanced but clock not reset to 15:00",
                    field_name="quarter_time_consistency",
                    current_value=transition.new_time_remaining,
                    expected_value=900,
                    rule_reference="CROSS.006"
                )
        
        # 5. Play outcome and field position consistency
        if transition.play_outcome == "touchdown" and transition.new_field_position != 100:
            builder.add_error(
                ValidationCategory.GAME_STATE,
                "Play outcome is touchdown but field position is not goal line",
                field_name="outcome_position_consistency",
                current_value=transition.new_field_position,
                expected_value=100,
                rule_reference="CROSS.007"
            )
        elif transition.play_outcome == "safety" and transition.new_field_position != 0:
            builder.add_error(
                ValidationCategory.GAME_STATE,
                "Play outcome is safety but field position is not goal line",
                field_name="outcome_position_consistency",
                current_value=transition.new_field_position,
                expected_value=0,
                rule_reference="CROSS.008"
            )
        
        return builder.build()
    
    def _merge_result(self, builder: ValidationResultBuilder, result: ValidationResult, 
                      validation_type: str) -> None:
        """Helper method to merge validation results"""
        builder.add_metadata(f"{validation_type}_issues_count", len(result.issues))
        builder.add_metadata(f"{validation_type}_valid", result.is_valid)
        
        for issue in result.issues:
            builder.issues.append(issue)
            if issue.severity.value == "error":
                builder._is_valid = False
    
    def validate_play_result(self, play_result: Any, current_game_state: Any) -> ValidationResult:
        """
        Convenience method to validate a play result against current game state
        
        Args:
            play_result: Play result object with outcome data
            current_game_state: Current game state object
            
        Returns:
            ValidationResult for the play result
        """
        # This would need to be implemented based on your specific play result
        # and game state object structures. This is a placeholder that shows
        # how to convert your objects to a GameStateTransition for validation.
        
        builder = ValidationResultBuilder()
        builder.add_error(
            ValidationCategory.GAME_STATE,
            "validate_play_result not yet implemented - use validate_transition with GameStateTransition",
            rule_reference="IMPL.001"
        )
        return builder.build()


# Factory functions for common transition types
def create_simple_field_transition(current_pos: int, new_pos: int, down: int, 
                                  yards_to_go: int, yards_gained: int) -> GameStateTransition:
    """Create a simple field position transition"""
    new_down = down + 1 if yards_gained < yards_to_go else 1
    new_yards_to_go = max(0, yards_to_go - yards_gained) if yards_gained < yards_to_go else 10
    
    return GameStateTransition(
        current_field_position=current_pos,
        new_field_position=new_pos,
        current_down=down,
        new_down=new_down,
        current_yards_to_go=yards_to_go,
        new_yards_to_go=new_yards_to_go,
        yards_gained=yards_gained,
        current_possession_team=0,
        new_possession_team=0,
        current_score=(0, 0),
        new_score=(0, 0),
        current_quarter=1,
        new_quarter=1,
        current_time_remaining=900,
        new_time_remaining=885,  # 15 seconds elapsed
        time_elapsed=15,
        play_type="run",
        play_outcome="gain"
    )


def create_scoring_transition(score_type: ScoreType, scoring_team: int,
                             field_position: int, current_score: Tuple[int, int]) -> GameStateTransition:
    """Create a scoring transition"""
    points = {
        ScoreType.TOUCHDOWN: 6,
        ScoreType.FIELD_GOAL: 3,
        ScoreType.SAFETY: 2,
        ScoreType.EXTRA_POINT: 1,
        ScoreType.TWO_POINT_CONVERSION: 2
    }
    
    new_score = list(current_score)
    new_score[scoring_team] += points[score_type]
    
    return GameStateTransition(
        current_field_position=field_position,
        new_field_position=field_position,
        current_down=1,
        new_down=1,
        current_yards_to_go=10,
        new_yards_to_go=10,
        yards_gained=0,
        current_possession_team=scoring_team,
        new_possession_team=1 - scoring_team,  # Possession changes after score
        possession_changed=True,
        possession_change_reason=PossessionChangeReason.KICKOFF,
        current_score=current_score,
        new_score=tuple(new_score),
        scoring_occurred=True,
        scoring_team=scoring_team,
        score_type=score_type,
        current_quarter=1,
        new_quarter=1,
        current_time_remaining=900,
        new_time_remaining=900,
        time_elapsed=0,
        play_type="scoring",
        play_outcome=score_type.value
    )


# Convenience validation functions
def quick_validate_field_change(current_pos: int, new_pos: int, yards_gained: int) -> ValidationResult:
    """Quick validation of a field position change"""
    validator = TransitionValidator()
    transition = create_simple_field_transition(current_pos, new_pos, 1, 10, yards_gained)
    return validator._validate_field_changes(transition)


def quick_validate_score(score_type: str, team: int, current_score: Tuple[int, int], 
                        new_score: Tuple[int, int]) -> ValidationResult:
    """Quick scoring validation"""
    try:
        score_enum = ScoreType(score_type.lower())
        validator = TransitionValidator()
        transition = create_scoring_transition(score_enum, team, 100 if score_enum == ScoreType.TOUCHDOWN else 50, current_score)
        transition.new_score = new_score
        return validator._validate_score_changes(transition)
    except ValueError:
        builder = ValidationResultBuilder()
        builder.add_error(
            ValidationCategory.SCORING_RULES,
            f"Invalid score type: {score_type}",
            field_name="score_type",
            current_value=score_type
        )
        return builder.build()