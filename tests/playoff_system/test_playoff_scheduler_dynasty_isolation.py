"""
Tests for playoff scheduler dynasty isolation.

Validates that playoff games are properly isolated by dynasty and that
duplicate detection works correctly across different dynasties.
"""

import pytest
import sys
from datetime import datetime
from pathlib import Path

# Add src to path if not already there
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from events.event_database_api import EventDatabaseAPI
from playoff_system.playoff_scheduler import PlayoffScheduler
from playoff_system.playoff_manager import PlayoffManager
from playoff_system.playoff_seeder import PlayoffSeeder
from playoff_system.bracket_models import PlayoffBracket, PlayoffGame
from playoff_system.seeding_models import PlayoffSeeding, ConferenceSeeding, PlayoffSeed
from src.calendar.date_models import Date


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_playoff_dynasty_isolation.db")
    return db_path


@pytest.fixture
def event_db(temp_db):
    """Create EventDatabaseAPI instance."""
    return EventDatabaseAPI(temp_db)


@pytest.fixture
def playoff_manager():
    """Create PlayoffManager instance."""
    return PlayoffManager()


@pytest.fixture
def playoff_scheduler(event_db, playoff_manager):
    """Create PlayoffScheduler instance."""
    return PlayoffScheduler(
        event_db_api=event_db,
        playoff_manager=playoff_manager
    )


@pytest.fixture
def sample_seeding():
    """Create sample playoff seeding for testing."""
    # AFC seeds
    afc_seeds = [
        PlayoffSeed(
            seed=i,
            team_id=i,
            wins=14-i,
            losses=3+i,
            ties=0,
            win_percentage=(14-i)/17.0,
            division_winner=(i <= 4),
            division_name=f"AFC Division {i}",
            conference="AFC",
            points_for=400,
            points_against=300,
            point_differential=100,
            division_record="4-2",
            conference_record="8-4"
        )
        for i in range(1, 8)
    ]

    # NFC seeds
    nfc_seeds = [
        PlayoffSeed(
            seed=i,
            team_id=i+16,
            wins=14-i,
            losses=3+i,
            ties=0,
            win_percentage=(14-i)/17.0,
            division_winner=(i <= 4),
            division_name=f"NFC Division {i}",
            conference="NFC",
            points_for=400,
            points_against=300,
            point_differential=100,
            division_record="4-2",
            conference_record="8-4"
        )
        for i in range(1, 8)
    ]

    afc_conference = ConferenceSeeding(
        conference="AFC",
        seeds=afc_seeds,
        division_winners=afc_seeds[:4],
        wildcards=afc_seeds[4:],
        clinched_teams=[s.team_id for s in afc_seeds],
        eliminated_teams=[]
    )

    nfc_conference = ConferenceSeeding(
        conference="NFC",
        seeds=nfc_seeds,
        division_winners=nfc_seeds[:4],
        wildcards=nfc_seeds[4:],
        clinched_teams=[s.team_id for s in nfc_seeds],
        eliminated_teams=[]
    )

    return PlayoffSeeding(
        season=2025,
        week=18,
        afc=afc_conference,
        nfc=nfc_conference,
        tiebreakers_applied=[],
        calculation_date=datetime.now().isoformat()
    )


def test_get_events_by_game_id_and_dynasty_empty(event_db):
    """Test dynasty-aware query returns empty list when no events exist."""
    events = event_db.get_events_by_game_id_and_dynasty(
        game_id="playoff_2025_wild_card_1",
        dynasty_id="test_dynasty"
    )

    assert events == []
    assert isinstance(events, list)


def test_get_events_by_game_id_and_dynasty_filters_correctly(event_db, playoff_scheduler, sample_seeding):
    """Test that dynasty-aware query filters events by both game_id and dynasty_id."""
    start_date = Date(2025, 1, 11)

    # Schedule playoff games for dynasty A
    result_a = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # Schedule playoff games for dynasty B (same season, different dynasty)
    result_b = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_b"
    )

    # Both should schedule successfully (6 games each)
    assert result_a['games_scheduled'] == 6
    assert result_b['games_scheduled'] == 6

    # Query for wild card game 1 for dynasty A
    events_a = event_db.get_events_by_game_id_and_dynasty(
        game_id="playoff_2025_wild_card_1",
        dynasty_id="dynasty_a"
    )

    # Query for wild card game 1 for dynasty B
    events_b = event_db.get_events_by_game_id_and_dynasty(
        game_id="playoff_2025_wild_card_1",
        dynasty_id="dynasty_b"
    )

    # Each dynasty should have exactly 1 event for this game_id
    assert len(events_a) == 1
    assert len(events_b) == 1

    # Verify they're for different dynasties
    assert events_a[0]['dynasty_id'] == "dynasty_a"
    assert events_b[0]['dynasty_id'] == "dynasty_b"

    # Verify both have the same game_id
    assert events_a[0]['game_id'] == "playoff_2025_wild_card_1"
    assert events_b[0]['game_id'] == "playoff_2025_wild_card_1"


def test_duplicate_prevention_within_same_dynasty(event_db, playoff_scheduler, sample_seeding):
    """Test that duplicate games are prevented within the same dynasty."""
    start_date = Date(2025, 1, 11)

    # Schedule playoff games for dynasty A
    result1 = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # Try to schedule again for same dynasty (should detect duplicates)
    result2 = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # First schedule should create 6 games
    assert result1['games_scheduled'] == 6

    # Second schedule should find all 6 as duplicates (returns existing IDs but doesn't create new games)
    assert result2['games_scheduled'] == 6

    # Verify only 6 events exist in database for dynasty_a (not 12)
    all_dynasty_a_events = event_db.get_events_by_dynasty("dynasty_a")
    assert len(all_dynasty_a_events) == 6


def test_no_cross_dynasty_interference(event_db, playoff_scheduler, sample_seeding):
    """Test that games for different dynasties don't interfere with each other."""
    start_date = Date(2025, 1, 11)

    # Schedule for dynasty A
    result_a = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # Schedule for dynasty B (should NOT see dynasty A's games as duplicates)
    result_b = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_b"
    )

    # Schedule for dynasty C
    result_c = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_c"
    )

    # All should create 6 games (no cross-dynasty interference)
    assert result_a['games_scheduled'] == 6
    assert result_b['games_scheduled'] == 6
    assert result_c['games_scheduled'] == 6

    # Verify each dynasty has exactly 6 events
    assert len(event_db.get_events_by_dynasty("dynasty_a")) == 6
    assert len(event_db.get_events_by_dynasty("dynasty_b")) == 6
    assert len(event_db.get_events_by_dynasty("dynasty_c")) == 6

    # Total events in database should be 18 (6 per dynasty)
    all_events = event_db.get_events_by_type("GAME")
    assert len(all_events) == 18


def test_delete_playoff_events_by_dynasty(event_db, playoff_scheduler, sample_seeding):
    """Test that delete_playoff_events_by_dynasty only deletes games for specified dynasty."""
    start_date = Date(2025, 1, 11)

    # Schedule for dynasty A
    playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # Schedule for dynasty B
    playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="dynasty_b"
    )

    # Verify both dynasties have games
    assert len(event_db.get_events_by_dynasty("dynasty_a")) == 6
    assert len(event_db.get_events_by_dynasty("dynasty_b")) == 6

    # Delete only dynasty A's playoff games
    deleted_count = event_db.delete_playoff_events_by_dynasty(
        dynasty_id="dynasty_a",
        season=2025
    )

    # Should have deleted 6 games
    assert deleted_count == 6

    # Dynasty A should have 0 games now
    assert len(event_db.get_events_by_dynasty("dynasty_a")) == 0

    # Dynasty B should still have 6 games (unaffected)
    assert len(event_db.get_events_by_dynasty("dynasty_b")) == 6


def test_delete_playoff_events_different_seasons(event_db, playoff_scheduler, sample_seeding):
    """Test that delete only affects specified season."""
    start_date_2025 = Date(2025, 1, 11)
    start_date_2026 = Date(2026, 1, 11)

    # Schedule 2025 playoffs for dynasty A
    playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date_2025,
        season=2025,
        dynasty_id="dynasty_a"
    )

    # Schedule 2026 playoffs for dynasty A
    seeding_2026 = sample_seeding
    seeding_2026.season = 2026
    playoff_scheduler.schedule_wild_card_round(
        seeding=seeding_2026,
        start_date=start_date_2026,
        season=2026,
        dynasty_id="dynasty_a"
    )

    # Dynasty A should have 12 games total (6 per season)
    assert len(event_db.get_events_by_dynasty("dynasty_a")) == 12

    # Delete only 2025 playoffs
    deleted_count = event_db.delete_playoff_events_by_dynasty(
        dynasty_id="dynasty_a",
        season=2025
    )

    # Should have deleted 6 games
    assert deleted_count == 6

    # Dynasty A should have 6 games remaining (2026 season)
    remaining_events = event_db.get_events_by_dynasty("dynasty_a")
    assert len(remaining_events) == 6

    # Verify remaining games are all from 2026
    for event in remaining_events:
        assert "2026" in event['game_id']


def test_old_games_dont_block_new_dynasty(event_db, playoff_scheduler, sample_seeding):
    """
    Test the exact scenario from the bug report:
    Old playoff games from a previous dynasty should not block scheduling for a new dynasty.
    """
    start_date = Date(2025, 1, 11)

    # Simulate the user's scenario: old dynasty "third" has playoff games
    result_old = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="third"
    )

    assert result_old['games_scheduled'] == 6

    # Now the user creates a new dynasty
    # Before the fix, this would detect the old "third" dynasty games as duplicates
    result_new = playoff_scheduler.schedule_wild_card_round(
        seeding=sample_seeding,
        start_date=start_date,
        season=2025,
        dynasty_id="new_dynasty"
    )

    # NEW BEHAVIOR (after fix): Should schedule 6 new games for new_dynasty
    assert result_new['games_scheduled'] == 6

    # Verify new_dynasty has its own 6 games
    new_dynasty_events = event_db.get_events_by_dynasty("new_dynasty")
    assert len(new_dynasty_events) == 6

    # Verify old dynasty still has its 6 games
    old_dynasty_events = event_db.get_events_by_dynasty("third")
    assert len(old_dynasty_events) == 6

    # Verify game_ids are the same but dynasty_ids are different
    for i in range(6):
        assert new_dynasty_events[i]['game_id'] == old_dynasty_events[i]['game_id']
        assert new_dynasty_events[i]['dynasty_id'] != old_dynasty_events[i]['dynasty_id']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
