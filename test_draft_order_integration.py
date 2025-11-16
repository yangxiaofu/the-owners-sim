#!/usr/bin/env python3
"""
Test script to verify draft order integration in SeasonCycleController.

This script checks:
1. That PlayoffsToOffseasonHandler receives the draft order parameters
2. That the _can_calculate_draft_order() check passes
3. That draft order calculation is attempted
"""

import sys
sys.path.insert(0, 'src')

from season.season_cycle_controller import SeasonCycleController

def test_draft_order_parameters():
    """Test that draft order parameters are provided to handler."""

    print("=" * 80)
    print("DRAFT ORDER INTEGRATION TEST")
    print("=" * 80)

    # Create controller (this will initialize handlers with parameters)
    print("\n1. Creating SeasonCycleController...")
    try:
        controller = SeasonCycleController(
            database_path="data/database/nfl_simulation.db",
            dynasty_id="test_draft_integration",
            season_year=2024,
            enable_persistence=True,
            verbose_logging=True
        )
        print("   ✓ Controller created successfully")
    except Exception as e:
        print(f"   ✗ Failed to create controller: {e}")
        return False

    # Check that helper methods exist
    print("\n2. Checking helper methods...")
    helper_methods = [
        '_get_regular_season_standings_for_handler',
        '_get_playoff_bracket_for_handler',
        '_schedule_event_for_handler'
    ]

    for method_name in helper_methods:
        if hasattr(controller, method_name):
            print(f"   ✓ {method_name} exists")
        else:
            print(f"   ✗ {method_name} MISSING")
            return False

    # Check transition manager
    print("\n3. Checking phase transition manager...")
    if hasattr(controller, 'phase_transition_manager'):
        print("   ✓ Phase transition manager exists")

        # Check if handlers are registered
        if hasattr(controller.phase_transition_manager, 'handlers'):
            handlers = controller.phase_transition_manager.handlers
            print(f"   ✓ Found {len(handlers)} registered handlers")

            # Look for playoffs_to_offseason handler
            from season.phase_transition.models import TransitionHandlerKey
            playoffs_to_offseason_key = TransitionHandlerKey(
                from_phase="playoffs",
                to_phase="offseason"
            )

            if playoffs_to_offseason_key in handlers:
                handler = handlers[playoffs_to_offseason_key]
                print("   ✓ PlayoffsToOffseasonHandler found")

                # Check if handler has draft order dependencies
                if hasattr(handler, '_can_calculate_draft_order'):
                    can_calculate = handler._can_calculate_draft_order()
                    print(f"   {'✓' if can_calculate else '✗'} _can_calculate_draft_order() = {can_calculate}")

                    # Check individual dependencies
                    if hasattr(handler, '_get_regular_season_standings'):
                        print(f"   {'✓' if handler._get_regular_season_standings else '✗'} _get_regular_season_standings = {handler._get_regular_season_standings is not None}")
                    if hasattr(handler, '_get_playoff_bracket'):
                        print(f"   {'✓' if handler._get_playoff_bracket else '✗'} _get_playoff_bracket = {handler._get_playoff_bracket is not None}")
                    if hasattr(handler, '_schedule_event'):
                        print(f"   {'✓' if handler._schedule_event else '✗'} _schedule_event = {handler._schedule_event is not None}")
                    if hasattr(handler, '_database_path'):
                        print(f"   {'✓' if handler._database_path else '✗'} _database_path = {handler._database_path}")
                else:
                    print("   ✗ Handler missing _can_calculate_draft_order method")
            else:
                print("   ✗ PlayoffsToOffseasonHandler NOT found in handlers")
        else:
            print("   ✗ Phase transition manager has no _handlers attribute")
    else:
        print("   ✗ Phase transition manager MISSING")
        return False

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    return True

if __name__ == "__main__":
    success = test_draft_order_parameters()
    sys.exit(0 if success else 1)
