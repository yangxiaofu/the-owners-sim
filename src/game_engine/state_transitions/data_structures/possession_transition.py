"""
PossessionTransition - Team Possession Changes

This data structure represents all changes to team possession, including
turnovers, change of possession scenarios, and the reasons behind possession
changes. It tracks which team has the ball and why possession changed.

Key responsibilities:
- Track possession changes between teams
- Identify turnover scenarios and types
- Record reasons for possession changes
- Handle special possession situations (onside kicks, etc.)
- Manage possession-related game state flags
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class PossessionChangeReason(Enum):
    """Enumeration of reasons why possession changed."""
    TURNOVER_FUMBLE = "turnover_fumble"
    TURNOVER_INTERCEPTION = "turnover_interception"
    TURNOVER_ON_DOWNS = "turnover_on_downs"
    PUNT = "punt"
    KICKOFF = "kickoff"
    SAFETY_KICK = "safety_kick"
    ONSIDE_KICK_RECOVERED = "onside_kick_recovered"
    BLOCKED_PUNT_RECOVERED = "blocked_punt_recovered"
    BLOCKED_FIELD_GOAL_RECOVERED = "blocked_field_goal_recovered"
    MUFFED_PUNT_RECOVERED = "muffed_punt_recovered"
    MUFFED_KICKOFF_RECOVERED = "muffed_kickoff_recovered"
    TOUCHDOWN_SCORED = "touchdown_scored"
    FIELD_GOAL_SCORED = "field_goal_scored"
    HALF_TIME = "half_time"
    GAME_START = "game_start"
    OVERTIME_START = "overtime_start"


class TurnoverType(Enum):
    """Enumeration of turnover types."""
    FUMBLE_LOST = "fumble_lost"
    INTERCEPTION = "interception"
    ON_DOWNS = "on_downs"
    MUFFED_PUNT = "muffed_punt"
    MUFFED_KICKOFF = "muffed_kickoff"
    BLOCKED_PUNT = "blocked_punt"
    BLOCKED_FIELD_GOAL = "blocked_field_goal"


@dataclass(frozen=True)
class PossessionTransition:
    """
    Immutable representation of possession changes between teams.
    
    This object contains all the information about how and why possession
    changed hands, including turnover details and special situations.
    
    Attributes:
        # Basic Possession Information
        possession_changes: Whether possession actually changes hands
        new_possessing_team: ID/name of team that will have possession
        old_possessing_team: ID/name of team that previously had possession
        
        # Turnover Information
        turnover_occurred: Whether this represents a turnover
        turnover_type: Type of turnover if applicable
        turnover_location: Field position where turnover occurred
        
        # Change Reason
        possession_change_reason: Why possession changed
        forced_turnover: Whether turnover was forced by defense (vs. unforced error)
        
        # Player Information
        turnover_caused_by_player: Player who caused the turnover (defensive)
        turnover_committed_by_player: Player who committed the turnover (offensive)
        recovering_player: Player who recovered the loose ball (if applicable)
        
        # Special Situations
        onside_kick_attempt: Whether this was an onside kick attempt
        onside_kick_successful: Whether onside kick was recovered by kicking team
        fair_catch_made: Whether a fair catch was made on the play
        touchback_occurred: Whether a touchback occurred
        
        # Possession Timing
        possession_time_started: Game time when new possession starts
        previous_possession_duration: How long previous team had possession
        
        # Down and Distance Reset
        resets_down_and_distance: Whether new possession gets fresh down/distance
        new_down_after_change: What down the new possessing team gets
        new_yards_to_go_after_change: Yards to go for new possessing team
        
        # Special Teams Involvement
        special_teams_involved: Whether special teams units were involved
        return_occurred: Whether there was a return (kickoff/punt)
        return_yards: Yards gained on return (if applicable)
        return_touchdown: Whether return resulted in touchdown
        
        # Game Impact
        momentum_shift: Whether this represents a significant momentum shift
        game_changing_play: Whether this play significantly impacts game outcome
        red_zone_turnover: Whether turnover occurred in red zone
        goal_line_turnover: Whether turnover occurred at goal line
    """
    
    # Basic Possession Information
    possession_changes: bool
    new_possessing_team: Optional[str] = None
    old_possessing_team: Optional[str] = None
    
    # Turnover Information
    turnover_occurred: bool = False
    turnover_type: Optional[TurnoverType] = None
    turnover_location: Optional[int] = None
    
    # Change Reason
    possession_change_reason: Optional[PossessionChangeReason] = None
    forced_turnover: bool = False
    
    # Player Information
    turnover_caused_by_player: Optional[str] = None
    turnover_committed_by_player: Optional[str] = None
    recovering_player: Optional[str] = None
    
    # Special Situations
    onside_kick_attempt: bool = False
    onside_kick_successful: bool = False
    fair_catch_made: bool = False
    touchback_occurred: bool = False
    
    # Possession Timing
    possession_time_started: Optional[str] = None
    previous_possession_duration: Optional[str] = None
    
    # Down and Distance Reset
    resets_down_and_distance: bool = False
    new_down_after_change: int = 1
    new_yards_to_go_after_change: int = 10
    
    # Special Teams Involvement
    special_teams_involved: bool = False
    return_occurred: bool = False
    return_yards: int = 0
    return_touchdown: bool = False
    
    # Game Impact
    momentum_shift: bool = False
    game_changing_play: bool = False
    red_zone_turnover: bool = False
    goal_line_turnover: bool = False
    
    def __post_init__(self):
        """Validate possession change data and set derived fields."""
        # If possession changes, we should have team information
        if self.possession_changes and (not self.new_possessing_team or not self.old_possessing_team):
            raise ValueError("If possession changes, both new and old possessing teams must be specified")
        
        # If it's a turnover, possession must change
        if self.turnover_occurred and not self.possession_changes:
            raise ValueError("Turnovers must result in possession changes")
        
        # If it's a turnover, we should have a turnover type
        if self.turnover_occurred and not self.turnover_type:
            raise ValueError("Turnovers must have a turnover type specified")
        
        # Set derived fields
        if self.turnover_location is not None:
            object.__setattr__(self, 'red_zone_turnover', self.turnover_location <= 20)
            object.__setattr__(self, 'goal_line_turnover', self.turnover_location <= 5)
        
        # Set momentum shift flag for significant plays
        if (self.turnover_occurred or self.return_touchdown or 
            self.red_zone_turnover or self.onside_kick_successful):
            object.__setattr__(self, 'momentum_shift', True)
        
        # Set game changing play flag
        if (self.return_touchdown or self.goal_line_turnover or 
            self.onside_kick_successful):
            object.__setattr__(self, 'game_changing_play', True)
    
    def is_defensive_turnover(self) -> bool:
        """Return True if this is a turnover caused by the defense."""
        defensive_turnovers = {
            TurnoverType.INTERCEPTION,
            TurnoverType.FUMBLE_LOST,
            TurnoverType.BLOCKED_PUNT,
            TurnoverType.BLOCKED_FIELD_GOAL
        }
        return self.turnover_type in defensive_turnovers
    
    def is_offensive_turnover(self) -> bool:
        """Return True if this is a turnover caused by offensive mistake."""
        offensive_turnovers = {
            TurnoverType.ON_DOWNS,
            TurnoverType.MUFFED_PUNT,
            TurnoverType.MUFFED_KICKOFF
        }
        return self.turnover_type in offensive_turnovers
    
    def is_special_teams_turnover(self) -> bool:
        """Return True if this turnover occurred during special teams play."""
        special_teams_turnovers = {
            TurnoverType.MUFFED_PUNT,
            TurnoverType.MUFFED_KICKOFF,
            TurnoverType.BLOCKED_PUNT,
            TurnoverType.BLOCKED_FIELD_GOAL
        }
        return self.turnover_type in special_teams_turnovers
    
    def requires_new_drive_stats(self) -> bool:
        """Return True if this possession change starts a new drive."""
        return self.possession_changes and self.resets_down_and_distance
    
    def get_possession_change_description(self) -> str:
        """Return a human-readable description of the possession change."""
        if not self.possession_changes:
            return "No possession change"
        
        if self.turnover_occurred:
            turnover_desc = self.turnover_type.value.replace('_', ' ').title()
            if self.turnover_location is not None:
                return f"{turnover_desc} at {self.turnover_location} yard line"
            return turnover_desc
        
        if self.possession_change_reason:
            return self.possession_change_reason.value.replace('_', ' ').title()
        
        return "Possession change"
    
    def get_turnover_summary(self) -> str:
        """Return a summary of turnover details if applicable."""
        if not self.turnover_occurred:
            return "No turnover"
        
        parts = [self.turnover_type.value.replace('_', ' ').title()]
        
        if self.turnover_caused_by_player:
            parts.append(f"forced by {self.turnover_caused_by_player}")
        
        if self.turnover_committed_by_player:
            parts.append(f"by {self.turnover_committed_by_player}")
        
        if self.recovering_player:
            parts.append(f"recovered by {self.recovering_player}")
        
        if self.turnover_location is not None:
            parts.append(f"at {self.turnover_location} yard line")
        
        return " - ".join(parts)
    
    def get_special_teams_summary(self) -> str:
        """Return a summary of special teams involvement."""
        if not self.special_teams_involved:
            return "No special teams involvement"
        
        parts = []
        
        if self.onside_kick_attempt:
            result = "successful" if self.onside_kick_successful else "failed"
            parts.append(f"Onside kick - {result}")
        
        if self.return_occurred:
            if self.return_touchdown:
                parts.append(f"Return TD - {self.return_yards} yards")
            else:
                parts.append(f"Return - {self.return_yards} yards")
        
        if self.fair_catch_made:
            parts.append("Fair catch")
        
        if self.touchback_occurred:
            parts.append("Touchback")
        
        return " | ".join(parts) if parts else "Special teams involved"
    
    def get_summary(self) -> str:
        """Return a complete summary of this possession transition."""
        if not self.possession_changes:
            return "No possession change"
        
        summary = f"{self.old_possessing_team} → {self.new_possessing_team}"
        
        if self.turnover_occurred:
            summary += f" ({self.get_turnover_summary()})"
        elif self.possession_change_reason:
            summary += f" ({self.possession_change_reason.value.replace('_', ' ')})"
        
        if self.momentum_shift:
            summary += " [MOMENTUM SHIFT]"
        
        if self.game_changing_play:
            summary += " [GAME CHANGER]"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this possession transition to a dictionary."""
        return {
            'basic_info': {
                'possession_changes': self.possession_changes,
                'new_possessing_team': self.new_possessing_team,
                'old_possessing_team': self.old_possessing_team,
                'possession_change_reason': self.possession_change_reason.value if self.possession_change_reason else None
            },
            'turnover_info': {
                'turnover_occurred': self.turnover_occurred,
                'turnover_type': self.turnover_type.value if self.turnover_type else None,
                'turnover_location': self.turnover_location,
                'forced_turnover': self.forced_turnover,
                'is_defensive_turnover': self.is_defensive_turnover(),
                'is_offensive_turnover': self.is_offensive_turnover(),
                'is_special_teams_turnover': self.is_special_teams_turnover()
            },
            'players': {
                'turnover_caused_by_player': self.turnover_caused_by_player,
                'turnover_committed_by_player': self.turnover_committed_by_player,
                'recovering_player': self.recovering_player
            },
            'special_situations': {
                'onside_kick_attempt': self.onside_kick_attempt,
                'onside_kick_successful': self.onside_kick_successful,
                'fair_catch_made': self.fair_catch_made,
                'touchback_occurred': self.touchback_occurred,
                'special_teams_involved': self.special_teams_involved
            },
            'return_info': {
                'return_occurred': self.return_occurred,
                'return_yards': self.return_yards,
                'return_touchdown': self.return_touchdown
            },
            'game_impact': {
                'momentum_shift': self.momentum_shift,
                'game_changing_play': self.game_changing_play,
                'red_zone_turnover': self.red_zone_turnover,
                'goal_line_turnover': self.goal_line_turnover
            },
            'down_distance': {
                'resets_down_and_distance': self.resets_down_and_distance,
                'new_down_after_change': self.new_down_after_change,
                'new_yards_to_go_after_change': self.new_yards_to_go_after_change
            },
            'summaries': {
                'possession_change_description': self.get_possession_change_description(),
                'turnover_summary': self.get_turnover_summary(),
                'special_teams_summary': self.get_special_teams_summary(),
                'overall_summary': self.get_summary()
            }
        }