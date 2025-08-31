from typing import Dict, Optional
from dataclasses import dataclass
from ..field.field_state import FieldState


@dataclass
class PersonnelPackage:
    """Represents the players on field for a specific play"""
    offensive_players: Dict
    defensive_players: Dict
    formation: str
    defensive_call: str


class PlayerSelector:
    """Handles personnel selection and substitution decisions"""
    
    @staticmethod
    def get_personnel(offense_team: Dict, defense_team: Dict, play_call: str, 
                     field_state: FieldState, config: Dict = None) -> PersonnelPackage:
        """
        Select appropriate personnel for both offense and defense
        
        Args:
            offense_team: Offensive team data and ratings
            defense_team: Defensive team data and ratings  
            play_call: Type of play being called ("run", "pass", etc.)
            field_state: Current field position and down/distance
            config: Optional configuration for personnel decisions
            
        Returns:
            PersonnelPackage: Selected players and formations
        """
        config = config or {}
        
        # Determine offensive formation based on play call and situation
        formation = PlayerSelector._select_offensive_formation(play_call, field_state)
        
        # Select offensive personnel based on formation
        offensive_players = PlayerSelector._select_offensive_players(
            offense_team, formation, field_state
        )
        
        # Determine defensive call based on formation and situation
        defensive_call = PlayerSelector._select_defensive_call(
            formation, play_call, field_state
        )
        
        # Select defensive personnel based on call
        defensive_players = PlayerSelector._select_defensive_players(
            defense_team, defensive_call, field_state
        )
        
        return PersonnelPackage(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            formation=formation,
            defensive_call=defensive_call
        )
    
    @staticmethod
    def _select_offensive_formation(play_call: str, field_state: FieldState) -> str:
        """Select offensive formation based on play type and situation"""
        
        # Goal line situations
        if field_state.is_goal_line():
            if play_call == "run":
                return "goal_line"
            else:
                return "goal_line_pass"
        
        # Short yardage situations
        if field_state.is_short_yardage():
            if play_call == "run":
                return "i_formation"
            else:
                return "tight_formation"
        
        # Long yardage situations
        if field_state.yards_to_go >= 8:
            return "shotgun_spread"
        
        # Standard formations
        if play_call == "run":
            return "singleback"
        elif play_call == "pass":
            return "shotgun"
        else:
            return "special_teams"
    
    @staticmethod
    def _select_offensive_players(offense_team: Dict, formation: str, 
                                field_state: FieldState) -> Dict:
        """Select specific offensive players based on formation"""
        
        # For now, return the team ratings as player selection
        # In a full implementation, this would select individual players
        # based on their ratings, fatigue, injuries, etc.
        
        base_players = {
            "qb": offense_team["offense"]["qb_rating"],
            "rb": offense_team["offense"]["rb_rating"], 
            "wr": offense_team["offense"]["wr_rating"],
            "te": offense_team["offense"]["te_rating"],
            "ol": offense_team["offense"]["ol_rating"]
        }
        
        # Modify personnel based on formation
        if formation == "goal_line":
            # Extra tight ends and fullbacks
            base_players["extra_te"] = base_players["te"]
            base_players["fb"] = base_players["rb"]
        elif formation == "shotgun_spread":
            # More receivers
            base_players["wr2"] = base_players["wr"]
            base_players["wr3"] = base_players["wr"] * 0.9  # Slightly lower rated WR3
        
        return base_players
    
    @staticmethod
    def _select_defensive_call(formation: str, play_call: str, field_state: FieldState) -> str:
        """Select defensive call based on offensive formation and situation"""
        
        # Goal line defense
        if field_state.is_goal_line():
            return "goal_line_defense"
        
        # Short yardage defense
        if field_state.is_short_yardage():
            return "run_stop"
        
        # Long yardage situations
        if field_state.yards_to_go >= 10:
            return "nickel_pass"
        
        # Predict run vs pass and adjust
        if formation in ["i_formation", "singleback", "goal_line"]:
            return "base_run_defense"
        elif formation in ["shotgun", "shotgun_spread"]:
            return "nickel_pass"
        else:
            return "base_defense"
    
    @staticmethod
    def _select_defensive_players(defense_team: Dict, defensive_call: str,
                                field_state: FieldState) -> Dict:
        """Select specific defensive players based on defensive call"""
        
        base_players = {
            "dl": defense_team["defense"]["dl_rating"],
            "lb": defense_team["defense"]["lb_rating"],
            "db": defense_team["defense"]["db_rating"]
        }
        
        # Modify personnel based on defensive call
        if defensive_call == "goal_line_defense":
            # Extra defensive linemen
            base_players["extra_dl"] = base_players["dl"]
        elif defensive_call == "nickel_pass":
            # Extra defensive backs
            base_players["extra_db"] = base_players["db"]
        elif defensive_call == "run_stop":
            # Extra linebackers
            base_players["extra_lb"] = base_players["lb"]
        
        return base_players
    
    @staticmethod
    def apply_fatigue(players: Dict, play_result: Dict) -> Dict:
        """Apply fatigue effects to players after a play (future enhancement)"""
        # Placeholder for fatigue system
        # In full implementation, this would:
        # - Reduce player effectiveness based on snaps played
        # - Make substitution decisions
        # - Handle injury risks
        return players