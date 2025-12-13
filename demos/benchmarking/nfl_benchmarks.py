"""
NFL 2023 Season Benchmark Data

Contains reference statistics from the 2023 NFL season for comparison
against simulation output. Benchmarks include game-level, team-level,
and position-specific metrics.

Sources: NFL.com, Pro Football Reference, ESPN
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class NFLBenchmark:
    """Single benchmark metric with expected ranges."""
    metric_name: str
    category: str  # 'game', 'team', 'qb', 'rb', 'wr', 'te', 'defense', 'kicker', 'ol'
    nfl_average: float
    nfl_min: float  # Low end of acceptable range
    nfl_max: float  # High end of acceptable range
    unit: str  # 'yards', 'count', 'percentage', 'ratio'
    per_game: bool  # True if this is a per-game average
    description: Optional[str] = None


class NFLBenchmarks2023:
    """
    NFL 2023 Season Reference Data

    All values are per-team per-game averages unless otherwise noted.
    Ranges represent typical variance across the league.
    """

    # =========================================================================
    # GAME-LEVEL METRICS (per team per game)
    # =========================================================================
    GAME_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'points_per_game': NFLBenchmark(
            'points_per_game', 'game', 21.5, 15.0, 28.0,
            'points', True, 'Average points scored per team per game'
        ),
        'total_yards_per_game': NFLBenchmark(
            'total_yards_per_game', 'game', 320.0, 280.0, 380.0,
            'yards', True, 'Total offensive yards per team per game'
        ),
        'passing_yards_per_game': NFLBenchmark(
            'passing_yards_per_game', 'game', 210.0, 170.0, 270.0,
            'yards', True, 'Passing yards per team per game'
        ),
        'rushing_yards_per_game': NFLBenchmark(
            'rushing_yards_per_game', 'game', 115.0, 85.0, 145.0,
            'yards', True, 'Rushing yards per team per game'
        ),
        'first_downs_per_game': NFLBenchmark(
            'first_downs_per_game', 'game', 19.0, 15.0, 24.0,
            'count', True, 'First downs per team per game'
        ),
        'third_down_conversion_pct': NFLBenchmark(
            'third_down_conversion_pct', 'game', 38.0, 30.0, 48.0,
            'percentage', True, 'Third down conversion percentage'
        ),
        'fourth_down_conversion_pct': NFLBenchmark(
            'fourth_down_conversion_pct', 'game', 50.0, 40.0, 65.0,
            'percentage', True, 'Fourth down conversion percentage'
        ),
        'red_zone_td_pct': NFLBenchmark(
            'red_zone_td_pct', 'game', 55.0, 45.0, 65.0,
            'percentage', True, 'Red zone touchdown percentage'
        ),
        'turnovers_per_game': NFLBenchmark(
            'turnovers_per_game', 'game', 1.3, 0.7, 2.0,
            'count', True, 'Turnovers committed per team per game'
        ),
        'sacks_per_game': NFLBenchmark(
            'sacks_per_game', 'game', 2.3, 1.5, 3.5,
            'count', True, 'Sacks recorded by defense per game'
        ),
        'penalties_per_game': NFLBenchmark(
            'penalties_per_game', 'game', 6.5, 4.5, 9.0,
            'count', True, 'Penalties committed per team per game'
        ),
        'penalty_yards_per_game': NFLBenchmark(
            'penalty_yards_per_game', 'game', 52.0, 35.0, 75.0,
            'yards', True, 'Penalty yards per team per game'
        ),
        'plays_per_game': NFLBenchmark(
            'plays_per_game', 'game', 64.0, 55.0, 75.0,
            'count', True, 'Offensive plays per team per game'
        ),
        'time_of_possession': NFLBenchmark(
            'time_of_possession', 'game', 30.0, 25.0, 35.0,
            'minutes', True, 'Time of possession in minutes'
        ),
    }

    # =========================================================================
    # QUARTERBACK METRICS (per QB per game, starting QB)
    # =========================================================================
    QB_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'qb_passing_yards': NFLBenchmark(
            'qb_passing_yards', 'qb', 210.0, 150.0, 300.0,
            'yards', True, 'Passing yards per starting QB per game'
        ),
        'qb_passing_tds': NFLBenchmark(
            'qb_passing_tds', 'qb', 1.4, 0.7, 2.5,
            'count', True, 'Passing TDs per starting QB per game'
        ),
        'qb_passing_attempts': NFLBenchmark(
            'qb_passing_attempts', 'qb', 34.0, 24.0, 45.0,
            'count', True, 'Pass attempts per starting QB per game'
        ),
        'qb_completions': NFLBenchmark(
            'qb_completions', 'qb', 22.0, 15.0, 32.0,
            'count', True, 'Completions per starting QB per game'
        ),
        'qb_completion_pct': NFLBenchmark(
            'qb_completion_pct', 'qb', 65.0, 55.0, 72.0,
            'percentage', True, 'Completion percentage'
        ),
        'qb_interceptions': NFLBenchmark(
            'qb_interceptions', 'qb', 0.7, 0.3, 1.3,
            'count', True, 'Interceptions per starting QB per game'
        ),
        'qb_sacks_taken': NFLBenchmark(
            'qb_sacks_taken', 'qb', 2.3, 1.2, 3.8,
            'count', True, 'Sacks taken per starting QB per game'
        ),
        'qb_yards_per_attempt': NFLBenchmark(
            'qb_yards_per_attempt', 'qb', 7.0, 5.5, 8.5,
            'yards', True, 'Yards per pass attempt'
        ),
        'qb_passer_rating': NFLBenchmark(
            'qb_passer_rating', 'qb', 90.0, 75.0, 110.0,
            'rating', True, 'NFL passer rating (0-158.3 scale)'
        ),
        'qb_rushing_yards': NFLBenchmark(
            'qb_rushing_yards', 'qb', 15.0, 0.0, 45.0,
            'yards', True, 'Rushing yards per starting QB per game'
        ),
    }

    # =========================================================================
    # RUNNING BACK METRICS (per RB1 per game)
    # =========================================================================
    RB_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'rb_rushing_yards': NFLBenchmark(
            'rb_rushing_yards', 'rb', 70.0, 40.0, 110.0,
            'yards', True, 'Rushing yards per lead RB per game'
        ),
        'rb_rushing_tds': NFLBenchmark(
            'rb_rushing_tds', 'rb', 0.5, 0.2, 1.0,
            'count', True, 'Rushing TDs per lead RB per game'
        ),
        'rb_rushing_attempts': NFLBenchmark(
            'rb_rushing_attempts', 'rb', 16.0, 10.0, 24.0,
            'count', True, 'Rushing attempts per lead RB per game'
        ),
        'rb_yards_per_carry': NFLBenchmark(
            'rb_yards_per_carry', 'rb', 4.3, 3.5, 5.5,
            'yards', True, 'Yards per carry'
        ),
        'rb_receptions': NFLBenchmark(
            'rb_receptions', 'rb', 2.5, 0.5, 5.0,
            'count', True, 'Receptions per lead RB per game'
        ),
        'rb_receiving_yards': NFLBenchmark(
            'rb_receiving_yards', 'rb', 18.0, 5.0, 40.0,
            'yards', True, 'Receiving yards per lead RB per game'
        ),
        'rb_total_touches': NFLBenchmark(
            'rb_total_touches', 'rb', 18.0, 12.0, 28.0,
            'count', True, 'Total touches (carries + receptions) per game'
        ),
    }

    # =========================================================================
    # WIDE RECEIVER METRICS (WR1 per game)
    # =========================================================================
    WR_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'wr1_receiving_yards': NFLBenchmark(
            'wr1_receiving_yards', 'wr', 65.0, 40.0, 100.0,
            'yards', True, 'Receiving yards per WR1 per game'
        ),
        'wr1_receptions': NFLBenchmark(
            'wr1_receptions', 'wr', 5.0, 3.0, 8.0,
            'count', True, 'Receptions per WR1 per game'
        ),
        'wr1_targets': NFLBenchmark(
            'wr1_targets', 'wr', 8.0, 5.0, 12.0,
            'count', True, 'Targets per WR1 per game'
        ),
        'wr1_receiving_tds': NFLBenchmark(
            'wr1_receiving_tds', 'wr', 0.4, 0.15, 0.8,
            'count', True, 'Receiving TDs per WR1 per game'
        ),
        'wr_yards_per_reception': NFLBenchmark(
            'wr_yards_per_reception', 'wr', 12.5, 9.0, 16.0,
            'yards', True, 'Yards per reception for WRs'
        ),
        'wr_catch_rate': NFLBenchmark(
            'wr_catch_rate', 'wr', 62.0, 52.0, 72.0,
            'percentage', True, 'Catch rate (receptions/targets)'
        ),
    }

    # =========================================================================
    # TIGHT END METRICS (TE1 per game)
    # =========================================================================
    TE_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'te1_receiving_yards': NFLBenchmark(
            'te1_receiving_yards', 'te', 35.0, 15.0, 60.0,
            'yards', True, 'Receiving yards per TE1 per game'
        ),
        'te1_receptions': NFLBenchmark(
            'te1_receptions', 'te', 3.0, 1.5, 5.5,
            'count', True, 'Receptions per TE1 per game'
        ),
        'te1_targets': NFLBenchmark(
            'te1_targets', 'te', 4.5, 2.5, 7.0,
            'count', True, 'Targets per TE1 per game'
        ),
        'te1_receiving_tds': NFLBenchmark(
            'te1_receiving_tds', 'te', 0.25, 0.1, 0.5,
            'count', True, 'Receiving TDs per TE1 per game'
        ),
    }

    # =========================================================================
    # DEFENSIVE PLAYER METRICS (per player per game)
    # =========================================================================
    DEFENSE_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'def_tackles_per_game': NFLBenchmark(
            'def_tackles_per_game', 'defense', 5.5, 3.0, 9.0,
            'count', True, 'Tackles per defensive player per game (starters)'
        ),
        'def_sacks_per_game': NFLBenchmark(
            'def_sacks_per_game', 'defense', 0.3, 0.1, 0.7,
            'count', True, 'Sacks per defensive player per game'
        ),
        'def_interceptions_per_game': NFLBenchmark(
            'def_interceptions_per_game', 'defense', 0.06, 0.02, 0.15,
            'count', True, 'Interceptions per defensive player per game'
        ),
        'def_passes_defended_per_game': NFLBenchmark(
            'def_passes_defended_per_game', 'defense', 0.4, 0.1, 0.8,
            'count', True, 'Passes defended per DB per game'
        ),
        'def_tackles_for_loss_per_game': NFLBenchmark(
            'def_tackles_for_loss_per_game', 'defense', 0.4, 0.1, 0.8,
            'count', True, 'TFLs per defensive player per game'
        ),
        'def_qb_hits_per_game': NFLBenchmark(
            'def_qb_hits_per_game', 'defense', 0.3, 0.1, 0.6,
            'count', True, 'QB hits per pass rusher per game'
        ),
    }

    # =========================================================================
    # KICKER METRICS
    # =========================================================================
    KICKER_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'fg_accuracy_overall': NFLBenchmark(
            'fg_accuracy_overall', 'kicker', 85.0, 78.0, 92.0,
            'percentage', True, 'Overall field goal accuracy'
        ),
        'fg_accuracy_0_39': NFLBenchmark(
            'fg_accuracy_0_39', 'kicker', 95.0, 90.0, 99.0,
            'percentage', True, 'FG accuracy 0-39 yards'
        ),
        'fg_accuracy_40_49': NFLBenchmark(
            'fg_accuracy_40_49', 'kicker', 85.0, 78.0, 92.0,
            'percentage', True, 'FG accuracy 40-49 yards'
        ),
        'fg_accuracy_50_plus': NFLBenchmark(
            'fg_accuracy_50_plus', 'kicker', 65.0, 55.0, 75.0,
            'percentage', True, 'FG accuracy 50+ yards'
        ),
        'xp_accuracy': NFLBenchmark(
            'xp_accuracy', 'kicker', 94.0, 90.0, 98.0,
            'percentage', True, 'Extra point accuracy'
        ),
        'fg_attempts_per_game': NFLBenchmark(
            'fg_attempts_per_game', 'kicker', 1.8, 1.2, 2.5,
            'count', True, 'FG attempts per game'
        ),
    }

    # =========================================================================
    # OFFENSIVE LINE METRICS (team-level per game)
    # =========================================================================
    OL_BENCHMARKS: Dict[str, NFLBenchmark] = {
        'sacks_allowed_per_game': NFLBenchmark(
            'sacks_allowed_per_game', 'ol', 2.3, 1.2, 3.8,
            'count', True, 'Sacks allowed per game'
        ),
        'qb_pressures_allowed_per_game': NFLBenchmark(
            'qb_pressures_allowed_per_game', 'ol', 8.0, 5.0, 12.0,
            'count', True, 'QB pressures allowed per game'
        ),
        'pressure_rate': NFLBenchmark(
            'pressure_rate', 'ol', 25.0, 18.0, 35.0,
            'percentage', True, 'Pressure rate (pressures / dropbacks)'
        ),
    }

    @classmethod
    def get_all_benchmarks(cls) -> Dict[str, NFLBenchmark]:
        """Return all benchmarks in a single dictionary."""
        all_benchmarks = {}
        all_benchmarks.update(cls.GAME_BENCHMARKS)
        all_benchmarks.update(cls.QB_BENCHMARKS)
        all_benchmarks.update(cls.RB_BENCHMARKS)
        all_benchmarks.update(cls.WR_BENCHMARKS)
        all_benchmarks.update(cls.TE_BENCHMARKS)
        all_benchmarks.update(cls.DEFENSE_BENCHMARKS)
        all_benchmarks.update(cls.KICKER_BENCHMARKS)
        all_benchmarks.update(cls.OL_BENCHMARKS)
        return all_benchmarks

    @classmethod
    def get_benchmarks_by_category(cls, category: str) -> Dict[str, NFLBenchmark]:
        """Return benchmarks for a specific category."""
        category_map = {
            'game': cls.GAME_BENCHMARKS,
            'qb': cls.QB_BENCHMARKS,
            'rb': cls.RB_BENCHMARKS,
            'wr': cls.WR_BENCHMARKS,
            'te': cls.TE_BENCHMARKS,
            'defense': cls.DEFENSE_BENCHMARKS,
            'kicker': cls.KICKER_BENCHMARKS,
            'ol': cls.OL_BENCHMARKS,
        }
        return category_map.get(category, {})
