#!/usr/bin/env python3
"""
Minimal test to verify draft order calculation after Super Bowl.

This creates a minimal scenario to test if draft order is calculated.
"""

import sys
sys.path.insert(0, 'src')

import logging

# Enable ALL logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from season.phase_transition.transition_handlers.playoffs_to_offseason import PlayoffsToOffseasonHandler
from season.phase_transition.models import PhaseTransition

def test_draft_order_calculation():
    """Test that draft order parameters enable calculation."""

    print("=" * 80)
    print("MINIMAL DRAFT ORDER TEST")
    print("=" * 80)

    # Create mock dependencies
    def mock_get_super_bowl_winner():
        return 1  # Chiefs

    def mock_schedule_offseason_events(year):
        print(f"[MOCK] Scheduling offseason events for {year}")

    def mock_generate_season_summary():
        return {
            "champion_team_id": 1,
            "season_year": 2024,
            "dynasty_id": "test"
        }

    def mock_update_database_phase(phase, year):
        print(f"[MOCK] Updating database phase to {phase} for {year}")

    # WITHOUT draft order parameters
    print("\n1. Testing handler WITHOUT draft order parameters...")
    handler_without = PlayoffsToOffseasonHandler(
        get_super_bowl_winner=mock_get_super_bowl_winner,
        schedule_offseason_events=mock_schedule_offseason_events,
        generate_season_summary=mock_generate_season_summary,
        update_database_phase=mock_update_database_phase,
        dynasty_id="test",
        season_year=2024,
        verbose_logging=True
    )

    can_calculate_without = handler_without._can_calculate_draft_order()
    print(f"   _can_calculate_draft_order() = {can_calculate_without}")
    print(f"   Expected: False")

    # WITH draft order parameters
    print("\n2. Testing handler WITH draft order parameters...")

    def mock_get_standings():
        # Return minimal 32-team standings
        return [
            {'team_id': i, 'wins': 8, 'losses': 9, 'ties': 0, 'win_percentage': 0.471}
            for i in range(1, 33)
        ]

    def mock_get_bracket():
        return {
            'wild_card_losers': [5, 8, 12, 15, 20, 24],
            'divisional_losers': [3, 7, 11, 16],
            'conference_losers': [2, 9],
            'super_bowl_loser': 14,
            'super_bowl_winner': 1
        }

    def mock_schedule_event(event):
        print(f"[MOCK] Scheduling event: {event.__class__.__name__}")

    handler_with = PlayoffsToOffseasonHandler(
        get_super_bowl_winner=mock_get_super_bowl_winner,
        schedule_offseason_events=mock_schedule_offseason_events,
        generate_season_summary=mock_generate_season_summary,
        update_database_phase=mock_update_database_phase,
        dynasty_id="test",
        season_year=2024,
        verbose_logging=True,
        get_regular_season_standings=mock_get_standings,
        get_playoff_bracket=mock_get_bracket,
        schedule_event=mock_schedule_event,
        database_path="data/database/nfl_simulation.db"
    )

    can_calculate_with = handler_with._can_calculate_draft_order()
    print(f"   _can_calculate_draft_order() = {can_calculate_with}")
    print(f"   Expected: True")

    print("\n" + "=" * 80)
    if can_calculate_without == False and can_calculate_with == True:
        print("✓ TEST PASSED: Draft order parameters work correctly")
    else:
        print("✗ TEST FAILED: Draft order parameters not working as expected")
    print("=" * 80)

if __name__ == "__main__":
    test_draft_order_calculation()
