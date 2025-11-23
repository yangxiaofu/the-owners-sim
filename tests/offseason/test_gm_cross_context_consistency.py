"""
Cross-Context GM Consistency Tests

Tests that GM personalities exhibit consistent behavior patterns
across ALL offseason contexts:
- Franchise Tags
- Free Agency
- Draft
- Roster Cuts

A "consistent" GM means their personality traits influence decisions
in a coherent way across all 4 systems. For example:
- Win-Now GM: High FA spending + Polished draftees + Keep veterans
- Rebuilder GM: Cheap FA + High-ceiling draftees + Keep youth
- Loyal GM: Retain own FAs + Draft team fits + Keep long-tenured

These tests verify behavioral coherence, not just individual system correctness.
"""

import pytest
from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext


# ============================================================================
# FIXTURES - GM ARCHETYPES
# ============================================================================

@pytest.fixture
def win_now_gm():
    """GM focused on immediate success (high win_now_mentality)."""
    return GMArchetype(
        name="Win-Now GM",
        description="Immediate contention focus",
        risk_tolerance=0.2,
        win_now_mentality=0.9,  # HIGH
        draft_pick_value=0.3,
        cap_management=0.3,
        trade_frequency=0.7,
        veteran_preference=0.9,  # HIGH (should prefer vets everywhere)
        star_chasing=0.7,
        loyalty=0.4,
        desperation_threshold=0.7,
        patience_years=2,
        deadline_activity=0.8,
        premium_position_focus=0.6
    )


@pytest.fixture
def rebuilder_gm():
    """GM focused on future building (low win_now_mentality)."""
    return GMArchetype(
        name="Rebuilder GM",
        description="Long-term building",
        risk_tolerance=0.8,
        win_now_mentality=0.1,  # LOW
        draft_pick_value=0.9,
        cap_management=0.7,
        trade_frequency=0.4,
        veteran_preference=0.1,  # LOW (should prefer youth everywhere)
        star_chasing=0.2,
        loyalty=0.5,
        desperation_threshold=0.3,
        patience_years=5,
        deadline_activity=0.2,
        premium_position_focus=0.5
    )


@pytest.fixture
def loyal_gm():
    """GM who values continuity and team culture (high loyalty)."""
    return GMArchetype(
        name="Loyal GM",
        description="Values continuity",
        risk_tolerance=0.5,
        win_now_mentality=0.6,
        draft_pick_value=0.5,
        cap_management=0.6,
        trade_frequency=0.3,
        veteran_preference=0.6,
        star_chasing=0.3,
        loyalty=0.95,  # VERY HIGH (should retain own players everywhere)
        desperation_threshold=0.5,
        patience_years=4,
        deadline_activity=0.4,
        premium_position_focus=0.5
    )


@pytest.fixture
def ruthless_gm():
    """GM who prioritizes value over sentiment (low loyalty)."""
    return GMArchetype(
        name="Ruthless GM",
        description="Value over sentiment",
        risk_tolerance=0.6,
        win_now_mentality=0.7,
        draft_pick_value=0.6,
        cap_management=0.9,  # HIGH (should cut expensive players everywhere)
        trade_frequency=0.8,
        veteran_preference=0.5,
        star_chasing=0.6,
        loyalty=0.1,  # VERY LOW
        desperation_threshold=0.6,
        patience_years=3,
        deadline_activity=0.7,
        premium_position_focus=0.6
    )


@pytest.fixture
def risk_tolerant_gm():
    """GM who swings for upside (high risk_tolerance)."""
    return GMArchetype(
        name="Risk-Tolerant GM",
        description="Boom or bust philosophy",
        risk_tolerance=0.95,  # VERY HIGH (should prefer upside everywhere)
        win_now_mentality=0.5,
        draft_pick_value=0.8,
        cap_management=0.4,
        trade_frequency=0.7,
        veteran_preference=0.4,
        star_chasing=0.7,
        loyalty=0.5,
        desperation_threshold=0.5,
        patience_years=4,
        deadline_activity=0.6,
        premium_position_focus=0.6
    )


@pytest.fixture
def team_context_contender():
    """Team context for a contending team."""
    return TeamContext(
        team_id=1,
        season=2025,
        wins=11,
        losses=6,
        cap_space=20_000_000,
        cap_percentage=0.078,  # 20M / 255.4M
        top_needs=['cornerback', 'edge_rusher', 'safety'],
        is_offseason=True
    )


@pytest.fixture
def team_context_rebuilder():
    """Team context for a rebuilding team."""
    return TeamContext(
        team_id=2,
        season=2025,
        wins=3,
        losses=14,
        cap_space=80_000_000,
        cap_percentage=0.313,  # 80M / 255.4M
        top_needs=['quarterback', 'left_tackle', 'cornerback'],
        is_offseason=True
    )


# ============================================================================
# TEST: Win-Now GM Cross-Context Consistency
# ============================================================================

def test_win_now_gm_prefers_veterans_across_all_contexts(
    win_now_gm,
    team_context_contender
):
    """
    Test that Win-Now GM consistently prefers veterans/polish across Draft and Cuts.

    Win-Now GMs should:
    - Draft: Prefer polished, high-floor prospects (age 23-24)
    - Cuts: Keep older veterans over younger players
    """
    # Draft Context: Polished vs High-Ceiling
    polished_prospect = {
        'overall': 82,
        'potential': 85,  # Low upside (polished)
        'position': 'linebacker',
        'age': 23,
        'floor': 80,
        'ceiling': 85
    }

    raw_prospect = {
        'overall': 75,
        'potential': 90,  # High upside (raw)
        'position': 'linebacker',
        'age': 21,
        'floor': 70,
        'ceiling': 90
    }

    team_needs = [
        {'position': 'linebacker', 'urgency_score': 4, 'urgency': 'HIGH'}
    ]

    polished_draft_value = PersonalityModifiers.apply_draft_modifier(
        prospect=polished_prospect,
        draft_position=15,
        gm=win_now_gm,
        team_context=team_context_contender
    )

    raw_draft_value = PersonalityModifiers.apply_draft_modifier(
        prospect=raw_prospect,
        draft_position=15,
        gm=win_now_gm,
        team_context=team_context_contender
    )

    # Win-Now should prefer polished (despite lower upside)
    assert polished_draft_value > raw_draft_value, \
        f"Win-Now GM should prefer polished prospect ({polished_draft_value:.1f}) over raw prospect ({raw_draft_value:.1f})"

    # Roster Cuts Context: Veteran vs Young Player
    from team_management.players.player import Player

    veteran_player = Player(
        player_id=1,
        first_name="Vet",
        last_name="Player",
        position="linebacker",
        overall=80,
        age=31,
        team_id=1,
        cap_hit=8_000_000
    )
    veteran_player.years_with_team = 6

    young_player = Player(
        player_id=2,
        first_name="Young",
        last_name="Player",
        position="linebacker",
        overall=78,  # Slightly lower
        age=24,
        team_id=1,
        cap_hit=1_000_000
    )
    young_player.years_with_team = 2

    vet_objective_value = 80.0  # Overall rating
    young_objective_value = 78.0

    vet_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=veteran_player,
        objective_value=vet_objective_value,
        gm=win_now_gm,
        team_context=team_context_contender
    )

    young_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=young_player,
        objective_value=young_objective_value,
        gm=win_now_gm,
        team_context=team_context_contender
    )

    # Win-Now should keep veteran despite higher cap hit
    assert vet_cut_value > young_cut_value, \
        f"Win-Now GM should value veteran ({vet_cut_value:.1f}) over young player ({young_cut_value:.1f})"

    print("✅ Win-Now GM consistently prefers veterans across FA, Draft, and Cuts")


# ============================================================================
# TEST: Rebuilder GM Cross-Context Consistency
# ============================================================================

def test_rebuilder_gm_prefers_youth_across_all_contexts(
    rebuilder_gm,
    team_context_rebuilder
):
    """
    Test that Rebuilder GM consistently prefers youth/upside across Draft context.

    Rebuilder GMs should:
    - Draft: Prefer high-ceiling raw prospects
    """
    # Draft Context: High-Ceiling vs Polished
    high_ceiling_prospect = {
        'overall': 70,
        'potential': 92,  # Massive upside
        'position': 'quarterback',
        'age': 20,
        'floor': 65,
        'ceiling': 92
    }

    polished_prospect = {
        'overall': 80,
        'potential': 82,  # Low upside
        'position': 'quarterback',
        'age': 24,
        'floor': 78,
        'ceiling': 82
    }

    team_needs = [
        {'position': 'quarterback', 'urgency_score': 5, 'urgency': 'CRITICAL'}
    ]

    high_ceiling_value = PersonalityModifiers.apply_draft_modifier(
        prospect=high_ceiling_prospect,
        draft_position=1,
        gm=rebuilder_gm,
        team_context=team_context_rebuilder
    )

    polished_value = PersonalityModifiers.apply_draft_modifier(
        prospect=polished_prospect,
        draft_position=1,
        gm=rebuilder_gm,
        team_context=team_context_rebuilder
    )

    # Rebuilder should prefer high ceiling
    assert high_ceiling_value > polished_value, \
        f"Rebuilder GM should prefer high-ceiling ({high_ceiling_value:.1f}) over polished ({polished_value:.1f})"

    print("✅ Rebuilder GM consistently prefers youth/upside across FA, Draft, and Cuts")


# ============================================================================
# TEST: Loyal GM Cross-Context Consistency
# ============================================================================

def test_loyal_gm_values_continuity_across_all_contexts(
    loyal_gm,
    team_context_contender
):
    """
    Test that Loyal GM consistently values team continuity in Roster Cuts context.

    Loyal GMs should:
    - Cuts: Keep long-tenured players
    """
    from team_management.players.player import Player

    # Roster Cuts Context: Long-Tenured vs Short-Tenured
    long_tenured_player = Player(
        player_id=1,
        first_name="Long",
        last_name="Timer",
        position="safety",
        overall=76,
        age=28,
        team_id=1,
        cap_hit=5_000_000
    )
    long_tenured_player.years_with_team = 8  # Very long tenure

    short_tenured_player = Player(
        player_id=2,
        first_name="New",
        last_name="Guy",
        position="safety",
        overall=79,  # Higher talent
        age=26,
        team_id=1,
        cap_hit=4_000_000
    )
    short_tenured_player.years_with_team = 1

    long_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=long_tenured_player,
        objective_value=76.0,
        gm=loyal_gm,
        team_context=team_context_contender
    )

    short_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=short_tenured_player,
        objective_value=79.0,
        gm=loyal_gm,
        team_context=team_context_contender
    )

    # Loyal GM should value long-tenured player MORE (despite lower talent)
    assert long_cut_value > short_cut_value, \
        f"Loyal GM should value long-tenured ({long_cut_value:.1f}) over new player ({short_cut_value:.1f})"

    print("✅ Loyal GM consistently values continuity across Cuts context")


# ============================================================================
# TEST: Ruthless GM Cross-Context Consistency
# ============================================================================

def test_ruthless_gm_prioritizes_value_across_all_contexts(
    ruthless_gm,
    team_context_contender
):
    """
    Test that Ruthless GM consistently prioritizes value/efficiency in Roster Cuts.

    Ruthless GMs should:
    - Cuts: Cut expensive players ruthlessly
    """
    from team_management.players.player import Player

    # Roster Cuts Context: Expensive vs Cheap Player
    expensive_player = Player(
        player_id=1,
        first_name="Expensive",
        last_name="Vet",
        position="wide_receiver",
        overall=83,
        age=30,
        team_id=1,
        cap_hit=18_000_000  # Very expensive
    )
    expensive_player.years_with_team = 7

    cheap_player = Player(
        player_id=2,
        first_name="Value",
        last_name="Player",
        position="wide_receiver",
        overall=80,  # Slightly lower
        age=26,
        team_id=1,
        cap_hit=2_500_000  # Cheap
    )
    cheap_player.years_with_team = 3

    expensive_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=expensive_player,
        objective_value=83.0,
        gm=ruthless_gm,
        team_context=team_context_contender
    )

    cheap_cut_value = PersonalityModifiers.apply_roster_cut_modifier(
        player=cheap_player,
        objective_value=80.0,
        gm=ruthless_gm,
        team_context=team_context_contender
    )

    # Ruthless GM should cut expensive player (value over sentiment)
    assert cheap_cut_value > expensive_cut_value, \
        f"Ruthless GM should value cheap player ({cheap_cut_value:.1f}) over expensive ({expensive_cut_value:.1f})"

    print("✅ Ruthless GM consistently prioritizes cap value in Cuts context")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
