"""
Award Scoring Criteria.

Implements scoring algorithms for each award type:
- MVP: 40% stats, 40% grades, 20% team success with position multipliers
- OPOY/DPOY: 50% stats, 50% grades (position-neutral within side)
- OROY/DROY: Same as OPOY/DPOY, rookies only
- CPOY: YoY improvement, games missed, narrative
- All-Pro: Position rankings with NFL slot counts

Part of Milestone 10: Awards System, Tollgate 2.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from .models import (
    AwardType,
    PlayerCandidate,
    AwardScore,
    OFFENSIVE_POSITIONS,
    DEFENSIVE_POSITIONS,
)
from analytics.grading_constants import get_position_group


# ============================================
# Position-Specific Stat Benchmarks
# ============================================

# QB benchmarks - raised for more differentiation at top
QB_BENCHMARKS = {
    'passing_yards': {'elite': 4800, 'good': 4000, 'average': 3400},
    'passing_tds': {'elite': 40, 'good': 32, 'average': 25},
    'passer_rating': {'elite': 110.0, 'good': 100.0, 'average': 90.0},
    'passing_interceptions': {'elite': 6, 'good': 10, 'average': 14},  # Lower is better
}

# RB benchmarks - raised for more differentiation at top
RB_BENCHMARKS = {
    'total_yards': {'elite': 2000, 'good': 1500, 'average': 1100},
    'total_tds': {'elite': 18, 'good': 12, 'average': 8},
    'receptions': {'elite': 90, 'good': 60, 'average': 40},
}

# WR benchmarks
WR_BENCHMARKS = {
    'receiving_yards': {'elite': 1400, 'good': 1100, 'average': 800},
    'receiving_tds': {'elite': 12, 'good': 8, 'average': 5},
    'receptions': {'elite': 100, 'good': 80, 'average': 60},
}

# TE benchmarks
TE_BENCHMARKS = {
    'receiving_yards': {'elite': 1000, 'good': 750, 'average': 500},
    'receiving_tds': {'elite': 10, 'good': 7, 'average': 4},
    'receptions': {'elite': 80, 'good': 60, 'average': 40},
}

# TE blocking benchmarks
TE_BLOCKING_BENCHMARKS = {
    'pass_blocking_grade': {'elite': 80, 'good': 70, 'average': 60},
}

# Defensive benchmarks
DEFENSIVE_BENCHMARKS = {
    'sacks': {'elite': 12.0, 'good': 8.0, 'average': 5.0},
    'interceptions': {'elite': 5, 'good': 3, 'average': 1},
    'tackles_total': {'elite': 120, 'good': 80, 'average': 50},
    'forced_fumbles': {'elite': 4, 'good': 2, 'average': 1},
}

# Position-specific defensive benchmarks
DL_BENCHMARKS = {
    'sacks': {'elite': 14.0, 'good': 10.0, 'average': 6.0},
    'tackles_total': {'elite': 60, 'good': 45, 'average': 30},
    'forced_fumbles': {'elite': 4, 'good': 3, 'average': 1},
}

# LB benchmarks (emphasize tackles and versatility)
LB_BENCHMARKS = {
    'tackles_total': {'elite': 130, 'good': 100, 'average': 70},
    'sacks': {'elite': 6.0, 'good': 4.0, 'average': 2.0},
    'interceptions': {'elite': 3, 'good': 2, 'average': 1},
}

# DB benchmarks (emphasize coverage and INTs)
DB_BENCHMARKS = {
    'interceptions': {'elite': 6, 'good': 4, 'average': 2},
    'tackles_total': {'elite': 80, 'good': 60, 'average': 40},
    'forced_fumbles': {'elite': 3, 'good': 2, 'average': 1},
}

# OL benchmarks (based on blocking grades)
OL_BENCHMARKS = {
    'pass_blocking_grade': {'elite': 85.0, 'good': 75.0, 'average': 65.0},
    'run_blocking_grade': {'elite': 85.0, 'good': 75.0, 'average': 65.0},
}


# ============================================
# MVP Position Multipliers
# ============================================

MVP_POSITION_MULTIPLIERS = {
    # Offensive positions
    # QB boosted to 1.15 to offset systematic grade disadvantage from INT penalties
    # WR/TE reduced to 0.80 to create ~35% gap (enough to overcome grade imbalance)
    'QB': 1.15,
    'RB': 0.85,
    'WR': 0.80,
    'TE': 0.80,
    'FB': 0.75,
    'LT': 0.70,
    'LG': 0.70,
    'C': 0.70,
    'RG': 0.70,
    'RT': 0.70,
    'OL': 0.70,
    # Defensive positions
    'LE': 0.75,
    'DT': 0.75,
    'RE': 0.75,
    'NT': 0.75,
    'EDGE': 0.80,
    'LOLB': 0.75,
    'MLB': 0.75,
    'ROLB': 0.75,
    'ILB': 0.75,
    'OLB': 0.75,
    'CB': 0.75,
    'FS': 0.75,
    'SS': 0.75,
    'S': 0.75,
    'DL': 0.75,
    'LB': 0.75,
    'DB': 0.75,
}

DEFAULT_POSITION_MULTIPLIER = 0.80


# ============================================
# All-Pro Position Slots (NFL Standard)
# ============================================

ALL_PRO_POSITION_SLOTS = {
    # Offense
    'QB': 1,
    'RB': 2,
    'FB': 1,
    'WR': 2,
    'TE': 1,
    'LT': 1,
    'LG': 1,
    'C': 1,
    'RG': 1,
    'RT': 1,
    # Defense
    'LE': 1,
    'DT': 2,
    'RE': 1,
    'EDGE': 2,
    'LOLB': 1,
    'MLB': 1,
    'ROLB': 1,
    'CB': 2,
    'FS': 1,
    'SS': 1,
    # Special teams
    'K': 1,
    'P': 1,
}


# ============================================
# Base Award Criteria Class
# ============================================

class BaseAwardCriteria(ABC):
    """
    Base class for award scoring criteria.

    Subclasses implement position-specific scoring algorithms.
    """

    def __init__(self, award_type: AwardType):
        """
        Initialize criteria with award type.

        Args:
            award_type: The type of award these criteria apply to
        """
        self.award_type = award_type

    @abstractmethod
    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """
        Calculate the score for a candidate.

        Args:
            candidate: Player candidate with all data populated

        Returns:
            AwardScore with component breakdown
        """
        pass

    def rank_candidates(self, candidates: List[PlayerCandidate]) -> List[AwardScore]:
        """
        Rank all candidates for the award.

        Args:
            candidates: List of eligible candidates

        Returns:
            List of AwardScore objects sorted by final_score descending
        """
        scores = [self.calculate_score(c) for c in candidates]
        # Sort by final_score descending, then by games_played, then overall_grade
        scores.sort(
            key=lambda s: (
                s.final_score,
                s.breakdown.get('games_played', 0),
                s.breakdown.get('overall_grade', 0),
            ),
            reverse=True
        )
        return scores

    def _normalize_stat(
        self,
        value: float,
        benchmarks: Dict[str, float],
        lower_is_better: bool = False
    ) -> float:
        """
        Normalize a stat value to 0-100 scale based on benchmarks.

        Args:
            value: Raw stat value
            benchmarks: Dict with 'elite', 'good', 'average' values
            lower_is_better: If True, lower values score higher (e.g., INTs)

        Returns:
            Normalized score 0-100
        """
        elite = benchmarks['elite']
        good = benchmarks['good']
        average = benchmarks['average']

        if lower_is_better:
            # Invert the scoring
            if value <= elite:
                return 100.0
            elif value <= good:
                # Between elite and good
                return 80.0 + 20.0 * (good - value) / (good - elite)
            elif value <= average:
                # Between good and average
                return 60.0 + 20.0 * (average - value) / (average - good)
            else:
                # Below average
                return max(0.0, 60.0 * (1 - (value - average) / average))
        else:
            if value >= elite:
                return 100.0
            elif value >= good:
                return 80.0 + 20.0 * (value - good) / (elite - good)
            elif value >= average:
                return 60.0 + 20.0 * (value - average) / (good - average)
            else:
                # Below average
                return max(0.0, 60.0 * value / average) if average > 0 else 0.0

    def _normalize_grade(self, grade: float) -> float:
        """
        Normalize a grade (0-100 scale) to component score.

        Args:
            grade: PFF-style grade 0-100

        Returns:
            Normalized component score 0-100
        """
        # Grades are already 0-100, but we apply scaling
        # Elite: 90+, Good: 80+, Average: 70+
        if grade >= 90:
            return 100.0
        elif grade >= 80:
            return 80.0 + 20.0 * (grade - 80) / 10
        elif grade >= 70:
            return 60.0 + 20.0 * (grade - 70) / 10
        else:
            return max(0.0, grade / 70 * 60)

    def _calculate_dl_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate DL stats: 50% sacks, 30% tackles, 20% FF.

        Args:
            candidate: Player candidate

        Returns:
            Normalized DL stat score 0-100
        """
        sacks = self._normalize_stat(candidate.sacks, DL_BENCHMARKS['sacks'])
        tackles = self._normalize_stat(candidate.tackles_total, DL_BENCHMARKS['tackles_total'])
        ff = self._normalize_stat(candidate.forced_fumbles, DL_BENCHMARKS['forced_fumbles'])
        return sacks * 0.50 + tackles * 0.30 + ff * 0.20

    def _calculate_lb_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate LB stats: 50% tackles, 25% sacks, 25% INTs.

        Args:
            candidate: Player candidate

        Returns:
            Normalized LB stat score 0-100
        """
        tackles = self._normalize_stat(candidate.tackles_total, LB_BENCHMARKS['tackles_total'])
        sacks = self._normalize_stat(candidate.sacks, LB_BENCHMARKS['sacks'])
        ints = self._normalize_stat(candidate.interceptions, LB_BENCHMARKS['interceptions'])
        return tackles * 0.50 + sacks * 0.25 + ints * 0.25

    def _calculate_db_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate DB stats: 50% INTs, 30% tackles, 20% FF.

        Args:
            candidate: Player candidate

        Returns:
            Normalized DB stat score 0-100
        """
        ints = self._normalize_stat(candidate.interceptions, DB_BENCHMARKS['interceptions'])
        tackles = self._normalize_stat(candidate.tackles_total, DB_BENCHMARKS['tackles_total'])
        ff = self._normalize_stat(candidate.forced_fumbles, DB_BENCHMARKS['forced_fumbles'])
        return ints * 0.50 + tackles * 0.30 + ff * 0.20

    def _calculate_te_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate TE stats: 35% yards, 30% TDs, 20% receptions, 15% blocking.

        Args:
            candidate: Player candidate

        Returns:
            Normalized TE stat score 0-100
        """
        yards = self._normalize_stat(candidate.receiving_yards, TE_BENCHMARKS['receiving_yards'])
        tds = self._normalize_stat(candidate.receiving_tds, TE_BENCHMARKS['receiving_tds'])
        recs = self._normalize_stat(candidate.receptions, TE_BENCHMARKS['receptions'])
        # Use position_grade as blocking indicator (populated from pass_blocking_grade for TEs)
        blocking = self._normalize_grade(candidate.position_grade) if candidate.position_grade else 50.0
        return yards * 0.35 + tds * 0.30 + recs * 0.20 + blocking * 0.15

    def _calculate_ol_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate OL stats using blocking grades with position-specific weights.

        Tackles (LT/RT): 60% pass blocking, 40% run blocking (protect QB)
        Guards (LG/RG): 40% pass blocking, 60% run blocking (open holes)
        Center (C): 50% pass blocking, 50% run blocking (balanced)

        Args:
            candidate: Player candidate

        Returns:
            Normalized OL stat score 0-100
        """
        pos = candidate.position.upper()
        pass_block = candidate.pass_blocking_grade or 0.0
        run_block = candidate.run_blocking_grade or 0.0

        # Normalize blocking grades using benchmarks
        pass_score = self._normalize_stat(pass_block, OL_BENCHMARKS['pass_blocking_grade'])
        run_score = self._normalize_stat(run_block, OL_BENCHMARKS['run_blocking_grade'])

        # Position-specific weighting
        if pos in ('LT', 'RT'):  # Tackles: pass-heavy
            weighted = pass_score * 0.60 + run_score * 0.40
        elif pos in ('LG', 'RG'):  # Guards: run-heavy
            weighted = pass_score * 0.40 + run_score * 0.60
        elif pos == 'C':  # Center: balanced
            weighted = (pass_score + run_score) / 2
        else:  # Generic OL fallback
            weighted = (pass_score + run_score) / 2

        # If no blocking grades available, use position_grade as fallback
        if pass_block == 0.0 and run_block == 0.0:
            return self._normalize_grade(candidate.position_grade) if candidate.position_grade else 50.0

        return weighted

    def _calculate_defensive_stats(self, candidate: PlayerCandidate) -> float:
        """
        Calculate position-specific defensive stats.

        Uses canonical position groups from grading_constants to route
        to the appropriate position-specific calculator.

        Args:
            candidate: Player candidate

        Returns:
            Normalized defensive stat score 0-100
        """
        pos_group = get_position_group(candidate.position)

        if pos_group == 'DL':
            return self._calculate_dl_stats(candidate)
        elif pos_group == 'LB':
            return self._calculate_lb_stats(candidate)
        else:  # DB or unknown defensive position
            return self._calculate_db_stats(candidate)


# ============================================
# MVP Criteria
# ============================================

class MVPCriteria(BaseAwardCriteria):
    """
    MVP scoring criteria.

    Weights:
    - 40% Stats (position-specific)
    - 40% Grades (overall season grade)
    - 20% Team Success

    Position Multipliers favor QBs (1.0) over other positions.
    """

    STAT_WEIGHT = 0.40
    GRADE_WEIGHT = 0.40
    TEAM_SUCCESS_WEIGHT = 0.20

    def __init__(self):
        super().__init__(AwardType.MVP)

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate MVP score for a candidate."""
        # Calculate stat component
        stat_score = self._calculate_stat_component(candidate)

        # Calculate grade component
        grade_score = self._normalize_grade(candidate.overall_grade)

        # Calculate team success component
        team_success_score = self._calculate_team_success(candidate)

        # Calculate weighted total
        total_score = (
            stat_score * self.STAT_WEIGHT +
            grade_score * self.GRADE_WEIGHT +
            team_success_score * self.TEAM_SUCCESS_WEIGHT
        )

        # Get position multiplier
        position_mult = MVP_POSITION_MULTIPLIERS.get(
            candidate.position, DEFAULT_POSITION_MULTIPLIER
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=self.award_type,
            stat_component=stat_score,
            grade_component=grade_score,
            team_success_component=team_success_score,
            total_score=total_score,
            position_multiplier=position_mult,
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'team_wins': candidate.team_wins,
                'playoff_seed': candidate.playoff_seed,
                'is_division_winner': candidate.is_division_winner,
                'is_conference_champion': candidate.is_conference_champion,
                'stat_details': self._get_stat_breakdown(candidate),
            }
        )

    def _calculate_stat_component(self, candidate: PlayerCandidate) -> float:
        """Calculate position-specific stat component."""
        position = candidate.position

        if position == 'QB':
            return self._calculate_qb_stats(candidate)
        elif position == 'RB':
            return self._calculate_rb_stats(candidate)
        elif position in ('WR', 'TE'):
            return self._calculate_receiver_stats(candidate)
        elif candidate.position_group == 'defense':
            return self._calculate_defensive_stats(candidate)
        else:
            # Fallback for other positions
            return self._normalize_grade(candidate.position_grade)

    def _calculate_qb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate QB stat component."""
        yards_score = self._normalize_stat(
            candidate.passing_yards, QB_BENCHMARKS['passing_yards']
        )
        tds_score = self._normalize_stat(
            candidate.passing_tds, QB_BENCHMARKS['passing_tds']
        )
        rating_score = self._normalize_stat(
            candidate.passer_rating, QB_BENCHMARKS['passer_rating']
        )
        int_score = self._normalize_stat(
            candidate.passing_interceptions,
            QB_BENCHMARKS['passing_interceptions'],
            lower_is_better=True
        )

        # Weight: 30% yards, 30% TDs, 25% rating, 15% INTs
        return (
            yards_score * 0.30 +
            tds_score * 0.30 +
            rating_score * 0.25 +
            int_score * 0.15
        )

    def _calculate_rb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate RB stat component: 40% yards, 40% TDs, 20% receptions."""
        total_yards = candidate.total_yards
        total_tds = candidate.total_tds

        yards_score = self._normalize_stat(total_yards, RB_BENCHMARKS['total_yards'])
        tds_score = self._normalize_stat(total_tds, RB_BENCHMARKS['total_tds'])
        recs_score = self._normalize_stat(candidate.receptions, RB_BENCHMARKS['receptions'])

        # Weight: 40% yards, 40% TDs, 20% receptions
        return yards_score * 0.40 + tds_score * 0.40 + recs_score * 0.20

    def _calculate_receiver_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate WR/TE stat component."""
        # Route TEs to position-specific method
        if candidate.position.lower() in ('tight_end', 'te'):
            return self._calculate_te_stats(candidate)

        # WR logic continues
        benchmarks = WR_BENCHMARKS

        yards_score = self._normalize_stat(
            candidate.receiving_yards, benchmarks['receiving_yards']
        )
        tds_score = self._normalize_stat(
            candidate.receiving_tds, benchmarks['receiving_tds']
        )
        rec_score = self._normalize_stat(
            candidate.receptions, benchmarks['receptions']
        )

        # Weight: 40% yards, 35% TDs, 25% receptions
        return yards_score * 0.40 + tds_score * 0.35 + rec_score * 0.25

    def _calculate_team_success(self, candidate: PlayerCandidate) -> float:
        """Calculate team success component."""
        score = 0.0

        # Win percentage (0-50 points)
        win_pct_score = candidate.win_percentage * 50

        # Playoff seed (0-25 points)
        if candidate.playoff_seed:
            # Seed 1 = 25pts, Seed 7 = 5pts
            seed_score = max(5, 30 - (candidate.playoff_seed * 4))
        else:
            seed_score = 0

        # Division winner (15 points)
        div_winner_score = 15 if candidate.is_division_winner else 0

        # Conference champion (10 points)
        conf_champ_score = 10 if candidate.is_conference_champion else 0

        score = win_pct_score + seed_score + div_winner_score + conf_champ_score

        # Normalize to 0-100
        return min(100, score)

    def _get_stat_breakdown(self, candidate: PlayerCandidate) -> Dict[str, Any]:
        """Get detailed stat breakdown for UI/debugging."""
        return {
            'passing_yards': candidate.passing_yards,
            'passing_tds': candidate.passing_tds,
            'passer_rating': candidate.passer_rating,
            'rushing_yards': candidate.rushing_yards,
            'rushing_tds': candidate.rushing_tds,
            'receiving_yards': candidate.receiving_yards,
            'receiving_tds': candidate.receiving_tds,
            'sacks': candidate.sacks,
            'interceptions': candidate.interceptions,
            'tackles_total': candidate.tackles_total,
        }


# ============================================
# OPOY Criteria
# ============================================

class OPOYCriteria(BaseAwardCriteria):
    """
    Offensive Player of the Year scoring criteria.

    Weights:
    - 50% Stats (position-specific)
    - 50% Grades

    No team success component. Position-neutral within offense.
    """

    STAT_WEIGHT = 0.50
    GRADE_WEIGHT = 0.50

    def __init__(self):
        super().__init__(AwardType.OPOY)

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate OPOY score for a candidate."""
        # Calculate stat component
        stat_score = self._calculate_stat_component(candidate)

        # Calculate grade component
        grade_score = self._normalize_grade(candidate.overall_grade)

        # Calculate weighted total (no team success)
        total_score = (
            stat_score * self.STAT_WEIGHT +
            grade_score * self.GRADE_WEIGHT
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=self.award_type,
            stat_component=stat_score,
            grade_component=grade_score,
            team_success_component=0.0,  # No team success for OPOY
            total_score=total_score,
            position_multiplier=1.0,  # No position multiplier for OPOY
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'stat_details': self._get_stat_breakdown(candidate),
            }
        )

    def _calculate_stat_component(self, candidate: PlayerCandidate) -> float:
        """Calculate position-specific stat component."""
        position = candidate.position

        if position == 'QB':
            return self._calculate_qb_stats(candidate)
        elif position == 'RB':
            return self._calculate_rb_stats(candidate)
        elif position in ('WR', 'TE'):
            return self._calculate_receiver_stats(candidate)
        else:
            # OL or other offensive positions - use grade
            return self._normalize_grade(candidate.position_grade)

    def _calculate_qb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate QB stat component."""
        yards_score = self._normalize_stat(
            candidate.passing_yards, QB_BENCHMARKS['passing_yards']
        )
        tds_score = self._normalize_stat(
            candidate.passing_tds, QB_BENCHMARKS['passing_tds']
        )
        rating_score = self._normalize_stat(
            candidate.passer_rating, QB_BENCHMARKS['passer_rating']
        )
        int_score = self._normalize_stat(
            candidate.passing_interceptions,
            QB_BENCHMARKS['passing_interceptions'],
            lower_is_better=True
        )

        return yards_score * 0.30 + tds_score * 0.30 + rating_score * 0.25 + int_score * 0.15

    def _calculate_rb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate RB stat component: 40% yards, 40% TDs, 20% receptions."""
        yards_score = self._normalize_stat(
            candidate.total_yards, RB_BENCHMARKS['total_yards']
        )
        tds_score = self._normalize_stat(
            candidate.total_tds, RB_BENCHMARKS['total_tds']
        )
        recs_score = self._normalize_stat(
            candidate.receptions, RB_BENCHMARKS['receptions']
        )
        return yards_score * 0.40 + tds_score * 0.40 + recs_score * 0.20

    def _calculate_receiver_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate WR/TE stat component."""
        # Route TEs to position-specific method
        if candidate.position.lower() in ('tight_end', 'te'):
            return self._calculate_te_stats(candidate)

        # WR logic continues
        benchmarks = WR_BENCHMARKS

        yards_score = self._normalize_stat(
            candidate.receiving_yards, benchmarks['receiving_yards']
        )
        tds_score = self._normalize_stat(
            candidate.receiving_tds, benchmarks['receiving_tds']
        )
        rec_score = self._normalize_stat(
            candidate.receptions, benchmarks['receptions']
        )

        return yards_score * 0.40 + tds_score * 0.35 + rec_score * 0.25

    def _get_stat_breakdown(self, candidate: PlayerCandidate) -> Dict[str, Any]:
        """Get detailed stat breakdown."""
        return {
            'passing_yards': candidate.passing_yards,
            'passing_tds': candidate.passing_tds,
            'passer_rating': candidate.passer_rating,
            'rushing_yards': candidate.rushing_yards,
            'rushing_tds': candidate.rushing_tds,
            'receiving_yards': candidate.receiving_yards,
            'receiving_tds': candidate.receiving_tds,
            'receptions': candidate.receptions,
        }


# ============================================
# DPOY Criteria
# ============================================

class DPOYCriteria(BaseAwardCriteria):
    """
    Defensive Player of the Year scoring criteria.

    Weights:
    - 50% Stats (sacks, INTs, tackles, FF)
    - 50% Grades

    No team success component. Position-neutral within defense.
    """

    STAT_WEIGHT = 0.50
    GRADE_WEIGHT = 0.50

    def __init__(self):
        super().__init__(AwardType.DPOY)

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate DPOY score for a candidate."""
        # Calculate stat component
        stat_score = self._calculate_defensive_stats(candidate)

        # Calculate grade component
        grade_score = self._normalize_grade(candidate.overall_grade)

        # Calculate weighted total
        total_score = (
            stat_score * self.STAT_WEIGHT +
            grade_score * self.GRADE_WEIGHT
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=self.award_type,
            stat_component=stat_score,
            grade_component=grade_score,
            team_success_component=0.0,
            total_score=total_score,
            position_multiplier=1.0,
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'stat_details': self._get_stat_breakdown(candidate),
            }
        )

    def _get_stat_breakdown(self, candidate: PlayerCandidate) -> Dict[str, Any]:
        """Get detailed stat breakdown."""
        return {
            'sacks': candidate.sacks,
            'interceptions': candidate.interceptions,
            'tackles_total': candidate.tackles_total,
            'forced_fumbles': candidate.forced_fumbles,
        }


# ============================================
# OROY Criteria
# ============================================

class OROYCriteria(OPOYCriteria):
    """
    Offensive Rookie of the Year scoring criteria.

    Same as OPOY, but only for rookies (years_pro == 0).
    """

    def __init__(self):
        # Bypass OPOYCriteria.__init__ to set correct award type
        BaseAwardCriteria.__init__(self, AwardType.OROY)


# ============================================
# DROY Criteria
# ============================================

class DROYCriteria(DPOYCriteria):
    """
    Defensive Rookie of the Year scoring criteria.

    Same as DPOY, but only for rookies (years_pro == 0).
    """

    def __init__(self):
        # Bypass DPOYCriteria.__init__ to set correct award type
        BaseAwardCriteria.__init__(self, AwardType.DROY)


# ============================================
# CPOY Criteria
# ============================================

class CPOYCriteria(BaseAwardCriteria):
    """
    Comeback Player of the Year scoring criteria.

    Narrative-driven award:
    - 40% YoY improvement (grade delta)
    - 30% Current season grade
    - 20% Games missed previous year
    - 10% Narrative strength (combination of factors)
    """

    YOY_IMPROVEMENT_WEIGHT = 0.40
    CURRENT_GRADE_WEIGHT = 0.30
    GAMES_MISSED_WEIGHT = 0.20
    NARRATIVE_WEIGHT = 0.10

    FULL_SEASON_GAMES = 18

    def __init__(self):
        super().__init__(AwardType.CPOY)

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate CPOY score for a candidate."""
        # Calculate YoY improvement
        yoy_score = self._calculate_yoy_improvement(candidate)

        # Calculate current grade score
        current_grade_score = self._normalize_grade(candidate.overall_grade)

        # Calculate games missed score
        games_missed_score = self._calculate_games_missed(candidate)

        # Calculate narrative score
        narrative_score = self._calculate_narrative(candidate)

        # Calculate weighted total
        total_score = (
            yoy_score * self.YOY_IMPROVEMENT_WEIGHT +
            current_grade_score * self.CURRENT_GRADE_WEIGHT +
            games_missed_score * self.GAMES_MISSED_WEIGHT +
            narrative_score * self.NARRATIVE_WEIGHT
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=self.award_type,
            stat_component=yoy_score,  # Using stat_component for YoY
            grade_component=current_grade_score,
            team_success_component=games_missed_score,  # Repurposing for games missed
            total_score=total_score,
            position_multiplier=1.0,
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'previous_season_grade': candidate.previous_season_grade,
                'games_missed_previous': candidate.games_missed_previous,
                'yoy_improvement': self._get_grade_improvement(candidate),
                'narrative_score': narrative_score,
            }
        )

    def _calculate_yoy_improvement(self, candidate: PlayerCandidate) -> float:
        """Calculate year-over-year grade improvement score."""
        improvement = self._get_grade_improvement(candidate)

        # Scale: 20+ points = 100, 10 points = 80, 5 points = 60
        if improvement >= 20:
            return 100.0
        elif improvement >= 10:
            return 80.0 + 20.0 * (improvement - 10) / 10
        elif improvement >= 5:
            return 60.0 + 20.0 * (improvement - 5) / 5
        elif improvement > 0:
            return 60.0 * improvement / 5
        else:
            return 0.0

    def _get_grade_improvement(self, candidate: PlayerCandidate) -> float:
        """Get the grade improvement from previous season."""
        if candidate.previous_season_grade is None:
            return 0.0
        return candidate.overall_grade - candidate.previous_season_grade

    def _calculate_games_missed(self, candidate: PlayerCandidate) -> float:
        """Calculate games missed score (more games missed = higher comeback narrative)."""
        games_missed = candidate.games_missed_previous

        # Scale: 10+ games = 100, 6 games = 80, 4 games = 60
        if games_missed >= 10:
            return 100.0
        elif games_missed >= 6:
            return 80.0 + 20.0 * (games_missed - 6) / 4
        elif games_missed >= 4:
            return 60.0 + 20.0 * (games_missed - 4) / 2
        elif games_missed > 0:
            return 60.0 * games_missed / 4
        else:
            return 0.0

    def _calculate_narrative(self, candidate: PlayerCandidate) -> float:
        """Calculate narrative strength (combination of factors)."""
        score = 0.0

        # Bonus for significant injury comeback (missed 8+ games)
        if candidate.games_missed_previous >= 8:
            score += 40

        # Bonus for large grade improvement (15+ points)
        improvement = self._get_grade_improvement(candidate)
        if improvement >= 15:
            score += 30
        elif improvement >= 10:
            score += 20

        # Bonus for high current grade (85+)
        if candidate.overall_grade >= 85:
            score += 20
        elif candidate.overall_grade >= 80:
            score += 10

        # Bonus for team success after comeback
        if candidate.playoff_seed and candidate.playoff_seed <= 4:
            score += 10

        return min(100, score)


# ============================================
# Pro Bowl Criteria
# ============================================

class ProBowlCriteria(BaseAwardCriteria):
    """
    Pro Bowl selection criteria - stats-driven like fan voting.

    Unlike All-Pro (which emphasizes grades), Pro Bowl selection mirrors
    real NFL fan voting where big stats and name recognition matter most.

    Weights:
    - 60% Stats (position-specific production)
    - 30% Grades (overall performance quality)
    - 10% Team Success (winning team bias in voting)

    This ensures stat leaders like Saquon Barkley (1400+ yards) make the
    Pro Bowl even if their grade isn't top-tier.
    """

    STATS_WEIGHT = 0.80      # Stats are primary (fans vote on production)
    GRADE_WEIGHT = 0.15      # Grade secondary
    TEAM_SUCCESS_WEIGHT = 0.05  # Winning team bias (minor)

    def __init__(self):
        super().__init__(AwardType.MVP)  # Using MVP as placeholder

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate Pro Bowl score for a candidate."""
        # Calculate stat component (position-specific)
        stats_score = self._calculate_position_stats(candidate)

        # Calculate grade component
        grade_score = self._normalize_grade(candidate.overall_grade)

        # Calculate team success component
        team_success_score = self._calculate_team_success(candidate)

        # Calculate weighted total
        total_score = (
            stats_score * self.STATS_WEIGHT +
            grade_score * self.GRADE_WEIGHT +
            team_success_score * self.TEAM_SUCCESS_WEIGHT
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=AwardType.MVP,
            stat_component=stats_score,
            grade_component=grade_score,
            team_success_component=team_success_score,
            total_score=total_score,
            position_multiplier=1.0,
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'position_grade': candidate.position_grade,
                'team_wins': candidate.team_wins,
            }
        )

    def _calculate_position_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate position-specific stats score."""
        position = candidate.position.upper()

        if position == 'QB':
            return self._calculate_qb_stats(candidate)
        elif position == 'RB':
            return self._calculate_rb_stats(candidate)
        elif position in ('WR', 'TE'):
            return self._calculate_receiver_stats(candidate)
        elif position in ('LT', 'LG', 'C', 'RG', 'RT', 'OL'):
            return self._calculate_ol_stats(candidate)
        elif candidate.position_group == 'defense':
            return self._calculate_defensive_stats(candidate)
        else:
            # Fallback for unknown positions
            return self._normalize_grade(candidate.position_grade)

    def _calculate_qb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate QB stats for Pro Bowl."""
        yards = self._normalize_stat(candidate.passing_yards, QB_BENCHMARKS['passing_yards'])
        tds = self._normalize_stat(candidate.passing_tds, QB_BENCHMARKS['passing_tds'])
        rating = self._normalize_stat(candidate.passer_rating, QB_BENCHMARKS['passer_rating'])
        int_score = self._normalize_stat(
            candidate.passing_interceptions,
            QB_BENCHMARKS['passing_interceptions'],
            lower_is_better=True
        )
        # Weight: 35% yards, 35% TDs, 20% rating, 10% INTs
        return yards * 0.35 + tds * 0.35 + rating * 0.20 + int_score * 0.10

    def _calculate_rb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate RB stats for Pro Bowl: 45% yards, 40% TDs, 15% receptions."""
        yards = self._normalize_stat(candidate.total_yards, RB_BENCHMARKS['total_yards'])
        tds = self._normalize_stat(candidate.total_tds, RB_BENCHMARKS['total_tds'])
        recs = self._normalize_stat(candidate.receptions, RB_BENCHMARKS['receptions'])
        # Heavy weight on yards - fans love big rushing numbers
        return yards * 0.45 + tds * 0.40 + recs * 0.15

    def _calculate_receiver_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate WR/TE stats for Pro Bowl."""
        if candidate.position.lower() in ('tight_end', 'te'):
            return self._calculate_te_stats(candidate)

        benchmarks = WR_BENCHMARKS
        yards = self._normalize_stat(candidate.receiving_yards, benchmarks['receiving_yards'])
        tds = self._normalize_stat(candidate.receiving_tds, benchmarks['receiving_tds'])
        recs = self._normalize_stat(candidate.receptions, benchmarks['receptions'])
        # Fans love big yard numbers
        return yards * 0.45 + tds * 0.35 + recs * 0.20

    def _calculate_team_success(self, candidate: PlayerCandidate) -> float:
        """Calculate team success component (winning teams get more Pro Bowl votes)."""
        score = 0.0

        # Win percentage (0-60 points)
        win_pct_score = candidate.win_percentage * 60

        # Playoff team bonus (0-30 points)
        if candidate.playoff_seed:
            if candidate.playoff_seed <= 3:
                seed_score = 30
            elif candidate.playoff_seed <= 5:
                seed_score = 20
            else:
                seed_score = 10
        else:
            seed_score = 0

        # Division winner bonus (10 points)
        div_winner_score = 10 if candidate.is_division_winner else 0

        score = win_pct_score + seed_score + div_winner_score
        return min(100, score)


# ============================================
# All-Pro Criteria
# ============================================

class AllProCriteria(BaseAwardCriteria):
    """
    All-Pro selection criteria.

    Position-based rankings:
    - 50% Overall season grade
    - 30% Position-specific grade
    - 20% Stats vs position average

    Returns rankings by position with NFL-standard slot counts.
    """

    # Stats primary for All-Pro (voters judge on production)
    STATS_WEIGHT = 0.50           # Stats are primary (like Pro Bowl)
    OVERALL_GRADE_WEIGHT = 0.30   # Grade secondary
    POSITION_GRADE_WEIGHT = 0.20  # Position grade tertiary

    def __init__(self):
        super().__init__(AwardType.MVP)  # Using MVP as placeholder

    def calculate_score(self, candidate: PlayerCandidate) -> AwardScore:
        """Calculate All-Pro score for a candidate."""
        # Overall grade component
        overall_score = self._normalize_grade(candidate.overall_grade)

        # Position grade component
        position_score = self._normalize_grade(candidate.position_grade)

        # Stats component (position-specific)
        stats_score = self._calculate_position_stats(candidate)

        # Calculate weighted total
        total_score = (
            overall_score * self.OVERALL_GRADE_WEIGHT +
            position_score * self.POSITION_GRADE_WEIGHT +
            stats_score * self.STATS_WEIGHT
        )

        return AwardScore(
            player_id=candidate.player_id,
            player_name=candidate.player_name,
            team_id=candidate.team_id,
            position=candidate.position,
            award_type=AwardType.MVP,  # Using MVP as placeholder
            stat_component=stats_score,
            grade_component=overall_score,
            team_success_component=position_score,  # Repurposing for position grade
            total_score=total_score,
            position_multiplier=1.0,
            breakdown={
                'games_played': candidate.games_played,
                'overall_grade': candidate.overall_grade,
                'position_grade': candidate.position_grade,
                'position_rank': candidate.position_rank,
            }
        )

    def _calculate_position_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate position-specific stats score."""
        position = candidate.position.upper()

        if position == 'QB':
            return self._calculate_qb_stats(candidate)
        elif position == 'RB':
            return self._calculate_rb_stats(candidate)
        elif position in ('WR', 'TE'):
            return self._calculate_receiver_stats(candidate)
        elif position in ('LT', 'LG', 'C', 'RG', 'RT', 'OL'):
            return self._calculate_ol_stats(candidate)
        elif candidate.position_group == 'defense':
            return self._calculate_defensive_stats(candidate)
        else:
            # Fallback for unknown positions
            return self._normalize_grade(candidate.position_grade)

    def _calculate_qb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate QB stats for All-Pro: 35% yards, 35% TDs, 20% rating, 10% INTs."""
        yards = self._normalize_stat(candidate.passing_yards, QB_BENCHMARKS['passing_yards'])
        tds = self._normalize_stat(candidate.passing_tds, QB_BENCHMARKS['passing_tds'])
        rating = self._normalize_stat(candidate.passer_rating, QB_BENCHMARKS['passer_rating'])
        int_score = self._normalize_stat(
            candidate.passing_interceptions,
            QB_BENCHMARKS['passing_interceptions'],
            lower_is_better=True
        )
        return yards * 0.35 + tds * 0.35 + rating * 0.20 + int_score * 0.10

    def _calculate_rb_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate RB stats for All-Pro: 40% yards, 40% TDs, 20% receptions."""
        yards = self._normalize_stat(candidate.total_yards, RB_BENCHMARKS['total_yards'])
        tds = self._normalize_stat(candidate.total_tds, RB_BENCHMARKS['total_tds'])
        recs = self._normalize_stat(candidate.receptions, RB_BENCHMARKS['receptions'])
        return yards * 0.40 + tds * 0.40 + recs * 0.20

    def _calculate_receiver_stats(self, candidate: PlayerCandidate) -> float:
        """Calculate WR/TE stats for All-Pro: 45% yards, 35% TDs, 20% receptions."""
        # Route TEs to position-specific method
        if candidate.position.lower() in ('tight_end', 'te'):
            return self._calculate_te_stats(candidate)

        # WR logic - weighted like Pro Bowl (fans love big yard numbers)
        benchmarks = WR_BENCHMARKS
        yards = self._normalize_stat(candidate.receiving_yards, benchmarks['receiving_yards'])
        tds = self._normalize_stat(candidate.receiving_tds, benchmarks['receiving_tds'])
        recs = self._normalize_stat(candidate.receptions, benchmarks['receptions'])
        return yards * 0.45 + tds * 0.35 + recs * 0.20

    def select_all_pro_team(
        self,
        candidates: List[PlayerCandidate]
    ) -> Dict[str, List[AwardScore]]:
        """
        Select the All-Pro team from candidates.

        Args:
            candidates: All eligible candidates

        Returns:
            Dict mapping position to list of selected AwardScore objects
        """
        # Group candidates by position
        by_position: Dict[str, List[PlayerCandidate]] = {}
        for c in candidates:
            pos = c.position
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(c)

        # Select top players for each position
        selections: Dict[str, List[AwardScore]] = {}

        for position, position_candidates in by_position.items():
            slots = ALL_PRO_POSITION_SLOTS.get(position, 1)

            # Score and rank candidates
            scores = [self.calculate_score(c) for c in position_candidates]
            scores.sort(key=lambda s: s.total_score, reverse=True)

            # Select top N
            selections[position] = scores[:slots]

        return selections


# ============================================
# Factory Function
# ============================================

def get_criteria_for_award(award_type: AwardType) -> BaseAwardCriteria:
    """
    Get the appropriate criteria class for an award type.

    Args:
        award_type: The award type to get criteria for

    Returns:
        Appropriate criteria instance

    Raises:
        ValueError: If award type is not recognized
    """
    criteria_map = {
        AwardType.MVP: MVPCriteria,
        AwardType.OPOY: OPOYCriteria,
        AwardType.DPOY: DPOYCriteria,
        AwardType.OROY: OROYCriteria,
        AwardType.DROY: DROYCriteria,
        AwardType.CPOY: CPOYCriteria,
    }

    criteria_class = criteria_map.get(award_type)
    if criteria_class is None:
        raise ValueError(f"Unknown award type: {award_type}")

    return criteria_class()
