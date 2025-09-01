"""
Score Calculator - Pure Scoring Calculations

This module contains pure functions to calculate scoring changes based on 
play results. Handles touchdowns, field goals, safeties, and extra points.

Based on the game_state.py scoring logic (lines 40-48).
"""

from typing import Optional
from dataclasses import dataclass
from ...plays.data_structures import PlayResult


@dataclass(frozen=True)
class ScoreTransition:
    """
    Immutable representation of scoring changes.
    
    Contains all score-related changes that should be applied after a play.
    """
    points_scored: int = 0                        # Points to add to scoring team
    scoring_team_id: Optional[int] = None         # Which team scored
    score_type: Optional[str] = None              # "touchdown", "field_goal", "safety", "extra_point"
    requires_extra_point: bool = False            # Whether TD requires extra point attempt
    
    # Score breakdown for detailed tracking
    home_team_points: int = 0                     # Points to add to home team
    away_team_points: int = 0                     # Points to add to away team
    
    # Context information
    play_description: Optional[str] = None        # Description of scoring play
    field_position: Optional[int] = None          # Where the score occurred


class ScoreCalculator:
    """
    Pure calculator for scoring changes.
    
    All methods calculate what scoring changes should occur based on
    play results and current game state, without actually changing anything.
    """
    
    def calculate_score_changes(self, play_result: PlayResult, game_state) -> ScoreTransition:
        """
        Calculate scoring changes based on play result.
        
        This replicates the logic from game_state.py update_after_play method
        (lines 40-48) but as pure calculation functions.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state with possession and score information
            
        Returns:
            ScoreTransition with calculated scoring changes
        """
        # Check if this play resulted in a score
        if not play_result.is_score:
            return ScoreTransition()  # No scoring changes
        
        current_possession = game_state.field.possession_team_id
        current_field_position = game_state.field.field_position
        
        # Handle different types of scores
        if play_result.outcome == "touchdown":
            return self._calculate_touchdown_score(
                current_possession, play_result, current_field_position
            )
        
        elif play_result.outcome == "field_goal":
            return self._calculate_field_goal_score(
                current_possession, play_result, current_field_position
            )
        
        elif play_result.outcome == "safety":
            return self._calculate_safety_score(
                current_possession, play_result, game_state
            )
        
        elif play_result.outcome == "extra_point":
            return self._calculate_extra_point_score(
                current_possession, play_result
            )
        
        elif play_result.outcome == "two_point_conversion":
            return self._calculate_two_point_conversion_score(
                current_possession, play_result
            )
        
        # Handle direct score_points from PlayResult if available
        if play_result.score_points > 0:
            return self._calculate_generic_score(
                current_possession, play_result, current_field_position
            )
        
        # No recognizable scoring play
        return ScoreTransition()
    
    def _calculate_touchdown_score(self, scoring_team_id: int, play_result: PlayResult,
                                  field_position: int) -> ScoreTransition:
        """
        Calculate scoring changes for a touchdown.
        
        Touchdowns are worth 6 points and require an extra point attempt.
        """
        points = 6
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id,
            score_type="touchdown",
            requires_extra_point=True,
            home_team_points=points if self._is_home_team(scoring_team_id) else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) else 0,
            play_description=f"{play_result.yards_gained}-yard {play_result.play_type} touchdown",
            field_position=field_position
        )
    
    def _calculate_field_goal_score(self, scoring_team_id: int, play_result: PlayResult,
                                   field_position: int) -> ScoreTransition:
        """
        Calculate scoring changes for a field goal.
        
        Field goals are worth 3 points.
        """
        points = 3
        
        # Calculate distance for description
        distance = 100 - field_position + 17  # Add end zone and holder distance
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id,
            score_type="field_goal",
            requires_extra_point=False,
            home_team_points=points if self._is_home_team(scoring_team_id) else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) else 0,
            play_description=f"{distance}-yard field goal",
            field_position=field_position
        )
    
    def _calculate_safety_score(self, possession_team_id: int, play_result: PlayResult,
                               game_state) -> ScoreTransition:
        """
        Calculate scoring changes for a safety.
        
        Safeties are worth 2 points and go to the team that DIDN'T have possession.
        """
        points = 2
        
        # Safety goes to the other team (defense)
        scoring_team_id = self._get_opposite_team_id(possession_team_id)
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id,
            score_type="safety",
            requires_extra_point=False,
            home_team_points=points if self._is_home_team(scoring_team_id) else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) else 0,
            play_description="Safety",
            field_position=0
        )
    
    def _calculate_extra_point_score(self, scoring_team_id: int, 
                                    play_result: PlayResult) -> ScoreTransition:
        """
        Calculate scoring changes for an extra point attempt.
        
        Extra points are worth 1 point if successful.
        """
        if play_result.outcome == "field_goal":  # Successful extra point
            points = 1
            description = "Extra point good"
        else:
            points = 0
            description = "Extra point failed"
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id if points > 0 else None,
            score_type="extra_point",
            requires_extra_point=False,
            home_team_points=points if self._is_home_team(scoring_team_id) and points > 0 else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) and points > 0 else 0,
            play_description=description,
            field_position=None
        )
    
    def _calculate_two_point_conversion_score(self, scoring_team_id: int,
                                             play_result: PlayResult) -> ScoreTransition:
        """
        Calculate scoring changes for a two-point conversion attempt.
        
        Two-point conversions are worth 2 points if successful.
        """
        if play_result.outcome in ["gain", "touchdown"]:  # Successful conversion
            points = 2
            description = "Two-point conversion good"
        else:
            points = 0
            description = "Two-point conversion failed"
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id if points > 0 else None,
            score_type="two_point_conversion",
            requires_extra_point=False,
            home_team_points=points if self._is_home_team(scoring_team_id) and points > 0 else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) and points > 0 else 0,
            play_description=description,
            field_position=None
        )
    
    def _calculate_generic_score(self, scoring_team_id: int, play_result: PlayResult,
                                field_position: int) -> ScoreTransition:
        """
        Calculate scoring changes from PlayResult.score_points field.
        
        This handles cases where the score is determined by the PlayResult.
        """
        points = play_result.score_points
        
        return ScoreTransition(
            points_scored=points,
            scoring_team_id=scoring_team_id,
            score_type=play_result.outcome,
            requires_extra_point=False,  # Assume no extra point unless explicitly touchdown
            home_team_points=points if self._is_home_team(scoring_team_id) else 0,
            away_team_points=points if not self._is_home_team(scoring_team_id) else 0,
            play_description=f"{points}-point {play_result.outcome}",
            field_position=field_position
        )
    
    def _is_home_team(self, team_id: int) -> bool:
        """
        Check if the given team ID is the home team.
        
        This assumes a simple home/away structure.
        Will need to be adapted based on actual team management.
        """
        # This logic will need to be updated based on actual team management
        # For now, assumes team ID 1 is home team
        return team_id == 1
    
    def _get_opposite_team_id(self, team_id: int) -> int:
        """
        Get the ID of the opposite team.
        
        This assumes a two-team game with home/away structure.
        Will need to be adapted based on actual team ID system.
        """
        # This logic will need to be updated based on actual team management
        # For now, assumes simple home (1) / away (2) or similar structure
        return 2 if team_id == 1 else 1
    
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