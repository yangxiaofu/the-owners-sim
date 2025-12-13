"""
Analytics Service

Orchestrates grading, metrics calculation, and storage for the
Advanced Analytics & PFF Grades system.

This service:
1. Grades all players for each play in a game
2. Aggregates play grades to game grades
3. Calculates advanced metrics (EPA, success rate)
4. Updates season grades and rankings
5. Persists all data to the database
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from collections import defaultdict
import logging

from analytics.models import PlayGrade, GameGrade, SeasonGrade, AdvancedMetrics, PlayContext
from analytics.grading_algorithm import StandardGradingAlgorithm, calculate_rankings
from analytics.advanced_metrics import AdvancedMetricsCalculator
from analytics.position_graders import create_all_graders

if TYPE_CHECKING:
    from game_cycle.database.play_grades_api import PlayGradesAPI
    from game_cycle.database.analytics_api import AnalyticsAPI

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Orchestrates grading and metrics calculation for games.

    Usage:
        service = AnalyticsService(dynasty_id, db_path)
        game_grades = service.grade_game(game_result, play_by_play)
        service.update_season_grades(season)
    """

    def __init__(self, dynasty_id: str, db_path: str):
        """Initialize the analytics service.

        Args:
            dynasty_id: Dynasty identifier for data isolation
            db_path: Path to the game cycle database
        """
        self.dynasty_id = dynasty_id
        self.db_path = db_path

        # Initialize grading components
        self.position_graders = create_all_graders()
        self.grading_algorithm = StandardGradingAlgorithm(self.position_graders)
        self.metrics_calculator = AdvancedMetricsCalculator()

        # Initialize database APIs lazily to avoid import cycles
        self._play_grades_api: Optional["PlayGradesAPI"] = None
        self._analytics_api: Optional["AnalyticsAPI"] = None

    @property
    def play_grades_api(self) -> "PlayGradesAPI":
        """Lazy-load PlayGradesAPI."""
        if self._play_grades_api is None:
            from game_cycle.database.play_grades_api import PlayGradesAPI
            self._play_grades_api = PlayGradesAPI(self.db_path)
        return self._play_grades_api

    @property
    def analytics_api(self) -> "AnalyticsAPI":
        """Lazy-load AnalyticsAPI."""
        if self._analytics_api is None:
            from game_cycle.database.analytics_api import AnalyticsAPI
            self._analytics_api = AnalyticsAPI(self.db_path)
        return self._analytics_api

    def grade_game(
        self,
        game_id: str,
        season: int,
        week: int,
        play_results: List[Any],
        home_team_id: int,
        away_team_id: int,
    ) -> List[GameGrade]:
        """Grade all players in a game from play-by-play data.

        This is the main entry point for grading a game. It:
        1. Creates PlayContext for each play
        2. Grades each player on each play
        3. Aggregates to game grades
        4. Calculates advanced metrics
        5. Persists everything to the database

        Args:
            game_id: Unique game identifier
            season: Season year
            week: Week number
            play_results: List of PlayResult objects from play engine
            home_team_id: Home team ID (1-32)
            away_team_id: Away team ID (1-32)

        Returns:
            List of GameGrade objects for all players
        """
        logger.info(f"Grading game {game_id} with {len(play_results)} plays")

        # Track play grades by player
        all_play_grades: Dict[int, List[PlayGrade]] = defaultdict(list)

        # Track play data for metrics calculation
        home_plays: List[Dict] = []
        away_plays: List[Dict] = []

        # Grade each play
        for play_num, play_result in enumerate(play_results):
            context = self._build_play_context(game_id, play_num, play_result)

            # Get player stats from play result
            player_stats_summary = getattr(play_result, "player_stats_summary", None)
            if player_stats_summary is None:
                continue

            player_stats_list = getattr(player_stats_summary, "player_stats", [])

            for player_stats in player_stats_list:
                player_id = getattr(player_stats, "player_id", 0) or getattr(
                    player_stats, "player_number", 0
                )
                if not player_id:
                    continue

                # Skip players who didn't actually participate
                # This prevents backup players from getting baseline grades
                if not self._player_participated(player_stats):
                    continue

                team_id = getattr(player_stats, "team_id", 0)

                # Determine if offense based on team and play type
                is_offense = self._is_offensive_player(player_stats, context, home_team_id)
                context.is_offense = is_offense

                # Grade the play
                grade = self.grading_algorithm.grade_play(
                    context, player_stats, play_result
                )
                # Store is_offense directly on grade to avoid context sharing bug
                # (context is shared by reference and gets overwritten)
                grade.is_offense = is_offense
                all_play_grades[player_id].append(grade)

            # Collect play data for metrics (always collect, split by offensive team)
            play_data = self._extract_play_data(play_result, context)
            offensive_team = getattr(play_result, "offensive_team_id", None)
            if offensive_team == home_team_id:
                home_plays.append(play_data)
            elif offensive_team == away_team_id:
                away_plays.append(play_data)
            # If offensive_team_id is not set, skip this play for metrics

        # Store play grades in batch
        all_grades_flat = [g for grades in all_play_grades.values() for g in grades]
        if all_grades_flat:
            try:
                self.play_grades_api.insert_play_grades_batch(
                    self.dynasty_id, all_grades_flat
                )
                logger.info(f"Stored {len(all_grades_flat)} play grades")
            except Exception as e:
                logger.error(f"Failed to store play grades: {e}")

        # Aggregate to game grades
        game_grades = []
        for player_id, play_grades in all_play_grades.items():
            if not play_grades:
                continue

            game_grade = self.grading_algorithm.aggregate_to_game(
                play_grades, game_id, season, week
            )
            game_grades.append(game_grade)

        # Store game grades
        if game_grades:
            try:
                self.analytics_api.insert_game_grades_batch(
                    self.dynasty_id, game_grades
                )
                logger.info(f"Stored {len(game_grades)} game grades")
            except Exception as e:
                logger.error(f"Failed to store game grades: {e}")

        # Calculate and store advanced metrics
        self._calculate_and_store_metrics(
            game_id, home_team_id, away_team_id, home_plays, away_plays
        )

        return game_grades

    def update_season_grades(self, season: int) -> List[SeasonGrade]:
        """Recalculate season grades and rankings for all players.

        Should be called after each week's games are graded, or at
        the end of the season.

        Args:
            season: Season year to update

        Returns:
            List of updated SeasonGrade objects
        """
        logger.info(f"Updating season grades for season {season}")

        # Get all game grades for the season
        game_grades = self.analytics_api.get_all_game_grades_for_season(
            self.dynasty_id, season
        )

        if not game_grades:
            logger.info("No game grades found for season")
            return []

        # Group by player
        by_player: Dict[int, List[GameGrade]] = defaultdict(list)
        for gg in game_grades:
            by_player[gg.player_id].append(gg)

        # Aggregate to season grades
        season_grades = []
        for player_id, grades in by_player.items():
            if not grades:
                continue

            season_grade = self.grading_algorithm.aggregate_to_season(grades)
            season_grades.append(season_grade)

        # Calculate rankings
        calculate_rankings(season_grades)

        # Persist
        if season_grades:
            try:
                self.analytics_api.upsert_season_grades_batch(
                    self.dynasty_id, season_grades
                )
                logger.info(f"Updated {len(season_grades)} season grades")
            except Exception as e:
                logger.error(f"Failed to update season grades: {e}")

        return season_grades

    def _build_play_context(self, game_id: str, play_num: int, play_result: Any) -> PlayContext:
        """Build PlayContext from a PlayResult."""
        # Extract context from play result
        yards = getattr(play_result, "yards", 0)
        outcome = getattr(play_result, "outcome", "unknown")

        # Determine play type
        if "pass" in outcome.lower():
            play_type = "pass"
        elif "rush" in outcome.lower() or "run" in outcome.lower():
            play_type = "run"
        elif "punt" in outcome.lower():
            play_type = "punt"
        elif "field_goal" in outcome.lower():
            play_type = "field_goal"
        elif "kickoff" in outcome.lower():
            play_type = "kickoff"
        else:
            play_type = "unknown"

        # Get game state info (may not always be available)
        return PlayContext(
            game_id=game_id,
            play_number=play_num,
            quarter=getattr(play_result, "quarter", 1),
            down=getattr(play_result, "down", 1),
            distance=getattr(play_result, "distance", 10),
            yard_line=getattr(play_result, "yard_line", 50),
            game_clock=getattr(play_result, "game_clock", 900),
            score_differential=getattr(play_result, "score_differential", 0),
            play_type=play_type,
            is_offense=True,  # Will be updated per player
        )

    def _is_offensive_player(
        self, player_stats: Any, context: PlayContext, home_team_id: int
    ) -> bool:
        """Determine if a player was on offense for this play."""
        team_id = getattr(player_stats, "team_id", 0)

        # Use offensive snaps > 0 as primary indicator
        off_snaps = getattr(player_stats, "offensive_snaps", 0)
        def_snaps = getattr(player_stats, "defensive_snaps", 0)

        if off_snaps > 0:
            return True
        if def_snaps > 0:
            return False

        # Fallback: assume offense if player has offensive stats
        passing = getattr(player_stats, "passing_attempts", 0) or 0
        rushing = getattr(player_stats, "rushing_attempts", 0) or 0
        targets = getattr(player_stats, "targets", 0) or 0

        return (passing + rushing + targets) > 0

    def _player_participated(self, player_stats: Any) -> bool:
        """Check if player was on the field for this play.

        Returns True if player has snaps (was on the field) OR has stats.
        This ensures ALL 22 players on the field get graded, not just
        those who made a stat-generating play.

        PFF-style grading grades EVERY player on the field every play.
        A DL player who holds their gap but doesn't make a tackle
        still contributed to the play and should be graded.
        """
        # Check for snap counts (player was on the field)
        offensive_snaps = getattr(player_stats, "offensive_snaps", 0) or 0
        defensive_snaps = getattr(player_stats, "defensive_snaps", 0) or 0

        if offensive_snaps > 0 or defensive_snaps > 0:
            return True

        # Fallback: Check for actual stats (legacy support)
        # Offensive stats
        passing = getattr(player_stats, "passing_attempts", 0) or 0
        rushing = getattr(player_stats, "rushing_attempts", 0) or 0
        targets = getattr(player_stats, "targets", 0) or 0
        receptions = getattr(player_stats, "receptions", 0) or 0
        blocks_made = getattr(player_stats, "blocks_made", 0) or 0

        # Defensive stats
        tackles = getattr(player_stats, "tackles", 0) or getattr(player_stats, "tackles_total", 0) or 0
        sacks = getattr(player_stats, "sacks", 0) or 0
        interceptions = getattr(player_stats, "interceptions", 0) or 0
        passes_defended = getattr(player_stats, "passes_defended", 0) or 0
        qb_hits = getattr(player_stats, "qb_hits", 0) or 0
        qb_pressures = getattr(player_stats, "qb_pressures", 0) or 0
        forced_fumbles = getattr(player_stats, "forced_fumbles", 0) or 0

        return (passing + rushing + targets + receptions + blocks_made +
                tackles + sacks + interceptions + passes_defended +
                qb_hits + qb_pressures + forced_fumbles) > 0

    def _extract_play_data(self, play_result: Any, context: PlayContext) -> Dict[str, Any]:
        """Extract play data dict for metrics calculation."""
        yards = getattr(play_result, "yards", 0) or 0

        return {
            "play_type": context.play_type,
            "down": context.down,
            "distance": context.distance,
            "yards_gained": yards,
            "start_yard_line": context.yard_line,
            "end_yard_line": min(99, max(1, context.yard_line + yards)),
            "end_down": 1 if yards >= context.distance else min(4, context.down + 1),
            "is_turnover": getattr(play_result, "is_turnover", False),
            "is_score": getattr(play_result, "is_scoring_play", False),
            "points_scored": getattr(play_result, "points", 0) or 0,
            "air_yards": getattr(play_result, "air_yards", 0) or 0,
            "yac": getattr(play_result, "yac", 0) or 0,
            "was_pressured": getattr(play_result, "was_pressured", False),
            "completed": context.play_type == "pass" and yards > 0,
        }

    def _calculate_and_store_metrics(
        self,
        game_id: str,
        home_team_id: int,
        away_team_id: int,
        home_plays: List[Dict],
        away_plays: List[Dict],
    ) -> None:
        """Calculate and store advanced metrics for both teams."""
        # Calculate home team metrics
        if home_plays:
            home_metrics = self.metrics_calculator.calculate_game_metrics(
                game_id, home_team_id, home_plays
            )
            home_metrics.dynasty_id = self.dynasty_id
            try:
                self.analytics_api.insert_advanced_metrics(
                    self.dynasty_id, home_metrics
                )
            except Exception as e:
                logger.error(f"Failed to store home team metrics: {e}")

        # Calculate away team metrics
        if away_plays:
            away_metrics = self.metrics_calculator.calculate_game_metrics(
                game_id, away_team_id, away_plays
            )
            away_metrics.dynasty_id = self.dynasty_id
            try:
                self.analytics_api.insert_advanced_metrics(
                    self.dynasty_id, away_metrics
                )
            except Exception as e:
                logger.error(f"Failed to store away team metrics: {e}")

    # =========================================================================
    # Query Methods (delegate to APIs)
    # =========================================================================

    def get_player_season_grade(
        self, player_id: int, season: int
    ) -> Optional[SeasonGrade]:
        """Get season grade for a player."""
        return self.analytics_api.get_season_grade(
            self.dynasty_id, player_id, season
        )

    def get_grade_leaders(
        self, season: int, position: Optional[str] = None, limit: int = 25
    ) -> List[SeasonGrade]:
        """Get top players by grade."""
        return self.analytics_api.get_grade_leaders(
            self.dynasty_id, season, position, limit
        )

    def get_player_game_grades(
        self, player_id: int, season: Optional[int] = None, limit: int = 20
    ) -> List[GameGrade]:
        """Get game grades for a player."""
        return self.analytics_api.get_player_game_grades(
            self.dynasty_id, player_id, season, limit
        )

    def get_team_grades(self, team_id: int, season: int) -> List[SeasonGrade]:
        """Get all player grades for a team."""
        return self.analytics_api.get_team_season_grades(
            self.dynasty_id, team_id, season
        )
