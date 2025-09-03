"""
Team Validation Framework - Comprehensive Team Operation Validation

The TeamValidator provides comprehensive validation for all team-related operations,
ensuring business rule compliance and preventing invalid game states.

This component validates:
- Possession assignments and transitions
- Scoring assignments and point values
- Team operation authorization
- Business rule compliance
- Data consistency checks

Key features:
- Comprehensive validation result reporting
- Context-aware validation rules
- Warning and error classification
- Extensible validation framework
- Performance-optimized validation

Usage:
    from game_engine.teams.team_validator import TeamValidator, ValidationResult
    from game_engine.teams.team_registry import TeamRegistry
    
    validator = TeamValidator(registry)
    
    # Validate possession assignment
    result = validator.validate_possession_assignment(TeamID.HOME, context)
    if not result.is_valid:
        print(f"Validation failed: {result.errors}")
    
    # Validate scoring assignment
    result = validator.validate_scoring_assignment(TeamID.AWAY, 6, context)
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from .team_types import TeamID, TeamInfo
from .team_registry import TeamRegistry


@dataclass
class ValidationResult:
    """Result of team validation with detailed error and warning reporting"""
    
    is_valid: bool
    errors: List[str]
    warnings: List[str] = field(default_factory=list)
    context_info: Dict[str, Any] = field(default_factory=dict)
    
    def add_error(self, message: str):
        """Add an error message and mark result as invalid"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add a warning message (doesn't affect validity)"""
        self.warnings.append(message)
    
    def add_context(self, key: str, value: Any):
        """Add context information for debugging"""
        self.context_info[key] = value
    
    def merge(self, other: 'ValidationResult'):
        """Merge another validation result into this one"""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        self.context_info.update(other.context_info)
        self.is_valid = self.is_valid and other.is_valid
    
    def has_warnings(self) -> bool:
        """Check if result has any warnings"""
        return len(self.warnings) > 0


class TeamValidator:
    """Comprehensive team operation validation with business rule enforcement"""
    
    def __init__(self, registry: TeamRegistry):
        """
        Initialize team validator with registry
        
        Args:
            registry: TeamRegistry instance for team operations
        """
        self.registry = registry
        
        # Validation statistics
        self._validation_count = 0
        self._error_count = 0
        self._warning_count = 0
    
    def validate_possession_assignment(self, team_id: TeamID, context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate possession assignments
        
        Args:
            team_id: The team being assigned possession
            context: Optional context information for validation
            
        Returns:
            ValidationResult: Detailed validation result
        """
        self._validation_count += 1
        context = context or {}
        
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_context('validation_type', 'possession_assignment')
        result.add_context('team_id', team_id)
        
        # Check team validity for possession
        if not self.registry.validate_team_operation(team_id, "possess", context):
            result.add_error(f"Team {team_id} cannot have possession in current context")
        
        # Check team info exists (except for NEUTRAL in special cases)
        team_info = self.registry.get_team_info(team_id)
        if team_info is None and team_id != TeamID.NEUTRAL:
            result.add_error(f"No team information found for {team_id}")
        elif team_info is None and team_id == TeamID.NEUTRAL:
            # NEUTRAL possession is allowed in kickoffs, etc.
            result.add_warning("Neutral team possession (allowed for kickoffs/special situations)")
        
        # Check possession transition validity
        previous_team = context.get('previous_possession_team')
        if previous_team is not None:
            transition_result = self.validate_team_transition(previous_team, team_id, context.get('reason', 'unknown'))
            result.merge(transition_result)
        
        # Update statistics
        if not result.is_valid:
            self._error_count += 1
        if result.has_warnings():
            self._warning_count += 1
        
        return result
    
    def validate_scoring_assignment(self, scoring_team: TeamID, points: int, context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate scoring assignments
        
        Args:
            scoring_team: The team being assigned points
            points: Number of points being awarded
            context: Optional context information for validation
            
        Returns:
            ValidationResult: Detailed validation result
        """
        self._validation_count += 1
        context = context or {}
        
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_context('validation_type', 'scoring_assignment')
        result.add_context('scoring_team', scoring_team)
        result.add_context('points', points)
        
        # Check scoring team validity
        if not self.registry.validate_team_operation(scoring_team, "score", context):
            result.add_error(f"Team {scoring_team} cannot score")
        
        # Check points validity
        if points <= 0:
            result.add_error(f"Invalid points value: {points} (must be positive)")
        elif points > 8:  # Maximum realistic NFL score in one play (safety + touchdown)
            result.add_warning(f"Unusually high score: {points} points in one play")
        
        # Validate specific point values for NFL rules
        valid_nfl_scores = {1, 2, 3, 6, 7, 8}  # Safety, FG, TD, conversion combinations
        if points not in valid_nfl_scores:
            result.add_warning(f"Unusual NFL score: {points} points")
        
        # Check scoreboard mapping exists
        try:
            scoreboard_field = self.registry.resolve_scoreboard_target(scoring_team)
            result.add_context('scoreboard_field', scoreboard_field)
        except ValueError as e:
            result.add_error(f"Cannot map scoring team to scoreboard: {e}")
        
        # Validate possession context if provided
        possession_id = context.get('possession_id')
        if possession_id is not None:
            try:
                possessing_team = self.registry.resolve_team_from_possession(possession_id)
                if possessing_team != scoring_team:
                    # This could be valid (defensive scores, etc.)
                    result.add_warning(f"Scoring team {scoring_team} differs from possessing team {possessing_team}")
            except Exception as e:
                result.add_error(f"Could not resolve possessing team for scoring validation: {e}")
        
        # Update statistics
        if not result.is_valid:
            self._error_count += 1
        if result.has_warnings():
            self._warning_count += 1
        
        return result
    
    def validate_team_transition(self, from_team: TeamID, to_team: TeamID, reason: str, context: Dict[str, Any] = None) -> ValidationResult:
        """
        Validate team transitions (possession changes, etc.)
        
        Args:
            from_team: Team losing possession/control
            to_team: Team gaining possession/control  
            reason: Reason for transition
            context: Optional context information
            
        Returns:
            ValidationResult: Detailed validation result
        """
        self._validation_count += 1
        context = context or {}
        
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_context('validation_type', 'team_transition')
        result.add_context('from_team', from_team)
        result.add_context('to_team', to_team)
        result.add_context('reason', reason)
        
        # Check both teams are valid
        for team_id, role in [(from_team, 'from'), (to_team, 'to')]:
            if not self._is_valid_team(team_id):
                result.add_error(f"Invalid {role} team: {team_id}")
        
        # Check same-team transitions
        if from_team == to_team and reason not in {'continuation', 'timeout', 'penalty_replay'}:
            result.add_warning(f"Same-team transition: {from_team} -> {to_team} (reason: {reason})")
        
        # Validate transition reasons
        valid_reasons = {
            'turnover', 'punt', 'kickoff', 'fumble', 'interception',
            'downs', 'touchdown', 'field_goal', 'safety',
            'continuation', 'timeout', 'penalty_replay', 'end_of_half'
        }
        if reason not in valid_reasons:
            result.add_warning(f"Unusual transition reason: '{reason}'")
        
        # Check transition logic consistency
        if reason == 'turnover' and from_team == to_team:
            result.add_error("Turnover cannot result in same-team possession")
        
        if reason == 'touchdown' and to_team not in {TeamID.HOME, TeamID.AWAY}:
            result.add_error(f"Touchdown transition to invalid team: {to_team}")
        
        # Update statistics
        if not result.is_valid:
            self._error_count += 1
        if result.has_warnings():
            self._warning_count += 1
        
        return result
    
    def validate_complete_operation(self, operation_type: str, data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete team operation (comprehensive validation)
        
        Args:
            operation_type: Type of operation ('score', 'possession_change', etc.)
            data: Complete operation data
            
        Returns:
            ValidationResult: Comprehensive validation result
        """
        self._validation_count += 1
        
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_context('validation_type', 'complete_operation')
        result.add_context('operation_type', operation_type)
        
        if operation_type == 'score':
            # Validate scoring operation
            scoring_team = data.get('scoring_team')
            points = data.get('points')
            
            if scoring_team is None:
                result.add_error("Missing scoring_team in score operation")
            elif points is None:
                result.add_error("Missing points in score operation")
            else:
                score_result = self.validate_scoring_assignment(scoring_team, points, data)
                result.merge(score_result)
                
        elif operation_type == 'possession_change':
            # Validate possession change operation
            from_team = data.get('from_team')
            to_team = data.get('to_team')
            reason = data.get('reason', 'unknown')
            
            if from_team is None or to_team is None:
                result.add_error("Missing team information in possession change operation")
            else:
                transition_result = self.validate_team_transition(from_team, to_team, reason, data)
                result.merge(transition_result)
                
                possession_result = self.validate_possession_assignment(to_team, data)
                result.merge(possession_result)
        else:
            result.add_warning(f"Unknown operation type: '{operation_type}'")
        
        # Update statistics
        if not result.is_valid:
            self._error_count += 1
        if result.has_warnings():
            self._warning_count += 1
        
        return result
    
    def _is_valid_team(self, team_id: TeamID) -> bool:
        """
        Check if team ID is valid
        
        Args:
            team_id: The team identifier to check
            
        Returns:
            bool: True if team ID is valid
        """
        return isinstance(team_id, TeamID) and team_id in {TeamID.HOME, TeamID.AWAY, TeamID.NEUTRAL}
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics
        
        Returns:
            Dict: Validation statistics and metrics
        """
        return {
            'total_validations': self._validation_count,
            'total_errors': self._error_count,
            'total_warnings': self._warning_count,
            'error_rate': (self._error_count / max(1, self._validation_count)) * 100,
            'warning_rate': (self._warning_count / max(1, self._validation_count)) * 100
        }
    
    def reset_stats(self):
        """Reset validation statistics"""
        self._validation_count = 0
        self._error_count = 0
        self._warning_count = 0
    
    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get comprehensive debug information
        
        Returns:
            Dict: Debug information including statistics and registry info
        """
        return {
            'validation_stats': self.get_validation_stats(),
            'registry_debug': self.registry.get_debug_info()
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        stats = self.get_validation_stats()
        return f"TeamValidator(validations={stats['total_validations']}, errors={stats['total_errors']})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return f"TeamValidator(registry={self.registry!r}, validations={self._validation_count})"