"""
Drive Transition Manager

Handles transitions between drives including kickoffs, punts, turnovers, and scoring plays.
Coordinates with PossessionManager and DriveManager to ensure smooth drive handoffs.
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from src.play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from src.play_engine.game_state.possession_manager import PossessionManager
from src.play_engine.game_state.game_clock import GameClock
from src.play_engine.core.play_result import PlayResult


class TransitionType(Enum):
    """Types of drive transitions"""
    KICKOFF = "kickoff"
    PUNT = "punt"
    TURNOVER = "turnover"
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"
    ONSIDE_KICK = "onside_kick"
    TIME_EXPIRATION = "time_expiration"


@dataclass
class KickoffResult:
    """Result of a kickoff play"""
    kicking_team_id: int
    receiving_team_id: int
    return_yards: int
    starting_field_position: int
    is_touchback: bool
    is_onside_kick: bool
    onside_kick_recovered: bool = False
    description: str = ""


@dataclass
class PuntResult:
    """Result of a punt play"""
    punting_team_id: int
    receiving_team_id: int
    punt_yards: int
    return_yards: int
    starting_field_position: int
    is_touchback: bool
    is_fair_catch: bool
    description: str = ""


@dataclass 
class TransitionResult:
    """Complete result of drive transition"""
    transition_type: TransitionType
    new_possessing_team_id: int
    new_starting_field_position: int
    time_elapsed: int = 0
    description: str = ""
    kickoff_result: Optional[KickoffResult] = None
    punt_result: Optional[PuntResult] = None


class DriveTransitionManager:
    """
    Manages transitions between drives based on how the previous drive ended.
    
    Handles realistic NFL scenarios:
    - Kickoffs after scoring plays
    - Punts after failed offensive drives
    - Turnovers with immediate possession change
    - Special situations (safeties, onside kicks)
    """
    
    def __init__(self, possession_manager: PossessionManager, game_clock: Optional[GameClock] = None):
        """
        Initialize drive transition manager
        
        Args:
            possession_manager: Manages possession tracking
            game_clock: Game clock for time management (optional)
        """
        self.possession_manager = possession_manager
        self.game_clock = game_clock
    
    def handle_drive_transition(self, 
                              completed_drive: DriveManager, 
                              home_team_id: int,
                              away_team_id: int) -> TransitionResult:
        """
        Handle transition from completed drive to next drive
        
        Args:
            completed_drive: The drive that just ended
            home_team_id: Home team ID
            away_team_id: Away team ID
            
        Returns:
            TransitionResult with details about the transition and new drive setup
        """
        drive_end_reason = completed_drive.get_drive_end_reason()
        possessing_team_id = completed_drive.get_possessing_team_id()
        
        # Determine opposing team
        opposing_team_id = away_team_id if possessing_team_id == home_team_id else home_team_id
        
        # Handle different drive ending scenarios
        if drive_end_reason == DriveEndReason.TOUCHDOWN:
            return self._handle_touchdown_transition(possessing_team_id, opposing_team_id)
        
        elif drive_end_reason == DriveEndReason.FIELD_GOAL:
            return self._handle_field_goal_transition(possessing_team_id, opposing_team_id)
        
        elif drive_end_reason == DriveEndReason.FIELD_GOAL_MISSED:
            return self._handle_field_goal_missed_transition(possessing_team_id, opposing_team_id, completed_drive)
        
        elif drive_end_reason == DriveEndReason.PUNT:
            return self._handle_punt_transition(possessing_team_id, opposing_team_id, completed_drive)
        
        elif drive_end_reason in [DriveEndReason.TURNOVER_INTERCEPTION, 
                                   DriveEndReason.TURNOVER_FUMBLE]:
            return self._handle_turnover_transition(possessing_team_id, opposing_team_id, completed_drive)
        
        elif drive_end_reason == DriveEndReason.SAFETY:
            return self._handle_safety_transition(possessing_team_id, opposing_team_id)
        
        elif drive_end_reason == DriveEndReason.TIME_EXPIRATION:
            return self._handle_time_expiration_transition(possessing_team_id, opposing_team_id)
        
        else:
            # Default to turnover on downs (treat as punt)
            return self._handle_punt_transition(possessing_team_id, opposing_team_id, completed_drive)
    
    def _handle_touchdown_transition(self, scoring_team_id: int, opposing_team_id: int) -> TransitionResult:
        """Handle transition after touchdown (kickoff)"""
        # After touchdown, scoring team kicks off to opposing team
        kickoff_result = self._simulate_kickoff(
            kicking_team_id=scoring_team_id,
            receiving_team_id=opposing_team_id,
            is_onside_kick=False
        )
        
        # Update possession to receiving team
        self.possession_manager.set_possession(opposing_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.TOUCHDOWN,
            new_possessing_team_id=opposing_team_id,
            new_starting_field_position=kickoff_result.starting_field_position,
            time_elapsed=5,  # Kickoff takes about 5 seconds
            description=f"Touchdown scored. Kickoff to opposing team at {kickoff_result.starting_field_position}-yard line",
            kickoff_result=kickoff_result
        )
    
    def _handle_field_goal_transition(self, scoring_team_id: int, opposing_team_id: int) -> TransitionResult:
        """Handle transition after field goal (kickoff)"""
        # After field goal, scoring team kicks off to opposing team
        kickoff_result = self._simulate_kickoff(
            kicking_team_id=scoring_team_id,
            receiving_team_id=opposing_team_id,
            is_onside_kick=False
        )
        
        # Update possession to receiving team
        self.possession_manager.set_possession(opposing_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.FIELD_GOAL,
            new_possessing_team_id=opposing_team_id,
            new_starting_field_position=kickoff_result.starting_field_position,
            time_elapsed=5,
            description=f"Field goal scored. Kickoff to opposing team at {kickoff_result.starting_field_position}-yard line",
            kickoff_result=kickoff_result
        )
    
    def _handle_field_goal_missed_transition(self, attempting_team_id: int, opposing_team_id: int, completed_drive) -> TransitionResult:
        """Handle transition after missed field goal (turnover on downs with special field position rules)"""
        # Get field position where field goal attempt was made
        attempt_position = completed_drive.get_current_field_position().yard_line
        
        # NFL Rule: Opposing team gets ball at spot of attempt, but never closer than 20-yard line
        # If attempt was from opponent's 30-yard line, opponent gets ball at their own 30
        # But if attempt was from inside opponent's 20, opponent gets ball at their own 20
        opponent_field_position = 100 - attempt_position  # Flip field
        new_field_position = max(20, opponent_field_position)  # Apply 20-yard minimum rule
        
        # Change possession to opposing team
        self.possession_manager.set_possession(opposing_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.TURNOVER,
            new_possessing_team_id=opposing_team_id,
            new_starting_field_position=new_field_position,
            time_elapsed=0,  # No time consumed by missed field goal
            description=f"Field goal missed. Turnover on downs to opposing team. New drive starts at {new_field_position}-yard line"
        )
    
    def _handle_punt_transition(self, punting_team_id: int, receiving_team_id: int, completed_drive: DriveManager) -> TransitionResult:
        """Handle transition after punt"""
        punt_result = self._simulate_punt(
            punting_team_id=punting_team_id,
            receiving_team_id=receiving_team_id,
            field_position=completed_drive.get_current_field_position().yard_line
        )
        
        # Update possession to receiving team
        self.possession_manager.set_possession(receiving_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.PUNT,
            new_possessing_team_id=receiving_team_id,
            new_starting_field_position=punt_result.starting_field_position,
            time_elapsed=8,  # Punt play takes longer
            description=f"Punt to opposing team. New drive starts at {punt_result.starting_field_position}-yard line",
            punt_result=punt_result
        )
    
    def _handle_turnover_transition(self, previous_possessing_team_id: int, new_possessing_team_id: int, completed_drive: DriveManager) -> TransitionResult:
        """Handle transition after turnover (no special teams play)"""
        # Turnover means possession changes immediately at current field position
        current_field_position = completed_drive.get_current_field_position().yard_line
        
        # For turnovers, field position flips (e.g., their 30 becomes our 70)
        flipped_field_position = 100 - current_field_position
        
        # Update possession to new team
        self.possession_manager.set_possession(new_possessing_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.TURNOVER,
            new_possessing_team_id=new_possessing_team_id,
            new_starting_field_position=flipped_field_position,
            time_elapsed=0,  # No additional time for turnover
            description=f"Turnover! New drive starts at {flipped_field_position}-yard line"
        )
    
    def _handle_safety_transition(self, team_that_gave_up_safety_id: int, opposing_team_id: int) -> TransitionResult:
        """Handle transition after safety (safety punt/kickoff)"""
        # After safety, team that gave up safety must kick to opposing team
        # This is typically a punt-like kick from their own 20
        kickoff_result = self._simulate_safety_kick(
            kicking_team_id=team_that_gave_up_safety_id,
            receiving_team_id=opposing_team_id
        )
        
        # Update possession to receiving team
        self.possession_manager.set_possession(opposing_team_id)
        
        return TransitionResult(
            transition_type=TransitionType.SAFETY,
            new_possessing_team_id=opposing_team_id,
            new_starting_field_position=kickoff_result.starting_field_position,
            time_elapsed=6,
            description=f"Safety! Free kick to opposing team at {kickoff_result.starting_field_position}-yard line",
            kickoff_result=kickoff_result
        )
    
    def _handle_time_expiration_transition(self, current_possessing_team_id: int, opposing_team_id: int) -> TransitionResult:
        """Handle transition when time expires (end of quarter/half/game)"""
        # When time expires, typically no possession change unless it's halftime
        if self.game_clock and self.game_clock.get_current_quarter() == 2:
            # End of first half - halftime possession change
            # The team that didn't receive opening kickoff gets second half kickoff
            halftime_receiving_team = opposing_team_id  # Simplified logic
            kickoff_result = self._simulate_kickoff(
                kicking_team_id=current_possessing_team_id,
                receiving_team_id=halftime_receiving_team,
                is_onside_kick=False
            )
            
            self.possession_manager.handle_halftime_change(halftime_receiving_team)
            
            return TransitionResult(
                transition_type=TransitionType.TIME_EXPIRATION,
                new_possessing_team_id=halftime_receiving_team,
                new_starting_field_position=kickoff_result.starting_field_position,
                time_elapsed=0,
                description=f"Halftime. Second half kickoff at {kickoff_result.starting_field_position}-yard line",
                kickoff_result=kickoff_result
            )
        else:
            # Regular quarter end - possession stays the same
            return TransitionResult(
                transition_type=TransitionType.TIME_EXPIRATION,
                new_possessing_team_id=current_possessing_team_id,
                new_starting_field_position=50,  # Default field position
                time_elapsed=0,
                description="Quarter ended. Possession continues next quarter"
            )
    
    def _simulate_kickoff(self, kicking_team_id: int, receiving_team_id: int, is_onside_kick: bool = False) -> KickoffResult:
        """Simulate kickoff with realistic NFL outcomes"""
        if is_onside_kick:
            # Onside kick - much shorter with recovery attempt
            recovery_success = random.random() < 0.3  # ~30% success rate
            if recovery_success:
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=0,
                    starting_field_position=45,  # Around midfield
                    is_touchback=False,
                    is_onside_kick=True,
                    onside_kick_recovered=True,
                    description="Onside kick recovered by kicking team!"
                )
            else:
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=random.randint(5, 15),
                    starting_field_position=random.randint(35, 50),
                    is_touchback=False,
                    is_onside_kick=True,
                    onside_kick_recovered=False,
                    description="Onside kick recovered by receiving team"
                )
        else:
            # Regular kickoff
            touchback_chance = 0.65  # 65% of kickoffs are touchbacks
            if random.random() < touchback_chance:
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=0,
                    starting_field_position=25,  # Touchback
                    is_touchback=True,
                    is_onside_kick=False,
                    description="Touchback. Drive starts at 25-yard line"
                )
            else:
                # Kickoff return
                return_yards = random.randint(15, 40)  # Typical return range
                starting_position = min(25 + return_yards, 95)  # Cap at 95-yard line
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=return_yards,
                    starting_field_position=starting_position,
                    is_touchback=False,
                    is_onside_kick=False,
                    description=f"Kickoff returned {return_yards} yards to {starting_position}-yard line"
                )
    
    def _simulate_punt(self, punting_team_id: int, receiving_team_id: int, field_position: int) -> PuntResult:
        """Simulate punt with realistic NFL outcomes"""
        # Punt distance varies based on field position
        base_punt_distance = random.randint(35, 50)
        
        # Fair catch chance increases in certain situations
        fair_catch_chance = 0.3
        is_fair_catch = random.random() < fair_catch_chance
        
        if is_fair_catch:
            punt_distance = base_punt_distance
            return_yards = 0
            final_position = min(field_position + punt_distance, 99)
        else:
            punt_distance = base_punt_distance
            return_yards = random.randint(3, 12)  # Typical punt return
            final_position = min(field_position + punt_distance - return_yards, 99)
        
        # Check for touchback
        is_touchback = final_position >= 80 and random.random() < 0.4
        if is_touchback:
            final_position = 20  # Touchback on punt
        
        # Convert to receiving team's field position
        receiving_team_field_position = 100 - final_position
        
        return PuntResult(
            punting_team_id=punting_team_id,
            receiving_team_id=receiving_team_id,
            punt_yards=punt_distance,
            return_yards=return_yards if not is_fair_catch else 0,
            starting_field_position=receiving_team_field_position,
            is_touchback=is_touchback,
            is_fair_catch=is_fair_catch,
            description=f"Punt {punt_distance} yards, {'' if is_fair_catch else f'returned {return_yards} yards, '}starts at {receiving_team_field_position}-yard line"
        )
    
    def _simulate_safety_kick(self, kicking_team_id: int, receiving_team_id: int) -> KickoffResult:
        """Simulate safety kick (free kick after safety)"""
        # Safety kicks are typically shorter and more returnable
        return_yards = random.randint(20, 35)
        starting_position = min(20 + return_yards, 90)
        
        return KickoffResult(
            kicking_team_id=kicking_team_id,
            receiving_team_id=receiving_team_id,
            return_yards=return_yards,
            starting_field_position=starting_position,
            is_touchback=False,
            is_onside_kick=False,
            description=f"Safety kick returned {return_yards} yards to {starting_position}-yard line"
        )