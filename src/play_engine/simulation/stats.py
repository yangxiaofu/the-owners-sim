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
    player_id: Optional[int] = None  # Unique player ID for real players
    player_attributes: Optional[Dict[str, int]] = None  # Real player ratings/attributes
    
    # Rushing stats
    carries: int = 0
    rushing_yards: int = 0
    
    # Passing stats (QB)
    pass_attempts: int = 0
    completions: int = 0
    passing_yards: int = 0
    passing_tds: int = 0
    interceptions_thrown: int = 0
    sacks_taken: int = 0
    sack_yards_lost: int = 0
    qb_hits_taken: int = 0
    pressures_faced: int = 0
    air_yards: int = 0
    
    # Receiving stats (WR/TE)
    targets: int = 0
    receptions: int = 0
    receiving_yards: int = 0
    receiving_tds: int = 0
    drops: int = 0
    yac: int = 0
    
    # Blocking stats (OL)
    blocks_made: int = 0
    blocks_missed: int = 0
    pass_blocks: int = 0
    pressures_allowed: int = 0
    sacks_allowed: int = 0
    
    # Defensive stats  
    tackles: int = 0
    assisted_tackles: int = 0
    sacks: float = 0  # Changed to float for split sacks
    tackles_for_loss: int = 0
    qb_hits: int = 0
    qb_pressures: int = 0
    qb_hurries: int = 0
    
    # Pass defense stats
    passes_defended: int = 0
    passes_deflected: int = 0
    tipped_passes: int = 0
    interceptions: int = 0
    forced_fumbles: int = 0
    
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
            # Rushing stats
            'carries', 'rushing_yards',
            # Passing stats (QB)  
            'pass_attempts', 'completions', 'passing_yards', 'passing_tds', 'interceptions_thrown',
            'sacks_taken', 'sack_yards_lost', 'qb_hits_taken', 'pressures_faced', 'air_yards',
            # Receiving stats (WR/TE)
            'targets', 'receptions', 'receiving_yards', 'receiving_tds', 'drops', 'yac',
            # Blocking stats (OL)
            'blocks_made', 'blocks_missed', 'pass_blocks', 'pressures_allowed', 'sacks_allowed',
            # Defensive stats
            'tackles', 'assisted_tackles', 'sacks', 'tackles_for_loss', 'qb_hits', 'qb_pressures', 'qb_hurries',
            # Pass defense stats  
            'passes_defended', 'passes_deflected', 'tipped_passes', 'interceptions', 'forced_fumbles',
            # Special stats
            'penalties', 'penalty_yards'
        }
        
        stats = {}
        for field_name, value in self.__dict__.items():
            if field_name in stat_fields and isinstance(value, (int, float)) and value != 0:
                stats[field_name] = value
        return stats
    
    def get_player_attribute(self, attribute_name: str, default: int = 75) -> int:
        """Get a specific player attribute/rating"""
        if self.player_attributes:
            return self.player_attributes.get(attribute_name, default)
        return default
    
    def is_real_player(self) -> bool:
        """Check if this is a real NFL player (has player_id)"""
        return self.player_id is not None
    
    def get_player_summary(self) -> str:
        """Get enhanced player summary with attributes for real players"""
        base_info = f"#{self.player_number} {self.player_name} ({self.position})"
        if self.is_real_player():
            overall = self.get_player_attribute('overall')
            base_info += f" - {overall} OVR"
        return base_info


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
    
    def get_passing_leader(self) -> PlayerStats:
        """Get quarterback with most passing yards this play"""
        passers = [stats for stats in self.player_stats if stats.pass_attempts > 0]
        if not passers:
            return None
        return max(passers, key=lambda x: x.passing_yards)
    
    def get_receiving_leader(self) -> PlayerStats:
        """Get player with most receiving yards this play"""
        receivers = [stats for stats in self.player_stats if stats.receptions > 0]
        if not receivers:
            return None
        return max(receivers, key=lambda x: x.receiving_yards)
    
    def get_pass_rush_leader(self) -> PlayerStats:
        """Get player with most pass rush stats (sacks/pressures) this play"""
        rushers = [stats for stats in self.player_stats if stats.sacks > 0 or stats.qb_pressures > 0 or stats.qb_hits > 0]
        if not rushers:
            return None
        return max(rushers, key=lambda x: x.sacks * 2 + x.qb_hits * 1.5 + x.qb_pressures)
    
    def get_pass_defense_leader(self) -> PlayerStats:
        """Get player with most pass defense stats this play"""
        defenders = [stats for stats in self.player_stats if stats.interceptions > 0 or stats.passes_defended > 0]
        if not defenders:
            return None
        return max(defenders, key=lambda x: x.interceptions * 3 + x.passes_defended)
    
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
    
    def get_real_players_summary(self) -> List[Dict[str, Any]]:
        """Get summary of real players who participated in this play"""
        real_players = []
        for stats in self.player_stats:
            if stats.is_real_player():
                real_players.append({
                    'name': stats.player_name,
                    'number': stats.player_number,
                    'position': stats.position,
                    'overall_rating': stats.get_player_attribute('overall'),
                    'key_stats': stats.get_total_stats()
                })
        return real_players
    
    def get_attribute_impact_summary(self) -> Dict[str, str]:
        """Analyze how player attributes may have impacted this play"""
        impacts = []
        
        # Analyze rushing performance vs player ratings
        rushing_leader = self.get_rushing_leader()
        if rushing_leader and rushing_leader.is_real_player():
            overall_rating = rushing_leader.get_player_attribute('overall')
            if rushing_leader.rushing_yards > 5 and overall_rating > 85:
                impacts.append(f"High-rated RB {rushing_leader.player_name} ({overall_rating} OVR) delivered expected performance with {rushing_leader.rushing_yards} yards")
            elif rushing_leader.rushing_yards <= 2 and overall_rating > 85:
                impacts.append(f"Elite RB {rushing_leader.player_name} ({overall_rating} OVR) was held below expectation ({rushing_leader.rushing_yards} yards)")
        
        # Analyze defensive performance
        leading_tackler = self.get_leading_tackler()
        if leading_tackler and leading_tackler.is_real_player():
            overall_rating = leading_tackler.get_player_attribute('overall')
            total_tackles = leading_tackler.tackles + leading_tackler.assisted_tackles
            if total_tackles > 0 and overall_rating > 85:
                impacts.append(f"Elite defender {leading_tackler.player_name} ({overall_rating} OVR) made key tackle")
        
        return {'attribute_impacts': impacts}


def create_player_stats_from_player(player) -> PlayerStats:
    """Create PlayerStats object from existing Player object"""
    # Check if this is a real player (has attributes from real data)
    player_id = None
    player_attributes = None
    
    # Real players will have more comprehensive attributes
    if hasattr(player, 'ratings') and player.ratings:
        # This is likely a real player - extract ID if available
        # For now, use a hash of name+number as pseudo-ID since real player_id 
        # isn't directly accessible from Player object
        player_id = hash(f"{player.name}_{player.number}") % 10000
        player_attributes = player.ratings.copy()
    
    return PlayerStats(
        player_name=player.name,
        player_number=player.number, 
        position=player.primary_position,
        player_id=player_id,
        player_attributes=player_attributes
    )