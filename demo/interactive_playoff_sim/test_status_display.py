#!/usr/bin/env python3
"""
Test Status Display in Interactive Playoff Simulator

Validates that the status display works correctly without errors.
"""

import sys
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from interactive_playoff_sim import InteractivePlayoffSimulator


def main():
    """Test status display."""
    print("Testing Status Display in Interactive Playoff Simulator...")
    print("="*80)

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_status_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize simulator
        print("\n1. Initializing simulator...")
        simulator = InteractivePlayoffSimulator(
            dynasty_id="status_test_dynasty",
            database_path=temp_db_path,
            season_year=2024
        )
        print("✅ Simulator initialized successfully")

        # Test display_current_status (this is what was failing)
        print("\n2. Testing display_current_status()...")
        print("="*80)
        try:
            simulator.display_current_status()
            print("="*80)
            print("✅ Status display works without errors")
        except Exception as e:
            print(f"❌ Status display failed: {e}")
            raise

        # Test that controller state is accessible
        print("\n3. Verifying controller state...")
        state = simulator.controller.get_current_state()
        print(f"   Current round: {state['current_round']}")
        print(f"   Games played: {state['games_played']}")
        print(f"   Current date: {state['current_date']}")
        print("✅ Controller state accessible")

        print("\n" + "="*80)
        print("✅ ALL STATUS DISPLAY TESTS PASSED")
        print("="*80)
        print("\nThe print_status() function now works correctly!")

    finally:
        # Cleanup
        import os
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
            print(f"\n🗑️  Cleaned up temporary database: {temp_db_path}")


if __name__ == "__main__":
    main()
