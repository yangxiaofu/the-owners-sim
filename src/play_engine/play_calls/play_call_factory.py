"""
Play call factory for easy creation and common play combinations

Provides convenient factory methods for creating common offensive and defensive
play calls with realistic combinations of play types, formations, and concepts.
"""

from typing import Dict, List, Optional, Union
from .offensive_play_call import OffensivePlayCall
from .defensive_play_call import DefensivePlayCall
from .special_teams_play_call import SpecialTeamsPlayCall
from ..play_types.offensive_types import OffensivePlayType, PuntPlayType
from ..play_types.defensive_types import DefensivePlayType
from ..mechanics.formations import OffensiveFormation, DefensiveFormation


class PlayCallFactory:
    """Factory for creating common play calls"""
    
    # Common offensive play combinations
    COMMON_OFFENSIVE_PLAYS = {
        "power_run": {
            "play_type": OffensivePlayType.RUN,
            "formation": OffensiveFormation.I_FORMATION,
            "concept": "power"
        },
        "sweep_run": {
            "play_type": OffensivePlayType.RUN,
            "formation": OffensiveFormation.I_FORMATION,
            "concept": "sweep"
        },
        "draw_play": {
            "play_type": OffensivePlayType.RUN,
            "formation": OffensiveFormation.SHOTGUN,
            "concept": "draw"
        },
        "quick_slants": {
            "play_type": OffensivePlayType.QUICK_SLANT,
            "formation": OffensiveFormation.SHOTGUN,
            "concept": "three_slants"
        },
        "four_verticals": {
            "play_type": OffensivePlayType.DEEP_BALL,
            "formation": OffensiveFormation.FOUR_WIDE,
            "concept": "four_verticals"
        },
        "play_action_deep": {
            "play_type": OffensivePlayType.PLAY_ACTION_PASS,
            "formation": OffensiveFormation.I_FORMATION,
            "concept": "play_action_deep"
        },
        "screen_pass": {
            "play_type": OffensivePlayType.SCREEN_PASS,
            "formation": OffensiveFormation.SHOTGUN,
            "concept": "bubble_screen"
        },
        "goal_line_run": {
            "play_type": OffensivePlayType.RUN,
            "formation": OffensiveFormation.GOAL_LINE,
            "concept": "goal_line_power"
        }
    }
    
    # Common defensive play combinations
    COMMON_DEFENSIVE_PLAYS = {
        "cover_2_base": {
            "play_type": DefensivePlayType.COVER_2,
            "formation": DefensiveFormation.FOUR_THREE,
            "coverage": "zone"
        },
        "cover_3_base": {
            "play_type": DefensivePlayType.COVER_3,
            "formation": DefensiveFormation.FOUR_THREE,
            "coverage": "zone"
        },
        "man_coverage": {
            "play_type": DefensivePlayType.MAN_COVERAGE,
            "formation": DefensiveFormation.FOUR_THREE,
            "coverage": "man"
        },
        "nickel_blitz": {
            "play_type": DefensivePlayType.BLITZ,
            "formation": DefensiveFormation.NICKEL,
            "coverage": "man",
            "blitz_package": "safety_blitz"
        },
        "corner_blitz": {
            "play_type": DefensivePlayType.CORNER_BLITZ,
            "formation": DefensiveFormation.BLITZ_PACKAGE,
            "coverage": "robber",
            "blitz_package": "corner_blitz"
        },
        "prevent_defense": {
            "play_type": DefensivePlayType.PREVENT_DEFENSE,
            "formation": DefensiveFormation.PREVENT,
            "coverage": "deep_zone"
        },
        "goal_line_defense": {
            "play_type": DefensivePlayType.GOAL_LINE_DEFENSE,
            "formation": DefensiveFormation.GOAL_LINE,
            "coverage": "goal_line"
        },
        "run_stuff": {
            "play_type": DefensivePlayType.RUN_STUFF,
            "formation": DefensiveFormation.FOUR_SIX,
            "coverage": "run_support"
        }
    }
    
    # Common special teams play combinations
    COMMON_SPECIAL_TEAMS_PLAYS = {
        "field_goal": {
            "play_type": OffensivePlayType.FIELD_GOAL,
            "formation": OffensiveFormation.FIELD_GOAL,
            "strategy": "field_goal_attempt"
        },
        "punt": {
            "play_type": OffensivePlayType.PUNT,
            "formation": OffensiveFormation.PUNT,
            "strategy": "directional_punt"
        },
        "fake_punt_pass": {
            "play_type": PuntPlayType.FAKE_PUNT_PASS,
            "formation": OffensiveFormation.PUNT,
            "strategy": "fake_punt_pass"
        },
        "fake_punt_run": {
            "play_type": PuntPlayType.FAKE_PUNT_RUN,
            "formation": OffensiveFormation.PUNT,
            "strategy": "fake_punt_run"
        },
        "kickoff": {
            "play_type": OffensivePlayType.KICKOFF,
            "formation": OffensiveFormation.KICKOFF,
            "strategy": "regular_kickoff"
        },
        "onside_kick": {
            "play_type": OffensivePlayType.ONSIDE_KICK,
            "formation": OffensiveFormation.KICKOFF,
            "strategy": "onside_kick"
        },
        "punt_return": {
            "play_type": DefensivePlayType.PUNT_RETURN,
            "formation": DefensiveFormation.PUNT_RETURN,
            "coverage": "return_middle"
        },
        "punt_block": {
            "play_type": DefensivePlayType.PUNT_BLOCK,
            "formation": DefensiveFormation.PUNT_RETURN,
            "strategy": "block_attempt"
        },
        "kickoff_return": {
            "play_type": DefensivePlayType.KICKOFF_RETURN,
            "formation": DefensiveFormation.PUNT_RETURN,  # Using generic special teams formation
            "coverage": "return_coverage"
        }
    }
    
    @classmethod
    def create_offensive_play(cls, play_name: str, **overrides) -> OffensivePlayCall:
        """
        Create common offensive play by name
        
        Args:
            play_name: Name from COMMON_OFFENSIVE_PLAYS
            **overrides: Override any default parameters
            
        Returns:
            OffensivePlayCall instance
            
        Raises:
            ValueError: If play_name not found
        """
        if play_name not in cls.COMMON_OFFENSIVE_PLAYS:
            available_plays = ", ".join(cls.COMMON_OFFENSIVE_PLAYS.keys())
            raise ValueError(f"Unknown play '{play_name}'. Available plays: {available_plays}")
        
        # Get default parameters and apply overrides
        params = cls.COMMON_OFFENSIVE_PLAYS[play_name].copy()
        params.update(overrides)
        
        return OffensivePlayCall(**params)
    
    @classmethod
    def create_defensive_play(cls, play_name: str, **overrides) -> DefensivePlayCall:
        """
        Create common defensive play by name
        
        Args:
            play_name: Name from COMMON_DEFENSIVE_PLAYS  
            **overrides: Override any default parameters
            
        Returns:
            DefensivePlayCall instance
            
        Raises:
            ValueError: If play_name not found
        """
        if play_name not in cls.COMMON_DEFENSIVE_PLAYS:
            available_plays = ", ".join(cls.COMMON_DEFENSIVE_PLAYS.keys())
            raise ValueError(f"Unknown play '{play_name}'. Available plays: {available_plays}")
        
        # Get default parameters and apply overrides
        params = cls.COMMON_DEFENSIVE_PLAYS[play_name].copy()
        params.update(overrides)
        
        return DefensivePlayCall(**params)
    
    @classmethod
    def create_special_teams_play(cls, play_name: str, **overrides) -> SpecialTeamsPlayCall:
        """
        Create common special teams play by name
        
        Args:
            play_name: Name from COMMON_SPECIAL_TEAMS_PLAYS
            **overrides: Override any default parameters
            
        Returns:
            SpecialTeamsPlayCall instance
            
        Raises:
            ValueError: If play_name not found
        """
        if play_name not in cls.COMMON_SPECIAL_TEAMS_PLAYS:
            available_plays = ", ".join(cls.COMMON_SPECIAL_TEAMS_PLAYS.keys())
            raise ValueError(f"Unknown play '{play_name}'. Available plays: {available_plays}")
        
        # Get default parameters and apply overrides
        params = cls.COMMON_SPECIAL_TEAMS_PLAYS[play_name].copy()
        params.update(overrides)
        
        return SpecialTeamsPlayCall(**params)
    
    @classmethod
    def create_power_run(cls, formation: Optional[str] = None) -> OffensivePlayCall:
        """Create a power run play"""
        return cls.create_offensive_play(
            "power_run", 
            formation=formation or OffensiveFormation.I_FORMATION
        )
    
    @classmethod
    def create_quick_pass(cls, formation: Optional[str] = None) -> OffensivePlayCall:
        """Create a quick passing play"""
        return cls.create_offensive_play(
            "quick_slants",
            formation=formation or OffensiveFormation.SHOTGUN
        )
    
    @classmethod
    def create_deep_pass(cls, formation: Optional[str] = None) -> OffensivePlayCall:
        """Create a deep passing play"""
        return cls.create_offensive_play(
            "four_verticals",
            formation=formation or OffensiveFormation.FOUR_WIDE
        )
    
    @classmethod
    def create_field_goal(cls) -> SpecialTeamsPlayCall:
        """Create a field goal play"""
        return cls.create_special_teams_play("field_goal")
    
    @classmethod  
    def create_punt(cls) -> SpecialTeamsPlayCall:
        """Create a punt play"""
        return cls.create_special_teams_play("punt")
    
    @classmethod
    def create_fake_punt_pass(cls) -> SpecialTeamsPlayCall:
        """Create a fake punt pass play"""
        return cls.create_special_teams_play("fake_punt_pass")
    
    @classmethod
    def create_fake_punt_run(cls) -> SpecialTeamsPlayCall:
        """Create a fake punt run play"""
        return cls.create_special_teams_play("fake_punt_run")
    
    @classmethod
    def create_kickoff(cls) -> SpecialTeamsPlayCall:
        """Create a kickoff play"""
        return cls.create_special_teams_play("kickoff")
    
    @classmethod
    def create_onside_kick(cls) -> SpecialTeamsPlayCall:
        """Create an onside kick play"""
        return cls.create_special_teams_play("onside_kick")
    
    @classmethod
    def create_cover_2(cls, formation: Optional[str] = None) -> DefensivePlayCall:
        """Create a Cover 2 defense"""
        return cls.create_defensive_play(
            "cover_2_base",
            formation=formation or DefensiveFormation.FOUR_THREE
        )
    
    @classmethod
    def create_blitz(cls, blitz_type: str = "safety_blitz") -> DefensivePlayCall:
        """Create a blitz play"""
        return cls.create_defensive_play(
            "nickel_blitz",
            blitz_package=blitz_type
        )
    
    @classmethod
    def create_prevent_defense(cls) -> DefensivePlayCall:
        """Create prevent defense for late game situations"""
        return cls.create_defensive_play("prevent_defense")
    
    @classmethod
    def create_goal_line_defense(cls) -> DefensivePlayCall:
        """Create goal line defense"""
        return cls.create_defensive_play("goal_line_defense")
    
    @classmethod
    def create_punt_return(cls) -> SpecialTeamsPlayCall:
        """Create punt return play"""
        return cls.create_special_teams_play("punt_return")
    
    @classmethod
    def create_punt_block(cls) -> SpecialTeamsPlayCall:
        """Create punt block play"""
        return cls.create_special_teams_play("punt_block")
    
    @classmethod
    def create_kickoff_return(cls) -> SpecialTeamsPlayCall:
        """Create kickoff return play"""
        return cls.create_special_teams_play("kickoff_return")
    
    @classmethod
    def get_available_offensive_plays(cls) -> List[str]:
        """Get list of available offensive play names"""
        return list(cls.COMMON_OFFENSIVE_PLAYS.keys())
    
    @classmethod
    def get_available_defensive_plays(cls) -> List[str]:
        """Get list of available defensive play names"""
        return list(cls.COMMON_DEFENSIVE_PLAYS.keys())
    
    @classmethod
    def get_available_special_teams_plays(cls) -> List[str]:
        """Get list of available special teams play names"""
        return list(cls.COMMON_SPECIAL_TEAMS_PLAYS.keys())
    
    @classmethod
    def create_situational_offense(cls, down: int, distance: int, field_position: int) -> OffensivePlayCall:
        """
        Create situational offensive play based on down, distance, and field position
        
        Args:
            down: Down number (1-4)
            distance: Yards to go for first down
            field_position: Yards from own goal line (0-100)
            
        Returns:
            Appropriate OffensivePlayCall for situation
        """
        # Goal line situations (within 5 yards of end zone)
        if field_position >= 95:
            return cls.create_offensive_play("goal_line_run")
        
        # Short yardage (4th and short, 3rd and short)
        if distance <= 2 and down >= 3:
            return cls.create_power_run()
        
        # Long distance (3rd and long, 2nd and long)
        if distance >= 8:
            if down == 3:
                return cls.create_deep_pass()  # Must convert
            else:
                return cls.create_quick_pass()  # Set up manageable 3rd down
        
        # Standard situations
        if down <= 2:
            # Early downs - establish run/pass balance
            return cls.create_power_run() if field_position < 50 else cls.create_quick_pass()
        else:
            # 3rd down - pass to convert
            return cls.create_quick_pass()
    
    @classmethod
    def create_situational_defense(cls, down: int, distance: int, field_position: int) -> DefensivePlayCall:
        """
        Create situational defensive play based on offensive situation
        
        Args:
            down: Down number (1-4)
            distance: Yards to go for first down  
            field_position: Yards from opponent's goal line (0-100)
            
        Returns:
            Appropriate DefensivePlayCall for situation
        """
        # Goal line defense (within 10 yards)
        if field_position <= 10:
            return cls.create_goal_line_defense()
        
        # Prevent defense (long field, late in half/game)
        if field_position <= 20 and distance >= 15:
            return cls.create_prevent_defense()
        
        # Obvious passing situations (3rd and long, 2nd and long)
        if distance >= 8 and down >= 2:
            return cls.create_defensive_play("nickel_blitz")
        
        # Short yardage defense
        if distance <= 2:
            return cls.create_defensive_play("run_stuff")
        
        # Standard situations - balanced defense
        return cls.create_cover_2()