from typing import Dict, Optional, List, Union
from dataclasses import dataclass, field
from ..field.field_state import FieldState
from ...database.models.players.player import Player
from ...database.models.players.positions import RunningBack, OffensiveLineman, DefensiveLineman, Linebacker
from ...database.generators.mock_generator import MockPlayerGenerator


@dataclass
class PersonnelPackage:
    """Represents the players on field for a specific play"""
    # Can handle either individual Player objects or team rating dicts
    offensive_players: Union[Dict[str, Player], Dict[str, int]]
    defensive_players: Union[Dict[str, Player], Dict[str, int]]
    formation: str
    defensive_call: str
    
    # Individual player tracking (when using player-based simulation)
    individual_players: bool = False
    rb_on_field: Optional[RunningBack] = None
    ol_on_field: List[OffensiveLineman] = field(default_factory=list)
    dl_on_field: List[DefensiveLineman] = field(default_factory=list)
    lb_on_field: List[Linebacker] = field(default_factory=list)
    
    def get_running_back(self) -> Optional[RunningBack]:
        """Get the running back on the field"""
        return self.rb_on_field
    
    def get_offensive_line(self) -> List[OffensiveLineman]:
        """Get the offensive line players on the field"""
        return self.ol_on_field
    
    def get_defensive_line(self) -> List[DefensiveLineman]:
        """Get the defensive line players on the field"""
        return self.dl_on_field
    
    def get_linebackers(self) -> List[Linebacker]:
        """Get the linebacker players on the field"""
        return self.lb_on_field
    
    def get_key_matchups(self) -> List[Dict]:
        """Identify key player-vs-player matchups for the play"""
        if not self.individual_players:
            return []
        
        matchups = []
        
        # RB vs MLB matchup (primary run defender)
        rb = self.get_running_back()
        mlb = self._get_mike_linebacker()
        if rb and mlb:
            matchups.append({
                'type': 'rb_vs_mlb',
                'offense': rb,
                'defense': mlb,
                'importance': 'high'
            })
        
        # OL vs DL matchups
        ol_players = self.get_offensive_line()
        dl_players = self.get_defensive_line()
        
        # Match up interior linemen first
        interior_ol = [p for p in ol_players if p.position in ['LG', 'C', 'RG']]
        interior_dl = [p for p in dl_players if p.position in ['DT', 'NT']]
        
        for i, ol_player in enumerate(interior_ol[:len(interior_dl)]):
            matchups.append({
                'type': 'ol_vs_dl_interior',
                'offense': ol_player,
                'defense': interior_dl[i],
                'importance': 'high'
            })
        
        return matchups
    
    def _get_mike_linebacker(self) -> Optional[Linebacker]:
        """Get the middle linebacker (primary run defender)"""
        lbs = self.get_linebackers()
        # Look for MLB first, then any LB
        for lb in lbs:
            if lb.position == 'MLB':
                return lb
        return lbs[0] if lbs else None


class PlayerSelector:
    """Handles personnel selection and substitution decisions"""
    
    def __init__(self, use_individual_players: bool = False):
        self.use_individual_players = use_individual_players
        self.team_rosters = {}  # Will hold individual player rosters if needed
        
        if use_individual_players:
            # Initialize with generated rosters - will be set externally
            pass
    
    def set_team_rosters(self, team_rosters: Dict[int, Dict[str, List[Player]]]):
        """Set the team rosters for individual player mode"""
        self.team_rosters = team_rosters
    
    def get_personnel(self, offense_team: Dict, defense_team: Dict, play_call: str, 
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
        formation = self._select_offensive_formation(play_call, field_state)
        
        # Determine defensive call based on formation and situation
        defensive_call = self._select_defensive_call(formation, play_call, field_state)
        
        if self.use_individual_players:
            # Use individual player selection
            return self._select_individual_personnel(
                offense_team, defense_team, formation, defensive_call, field_state, config
            )
        else:
            # Use team rating based selection (backward compatibility)
            offensive_players = self._select_offensive_players(
                offense_team, formation, field_state
            )
            defensive_players = self._select_defensive_players(
                defense_team, defensive_call, field_state
            )
            
            return PersonnelPackage(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                formation=formation,
                defensive_call=defensive_call,
                individual_players=False
            )
    
    def _select_individual_personnel(self, offense_team: Dict, defense_team: Dict, 
                                   formation: str, defensive_call: str, 
                                   field_state: FieldState, config: Dict) -> PersonnelPackage:
        """Select individual players for the play"""
        offense_team_id = offense_team.get('team_id', offense_team.get('id', 1))
        defense_team_id = defense_team.get('team_id', defense_team.get('id', 2))
        
        # Get team rosters
        offense_roster = self.team_rosters.get(offense_team_id, {})
        defense_roster = self.team_rosters.get(defense_team_id, {})
        
        # Select offensive players
        rb_on_field = self._select_running_back(offense_roster, formation, field_state)
        ol_on_field = self._select_offensive_line(offense_roster, formation)
        
        # Select defensive players
        dl_on_field = self._select_defensive_line(defense_roster, defensive_call)
        lb_on_field = self._select_linebackers(defense_roster, defensive_call)
        
        # Create player dicts for backward compatibility
        offensive_players = {
            'rb': rb_on_field.overall_rating if rb_on_field else 50,
            'ol': sum(p.overall_rating for p in ol_on_field) // max(len(ol_on_field), 1) if ol_on_field else 50
        }
        
        defensive_players = {
            'dl': sum(p.overall_rating for p in dl_on_field) // max(len(dl_on_field), 1) if dl_on_field else 50,
            'lb': sum(p.overall_rating for p in lb_on_field) // max(len(lb_on_field), 1) if lb_on_field else 50
        }
        
        return PersonnelPackage(
            offensive_players=offensive_players,
            defensive_players=defensive_players,
            formation=formation,
            defensive_call=defensive_call,
            individual_players=True,
            rb_on_field=rb_on_field,
            ol_on_field=ol_on_field,
            dl_on_field=dl_on_field,
            lb_on_field=lb_on_field
        )
    
    def _select_running_back(self, roster: Dict[str, List[Player]], formation: str, field_state: FieldState) -> Optional[RunningBack]:
        """Select the appropriate RB for the play"""
        running_backs = roster.get('running_backs', [])
        
        if not running_backs:
            return None
        
        # Goal line: prefer fullback if available
        if field_state.is_goal_line() and formation == "goal_line":
            fullbacks = [rb for rb in running_backs if rb.position == "FB" and rb.is_available()]
            if fullbacks:
                return fullbacks[0]
        
        # Default to starter RB
        starters = [rb for rb in running_backs if rb.role.value == "starter" and rb.position == "RB" and rb.is_available()]
        if starters:
            return starters[0]
            
        # Fall back to any available RB
        available_rbs = [rb for rb in running_backs if rb.position == "RB" and rb.is_available()]
        return available_rbs[0] if available_rbs else None
    
    def _select_offensive_line(self, roster: Dict[str, List[Player]], formation: str) -> List[OffensiveLineman]:
        """Select the offensive line for the play"""
        ol_players = roster.get('offensive_line', [])
        
        if not ol_players:
            return []
        
        # Get starters for each position
        positions = ["LT", "LG", "C", "RG", "RT"]
        selected_ol = []
        
        for pos in positions:
            # Find starter for this position
            starters = [ol for ol in ol_players if ol.position == pos and ol.role.value == "starter" and ol.is_available()]
            if starters:
                selected_ol.append(starters[0])
            else:
                # Fall back to any player who can play this position
                backups = [ol for ol in ol_players if ol.position in [pos, "OL"] and ol.is_available()]
                if backups:
                    selected_ol.append(backups[0])
        
        return selected_ol
    
    def _select_defensive_line(self, roster: Dict[str, List[Player]], defensive_call: str) -> List[DefensiveLineman]:
        """Select the defensive line for the play"""
        dl_players = roster.get('defensive_line', [])
        
        if not dl_players:
            return []
        
        # Base 4-man front
        positions = ["LE", "DT", "DT", "RE"]
        
        # Adjust for defensive call
        if defensive_call == "goal_line_defense":
            # More DTs on goal line
            positions = ["DT", "DT", "DT", "DT"]
        
        selected_dl = []
        position_counts = {}
        
        for pos in positions:
            # Track how many we've used of each position
            count = position_counts.get(pos, 0)
            position_counts[pos] = count + 1
            
            # Find available player for this position
            candidates = [dl for dl in dl_players if dl.position == pos and dl.is_available()]
            
            # Skip players already selected
            candidates = [dl for dl in candidates if dl not in selected_dl]
            
            if candidates:
                selected_dl.append(candidates[0])
            else:
                # Fall back to any available DL
                backups = [dl for dl in dl_players if dl.is_available() and dl not in selected_dl]
                if backups:
                    selected_dl.append(backups[0])
        
        return selected_dl
    
    def _select_linebackers(self, roster: Dict[str, List[Player]], defensive_call: str) -> List[Linebacker]:
        """Select the linebackers for the play"""
        lb_players = roster.get('linebackers', [])
        
        if not lb_players:
            return []
        
        # Base 3-4 or 4-3 LB setup
        positions = ["LOLB", "MLB", "ROLB"]
        
        # Adjust for defensive call
        if defensive_call == "run_stop":
            # Extra LB for run stopping
            positions.append("LB")
        
        selected_lbs = []
        
        for pos in positions:
            # Find available player for this position
            candidates = [lb for lb in lb_players if lb.position in [pos, "LB"] and lb.is_available()]
            
            # Skip players already selected
            candidates = [lb for lb in candidates if lb not in selected_lbs]
            
            if candidates:
                # Prefer starters
                starters = [lb for lb in candidates if lb.role.value == "starter"]
                if starters:
                    selected_lbs.append(starters[0])
                else:
                    selected_lbs.append(candidates[0])
        
        return selected_lbs
    
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