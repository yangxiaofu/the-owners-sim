"""
Possession Calculator - Pure Possession Change Calculations

This module contains pure functions to calculate possession changes based on 
play results. Handles turnovers, scores, punts, and turnover on downs.

Based on the game_orchestrator.py possession logic (lines 177-222).
"""

from typing import Optional
from dataclasses import dataclass
from ...plays.data_structures import PlayResult


@dataclass(frozen=True)
class PossessionTransition:
    """
    Immutable representation of possession changes.
    
    Contains all possession-related changes that should be applied after a play.
    """
    new_possession_team_id: Optional[int] = None  # Which team should have possession
    possession_changed: bool = False              # Whether possession actually changed
    reason_for_change: Optional[str] = None       # Why possession changed
    requires_kickoff: bool = False                # Whether change requires kickoff
    requires_punt: bool = False                   # Whether this was due to a punt
    requires_turnover_at_spot: bool = False       # Whether turnover happens at spot
    new_field_position: Optional[int] = None      # Field position after possession change
    
    # Context information
    previous_possession_team_id: Optional[int] = None
    change_type: Optional[str] = None             # "score", "turnover", "punt", "turnover_on_downs"


class PossessionCalculator:
    """
    Pure calculator for possession changes.
    
    All methods calculate what possession changes should occur based on
    play results and current game state, without actually changing anything.
    """
    
    def calculate_possession_changes(self, play_result: PlayResult, game_state) -> PossessionTransition:
        """
        Calculate possession changes based on play result.
        
        This replicates the logic from game_orchestrator.py lines 177-222
        but as pure calculation functions.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state with possession information
            
        Returns:
            PossessionTransition with calculated possession changes
        """
        current_possession = game_state.field.possession_team_id
        
        # Check for scoring plays first (lines 177-188)
        if play_result.is_score:
            return self._calculate_score_possession_change(
                play_result, current_possession
            )
        
        # Check for turnovers (lines 191-197)
        if play_result.is_turnover:
            return self._calculate_turnover_possession_change(
                play_result, current_possession, game_state
            )
        
        # Check for punts (lines 200-206)  
        if play_result.play_type == "punt":
            return self._calculate_punt_possession_change(
                play_result, current_possession, game_state
            )
        
        # Check for normal plays that resulted in touchdown (lines 209-214)
        # This is handled by the field calculator, but we need to check if
        # the field update would result in a touchdown
        field_result = self._simulate_field_update(play_result, game_state)
        if field_result == "touchdown":
            return self._calculate_touchdown_possession_change(
                current_possession
            )
        
        # Check for turnover on downs (lines 217-222)
        if self._is_turnover_on_downs(play_result, game_state):
            return self._calculate_turnover_on_downs_possession_change(
                current_possession, game_state
            )
        
        # No possession change
        return PossessionTransition(
            new_possession_team_id=current_possession,
            possession_changed=False,
            previous_possession_team_id=current_possession
        )
    
    def _calculate_score_possession_change(self, play_result: PlayResult, 
                                         current_possession: int) -> PossessionTransition:
        """
        Calculate possession change after a score.
        
        Based on lines 177-188 in game_orchestrator.py.
        After scoring, possession switches and requires kickoff.
        """
        # Determine receiving team (opposite of scoring team)
        new_possession = self._get_opposite_team_id(current_possession)
        
        return PossessionTransition(
            new_possession_team_id=new_possession,
            possession_changed=True,
            reason_for_change=f"{play_result.play_type} score",
            requires_kickoff=True,
            requires_punt=False,
            requires_turnover_at_spot=False,
            new_field_position=25,  # Standard kickoff return position
            previous_possession_team_id=current_possession,
            change_type="score"
        )
    
    def _calculate_turnover_possession_change(self, play_result: PlayResult,
                                            current_possession: int, 
                                            game_state) -> PossessionTransition:
        """
        Calculate possession change for turnovers (fumbles, interceptions).
        
        Based on lines 191-197 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession)
        
        # TODO: Calculate actual turnover field position based on where it occurred
        # For now using simplified logic from original code
        turnover_field_position = 50  # Simplified as in original
        
        return PossessionTransition(
            new_possession_team_id=new_possession,
            possession_changed=True,
            reason_for_change=play_result.outcome,  # "fumble" or "interception"
            requires_kickoff=False,
            requires_punt=False, 
            requires_turnover_at_spot=True,
            new_field_position=turnover_field_position,
            previous_possession_team_id=current_possession,
            change_type="turnover"
        )
    
    def _calculate_punt_possession_change(self, play_result: PlayResult,
                                        current_possession: int,
                                        game_state) -> PossessionTransition:
        """
        Calculate possession change for punts.
        
        Based on lines 200-206 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession)
        
        # TODO: Calculate actual punt field position
        # For now using simplified logic from original code  
        punt_field_position = max(20, 100 - play_result.yards_gained)
        
        return PossessionTransition(
            new_possession_team_id=new_possession,
            possession_changed=True,
            reason_for_change="punt",
            requires_kickoff=False,
            requires_punt=True,
            requires_turnover_at_spot=False,
            new_field_position=punt_field_position,
            previous_possession_team_id=current_possession,
            change_type="punt"
        )
    
    def _calculate_touchdown_possession_change(self, current_possession: int) -> PossessionTransition:
        """
        Calculate possession change for touchdown scored by normal play.
        
        Based on lines 209-214 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession)
        
        return PossessionTransition(
            new_possession_team_id=new_possession,
            possession_changed=True,
            reason_for_change="touchdown",
            requires_kickoff=True,
            requires_punt=False,
            requires_turnover_at_spot=False,
            new_field_position=25,  # Standard kickoff return position
            previous_possession_team_id=current_possession,
            change_type="score"
        )
    
    def _calculate_turnover_on_downs_possession_change(self, current_possession: int,
                                                     game_state) -> PossessionTransition:
        """
        Calculate possession change for turnover on downs.
        
        Based on lines 217-222 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession)
        
        # Field position stays the same for turnover on downs
        current_field_position = game_state.field.field_position
        
        return PossessionTransition(
            new_possession_team_id=new_possession,
            possession_changed=True,
            reason_for_change="turnover on downs",
            requires_kickoff=False,
            requires_punt=False,
            requires_turnover_at_spot=True,
            new_field_position=current_field_position,
            previous_possession_team_id=current_possession,
            change_type="turnover_on_downs"
        )
    
    def _get_opposite_team_id(self, team_id: int) -> int:
        """
        Get the ID of the opposite team.
        
        This assumes a two-team game with home/away structure.
        Will need to be adapted based on actual team ID system.
        """
        # This logic will need to be updated based on actual team management
        # For now, assumes simple home (1) / away (2) or similar structure
        return 2 if team_id == 1 else 1
    
    def _simulate_field_update(self, play_result: PlayResult, game_state) -> str:
        """
        Simulate what the field update would return for touchdown detection.
        
        This replicates the field update logic to detect touchdowns.
        """
        current_field_position = game_state.field.field_position
        new_position = current_field_position + play_result.yards_gained
        
        if new_position >= 100:
            return "touchdown"
        
        return "normal"
    
    def _is_turnover_on_downs(self, play_result: PlayResult, game_state) -> bool:
        """
        Check if the play would result in turnover on downs.
        
        This checks if the down would exceed 4 after the play.
        """
        current_down = game_state.field.down
        yards_to_go = game_state.field.yards_to_go
        yards_gained = play_result.yards_gained
        
        # Check if first down would be achieved
        if yards_gained >= yards_to_go:
            return False  # First down achieved, no turnover
        
        # Check if next down would exceed 4
        next_down = current_down + 1
        return next_down > 4