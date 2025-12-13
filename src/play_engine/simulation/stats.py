"""
Player statistics tracking for individual play simulation

Tracks individual player contributions during play execution including
rushing, blocking, tackling, and other position-specific statistics.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from ..play_types.base_types import PlayType
try:
    from ...constants.player_stats_fields import PlayerStatField, ALL_STAT_FIELDS
except ImportError:
    # Handle direct execution cases
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
    from constants.player_stats_fields import PlayerStatField, ALL_STAT_FIELDS


@dataclass
class PlayerStats:
    """Individual player statistics for a single play"""
    player_name: str
    player_number: int
    position: str
    team_id: Optional[int] = None  # Team ID this player belongs to
    player_id: Optional[int] = None  # Unique player ID for real players
    player_attributes: Optional[Dict[str, int]] = None  # Real player ratings/attributes
    
    # Rushing stats
    rushing_attempts: int = 0  # Database-compatible name (was: carries)
    rushing_yards: int = 0
    yards_after_contact: int = 0  # Yards gained after initial defender contact (RB power/elusiveness)

    # Passing stats (QB)
    passing_attempts: int = 0  # Database-compatible name (was: pass_attempts)
    passing_completions: int = 0  # Database-compatible name (was: completions)
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

    # Advanced offensive line stats
    pancakes: int = 0                      # Dominant blocks where lineman completely controls defender
    hurries_allowed: int = 0               # QB rushed into quick throw but not sacked
    run_blocking_grade: float = 0.0        # 0-100 grade for run blocking effectiveness
    pass_blocking_efficiency: float = 0.0  # 0-100 grade for pass protection effectiveness
    missed_assignments: int = 0            # Mental errors/blown assignments
    holding_penalties: int = 0             # Holding penalties committed
    false_start_penalties: int = 0         # False start penalties committed
    downfield_blocks: int = 0              # Blocks made downfield (screens, draws, etc.)
    double_team_blocks: int = 0            # Successful double-team blocks
    chip_blocks: int = 0                   # Quick chip blocks before releasing
    
    # Defensive stats
    tackles: int = 0
    assisted_tackles: int = 0
    missed_tackles: int = 0  # Tackle attempts that failed to bring down ball carrier
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
    fumble_recoveries: int = 0  # Fumbles recovered by this defender

    # Ball carrier fumble stats
    fumbles_lost: int = 0  # Fumbles lost by ball carrier (turnover)

    # Coverage stats (DB/LB grading metrics)
    coverage_targets: int = 0       # Times targeted while in coverage
    coverage_completions: int = 0   # Completions allowed in coverage
    coverage_yards_allowed: int = 0 # Yards allowed in coverage

    # Pass rush stats (DL grading metrics)
    pass_rush_wins: int = 0           # Winning pass rush reps (beat blocker)
    pass_rush_attempts: int = 0       # Total pass rush attempts
    times_double_teamed: int = 0      # Times this player was double-teamed
    blocking_encounters: int = 0      # Total blocking encounters (base for double team rate)

    # Ball carrier advanced stats (RB/WR grading)
    broken_tackles: int = 0           # Tackles broken/evaded after contact
    tackles_faced: int = 0            # Total tackle attempts faced

    # QB advanced stats
    time_to_throw_total: float = 0.0  # Cumulative time to throw (seconds)
    throw_count: int = 0              # Number of throws for averaging

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

    # Punting stats (Punter)
    punts: int = 0
    punt_yards: int = 0
    net_punt_yards: int = 0
    long_punts: int = 0
    punts_inside_20: int = 0
    punts_downed: int = 0

    # Punt return stats (Returner)
    punt_returns: int = 0
    punt_return_yards: int = 0
    fair_catches: int = 0
    muffed_punts: int = 0
    long_punt_returns: int = 0

    # Snap tracking (playing time)
    offensive_snaps: int = 0  # Snaps played on offense
    defensive_snaps: int = 0  # Snaps played on defense
    # Note: total_snaps is now a computed property - see below

    # Extra point stats
    extra_points_made: int = 0
    extra_points_attempted: int = 0

    # Distance-based FG tracking
    fg_attempts_0_39: int = 0
    fg_made_0_39: int = 0
    fg_attempts_40_49: int = 0
    fg_made_40_49: int = 0
    fg_attempts_50_plus: int = 0
    fg_made_50_plus: int = 0

    # Additional passing stats for holders on fake field goals
    passing_touchdowns: int = 0
    rushing_tds: int = 0  # Database-compatible name (was: rushing_touchdowns)
    
    # Special stats
    penalties: int = 0
    penalty_yards: int = 0
    
    def add_carry(self, yards: int):
        """Add rushing attempt and yards"""
        self.rushing_attempts += 1
        self.rushing_yards += yards

    def add_yards_after_contact(self, yards: int):
        """Add yards gained after initial defender contact (RB power/elusiveness metric)"""
        self.yards_after_contact += yards

    def add_tackle(self, assisted: bool = False):
        """Add tackle (solo or assisted)"""
        if assisted:
            self.assisted_tackles += 1
        else:
            self.tackles += 1

    def add_missed_tackle(self):
        """Record a missed tackle attempt (failed to bring down ball carrier)"""
        self.missed_tackles += 1

    def add_block(self, successful: bool = True):
        """Add blocking attempt"""
        if successful:
            self.blocks_made += 1
        else:
            self.blocks_missed += 1

    # Advanced offensive line helper methods
    def add_pancake(self):
        """Add a pancake block (dominant block where lineman completely controls defender)"""
        self.pancakes += 1
        self.blocks_made += 1  # Pancakes count as successful blocks

    def add_sack_allowed(self):
        """Add a sack allowed by this lineman"""
        self.sacks_allowed += 1

    def add_pressure_allowed(self):
        """Add a pressure allowed by this lineman"""
        self.pressures_allowed += 1

    def add_hurry_allowed(self):
        """Add a hurry allowed (QB rushed into quick throw)"""
        self.hurries_allowed += 1

    def add_missed_assignment(self):
        """Add a missed assignment/mental error"""
        self.missed_assignments += 1
        self.blocks_missed += 1  # Missed assignments count as missed blocks

    def add_holding_penalty(self):
        """Add a holding penalty"""
        self.holding_penalties += 1

    def add_false_start_penalty(self):
        """Add a false start penalty"""
        self.false_start_penalties += 1

    def add_downfield_block(self):
        """Add a downfield block (screens, draws, etc.)"""
        self.downfield_blocks += 1
        self.blocks_made += 1

    def add_double_team_block(self):
        """Add a successful double-team block"""
        self.double_team_blocks += 1
        self.blocks_made += 1

    def add_chip_block(self):
        """Add a chip block before releasing"""
        self.chip_blocks += 1
        self.blocks_made += 1

    def set_run_blocking_grade(self, grade: float):
        """Set run blocking grade (0-100)"""
        self.run_blocking_grade = max(0.0, min(100.0, grade))

    def set_pass_blocking_efficiency(self, efficiency: float):
        """Set pass blocking efficiency (0-100)"""
        self.pass_blocking_efficiency = max(0.0, min(100.0, efficiency))
    
    def add_coverage_target(self, completed: bool, yards: int):
        """Track a pass thrown at this player while in coverage (DB/LB grading metric)"""
        self.coverage_targets += 1
        if completed:
            self.coverage_completions += 1
            self.coverage_yards_allowed += yards

    @property
    def catch_rate_allowed(self) -> float:
        """Calculate catch rate allowed in coverage (lower is better)"""
        if self.coverage_targets == 0:
            return 0.0
        return self.coverage_completions / self.coverage_targets

    # Pass rush helper methods (DL grading)
    def add_pass_rush_attempt(self, won: bool, double_teamed: bool = False):
        """Track a pass rush attempt and outcome (DL grading metric)"""
        self.pass_rush_attempts += 1
        self.blocking_encounters += 1
        if won:
            self.pass_rush_wins += 1
        if double_teamed:
            self.times_double_teamed += 1

    @property
    def pass_rush_win_rate(self) -> float:
        """Calculate pass rush win rate (higher is better for DL)"""
        if self.pass_rush_attempts == 0:
            return 0.0
        return self.pass_rush_wins / self.pass_rush_attempts

    @property
    def double_team_rate(self) -> float:
        """Calculate how often this player is double-teamed (higher = more dominant)"""
        if self.blocking_encounters == 0:
            return 0.0
        return self.times_double_teamed / self.blocking_encounters

    # Ball carrier helper methods (RB/WR grading)
    def add_tackle_faced(self, broken: bool):
        """Track a tackle attempt faced by ball carrier"""
        self.tackles_faced += 1
        if broken:
            self.broken_tackles += 1

    @property
    def broken_tackle_rate(self) -> float:
        """Calculate broken tackle rate (higher is better for ball carriers)"""
        if self.tackles_faced == 0:
            return 0.0
        return self.broken_tackles / self.tackles_faced

    # QB time to throw helper methods
    def add_time_to_throw(self, seconds: float):
        """Track time to throw for a pass attempt (QB grading metric)"""
        self.time_to_throw_total += seconds
        self.throw_count += 1

    @property
    def avg_time_to_throw(self) -> float:
        """Calculate average time to throw (lower can indicate quick release or pressure)"""
        if self.throw_count == 0:
            return 0.0
        return self.time_to_throw_total / self.throw_count

    def add_penalty(self, yards: int):
        """Add penalty and yardage"""
        self.penalties += 1
        self.penalty_yards += yards

    def add_rushing_touchdown(self):
        """Add rushing touchdown"""
        self.rushing_tds += 1

    def add_passing_touchdown(self):
        """Add passing touchdown"""
        self.passing_tds += 1

    def add_receiving_touchdown(self):
        """Add receiving touchdown"""
        self.receiving_tds += 1

    @property
    def total_snaps(self) -> int:
        """Computed total snaps across all phases (offense + defense + special teams)"""
        return self.offensive_snaps + self.defensive_snaps + self.special_teams_snaps

    def add_offensive_snap(self):
        """Record an offensive snap"""
        self.offensive_snaps += 1

    def add_defensive_snap(self):
        """Record a defensive snap"""
        self.defensive_snaps += 1

    def add_special_teams_snap(self):
        """Record a special teams snap"""
        self.special_teams_snaps += 1

    def get_total_stats(self) -> Dict[str, int]:
        """Get all non-zero stats as dictionary"""
        # Use canonical stat fields from enum
        stat_fields = ALL_STAT_FIELDS

        stats = {}
        for field_name, value in self.__dict__.items():
            if field_name in stat_fields and isinstance(value, (int, float)) and value != 0:
                stats[field_name] = value
        return stats

    def get_total_yards(self) -> int:
        """
        Calculate total yards for this player across all categories.

        NFL Standard: Total yards = rushing yards + receiving yards
        Note: Passing yards are credited separately and not included in "total yards"
        for the purposes of player evaluation (QBs have passing yards as their primary metric)

        Returns:
            Total yards accumulated by this player
        """
        return self.rushing_yards + self.receiving_yards

    def get_total_touchdowns(self) -> int:
        """
        Calculate total touchdowns scored by this player across all categories.

        Includes rushing touchdowns, receiving touchdowns, and passing touchdowns.
        Note: passing_tds is for QBs who throw TD passes, passing_touchdowns is for
        non-QBs who throw TD passes (e.g., trick plays)

        Returns:
            Total touchdowns scored by this player
        """
        return self.rushing_tds + self.receiving_tds + self.passing_tds + self.passing_touchdowns

    # ==========================================================================
    # DEPRECATED: Legacy compatibility properties
    # These aliases exist for backwards compatibility with older code.
    # New code should use the canonical field names directly.
    #
    # Known callers to migrate:
    #   - field_goal.py: carries, pass_attempts, completions, rushing_touchdowns
    #   - punt.py: pass_attempts, pass_completions, carries, rushing_touchdowns
    #   - pass_plays.py: pass_attempts, completions
    #   - box_score_generator.py: carries, pass_attempts, completions, rushing_touchdowns
    # ==========================================================================

    @property
    def passing_interceptions(self) -> int:
        """DEPRECATED: Use interceptions_thrown instead"""
        return self.interceptions_thrown

    @property
    def rushing_touchdowns(self) -> int:
        """DEPRECATED: Use rushing_tds instead"""
        return self.rushing_tds

    @rushing_touchdowns.setter
    def rushing_touchdowns(self, value: int) -> None:
        """DEPRECATED: Use rushing_tds instead"""
        self.rushing_tds = value

    @property
    def pass_deflections(self) -> int:
        """DEPRECATED: Use passes_defended instead"""
        return self.passes_defended

    @property
    def field_goals_attempted(self) -> int:
        """DEPRECATED: Use field_goal_attempts instead"""
        return self.field_goal_attempts

    @property
    def carries(self) -> int:
        """DEPRECATED: Use rushing_attempts instead"""
        return self.rushing_attempts

    @carries.setter
    def carries(self, value: int) -> None:
        """DEPRECATED: Use rushing_attempts instead"""
        self.rushing_attempts = value

    @property
    def pass_attempts(self) -> int:
        """DEPRECATED: Use passing_attempts instead"""
        return self.passing_attempts

    @pass_attempts.setter
    def pass_attempts(self, value: int) -> None:
        """DEPRECATED: Use passing_attempts instead"""
        self.passing_attempts = value

    @property
    def completions(self) -> int:
        """DEPRECATED: Use passing_completions instead"""
        return self.passing_completions

    @completions.setter
    def completions(self, value: int) -> None:
        """DEPRECATED: Use passing_completions instead"""
        self.passing_completions = value

    @property
    def pass_completions(self) -> int:
        """DEPRECATED: Use passing_completions instead"""
        return self.passing_completions

    @pass_completions.setter
    def pass_completions(self, value: int) -> None:
        """DEPRECATED: Use passing_completions instead"""
        self.passing_completions = value
    
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
    points_scored: int = 0  # 3 for made FG, 6 for fake TD, 1 for PAT, 2 for 2pt conversion, etc.

    # Extra point specific information (optional, only populated for extra point plays)
    extra_point_outcome: Optional[str] = None  # "pat_made", "pat_missed", "pat_blocked"
    two_point_conversion_outcome: Optional[str] = None  # "two_point_good", "two_point_failed"
    two_point_conversion_type: Optional[str] = None  # "pass" or "run" if 2pt attempt
    
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
        rushers = [stats for stats in self.player_stats if stats.rushing_attempts > 0]
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
        passers = [stats for stats in self.player_stats if stats.passing_attempts > 0]
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

    # Extra point specific methods
    def is_extra_point_play(self) -> bool:
        """Check if this is an extra point play"""
        return self.extra_point_outcome is not None

    def is_two_point_conversion_play(self) -> bool:
        """Check if this is a two-point conversion play"""
        return self.two_point_conversion_outcome is not None

    def was_extra_point_successful(self) -> bool:
        """Check if extra point was successful"""
        return (self.extra_point_outcome == "pat_made" or
                self.two_point_conversion_outcome == "two_point_good" or
                self.points_scored in [1, 2])

    def get_extra_point_summary(self) -> Optional[Dict[str, Any]]:
        """Get extra point specific summary information"""
        if not (self.is_extra_point_play() or self.is_two_point_conversion_play()):
            return None

        summary = {
            "points_scored": self.points_scored,
            "successful": self.was_extra_point_successful()
        }

        if self.is_extra_point_play():
            summary["type"] = "pat"
            summary["outcome"] = self.extra_point_outcome
        else:
            summary["type"] = "two_point_conversion"
            summary["outcome"] = self.two_point_conversion_outcome
            summary["conversion_type"] = self.two_point_conversion_type

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
            total_stats = player_stats.get_total_stats()
            if total_stats:  # Only accumulate players with actual stats
                self._merge_player_stats(player_stats)
    
    # Fields excluded from automatic stat merging (player identity, not stats)
    _MERGE_EXCLUDED_FIELDS = frozenset({
        'player_name', 'player_number', 'position', 'team_id',
        'player_id', 'player_attributes', 'total_snaps'
    })

    # Fields that use max() instead of sum() when merging
    _MERGE_MAX_FIELDS = frozenset({
        'longest_field_goal', 'run_blocking_grade', 'pass_blocking_efficiency'
    })

    # PFF-critical stats to trace for grading audit
    # These stats are required for accurate PFF-style grades but often missing
    _PFF_CRITICAL_STATS = frozenset({
        # Coverage stats (DB/LB grading)
        'coverage_targets', 'coverage_completions', 'coverage_yards_allowed',
        # Pass rush stats (DL grading)
        'pass_rush_wins', 'pass_rush_attempts', 'times_double_teamed', 'blocking_encounters',
        # Ball carrier stats (RB/WR grading)
        'broken_tackles', 'tackles_faced', 'yards_after_contact',
        # QB stats
        'time_to_throw_total', 'throw_count', 'air_yards', 'pressures_faced',
        # OL individual stats
        'sacks_allowed', 'pressures_allowed', 'hurries_allowed',
        # Tackling (currently missing)
        'missed_tackles',
    })

    # Enable/disable PFF stats tracing (set to True to debug stats flow)
    _TRACE_PFF_STATS = False

    def _merge_player_stats(self, incoming_stats: PlayerStats) -> None:
        """
        Merge incoming player stats into accumulated totals using introspection.

        Automatically handles all numeric stat fields:
        - Most fields: summed (rushing_yards, tackles, etc.)
        - Max fields: take maximum (longest_field_goal, grades)
        - Excluded fields: player identity fields not merged

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
                team_id=incoming_stats.team_id,
                player_id=incoming_stats.player_id,
                player_attributes=incoming_stats.player_attributes
            )

        existing = self._player_totals[player_key]

        # PFF stats tracing - log when non-zero PFF-critical stats are being merged
        if self._TRACE_PFF_STATS:
            pff_stats_found = []
            for stat_name in self._PFF_CRITICAL_STATS:
                value = getattr(incoming_stats, stat_name, 0)
                if value:
                    pff_stats_found.append(f"{stat_name}={value}")
            if pff_stats_found:
                print(f"[PFF_TRACE:ACCUMULATOR] {incoming_stats.player_name} ({incoming_stats.position}): "
                      f"{', '.join(pff_stats_found)}")

        # Auto-merge all numeric fields using introspection
        for field_name, incoming_value in incoming_stats.__dict__.items():
            # Skip non-stat fields
            if field_name in self._MERGE_EXCLUDED_FIELDS:
                continue

            # Only merge numeric values
            if not isinstance(incoming_value, (int, float)):
                continue

            # Skip zero values (no stat recorded)
            if incoming_value == 0:
                continue

            existing_value = getattr(existing, field_name, 0)

            # Use max strategy for grade/longest fields, sum for everything else
            if field_name in self._MERGE_MAX_FIELDS:
                setattr(existing, field_name, max(existing_value, incoming_value))
            else:
                setattr(existing, field_name, existing_value + incoming_value)

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
    passing_yards: int = 0  # Gross passing yards (completions only)
    rushing_yards: int = 0
    passing_attempts: int = 0  # Database-compatible name
    passing_completions: int = 0  # Database-compatible name
    touchdowns: int = 0
    first_downs: int = 0
    turnovers: int = 0
    
    # Sack statistics (offensive perspective)
    times_sacked: int = 0
    sack_yards_lost: int = 0  # Total yards lost to sacks
    
    # Defensive Stats (when this team is defending)
    sacks: int = 0
    tackles_for_loss: int = 0
    interceptions: int = 0
    forced_fumbles: int = 0
    passes_defended: int = 0
    
    # Special Teams Stats
    field_goals_attempted: int = 0
    field_goals_made: int = 0
    punt_return_yards: int = 0
    kick_return_yards: int = 0
    
    # Penalties (committed by this team)
    penalties: int = 0
    penalty_yards: int = 0
    
    def get_net_passing_yards(self) -> int:
        """
        Calculate net passing yards (NFL standard).
        Net passing = gross passing yards - sack yards lost
        
        Returns:
            Net passing yards for the team
        """
        return self.passing_yards - self.sack_yards_lost
    
    # Field categories for filtering stats (defined once, used by all methods)
    _OFFENSIVE_FIELDS = frozenset({
        'total_yards', 'passing_yards', 'rushing_yards', 'passing_attempts',
        'passing_completions', 'touchdowns', 'first_downs', 'turnovers',
        'times_sacked', 'sack_yards_lost'
    })

    _DEFENSIVE_FIELDS = frozenset({
        'sacks', 'tackles_for_loss', 'interceptions', 'forced_fumbles', 'passes_defended'
    })

    _SPECIAL_TEAMS_FIELDS = frozenset({
        'field_goals_attempted', 'field_goals_made', 'punt_return_yards', 'kick_return_yards'
    })

    _PENALTY_FIELDS = frozenset({'penalties', 'penalty_yards'})

    def _get_non_zero_stats(self, fields: frozenset) -> Dict[str, int]:
        """Helper to get non-zero stats for a set of field names"""
        return {
            field: value for field in fields
            if isinstance(value := getattr(self, field, 0), (int, float)) and value != 0
        }

    def get_total_offensive_stats(self) -> Dict[str, int]:
        """Get all non-zero offensive stats as dictionary"""
        return self._get_non_zero_stats(self._OFFENSIVE_FIELDS)

    def get_total_defensive_stats(self) -> Dict[str, int]:
        """Get all non-zero defensive stats as dictionary"""
        return self._get_non_zero_stats(self._DEFENSIVE_FIELDS)

    def get_all_stats(self) -> Dict[str, int]:
        """Get all non-zero stats as dictionary"""
        all_fields = (
            self._OFFENSIVE_FIELDS |
            self._DEFENSIVE_FIELDS |
            self._SPECIAL_TEAMS_FIELDS |
            self._PENALTY_FIELDS
        )
        return self._get_non_zero_stats(all_fields)


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
        self._aggregate_play_level_stats(play_summary, offensive_team_id, defensive_team_id)
    
    def _aggregate_offensive_stats(self, player_stats: List[PlayerStats], team_id: int) -> None:
        """Aggregate offensive stats from all players to the team total"""
        team = self._team_totals[team_id]
        
        for player in player_stats:
            # Rushing stats
            team.rushing_yards += player.rushing_yards
            
            # Passing stats
            team.passing_yards += player.passing_yards
            team.passing_attempts += player.passing_attempts
            team.passing_completions += player.passing_completions
            team.touchdowns += player.passing_tds + player.rushing_tds
            
            # Sack stats (offensive perspective)
            team.times_sacked += player.sacks_taken
            team.sack_yards_lost += player.sack_yards_lost
            
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
    
    def _aggregate_play_level_stats(self, play_summary: PlayStatsSummary, offensive_team_id: int, defensive_team_id: int) -> None:
        """
        Aggregate play-level stats like total yards and first downs.
        
        CRITICAL FIX: Only add offensive yards (RUN/PASS) to total_yards.
        Return yards from special teams plays go to separate categories.
        """
        offensive_team = self._team_totals[offensive_team_id]
        defensive_team = self._team_totals[defensive_team_id]
        
        # Handle yards based on play type
        if play_summary.play_type in [PlayType.RUN, PlayType.PASS]:
            # Offensive plays: yards go to total_yards (passing + rushing)
            offensive_team.total_yards += play_summary.yards_gained
            
        elif play_summary.play_type == PlayType.PUNT:
            # Punt return yards go to receiving team (defensive team during punt)
            # Note: play_summary.yards_gained for punts often includes net punt yards
            # For proper implementation, we'd need to extract return yards separately
            # For now, treat positive yards as return yards to receiving team
            if play_summary.yards_gained > 0:
                defensive_team.punt_return_yards += play_summary.yards_gained
                
        elif play_summary.play_type == PlayType.KICKOFF:
            # Kickoff return yards go to receiving team (defensive team during kickoff)
            if play_summary.yards_gained > 0:
                defensive_team.kick_return_yards += play_summary.yards_gained
                
        # Field goals don't contribute to total yards (they're special teams plays)
        # No yards added for PlayType.FIELD_GOAL
        
        # Check for turnovers (interceptions and fumbles lost)
        interceptions = sum(player.interceptions_thrown for player in play_summary.player_stats)
        fumbles_lost = sum(player.fumbles_lost for player in play_summary.player_stats)
        offensive_team.turnovers += interceptions + fumbles_lost
    
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


def create_player_stats_from_player(player, team_id: Optional[int] = None) -> PlayerStats:
    """Create PlayerStats object from existing Player object"""
    # Check if this is a real player (has attributes from real data)
    player_id = None
    player_attributes = None

    # Try to extract team_id from player object if not provided
    extracted_team_id = team_id
    if team_id is None and hasattr(player, 'team_id'):
        extracted_team_id = player.team_id

    # Real players will have more comprehensive attributes
    if hasattr(player, 'ratings') and player.ratings:
        # Use database player_id if available (preferred), otherwise generate for synthetic players
        if hasattr(player, 'player_id') and player.player_id is not None:
            # Database player from roster - use stable player_id
            player_id = player.player_id
        else:
            # Synthetic player (demos/tests) - generate deterministic collision-resistant ID
            # Format: {team_id}{jersey_number:02d}{name_hash:04d}
            # Example: 220512345 = team 22, jersey #5, name hash 12345
            # This provides ~10M unique combinations vs 10K before, drastically reducing collisions
            team_id_part = extracted_team_id if extracted_team_id else 0
            player_id = int(f"{team_id_part}{player.number:02d}{abs(hash(player.name)) % 10000:04d}")
        player_attributes = player.ratings.copy()

    return PlayerStats(
        player_name=player.name,
        player_number=player.number,
        position=player.primary_position,
        team_id=extracted_team_id,
        player_id=player_id,
        player_attributes=player_attributes
    )