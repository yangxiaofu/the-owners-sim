"""
Draft-Focused Cross-Context Consistency Tests

Simplified tests verifying GM personalities create consistent draft behaviors.

These tests validate that the same GM personality trait creates predictable
draft decisions across different scenarios.
"""

import pytest
from team_management.gm_archetype import GMArchetype
from transactions.personality_modifiers import PersonalityModifiers, TeamContext


@pytest.fixture
def win_now_gm():
    """GM focused on immediate success."""
    return GMArchetype(
        name="Win-Now GM",
        description="Immediate contention focus",
        risk_tolerance=0.2,
        win_now_mentality=0.9,
        draft_pick_value=0.3,
        cap_management=0.3,
        trade_frequency=0.7,
        veteran_preference=0.9,
        star_chasing=0.7,
        loyalty=0.4,
        desperation_threshold=0.7,
        patience_years=2,
        deadline_activity=0.8,
        premium_position_focus=0.6
    )


@pytest.fixture
def rebuilder_gm():
    """GM focused on future building."""
    return GMArchetype(
        name="Rebuilder GM",
        description="Long-term building",
        risk_tolerance=0.8,
        win_now_mentality=0.1,
        draft_pick_value=0.9,
        cap_management=0.7,
        trade_frequency=0.4,
        veteran_preference=0.1,
        star_chasing=0.2,
        loyalty=0.5,
        desperation_threshold=0.3,
        patience_years=5,
        deadline_activity=0.2,
        premium_position_focus=0.5
    )


@pytest.fixture
def team_context():
    """Generic team context."""
    return TeamContext(
        team_id=1,
        season=2025,
        wins=8,
        losses=9,
        cap_space=40_000_000,
        cap_percentage=0.157,
        top_needs=['cornerback', 'linebacker', 'quarterback'],
        is_offseason=True
    )


def test_win_now_gm_prefers_polished_prospects(win_now_gm, team_context):
    """
    Test that Win-Now GM consistently prefers polished, NFL-ready prospects.

    Win-Now GMs should prefer low-upside, high-floor prospects who can
    contribute immediately.
    """
    # Polished prospect: High floor, low ceiling, older
    polished = {
        'overall': 82,
        'potential': 85,
        'position': 'cornerback',
        'age': 23,
        'floor': 80,
        'ceiling': 85
    }

    # Raw prospect: Low floor, high ceiling, younger
    raw = {
        'overall': 75,
        'potential': 90,
        'position': 'cornerback',
        'age': 20,
        'floor': 70,
        'ceiling': 90
    }

    polished_value = PersonalityModifiers.apply_draft_modifier(
        prospect=polished,
        draft_position=15,
        gm=win_now_gm,
        team_context=team_context
    )

    raw_value = PersonalityModifiers.apply_draft_modifier(
        prospect=raw,
        draft_position=15,
        gm=win_now_gm,
        team_context=team_context
    )

    # Win-Now should prefer polished despite lower upside
    assert polished_value > raw_value, \
        f"Win-Now GM should prefer polished ({polished_value:.1f}) over raw ({raw_value:.1f})"


def test_rebuilder_gm_not_penalized_for_high_upside(rebuilder_gm, team_context):
    """
    Test that Rebuilder GM does not heavily penalize high-ceiling prospects.

    Rebuilder GMs should be willing to draft raw talent with high upside,
    even if it means lower immediate contribution.

    Note: This test verifies that high-ceiling prospects are NOT heavily
    discounted by Rebuilder GMs (tolerance for upside).
    """
    # High-ceiling prospect
    high_ceiling = {
        'overall': 70,
        'potential': 90,
        'position': 'quarterback',
        'age': 20,
        'floor': 65,
        'ceiling': 90
    }

    # Polished prospect
    polished = {
        'overall': 80,
        'potential': 82,
        'position': 'quarterback',
        'age': 24,
        'floor': 78,
        'ceiling': 82
    }

    high_ceiling_value = PersonalityModifiers.apply_draft_modifier(
        prospect=high_ceiling,
        draft_position=1,
        gm=rebuilder_gm,
        team_context=team_context
    )

    polished_value = PersonalityModifiers.apply_draft_modifier(
        prospect=polished,
        draft_position=1,
        gm=rebuilder_gm,
        team_context=team_context
    )

    # Rebuilder should not penalize high-ceiling heavily
    # (may still prefer polished due to higher overall, but gap should be smaller than Win-Now)
    gap = polished_value - high_ceiling_value

    assert gap < 15.0, \
        f"Rebuilder GM should not heavily penalize high-ceiling prospect (gap: {gap:.1f} should be <15)"


def test_gm_modifiers_create_observable_differences(win_now_gm, rebuilder_gm, team_context):
    """
    Test that different GM archetypes produce observably different evaluations.

    The SAME prospect should be valued differently by Win-Now vs Rebuilder GMs.
    """
    # High-upside raw prospect
    raw_prospect = {
        'overall': 72,
        'potential': 88,
        'position': 'linebacker',
        'age': 21,
        'floor': 68,
        'ceiling': 88
    }

    win_now_value = PersonalityModifiers.apply_draft_modifier(
        prospect=raw_prospect,
        draft_position=20,
        gm=win_now_gm,
        team_context=team_context
    )

    rebuilder_value = PersonalityModifiers.apply_draft_modifier(
        prospect=raw_prospect,
        draft_position=20,
        gm=rebuilder_gm,
        team_context=team_context
    )

    # Values should differ (proving GM modifiers work)
    variance = abs(win_now_value - rebuilder_value) / max(win_now_value, rebuilder_value) * 100

    assert variance > 0, \
        f"GM modifiers should create variance, got {variance:.1f}% (Win-Now: {win_now_value:.1f}, Rebuilder: {rebuilder_value:.1f})"

    assert win_now_value != rebuilder_value, \
        f"Win-Now and Rebuilder should value prospects differently ({win_now_value:.1f} vs {rebuilder_value:.1f})"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
