"""
Basic scheduler to assign matchups to time slots.

YAGNI: Simple assignment algorithm. No complex optimization,
no constraint solving, no network requirements.
"""

from typing import List, Dict, Set, Tuple
from random import shuffle, random
from pathlib import Path
import sys

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scheduling.data.team_data import TeamDataManager
from scheduling.data.rivalries import RivalryDetector
from .schedule_template import SeasonSchedule
from .time_slots import TimeSlot


class BasicScheduler:
    """Simple scheduler that assigns matchups to time slots"""
    
    def __init__(self):
        self.team_manager = TeamDataManager()
        self.rivalry_detector = RivalryDetector()
    
    def schedule_matchups(self, matchups: List[Tuple[int, int]], 
                         year: int = 2024) -> SeasonSchedule:
        """
        Assign matchups to time slots using basic algorithm.
        
        Args:
            matchups: List of (home_team_id, away_team_id) tuples
            year: Season year
            
        Returns:
            Complete season schedule
        """
        schedule = SeasonSchedule(year, [])
        available_slots = schedule.games.copy()
        team_week_assigned: Dict[int, Set[int]] = {}  # Team -> set of weeks assigned
        
        # Separate primetime-worthy matchups
        primetime_matchups = self.get_primetime_worthy_matchups(matchups)
        regular_matchups = [m for m in matchups if m not in primetime_matchups]
        
        # First, assign primetime games
        self._assign_primetime_games(schedule, primetime_matchups, team_week_assigned)
        
        # Then assign remaining games
        remaining_matchups = [m for m in regular_matchups 
                            if not self._is_game_assigned(schedule, m)]
        
        shuffle(remaining_matchups)  # Randomize for variety
        
        for home_team, away_team in remaining_matchups:
            if self._is_game_assigned(schedule, (home_team, away_team)):
                continue  # Already assigned in primetime
                
            # Find available slot where neither team is already playing
            assigned = False
            
            # Get available slots (not assigned and teams not playing that week)
            available_slots = [
                slot for slot in schedule.get_empty_slots()
                if not self._team_plays_week(team_week_assigned, home_team, slot.week) and
                   not self._team_plays_week(team_week_assigned, away_team, slot.week)
            ]
            
            if not available_slots:
                raise ValueError(f"Could not assign {away_team}@{home_team} - no available slots")
            
            # Pick first available slot (could be enhanced with better logic)
            slot = available_slots[0]
            slot.assign_game(home_team, away_team)
            
            # Track assignments
            self._mark_team_week(team_week_assigned, home_team, slot.week)
            self._mark_team_week(team_week_assigned, away_team, slot.week)
            
            assigned = True
        
        return schedule
    
    def _assign_primetime_games(self, schedule: SeasonSchedule, 
                               primetime_matchups: List[Tuple[int, int]],
                               team_week_assigned: Dict[int, Set[int]]) -> None:
        """Assign high-profile matchups to primetime slots"""
        primetime_slots = [slot for slot in schedule.games if slot.is_primetime]
        
        # Shuffle both for variety
        shuffle(primetime_matchups)
        shuffle(primetime_slots)
        
        assigned_count = 0
        max_primetime = min(len(primetime_matchups), len(primetime_slots) // 2)  # Don't fill all primetime
        
        for home_team, away_team in primetime_matchups:
            if assigned_count >= max_primetime:
                break
                
            # Find available primetime slot
            for slot in primetime_slots:
                if (slot.is_assigned or
                    self._team_plays_week(team_week_assigned, home_team, slot.week) or
                    self._team_plays_week(team_week_assigned, away_team, slot.week)):
                    continue
                
                slot.assign_game(home_team, away_team)
                self._mark_team_week(team_week_assigned, home_team, slot.week)
                self._mark_team_week(team_week_assigned, away_team, slot.week)
                assigned_count += 1
                break
    
    def _is_game_assigned(self, schedule: SeasonSchedule, matchup: Tuple[int, int]) -> bool:
        """Check if a specific matchup is already assigned"""
        home_team, away_team = matchup
        for game in schedule.get_assigned_games():
            if game.home_team_id == home_team and game.away_team_id == away_team:
                return True
        return False
    
    def _team_plays_week(self, assignments: Dict[int, Set[int]], team_id: int, week: int) -> bool:
        """Check if team already plays in given week"""
        return week in assignments.get(team_id, set())
    
    def _mark_team_week(self, assignments: Dict[int, Set[int]], team_id: int, week: int) -> None:
        """Mark that team plays in given week"""
        if team_id not in assignments:
            assignments[team_id] = set()
        assignments[team_id].add(week)
    
    def get_primetime_worthy_matchups(self, matchups: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """Identify matchups suitable for primetime (simple heuristic)"""
        primetime_worthy = []
        
        # Large market teams (simplified - Cowboys, Giants, Patriots, 49ers, Packers, etc.)
        large_market_teams = {17, 18, 22, 31, 23, 14}  # Cowboys, Giants, Patriots, 49ers, Packers, Chiefs
        
        for home_team, away_team in matchups:
            # Rivalries get primetime preference
            if self.rivalry_detector.are_rivals(home_team, away_team):
                primetime_worthy.append((home_team, away_team))
            # Large market teams
            elif home_team in large_market_teams or away_team in large_market_teams:
                # Add some randomness to avoid always picking the same teams
                if random() < 0.6:  # 60% chance
                    primetime_worthy.append((home_team, away_team))
        
        return primetime_worthy
    
    def generate_simple_matchups(self, num_games: int = 272) -> List[Tuple[int, int]]:
        """
        Generate simple matchups for testing (not NFL-accurate).
        This is just for testing the scheduler.
        """
        matchups = []
        games_per_team = num_games * 2 // 32  # Each game involves 2 teams
        
        team_game_count = {team_id: 0 for team_id in range(1, 33)}
        
        for home_team in range(1, 33):
            for away_team in range(1, 33):
                if (home_team != away_team and 
                    team_game_count[home_team] < games_per_team and
                    team_game_count[away_team] < games_per_team and
                    len(matchups) < num_games):
                    
                    matchups.append((home_team, away_team))
                    team_game_count[home_team] += 1
                    team_game_count[away_team] += 1
        
        return matchups[:num_games]