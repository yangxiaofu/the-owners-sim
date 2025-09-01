"""
Score Validator

Validates scoring transitions to ensure they follow NFL scoring rules
for touchdowns, field goals, safeties, and extra points/two-point conversions.
"""

from typing import Any, Dict, Optional, Tuple
from enum import Enum
from .validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)


class ScoreType(Enum):
    """Valid scoring types in NFL"""
    TOUCHDOWN = "touchdown"           # 6 points
    FIELD_GOAL = "field_goal"        # 3 points  
    SAFETY = "safety"                # 2 points
    EXTRA_POINT = "extra_point"      # 1 point (after touchdown)
    TWO_POINT_CONVERSION = "two_point_conversion"  # 2 points (after touchdown)
    DEFENSIVE_TWO_POINT = "defensive_two_point"    # 2 points (rare)


class ScoreValidator:
    """Validates scoring rule compliance according to NFL regulations"""
    
    # NFL Scoring Constants
    TOUCHDOWN_POINTS = 6
    FIELD_GOAL_POINTS = 3
    SAFETY_POINTS = 2
    EXTRA_POINT_POINTS = 1
    TWO_POINT_CONVERSION_POINTS = 2
    DEFENSIVE_TWO_POINT_POINTS = 2
    
    # Field position requirements
    TOUCHDOWN_POSITION = 100    # Must reach end zone
    SAFETY_POSITION = 0         # Must be in own end zone
    
    # Maximum reasonable field goal range (in practice)
    MAX_FIELD_GOAL_RANGE = 70   # Yards from goal line
    
    def validate_touchdown(self, field_position: int, scoring_team: int,
                          previous_score: Tuple[int, int], new_score: Tuple[int, int],
                          context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate touchdown scoring
        
        Args:
            field_position: Field position where touchdown occurred
            scoring_team: Team that scored (0 for home, 1 for away)
            previous_score: (home_score, away_score) before touchdown
            new_score: (home_score, away_score) after touchdown
            context: Additional context (play_type, etc.)
            
        Returns:
            ValidationResult for touchdown validity
        """
        builder = ValidationResultBuilder()
        
        # Validate field position
        if field_position != self.TOUCHDOWN_POSITION:
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                f"Touchdown must occur at {self.TOUCHDOWN_POSITION}-yard line (in end zone)",
                field_name="field_position", 
                current_value=field_position,
                expected_value=self.TOUCHDOWN_POSITION,
                rule_reference="NFL.SCORE.001"
            )
        
        # Validate score change
        expected_score_change = self.TOUCHDOWN_POINTS
        home_diff = new_score[0] - previous_score[0]
        away_diff = new_score[1] - previous_score[1]
        
        if scoring_team == 0:  # Home team scored
            if home_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Home team touchdown should add {expected_score_change} points",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.002"
                )
            if away_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Away team score should not change on home team touchdown",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.003"
                )
        elif scoring_team == 1:  # Away team scored
            if away_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Away team touchdown should add {expected_score_change} points",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.004"
                )
            if home_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Home team score should not change on away team touchdown",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.005"
                )
        else:
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                "Invalid scoring team - must be 0 (home) or 1 (away)",
                field_name="scoring_team",
                current_value=scoring_team,
                expected_value="0 or 1",
                rule_reference="NFL.SCORE.006"
            )
        
        # Validate play context if available
        if context and "play_type" in context:
            play_type = context["play_type"]
            valid_td_plays = ["run", "pass", "fumble_recovery", "interception_return", 
                             "kick_return", "punt_return", "blocked_kick_return"]
            
            if play_type not in valid_td_plays:
                builder.add_warning(
                    ValidationCategory.SCORING_RULES,
                    f"Unusual play type for touchdown: {play_type}",
                    field_name="play_type",
                    current_value=play_type,
                    rule_reference="NFL.SCORE.007"
                )
        
        return builder.build()
    
    def validate_field_goal(self, field_position: int, scoring_team: int,
                           previous_score: Tuple[int, int], new_score: Tuple[int, int],
                           context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate field goal scoring
        
        Args:
            field_position: Field position where field goal was attempted
            scoring_team: Team that scored
            previous_score: Score before field goal  
            new_score: Score after field goal
            context: Additional context (distance, etc.)
            
        Returns:
            ValidationResult for field goal validity
        """
        builder = ValidationResultBuilder()
        
        # Calculate kick distance (field position + 17 yards for end zone + goal post)
        kick_distance = (100 - field_position) + 17
        
        # Validate reasonable field goal range
        if kick_distance > self.MAX_FIELD_GOAL_RANGE:
            builder.add_warning(
                ValidationCategory.SCORING_RULES,
                f"Field goal attempt from {kick_distance} yards is extremely long range",
                field_name="kick_distance",
                current_value=kick_distance,
                rule_reference="NFL.SCORE.008"
            )
        
        # Field goals shouldn't be attempted from very close range
        if kick_distance < 20:
            builder.add_warning(
                ValidationCategory.SCORING_RULES,
                f"Field goal attempt from {kick_distance} yards - touchdown attempt more typical",
                field_name="kick_distance",
                current_value=kick_distance,
                rule_reference="NFL.SCORE.009"
            )
        
        # Validate score change
        expected_score_change = self.FIELD_GOAL_POINTS
        home_diff = new_score[0] - previous_score[0]
        away_diff = new_score[1] - previous_score[1]
        
        if scoring_team == 0:  # Home team scored
            if home_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Home team field goal should add {expected_score_change} points",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.010"
                )
            if away_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Away team score should not change on home team field goal",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.011"
                )
        elif scoring_team == 1:  # Away team scored
            if away_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Away team field goal should add {expected_score_change} points",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.012"
                )
            if home_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Home team score should not change on away team field goal",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.013"
                )
        
        # Validate context
        if context and "down" in context:
            down = context["down"]
            if down != 4:
                builder.add_warning(
                    ValidationCategory.SCORING_RULES,
                    f"Field goal attempt on {down} down is unusual - typically attempted on 4th down",
                    field_name="down",
                    current_value=down,
                    expected_value=4,
                    rule_reference="NFL.SCORE.014"
                )
        
        return builder.build()
    
    def validate_safety(self, field_position: int, scoring_team: int,
                       previous_score: Tuple[int, int], new_score: Tuple[int, int],
                       context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate safety scoring
        
        Args:
            field_position: Field position where safety occurred
            scoring_team: Team that scored (defense)
            previous_score: Score before safety
            new_score: Score after safety
            context: Additional context
            
        Returns:
            ValidationResult for safety validity
        """
        builder = ValidationResultBuilder()
        
        # Validate field position - safety occurs in end zone (position 0)
        if field_position != self.SAFETY_POSITION:
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                f"Safety must occur at {self.SAFETY_POSITION}-yard line (in end zone)",
                field_name="field_position",
                current_value=field_position,
                expected_value=self.SAFETY_POSITION,
                rule_reference="NFL.SCORE.015"
            )
        
        # Validate score change
        expected_score_change = self.SAFETY_POINTS
        home_diff = new_score[0] - previous_score[0]
        away_diff = new_score[1] - previous_score[1]
        
        if scoring_team == 0:  # Home team scored
            if home_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Home team safety should add {expected_score_change} points",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.016"
                )
            if away_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Away team score should not change on home team safety",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.017"
                )
        elif scoring_team == 1:  # Away team scored
            if away_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Away team safety should add {expected_score_change} points",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.018"
                )
            if home_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Home team score should not change on away team safety",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.019"
                )
        
        return builder.build()
    
    def validate_extra_point(self, scoring_team: int, previous_score: Tuple[int, int],
                            new_score: Tuple[int, int], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate extra point scoring (must follow touchdown)
        
        Args:
            scoring_team: Team attempting extra point
            previous_score: Score before extra point (should include touchdown)
            new_score: Score after extra point
            context: Additional context (should include recent touchdown)
            
        Returns:
            ValidationResult for extra point validity
        """
        builder = ValidationResultBuilder()
        
        # Validate score change
        expected_score_change = self.EXTRA_POINT_POINTS
        home_diff = new_score[0] - previous_score[0]
        away_diff = new_score[1] - previous_score[1]
        
        if scoring_team == 0:  # Home team extra point
            if home_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Home team extra point should add {expected_score_change} point",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.020"
                )
            if away_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Away team score should not change on home team extra point",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.021"
                )
        elif scoring_team == 1:  # Away team extra point
            if away_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Away team extra point should add {expected_score_change} point",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.022"
                )
            if home_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Home team score should not change on away team extra point",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.023"
                )
        
        # Validate that extra point follows a touchdown
        if context and "previous_play" in context:
            previous_play = context["previous_play"]
            if previous_play.get("outcome") != "touchdown":
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Extra point attempt must immediately follow a touchdown",
                    field_name="previous_play_outcome",
                    current_value=previous_play.get("outcome"),
                    expected_value="touchdown",
                    rule_reference="NFL.SCORE.024"
                )
        
        return builder.build()
    
    def validate_two_point_conversion(self, scoring_team: int, previous_score: Tuple[int, int],
                                     new_score: Tuple[int, int], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate two-point conversion scoring (must follow touchdown)
        
        Args:
            scoring_team: Team attempting two-point conversion
            previous_score: Score before conversion
            new_score: Score after conversion
            context: Additional context
            
        Returns:
            ValidationResult for two-point conversion validity
        """
        builder = ValidationResultBuilder()
        
        # Validate score change
        expected_score_change = self.TWO_POINT_CONVERSION_POINTS
        home_diff = new_score[0] - previous_score[0]
        away_diff = new_score[1] - previous_score[1]
        
        if scoring_team == 0:  # Home team conversion
            if home_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Home team two-point conversion should add {expected_score_change} points",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.025"
                )
            if away_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Away team score should not change on home team two-point conversion",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.026"
                )
        elif scoring_team == 1:  # Away team conversion
            if away_diff != expected_score_change:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    f"Away team two-point conversion should add {expected_score_change} points",
                    field_name="away_score_change",
                    current_value=away_diff,
                    expected_value=expected_score_change,
                    rule_reference="NFL.SCORE.027"
                )
            if home_diff != 0:
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Home team score should not change on away team two-point conversion",
                    field_name="home_score_change",
                    current_value=home_diff,
                    expected_value=0,
                    rule_reference="NFL.SCORE.028"
                )
        
        # Validate that conversion follows a touchdown
        if context and "previous_play" in context:
            previous_play = context["previous_play"]
            if previous_play.get("outcome") != "touchdown":
                builder.add_error(
                    ValidationCategory.SCORING_RULES,
                    "Two-point conversion attempt must immediately follow a touchdown",
                    field_name="previous_play_outcome",
                    current_value=previous_play.get("outcome"),
                    expected_value="touchdown",
                    rule_reference="NFL.SCORE.029"
                )
        
        return builder.build()
    
    def validate_score_transition(self, score_type: ScoreType, field_position: int,
                                 scoring_team: int, previous_score: Tuple[int, int],
                                 new_score: Tuple[int, int], context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate any scoring transition based on score type
        
        Args:
            score_type: Type of scoring play
            field_position: Position where scoring occurred
            scoring_team: Team that scored
            previous_score: Score before the play
            new_score: Score after the play
            context: Additional context
            
        Returns:
            ValidationResult for the scoring transition
        """
        if score_type == ScoreType.TOUCHDOWN:
            return self.validate_touchdown(field_position, scoring_team, previous_score, new_score, context)
        elif score_type == ScoreType.FIELD_GOAL:
            return self.validate_field_goal(field_position, scoring_team, previous_score, new_score, context)
        elif score_type == ScoreType.SAFETY:
            return self.validate_safety(field_position, scoring_team, previous_score, new_score, context)
        elif score_type == ScoreType.EXTRA_POINT:
            return self.validate_extra_point(scoring_team, previous_score, new_score, context)
        elif score_type == ScoreType.TWO_POINT_CONVERSION:
            return self.validate_two_point_conversion(scoring_team, previous_score, new_score, context)
        else:
            builder = ValidationResultBuilder()
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                f"Unknown score type: {score_type}",
                field_name="score_type",
                current_value=score_type,
                rule_reference="NFL.SCORE.030"
            )
            return builder.build()
    
    def validate_score_bounds(self, score: Tuple[int, int]) -> ValidationResult:
        """
        Validate that scores are within reasonable bounds
        
        Args:
            score: (home_score, away_score) tuple
            
        Returns:
            ValidationResult for score bounds
        """
        builder = ValidationResultBuilder()
        home_score, away_score = score
        
        # Check for negative scores
        if home_score < 0:
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                "Home team score cannot be negative",
                field_name="home_score",
                current_value=home_score,
                expected_value=">= 0",
                rule_reference="NFL.SCORE.031"
            )
        
        if away_score < 0:
            builder.add_error(
                ValidationCategory.SCORING_RULES,
                "Away team score cannot be negative",
                field_name="away_score",
                current_value=away_score,
                expected_value=">= 0",
                rule_reference="NFL.SCORE.032"
            )
        
        # Check for unreasonably high scores (likely indicates error)
        max_reasonable_score = 100  # Very high but possible
        
        if home_score > max_reasonable_score:
            builder.add_warning(
                ValidationCategory.SCORING_RULES,
                f"Home team score ({home_score}) is unusually high - verify correctness",
                field_name="home_score",
                current_value=home_score,
                rule_reference="NFL.SCORE.033"
            )
        
        if away_score > max_reasonable_score:
            builder.add_warning(
                ValidationCategory.SCORING_RULES,
                f"Away team score ({away_score}) is unusually high - verify correctness",
                field_name="away_score",
                current_value=away_score,
                rule_reference="NFL.SCORE.034"
            )
        
        return builder.build()


# Convenience functions
def validate_touchdown_quick(field_position: int, team: int, score_before: Tuple[int, int], 
                            score_after: Tuple[int, int]) -> ValidationResult:
    """Quick touchdown validation"""
    validator = ScoreValidator()
    return validator.validate_touchdown(field_position, team, score_before, score_after)


def validate_field_goal_quick(field_position: int, team: int, score_before: Tuple[int, int],
                             score_after: Tuple[int, int]) -> ValidationResult:
    """Quick field goal validation"""
    validator = ScoreValidator()
    return validator.validate_field_goal(field_position, team, score_before, score_after)


def validate_safety_quick(team: int, score_before: Tuple[int, int], score_after: Tuple[int, int]) -> ValidationResult:
    """Quick safety validation"""
    validator = ScoreValidator()
    return validator.validate_safety(0, team, score_before, score_after)