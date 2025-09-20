"""
Simple schedule template for holding all 272 NFL games.

YAGNI: Basic data structure with minimal validation.
No complex template loading, no JSON schemas.
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from .time_slots import GameSlot, TimeSlot


@dataclass 
class SeasonSchedule:
    """Holds all games for an NFL season"""
    year: int
    games: List[GameSlot]
    
    def __post_init__(self):
        if not self.games:
            self.games = self._create_empty_schedule()
    
    def _create_empty_schedule(self) -> List[GameSlot]:
        """Create empty schedule with all time slots"""
        games = []
        
        for week in range(1, 19):  # Weeks 1-18
            # Thursday night (except week 1)
            if week > 1:
                games.append(GameSlot(week, TimeSlot.THURSDAY_NIGHT))
            
            # Sunday early games (10 slots) - increased for 272 game capacity
            for _ in range(10):
                games.append(GameSlot(week, TimeSlot.SUNDAY_EARLY))
            
            # Sunday late games (5 slots) - increased for 272 game capacity
            for _ in range(5):
                games.append(GameSlot(week, TimeSlot.SUNDAY_LATE))
                
            # Sunday night
            games.append(GameSlot(week, TimeSlot.SUNDAY_NIGHT))
            
            # Monday night (no MNF in week 18)
            if week != 18:
                games.append(GameSlot(week, TimeSlot.MONDAY_NIGHT))
        
        return games
    
    def get_week_games(self, week: int) -> List[GameSlot]:
        """Get all games for a specific week"""
        return [g for g in self.games if g.week == week]
    
    def get_team_schedule(self, team_id: int) -> List[GameSlot]:
        """Get all games for a specific team"""
        return [g for g in self.games 
                if g.home_team_id == team_id or g.away_team_id == team_id]
    
    def get_assigned_games(self) -> List[GameSlot]:
        """Get all games that have been assigned"""
        return [g for g in self.games if g.is_assigned]
    
    def get_empty_slots(self) -> List[GameSlot]:
        """Get all empty slots"""
        return [g for g in self.games if not g.is_assigned]
    
    def get_primetime_games(self) -> List[GameSlot]:
        """Get all primetime games"""
        return [g for g in self.games if g.is_primetime and g.is_assigned]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Basic validation - each team plays 17 games"""
        errors = []
        
        # Count games per team
        team_games = {}
        for game in self.games:
            if game.is_assigned:
                for team_id in [game.home_team_id, game.away_team_id]:
                    team_games[team_id] = team_games.get(team_id, 0) + 1
        
        # Check each team has 17 games
        for team_id in range(1, 33):
            count = team_games.get(team_id, 0) 
            if count != 17:
                errors.append(f"Team {team_id}: {count} games (expected 17)")
        
        # Check total games
        assigned_games = len([g for g in self.games if g.is_assigned])
        if assigned_games != 272:
            errors.append(f"Total games: {assigned_games} (expected 272)")
        
        # Check no team plays twice in same week
        for team_id in range(1, 33):
            team_schedule = self.get_team_schedule(team_id)
            weeks_played = [game.week for game in team_schedule if game.is_assigned]
            if len(weeks_played) != len(set(weeks_played)):
                errors.append(f"Team {team_id} plays multiple games in same week")
        
        return len(errors) == 0, errors
    
    def get_team_home_games(self, team_id: int) -> List[GameSlot]:
        """Get all home games for a team"""
        return [g for g in self.games if g.home_team_id == team_id]
    
    def get_team_away_games(self, team_id: int) -> List[GameSlot]:
        """Get all away games for a team"""
        return [g for g in self.games if g.away_team_id == team_id]
    
    def get_home_away_balance(self, team_id: int) -> Tuple[int, int]:
        """Get home/away game counts for a team"""
        home_games = len(self.get_team_home_games(team_id))
        away_games = len(self.get_team_away_games(team_id))
        return home_games, away_games
    
    def get_total_slots(self) -> int:
        """Get total number of available slots"""
        return len(self.games)
    
    def clear_all_assignments(self) -> None:
        """Clear all game assignments"""
        for game in self.games:
            game.clear_assignment()
    
    def __str__(self) -> str:
        """String representation of the schedule"""
        assigned_count = len(self.get_assigned_games())
        total_slots = self.get_total_slots()
        return f"SeasonSchedule {self.year}: {assigned_count}/{total_slots} games assigned"
    
    def __len__(self) -> int:
        """Return number of assigned games"""
        return len(self.get_assigned_games())