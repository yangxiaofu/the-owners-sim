"""
Score Calculator - Pure Scoring Calculations

This module contains pure functions to calculate scoring changes based on 
play results. Handles touchdowns, field goals, safeties, and extra points.

Based on the game_state.py scoring logic (lines 40-48).
"""

from typing import Optional
from game_engine.plays.data_structures import PlayResult
# Import the proper ScoreTransition from data_structures
from game_engine.state_transitions.data_structures import ScoreTransition, ScoreType, ConversionType
# Import new team system components
from game_engine.teams import TeamID, TeamMapper, TeamRegistry, TeamContext


class ScoreCalculator:
    """
    Pure calculator for scoring changes with integrated team system.
    
    All methods calculate what scoring changes should occur based on
    play results and current game state, without actually changing anything.
    
    Now integrates with the team system to provide type-safe, consistent
    team identification that fixes the scoreboard bug.
    """
    
    def __init__(self, team_mapper: Optional[TeamMapper] = None):
        """
        Initialize score calculator with team system integration
        
        Args:
            team_mapper: TeamMapper for consistent team resolution.
                        If None, will attempt to create one from game state.
        """
        self.team_mapper = team_mapper
    
    def calculate_score_changes(self, play_result: PlayResult, game_state) -> ScoreTransition:
        """
        Calculate scoring changes based on play result.
        
        This replicates the logic from game_state.py update_after_play method
        (lines 40-48) but as pure calculation functions.
        
        Now uses the team system for consistent, type-safe team resolution
        that fixes the scoreboard bug.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state with possession and score information
            
        Returns:
            ScoreTransition with calculated scoring changes
        """
        # Check if this play resulted in a score
        if not play_result.is_score:
            return ScoreTransition(score_occurred=False)  # No scoring changes
        
        # CRITICAL FIX: Use team system for consistent team resolution
        raw_possession_id = game_state.field.possession_team_id
        current_possession_team = self._resolve_team_from_possession(raw_possession_id, game_state)
        current_field_position = game_state.field.field_position
        
        # Handle different types of scores
        if play_result.outcome == "touchdown":
            return self._calculate_touchdown_score(
                current_possession_team, play_result, current_field_position, game_state
            )
        
        elif play_result.outcome == "field_goal":
            return self._calculate_field_goal_score(
                current_possession_team, play_result, current_field_position, game_state
            )
        
        elif play_result.outcome == "safety":
            return self._calculate_safety_score(
                current_possession_team, play_result, game_state
            )
        
        elif play_result.outcome == "extra_point":
            return self._calculate_extra_point_score(
                current_possession_team, play_result, game_state
            )
        
        elif play_result.outcome == "two_point_conversion":
            return self._calculate_two_point_conversion_score(
                current_possession_team, play_result, game_state
            )
        
        # Handle direct score_points from PlayResult if available
        if play_result.score_points > 0:
            return self._calculate_generic_score(
                current_possession_team, play_result, current_field_position
            )
        
        # No recognizable scoring play
        return ScoreTransition(score_occurred=False)
    
    def _calculate_touchdown_score(self, scoring_team: TeamID, play_result: PlayResult,
                                  field_position: int, game_state=None) -> ScoreTransition:
        """
        Calculate scoring changes for a touchdown.
        
        Touchdowns are worth 6 points and require an extra point attempt.
        Now uses type-safe TeamID for consistent team identification.
        """
        points = 6
        
        return ScoreTransition(
            score_occurred=True,
            score_type=ScoreType.TOUCHDOWN,
            points_scored=points,
            scoring_team=scoring_team,  # CRITICAL FIX: Pass TeamID directly
            touchdown_scored=True,
            touchdown_type=play_result.play_type,
            touchdown_distance=play_result.yards_gained,
            conversion_attempt=True,  # TD requires conversion attempt
            new_home_score=points if scoring_team == TeamID.HOME else 0,
            new_away_score=points if scoring_team == TeamID.AWAY else 0
        )
    
    def _calculate_field_goal_score(self, scoring_team: TeamID, play_result: PlayResult,
                                   field_position: int, game_state=None) -> ScoreTransition:
        """
        Calculate scoring changes for a field goal.
        
        Field goals are worth 3 points.
        Now uses type-safe TeamID for consistent team identification.
        """
        points = 3
        
        # Calculate distance for description
        distance = 100 - field_position + 17  # Add end zone and holder distance
        
        return ScoreTransition(
            score_occurred=True,
            score_type=ScoreType.FIELD_GOAL,
            points_scored=points,
            scoring_team=scoring_team,  # CRITICAL FIX: Pass TeamID directly
            field_goal_scored=True,
            field_goal_distance=distance,
            new_home_score=points if scoring_team == TeamID.HOME else 0,
            new_away_score=points if scoring_team == TeamID.AWAY else 0
        )
    
    def _calculate_safety_score(self, possession_team: TeamID, play_result: PlayResult,
                               game_state) -> ScoreTransition:
        """
        Calculate scoring changes for a safety.
        
        Safeties are worth 2 points and go to the team that DIDN'T have possession.
        Now uses type-safe TeamID for consistent team identification.
        """
        points = 2
        
        # Safety goes to the other team (defense)
        scoring_team = self._get_opposite_team(possession_team)
        
        return ScoreTransition(
            score_occurred=True,
            score_type=ScoreType.SAFETY,
            points_scored=points,
            scoring_team=scoring_team,  # CRITICAL FIX: Pass TeamID directly
            new_home_score=points if scoring_team == TeamID.HOME else 0,
            new_away_score=points if scoring_team == TeamID.AWAY else 0,
            safety_scored=True,
            requires_safety_kick=True
        )
    
    def _calculate_extra_point_score(self, scoring_team: TeamID, 
                                    play_result: PlayResult, game_state=None) -> ScoreTransition:
        """
        Calculate scoring changes for an extra point attempt.
        
        Extra points are worth 1 point if successful.
        Now uses type-safe TeamID for consistent team identification.
        """
        if play_result.outcome == "field_goal":  # Successful extra point
            points = 1
        else:
            points = 0
        
        return ScoreTransition(
            score_occurred=points > 0,
            score_type=ScoreType.EXTRA_POINT,
            points_scored=points,
            scoring_team=scoring_team if points > 0 else None,  # CRITICAL FIX: Pass TeamID directly
            new_home_score=points if scoring_team == TeamID.HOME and points > 0 else 0,
            new_away_score=points if scoring_team == TeamID.AWAY and points > 0 else 0,
            conversion_attempt=True,
            conversion_successful=points > 0,
            conversion_points=points,
            conversion_type=ConversionType.EXTRA_POINT_KICK
        )
    
    def _calculate_two_point_conversion_score(self, scoring_team: TeamID,
                                             play_result: PlayResult, game_state=None) -> ScoreTransition:
        """
        Calculate scoring changes for a two-point conversion attempt.
        
        Two-point conversions are worth 2 points if successful.
        Now uses type-safe TeamID for consistent team identification.
        """
        if play_result.outcome in ["gain", "touchdown"]:  # Successful conversion
            points = 2
        else:
            points = 0
        
        return ScoreTransition(
            score_occurred=points > 0,
            score_type=ScoreType.TWO_POINT_CONVERSION,
            points_scored=points,
            scoring_team=scoring_team if points > 0 else None,  # CRITICAL FIX: Pass TeamID directly
            new_home_score=points if scoring_team == TeamID.HOME and points > 0 else 0,
            new_away_score=points if scoring_team == TeamID.AWAY and points > 0 else 0,
            conversion_attempt=True,
            conversion_successful=points > 0,
            conversion_points=points,
            conversion_type=ConversionType.TWO_POINT_ATTEMPT
        )
    
    def _calculate_generic_score(self, scoring_team: TeamID, play_result: PlayResult,
                                field_position: int) -> ScoreTransition:
        """
        Calculate scoring changes from PlayResult.score_points field.
        
        This handles cases where the score is determined by the PlayResult.
        Now uses type-safe TeamID for consistent team identification.
        """
        points = play_result.score_points
        
        # Try to map outcome to ScoreType, fallback to generic
        score_type = None
        try:
            score_type = ScoreType(play_result.outcome)
        except ValueError:
            # If outcome doesn't match ScoreType enum, use a reasonable default
            if points == 6:
                score_type = ScoreType.TOUCHDOWN
            elif points == 3:
                score_type = ScoreType.FIELD_GOAL
            elif points == 2:
                score_type = ScoreType.SAFETY
            elif points == 1:
                score_type = ScoreType.EXTRA_POINT
        
        return ScoreTransition(
            score_occurred=points > 0,
            score_type=score_type,
            points_scored=points,
            scoring_team=scoring_team if points > 0 else None,  # CRITICAL FIX: Pass TeamID directly
            new_home_score=points if scoring_team == TeamID.HOME else 0,
            new_away_score=points if scoring_team == TeamID.AWAY else 0
        )
    
    def _resolve_team_from_possession(self, possession_id: any, game_state=None) -> TeamID:
        """
        Resolve possession ID to standardized TeamID using team system.
        
        This is the critical method that fixes the scoreboard bug by providing
        consistent team resolution through the team mapper.
        """
        if self.team_mapper:
            return self.team_mapper.map_possession_to_team(possession_id)
        
        # Fallback: create temporary team system components from game state
        if game_state and hasattr(game_state, 'scoreboard'):
            # Extract team data from game state
            home_data = {"name": "Home Team", "abbreviation": "HOME"}
            away_data = {"name": "Away Team", "abbreviation": "AWAY"}
            
            context = TeamContext(home_data, away_data)
            registry = TeamRegistry(context)
            
            return registry.resolve_team_from_possession(possession_id)
        
        # Final fallback: use TeamID's built-in conversion
        try:
            return TeamID.from_any(possession_id)
        except (ValueError, TypeError):
            # Ultimate fallback for unknown possession IDs
            return TeamID.HOME
    
    def _get_opposite_team(self, team_id: TeamID) -> TeamID:
        """
        Get the opposite team using type-safe TeamID logic.
        
        Args:
            team_id: The current team
            
        Returns:
            TeamID: The opposite team (HOME <-> AWAY)
        """
        if team_id == TeamID.HOME:
            return TeamID.AWAY
        elif team_id == TeamID.AWAY:
            return TeamID.HOME
        else:
            # For NEUTRAL, default to HOME (shouldn't happen in normal scoring)
            return TeamID.HOME
    
    def calculate_final_score_difference(self, home_score: int, away_score: int) -> int:
        """
        Calculate the final score difference (positive means home team winning).
        
        Args:
            home_score: Home team's total score
            away_score: Away team's total score
            
        Returns:
            Score difference (positive = home winning, negative = away winning)
        """
        return home_score - away_score
    
    def is_game_winning_score(self, score_transition: ScoreTransition, 
                            current_home_score: int, current_away_score: int,
                            time_remaining: int) -> bool:
        """
        Check if this score would be a game-winning or game-tying score.
        
        Args:
            score_transition: The calculated score transition
            current_home_score: Current home team score
            current_away_score: Current away team score
            time_remaining: Time remaining in game (seconds)
            
        Returns:
            True if this could be a game-deciding score
        """
        if time_remaining <= 120:  # Last 2 minutes
            new_home_score = current_home_score + score_transition.home_team_points
            new_away_score = current_away_score + score_transition.away_team_points
            
            # Check if score changes the lead or ties the game
            old_difference = current_home_score - current_away_score
            new_difference = new_home_score - new_away_score
            
            return (old_difference * new_difference <= 0 or  # Lead change
                   abs(new_difference) <= 7)  # Within one score
        
        return False