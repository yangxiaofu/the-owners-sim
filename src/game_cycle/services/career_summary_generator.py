"""
Career Summary Generator for Game Cycle.

Generates comprehensive career summaries for retiring players including:
- Lifetime statistics aggregated from player_game_stats
- Career accomplishments (MVP, Pro Bowl, All-Pro, Super Bowl)
- Hall of Fame score calculation (0-100)
- Narrative text generation for UI display
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
import sqlite3

from src.game_cycle.database.retired_players_api import CareerSummary
from src.utils.player_field_extractors import extract_primary_position


# ============================================
# Constants - Position-Specific HOF Thresholds
# ============================================

@dataclass(frozen=True)
class HOFStatsThreshold:
    """Immutable thresholds for position-specific HOF scoring."""
    elite: int      # +20 points
    great: int      # +15 points
    good: int       # +10 points
    solid: int      # +5 points


HOF_THRESHOLDS: Dict[str, Dict[str, HOFStatsThreshold]] = {
    'QB': {
        'pass_yards': HOFStatsThreshold(elite=40000, great=30000, good=20000, solid=15000),
        'pass_tds': HOFStatsThreshold(elite=300, great=200, good=150, solid=100),
    },
    'RB': {
        'rush_yards': HOFStatsThreshold(elite=10000, great=8000, good=5000, solid=3000),
        'rush_tds': HOFStatsThreshold(elite=75, great=50, good=35, solid=20),
    },
    'WR': {
        'rec_yards': HOFStatsThreshold(elite=12000, great=10000, good=8000, solid=5000),
        'rec_tds': HOFStatsThreshold(elite=80, great=60, good=40, solid=25),
        'receptions': HOFStatsThreshold(elite=900, great=700, good=500, solid=350),
    },
    'TE': {
        'rec_yards': HOFStatsThreshold(elite=8000, great=6000, good=4500, solid=3000),
        'rec_tds': HOFStatsThreshold(elite=60, great=45, good=30, solid=20),
    },
    'EDGE': {
        'sacks': HOFStatsThreshold(elite=100, great=75, good=50, solid=35),
    },
    'DL': {
        'sacks': HOFStatsThreshold(elite=80, great=60, good=40, solid=25),
        'tackles': HOFStatsThreshold(elite=600, great=450, good=300, solid=200),
    },
    'LB': {
        'tackles': HOFStatsThreshold(elite=1200, great=1000, good=750, solid=500),
        'sacks': HOFStatsThreshold(elite=40, great=30, good=20, solid=10),
    },
    'CB': {
        'interceptions': HOFStatsThreshold(elite=50, great=40, good=30, solid=20),
    },
    'S': {
        'interceptions': HOFStatsThreshold(elite=40, great=30, good=20, solid=12),
        'tackles': HOFStatsThreshold(elite=800, great=600, good=400, solid=250),
    },
    'K': {
        'fg_made': HOFStatsThreshold(elite=400, great=300, good=200, solid=150),
    },
}

# Position abbreviation to group mapping
POSITION_TO_GROUP: Dict[str, str] = {
    # Quarterback
    'QB': 'QB', 'QUARTERBACK': 'QB',
    # Running backs
    'RB': 'RB', 'HB': 'RB', 'RUNNING_BACK': 'RB', 'HALFBACK': 'RB',
    'FB': 'RB', 'FULLBACK': 'RB',
    # Wide receiver
    'WR': 'WR', 'WIDE_RECEIVER': 'WR',
    # Tight end
    'TE': 'TE', 'TIGHT_END': 'TE',
    # Offensive line (no stats-based HOF bonus)
    'LT': 'OL', 'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
    'OL': 'OL', 'OT': 'OL', 'OG': 'OL', 'CENTER': 'OL',
    # Edge rushers
    'LE': 'EDGE', 'RE': 'EDGE', 'EDGE': 'EDGE', 'DE': 'EDGE',
    # Defensive line interior
    'DT': 'DL', 'NT': 'DL', 'NOSE_TACKLE': 'DL',
    # Linebackers
    'LOLB': 'LB', 'MLB': 'LB', 'ROLB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'LB': 'LB',
    'LINEBACKER': 'LB',
    # Cornerback
    'CB': 'CB', 'CORNERBACK': 'CB',
    # Safety
    'FS': 'S', 'SS': 'S', 'S': 'S', 'SAFETY': 'S',
    # Kicker/Punter
    'K': 'K', 'KICKER': 'K',
    'P': 'P', 'PUNTER': 'P',
}

# Team names for narrative generation
TEAM_NAMES: Dict[int, str] = {
    1: "Buffalo Bills", 2: "Miami Dolphins", 3: "New England Patriots", 4: "New York Jets",
    5: "Baltimore Ravens", 6: "Cincinnati Bengals", 7: "Cleveland Browns", 8: "Pittsburgh Steelers",
    9: "Houston Texans", 10: "Indianapolis Colts", 11: "Jacksonville Jaguars", 12: "Tennessee Titans",
    13: "Denver Broncos", 14: "Kansas City Chiefs", 15: "Las Vegas Raiders", 16: "Los Angeles Chargers",
    17: "Dallas Cowboys", 18: "New York Giants", 19: "Philadelphia Eagles", 20: "Washington Commanders",
    21: "Chicago Bears", 22: "Detroit Lions", 23: "Green Bay Packers", 24: "Minnesota Vikings",
    25: "Atlanta Falcons", 26: "Carolina Panthers", 27: "New Orleans Saints", 28: "Tampa Bay Buccaneers",
    29: "Arizona Cardinals", 30: "Los Angeles Rams", 31: "San Francisco 49ers", 32: "Seattle Seahawks",
}


# ============================================
# Main Service Class
# ============================================

class CareerSummaryGenerator:
    """
    Generates comprehensive career summaries for retiring players.

    Aggregates career statistics from player_game_stats across all seasons,
    counts awards/accolades, calculates Hall of Fame score, and generates
    narrative text for display.
    """

    # HOF Score Weights
    MVP_AWARD_POINTS = 25        # +25 per MVP (max 50)
    MVP_MAX_POINTS = 50
    SUPER_BOWL_WIN_POINTS = 15   # +15 per SB win (max 30)
    SUPER_BOWL_MAX_POINTS = 30
    ALL_PRO_FIRST_POINTS = 8     # +8 per First Team
    ALL_PRO_SECOND_POINTS = 4    # +4 per Second Team
    PRO_BOWL_POINTS = 2          # +2 per Pro Bowl (max 20)
    PRO_BOWL_MAX_POINTS = 20
    CAREER_STATS_MAX_POINTS = 20  # Position-specific stats bonus
    LONGEVITY_10_SEASONS = 5     # +5 for 10+ seasons
    LONGEVITY_15_SEASONS = 10    # +10 for 15+ seasons

    def __init__(self, db_path: str, dynasty_id: str):
        """
        Initialize the career summary generator.

        Args:
            db_path: Path to the game cycle database
            dynasty_id: Dynasty identifier for isolation
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._logger = logging.getLogger(__name__)

    # =========================================================================
    # Public API Methods
    # =========================================================================

    def generate_career_summary(
        self,
        player_dict: Dict[str, Any],
        retirement_season: int
    ) -> CareerSummary:
        """
        Generate a complete career summary for a retiring player.

        Args:
            player_dict: Player data dictionary with keys:
                - player_id: int
                - first_name, last_name: str
                - positions: List[str] or str (JSON)
                - team_id: int (final team)
            retirement_season: Season the player retired

        Returns:
            CareerSummary dataclass populated with all career data
        """
        player_id = player_dict['player_id']
        full_name = self._get_player_name(player_dict)
        position = extract_primary_position(player_dict.get('positions'), default='WR', uppercase=True)

        # Aggregate career statistics
        stats = self._aggregate_career_stats(player_id)

        # Get teams history
        teams_played_for, primary_team_id = self._get_teams_played_for(player_id)

        # Get seasons count
        seasons = self._get_distinct_seasons(player_id)
        seasons_count = len(seasons)

        # Count awards and accomplishments
        mvp_awards = self._count_mvp_awards(player_id)
        super_bowl_wins = self._count_super_bowl_wins(player_id)
        super_bowl_mvps = self._count_super_bowl_mvps(player_id)
        all_pro_first, all_pro_second = self._count_all_pro_selections(player_id)
        pro_bowls = self._count_pro_bowl_selections(player_id)

        # Get draft info
        draft_year, draft_round, draft_pick = self._get_draft_info(player_id)

        # Build initial summary (without HOF score)
        summary = CareerSummary(
            player_id=player_id,
            full_name=full_name,
            position=position,
            draft_year=draft_year,
            draft_round=draft_round,
            draft_pick=draft_pick,
            games_played=stats.get('games_played', 0),
            games_started=stats.get('games_started', 0),
            pass_yards=stats.get('pass_yards', 0),
            pass_tds=stats.get('pass_tds', 0),
            pass_ints=stats.get('pass_ints', 0),
            rush_yards=stats.get('rush_yards', 0),
            rush_tds=stats.get('rush_tds', 0),
            receptions=stats.get('receptions', 0),
            rec_yards=stats.get('rec_yards', 0),
            rec_tds=stats.get('rec_tds', 0),
            tackles=stats.get('tackles', 0),
            sacks=stats.get('sacks', 0.0),
            interceptions=stats.get('interceptions', 0),
            forced_fumbles=stats.get('forced_fumbles', 0),
            fg_made=stats.get('fg_made', 0),
            fg_attempted=stats.get('fg_attempted', 0),
            pro_bowls=pro_bowls,
            all_pro_first_team=all_pro_first,
            all_pro_second_team=all_pro_second,
            mvp_awards=mvp_awards,
            super_bowl_wins=super_bowl_wins,
            super_bowl_mvps=super_bowl_mvps,
            teams_played_for=teams_played_for,
            primary_team_id=primary_team_id or player_dict.get('team_id', 0),
            career_approximate_value=0,  # Not implemented yet
            hall_of_fame_score=0,
        )

        # Calculate HOF score
        hof_score = self.calculate_hof_score(summary, seasons_count)
        summary.hall_of_fame_score = hof_score

        return summary

    def calculate_hof_score(
        self,
        summary: CareerSummary,
        seasons_played: Optional[int] = None
    ) -> int:
        """
        Calculate Hall of Fame score (0-100) for a career summary.

        Formula:
        - MVP awards: +25 per award (max +50)
        - Super Bowl wins: +15 per win (max +30)
        - All-Pro First Team: +8 per selection
        - All-Pro Second Team: +4 per selection
        - Pro Bowls: +2 per selection (max +20)
        - Career stats bonus: +0-20 (position-specific)
        - Longevity: +5-10 (10+ seasons)

        Args:
            summary: CareerSummary with populated stats and accolades
            seasons_played: Number of seasons (if not provided, estimates from games)

        Returns:
            Integer score capped at 100
        """
        score = 0

        # 1. MVP Awards (max 50)
        mvp_points = min(summary.mvp_awards * self.MVP_AWARD_POINTS, self.MVP_MAX_POINTS)
        score += mvp_points

        # 2. Super Bowl Wins (max 30)
        sb_points = min(summary.super_bowl_wins * self.SUPER_BOWL_WIN_POINTS, self.SUPER_BOWL_MAX_POINTS)
        score += sb_points

        # 3. All-Pro First Team (uncapped)
        score += summary.all_pro_first_team * self.ALL_PRO_FIRST_POINTS

        # 4. All-Pro Second Team (uncapped)
        score += summary.all_pro_second_team * self.ALL_PRO_SECOND_POINTS

        # 5. Pro Bowls (max 20)
        pb_points = min(summary.pro_bowls * self.PRO_BOWL_POINTS, self.PRO_BOWL_MAX_POINTS)
        score += pb_points

        # 6. Career Stats Bonus (0-20 based on position)
        position_group = self._get_position_group(summary.position)
        stats_bonus = self._calculate_stats_bonus(position_group, summary)
        score += stats_bonus

        # 7. Longevity Bonus
        if seasons_played is None:
            # Estimate from games played (assume 16-game seasons)
            seasons_played = max(1, summary.games_played // 16)
        longevity_bonus = self._calculate_longevity_bonus(seasons_played)
        score += longevity_bonus

        # Cap at 100
        return min(score, 100)

    def generate_narrative(self, summary: CareerSummary) -> str:
        """
        Generate a narrative summary text for UI display.

        Creates human-readable career summary including:
        - Career overview (position, tenure, primary team)
        - Key statistics (position-appropriate)
        - Major accomplishments
        - Hall of Fame assessment

        Args:
            summary: CareerSummary with populated data

        Returns:
            Multi-paragraph narrative string
        """
        paragraphs = []

        # Paragraph 1: Career Overview
        overview = self._generate_career_overview(summary)
        paragraphs.append(overview)

        # Paragraph 2: Key Statistics
        stats_text = self._generate_stats_paragraph(summary)
        if stats_text:
            paragraphs.append(stats_text)

        # Paragraph 3: Accomplishments
        accolades_text = self._generate_accolades_paragraph(summary)
        if accolades_text:
            paragraphs.append(accolades_text)

        # Paragraph 4: HOF Assessment
        hof_text = self._generate_hof_assessment(summary)
        paragraphs.append(hof_text)

        return "\n\n".join(paragraphs)

    # =========================================================================
    # Stats Aggregation Methods
    # =========================================================================

    def _aggregate_career_stats(self, player_id: int) -> Dict[str, Any]:
        """
        Aggregate all career statistics from player_game_stats.

        Args:
            player_id: Player ID to aggregate

        Returns:
            Dictionary with aggregated stats
        """
        try:
            conn = sqlite3.connect(self._db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(DISTINCT pgs.game_id) as games_played,
                    COALESCE(SUM(pgs.passing_yards), 0) as pass_yards,
                    COALESCE(SUM(pgs.passing_tds), 0) as pass_tds,
                    COALESCE(SUM(pgs.passing_interceptions), 0) as pass_ints,
                    COALESCE(SUM(pgs.rushing_yards), 0) as rush_yards,
                    COALESCE(SUM(pgs.rushing_tds), 0) as rush_tds,
                    COALESCE(SUM(pgs.receptions), 0) as receptions,
                    COALESCE(SUM(pgs.receiving_yards), 0) as rec_yards,
                    COALESCE(SUM(pgs.receiving_tds), 0) as rec_tds,
                    COALESCE(SUM(pgs.tackles_total), 0) as tackles,
                    COALESCE(SUM(pgs.sacks), 0) as sacks,
                    COALESCE(SUM(pgs.interceptions), 0) as interceptions,
                    COALESCE(SUM(pgs.forced_fumbles), 0) as forced_fumbles,
                    COALESCE(SUM(pgs.field_goals_made), 0) as fg_made,
                    COALESCE(SUM(pgs.field_goals_attempted), 0) as fg_attempted
                FROM player_game_stats pgs
                WHERE pgs.dynasty_id = ? AND CAST(pgs.player_id AS INTEGER) = ?
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return {}

        except Exception as e:
            self._logger.error(f"Error aggregating stats for player {player_id}: {e}")
            return {}

    def _get_distinct_seasons(self, player_id: int) -> List[int]:
        """
        Get list of distinct seasons a player appeared in.

        Args:
            player_id: Player ID

        Returns:
            List of season years
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT g.season
                FROM player_game_stats pgs
                JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                WHERE pgs.dynasty_id = ? AND CAST(pgs.player_id AS INTEGER) = ?
                ORDER BY g.season
            """, (self._dynasty_id, player_id))

            rows = cursor.fetchall()
            conn.close()

            return [row[0] for row in rows]

        except Exception as e:
            self._logger.debug(f"Error getting seasons for player {player_id}: {e}")
            return []

    def _get_teams_played_for(self, player_id: int) -> Tuple[List[int], Optional[int]]:
        """
        Get list of teams and determine primary team.

        Args:
            player_id: Player ID

        Returns:
            Tuple of (team_ids list, primary_team_id)
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    pgs.team_id,
                    COUNT(DISTINCT pgs.game_id) as games_with_team
                FROM player_game_stats pgs
                WHERE pgs.dynasty_id = ? AND CAST(pgs.player_id AS INTEGER) = ?
                GROUP BY pgs.team_id
                ORDER BY games_with_team DESC
            """, (self._dynasty_id, player_id))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return [], None

            teams = [row[0] for row in rows]
            primary_team = rows[0][0]  # Team with most games

            return teams, primary_team

        except Exception as e:
            self._logger.debug(f"Error getting teams for player {player_id}: {e}")
            return [], None

    # =========================================================================
    # Awards/Accolades Methods
    # =========================================================================

    def _count_mvp_awards(self, player_id: int) -> int:
        """Count MVP awards won."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM award_winners
                WHERE dynasty_id = ? AND player_id = ?
                  AND award_id = 'mvp' AND is_winner = 1
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0

        except Exception as e:
            self._logger.debug(f"Error counting MVP awards for player {player_id}: {e}")
            return 0

    def _count_super_bowl_wins(self, player_id: int) -> int:
        """Count Super Bowl wins (player on team that won)."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Count seasons where player's team won Super Bowl
            cursor.execute("""
                SELECT COUNT(DISTINCT tsh.season) as count
                FROM team_season_history tsh
                WHERE tsh.dynasty_id = ? AND tsh.won_super_bowl = 1
                  AND tsh.team_id IN (
                      SELECT DISTINCT pgs.team_id
                      FROM player_game_stats pgs
                      JOIN games g ON pgs.game_id = g.game_id AND pgs.dynasty_id = g.dynasty_id
                      WHERE pgs.dynasty_id = ? AND CAST(pgs.player_id AS INTEGER) = ?
                        AND g.season = tsh.season
                  )
            """, (self._dynasty_id, self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0

        except Exception as e:
            self._logger.debug(f"Error counting SB wins for player {player_id}: {e}")
            return 0

    def _count_super_bowl_mvps(self, player_id: int) -> int:
        """Count Super Bowl MVP awards."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Check for Super Bowl MVP award
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM award_winners
                WHERE dynasty_id = ? AND player_id = ?
                  AND award_id = 'super_bowl_mvp' AND is_winner = 1
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0

        except Exception as e:
            self._logger.debug(f"Error counting SB MVPs for player {player_id}: {e}")
            return 0

    def _count_all_pro_selections(self, player_id: int) -> Tuple[int, int]:
        """
        Count All-Pro selections.

        Returns:
            Tuple of (first_team_count, second_team_count)
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT team_type, COUNT(*) as count
                FROM all_pro_selections
                WHERE dynasty_id = ? AND player_id = ?
                GROUP BY team_type
            """, (self._dynasty_id, player_id))

            rows = cursor.fetchall()
            conn.close()

            first_team = 0
            second_team = 0

            for row in rows:
                if row[0] == 'FIRST_TEAM':
                    first_team = row[1]
                elif row[0] == 'SECOND_TEAM':
                    second_team = row[1]

            return first_team, second_team

        except Exception as e:
            self._logger.debug(f"Error counting All-Pro for player {player_id}: {e}")
            return 0, 0

    def _count_pro_bowl_selections(self, player_id: int) -> int:
        """Count Pro Bowl selections."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM pro_bowl_selections
                WHERE dynasty_id = ? AND player_id = ?
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0

        except Exception as e:
            self._logger.debug(f"Error counting Pro Bowls for player {player_id}: {e}")
            return 0

    def _count_other_major_awards(self, player_id: int) -> int:
        """Count other major awards (OPOY, DPOY, OROY, DROY, CPOY)."""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT COUNT(*) as count
                FROM award_winners
                WHERE dynasty_id = ? AND player_id = ?
                  AND award_id IN ('opoy', 'dpoy', 'oroy', 'droy', 'cpoy')
                  AND is_winner = 1
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            return row[0] if row else 0

        except Exception as e:
            self._logger.debug(f"Error counting other awards for player {player_id}: {e}")
            return 0

    # =========================================================================
    # HOF Score Calculation Methods
    # =========================================================================

    def _calculate_stats_bonus(
        self,
        position_group: str,
        summary: CareerSummary
    ) -> int:
        """
        Calculate position-specific stats bonus (0-20 points).

        Takes the MAXIMUM bonus achieved across all relevant stat categories.

        Args:
            position_group: Position group (QB, RB, WR, etc.)
            summary: CareerSummary with stats

        Returns:
            Integer bonus points (0-20)
        """
        if position_group not in HOF_THRESHOLDS:
            return 0

        thresholds = HOF_THRESHOLDS[position_group]
        max_bonus = 0

        for stat_name, threshold in thresholds.items():
            # Get stat value from summary
            stat_value = getattr(summary, stat_name, 0)
            if stat_value is None:
                stat_value = 0

            # Convert to int/float for comparison
            if isinstance(stat_value, (int, float)):
                # Determine bonus tier
                if stat_value >= threshold.elite:
                    bonus = 20
                elif stat_value >= threshold.great:
                    bonus = 15
                elif stat_value >= threshold.good:
                    bonus = 10
                elif stat_value >= threshold.solid:
                    bonus = 5
                else:
                    bonus = 0

                max_bonus = max(max_bonus, bonus)

        return max_bonus

    def _calculate_longevity_bonus(self, seasons_played: int) -> int:
        """
        Calculate longevity bonus.

        Args:
            seasons_played: Number of seasons in career

        Returns:
            Bonus points (5 for 10+ seasons, 10 for 15+ seasons)
        """
        if seasons_played >= 15:
            return self.LONGEVITY_15_SEASONS
        elif seasons_played >= 10:
            return self.LONGEVITY_10_SEASONS
        return 0

    def _get_position_group(self, position: str) -> str:
        """Map position abbreviation to position group."""
        pos_upper = position.upper().replace(' ', '_')
        return POSITION_TO_GROUP.get(pos_upper, 'UNKNOWN')

    # =========================================================================
    # Draft Info Methods
    # =========================================================================

    def _get_draft_info(self, player_id: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Get draft information for a player.

        Args:
            player_id: Player ID

        Returns:
            Tuple of (draft_year, draft_round, draft_pick) - all optional
        """
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Try to get draft info from draft_prospects joined with draft_classes
            cursor.execute("""
                SELECT
                    dc.season as draft_year,
                    dp.draft_round,
                    dp.draft_pick
                FROM draft_prospects dp
                JOIN draft_classes dc ON dp.draft_class_id = dc.draft_class_id
                    AND dp.dynasty_id = dc.dynasty_id
                WHERE dp.dynasty_id = ? AND dp.roster_player_id = ?
                  AND dp.is_drafted = 1
                LIMIT 1
            """, (self._dynasty_id, player_id))

            row = cursor.fetchone()
            conn.close()

            if row:
                return row[0], row[1], row[2]
            return None, None, None

        except Exception as e:
            self._logger.debug(f"Error getting draft info for player {player_id}: {e}")
            return None, None, None

    # =========================================================================
    # Narrative Generation Helpers
    # =========================================================================

    def _generate_career_overview(self, summary: CareerSummary) -> str:
        """Generate opening paragraph with career overview."""
        team_name = self._get_team_name(summary.primary_team_id)
        seasons = max(1, summary.games_played // 16)

        overview = f"{summary.full_name} had a {seasons}-year career as a {summary.position}"

        if summary.draft_year and summary.draft_round:
            overview += f", drafted in round {summary.draft_round} of the {summary.draft_year} NFL Draft"

        overview += f". He spent the majority of his career with the {team_name}"

        if summary.teams_played_for and len(summary.teams_played_for) > 1:
            other_count = len(summary.teams_played_for) - 1
            overview += f", also playing for {other_count} other team{'s' if other_count > 1 else ''}"

        overview += "."

        return overview

    def _generate_stats_paragraph(self, summary: CareerSummary) -> str:
        """Generate stats paragraph based on position."""
        position_group = self._get_position_group(summary.position)

        if position_group == 'QB':
            return (
                f"Over {summary.games_played} career games, {summary.full_name.split()[-1]} "
                f"threw for {self._format_number(summary.pass_yards)} yards and "
                f"{summary.pass_tds} touchdowns with {summary.pass_ints} interceptions."
            )

        elif position_group == 'RB':
            text = (
                f"As a runner, he accumulated {self._format_number(summary.rush_yards)} rushing yards "
                f"and {summary.rush_tds} touchdowns on the ground."
            )
            if summary.receptions > 0:
                text += (
                    f" He also contributed {summary.receptions} receptions "
                    f"for {self._format_number(summary.rec_yards)} receiving yards."
                )
            return text

        elif position_group == 'WR':
            return (
                f"He finished with {summary.receptions} career receptions for "
                f"{self._format_number(summary.rec_yards)} yards and {summary.rec_tds} touchdowns."
            )

        elif position_group == 'TE':
            return (
                f"The tight end recorded {summary.receptions} receptions for "
                f"{self._format_number(summary.rec_yards)} yards and {summary.rec_tds} touchdowns."
            )

        elif position_group in ('EDGE', 'DL', 'LB'):
            return (
                f"Defensively, he recorded {summary.tackles} career tackles, "
                f"{summary.sacks:.1f} sacks, {summary.interceptions} interceptions, "
                f"and {summary.forced_fumbles} forced fumbles."
            )

        elif position_group in ('CB', 'S'):
            return (
                f"In the secondary, he tallied {summary.tackles} tackles and "
                f"{summary.interceptions} interceptions over his career."
            )

        elif position_group == 'K':
            if summary.fg_attempted > 0:
                fg_pct = (summary.fg_made / summary.fg_attempted) * 100
                return (
                    f"The kicker made {summary.fg_made} of {summary.fg_attempted} "
                    f"field goals ({fg_pct:.1f}%) during his career."
                )

        return ""

    def _generate_accolades_paragraph(self, summary: CareerSummary) -> str:
        """Generate accomplishments paragraph."""
        accolades = []

        if summary.mvp_awards > 0:
            accolades.append(f"{summary.mvp_awards}x NFL MVP")
        if summary.super_bowl_wins > 0:
            accolades.append(f"{summary.super_bowl_wins}x Super Bowl champion")
        if summary.super_bowl_mvps > 0:
            accolades.append(f"{summary.super_bowl_mvps}x Super Bowl MVP")
        if summary.all_pro_first_team > 0:
            accolades.append(f"{summary.all_pro_first_team}x First-Team All-Pro")
        if summary.all_pro_second_team > 0:
            accolades.append(f"{summary.all_pro_second_team}x Second-Team All-Pro")
        if summary.pro_bowls > 0:
            accolades.append(f"{summary.pro_bowls}x Pro Bowl selection")

        if accolades:
            return f"Career accolades include: {', '.join(accolades)}."
        return ""

    def _generate_hof_assessment(self, summary: CareerSummary) -> str:
        """Generate Hall of Fame assessment paragraph."""
        score = summary.hall_of_fame_score
        last_name = summary.full_name.split()[-1] if summary.full_name else "He"

        if score >= 85:
            return (
                f"With a Hall of Fame score of {score}, {last_name} is "
                f"virtually certain to be inducted into the Hall of Fame when eligible. "
                f"He is regarded as one of the all-time greats at his position."
            )
        elif score >= 70:
            return (
                f"His Hall of Fame score of {score} makes him a strong candidate "
                f"for Canton. He will be remembered as one of the best players "
                f"of his generation."
            )
        elif score >= 55:
            return (
                f"With a Hall of Fame score of {score}, he may be considered "
                f"for the Hall of Fame, though induction is not guaranteed. "
                f"He had a highly productive career at the professional level."
            )
        elif score >= 40:
            return (
                f"His Hall of Fame score of {score} reflects a solid NFL career. "
                f"While unlikely to make the Hall of Fame, he was a respected "
                f"contributor to his teams."
            )
        else:
            return (
                f"He concludes his career with a Hall of Fame score of {score}. "
                f"While not Canton-bound, he made meaningful contributions "
                f"during his time in the league."
            )

    def _format_number(self, value: int) -> str:
        """Format large numbers with commas."""
        return f"{value:,}"

    def _get_team_name(self, team_id: Optional[int]) -> str:
        """Get team name from team_id."""
        if team_id is None:
            return "multiple teams"
        return TEAM_NAMES.get(team_id, f"Team {team_id}")

    def _get_player_name(self, player_dict: Dict[str, Any]) -> str:
        """Get formatted player name."""
        first = player_dict.get('first_name', '')
        last = player_dict.get('last_name', '')
        return f"{first} {last}".strip() or "Unknown Player"
