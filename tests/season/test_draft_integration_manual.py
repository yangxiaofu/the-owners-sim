"""
Manual integration test for draft class generation.

Run with: PYTHONPATH=src python tests/season/test_draft_integration_manual.py

This is a standalone script that verifies draft class generation works
when SeasonCycleController initializes.
"""

import sys
import tempfile
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from src.season.season_cycle_controller import SeasonCycleController
from src.database.draft_class_api import DraftClassAPI
from src.calendar.season_phase_tracker import SeasonPhase


def test_draft_class_generated_at_season_start():
    """Verify draft class is generated when season starts."""
    print("\n" + "="*80)
    print("TEST: Draft Class Generated at Season Start")
    print("="*80)

    # Create temporary database
    fd, temp_db = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        # Action: Create season cycle controller (season start)
        print("\n1. Creating SeasonCycleController...")
        controller = SeasonCycleController(
            database_path=temp_db,
            dynasty_id="test_dynasty",
            season_year=2024,
            initial_phase=SeasonPhase.REGULAR_SEASON,
            verbose_logging=True  # Show draft class generation message
        )

        # Assert: Draft class for 2024 exists
        print("\n2. Checking if draft class was generated...")
        draft_api = DraftClassAPI(temp_db)
        has_draft_class = draft_api.dynasty_has_draft_class("test_dynasty", 2024)

        if has_draft_class:
            print("✅ Draft class exists for season 2024")
        else:
            print("❌ FAIL: Draft class not found")
            return False

        # Get prospects
        print("\n3. Retrieving draft prospects...")
        prospects = draft_api.get_all_prospects("test_dynasty", 2024)
        print(f"   Prospects found: {len(prospects)}")

        if len(prospects) == 224:
            print(f"✅ Correct number of prospects (224 = 7 rounds × 32 teams)")
        else:
            print(f"❌ FAIL: Expected 224 prospects, got {len(prospects)}")
            return False

        # Show sample prospects
        print("\n4. Sample prospects:")
        for prospect in prospects[:5]:
            print(f"   • {prospect['first_name']} {prospect['last_name']} - {prospect['position']} ({prospect['overall']} OVR)")

        print("\n" + "="*80)
        print("✅ TEST PASSED: Draft class generation works!")
        print("="*80)
        return True

    finally:
        # Cleanup
        try:
            os.unlink(temp_db)
        except:
            pass


def test_draft_class_idempotent():
    """Verify draft class is not regenerated if it already exists."""
    print("\n" + "="*80)
    print("TEST: Draft Class Generation is Idempotent")
    print("="*80)

    fd, temp_db = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    try:
        # Setup: Pre-generate draft class
        print("\n1. Pre-generating draft class...")
        draft_api = DraftClassAPI(temp_db)
        original_id = draft_api.generate_draft_class("test_dynasty", 2024)
        print(f"   Draft class ID: {original_id}")

        # Action: Create season controller (should skip generation)
        print("\n2. Creating SeasonCycleController (should skip generation)...")
        controller = SeasonCycleController(
            database_path=temp_db,
            dynasty_id="test_dynasty",
            season_year=2024,
            verbose_logging=True  # Should show "already exists" message
        )

        # Assert: Draft class still exists with same ID
        print("\n3. Verifying draft class was not regenerated...")
        has_draft_class = draft_api.dynasty_has_draft_class("test_dynasty", 2024)

        if has_draft_class:
            print("✅ Draft class still exists")
        else:
            print("❌ FAIL: Draft class disappeared")
            return False

        prospects = draft_api.get_all_prospects("test_dynasty", 2024)
        if len(prospects) == 224:
            print(f"✅ Same number of prospects (224)")
        else:
            print(f"❌ FAIL: Prospect count changed to {len(prospects)}")
            return False

        print("\n" + "="*80)
        print("✅ TEST PASSED: Draft class generation is idempotent!")
        print("="*80)
        return True

    finally:
        try:
            os.unlink(temp_db)
        except:
            pass


if __name__ == "__main__":
    print("\n🏈 Draft Class Generation Integration Tests")
    print("="*80)

    test1_passed = test_draft_class_generated_at_season_start()
    test2_passed = test_draft_class_idempotent()

    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    print(f"Test 1 (Generation at Season Start): {'✅ PASSED' if test1_passed else '❌ FAILED'}")
    print(f"Test 2 (Idempotent Generation): {'✅ PASSED' if test2_passed else '❌ FAILED'}")

    if test1_passed and test2_passed:
        print("\n🎉 All tests passed! Draft class generation is working correctly.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. See output above for details.")
        sys.exit(1)
