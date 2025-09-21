"""
Centralized Statistics Aggregator

Serves as the bridge between individual play results and comprehensive game statistics.
Coordinates the flow of statistics from PlayResult objects to PlayerStatsAccumulator and
TeamStatsAccumulator, while maintaining game-level statistics.

This class solves the integration gap between the GameLoopController (which generates
PlayResult objects) and the existing proven statistics infrastructure.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from ..play_engine.core.play_result import PlayResult
from ..play_engine.simulation.stats import (
    PlayerStatsAccumulator,
    TeamStatsAccumulator,
    PlayStatsSummary,
    PlayerStats,
    TeamStats
)
# PlayerGameStats removed with simulation system - will need to be recreated if needed
# from ..simulation.results.game_result import PlayerGameStats
from ..team_management.teams.team_loader import Team


@dataclass
class GameLevelStats:
    """
    Game-level statistics that aren't captured by player or team aggregators.
    
    These are meta-statistics about the game itself, drive patterns, and
    overall game flow that complement the detailed player/team statistics.
    """
    
    # Game metadata
    home_team_id: int
    away_team_id: int
    game_start_time: Optional[datetime] = None
    
    # Play-level tracking
    total_plays_run: int = 0
    total_drives_completed: int = 0
    total_game_time_seconds: float = 0.0
    
    # Drive outcomes tracking
    touchdowns: int = 0
    field_goals_made: int = 0
    field_goals_missed: int = 0
    punts: int = 0
    turnovers: int = 0
    safeties: int = 0
    
    # Game flow statistics
    first_downs_total: int = 0
    fourth_down_attempts: int = 0
    fourth_down_conversions: int = 0
    red_zone_attempts: int = 0
    red_zone_scores: int = 0
    
    # Special situations
    penalty_plays: int = 0
    total_penalty_yards: int = 0
    scoring_plays: int = 0
    big_plays_20_plus: int = 0  # Plays of 20+ yards
    
    # Team-specific game outcomes (for quick access)
    final_score: Dict[int, int] = field(default_factory=dict)
    winner_team_id: Optional[int] = None
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of game-level statistics"""
        return {
            "game_info": {
                "home_team_id": self.home_team_id,
                "away_team_id": self.away_team_id,
                "game_duration_minutes": self.total_game_time_seconds / 60.0,
                "final_score": self.final_score.copy(),
                "winner": self.winner_team_id
            },
            "play_stats": {
                "total_plays": self.total_plays_run,
                "total_drives": self.total_drives_completed,
                "scoring_plays": self.scoring_plays,
                "penalty_plays": self.penalty_plays,
                "big_plays_20_plus": self.big_plays_20_plus
            },
            "drive_outcomes": {
                "touchdowns": self.touchdowns,
                "field_goals_made": self.field_goals_made,
                "field_goals_missed": self.field_goals_missed,
                "punts": self.punts,
                "turnovers": self.turnovers,
                "safeties": self.safeties
            },
            "situational_stats": {
                "first_downs_total": self.first_downs_total,
                "fourth_down_attempts": self.fourth_down_attempts,
                "fourth_down_conversions": self.fourth_down_conversions,
                "red_zone_attempts": self.red_zone_attempts,
                "red_zone_scores": self.red_zone_scores,
                "total_penalty_yards": self.total_penalty_yards
            }
        }


class CentralizedStatsAggregator:
    """
    Central coordinator for all game statistics.
    
    Acts as the bridge between individual PlayResult objects from game simulation
    and the existing proven PlayerStatsAccumulator and TeamStatsAccumulator systems.
    
    Key Responsibilities:
    1. Extract PlayStatsSummary from PlayResult objects
    2. Feed detailed statistics to PlayerStatsAccumulator
    3. Feed team statistics to TeamStatsAccumulator  
    4. Maintain game-level meta-statistics
    5. Provide unified access to all statistics
    
    This design leverages existing battle-tested components rather than replacing them.
    """
    
    def __init__(self, home_team_id: int, away_team_id: int, 
                 game_identifier: Optional[str] = None):
        """
        Initialize the centralized statistics aggregator.
        
        Args:
            home_team_id: Numerical ID of the home team (1-32)
            away_team_id: Numerical ID of the away team (1-32) 
            game_identifier: Optional identifier for this game (e.g., "Browns_vs_49ers_Week1")
        """
        self.game_id = game_identifier or f"Game_{home_team_id}_vs_{away_team_id}"
        
        # Initialize existing proven statistics components
        self.player_stats = PlayerStatsAccumulator(self.game_id)
        self.team_stats = TeamStatsAccumulator(self.game_id)
        
        # Initialize game-level statistics
        self.game_stats = GameLevelStats(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            game_start_time=datetime.now()
        )
        
        # Track teams for quick reference
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Internal tracking
        self._plays_processed = 0
        self._drives_completed = 0
    
    def record_play_result(self, play_result: PlayResult, possessing_team_id: int,
                          down: int = 1, yards_to_go: int = 10, 
                          field_position: int = 50) -> None:
        """
        Record statistics from a single play result.
        
        This is the main entry point that bridges PlayResult objects with the
        existing statistics infrastructure.
        
        Args:
            play_result: PlayResult object containing play outcome and player stats
            possessing_team_id: Team ID of the team with possession
            down: Current down (1-4)
            yards_to_go: Yards needed for first down
            field_position: Current field position (0-100, 0=own goal line)
        """
        self._plays_processed += 1
        
        # Record basic play-level statistics
        self.game_stats.total_plays_run += 1
        self.game_stats.total_game_time_seconds += play_result.time_elapsed
        
        # Process detailed player statistics if available
        if play_result.has_player_stats() and play_result.player_stats_summary:
            self._process_detailed_stats(
                play_result.player_stats_summary, 
                possessing_team_id, 
                play_result
            )
        
        # Record play-level outcomes
        self._record_play_outcomes(play_result, possessing_team_id, 
                                  down, yards_to_go, field_position)
        
        # Update situational statistics
        self._update_situational_stats(play_result, down, yards_to_go, field_position)
    
    def _process_detailed_stats(self, stats_summary: PlayStatsSummary, 
                               possessing_team_id: int, play_result: PlayResult) -> None:
        """
        Process detailed player statistics through existing accumulators.
        
        Args:
            stats_summary: PlayStatsSummary containing all player stats
            possessing_team_id: Team with possession
            play_result: Complete play result for context
        """
        # Feed to PlayerStatsAccumulator (proven component)
        self.player_stats.add_play_stats(stats_summary)
        
        # Feed to TeamStatsAccumulator (proven component)
        defensive_team_id = self.away_team_id if possessing_team_id == self.home_team_id else self.home_team_id
        self.team_stats.add_play_stats(stats_summary, possessing_team_id, defensive_team_id)
    
    def _record_play_outcomes(self, play_result: PlayResult, possessing_team_id: int,
                             down: int, yards_to_go: int, field_position: int) -> None:
        """Record play outcome statistics at the game level."""
        
        # Scoring plays
        if play_result.is_scoring_play:
            self.game_stats.scoring_plays += 1
            
            if play_result.points == 6:  # Touchdown
                self.game_stats.touchdowns += 1
            elif play_result.points == 3:  # Field goal
                self.game_stats.field_goals_made += 1
            elif play_result.points == 2:  # Safety
                self.game_stats.safeties += 1
        
        # Missed field goals (no points but field goal attempt)
        if play_result.is_missed_field_goal():
            self.game_stats.field_goals_missed += 1
        
        # Turnovers
        if play_result.is_turnover:
            self.game_stats.turnovers += 1
        
        # Punts
        if play_result.is_punt:
            self.game_stats.punts += 1
        
        # Penalties
        if play_result.penalty_occurred:
            self.game_stats.penalty_plays += 1
            self.game_stats.total_penalty_yards += abs(play_result.penalty_yards)
        
        # Big plays (20+ yards)
        if abs(play_result.yards) >= 20:
            self.game_stats.big_plays_20_plus += 1
        
        # First downs
        if play_result.achieved_first_down:
            self.game_stats.first_downs_total += 1
    
    def _update_situational_stats(self, play_result: PlayResult, down: int, 
                                 yards_to_go: int, field_position: int) -> None:
        """Update situational statistics based on game context."""
        
        # Fourth down attempts
        if down == 4:
            self.game_stats.fourth_down_attempts += 1
            if play_result.achieved_first_down:
                self.game_stats.fourth_down_conversions += 1
        
        # Red zone attempts (inside 20-yard line)
        if field_position >= 80:  # 80+ means within 20 yards of goal
            self.game_stats.red_zone_attempts += 1
            if play_result.is_scoring_play:
                self.game_stats.red_zone_scores += 1
    
    def record_drive_completion(self, drive_outcome: str, possessing_team_id: int) -> None:
        """
        Record the completion of a drive.
        
        Args:
            drive_outcome: Drive end reason (touchdown, field_goal, punt, turnover, etc.)
            possessing_team_id: Team that had possession during the drive
        """
        self._drives_completed += 1
        self.game_stats.total_drives_completed += 1
    
    def finalize_game(self, final_score: Dict[int, int]) -> None:
        """
        Finalize the game and record final statistics.
        
        Args:
            final_score: Final score mapping {team_id: points}
        """
        self.game_stats.final_score = final_score.copy()
        
        # Determine winner
        home_score = final_score.get(self.home_team_id, 0)
        away_score = final_score.get(self.away_team_id, 0)
        
        if home_score > away_score:
            self.game_stats.winner_team_id = self.home_team_id
        elif away_score > home_score:
            self.game_stats.winner_team_id = self.away_team_id
        # else: tie game, winner remains None
    
    # Public API Methods for External Access
    
    def get_player_statistics(self, team_id: Optional[int] = None, 
                            player_name: Optional[str] = None) -> List[PlayerStats]:
        """
        Get player statistics with optional filtering.
        
        Args:
            team_id: Filter by team (None = all teams)
            player_name: Filter by specific player (None = all players)
            
        Returns:
            List of PlayerStats objects matching the criteria
        """
        all_players = self.player_stats.get_all_players_with_stats()
        
        # Note: PlayerStatsAccumulator doesn't currently filter by team_id
        # This would need enhancement in the existing class to support team filtering
        # For now, return all players (future enhancement)
        
        if player_name:
            # Filter by player name if specified
            all_players = [p for p in all_players if player_name.lower() in p.player_name.lower()]
        
        return all_players

    def get_player_game_statistics(self) -> List[PlayerGameStats]:
        """
        Convert accumulated PlayerStats to PlayerGameStats objects for persistence.

        This is the critical conversion method that bridges the gap between
        simulation PlayerStats and persistence-ready PlayerGameStats.

        Returns:
            List of PlayerGameStats objects ready for database persistence
        """
        all_players = self.player_stats.get_all_players_with_stats()
        game_stats_list = []

        for player_stats in all_players:
            # Strict validation: no fallbacks for missing team_id
            if player_stats.team_id is None:
                raise ValueError(f"Player {player_stats.player_name} ({player_stats.position}) has no team_id - team assignment is broken")

            # Convert PlayerStats to PlayerGameStats with proper field mapping
            game_stats = PlayerGameStats(
                player_name=player_stats.player_name,
                position=player_stats.position,
                team_id=player_stats.team_id,  # No fallback - fail fast if None

                # Offensive stats
                passing_yards=player_stats.passing_yards,
                passing_tds=player_stats.passing_tds,
                passing_interceptions=player_stats.interceptions_thrown,
                rushing_yards=player_stats.rushing_yards,
                rushing_tds=player_stats.rushing_tds,
                receiving_yards=player_stats.receiving_yards,
                receiving_tds=player_stats.receiving_tds,
                receptions=player_stats.receptions,

                # Defensive stats
                tackles=player_stats.tackles,
                sacks=player_stats.sacks,
                interceptions=player_stats.interceptions,
                pass_deflections=player_stats.passes_defended,

                # Special teams
                field_goals_made=player_stats.field_goals_made,
                field_goals_attempted=player_stats.field_goal_attempts,
                extra_points_made=player_stats.extra_points_made,
                extra_points_attempted=player_stats.extra_points_attempted,

                # Performance metrics (basic defaults)
                performance_rating=0.0,  # Could be calculated based on stats
                snap_count=0  # Not tracked in PlayerStats currently
            )

            game_stats_list.append(game_stats)

        return game_stats_list

    def get_team_statistics(self, team_id: int) -> Optional[TeamStats]:
        """
        Get team statistics for a specific team.
        
        Args:
            team_id: Team identifier (1-32)
            
        Returns:
            TeamStats object or None if team not found
        """
        return self.team_stats.get_team_stats(team_id)
    
    def get_game_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive game-level statistics.
        
        Returns:
            Dictionary with complete game statistics including player, team, and meta stats
        """
        game_summary = self.game_stats.get_summary()
        
        # Add player and team statistics counts
        game_summary["statistics_summary"] = {
            "total_players_with_stats": self.player_stats.get_player_count(),
            "home_team_stats": self.get_team_statistics(self.home_team_id),
            "away_team_stats": self.get_team_statistics(self.away_team_id),
            "plays_processed": self._plays_processed,
            "drives_completed": self._drives_completed
        }
        
        return game_summary
    
    def get_all_statistics(self) -> Dict[str, Any]:
        """
        Get all statistics in a comprehensive format.
        
        Returns:
            Complete statistics package with player, team, and game data
        """
        return {
            "game_info": self.game_stats.get_summary(),
            "player_statistics": {
                "all_players": [p.__dict__ for p in self.get_player_statistics()],
                "total_players": self.player_stats.get_player_count(),
                "plays_processed": self.player_stats.get_plays_processed()
            },
            "team_statistics": {
                "home_team": self.get_team_statistics(self.home_team_id).__dict__ if self.get_team_statistics(self.home_team_id) else {},
                "away_team": self.get_team_statistics(self.away_team_id).__dict__ if self.get_team_statistics(self.away_team_id) else {},
                "total_teams": self.team_stats.get_team_count(),
                "plays_processed": self.team_stats.get_plays_processed()
            },
            "summary": {
                "game_id": self.game_id,
                "total_plays_recorded": self._plays_processed,
                "total_drives_completed": self._drives_completed,
                "statistics_complete": self._plays_processed > 0
            }
        }
    
    def reset(self) -> None:
        """Reset all statistics to initial state (useful for testing)."""
        self.player_stats.reset()
        self.team_stats.reset()
        self.game_stats = GameLevelStats(
            home_team_id=self.home_team_id,
            away_team_id=self.away_team_id,
            game_start_time=datetime.now()
        )
        self._plays_processed = 0
        self._drives_completed = 0
    
    def get_plays_processed(self) -> int:
        """Get total number of plays processed by this aggregator."""
        return self._plays_processed
    
    def get_drives_completed(self) -> int:
        """Get total number of drives completed."""
        return self._drives_completed
    
    def is_statistics_complete(self) -> bool:
        """Check if any statistics have been recorded."""
        return self._plays_processed > 0