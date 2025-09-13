"""
Minimal team data manager - just what we need for scheduling.

YAGNI Principle: Only load and manage the team data actually needed
for schedule generation. No weather, no stadium details, no market analysis.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scheduling.data.division_structure import NFL_STRUCTURE, Division


@dataclass
class Team:
    """Basic team info needed for scheduling"""
    team_id: int
    city: str
    nickname: str
    abbreviation: str
    
    @property
    def full_name(self) -> str:
        """Get full team name"""
        return f"{self.city} {self.nickname}"
    
    @property
    def division(self) -> Division:
        """Get team's division"""
        return NFL_STRUCTURE.get_division_for_team(self.team_id)
    
    @property
    def division_opponents(self) -> List[int]:
        """Get division opponent IDs"""
        return NFL_STRUCTURE.get_division_opponents(self.team_id)


class TeamDataManager:
    """Load and manage team data - minimal implementation"""
    
    def __init__(self, teams_file: str = "src/data/teams.json"):
        self.teams: Dict[int, Team] = {}
        self._load_teams(teams_file)
    
    def _load_teams(self, teams_file: str) -> None:
        """Load teams from existing JSON file"""
        file_path = Path(teams_file)
        
        # Handle relative paths from different execution contexts
        if not file_path.exists():
            # Try from project root
            project_root = Path(__file__).parent.parent.parent.parent
            file_path = project_root / teams_file
        
        if not file_path.exists():
            raise FileNotFoundError(f"Teams file not found: {teams_file}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Handle both direct dict and nested structure
        teams_data = data.get("teams", data) if isinstance(data, dict) else data
        
        for team_id_str, info in teams_data.items():
            team_id = int(team_id_str)
            self.teams[team_id] = Team(
                team_id=team_id,
                city=info['city'],
                nickname=info['nickname'],
                abbreviation=info['abbreviation']
            )
    
    def get_team(self, team_id: int) -> Optional[Team]:
        """Get team by ID"""
        return self.teams.get(team_id)
    
    def get_all_teams(self) -> List[Team]:
        """Get all teams"""
        return list(self.teams.values())
    
    def get_teams_by_division(self, division: Division) -> List[Team]:
        """Get all teams in a division"""
        division_team_ids = NFL_STRUCTURE.get_division_teams(division)
        return [self.teams[tid] for tid in division_team_ids if tid in self.teams]
    
    def team_exists(self, team_id: int) -> bool:
        """Check if team exists"""
        return team_id in self.teams
    
    def __len__(self) -> int:
        """Get number of teams loaded"""
        return len(self.teams)
    
    def __repr__(self) -> str:
        """String representation"""
        return f"TeamDataManager(teams={len(self.teams)})"