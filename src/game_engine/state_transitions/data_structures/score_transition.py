"""
ScoreTransition - Score and Touchdown Logic

This data structure represents all scoring plays and score changes in the game.
It handles touchdowns, field goals, safeties, extra points, two-point conversions,
and all related scoring scenarios.

Key responsibilities:
- Track all types of scoring plays
- Manage point values and score updates
- Handle extra point and conversion attempts
- Track scoring player and team information
- Determine if kickoff is required after scoring
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ScoreType(Enum):
    """Enumeration of different types of scoring plays."""
    TOUCHDOWN = "touchdown"
    FIELD_GOAL = "field_goal"
    SAFETY = "safety"
    EXTRA_POINT = "extra_point"
    TWO_POINT_CONVERSION = "two_point_conversion"
    DEFENSIVE_TWO_POINT = "defensive_two_point"  # Defense returns conversion attempt
    PICK_SIX = "pick_six"  # Interception return for TD
    FUMBLE_RECOVERY_TD = "fumble_recovery_td"  # Fumble recovery for TD
    BLOCKED_PUNT_TD = "blocked_punt_td"  # Blocked punt return for TD
    PUNT_RETURN_TD = "punt_return_td"  # Punt return for TD
    KICKOFF_RETURN_TD = "kickoff_return_td"  # Kickoff return for TD
    BLOCKED_FIELD_GOAL_TD = "blocked_field_goal_td"  # Blocked FG return for TD


class ConversionType(Enum):
    """Type of conversion attempt after touchdown."""
    EXTRA_POINT_KICK = "extra_point_kick"
    TWO_POINT_ATTEMPT = "two_point_attempt"
    NO_ATTEMPT = "no_attempt"  # Game ending scenario, etc.


@dataclass(frozen=True)
class ScoreTransition:
    """
    Immutable representation of scoring plays and score changes.
    
    This object contains all the information about scoring plays,
    including the type of score, points awarded, and post-scoring procedures.
    
    Attributes:
        # Basic Scoring Information
        score_occurred: Whether any scoring took place
        score_type: Type of scoring play
        points_scored: Total points awarded on this play
        scoring_team: Team that scored the points
        
        # Score Updates
        new_home_score: New score for home team
        new_away_score: New score for away team  
        old_home_score: Previous score for home team
        old_away_score: Previous score for away team
        
        # Touchdown Specific
        touchdown_scored: Whether a touchdown was scored
        touchdown_type: Type of touchdown (rushing, passing, return, etc.)
        touchdown_distance: Distance of the scoring play in yards
        touchdown_player: Player who scored the touchdown
        touchdown_time: Game time when touchdown was scored
        
        # Field Goal Specific
        field_goal_scored: Whether a field goal was made
        field_goal_distance: Distance of field goal attempt
        field_goal_kicker: Player who kicked the field goal
        field_goal_blocked: Whether field goal was blocked
        field_goal_missed: Whether field goal was missed (vs. blocked)
        
        # Safety Specific
        safety_scored: Whether a safety was scored
        safety_type: Type of safety (sack, holding, intentional grounding, etc.)
        safety_player: Player who was credited with the safety
        
        # Extra Point/Conversion
        conversion_attempt: Whether there will be a conversion attempt
        conversion_type: Type of conversion (kick or two-point)
        conversion_successful: Whether conversion was successful
        conversion_points: Points from conversion (1 or 2)
        conversion_player: Player who executed the conversion
        
        # Defensive Scoring
        defensive_score: Whether defense/special teams scored
        return_touchdown: Whether this was a return for touchdown
        return_distance: Distance of scoring return
        pick_six: Whether this was an interception return for TD
        fumble_return_td: Whether this was a fumble return for TD
        
        # Game Impact
        go_ahead_score: Whether this score puts team ahead
        game_tying_score: Whether this score ties the game
        game_winning_score: Whether this is the game-winning score
        red_zone_score: Whether score came from red zone
        goal_line_score: Whether score came from goal line
        
        # Post-Scoring Procedures
        requires_kickoff: Whether a kickoff is required after this score
        requires_conversion: Whether conversion attempt is needed
        requires_safety_kick: Whether a safety kick is required
        
        # Special Situations
        pick_two: Whether defense scored on conversion return
        onside_kick_likely: Whether team is likely to attempt onside kick
        celebration_penalty: Whether excessive celebration penalty occurred
        
        # Timing and Context
        quarter_scored: Quarter in which score occurred
        time_remaining: Time remaining when score occurred
        score_margin_before: Point margin before this score
        score_margin_after: Point margin after this score
    """
    
    # Basic Scoring Information
    score_occurred: bool
    score_type: Optional[ScoreType] = None
    points_scored: int = 0
    scoring_team: Optional[str] = None
    
    # Score Updates
    new_home_score: int = 0
    new_away_score: int = 0
    old_home_score: int = 0
    old_away_score: int = 0
    
    # Touchdown Specific
    touchdown_scored: bool = False
    touchdown_type: Optional[str] = None
    touchdown_distance: int = 0
    touchdown_player: Optional[str] = None
    touchdown_time: Optional[str] = None
    
    # Field Goal Specific
    field_goal_scored: bool = False
    field_goal_distance: int = 0
    field_goal_kicker: Optional[str] = None
    field_goal_blocked: bool = False
    field_goal_missed: bool = False
    
    # Safety Specific
    safety_scored: bool = False
    safety_type: Optional[str] = None
    safety_player: Optional[str] = None
    
    # Extra Point/Conversion
    conversion_attempt: bool = False
    conversion_type: Optional[ConversionType] = None
    conversion_successful: bool = False
    conversion_points: int = 0
    conversion_player: Optional[str] = None
    
    # Defensive Scoring
    defensive_score: bool = False
    return_touchdown: bool = False
    return_distance: int = 0
    pick_six: bool = False
    fumble_return_td: bool = False
    
    # Game Impact
    go_ahead_score: bool = False
    game_tying_score: bool = False
    game_winning_score: bool = False
    red_zone_score: bool = False
    goal_line_score: bool = False
    
    # Post-Scoring Procedures
    requires_kickoff: bool = False
    requires_conversion: bool = False
    requires_safety_kick: bool = False
    
    # Special Situations
    pick_two: bool = False
    onside_kick_likely: bool = False
    celebration_penalty: bool = False
    
    # Timing and Context
    quarter_scored: Optional[int] = None
    time_remaining: Optional[str] = None
    score_margin_before: int = 0
    score_margin_after: int = 0
    
    def __post_init__(self):
        """Validate scoring data and calculate derived fields."""
        # If score occurred, we should have basic information
        if self.score_occurred:
            if not self.scoring_team:
                raise ValueError("Scoring plays must specify the scoring team")
            if self.points_scored <= 0:
                raise ValueError("Scoring plays must award positive points")
            if not self.score_type:
                raise ValueError("Scoring plays must specify the score type")
        
        # Set score-specific flags based on score type
        if self.score_type:
            if self.score_type in [ScoreType.TOUCHDOWN, ScoreType.PICK_SIX, 
                                 ScoreType.FUMBLE_RECOVERY_TD, ScoreType.PUNT_RETURN_TD,
                                 ScoreType.KICKOFF_RETURN_TD, ScoreType.BLOCKED_PUNT_TD]:
                object.__setattr__(self, 'touchdown_scored', True)
                if self.touchdown_distance <= 1:
                    object.__setattr__(self, 'goal_line_score', True)
                elif self.touchdown_distance <= 20:
                    object.__setattr__(self, 'red_zone_score', True)
            
            if self.score_type == ScoreType.FIELD_GOAL:
                object.__setattr__(self, 'field_goal_scored', True)
            
            if self.score_type == ScoreType.SAFETY:
                object.__setattr__(self, 'safety_scored', True)
            
            # Set return touchdown flags
            if self.score_type in [ScoreType.PICK_SIX, ScoreType.FUMBLE_RECOVERY_TD,
                                 ScoreType.PUNT_RETURN_TD, ScoreType.KICKOFF_RETURN_TD]:
                object.__setattr__(self, 'return_touchdown', True)
                object.__setattr__(self, 'defensive_score', True)
        
        # Calculate game impact
        if self.score_occurred:
            # Determine if this score changed the game situation
            if self.score_margin_before <= 0 and self.score_margin_after > 0:
                object.__setattr__(self, 'go_ahead_score', True)
            elif abs(self.score_margin_before) <= 3 and abs(self.score_margin_after) <= 3:
                object.__setattr__(self, 'game_tying_score', True)
        
        # Set post-scoring requirements
        if self.touchdown_scored or self.field_goal_scored:
            object.__setattr__(self, 'requires_kickoff', True)
        
        if self.touchdown_scored and not self.conversion_attempt:
            object.__setattr__(self, 'requires_conversion', True)
        
        if self.safety_scored:
            object.__setattr__(self, 'requires_safety_kick', True)
    
    def get_score_description(self) -> str:
        """Return a human-readable description of the score."""
        if not self.score_occurred:
            return "No score"
        
        descriptions = {
            ScoreType.TOUCHDOWN: f"Touchdown ({self.points_scored} points)",
            ScoreType.FIELD_GOAL: f"Field Goal ({self.field_goal_distance} yards)",
            ScoreType.SAFETY: f"Safety ({self.points_scored} points)",
            ScoreType.EXTRA_POINT: "Extra Point",
            ScoreType.TWO_POINT_CONVERSION: "Two-Point Conversion",
            ScoreType.PICK_SIX: f"Pick Six ({self.return_distance} yard return)",
            ScoreType.FUMBLE_RECOVERY_TD: f"Fumble Return TD ({self.return_distance} yards)",
            ScoreType.PUNT_RETURN_TD: f"Punt Return TD ({self.return_distance} yards)",
            ScoreType.KICKOFF_RETURN_TD: f"Kickoff Return TD ({self.return_distance} yards)"
        }
        
        return descriptions.get(self.score_type, f"{self.score_type.value} ({self.points_scored} points)")
    
    def get_score_summary(self) -> str:
        """Return a summary of the scoring play."""
        parts = [self.get_score_description()]
        
        if self.touchdown_player:
            parts.append(f"by {self.touchdown_player}")
        elif self.field_goal_kicker:
            parts.append(f"by {self.field_goal_kicker}")
        elif self.safety_player:
            parts.append(f"on {self.safety_player}")
        
        if self.touchdown_distance > 0:
            parts.append(f"({self.touchdown_distance} yard play)")
        
        return " ".join(parts)
    
    def get_game_impact_description(self) -> str:
        """Return description of the game impact."""
        impacts = []
        
        if self.go_ahead_score:
            impacts.append("Go-ahead score")
        elif self.game_tying_score:
            impacts.append("Game-tying score")
        
        if self.game_winning_score:
            impacts.append("Game winner")
        
        if self.red_zone_score:
            impacts.append("Red zone score")
        elif self.goal_line_score:
            impacts.append("Goal line score")
        
        if self.defensive_score:
            impacts.append("Defensive score")
        
        return ", ".join(impacts) if impacts else "Regular score"
    
    def get_conversion_description(self) -> str:
        """Return description of conversion attempt if applicable."""
        if not self.conversion_attempt:
            return "No conversion"
        
        result = "successful" if self.conversion_successful else "failed"
        
        if self.conversion_type == ConversionType.EXTRA_POINT_KICK:
            return f"Extra point - {result}"
        elif self.conversion_type == ConversionType.TWO_POINT_ATTEMPT:
            return f"Two-point conversion - {result}"
        
        return f"Conversion attempt - {result}"
    
    def get_post_score_requirements(self) -> str:
        """Return description of what happens after this score."""
        requirements = []
        
        if self.requires_conversion:
            requirements.append("Conversion attempt")
        
        if self.requires_kickoff:
            requirements.append("Kickoff")
        
        if self.requires_safety_kick:
            requirements.append("Safety kick")
        
        if self.onside_kick_likely:
            requirements.append("Possible onside kick")
        
        return " → ".join(requirements) if requirements else "No special requirements"
    
    def is_major_score(self) -> bool:
        """Return True if this is a major scoring play (6+ points)."""
        return self.points_scored >= 6
    
    def is_defensive_touchdown(self) -> bool:
        """Return True if defense scored a touchdown."""
        return self.return_touchdown or self.pick_six or self.fumble_return_td
    
    def is_special_teams_score(self) -> bool:
        """Return True if special teams scored."""
        return self.score_type in [
            ScoreType.PUNT_RETURN_TD,
            ScoreType.KICKOFF_RETURN_TD,
            ScoreType.BLOCKED_PUNT_TD,
            ScoreType.BLOCKED_FIELD_GOAL_TD
        ]
    
    def get_summary(self) -> str:
        """Return a complete summary of this score transition."""
        if not self.score_occurred:
            return "No score"
        
        summary = f"{self.scoring_team}: {self.get_score_description()}"
        
        impact = self.get_game_impact_description()
        if impact != "Regular score":
            summary += f" [{impact.upper()}]"
        
        requirements = self.get_post_score_requirements()
        if requirements != "No special requirements":
            summary += f" → {requirements}"
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert this score transition to a dictionary."""
        return {
            'basic_info': {
                'score_occurred': self.score_occurred,
                'score_type': self.score_type.value if self.score_type else None,
                'points_scored': self.points_scored,
                'scoring_team': self.scoring_team,
                'score_description': self.get_score_description()
            },
            'score_updates': {
                'new_home_score': self.new_home_score,
                'new_away_score': self.new_away_score,
                'old_home_score': self.old_home_score,
                'old_away_score': self.old_away_score,
                'score_margin_before': self.score_margin_before,
                'score_margin_after': self.score_margin_after
            },
            'touchdown_info': {
                'touchdown_scored': self.touchdown_scored,
                'touchdown_type': self.touchdown_type,
                'touchdown_distance': self.touchdown_distance,
                'touchdown_player': self.touchdown_player,
                'touchdown_time': self.touchdown_time
            },
            'field_goal_info': {
                'field_goal_scored': self.field_goal_scored,
                'field_goal_distance': self.field_goal_distance,
                'field_goal_kicker': self.field_goal_kicker,
                'field_goal_blocked': self.field_goal_blocked,
                'field_goal_missed': self.field_goal_missed
            },
            'safety_info': {
                'safety_scored': self.safety_scored,
                'safety_type': self.safety_type,
                'safety_player': self.safety_player
            },
            'conversion_info': {
                'conversion_attempt': self.conversion_attempt,
                'conversion_type': self.conversion_type.value if self.conversion_type else None,
                'conversion_successful': self.conversion_successful,
                'conversion_points': self.conversion_points,
                'conversion_description': self.get_conversion_description()
            },
            'defensive_special_teams': {
                'defensive_score': self.defensive_score,
                'return_touchdown': self.return_touchdown,
                'return_distance': self.return_distance,
                'pick_six': self.pick_six,
                'fumble_return_td': self.fumble_return_td,
                'is_defensive_touchdown': self.is_defensive_touchdown(),
                'is_special_teams_score': self.is_special_teams_score()
            },
            'game_impact': {
                'go_ahead_score': self.go_ahead_score,
                'game_tying_score': self.game_tying_score,
                'game_winning_score': self.game_winning_score,
                'red_zone_score': self.red_zone_score,
                'goal_line_score': self.goal_line_score,
                'is_major_score': self.is_major_score(),
                'game_impact_description': self.get_game_impact_description()
            },
            'post_scoring': {
                'requires_kickoff': self.requires_kickoff,
                'requires_conversion': self.requires_conversion,
                'requires_safety_kick': self.requires_safety_kick,
                'onside_kick_likely': self.onside_kick_likely,
                'post_score_requirements': self.get_post_score_requirements()
            },
            'timing_context': {
                'quarter_scored': self.quarter_scored,
                'time_remaining': self.time_remaining
            },
            'summaries': {
                'score_summary': self.get_score_summary(),
                'overall_summary': self.get_summary()
            }
        }