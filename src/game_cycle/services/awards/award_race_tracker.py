"""
Award Race Tracker Service.

Tracks top performers weekly starting at week 10 for performance optimization
and mid-season "award race" visibility.

Part of Milestone 10: Awards System - Performance Optimization.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from .models import (
    AwardType,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
)
from constants.position_abbreviations import get_position_abbreviation

logger = logging.getLogger(__name__)


# Configuration constants
TRACKING_START_WEEK = 10
CUMULATIVE_LEADERS_LIMIT = 20
WEEKLY_HOT_LIMIT = 5
MINIMUM_GAMES_FOR_TRACKING = 6  # Lower threshold for early tracking

# Default scoring values
DEFAULT_SCORE = 50.0
STATS_WEIGHT = 0.5
GRADE_WEIGHT = 0.5

# Elite benchmarks - QB
QB_ELITE_PASSING_YARDS = 5000
QB_ELITE_PASSING_TDS = 45
QB_YARDS_WEIGHT = 0.35
QB_TD_WEIGHT = 0.35
QB_RATING_WEIGHT = 0.30

# Elite benchmarks - RB
RB_ELITE_TOTAL_YARDS = 2000
RB_ELITE_RUSHING_TDS = 15
RB_YARDS_WEIGHT = 0.60
RB_TD_WEIGHT = 0.40

# Elite benchmarks - Receiver (WR/TE)
RECEIVER_ELITE_YARDS = 1600
RECEIVER_ELITE_TDS = 12
RECEIVER_ELITE_RECEPTIONS = 120
RECEIVER_YARDS_WEIGHT = 0.45
RECEIVER_TD_WEIGHT = 0.35
RECEIVER_REC_WEIGHT = 0.20

# Elite benchmarks - Defense
DEF_ELITE_SACKS = 15
DEF_ELITE_INTERCEPTIONS = 7
DEF_ELITE_TACKLES = 150
DEF_SACKS_WEIGHT = 0.35
DEF_INT_WEIGHT = 0.35
DEF_TACKLES_WEIGHT = 0.30

# Position groupings for scoring (use abbreviations matching player_game_stats.position)
RECEIVER_POSITIONS = frozenset({'WR', 'TE'})


@dataclass
class TrackedPlayer:
    """A player being tracked for an award race."""
    player_id: int
    first_name: str
    last_name: str
    team_id: int
    position: str
    cumulative_score: float
    week_score: float = 0.0
    games_played: int = 0
    is_rookie: bool = False


class AwardRaceTracker:
    """
    Tracks top performers each week for faster end-of-season award calculation.

    The tracker uses a simple scoring algorithm:
    - 50% normalized stats (position-specific)
    - 50% season grade

    Each week, it stores:
    - Top 20 cumulative leaders per award
    - Top 5 "hot" performers for the week (catches late breakouts)
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the award race tracker.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Season year
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Lazy-loaded dependencies
        self._db = None
        self._awards_api = None
        self._stats_api = None
        self._analytics_api = None

    # ============================================
    # Properties (Lazy Loading)
    # ============================================

    @property
    def db(self):
        """Lazy-load GameCycleDatabase."""
        if self._db is None:
            from game_cycle.database.connection import GameCycleDatabase
            self._db = GameCycleDatabase(self._db_path)
        return self._db

    @property
    def awards_api(self):
        """Lazy-load AwardsAPI."""
        if self._awards_api is None:
            from game_cycle.database.awards_api import AwardsAPI
            self._awards_api = AwardsAPI(self.db)
        return self._awards_api

    @property
    def stats_api(self):
        """Lazy-load StatsAPI."""
        if self._stats_api is None:
            from statistics.stats_api import StatsAPI
            self._stats_api = StatsAPI(self._db_path, self._dynasty_id)
        return self._stats_api

    @property
    def analytics_api(self):
        """Lazy-load AnalyticsAPI."""
        if self._analytics_api is None:
            from game_cycle.database.analytics_api import AnalyticsAPI
            self._analytics_api = AnalyticsAPI(self._db_path)
        return self._analytics_api

    # ============================================
    # Public Methods
    # ============================================

    def should_track(self, week: int) -> bool:
        """
        Check if tracking should occur for this week.

        Args:
            week: Current week number

        Returns:
            True if tracking should occur (week >= TRACKING_START_WEEK)
        """
        return week >= TRACKING_START_WEEK

    def update_tracking(self, week: int) -> int:
        """
        Update award race tracking for a given week.

        Args:
            week: Week number (10-18)

        Returns:
            Number of entries tracked
        """
        if not self.should_track(week):
            logger.debug(f"Skipping tracking for week {week} (before week {TRACKING_START_WEEK})")
            return 0

        logger.info(f"Updating award race tracking for week {week}")

        # Track 5 awards (CPOY is end-of-season only)
        award_types = [
            AwardType.MVP,
            AwardType.OPOY,
            AwardType.DPOY,
            AwardType.OROY,
            AwardType.DROY,
        ]

        from game_cycle.database.awards_api import AwardRaceEntry

        all_entries: List[AwardRaceEntry] = []

        for award_type in award_types:
            entries = self._track_award(award_type, week)
            all_entries.extend(entries)

        # Batch insert all entries
        if all_entries:
            count = self.awards_api.batch_upsert_award_race_entries(all_entries)
            logger.info(f"Tracked {count} entries across {len(award_types)} awards for week {week}")
            return count

        return 0

    def get_current_standings(
        self,
        award_type: AwardType,
        week: Optional[int] = None
    ) -> List[Dict]:
        """
        Get current award race standings.

        Args:
            award_type: Type of award
            week: Optional specific week (defaults to latest)

        Returns:
            List of standings dictionaries
        """
        if week is not None:
            entries = self.awards_api.get_award_race_standings(
                self._dynasty_id, self._season, week, award_type.value
            )
        else:
            entries = self.awards_api.get_latest_award_race_standings(
                self._dynasty_id, self._season, award_type.value
            )

        return [e.to_dict() for e in entries]

    # ============================================
    # Private Methods
    # ============================================

    def _track_award(self, award_type: AwardType, week: int) -> List:
        """
        Track top performers for a specific award.

        Args:
            award_type: Type of award to track
            week: Current week

        Returns:
            List of AwardRaceEntry objects
        """
        from game_cycle.database.awards_api import AwardRaceEntry

        # Get all eligible players with scores
        candidates = self._get_scored_candidates(award_type)

        if not candidates:
            logger.debug(f"No candidates found for {award_type.value}")
            return []

        # Sort by cumulative score (descending)
        candidates.sort(key=lambda x: x.cumulative_score, reverse=True)

        # Get cumulative leaders (top 20)
        cumulative_leaders = candidates[:CUMULATIVE_LEADERS_LIMIT]

        # Get weekly hot performers (top 5 by this week's score)
        hot_this_week = sorted(candidates, key=lambda x: x.week_score, reverse=True)[:WEEKLY_HOT_LIMIT]

        # Merge (deduplicate by player_id)
        tracked_ids: Set[int] = set()
        merged: List[TrackedPlayer] = []

        for player in cumulative_leaders:
            if player.player_id not in tracked_ids:
                tracked_ids.add(player.player_id)
                merged.append(player)

        for player in hot_this_week:
            if player.player_id not in tracked_ids:
                tracked_ids.add(player.player_id)
                merged.append(player)

        # Re-sort merged list by cumulative score and assign ranks
        merged.sort(key=lambda x: x.cumulative_score, reverse=True)

        # Create AwardRaceEntry objects
        entries = []
        for rank, player in enumerate(merged, start=1):
            entry = AwardRaceEntry(
                dynasty_id=self._dynasty_id,
                season=self._season,
                week=week,
                award_type=award_type.value,
                player_id=player.player_id,
                team_id=player.team_id,
                position=player.position,
                cumulative_score=player.cumulative_score,
                week_score=player.week_score,
                rank=rank,
                first_name=player.first_name,
                last_name=player.last_name,
            )
            entries.append(entry)

        logger.debug(f"Tracked {len(entries)} players for {award_type.value}")
        return entries

    def _get_scored_candidates(self, award_type: AwardType) -> List[TrackedPlayer]:
        """
        Get all eligible candidates with simple scores.

        Uses player stats directly instead of season grades (which may not exist
        during the regular season).

        Args:
            award_type: Type of award

        Returns:
            List of TrackedPlayer objects with scores
        """
        # Get position filter based on award type
        eligible_positions = self._get_eligible_positions(award_type)
        is_rookie_only = award_type in (AwardType.OROY, AwardType.DROY)

        # Get players with stats this season directly from database
        players_with_stats = self._get_players_with_stats(eligible_positions)

        if not players_with_stats:
            logger.debug(f"No players with stats found for {award_type.value}")
            return []

        candidates = []

        for player_data in players_with_stats:
            player_id = player_data.get('player_id')
            if not player_id:
                continue

            # Check rookie status if needed
            if is_rookie_only:
                years_pro = player_data.get('years_pro', 1)
                if years_pro > 0:
                    continue

            position = player_data.get('position', '')
            if position not in eligible_positions:
                continue

            # Check minimum games
            games_played = player_data.get('games_played', 0)
            if games_played < MINIMUM_GAMES_FOR_TRACKING:
                continue

            # Validate team_id - must be between 1 and 32 (database constraint)
            team_id = player_data.get('team_id')
            if team_id is None or not (1 <= team_id <= 32):
                logger.debug(f"Skipping player {player_id} with invalid team_id: {team_id}")
                continue

            # Calculate score using pre-fetched stats (no DB query needed)
            cumulative_score = self._calculate_stat_score(player_data, award_type)
            week_score = cumulative_score  # Simplified: same as cumulative for now

            candidate = TrackedPlayer(
                player_id=player_id,
                first_name=player_data.get('first_name', ''),
                last_name=player_data.get('last_name', ''),
                team_id=team_id,  # Already validated above
                position=position,
                cumulative_score=cumulative_score,
                week_score=week_score,
                games_played=games_played,
                is_rookie=is_rookie_only,
            )
            candidates.append(candidate)

        logger.debug(f"Found {len(candidates)} candidates for {award_type.value}")
        return candidates

    def _get_players_with_stats(self, eligible_positions: Set[str]) -> List[Dict]:
        """
        Get all players who have stats this season via StatsAPI.

        Uses existing StatsAPI._get_all_player_stats() method which queries
        player_game_stats table (has position column).

        Args:
            eligible_positions: Set of position strings to filter by

        Returns:
            List of player dictionaries with id, name, position, team_id, games_played, years_pro
        """
        try:
            # Use existing StatsAPI method
            all_stats = self.stats_api._get_all_player_stats(self._season)

            if not all_stats:
                logger.debug("No player stats found for season")
                return []

            result = []
            for stats in all_stats:
                raw_position = stats.get('position', '')
                position = get_position_abbreviation(raw_position) if raw_position else ''
                games = stats.get('games', 0)

                if position in eligible_positions and games >= MINIMUM_GAMES_FOR_TRACKING:
                    # Get years_pro from players table
                    player_info = self._get_player_info(stats.get('player_id'))
                    years_pro = player_info.get('years_pro', 0) if player_info else 0

                    # Parse name from player_name field
                    player_name = stats.get('player_name', '') or ''
                    name_parts = player_name.split()
                    first_name = name_parts[0] if name_parts else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    # Calculate passer rating if QB (not in aggregated stats)
                    passer_rating = 0.0
                    if position == 'QB':
                        passer_rating = self._calculate_passer_rating(
                            stats.get('passing_completions', 0),
                            stats.get('passing_attempts', 0),
                            stats.get('passing_yards', 0),
                            stats.get('passing_touchdowns', 0),
                            stats.get('passing_interceptions', 0)
                        )

                    result.append({
                        'player_id': stats.get('player_id'),
                        'first_name': first_name,
                        'last_name': last_name,
                        'team_id': stats.get('team_id', 0),
                        'position': position,
                        'years_pro': years_pro,
                        'games_played': games,
                        # Include stats for scoring (avoids N+1 queries)
                        'passing_yards': stats.get('passing_yards', 0),
                        'passing_touchdowns': stats.get('passing_touchdowns', 0),
                        'passer_rating': passer_rating,
                        'rushing_yards': stats.get('rushing_yards', 0),
                        'rushing_touchdowns': stats.get('rushing_touchdowns', 0),
                        'receiving_yards': stats.get('receiving_yards', 0),
                        'receiving_touchdowns': stats.get('receiving_touchdowns', 0),
                        'receptions': stats.get('receptions', 0),
                        'sacks': stats.get('sacks', 0),
                        'interceptions': stats.get('interceptions', 0),
                        'tackles_total': stats.get('tackles_total', 0),
                    })

            logger.debug(f"Found {len(result)} players with stats in eligible positions")
            return result

        except Exception as e:
            logger.warning(f"Failed to get players with stats: {e}")
            return []

    def _get_eligible_positions(self, award_type: AwardType) -> Set[str]:
        """Get eligible positions for an award type."""
        if award_type in (AwardType.MVP,):
            # All offensive and defensive positions
            return OFFENSIVE_POSITIONS | DEFENSIVE_POSITIONS
        elif award_type in (AwardType.OPOY, AwardType.OROY):
            return OFFENSIVE_POSITIONS
        elif award_type in (AwardType.DPOY, AwardType.DROY):
            return DEFENSIVE_POSITIONS
        else:
            return OFFENSIVE_POSITIONS | DEFENSIVE_POSITIONS

    def _calculate_passer_rating(
        self,
        completions: int,
        attempts: int,
        yards: int,
        touchdowns: int,
        interceptions: int
    ) -> float:
        """
        Calculate NFL passer rating (0-158.3 scale).

        Args:
            completions: Passing completions
            attempts: Passing attempts
            yards: Passing yards
            touchdowns: Passing touchdowns
            interceptions: Interceptions thrown

        Returns:
            Passer rating (0-158.3)
        """
        if attempts == 0:
            return 0.0

        # NFL passer rating formula components
        a = max(0, min(2.375, ((completions / attempts) - 0.3) * 5))
        b = max(0, min(2.375, ((yards / attempts) - 3) * 0.25))
        c = max(0, min(2.375, (touchdowns / attempts) * 20))
        d = max(0, min(2.375, 2.375 - ((interceptions / attempts) * 25)))

        return round(((a + b + c + d) / 6) * 100, 1)

    def _calculate_stat_score(self, stats: Dict, award_type: AwardType) -> float:
        """
        Calculate stat score from already-fetched stats dict.

        This avoids the N+1 query problem by using pre-fetched stats
        from _get_players_with_stats() instead of querying per player.

        Args:
            stats: Dictionary with player stats (from _get_players_with_stats)
            award_type: Type of award being scored

        Returns:
            Score from 0-100
        """
        if not stats:
            return DEFAULT_SCORE

        position = stats.get('position', 'UNKNOWN')

        if position == 'QB':
            return self._score_qb_stats(stats)
        elif position == 'RB':
            return self._score_rb_stats(stats)
        elif position in RECEIVER_POSITIONS:
            return self._score_receiver_stats(stats)
        elif position in DEFENSIVE_POSITIONS:
            return self._score_defensive_stats(stats)
        else:
            return DEFAULT_SCORE

    def _get_season_grades(self, eligible_positions: Set[str]) -> List[Dict]:
        """
        Get season grades for eligible positions.

        Returns:
            List of grade dictionaries with player_id, overall_grade, games_played
        """
        try:
            grades = self.analytics_api.get_all_season_grades(
                dynasty_id=self._dynasty_id,
                season=self._season
            )
            return grades if grades else []
        except Exception as e:
            logger.warning(f"Failed to get season grades: {e}")
            return []

    def _get_player_info(self, player_id: int) -> Optional[Dict]:
        """Get player info from database."""
        try:
            row = self.db.query_one(
                """SELECT player_id, first_name, last_name, team_id,
                          json_extract(positions, '$[0]') as position, years_pro
                   FROM players
                   WHERE dynasty_id = ? AND player_id = ?""",
                (self._dynasty_id, player_id)
            )
            return dict(row) if row else None
        except Exception as e:
            logger.warning(f"Failed to get player info for {player_id}: {e}")
            return None

    def _get_years_pro(self, player_id: int) -> Optional[int]:
        """Get years pro for a player."""
        player_info = self._get_player_info(player_id)
        return player_info.get('years_pro') if player_info else None

    def _calculate_simple_score(
        self,
        player_id: int,
        grade_data: Dict,
        award_type: AwardType
    ) -> float:
        """
        Calculate a simple weighted score for tracking.

        Formula: 50% normalized stats + 50% overall grade

        Args:
            player_id: Player ID
            grade_data: Grade data dictionary
            award_type: Type of award

        Returns:
            Score from 0-100
        """
        # Get overall grade (0-100)
        overall_grade = grade_data.get('overall_grade', DEFAULT_SCORE)

        # Get normalized stat score (0-100) based on position
        stat_score = self._get_normalized_stat_score(player_id, award_type)

        # Weighted average: 50% stats + 50% grade
        final_score = (stat_score * STATS_WEIGHT) + (overall_grade * GRADE_WEIGHT)

        return round(final_score, 2)

    def _get_normalized_stat_score(self, player_id: int, award_type: AwardType) -> float:
        """
        Get a normalized stat score (0-100) for a player.

        This is a simplified version for tracking purposes.
        Full scoring is done at end of season.
        """
        try:
            stats = self.stats_api.get_player_season_stats(player_id, self._season)
            if not stats:
                return DEFAULT_SCORE  # Default if no stats

            # Get position-specific stat score (normalize from full name to abbreviation)
            raw_position = stats.get('position', 'UNKNOWN')
            position = get_position_abbreviation(raw_position)

            if position == 'QB':
                return self._score_qb_stats(stats)
            elif position == 'RB':
                return self._score_rb_stats(stats)
            elif position in RECEIVER_POSITIONS:
                return self._score_receiver_stats(stats)
            elif position in DEFENSIVE_POSITIONS:
                return self._score_defensive_stats(stats)
            else:
                return DEFAULT_SCORE  # Default for other positions

        except Exception as e:
            logger.warning(f"Failed to get stats for player {player_id}: {e}")
            return DEFAULT_SCORE

    def _score_qb_stats(self, stats: Dict) -> float:
        """Score QB stats (0-100)."""
        passing_yards = stats.get('passing_yards', 0)
        passing_tds = stats.get('passing_touchdowns', 0)
        passer_rating = stats.get('passer_rating', 0)

        # Normalize against elite benchmarks
        yards_score = min(100, (passing_yards / QB_ELITE_PASSING_YARDS) * 100)
        td_score = min(100, (passing_tds / QB_ELITE_PASSING_TDS) * 100)
        rating_score = min(100, passer_rating)

        return (yards_score * QB_YARDS_WEIGHT) + (td_score * QB_TD_WEIGHT) + (rating_score * QB_RATING_WEIGHT)

    def _score_rb_stats(self, stats: Dict) -> float:
        """Score RB stats (0-100)."""
        rush_yards = stats.get('rushing_yards', 0)
        rush_tds = stats.get('rushing_touchdowns', 0)
        rec_yards = stats.get('receiving_yards', 0)

        total_yards = rush_yards + rec_yards

        # Normalize against elite benchmarks
        yards_score = min(100, (total_yards / RB_ELITE_TOTAL_YARDS) * 100)
        td_score = min(100, (rush_tds / RB_ELITE_RUSHING_TDS) * 100)

        return (yards_score * RB_YARDS_WEIGHT) + (td_score * RB_TD_WEIGHT)

    def _score_receiver_stats(self, stats: Dict) -> float:
        """Score WR/TE stats (0-100)."""
        rec_yards = stats.get('receiving_yards', 0)
        rec_tds = stats.get('receiving_touchdowns', 0)
        receptions = stats.get('receptions', 0)

        # Normalize against elite benchmarks
        yards_score = min(100, (rec_yards / RECEIVER_ELITE_YARDS) * 100)
        td_score = min(100, (rec_tds / RECEIVER_ELITE_TDS) * 100)
        rec_score = min(100, (receptions / RECEIVER_ELITE_RECEPTIONS) * 100)

        return (yards_score * RECEIVER_YARDS_WEIGHT) + (td_score * RECEIVER_TD_WEIGHT) + (rec_score * RECEIVER_REC_WEIGHT)

    def _score_defensive_stats(self, stats: Dict) -> float:
        """Score defensive stats (0-100)."""
        sacks = stats.get('sacks', 0)
        interceptions = stats.get('interceptions', 0)
        tackles = stats.get('tackles_total', 0)

        # Normalize against elite benchmarks
        sacks_score = min(100, (sacks / DEF_ELITE_SACKS) * 100)
        int_score = min(100, (interceptions / DEF_ELITE_INTERCEPTIONS) * 100)
        tackles_score = min(100, (tackles / DEF_ELITE_TACKLES) * 100)

        return (sacks_score * DEF_SACKS_WEIGHT) + (int_score * DEF_INT_WEIGHT) + (tackles_score * DEF_TACKLES_WEIGHT)

    def _calculate_week_score(self, player_id: int, award_type: AwardType) -> float:
        """
        Calculate this week's performance score.

        For now, uses cumulative stats as a proxy.
        Could be enhanced to track weekly box scores.
        """
        # Simplified: Use same calculation as cumulative
        # In a full implementation, this would look at weekly box scores
        return self._get_normalized_stat_score(player_id, award_type)