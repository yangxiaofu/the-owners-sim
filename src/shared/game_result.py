"""
Shared Game Result Classes

Contains unified GameResult and related classes that can be imported 
throughout the system without circular dependency issues.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

# Import Team class - use string for type annotation to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from team_management.teams.team_loader import Team


@dataclass 
class GameResult:
    """Complete game result with comprehensive statistics"""
    home_team: 'Team'
    away_team: 'Team'
    final_score: Dict[int, int]
    quarter_scores: List[Dict[int, int]] = field(default_factory=list)
    drives: List[Any] = field(default_factory=list)  # List[DriveResult]
    total_plays: int = 0
    game_duration_minutes: int = 0
    overtime_played: bool = False
    
    # Additional fields for compatibility with existing code
    winner: Optional['Team'] = None
    total_drives: int = 0
    drive_results: List[Any] = field(default_factory=list)
    final_statistics: Optional[Dict[str, Any]] = None
    week: int = 1
    season_type: str = "regular_season"
    date: Optional[Any] = None  # Date field for compatibility
    player_stats: Optional[Any] = None  # Player stats for store compatibility
    home_team_stats: Optional[Any] = None  # Home team stats for store compatibility
    away_team_stats: Optional[Any] = None  # Away team stats for store compatibility
    overtime_periods: int = 0  # Overtime periods for store compatibility
    weather_conditions: Optional[Any] = None  # Weather conditions for store compatibility
    
    def __post_init__(self):
        """Auto-populate compatible fields if not provided"""
        if self.total_drives == 0 and self.drives:
            self.total_drives = len(self.drives)
        
        # If drive_results is empty but drives is populated, copy over
        if not self.drive_results and self.drives:
            self.drive_results = self.drives
    
    # Legacy compatibility properties
    @property
    def home_team_id(self) -> int:
        """Legacy compatibility: access home team ID"""
        return self.home_team.team_id
    
    @property
    def away_team_id(self) -> int:
        """Legacy compatibility: access away team ID"""
        return self.away_team.team_id
    
    @property
    def home_score(self) -> int:
        """Get final home team score"""
        return self.final_score.get(self.home_team.team_id, 0)
    
    @property
    def away_score(self) -> int:
        """Get final away team score"""
        return self.final_score.get(self.away_team.team_id, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            'home_team_id': self.home_team.team_id,
            'away_team_id': self.away_team.team_id,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'total_plays': self.total_plays,
            'game_duration_minutes': self.game_duration_minutes,
            'overtime_played': self.overtime_played,
            'quarter_scores': self.quarter_scores
        }