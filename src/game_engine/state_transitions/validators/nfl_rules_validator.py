"""
NFL Rules Validator

Validates game state transitions against official NFL rules including
clock management, quarter progression, game timing, and special situations.
"""

from typing import Any, Dict, Optional, List
from enum import Enum
from game_engine.state_transitions.validators.validation_result import (
    ValidationResult, ValidationResultBuilder, ValidationCategory,
    create_success_result
)


class GamePeriod(Enum):
    """NFL Game periods"""
    FIRST_QUARTER = 1
    SECOND_QUARTER = 2  
    THIRD_QUARTER = 3
    FOURTH_QUARTER = 4
    OVERTIME = 5


class ClockState(Enum):
    """Clock states in NFL"""
    RUNNING = "running"
    STOPPED = "stopped"
    EXPIRED = "expired"


class NFLRulesValidator:
    """Validates game state transitions against official NFL rules"""
    
    # NFL Game Constants
    QUARTER_LENGTH_SECONDS = 900  # 15 minutes per quarter
    HALFTIME_BREAK_SECONDS = 1800  # 30 minutes (not simulated but tracked)
    OVERTIME_LENGTH_SECONDS = 600   # 10 minutes in regular season
    PLAYOFF_OVERTIME_LENGTH_SECONDS = 900  # 15 minutes in playoffs
    
    # Game timing rules
    MIN_CLOCK_TIME = 0
    MAX_CLOCK_TIME = QUARTER_LENGTH_SECONDS
    
    # Two minute warning
    TWO_MINUTE_WARNING = 120  # 2 minutes in seconds
    
    # Valid quarters
    VALID_QUARTERS = [1, 2, 3, 4, 5]  # 5 = overtime
    
    def validate_clock_transition(self, current_time: int, new_time: int, 
                                 quarter: int, time_elapsed: int,
                                 context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate clock time transition follows NFL timing rules
        
        Args:
            current_time: Current clock time in seconds
            new_time: New clock time after play
            quarter: Current quarter (1-5)
            time_elapsed: Time that should have elapsed during play
            context: Additional context (clock_stopped, etc.)
            
        Returns:
            ValidationResult for clock transition validity
        """
        builder = ValidationResultBuilder()
        
        # Validate basic clock bounds
        if not isinstance(current_time, int) or current_time < self.MIN_CLOCK_TIME:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"Current clock time must be >= {self.MIN_CLOCK_TIME}",
                field_name="current_time",
                current_value=current_time,
                expected_value=f">= {self.MIN_CLOCK_TIME}",
                rule_reference="NFL.CLOCK.001"
            )
        
        if not isinstance(current_time, int) or current_time > self.MAX_CLOCK_TIME:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"Current clock time cannot exceed {self.MAX_CLOCK_TIME}",
                field_name="current_time",
                current_value=current_time,
                expected_value=f"<= {self.MAX_CLOCK_TIME}",
                rule_reference="NFL.CLOCK.002"
            )
        
        # Validate new time bounds
        if not isinstance(new_time, int) or new_time < self.MIN_CLOCK_TIME:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"New clock time must be >= {self.MIN_CLOCK_TIME}",
                field_name="new_time",
                current_value=new_time,
                expected_value=f">= {self.MIN_CLOCK_TIME}",
                rule_reference="NFL.CLOCK.003"
            )
        
        if not isinstance(new_time, int) or new_time > self.MAX_CLOCK_TIME:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"New clock time cannot exceed {self.MAX_CLOCK_TIME}",
                field_name="new_time",
                current_value=new_time,
                expected_value=f"<= {self.MAX_CLOCK_TIME}",
                rule_reference="NFL.CLOCK.004"
            )
        
        # Validate time progression (clock should generally decrease)
        if context and not context.get("clock_stopped", False):
            expected_new_time = current_time - time_elapsed
            
            # Handle quarter boundaries
            if expected_new_time < 0 and quarter < 4:
                # Quarter should advance, clock resets to 15:00
                if new_time != self.MAX_CLOCK_TIME:
                    builder.add_error(
                        ValidationCategory.CLOCK_CONSTRAINTS,
                        f"Clock should reset to {self.MAX_CLOCK_TIME} at start of new quarter",
                        field_name="new_time",
                        current_value=new_time,
                        expected_value=self.MAX_CLOCK_TIME,
                        rule_reference="NFL.CLOCK.005"
                    )
            elif expected_new_time < 0 and quarter == 4:
                # Game should end or go to overtime
                if new_time != 0:
                    builder.add_warning(
                        ValidationCategory.CLOCK_CONSTRAINTS,
                        "Clock expired in 4th quarter - game should end or go to overtime",
                        field_name="new_time",
                        current_value=new_time,
                        expected_value=0,
                        rule_reference="NFL.CLOCK.006"
                    )
            elif expected_new_time >= 0 and new_time != expected_new_time:
                # Normal time progression
                builder.add_error(
                    ValidationCategory.CLOCK_CONSTRAINTS,
                    f"Clock time progression incorrect - expected {expected_new_time}",
                    field_name="new_time",
                    current_value=new_time,
                    expected_value=expected_new_time,
                    rule_reference="NFL.CLOCK.007"
                )
        
        # Validate reasonable time elapsed
        if time_elapsed < 0:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                "Time elapsed cannot be negative",
                field_name="time_elapsed",
                current_value=time_elapsed,
                expected_value=">= 0",
                rule_reference="NFL.CLOCK.008"
            )
        elif time_elapsed > 45:  # More than 45 seconds is unusual
            builder.add_warning(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"Time elapsed ({time_elapsed}s) is unusually long for a single play",
                field_name="time_elapsed",
                current_value=time_elapsed,
                rule_reference="NFL.CLOCK.009"
            )
        
        return builder.build()
    
    def validate_quarter_progression(self, current_quarter: int, new_quarter: int,
                                   current_time: int, new_time: int,
                                   context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate quarter advancement follows NFL rules
        
        Args:
            current_quarter: Current quarter (1-5)
            new_quarter: New quarter after transition
            current_time: Clock time in current quarter
            new_time: Clock time in new quarter
            context: Additional context (halftime, etc.)
            
        Returns:
            ValidationResult for quarter progression validity
        """
        builder = ValidationResultBuilder()
        
        # Validate quarter bounds
        if current_quarter not in self.VALID_QUARTERS:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"Current quarter must be one of {self.VALID_QUARTERS}",
                field_name="current_quarter",
                current_value=current_quarter,
                expected_value=f"one of {self.VALID_QUARTERS}",
                rule_reference="NFL.QUARTER.001"
            )
        
        if new_quarter not in self.VALID_QUARTERS:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"New quarter must be one of {self.VALID_QUARTERS}",
                field_name="new_quarter",
                current_value=new_quarter,
                expected_value=f"one of {self.VALID_QUARTERS}",
                rule_reference="NFL.QUARTER.002"
            )
        
        # Validate quarter progression logic
        if new_quarter == current_quarter:
            # No quarter change - validate time makes sense
            if current_time == 0 and new_time == self.MAX_CLOCK_TIME:
                builder.add_error(
                    ValidationCategory.CLOCK_CONSTRAINTS,
                    "Clock reset without quarter advancement",
                    field_name="quarter_progression",
                    current_value=f"Q{current_quarter} -> Q{new_quarter}",
                    rule_reference="NFL.QUARTER.003"
                )
        elif new_quarter == current_quarter + 1:
            # Valid quarter advancement
            if current_quarter == 2 and new_quarter == 3:
                # Halftime - special validation
                if context and not context.get("halftime_processed", False):
                    builder.add_warning(
                        ValidationCategory.CLOCK_CONSTRAINTS,
                        "Halftime transition should be properly processed",
                        field_name="halftime_processing",
                        rule_reference="NFL.QUARTER.004"
                    )
            
            # Clock should reset to full quarter time
            if new_time != self.MAX_CLOCK_TIME:
                builder.add_error(
                    ValidationCategory.CLOCK_CONSTRAINTS,
                    f"Clock should reset to {self.MAX_CLOCK_TIME} at start of new quarter",
                    field_name="new_time",
                    current_value=new_time,
                    expected_value=self.MAX_CLOCK_TIME,
                    rule_reference="NFL.QUARTER.005"
                )
        elif current_quarter == 4 and new_quarter == 5:
            # Overtime transition - special rules
            if context and context.get("score_tied", True):
                # Overtime clock rules differ from regular quarters
                overtime_time = self.OVERTIME_LENGTH_SECONDS
                if context.get("playoff_game", False):
                    overtime_time = self.PLAYOFF_OVERTIME_LENGTH_SECONDS
                
                if new_time != overtime_time:
                    builder.add_warning(
                        ValidationCategory.CLOCK_CONSTRAINTS,
                        f"Overtime should start with {overtime_time} seconds",
                        field_name="new_time",
                        current_value=new_time,
                        expected_value=overtime_time,
                        rule_reference="NFL.QUARTER.006"
                    )
            else:
                builder.add_error(
                    ValidationCategory.CLOCK_CONSTRAINTS,
                    "Overtime can only occur when game is tied",
                    field_name="overtime_conditions",
                    rule_reference="NFL.QUARTER.007"
                )
        else:
            builder.add_error(
                ValidationCategory.CLOCK_CONSTRAINTS,
                f"Invalid quarter progression: Q{current_quarter} -> Q{new_quarter}",
                field_name="quarter_progression",
                current_value=f"Q{current_quarter} -> Q{new_quarter}",
                rule_reference="NFL.QUARTER.008"
            )
        
        return builder.build()
    
    def validate_game_end_conditions(self, quarter: int, time_remaining: int,
                                   score: tuple, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate conditions for game ending
        
        Args:
            quarter: Current quarter
            time_remaining: Time left in current period
            score: (home_score, away_score)
            context: Additional context
            
        Returns:
            ValidationResult for game end validity
        """
        builder = ValidationResultBuilder()
        
        home_score, away_score = score
        is_tied = home_score == away_score
        
        # Regular time game end
        if quarter == 4 and time_remaining == 0:
            if is_tied:
                builder.add_info(
                    ValidationCategory.NFL_RULES,
                    "Game tied at end of regulation - overtime required",
                    rule_reference="NFL.END.001"
                )
            else:
                builder.add_info(
                    ValidationCategory.NFL_RULES,
                    "Game ends - regulation time complete with winner determined",
                    rule_reference="NFL.END.002"
                )
        
        # Overtime game end
        elif quarter == 5:
            if time_remaining == 0:
                if is_tied:
                    if context and context.get("playoff_game", False):
                        builder.add_warning(
                            ValidationCategory.NFL_RULES,
                            "Playoff overtime tied - additional overtime required",
                            rule_reference="NFL.END.003"
                        )
                    else:
                        builder.add_info(
                            ValidationCategory.NFL_RULES,
                            "Regular season overtime ends in tie",
                            rule_reference="NFL.END.004"
                        )
                else:
                    builder.add_info(
                        ValidationCategory.NFL_RULES,
                        "Overtime ends with winner determined",
                        rule_reference="NFL.END.005"
                    )
            elif not is_tied and context and context.get("sudden_death", True):
                builder.add_info(
                    ValidationCategory.NFL_RULES,
                    "Overtime can end early if team scores (sudden death rules)",
                    rule_reference="NFL.END.006"
                )
        
        return builder.build()
    
    def validate_two_minute_warning(self, quarter: int, time_remaining: int, 
                                  context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate two-minute warning occurrence
        
        Args:
            quarter: Current quarter
            time_remaining: Time remaining in quarter
            context: Additional context (warning_occurred, etc.)
            
        Returns:
            ValidationResult for two-minute warning validity
        """
        builder = ValidationResultBuilder()
        
        # Two-minute warning only occurs in 2nd and 4th quarters
        if quarter in [2, 4]:
            if time_remaining <= self.TWO_MINUTE_WARNING and time_remaining > 0:
                if context and context.get("two_minute_warning_occurred", False):
                    builder.add_info(
                        ValidationCategory.NFL_RULES,
                        f"Two-minute warning should occur in Q{quarter}",
                        rule_reference="NFL.WARNING.001"
                    )
                else:
                    builder.add_warning(
                        ValidationCategory.NFL_RULES,
                        f"Two-minute warning has not been processed in Q{quarter}",
                        field_name="two_minute_warning",
                        rule_reference="NFL.WARNING.002"
                    )
        elif quarter in [1, 3, 5]:
            if context and context.get("two_minute_warning_occurred", False):
                builder.add_error(
                    ValidationCategory.NFL_RULES,
                    f"Two-minute warning should not occur in Q{quarter}",
                    field_name="two_minute_warning",
                    current_value=True,
                    expected_value=False,
                    rule_reference="NFL.WARNING.003"
                )
        
        return builder.build()
    
    def validate_timeout_usage(self, team_timeouts: Dict[int, int], timeout_used: bool,
                              using_team: Optional[int], quarter: int,
                              context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Validate timeout usage follows NFL rules
        
        Args:
            team_timeouts: Dictionary of team_id -> remaining timeouts
            timeout_used: Whether a timeout was used this play
            using_team: Team that used timeout (if any)
            quarter: Current quarter
            context: Additional context
            
        Returns:
            ValidationResult for timeout validity
        """
        builder = ValidationResultBuilder()
        
        if timeout_used and using_team is not None:
            if using_team not in team_timeouts:
                builder.add_error(
                    ValidationCategory.NFL_RULES,
                    f"Unknown team {using_team} attempted to use timeout",
                    field_name="using_team",
                    current_value=using_team,
                    rule_reference="NFL.TIMEOUT.001"
                )
            elif team_timeouts[using_team] <= 0:
                builder.add_error(
                    ValidationCategory.NFL_RULES,
                    f"Team {using_team} has no timeouts remaining",
                    field_name="team_timeouts",
                    current_value=team_timeouts[using_team],
                    expected_value="> 0",
                    rule_reference="NFL.TIMEOUT.002"
                )
            elif team_timeouts[using_team] > 3:
                builder.add_error(
                    ValidationCategory.NFL_RULES,
                    f"Team {using_team} cannot have more than 3 timeouts",
                    field_name="team_timeouts",
                    current_value=team_timeouts[using_team],
                    expected_value="<= 3",
                    rule_reference="NFL.TIMEOUT.003"
                )
        
        # Validate timeout reset at halftime
        if quarter == 3 and context and context.get("start_of_quarter", False):
            for team_id, timeouts in team_timeouts.items():
                if timeouts != 3:
                    builder.add_warning(
                        ValidationCategory.NFL_RULES,
                        f"Team {team_id} should have 3 timeouts at start of second half",
                        field_name=f"team_{team_id}_timeouts",
                        current_value=timeouts,
                        expected_value=3,
                        rule_reference="NFL.TIMEOUT.004"
                    )
        
        return builder.build()
    
    def validate_complete_game_state(self, quarter: int, time_remaining: int,
                                   score: tuple, field_position: int, down: int,
                                   team_timeouts: Dict[int, int],
                                   context: Optional[Dict[str, Any]] = None) -> ValidationResult:
        """
        Comprehensive validation of complete game state against NFL rules
        
        Args:
            quarter: Current quarter (1-5)
            time_remaining: Seconds remaining in quarter
            score: (home_score, away_score) tuple
            field_position: Current field position
            down: Current down
            team_timeouts: Timeout count by team
            context: Additional context
            
        Returns:
            ValidationResult for complete game state validity
        """
        builder = ValidationResultBuilder()
        
        # Individual validations
        clock_result = self.validate_clock_transition(
            time_remaining, time_remaining, quarter, 0, context
        )
        
        quarter_result = self.validate_quarter_progression(
            quarter, quarter, time_remaining, time_remaining, context
        )
        
        end_result = self.validate_game_end_conditions(
            quarter, time_remaining, score, context
        )
        
        warning_result = self.validate_two_minute_warning(
            quarter, time_remaining, context
        )
        
        timeout_result = self.validate_timeout_usage(
            team_timeouts, False, None, quarter, context
        )
        
        # Merge all results
        all_results = [clock_result, quarter_result, end_result, warning_result, timeout_result]
        
        for result in all_results:
            for issue in result.issues:
                builder.issues.append(issue)
                if issue.severity.value == "error":
                    builder._is_valid = False
        
        # Additional cross-validations
        if quarter > 4 and score[0] == score[1]:
            # Overtime with tied score
            if context and context.get("playoff_game", False):
                builder.add_info(
                    ValidationCategory.NFL_RULES,
                    "Playoff overtime - game must continue until winner determined",
                    rule_reference="NFL.RULES.001"
                )
        
        # Validate field position and down are reasonable for current game state
        if down > 4:
            builder.add_error(
                ValidationCategory.NFL_RULES,
                "Down cannot exceed 4 in NFL",
                field_name="down",
                current_value=down,
                expected_value="1-4",
                rule_reference="NFL.RULES.002"
            )
        
        return builder.build()


# Convenience functions for common validations
def validate_quarter_time(quarter: int, time_remaining: int) -> ValidationResult:
    """Quick quarter and time validation"""
    validator = NFLRulesValidator()
    builder = ValidationResultBuilder()
    
    if quarter not in validator.VALID_QUARTERS:
        builder.add_error(
            ValidationCategory.CLOCK_CONSTRAINTS,
            f"Quarter must be one of {validator.VALID_QUARTERS}",
            field_name="quarter",
            current_value=quarter
        )
    
    if time_remaining < 0 or time_remaining > validator.MAX_CLOCK_TIME:
        builder.add_error(
            ValidationCategory.CLOCK_CONSTRAINTS,
            f"Time remaining must be between 0 and {validator.MAX_CLOCK_TIME}",
            field_name="time_remaining",
            current_value=time_remaining
        )
    
    return builder.build()


def validate_game_end(quarter: int, time_remaining: int, home_score: int, away_score: int) -> ValidationResult:
    """Quick game end validation"""
    validator = NFLRulesValidator()
    return validator.validate_game_end_conditions(quarter, time_remaining, (home_score, away_score))