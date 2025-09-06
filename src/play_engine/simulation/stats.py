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
    
    # Special teams stats (field goals, punts, kicks)
    field_goal_attempts: int = 0
    field_goals_made: int = 0
    field_goals_missed: int = 0
    field_goals_blocked: int = 0
    longest_field_goal: int = 0
    field_goal_holds: int = 0
    long_snaps: int = 0
    special_teams_snaps: int = 0
    blocks_allowed: int = 0
    
    # Additional passing stats for holders on fake field goals
    passing_touchdowns: int = 0
    rushing_touchdowns: int = 0
    
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
            # Special teams stats
            'field_goal_attempts', 'field_goals_made', 'field_goals_missed', 'field_goals_blocked',
            'longest_field_goal', 'field_goal_holds', 'long_snaps', 'special_teams_snaps', 'blocks_allowed',
            'passing_touchdowns', 'rushing_touchdowns',
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
    
    # Field goal specific information (optional, only populated for field goal plays)
    field_goal_outcome: Optional[str] = None  # "made", "missed_wide_left", "blocked", "fake_success", etc.
    is_fake_field_goal: bool = False
    fake_field_goal_type: Optional[str] = None  # "pass" or "run" if fake
    field_goal_distance: Optional[int] = None
    points_scored: int = 0  # 3 for made FG, 6 for fake TD, etc.
    
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
    
    # Field goal specific methods
    def get_kicker_stats(self) -> Optional[PlayerStats]:
        """Get kicker's stats for this play"""
        kickers = [stats for stats in self.player_stats if 'field_goal_attempts' in stats.get_total_stats() or 'field_goals_made' in stats.get_total_stats()]
        return kickers[0] if kickers else None
    
    def get_holder_stats(self) -> Optional[PlayerStats]:
        """Get holder's stats for this play"""
        holders = [stats for stats in self.player_stats if 'field_goal_holds' in stats.get_total_stats()]
        return holders[0] if holders else None
    
    def get_special_teams_stats(self) -> List[PlayerStats]:
        """Get all special teams players who recorded stats this play"""
        special_teams = [stats for stats in self.player_stats if 
                        'special_teams_snaps' in stats.get_total_stats() or 
                        'long_snaps' in stats.get_total_stats() or
                        'field_goal_holds' in stats.get_total_stats() or
                        'field_goal_attempts' in stats.get_total_stats()]
        return special_teams
    
    def is_field_goal_play(self) -> bool:
        """Check if this is a field goal play"""
        return self.field_goal_outcome is not None
    
    def was_field_goal_successful(self) -> bool:
        """Check if field goal was successful (made or successful fake)"""
        return self.field_goal_outcome in ["made", "fake_success"] or self.points_scored > 0
    
    def get_field_goal_summary(self) -> Optional[Dict[str, Any]]:
        """Get field goal specific summary information"""
        if not self.is_field_goal_play():
            return None
        
        summary = {
            "outcome": self.field_goal_outcome,
            "distance": self.field_goal_distance,
            "points_scored": self.points_scored,
            "is_fake": self.is_fake_field_goal,
            "successful": self.was_field_goal_successful()
        }
        
        if self.is_fake_field_goal:
            summary["fake_type"] = self.fake_field_goal_type
            
        return summary


class PlayerStatsAccumulator:
    """
    Accumulates individual player statistics across multiple plays within a game.
    
    Handles merging player stats from PlayStatsSummary objects into running game totals.
    Provides query methods for accessing accumulated player statistics.
    """
    
    def __init__(self, game_identifier: Optional[str] = None):
        """
        Initialize accumulator for tracking player stats across a game.
        
        Args:
            game_identifier: Optional identifier for this game (e.g., "Browns_vs_49ers_Q1")
        """
        self.game_id = game_identifier
        self._player_totals: Dict[str, PlayerStats] = {}
        self._plays_processed = 0
    
    def add_play_stats(self, play_summary: PlayStatsSummary) -> None:
        """
        Accumulate player stats from a single play into running game totals.
        
        Args:
            play_summary: PlayStatsSummary containing all player stats from one play
        """
        self._plays_processed += 1
        
        # Process each player's stats from the play
        for player_stats in play_summary.player_stats:
            if player_stats.get_total_stats():  # Only accumulate players with actual stats
                self._merge_player_stats(player_stats)
    
    def _merge_player_stats(self, incoming_stats: PlayerStats) -> None:
        """
        Merge incoming player stats into accumulated totals.
        
        Args:
            incoming_stats: PlayerStats from a single play to merge into totals
        """
        # Create unique key for this player
        player_key = f"{incoming_stats.player_name}_{incoming_stats.position}"
        
        if player_key not in self._player_totals:
            # First time seeing this player - create new accumulated stats
            self._player_totals[player_key] = PlayerStats(
                player_name=incoming_stats.player_name,
                player_number=incoming_stats.player_number,
                position=incoming_stats.position,
                player_id=incoming_stats.player_id,
                player_attributes=incoming_stats.player_attributes
            )
        
        # Accumulate stats into existing totals
        existing = self._player_totals[player_key]
        
        # Rushing stats - sum totals
        existing.carries += incoming_stats.carries
        existing.rushing_yards += incoming_stats.rushing_yards
        
        # Passing stats - sum totals
        existing.pass_attempts += incoming_stats.pass_attempts
        existing.completions += incoming_stats.completions
        existing.passing_yards += incoming_stats.passing_yards
        existing.passing_tds += incoming_stats.passing_tds
        existing.interceptions_thrown += incoming_stats.interceptions_thrown
        existing.sacks_taken += incoming_stats.sacks_taken
        existing.sack_yards_lost += incoming_stats.sack_yards_lost
        existing.qb_hits_taken += incoming_stats.qb_hits_taken
        existing.pressures_faced += incoming_stats.pressures_faced
        existing.air_yards += incoming_stats.air_yards
        existing.passing_touchdowns += incoming_stats.passing_touchdowns
        existing.rushing_touchdowns += incoming_stats.rushing_touchdowns
        
        # Receiving stats - sum totals
        existing.targets += incoming_stats.targets
        existing.receptions += incoming_stats.receptions
        existing.receiving_yards += incoming_stats.receiving_yards
        existing.receiving_tds += incoming_stats.receiving_tds
        existing.drops += incoming_stats.drops
        existing.yac += incoming_stats.yac
        
        # Blocking stats - sum totals
        existing.blocks_made += incoming_stats.blocks_made
        existing.blocks_missed += incoming_stats.blocks_missed
        existing.pass_blocks += incoming_stats.pass_blocks
        existing.pressures_allowed += incoming_stats.pressures_allowed
        existing.sacks_allowed += incoming_stats.sacks_allowed
        
        # Defensive stats - sum totals
        existing.tackles += incoming_stats.tackles
        existing.assisted_tackles += incoming_stats.assisted_tackles
        existing.sacks += incoming_stats.sacks
        existing.tackles_for_loss += incoming_stats.tackles_for_loss
        existing.qb_hits += incoming_stats.qb_hits
        existing.qb_pressures += incoming_stats.qb_pressures
        existing.qb_hurries += incoming_stats.qb_hurries
        
        # Pass defense stats - sum totals
        existing.passes_defended += incoming_stats.passes_defended
        existing.passes_deflected += incoming_stats.passes_deflected
        existing.tipped_passes += incoming_stats.tipped_passes
        existing.interceptions += incoming_stats.interceptions
        existing.forced_fumbles += incoming_stats.forced_fumbles
        
        # Special teams stats - sum totals
        existing.field_goal_attempts += incoming_stats.field_goal_attempts
        existing.field_goals_made += incoming_stats.field_goals_made
        existing.field_goals_missed += incoming_stats.field_goals_missed
        existing.field_goals_blocked += incoming_stats.field_goals_blocked
        existing.field_goal_holds += incoming_stats.field_goal_holds
        existing.long_snaps += incoming_stats.long_snaps
        existing.special_teams_snaps += incoming_stats.special_teams_snaps
        existing.blocks_allowed += incoming_stats.blocks_allowed
        
        # Handle longest field goal (take maximum)
        existing.longest_field_goal = max(existing.longest_field_goal, incoming_stats.longest_field_goal)
        
        # Penalty stats - sum totals
        existing.penalties += incoming_stats.penalties
        existing.penalty_yards += incoming_stats.penalty_yards
    
    def get_player_stats(self, player_identifier: str) -> Optional[PlayerStats]:
        """
        Get accumulated stats for a specific player.
        
        Args:
            player_identifier: Player key in format "PlayerName_Position"
            
        Returns:
            PlayerStats object with accumulated totals, or None if player not found
        """
        return self._player_totals.get(player_identifier)
    
    def get_all_players_with_stats(self) -> List[PlayerStats]:
        """
        Get all players who have recorded statistics.
        
        Returns:
            List of PlayerStats objects for all players with accumulated stats
        """
        return [stats for stats in self._player_totals.values() if stats.get_total_stats()]
    
    def get_players_by_position(self, position: str) -> List[PlayerStats]:
        """
        Get all players at a specific position who have recorded stats.
        
        Args:
            position: Position code (e.g., "QB", "RB", "WR")
            
        Returns:
            List of PlayerStats objects for players at the specified position
        """
        return [stats for stats in self._player_totals.values() 
                if stats.position == position and stats.get_total_stats()]
    
    def get_plays_processed(self) -> int:
        """
        Get the number of plays that have been processed by this accumulator.
        
        Returns:
            Number of PlayStatsSummary objects processed
        """
        return self._plays_processed
    
    def get_player_count(self) -> int:
        """
        Get the number of unique players with recorded statistics.
        
        Returns:
            Count of players who have accumulated stats
        """
        return len(self.get_all_players_with_stats())
    
    def reset(self) -> None:
        """
        Reset the accumulator to initial state.
        
        Clears all accumulated player stats and resets play count.
        """
        self._player_totals.clear()
        self._plays_processed = 0


@dataclass
class TeamStats:
    """
    Team-level statistics accumulated across multiple plays within a game.
    
    Separates offensive stats (when team has possession) from defensive stats
    (when team is defending).
    """
    team_id: int
    
    # Offensive Stats (when this team has possession)
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    pass_attempts: int = 0
    completions: int = 0
    touchdowns: int = 0
    first_downs: int = 0
    turnovers: int = 0
    
    # Defensive Stats (when this team is defending)
    sacks: int = 0
    tackles_for_loss: int = 0
    interceptions: int = 0
    forced_fumbles: int = 0
    passes_defended: int = 0
    
    # Special Teams Stats
    field_goals_attempted: int = 0
    field_goals_made: int = 0
    
    # Penalties (committed by this team)
    penalties: int = 0
    penalty_yards: int = 0
    
    def get_total_offensive_stats(self) -> Dict[str, int]:
        """Get all non-zero offensive stats as dictionary"""
        offensive_fields = {
            'total_yards', 'passing_yards', 'rushing_yards', 'pass_attempts', 
            'completions', 'touchdowns', 'first_downs', 'turnovers'
        }
        
        stats = {}
        for field_name in offensive_fields:
            value = getattr(self, field_name, 0)
            if isinstance(value, (int, float)) and value != 0:
                stats[field_name] = value
        return stats
    
    def get_total_defensive_stats(self) -> Dict[str, int]:
        """Get all non-zero defensive stats as dictionary"""
        defensive_fields = {
            'sacks', 'tackles_for_loss', 'interceptions', 'forced_fumbles', 'passes_defended'
        }
        
        stats = {}
        for field_name in defensive_fields:
            value = getattr(self, field_name, 0)
            if isinstance(value, (int, float)) and value != 0:
                stats[field_name] = value
        return stats
    
    def get_all_stats(self) -> Dict[str, int]:
        """Get all non-zero stats as dictionary"""
        all_fields = {
            'total_yards', 'passing_yards', 'rushing_yards', 'pass_attempts', 
            'completions', 'touchdowns', 'first_downs', 'turnovers',
            'sacks', 'tackles_for_loss', 'interceptions', 'forced_fumbles', 'passes_defended',
            'field_goals_attempted', 'field_goals_made', 'penalties', 'penalty_yards'
        }
        
        stats = {}
        for field_name in all_fields:
            value = getattr(self, field_name, 0)
            if isinstance(value, (int, float)) and value != 0:
                stats[field_name] = value
        return stats


class TeamStatsAccumulator:
    """
    Accumulates team-level statistics from individual player stats across multiple plays.
    
    Takes PlayStatsSummary objects and aggregates offensive stats to the possessing team
    and defensive stats to the defending team.
    """
    
    def __init__(self, game_identifier: Optional[str] = None):
        """
        Initialize accumulator for tracking team stats across a game.
        
        Args:
            game_identifier: Optional identifier for this game
        """
        self.game_id = game_identifier
        self._team_totals: Dict[int, TeamStats] = {}
        self._plays_processed = 0
    
    def add_play_stats(self, play_summary: PlayStatsSummary, 
                      offensive_team_id: int, defensive_team_id: int) -> None:
        """
        Accumulate team stats from a single play into running game totals.
        
        Args:
            play_summary: PlayStatsSummary containing all player stats from one play
            offensive_team_id: Team ID of the team with possession
            defensive_team_id: Team ID of the team defending
        """
        self._plays_processed += 1
        
        # Ensure both teams exist in our tracking
        if offensive_team_id not in self._team_totals:
            self._team_totals[offensive_team_id] = TeamStats(team_id=offensive_team_id)
        if defensive_team_id not in self._team_totals:
            self._team_totals[defensive_team_id] = TeamStats(team_id=defensive_team_id)
        
        # Aggregate offensive stats to possessing team
        self._aggregate_offensive_stats(play_summary.player_stats, offensive_team_id)
        
        # Aggregate defensive stats to defending team  
        self._aggregate_defensive_stats(play_summary.player_stats, defensive_team_id)
        
        # Handle penalties (need to determine which team committed them)
        self._aggregate_penalty_stats(play_summary, offensive_team_id, defensive_team_id)
        
        # Handle play-level stats like yards gained and first downs
        self._aggregate_play_level_stats(play_summary, offensive_team_id)
    
    def _aggregate_offensive_stats(self, player_stats: List[PlayerStats], team_id: int) -> None:
        """Aggregate offensive stats from all players to the team total"""
        team = self._team_totals[team_id]
        
        for player in player_stats:
            # Rushing stats
            team.rushing_yards += player.rushing_yards
            
            # Passing stats
            team.passing_yards += player.passing_yards
            team.pass_attempts += player.pass_attempts
            team.completions += player.completions
            team.touchdowns += player.passing_tds + player.rushing_touchdowns
            
            # Special teams
            team.field_goals_attempted += player.field_goal_attempts
            team.field_goals_made += player.field_goals_made
    
    def _aggregate_defensive_stats(self, player_stats: List[PlayerStats], team_id: int) -> None:
        """Aggregate defensive stats from all players to the team total"""
        team = self._team_totals[team_id]
        
        for player in player_stats:
            # Defensive stats
            team.sacks += player.sacks
            team.tackles_for_loss += player.tackles_for_loss
            team.interceptions += player.interceptions
            team.forced_fumbles += player.forced_fumbles
            team.passes_defended += player.passes_defended
    
    def _aggregate_penalty_stats(self, play_summary: PlayStatsSummary, 
                                offensive_team_id: int, defensive_team_id: int) -> None:
        """Aggregate penalty stats - assign to the team that committed the penalty"""
        if not play_summary.penalty_occurred:
            return
        
        # For now, assign penalties to offensive team (could be enhanced with penalty details)
        # In a real implementation, we'd check which team actually committed the penalty
        penalty_team_id = offensive_team_id  # Simplified assumption
        
        team = self._team_totals[penalty_team_id]
        team.penalties += 1
        
        # Get penalty yards from the play summary
        if hasattr(play_summary, 'penalty_instance') and play_summary.penalty_instance:
            penalty_yards = getattr(play_summary.penalty_instance, 'yards_assessed', 0)
            team.penalty_yards += penalty_yards
    
    def _aggregate_play_level_stats(self, play_summary: PlayStatsSummary, offensive_team_id: int) -> None:
        """Aggregate play-level stats like total yards and first downs"""
        team = self._team_totals[offensive_team_id]
        
        # Total yards for the play
        team.total_yards += play_summary.yards_gained
        
        # Check for turnovers (simplified - could be enhanced)
        if any(player.interceptions_thrown > 0 for player in play_summary.player_stats):
            team.turnovers += 1
    
    def get_team_stats(self, team_id: int) -> Optional[TeamStats]:
        """
        Get accumulated stats for a specific team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            TeamStats object with accumulated totals, or None if team not found
        """
        return self._team_totals.get(team_id)
    
    def get_all_teams_stats(self) -> List[TeamStats]:
        """
        Get all teams that have recorded statistics.
        
        Returns:
            List of TeamStats objects for all teams with accumulated stats
        """
        return list(self._team_totals.values())
    
    def get_teams_with_stats(self) -> List[TeamStats]:
        """
        Get only teams that have non-zero statistics.
        
        Returns:
            List of TeamStats objects for teams with actual stats recorded
        """
        return [team for team in self._team_totals.values() if team.get_all_stats()]
    
    def get_plays_processed(self) -> int:
        """
        Get the number of plays that have been processed by this accumulator.
        
        Returns:
            Number of PlayStatsSummary objects processed
        """
        return self._plays_processed
    
    def get_team_count(self) -> int:
        """
        Get the number of teams being tracked.
        
        Returns:
            Count of teams in the accumulator
        """
        return len(self._team_totals)
    
    def reset(self) -> None:
        """
        Reset the accumulator to initial state.
        
        Clears all accumulated team stats and resets play count.
        """
        self._team_totals.clear()
        self._plays_processed = 0


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