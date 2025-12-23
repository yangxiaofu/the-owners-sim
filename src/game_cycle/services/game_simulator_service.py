"""
Game Simulator Service for Game Cycle

Unified game simulation service supporting both instant (fast) and full (play-by-play) modes.
Ensures output format is consistent regardless of simulation mode for Stats tab compatibility.

Usage:
    service = GameSimulatorService(db_path, dynasty_id)

    # Instant mode (fast, mock stats)
    result = service.simulate_game(game_id, home_id, away_id, mode=SimulationMode.INSTANT)

    # Full mode (realistic play-by-play)
    result = service.simulate_game(game_id, home_id, away_id, mode=SimulationMode.FULL)

    # Both modes return GameSimulationResult with compatible player_stats format
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.game_cycle.models.injury_models import Injury


class SimulationMode(Enum):
    """Simulation mode selection."""
    INSTANT = "instant"  # Fast mock stats generation (~1s/week)
    FULL = "full"        # Real play-by-play simulation (~3-5s/game)


@dataclass
class GameSimulationResult:
    """
    Unified result format for both simulation modes.

    Contains game outcome, player statistics, and injuries in a format ready for
    database insertion via UnifiedDatabaseAPI.stats_insert_game_stats().
    """
    game_id: str
    home_team_id: int
    away_team_id: int
    home_score: int
    away_score: int
    total_plays: int = 0
    game_duration_minutes: int = 0
    overtime_periods: int = 0
    player_stats: List[Dict[str, Any]] = field(default_factory=list)
    injuries: List["Injury"] = field(default_factory=list)  # Injuries from this game
    drives: List[Any] = field(default_factory=list)  # Play-by-play drives (FULL mode only)
    # Team-level stats for box scores (first_downs, 3rd/4th down, TOP, penalties)
    home_team_stats: Dict[str, Any] = field(default_factory=dict)
    away_team_stats: Dict[str, Any] = field(default_factory=dict)


class GameSimulatorService:
    """
    Unified game simulation service supporting both instant and full modes.

    Ensures output format is consistent regardless of simulation mode,
    allowing the Stats tab to work identically with either approach.

    Attributes:
        db_path: Path to the game cycle database
        dynasty_id: Current dynasty identifier for roster lookups
    """

    def __init__(self, db_path: str, dynasty_id: str):
        """
        Initialize game simulator service.

        Args:
            db_path: Path to game cycle database
            dynasty_id: Dynasty context for roster lookups
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id

    def simulate_game(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        mode: SimulationMode = SimulationMode.INSTANT,
        season: int = 2025,
        week: int = 1,
        is_playoff: bool = False
    ) -> GameSimulationResult:
        """
        Simulate a game using the specified mode.

        Args:
            game_id: Unique game identifier
            home_team_id: Home team ID (1-32)
            away_team_id: Away team ID (1-32)
            mode: Simulation mode (INSTANT or FULL)
            season: Season year
            week: Week number
            is_playoff: Whether this is a playoff game

        Returns:
            GameSimulationResult with scores and player stats
        """
        if mode == SimulationMode.FULL:
            return self._simulate_full(
                game_id, home_team_id, away_team_id,
                season, week, is_playoff
            )
        else:
            return self._simulate_instant(
                game_id, home_team_id, away_team_id,
                season, week, is_playoff
            )

    def _simulate_instant(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        season: int,
        week: int,
        is_playoff: bool
    ) -> GameSimulationResult:
        """
        Fast mock simulation using existing generators.

        Uses score decomposition and rating-weighted stat allocation
        for quick, realistic-looking results. Also generates injuries
        based on player participation.

        Args:
            game_id: Unique game identifier
            home_team_id: Home team ID (1-32)
            away_team_id: Away team ID (1-32)
            season: Season year
            week: Week number
            is_playoff: Whether this is a playoff game

        Returns:
            GameSimulationResult with mock stats and injuries
        """
        from src.game_cycle.game_result_generator import generate_instant_result
        from src.game_cycle.services.mock_stats_generator import MockStatsGenerator

        # Generate score
        home_score, away_score = generate_instant_result(
            home_team_id, away_team_id, is_playoff
        )

        # Generate mock player stats, team stats, and injuries
        stats_gen = MockStatsGenerator(self._db_path, self._dynasty_id, season)
        mock_stats = stats_gen.generate(
            game_id, home_team_id, away_team_id, home_score, away_score, week
        )

        return GameSimulationResult(
            game_id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            total_plays=0,  # Not tracked in instant mode
            game_duration_minutes=0,
            overtime_periods=0,
            player_stats=mock_stats.player_stats,
            injuries=mock_stats.injuries,
            home_team_stats=mock_stats.home_team_stats,
            away_team_stats=mock_stats.away_team_stats
        )

    def _simulate_full(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        season: int,
        week: int,
        is_playoff: bool
    ) -> GameSimulationResult:
        """
        Full play-by-play simulation using FullGameSimulator.

        Runs complete game simulation with realistic play calling,
        formations, and detailed statistics tracking.

        Args:
            game_id: Unique game identifier
            home_team_id: Home team ID (1-32)
            away_team_id: Away team ID (1-32)
            season: Season year
            week: Week number
            is_playoff: Whether this is a playoff game

        Returns:
            GameSimulationResult with detailed play-by-play stats
        """
        from game_management.full_game_simulator import FullGameSimulator

        # Determine overtime type
        overtime_type = "playoffs" if is_playoff else "regular_season"
        season_type = "playoffs" if is_playoff else "regular_season"

        # Create and run simulator
        simulator = FullGameSimulator(
            away_team_id=away_team_id,
            home_team_id=home_team_id,
            dynasty_id=self._dynasty_id,
            db_path=self._db_path,
            overtime_type=overtime_type,
            season_type=season_type
        )

        game_result = simulator.simulate_game()

        # Extract scores
        home_score = game_result.final_score.get(home_team_id, 0)
        away_score = game_result.final_score.get(away_team_id, 0)

        # Convert player stats to database format
        player_stats = self._convert_player_stats(
            game_result, game_id, home_team_id, away_team_id, season_type
        )

        # Generate injuries for full simulation mode
        # Uses the same injury generation as instant mode
        injuries = self._generate_injuries_for_full_sim(
            game_id, player_stats, week, season
        )

        # Grade plays and calculate advanced metrics (FULL mode only)
        try:
            from src.analytics.services import AnalyticsService

            # Extract all plays from drives
            all_plays = []
            for drive in game_result.drives:
                if hasattr(drive, 'plays'):
                    all_plays.extend(drive.plays)

            if all_plays:
                analytics_service = AnalyticsService(self._dynasty_id, self._db_path)
                analytics_service.grade_game(
                    game_id=game_id,
                    season=season,
                    week=week,
                    play_results=all_plays,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id
                )
        except Exception as e:
            # Don't fail the game if analytics fails
            print(f"[WARNING] Analytics grading failed for game {game_id}: {e}")

        # Extract team stats for box scores (first_downs, 3rd/4th down, TOP, penalties)
        home_team_stats = getattr(game_result, 'home_team_stats', {}) or {}
        away_team_stats = getattr(game_result, 'away_team_stats', {}) or {}

        return GameSimulationResult(
            game_id=game_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            home_score=home_score,
            away_score=away_score,
            total_plays=game_result.total_plays,
            game_duration_minutes=game_result.game_duration_minutes,
            overtime_periods=1 if game_result.overtime_played else 0,
            player_stats=player_stats,
            injuries=injuries,
            drives=game_result.drives if hasattr(game_result, 'drives') else [],  # Include for play-by-play
            home_team_stats=home_team_stats,
            away_team_stats=away_team_stats
        )

    def _convert_player_stats(
        self,
        game_result,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        season_type: str
    ) -> List[Dict[str, Any]]:
        """
        Convert FullGameSimulator stats to MockStatsGenerator format.

        The FullGameSimulator returns ~20 stat fields, but the database
        expects 50+ fields. This method maps and enriches the stats.

        Args:
            game_result: GameResult from FullGameSimulator
            game_id: Unique game identifier
            home_team_id: Home team ID
            away_team_id: Away team ID
            season_type: "regular_season" or "playoffs"

        Returns:
            List of player stat dictionaries ready for database insertion
        """
        converted_stats = []

        # Get raw player stats from game result
        raw_stats = game_result.player_stats
        if not raw_stats:
            print(f"[WARNING] No player stats in game result for {game_id}")
            return converted_stats

        for player_stat in raw_stats:
            # Handle both dict and object formats
            if isinstance(player_stat, dict):
                stat = player_stat
            else:
                # Convert dataclass/object to dict
                stat = vars(player_stat) if hasattr(player_stat, '__dict__') else {}

            # Extract base info
            player_name = stat.get('player_name', 'Unknown')
            position = stat.get('position', 'UNK')
            team_id = stat.get('team_id')

            if team_id is None:
                print(f"[WARNING] Skipping player {player_name} - no team_id")
                continue

            # Generate a player_id if not present (use name-based hash)
            player_id = stat.get('player_id')
            if not player_id:
                # Create deterministic ID from name and team
                player_id = f"sim_{team_id}_{player_name.replace(' ', '_').lower()}"

            # Build full stat dict with all 50+ columns
            full_stat = self._build_full_stat_dict(
                dynasty_id=self._dynasty_id,
                game_id=game_id,
                player_id=player_id,
                player_name=player_name,
                team_id=team_id,
                position=position,
                season_type=season_type,
                raw_stat=stat
            )

            converted_stats.append(full_stat)

        # Phase 2: Validation warnings for debugging stats issues
        self._validate_converted_stats(converted_stats)

        return converted_stats

    def _validate_converted_stats(self, converted_stats: List[Dict[str, Any]]) -> None:
        """
        Validate converted stats and log warnings for debugging.

        Helps identify when stats are missing or suspiciously low.
        """
        if not converted_stats:
            return

        # Validate QB stats
        qbs = [s for s in converted_stats if s.get('position') == 'QB']
        for qb in qbs:
            if qb.get('passing_attempts', 0) > 0 and qb.get('passing_yards', 0) == 0:
                print(f"[WARNING] QB {qb.get('player_name')} has {qb.get('passing_attempts')} attempts but 0 yards")
            if qb.get('passing_sacks', 0) == 0 and qb.get('passing_attempts', 0) > 20:
                print(f"[DEBUG] QB {qb.get('player_name')} took 0 sacks with {qb.get('passing_attempts')} attempts")

        # Validate snap counts
        players_with_off_snaps = [s for s in converted_stats if s.get('snap_counts_offense', 0) > 0]
        players_with_def_snaps = [s for s in converted_stats if s.get('snap_counts_defense', 0) > 0]

        if len(players_with_off_snaps) < 11:
            print(f"[WARNING] Only {len(players_with_off_snaps)} players have offensive snap counts (expected 11+)")
        if len(players_with_def_snaps) < 11:
            print(f"[WARNING] Only {len(players_with_def_snaps)} players have defensive snap counts (expected 11+)")

        # Validate receivers have YAC on catches
        receivers = [s for s in converted_stats if s.get('position') in ('WR', 'TE', 'RB')]
        for rec in receivers:
            receptions = rec.get('receptions', 0)
            yac = rec.get('yards_after_catch', 0)
            if receptions > 5 and yac == 0:
                print(f"[DEBUG] {rec.get('player_name')} ({rec.get('position')}) has {receptions} catches but 0 YAC")

    # PFF-critical stats that need to be traced for grading audit
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

    def _build_full_stat_dict(
        self,
        dynasty_id: str,
        game_id: str,
        player_id: str,
        player_name: str,
        team_id: int,
        position: str,
        season_type: str,
        raw_stat: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build a complete stat dictionary with all 50+ columns.

        Maps fields from FullGameSimulator format to database format,
        filling missing fields with appropriate defaults.

        Args:
            dynasty_id: Dynasty identifier
            game_id: Game identifier
            player_id: Player identifier
            player_name: Player full name
            team_id: Team identifier
            position: Position abbreviation
            season_type: Season type string
            raw_stat: Raw stat dict from simulator

        Returns:
            Complete stat dictionary for database insertion
        """
        # PFF stats tracing - log when PFF-critical stats exist in raw_stat
        if self._TRACE_PFF_STATS:
            pff_stats_found = []
            for stat_name in self._PFF_CRITICAL_STATS:
                value = raw_stat.get(stat_name, 0)
                if value:
                    pff_stats_found.append(f"{stat_name}={value}")
            if pff_stats_found:
                print(f"[PFF_TRACE:BUILD_DICT] {player_name} ({position}): "
                      f"{', '.join(pff_stats_found)}")

        # Map field names from simulator to database format
        # FullGameSimulator uses: interceptions_thrown → passing_interceptions
        # FullGameSimulator uses: passes_defended → pass_deflections

        return {
            # Required identifiers
            'dynasty_id': dynasty_id,
            'game_id': game_id,
            'player_id': player_id,
            'player_name': player_name,
            'team_id': team_id,
            'position': position,
            'season_type': season_type,

            # Passing stats
            'passing_yards': raw_stat.get('passing_yards', 0),
            'passing_tds': raw_stat.get('passing_tds', 0),
            'passing_attempts': raw_stat.get('passing_attempts', 0),
            'passing_completions': raw_stat.get('passing_completions', 0),
            'passing_interceptions': raw_stat.get('passing_interceptions',
                                     raw_stat.get('interceptions_thrown', 0)),
            # QB sack stats: FullGameSimulator uses 'sacks_taken'/'sack_yards_lost'
            'passing_sacks': raw_stat.get('passing_sacks',
                            raw_stat.get('sacks_taken', 0)),
            'passing_sack_yards': raw_stat.get('passing_sack_yards',
                                  raw_stat.get('sack_yards_lost', 0)),
            'passing_rating': self._calculate_passer_rating(raw_stat),
            # Air yards: distance ball traveled in air (advanced passing stat)
            'air_yards': raw_stat.get('air_yards', 0),

            # Rushing stats
            'rushing_yards': raw_stat.get('rushing_yards', 0),
            'rushing_tds': raw_stat.get('rushing_tds', 0),
            'rushing_attempts': raw_stat.get('rushing_attempts', 0),
            'rushing_long': raw_stat.get('rushing_long', 0),
            'rushing_20_plus': raw_stat.get('rushing_20_plus', 0),
            'rushing_fumbles': raw_stat.get('rushing_fumbles', 0),
            'fumbles_lost': raw_stat.get('fumbles_lost', 0),

            # Receiving stats
            'receiving_yards': raw_stat.get('receiving_yards', 0),
            'receiving_tds': raw_stat.get('receiving_tds', 0),
            'receptions': raw_stat.get('receptions', 0),
            'targets': raw_stat.get('targets', 0),
            'receiving_long': raw_stat.get('receiving_long', 0),
            # Receiving drops: FullGameSimulator uses 'drops'
            'receiving_drops': raw_stat.get('receiving_drops',
                              raw_stat.get('drops', 0)),
            # Yards after catch: FullGameSimulator uses 'yac'
            'yards_after_catch': raw_stat.get('yards_after_catch',
                                raw_stat.get('yac', 0)),
            'receiving_fumbles': raw_stat.get('receiving_fumbles', 0),

            # Defensive stats - PlayerStats uses 'tackles' for solo and 'assisted_tackles' for assisted
            # Map correctly: tackles_solo <- tackles, tackles_assist <- assisted_tackles
            'tackles_solo': raw_stat.get('tackles_solo', raw_stat.get('tackles', 0)),
            'tackles_assist': raw_stat.get('tackles_assist', raw_stat.get('assisted_tackles', 0)),
            # Total = solo + assisted (calculate if not provided directly)
            'tackles_total': (raw_stat.get('tackles_total', 0) or
                             (raw_stat.get('tackles', 0) + raw_stat.get('assisted_tackles', 0))),
            'sacks': float(raw_stat.get('sacks', 0)),
            'interceptions': raw_stat.get('interceptions', 0),
            'forced_fumbles': raw_stat.get('forced_fumbles', 0),
            'fumbles_recovered': raw_stat.get('fumbles_recovered', 0),
            'passes_defended': raw_stat.get('passes_defended',
                               raw_stat.get('pass_deflections', 0)),
            # Advanced defensive stats
            'tackles_for_loss': raw_stat.get('tackles_for_loss', 0),
            'qb_hits': raw_stat.get('qb_hits', 0),
            'qb_pressures': raw_stat.get('qb_pressures', 0),

            # Kicking/Punting stats
            'field_goals_made': raw_stat.get('field_goals_made', 0),
            'field_goals_attempted': raw_stat.get('field_goals_attempted', 0),
            'extra_points_made': raw_stat.get('extra_points_made', 0),
            'extra_points_attempted': raw_stat.get('extra_points_attempted', 0),
            'punts': raw_stat.get('punts', 0),
            'punt_yards': raw_stat.get('punt_yards', 0),

            # OL stats (tracked in full sim)
            'pass_blocks': raw_stat.get('pass_blocks', 0),
            'pancakes': raw_stat.get('pancakes', 0),
            'sacks_allowed': raw_stat.get('sacks_allowed', 0),
            'hurries_allowed': raw_stat.get('hurries_allowed', 0),
            'pressures_allowed': raw_stat.get('pressures_allowed', 0),
            'run_blocking_grade': float(raw_stat.get('run_blocking_grade', 0.0)),
            'pass_blocking_efficiency': float(raw_stat.get('pass_blocking_efficiency', 0.0)),
            'missed_assignments': raw_stat.get('missed_assignments', 0),
            'holding_penalties': raw_stat.get('holding_penalties', 0),
            'false_start_penalties': raw_stat.get('false_start_penalties', 0),
            'downfield_blocks': raw_stat.get('downfield_blocks', 0),
            'double_team_blocks': raw_stat.get('double_team_blocks', 0),
            'chip_blocks': raw_stat.get('chip_blocks', 0),

            # Snap counts: FullGameSimulator uses 'offensive_snaps', 'defensive_snaps', 'special_teams_snaps'
            'snap_counts_offense': raw_stat.get('snap_counts_offense',
                                   raw_stat.get('offensive_snaps',
                                   raw_stat.get('snap_count', 0))),
            'snap_counts_defense': raw_stat.get('snap_counts_defense',
                                   raw_stat.get('defensive_snaps', 0)),
            'snap_counts_special_teams': raw_stat.get('snap_counts_special_teams',
                                         raw_stat.get('special_teams_snaps', 0)),

            # Fantasy points (calculated)
            'fantasy_points': self._calculate_fantasy_points(raw_stat),

            # ============================================================
            # PFF-CRITICAL STATS - Required for accurate position grading
            # ============================================================

            # Coverage stats (DB/LB grading)
            'coverage_targets': raw_stat.get('coverage_targets', 0),
            'coverage_completions': raw_stat.get('coverage_completions', 0),
            'coverage_yards_allowed': raw_stat.get('coverage_yards_allowed', 0),

            # Pass rush stats (DL grading)
            'pass_rush_wins': raw_stat.get('pass_rush_wins', 0),
            'pass_rush_attempts': raw_stat.get('pass_rush_attempts', 0),
            'times_double_teamed': raw_stat.get('times_double_teamed', 0),
            'blocking_encounters': raw_stat.get('blocking_encounters', 0),

            # Ball carrier stats (RB/WR grading)
            'broken_tackles': raw_stat.get('broken_tackles', 0),
            'tackles_faced': raw_stat.get('tackles_faced', 0),
            'yards_after_contact': raw_stat.get('yards_after_contact', 0),

            # QB advanced stats
            'pressures_faced': raw_stat.get('pressures_faced', 0),
            'time_to_throw_total': raw_stat.get('time_to_throw_total', 0),
            'throw_count': raw_stat.get('throw_count', 0),

            # Tackling stats
            'missed_tackles': raw_stat.get('missed_tackles', 0),
        }

    def _calculate_passer_rating(self, stat: Dict[str, Any]) -> float:
        """
        Calculate NFL passer rating from raw stats.

        Uses the official NFL formula with 4 components (a, b, c, d),
        each capped between 0 and 2.375.

        Args:
            stat: Dictionary with passing stats

        Returns:
            Passer rating (0-158.3 scale)
        """
        attempts = stat.get('passing_attempts', 0)
        if attempts == 0:
            return 0.0

        completions = stat.get('passing_completions', 0)
        yards = stat.get('passing_yards', 0)
        tds = stat.get('passing_tds', 0)
        ints = stat.get('passing_interceptions',
               stat.get('interceptions_thrown', 0))

        # Component a: Completion percentage
        a = ((completions / attempts) - 0.3) * 5
        a = max(0, min(2.375, a))

        # Component b: Yards per attempt
        b = ((yards / attempts) - 3) * 0.25
        b = max(0, min(2.375, b))

        # Component c: Touchdown percentage
        c = (tds / attempts) * 20
        c = max(0, min(2.375, c))

        # Component d: Interception percentage (inverse)
        d = 2.375 - ((ints / attempts) * 25)
        d = max(0, min(2.375, d))

        # Final rating
        rating = ((a + b + c + d) / 6) * 100
        return round(rating, 1)

    def _calculate_fantasy_points(self, stat: Dict[str, Any]) -> float:
        """
        Calculate fantasy points using standard PPR scoring.

        Args:
            stat: Dictionary with player stats

        Returns:
            Total fantasy points
        """
        points = 0.0

        # Passing
        points += stat.get('passing_yards', 0) * 0.04
        points += stat.get('passing_tds', 0) * 4
        ints = stat.get('passing_interceptions',
               stat.get('interceptions_thrown', 0))
        points -= ints * 2

        # Rushing
        points += stat.get('rushing_yards', 0) * 0.1
        points += stat.get('rushing_tds', 0) * 6

        # Receiving
        points += stat.get('receiving_yards', 0) * 0.1
        points += stat.get('receiving_tds', 0) * 6
        points += stat.get('receptions', 0) * 0.5  # PPR

        # Defense (IDP)
        points += stat.get('tackles', stat.get('tackles_total', 0)) * 1
        points += float(stat.get('sacks', 0)) * 2
        points += stat.get('interceptions', 0) * 2

        # Kicking
        points += stat.get('field_goals_made', 0) * 3
        points += stat.get('extra_points_made', 0) * 1

        return round(points, 1)

    def _generate_injuries_for_full_sim(
        self,
        game_id: str,
        player_stats: List[Dict[str, Any]],
        week: int,
        season: int
    ) -> List["Injury"]:
        """
        Generate injuries for full simulation mode.

        Reuses the same injury generation logic as MockStatsGenerator
        to ensure consistent injury rates across both simulation modes.

        Args:
            game_id: Game identifier
            player_stats: List of player stat dicts with snap counts
            week: Game week number
            season: Season year

        Returns:
            List of Injury objects that occurred during the game
        """
        from src.game_cycle.services.injury_service import InjuryService
        import sqlite3

        injuries = []
        injury_service = InjuryService(self._db_path, self._dynasty_id, season)

        for player_stat in player_stats:
            # Calculate total snaps played
            total_snaps = (
                player_stat.get('snap_counts_offense', 0) +
                player_stat.get('snap_counts_defense', 0) +
                player_stat.get('snap_counts_special_teams', 0)
            )

            # Skip players who didn't play
            if total_snaps == 0:
                continue

            player_id = player_stat.get('player_id')
            if not player_id:
                continue

            # Fetch player details needed for injury generation
            player_data = self._get_player_data_for_injury(player_id)
            if not player_data:
                continue

            # Generate injury (returns None if no injury occurs)
            injury = injury_service.generate_injury(
                player=player_data,
                week=week,
                occurred_during='game',
                game_id=game_id
            )

            if injury:
                injuries.append(injury)

        return injuries

    def _get_player_data_for_injury(self, player_id) -> Optional[Dict[str, Any]]:
        """
        Fetch player data needed for injury generation.

        Args:
            player_id: Player ID to look up

        Returns:
            Player data dict with attributes needed for injury calculation,
            or None if not found
        """
        import sqlite3
        import json

        try:
            with sqlite3.connect(self._db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT
                        player_id,
                        first_name,
                        last_name,
                        team_id,
                        positions,
                        attributes,
                        birthdate
                    FROM players
                    WHERE dynasty_id = ? AND player_id = ?
                """, (self._dynasty_id, player_id))

                row = cursor.fetchone()

                if not row:
                    return None

                attributes = json.loads(row['attributes']) if row['attributes'] else {}
                positions = json.loads(row['positions']) if row['positions'] else []

                return {
                    'player_id': row['player_id'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'team_id': row['team_id'],
                    'positions': positions,
                    'attributes': attributes,
                    'birthdate': row['birthdate']
                }

        except Exception as e:
            print(f"[WARNING] Failed to get player data for injury: {e}")
            return None