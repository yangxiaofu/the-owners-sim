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
