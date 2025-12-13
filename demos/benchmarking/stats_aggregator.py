"""
Benchmark Statistics Aggregator

Collects and aggregates statistics from multiple game simulations
for comparison against NFL benchmarks.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import defaultdict
import statistics


@dataclass
class GameSummary:
    """Summary statistics from a single game simulation."""
    game_id: int
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    total_plays: int
    total_drives: int
    simulation_time_seconds: float

    # Team stats (per team, will aggregate both teams)
    home_total_yards: int = 0
    away_total_yards: int = 0
    home_passing_yards: int = 0
    away_passing_yards: int = 0
    home_rushing_yards: int = 0
    away_rushing_yards: int = 0
    home_first_downs: int = 0
    away_first_downs: int = 0
    home_turnovers: int = 0
    away_turnovers: int = 0
    home_sacks: int = 0  # Defensive sacks
    away_sacks: int = 0
    home_penalties: int = 0
    away_penalties: int = 0
    home_penalty_yards: int = 0
    away_penalty_yards: int = 0

    # Third down stats
    home_third_down_att: int = 0
    home_third_down_conv: int = 0
    away_third_down_att: int = 0
    away_third_down_conv: int = 0

    # Fourth down stats
    home_fourth_down_att: int = 0
    home_fourth_down_conv: int = 0
    away_fourth_down_att: int = 0
    away_fourth_down_conv: int = 0

    # Red zone stats
    home_red_zone_att: int = 0
    home_red_zone_td: int = 0
    away_red_zone_att: int = 0
    away_red_zone_td: int = 0

    # Time of possession (in seconds)
    home_time_of_possession: float = 0.0
    away_time_of_possession: float = 0.0

    # Defensive stats (from TeamGameStats)
    home_qb_hits: int = 0
    away_qb_hits: int = 0
    home_interceptions: int = 0
    away_interceptions: int = 0
    home_passes_defended: int = 0
    away_passes_defended: int = 0
    home_tackles_for_loss: int = 0
    away_tackles_for_loss: int = 0


@dataclass
class PositionStats:
    """Aggregated stats for a position leader in a single game."""
    player_name: str
    team_id: int
    position: str
    stats: Dict[str, Any] = field(default_factory=dict)


class BenchmarkStatsAggregator:
    """
    Aggregates statistics across multiple game simulations.

    Collects game-level, team-level, and player-level stats
    for comparison against NFL benchmarks.
    """

    def __init__(self):
        self.game_summaries: List[GameSummary] = []
        self._position_stats: Dict[str, List[PositionStats]] = defaultdict(list)
        self._raw_player_stats: List[Dict[str, Any]] = []

    def add_game_result(
        self,
        game_id: int,
        game_result: Any,
        all_stats: Dict[str, Any],
        simulation_time: float
    ):
        """
        Extract and store statistics from a single game result.

        Args:
            game_id: Game identifier
            game_result: GameResult object from FullGameSimulator
            all_stats: Output from stats_aggregator.get_all_statistics()
            simulation_time: Time taken to simulate this game
        """
        # Extract basic info from game_result
        home_team_id = game_result.home_team.team_id
        away_team_id = game_result.away_team.team_id
        home_score = game_result.final_score.get(home_team_id, 0)
        away_score = game_result.final_score.get(away_team_id, 0)

        # Create game summary
        summary = GameSummary(
            game_id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            total_plays=game_result.total_plays,
            total_drives=game_result.total_drives,
            simulation_time_seconds=simulation_time
        )

        # Extract team stats from all_stats
        # Structure from CentralizedStatsAggregator.get_all_statistics():
        # {
        #   'game_info': {...},
        #   'player_statistics': {'all_players': [...], ...},
        #   'team_statistics': {'home_team': {...}, 'away_team': {...}},
        #   'summary': {...}
        # }
        team_statistics = all_stats.get('team_statistics', {})
        home_team_stats = team_statistics.get('home_team', {})
        away_team_stats = team_statistics.get('away_team', {})

        # Extract game info for additional stats
        game_info = all_stats.get('game_info', {})
        situational_stats = game_info.get('situational_stats', {}) if isinstance(game_info, dict) else {}
        drive_outcomes = game_info.get('drive_outcomes', {}) if isinstance(game_info, dict) else {}

        # Extract team stats - structure is TeamStats.__dict__
        if home_team_stats:
            summary.home_passing_yards = home_team_stats.get('passing_yards', 0)
            summary.home_rushing_yards = home_team_stats.get('rushing_yards', 0)
            # Fix: Calculate total_yards from passing + rushing (tracked total_yards is incomplete)
            summary.home_total_yards = summary.home_passing_yards + summary.home_rushing_yards
            summary.home_first_downs = home_team_stats.get('first_downs', 0)
            summary.home_turnovers = home_team_stats.get('turnovers', 0)
            summary.home_sacks = home_team_stats.get('sacks', 0)  # Defensive sacks
            summary.home_penalties = home_team_stats.get('penalties', 0)
            summary.home_penalty_yards = home_team_stats.get('penalty_yards', 0)

        if away_team_stats:
            summary.away_passing_yards = away_team_stats.get('passing_yards', 0)
            summary.away_rushing_yards = away_team_stats.get('rushing_yards', 0)
            # Fix: Calculate total_yards from passing + rushing (tracked total_yards is incomplete)
            summary.away_total_yards = summary.away_passing_yards + summary.away_rushing_yards
            summary.away_first_downs = away_team_stats.get('first_downs', 0)
            summary.away_turnovers = away_team_stats.get('turnovers', 0)
            summary.away_sacks = away_team_stats.get('sacks', 0)
            summary.away_penalties = away_team_stats.get('penalties', 0)
            summary.away_penalty_yards = away_team_stats.get('penalty_yards', 0)

        # Extract per-team situational stats from unified TeamGameStats
        # These are tracked per-team from the start (no more 50/50 splits!)
        home_game_stats = all_stats.get('home_team_game_stats', {})
        away_game_stats = all_stats.get('away_team_game_stats', {})

        if home_game_stats:
            # Third down (per-team) - THIS WAS MISSING BEFORE!
            summary.home_third_down_att = home_game_stats.get('third_down_attempts', 0)
            summary.home_third_down_conv = home_game_stats.get('third_down_conversions', 0)

            # Fourth down (per-team)
            summary.home_fourth_down_att = home_game_stats.get('fourth_down_attempts', 0)
            summary.home_fourth_down_conv = home_game_stats.get('fourth_down_conversions', 0)

            # Red zone (per-team)
            summary.home_red_zone_att = home_game_stats.get('red_zone_attempts', 0)
            summary.home_red_zone_td = home_game_stats.get('red_zone_touchdowns', 0)

            # Time of possession (per-team) - THIS WAS MISSING BEFORE!
            summary.home_time_of_possession = home_game_stats.get('time_of_possession_seconds', 0.0)

            # First downs (per-team) - use if team stats are zero
            home_first_downs_from_game_stats = home_game_stats.get('first_downs', 0)
            if summary.home_first_downs == 0 and home_first_downs_from_game_stats > 0:
                summary.home_first_downs = home_first_downs_from_game_stats

        if away_game_stats:
            # Third down (per-team) - THIS WAS MISSING BEFORE!
            summary.away_third_down_att = away_game_stats.get('third_down_attempts', 0)
            summary.away_third_down_conv = away_game_stats.get('third_down_conversions', 0)

            # Fourth down (per-team)
            summary.away_fourth_down_att = away_game_stats.get('fourth_down_attempts', 0)
            summary.away_fourth_down_conv = away_game_stats.get('fourth_down_conversions', 0)

            # Red zone (per-team)
            summary.away_red_zone_att = away_game_stats.get('red_zone_attempts', 0)
            summary.away_red_zone_td = away_game_stats.get('red_zone_touchdowns', 0)

            # Time of possession (per-team) - THIS WAS MISSING BEFORE!
            summary.away_time_of_possession = away_game_stats.get('time_of_possession_seconds', 0.0)

            # First downs (per-team) - use if team stats are zero
            away_first_downs_from_game_stats = away_game_stats.get('first_downs', 0)
            if summary.away_first_downs == 0 and away_first_downs_from_game_stats > 0:
                summary.away_first_downs = away_first_downs_from_game_stats

        # Extract defensive stats from TeamGameStats (NEW!)
        # These are now tracked per-team directly in CentralizedStatsAggregator
        if home_game_stats:
            summary.home_qb_hits = home_game_stats.get('qb_hits', 0)
            summary.home_interceptions = home_game_stats.get('interceptions', 0)
            summary.home_passes_defended = home_game_stats.get('passes_defended', 0)
            summary.home_tackles_for_loss = home_game_stats.get('tackles_for_loss', 0)

            # Penalties - now tracked per-team in TeamGameStats
            home_penalties_from_game_stats = home_game_stats.get('penalties', 0)
            home_penalty_yards_from_game_stats = home_game_stats.get('penalty_yards', 0)
            if home_penalties_from_game_stats > 0 or home_penalty_yards_from_game_stats > 0:
                summary.home_penalties = home_penalties_from_game_stats
                summary.home_penalty_yards = home_penalty_yards_from_game_stats

        if away_game_stats:
            summary.away_qb_hits = away_game_stats.get('qb_hits', 0)
            summary.away_interceptions = away_game_stats.get('interceptions', 0)
            summary.away_passes_defended = away_game_stats.get('passes_defended', 0)
            summary.away_tackles_for_loss = away_game_stats.get('tackles_for_loss', 0)

            # Penalties - now tracked per-team in TeamGameStats
            away_penalties_from_game_stats = away_game_stats.get('penalties', 0)
            away_penalty_yards_from_game_stats = away_game_stats.get('penalty_yards', 0)
            if away_penalties_from_game_stats > 0 or away_penalty_yards_from_game_stats > 0:
                summary.away_penalties = away_penalties_from_game_stats
                summary.away_penalty_yards = away_penalty_yards_from_game_stats

        # Fallback to game-level stats with 50/50 split if per-team not available
        # (for backwards compatibility with older game results)
        if not home_game_stats and not away_game_stats and situational_stats:
            # First downs - use if team stats are zero (TeamStats.first_downs not tracked)
            total_first_downs = situational_stats.get('first_downs_total', 0)
            if summary.home_first_downs == 0 and summary.away_first_downs == 0 and total_first_downs > 0:
                summary.home_first_downs = total_first_downs // 2
                summary.away_first_downs = total_first_downs - (total_first_downs // 2)

            # Fourth down attempts/conversions - extract from situational_stats
            fourth_down_att = situational_stats.get('fourth_down_attempts', 0)
            fourth_down_conv = situational_stats.get('fourth_down_conversions', 0)
            if fourth_down_att > 0:
                summary.home_fourth_down_att = fourth_down_att // 2
                summary.away_fourth_down_att = fourth_down_att - (fourth_down_att // 2)
                summary.home_fourth_down_conv = fourth_down_conv // 2
                summary.away_fourth_down_conv = fourth_down_conv - (fourth_down_conv // 2)

            # Red zone attempts/scores - extract from situational_stats
            red_zone_att = situational_stats.get('red_zone_attempts', 0)
            red_zone_scores = situational_stats.get('red_zone_scores', 0)
            if red_zone_att > 0:
                summary.home_red_zone_att = red_zone_att // 2
                summary.away_red_zone_att = red_zone_att - (red_zone_att // 2)
                summary.home_red_zone_td = red_zone_scores // 2
                summary.away_red_zone_td = red_zone_scores - (red_zone_scores // 2)

        self.game_summaries.append(summary)

        # Extract player stats and categorize by position
        # Structure: {'player_statistics': {'all_players': [...]}}
        player_statistics = all_stats.get('player_statistics', {})
        player_stats_list = player_statistics.get('all_players', [])

        if player_stats_list:
            self._process_player_stats(player_stats_list, home_team_id, away_team_id)

    def _process_player_stats(
        self,
        player_stats: List[Dict[str, Any]],
        home_team_id: int,
        away_team_id: int
    ):
        """Process and categorize player stats by position."""
        # Store raw stats
        self._raw_player_stats.extend(player_stats)

        # Group by team and position
        home_by_position = defaultdict(list)
        away_by_position = defaultdict(list)

        for ps in player_stats:
            team_id = ps.get('team_id')
            position = ps.get('position', 'UNK')

            if team_id == home_team_id:
                home_by_position[position].append(ps)
            elif team_id == away_team_id:
                away_by_position[position].append(ps)

        # Extract position leaders for each team
        # Note: Position names in stats are full names (e.g., 'quarterback', not 'QB')
        for position_dict, team_id in [(home_by_position, home_team_id),
                                        (away_by_position, away_team_id)]:
            # QB - by passing yards
            self._add_position_leader(position_dict, 'quarterback', 'passing_yards', team_id)

            # RB - by rushing yards (also check fullback)
            self._add_position_leader(position_dict, 'running_back', 'rushing_yards', team_id)

            # WR - by receiving yards (top receiver)
            self._add_position_leader(position_dict, 'wide_receiver', 'receiving_yards', team_id)

            # TE - by receiving yards
            self._add_position_leader(position_dict, 'tight_end', 'receiving_yards', team_id)

            # Kicker - K position
            self._add_position_leader(position_dict, 'kicker', 'field_goals_made', team_id)

            # Defensive players - various positions (using full names)
            for def_pos in ['mike_linebacker', 'inside_linebacker', 'outside_linebacker',
                           'will_linebacker', 'sam_linebacker', 'cornerback',
                           'nickel_cornerback', 'free_safety', 'strong_safety',
                           'defensive_end', 'defensive_tackle', 'nose_tackle']:
                self._add_position_leader(position_dict, def_pos, 'tackles', team_id)

    def _add_position_leader(
        self,
        position_dict: Dict[str, List[Dict]],
        position: str,
        sort_stat: str,
        team_id: int
    ):
        """Add the position leader to the tracking list."""
        players = position_dict.get(position, [])
        if not players:
            return

        # Sort by the key stat
        sorted_players = sorted(
            players,
            key=lambda p: p.get(sort_stat, 0),
            reverse=True
        )

        leader = sorted_players[0]
        pos_stats = PositionStats(
            player_name=leader.get('player_name', 'Unknown'),
            team_id=team_id,
            position=position,
            stats=leader
        )
        self._position_stats[position].append(pos_stats)

    def get_game_averages(self) -> Dict[str, float]:
        """
        Calculate per-game averages across all simulated games.

        Returns:
            Dictionary of metric name to average value
        """
        if not self.game_summaries:
            return {}

        n = len(self.game_summaries)

        # Aggregate team stats (average of both teams per game)
        total_points = sum(g.home_score + g.away_score for g in self.game_summaries)
        total_yards = sum(g.home_total_yards + g.away_total_yards for g in self.game_summaries)
        total_passing = sum(g.home_passing_yards + g.away_passing_yards for g in self.game_summaries)
        total_rushing = sum(g.home_rushing_yards + g.away_rushing_yards for g in self.game_summaries)
        total_first_downs = sum(g.home_first_downs + g.away_first_downs for g in self.game_summaries)
        total_turnovers = sum(g.home_turnovers + g.away_turnovers for g in self.game_summaries)
        total_sacks = sum(g.home_sacks + g.away_sacks for g in self.game_summaries)
        total_penalties = sum(g.home_penalties + g.away_penalties for g in self.game_summaries)
        total_penalty_yards = sum(g.home_penalty_yards + g.away_penalty_yards for g in self.game_summaries)
        total_plays = sum(g.total_plays for g in self.game_summaries)

        # Third down conversion
        third_down_att = sum(
            g.home_third_down_att + g.away_third_down_att
            for g in self.game_summaries
        )
        third_down_conv = sum(
            g.home_third_down_conv + g.away_third_down_conv
            for g in self.game_summaries
        )
        third_down_pct = (third_down_conv / third_down_att * 100) if third_down_att > 0 else 0

        # Fourth down conversion percentage
        fourth_down_att = sum(
            g.home_fourth_down_att + g.away_fourth_down_att
            for g in self.game_summaries
        )
        fourth_down_conv = sum(
            g.home_fourth_down_conv + g.away_fourth_down_conv
            for g in self.game_summaries
        )
        fourth_down_pct = (fourth_down_conv / fourth_down_att * 100) if fourth_down_att > 0 else 0

        # Red zone TD percentage
        red_zone_att = sum(
            g.home_red_zone_att + g.away_red_zone_att
            for g in self.game_summaries
        )
        red_zone_td = sum(
            g.home_red_zone_td + g.away_red_zone_td
            for g in self.game_summaries
        )
        red_zone_td_pct = (red_zone_td / red_zone_att * 100) if red_zone_att > 0 else 0

        # Time of possession (in minutes) - NEW!
        total_time_of_possession = sum(
            g.home_time_of_possession + g.away_time_of_possession
            for g in self.game_summaries
        )

        # Per-team per-game averages (divide by 2*n for both teams)
        team_games = 2 * n

        # Convert TOP from seconds to minutes for per-team average
        time_of_possession_minutes = (total_time_of_possession / 60) / team_games if team_games > 0 else 0

        return {
            'points_per_game': total_points / team_games,
            'total_yards_per_game': total_yards / team_games,
            'passing_yards_per_game': total_passing / team_games,
            'rushing_yards_per_game': total_rushing / team_games,
            'first_downs_per_game': total_first_downs / team_games,
            'turnovers_per_game': total_turnovers / team_games,
            'sacks_per_game': total_sacks / team_games,
            'penalties_per_game': total_penalties / team_games,
            'penalty_yards_per_game': total_penalty_yards / team_games,
            'plays_per_game': total_plays / team_games,
            'third_down_conversion_pct': third_down_pct,
            'fourth_down_conversion_pct': fourth_down_pct,
            'red_zone_td_pct': red_zone_td_pct,
            'time_of_possession': time_of_possession_minutes,  # NEW! In minutes
            # Simulation metadata
            '_games_simulated': n,
            '_total_simulation_time': sum(g.simulation_time_seconds for g in self.game_summaries),
        }

    def get_position_averages(self, position: str) -> Dict[str, float]:
        """
        Calculate per-game averages for a specific position.

        Args:
            position: Position code (QB, RB, WR, TE, K, etc.)

        Returns:
            Dictionary of stat name to average value
        """
        pos_stats = self._position_stats.get(position, [])
        if not pos_stats:
            return {}

        n = len(pos_stats)
        aggregated = defaultdict(float)
        counts = defaultdict(int)

        for ps in pos_stats:
            for stat_name, value in ps.stats.items():
                if isinstance(value, (int, float)):
                    aggregated[stat_name] += value
                    counts[stat_name] += 1

        return {
            stat_name: aggregated[stat_name] / counts[stat_name]
            for stat_name in aggregated
            if counts[stat_name] > 0
        }

    def get_qb_averages(self) -> Dict[str, float]:
        """Get quarterback-specific averages."""
        qb_stats = self._position_stats.get('quarterback', [])
        if not qb_stats:
            return {}

        n = len(qb_stats)

        # Aggregate QB stats
        passing_yards = sum(ps.stats.get('passing_yards', 0) for ps in qb_stats)
        passing_tds = sum(ps.stats.get('passing_tds', 0) for ps in qb_stats)
        passing_attempts = sum(ps.stats.get('passing_attempts', 0) for ps in qb_stats)
        passing_completions = sum(ps.stats.get('passing_completions', 0) for ps in qb_stats)
        interceptions = sum(
            ps.stats.get('interceptions_thrown', ps.stats.get('passing_interceptions', 0))
            for ps in qb_stats
        )
        sacks_taken = sum(
            ps.stats.get('sacks_taken', ps.stats.get('passing_sacks', 0))
            for ps in qb_stats
        )
        rushing_yards = sum(ps.stats.get('rushing_yards', 0) for ps in qb_stats)

        comp_pct = (passing_completions / passing_attempts * 100) if passing_attempts > 0 else 0
        yards_per_attempt = passing_yards / passing_attempts if passing_attempts > 0 else 0

        # Calculate NFL passer rating (0-158.3 scale)
        passer_rating = self._calculate_passer_rating(
            passing_completions, passing_attempts, passing_yards, passing_tds, interceptions
        )

        return {
            'qb_passing_yards': passing_yards / n,
            'qb_passing_tds': passing_tds / n,
            'qb_passing_attempts': passing_attempts / n,
            'qb_completions': passing_completions / n,
            'qb_completion_pct': comp_pct,
            'qb_interceptions': interceptions / n,
            'qb_sacks_taken': sacks_taken / n,
            'qb_yards_per_attempt': yards_per_attempt,
            'qb_rushing_yards': rushing_yards / n,
            'qb_passer_rating': passer_rating,
        }

    def _calculate_passer_rating(
        self,
        completions: int,
        attempts: int,
        yards: int,
        tds: int,
        interceptions: int
    ) -> float:
        """
        Calculate NFL passer rating (0-158.3 scale).

        Uses the official NFL formula:
        A = ((Comp% - 30) * 0.05), clamped 0-2.375
        B = ((Y/A - 3) * 0.25), clamped 0-2.375
        C = (TD% * 0.2), clamped 0-2.375
        D = (2.375 - (INT% * 0.25)), clamped 0-2.375
        Rating = ((A + B + C + D) / 6) * 100
        """
        if attempts == 0:
            return 0.0

        # Calculate component percentages
        comp_pct = (completions / attempts) * 100
        yards_per_att = yards / attempts
        td_pct = (tds / attempts) * 100
        int_pct = (interceptions / attempts) * 100

        # Calculate each component, clamped to 0-2.375
        a = max(0, min(2.375, (comp_pct - 30) * 0.05))
        b = max(0, min(2.375, (yards_per_att - 3) * 0.25))
        c = max(0, min(2.375, td_pct * 0.2))
        d = max(0, min(2.375, 2.375 - (int_pct * 0.25)))

        # Final calculation
        return ((a + b + c + d) / 6) * 100

    def get_rb_averages(self) -> Dict[str, float]:
        """Get running back-specific averages."""
        rb_stats = self._position_stats.get('running_back', [])
        if not rb_stats:
            return {}

        n = len(rb_stats)

        rushing_yards = sum(ps.stats.get('rushing_yards', 0) for ps in rb_stats)
        rushing_tds = sum(ps.stats.get('rushing_tds', 0) for ps in rb_stats)
        rushing_attempts = sum(ps.stats.get('rushing_attempts', 0) for ps in rb_stats)
        receptions = sum(ps.stats.get('receptions', 0) for ps in rb_stats)
        receiving_yards = sum(ps.stats.get('receiving_yards', 0) for ps in rb_stats)

        ypc = rushing_yards / rushing_attempts if rushing_attempts > 0 else 0

        return {
            'rb_rushing_yards': rushing_yards / n,
            'rb_rushing_tds': rushing_tds / n,
            'rb_rushing_attempts': rushing_attempts / n,
            'rb_yards_per_carry': ypc,
            'rb_receptions': receptions / n,
            'rb_receiving_yards': receiving_yards / n,
            'rb_total_touches': (rushing_attempts + receptions) / n,
        }

    def get_wr_averages(self) -> Dict[str, float]:
        """Get wide receiver (WR1) averages."""
        wr_stats = self._position_stats.get('wide_receiver', [])
        if not wr_stats:
            return {}

        n = len(wr_stats)

        receiving_yards = sum(ps.stats.get('receiving_yards', 0) for ps in wr_stats)
        receiving_tds = sum(ps.stats.get('receiving_tds', 0) for ps in wr_stats)
        receptions = sum(ps.stats.get('receptions', 0) for ps in wr_stats)
        targets = sum(ps.stats.get('targets', 0) for ps in wr_stats)

        ypr = receiving_yards / receptions if receptions > 0 else 0
        catch_rate = (receptions / targets * 100) if targets > 0 else 0

        return {
            'wr1_receiving_yards': receiving_yards / n,
            'wr1_receiving_tds': receiving_tds / n,
            'wr1_receptions': receptions / n,
            'wr1_targets': targets / n,
            'wr_yards_per_reception': ypr,
            'wr_catch_rate': catch_rate,
        }

    def get_te_averages(self) -> Dict[str, float]:
        """Get tight end (TE1) averages."""
        te_stats = self._position_stats.get('tight_end', [])
        if not te_stats:
            return {}

        n = len(te_stats)

        receiving_yards = sum(ps.stats.get('receiving_yards', 0) for ps in te_stats)
        receiving_tds = sum(ps.stats.get('receiving_tds', 0) for ps in te_stats)
        receptions = sum(ps.stats.get('receptions', 0) for ps in te_stats)
        targets = sum(ps.stats.get('targets', 0) for ps in te_stats)

        return {
            'te1_receiving_yards': receiving_yards / n,
            'te1_receiving_tds': receiving_tds / n,
            'te1_receptions': receptions / n,
            'te1_targets': targets / n,
        }

    def get_kicker_averages(self) -> Dict[str, float]:
        """Get kicker averages."""
        k_stats = self._position_stats.get('kicker', [])
        if not k_stats:
            return {}

        n = len(k_stats)

        # Note: PlayerStats uses field_goal_attempts (singular), TeamStats uses field_goals_attempted (plural)
        fg_made = sum(ps.stats.get('field_goals_made', 0) for ps in k_stats)
        fg_att = sum(ps.stats.get('field_goal_attempts', ps.stats.get('field_goals_attempted', 0)) for ps in k_stats)
        xp_made = sum(ps.stats.get('extra_points_made', 0) for ps in k_stats)
        xp_att = sum(ps.stats.get('extra_point_attempts', ps.stats.get('extra_points_attempted', 0)) for ps in k_stats)

        fg_pct = (fg_made / fg_att * 100) if fg_att > 0 else 0
        xp_pct = (xp_made / xp_att * 100) if xp_att > 0 else 0

        # Distance-based FG stats
        fg_0_39_made = sum(ps.stats.get('fg_made_0_39', 0) for ps in k_stats)
        fg_0_39_att = sum(ps.stats.get('fg_attempts_0_39', 0) for ps in k_stats)
        fg_0_39_pct = (fg_0_39_made / fg_0_39_att * 100) if fg_0_39_att > 0 else 0

        fg_40_49_made = sum(ps.stats.get('fg_made_40_49', 0) for ps in k_stats)
        fg_40_49_att = sum(ps.stats.get('fg_attempts_40_49', 0) for ps in k_stats)
        fg_40_49_pct = (fg_40_49_made / fg_40_49_att * 100) if fg_40_49_att > 0 else 0

        fg_50_plus_made = sum(ps.stats.get('fg_made_50_plus', 0) for ps in k_stats)
        fg_50_plus_att = sum(ps.stats.get('fg_attempts_50_plus', 0) for ps in k_stats)
        fg_50_plus_pct = (fg_50_plus_made / fg_50_plus_att * 100) if fg_50_plus_att > 0 else 0

        return {
            'fg_accuracy_overall': fg_pct,
            'fg_accuracy_0_39': fg_0_39_pct,
            'fg_accuracy_40_49': fg_40_49_pct,
            'fg_accuracy_50_plus': fg_50_plus_pct,
            'xp_accuracy': xp_pct,
            'fg_attempts_per_game': fg_att / n,
            '_fg_made': fg_made,
            '_fg_attempted': fg_att,
            '_xp_made': xp_made,
            '_xp_attempted': xp_att,
            '_fg_0_39_made': fg_0_39_made,
            '_fg_0_39_att': fg_0_39_att,
            '_fg_40_49_made': fg_40_49_made,
            '_fg_40_49_att': fg_40_49_att,
            '_fg_50_plus_made': fg_50_plus_made,
            '_fg_50_plus_att': fg_50_plus_att,
        }

    def get_defense_averages(self) -> Dict[str, float]:
        """Get defensive player averages (across all defensive positions).

        NFL defensive player stats are "per player per game" for starters.
        We calculate: total_stat / (num_games * defenders_per_game)

        For tackles, we only count players who recorded tackles to match
        NFL tracking (tacklers are identified, non-tacklers don't show 0).
        """
        # Combine all defensive positions (using full position names)
        def_positions = ['mike_linebacker', 'inside_linebacker', 'outside_linebacker',
                        'will_linebacker', 'sam_linebacker', 'cornerback',
                        'nickel_cornerback', 'free_safety', 'strong_safety',
                        'defensive_end', 'defensive_tackle', 'nose_tackle']
        all_def_stats = []

        for pos in def_positions:
            all_def_stats.extend(self._position_stats.get(pos, []))

        if not all_def_stats and not self.game_summaries:
            return {}

        n = len(all_def_stats) if all_def_stats else 1
        num_games = len(self.game_summaries) if self.game_summaries else 1
        team_games = 2 * num_games  # Both teams per game

        # Sum all stats from player stats (for tackles, sacks from position leaders)
        # NFL "total tackles" = solo tackles + assisted tackles
        solo_tackles = sum(ps.stats.get('tackles', 0) for ps in all_def_stats)
        assisted_tackles = sum(ps.stats.get('assisted_tackles', 0) for ps in all_def_stats)
        tackles = solo_tackles + assisted_tackles
        sacks = sum(ps.stats.get('sacks', 0) for ps in all_def_stats)

        # For tackles: only count entries with any tackles to avoid dilution
        # NFL tracks tacklers only - non-tacklers don't appear with 0 tackles
        tackles_entries = [ps for ps in all_def_stats
                          if ps.stats.get('tackles', 0) > 0 or ps.stats.get('assisted_tackles', 0) > 0]
        tackles_n = len(tackles_entries) if tackles_entries else 1

        # PRIORITY: Use team-level stats from GameSummary (tracked via TeamGameStats)
        # These are more accurate because they track ALL defensive stats, not just tackle leaders
        total_qb_hits = sum(g.home_qb_hits + g.away_qb_hits for g in self.game_summaries)
        total_interceptions = sum(g.home_interceptions + g.away_interceptions for g in self.game_summaries)
        total_passes_defended = sum(g.home_passes_defended + g.away_passes_defended for g in self.game_summaries)
        total_tfl = sum(g.home_tackles_for_loss + g.away_tackles_for_loss for g in self.game_summaries)

        # Fallback to player stats if team stats are zero
        if total_interceptions == 0:
            total_interceptions = sum(ps.stats.get('interceptions', 0) for ps in all_def_stats)
        if total_passes_defended == 0:
            total_passes_defended = sum(ps.stats.get('passes_defended', 0) for ps in all_def_stats)
        if total_tfl == 0:
            total_tfl = sum(ps.stats.get('tackles_for_loss', 0) for ps in all_def_stats)
        if total_qb_hits == 0:
            total_qb_hits = sum(ps.stats.get('qb_hits', 0) for ps in all_def_stats)

        return {
            'def_tackles_per_game': tackles / tackles_n if tackles_n > 0 else 0,
            'def_sacks_per_game': sacks / n if n > 0 else 0,
            'def_interceptions_per_game': total_interceptions / n if n > 0 else 0,
            'def_passes_defended_per_game': total_passes_defended / n if n > 0 else 0,
            'def_tackles_for_loss_per_game': total_tfl / n if n > 0 else 0,
            'def_qb_hits_per_game': total_qb_hits / n if n > 0 else 0,
        }

    def get_distribution_stats(self, metric: str) -> Dict[str, float]:
        """
        Calculate distribution statistics for a metric.

        Args:
            metric: Name of the metric (e.g., 'points_per_game')

        Returns:
            Dictionary with min, max, mean, std_dev, median, p25, p75
        """
        values = self._extract_metric_values(metric)
        if not values:
            return {}

        return {
            'min': min(values),
            'max': max(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'p25': statistics.quantiles(values, n=4)[0] if len(values) >= 4 else min(values),
            'p75': statistics.quantiles(values, n=4)[2] if len(values) >= 4 else max(values),
            'count': len(values),
        }

    def _extract_metric_values(self, metric: str) -> List[float]:
        """Extract per-game values for a specific metric."""
        values = []

        for g in self.game_summaries:
            if metric == 'points_per_game':
                values.append(g.home_score)
                values.append(g.away_score)
            elif metric == 'total_yards_per_game':
                values.append(g.home_total_yards)
                values.append(g.away_total_yards)
            elif metric == 'passing_yards_per_game':
                values.append(g.home_passing_yards)
                values.append(g.away_passing_yards)
            elif metric == 'rushing_yards_per_game':
                values.append(g.home_rushing_yards)
                values.append(g.away_rushing_yards)
            # Add more metrics as needed

        return values

    def export_raw_data(self) -> Dict[str, Any]:
        """Export all raw data for JSON/CSV output."""
        return {
            'game_summaries': [
                {
                    'game_id': g.game_id,
                    'home_team_id': g.home_team_id,
                    'away_team_id': g.away_team_id,
                    'home_score': g.home_score,
                    'away_score': g.away_score,
                    'total_plays': g.total_plays,
                    'simulation_time': g.simulation_time_seconds,
                    'home_total_yards': g.home_total_yards,
                    'away_total_yards': g.away_total_yards,
                    'home_passing_yards': g.home_passing_yards,
                    'away_passing_yards': g.away_passing_yards,
                    'home_rushing_yards': g.home_rushing_yards,
                    'away_rushing_yards': g.away_rushing_yards,
                }
                for g in self.game_summaries
            ],
            'position_stats': {
                position: [
                    {
                        'player_name': ps.player_name,
                        'team_id': ps.team_id,
                        'stats': ps.stats,
                    }
                    for ps in stats_list
                ]
                for position, stats_list in self._position_stats.items()
            },
            'aggregated_averages': {
                'game': self.get_game_averages(),
                'qb': self.get_qb_averages(),
                'rb': self.get_rb_averages(),
                'wr': self.get_wr_averages(),
                'te': self.get_te_averages(),
                'kicker': self.get_kicker_averages(),
                'defense': self.get_defense_averages(),
            },
        }
