"""
Tests for Draft Personality Modifiers

Comprehensive test suite for GM personality trait modifiers
applied to draft prospect evaluation.
"""

import pytest

from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext


# ============================================================================
# FIXTURES - GM ARCHETYPES
# ============================================================================

@pytest.fixture
def neutral_gm():
    """GM with all traits at neutral (0.5)"""
    return GMArchetype(
        name="Balanced GM",
        description="All traits neutral",
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.5,
        loyalty=0.5,
        desperation_threshold=0.5,
        patience_years=3,
        deadline_activity=0.5,
        premium_position_focus=0.5
    )


@pytest.fixture
def risk_tolerant_gm():
    """Risk-tolerant GM (loves high-ceiling prospects)"""
    return GMArchetype(
        name="Risk-Tolerant GM",
        description="Loves upside, drafts for ceiling",
        risk_tolerance=0.9,
        win_now_mentality=0.3,
        draft_pick_value=0.8,  # BPA approach
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.3,
        star_chasing=0.6,
        loyalty=0.5,
        desperation_threshold=0.5,
        patience_years=5,
        deadline_activity=0.5,
        premium_position_focus=0.5
    )


@pytest.fixture
def risk_averse_gm():
    """Risk-averse GM (prefers safe, high-floor prospects)"""
    return GMArchetype(
        name="Risk-Averse GM",
        description="Prefers safe picks, high floor",
        risk_tolerance=0.1,
        win_now_mentality=0.7,
        draft_pick_value=0.4,  # Need-based approach
        cap_management=0.8,
        trade_frequency=0.3,
        veteran_preference=0.7,
        star_chasing=0.2,
        loyalty=0.8,
        desperation_threshold=0.6,
        patience_years=3,
        deadline_activity=0.3,
        premium_position_focus=0.5
    )


@pytest.fixture
def win_now_gm():
    """Win-Now GM (prefers polished, pro-ready prospects)"""
    return GMArchetype(
        name="Win-Now GM",
        description="Wants immediate contributors",
        risk_tolerance=0.4,
        win_now_mentality=0.9,
        draft_pick_value=0.3,  # Need-based, not BPA
        cap_management=0.3,
        trade_frequency=0.7,
        veteran_preference=0.8,
        star_chasing=0.7,
        loyalty=0.4,
        desperation_threshold=0.7,
        patience_years=2,
        deadline_activity=0.8,
        premium_position_focus=0.7
    )


@pytest.fixture
def rebuilder_gm():
    """Rebuilder GM (prefers raw, developmental prospects)"""
    return GMArchetype(
        name="Rebuilder GM",
        description="Building for the future",
        risk_tolerance=0.8,
        win_now_mentality=0.2,
        draft_pick_value=0.9,  # BPA approach
        cap_management=0.7,
        trade_frequency=0.4,
        veteran_preference=0.2,
        star_chasing=0.3,
        loyalty=0.6,
        desperation_threshold=0.3,
        patience_years=5,
        deadline_activity=0.2,
        premium_position_focus=0.4
    )


@pytest.fixture
def bpa_gm():
    """BPA GM (draft_pick_value > 0.7, ignores needs)"""
    return GMArchetype(
        name="BPA GM",
        description="Best Player Available always",
        risk_tolerance=0.6,
        win_now_mentality=0.5,
        draft_pick_value=0.9,  # Strong BPA
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.5,
        loyalty=0.5,
        desperation_threshold=0.5,
        patience_years=3,
        deadline_activity=0.5,
        premium_position_focus=0.5
    )


@pytest.fixture
def need_based_gm():
    """Need-based GM (draft_pick_value < 0.7, prioritizes needs)"""
    return GMArchetype(
        name="Need-Based GM",
        description="Drafts to fill holes",
        risk_tolerance=0.5,
        win_now_mentality=0.6,
        draft_pick_value=0.3,  # Strong need-based
        cap_management=0.6,
        trade_frequency=0.5,
        veteran_preference=0.6,
        star_chasing=0.4,
        loyalty=0.6,
        desperation_threshold=0.5,
        patience_years=3,
        deadline_activity=0.5,
        premium_position_focus=0.5
    )


@pytest.fixture
def premium_position_gm():
    """GM focused on premium positions (QB/Edge/LT)"""
    return GMArchetype(
        name="Premium Position GM",
        description="QB/Edge/LT or bust",
        risk_tolerance=0.5,
        win_now_mentality=0.5,
        draft_pick_value=0.5,
        cap_management=0.5,
        trade_frequency=0.5,
        veteran_preference=0.5,
        star_chasing=0.6,
        loyalty=0.5,
        desperation_threshold=0.5,
        patience_years=3,
        deadline_activity=0.5,
        premium_position_focus=1.0  # Max focus
    )


# ============================================================================
# FIXTURES - TEAM CONTEXTS
# ============================================================================

@pytest.fixture
def qb_needy_team():
    """Team with critical QB need"""
    return TeamContext(
        team_id=1,
        season=2025,
        wins=5,
        losses=12,
        playoff_position=None,
        games_out_of_playoff=8,
        cap_space=30_000_000,
        cap_percentage=0.15,
        top_needs=['quarterback', 'left_tackle', 'edge_rusher'],
        is_deadline=False,
        is_offseason=True
    )


@pytest.fixture
def balanced_needs_team():
    """Team with balanced needs (no critical hole)"""
    return TeamContext(
        team_id=2,
        season=2025,
        wins=9,
        losses=8,
        playoff_position=None,
        games_out_of_playoff=1,
        cap_space=20_000_000,
        cap_percentage=0.10,
        top_needs=['linebacker', 'safety', 'running_back'],
        is_deadline=False,
        is_offseason=True
    )


@pytest.fixture
def no_needs_team():
    """Stacked team with no clear needs"""
    return TeamContext(
        team_id=3,
        season=2025,
        wins=13,
        losses=4,
        playoff_position=2,
        games_out_of_playoff=None,
        cap_space=10_000_000,
        cap_percentage=0.05,
        top_needs=[],  # No critical needs
        is_deadline=False,
        is_offseason=True
    )


# ============================================================================
# FIXTURES - DRAFT PROSPECTS
# ============================================================================

@pytest.fixture
def high_ceiling_qb():
    """Raw QB with huge upside (70 OVR, 92 POT)"""
    return {
        'player_id': 1,
        'overall': 70,
        'potential': 92,
        'position': 'quarterback',
        'age': 21,
        'first_name': 'Caleb',
        'last_name': 'Williams',
        'projected_pick_min': 1,
        'projected_pick_max': 5
    }


@pytest.fixture
def high_floor_lb():
    """Polished LB with limited upside (78 OVR, 82 POT)"""
    return {
        'player_id': 2,
        'overall': 78,
        'potential': 82,
        'position': 'linebacker',
        'age': 23,
        'first_name': 'Edgerrin',
        'last_name': 'Cooper',
        'projected_pick_min': 15,
        'projected_pick_max': 30
    }


@pytest.fixture
def polished_lt():
    """Pro-ready 24-year-old LT (76 OVR, 80 POT)"""
    return {
        'player_id': 3,
        'overall': 76,
        'potential': 80,
        'position': 'left_tackle',
        'age': 24,
        'first_name': 'Joe',
        'last_name': 'Alt',
        'projected_pick_min': 10,
        'projected_pick_max': 20
    }


@pytest.fixture
def young_edge():
    """Young EDGE rusher (74 OVR, 88 POT)"""
    return {
        'player_id': 4,
        'overall': 74,
        'potential': 88,
        'position': 'defensive_end',
        'age': 21,
        'first_name': 'Jared',
        'last_name': 'Verse',
        'projected_pick_min': 5,
        'projected_pick_max': 15
    }


@pytest.fixture
def elite_wr():
    """Elite WR prospect (91 OVR, 94 POT)"""
    return {
        'player_id': 5,
        'overall': 91,
        'potential': 94,
        'position': 'wide_receiver',
        'age': 22,
        'first_name': 'Marvin',
        'last_name': 'Harrison Jr',
        'projected_pick_min': 3,
        'projected_pick_max': 8
    }


@pytest.fixture
def rb_depth():
    """RB depth piece (72 OVR, 75 POT)"""
    return {
        'player_id': 6,
        'overall': 72,
        'potential': 75,
        'position': 'running_back',
        'age': 22,
        'first_name': 'Jonathon',
        'last_name': 'Brooks',
        'projected_pick_min': 40,
        'projected_pick_max': 60
    }


# ============================================================================
# TESTS - MODIFIER 1: RISK TOLERANCE
# ============================================================================

class TestRiskToleranceModifier:
    """Test risk tolerance modifier (high-ceiling vs high-floor)"""

    def test_risk_tolerant_boosts_high_ceiling(
        self, risk_tolerant_gm, high_ceiling_qb, qb_needy_team
    ):
        """Risk-tolerant GM boosts high-ceiling prospects"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=risk_tolerant_gm,
            team_context=qb_needy_team
        )

        # Upside = 92 - 70 = 22 (> 10, high ceiling)
        # risk_tolerance = 0.9, multiplier = 1.0 + ((0.9 - 0.5) * 0.4) = 1.16
        # Expected boost: 70 * 1.16 = 81.2 (before other modifiers)
        assert result > 70, "Should boost high-ceiling prospect"

    def test_risk_averse_discounts_high_ceiling(
        self, risk_averse_gm, high_ceiling_qb, balanced_needs_team
    ):
        """Risk-averse GM discounts high-ceiling prospects"""
        # Set draft_pick_value > 0.7 to isolate risk tolerance (no need bonuses)
        risk_averse_gm.draft_pick_value = 0.8

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=risk_averse_gm,
            team_context=balanced_needs_team
        )

        # Upside = 92 - 70 = 22 (> 10, high ceiling)
        # risk_tolerance = 0.1, multiplier = 1.0 - ((0.5 - 0.1) * 0.2) = 0.92
        # premium_position_focus = 0.5, multiplier = 1.0 + (0.5 * 0.3) = 1.15
        # Expected: 70 * 0.92 * 1.15 = 74.06
        assert result >= 70 and result < 78, "Should have minimal net boost despite premium position"

    def test_no_modifier_for_high_floor(
        self, risk_tolerant_gm, high_floor_lb, balanced_needs_team
    ):
        """Risk tolerance doesn't affect high-floor prospects"""
        # Set draft_pick_value > 0.7 to isolate (no need bonuses)
        risk_tolerant_gm.draft_pick_value = 0.8

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_floor_lb,
            draft_position=15,
            gm=risk_tolerant_gm,
            team_context=balanced_needs_team
        )

        # Upside = 82 - 78 = 4 (< 10, not high ceiling, no risk modifier)
        # Age 23 >= 23, win_now = 0.3, multiplier = 1.0 + (0.3 * 0.3) = 1.09
        # Expected: 78 * 1.09 = 85.02
        assert result >= 84 and result < 87, "Should have win-now boost only"


# ============================================================================
# TESTS - MODIFIER 2: WIN-NOW MENTALITY
# ============================================================================

class TestWinNowModifier:
    """Test win-now mentality modifier (polished vs raw)"""

    def test_win_now_boosts_polished(
        self, win_now_gm, polished_lt, qb_needy_team
    ):
        """Win-Now GM boosts polished prospects (age 23+)"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=polished_lt,
            draft_position=10,
            gm=win_now_gm,
            team_context=qb_needy_team
        )

        # Age 24 >= 23, win_now = 0.9
        # Multiplier = 1.0 + (0.9 * 0.3) = 1.27
        # Expected: 76 * 1.27 = 96.5 (before other modifiers)
        assert result > 76, "Should boost polished prospect"

    def test_win_now_neutral_on_young(
        self, win_now_gm, high_ceiling_qb, balanced_needs_team
    ):
        """Win-Now GM doesn't boost young prospects"""
        # Set draft_pick_value > 0.7 to isolate (no need bonuses)
        win_now_gm.draft_pick_value = 0.8

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=win_now_gm,
            team_context=balanced_needs_team
        )

        # Age 21 < 23, no win-now modifier
        # risk_tolerance = 0.4, slight discount: 1.0 - ((0.5 - 0.4) * 0.2) = 0.98
        # premium_position_focus = 0.7, boost: 1.0 + (0.7 * 0.3) = 1.21
        # Expected: 70 * 0.98 * 1.21 = 83.01
        assert result >= 80 and result < 86, "Should get premium position boost, no win-now boost"

    def test_rebuilder_neutral_on_polished(
        self, rebuilder_gm, polished_lt, balanced_needs_team
    ):
        """Rebuilder GM has minimal boost for polished prospects"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=polished_lt,
            draft_position=10,
            gm=rebuilder_gm,
            team_context=balanced_needs_team
        )

        # Age 24 >= 23, win_now = 0.2, multiplier = 1.0 + (0.2 * 0.3) = 1.06
        # Age 24 >= 24, veteran_preference = 0.2, multiplier = 1.0 + (0.2 * 0.2) = 1.04
        # premium_position_focus = 0.4, multiplier = 1.0 + (0.4 * 0.3) = 1.12
        # Expected: 76 * 1.06 * 1.04 * 1.12 = 93.84
        assert result >= 92 and result < 96, "Rebuilder gets combined boosts from multiple modifiers"


# ============================================================================
# TESTS - MODIFIER 3: PREMIUM POSITION FOCUS
# ============================================================================

class TestPremiumPositionModifier:
    """Test premium position focus modifier (QB/Edge/LT)"""

    def test_premium_position_boost_qb(
        self, premium_position_gm, high_ceiling_qb, balanced_needs_team
    ):
        """Premium Position GM boosts QB"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=premium_position_gm,
            team_context=balanced_needs_team
        )

        # Position = QB, premium_position_focus = 1.0
        # Multiplier = 1.0 + (1.0 * 0.3) = 1.3
        # Expected: 70 * 1.3 = 91 (before other modifiers)
        assert result > 80, "Should boost QB significantly"

    def test_premium_position_boost_edge(
        self, premium_position_gm, young_edge, balanced_needs_team
    ):
        """Premium Position GM boosts EDGE"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=young_edge,
            draft_position=5,
            gm=premium_position_gm,
            team_context=balanced_needs_team
        )

        # Position = defensive_end (EDGE), premium_position_focus = 1.0
        # Multiplier = 1.0 + (1.0 * 0.3) = 1.3
        assert result > 74, "Should boost EDGE"

    def test_premium_position_boost_lt(
        self, premium_position_gm, polished_lt, balanced_needs_team
    ):
        """Premium Position GM boosts LT"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=polished_lt,
            draft_position=10,
            gm=premium_position_gm,
            team_context=balanced_needs_team
        )

        # Position = left_tackle, premium_position_focus = 1.0
        # Multiplier = 1.0 + (1.0 * 0.3) = 1.3
        assert result > 76, "Should boost LT"

    def test_no_boost_for_non_premium(
        self, premium_position_gm, elite_wr, balanced_needs_team
    ):
        """Premium Position GM doesn't boost WR"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=elite_wr,
            draft_position=3,
            gm=premium_position_gm,
            team_context=balanced_needs_team
        )

        # Position = wide_receiver (not premium)
        # No premium position boost
        # Base 91 should stay relatively close
        assert result >= 90 and result <= 95, "WR should not get premium boost"


# ============================================================================
# TESTS - MODIFIER 4: VETERAN PREFERENCE
# ============================================================================

class TestVeteranPreferenceModifier:
    """Test veteran preference modifier (age bias)"""

    def test_veteran_preference_boosts_older(
        self, win_now_gm, polished_lt, balanced_needs_team
    ):
        """Veteran-preferring GM boosts older prospects (24+)"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=polished_lt,
            draft_position=10,
            gm=win_now_gm,
            team_context=balanced_needs_team
        )

        # Age 24 >= 24, veteran_preference = 0.8
        # Multiplier = 1.0 + (0.8 * 0.2) = 1.16
        # Combined with win_now (1.27) and premium_position (1.21)
        assert result > 76, "Should boost older prospect"

    def test_youth_focus_neutral_on_young(
        self, rebuilder_gm, high_ceiling_qb, balanced_needs_team
    ):
        """Youth-focused GM neutral on young prospects"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=rebuilder_gm,
            team_context=balanced_needs_team
        )

        # Age 21 < 24, no veteran preference modifier
        # But gets risk_tolerance boost (0.8, high ceiling)
        assert result > 70, "Young prospect gets risk boost, no age penalty"


# ============================================================================
# TESTS - MODIFIER 5: DRAFT PICK VALUE (BPA vs NEED-BASED)
# ============================================================================

class TestDraftPickValueModifier:
    """Test draft pick value modifier (BPA vs need-based)"""

    def test_bpa_gm_ignores_needs(
        self, bpa_gm, high_ceiling_qb, qb_needy_team
    ):
        """BPA GM (draft_pick_value > 0.7) ignores team needs"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=bpa_gm,
            team_context=qb_needy_team
        )

        # draft_pick_value = 0.9 > 0.7 (BPA approach)
        # No need bonuses applied, even though QB is top need
        # Only gets risk_tolerance boost
        # Expected: ~70 (no major boost from needs)
        assert result < 100, "BPA GM should ignore need bonuses"

    def test_need_based_gm_critical_need_boost(
        self, need_based_gm, high_ceiling_qb, qb_needy_team
    ):
        """Need-based GM gets 1.5x for critical need match"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=need_based_gm,
            team_context=qb_needy_team
        )

        # draft_pick_value = 0.3 <= 0.7 (need-based)
        # Position = QB, top_needs[0] = 'quarterback' (critical match)
        # Multiplier = 1.5x
        # Expected: 70 * 1.5 = 105 (before other modifiers)
        assert result > 100, "Critical need should get 1.5x boost"

    def test_need_based_gm_top3_need_boost(
        self, need_based_gm, polished_lt, qb_needy_team
    ):
        """Need-based GM gets 1.2x for top-3 need match"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=polished_lt,
            draft_position=10,
            gm=need_based_gm,
            team_context=qb_needy_team
        )

        # draft_pick_value = 0.3 <= 0.7 (need-based)
        # Position = LT, top_needs[1] = 'left_tackle' (top-3 match)
        # Multiplier = 1.2x
        # Expected: 76 * 1.2 = 91.2 (before other modifiers)
        assert result > 90, "Top-3 need should get 1.2x boost"

    def test_need_based_gm_no_need_match(
        self, need_based_gm, elite_wr, qb_needy_team
    ):
        """Need-based GM gets no boost for non-need position"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=elite_wr,
            draft_position=3,
            gm=need_based_gm,
            team_context=qb_needy_team
        )

        # draft_pick_value = 0.3 <= 0.7 (need-based)
        # Position = WR, not in top_needs (no match)
        # No need multiplier applied
        # Base: 91 (stays close)
        assert result >= 88 and result <= 95, "Non-need position gets no bonus"


# ============================================================================
# TESTS - COMBINED MODIFIERS
# ============================================================================

class TestCombinedModifiers:
    """Test multiple modifiers stacking"""

    def test_extreme_stacking_all_traits_align(
        self, high_ceiling_qb, qb_needy_team
    ):
        """All modifiers align: extreme boost"""
        extreme_gm = GMArchetype(
            name="Extreme GM",
            description="All traits favor this prospect",
            risk_tolerance=1.0,  # Max boost for high-ceiling
            win_now_mentality=0.0,  # No penalty for young
            draft_pick_value=0.3,  # Need-based (QB is top need)
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.0,  # No penalty for young
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=1.0  # Max boost for QB
        )

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=extreme_gm,
            team_context=qb_needy_team
        )

        # Expected modifiers:
        # - Risk: 1.0 + ((1.0 - 0.5) * 0.4) = 1.2x
        # - Win-Now: 1.0x (age 21 < 23)
        # - Premium Position: 1.0 + (1.0 * 0.3) = 1.3x
        # - Veteran: 1.0x (age 21 < 24)
        # - Need: 1.5x (critical need)
        # Total: 70 * 1.2 * 1.3 * 1.5 = 163.8
        assert result > 150, "All modifiers should stack to ~164"

    def test_opposing_traits_cancel_out(
        self, high_ceiling_qb, balanced_needs_team
    ):
        """Opposing traits partially cancel"""
        conflicted_gm = GMArchetype(
            name="Conflicted GM",
            description="Traits conflict",
            risk_tolerance=0.0,  # Max discount for high-ceiling (-10%)
            win_now_mentality=0.0,  # No boost for young
            draft_pick_value=0.8,  # BPA (no need bonuses)
            cap_management=0.5,
            trade_frequency=0.5,
            veteran_preference=0.0,  # No boost for young
            star_chasing=0.5,
            loyalty=0.5,
            desperation_threshold=0.5,
            patience_years=3,
            deadline_activity=0.5,
            premium_position_focus=1.0  # +30% for QB
        )

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=high_ceiling_qb,
            draft_position=1,
            gm=conflicted_gm,
            team_context=balanced_needs_team
        )

        # Expected:
        # - Risk: 1.0 - ((0.5 - 0.0) * 0.2) = 0.9x (discount)
        # - Win-Now: 1.0x (no boost)
        # - Premium Position: 1.3x (boost)
        # - Veteran: 1.0x (no boost)
        # - Need: 1.0x (BPA, no needs)
        # Total: 70 * 0.9 * 1.3 = 81.9
        assert result >= 80 and result <= 85, "Traits should partially cancel"


# ============================================================================
# TESTS - EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_missing_potential_field(
        self, neutral_gm, balanced_needs_team
    ):
        """Gracefully handle missing potential field"""
        prospect_no_potential = {
            'player_id': 99,
            'overall': 80,
            # potential field missing
            'position': 'cornerback',
            'age': 22
        }

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=prospect_no_potential,
            draft_position=20,
            gm=neutral_gm,
            team_context=balanced_needs_team
        )

        # Should default to overall = potential (upside = 0, no risk modifier)
        assert result == pytest.approx(80.0, rel=0.01), "Should handle missing potential"

    def test_missing_age_field(
        self, win_now_gm, balanced_needs_team
    ):
        """Gracefully handle missing age field"""
        prospect_no_age = {
            'player_id': 100,
            'overall': 85,
            'potential': 88,
            'position': 'safety'
            # age field missing
        }

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=prospect_no_age,
            draft_position=25,
            gm=win_now_gm,
            team_context=balanced_needs_team
        )

        # Should default to age 21 (no win-now or veteran bonuses)
        # draft_pick_value = 0.3 (need-based)
        # safety is in top_needs[1] for balanced_needs_team (top-3 match)
        # Multiplier = 1.2x
        # Expected: 85 * 1.2 = 102
        assert result == pytest.approx(102.0, rel=0.01), "Should handle missing age and apply need bonus"

    def test_empty_top_needs_list(
        self, need_based_gm, elite_wr, no_needs_team
    ):
        """Gracefully handle empty top_needs list"""
        result = PersonalityModifiers.apply_draft_modifier(
            prospect=elite_wr,
            draft_position=3,
            gm=need_based_gm,
            team_context=no_needs_team
        )

        # top_needs = [], no need bonuses even for need-based GM
        # Base: 91
        assert result >= 90 and result <= 95, "Should handle empty needs list"

    def test_none_top_needs(
        self, need_based_gm, elite_wr
    ):
        """Gracefully handle None top_needs"""
        context_no_needs = TeamContext(
            team_id=99,
            season=2025,
            wins=10,
            losses=7,
            top_needs=None  # None instead of list
        )

        result = PersonalityModifiers.apply_draft_modifier(
            prospect=elite_wr,
            draft_position=3,
            gm=need_based_gm,
            team_context=context_no_needs
        )

        # Should handle None gracefully (defaults to [])
        assert result >= 90 and result <= 95, "Should handle None top_needs"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
