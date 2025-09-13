"""
Minimal standings provider for place-based matchup scheduling.

YAGNI: Just enough to determine who finished 1st, 2nd, 3rd, 4th in each division.
No complex tiebreakers, no playoff seeding, no wildcard tracking.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class TeamStanding:
    """Simple team standing record"""
    team_id: int
    wins: int
    losses: int
    ties: int
    division_place: int  # 1st, 2nd, 3rd, or 4th
    
    @property
    def win_percentage(self) -> float:
        """Calculate win percentage"""
        total_games = self.wins + self.losses + self.ties
        if total_games == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / total_games


class StandingsProvider:
    """Provides previous season standings for scheduling"""
    
    def __init__(self):
        self.standings: Dict[int, TeamStanding] = {}
        self._load_default_standings()
    
    def _load_default_standings(self) -> None:
        """Load default standings (can be from file or hardcoded)"""
        # For now, just create random but valid standings
        # In production, would load from previous season data
        # YAGNI: Not implementing file loading until actually needed
        
        # Simple approach: Assign places 1-4 in each division
        # AFC East: 1, 2, 3, 4
        # AFC North: 5, 6, 7, 8
        # etc.
        
        division_teams = [
            [1, 2, 3, 4],      # AFC East
            [5, 6, 7, 8],      # AFC North
            [9, 10, 11, 12],   # AFC South
            [13, 14, 15, 16],  # AFC West
            [17, 18, 19, 20],  # NFC East
            [21, 22, 23, 24],  # NFC North
            [25, 26, 27, 28],  # NFC South
            [29, 30, 31, 32],  # NFC West
        ]
        
        for division in division_teams:
            for place, team_id in enumerate(division, 1):
                # Simple win/loss records that make sense for places
                wins = 14 - (place - 1) * 3  # 14, 11, 8, 5
                losses = 17 - wins
                
                self.standings[team_id] = TeamStanding(
                    team_id=team_id,
                    wins=wins,
                    losses=losses,
                    ties=0,
                    division_place=place
                )
    
    def get_division_place(self, team_id: int) -> int:
        """Get a team's division finish (1-4)"""
        if team_id in self.standings:
            return self.standings[team_id].division_place
        return 1  # Default to 1st if no data
    
    def get_teams_by_place(self, division_teams: List[int], place: int) -> List[int]:
        """Get teams that finished in a specific place in their divisions"""
        result = []
        for team_id in division_teams:
            if self.get_division_place(team_id) == place:
                result.append(team_id)
        return result
    
    def get_standing(self, team_id: int) -> Optional[TeamStanding]:
        """Get full standing for a team"""
        return self.standings.get(team_id)