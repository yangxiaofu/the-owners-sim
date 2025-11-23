"""
Tests for Trade Personality Modifiers

Comprehensive test suite for GM personality trait modifiers
and trade decision-making logic.
"""

import pytest

from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext
from transactions.models import TradeAsset, AssetType, DraftPick


# ============================================================================
# FIXTURES
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
def conservative_gm():
    """Conservative GM archetype"""
    return GMArchetype(
        name="Conservative GM",
        description="Risk-averse, values cap space and draft picks",
        risk_tolerance=0.2,
        win_now_mentality=0.3,
        draft_pick_value=0.8,
        cap_management=0.9,
        trade_frequency=0.3,
        veteran_preference=0.7,
        star_chasing=0.2,
        loyalty=0.8,
        desperation_threshold=0.6,
        patience_years=5,
        deadline_activity=0.2,
        premium_position_focus=0.5
    )


@pytest.fixture
def aggressive_gm():
    """Aggressive GM archetype"""
    return GMArchetype(
        name="Aggressive GM",
        description="Win-now, star chasing, cap aggressive",
        risk_tolerance=0.8,
        win_now_mentality=0.9,
        draft_pick_value=0.3,
        cap_management=0.2,
        trade_frequency=0.9,
        veteran_preference=0.8,
        star_chasing=0.9,
        loyalty=0.3,
        desperation_threshold=0.7,
        patience_years=2,
        deadline_activity=0.9,
        premium_position_focus=0.8
    )


@pytest.fixture
def rebuilding_context():
    """Team in rebuild mode"""
    return TeamContext(
        team_id=1,
        season=2025,
        wins=3,
        losses=14,
        playoff_position=None,
        games_out_of_playoff=8,
        cap_space=50_000_000,
        cap_percentage=0.25,
        top_needs=['quarterback', 'edge_rusher', 'cornerback'],
        is_deadline=False,
        is_offseason=False
    )


@pytest.fixture
def contender_context():
    """Team in playoff contention"""
    return TeamContext(
        team_id=2,
        season=2025,
        wins=11,
        losses=3,
        playoff_position=2,
        games_out_of_playoff=None,
        cap_space=5_000_000,
        cap_percentage=0.025,
        top_needs=['left_tackle', 'linebacker'],
        is_deadline=False,
        is_offseason=False
    )


@pytest.fixture
def deadline_contender_context():
    """Contender at trade deadline"""
    return TeamContext(
        team_id=3,
        season=2025,
        wins=8,
        losses=5,
        playoff_position=7,  # Last wildcard spot
        games_out_of_playoff=None,
        cap_space=10_000_000,
        cap_percentage=0.05,
        top_needs=['wide_receiver'],
        is_deadline=True,
        is_offseason=False
    )


@pytest.fixture
def young_rb():
    """Young running back asset"""
    return TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=1001,
        player_name="Young RB",
        position="running_back",
        overall_rating=78,
        age=23,
        years_pro=2,
        contract_years_remaining=2,
        annual_cap_hit=2_500_000,
        trade_value=100.0
    )


@pytest.fixture
def elite_qb():
    """Elite veteran quarterback"""
    return TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=1002,
        player_name="Elite QB",
        position="quarterback",
        overall_rating=95,
        age=29,
        years_pro=7,
        contract_years_remaining=3,
        annual_cap_hit=45_000_000,
        trade_value=700.0
    )


@pytest.fixture
def aging_wr():
    """Aging wide receiver"""
    return TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=1003,
        player_name="Aging WR",
        position="wide_receiver",
        overall_rating=85,
        age=33,
        years_pro=11,
        contract_years_remaining=1,
        annual_cap_hit=15_000_000,
        trade_value=200.0
    )


@pytest.fixture
def first_round_pick():
    """First round draft pick"""
    pick = DraftPick(
        round=1,
        year=2025,
        original_team_id=1,
        current_team_id=1,
        overall_pick_projected=15
    )
    return TradeAsset(
        asset_type=AssetType.DRAFT_PICK,
        draft_pick=pick,
        trade_value=150.0
    )


@pytest.fixture
def star_edge():
    """Elite edge rusher"""
    return TradeAsset(
        asset_type=AssetType.PLAYER,
        player_id=1004,
        player_name="Star Edge",
        position="edge_rusher",
        overall_rating=92,
        age=27,
        years_pro=5,
        contract_years_remaining=2,
        annual_cap_hit=22_000_000,
        trade_value=500.0
    )


# ============================================================================
# TEST RISK TOLERANCE MODIFIER
# ============================================================================

class TestRiskToleranceModifier:
    """Tests for risk_tolerance trait modifier"""

    def test_young_player_risk_averse_discount(self, young_rb, conservative_gm, rebuilding_context):
        """Risk-averse GM discounts young unproven players"""
        modifier = PersonalityModifiers.apply_risk_tolerance_modifier(
            young_rb, conservative_gm, rebuilding_context
        )
        # Conservative GM (risk=0.2) should discount young player
        # Formula: 0.8 + (0.2 * 0.4) = 0.88
        assert 0.85 < modifier < 0.92

    def test_young_player_risk_seeking_premium(self, young_rb, aggressive_gm, rebuilding_context):
        """Risk-seeking GM premiums young high-upside players"""
        modifier = PersonalityModifiers.apply_risk_tolerance_modifier(
            young_rb, aggressive_gm, rebuilding_context
        )
        # Aggressive GM (risk=0.8) should premium young player
        # Formula: 0.8 + (0.8 * 0.4) = 1.12
        assert 1.08 < modifier < 1.16

    def test_veteran_risk_averse_premium(self, aging_wr, conservative_gm, contender_context):
        """Risk-averse GM premiums proven veterans"""
        modifier = PersonalityModifiers.apply_risk_tolerance_modifier(
            aging_wr, conservative_gm, contender_context
        )
        # Conservative GM (risk=0.2) should premium veteran
        # Formula: 1.1 - (0.2 * 0.2) = 1.06
        assert 1.03 < modifier < 1.09

    def test_prime_age_neutral(self, star_edge, neutral_gm, contender_context):
        """Prime age players (25-29) neutral regardless of risk tolerance"""
        modifier = PersonalityModifiers.apply_risk_tolerance_modifier(
            star_edge, neutral_gm, contender_context
        )
        assert modifier == 1.0

    def test_draft_picks_unaffected(self, first_round_pick, aggressive_gm, contender_context):
        """Risk tolerance doesn't affect draft picks"""
        modifier = PersonalityModifiers.apply_risk_tolerance_modifier(
            first_round_pick, aggressive_gm, contender_context
        )
        assert modifier == 1.0


# ============================================================================
# TEST WIN NOW MODIFIER
# ============================================================================

class TestWinNowModifier:
    """Tests for win_now_mentality trait modifier"""

    def test_proven_player_contender_premium(self, elite_qb, aggressive_gm, contender_context):
        """Win-now contender pays premium for proven player"""
        modifier = PersonalityModifiers.apply_win_now_modifier(
            elite_qb, aggressive_gm, contender_context
        )
        # Aggressive win-now (0.9) + contender = premium
        # Formula: 1.0 + (0.9 * 0.4) = 1.36
        assert 1.30 < modifier < 1.40

    def test_aging_player_rebuilder_discount(self, aging_wr, aggressive_gm, rebuilding_context):
        """Rebuilding team discounts aging veterans"""
        modifier = PersonalityModifiers.apply_win_now_modifier(
            aging_wr, aggressive_gm, rebuilding_context
        )
        # Rebuilding team discounts old player
        # Formula: 1.0 - (0.9 * 0.3) = 0.73
        assert 0.70 < modifier < 0.80

    def test_picks_contender_discount(self, first_round_pick, aggressive_gm, contender_context):
        """Win-now contender discounts draft picks"""
        modifier = PersonalityModifiers.apply_win_now_modifier(
            first_round_pick, aggressive_gm, contender_context
        )
        # Contender with high win-now discounts picks
        # Formula: 1.0 - (0.9 * 0.3) = 0.73
        assert 0.70 < modifier < 0.77

    def test_picks_rebuilder_premium(self, first_round_pick, conservative_gm, rebuilding_context):
        """Rebuilding team premiums draft picks"""
        modifier = PersonalityModifiers.apply_win_now_modifier(
            first_round_pick, conservative_gm, rebuilding_context
        )
        # Rebuilder with low win-now premiums picks
        # Formula: 1.0 + ((1.0 - 0.3) * 0.4) = 1.28
        assert 1.25 < modifier < 1.35

    def test_neutral_gm_neutral_context(self, young_rb, neutral_gm):
        """Neutral GM with average team gets neutral modifier"""
        context = TeamContext(
            team_id=1,
            season=2025,
            wins=8,
            losses=8,
            cap_space=20_000_000,
            cap_percentage=0.10
        )
        modifier = PersonalityModifiers.apply_win_now_modifier(
            young_rb, neutral_gm, context
        )
        # Middle-of-pack team should be close to 1.0
        assert 0.95 < modifier < 1.05


# ============================================================================
# TEST DRAFT PICK VALUE MODIFIER
# ============================================================================

class TestDraftPickValueModifier:
    """Tests for draft_pick_value trait modifier"""

    def test_high_draft_value_premium(self, first_round_pick, conservative_gm):
        """GM who values picks applies premium"""
        modifier = PersonalityModifiers.apply_draft_pick_value_modifier(
            first_round_pick, conservative_gm
        )
        # High draft_pick_value (0.8)
        # Formula: 0.7 + (0.8 * 0.8) = 1.34
        assert 1.30 < modifier < 1.40

    def test_low_draft_value_discount(self, first_round_pick, aggressive_gm):
        """GM who devalues picks applies discount"""
        modifier = PersonalityModifiers.apply_draft_pick_value_modifier(
            first_round_pick, aggressive_gm
        )
        # Low draft_pick_value (0.3)
        # Formula: 0.7 + (0.3 * 0.8) = 0.94
        assert 0.90 < modifier < 0.98

    def test_neutral_draft_value(self, first_round_pick, neutral_gm):
        """Neutral GM gets 1.0x on picks"""
        modifier = PersonalityModifiers.apply_draft_pick_value_modifier(
            first_round_pick, neutral_gm
        )
        # Neutral (0.5): 0.7 + (0.5 * 0.8) = 1.10
        assert 1.05 < modifier < 1.15

    def test_players_unaffected(self, elite_qb, conservative_gm):
        """Draft pick value trait doesn't affect players"""
        modifier = PersonalityModifiers.apply_draft_pick_value_modifier(
            elite_qb, conservative_gm
        )
        assert modifier == 1.0


# ============================================================================
# TEST CAP MANAGEMENT MODIFIER
# ============================================================================

class TestCapManagementModifier:
    """Tests for cap_management trait modifier"""

    def test_expensive_contract_conservative_discount(self, elite_qb, conservative_gm, contender_context):
        """Conservative GM heavily discounts expensive contracts"""
        modifier = PersonalityModifiers.apply_cap_management_modifier(
            elite_qb, conservative_gm, contender_context
        )
        # High cap_management (0.9), expensive contract ($45M)
        # Formula: 1.0 - (0.4 * 0.9) = 0.64
        # Low cap space (<10%) adds 10% penalty: 0.64 * 0.9 = 0.576
        assert 0.55 < modifier < 0.65

    def test_cheap_contract_conservative_premium(self, young_rb, conservative_gm, rebuilding_context):
        """Conservative GM premiums cheap contracts"""
        modifier = PersonalityModifiers.apply_cap_management_modifier(
            young_rb, conservative_gm, rebuilding_context
        )
        # High cap_management (0.9), cheap contract ($2.5M)
        # Formula: 1.0 + (0.9 * 0.2) = 1.18
        assert 1.15 < modifier < 1.22

    def test_expensive_contract_aggressive_minor_discount(self, elite_qb, aggressive_gm, contender_context):
        """Aggressive GM less concerned about expensive contracts"""
        modifier = PersonalityModifiers.apply_cap_management_modifier(
            elite_qb, aggressive_gm, contender_context
        )
        # Low cap_management (0.2), expensive contract
        # Formula: 1.0 - (0.4 * 0.2) = 0.92
        # Low cap space penalty: 0.92 * 0.9 = 0.828
        assert 0.80 < modifier < 0.88

    def test_mid_range_contract_neutral(self, neutral_gm, contender_context):
        """Mid-range contracts ($5-20M) are neutral"""
        # Create player with truly mid-range contract ($10M)
        mid_player = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1010,
            player_name="Mid Player",
            position="linebacker",
            overall_rating=80,
            age=28,
            annual_cap_hit=10_000_000,
            trade_value=200.0
        )
        modifier = PersonalityModifiers.apply_cap_management_modifier(
            mid_player, neutral_gm, contender_context
        )
        assert modifier == 1.0


# ============================================================================
# TEST VETERAN PREFERENCE MODIFIER
# ============================================================================

class TestVeteranPreferenceModifier:
    """Tests for veteran_preference trait modifier"""

    def test_young_player_youth_focused_premium(self, young_rb, aggressive_gm):
        """Youth-focused GM premiums young players"""
        # Aggressive GM has high veteran_preference (0.8), so inverse
        # Actually, let's create youth-focused GM
        youth_gm = GMArchetype(
            name="Youth GM",
            description="Loves young players",
            veteran_preference=0.2  # Low = youth focused
        )
        modifier = PersonalityModifiers.apply_veteran_preference_modifier(
            young_rb, youth_gm
        )
        # Low veteran_preference (0.2), young player (23)
        # Formula: 1.2 - (0.2 * 0.35) = 1.13
        assert 1.10 < modifier < 1.18

    def test_veteran_veteran_focused_premium(self, aging_wr, conservative_gm):
        """Veteran-focused GM premiums proven veterans"""
        modifier = PersonalityModifiers.apply_veteran_preference_modifier(
            aging_wr, conservative_gm
        )
        # High veteran_preference (0.7), aging vet (33)
        # Formula: 1.0 - (0.7 * 0.2) = 0.86
        assert 0.83 < modifier < 0.90

    def test_prime_veteran_premium(self, conservative_gm):
        """Veteran-focused GM premiums prime vets (28-32)"""
        # Create prime age veteran (must be 28-32)
        prime_vet = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1011,
            player_name="Prime Vet",
            position="edge_rusher",
            overall_rating=88,
            age=29,  # Within prime range (28-32)
            trade_value=400.0
        )
        modifier = PersonalityModifiers.apply_veteran_preference_modifier(
            prime_vet, conservative_gm
        )
        # High veteran_preference (0.7), prime vet (29)
        # Formula: 0.85 + (0.7 * 0.35) = 1.095
        assert 1.05 < modifier < 1.15


# ============================================================================
# TEST STAR CHASING MODIFIER
# ============================================================================

class TestStarChasingModifier:
    """Tests for star_chasing trait modifier"""

    def test_elite_player_star_chaser_premium(self, elite_qb, aggressive_gm):
        """Star-chasing GM pays major premium for elite players"""
        modifier = PersonalityModifiers.apply_star_chasing_modifier(
            elite_qb, aggressive_gm
        )
        # High star_chasing (0.9), elite player (95 OVR)
        # Formula: 1.0 + (0.9 * 0.5) = 1.45
        assert 1.40 < modifier < 1.50

    def test_star_player_moderate_premium(self, aging_wr, aggressive_gm):
        """Star-chasing GM pays moderate premium for stars (85-89 OVR)"""
        modifier = PersonalityModifiers.apply_star_chasing_modifier(
            aging_wr, aggressive_gm
        )
        # High star_chasing (0.9), star (85 OVR)
        # Formula: 1.0 + (0.9 * 0.2) = 1.18
        assert 1.15 < modifier < 1.22

    def test_average_player_balanced_premium(self, young_rb, conservative_gm):
        """Balanced GMs premium depth players"""
        modifier = PersonalityModifiers.apply_star_chasing_modifier(
            young_rb, conservative_gm
        )
        # Low star_chasing (0.2), average (78 OVR)
        # Formula: 1.1 - (0.2 * 0.2) = 1.06
        assert 1.03 < modifier < 1.09


# ============================================================================
# TEST LOYALTY MODIFIER
# ============================================================================

class TestLoyaltyModifier:
    """Tests for loyalty trait modifier"""

    def test_giving_away_high_loyalty_premium(self, elite_qb, conservative_gm):
        """High loyalty GM premiums keeping own players"""
        modifier = PersonalityModifiers.apply_loyalty_modifier(
            elite_qb, conservative_gm, is_acquiring=False
        )
        # High loyalty (0.8), giving away
        # Formula: 1.0 + (0.8 * 0.4) = 1.32
        assert 1.28 < modifier < 1.36

    def test_acquiring_loyalty_neutral(self, elite_qb, conservative_gm):
        """Loyalty doesn't affect acquiring players"""
        modifier = PersonalityModifiers.apply_loyalty_modifier(
            elite_qb, conservative_gm, is_acquiring=True
        )
        assert modifier == 1.0

    def test_giving_away_low_loyalty_neutral(self, elite_qb, aggressive_gm):
        """Low loyalty GM neutral on giving away players"""
        modifier = PersonalityModifiers.apply_loyalty_modifier(
            elite_qb, aggressive_gm, is_acquiring=False
        )
        # Low loyalty (0.3), giving away
        # Formula: 1.0 + (0.3 * 0.4) = 1.12
        assert 1.08 < modifier < 1.16


# ============================================================================
# TEST PREMIUM POSITION MODIFIER
# ============================================================================

class TestPremiumPositionModifier:
    """Tests for premium_position_focus trait modifier"""

    def test_qb_premium_position_focused(self, elite_qb, aggressive_gm):
        """Position-focused GM premiums QB"""
        modifier = PersonalityModifiers.apply_premium_position_modifier(
            elite_qb, aggressive_gm
        )
        # High premium_position_focus (0.8), QB
        # Formula: 1.0 + (0.8 * 0.2) = 1.16
        assert 1.13 < modifier < 1.20

    def test_edge_premium_position_focused(self, star_edge, aggressive_gm):
        """Position-focused GM premiums Edge"""
        modifier = PersonalityModifiers.apply_premium_position_modifier(
            star_edge, aggressive_gm
        )
        # High premium_position_focus (0.8), Edge
        # Formula: 1.0 + (0.8 * 0.2) = 1.16
        assert 1.13 < modifier < 1.20

    def test_wr_position_focused_slight_discount(self, aging_wr, aggressive_gm):
        """Position-focused GM slight discount on non-premium positions"""
        modifier = PersonalityModifiers.apply_premium_position_modifier(
            aging_wr, aggressive_gm
        )
        # High premium_position_focus (0.8), WR (non-premium)
        # Formula: 1.0 - (0.8 * 0.05) = 0.96
        assert 0.94 < modifier < 0.98


# ============================================================================
# TEST SITUATIONAL MODIFIERS
# ============================================================================

class TestDesperationModifier:
    """Tests for desperation modifier"""

    def test_desperate_team_premiums_proven_players(self, elite_qb, conservative_gm):
        """Desperate team pays premium for proven help"""
        desperate_context = TeamContext(
            team_id=1,
            season=2025,
            wins=2,  # Win pct = 0.12
            losses=14,
            cap_space=30_000_000,
            cap_percentage=0.15
        )
        # Conservative GM has desperation_threshold=0.6
        # Team win_pct (0.125) << threshold (0.6)
        # Desperation severity: (0.6 - 0.125) / 0.2 = 2.375 → capped at 1.0

        modifier = PersonalityModifiers.apply_desperation_modifier(
            elite_qb, conservative_gm, desperate_context
        )
        # Full desperation + proven player
        # Formula: 1.0 + (1.0 * 0.3) = 1.3
        assert 1.25 < modifier < 1.35

    def test_desperate_team_discounts_picks(self, first_round_pick, conservative_gm):
        """Desperate team discounts draft picks"""
        desperate_context = TeamContext(
            team_id=1,
            season=2025,
            wins=3,
            losses=13,
            cap_space=30_000_000,
            cap_percentage=0.15
        )
        modifier = PersonalityModifiers.apply_desperation_modifier(
            first_round_pick, conservative_gm, desperate_context
        )
        # Desperation + draft pick
        # Formula: 1.0 - (severity * 0.2)
        assert 0.78 < modifier < 0.85


class TestDeadlineModifier:
    """Tests for trade deadline modifier"""

    def test_deadline_contender_premiums_proven_players(self, elite_qb, aggressive_gm, deadline_contender_context):
        """Contender at deadline pays premium for proven help"""
        modifier = PersonalityModifiers.apply_deadline_modifier(
            elite_qb, aggressive_gm, deadline_contender_context
        )
        # High deadline_activity (0.9), contender, proven player
        # Formula: 1.0 + (0.9 * 0.2) = 1.18
        assert 1.15 < modifier < 1.22

    def test_deadline_contender_discounts_picks(self, first_round_pick, aggressive_gm, deadline_contender_context):
        """Contender at deadline discounts draft picks"""
        modifier = PersonalityModifiers.apply_deadline_modifier(
            first_round_pick, aggressive_gm, deadline_contender_context
        )
        # High deadline_activity (0.9), contender, pick
        # Formula: 1.0 - (0.9 * 0.15) = 0.865
        assert 0.83 < modifier < 0.90

    def test_non_deadline_neutral(self, elite_qb, aggressive_gm, contender_context):
        """Non-deadline trades not affected"""
        modifier = PersonalityModifiers.apply_deadline_modifier(
            elite_qb, aggressive_gm, contender_context
        )
        assert modifier == 1.0


class TestTeamNeedModifier:
    """Tests for team need modifier"""

    def test_top_need_premium(self, rebuilding_context):
        """Asset filling top need gets premium"""
        qb = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1005,
            player_name="QB",
            position="quarterback",
            overall_rating=85,
            age=26,
            trade_value=400.0
        )
        modifier = PersonalityModifiers.apply_team_need_modifier(
            qb, rebuilding_context
        )
        # QB is top need for rebuilding team
        assert modifier == 1.3

    def test_secondary_need_moderate_premium(self, rebuilding_context):
        """Asset filling secondary need gets moderate premium"""
        edge = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1006,
            player_name="Edge",
            position="edge_rusher",
            overall_rating=83,
            age=25,
            trade_value=300.0
        )
        modifier = PersonalityModifiers.apply_team_need_modifier(
            edge, rebuilding_context
        )
        # Edge is secondary need (position 2)
        assert modifier == 1.15

    def test_non_need_neutral(self, young_rb, rebuilding_context):
        """Asset not filling need is neutral"""
        modifier = PersonalityModifiers.apply_team_need_modifier(
            young_rb, rebuilding_context
        )
        # RB not in top needs
        assert modifier == 1.0


# ============================================================================
# TEST COMBINED MODIFIERS
# ============================================================================

class TestCombinedModifiers:
    """Tests for calculate_total_modifier"""

    def test_neutral_gm_produces_near_neutral(self, neutral_gm, contender_context):
        """Neutral GM with average context produces ~1.0x"""
        # Use player with moderate contract to avoid extreme cap modifiers
        moderate_player = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=1012,
            player_name="Moderate Player",
            position="wide_receiver",
            overall_rating=82,
            age=27,
            annual_cap_hit=12_000_000,  # Mid-range contract
            trade_value=250.0
        )
        total = PersonalityModifiers.calculate_total_modifier(
            moderate_player, neutral_gm, contender_context, is_acquiring=True
        )
        # Should be close to 1.0 but may have slight variance
        assert 0.90 < total < 1.15

    def test_aggressive_gm_star_premiums_stack(self, elite_qb, aggressive_gm, deadline_contender_context):
        """Aggressive GM with star at deadline stacks premiums"""
        total = PersonalityModifiers.calculate_total_modifier(
            elite_qb, aggressive_gm, deadline_contender_context, is_acquiring=True
        )
        # Multiple premiums should stack significantly
        # win_now + star_chasing + deadline + premium_position + expensive_contract
        # Should be well above 1.0 but capped at 2.0
        assert 1.30 < total <= 2.00

    def test_conservative_gm_young_player_discounts_stack(self, young_rb, conservative_gm, rebuilding_context):
        """Conservative GM with young player shows risk-averse tendencies"""
        total = PersonalityModifiers.calculate_total_modifier(
            young_rb, conservative_gm, rebuilding_context, is_acquiring=True
        )
        # Risk discount present, but cheap contract and low star_chasing create offsetting premiums
        # Net result should be close to neutral with slight variance
        assert 0.85 < total < 1.15

    def test_modifier_capping(self, elite_qb, aggressive_gm):
        """Extreme modifiers capped at 0.50x-2.00x"""
        # Create extremely desperate context
        desperate_context = TeamContext(
            team_id=1,
            season=2025,
            wins=0,
            losses=16,
            playoff_position=None,
            games_out_of_playoff=10,
            cap_space=80_000_000,
            cap_percentage=0.40,
            top_needs=['quarterback'],
            is_deadline=True,
            is_offseason=False
        )

        total = PersonalityModifiers.calculate_total_modifier(
            elite_qb, aggressive_gm, desperate_context, is_acquiring=True
        )
        # Should be capped at 2.0 even with extreme premiums
        assert 0.50 <= total <= 2.00


# ============================================================================
# TEST ACCEPTANCE THRESHOLD
# ============================================================================

class TestAcceptanceThreshold:
    """Tests for calculate_acceptance_threshold"""

    def test_neutral_gm_standard_range(self, neutral_gm, contender_context):
        """Neutral GM produces standard range"""
        min_ratio, max_ratio = PersonalityModifiers.calculate_acceptance_threshold(
            neutral_gm, contender_context
        )
        # Should be around ±20%
        assert 0.75 < min_ratio < 0.85
        assert 1.15 < max_ratio < 1.25

    def test_aggressive_gm_wider_range(self, aggressive_gm, contender_context):
        """Aggressive GM (high trade_frequency + risk_tolerance) has wider range"""
        min_ratio, max_ratio = PersonalityModifiers.calculate_acceptance_threshold(
            aggressive_gm, contender_context
        )
        # Should be wider than neutral
        assert 0.70 < min_ratio < 0.80
        assert 1.25 < max_ratio < 1.35

    def test_conservative_gm_narrower_range(self, conservative_gm, contender_context):
        """Conservative GM has narrower acceptable range"""
        min_ratio, max_ratio = PersonalityModifiers.calculate_acceptance_threshold(
            conservative_gm, contender_context
        )
        # Should be narrower than neutral
        assert 0.78 < min_ratio < 0.88
        assert 1.12 < max_ratio < 1.22

    def test_desperation_expands_max(self, aggressive_gm):
        """Desperation expands max ratio (willing to overpay)"""
        desperate_context = TeamContext(
            team_id=1,
            season=2025,
            wins=2,
            losses=14,
            cap_space=30_000_000,
            cap_percentage=0.15
        )
        # aggressive_gm has desperation_threshold=0.7
        # Win pct = 0.125 << 0.7, so desperate

        min_ratio, max_ratio = PersonalityModifiers.calculate_acceptance_threshold(
            aggressive_gm, desperate_context
        )
        # Max should be expanded significantly
        assert max_ratio > 1.30

    def test_bounds_enforcement(self, neutral_gm, contender_context):
        """Thresholds enforced to reasonable bounds (±10% to ±40%)"""
        min_ratio, max_ratio = PersonalityModifiers.calculate_acceptance_threshold(
            neutral_gm, contender_context
        )
        # Minimum bounds: 0.60-0.90
        assert 0.60 <= min_ratio <= 0.90
        # Maximum bounds: 1.10-1.40
        assert 1.10 <= max_ratio <= 1.40


# ============================================================================
# TEST EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Edge case and validation tests"""

    def test_extreme_trait_values(self, elite_qb, contender_context):
        """Extreme trait values (0.0, 1.0) stay within bounds"""
        extreme_gm = GMArchetype(
            name="Extreme GM",
            description="All traits at extremes",
            risk_tolerance=1.0,
            win_now_mentality=1.0,
            draft_pick_value=1.0,
            cap_management=1.0,
            trade_frequency=1.0,
            veteran_preference=1.0,
            star_chasing=1.0,
            loyalty=1.0,
            desperation_threshold=1.0,
            patience_years=1,
            deadline_activity=1.0,
            premium_position_focus=1.0
        )

        total = PersonalityModifiers.calculate_total_modifier(
            elite_qb, extreme_gm, contender_context, is_acquiring=True
        )
        assert 0.50 <= total <= 2.00

    def test_missing_player_data(self, neutral_gm, contender_context):
        """Missing player data returns 1.0x (neutral)"""
        incomplete_player = TradeAsset(
            asset_type=AssetType.PLAYER,
            player_id=9999,
            player_name="Unknown",
            trade_value=100.0
            # Missing position, age, rating, etc.
        )

        # Should not crash, return neutral modifiers
        total = PersonalityModifiers.calculate_total_modifier(
            incomplete_player, neutral_gm, contender_context, is_acquiring=True
        )
        assert 0.90 <= total <= 1.10  # Close to neutral

    def test_zero_games_played_context(self, elite_qb, neutral_gm):
        """Team with zero games played (pre-season) handles gracefully"""
        preseason_context = TeamContext(
            team_id=1,
            season=2025,
            wins=0,
            losses=0,  # No games played
            cap_space=50_000_000,
            cap_percentage=0.25
        )

        total = PersonalityModifiers.calculate_total_modifier(
            elite_qb, neutral_gm, preseason_context, is_acquiring=True
        )
        # Should default to 0.5 win percentage
        assert 0.50 <= total <= 2.00


# ============================================================================
# TEST FREE AGENCY MODIFIERS
# ============================================================================

class TestFreeAgencyModifier:
    """Tests for apply_free_agency_modifier() method"""

    # ========== FIXTURES ==========

    @pytest.fixture
    def elite_fa_wr(self):
        """Elite 92 OVR free agent wide receiver, age 28"""
        from team_management.players.player import Player
        player = Player(
            name="Elite FA WR",
            number=1,
            primary_position="wide_receiver",
            player_id=2001
        )
        player.ratings['overall'] = 92
        player.overall = 92  # Also set as attribute for convenience
        player.age = 28
        player.injury_prone = False
        return player

    @pytest.fixture
    def veteran_starter_rb(self):
        """Veteran 82 OVR starter running back, age 31"""
        from team_management.players.player import Player
        player = Player(
            name="Veteran RB",
            number=2,
            primary_position="running_back",
            player_id=2002
        )
        player.ratings['overall'] = 82
        player.overall = 82  # Also set as attribute for convenience
        player.age = 31
        player.injury_prone = False
        return player

    @pytest.fixture
    def injury_prone_te(self):
        """Injury-prone 85 OVR tight end"""
        from team_management.players.player import Player
        player = Player(
            name="Injury-Prone TE",
            number=3,
            primary_position="tight_end",
            player_id=2003
        )
        player.ratings['overall'] = 85
        player.overall = 85  # Also set as attribute for convenience
        player.age = 26
        player.injury_prone = True
        return player

    @pytest.fixture
    def average_cb(self):
        """Average 75 OVR cornerback, age 25"""
        from team_management.players.player import Player
        player = Player(
            name="Average CB",
            number=4,
            primary_position="cornerback",
            player_id=2004
        )
        player.ratings['overall'] = 75
        player.overall = 75  # Also set as attribute for convenience
        player.age = 25
        player.injury_prone = False
        return player

    @pytest.fixture
    def market_value_15m(self):
        """$15M AAV market value"""
        return {
            'aav': 15_000_000,
            'years': 4,
            'total': 60_000_000,
            'guaranteed': 30_000_000
        }

    @pytest.fixture
    def market_value_5m(self):
        """$5M AAV market value"""
        return {
            'aav': 5_000_000,
            'years': 3,
            'total': 15_000_000,
            'guaranteed': 10_000_000
        }

    @pytest.fixture
    def win_now_gm(self):
        """Win-Now GM (high win_now_mentality, low cap_management)"""
        return GMArchetype(
            name="Win-Now GM",
            description="Aggressive, win-now focused",
            win_now_mentality=0.9,
            cap_management=0.3,
            star_chasing=0.7,
            veteran_preference=0.6,
            risk_tolerance=0.5
        )

    @pytest.fixture
    def rebuilder_gm(self):
        """Rebuilder GM (low win_now, high cap_management)"""
        return GMArchetype(
            name="Rebuilder GM",
            description="Patient, cap-conscious rebuilder",
            win_now_mentality=0.2,
            cap_management=0.9,
            star_chasing=0.2,
            veteran_preference=0.3,
            risk_tolerance=0.5
        )

    # ========== INDIVIDUAL MODIFIER TESTS ==========

    def test_win_now_premium_for_proven_starters(
        self, veteran_starter_rb, market_value_15m, win_now_gm, contender_context
    ):
        """Win-Now GMs overpay for proven starters (80+ OVR)"""
        result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, win_now_gm, contender_context
        )
        # Multiple modifiers apply:
        # 1. win_now (82 OVR >= 80): 1.0 + ((0.9 - 0.5) * 0.8) = 1.32
        # 2. cap_management (82 OVR < 85): 1.0 - (0.3 * 0.4) = 0.88
        # Combined: 15M * 1.32 * 0.88 ≈ 17.424M
        assert result['aav'] > 15_000_000
        assert result['aav'] <= 21_000_000  # Max 1.4x
        assert 17_000_000 < result['aav'] < 19_000_000  # Expected range with stacking

    def test_cap_management_discount(
        self, veteran_starter_rb, market_value_15m, rebuilder_gm, rebuilding_context
    ):
        """Cap-conscious GMs discount non-elite players (< 85 OVR)"""
        result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, rebuilder_gm, rebuilding_context
        )
        # Multiple modifiers apply:
        # 1. cap_management (82 OVR < 85): 1.0 - (0.9 * 0.4) = 0.64
        # 2. veteran_preference (age 31 >= 30, vet_pref=0.3 < 0.5): 1.0 - ((0.5 - 0.3) * 0.4) = 0.92
        # Combined: 15M * 0.64 * 0.92 ≈ 8.832M
        assert result['aav'] < 15_000_000
        assert result['aav'] >= 8_500_000  # Min with stacking
        assert 8_500_000 < result['aav'] < 9_500_000  # Expected range with stacking

    def test_veteran_preference_premium(
        self, veteran_starter_rb, market_value_15m, contender_context
    ):
        """Veteran-preferring GMs pay more for 30+ age players"""
        gm = GMArchetype(name="Veteran-Focused GM", description="Prefers veterans", veteran_preference=0.9)
        result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, gm, contender_context
        )
        # Multiple modifiers apply:
        # 1. cap_management (82 OVR < 85, default=0.5): 1.0 - (0.5 * 0.4) = 0.8
        # 2. veteran_preference (age 31 >= 30, vet_pref=0.9 > 0.5): 1.0 + ((0.9 - 0.5) * 0.4) = 1.16
        # Combined: 15M * 0.8 * 1.16 = 13.92M
        assert result['aav'] < 15_000_000  # Cap discount outweighs vet premium
        assert 13_500_000 < result['aav'] < 14_500_000  # Expected range with stacking

    def test_veteran_preference_discount(
        self, veteran_starter_rb, market_value_15m, rebuilding_context
    ):
        """Youth-focused GMs discount 30+ age players"""
        gm = GMArchetype(name="Youth-Focused GM", description="Prefers young players", veteran_preference=0.1)
        result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, gm, rebuilding_context
        )
        # Multiple modifiers apply:
        # 1. cap_management (82 OVR < 85, default=0.5): 1.0 - (0.5 * 0.4) = 0.8
        # 2. veteran_preference (age 31 >= 30, vet_pref=0.1 < 0.5): 1.0 - ((0.5 - 0.1) * 0.4) = 0.84
        # Combined: 15M * 0.8 * 0.84 = 10.08M
        assert result['aav'] < 15_000_000
        assert 9_500_000 < result['aav'] < 11_000_000  # Expected range with stacking

    def test_star_chasing_premium(
        self, elite_fa_wr, market_value_15m, contender_context
    ):
        """Star-chasing GMs overpay for elite FAs (90+ OVR)"""
        gm = GMArchetype(name="Star Chaser GM", description="Loves elite players", star_chasing=0.9)
        result = PersonalityModifiers.apply_free_agency_modifier(
            elite_fa_wr, market_value_15m, gm, contender_context
        )
        # Expected: 15M * 1.45 = 21.75M
        # Formula: 1.0 + (0.9 * 0.5) = 1.45
        assert result['aav'] > 15_000_000
        assert result['aav'] <= 22_500_000  # Max 1.5x
        assert 20_000_000 < result['aav'] < 23_000_000

    def test_risk_tolerance_discount(
        self, injury_prone_te, market_value_15m, contender_context
    ):
        """Risk-averse GMs discount injury-prone players"""
        gm = GMArchetype(name="Risk-Averse GM", description="Avoids risky players", risk_tolerance=0.2)
        result = PersonalityModifiers.apply_free_agency_modifier(
            injury_prone_te, market_value_15m, gm, contender_context
        )
        # Expected: 15M * 0.82 = 12.3M
        # Formula: 1.0 - ((0.5 - 0.2) * 0.6) = 0.82
        assert result['aav'] < 15_000_000
        assert result['aav'] >= 10_500_000  # Min 0.7x
        assert 11_500_000 < result['aav'] < 13_000_000

    def test_risk_neutral_for_injury_prone_at_threshold(
        self, injury_prone_te, market_value_15m, contender_context
    ):
        """Risk-tolerant GMs (>= 0.5) don't discount injury-prone players"""
        gm = GMArchetype(name="Risk-Tolerant GM", description="Accepts risky players", risk_tolerance=0.6)
        result = PersonalityModifiers.apply_free_agency_modifier(
            injury_prone_te, market_value_15m, gm, contender_context
        )
        # No discount since risk_tolerance >= 0.5
        assert result['aav'] == 15_000_000

    # ========== COMBINED MODIFIER TESTS ==========

    def test_combined_modifiers_win_now(
        self, elite_fa_wr, market_value_15m, win_now_gm, contender_context
    ):
        """Multiple modifiers stack multiplicatively"""
        result = PersonalityModifiers.apply_free_agency_modifier(
            elite_fa_wr, market_value_15m, win_now_gm, contender_context
        )
        # Expected: Multiple bonuses stack
        # 1. win_now (elite_fa_wr is 92 OVR >= 80): ~1.32x
        # 2. star_chasing (92 OVR >= 90): ~1.35x
        # Combined: 15M * 1.32 * 1.35 ≈ 26.7M
        assert result['aav'] > 20_000_000  # Significant overpay
        assert result['aav'] > 25_000_000  # Multiple multipliers

    def test_combined_modifiers_rebuilder(
        self, veteran_starter_rb, market_value_15m, rebuilder_gm, rebuilding_context
    ):
        """Rebuilder applies multiple discounts"""
        result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, rebuilder_gm, rebuilding_context
        )
        # Expected: Multiple discounts stack
        # 1. cap_management (82 OVR < 85): 0.64x
        # 2. veteran_preference (age 31 >= 30, vet_pref=0.3): 0.88x
        # Combined: 15M * 0.64 * 0.88 ≈ 8.45M
        assert result['aav'] < 15_000_000
        assert result['aav'] < 10_000_000  # Multiple discounts
        assert 7_500_000 < result['aav'] < 9_500_000

    # ========== EDGE CASE TESTS ==========

    def test_backward_compatibility_no_injury_prone(
        self, average_cb, market_value_5m, contender_context
    ):
        """Handles players without injury_prone attribute"""
        # Remove injury_prone attribute
        delattr(average_cb, 'injury_prone')
        gm = GMArchetype(name="Risk-Averse GM", description="Avoids risky players", risk_tolerance=0.1)
        result = PersonalityModifiers.apply_free_agency_modifier(
            average_cb, market_value_5m, gm, contender_context
        )
        # Should not crash, just skip injury modifier
        # But cap_management still applies (75 OVR < 85, default=0.5): 1.0 - (0.5 * 0.4) = 0.8
        # 5M * 0.8 = 4M
        assert result['aav'] == 4_000_000

    def test_original_dict_not_mutated(
        self, elite_fa_wr, market_value_15m, win_now_gm, contender_context
    ):
        """Original market_value dict is not mutated"""
        original_aav = market_value_15m['aav']
        result = PersonalityModifiers.apply_free_agency_modifier(
            elite_fa_wr, market_value_15m, win_now_gm, contender_context
        )
        # Original should be unchanged
        assert market_value_15m['aav'] == original_aav
        # Result should be modified
        assert result['aav'] != original_aav

    def test_no_modifiers_apply(
        self, average_cb, market_value_5m, neutral_gm, rebuilding_context
    ):
        """Player with no modifier triggers returns original value"""
        # average_cb: 75 OVR (< 80, not star), age 25 (< 30), not injury-prone
        # neutral_gm: All traits = 0.5
        result = PersonalityModifiers.apply_free_agency_modifier(
            average_cb, market_value_5m, neutral_gm, rebuilding_context
        )
        # Only cap_management applies (75 OVR < 85): 1.0 - (0.5 * 0.4) = 0.8
        assert result['aav'] < 5_000_000
        assert 3_500_000 < result['aav'] < 4_500_000

    def test_all_dict_keys_preserved(
        self, elite_fa_wr, market_value_15m, win_now_gm, contender_context
    ):
        """All keys in market_value dict are preserved"""
        result = PersonalityModifiers.apply_free_agency_modifier(
            elite_fa_wr, market_value_15m, win_now_gm, contender_context
        )
        # All original keys should be present
        assert 'aav' in result
        assert 'years' in result
        assert 'total' in result
        assert 'guaranteed' in result

    def test_extreme_multiplier_stacking(
        self, elite_fa_wr, market_value_15m, contender_context
    ):
        """Extreme GM traits don't produce unrealistic values"""
        extreme_gm = GMArchetype(
            name="Extreme GM",
            description="All traits at extremes",
            win_now_mentality=1.0,
            star_chasing=1.0,
            cap_management=0.0,
            veteran_preference=1.0,
            risk_tolerance=1.0
        )
        result = PersonalityModifiers.apply_free_agency_modifier(
            elite_fa_wr, market_value_15m, extreme_gm, contender_context
        )
        # Even with extreme traits, should remain somewhat reasonable
        # Max expected: ~1.4 (win_now) * 1.5 (star) = 2.1x = 31.5M
        assert result['aav'] < 35_000_000  # Extreme but not absurd

    # ========== BEHAVIORAL DIFFERENTIATION TESTS ==========

    def test_win_now_vs_rebuilder_variance(
        self, veteran_starter_rb, market_value_15m,
        win_now_gm, rebuilder_gm, contender_context, rebuilding_context
    ):
        """Win-Now and Rebuilder GMs show ≥20% AAV variance"""
        win_now_result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, win_now_gm, contender_context
        )
        rebuilder_result = PersonalityModifiers.apply_free_agency_modifier(
            veteran_starter_rb, market_value_15m, rebuilder_gm, rebuilding_context
        )

        # Calculate variance
        variance = abs(win_now_result['aav'] - rebuilder_result['aav']) / market_value_15m['aav']

        # Should show ≥20% variance (from specification)
        assert variance >= 0.20, f"Variance {variance:.2%} is below 20% threshold"

        # Win-Now should pay more than Rebuilder
        assert win_now_result['aav'] > rebuilder_result['aav']


# ============================================================================
# TESTS - ROSTER CUT MODIFIERS (PHASE 3)
# ============================================================================

class TestLoyaltyModifier:
    """Tests for loyalty modifier (tenure bonus)."""

    def test_loyal_gm_boosts_long_tenured_player(self, rebuilding_context):
        """Loyal GM gives value boost to long-tenured players (5+ years)."""
        from team_management.players.player import Player

        # Create loyal GM
        loyal_gm = GMArchetype(
            name="Loyal GM",
            description="Values team loyalty",
            loyalty=0.9,
            cap_management=0.5,
            veteran_preference=0.5
        )

        # Create long-tenured player (7 years with team)
        player = Player(
            name="Veteran Player",
            number=99,
            primary_position="linebacker",
            player_id=3001
        )
        player.years_with_team = 7
        player.age = 28
        player.cap_hit = 4_000_000

        objective_value = 70.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, loyal_gm, rebuilding_context
        )

        # Expected: 70 * 1.36 = 95.2
        # Formula: 1.0 + (0.9 * 0.4) = 1.36
        assert modified_value > objective_value
        assert 94.0 < modified_value < 96.0

    def test_ruthless_gm_minimal_tenure_bonus(self, rebuilding_context):
        """Ruthless GM gives minimal tenure bonus."""
        from team_management.players.player import Player

        # Create ruthless GM
        ruthless_gm = GMArchetype(
            name="Ruthless GM",
            description="No sentiment",
            loyalty=0.1,
            cap_management=0.5,
            veteran_preference=0.5
        )

        # Create long-tenured player (8 years with team)
        player = Player(
            name="Veteran Player",
            number=98,
            primary_position="safety",
            player_id=3002
        )
        player.years_with_team = 8
        player.age = 29
        player.cap_hit = 3_500_000

        objective_value = 68.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, ruthless_gm, rebuilding_context
        )

        # Expected: 68 * 1.04 = 70.72
        # Formula: 1.0 + (0.1 * 0.4) = 1.04
        assert modified_value > objective_value
        assert 70.0 < modified_value < 72.0


class TestCapManagementModifier:
    """Tests for cap management modifier (expensive player discount)."""

    def test_cap_conscious_gm_discounts_expensive_player(self, rebuilding_context):
        """Cap-conscious GM discounts expensive players (>$5M cap hit)."""
        from team_management.players.player import Player

        # Create cap-conscious GM
        cap_conscious_gm = GMArchetype(
            name="Cap-Conscious GM",
            description="Values cap space",
            loyalty=0.5,
            cap_management=0.9,
            veteran_preference=0.5
        )

        # Create expensive player ($8M cap hit)
        player = Player(
            name="Expensive Player",
            number=97,
            primary_position="wide_receiver",
            player_id=3003
        )
        player.years_with_team = 3
        player.age = 27
        player.cap_hit = 8_000_000

        objective_value = 75.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, cap_conscious_gm, rebuilding_context
        )

        # Expected: 75 * 0.8 = 60.0
        # Formula: 0.8x discount for expensive player
        assert modified_value < objective_value
        assert 59.0 < modified_value < 61.0

    def test_cap_flexible_gm_no_discount(self, rebuilding_context):
        """Cap-flexible GM does not discount expensive players."""
        from team_management.players.player import Player

        # Create cap-flexible GM (cap_management <= 0.7)
        cap_flexible_gm = GMArchetype(
            name="Cap-Flexible GM",
            description="Not worried about cap",
            loyalty=0.5,
            cap_management=0.3,
            veteran_preference=0.5
        )

        # Create expensive player ($7M cap hit)
        player = Player(
            name="Expensive Player",
            number=96,
            primary_position="running_back",
            player_id=3004
        )
        player.years_with_team = 2
        player.age = 26
        player.cap_hit = 7_000_000

        objective_value = 72.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, cap_flexible_gm, rebuilding_context
        )

        # Expected: 72 * 1.0 = 72.0 (no discount since cap_management <= 0.7)
        assert modified_value == objective_value


class TestVeteranPreferenceRosterCuts:
    """Tests for veteran preference modifier (age factor)."""

    def test_veteran_preferring_gm_boosts_old_player(self, rebuilding_context):
        """Veteran-preferring GM boosts 30+ age players."""
        from team_management.players.player import Player

        # Create veteran-preferring GM
        vet_pref_gm = GMArchetype(
            name="Veteran-Preferring GM",
            description="Loves experience",
            loyalty=0.5,
            cap_management=0.5,
            veteran_preference=0.9
        )

        # Create 32-year-old player
        player = Player(
            name="Old Player",
            number=95,
            primary_position="linebacker",
            player_id=3005
        )
        player.years_with_team = 4
        player.age = 32
        player.cap_hit = 4_500_000

        objective_value = 65.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, vet_pref_gm, rebuilding_context
        )

        # Expected: 65 * 1.16 = 75.4
        # Formula: 1.0 + ((0.9 - 0.5) * 0.4) = 1.16
        assert modified_value > objective_value
        assert 74.5 < modified_value < 76.5

    def test_youth_focused_gm_discounts_old_player(self, rebuilding_context):
        """Youth-focused GM discounts 30+ age players."""
        from team_management.players.player import Player

        # Create youth-focused GM
        youth_gm = GMArchetype(
            name="Youth-Focused GM",
            description="Prefers young talent",
            loyalty=0.5,
            cap_management=0.5,
            veteran_preference=0.2
        )

        # Create 31-year-old player
        player = Player(
            name="Old Player",
            number=94,
            primary_position="cornerback",
            player_id=3006
        )
        player.years_with_team = 3
        player.age = 31
        player.cap_hit = 3_000_000

        objective_value = 70.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, youth_gm, rebuilding_context
        )

        # Expected: 70 * 0.88 = 61.6
        # Formula: 1.0 - ((0.5 - 0.2) * 0.4) = 0.88
        assert modified_value < objective_value
        assert 60.5 < modified_value < 62.5


class TestRosterCutCombinedModifiers:
    """Tests for combined roster cut modifiers."""

    def test_all_modifiers_stack_multiplicatively(self, rebuilding_context):
        """All 3 modifiers stack multiplicatively."""
        from team_management.players.player import Player

        # Create GM with all 3 traits active
        gm = GMArchetype(
            name="Complex GM",
            description="Multiple traits",
            loyalty=0.8,
            cap_management=0.9,
            veteran_preference=0.6
        )

        # Create player triggering all 3 modifiers
        # 32 years old, 7 years tenure, $7M cap hit
        player = Player(
            name="Complex Player",
            number=93,
            primary_position="defensive_end",
            player_id=3007
        )
        player.age = 32
        player.years_with_team = 7
        player.cap_hit = 7_000_000

        objective_value = 68.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, rebuilding_context
        )

        # Expected: 68 * 1.32 * 0.8 * 1.04 ≈ 74.7
        # loyalty: 1.0 + (0.8 * 0.4) = 1.32
        # cap_mgmt: 0.8 (expensive player, cap_management > 0.7)
        # vet_pref: 1.0 + ((0.6 - 0.5) * 0.4) = 1.04
        assert 73.5 < modified_value < 75.5

    def test_offsetting_modifiers(self, rebuilding_context):
        """Loyalty and cap management can offset each other."""
        from team_management.players.player import Player

        # Create GM with high loyalty AND high cap management
        gm = GMArchetype(
            name="Conflicted GM",
            description="Loyalty vs cap discipline",
            loyalty=0.9,  # Boosts tenure
            cap_management=0.9,  # Discounts expensive
            veteran_preference=0.5
        )

        # Create expensive veteran with tenure
        player = Player(
            name="Expensive Vet",
            number=92,
            primary_position="quarterback",
            player_id=3008
        )
        player.years_with_team = 8  # Triggers loyalty boost
        player.age = 28  # No vet preference modifier
        player.cap_hit = 8_000_000  # Triggers cap discount

        objective_value = 80.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, gm, rebuilding_context
        )

        # Expected: 80 * 1.36 * 0.8 = 87.04
        # loyalty: 1.0 + (0.9 * 0.4) = 1.36
        # cap_mgmt: 0.8
        # Net result: modifiers offset but loyalty wins slightly
        assert modified_value > objective_value  # Loyalty wins
        assert 86.0 < modified_value < 89.0


class TestRosterCutEdgeCases:
    """Tests for edge cases in roster cut modifiers."""

    def test_missing_years_with_team_field(self, rebuilding_context):
        """Handle missing years_with_team field gracefully."""
        from team_management.players.player import Player

        # Create loyal GM
        loyal_gm = GMArchetype(
            name="Loyal GM",
            description="Values tenure",
            loyalty=0.9,
            cap_management=0.5,
            veteran_preference=0.5
        )

        # Create player WITHOUT years_with_team attribute
        player = Player(
            name="Unknown Tenure",
            number=91,
            primary_position="tight_end",
            player_id=3009
        )
        # Don't set years_with_team (tests getattr default=0)
        player.age = 27
        player.cap_hit = 3_000_000

        objective_value = 65.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, loyal_gm, rebuilding_context
        )

        # Expected: 65 * 1.0 = 65.0 (no tenure bonus, defaults to 0 years)
        assert modified_value == objective_value

    def test_missing_cap_hit_field(self, rebuilding_context):
        """Handle missing cap_hit field gracefully."""
        from team_management.players.player import Player

        # Create cap-conscious GM
        cap_gm = GMArchetype(
            name="Cap-Conscious GM",
            description="Watches cap",
            loyalty=0.5,
            cap_management=0.9,
            veteran_preference=0.5
        )

        # Create player WITHOUT cap_hit attribute
        player = Player(
            name="Unknown Cap Hit",
            number=90,
            primary_position="offensive_tackle",
            player_id=3010
        )
        player.years_with_team = 2
        player.age = 26
        # Don't set cap_hit (tests getattr default=0)

        objective_value = 70.0

        modified_value = PersonalityModifiers.apply_roster_cut_modifier(
            player, objective_value, cap_gm, rebuilding_context
        )

        # Expected: 70 * 1.0 = 70.0 (no cap discount, defaults to $0)
        assert modified_value == objective_value
