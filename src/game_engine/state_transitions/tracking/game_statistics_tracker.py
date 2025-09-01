"""
Game Statistics Tracker - Comprehensive statistics collection and analysis

This module provides complete separation of statistics tracking from game logic,
allowing for deep analysis of game performance without coupling to core game state.

The tracker observes PlayResults and state transitions to build comprehensive
statistical profiles including:
- Play type distributions and effectiveness  
- Clock management patterns
- Field position analytics
- Scoring efficiency
- Player performance metrics
- Situational analysis

Design Principles:
- Observer pattern: tracks but never modifies game state
- Immutable statistics: all metrics are read-only snapshots
- Clean interfaces: easy to query and extend
- Performance optimized: minimal overhead during game execution
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, DefaultDict, Tuple, Any
from collections import defaultdict
from enum import Enum
import statistics
import time

from ..data_structures.game_state_transition import GameStateTransition
from ...plays.data_structures import PlayResult


class GamePhase(Enum):
    """Different phases of the game for contextual statistics"""
    FIRST_QUARTER = "first_quarter"
    SECOND_QUARTER = "second_quarter"  
    THIRD_QUARTER = "third_quarter"
    FOURTH_QUARTER = "fourth_quarter"
    OVERTIME = "overtime"
    TWO_MINUTE_WARNING = "two_minute_warning"
    RED_ZONE = "red_zone"
    GOAL_LINE = "goal_line"


@dataclass
class PlayTypeStats:
    """Comprehensive statistics for a specific play type"""
    total_attempts: int = 0
    total_yards: int = 0
    total_time_used: float = 0.0
    touchdowns: int = 0
    turnovers: int = 0
    first_downs: int = 0
    negative_plays: int = 0
    big_plays: int = 0  # 20+ yards
    explosive_plays: int = 0  # 40+ yards
    
    # Efficiency metrics
    success_rate: float = 0.0  # Based on down/distance context
    yards_per_attempt: float = 0.0
    time_per_attempt: float = 0.0
    
    # Advanced metrics
    yards_by_down: Dict[int, List[int]] = field(default_factory=lambda: defaultdict(list))
    success_by_down: Dict[int, List[bool]] = field(default_factory=lambda: defaultdict(list))
    yards_by_distance: Dict[str, List[int]] = field(default_factory=lambda: defaultdict(list))  # short/medium/long
    
    def update(self, play_result: PlayResult) -> None:
        """Update statistics with new play result"""
        self.total_attempts += 1
        self.total_yards += play_result.yards_gained
        self.total_time_used += play_result.time_elapsed
        
        if play_result.is_score and play_result.score_points == 6:
            self.touchdowns += 1
        if play_result.is_turnover:
            self.turnovers += 1
        if play_result.down_conversion:
            self.first_downs += 1
        if play_result.yards_gained < 0:
            self.negative_plays += 1
        if play_result.big_play:
            self.big_plays += 1
        if play_result.explosive_play:
            self.explosive_plays += 1
            
        # Track by down
        self.yards_by_down[play_result.down].append(play_result.yards_gained)
        
        # Determine success based on NFL standards
        success = self._calculate_play_success(play_result)
        self.success_by_down[play_result.down].append(success)
        
        # Track by distance category
        distance_category = self._categorize_distance(play_result.distance)
        self.yards_by_distance[distance_category].append(play_result.yards_gained)
        
        # Recalculate efficiency metrics
        self._recalculate_metrics()
    
    def _calculate_play_success(self, play_result: PlayResult) -> bool:
        """NFL success rate definition based on down/distance/yards"""
        if play_result.is_score or play_result.down_conversion:
            return True
            
        yards_needed = play_result.distance
        yards_gained = play_result.yards_gained
        down = play_result.down
        
        # NFL success rate standards
        if down == 1:
            return yards_gained >= yards_needed * 0.5  # 50% of distance
        elif down == 2:
            return yards_gained >= yards_needed * 0.7  # 70% of distance  
        elif down in [3, 4]:
            return yards_gained >= yards_needed  # Must convert
            
        return False
    
    def _categorize_distance(self, distance: int) -> str:
        """Categorize yards to go for strategic analysis"""
        if distance <= 3:
            return "short"
        elif distance <= 7:
            return "medium"
        else:
            return "long"
    
    def _recalculate_metrics(self) -> None:
        """Recalculate derived metrics"""
        if self.total_attempts > 0:
            self.yards_per_attempt = self.total_yards / self.total_attempts
            self.time_per_attempt = self.total_time_used / self.total_attempts
            
            # Calculate overall success rate
            total_successes = sum(
                sum(successes) for successes in self.success_by_down.values()
            )
            total_attempts = sum(
                len(successes) for successes in self.success_by_down.values()
            )
            self.success_rate = total_successes / total_attempts if total_attempts > 0 else 0.0


@dataclass 
class DriveStats:
    """Statistics for individual offensive drives"""
    start_field_position: int
    start_time: int
    end_field_position: Optional[int] = None
    end_time: Optional[int] = None
    plays: List[PlayResult] = field(default_factory=list)
    result: Optional[str] = None  # "touchdown", "field_goal", "punt", "turnover", "end_of_half"
    
    @property
    def duration(self) -> Optional[int]:
        """Drive duration in seconds"""
        if self.end_time is not None:
            return self.start_time - self.end_time
        return None
    
    @property
    def total_yards(self) -> int:
        """Net yards gained during drive"""
        return sum(play.yards_gained for play in self.plays)
    
    @property
    def play_count(self) -> int:
        """Number of plays in drive"""
        return len(self.plays)


@dataclass
class SituationalStats:
    """Statistics broken down by game situation"""
    red_zone: PlayTypeStats = field(default_factory=PlayTypeStats)
    goal_line: PlayTypeStats = field(default_factory=PlayTypeStats)  
    two_minute_drill: PlayTypeStats = field(default_factory=PlayTypeStats)
    third_down: PlayTypeStats = field(default_factory=PlayTypeStats)
    fourth_down: PlayTypeStats = field(default_factory=PlayTypeStats)
    
    # Field position zones
    own_territory: PlayTypeStats = field(default_factory=PlayTypeStats)  # Own 1-49
    opponent_territory: PlayTypeStats = field(default_factory=PlayTypeStats)  # Opp 49-21
    scoring_zone: PlayTypeStats = field(default_factory=PlayTypeStats)  # Opp 20-1


@dataclass
class GameStatisticsSummary:
    """Final comprehensive game statistics"""
    # Basic game info
    total_plays: int = 0
    total_time_used: float = 0.0
    game_duration_real_time: float = 0.0
    
    # Play type breakdown
    play_type_stats: Dict[str, PlayTypeStats] = field(default_factory=dict)
    
    # Team-specific statistics
    team_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Situational analysis
    situational_stats: SituationalStats = field(default_factory=SituationalStats)
    
    # Drive analysis
    drives: List[DriveStats] = field(default_factory=list)
    
    # Clock management
    clock_stats: Dict[str, float] = field(default_factory=dict)
    
    # Efficiency metrics
    third_down_conversion_rate: float = 0.0
    fourth_down_conversion_rate: float = 0.0
    red_zone_efficiency: float = 0.0
    turnover_differential: int = 0
    
    # Performance metrics
    avg_yards_per_play: float = 0.0
    plays_per_minute: float = 0.0
    time_of_possession: Dict[str, float] = field(default_factory=dict)


class GameStatisticsTracker:
    """
    Comprehensive game statistics tracker that observes but never modifies game state.
    
    This tracker builds a complete statistical profile of the game including:
    - Play-by-play performance metrics
    - Situational effectiveness analysis  
    - Clock management patterns
    - Drive efficiency tracking
    - Player contribution metrics
    
    The tracker operates as a pure observer - it receives PlayResults and transitions
    but never modifies game state, maintaining clean separation of concerns.
    """
    
    def __init__(self, home_team_id: str, away_team_id: str):
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.game_start_time = time.time()
        
        # Core statistics tracking
        self.play_type_stats: Dict[str, PlayTypeStats] = defaultdict(PlayTypeStats)
        self.situational_stats = SituationalStats()
        self.drives: List[DriveStats] = []
        self.current_drive: Optional[DriveStats] = None
        
        # Team-specific tracking
        self.team_stats: Dict[str, Dict[str, Any]] = {
            home_team_id: self._init_team_stats(),
            away_team_id: self._init_team_stats()
        }
        
        # Clock and performance tracking
        self.total_plays = 0
        self.total_time_used = 0.0
        self.clock_usage_by_type: Dict[str, List[float]] = defaultdict(list)
        
        # Advanced metrics
        self.possession_history: List[Tuple[str, int, int]] = []  # (team, start_time, field_pos)
        self.score_history: List[Tuple[int, str, int, str]] = []  # (quarter, team, points, play_type)
        
    def _init_team_stats(self) -> Dict[str, Any]:
        """Initialize team-specific statistics structure"""
        return {
            "plays": 0,
            "yards": 0,
            "time_of_possession": 0.0,
            "turnovers": 0,
            "scores": 0,
            "first_downs": 0,
            "third_downs_attempted": 0,
            "third_downs_converted": 0,
            "fourth_downs_attempted": 0, 
            "fourth_downs_converted": 0,
            "red_zone_attempts": 0,
            "red_zone_scores": 0,
            "drives": 0,
            "avg_drive_length": 0.0,
            "avg_drive_time": 0.0
        }
    
    def start_new_drive(self, team_id: str, field_position: int, game_time: int) -> None:
        """Start tracking a new offensive drive"""
        # End previous drive if exists
        if self.current_drive:
            self.current_drive.end_time = game_time
            self.drives.append(self.current_drive)
        
        # Start new drive
        self.current_drive = DriveStats(
            start_field_position=field_position,
            start_time=game_time
        )
        self.team_stats[team_id]["drives"] += 1
        
    def record_play(self, play_result: PlayResult, possession_team_id: str) -> None:
        """
        Record a play result and update all relevant statistics.
        
        This is the main entry point for play-by-play tracking.
        """
        self.total_plays += 1
        self.total_time_used += play_result.time_elapsed
        
        # Update play type statistics
        play_type = play_result.play_type
        self.play_type_stats[play_type].update(play_result)
        self.clock_usage_by_type[play_type].append(play_result.time_elapsed)
        
        # Update team statistics
        team_stats = self.team_stats[possession_team_id]
        team_stats["plays"] += 1
        team_stats["yards"] += play_result.yards_gained
        team_stats["time_of_possession"] += play_result.time_elapsed
        
        if play_result.is_turnover:
            team_stats["turnovers"] += 1
        if play_result.is_score:
            team_stats["scores"] += 1
        if play_result.down_conversion:
            team_stats["first_downs"] += 1
            
        # Track down-specific conversions
        if play_result.down == 3:
            team_stats["third_downs_attempted"] += 1
            if play_result.down_conversion or play_result.is_score:
                team_stats["third_downs_converted"] += 1
        elif play_result.down == 4:
            team_stats["fourth_downs_attempted"] += 1
            if play_result.down_conversion or play_result.is_score:
                team_stats["fourth_downs_converted"] += 1
                
        # Track red zone efficiency
        if play_result.red_zone_play:
            team_stats["red_zone_attempts"] += 1
            if play_result.is_score:
                team_stats["red_zone_scores"] += 1
        
        # Update situational statistics
        self._update_situational_stats(play_result)
        
        # Update current drive
        if self.current_drive:
            self.current_drive.plays.append(play_result)
            
        # Record scoring plays
        if play_result.is_score:
            self.score_history.append((
                play_result.quarter,
                possession_team_id, 
                play_result.score_points,
                play_result.play_type
            ))
    
    def _update_situational_stats(self, play_result: PlayResult) -> None:
        """Update situational statistics based on play context"""
        if play_result.red_zone_play:
            self.situational_stats.red_zone.update(play_result)
            
        if play_result.goal_line_play:
            self.situational_stats.goal_line.update(play_result)
            
        if play_result.two_minute_drill:
            self.situational_stats.two_minute_drill.update(play_result)
            
        if play_result.down == 3:
            self.situational_stats.third_down.update(play_result)
        elif play_result.down == 4:
            self.situational_stats.fourth_down.update(play_result)
            
        # Field position zones
        field_pos = play_result.field_position
        if field_pos <= 49:  # Own territory
            self.situational_stats.own_territory.update(play_result)
        elif field_pos <= 79:  # Opponent territory
            self.situational_stats.opponent_territory.update(play_result)
        else:  # Scoring zone (opponent 20-1)
            self.situational_stats.scoring_zone.update(play_result)
    
    def record_transition(self, transition: GameStateTransition) -> None:
        """
        Record a state transition for audit and analysis purposes.
        
        This allows tracking of all game state changes for replay/debugging.
        """
        # This can be expanded to track specific transition types
        # For now, we focus on possession changes for drive tracking
        pass
    
    def get_current_summary(self) -> GameStatisticsSummary:
        """Generate current game statistics summary"""
        # Finalize current drive if exists
        if self.current_drive:
            self.drives.append(self.current_drive)
            self.current_drive = None
            
        # Calculate clock statistics 
        clock_stats = self._calculate_clock_stats()
        
        # Calculate efficiency metrics
        efficiency_metrics = self._calculate_efficiency_metrics()
        
        # Update team averages
        self._update_team_averages()
        
        summary = GameStatisticsSummary(
            total_plays=self.total_plays,
            total_time_used=self.total_time_used,
            game_duration_real_time=time.time() - self.game_start_time,
            play_type_stats=dict(self.play_type_stats),
            team_stats=self.team_stats,
            situational_stats=self.situational_stats,
            drives=self.drives.copy(),
            clock_stats=clock_stats,
            **efficiency_metrics
        )
        
        return summary
    
    def _calculate_clock_stats(self) -> Dict[str, float]:
        """Calculate comprehensive clock management statistics"""
        if self.total_plays == 0:
            return {}
            
        clock_stats = {
            "avg_per_play": self.total_time_used / self.total_plays,
            "total_clock_used": self.total_time_used,
            "plays_per_minute": self.total_plays / (self.total_time_used / 60) if self.total_time_used > 0 else 0
        }
        
        # Calculate averages by play type
        for play_type, times in self.clock_usage_by_type.items():
            if times:
                clock_stats[f"{play_type}_avg"] = statistics.mean(times)
                clock_stats[f"{play_type}_count"] = len(times)
                
        return clock_stats
    
    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate advanced efficiency metrics"""
        metrics = {}
        
        # Third down efficiency
        total_third_attempts = sum(team["third_downs_attempted"] for team in self.team_stats.values())
        total_third_conversions = sum(team["third_downs_converted"] for team in self.team_stats.values())
        metrics["third_down_conversion_rate"] = (
            total_third_conversions / total_third_attempts if total_third_attempts > 0 else 0.0
        )
        
        # Fourth down efficiency  
        total_fourth_attempts = sum(team["fourth_downs_attempted"] for team in self.team_stats.values())
        total_fourth_conversions = sum(team["fourth_downs_converted"] for team in self.team_stats.values())
        metrics["fourth_down_conversion_rate"] = (
            total_fourth_conversions / total_fourth_attempts if total_fourth_attempts > 0 else 0.0
        )
        
        # Red zone efficiency
        total_rz_attempts = sum(team["red_zone_attempts"] for team in self.team_stats.values())
        total_rz_scores = sum(team["red_zone_scores"] for team in self.team_stats.values())
        metrics["red_zone_efficiency"] = (
            total_rz_scores / total_rz_attempts if total_rz_attempts > 0 else 0.0
        )
        
        # Turnover differential (home team perspective)
        home_turnovers = self.team_stats[self.home_team_id]["turnovers"]
        away_turnovers = self.team_stats[self.away_team_id]["turnovers"]
        metrics["turnover_differential"] = away_turnovers - home_turnovers
        
        # Overall efficiency
        total_yards = sum(team["yards"] for team in self.team_stats.values())
        metrics["avg_yards_per_play"] = total_yards / self.total_plays if self.total_plays > 0 else 0.0
        
        # Time of possession (percentage)
        if self.total_time_used > 0:
            metrics["time_of_possession"] = {
                self.home_team_id: (self.team_stats[self.home_team_id]["time_of_possession"] / self.total_time_used) * 100,
                self.away_team_id: (self.team_stats[self.away_team_id]["time_of_possession"] / self.total_time_used) * 100
            }
        
        return metrics
    
    def _update_team_averages(self) -> None:
        """Update team-specific average statistics"""
        for team_id, stats in self.team_stats.items():
            team_drives = [drive for drive in self.drives if True]  # TODO: track drive team
            
            if team_drives:
                stats["avg_drive_length"] = statistics.mean([drive.total_yards for drive in team_drives])
                drive_durations = [drive.duration for drive in team_drives if drive.duration is not None]
                if drive_durations:
                    stats["avg_drive_time"] = statistics.mean(drive_durations)
    
    def get_play_type_analysis(self, play_type: str) -> Optional[PlayTypeStats]:
        """Get detailed analysis for a specific play type"""
        return self.play_type_stats.get(play_type)
    
    def get_situational_analysis(self) -> SituationalStats:
        """Get situational effectiveness analysis"""
        return self.situational_stats
    
    def get_team_comparison(self) -> Dict[str, Any]:
        """Get comparative analysis between teams"""
        home_stats = self.team_stats[self.home_team_id]
        away_stats = self.team_stats[self.away_team_id]
        
        return {
            "total_yards": {
                self.home_team_id: home_stats["yards"],
                self.away_team_id: away_stats["yards"],
                "differential": home_stats["yards"] - away_stats["yards"]
            },
            "time_of_possession": {
                self.home_team_id: home_stats["time_of_possession"],
                self.away_team_id: away_stats["time_of_possession"],
                "differential": home_stats["time_of_possession"] - away_stats["time_of_possession"]
            },
            "turnovers": {
                self.home_team_id: home_stats["turnovers"],
                self.away_team_id: away_stats["turnovers"], 
                "differential": away_stats["turnovers"] - home_stats["turnovers"]
            },
            "third_down_efficiency": {
                self.home_team_id: home_stats["third_downs_converted"] / home_stats["third_downs_attempted"] if home_stats["third_downs_attempted"] > 0 else 0,
                self.away_team_id: away_stats["third_downs_converted"] / away_stats["third_downs_attempted"] if away_stats["third_downs_attempted"] > 0 else 0
            }
        }
        
    def reset(self) -> None:
        """Reset all statistics for a new game"""
        self.__init__(self.home_team_id, self.away_team_id)