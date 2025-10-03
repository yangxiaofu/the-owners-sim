#!/usr/bin/env python3
"""
Quick Test of Interactive Playoff Simulator

Tests that the simulator initializes correctly without manual input.
"""

import sys
from pathlib import Path
import tempfile

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from interactive_playoff_sim import InteractivePlayoffSimulator

def main():
    """Test simulator initialization."""
    print("Testing Interactive Playoff Simulator...")

    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_playoff_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        # Initialize simulator
        print("\n1. Initializing simulator...")
        simulator = InteractivePlayoffSimulator(
            dynasty_id="test_dynasty",
            database_path=temp_db_path,
            season_year=2024
        )
        print("✅ Simulator initialized successfully")

        # Test get_current_bracket
        print("\n2. Getting current bracket...")
        bracket = simulator.controller.get_current_bracket()
        assert bracket is not None
        assert 'current_round' in bracket
        assert bracket['current_round'] == 'wild_card'
        print(f"✅ Current round: {bracket['current_round']}")

        # Test bracket contains PlayoffBracket object
        print("\n3. Checking wild card bracket...")
        wild_card_bracket = bracket['wild_card']
        assert wild_card_bracket is not None
        assert hasattr(wild_card_bracket, 'round_name')
        assert hasattr(wild_card_bracket, 'games')
        print(f"✅ Wild card bracket: {len(wild_card_bracket.games)} games")

        # Test original seeding
        print("\n4. Checking original seeding...")
        seeding = bracket['original_seeding']
        assert seeding is not None
        assert len(seeding.afc.seeds) == 7
        assert len(seeding.nfc.seeds) == 7
        print(f"✅ Seeding: {len(seeding.afc.seeds)} AFC + {len(seeding.nfc.seeds)} NFC teams")

        # Test controller state
        print("\n5. Checking controller state...")
        state = simulator.controller.get_current_state()
        assert 'current_date' in state
        assert 'current_round' in state
        assert 'games_played' in state
        print(f"✅ Controller state: {state['current_round']} round, {state['games_played']} games played")

        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print("\nThe interactive playoff simulator is working correctly!")
        print("\nTo run interactively:")
        print("  PYTHONPATH=src python demo/interactive_playoff_sim/interactive_playoff_sim.py")

    finally:
        # Cleanup
        import os
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)
            print(f"\n🗑️  Cleaned up temporary database: {temp_db_path}")


if __name__ == "__main__":
    main()
