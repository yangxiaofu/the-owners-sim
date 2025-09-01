"""
SpecialSituationTransition - Kickoffs, Punts, Turnovers, and Complex Scenarios

This data structure represents complex game situations that involve multiple
state changes, special teams plays, and unusual scenarios. It handles situations
that don't fit cleanly into basic field/possession/score/clock categories.

Key responsibilities:
- Handle kickoff scenarios and returns
- Manage punt situations and returns  
- Track complex turnover scenarios
- Handle blocked kicks and recoveries
- Manage onside kicks and surprise plays
- Track penalty situations affecting multiple game states
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum


class SpecialSituationType(Enum):
    """Types of special situations that can occur."""
    KICKOFF = "kickoff"
    PUNT = "punt"
    FIELD_GOAL_ATTEMPT = "field_goal_attempt"
    EXTRA_POINT_ATTEMPT = "extra_point_attempt"
    TWO_POINT_ATTEMPT = "two_point_attempt"
    ONSIDE_KICK = "onside_kick"
    SQUIB_KICK = "squib_kick"
    SAFETY_KICK = "safety_kick"
    BLOCKED_KICK = "blocked_kick"
    FAKE_PUNT = "fake_punt"
    FAKE_FIELD_GOAL = "fake_field_goal"
    MUFFED_PUNT = "muffed_punt"
    MUFFED_KICKOFF = "muffed_kickoff"
    PENALTY_ENFORCEMENT = "penalty_enforcement"
    MULTIPLE_PENALTIES = "multiple_penalties"
    FUMBLE_RECOVERY = "fumble_recovery"
    INTERCEPTION = "interception"
    BLOCKED_PUNT = "blocked_punt"
    COFFIN_CORNER_PUNT = "coffin_corner_punt"
    TOUCHBACK = "touchback"
    FAIR_CATCH = "fair_catch"


class KickType(Enum):
    """Types of kicking plays."""
    NORMAL_KICKOFF = "normal_kickoff"
    ONSIDE_KICK = "onside_kick"
    SQUIB_KICK = "squib_kick"
    POOCH_KICK = "pooch_kick"
    REGULAR_PUNT = "regular_punt"
    COFFIN_CORNER_PUNT = "coffin_corner_punt"
    FIELD_GOAL = "field_goal"
    EXTRA_POINT = "extra_point"
    SAFETY_KICK = "safety_kick"


class ReturnType(Enum):
    """Types of return plays."""
    KICKOFF_RETURN = "kickoff_return"
    PUNT_RETURN = "punt_return"
    BLOCKED_KICK_RETURN = "blocked_kick_return"
    FUMBLE_RETURN = "fumble_return"
    INTERCEPTION_RETURN = "interception_return"
    NO_RETURN = "no_return"  # Fair catch, touchback, etc.


@dataclass(frozen=True)
class SpecialSituationTransition:
    """
    Immutable representation of complex special situation changes.
    
    This object handles complex scenarios that involve multiple types of
    state changes and special teams plays.
    
    Attributes:
        # Basic Situation Information
        situation_type: Type of special situation
        situation_occurred: Whether the special situation actually happened
        situation_description: Human-readable description of what occurred
        
        # Kicking Information
        kick_attempted: Whether a kick was attempted
        kick_type: Type of kick attempted
        kicker: Player who attempted the kick
        kick_distance: Distance of the kick
        kick_successful: Whether the kick was successful
        kick_blocked: Whether the kick was blocked
        blocking_player: Player who blocked the kick (if applicable)
        
        # Return Information
        return_attempted: Whether a return was attempted
        return_type: Type of return
        returner: Player who returned the kick/ball
        return_distance: Distance of the return
        return_touchback: Whether return resulted in touchback
        fair_catch: Whether fair catch was called
        
        # Recovery Information
        ball_recovered: Whether loose ball was recovered
        recovering_team: Team that recovered the ball
        recovering_player: Player who recovered the ball
        recovery_location: Field position where ball was recovered
        
        # Penalty Information
        penalties_occurred: Whether penalties were assessed
        penalty_types: List of penalty types that occurred
        penalty_yards: Total yards from penalties
        penalty_automatic_first_down: Whether penalty gave automatic first down
        offsetting_penalties: Whether penalties offset each other
        
        # Multiple Scenario Handling
        multiple_events: Whether multiple events occurred on same play
        event_sequence: Ordered list of events that occurred
        primary_event: The most significant event of the play
        secondary_events: List of secondary events
        
        # Field Position Impact
        net_field_position_change: Net change in field position
        starting_field_position: Where the play started
        ending_field_position: Where the play ended
        crossed_midfield: Whether play crossed midfield
        
        # Game State Complexity
        possession_unclear: Whether possession is temporarily unclear
        requires_official_review: Whether play requires official review
        measurement_needed: Whether measurement is needed
        down_by_contact: Whether player was down by contact
        
        # Special Teams Units
        special_teams_on_field: Whether special teams units were involved  
        punt_team_on_field: Whether punt team was on field
        kickoff_team_on_field: Whether kickoff team was on field
        field_goal_team_on_field: Whether field goal team was on field
        
        # Timing Impact
        clock_impact: How this situation affects the game clock
        timeout_charged: Whether situation caused timeout to be charged
        delay_of_game: Whether delay of game occurred
        
        # Coaching Decisions
        fake_play_attempted: Whether a fake play was attempted
        surprise_play: Whether this was an unexpected play call
        strategic_decision: Description of strategic decision made
        risk_level: Risk level of the play call (low/medium/high)
        
        # Weather/Field Conditions Impact
        weather_impact: Whether weather affected the play
        field_conditions_impact: Whether field conditions were a factor
        wind_impact: Whether wind was a significant factor
        
        # Statistical Impact
        turnover_margin_impact: How this affects turnover margin
        field_position_battle: Impact on field position battle
        momentum_shift_magnitude: Magnitude of momentum shift (none/small/large)
        
        # Follow-up Actions Required
        requires_kickoff: Whether a kickoff is needed after this
        requires_punt: Whether a punt is needed
        requires_field_goal_attempt: Whether field goal attempt follows
        requires_safety_kick: Whether safety kick is needed
        requires_penalty_enforcement: Whether penalties need to be enforced
        
        # Replay and Review
        reviewable_play: Whether play is subject to replay review
        challenge_possible: Whether play can be challenged
        automatic_review: Whether play is automatically reviewed
        review_outcome: Outcome of review if conducted
    """
    
    # Basic Situation Information
    situation_type: SpecialSituationType
    situation_occurred: bool = True
    situation_description: str = ""
    
    # Kicking Information  
    kick_attempted: bool = False
    kick_type: Optional[KickType] = None
    kicker: Optional[str] = None
    kick_distance: int = 0
    kick_successful: bool = False
    kick_blocked: bool = False
    blocking_player: Optional[str] = None
    
    # Return Information
    return_attempted: bool = False
    return_type: Optional[ReturnType] = None
    returner: Optional[str] = None
    return_distance: int = 0
    return_touchback: bool = False
    fair_catch: bool = False
    
    # Recovery Information
    ball_recovered: bool = False
    recovering_team: Optional[str] = None
    recovering_player: Optional[str] = None
    recovery_location: Optional[int] = None
    
    # Penalty Information
    penalties_occurred: bool = False
    penalty_types: List[str] = None
    penalty_yards: int = 0
    penalty_automatic_first_down: bool = False
    offsetting_penalties: bool = False
    
    # Multiple Scenario Handling
    multiple_events: bool = False
    event_sequence: List[str] = None
    primary_event: Optional[str] = None
    secondary_events: List[str] = None
    
    # Field Position Impact
    net_field_position_change: int = 0
    starting_field_position: Optional[int] = None
    ending_field_position: Optional[int] = None
    crossed_midfield: bool = False
    
    # Game State Complexity
    possession_unclear: bool = False
    requires_official_review: bool = False
    measurement_needed: bool = False
    down_by_contact: bool = False
    
    # Special Teams Units
    special_teams_on_field: bool = False
    punt_team_on_field: bool = False
    kickoff_team_on_field: bool = False
    field_goal_team_on_field: bool = False
    
    # Timing Impact
    clock_impact: Optional[str] = None
    timeout_charged: bool = False
    delay_of_game: bool = False
    
    # Coaching Decisions
    fake_play_attempted: bool = False
    surprise_play: bool = False
    strategic_decision: Optional[str] = None
    risk_level: str = "low"  # low, medium, high
    
    # Weather/Field Conditions Impact
    weather_impact: bool = False
    field_conditions_impact: bool = False
    wind_impact: bool = False
    
    # Statistical Impact
    turnover_margin_impact: int = 0
    field_position_battle: Optional[str] = None
    momentum_shift_magnitude: str = "none"  # none, small, large
    
    # Follow-up Actions Required
    requires_kickoff: bool = False
    requires_punt: bool = False
    requires_field_goal_attempt: bool = False
    requires_safety_kick: bool = False
    requires_penalty_enforcement: bool = False
    
    # Replay and Review
    reviewable_play: bool = False
    challenge_possible: bool = False
    automatic_review: bool = False
    review_outcome: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default empty collections and validate data."""
        if self.penalty_types is None:
            object.__setattr__(self, 'penalty_types', [])
        if self.event_sequence is None:
            object.__setattr__(self, 'event_sequence', [])
        if self.secondary_events is None:
            object.__setattr__(self, 'secondary_events', [])
        
        # Set derived flags based on situation type
        if self.situation_type in [SpecialSituationType.KICKOFF, SpecialSituationType.ONSIDE_KICK, 
                                 SpecialSituationType.SQUIB_KICK, SpecialSituationType.SAFETY_KICK]:
            object.__setattr__(self, 'kickoff_team_on_field', True)
            object.__setattr__(self, 'special_teams_on_field', True)
        
        if self.situation_type in [SpecialSituationType.PUNT, SpecialSituationType.BLOCKED_PUNT,
                                 SpecialSituationType.FAKE_PUNT]:
            object.__setattr__(self, 'punt_team_on_field', True)
            object.__setattr__(self, 'special_teams_on_field', True)
        
        if self.situation_type in [SpecialSituationType.FIELD_GOAL_ATTEMPT, SpecialSituationType.EXTRA_POINT_ATTEMPT,
                                 SpecialSituationType.FAKE_FIELD_GOAL]:
            object.__setattr__(self, 'field_goal_team_on_field', True)
            object.__setattr__(self, 'special_teams_on_field', True)
        
        # Set strategic decision flags
        if self.fake_play_attempted or self.situation_type in [SpecialSituationType.ONSIDE_KICK,
                                                             SpecialSituationType.FAKE_PUNT]:
            object.__setattr__(self, 'surprise_play', True)
            object.__setattr__(self, 'risk_level', 'high')
    
    def is_scoring_opportunity(self) -> bool:
        """Return True if this situation could result in points."""
        scoring_situations = {
            SpecialSituationType.FIELD_GOAL_ATTEMPT,
            SpecialSituationType.EXTRA_POINT_ATTEMPT,
            SpecialSituationType.TWO_POINT_ATTEMPT,
            SpecialSituationType.BLOCKED_KICK  # Could be returned for TD
        }
        return self.situation_type in scoring_situations
    
    def is_change_of_possession_play(self) -> bool:
        """Return True if this play typically changes possession."""
        possession_change_situations = {
            SpecialSituationType.KICKOFF,
            SpecialSituationType.PUNT,
            SpecialSituationType.ONSIDE_KICK,
            SpecialSituationType.SAFETY_KICK,
            SpecialSituationType.FUMBLE_RECOVERY,
            SpecialSituationType.INTERCEPTION
        }
        return self.situation_type in possession_change_situations
    
    def has_return_potential(self) -> bool:
        """Return True if this situation allows for a return."""
        return_situations = {
            SpecialSituationType.KICKOFF,
            SpecialSituationType.PUNT,
            SpecialSituationType.BLOCKED_KICK,
            SpecialSituationType.BLOCKED_PUNT
        }
        return self.situation_type in return_situations
    
    def is_high_risk_play(self) -> bool:
        """Return True if this is a high-risk play call."""
        return (self.risk_level == "high" or self.fake_play_attempted or 
                self.surprise_play or self.situation_type == SpecialSituationType.ONSIDE_KICK)
    
    def get_situation_summary(self) -> str:
        """Return a summary of the special situation."""
        if self.situation_description:
            return self.situation_description
        
        # Generate description based on situation type
        descriptions = {
            SpecialSituationType.KICKOFF: "Kickoff",
            SpecialSituationType.PUNT: "Punt",
            SpecialSituationType.ONSIDE_KICK: "Onside kick",
            SpecialSituationType.FIELD_GOAL_ATTEMPT: f"Field goal attempt ({self.kick_distance} yards)",
            SpecialSituationType.BLOCKED_KICK: "Blocked kick",
            SpecialSituationType.FAKE_PUNT: "Fake punt",
            SpecialSituationType.MUFFED_PUNT: "Muffed punt"
        }
        
        return descriptions.get(self.situation_type, self.situation_type.value.replace('_', ' ').title())
    
    def get_kick_summary(self) -> str:
        """Return summary of kicking play if applicable."""
        if not self.kick_attempted:
            return "No kick attempted"
        
        parts = []
        
        if self.kick_type:
            parts.append(self.kick_type.value.replace('_', ' ').title())
        
        if self.kick_distance > 0:
            parts.append(f"{self.kick_distance} yards")
        
        if self.kicker:
            parts.append(f"by {self.kicker}")
        
        if self.kick_blocked:
            parts.append("BLOCKED")
            if self.blocking_player:
                parts.append(f"by {self.blocking_player}")
        elif self.kick_successful:
            parts.append("GOOD")
        else:
            parts.append("MISSED")
        
        return " - ".join(parts)
    
    def get_return_summary(self) -> str:
        """Return summary of return play if applicable."""
        if not self.return_attempted:
            if self.fair_catch:
                return "Fair catch"
            elif self.return_touchback:
                return "Touchback"
            return "No return"
        
        parts = []
        
        if self.returner:
            parts.append(f"{self.returner}")
        
        if self.return_distance > 0:
            parts.append(f"{self.return_distance} yard return")
        else:
            parts.append("No gain on return")
        
        if self.return_type:
            parts.insert(0, self.return_type.value.replace('_', ' ').title())
        
        return " - ".join(parts)
    
    def get_penalty_summary(self) -> str:
        """Return summary of penalties if applicable."""
        if not self.penalties_occurred:
            return "No penalties"
        
        if self.offsetting_penalties:
            return "Offsetting penalties"
        
        parts = []
        
        if self.penalty_types:
            parts.extend(self.penalty_types)
        
        if self.penalty_yards != 0:
            if self.penalty_yards > 0:
                parts.append(f"{self.penalty_yards} yards")
            else:
                parts.append(f"Loss of {abs(self.penalty_yards)} yards")
        
        if self.penalty_automatic_first_down:
            parts.append("Automatic first down")
        
        return " - ".join(parts)
    
    def get_complexity_description(self) -> str:
        """Return description of play complexity."""
        complexity_factors = []
        
        if self.multiple_events:
            complexity_factors.append("Multiple events")
        
        if self.requires_official_review:
            complexity_factors.append("Under review")
        
        if self.possession_unclear:
            complexity_factors.append("Unclear possession")
        
        if self.penalties_occurred:
            complexity_factors.append("Penalties involved")
        
        if self.weather_impact or self.field_conditions_impact:
            complexity_factors.append("Conditions factor")
        
        return " | ".join(complexity_factors) if complexity_factors else "Standard play"
    
    def get_follow_up_requirements(self) -> List[str]:
        """Return list of required follow-up actions."""
        requirements = []
        
        if self.requires_kickoff:
            requirements.append("Kickoff required")
        
        if self.requires_punt:
            requirements.append("Punt required")
        
        if self.requires_field_goal_attempt:
            requirements.append("Field goal attempt")
        
        if self.requires_safety_kick:
            requirements.append("Safety kick required")
        
        if self.requires_penalty_enforcement:
            requirements.append("Enforce penalties")
        
        if self.measurement_needed:
            requirements.append("Measurement needed")
        
        return requirements
    
    def get_summary(self) -> str:
        """Return a complete summary of this special situation."""
        parts = [self.get_situation_summary()]
        
        if self.kick_attempted:
            kick_summary = self.get_kick_summary()
            if kick_summary != "No kick attempted":
                parts.append(kick_summary)
        
        if self.return_attempted or self.fair_catch or self.return_touchback:
            return_summary = self.get_return_summary()
            if return_summary != "No return":
                parts.append(return_summary)
        
        if self.penalties_occurred:
            penalty_summary = self.get_penalty_summary()
            if penalty_summary != "No penalties":
                parts.append(f"Penalty: {penalty_summary}")
        
        # Add follow-up requirements
        requirements = self.get_follow_up_requirements()
        if requirements:
            parts.append(f"Next: {', '.join(requirements)}")
        
        return " | ".join(parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this special situation transition to a dictionary."""
        return {
            'situation_info': {
                'situation_type': self.situation_type.value,
                'situation_occurred': self.situation_occurred,
                'situation_description': self.situation_description,
                'situation_summary': self.get_situation_summary()
            },
            'kick_info': {
                'kick_attempted': self.kick_attempted,
                'kick_type': self.kick_type.value if self.kick_type else None,
                'kicker': self.kicker,
                'kick_distance': self.kick_distance,
                'kick_successful': self.kick_successful,
                'kick_blocked': self.kick_blocked,
                'blocking_player': self.blocking_player,
                'kick_summary': self.get_kick_summary()
            },
            'return_info': {
                'return_attempted': self.return_attempted,
                'return_type': self.return_type.value if self.return_type else None,
                'returner': self.returner,
                'return_distance': self.return_distance,
                'return_touchback': self.return_touchback,
                'fair_catch': self.fair_catch,
                'return_summary': self.get_return_summary()
            },
            'recovery_info': {
                'ball_recovered': self.ball_recovered,
                'recovering_team': self.recovering_team,
                'recovering_player': self.recovering_player,
                'recovery_location': self.recovery_location
            },
            'penalty_info': {
                'penalties_occurred': self.penalties_occurred,
                'penalty_types': list(self.penalty_types),
                'penalty_yards': self.penalty_yards,
                'penalty_automatic_first_down': self.penalty_automatic_first_down,
                'offsetting_penalties': self.offsetting_penalties,
                'penalty_summary': self.get_penalty_summary()
            },
            'complexity': {
                'multiple_events': self.multiple_events,
                'event_sequence': list(self.event_sequence),
                'primary_event': self.primary_event,
                'secondary_events': list(self.secondary_events),
                'complexity_description': self.get_complexity_description()
            },
            'field_position': {
                'net_field_position_change': self.net_field_position_change,
                'starting_field_position': self.starting_field_position,
                'ending_field_position': self.ending_field_position,
                'crossed_midfield': self.crossed_midfield
            },
            'special_teams': {
                'special_teams_on_field': self.special_teams_on_field,
                'punt_team_on_field': self.punt_team_on_field,
                'kickoff_team_on_field': self.kickoff_team_on_field,
                'field_goal_team_on_field': self.field_goal_team_on_field
            },
            'coaching_strategy': {
                'fake_play_attempted': self.fake_play_attempted,
                'surprise_play': self.surprise_play,
                'strategic_decision': self.strategic_decision,
                'risk_level': self.risk_level,
                'is_high_risk_play': self.is_high_risk_play()
            },
            'game_impact': {
                'turnover_margin_impact': self.turnover_margin_impact,
                'field_position_battle': self.field_position_battle,
                'momentum_shift_magnitude': self.momentum_shift_magnitude,
                'is_scoring_opportunity': self.is_scoring_opportunity(),
                'is_change_of_possession_play': self.is_change_of_possession_play()
            },
            'follow_up': {
                'requires_kickoff': self.requires_kickoff,
                'requires_punt': self.requires_punt,
                'requires_field_goal_attempt': self.requires_field_goal_attempt,
                'requires_safety_kick': self.requires_safety_kick,
                'requires_penalty_enforcement': self.requires_penalty_enforcement,
                'follow_up_requirements': self.get_follow_up_requirements()
            },
            'review_replay': {
                'reviewable_play': self.reviewable_play,
                'challenge_possible': self.challenge_possible,
                'automatic_review': self.automatic_review,
                'review_outcome': self.review_outcome,
                'requires_official_review': self.requires_official_review
            },
            'summary': self.get_summary()
        }