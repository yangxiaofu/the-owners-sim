"""
PopularityCalculator Service - Calculates player popularity scores.

Part of Milestone 16: Player Popularity.

Calculates popularity using the formula:
    Popularity = (Performance_Score × Visibility_Multiplier × Market_Multiplier) - Weekly_Decay
    Capped: 0-100 range

Components:
- Performance Score: PFF grade adjusted by position value (0-100)
- Visibility Multiplier: Media exposure, awards, social buzz, team success (0.5x-3.0x)
- Market Multiplier: Stadium capacity-based market size (0.8x-2.0x)
- Weekly Decay: Activity-based popularity decay (-3 to 0 points)
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..database.connection import GameCycleDatabase
from ..database.analytics_api import AnalyticsAPI
from ..database.media_coverage_api import MediaCoverageAPI
from ..database.awards_api import AwardsAPI
from ..database.social_posts_api import SocialPostsAPI
from ..database.standings_api import StandingsAPI
from ..stage_definitions import StageType
from constants.position_abbreviations import get_position_abbreviation


logger = logging.getLogger(__name__)


# ============================================
# Constants
# ============================================

# Position value multipliers for performance score
POSITION_VALUE_MULTIPLIERS = {
    'QB': 1.2,
    'EDGE': 1.2,
    'CB': 1.2,
    'WR': 1.1,
    'RB': 1.1,
    'LB': 1.1,
    'OLB': 1.1,
    'ILB': 1.1,
    'MLB': 1.1,
    'S': 1.1,
    'FS': 1.1,
    'SS': 1.1,
    'TE': 1.0,
    'DT': 1.0,
    'DE': 1.0,
    'OL': 1.0,
    'OT': 1.0,
    'OG': 1.0,
    'LT': 1.0,
    'LG': 1.0,
    'C': 1.0,
    'RG': 1.0,
    'RT': 1.0,
    'FB': 0.9,
    'LS': 0.9,
    'K': 0.7,
    'P': 0.7,
}

# Visibility multiplier bounds
VISIBILITY_FLOOR = 0.5
VISIBILITY_CEILING = 3.0

# Media exposure bonuses
NATIONAL_HEADLINE_BOOST = 0.3  # Priority > 80
REGIONAL_HEADLINE_BOOST = 0.2  # Priority 60-80
LOCAL_HEADLINE_BOOST = 0.1     # Priority < 60

# Award race bonuses
MVP_TOP_3_BOOST = 0.5
MVP_TOP_10_BOOST = 0.3
AWARD_TOP_5_BOOST = 0.4

# Award recognition bonuses
ALL_PRO_BOOST = 0.5
PRO_BOWL_BOOST = 0.3

# Social engagement bonuses
SOCIAL_PER_10_POSTS = 0.02
VIRAL_THRESHOLD_POSTS = 50
VIRAL_THRESHOLD_ENGAGEMENT = 1000
VIRAL_BOOST = 0.05

# Team success bonuses/penalties
PLAYOFF_POSITION_BOOST = 0.5
WINNING_RECORD_BOOST = 0.3
LOSING_RECORD_PENALTY = -0.3

# Market multiplier tiers (based on stadium capacity)
LARGE_MARKET_MIN = 75000
LARGE_MARKET_RANGE = (1.8, 2.0)
MEDIUM_LARGE_MIN = 70000
MEDIUM_LARGE_RANGE = (1.4, 1.6)
MEDIUM_MIN = 65000
MEDIUM_RANGE = (1.1, 1.3)
SMALL_RANGE = (0.8, 1.0)

# Weekly decay values
DECAY_INJURED = -3
DECAY_INACTIVE = -2
DECAY_MINOR = -1
DECAY_ACTIVE = 0

# Rookie initialization values
ROOKIE_DRAFT_VALUES = {
    1: 40,   # 1st overall
    2: 38,
    3: 37,
    4: 36,
    5: 35,   # Top 5
    10: 30,  # Top 10
}

# Trade adjustment
TRADE_DISRUPTION_PENALTY = 0.20  # 20% drop
TRADE_ADJUSTMENT_WEEKS = 4

# Playoff multipliers
PLAYOFF_STATS_MULTIPLIER = 1.5
SUPER_BOWL_MVP_BONUS = 15

# Playoff week numbers (from stage_definitions.py)
PLAYOFF_WEEKS = {19, 20, 21, 22}  # Wild Card, Divisional, Conference, Super Bowl


# ============================================
# Enums
# ============================================

class PopularityTier(Enum):
    """Popularity tier classification."""
    TRANSCENDENT = "TRANSCENDENT"  # 90-100
    STAR = "STAR"                  # 75-89
    KNOWN = "KNOWN"                # 50-74
    ROLE_PLAYER = "ROLE_PLAYER"   # 25-49
    UNKNOWN = "UNKNOWN"            # 0-24


class PopularityTrend(Enum):
    """Popularity trend over time."""
    RISING = "RISING"      # +5 or more over 4 weeks
    FALLING = "FALLING"    # -5 or more over 4 weeks
    STABLE = "STABLE"      # Within ±5


# ============================================
# PopularityCalculator Service
# ============================================

class PopularityCalculator:
    """
    Service for calculating player popularity scores.

    Handles:
    - Performance score calculation (PFF grade + position value)
    - Visibility multiplier (media, awards, social, team success)
    - Market multiplier (stadium capacity)
    - Weekly decay based on activity
    - Tier classification and trend tracking
    - Special cases: rookies, trades, playoffs, injuries
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize service with database connection.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier for isolation
        """
        self._db = db
        self._dynasty_id = dynasty_id
        self._analytics_api = AnalyticsAPI(db.db_path)
        self._media_api = MediaCoverageAPI(db)
        self._awards_api = AwardsAPI(db)
        self._social_api = SocialPostsAPI(db)
        self._standings_api = StandingsAPI(db)
        self._logger = logging.getLogger(__name__)
        self._team_data = self._load_team_data()

    def _load_team_data(self) -> Dict[int, Dict]:
        """Load team data from teams.json for market multipliers."""
        try:
            current_dir = Path(__file__).parent
            teams_path = current_dir.parent.parent / "data" / "teams.json"
            with open(teams_path, 'r') as f:
                data = json.load(f)
                # Convert string keys to integers
                return {int(k): v for k, v in data.get('teams', {}).items()}
        except Exception as e:
            self._logger.error(f"Failed to load team data: {e}")
            return {}

    # ========================================================================
    # Core Calculation Methods
    # ========================================================================

    def calculate_performance_score(
        self,
        player_id: int,
        season: int,
        week: int,
        position: str
    ) -> float:
        """
        Calculate base performance score from PFF grade + position value adjustment.

        Args:
            player_id: Player identifier
            season: Season year
            week: Week number
            position: Player position (for value multiplier)

        Returns:
            0-100 performance score

        Formula:
            Performance = PFF_Overall_Grade × Position_Value_Multiplier
            Capped at 100
        """
        try:
            # Get player's season grade from analytics API
            season_grade = self._analytics_api.get_season_grade(
                self._dynasty_id, player_id, season
            )

            if not season_grade:
                # No grade yet (likely hasn't played or insufficient snaps)
                return 50.0  # Use baseline score instead of 0

            # Get overall grade (0-100 scale)
            overall_grade = season_grade.overall_grade or 0.0

            # Apply position value multiplier
            position_abbr = get_position_abbreviation(position)
            multiplier = POSITION_VALUE_MULTIPLIERS.get(position_abbr, 1.0)

            performance = overall_grade * multiplier

            # Cap at 100
            return min(performance, 100.0)

        except Exception as e:
            self._logger.error(
                f"Error calculating performance score for player {player_id}: {e}"
            )
            return 0.0

    def calculate_visibility_multiplier(
        self,
        player_id: int,
        season: int,
        week: int
    ) -> float:
        """
        Calculate visibility multiplier based on media exposure, awards, social buzz.

        Args:
            player_id: Player identifier
            season: Season year
            week: Week number

        Returns:
            0.5x - 3.0x visibility multiplier

        Components:
        - Base: 1.0x
        - Media exposure: +0.1x to +0.3x per headline (by priority)
        - Award race: +0.3x to +0.5x for top candidates
        - Season awards: +0.5x per All-Pro, +0.3x per Pro Bowl
        - Social engagement: +0.02x per 10 posts, +0.05x if viral
        - Team success: +0.5x playoff position, +0.3x winning record, -0.3x losing
        """
        try:
            multiplier = 1.0

            # Media exposure - get all headlines and filter by player
            all_headlines = self._media_api.get_headlines(
                self._dynasty_id, season, week
            )
            # Filter to headlines that mention this player
            player_headlines = [h for h in all_headlines if player_id in h.player_ids]

            for headline in player_headlines:
                if headline.priority > 80:
                    multiplier += NATIONAL_HEADLINE_BOOST
                elif headline.priority >= 60:
                    multiplier += REGIONAL_HEADLINE_BOOST
                else:
                    multiplier += LOCAL_HEADLINE_BOOST

            # Award race (check nominees for major awards)
            mvp_nominees = self._awards_api.get_nominees(
                self._dynasty_id, season, 'MVP'
            )
            for nominee in mvp_nominees:
                if nominee.player_id == player_id:
                    if nominee.nomination_rank <= 3:
                        multiplier += MVP_TOP_3_BOOST
                    elif nominee.nomination_rank <= 10:
                        multiplier += MVP_TOP_10_BOOST
                    break

            # OPOY/DPOY race
            for award_id in ['OPOY', 'DPOY']:
                nominees = self._awards_api.get_nominees(
                    self._dynasty_id, season, award_id
                )
                for nominee in nominees:
                    if nominee.player_id == player_id and nominee.nomination_rank <= 5:
                        multiplier += AWARD_TOP_5_BOOST
                        break

            # Season awards (All-Pro, Pro Bowl)
            all_pro_history = self._awards_api.get_player_all_pro_history(
                self._dynasty_id, player_id
            )
            # Filter to current season only
            all_pro_selections = [s for s in all_pro_history if s.season == season]
            multiplier += len(all_pro_selections) * ALL_PRO_BOOST

            pro_bowl_history = self._awards_api.get_player_pro_bowl_history(
                self._dynasty_id, player_id
            )
            # Filter to current season only
            pro_bowl_selections = [s for s in pro_bowl_history if s.season == season]
            multiplier += len(pro_bowl_selections) * PRO_BOWL_BOOST

            # Social engagement
            # TODO: Implement get_posts_by_player() in SocialPostsAPI
            # For now, skip social component
            # social_posts = self._social_api.get_posts_by_player(
            #     self._dynasty_id, season, week, player_id
            # )
            # post_count = len(social_posts)
            # multiplier += (post_count // 10) * SOCIAL_PER_10_POSTS

            # Check for viral moment
            # total_engagement = sum(
            #     post.likes + post.retweets for post in social_posts
            # )
            # if post_count >= VIRAL_THRESHOLD_POSTS and total_engagement >= VIRAL_THRESHOLD_ENGAGEMENT:
            #     multiplier += VIRAL_BOOST

            # Team success (requires player's team_id)
            # Note: This would require getting player's team from UnifiedDatabaseAPI
            # For now, we'll skip team success component
            # TODO: Add team success component once player team lookup is available

            # Apply floor and ceiling
            multiplier = max(VISIBILITY_FLOOR, min(multiplier, VISIBILITY_CEILING))

            return multiplier

        except Exception as e:
            self._logger.error(
                f"Error calculating visibility multiplier for player {player_id}: {e}"
            )
            return 1.0  # Default to base multiplier on error

    def calculate_market_multiplier(self, team_id: int) -> float:
        """
        Calculate market multiplier based on stadium capacity.

        Args:
            team_id: Team identifier

        Returns:
            0.8x - 2.0x market multiplier

        Tiers (based on stadium capacity):
        - Large Market (75K+): 1.8x - 2.0x
        - Medium-Large (70K-75K): 1.4x - 1.6x
        - Medium (65K-70K): 1.1x - 1.3x
        - Small (<65K): 0.8x - 1.0x
        """
        try:
            team = self._team_data.get(team_id)
            if not team:
                self._logger.warning(f"Team {team_id} not found in teams.json")
                return 1.0

            stadium = team.get('stadium', {})
            capacity = stadium.get('capacity', 0)

            # Determine market tier
            if capacity >= LARGE_MARKET_MIN:
                # Large market: scale within range based on capacity
                min_val, max_val = LARGE_MARKET_RANGE
                # Use 75K as base, 82K as max (Washington has 82K)
                scale = min((capacity - 75000) / 7000, 1.0)
                return min_val + (max_val - min_val) * scale
            elif capacity >= MEDIUM_LARGE_MIN:
                min_val, max_val = MEDIUM_LARGE_RANGE
                scale = (capacity - 70000) / 5000
                return min_val + (max_val - min_val) * scale
            elif capacity >= MEDIUM_MIN:
                min_val, max_val = MEDIUM_RANGE
                scale = (capacity - 65000) / 5000
                return min_val + (max_val - min_val) * scale
            else:
                # Small market
                min_val, max_val = SMALL_RANGE
                # Use 60K as min, 65K as max
                scale = max((capacity - 60000) / 5000, 0.0)
                return min_val + (max_val - min_val) * scale

        except Exception as e:
            self._logger.error(
                f"Error calculating market multiplier for team {team_id}: {e}"
            )
            return 1.0

    def apply_weekly_decay(
        self,
        current_popularity: float,
        events_this_week: List[str]
    ) -> float:
        """
        Apply decay if player had no significant activity.

        Args:
            current_popularity: Current popularity score
            events_this_week: List of event types this week

        Returns:
            Decay amount to subtract from popularity

        Decay Rules:
        - -3 points if injured/inactive entire week
        - -2 points if no headlines, no social buzz, no award race movement
        - -1 point if only minor activity
        - 0 if any significant event
        """
        # Check for significant events
        significant_events = {
            'GAME_RESULT', 'MILESTONE', 'AWARD', 'HEADLINE',
            'TRADE', 'SIGNING', 'PLAYOFF_GAME'
        }

        if any(event in significant_events for event in events_this_week):
            return DECAY_ACTIVE

        # Check for injury/inactive
        if 'INJURY' in events_this_week or 'INACTIVE' in events_this_week:
            return DECAY_INJURED

        # Check for minor activity
        minor_events = {'PRACTICE', 'SOCIAL_POST', 'QUOTE'}
        if any(event in minor_events for event in events_this_week):
            return DECAY_MINOR

        # No activity at all
        return DECAY_INACTIVE

    def classify_tier(self, popularity_score: float) -> PopularityTier:
        """
        Classify player into popularity tier.

        Args:
            popularity_score: 0-100 popularity score

        Returns:
            PopularityTier enum

        Tiers:
        - TRANSCENDENT: 90-100
        - STAR: 75-89
        - KNOWN: 50-74
        - ROLE_PLAYER: 25-49
        - UNKNOWN: 0-24
        """
        if popularity_score >= 90:
            return PopularityTier.TRANSCENDENT
        elif popularity_score >= 75:
            return PopularityTier.STAR
        elif popularity_score >= 50:
            return PopularityTier.KNOWN
        elif popularity_score >= 25:
            return PopularityTier.ROLE_PLAYER
        else:
            return PopularityTier.UNKNOWN

    def calculate_trend(
        self,
        player_id: int,
        season: int,
        week: int
    ) -> PopularityTrend:
        """
        Determine trend based on 4-week rolling average.

        Args:
            player_id: Player identifier
            season: Season year
            week: Current week number

        Returns:
            PopularityTrend enum

        Trends:
        - RISING: +5 or more over 4 weeks
        - FALLING: -5 or more over 4 weeks
        - STABLE: within ±5
        """
        # TODO: Implement once PopularityAPI exists to fetch historical scores
        # For now, return STABLE as default
        return PopularityTrend.STABLE

    # ========================================================================
    # Special Case Methods
    # ========================================================================

    def initialize_rookie_popularity(
        self,
        player_id: int,
        draft_round: int,
        draft_pick: int
    ) -> float:
        """
        Set initial popularity for rookie players based on draft position.

        Args:
            player_id: Player identifier
            draft_round: Draft round (1-7)
            draft_pick: Overall pick number

        Returns:
            Initial popularity score (0-100)

        Baseline Scores:
        - 1st overall pick: 40
        - Top 5 picks: 35
        - Top 10 picks: 30
        - 1st round (11-32): 25
        - 2nd round: 20
        - 3rd round: 15
        - 4th-7th rounds: 10
        - Undrafted: 5
        """
        if draft_round == 0:  # Undrafted
            return 5.0

        # Use lookup table for top picks
        if draft_pick in ROOKIE_DRAFT_VALUES:
            return float(ROOKIE_DRAFT_VALUES[draft_pick])

        # Top 10
        if draft_pick <= 10:
            return 30.0

        # By round
        if draft_round == 1:
            return 25.0
        elif draft_round == 2:
            return 20.0
        elif draft_round == 3:
            return 15.0
        else:  # Rounds 4-7
            return 10.0

    def adjust_for_trade(
        self,
        player_id: int,
        old_team_id: int,
        new_team_id: int,
        week: int,
        current_popularity: float
    ) -> float:
        """
        Apply trade disruption and calculate adjusted popularity.

        Args:
            player_id: Player identifier
            old_team_id: Previous team ID
            new_team_id: New team ID
            week: Week of trade
            current_popularity: Current popularity score

        Returns:
            Adjusted popularity after trade disruption

        Trade Impact:
        - Initial: Drop popularity by 20% (trade disruption)
        - Weeks 1-4: Linear interpolation from old to new market multiplier
        - Week 5+: Full new market multiplier applied

        Note: This method returns the immediate post-trade popularity.
        The weekly calculation will handle the gradual market adjustment.
        """
        # Apply 20% disruption
        disrupted_popularity = current_popularity * (1.0 - TRADE_DISRUPTION_PENALTY)

        # Log the trade event
        self._logger.info(
            f"Player {player_id} traded from team {old_team_id} to {new_team_id} "
            f"in week {week}. Popularity: {current_popularity:.1f} → {disrupted_popularity:.1f}"
        )

        return max(0.0, disrupted_popularity)

    def apply_playoff_multiplier(
        self,
        week: int,
        stats_impact: float,
        headlines_impact: float
    ) -> Tuple[float, float]:
        """
        Apply 1.5x multiplier to playoff performance for visibility calculation.

        Args:
            week: Week number
            stats_impact: Base stats impact on visibility
            headlines_impact: Base headlines impact on visibility

        Returns:
            Tuple of (adjusted_stats_impact, adjusted_headlines_impact)

        Playoff Boost:
        - Playoff stats count 1.5x
        - Playoff headlines get 1.5x weight
        - Super Bowl MVP: handled separately (instant +15 bonus)
        """
        if week in PLAYOFF_WEEKS:
            return (
                stats_impact * PLAYOFF_STATS_MULTIPLIER,
                headlines_impact * PLAYOFF_STATS_MULTIPLIER
            )
        return (stats_impact, headlines_impact)

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_recent_snap_count(
        self,
        player_id: int,
        season: int,
        current_week: int,
        weeks: int = 4
    ) -> int:
        """
        Get total snaps for a player over the last N weeks.

        This uses a rolling window to allow backups who become starters
        to gain popularity quickly, while filtering out low-usage players.

        Args:
            player_id: Player identifier
            season: Season year
            current_week: Current week number
            weeks: Number of recent weeks to check (default 4)

        Returns:
            Total snap count over the rolling window
        """
        try:
            from ..database.analytics_api import AnalyticsAPI

            analytics_api = AnalyticsAPI(self._db.db_path)
            conn = analytics_api._get_connection()
            cursor = conn.cursor()

            # Calculate start week (minimum week 1)
            start_week = max(1, current_week - weeks + 1)

            # Get total snaps from game grades in the rolling window
            cursor.execute("""
                SELECT SUM(offensive_snaps + defensive_snaps + special_teams_snaps) as total_snaps
                FROM player_game_grades
                WHERE dynasty_id = ? AND player_id = ? AND season = ?
                      AND week BETWEEN ? AND ?
            """, (self._dynasty_id, player_id, season, start_week, current_week))

            result = cursor.fetchone()
            conn.close()

            return int(result[0]) if result and result[0] else 0

        except Exception as e:
            self._logger.error(
                f"Error getting recent snap count for player {player_id}: {e}"
            )
            return 0

    # ========================================================================
    # Main Orchestrator Method
    # ========================================================================

    def calculate_weekly_popularity(
        self,
        season: int,
        week: int
    ) -> int:
        """
        Main orchestrator method - calculate popularity for all active players.

        Args:
            season: Season year
            week: Week number

        Returns:
            Number of players updated

        Process:
        1. Get all active players
        2. For each player:
           - Calculate performance score
           - Calculate visibility multiplier
           - Get market multiplier
           - Apply formula: (Performance × Visibility × Market) - Decay
           - Cap to 0-100 range
           - Classify tier
           - Calculate trend
           - Save via PopularityAPI
        """
        try:
            import json
            from ..database.popularity_api import PopularityAPI

            self._logger.info(
                f"Calculating popularity for season {season}, week {week} (dynasty={self._dynasty_id})"
            )

            # Get all active players from game_cycle database
            conn = self._db.get_connection()
            cursor = conn.cursor()

            # Query all active players (team_id > 0 means on a roster, 0 = free agent)
            cursor.execute("""
                SELECT player_id, team_id, positions, first_name, last_name
                FROM players
                WHERE dynasty_id = ? AND team_id > 0 AND status = 'active'
            """, (self._dynasty_id,))

            all_players = []
            for row in cursor.fetchall():
                positions = json.loads(row[2]) if row[2] else []  # positions is column index 2
                all_players.append({
                    'player_id': row[0],  # player_id
                    'team_id': row[1],    # team_id
                    'positions': positions,
                    'name': f"{row[3]} {row[4]}"  # first_name + last_name
                })

            if not all_players:
                self._logger.warning("No players found for popularity calculation")
                return 0

            self._logger.info(f"Found {len(all_players)} active players for popularity calculation")

            # Initialize PopularityAPI
            pop_api = PopularityAPI(self._db)
            players_updated = 0

            # Calculate popularity for each player
            for player in all_players:
                try:
                    player_id = player.get('player_id')
                    team_id = player.get('team_id', 0)
                    positions = player.get('positions', [])

                    if not player_id or not positions:
                        continue

                    # Get primary position
                    position = positions[0] if isinstance(positions, list) else positions

                    # Check minimum snap threshold using rolling 4-week window
                    # This allows backups who become starters to gain popularity quickly
                    # while filtering out low-usage players (100 snaps = ~25 snaps/game)
                    recent_snaps = self._get_recent_snap_count(player_id, season, week, weeks=4)

                    if recent_snaps < 100:  # ~25 snaps/game over 4 games
                        # Skip players who haven't played enough recently to be relevant
                        continue

                    # Calculate components
                    performance = self.calculate_performance_score(
                        player_id, season, week, position
                    )
                    visibility = self.calculate_visibility_multiplier(
                        player_id, season, week
                    )
                    market = self.calculate_market_multiplier(team_id)

                    # Apply formula with normalized performance and scaled multipliers
                    # Normalize performance to 0-1 scale (PFF grades are 0-100)
                    normalized_performance = performance / 100.0

                    # Scale multipliers to prevent ceiling clustering (realistic distribution)
                    # Visibility: 0.5-3.0x → 0.7-1.3x (reduce range by 75%)
                    visibility_scaled = 0.7 + (visibility - 0.5) / 2.5 * 0.6
                    # Market: 0.8-2.0x → 0.9-1.2x (reduce range by 75%)
                    market_scaled = 0.9 + (market - 0.8) / 1.2 * 0.3

                    # Calculate raw score (max theoretical: 1.0 × 1.3 × 1.2 × 100 = 156)
                    raw_score = normalized_performance * visibility_scaled * market_scaled * 100

                    # Apply weekly decay (use baseline -1 for now until event tracking is implemented)
                    decay = -1.0  # TODO: Implement event-based decay calculation
                    final_score = raw_score + decay

                    # Cap to 0-100 range
                    final_score = max(0.0, min(100.0, final_score))

                    # Classify tier and trend
                    tier_enum = self.classify_tier(final_score)
                    trend_enum = self.calculate_trend(player_id, season, week)

                    # Calculate week change (difference from previous week)
                    week_change = 0.0
                    if week > 1:
                        prev_score = pop_api.get_popularity_score(
                            self._dynasty_id, player_id, season, week - 1
                        )
                        if prev_score:
                            week_change = final_score - prev_score.popularity_score

                    # Save to database (convert enums to string values)
                    pop_api.save_popularity_score(
                        dynasty_id=self._dynasty_id,
                        player_id=player_id,
                        season=season,
                        week=week,
                        popularity_score=final_score,
                        performance_score=performance,
                        visibility_multiplier=visibility,
                        market_multiplier=market,
                        week_change=week_change,
                        trend=trend_enum.value,
                        tier=tier_enum.value
                    )

                    players_updated += 1

                except Exception as e:
                    self._logger.error(
                        f"Failed to calculate popularity for player {player.get('player_id')}: {e}"
                    )
                    continue

            self._logger.info(
                f"Popularity calculation complete: {players_updated} players updated"
            )
            return players_updated

        except Exception as e:
            self._logger.error(f"Failed to calculate weekly popularity: {e}", exc_info=True)
            return 0
