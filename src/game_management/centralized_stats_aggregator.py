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

from play_engine.core.play_result import PlayResult
from play_engine.simulation.stats import (
    PlayerStatsAccumulator,
    TeamStatsAccumulator,
    PlayStatsSummary,
    PlayerStats,
    TeamStats
)
from game_management.team_game_stats import TeamGameStats
# PlayerGameStats removed with simulation system - will need to be recreated if needed
# from simulation.results.game_result import PlayerGameStats
from team_management.teams.team_loader import Team


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

        # NEW: Per-team situational stats (unified TeamGameStats)
        # These track all per-team stats including situational (3rd/4th down, TOP, red zone)
        self.home_team_game_stats = TeamGameStats(team_id=home_team_id)
        self.away_team_game_stats = TeamGameStats(team_id=away_team_id)

        # Internal tracking
        self._plays_processed = 0
        self._drives_completed = 0

        # Drive-level state tracking for correct red zone stats
        # NFL Red Zone TD % = TDs / Red Zone Trips (not TDs / Red Zone Plays)
        self._current_drive_in_red_zone: Dict[int, bool] = {
            home_team_id: False,
            away_team_id: False
        }

    def _get_team_stats(self, team_id: int) -> TeamGameStats:
        """Get the TeamGameStats for a specific team."""
        if team_id == self.home_team_id:
            return self.home_team_game_stats
        elif team_id == self.away_team_id:
            return self.away_team_game_stats
        else:
            raise ValueError(f"Unknown team_id: {team_id}. Expected {self.home_team_id} or {self.away_team_id}")

    def reset_drive_state(self, possessing_team_id: int) -> None:
        """
        Reset drive-level state for the specified team.

        Called when a new drive starts to ensure red zone trips are counted
        per drive (not per play). This aligns with NFL's definition of
        "Red Zone TD %" = TDs / Red Zone Trips.

        Args:
            possessing_team_id: Team ID starting the new drive
        """
        if possessing_team_id in self._current_drive_in_red_zone:
            self._current_drive_in_red_zone[possessing_team_id] = False

    def _get_opponent_stats(self, team_id: int) -> TeamGameStats:
        """Get the TeamGameStats for the opponent of the specified team."""
        if team_id == self.home_team_id:
            return self.away_team_game_stats
        elif team_id == self.away_team_id:
            return self.home_team_game_stats
        else:
            raise ValueError(f"Unknown team_id: {team_id}. Expected {self.home_team_id} or {self.away_team_id}")

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

        # DEBUG: Track if this play was already recorded
        play_id = id(play_result)
        if not hasattr(self, '_recorded_plays'):
            self._recorded_plays = set()

        if play_id in self._recorded_plays:
            print(f"⚠️ SKIPPING duplicate play recording!")
            print(f"   Play ID: {play_id}")
            print(f"   Outcome: {play_result.outcome}")
            print(f"   Yards: {play_result.yards}")
            print(f"   Is scoring play: {play_result.is_scoring_play}")
            print(f"   This play was already recorded - SKIPPING to prevent stat doubling")
            return  # ✅ PREVENT doubling by skipping duplicate recording
        else:
            self._recorded_plays.add(play_id)
        
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
        
        # Update situational statistics (both game-level and per-team)
        self._update_situational_stats(play_result, possessing_team_id, down, yards_to_go, field_position)
    
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

        # NEW: Extract defensive stats from player stats and route to TeamGameStats
        # This ensures qb_hits, interceptions, sacks, etc. are tracked per-team
        self._update_team_game_stats_from_player_stats(stats_summary, possessing_team_id, defensive_team_id)

    def _update_team_game_stats_from_player_stats(self, stats_summary: PlayStatsSummary,
                                                   offensive_team_id: int, defensive_team_id: int) -> None:
        """
        Extract stats from player stats and route to the correct team's TeamGameStats.

        Defensive stats (qb_hits, sacks, interceptions, etc.) go to defensive team.
        Offensive stats go to offensive team.
        """
        offensive_stats = self._get_team_stats(offensive_team_id)
        defensive_stats = self._get_team_stats(defensive_team_id)

        if not stats_summary or not hasattr(stats_summary, 'player_stats'):
            return

        for player_stat in stats_summary.player_stats:
            # === Defensive Stats (route to defensive team) ===
            qb_hits = getattr(player_stat, 'qb_hits', 0) or 0
            if qb_hits > 0:
                defensive_stats.qb_hits += qb_hits

            sacks = getattr(player_stat, 'sacks', 0) or 0
            if sacks > 0:
                defensive_stats.sacks += sacks

            interceptions = getattr(player_stat, 'interceptions', 0) or 0
            if interceptions > 0:
                defensive_stats.interceptions += interceptions

            passes_defended = getattr(player_stat, 'passes_defended', 0) or 0
            if passes_defended > 0:
                defensive_stats.passes_defended += passes_defended

            forced_fumbles = getattr(player_stat, 'forced_fumbles', 0) or 0
            if forced_fumbles > 0:
                defensive_stats.forced_fumbles += forced_fumbles

            tackles_for_loss = getattr(player_stat, 'tackles_for_loss', 0) or 0
            if tackles_for_loss > 0:
                defensive_stats.tackles_for_loss += tackles_for_loss

            # === Offensive Turnovers (route to offensive team) ===
            interceptions_thrown = getattr(player_stat, 'interceptions_thrown', 0) or 0
            if interceptions_thrown > 0:
                offensive_stats.interceptions_thrown += interceptions_thrown
                offensive_stats.turnovers += interceptions_thrown

            fumbles_lost = getattr(player_stat, 'fumbles_lost', 0) or 0
            if fumbles_lost > 0:
                offensive_stats.fumbles_lost += fumbles_lost
                offensive_stats.turnovers += fumbles_lost

            # === Sacks Taken (offensive perspective) ===
            sacks_taken = getattr(player_stat, 'sacks_taken', 0) or 0
            if sacks_taken > 0:
                offensive_stats.times_sacked += sacks_taken
    
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

            # Route penalty to the team that committed it (per-team tracking)
            # penalty_yards > 0 means defense committed (offense benefits)
            # penalty_yards < 0 means offense committed (defense benefits)
            penalty_yards_abs = abs(play_result.penalty_yards)
            if play_result.penalty_yards > 0:
                # Defensive penalty - charge to defensive team
                defensive_team_id = self.away_team_id if possessing_team_id == self.home_team_id else self.home_team_id
                defensive_stats = self._get_team_stats(defensive_team_id)
                defensive_stats.penalties += 1
                defensive_stats.penalty_yards += penalty_yards_abs
            elif play_result.penalty_yards < 0:
                # Offensive penalty - charge to offensive team
                offensive_stats = self._get_team_stats(possessing_team_id)
                offensive_stats.penalties += 1
                offensive_stats.penalty_yards += penalty_yards_abs
            else:
                # Zero yards (offsetting or rare cases) - charge to possessing team as default
                offensive_stats = self._get_team_stats(possessing_team_id)
                offensive_stats.penalties += 1
        
        # Big plays (20+ yards)
        if abs(play_result.yards) >= 20:
            self.game_stats.big_plays_20_plus += 1
        
        # First downs
        if play_result.achieved_first_down:
            self.game_stats.first_downs_total += 1
    
    def _update_situational_stats(self, play_result: PlayResult, possessing_team_id: int,
                                 down: int, yards_to_go: int, field_position: int) -> None:
        """
        Update situational statistics based on game context.

        Routes stats to correct team based on possession, tracking:
        - Third down attempts/conversions (per-team)
        - Fourth down attempts/conversions (per-team and game-level)
        - Red zone attempts/scores (per-team and game-level)
        - Time of possession (per-team)
        - First downs (per-team)
        """
        # Get the offensive team's stats (possessing team)
        offensive_stats = self._get_team_stats(possessing_team_id)

        # === Time of Possession (per-team) ===
        offensive_stats.time_of_possession_seconds += play_result.time_elapsed

        # === Third Down Tracking (per-team) - THIS WAS MISSING! ===
        if down == 3:
            offensive_stats.third_down_attempts += 1
            if play_result.achieved_first_down or play_result.is_scoring_play:
                offensive_stats.third_down_conversions += 1

        # === Fourth Down Tracking (per-team AND game-level) ===
        # Only track "go for it" attempts - exclude punts and field goals
        # NFL 4th down conversion % measures success rate when teams GO FOR IT,
        # not all 4th down plays (punts/FGs are separate special teams stats)
        if down == 4:
            is_punt = getattr(play_result, 'is_punt', False)
            is_field_goal = 'field_goal' in str(getattr(play_result, 'outcome', '')).lower()

            if not is_punt and not is_field_goal:
                # Game-level (existing)
                self.game_stats.fourth_down_attempts += 1
                if play_result.achieved_first_down or play_result.is_scoring_play:
                    self.game_stats.fourth_down_conversions += 1

                # Per-team (NEW)
                offensive_stats.fourth_down_attempts += 1
                if play_result.achieved_first_down or play_result.is_scoring_play:
                    offensive_stats.fourth_down_conversions += 1

        # === Red Zone Tracking (per-team AND game-level) ===
        # NFL "Red Zone TD %" = TDs / Red Zone Trips (drives entering red zone)
        # NOT TDs / Red Zone Plays - that would give ~20% instead of ~55%
        if field_position >= 80:  # 80+ means within 20 yards of goal
            # Only count the FIRST time this drive enters the red zone
            if not self._current_drive_in_red_zone.get(possessing_team_id, False):
                self._current_drive_in_red_zone[possessing_team_id] = True
                # Game-level
                self.game_stats.red_zone_attempts += 1
                # Per-team
                offensive_stats.red_zone_attempts += 1

            # Scoring plays count regardless (but still per-drive for attempts)
            if play_result.is_scoring_play:
                self.game_stats.red_zone_scores += 1
                if play_result.points == 6:  # Touchdown
                    offensive_stats.red_zone_touchdowns += 1
                elif play_result.points == 3:  # Field goal
                    offensive_stats.red_zone_field_goals += 1

        # === First Downs (per-team) ===
        if play_result.achieved_first_down:
            offensive_stats.first_downs += 1
            # Track by type if available from play_result
            if hasattr(play_result, 'play_type'):
                if play_result.play_type in ['pass', 'pass_completion']:
                    offensive_stats.first_downs_passing += 1
                elif play_result.play_type in ['run', 'rush']:
                    offensive_stats.first_downs_rushing += 1

        # === Yards/Attempts (per-team) ===
        offensive_stats.total_yards += play_result.yards
        if hasattr(play_result, 'play_type'):
            if play_result.play_type in ['pass', 'pass_completion']:
                offensive_stats.passing_yards += play_result.yards
                offensive_stats.passing_attempts += 1
                if play_result.yards > 0 and not getattr(play_result, 'is_incomplete', False):
                    offensive_stats.passing_completions += 1
            elif play_result.play_type in ['run', 'rush']:
                offensive_stats.rushing_yards += play_result.yards
                offensive_stats.rushing_attempts += 1
    
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

    def get_player_game_statistics(self) -> List[Dict]:
        """
        Convert accumulated PlayerStats to dictionary objects for persistence.

        This is the critical conversion method that bridges the gap between
        simulation PlayerStats and persistence-ready data.

        Returns:
            List of dictionary objects ready for database persistence
        """
        all_players = self.player_stats.get_all_players_with_stats()
        game_stats_list = []

        for player_stats in all_players:
            # Strict validation: no fallbacks for missing team_id
            if player_stats.team_id is None:
                raise ValueError(f"Player {player_stats.player_name} ({player_stats.position}) has no team_id - team assignment is broken")

            # Convert PlayerStats to dictionary with proper field mapping
            # All fields tracked by play engine PlayerStats class
            game_stats = {
                "player_name": player_stats.player_name,
                "position": player_stats.position,
                "team_id": player_stats.team_id,  # No fallback - fail fast if None
                "player_id": player_stats.player_id,  # Required for injury generation

                # Passing stats (complete)
                "passing_yards": player_stats.passing_yards,
                "passing_tds": player_stats.passing_tds,
                "passing_attempts": player_stats.passing_attempts,
                "passing_completions": player_stats.passing_completions,
                "passing_interceptions": player_stats.interceptions_thrown,
                "sacks_taken": player_stats.sacks_taken,
                "sack_yards_lost": player_stats.sack_yards_lost,
                "air_yards": getattr(player_stats, 'air_yards', 0),

                # Rushing stats (complete)
                "rushing_yards": player_stats.rushing_yards,
                "rushing_tds": player_stats.rushing_tds,
                "rushing_attempts": player_stats.rushing_attempts,

                # Receiving stats (complete)
                "receiving_yards": player_stats.receiving_yards,
                "receiving_tds": player_stats.receiving_tds,
                "receptions": player_stats.receptions,
                "targets": getattr(player_stats, 'targets', 0),
                "drops": getattr(player_stats, 'drops', 0),
                "yac": getattr(player_stats, 'yac', 0),

                # Defensive stats (complete)
                "tackles": player_stats.tackles,
                "assisted_tackles": player_stats.assisted_tackles,
                "sacks": player_stats.sacks,
                "tackles_for_loss": player_stats.tackles_for_loss,
                "qb_hits": player_stats.qb_hits,
                "qb_pressures": player_stats.qb_pressures,
                "interceptions": player_stats.interceptions,
                "passes_defended": player_stats.passes_defended,
                "passes_deflected": player_stats.passes_deflected,
                "forced_fumbles": player_stats.forced_fumbles,

                # Special teams - Kicking
                "field_goals_made": player_stats.field_goals_made,
                "field_goals_attempted": player_stats.field_goal_attempts,
                "extra_points_made": player_stats.extra_points_made,
                "extra_points_attempted": player_stats.extra_points_attempted,

                # Special teams - Punting
                "punts": getattr(player_stats, 'punts', 0),
                "punt_yards": getattr(player_stats, 'punt_yards', 0),

                # O-Line stats (complete)
                "pass_blocks": player_stats.pass_blocks,
                "pancakes": player_stats.pancakes,
                "sacks_allowed": player_stats.sacks_allowed,
                "hurries_allowed": player_stats.hurries_allowed,
                "pressures_allowed": player_stats.pressures_allowed,
                "run_blocking_grade": player_stats.run_blocking_grade,
                "pass_blocking_efficiency": player_stats.pass_blocking_efficiency,
                "missed_assignments": player_stats.missed_assignments,
                "holding_penalties": player_stats.holding_penalties,
                "false_start_penalties": player_stats.false_start_penalties,
                "downfield_blocks": player_stats.downfield_blocks,
                "double_team_blocks": player_stats.double_team_blocks,
                "chip_blocks": player_stats.chip_blocks,

                # Snap counts (now properly tracked!)
                "offensive_snaps": player_stats.offensive_snaps,
                "defensive_snaps": player_stats.defensive_snaps,
                "special_teams_snaps": player_stats.special_teams_snaps,

                # Legacy compatibility
                "pass_deflections": player_stats.passes_defended,
                "performance_rating": 0.0,
                "snap_count": player_stats.offensive_snaps + player_stats.defensive_snaps + player_stats.special_teams_snaps,

                # ============================================================
                # PFF-CRITICAL STATS - Required for accurate position grading
                # ============================================================

                # Coverage stats (DB/LB grading)
                "coverage_targets": getattr(player_stats, 'coverage_targets', 0),
                "coverage_completions": getattr(player_stats, 'coverage_completions', 0),
                "coverage_yards_allowed": getattr(player_stats, 'coverage_yards_allowed', 0),

                # Pass rush stats (DL grading)
                "pass_rush_wins": getattr(player_stats, 'pass_rush_wins', 0),
                "pass_rush_attempts": getattr(player_stats, 'pass_rush_attempts', 0),
                "times_double_teamed": getattr(player_stats, 'times_double_teamed', 0),
                "blocking_encounters": getattr(player_stats, 'blocking_encounters', 0),

                # Ball carrier stats (RB/WR grading)
                "broken_tackles": getattr(player_stats, 'broken_tackles', 0),
                "tackles_faced": getattr(player_stats, 'tackles_faced', 0),
                "yards_after_contact": getattr(player_stats, 'yards_after_contact', 0),

                # QB advanced stats
                "pressures_faced": getattr(player_stats, 'pressures_faced', 0),
                "time_to_throw_total": getattr(player_stats, 'time_to_throw_total', 0),
                "throw_count": getattr(player_stats, 'throw_count', 0),

                # Tackling stats
                "missed_tackles": getattr(player_stats, 'missed_tackles', 0),
            }

            game_stats_list.append(game_stats)

        return game_stats_list

    def get_team_statistics(self, team_id: int) -> Optional[TeamGameStats]:
        """
        Get team statistics for a specific team.

        Returns TeamGameStats which includes ALL tracked stats:
        - Basic: total_yards, passing_yards, rushing_yards, turnovers
        - Situational: first_downs, third_down_*, fourth_down_*, time_of_possession_seconds
        - Penalties: penalties, penalty_yards

        Args:
            team_id: Team identifier (1-32)

        Returns:
            TeamGameStats object or None if team not found
        """
        return self._get_team_stats(team_id)
    
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
            # NEW: Per-team situational stats (unified TeamGameStats)
            "home_team_game_stats": self.home_team_game_stats.to_dict(),
            "away_team_game_stats": self.away_team_game_stats.to_dict(),
            "summary": {
                "game_id": self.game_id,
                "total_plays_recorded": self._plays_processed,
                "total_drives_completed": self._drives_completed,
                "statistics_complete": self._plays_processed > 0
            }
        }

    def get_home_team_game_stats(self) -> TeamGameStats:
        """Get the unified TeamGameStats for the home team."""
        return self.home_team_game_stats

    def get_away_team_game_stats(self) -> TeamGameStats:
        """Get the unified TeamGameStats for the away team."""
        return self.away_team_game_stats
    
    def reset(self) -> None:
        """Reset all statistics to initial state (useful for testing)."""
        self.player_stats.reset()
        self.team_stats.reset()
        self.game_stats = GameLevelStats(
            home_team_id=self.home_team_id,
            away_team_id=self.away_team_id,
            game_start_time=datetime.now()
        )
        # Reset per-team situational stats
        self.home_team_game_stats = TeamGameStats(team_id=self.home_team_id)
        self.away_team_game_stats = TeamGameStats(team_id=self.away_team_id)
        self._plays_processed = 0
        self._drives_completed = 0
        if hasattr(self, '_recorded_plays'):
            self._recorded_plays.clear()
    
    def get_plays_processed(self) -> int:
        """Get total number of plays processed by this aggregator."""
        return self._plays_processed
    
    def get_drives_completed(self) -> int:
        """Get total number of drives completed."""
        return self._drives_completed
    
    def is_statistics_complete(self) -> bool:
        """Check if any statistics have been recorded."""
        return self._plays_processed > 0