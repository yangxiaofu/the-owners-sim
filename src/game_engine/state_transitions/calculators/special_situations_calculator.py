"""
Special Situations Calculator - Pure Complex Scenario Calculations

This module contains pure functions to calculate special situation changes
like kickoffs, punts, turnovers, and other complex game scenarios.

Based on the game_orchestrator.py kickoff simulation (lines 182-188) and
other special situation handling throughout the game loop.
"""

from typing import List, Optional
from dataclasses import dataclass, field
from ...plays.data_structures import PlayResult


@dataclass(frozen=True)
class KickoffResult:
    """Result of a kickoff simulation."""
    final_field_position: int = 25              # Where receiving team starts
    return_yards: int = 0                       # Yards returned
    outcome: str = "return"                     # "return", "touchback", "onside", "fumble"
    returner: Optional[str] = None              # Player who returned kick
    tackler: Optional[str] = None               # Player who made tackle


@dataclass(frozen=True)
class SpecialSituationTransition:
    """
    Immutable representation of special situation changes.
    
    Contains all special situation-related changes that should be applied.
    """
    situation_type: str                         # "kickoff", "punt_return", "onside_kick", "safety_kick"
    requires_immediate_action: bool = False     # Whether this needs immediate handling
    new_field_position: Optional[int] = None    # Field position after special situation
    new_possession_team_id: Optional[int] = None # Team that gains possession
    
    # Kickoff specific data
    kickoff_result: Optional[KickoffResult] = None
    
    # Punt specific data
    punt_distance: Optional[int] = None         # Net punt distance
    punt_return_yards: Optional[int] = None     # Return yards
    fair_catch: bool = False                    # Whether fair catch was called
    
    # Turnover specific data
    turnover_location: Optional[int] = None     # Where turnover occurred
    recovery_team_id: Optional[int] = None      # Team that recovered ball
    
    # Context information
    description: Optional[str] = None           # Human readable description
    involves_penalty: bool = False              # Whether penalty affects outcome


class SpecialSituationsCalculator:
    """
    Pure calculator for special situations and complex scenarios.
    
    All methods calculate what special situation changes should occur based on
    play results and current game state, without actually changing anything.
    """
    
    def calculate_special_situations(self, play_result: PlayResult, game_state) -> List[SpecialSituationTransition]:
        """
        Calculate all special situation changes based on play result.
        
        This identifies and calculates complex scenarios that require
        special handling beyond normal field/possession/score changes.
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state
            
        Returns:
            List of SpecialSituationTransition objects for complex scenarios
        """
        special_situations = []
        
        # Check for required kickoff after scoring
        if play_result.is_score:
            kickoff_situation = self._calculate_post_score_kickoff(play_result, game_state)
            if kickoff_situation:
                special_situations.append(kickoff_situation)
        
        # Check for punt return situation
        if play_result.play_type == "punt":
            punt_situation = self._calculate_punt_return(play_result, game_state)
            if punt_situation:
                special_situations.append(punt_situation)
        
        # Check for turnover recovery scenarios
        if play_result.is_turnover:
            turnover_situation = self._calculate_turnover_recovery(play_result, game_state)
            if turnover_situation:
                special_situations.append(turnover_situation)
        
        # Check for safety punt requirement
        if play_result.outcome == "safety":
            safety_situation = self._calculate_safety_punt(play_result, game_state)
            if safety_situation:
                special_situations.append(safety_situation)
        
        # Check for onside kick scenarios
        if self._should_consider_onside_kick(play_result, game_state):
            onside_situation = self._calculate_onside_kick_attempt(play_result, game_state)
            if onside_situation:
                special_situations.append(onside_situation)
        
        return special_situations
    
    def _calculate_post_score_kickoff(self, play_result: PlayResult, game_state) -> Optional[SpecialSituationTransition]:
        """
        Calculate kickoff requirements after a score.
        
        Based on game_orchestrator.py lines 182-188.
        """
        if not play_result.is_score:
            return None
        
        scoring_team_id = game_state.field.possession_team_id
        receiving_team_id = self._get_opposite_team_id(scoring_team_id)
        
        # Simulate the kickoff
        kickoff_result = self._simulate_kickoff(scoring_team_id, receiving_team_id)
        
        return SpecialSituationTransition(
            situation_type="kickoff",
            requires_immediate_action=True,
            new_field_position=kickoff_result.final_field_position,
            new_possession_team_id=receiving_team_id,
            kickoff_result=kickoff_result,
            description=f"Kickoff after {play_result.outcome}",
            involves_penalty=False
        )
    
    def _calculate_punt_return(self, play_result: PlayResult, game_state) -> Optional[SpecialSituationTransition]:
        """
        Calculate punt return scenario.
        
        This handles the receiving team's punt return attempt.
        """
        if play_result.play_type != "punt":
            return None
        
        punting_team_id = game_state.field.possession_team_id
        receiving_team_id = self._get_opposite_team_id(punting_team_id)
        
        # Calculate punt specifics
        punt_distance = play_result.yards_gained
        final_position = max(20, 100 - punt_distance)  # Simplified from original
        
        # Simulate return (simplified)
        return_yards = self._simulate_punt_return()
        fair_catch = self._should_fair_catch(final_position)
        
        if fair_catch:
            return_yards = 0
        
        final_field_position = max(1, final_position - return_yards)
        
        return SpecialSituationTransition(
            situation_type="punt_return",
            requires_immediate_action=False,
            new_field_position=final_field_position,
            new_possession_team_id=receiving_team_id,
            punt_distance=punt_distance,
            punt_return_yards=return_yards,
            fair_catch=fair_catch,
            description=f"{punt_distance}-yard punt, {return_yards}-yard return" if not fair_catch else f"{punt_distance}-yard punt, fair catch",
            involves_penalty=False
        )
    
    def _calculate_turnover_recovery(self, play_result: PlayResult, game_state) -> Optional[SpecialSituationTransition]:
        """
        Calculate turnover recovery scenario.
        
        This handles where the ball is spotted after a turnover.
        """
        if not play_result.is_turnover:
            return None
        
        current_possession = game_state.field.possession_team_id
        recovering_team_id = self._get_opposite_team_id(current_possession)
        
        # Calculate turnover location (simplified)
        turnover_location = self._calculate_turnover_spot(play_result, game_state)
        
        return SpecialSituationTransition(
            situation_type=f"turnover_{play_result.outcome}",
            requires_immediate_action=False,
            new_field_position=turnover_location,
            new_possession_team_id=recovering_team_id,
            turnover_location=turnover_location,
            recovery_team_id=recovering_team_id,
            description=f"{play_result.outcome} recovered at {turnover_location}-yard line",
            involves_penalty=False
        )
    
    def _calculate_safety_punt(self, play_result: PlayResult, game_state) -> Optional[SpecialSituationTransition]:
        """
        Calculate safety punt scenario.
        
        After a safety, the team that gave up the safety must punt from their 20-yard line.
        """
        if play_result.outcome != "safety":
            return None
        
        safety_team_id = game_state.field.possession_team_id  # Team that gave up safety
        receiving_team_id = self._get_opposite_team_id(safety_team_id)
        
        return SpecialSituationTransition(
            situation_type="safety_kick",
            requires_immediate_action=True,
            new_field_position=20,  # Safety punt from 20-yard line
            new_possession_team_id=safety_team_id,  # Team that gave up safety punts
            description="Safety punt required",
            involves_penalty=False
        )
    
    def _calculate_onside_kick_attempt(self, play_result: PlayResult, game_state) -> Optional[SpecialSituationTransition]:
        """
        Calculate onside kick attempt scenario.
        
        This would be used in desperate late-game situations.
        """
        # Simulate onside kick attempt
        recovery_successful = self._simulate_onside_kick_recovery()
        
        if recovery_successful:
            # Kicking team recovers
            recovering_team_id = game_state.field.possession_team_id
            field_position = 50  # Simplified onside recovery position
        else:
            # Receiving team gets great field position
            recovering_team_id = self._get_opposite_team_id(game_state.field.possession_team_id)
            field_position = 40  # Good field position for receiving team
        
        return SpecialSituationTransition(
            situation_type="onside_kick",
            requires_immediate_action=True,
            new_field_position=field_position,
            new_possession_team_id=recovering_team_id,
            description=f"Onside kick {'recovered' if recovery_successful else 'failed'}",
            involves_penalty=False
        )
    
    def _simulate_kickoff(self, kicking_team_id: int, receiving_team_id: int) -> KickoffResult:
        """
        Simulate a kickoff return.
        
        This replicates the _simulate_kickoff method from game_orchestrator.py.
        """
        # Simplified kickoff simulation
        # In a real implementation, this would be much more complex
        
        # 70% chance of normal return, 30% chance of touchback
        import random
        
        if random.random() < 0.3:
            # Touchback
            return KickoffResult(
                final_field_position=25,
                return_yards=0,
                outcome="touchback"
            )
        else:
            # Normal return
            return_yards = random.randint(15, 35)  # Typical return range
            final_position = min(25 + return_yards, 50)  # Cap at midfield
            
            return KickoffResult(
                final_field_position=final_position,
                return_yards=return_yards,
                outcome="return"
            )
    
    def _simulate_punt_return(self) -> int:
        """Simulate punt return yards."""
        import random
        # Most punts have minimal return
        return random.randint(0, 12)
    
    def _should_fair_catch(self, punt_position: int) -> bool:
        """Determine if punt return should be fair caught."""
        # More likely to fair catch deep in own territory
        return punt_position < 15
    
    def _calculate_turnover_spot(self, play_result: PlayResult, game_state) -> int:
        """Calculate where turnover occurred."""
        # Simplified - use current field position adjusted by play
        base_position = game_state.field.field_position
        return max(1, min(99, base_position + play_result.yards_gained))
    
    def _should_consider_onside_kick(self, play_result: PlayResult, game_state) -> bool:
        """Determine if onside kick should be considered."""
        # Only consider in specific game situations
        if not play_result.is_score:
            return False
        
        # Check if losing with little time left
        clock = game_state.clock
        if clock.quarter >= 4 and clock.clock < 300:  # Less than 5 minutes
            # Would need to check score differential
            return True
        
        return False
    
    def _simulate_onside_kick_recovery(self) -> bool:
        """Simulate onside kick recovery success."""
        import random
        # Onside kicks succeed about 25% of the time
        return random.random() < 0.25
    
    def _get_opposite_team_id(self, team_id: int) -> int:
        """Get the opposite team ID."""
        # This logic will need to be updated based on actual team management
        return 2 if team_id == 1 else 1