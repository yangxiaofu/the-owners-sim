"""
Game Result

Specialized result class for NFL game simulations with rich game-specific data
and metadata for standings updates, player statistics, and season progression.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from .base_result import SimulationResult, EventType


@dataclass
class PlayerGameStats:
    """Individual player statistics from a game"""
    player_name: str
    position: str
    team_id: int
    
    # Offensive stats
    passing_yards: int = 0
    passing_tds: int = 0
    passing_interceptions: int = 0
    rushing_yards: int = 0
    rushing_tds: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    receptions: int = 0
    
    # Defensive stats  
    tackles: int = 0
    sacks: float = 0.0
    interceptions: int = 0
    pass_deflections: int = 0
    
    # Special teams
    field_goals_made: int = 0
    field_goals_attempted: int = 0
    extra_points_made: int = 0
    extra_points_attempted: int = 0
    
    # Performance metrics
    performance_rating: float = 0.0
    snap_count: int = 0
    
    def get_total_touchdowns(self) -> int:
        """Get total touchdowns scored by this player"""
        return self.passing_tds + self.rushing_tds + self.receiving_tds
    
    def get_total_yards(self) -> int:
        """Get total offensive yards for this player"""
        return self.passing_yards + self.rushing_yards + self.receiving_yards


@dataclass
class TeamGameStats:
    """Team-level statistics from a game"""
    team_id: int
    score: int
    
    # Team totals
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    turnovers: int = 0
    penalties: int = 0
    penalty_yards: int = 0
    time_of_possession_seconds: int = 0
    
    # Drives
    total_drives: int = 0
    scoring_drives: int = 0
    red_zone_attempts: int = 0
    red_zone_conversions: int = 0
    
    # Special performance metrics
    third_down_conversions: int = 0
    third_down_attempts: int = 0
    fourth_down_conversions: int = 0
    fourth_down_attempts: int = 0
    
    def get_third_down_percentage(self) -> float:
        """Calculate third down conversion percentage"""
        if self.third_down_attempts == 0:
            return 0.0
        return (self.third_down_conversions / self.third_down_attempts) * 100
    
    def get_red_zone_percentage(self) -> float:
        """Calculate red zone conversion percentage"""
        if self.red_zone_attempts == 0:
            return 0.0
        return (self.red_zone_conversions / self.red_zone_attempts) * 100


@dataclass
class GameStateChanges:
    """Changes to team/league state resulting from this game"""
    
    # Standings impact
    winner_id: Optional[int] = None
    loser_id: Optional[int] = None
    is_tie: bool = False
    
    # Season context
    playoff_implications: List[str] = field(default_factory=list)
    division_standings_changes: Dict[str, Any] = field(default_factory=dict)
    wild_card_implications: List[str] = field(default_factory=list)
    
    # Team momentum and morale changes
    team_momentum_changes: Dict[int, float] = field(default_factory=dict)  # team_id -> momentum delta
    coaching_confidence_changes: Dict[int, float] = field(default_factory=dict)
    
    # Injury and fatigue impacts
    player_injuries: List[Dict[str, Any]] = field(default_factory=list)
    team_fatigue_levels: Dict[int, float] = field(default_factory=dict)
    
    # Performance ratings
    player_performance_updates: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # player_name -> updates
    
    def add_playoff_implication(self, description: str) -> None:
        """Add a playoff implication from this game"""
        self.playoff_implications.append(description)
    
    def add_player_injury(self, player_name: str, injury_type: str, severity: str, weeks_out: int) -> None:
        """Record a player injury from this game"""
        self.player_injuries.append({
            "player_name": player_name,
            "injury_type": injury_type,
            "severity": severity,
            "weeks_out": weeks_out,
            "game_date": datetime.now()  # This would be the actual game date
        })
    
    def set_team_momentum(self, team_id: int, momentum_delta: float) -> None:
        """Set momentum change for a team"""
        self.team_momentum_changes[team_id] = momentum_delta


@dataclass
class GameResult(SimulationResult):
    """
    Specialized result for NFL game simulations.
    
    Contains rich game data including scores, statistics, player performance,
    and state changes that need to be processed for season progression.
    """
    
    # Game basic info
    away_team_id: int = 0
    home_team_id: int = 0
    away_score: int = 0
    home_score: int = 0
    week: int = 0
    season_type: str = "regular_season"
    
    # Game flow and performance
    total_plays: int = 0
    total_drives: int = 0
    game_duration_minutes: int = 0
    overtime_periods: int = 0
    weather_conditions: str = "clear"
    
    # Team statistics
    team_stats: Dict[int, TeamGameStats] = field(default_factory=dict)
    
    # Player statistics
    player_stats: List[PlayerGameStats] = field(default_factory=list)
    
    # State changes and impacts
    state_changes: GameStateChanges = field(default_factory=GameStateChanges)
    
    # Game narrative and highlights
    key_plays: List[str] = field(default_factory=list)
    game_highlights: List[str] = field(default_factory=list)
    turning_points: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        super().__post_init__()
        # Set event type for games
        self.event_type = EventType.GAME
        
        # Initialize state changes if not provided
        if not hasattr(self, 'state_changes') or self.state_changes is None:
            self.state_changes = GameStateChanges()
        
        # Determine winner and update state changes
        if self.away_score > self.home_score:
            self.state_changes.winner_id = self.away_team_id
            self.state_changes.loser_id = self.home_team_id
        elif self.home_score > self.away_score:
            self.state_changes.winner_id = self.home_team_id
            self.state_changes.loser_id = self.away_team_id
        else:
            self.state_changes.is_tie = True
    
    def get_winner_id(self) -> Optional[int]:
        """Get the ID of the winning team, None if tie"""
        return self.state_changes.winner_id
    
    def get_loser_id(self) -> Optional[int]:
        """Get the ID of the losing team, None if tie"""
        return self.state_changes.loser_id
    
    def is_tie_game(self) -> bool:
        """Check if the game ended in a tie"""
        return self.state_changes.is_tie
    
    def get_final_score_string(self) -> str:
        """Get formatted final score string"""
        return f"Away {self.away_score} - {self.home_score} Home"
    
    def get_team_stats(self, team_id: int) -> Optional[TeamGameStats]:
        """Get team statistics for a specific team"""
        return self.team_stats.get(team_id)
    
    def get_player_stats_for_team(self, team_id: int) -> List[PlayerGameStats]:
        """Get all player statistics for a specific team"""
        return [stats for stats in self.player_stats if stats.team_id == team_id]
    
    def add_key_play(self, description: str) -> None:
        """Add a key play to the game narrative"""
        self.key_plays.append(description)
    
    def add_highlight(self, description: str) -> None:
        """Add a highlight to the game"""
        self.game_highlights.append(description)
    
    def add_turning_point(self, description: str) -> None:
        """Add a turning point to the game narrative"""
        self.turning_points.append(description)
    
    def get_game_summary(self) -> str:
        """Get comprehensive game summary"""
        winner_str = "TIE" if self.is_tie_game() else f"Winner: Team {self.get_winner_id()}"
        return (f"Game: Team {self.away_team_id} @ Team {self.home_team_id} - "
                f"{self.get_final_score_string()} - {winner_str} - "
                f"{self.total_plays} plays, {self.game_duration_minutes} minutes")
    
    def requires_standings_update(self) -> bool:
        """Check if this game requires standings updates"""
        return self.season_type in ["regular_season", "playoffs"] and self.success
    
    def requires_player_stat_updates(self) -> bool:
        """Check if this game requires player statistics updates"""
        return bool(self.player_stats) and self.success
    
    def requires_injury_processing(self) -> bool:
        """Check if this game has injuries that need processing"""
        return bool(self.state_changes.player_injuries) and self.success