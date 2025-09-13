"""
Core data models for NFL schedule generation

Provides data structures for representing scheduled games, 
time slots, and schedule constraints.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, time
from typing import Optional, List, Dict, Set, Tuple
from enum import Enum
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from simulation.events.game_simulation_event import GameSimulationEvent
from .division_structure import NFL_STRUCTURE, Division, Conference


class TimeSlot(Enum):
    """NFL game time slots"""
    TNF = "Thursday Night Football"      # Thursday 8:15 PM ET
    SUNDAY_EARLY = "Sunday 1:00 PM ET"   # Sunday 1:00 PM ET
    SUNDAY_LATE = "Sunday 4:05/4:25 PM ET"  # Sunday 4:05/4:25 PM ET
    SNF = "Sunday Night Football"        # Sunday 8:20 PM ET
    MNF = "Monday Night Football"        # Monday 8:15 PM ET
    SATURDAY = "Saturday Special"        # Late season Saturday games
    INTERNATIONAL = "International"      # London/Germany morning games


class GameType(Enum):
    """Types of games in schedule"""
    DIVISION = "division"
    CONFERENCE = "conference"
    INTER_CONFERENCE = "inter_conference"
    PLACE_BASED = "place_based"


@dataclass
class ScheduledGame:
    """Represents a scheduled NFL game"""
    game_id: str
    week: int
    game_date: datetime
    home_team_id: int
    away_team_id: int
    time_slot: TimeSlot
    game_type: GameType
    
    # Optional metadata
    is_primetime: bool = False
    is_international: bool = False
    is_rivalry: bool = False
    is_thanksgiving: bool = False
    is_christmas: bool = False
    stadium_override: Optional[str] = None  # For international/neutral site games
    
    def __post_init__(self):
        """Post-initialization validation and setup"""
        # Auto-detect primetime games
        if self.time_slot in [TimeSlot.TNF, TimeSlot.SNF, TimeSlot.MNF]:
            self.is_primetime = True
        
        # Auto-detect game type if not provided
        if self.game_type is None:
            self._detect_game_type()
        
        # Validate teams are different
        if self.home_team_id == self.away_team_id:
            raise ValueError(f"Home and away teams cannot be the same: {self.home_team_id}")
    
    def _detect_game_type(self):
        """Auto-detect game type based on teams"""
        home_div = NFL_STRUCTURE.get_division_for_team(self.home_team_id)
        away_div = NFL_STRUCTURE.get_division_for_team(self.away_team_id)
        
        if home_div == away_div:
            self.game_type = GameType.DIVISION
        else:
            home_conf = NFL_STRUCTURE.get_conference_for_team(self.home_team_id)
            away_conf = NFL_STRUCTURE.get_conference_for_team(self.away_team_id)
            
            if home_conf == away_conf:
                self.game_type = GameType.CONFERENCE
            else:
                self.game_type = GameType.INTER_CONFERENCE
    
    def to_calendar_event(self) -> GameSimulationEvent:
        """Convert to GameSimulationEvent for CalendarManager"""
        return GameSimulationEvent(
            date=self.game_date,
            away_team_id=self.away_team_id,
            home_team_id=self.home_team_id,
            week=self.week,
            season_type="regular_season"
        )
    
    def get_teams(self) -> Tuple[int, int]:
        """Get both team IDs as a tuple"""
        return (self.home_team_id, self.away_team_id)
    
    def involves_team(self, team_id: int) -> bool:
        """Check if a specific team is involved in this game"""
        return team_id in (self.home_team_id, self.away_team_id)
    
    def swap_home_away(self):
        """Swap home and away teams"""
        self.home_team_id, self.away_team_id = self.away_team_id, self.home_team_id
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'game_id': self.game_id,
            'week': self.week,
            'date': self.game_date.isoformat(),
            'home_team': self.home_team_id,
            'away_team': self.away_team_id,
            'time_slot': self.time_slot.value,
            'game_type': self.game_type.value,
            'is_primetime': self.is_primetime,
            'is_international': self.is_international,
            'is_rivalry': self.is_rivalry
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ScheduledGame':
        """Create from dictionary (JSON deserialization)"""
        return cls(
            game_id=data['game_id'],
            week=data['week'],
            game_date=datetime.fromisoformat(data['date']),
            home_team_id=data['home_team'],
            away_team_id=data['away_team'],
            time_slot=TimeSlot(data['time_slot']),
            game_type=GameType(data['game_type']),
            is_primetime=data.get('is_primetime', False),
            is_international=data.get('is_international', False),
            is_rivalry=data.get('is_rivalry', False)
        )


@dataclass
class WeekSchedule:
    """Represents all games in a single week"""
    week_number: int
    games: List[ScheduledGame] = field(default_factory=list)
    teams_on_bye: Set[int] = field(default_factory=set)
    
    def add_game(self, game: ScheduledGame):
        """Add a game to this week"""
        if game.week != self.week_number:
            raise ValueError(f"Game week {game.week} doesn't match week {self.week_number}")
        self.games.append(game)
    
    def get_teams_playing(self) -> Set[int]:
        """Get all teams playing this week"""
        teams = set()
        for game in self.games:
            teams.add(game.home_team_id)
            teams.add(game.away_team_id)
        return teams
    
    def get_primetime_games(self) -> List[ScheduledGame]:
        """Get all primetime games this week"""
        return [g for g in self.games if g.is_primetime]
    
    def get_games_by_slot(self, slot: TimeSlot) -> List[ScheduledGame]:
        """Get games in a specific time slot"""
        return [g for g in self.games if g.time_slot == slot]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate week schedule"""
        errors = []
        
        # Check no team plays twice
        teams_playing = []
        for game in self.games:
            teams_playing.extend([game.home_team_id, game.away_team_id])
        
        if len(teams_playing) != len(set(teams_playing)):
            errors.append(f"Week {self.week_number}: Some teams play multiple games")
        
        # Check teams on bye aren't playing
        playing_set = set(teams_playing)
        if playing_set & self.teams_on_bye:
            conflicts = playing_set & self.teams_on_bye
            errors.append(f"Week {self.week_number}: Teams on bye are playing: {conflicts}")
        
        # Check all teams are accounted for
        all_teams = playing_set | self.teams_on_bye
        if len(all_teams) != 32:
            errors.append(f"Week {self.week_number}: Only {len(all_teams)} teams accounted for")
        
        return len(errors) == 0, errors


@dataclass
class SeasonSchedule:
    """Complete NFL season schedule"""
    season_year: int
    weeks: Dict[int, WeekSchedule] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize weeks if not provided"""
        if not self.weeks:
            for week_num in range(1, 19):  # 18 weeks
                self.weeks[week_num] = WeekSchedule(week_num)
    
    def add_game(self, game: ScheduledGame):
        """Add a game to the schedule"""
        if game.week not in self.weeks:
            self.weeks[game.week] = WeekSchedule(game.week)
        self.weeks[game.week].add_game(game)
    
    def get_team_schedule(self, team_id: int) -> List[ScheduledGame]:
        """Get all games for a specific team"""
        games = []
        for week in self.weeks.values():
            for game in week.games:
                if game.involves_team(team_id):
                    games.append(game)
        return sorted(games, key=lambda g: g.week)
    
    def get_team_bye_week(self, team_id: int) -> Optional[int]:
        """Get bye week for a team"""
        for week_num, week in self.weeks.items():
            if team_id in week.teams_on_bye:
                return week_num
        return None
    
    def get_all_games(self) -> List[ScheduledGame]:
        """Get all games in the season"""
        games = []
        for week in self.weeks.values():
            games.extend(week.games)
        return games
    
    def get_division_games(self, team_id: int) -> List[ScheduledGame]:
        """Get all division games for a team"""
        team_games = self.get_team_schedule(team_id)
        return [g for g in team_games if g.game_type == GameType.DIVISION]
    
    def get_primetime_games(self) -> List[ScheduledGame]:
        """Get all primetime games in the season"""
        games = []
        for week in self.weeks.values():
            games.extend(week.get_primetime_games())
        return games
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate entire season schedule"""
        errors = []
        
        # Validate each week
        for week_num, week in self.weeks.items():
            is_valid, week_errors = week.validate()
            if not is_valid:
                errors.extend(week_errors)
        
        # Check each team plays 17 games
        for team_id in range(1, 33):
            games = self.get_team_schedule(team_id)
            if len(games) != 17:
                errors.append(f"Team {team_id} has {len(games)} games, expected 17")
        
        # Check each team has exactly one bye
        for team_id in range(1, 33):
            bye_week = self.get_team_bye_week(team_id)
            if bye_week is None:
                errors.append(f"Team {team_id} has no bye week")
        
        # Check division games (should be 6 per team)
        for team_id in range(1, 33):
            div_games = self.get_division_games(team_id)
            if len(div_games) != 6:
                errors.append(f"Team {team_id} has {len(div_games)} division games, expected 6")
        
        return len(errors) == 0, errors
    
    def to_json_format(self) -> List[Dict]:
        """Convert to JSON-serializable format for CalendarManager"""
        games_list = []
        for game in self.get_all_games():
            games_list.append(game.to_dict())
        return games_list
    
    def summary_stats(self) -> Dict:
        """Get summary statistics for the schedule"""
        all_games = self.get_all_games()
        return {
            'total_games': len(all_games),
            'primetime_games': len(self.get_primetime_games()),
            'division_games': sum(1 for g in all_games if g.game_type == GameType.DIVISION),
            'conference_games': sum(1 for g in all_games if g.game_type == GameType.CONFERENCE),
            'inter_conference_games': sum(1 for g in all_games if g.game_type == GameType.INTER_CONFERENCE),
            'international_games': sum(1 for g in all_games if g.is_international),
            'rivalry_games': sum(1 for g in all_games if g.is_rivalry)
        }