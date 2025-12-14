"""
Award Eligibility Checker.

Determines player eligibility for awards based on:
- Games played (minimum 12 games)
- Snap counts
- Position group (offense/defense)
- Rookie status (years_pro == 0)

Part of Milestone 10: Awards System, Tollgate 2.
"""

import logging
from typing import Dict, List, Optional, Any

from .models import (
    AwardType,
    PlayerCandidate,
    EligibilityResult,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
)

logger = logging.getLogger(__name__)


# Eligibility constants
MINIMUM_GAMES = 12  # 67% of 18-game season
MINIMUM_SNAPS = 100  # Minimum snaps for season grades
FULL_SEASON_GAMES = 18


class EligibilityChecker:
    """
    Checks player eligibility for awards and populates candidate data.

    Integrates with StatsAPI, AnalyticsAPI, and StandingsAPI to gather
    all data needed for award scoring.
    """

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the eligibility checker.

        Args:
            db_path: Path to the database
            dynasty_id: Dynasty identifier
            season: Season year to check
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season

        # Lazy-loaded APIs
        self._stats_api = None
        self._analytics_api = None
        self._standings_api = None
        self._playoff_api = None
        self._db = None

        # Cached data
        self._standings_cache: Dict[int, Any] = {}
        self._conference_champions: Optional[List[int]] = None

    # ============================================
    # Properties (Lazy Loading)
    # ============================================

    @property
    def db(self):
        """Lazy-load GameCycleDatabase."""
        if self._db is None:
            from src.game_cycle.database.connection import GameCycleDatabase
            self._db = GameCycleDatabase(self._db_path)
        return self._db

    @property
    def stats_api(self):
        """Lazy-load StatsAPI."""
        if self._stats_api is None:
            from src.statistics.stats_api import StatsAPI
            self._stats_api = StatsAPI(self._db_path, self._dynasty_id)
        return self._stats_api

    @property
    def analytics_api(self):
        """Lazy-load AnalyticsAPI."""
        if self._analytics_api is None:
            from src.game_cycle.database.analytics_api import AnalyticsAPI
            self._analytics_api = AnalyticsAPI(self._db_path)
        return self._analytics_api

    @property
    def standings_api(self):
        """Lazy-load StandingsAPI."""
        if self._standings_api is None:
            from src.game_cycle.database.standings_api import StandingsAPI
            self._standings_api = StandingsAPI(self.db)
        return self._standings_api

    @property
    def playoff_api(self):
        """Lazy-load PlayoffBracketAPI."""
        if self._playoff_api is None:
            from src.game_cycle.database.playoff_bracket_api import PlayoffBracketAPI
            self._playoff_api = PlayoffBracketAPI(self.db)
        return self._playoff_api

    # ============================================
    # Public Methods
    # ============================================

    def check_eligibility(
        self,
        player_id: int,
        award_type: AwardType,
        games_graded_override: Optional[int] = None
    ) -> EligibilityResult:
        """
        Check if a player is eligible for a specific award.

        Args:
            player_id: Player ID to check
            award_type: Type of award to check eligibility for
            games_graded_override: Optional override for games played check
                                   (uses games_graded from season grades instead of stats_api)

        Returns:
            EligibilityResult with eligibility status and reasons
        """
        # Get player info
        player_info = self._get_player_info(player_id)
        if not player_info:
            return EligibilityResult(
                player_id=player_id,
                player_name="Unknown",
                is_eligible=False,
                reasons=["Player not found"],
            )

        player_name = f"{player_info['first_name']} {player_info['last_name']}"
        years_pro = player_info.get('years_pro', 0)
        position = self._parse_position(player_info.get('positions', '[]'))
        position_group = self._get_position_group(position)

        reasons = []

        # Check games played (use override from season grades if provided)
        games_eligible, games_played = self._check_games_played(player_id, games_graded_override)
        if not games_eligible:
            reasons.append(f"Played {games_played} games (minimum {MINIMUM_GAMES})")

        # Get snap count from grades
        grade_data = self._get_player_grades(player_id)
        total_snaps = grade_data.get('total_snaps', 0) if grade_data else 0

        # Enforce minimum snap count requirement
        if total_snaps < MINIMUM_SNAPS:
            reasons.append(f"Played {total_snaps} snaps (minimum {MINIMUM_SNAPS})")

        # Check position eligibility based on award type
        position_eligible = self._check_position_eligibility(
            position_group, award_type
        )
        if not position_eligible:
            reasons.append(f"Position {position} not eligible for {award_type.value}")

        # Check rookie status for ROY awards
        is_rookie = years_pro == 0
        if award_type in (AwardType.OROY, AwardType.DROY):
            if not is_rookie:
                reasons.append(f"Not a rookie (years_pro={years_pro})")

        # Check CPOY requirements
        if award_type == AwardType.CPOY:
            cpoy_eligible, cpoy_reason = self._check_cpoy_eligibility(player_id)
            if not cpoy_eligible:
                reasons.append(cpoy_reason)

        is_eligible = len(reasons) == 0

        return EligibilityResult(
            player_id=player_id,
            player_name=player_name,
            is_eligible=is_eligible,
            reasons=reasons,
            games_played=games_played,
            total_snaps=total_snaps,
            is_rookie=is_rookie,
            position_group=position_group,
        )

    def get_eligible_candidates(
        self,
        award_type: AwardType
    ) -> List[PlayerCandidate]:
        """
        Get all eligible candidates for an award with populated data.

        Args:
            award_type: Type of award to get candidates for

        Returns:
            List of PlayerCandidate objects sorted by overall_grade descending
        """
        candidates = []

        # Get all players with season grades
        all_grades = self._get_all_season_grades()
        if not all_grades:
            logger.warning(f"No season grades found for {self._dynasty_id} season {self._season}")
            return candidates

        for grade in all_grades:
            # Handle both dataclass and dict formats
            if hasattr(grade, 'player_id'):
                # It's a SeasonGrade dataclass
                player_id = grade.player_id
                games_graded = getattr(grade, 'games_graded', None)
            else:
                # It's a dict
                player_id = grade.get('player_id')
                games_graded = grade.get('games_graded')

            # Check eligibility (pass games_graded from season grades to avoid stats API call)
            eligibility = self.check_eligibility(player_id, award_type, games_graded)
            if not eligibility.is_eligible:
                continue

            # Populate full candidate data
            candidate = self._populate_candidate_data(player_id, grade)
            if candidate:
                candidates.append(candidate)

        # Sort by overall grade descending
        candidates.sort(key=lambda c: c.overall_grade, reverse=True)

        return candidates

    def get_eligible_candidates_fast(
        self,
        award_type: AwardType,
        per_position_limit: int = 15,
    ) -> List[PlayerCandidate]:
        """
        FAST version of get_eligible_candidates using SQL-level filtering.

        This method:
        1. Uses a single SQL query to get top N candidates per position
        2. Filters by games played at the database level
        3. JOINs player info in the same query
        4. Avoids individual lookups for each player

        Performance: ~0.5s vs ~44s for the standard method.

        Args:
            award_type: Type of award to get candidates for
            per_position_limit: Max candidates per position (default 15)

        Returns:
            List of PlayerCandidate objects sorted by overall_grade descending
        """
        candidates = []

        # Use optimized SQL query that does filtering at database level
        try:
            top_candidates = self.analytics_api.get_top_candidates_by_position(
                dynasty_id=self._dynasty_id,
                season=self._season,
                min_games=MINIMUM_GAMES,
                per_position_limit=per_position_limit,
            )
        except Exception as e:
            logger.warning(f"Fast candidate retrieval failed: {e}")
            # Fall back to standard method
            return self.get_eligible_candidates(award_type)

        if not top_candidates:
            logger.warning(f"No candidates found for {self._dynasty_id} season {self._season}")
            return candidates

        # Convert to PlayerCandidate objects (data already filtered and joined)
        for data in top_candidates:
            player_id = data['player_id']
            raw_position = data.get('position', '')
            years_pro = data.get('years_pro', 0)

            # Convert full position name to abbreviation for group detection
            position = self._normalize_position(raw_position)

            # Quick eligibility checks based on award type
            position_group = self._get_position_group(position)
            is_rookie = years_pro == 0

            # Filter by award type requirements
            if award_type == AwardType.OROY and not is_rookie:
                continue
            if award_type == AwardType.OROY and position_group not in ('offense',):
                continue
            if award_type == AwardType.DROY and not is_rookie:
                continue
            if award_type == AwardType.DROY and position_group not in ('defense',):
                continue
            if award_type == AwardType.OPOY and position_group not in ('offense',):
                continue
            if award_type == AwardType.DPOY and position_group not in ('defense',):
                continue

            # Build PlayerCandidate directly from query results
            # Use normalized position (abbreviation) for consistency
            candidate = PlayerCandidate(
                player_id=player_id,
                player_name=data.get('player_name', ''),
                team_id=data.get('team_id', 0),
                position=position,  # Already normalized to abbreviation
                season=self._season,
                games_played=data.get('games_graded', 0),
                overall_grade=data.get('overall_grade', 0.0),
                position_grade=self._calculate_position_grade(position, data),
                position_rank=data.get('position_rank'),
                overall_rank=data.get('overall_rank'),
                epa_total=data.get('epa_total') or 0.0,
                total_snaps=data.get('total_snaps', 0),
                years_pro=years_pro,
                # Season stats (now populated from analytics_api)
                passing_yards=data.get('passing_yards', 0),
                passing_tds=data.get('passing_tds', 0),
                passing_interceptions=data.get('passing_interceptions', 0),
                passer_rating=data.get('passer_rating', 0.0),
                rushing_yards=data.get('rushing_yards', 0),
                rushing_tds=data.get('rushing_tds', 0),
                receiving_yards=data.get('receiving_yards', 0),
                receiving_tds=data.get('receiving_tds', 0),
                receptions=data.get('receptions', 0),
                sacks=data.get('sacks', 0.0),
                interceptions=data.get('interceptions', 0),
                tackles_total=data.get('tackles_total', 0),
                forced_fumbles=data.get('forced_fumbles', 0),
                # Defensive grades
                pass_rush_grade=data.get('pass_rush_grade', 0.0),
                coverage_grade=data.get('coverage_grade', 0.0),
                tackling_grade=data.get('tackling_grade', 0.0),
                run_defense_grade=data.get('run_defense_grade', 0.0),
                # OL blocking grades
                pass_blocking_grade=data.get('pass_blocking_grade', 0.0),
                run_blocking_grade=data.get('run_blocking_grade', 0.0),
            )
            candidates.append(candidate)

        # Sort by overall grade descending
        candidates.sort(key=lambda c: c.overall_grade, reverse=True)

        logger.info(f"Fast retrieval: {len(candidates)} candidates for {award_type.name}")
        return candidates

    def get_candidate_by_id(
        self,
        player_id: int,
        award_type: AwardType
    ) -> Optional[PlayerCandidate]:
        """
        Get a single candidate by player ID with full data populated.

        Used by AwardsService to convert tracked nominees to full PlayerCandidate
        objects for the voting process.

        Args:
            player_id: Player ID to retrieve
            award_type: Type of award (for eligibility checking)

        Returns:
            PlayerCandidate if player is eligible and data is available, None otherwise
        """
        try:
            # Get player's season grade
            grade = self._get_player_grades(player_id)
            if not grade:
                logger.debug(f"No season grades for player {player_id}")
                return None

            # Get games played for eligibility check
            if isinstance(grade, dict):
                games_graded = grade.get('games_graded', 0)
            else:
                games_graded = getattr(grade, 'games_graded', 0)

            # Check eligibility
            eligibility = self.check_eligibility(player_id, award_type, games_graded)
            if not eligibility.is_eligible:
                logger.debug(f"Player {player_id} not eligible: {eligibility.reasons}")
                return None

            # Populate full candidate data
            candidate = self._populate_candidate_data(player_id, grade)
            return candidate

        except Exception as e:
            logger.warning(f"Failed to get candidate by ID {player_id}: {e}")
            return None

    # ============================================
    # Private Helper Methods
    # ============================================

    def _calculate_position_grade(self, position: str, data: dict) -> float:
        """Calculate position-appropriate grade based on position type."""
        pos = position.lower()

        # OL positions - weighted average of blocking grades
        if pos in ('left_tackle', 'right_tackle', 'lt', 'rt'):
            # Tackles: pass-heavy (60/40)
            pass_block = data.get('pass_blocking_grade') or 0.0
            run_block = data.get('run_blocking_grade') or 0.0
            if pass_block or run_block:
                total_weight = (0.60 if pass_block else 0) + (0.40 if run_block else 0)
                return (pass_block * 0.60 + run_block * 0.40) / total_weight if total_weight else 0.0
        elif pos in ('left_guard', 'right_guard', 'lg', 'rg'):
            # Guards: run-heavy (40/60)
            pass_block = data.get('pass_blocking_grade') or 0.0
            run_block = data.get('run_blocking_grade') or 0.0
            if pass_block or run_block:
                total_weight = (0.40 if pass_block else 0) + (0.60 if run_block else 0)
                return (pass_block * 0.40 + run_block * 0.60) / total_weight if total_weight else 0.0
        elif pos in ('center', 'c'):
            # Center: balanced (50/50)
            pass_block = data.get('pass_blocking_grade') or 0.0
            run_block = data.get('run_blocking_grade') or 0.0
            if pass_block or run_block:
                total_weight = (0.50 if pass_block else 0) + (0.50 if run_block else 0)
                return (pass_block * 0.50 + run_block * 0.50) / total_weight if total_weight else 0.0

        # Fallback: existing OR-chain logic for other positions
        return (data.get('passing_grade') or data.get('rushing_grade')
                or data.get('receiving_grade') or data.get('tackling_grade')
                or data.get('pass_blocking_grade') or data.get('run_blocking_grade') or 0.0)

    def _get_player_info(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player info from players table."""
        row = self.db.query_one(
            """SELECT player_id, first_name, last_name, positions, team_id, years_pro, status, birthdate
               FROM players
               WHERE dynasty_id = ? AND player_id = ?""",
            (self._dynasty_id, player_id)
        )
        if not row:
            return None

        result = dict(row)

        # Calculate years_pro from birthdate if not set (years_pro == 0 and birthdate exists)
        if result.get('years_pro', 0) == 0 and result.get('birthdate'):
            result['years_pro'] = self._calculate_years_pro(result['birthdate'])

        return result

    def _calculate_years_pro(self, birthdate: str) -> int:
        """Calculate years pro from birthdate assuming entry age of 22."""
        try:
            from datetime import datetime
            birth_year = int(birthdate[:4])
            # Assume players enter NFL at age 22 (after college)
            entry_year = birth_year + 22
            years_pro = self._season - entry_year
            return max(0, years_pro)  # Minimum 0 for rookies
        except (ValueError, TypeError):
            return 0

    def _check_games_played(
        self,
        player_id: int,
        games_graded_override: Optional[int] = None
    ) -> tuple:
        """
        Check if player has played minimum games.

        Args:
            player_id: Player ID to check
            games_graded_override: Optional games count from season grades (preferred)

        Returns:
            Tuple of (is_eligible, games_played)
        """
        # Use override if provided (from aggregated season grades)
        if games_graded_override is not None:
            return games_graded_override >= MINIMUM_GAMES, games_graded_override

        # Fall back to stats API for individual player lookups
        try:
            stats = self.stats_api.get_player_season_stats(str(player_id), self._season)
            games_played = stats.get('games_played', 0) if stats else 0
        except Exception as e:
            logger.warning(f"Error getting stats for player {player_id}: {e}")
            games_played = 0

        return games_played >= MINIMUM_GAMES, games_played

    def _get_player_grades(self, player_id: int) -> Optional[Dict[str, Any]]:
        """Get player season grades from AnalyticsAPI."""
        try:
            grade = self.analytics_api.get_season_grade(
                self._dynasty_id, player_id, self._season
            )
            if grade:
                # Convert dataclass to dict if needed
                if hasattr(grade, 'overall_grade'):
                    return {
                        'overall_grade': grade.overall_grade,
                        'position_rank': grade.position_rank,
                        'overall_rank': grade.overall_rank,
                        'epa_total': grade.epa_total,
                        'total_snaps': grade.total_snaps,
                        'games_graded': grade.games_graded,
                        'passing_grade': getattr(grade, 'passing_grade', None),
                        'rushing_grade': getattr(grade, 'rushing_grade', None),
                        'receiving_grade': getattr(grade, 'receiving_grade', None),
                        'pass_rush_grade': getattr(grade, 'pass_rush_grade', None),
                        'coverage_grade': getattr(grade, 'coverage_grade', None),
                    }
                return grade
        except Exception as e:
            logger.warning(f"Error getting grades for player {player_id}: {e}")
        return None

    def _get_all_season_grades(self) -> List[Any]:
        """Get all player season grades for the season."""
        try:
            return self.analytics_api.get_all_season_grades(
                self._dynasty_id, self._season
            )
        except Exception as e:
            logger.warning(f"Error getting all season grades: {e}")
            return []

    def _get_team_standing(self, team_id: int) -> Optional[Dict[str, Any]]:
        """Get team standing with caching."""
        if team_id in self._standings_cache:
            return self._standings_cache[team_id]

        try:
            standing = self.standings_api.get_team_standing(
                self._dynasty_id, self._season, team_id
            )
            if standing:
                # Convert dataclass to dict if needed
                if hasattr(standing, 'wins'):
                    result = {
                        'wins': standing.wins,
                        'losses': standing.losses,
                        'ties': getattr(standing, 'ties', 0),
                        'playoff_seed': standing.playoff_seed,
                        'division_wins': getattr(standing, 'division_wins', 0),
                        'conference_wins': getattr(standing, 'conference_wins', 0),
                    }
                else:
                    result = standing
                self._standings_cache[team_id] = result
                return result
        except Exception as e:
            logger.warning(f"Error getting standing for team {team_id}: {e}")

        return None

    def _get_conference_champions(self) -> List[int]:
        """Get list of conference champion team IDs."""
        if self._conference_champions is not None:
            return self._conference_champions

        champions = []
        try:
            for conf in ['AFC', 'NFC']:
                winners = self.playoff_api.get_round_winners(
                    self._dynasty_id, self._season, 'conference', conf
                )
                champions.extend(winners)
        except Exception as e:
            logger.warning(f"Error getting conference champions: {e}")

        self._conference_champions = champions
        return champions

    def _check_position_eligibility(
        self,
        position_group: str,
        award_type: AwardType
    ) -> bool:
        """Check if position group is eligible for award type."""
        if award_type == AwardType.MVP:
            # MVP is open to all positions
            return True
        elif award_type in (AwardType.OPOY, AwardType.OROY):
            return position_group == 'offense'
        elif award_type in (AwardType.DPOY, AwardType.DROY):
            return position_group == 'defense'
        elif award_type == AwardType.CPOY:
            # CPOY is open to all positions (except maybe special teams)
            return position_group in ('offense', 'defense')
        return True

    def _check_cpoy_eligibility(self, player_id: int) -> tuple:
        """
        Check CPOY-specific eligibility requirements.

        Requirements:
        - Missed 4+ games previous season OR
        - Improved grade by 5+ points from previous season

        Returns:
            Tuple of (is_eligible, reason_if_not)
        """
        player_info = self._get_player_info(player_id)
        if not player_info:
            return False, "Player not found"

        years_pro = player_info.get('years_pro', 0)
        if years_pro == 0:
            return False, "Rookies not eligible for CPOY"

        # Get previous season grade
        try:
            prev_grade = self.analytics_api.get_season_grade(
                self._dynasty_id, player_id, self._season - 1
            )
            current_grade = self.analytics_api.get_season_grade(
                self._dynasty_id, player_id, self._season
            )

            if not prev_grade or not current_grade:
                # If no previous season data, allow for injury comeback narrative
                return True, ""

            prev_overall = getattr(prev_grade, 'overall_grade', 50.0)
            curr_overall = getattr(current_grade, 'overall_grade', 50.0)
            games_prev = getattr(prev_grade, 'games_graded', 18)

            # Check comeback criteria
            games_missed = FULL_SEASON_GAMES - games_prev
            grade_improvement = curr_overall - prev_overall

            if games_missed >= 4 or grade_improvement >= 5:
                return True, ""
            else:
                return False, f"No comeback narrative (games missed: {games_missed}, grade delta: {grade_improvement:.1f})"

        except Exception as e:
            logger.warning(f"Error checking CPOY eligibility for player {player_id}: {e}")
            # Allow through if we can't verify
            return True, ""

    def _populate_candidate_data(
        self,
        player_id: int,
        grade_data: Any
    ) -> Optional[PlayerCandidate]:
        """
        Populate full candidate data from all sources.

        Args:
            player_id: Player ID
            grade_data: Season grade data (dataclass or dict)

        Returns:
            Populated PlayerCandidate or None if data unavailable
        """
        # Get player info
        player_info = self._get_player_info(player_id)
        if not player_info:
            return None

        player_name = f"{player_info['first_name']} {player_info['last_name']}"
        team_id = player_info['team_id']
        position = self._parse_position(player_info.get('positions', '[]'))
        years_pro = player_info.get('years_pro', 0)

        # Get stats
        stats = {}
        try:
            stats = self.stats_api.get_player_season_stats(str(player_id), self._season) or {}
        except Exception as e:
            logger.warning(f"Error getting stats for player {player_id}: {e}")

        # Extract grade data
        if hasattr(grade_data, 'overall_grade'):
            overall_grade = grade_data.overall_grade
            position_grade = getattr(grade_data, 'position_grade', overall_grade)
            position_rank = grade_data.position_rank
            overall_rank = grade_data.overall_rank
            epa_total = getattr(grade_data, 'epa_total', 0.0) or 0.0
            total_snaps = getattr(grade_data, 'total_snaps', 0) or 0
        else:
            overall_grade = grade_data.get('overall_grade', 50.0)
            position_grade = grade_data.get('position_grade', overall_grade)
            position_rank = grade_data.get('position_rank')
            overall_rank = grade_data.get('overall_rank')
            epa_total = grade_data.get('epa_total', 0.0) or 0.0
            total_snaps = grade_data.get('total_snaps', 0) or 0

        # Get team success
        standing = self._get_team_standing(team_id) or {}
        team_wins = standing.get('wins', 0)
        team_losses = standing.get('losses', 0)
        total_games = team_wins + team_losses
        win_percentage = team_wins / total_games if total_games > 0 else 0.0
        playoff_seed = standing.get('playoff_seed')

        # Check division winner (seed 1-4 with best record in division)
        # Simplified: seed 1-4 and division_wins > 0
        is_division_winner = (
            playoff_seed is not None and
            playoff_seed <= 4 and
            standing.get('division_wins', 0) >= 4  # Won most division games
        )

        # Check conference champion
        conf_champs = self._get_conference_champions()
        is_conference_champion = team_id in conf_champs

        # Get previous season data for CPOY
        previous_grade = None
        games_missed_prev = 0
        if years_pro > 0:
            try:
                prev = self.analytics_api.get_season_grade(
                    self._dynasty_id, player_id, self._season - 1
                )
                if prev:
                    previous_grade = getattr(prev, 'overall_grade', None)
                    games_prev = getattr(prev, 'games_graded', FULL_SEASON_GAMES)
                    games_missed_prev = FULL_SEASON_GAMES - games_prev
            except Exception:
                pass

        return PlayerCandidate(
            player_id=player_id,
            player_name=player_name,
            team_id=team_id,
            position=position,
            season=self._season,
            games_played=stats.get('games_played', 0),
            passing_yards=stats.get('passing_yards', 0),
            passing_tds=stats.get('passing_touchdowns', 0),
            passing_interceptions=stats.get('passing_interceptions', 0),
            passer_rating=stats.get('passer_rating', 0.0),
            rushing_yards=stats.get('rushing_yards', 0),
            rushing_tds=stats.get('rushing_touchdowns', 0),
            receiving_yards=stats.get('receiving_yards', 0),
            receiving_tds=stats.get('receiving_touchdowns', 0),
            receptions=stats.get('receptions', 0),
            sacks=stats.get('sacks', 0.0),
            interceptions=stats.get('interceptions', 0),
            tackles_total=stats.get('tackles_total', 0),
            forced_fumbles=stats.get('forced_fumbles', 0),
            overall_grade=overall_grade,
            position_grade=position_grade,
            position_rank=position_rank,
            overall_rank=overall_rank,
            epa_total=epa_total,
            total_snaps=total_snaps,
            team_wins=team_wins,
            team_losses=team_losses,
            win_percentage=win_percentage,
            playoff_seed=playoff_seed,
            is_division_winner=is_division_winner,
            is_conference_champion=is_conference_champion,
            years_pro=years_pro,
            previous_season_grade=previous_grade,
            games_missed_previous=games_missed_prev,
        )

    def _parse_position(self, positions_json: str) -> str:
        """Parse position from JSON array, returning primary position as abbreviation."""
        import json
        try:
            positions = json.loads(positions_json)
            if isinstance(positions, list) and positions:
                pos_name = positions[0].lower()
            elif isinstance(positions, str):
                pos_name = positions.lower()
            else:
                return 'UNKNOWN'

            # Convert full position name to abbreviation using awards_service mapping
            from game_cycle.services.awards_service import POSITION_TO_ABBREVIATION
            return POSITION_TO_ABBREVIATION.get(pos_name, pos_name.upper())
        except (json.JSONDecodeError, TypeError):
            pass
        return 'UNKNOWN'

    def _normalize_position(self, position: str) -> str:
        """Convert position name to standard abbreviation."""
        if not position:
            return 'UNKNOWN'
        pos_lower = position.lower()
        from game_cycle.services.awards_service import POSITION_TO_ABBREVIATION
        return POSITION_TO_ABBREVIATION.get(pos_lower, position.upper())

    def _get_position_group(self, position: str) -> str:
        """Get position group for a position."""
        pos_upper = position.upper()
        if pos_upper in OFFENSIVE_POSITIONS:
            return 'offense'
        elif pos_upper in DEFENSIVE_POSITIONS:
            return 'defense'
        else:
            # Default to offense for unknown positions
            return 'offense'
