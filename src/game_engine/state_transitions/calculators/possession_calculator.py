"""
Possession Calculator - Pure Possession Change Calculations

This module contains pure functions to calculate possession changes based on 
play results. Handles turnovers, scores, punts, and turnover on downs.

Based on the game_orchestrator.py possession logic (lines 177-222).
"""

from typing import Optional
from game_engine.plays.data_structures import PlayResult
# Import the proper PossessionTransition from data_structures
from game_engine.state_transitions.data_structures import PossessionTransition, PossessionChangeReason


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
                play_result, current_possession, game_state
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
                current_possession, game_state
            )
        
        # Check for turnover on downs (lines 217-222)
        if self._is_turnover_on_downs(play_result, game_state):
            return self._calculate_turnover_on_downs_possession_change(
                current_possession, game_state
            )
        
        # No possession change
        return PossessionTransition(
            possession_changes=False,
            old_possessing_team=str(current_possession) if current_possession else None,
            new_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _calculate_score_possession_change(self, play_result: PlayResult, 
                                         current_possession: int, game_state) -> PossessionTransition:
        """
        Calculate possession change after a score.
        
        Based on lines 177-188 in game_orchestrator.py.
        After scoring, possession switches and requires kickoff.
        """
        # Determine receiving team (opposite of scoring team)
        new_possession = self._get_opposite_team_id(current_possession, game_state)
        
        return PossessionTransition(
            new_possessing_team=str(new_possession) if new_possession else None,
            possession_changes=True,
            possession_change_reason=PossessionChangeReason.TOUCHDOWN_SCORED if play_result.play_type in ["run", "pass"] 
                                    else PossessionChangeReason.FIELD_GOAL_SCORED,
            old_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _calculate_turnover_possession_change(self, play_result: PlayResult,
                                            current_possession: int, 
                                            game_state) -> PossessionTransition:
        """
        Calculate possession change for turnovers (fumbles, interceptions).
        
        Based on lines 191-197 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession, game_state)
        
        # TODO: Calculate actual turnover field position based on where it occurred
        # For now using simplified logic from original code
        turnover_field_position = 50  # Simplified as in original
        
        # Import TurnoverType for proper enum mapping
        from ..data_structures.possession_transition import TurnoverType
        
        # Map play outcome to turnover type
        turnover_type_map = {
            "fumble": TurnoverType.FUMBLE_LOST,
            "interception": TurnoverType.INTERCEPTION
        }
        
        # Map outcome to proper PossessionChangeReason enum
        reason_map = {
            "fumble": PossessionChangeReason.TURNOVER_FUMBLE,
            "interception": PossessionChangeReason.TURNOVER_INTERCEPTION
        }
        
        return PossessionTransition(
            new_possessing_team=str(new_possession) if new_possession else None,
            possession_changes=True,
            possession_change_reason=reason_map.get(play_result.outcome, PossessionChangeReason.TURNOVER_FUMBLE),
            turnover_occurred=True,
            turnover_type=turnover_type_map.get(play_result.outcome, TurnoverType.FUMBLE_LOST),
            old_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _calculate_punt_possession_change(self, play_result: PlayResult,
                                        current_possession: int,
                                        game_state) -> PossessionTransition:
        """
        Calculate possession change for punts.
        
        Based on lines 200-206 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession, game_state)
        
        # TODO: Calculate actual punt field position
        # For now using simplified logic from original code  
        punt_field_position = max(20, 100 - play_result.yards_gained)
        
        return PossessionTransition(
            new_possessing_team=str(new_possession) if new_possession else None,
            possession_changes=True,
            possession_change_reason=PossessionChangeReason.PUNT,
            old_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _calculate_touchdown_possession_change(self, current_possession: int, game_state) -> PossessionTransition:
        """
        Calculate possession change for touchdown scored by normal play.
        
        Based on lines 209-214 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession, game_state)
        
        return PossessionTransition(
            new_possessing_team=str(new_possession) if new_possession else None,
            possession_changes=True,
            possession_change_reason=PossessionChangeReason.TOUCHDOWN_SCORED,
            old_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _calculate_turnover_on_downs_possession_change(self, current_possession: int,
                                                     game_state) -> PossessionTransition:
        """
        Calculate possession change for turnover on downs.
        
        Based on lines 217-222 in game_orchestrator.py.
        """
        new_possession = self._get_opposite_team_id(current_possession, game_state)
        
        # Field position stays the same for turnover on downs
        current_field_position = game_state.field.field_position
        
        from ..data_structures.possession_transition import TurnoverType
        
        return PossessionTransition(
            new_possessing_team=str(new_possession) if new_possession else None,
            possession_changes=True,
            possession_change_reason=PossessionChangeReason.TURNOVER_ON_DOWNS,
            turnover_occurred=True,
            turnover_type=TurnoverType.ON_DOWNS,
            old_possessing_team=str(current_possession) if current_possession else None
        )
    
    def _get_opposite_team_id(self, team_id: int, game_state) -> int:
        """
        Get the ID of the opposite team using proper team resolution.
        
        YAGNI FIX: Copy proven working pattern from TransitionApplicator._get_opposing_team_id()
        Uses actual game state team IDs instead of hardcoded values.
        """
        if team_id == game_state.scoreboard.home_team_id:
            return game_state.scoreboard.away_team_id
        return game_state.scoreboard.home_team_id
    
    def _simulate_field_update(self, play_result: PlayResult, game_state) -> str:
        """
        Simulate what the field update would return for touchdown detection.
        
        This replicates the field update logic to detect touchdowns.
        Only detects touchdowns for plays that actually cross into the end zone
        from a normal field position (not already in the end zone).
        """
        current_field_position = game_state.field.field_position
        new_position = current_field_position + play_result.yards_gained
        
        # Only consider it a touchdown if:
        # 1. The play crosses into the end zone (from < 100 to >= 100)
        # 2. The play is actually marked as a scoring play
        # 3. The play starts from a normal field position (not already in end zone)
        if (new_position >= 100 and 
            current_field_position < 100 and 
            play_result.is_score):
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