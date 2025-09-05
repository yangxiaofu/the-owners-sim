"""
Penalty Data Structures and Statistics Tracking

Comprehensive data structures for tracking penalty information, including:
- Individual penalty instances with full context
- Player penalty statistics
- Team penalty tracking
- Game flow impact tracking
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class PenaltyInstance:
    """Represents a single penalty occurrence with full context"""
    
    penalty_type: str                    # "offensive_holding"
    penalized_player_name: str           # "John Smith"  
    penalized_player_number: int         # 67
    penalized_player_position: str       # "left_guard"
    team_penalized: str                  # "home" or "away"
    
    # Penalty impact
    yards_assessed: int                  # -10 for holding
    automatic_first_down: bool           # True/False
    automatic_loss_of_down: bool         # True/False 
    negated_play: bool                   # True if play result was negated
    
    # Game context
    quarter: int                         # 1-4, 5 for OT
    time_remaining: str                  # "8:43"
    down: int                           # 1-4
    distance: int                       # Yards to go
    field_position: int                 # Yards from own goal line (0-100)
    score_differential: int             # Points ahead/behind
    
    # Play context
    original_play_result: Optional[int] = None  # Yards gained before penalty
    final_play_result: int = 0          # Final result after penalty
    play_type: str = "run"              # "run", "pass", etc.
    formation_offensive: str = "i_formation"
    formation_defensive: str = "4_3_base"
    
    # Penalty details
    penalty_timing: str = "during_play"  # "pre_snap", "during_play", "post_play"
    context_description: str = ""       # "Holding while blocking inside zone run"
    referee_explanation: str = ""       # Official penalty description
    
    # Attribution details
    discipline_rating: int = 75         # Player's discipline at time of penalty
    composure_rating: int = 75          # Player's composure at time of penalty
    pressure_situation: bool = False    # Red zone, 4th down, etc.
    
    # Metadata
    penalty_id: str = field(default_factory=lambda: f"penalty_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}")
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PlayerPenaltyStats:
    """Comprehensive penalty statistics for a single player"""
    
    player_name: str
    player_number: int
    player_position: str
    
    # Overall penalty counts
    total_penalties: int = 0
    total_penalty_yards: int = 0
    
    # Penalty type breakdown
    penalty_counts: Dict[str, int] = field(default_factory=dict)
    penalty_yards: Dict[str, int] = field(default_factory=dict)
    
    # Situational penalty stats
    red_zone_penalties: int = 0
    fourth_down_penalties: int = 0
    two_minute_penalties: int = 0
    pre_snap_penalties: int = 0
    post_play_penalties: int = 0
    
    # Impact stats
    penalties_negating_positive_plays: int = 0
    penalties_giving_first_downs: int = 0
    penalty_yards_in_losses: int = 0
    penalty_yards_in_wins: int = 0
    
    # Recent penalties (last 5)
    recent_penalties: List[PenaltyInstance] = field(default_factory=list)
    
    def add_penalty(self, penalty: PenaltyInstance):
        """Add a penalty to this player's statistics"""
        self.total_penalties += 1
        self.total_penalty_yards += penalty.yards_assessed
        
        # Update penalty type counts
        penalty_type = penalty.penalty_type
        self.penalty_counts[penalty_type] = self.penalty_counts.get(penalty_type, 0) + 1
        self.penalty_yards[penalty_type] = self.penalty_yards.get(penalty_type, 0) + penalty.yards_assessed
        
        # Update situational stats
        if penalty.field_position >= 80:  # Red zone
            self.red_zone_penalties += 1
        if penalty.down == 4:
            self.fourth_down_penalties += 1
        if penalty.penalty_timing == "pre_snap":
            self.pre_snap_penalties += 1
        elif penalty.penalty_timing == "post_play":
            self.post_play_penalties += 1
            
        # Impact stats
        if penalty.negated_play and penalty.original_play_result and penalty.original_play_result > 0:
            self.penalties_negating_positive_plays += 1
        if penalty.automatic_first_down:
            self.penalties_giving_first_downs += 1
        
        # Keep track of recent penalties (last 5)
        self.recent_penalties.append(penalty)
        if len(self.recent_penalties) > 5:
            self.recent_penalties.pop(0)
    
    def get_penalty_rate(self, plays_total: int) -> float:
        """Get penalties per play rate"""
        if plays_total == 0:
            return 0.0
        return self.total_penalties / plays_total
    
    def get_most_common_penalty(self) -> Optional[str]:
        """Get the most common penalty type for this player"""
        if not self.penalty_counts:
            return None
        return max(self.penalty_counts, key=self.penalty_counts.get)
    
    def is_penalty_prone(self) -> bool:
        """Determine if player is penalty-prone (above average penalty rate)"""
        # This could be configurable, but for now use a simple threshold
        return self.total_penalties >= 5  # 5+ penalties indicates tendency
    
    def get_penalty_summary(self) -> Dict[str, Any]:
        """Get comprehensive penalty summary for this player"""
        return {
            "player_info": f"#{self.player_number} {self.player_name} ({self.player_position})",
            "total_penalties": self.total_penalties,
            "total_penalty_yards": self.total_penalty_yards,
            "most_common_penalty": self.get_most_common_penalty(),
            "situational_penalties": {
                "red_zone": self.red_zone_penalties,
                "fourth_down": self.fourth_down_penalties,
                "pre_snap": self.pre_snap_penalties,
                "post_play": self.post_play_penalties
            },
            "impact_stats": {
                "negated_positive_plays": self.penalties_negating_positive_plays,
                "gave_first_downs": self.penalties_giving_first_downs
            },
            "penalty_prone": self.is_penalty_prone()
        }


@dataclass
class TeamPenaltyStats:
    """Team-wide penalty statistics and tracking"""
    
    team_name: str
    
    # Overall team stats
    total_penalties: int = 0
    total_penalty_yards: int = 0
    opponent_penalty_yards: int = 0  # Penalty yards benefited from
    
    # Game splits
    penalties_at_home: int = 0
    penalties_away: int = 0
    penalty_yards_at_home: int = 0
    penalty_yards_away: int = 0
    
    # Situational team stats
    penalties_when_winning: int = 0
    penalties_when_losing: int = 0
    penalties_in_red_zone: int = 0
    penalties_on_third_down: int = 0
    penalties_in_fourth_quarter: int = 0
    
    # Impact on drives
    drives_killed_by_penalties: int = 0
    touchdowns_negated_by_penalties: int = 0
    first_downs_given_up_by_penalties: int = 0
    
    # Player penalty tracking
    player_penalties: Dict[str, PlayerPenaltyStats] = field(default_factory=dict)
    
    # Penalty instances for detailed analysis
    all_penalties: List[PenaltyInstance] = field(default_factory=list)
    
    def add_penalty(self, penalty: PenaltyInstance):
        """Add a penalty to team statistics"""
        self.total_penalties += 1
        self.total_penalty_yards += penalty.yards_assessed
        
        # Update player-specific stats
        player_key = f"{penalty.penalized_player_name}_{penalty.penalized_player_number}"
        if player_key not in self.player_penalties:
            self.player_penalties[player_key] = PlayerPenaltyStats(
                penalty.penalized_player_name,
                penalty.penalized_player_number,
                penalty.penalized_player_position
            )
        self.player_penalties[player_key].add_penalty(penalty)
        
        # Update situational stats
        if penalty.score_differential > 0:
            self.penalties_when_winning += 1
        elif penalty.score_differential < 0:
            self.penalties_when_losing += 1
            
        if penalty.field_position >= 80:
            self.penalties_in_red_zone += 1
        if penalty.down == 3:
            self.penalties_on_third_down += 1
        if penalty.quarter == 4:
            self.penalties_in_fourth_quarter += 1
        
        # Store for detailed analysis
        self.all_penalties.append(penalty)
    
    def get_penalty_rate_by_situation(self) -> Dict[str, float]:
        """Get penalty rates in different game situations"""
        total = max(1, self.total_penalties)  # Avoid division by zero
        
        return {
            "when_winning": self.penalties_when_winning / total,
            "when_losing": self.penalties_when_losing / total,
            "in_red_zone": self.penalties_in_red_zone / total,
            "on_third_down": self.penalties_on_third_down / total,
            "in_fourth_quarter": self.penalties_in_fourth_quarter / total
        }
    
    def get_most_penalized_players(self, limit: int = 5) -> List[PlayerPenaltyStats]:
        """Get players with the most penalties"""
        return sorted(
            self.player_penalties.values(),
            key=lambda x: x.total_penalties,
            reverse=True
        )[:limit]
    
    def get_home_away_penalty_differential(self) -> Dict[str, Any]:
        """Analyze home vs away penalty rates"""
        home_games = max(1, self.penalties_at_home)
        away_games = max(1, self.penalties_away)
        
        return {
            "penalties_per_game_home": self.penalties_at_home / home_games,
            "penalties_per_game_away": self.penalties_away / away_games,
            "penalty_yards_per_game_home": self.penalty_yards_at_home / home_games,
            "penalty_yards_per_game_away": self.penalty_yards_away / away_games,
            "home_field_advantage": (self.penalties_away - self.penalties_at_home) / max(1, self.penalties_at_home + self.penalties_away)
        }


@dataclass 
class GamePenaltyTracker:
    """Tracks all penalties in a single game"""
    
    game_id: str
    home_team: str
    away_team: str
    
    # Game-level penalty tracking
    all_penalties: List[PenaltyInstance] = field(default_factory=list)
    penalties_by_quarter: Dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0})
    penalty_yards_by_quarter: Dict[int, int] = field(default_factory=lambda: {1: 0, 2: 0, 3: 0, 4: 0})
    
    # Team penalty counts
    home_team_penalties: int = 0
    away_team_penalties: int = 0
    home_team_penalty_yards: int = 0
    away_team_penalty_yards: int = 0
    
    def add_penalty(self, penalty: PenaltyInstance):
        """Add penalty to game tracking"""
        self.all_penalties.append(penalty)
        
        # Update quarterly stats
        quarter = min(penalty.quarter, 4)  # Cap at 4 for OT
        self.penalties_by_quarter[quarter] += 1
        self.penalty_yards_by_quarter[quarter] += penalty.yards_assessed
        
        # Update team stats
        if penalty.team_penalized == "home":
            self.home_team_penalties += 1
            self.home_team_penalty_yards += penalty.yards_assessed
        else:
            self.away_team_penalties += 1
            self.away_team_penalty_yards += penalty.yards_assessed
    
    def get_game_penalty_summary(self) -> Dict[str, Any]:
        """Get comprehensive game penalty summary"""
        total_penalties = len(self.all_penalties)
        total_yards = sum(p.yards_assessed for p in self.all_penalties)
        
        return {
            "game_info": f"{self.away_team} @ {self.home_team}",
            "total_penalties": total_penalties,
            "total_penalty_yards": total_yards,
            "home_team_stats": {
                "penalties": self.home_team_penalties,
                "penalty_yards": self.home_team_penalty_yards
            },
            "away_team_stats": {
                "penalties": self.away_team_penalties, 
                "penalty_yards": self.away_team_penalty_yards
            },
            "penalties_by_quarter": self.penalties_by_quarter,
            "penalty_yards_by_quarter": self.penalty_yards_by_quarter,
            "most_common_penalties": self._get_most_common_penalties(),
            "biggest_impact_penalties": self._get_biggest_impact_penalties()
        }
    
    def _get_most_common_penalties(self) -> Dict[str, int]:
        """Get count of most common penalty types in game"""
        penalty_counts = {}
        for penalty in self.all_penalties:
            penalty_counts[penalty.penalty_type] = penalty_counts.get(penalty.penalty_type, 0) + 1
        
        # Return top 3
        return dict(sorted(penalty_counts.items(), key=lambda x: x[1], reverse=True)[:3])
    
    def _get_biggest_impact_penalties(self) -> List[Dict[str, Any]]:
        """Get penalties with biggest impact on game"""
        impact_penalties = []
        
        for penalty in self.all_penalties:
            impact_score = 0
            
            # High impact factors
            if penalty.automatic_first_down:
                impact_score += 3
            if penalty.negated_play and penalty.original_play_result and penalty.original_play_result > 10:
                impact_score += 3
            if abs(penalty.yards_assessed) >= 15:
                impact_score += 2
            if penalty.field_position >= 80:  # Red zone
                impact_score += 2
            if penalty.quarter >= 4:  # Fourth quarter or OT
                impact_score += 2
            
            if impact_score >= 3:
                impact_penalties.append({
                    "penalty": penalty,
                    "impact_score": impact_score,
                    "description": f"{penalty.penalty_type} on #{penalty.penalized_player_number} {penalty.penalized_player_name}"
                })
        
        # Return top 3 by impact score
        return sorted(impact_penalties, key=lambda x: x["impact_score"], reverse=True)[:3]