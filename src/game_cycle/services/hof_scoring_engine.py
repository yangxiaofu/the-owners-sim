"""
HOF Scoring Engine - Calculate Hall of Fame scores with detailed breakdowns.

Wraps existing scoring logic from CareerSummaryGenerator and adds:
- Score breakdown by category
- Tier classification (First Ballot, Strong, Borderline, Long Shot, Not HOF)
- Stats tier identification (elite, great, good, solid)

The scoring formula matches the existing calculate_hof_score() implementation
to ensure consistency with career_summaries.hall_of_fame_score values.
"""

from dataclasses import dataclass
from typing import Dict, Any, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from game_cycle.services.hof_eligibility_service import HOFCandidate


# ============================================
# Enums and Constants
# ============================================

class HOFTier(Enum):
    """Classification of HOF candidacy strength."""
    FIRST_BALLOT = "FIRST_BALLOT"      # 85+ score - Immediate lock
    STRONG = "STRONG"                   # 70-84 - Likely eventual inductee
    BORDERLINE = "BORDERLINE"           # 55-69 - May get in eventually
    LONG_SHOT = "LONG_SHOT"             # 40-54 - Unlikely but possible
    NOT_HOF = "NOT_HOF"                 # <40 - Won't make it


# Position-specific stat thresholds for HOF scoring
# Format: (elite, great, good, solid)
HOF_STATS_THRESHOLDS: Dict[str, Dict[str, tuple]] = {
    'QB': {
        'pass_yards': (40000, 30000, 20000, 15000),
        'pass_tds': (300, 200, 150, 100),
    },
    'RB': {
        'rush_yards': (10000, 8000, 5000, 3000),
        'rush_tds': (75, 50, 35, 20),
    },
    'WR': {
        'rec_yards': (12000, 10000, 8000, 5000),
        'rec_tds': (80, 60, 40, 25),
        'receptions': (900, 700, 500, 350),
    },
    'TE': {
        'rec_yards': (8000, 6000, 4500, 3000),
        'rec_tds': (60, 45, 30, 20),
    },
    'EDGE': {
        'sacks': (100, 75, 50, 35),
    },
    'DL': {
        'sacks': (80, 60, 40, 25),
        'tackles': (600, 450, 300, 200),
    },
    'LB': {
        'tackles': (1200, 1000, 750, 500),
        'sacks': (40, 30, 20, 10),
    },
    'CB': {
        'interceptions': (50, 40, 30, 20),
    },
    'S': {
        'interceptions': (40, 30, 20, 12),
        'tackles': (800, 600, 400, 250),
    },
    'K': {
        'fg_made': (400, 300, 200, 150),
    },
}

# Position abbreviation to group mapping
POSITION_TO_GROUP: Dict[str, str] = {
    # Quarterback
    'QB': 'QB',
    # Running backs
    'RB': 'RB', 'HB': 'RB', 'FB': 'RB',
    # Wide receiver
    'WR': 'WR',
    # Tight end
    'TE': 'TE',
    # Offensive line (no stats-based HOF bonus)
    'LT': 'OL', 'LG': 'OL', 'C': 'OL', 'RG': 'OL', 'RT': 'OL',
    # Edge rushers
    'LE': 'EDGE', 'RE': 'EDGE', 'EDGE': 'EDGE', 'DE': 'EDGE',
    # Defensive line interior
    'DT': 'DL', 'NT': 'DL',
    # Linebackers
    'LOLB': 'LB', 'MLB': 'LB', 'ROLB': 'LB', 'ILB': 'LB', 'OLB': 'LB', 'LB': 'LB',
    # Cornerback
    'CB': 'CB',
    # Safety
    'FS': 'S', 'SS': 'S', 'S': 'S',
    # Kicker/Punter
    'K': 'K', 'P': 'P',
}


# ============================================
# Dataclasses
# ============================================

@dataclass
class HOFScoreBreakdown:
    """Detailed breakdown of HOF score calculation."""
    total_score: int
    tier: HOFTier

    # Factor contributions (actual points earned)
    mvp_score: int = 0           # +25 per MVP (max 50)
    super_bowl_score: int = 0    # +15 per win (max 30)
    all_pro_first_score: int = 0 # +8 per selection (uncapped)
    all_pro_second_score: int = 0# +4 per selection (uncapped)
    pro_bowl_score: int = 0      # +2 per selection (max 20)
    stats_score: int = 0         # 0-20 position-specific
    longevity_score: int = 0     # 0-10

    # Source data (for display)
    mvp_count: int = 0
    super_bowl_count: int = 0
    all_pro_first_count: int = 0
    all_pro_second_count: int = 0
    pro_bowl_count: int = 0
    career_seasons: int = 0
    stats_tier: str = ""  # "elite", "great", "good", "solid", or ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize breakdown for database storage."""
        return {
            'total_score': self.total_score,
            'tier': self.tier.value,
            'mvp_score': self.mvp_score,
            'super_bowl_score': self.super_bowl_score,
            'all_pro_first_score': self.all_pro_first_score,
            'all_pro_second_score': self.all_pro_second_score,
            'pro_bowl_score': self.pro_bowl_score,
            'stats_score': self.stats_score,
            'longevity_score': self.longevity_score,
            'mvp_count': self.mvp_count,
            'super_bowl_count': self.super_bowl_count,
            'all_pro_first_count': self.all_pro_first_count,
            'all_pro_second_count': self.all_pro_second_count,
            'pro_bowl_count': self.pro_bowl_count,
            'career_seasons': self.career_seasons,
            'stats_tier': self.stats_tier,
        }


# ============================================
# HOFScoringEngine Class
# ============================================

class HOFScoringEngine:
    """
    Calculates Hall of Fame scores with detailed breakdowns.

    Wraps existing scoring logic from CareerSummaryGenerator and adds:
    - Score breakdown by category
    - Tier classification
    - Stats tier identification

    Score Ranges:
    - 85-100: First-ballot lock (rare)
    - 70-84: Strong candidate
    - 55-69: Borderline
    - 40-54: Long shot
    - 0-39: Not HOF caliber
    """

    # Point values (matching existing calculate_hof_score)
    MVP_POINTS = 25
    MVP_MAX = 50
    SUPER_BOWL_POINTS = 15
    SUPER_BOWL_MAX = 30
    ALL_PRO_FIRST_POINTS = 8
    ALL_PRO_SECOND_POINTS = 4
    PRO_BOWL_POINTS = 2
    PRO_BOWL_MAX = 20

    # Stats tier bonuses
    STATS_BONUS = {'elite': 20, 'great': 15, 'good': 10, 'solid': 5}

    # Longevity bonuses
    LONGEVITY_10_PLUS = 5
    LONGEVITY_15_PLUS = 10

    # Tier thresholds
    TIER_FIRST_BALLOT = 85
    TIER_STRONG = 70
    TIER_BORDERLINE = 55
    TIER_LONG_SHOT = 40

    def calculate_score(
        self,
        mvp_awards: int,
        super_bowl_wins: int,
        all_pro_first: int,
        all_pro_second: int,
        pro_bowls: int,
        career_seasons: int,
        position: str,
        career_stats: Dict[str, Any]
    ) -> HOFScoreBreakdown:
        """
        Calculate HOF score with full breakdown.

        Args:
            mvp_awards: Number of MVP awards
            super_bowl_wins: Number of Super Bowl wins
            all_pro_first: Number of All-Pro First Team selections
            all_pro_second: Number of All-Pro Second Team selections
            pro_bowls: Number of Pro Bowl selections
            career_seasons: Total seasons played
            position: Primary position abbreviation (e.g., "QB", "WR")
            career_stats: Dict of career stats (pass_yards, rush_yards, etc.)

        Returns:
            HOFScoreBreakdown with individual component scores and tier
        """
        # MVP: +25 per, max 50
        mvp_score = min(mvp_awards * self.MVP_POINTS, self.MVP_MAX)

        # Super Bowl: +15 per, max 30
        sb_score = min(super_bowl_wins * self.SUPER_BOWL_POINTS, self.SUPER_BOWL_MAX)

        # All-Pro First: +8 per (uncapped)
        ap1_score = all_pro_first * self.ALL_PRO_FIRST_POINTS

        # All-Pro Second: +4 per (uncapped)
        ap2_score = all_pro_second * self.ALL_PRO_SECOND_POINTS

        # Pro Bowls: +2 per, max 20
        pb_score = min(pro_bowls * self.PRO_BOWL_POINTS, self.PRO_BOWL_MAX)

        # Stats bonus (0-20)
        stats_tier = self._calculate_stats_tier(position, career_stats)
        stats_score = self.STATS_BONUS.get(stats_tier, 0)

        # Longevity bonus (0-10)
        if career_seasons >= 15:
            longevity_score = self.LONGEVITY_15_PLUS
        elif career_seasons >= 10:
            longevity_score = self.LONGEVITY_10_PLUS
        else:
            longevity_score = 0

        # Total (capped at 100)
        total = min(100, mvp_score + sb_score + ap1_score + ap2_score +
                    pb_score + stats_score + longevity_score)

        return HOFScoreBreakdown(
            total_score=total,
            tier=self._determine_tier(total),
            mvp_score=mvp_score,
            super_bowl_score=sb_score,
            all_pro_first_score=ap1_score,
            all_pro_second_score=ap2_score,
            pro_bowl_score=pb_score,
            stats_score=stats_score,
            longevity_score=longevity_score,
            mvp_count=mvp_awards,
            super_bowl_count=super_bowl_wins,
            all_pro_first_count=all_pro_first,
            all_pro_second_count=all_pro_second,
            pro_bowl_count=pro_bowls,
            career_seasons=career_seasons,
            stats_tier=stats_tier,
        )

    def calculate_from_candidate(self, candidate: "HOFCandidate") -> HOFScoreBreakdown:
        """
        Calculate score from HOFCandidate dataclass.

        Args:
            candidate: HOFCandidate with career data

        Returns:
            HOFScoreBreakdown with score and breakdown
        """
        return self.calculate_score(
            mvp_awards=candidate.mvp_awards,
            super_bowl_wins=candidate.super_bowl_wins,
            all_pro_first=candidate.all_pro_first_team,
            all_pro_second=candidate.all_pro_second_team,
            pro_bowls=candidate.pro_bowl_selections,
            career_seasons=candidate.career_seasons,
            position=candidate.primary_position,
            career_stats=candidate.career_stats,
        )

    def _calculate_stats_tier(
        self,
        position: str,
        career_stats: Dict[str, Any]
    ) -> str:
        """
        Determine stats tier by comparing to position thresholds.

        Uses the MAXIMUM tier achieved across all relevant stat categories
        for the position (matching existing CareerSummaryGenerator logic).

        Args:
            position: Position abbreviation (e.g., "QB", "WR")
            career_stats: Dict of career stats

        Returns:
            Tier string: "elite", "great", "good", "solid", or "" (none)
        """
        pos_group = self._get_position_group(position)
        thresholds = HOF_STATS_THRESHOLDS.get(pos_group, {})

        if not thresholds:
            return ''

        best_tier = ''
        tier_priority = {'elite': 4, 'great': 3, 'good': 2, 'solid': 1, '': 0}

        for stat, (elite, great, good, solid) in thresholds.items():
            value = career_stats.get(stat, 0)
            if value is None:
                value = 0

            # Determine tier for this stat
            current_tier = ''
            if value >= elite:
                current_tier = 'elite'
            elif value >= great:
                current_tier = 'great'
            elif value >= good:
                current_tier = 'good'
            elif value >= solid:
                current_tier = 'solid'

            # Keep the best tier across all stats
            if tier_priority.get(current_tier, 0) > tier_priority.get(best_tier, 0):
                best_tier = current_tier

            # Short-circuit if we hit elite
            if best_tier == 'elite':
                break

        return best_tier

    def _get_position_group(self, position: str) -> str:
        """
        Map position abbreviation to scoring group.

        Args:
            position: Position abbreviation

        Returns:
            Position group for threshold lookup
        """
        return POSITION_TO_GROUP.get(position.upper(), '')

    def _determine_tier(self, total_score: int) -> HOFTier:
        """
        Classify total score into HOF tier.

        Args:
            total_score: Total HOF score (0-100)

        Returns:
            HOFTier enum value
        """
        if total_score >= self.TIER_FIRST_BALLOT:
            return HOFTier.FIRST_BALLOT
        elif total_score >= self.TIER_STRONG:
            return HOFTier.STRONG
        elif total_score >= self.TIER_BORDERLINE:
            return HOFTier.BORDERLINE
        elif total_score >= self.TIER_LONG_SHOT:
            return HOFTier.LONG_SHOT
        else:
            return HOFTier.NOT_HOF
