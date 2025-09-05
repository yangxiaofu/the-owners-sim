"""
Player statistics tracking for individual play simulation

Tracks individual player contributions during play execution including
rushing, blocking, tackling, and other position-specific statistics.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class PlayerStats:
    """Individual player statistics for a single play"""
    player_name: str
    player_number: int
    position: str
    
    # Offensive stats
    carries: int = 0
    rushing_yards: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    blocks_made: int = 0
    blocks_missed: int = 0
    
    # Defensive stats  
    tackles: int = 0
    assisted_tackles: int = 0
    sacks: int = 0
    tackles_for_loss: int = 0
    
    # Special stats
    penalties: int = 0
    penalty_yards: int = 0
    
    def add_carry(self, yards: int):
        """Add rushing attempt and yards"""
        self.carries += 1
        self.rushing_yards += yards
    
    def add_tackle(self, assisted: bool = False):
        """Add tackle (solo or assisted)"""
        if assisted:
            self.assisted_tackles += 1
        else:
            self.tackles += 1
    
    def add_block(self, successful: bool = True):
        """Add blocking attempt"""
        if successful:
            self.blocks_made += 1
        else:
            self.blocks_missed += 1
    
    def add_penalty(self, yards: int):
        """Add penalty and yardage"""
        self.penalties += 1
        self.penalty_yards += yards
    
    def get_total_stats(self) -> Dict[str, int]:
        """Get all non-zero stats as dictionary"""
        stat_fields = {
            'carries', 'rushing_yards', 'receptions', 'receiving_yards',
            'blocks_made', 'blocks_missed', 'tackles', 'assisted_tackles',
            'sacks', 'tackles_for_loss', 'penalties', 'penalty_yards'
        }
        
        stats = {}
        for field_name, value in self.__dict__.items():
            if field_name in stat_fields and isinstance(value, int) and value != 0:
                stats[field_name] = value
        return stats


@dataclass
class PlayStatsSummary:
    """Summary of all player statistics for a single play with penalty information"""
    play_type: str
    yards_gained: int
    time_elapsed: float
    player_stats: List[PlayerStats] = field(default_factory=list)
    
    # Penalty information
    penalty_occurred: bool = False
    penalty_instance: Optional[object] = None  # PenaltyInstance object
    original_yards: Optional[int] = None  # Yards before penalty
    play_negated: bool = False
    
    def add_player_stats(self, stats: PlayerStats):
        """Add individual player stats to the play summary"""
        self.player_stats.append(stats)
    
    def get_players_with_stats(self) -> List[PlayerStats]:
        """Get only players who recorded statistics this play"""
        return [stats for stats in self.player_stats if stats.get_total_stats()]
    
    def get_stats_by_position(self, position: str) -> List[PlayerStats]:
        """Get stats for all players at a specific position"""
        return [stats for stats in self.player_stats if stats.position == position]
    
    def get_rushing_leader(self) -> PlayerStats:
        """Get player with most rushing yards this play"""
        rushers = [stats for stats in self.player_stats if stats.carries > 0]
        if not rushers:
            return None
        return max(rushers, key=lambda x: x.rushing_yards)
    
    def get_leading_tackler(self) -> PlayerStats:
        """Get player with most tackles this play"""
        tacklers = [stats for stats in self.player_stats if stats.tackles + stats.assisted_tackles > 0]
        if not tacklers:
            return None
        return max(tacklers, key=lambda x: x.tackles + x.assisted_tackles * 0.5)
    
    def get_penalty_summary(self) -> Optional[Dict[str, Any]]:
        """Get penalty summary for this play"""
        if not self.penalty_occurred or not self.penalty_instance:
            return None
        
        return {
            "penalty_type": getattr(self.penalty_instance, 'penalty_type', 'Unknown'),
            "penalized_player": f"#{getattr(self.penalty_instance, 'penalized_player_number', 0)} {getattr(self.penalty_instance, 'penalized_player_name', 'Unknown')}",
            "penalty_yards": getattr(self.penalty_instance, 'yards_assessed', 0),
            "original_play_yards": self.original_yards,
            "final_play_yards": self.yards_gained,
            "play_negated": self.play_negated,
            "context": getattr(self.penalty_instance, 'context_description', 'No context'),
            "automatic_first_down": getattr(self.penalty_instance, 'automatic_first_down', False)
        }
    
    def has_penalty(self) -> bool:
        """Check if this play had a penalty"""
        return self.penalty_occurred


def create_player_stats_from_player(player) -> PlayerStats:
    """Create PlayerStats object from existing Player object"""
    return PlayerStats(
        player_name=player.name,
        player_number=player.number, 
        position=player.primary_position
    )