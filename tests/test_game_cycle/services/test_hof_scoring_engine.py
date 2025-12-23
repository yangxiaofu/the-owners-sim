"""
Unit tests for HOFScoringEngine.

Tests scoring calculations, tier classification, stats tiers,
and breakdown serialization.
"""

import pytest
from game_cycle.services.hof_scoring_engine import (
    HOFScoringEngine,
    HOFScoreBreakdown,
    HOFTier,
    HOF_STATS_THRESHOLDS,
    POSITION_TO_GROUP,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def engine():
    """Create HOFScoringEngine instance."""
    return HOFScoringEngine()


# ============================================
# Test Calculate Score - Career Profiles
# ============================================

class TestCalculateScore:
    """Test calculate_score() with various career profiles."""

    def test_first_ballot_lock(self, engine):
        """Elite career (2 MVPs, 2 rings, 5 All-Pro 1st) = 85+ score."""
        breakdown = engine.calculate_score(
            mvp_awards=2,
            super_bowl_wins=2,
            all_pro_first=5,
            all_pro_second=0,
            pro_bowls=10,
            career_seasons=15,
            position='QB',
            career_stats={'pass_yards': 50000, 'pass_tds': 400}
        )

        # 2 MVP = 50 + 2 SB = 30 + 5 AP1 = 40 + 10 PB = 20 + elite stats = 20 + longevity = 10
        # Total would be 170, capped at 100
        assert breakdown.total_score == 100
        assert breakdown.tier == HOFTier.FIRST_BALLOT

    def test_strong_candidate(self, engine):
        """Good career (1 ring, 3 All-Pro, 8 Pro Bowls) = 70-84."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=1,
            all_pro_first=3,
            all_pro_second=2,
            pro_bowls=8,
            career_seasons=12,
            position='WR',
            career_stats={'rec_yards': 11000, 'rec_tds': 70, 'receptions': 800}
        )

        # 0 MVP + 1 SB = 15 + 3 AP1 = 24 + 2 AP2 = 8 + 8 PB = 16 + great stats = 15 + longevity = 5
        # Total = 83
        assert 70 <= breakdown.total_score <= 84
        assert breakdown.tier == HOFTier.STRONG

    def test_borderline_candidate(self, engine):
        """Solid career (1 SB, 3 All-Pro 1st, 6 Pro Bowls) = 55-69."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=1,   # 15 points
            all_pro_first=2,     # 16 points
            all_pro_second=1,    # 4 points
            pro_bowls=6,         # 12 points
            career_seasons=11,   # 5 points (longevity)
            position='RB',
            career_stats={'rush_yards': 7500, 'rush_tds': 45}  # good = 10 points
        )

        # Total = 15 + 16 + 4 + 12 + 5 + 10 = 62
        assert 55 <= breakdown.total_score <= 69
        assert breakdown.tier == HOFTier.BORDERLINE

    def test_long_shot_candidate(self, engine):
        """Decent career (1 All-Pro 1st, 2 All-Pro 2nd, 5 Pro Bowls) = 40-54."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=1,     # 8 points
            all_pro_second=2,    # 8 points
            pro_bowls=5,         # 10 points
            career_seasons=12,   # 5 points (longevity)
            position='CB',
            career_stats={'interceptions': 35}  # good = 10 points
        )

        # Total = 8 + 8 + 10 + 5 + 10 = 41
        assert 40 <= breakdown.total_score <= 54
        assert breakdown.tier == HOFTier.LONG_SHOT

    def test_not_hof_caliber(self, engine):
        """Average career = <40."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=1,
            career_seasons=8,
            position='TE',
            career_stats={'rec_yards': 4000, 'rec_tds': 25}
        )

        # 0 + 0 + 0 + 0 + 1 PB = 2 + good stats = 10 + no longevity = 0
        # Total = 12
        assert breakdown.total_score < 40
        assert breakdown.tier == HOFTier.NOT_HOF

    def test_mvp_capped_at_50(self, engine):
        """3 MVPs = 50 points (not 75)."""
        breakdown = engine.calculate_score(
            mvp_awards=3,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=5,
            position='QB',
            career_stats={}
        )

        assert breakdown.mvp_score == 50
        assert breakdown.mvp_count == 3

    def test_super_bowl_capped_at_30(self, engine):
        """4 rings = 30 points (not 60)."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=4,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=5,
            position='QB',
            career_stats={}
        )

        assert breakdown.super_bowl_score == 30
        assert breakdown.super_bowl_count == 4

    def test_pro_bowl_capped_at_20(self, engine):
        """15 Pro Bowls = 20 points (not 30)."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=15,
            career_seasons=15,
            position='QB',
            career_stats={}
        )

        assert breakdown.pro_bowl_score == 20
        assert breakdown.pro_bowl_count == 15

    def test_total_capped_at_100(self, engine):
        """Even extreme career caps at 100."""
        breakdown = engine.calculate_score(
            mvp_awards=5,        # 50 (capped)
            super_bowl_wins=5,  # 30 (capped)
            all_pro_first=10,   # 80
            all_pro_second=5,   # 20
            pro_bowls=15,       # 20 (capped)
            career_seasons=20,  # 10
            position='QB',
            career_stats={'pass_yards': 80000, 'pass_tds': 600}  # 20
        )

        # Raw total would be: 50 + 30 + 80 + 20 + 20 + 10 + 20 = 230
        assert breakdown.total_score == 100

    def test_all_pro_uncapped(self, engine):
        """All-Pro selections have no cap."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=10,   # 80 points
            all_pro_second=5,   # 20 points
            pro_bowls=0,
            career_seasons=5,
            position='QB',
            career_stats={}
        )

        assert breakdown.all_pro_first_score == 80
        assert breakdown.all_pro_second_score == 20


# ============================================
# Test Tier Classification
# ============================================

class TestTierClassification:
    """Test tier determination based on total score."""

    def test_first_ballot_tier_at_85(self, engine):
        """Score 85 = FIRST_BALLOT."""
        tier = engine._determine_tier(85)
        assert tier == HOFTier.FIRST_BALLOT

    def test_first_ballot_tier_at_100(self, engine):
        """Score 100 = FIRST_BALLOT."""
        tier = engine._determine_tier(100)
        assert tier == HOFTier.FIRST_BALLOT

    def test_strong_tier_at_70(self, engine):
        """Score 70 = STRONG."""
        tier = engine._determine_tier(70)
        assert tier == HOFTier.STRONG

    def test_strong_tier_at_84(self, engine):
        """Score 84 = STRONG."""
        tier = engine._determine_tier(84)
        assert tier == HOFTier.STRONG

    def test_borderline_tier_at_55(self, engine):
        """Score 55 = BORDERLINE."""
        tier = engine._determine_tier(55)
        assert tier == HOFTier.BORDERLINE

    def test_borderline_tier_at_69(self, engine):
        """Score 69 = BORDERLINE."""
        tier = engine._determine_tier(69)
        assert tier == HOFTier.BORDERLINE

    def test_long_shot_tier_at_40(self, engine):
        """Score 40 = LONG_SHOT."""
        tier = engine._determine_tier(40)
        assert tier == HOFTier.LONG_SHOT

    def test_long_shot_tier_at_54(self, engine):
        """Score 54 = LONG_SHOT."""
        tier = engine._determine_tier(54)
        assert tier == HOFTier.LONG_SHOT

    def test_not_hof_tier_at_39(self, engine):
        """Score 39 = NOT_HOF."""
        tier = engine._determine_tier(39)
        assert tier == HOFTier.NOT_HOF

    def test_not_hof_tier_at_0(self, engine):
        """Score 0 = NOT_HOF."""
        tier = engine._determine_tier(0)
        assert tier == HOFTier.NOT_HOF


# ============================================
# Test Stats Tier Calculation
# ============================================

class TestStatsTier:
    """Test position-specific stats tier calculations."""

    def test_qb_elite_stats(self, engine):
        """QB with 45000 yards = elite tier."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': 45000, 'pass_tds': 350})
        assert tier == 'elite'

    def test_qb_great_stats(self, engine):
        """QB with 35000 yards = great tier."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': 35000, 'pass_tds': 250})
        assert tier == 'great'

    def test_qb_good_stats(self, engine):
        """QB with 25000 yards = good tier."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': 25000, 'pass_tds': 175})
        assert tier == 'good'

    def test_qb_solid_stats(self, engine):
        """QB with 17000 yards = solid tier."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': 17000, 'pass_tds': 120})
        assert tier == 'solid'

    def test_rb_elite_stats(self, engine):
        """RB with 12000 yards = elite tier."""
        tier = engine._calculate_stats_tier('RB', {'rush_yards': 12000, 'rush_tds': 100})
        assert tier == 'elite'

    def test_rb_great_stats(self, engine):
        """RB with 9000 yards = great tier."""
        tier = engine._calculate_stats_tier('RB', {'rush_yards': 9000, 'rush_tds': 60})
        assert tier == 'great'

    def test_wr_elite_stats(self, engine):
        """WR with 14000 yards = elite tier."""
        tier = engine._calculate_stats_tier('WR', {'rec_yards': 14000, 'rec_tds': 90, 'receptions': 1000})
        assert tier == 'elite'

    def test_wr_good_stats(self, engine):
        """WR with 8500 yards = good tier."""
        tier = engine._calculate_stats_tier('WR', {'rec_yards': 8500, 'rec_tds': 50, 'receptions': 600})
        assert tier == 'good'

    def test_edge_elite_sacks(self, engine):
        """EDGE with 120 sacks = elite tier."""
        tier = engine._calculate_stats_tier('EDGE', {'sacks': 120})
        assert tier == 'elite'

    def test_lb_great_tackles(self, engine):
        """LB with 1100 tackles = great tier."""
        tier = engine._calculate_stats_tier('MLB', {'tackles': 1100, 'sacks': 25})
        assert tier == 'great'

    def test_cb_elite_interceptions(self, engine):
        """CB with 55 interceptions = elite tier."""
        tier = engine._calculate_stats_tier('CB', {'interceptions': 55})
        assert tier == 'elite'

    def test_safety_good_stats(self, engine):
        """Safety with 25 INTs = good tier."""
        tier = engine._calculate_stats_tier('FS', {'interceptions': 25, 'tackles': 500})
        assert tier == 'good'

    def test_kicker_great_fg(self, engine):
        """Kicker with 350 FG = great tier."""
        tier = engine._calculate_stats_tier('K', {'fg_made': 350})
        assert tier == 'great'

    def test_no_stats_empty_tier(self, engine):
        """Position with no relevant stats = empty tier."""
        tier = engine._calculate_stats_tier('QB', {})
        assert tier == ''

    def test_unknown_position_empty_tier(self, engine):
        """Unknown position = empty tier."""
        tier = engine._calculate_stats_tier('XYZ', {'pass_yards': 50000})
        assert tier == ''

    def test_best_tier_across_multiple_stats(self, engine):
        """Best tier from any stat is used (elite TDs trumps great yards)."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': 35000, 'pass_tds': 350})
        # 35000 yards = great, 350 TDs = elite -> should return elite
        assert tier == 'elite'


# ============================================
# Test Position Group Mapping
# ============================================

class TestPositionGroupMapping:
    """Test position abbreviation to group mapping."""

    def test_qb_maps_to_qb(self, engine):
        """QB maps to QB group."""
        assert engine._get_position_group('QB') == 'QB'

    def test_halfback_maps_to_rb(self, engine):
        """HB maps to RB group."""
        assert engine._get_position_group('HB') == 'RB'

    def test_fullback_maps_to_rb(self, engine):
        """FB maps to RB group."""
        assert engine._get_position_group('FB') == 'RB'

    def test_defensive_end_maps_to_edge(self, engine):
        """DE maps to EDGE group."""
        assert engine._get_position_group('DE') == 'EDGE'

    def test_left_end_maps_to_edge(self, engine):
        """LE maps to EDGE group."""
        assert engine._get_position_group('LE') == 'EDGE'

    def test_defensive_tackle_maps_to_dl(self, engine):
        """DT maps to DL group."""
        assert engine._get_position_group('DT') == 'DL'

    def test_linebacker_variants(self, engine):
        """All LB variants map to LB group."""
        assert engine._get_position_group('MLB') == 'LB'
        assert engine._get_position_group('LOLB') == 'LB'
        assert engine._get_position_group('ROLB') == 'LB'
        assert engine._get_position_group('ILB') == 'LB'
        assert engine._get_position_group('OLB') == 'LB'

    def test_safety_variants(self, engine):
        """FS and SS map to S group."""
        assert engine._get_position_group('FS') == 'S'
        assert engine._get_position_group('SS') == 'S'

    def test_offensive_line_maps_to_ol(self, engine):
        """O-line positions map to OL group."""
        assert engine._get_position_group('LT') == 'OL'
        assert engine._get_position_group('C') == 'OL'
        assert engine._get_position_group('RG') == 'OL'

    def test_case_insensitive(self, engine):
        """Position lookup is case-insensitive."""
        assert engine._get_position_group('qb') == 'QB'
        assert engine._get_position_group('Qb') == 'QB'


# ============================================
# Test Longevity Bonus
# ============================================

class TestLongevityBonus:
    """Test longevity bonus calculation."""

    def test_longevity_15_plus_seasons(self, engine):
        """15+ seasons = 10 points."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=15,
            position='QB',
            career_stats={}
        )
        assert breakdown.longevity_score == 10
        assert breakdown.career_seasons == 15

    def test_longevity_10_to_14_seasons(self, engine):
        """10-14 seasons = 5 points."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=12,
            position='QB',
            career_stats={}
        )
        assert breakdown.longevity_score == 5

    def test_longevity_under_10_seasons(self, engine):
        """<10 seasons = 0 points."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=9,
            position='QB',
            career_stats={}
        )
        assert breakdown.longevity_score == 0


# ============================================
# Test Breakdown Serialization
# ============================================

class TestBreakdown:
    """Test HOFScoreBreakdown serialization and structure."""

    def test_breakdown_serialization(self, engine):
        """to_dict() produces valid JSON-serializable dict."""
        breakdown = engine.calculate_score(
            mvp_awards=1,
            super_bowl_wins=1,
            all_pro_first=2,
            all_pro_second=1,
            pro_bowls=5,
            career_seasons=12,
            position='QB',
            career_stats={'pass_yards': 40000, 'pass_tds': 300}
        )

        result = breakdown.to_dict()

        # Verify all expected keys present
        expected_keys = {
            'total_score', 'tier',
            'mvp_score', 'super_bowl_score',
            'all_pro_first_score', 'all_pro_second_score',
            'pro_bowl_score', 'stats_score', 'longevity_score',
            'mvp_count', 'super_bowl_count',
            'all_pro_first_count', 'all_pro_second_count',
            'pro_bowl_count', 'career_seasons', 'stats_tier'
        }
        assert set(result.keys()) == expected_keys

        # Verify tier is serialized as string
        assert isinstance(result['tier'], str)
        assert result['tier'] in ('FIRST_BALLOT', 'STRONG', 'BORDERLINE', 'LONG_SHOT', 'NOT_HOF')

    def test_breakdown_components_sum(self, engine):
        """Individual scores sum correctly (before cap)."""
        breakdown = engine.calculate_score(
            mvp_awards=1,       # 25
            super_bowl_wins=1,  # 15
            all_pro_first=2,    # 16
            all_pro_second=1,   # 4
            pro_bowls=5,        # 10
            career_seasons=12,  # 5
            position='QB',
            career_stats={'pass_yards': 40000, 'pass_tds': 300}  # elite = 20
        )

        # Individual components
        component_sum = (
            breakdown.mvp_score +
            breakdown.super_bowl_score +
            breakdown.all_pro_first_score +
            breakdown.all_pro_second_score +
            breakdown.pro_bowl_score +
            breakdown.stats_score +
            breakdown.longevity_score
        )

        # For this profile: 25 + 15 + 16 + 4 + 10 + 20 + 5 = 95
        assert component_sum == 95
        assert breakdown.total_score == 95  # Under cap

    def test_breakdown_counts_match_inputs(self, engine):
        """Count fields match input values."""
        breakdown = engine.calculate_score(
            mvp_awards=2,
            super_bowl_wins=3,
            all_pro_first=4,
            all_pro_second=5,
            pro_bowls=8,
            career_seasons=14,
            position='RB',
            career_stats={'rush_yards': 9000}
        )

        assert breakdown.mvp_count == 2
        assert breakdown.super_bowl_count == 3
        assert breakdown.all_pro_first_count == 4
        assert breakdown.all_pro_second_count == 5
        assert breakdown.pro_bowl_count == 8
        assert breakdown.career_seasons == 14


# ============================================
# Test Calculate From Candidate
# ============================================

class TestCalculateFromCandidate:
    """Test calculate_from_candidate() convenience method."""

    def test_calculate_from_candidate(self, engine):
        """calculate_from_candidate() works with HOFCandidate-like object."""
        # Create a mock candidate object with required attributes
        class MockCandidate:
            mvp_awards = 1
            super_bowl_wins = 2
            all_pro_first_team = 3
            all_pro_second_team = 1
            pro_bowl_selections = 7
            career_seasons = 13
            primary_position = 'QB'
            career_stats = {'pass_yards': 35000, 'pass_tds': 250}

        candidate = MockCandidate()
        breakdown = engine.calculate_from_candidate(candidate)

        # Verify it calculated correctly
        assert breakdown.mvp_count == 1
        assert breakdown.super_bowl_count == 2
        assert breakdown.all_pro_first_count == 3
        assert breakdown.all_pro_second_count == 1
        assert breakdown.pro_bowl_count == 7
        assert breakdown.career_seasons == 13
        assert breakdown.stats_tier == 'great'


# ============================================
# Test Edge Cases
# ============================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_everything(self, engine):
        """All zeros produces zero score."""
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=0,
            position='QB',
            career_stats={}
        )

        assert breakdown.total_score == 0
        assert breakdown.tier == HOFTier.NOT_HOF

    def test_none_in_career_stats(self, engine):
        """None values in career_stats handled gracefully."""
        tier = engine._calculate_stats_tier('QB', {'pass_yards': None, 'pass_tds': 200})
        # pass_yards = None treated as 0, pass_tds = 200 = great
        assert tier == 'great'

    def test_negative_values_treated_as_zero(self, engine):
        """Negative stat values don't break calculation."""
        # This is an edge case - negative values shouldn't happen but shouldn't crash
        breakdown = engine.calculate_score(
            mvp_awards=0,
            super_bowl_wins=0,
            all_pro_first=0,
            all_pro_second=0,
            pro_bowls=0,
            career_seasons=5,
            position='QB',
            career_stats={'pass_yards': -1000}  # Invalid but shouldn't crash
        )

        # Should complete without error
        assert breakdown.stats_tier == ''  # No tier for negative stats
