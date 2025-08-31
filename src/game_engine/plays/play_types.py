from abc import ABC, abstractmethod
from typing import Dict, Tuple, Union
from ..field.field_state import FieldState
from .data_structures import PlayResult
from ..personnel.player_selector import PersonnelPackage


class PlayType(ABC):
    """Abstract base class for all play types using Strategy pattern"""
    
    @abstractmethod
    def simulate(self, personnel: PersonnelPackage, field_state: FieldState) -> PlayResult:
        """
        Simulate the play using selected personnel and return the result
        
        Args:
            personnel: PersonnelPackage containing selected players, formations, and matchups
            field_state: Current field position, down, distance, etc.
            
        Returns:
            PlayResult: Complete result of the play execution
        """
        pass
    
    def simulate_legacy(self, offense_team: Dict, defense_team: Dict, field_state: FieldState) -> PlayResult:
        """
        Legacy simulation method for backward compatibility.
        
        This method provides backward compatibility for existing code that uses
        team ratings instead of personnel packages. New implementations should
        override the main simulate() method instead.
        
        Args:
            offense_team: Dict containing offensive team ratings and data
            defense_team: Dict containing defensive team ratings and data  
            field_state: Current field position, down, distance, etc.
            
        Returns:
            PlayResult: Complete result of the play execution
        """
        # Create a minimal personnel package for legacy support
        from ..personnel.player_selector import PersonnelPackage
        
        personnel = PersonnelPackage(
            offensive_players=offense_team.get("offense", {}),
            defensive_players=defense_team.get("defense", {}),
            formation="singleback",  # Default formation
            defensive_call="base_defense",  # Default call
            individual_players=False
        )
        
        return self.simulate(personnel, field_state)
    
    def _get_formation_modifier(self, offense_formation: str, defense_call: str, play_type: str) -> float:
        """
        Calculate formation advantage/disadvantage modifier.
        
        Args:
            offense_formation: Offensive formation used
            defense_call: Defensive call used
            play_type: Type of play being run
            
        Returns:
            float: Modifier (1.0 = neutral, >1.0 = advantage, <1.0 = disadvantage)
        """
        # Formation advantage matrix
        advantages = {
            # Goal line situations
            ("goal_line", "base_defense", "run"): 1.15,
            ("goal_line", "nickel_pass", "run"): 1.25,
            ("goal_line_pass", "goal_line_defense", "pass"): 1.10,
            
            # Short yardage
            ("i_formation", "nickel_pass", "run"): 1.20,
            ("i_formation", "base_defense", "run"): 1.10,
            
            # Long yardage
            ("shotgun_spread", "base_run_defense", "pass"): 1.25,
            ("shotgun_spread", "base_defense", "pass"): 1.15,
            ("shotgun", "run_stop", "pass"): 1.20,
            
            # Standard formations
            ("singleback", "nickel_pass", "run"): 1.10,
            ("shotgun", "goal_line_defense", "pass"): 1.15,
        }
        
        return advantages.get((offense_formation, defense_call, play_type), 1.0)
    
    def _extract_player_ratings(self, personnel: PersonnelPackage, position_group: str) -> Dict[str, float]:
        """
        Extract player ratings from personnel package, handling both individual and team modes.
        
        Args:
            personnel: Personnel package containing player data
            position_group: Position group to extract ('offense', 'defense')
            
        Returns:
            Dict with position ratings
        """
        if position_group == "offense":
            players = personnel.offensive_players
        else:
            players = personnel.defensive_players
        
        if personnel.individual_players:
            # Calculate effective ratings from individual players
            ratings = {}
            
            if personnel.rb_on_field:
                ratings['rb'] = personnel.rb_on_field.effective_rating
                
            if personnel.ol_on_field:
                ratings['ol'] = sum(ol.effective_rating for ol in personnel.ol_on_field) / len(personnel.ol_on_field)
                
            if personnel.dl_on_field:
                ratings['dl'] = sum(dl.effective_rating for dl in personnel.dl_on_field) / len(personnel.dl_on_field)
                
            if personnel.lb_on_field:
                ratings['lb'] = sum(lb.effective_rating for lb in personnel.lb_on_field) / len(personnel.lb_on_field)
            
            # Fallback to personnel package ratings for missing positions
            for key, value in players.items():
                if key not in ratings and isinstance(value, (int, float)):
                    ratings[key] = value
                    
            return ratings
        else:
            # Use team ratings directly
            return dict(players)
    
    def _calculate_time_elapsed(self, play_type: str, outcome: str) -> int:
        """Calculate seconds elapsed for this play (shared logic)"""
        import random
        
        if play_type == "pass" and outcome == "incomplete":
            return random.randint(3, 8)  # Clock stops on incomplete
        elif outcome == "touchdown":
            return random.randint(5, 15)  # Quick scoring plays
        elif play_type in ["punt", "field_goal", "kickoff"]:
            return random.randint(8, 15)  # Special teams plays
        else:
            return random.randint(15, 40)  # Normal running clock
    
    def _calculate_points(self, outcome: str) -> int:
        """Calculate points scored for this outcome (shared logic)"""
        if outcome == "touchdown":
            return 6  # Plus extra point (7 total)
        elif outcome == "field_goal":
            return 3
        elif outcome == "safety":
            return 2
        else:
            return 0