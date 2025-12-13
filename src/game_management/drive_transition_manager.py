"""
Drive Transition Manager

Handles transitions between drives including kickoffs, punts, turnovers, and scoring plays.
Coordinates with PossessionManager and DriveManager to ensure smooth drive handoffs.
"""

import random
from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from play_engine.game_state.drive_manager import DriveManager, DriveEndReason
from play_engine.game_state.possession_manager import PossessionManager
from play_engine.game_state.game_clock import GameClock
from play_engine.core.play_result import PlayResult


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
    # Quarter continuation fields - preserve down state when drive continues across quarters
    continuing_down: Optional[int] = None  # Current down (1-4)
    continuing_yards_to_go: Optional[int] = None  # Yards needed for first down
    is_drive_continuation: bool = False  # True if same drive continues (Q1→Q2, Q3→Q4)


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
                              away_team_id: int,
                              actual_punt_play=None) -> TransitionResult:
        """
        Handle transition from completed drive to next drive

        Args:
            completed_drive: The drive that just ended
            home_team_id: Home team ID
            away_team_id: Away team ID
            actual_punt_play: Optional PlayResult containing actual punt data
                             (if provided, uses this instead of re-simulating)

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
            return self._handle_punt_transition(possessing_team_id, opposing_team_id, completed_drive, actual_punt_play)

        elif drive_end_reason in [DriveEndReason.TURNOVER_INTERCEPTION,
                                   DriveEndReason.TURNOVER_FUMBLE]:
            return self._handle_turnover_transition(possessing_team_id, opposing_team_id, completed_drive)

        elif drive_end_reason == DriveEndReason.SAFETY:
            return self._handle_safety_transition(possessing_team_id, opposing_team_id)

        elif drive_end_reason == DriveEndReason.TIME_EXPIRATION:
            return self._handle_time_expiration_transition(possessing_team_id, opposing_team_id, completed_drive)

        else:
            # Default to turnover on downs (treat as punt)
            return self._handle_punt_transition(possessing_team_id, opposing_team_id, completed_drive, actual_punt_play)
    
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
    
    def _handle_punt_transition(self, punting_team_id: int, receiving_team_id: int,
                                 completed_drive: DriveManager, actual_punt_play=None) -> TransitionResult:
        """Handle transition after punt

        Args:
            punting_team_id: Team that punted
            receiving_team_id: Team receiving the punt
            completed_drive: The drive that just ended
            actual_punt_play: Optional PlayResult with actual punt data from the game engine
        """
        field_position = completed_drive.get_current_field_position().yard_line

        # ✅ FIX: Use actual punt data if available, otherwise fallback to simulation
        if actual_punt_play is not None:
            # Use the ACTUAL punt result from the game engine
            punt_distance = getattr(actual_punt_play, 'punt_distance', None)
            return_yards = getattr(actual_punt_play, 'return_yards', None) or 0

            if punt_distance is not None:
                # Calculate receiving team's field position using actual values
                landing_spot = field_position + punt_distance

                # Handle touchback
                if landing_spot >= 100:
                    receiving_team_field_position = 25
                    is_touchback = True
                else:
                    is_touchback = False
                    # Flip to receiving team's perspective
                    receiving_team_field_position = 100 - landing_spot
                    # Apply return yards (return moves toward opponent's goal = increases field position)
                    receiving_team_field_position = min(receiving_team_field_position + return_yards, 95)

                # Create a PuntResult with actual data
                punt_result = PuntResult(
                    punting_team_id=punting_team_id,
                    receiving_team_id=receiving_team_id,
                    punt_yards=punt_distance,
                    return_yards=return_yards,
                    starting_field_position=receiving_team_field_position,
                    is_touchback=is_touchback,
                    is_fair_catch=return_yards == 0 and not is_touchback,  # Approximate
                    description=f"Punt {punt_distance} yards, returned {return_yards} yards, starts at {receiving_team_field_position}-yard line"
                )
            else:
                # Fallback: punt_distance not available, re-simulate
                punt_result = self._simulate_punt(
                    punting_team_id=punting_team_id,
                    receiving_team_id=receiving_team_id,
                    field_position=field_position
                )
        else:
            # No actual punt data, re-simulate (legacy behavior)
            punt_result = self._simulate_punt(
                punting_team_id=punting_team_id,
                receiving_team_id=receiving_team_id,
                field_position=field_position
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
    
    def _handle_time_expiration_transition(self, current_possessing_team_id: int,
                                            opposing_team_id: int,
                                            completed_drive: DriveManager) -> TransitionResult:
        """Handle transition when time expires (end of quarter/half/game)"""
        # When time expires, typically no possession change unless it's halftime
        if self.game_clock and self.game_clock.quarter == 2:
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
            # Regular quarter end (Q1, Q3, Q4) - preserve field position AND down state
            current_field_position = completed_drive.get_current_field_position().yard_line
            current_down_state = completed_drive.get_current_down_state()

            return TransitionResult(
                transition_type=TransitionType.TIME_EXPIRATION,
                new_possessing_team_id=current_possessing_team_id,
                new_starting_field_position=current_field_position,
                time_elapsed=0,
                description=f"Quarter ended. Drive continues at {current_field_position}-yard line, {current_down_state.current_down}{'st' if current_down_state.current_down == 1 else 'nd' if current_down_state.current_down == 2 else 'rd' if current_down_state.current_down == 3 else 'th'} & {current_down_state.yards_to_go}",
                continuing_down=current_down_state.current_down,
                continuing_yards_to_go=current_down_state.yards_to_go,
                is_drive_continuation=True
            )
    
    def _simulate_kickoff(self, kicking_team_id: int, receiving_team_id: int, is_onside_kick: bool = False) -> KickoffResult:
        """
        Simulate kickoff with realistic NFL outcomes

        Based on 2024 NFL data:
        - Touchback rate: ~50-55% (down from 65% in previous years)
        - Average return: 23-26 yards (for non-touchbacks)
        - Return range: 10-40 yards typical, rare 40+ yard returns
        - Starting position distribution:
          * Touchbacks: 25-yard line (55%)
          * Returns: 18-32 yard line average (45%)
        """
        if is_onside_kick:
            # Onside kick - much shorter with recovery attempt
            recovery_success = random.random() < 0.25  # ~25% success rate (NFL average)
            if recovery_success:
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=0,
                    starting_field_position=random.randint(42, 48),  # Around midfield
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
            # Regular kickoff - more realistic distribution
            touchback_chance = 0.52  # 52% touchback rate (2024 NFL average)

            if random.random() < touchback_chance:
                return KickoffResult(
                    kicking_team_id=kicking_team_id,
                    receiving_team_id=receiving_team_id,
                    return_yards=0,
                    starting_field_position=25,  # Touchback at 25-yard line
                    is_touchback=True,
                    is_onside_kick=False,
                    description="Touchback to 25-yard line"
                )
            else:
                # Kickoff return - simulate realistic outcomes
                # Most NFL kickoffs reach 3-8 yards deep in the end zone or land at 1-5 yard line
                distribution_roll = random.random()

                if distribution_roll < 0.10:  # 10% - short return (bad blocking/quick tackle)
                    return_yards = random.randint(8, 17)
                elif distribution_roll < 0.70:  # 60% - average return
                    return_yards = random.randint(18, 28)
                elif distribution_roll < 0.92:  # 22% - good return
                    return_yards = random.randint(29, 38)
                else:  # 8% - big return (40+ yards)
                    return_yards = random.randint(39, 65)

                # Most kickoffs land in/near the end zone, so returns start from goal line
                # A 20-yard return from the goal line = 20-yard line
                # A 25-yard return from the goal line = 25-yard line
                # NFL average return position is around 22-24 yard line
                starting_position = min(return_yards, 95)  # Can't exceed 95-yard line

                # Add slight variance for kicks that don't reach end zone
                # (about 15% of non-touchback kicks land short)
                if random.random() < 0.15:
                    # Kick landed short (3-7 yard line)
                    catch_spot = random.randint(3, 7)
                    starting_position = min(catch_spot + return_yards, 95)

                # Cap extremely good field position (very rare to cross own 45 unless huge return)
                if starting_position > 45 and return_yards < 50:
                    starting_position = random.randint(35, 43)

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
        punt_distance = random.randint(35, 50)

        # Fair catch chance increases in certain situations
        fair_catch_chance = 0.3
        is_fair_catch = random.random() < fair_catch_chance

        # Calculate where punt lands from punting team's perspective (how far down field)
        landing_spot = field_position + punt_distance

        # Handle touchback (punt into end zone)
        if landing_spot >= 100:
            receiving_team_field_position = 25  # Touchback at 25-yard line
            is_touchback = True
            return_yards = 0
        else:
            is_touchback = False
            # Convert to receiving team's yard line (flip the field)
            receiving_team_field_position = 100 - landing_spot

            # Apply return yards if not a fair catch
            if is_fair_catch:
                return_yards = 0
            else:
                return_yards = random.randint(3, 12)  # Typical punt return
                # Return moves the ball toward punting team's goal (increases field position)
                receiving_team_field_position = min(receiving_team_field_position + return_yards, 95)

        return PuntResult(
            punting_team_id=punting_team_id,
            receiving_team_id=receiving_team_id,
            punt_yards=punt_distance,
            return_yards=return_yards,
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