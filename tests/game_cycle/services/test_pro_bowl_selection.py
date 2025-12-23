"""
Unit tests for Pro Bowl selection system.

Tests verify:
- Roster size matches real NFL (44 per conference)
- Position slot counts match real NFL
- Position mapping works correctly
- Voting component weights sum to 1.0
- Special teams benchmarks are defined
"""

import pytest
from game_cycle.services.awards_service import PRO_BOWL_SLOTS, PRO_BOWL_POSITION_MAPPING


def test_pro_bowl_roster_size():
    """Verify total roster size is 44 per conference (matches real NFL 2025)."""
    total = sum(PRO_BOWL_SLOTS.values())
    assert total == 44, f"Expected 44 slots per conference, got {total}"


def test_pro_bowl_position_counts():
    """Verify individual position slot counts match real NFL."""
    # Offense (21 total)
    assert PRO_BOWL_SLOTS['QB'] == 3, "Should have 3 QB slots"
    assert PRO_BOWL_SLOTS['RB'] == 3, "Should have 3 RB slots"
    assert PRO_BOWL_SLOTS['FB'] == 1, "Should have 1 FB slot"
    assert PRO_BOWL_SLOTS['WR'] == 4, "Should have 4 WR slots"
    assert PRO_BOWL_SLOTS['TE'] == 2, "Should have 2 TE slots"

    # OL (8 total: 3 OT, 3 OG, 2 C)
    assert PRO_BOWL_SLOTS['OT'] == 3, "Should have 3 OT slots (consolidated from LT/RT)"
    assert PRO_BOWL_SLOTS['OG'] == 3, "Should have 3 OG slots (consolidated from LG/RG)"
    assert PRO_BOWL_SLOTS['C'] == 2, "Should have 2 C slots"

    # Defense (18 total)
    assert PRO_BOWL_SLOTS['DE'] == 3, "Should have 3 DE slots"
    assert PRO_BOWL_SLOTS['DT'] == 3, "Should have 3 DT slots"
    assert PRO_BOWL_SLOTS['OLB'] == 3, "Should have 3 OLB slots (consolidated from LOLB/ROLB)"
    assert PRO_BOWL_SLOTS['ILB'] == 2, "Should have 2 ILB slots"
    assert PRO_BOWL_SLOTS['CB'] == 4, "Should have 4 CB slots"
    assert PRO_BOWL_SLOTS['FS'] == 1, "Should have 1 FS slot"
    assert PRO_BOWL_SLOTS['SS'] == 2, "Should have 2 SS slots"

    # Special Teams (5 total)
    assert PRO_BOWL_SLOTS['K'] == 1, "Should have 1 K slot"
    assert PRO_BOWL_SLOTS['P'] == 1, "Should have 1 P slot"
    assert PRO_BOWL_SLOTS['LS'] == 1, "Should have 1 LS slot (new)"
    assert PRO_BOWL_SLOTS['RS'] == 1, "Should have 1 RS slot (new)"
    assert PRO_BOWL_SLOTS['ST'] == 1, "Should have 1 ST slot (new)"


def test_pro_bowl_position_mapping():
    """Verify all Pro Bowl positions have proper mappings."""
    for position in PRO_BOWL_SLOTS.keys():
        assert position in PRO_BOWL_POSITION_MAPPING, \
            f"Missing position mapping for {position}"

        # Verify mapping is a list
        assert isinstance(PRO_BOWL_POSITION_MAPPING[position], list), \
            f"Position mapping for {position} should be a list"

        # Verify mapping is not empty
        assert len(PRO_BOWL_POSITION_MAPPING[position]) > 0, \
            f"Position mapping for {position} should not be empty"


def test_consolidated_position_mappings():
    """Verify consolidated positions map to multiple player positions."""
    # Offensive tackles should include both LT and RT
    assert 'LT' in PRO_BOWL_POSITION_MAPPING['OT'], "OT should map to LT"
    assert 'RT' in PRO_BOWL_POSITION_MAPPING['OT'], "OT should map to RT"

    # Offensive guards should include both LG and RG
    assert 'LG' in PRO_BOWL_POSITION_MAPPING['OG'], "OG should map to LG"
    assert 'RG' in PRO_BOWL_POSITION_MAPPING['OG'], "OG should map to RG"

    # Defensive ends should include EDGE
    assert 'EDGE' in PRO_BOWL_POSITION_MAPPING['DE'], "DE should map to EDGE"

    # Outside linebackers should include LOLB and ROLB
    assert 'LOLB' in PRO_BOWL_POSITION_MAPPING['OLB'], "OLB should map to LOLB"
    assert 'ROLB' in PRO_BOWL_POSITION_MAPPING['OLB'], "OLB should map to ROLB"

    # Inside linebackers should include MLB
    assert 'MLB' in PRO_BOWL_POSITION_MAPPING['ILB'], "ILB should map to MLB"

    # Return specialist should include both KR and PR
    assert 'KR' in PRO_BOWL_POSITION_MAPPING['RS'], "RS should map to KR"
    assert 'PR' in PRO_BOWL_POSITION_MAPPING['RS'], "RS should map to PR"


def test_voting_component_weights():
    """Verify voting component weights sum to 1.0."""
    from game_cycle.services.awards.award_criteria import (
        FanVotingComponent,
        PlayerVotingComponent,
        CoachVotingComponent
    )

    components = [
        ('FanVotingComponent', FanVotingComponent()),
        ('PlayerVotingComponent', PlayerVotingComponent()),
        ('CoachVotingComponent', CoachVotingComponent()),
    ]

    for name, component in components:
        total = (
            component.STATS_WEIGHT +
            component.GRADE_WEIGHT +
            getattr(component, 'TEAM_SUCCESS_WEIGHT', 0) +
            getattr(component, 'POSITIONAL_VALUE_WEIGHT', 0) +
            getattr(component, 'FILM_GRADE_WEIGHT', 0)
        )
        assert abs(total - 1.0) < 0.01, \
            f"{name} weights don't sum to 1.0: {total} " \
            f"(STATS={component.STATS_WEIGHT}, " \
            f"GRADE={component.GRADE_WEIGHT}, " \
            f"other={total - component.STATS_WEIGHT - component.GRADE_WEIGHT})"


def test_fan_voting_weights():
    """Verify fan voting component has stats-heavy weighting."""
    from game_cycle.services.awards.award_criteria import FanVotingComponent

    fan = FanVotingComponent()
    assert fan.STATS_WEIGHT == 0.70, "Fan voting should weight stats at 70%"
    assert fan.GRADE_WEIGHT == 0.20, "Fan voting should weight grade at 20%"
    assert fan.TEAM_SUCCESS_WEIGHT == 0.10, "Fan voting should weight team success at 10%"


def test_player_voting_weights():
    """Verify player voting component has grade-heavy weighting."""
    from game_cycle.services.awards.award_criteria import PlayerVotingComponent

    player = PlayerVotingComponent()
    assert player.STATS_WEIGHT == 0.30, "Player voting should weight stats at 30%"
    assert player.GRADE_WEIGHT == 0.60, "Player voting should weight grade at 60%"
    assert player.POSITIONAL_VALUE_WEIGHT == 0.10, "Player voting should weight positional value at 10%"


def test_coach_voting_weights():
    """Verify coach voting component has balanced weighting."""
    from game_cycle.services.awards.award_criteria import CoachVotingComponent

    coach = CoachVotingComponent()
    assert coach.STATS_WEIGHT == 0.40, "Coach voting should weight stats at 40%"
    assert coach.GRADE_WEIGHT == 0.50, "Coach voting should weight grade at 50%"
    assert coach.FILM_GRADE_WEIGHT == 0.10, "Coach voting should weight film grade at 10%"


def test_special_teams_benchmarks():
    """Verify special teams benchmarks are defined."""
    from game_cycle.services.awards.award_criteria import (
        LS_BENCHMARKS,
        RS_BENCHMARKS,
        ST_BENCHMARKS
    )

    # Long Snapper benchmarks
    assert 'special_teams_grade' in LS_BENCHMARKS, \
        "LS_BENCHMARKS should include special_teams_grade"
    assert 'elite' in LS_BENCHMARKS['special_teams_grade'], \
        "LS special_teams_grade should have elite benchmark"
    assert 'good' in LS_BENCHMARKS['special_teams_grade'], \
        "LS special_teams_grade should have good benchmark"
    assert 'average' in LS_BENCHMARKS['special_teams_grade'], \
        "LS special_teams_grade should have average benchmark"

    # Return Specialist benchmarks
    assert 'return_yards' in RS_BENCHMARKS, \
        "RS_BENCHMARKS should include return_yards"
    assert 'return_tds' in RS_BENCHMARKS, \
        "RS_BENCHMARKS should include return_tds"
    assert 'yards_per_return' in RS_BENCHMARKS, \
        "RS_BENCHMARKS should include yards_per_return"

    # Special Teamer benchmarks
    assert 'special_teams_tackles' in ST_BENCHMARKS, \
        "ST_BENCHMARKS should include special_teams_tackles"
    assert 'special_teams_grade' in ST_BENCHMARKS, \
        "ST_BENCHMARKS should include special_teams_grade"


def test_return_specialist_benchmarks_realistic():
    """Verify return specialist benchmarks are realistic for 18-game season."""
    from game_cycle.services.awards.award_criteria import RS_BENCHMARKS

    # Elite return yards should be achievable but challenging
    assert 1000 <= RS_BENCHMARKS['return_yards']['elite'] <= 1500, \
        "Elite return yards should be 1000-1500 for 18-game season"

    # Elite return TDs should be rare but possible
    assert RS_BENCHMARKS['return_tds']['elite'] >= 2, \
        "Elite return TDs should be at least 2"

    # Elite yards per return should reflect NFL standards
    assert 10.0 <= RS_BENCHMARKS['yards_per_return']['elite'] <= 15.0, \
        "Elite yards per return should be 10-15 yards"


def test_special_teamer_benchmarks_realistic():
    """Verify special teamer benchmarks are realistic."""
    from game_cycle.services.awards.award_criteria import ST_BENCHMARKS

    # Elite special teams tackles for 18-game season
    assert 15 <= ST_BENCHMARKS['special_teams_tackles']['elite'] <= 25, \
        "Elite ST tackles should be 15-25 for 18-game season"

    # Special teams grade should use standard grading scale
    assert ST_BENCHMARKS['special_teams_grade']['elite'] >= 80.0, \
        "Elite ST grade should be 80+ on PFF scale"


def test_effective_voting_weights():
    """Verify effective weights after 33.3% voting simulation."""
    # With 33.3% each voting component:
    # Stats: 0.70 * 0.333 + 0.30 * 0.333 + 0.40 * 0.333 = 0.4662 (~47%)
    # Grade: 0.20 * 0.333 + 0.60 * 0.333 + 0.50 * 0.333 = 0.4329 (~43%)
    # Other: remaining ~10%

    from game_cycle.services.awards.award_criteria import (
        FanVotingComponent,
        PlayerVotingComponent,
        CoachVotingComponent
    )

    fan = FanVotingComponent()
    player = PlayerVotingComponent()
    coach = CoachVotingComponent()

    # Effective stats weight
    stats_effective = (fan.STATS_WEIGHT + player.STATS_WEIGHT + coach.STATS_WEIGHT) / 3
    assert 0.45 <= stats_effective <= 0.50, \
        f"Effective stats weight should be ~47%, got {stats_effective:.1%}"

    # Effective grade weight
    grade_effective = (fan.GRADE_WEIGHT + player.GRADE_WEIGHT + coach.GRADE_WEIGHT) / 3
    assert 0.40 <= grade_effective <= 0.45, \
        f"Effective grade weight should be ~43%, got {grade_effective:.1%}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
