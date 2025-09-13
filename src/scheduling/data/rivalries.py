"""
Minimal rivalry detection for scheduling.

YAGNI: Division rivals only. No complex intensity scoring,
no historical analysis, no inter-conference rivalries.
"""

from typing import List, Set
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scheduling.data.division_structure import NFL_STRUCTURE


class RivalryDetector:
    """Simple rivalry detection - division rivals only"""
    
    def __init__(self):
        self.nfl_structure = NFL_STRUCTURE
    
    def are_division_rivals(self, team1_id: int, team2_id: int) -> bool:
        """Check if two teams are division rivals"""
        if team1_id == team2_id:
            return False
        
        team1_division = self.nfl_structure.get_division_for_team(team1_id)
        team2_division = self.nfl_structure.get_division_for_team(team2_id)
        
        return team1_division == team2_division
    
    def get_division_rivals(self, team_id: int) -> List[int]:
        """Get all division rivals for a team"""
        return self.nfl_structure.get_division_opponents(team_id)
    
    def are_rivals(self, team1_id: int, team2_id: int) -> bool:
        """Check if two teams are rivals (division only for YAGNI)"""
        return self.are_division_rivals(team1_id, team2_id)
    
    def get_rivals(self, team_id: int) -> List[int]:
        """Get all rivals for a team (division only for YAGNI)"""
        return self.get_division_rivals(team_id)
    
    def get_rivalry_games(self, team_ids: List[int]) -> List[tuple[int, int]]:
        """Get all rivalry matchups from a list of teams"""
        rivalry_games = []
        
        for i, team1 in enumerate(team_ids):
            for team2 in team_ids[i+1:]:
                if self.are_rivals(team1, team2):
                    rivalry_games.append((team1, team2))
        
        return rivalry_games