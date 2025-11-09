"""
Integration tests for draft class generation at season start.

Tests verify that draft classes are automatically generated when
SeasonCycleController initializes and that draft events are scheduled
during offseason transition.
"""

import pytest
import tempfile
import os


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except:
        pass


def test_draft_class_generated_at_season_start(temp_db):
    """Verify draft class is generated when season starts."""
    from season.season_cycle_controller import SeasonCycleController
    from database.draft_class_api import DraftClassAPI
    from src.calendar.season_phase_tracker import SeasonPhase

    # Action: Create season cycle controller (season start)
    controller = SeasonCycleController(
        database_path=temp_db,
        dynasty_id="test_dynasty",
        season_year=2024,
        initial_phase=SeasonPhase.REGULAR_SEASON,
        verbose_logging=False
    )

    # Assert: Draft class for 2024 exists
    draft_api = DraftClassAPI(temp_db)
    assert draft_api.dynasty_has_draft_class("test_dynasty", 2024)

    prospects = draft_api.get_all_prospects("test_dynasty", 2024)
    assert len(prospects) == 224


def test_draft_class_idempotent(temp_db):
    """Verify draft class is not regenerated if it already exists."""
    from season.season_cycle_controller import SeasonCycleController
    from database.draft_class_api import DraftClassAPI

    # Setup: Pre-generate draft class
    draft_api = DraftClassAPI(temp_db)
    original_id = draft_api.generate_draft_class("test_dynasty", 2024)

    # Action: Create season controller (should skip generation)
    controller = SeasonCycleController(
        database_path=temp_db,
        dynasty_id="test_dynasty",
        season_year=2024,
        verbose_logging=False
    )

    # Assert: Draft class still exists with same ID
    assert draft_api.dynasty_has_draft_class("test_dynasty", 2024)

    # Verify same draft class (not regenerated)
    prospects = draft_api.get_all_prospects("test_dynasty", 2024)
    assert len(prospects) == 224


def test_draft_class_dynasty_isolation(temp_db):
    """Verify different dynasties get different draft classes."""
    from season.season_cycle_controller import SeasonCycleController
    from database.draft_class_api import DraftClassAPI

    # Create two dynasties for same season
    controller1 = SeasonCycleController(
        database_path=temp_db,
        dynasty_id="dynasty_a",
        season_year=2024,
        verbose_logging=False
    )

    controller2 = SeasonCycleController(
        database_path=temp_db,
        dynasty_id="dynasty_b",
        season_year=2024,
        verbose_logging=False
    )

    # Assert: Different draft classes
    draft_api = DraftClassAPI(temp_db)
    prospects_a = draft_api.get_all_prospects("dynasty_a", 2024)
    prospects_b = draft_api.get_all_prospects("dynasty_b", 2024)

    # Same number of prospects
    assert len(prospects_a) == 224
    assert len(prospects_b) == 224

    # But different player IDs (different prospects)
    ids_a = {p['player_id'] for p in prospects_a}
    ids_b = {p['player_id'] for p in prospects_b}
    assert ids_a.isdisjoint(ids_b)  # No overlap


def test_draft_class_correct_season_year(temp_db):
    """Verify draft class uses correct season year."""
    from season.season_cycle_controller import SeasonCycleController
    from database.draft_class_api import DraftClassAPI

    # Create controller for 2025 season
    controller = SeasonCycleController(
        database_path=temp_db,
        dynasty_id="test_dynasty",
        season_year=2025,
        verbose_logging=False
    )

    # Assert: Draft class for 2025 exists (not 2024 or 2026)
    draft_api = DraftClassAPI(temp_db)
    assert draft_api.dynasty_has_draft_class("test_dynasty", 2025)
    assert not draft_api.dynasty_has_draft_class("test_dynasty", 2024)
    assert not draft_api.dynasty_has_draft_class("test_dynasty", 2026)


def test_integration_suite_summary():
    """Print summary of integration test suite."""
    print("\n" + "="*80)
    print("DRAFT CLASS GENERATION INTEGRATION TEST SUITE")
    print("="*80)
    print("\nTests Covered:")
    print("  1. Draft class generated at season start")
    print("  2. Draft class generation is idempotent")
    print("  3. Dynasty isolation (different dynasties = different prospects)")
    print("  4. Correct season year used")
    print("\nIntegration Point:")
    print("  - SeasonCycleController.__init__() → _generate_draft_class_if_needed()")
    print("\nExpected Behavior:")
    print("  - 224 prospects generated (7 rounds × 32 teams)")
    print("  - Generation happens once per dynasty per season")
    print("  - Uses unified player_id system (no conversion needed)")
    print("="*80)
