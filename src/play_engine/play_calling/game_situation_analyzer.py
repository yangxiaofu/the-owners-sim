"""
Game Situation Analyzer - Context Analysis for Intelligent Decision Making

Analyzes game context and converts it into appropriate format for the matrix-based
4th down decision system and other situational play calling decisions.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class GamePhase(Enum):
    """Phases of the game for different strategic considerations"""
    FIRST_HALF = "first_half"
    THIRD_QUARTER = "third_quarter"  
    FOURTH_QUARTER_EARLY = "fourth_quarter_early"
    FOURTH_QUARTER_LATE = "fourth_quarter_late"
    TWO_MINUTE_WARNING = "two_minute_warning"
    FINAL_MINUTE = "final_minute"


class GameScript(Enum):
    """Overall game script/flow for strategic decisions"""
    CONTROL_GAME = "control_game"        # Big lead, run clock
    COMPETITIVE = "competitive"          # Close game, normal strategy
    COMEBACK_MODE = "comeback_mode"      # Behind, need to score quickly
    DESPERATION = "desperation"          # Far behind, high risk/reward
    PROTECT_LEAD = "protect_lead"        # Small lead, conservative


@dataclass
class GameContext:
    """Comprehensive game situation context"""
    # Basic game state
    quarter: int
    time_remaining: int                  # Seconds remaining in game
    score_differential: int              # Points ahead (+) or behind (-)
    field_position: int                  # Current field position (1-100)
    down: int                           # Current down (1-4)
    yards_to_go: int                    # Yards needed for first down
    
    # Game flow analysis
    game_phase: GamePhase
    game_script: GameScript
    momentum: str                       # "home", "away", "neutral"
    
    # Environmental factors  
    weather_conditions: Optional[str] = None
    venue_type: str = "outdoor"         # "indoor", "outdoor", "dome"
    is_home_game: bool = True
    
    # Game importance
    playoff_implications: bool = False   # Division/playoff implications
    rivalry_game: bool = False          # Divisional rival
    primetime: bool = False             # National TV game
    
    # Team context
    timeouts_remaining: int = 3
    injury_situation: str = "normal"    # "normal", "key_players_hurt", "decimated"


class GameSituationAnalyzer:
    """Analyzes game context for intelligent decision making"""
    
    @classmethod
    def analyze_game_context(cls, raw_context: Dict[str, Any]) -> GameContext:
        """
        Convert raw game context into structured GameContext
        
        Args:
            raw_context: Dictionary with game state information
            
        Returns:
            Structured GameContext for decision making
        """
        # Extract basic information
        quarter = raw_context.get('quarter', 4)
        time_remaining = raw_context.get('time_remaining', 900)
        score_differential = raw_context.get('score_differential', 0)
        field_position = raw_context.get('field_position', 50)
        down = raw_context.get('down', 4)
        yards_to_go = raw_context.get('yards_to_go', 5)
        
        # Analyze game phase
        game_phase = cls._determine_game_phase(quarter, time_remaining)
        
        # Analyze game script
        game_script = cls._determine_game_script(score_differential, game_phase)
        
        # Analyze momentum (simplified for now)
        momentum = raw_context.get('momentum', 'neutral')
        
        # Environmental factors
        weather = raw_context.get('weather_conditions')
        venue = raw_context.get('venue_type', 'outdoor')
        is_home = raw_context.get('is_home_game', True)
        
        # Game importance
        playoff_implications = raw_context.get('playoff_implications', False)
        rivalry = raw_context.get('rivalry_game', False)
        primetime = raw_context.get('primetime', False)
        
        # Team context
        timeouts = raw_context.get('timeouts_remaining', 3)
        injuries = raw_context.get('injury_situation', 'normal')
        
        return GameContext(
            quarter=quarter,
            time_remaining=time_remaining,
            score_differential=score_differential,
            field_position=field_position,
            down=down,
            yards_to_go=yards_to_go,
            game_phase=game_phase,
            game_script=game_script,
            momentum=momentum,
            weather_conditions=weather,
            venue_type=venue,
            is_home_game=is_home,
            playoff_implications=playoff_implications,
            rivalry_game=rivalry,
            primetime=primetime,
            timeouts_remaining=timeouts,
            injury_situation=injuries
        )
    
    @classmethod
    def _determine_game_phase(cls, quarter: int, time_remaining: int) -> GamePhase:
        """Determine what phase of the game we're in"""
        if quarter <= 2:
            return GamePhase.FIRST_HALF
        elif quarter == 3:
            return GamePhase.THIRD_QUARTER
        else:  # Fourth quarter or overtime
            if time_remaining > 600:       # >10 minutes
                return GamePhase.FOURTH_QUARTER_EARLY
            elif time_remaining > 120:    # 2-10 minutes
                return GamePhase.FOURTH_QUARTER_LATE
            elif time_remaining > 60:     # 1-2 minutes
                return GamePhase.TWO_MINUTE_WARNING
            else:                         # <1 minute
                return GamePhase.FINAL_MINUTE
    
    @classmethod
    def _determine_game_script(cls, score_differential: int, game_phase: GamePhase) -> GameScript:
        """Determine the overall game script/strategy needed"""
        # Late game script determination
        if game_phase in [GamePhase.TWO_MINUTE_WARNING, GamePhase.FINAL_MINUTE]:
            if score_differential <= -14:
                return GameScript.DESPERATION
            elif score_differential <= -3:
                return GameScript.COMEBACK_MODE
            elif score_differential >= 14:
                return GameScript.CONTROL_GAME
            elif score_differential >= 3:
                return GameScript.PROTECT_LEAD
            else:
                return GameScript.COMPETITIVE
        
        # Early/mid game script determination  
        else:
            if score_differential >= 21:
                return GameScript.CONTROL_GAME
            elif score_differential >= 10:
                return GameScript.PROTECT_LEAD
            elif score_differential <= -21:
                return GameScript.DESPERATION
            elif score_differential <= -10:
                return GameScript.COMEBACK_MODE
            else:
                return GameScript.COMPETITIVE
    
    @classmethod
    def get_special_situations(cls, context: GameContext) -> List[str]:
        """
        Extract special situation modifiers for decision making
        
        Args:
            context: Analyzed game context
            
        Returns:
            List of special situation keys for matrix modifiers
        """
        special_situations = []
        
        # Weather conditions
        if context.weather_conditions:
            if context.weather_conditions in ['rain', 'snow', 'wind']:
                special_situations.append('weather_bad')
            elif context.weather_conditions in ['blizzard', 'hurricane', 'severe_wind']:
                special_situations.append('weather_extreme')
        
        # Venue advantage
        if context.is_home_game:
            special_situations.append('home_field')
        
        # Game importance
        if context.primetime:
            special_situations.append('primetime_game')
        
        if context.playoff_implications:
            special_situations.append('playoff_game')
        
        # Game script special cases
        if context.game_script == GameScript.DESPERATION:
            special_situations.append('elimination_game')
        elif context.game_script == GameScript.CONTROL_GAME:
            special_situations.append('division_clinched')
        
        return special_situations
    
    @classmethod
    def get_urgency_level(cls, context: GameContext) -> float:
        """
        Calculate overall urgency level (0.0 = no urgency, 1.0 = maximum urgency)
        
        Args:
            context: Analyzed game context
            
        Returns:
            Urgency level for decision making
        """
        base_urgency = 0.0
        
        # Time-based urgency
        if context.game_phase == GamePhase.FINAL_MINUTE:
            base_urgency += 0.5
        elif context.game_phase == GamePhase.TWO_MINUTE_WARNING:
            base_urgency += 0.3
        elif context.game_phase == GamePhase.FOURTH_QUARTER_LATE:
            base_urgency += 0.2
        
        # Score-based urgency
        if context.score_differential <= -14:  # Two possessions behind
            base_urgency += 0.4
        elif context.score_differential <= -7:  # One possession behind
            base_urgency += 0.2
        elif context.score_differential <= -3:  # Close behind
            base_urgency += 0.1
        
        # Game script urgency
        if context.game_script == GameScript.DESPERATION:
            base_urgency += 0.3
        elif context.game_script == GameScript.COMEBACK_MODE:
            base_urgency += 0.2
        
        return min(1.0, base_urgency)
    
    @classmethod
    def should_be_conservative(cls, context: GameContext) -> bool:
        """
        Determine if situation calls for conservative approach
        
        Args:
            context: Analyzed game context
            
        Returns:
            True if situation favors conservative play calling
        """
        # Big lead situations
        if context.game_script == GameScript.CONTROL_GAME:
            return True
        
        # Protecting small lead late
        if (context.game_script == GameScript.PROTECT_LEAD and 
            context.game_phase in [GamePhase.FOURTH_QUARTER_LATE, GamePhase.TWO_MINUTE_WARNING]):
            return True
        
        # Bad weather conditions
        if context.weather_conditions in ['blizzard', 'hurricane', 'severe_wind']:
            return True
        
        # Injury situations
        if context.injury_situation == 'decimated':
            return True
            
        return False
    
    @classmethod
    def should_be_aggressive(cls, context: GameContext) -> bool:
        """
        Determine if situation calls for aggressive approach
        
        Args:
            context: Analyzed game context
            
        Returns:
            True if situation favors aggressive play calling
        """
        # Desperation mode
        if context.game_script == GameScript.DESPERATION:
            return True
        
        # Comeback mode in late game
        if (context.game_script == GameScript.COMEBACK_MODE and
            context.game_phase in [GamePhase.TWO_MINUTE_WARNING, GamePhase.FINAL_MINUTE]):
            return True
        
        # High-stakes games
        if context.playoff_implications and context.score_differential <= 7:
            return True
        
        return False
    
    @classmethod
    def get_decision_context_summary(cls, context: GameContext) -> Dict[str, Any]:
        """
        Create summary of key decision-making factors
        
        Args:
            context: Analyzed game context
            
        Returns:
            Dictionary summary of key factors
        """
        return {
            'game_phase': context.game_phase.value,
            'game_script': context.game_script.value,
            'urgency_level': cls.get_urgency_level(context),
            'should_be_conservative': cls.should_be_conservative(context),
            'should_be_aggressive': cls.should_be_aggressive(context),
            'special_situations': cls.get_special_situations(context),
            'score_situation': {
                'differential': context.score_differential,
                'ahead': context.score_differential > 0,
                'tied': context.score_differential == 0,
                'behind': context.score_differential < 0,
                'close_game': abs(context.score_differential) <= 7,
                'blowout': abs(context.score_differential) >= 21
            },
            'time_situation': {
                'quarter': context.quarter,
                'time_remaining': context.time_remaining,
                'late_game': context.game_phase in [GamePhase.TWO_MINUTE_WARNING, GamePhase.FINAL_MINUTE],
                'timeouts_remaining': context.timeouts_remaining
            }
        }