"""
Team Game Statistics - Unified dataclass for all team-level game statistics.

This is the single source of truth for team statistics used across:
- CentralizedStatsAggregator (game-level aggregation)
- BenchmarkStatsAggregator (multi-game benchmarking)
- Box scores and game summaries

All stats are tracked per-team from the start, eliminating the need for
50/50 splits or other hacks in downstream consumers.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any


@dataclass
class TeamGameStats:
    """
    Single source of truth for all team-level game statistics.

    Combines offensive, defensive, situational, special teams, and penalty
    statistics into one unified structure that flows through the entire
    stats pipeline.
    """
    team_id: int

    # === Offensive Stats ===
    total_yards: int = 0
    passing_yards: int = 0
    rushing_yards: int = 0
    passing_attempts: int = 0
    passing_completions: int = 0
    rushing_attempts: int = 0
    touchdowns: int = 0
    passing_touchdowns: int = 0
    rushing_touchdowns: int = 0

    # === Situational Stats ===
    first_downs: int = 0
    first_downs_passing: int = 0
    first_downs_rushing: int = 0
    first_downs_penalty: int = 0
    third_down_attempts: int = 0
    third_down_conversions: int = 0
    fourth_down_attempts: int = 0
    fourth_down_conversions: int = 0
    red_zone_attempts: int = 0
    red_zone_touchdowns: int = 0
    red_zone_field_goals: int = 0
    goal_to_go_attempts: int = 0
    goal_to_go_touchdowns: int = 0
    time_of_possession_seconds: float = 0.0

    # === Defensive Stats ===
    # These are stats the DEFENSE accumulates (opponent's offensive failures)
    sacks: float = 0.0
    sack_yards: int = 0
    qb_hits: int = 0
    tackles_for_loss: int = 0
    interceptions: int = 0
    interception_yards: int = 0
    forced_fumbles: int = 0
    fumble_recoveries: int = 0
    passes_defended: int = 0
    defensive_touchdowns: int = 0

    # === Turnovers (offensive perspective - turnovers committed) ===
    interceptions_thrown: int = 0
    fumbles_lost: int = 0
    turnovers: int = 0  # Total turnovers committed

    # === Sacks Taken (offensive perspective) ===
    times_sacked: int = 0
    sack_yards_lost: int = 0

    # === Special Teams ===
    field_goals_attempted: int = 0
    field_goals_made: int = 0
    extra_points_attempted: int = 0
    extra_points_made: int = 0
    punts: int = 0
    punt_yards: int = 0
    punt_return_yards: int = 0
    punt_returns: int = 0
    kick_return_yards: int = 0
    kick_returns: int = 0

    # === Penalties ===
    penalties: int = 0
    penalty_yards: int = 0

    # === Scoring ===
    points_scored: int = 0

    # === Computed Properties ===

    @property
    def third_down_pct(self) -> float:
        """Third down conversion percentage."""
        if self.third_down_attempts == 0:
            return 0.0
        return (self.third_down_conversions / self.third_down_attempts) * 100

    @property
    def fourth_down_pct(self) -> float:
        """Fourth down conversion percentage."""
        if self.fourth_down_attempts == 0:
            return 0.0
        return (self.fourth_down_conversions / self.fourth_down_attempts) * 100

    @property
    def red_zone_td_pct(self) -> float:
        """Red zone touchdown percentage."""
        if self.red_zone_attempts == 0:
            return 0.0
        return (self.red_zone_touchdowns / self.red_zone_attempts) * 100

    @property
    def red_zone_scoring_pct(self) -> float:
        """Red zone scoring percentage (TDs + FGs)."""
        if self.red_zone_attempts == 0:
            return 0.0
        scores = self.red_zone_touchdowns + self.red_zone_field_goals
        return (scores / self.red_zone_attempts) * 100

    @property
    def completion_pct(self) -> float:
        """Passing completion percentage."""
        if self.passing_attempts == 0:
            return 0.0
        return (self.passing_completions / self.passing_attempts) * 100

    @property
    def yards_per_play(self) -> float:
        """Average yards per play."""
        total_plays = self.passing_attempts + self.rushing_attempts
        if total_plays == 0:
            return 0.0
        return self.total_yards / total_plays

    @property
    def yards_per_pass(self) -> float:
        """Average yards per pass attempt."""
        if self.passing_attempts == 0:
            return 0.0
        return self.passing_yards / self.passing_attempts

    @property
    def yards_per_rush(self) -> float:
        """Average yards per rush attempt."""
        if self.rushing_attempts == 0:
            return 0.0
        return self.rushing_yards / self.rushing_attempts

    @property
    def time_of_possession_str(self) -> str:
        """Time of possession formatted as MM:SS."""
        minutes = int(self.time_of_possession_seconds // 60)
        seconds = int(self.time_of_possession_seconds % 60)
        return f"{minutes}:{seconds:02d}"

    @property
    def punt_average(self) -> float:
        """Average punt distance."""
        if self.punts == 0:
            return 0.0
        return self.punt_yards / self.punts

    @property
    def field_goal_pct(self) -> float:
        """Field goal percentage."""
        if self.field_goals_attempted == 0:
            return 0.0
        return (self.field_goals_made / self.field_goals_attempted) * 100

    @property
    def turnover_margin(self) -> int:
        """Turnover margin (takeaways - giveaways)."""
        takeaways = self.interceptions + self.fumble_recoveries
        giveaways = self.turnovers
        return takeaways - giveaways

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = asdict(self)
        # Add computed properties
        result['third_down_pct'] = self.third_down_pct
        result['fourth_down_pct'] = self.fourth_down_pct
        result['red_zone_td_pct'] = self.red_zone_td_pct
        result['red_zone_scoring_pct'] = self.red_zone_scoring_pct
        result['completion_pct'] = self.completion_pct
        result['yards_per_play'] = self.yards_per_play
        result['yards_per_pass'] = self.yards_per_pass
        result['yards_per_rush'] = self.yards_per_rush
        result['time_of_possession_str'] = self.time_of_possession_str
        result['punt_average'] = self.punt_average
        result['field_goal_pct'] = self.field_goal_pct
        result['turnover_margin'] = self.turnover_margin
        return result

    def merge_from(self, other: 'TeamGameStats') -> None:
        """
        Merge stats from another TeamGameStats object (same team).
        Used for aggregating drive-level stats into game-level stats.
        """
        if other.team_id != self.team_id:
            raise ValueError(f"Cannot merge stats from different teams: {self.team_id} vs {other.team_id}")

        # Offensive
        self.total_yards += other.total_yards
        self.passing_yards += other.passing_yards
        self.rushing_yards += other.rushing_yards
        self.passing_attempts += other.passing_attempts
        self.passing_completions += other.passing_completions
        self.rushing_attempts += other.rushing_attempts
        self.touchdowns += other.touchdowns
        self.passing_touchdowns += other.passing_touchdowns
        self.rushing_touchdowns += other.rushing_touchdowns

        # Situational
        self.first_downs += other.first_downs
        self.first_downs_passing += other.first_downs_passing
        self.first_downs_rushing += other.first_downs_rushing
        self.first_downs_penalty += other.first_downs_penalty
        self.third_down_attempts += other.third_down_attempts
        self.third_down_conversions += other.third_down_conversions
        self.fourth_down_attempts += other.fourth_down_attempts
        self.fourth_down_conversions += other.fourth_down_conversions
        self.red_zone_attempts += other.red_zone_attempts
        self.red_zone_touchdowns += other.red_zone_touchdowns
        self.red_zone_field_goals += other.red_zone_field_goals
        self.goal_to_go_attempts += other.goal_to_go_attempts
        self.goal_to_go_touchdowns += other.goal_to_go_touchdowns
        self.time_of_possession_seconds += other.time_of_possession_seconds

        # Defensive
        self.sacks += other.sacks
        self.sack_yards += other.sack_yards
        self.qb_hits += other.qb_hits
        self.tackles_for_loss += other.tackles_for_loss
        self.interceptions += other.interceptions
        self.interception_yards += other.interception_yards
        self.forced_fumbles += other.forced_fumbles
        self.fumble_recoveries += other.fumble_recoveries
        self.passes_defended += other.passes_defended
        self.defensive_touchdowns += other.defensive_touchdowns

        # Turnovers
        self.interceptions_thrown += other.interceptions_thrown
        self.fumbles_lost += other.fumbles_lost
        self.turnovers += other.turnovers

        # Sacks taken
        self.times_sacked += other.times_sacked
        self.sack_yards_lost += other.sack_yards_lost

        # Special teams
        self.field_goals_attempted += other.field_goals_attempted
        self.field_goals_made += other.field_goals_made
        self.extra_points_attempted += other.extra_points_attempted
        self.extra_points_made += other.extra_points_made
        self.punts += other.punts
        self.punt_yards += other.punt_yards
        self.punt_return_yards += other.punt_return_yards
        self.punt_returns += other.punt_returns
        self.kick_return_yards += other.kick_return_yards
        self.kick_returns += other.kick_returns

        # Penalties
        self.penalties += other.penalties
        self.penalty_yards += other.penalty_yards

        # Scoring
        self.points_scored += other.points_scored