"""
Unit tests for MilestoneDetector service.

Tests verify milestone detection logic using pure Python mocks - no Qt or database required.
This follows the dependency injection pattern used by PhaseCompletionChecker.
"""
import pytest
from datetime import datetime, timedelta
from typing import List, Dict

from src.season.milestone_detector import MilestoneDetector


class TestMilestoneDetectorDraftDay:
    """Test draft day milestone detection."""

    def test_finds_draft_day_in_lookahead_window(self):
        """Detects DRAFT_DAY event 4 days ahead."""
        # Create draft event for April 24, 2025
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)
        draft_end_ms = draft_start_ms + (24 * 60 * 60 * 1000)  # Same day

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            # Return draft event if query overlaps with draft day
            if start_ms <= draft_start_ms <= end_ms or start_ms <= draft_end_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {'parameters': {'season': 2025}, 'results': None}
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",  # 4 days before draft
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is not None
        assert result['event_type'] == 'DRAFT_DAY'
        assert result['days_until'] == 4
        assert result['milestone_date'] == '2025-04-24'
        assert result['display_name'] == 'Draft Day'

    def test_finds_draft_day_on_current_day(self):
        """Detects DRAFT_DAY event on same day (days_until=0)."""
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {'parameters': {'season': 2025}, 'results': None}
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",  # Draft day!
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is not None
        assert result['days_until'] == 0
        assert result['event_type'] == 'DRAFT_DAY'

    def test_skips_already_executed_draft(self):
        """Skips DRAFT_DAY events with results already populated."""
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {
                        'parameters': {'season': 2025},
                        'results': {'completed': True}  # Already executed!
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # Should NOT detect already-executed event
        assert result is None


class TestMilestoneDetectorPhaseFiltering:
    """Test phase-based filtering."""

    def test_returns_none_when_not_in_offseason(self):
        """Returns None if phase is not offseason."""
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-09-15",
            get_current_phase=lambda: "regular_season",  # Not offseason!
            get_events_for_date_range=lambda d, s, e: [],
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)
        assert result is None

    def test_returns_none_during_playoffs(self):
        """Returns None during playoffs phase."""
        detector = MilestoneDetector(
            get_current_date=lambda: "2026-01-15",
            get_current_phase=lambda: "playoffs",
            get_events_for_date_range=lambda d, s, e: [],
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)
        assert result is None

    def test_returns_none_during_preseason(self):
        """Returns None during preseason phase."""
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-08-01",
            get_current_phase=lambda: "preseason",
            get_events_for_date_range=lambda d, s, e: [],
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)
        assert result is None


class TestMilestoneDetectorDeadlines:
    """Test deadline milestone detection."""

    def test_finds_franchise_tag_deadline(self):
        """Detects DEADLINE event with FRANCHISE_TAG type."""
        deadline_date = datetime(2025, 3, 4)  # Typical franchise tag deadline
        deadline_start_ms = int(deadline_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= deadline_start_ms <= end_ms:
                return [{
                    'event_type': 'DEADLINE',
                    'data': {
                        'parameters': {'deadline_type': 'FRANCHISE_TAG'},
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-03-01",  # 3 days before deadline
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is not None
        assert result['event_type'] == 'DEADLINE'
        assert result['event_subtype'] == 'FRANCHISE_TAG'
        assert result['days_until'] == 3
        assert 'Franchise Tag' in result['display_name']

    def test_finds_roster_cuts_deadline(self):
        """Detects DEADLINE event with FINAL_ROSTER_CUTS type."""
        deadline_date = datetime(2025, 9, 1)
        deadline_start_ms = int(deadline_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= deadline_start_ms <= end_ms:
                return [{
                    'event_type': 'DEADLINE',
                    'data': {
                        'parameters': {'deadline_type': 'FINAL_ROSTER_CUTS'},
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-08-30",  # 2 days before
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is not None
        assert result['event_subtype'] == 'FINAL_ROSTER_CUTS'
        assert result['days_until'] == 2

    def test_detects_all_deadline_types(self):
        """All deadline types are detected as interactive (simpler, no whitelist)."""
        deadline_date = datetime(2025, 3, 15)
        deadline_start_ms = int(deadline_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= deadline_start_ms <= end_ms:
                return [{
                    'event_type': 'DEADLINE',
                    'data': {
                        'parameters': {'deadline_type': 'RFA_TENDER'},
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-03-14",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # ALL deadlines are now interactive (no whitelist filtering)
        assert result is not None
        assert result['event_type'] == 'DEADLINE'
        assert result['event_subtype'] == 'RFA_TENDER'
        assert result['days_until'] == 1
        assert 'Rfa Tender' in result['display_name']


class TestMilestoneDetectorWindows:
    """Test window milestone detection."""

    def test_finds_free_agency_window_start(self):
        """Detects WINDOW event with FREE_AGENCY START."""
        window_date = datetime(2025, 3, 12)  # Typical FA start
        window_start_ms = int(window_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= window_start_ms <= end_ms:
                return [{
                    'event_type': 'WINDOW',
                    'data': {
                        'parameters': {
                            'window_name': 'FREE_AGENCY',
                            'window_type': 'START'
                        },
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-03-10",  # 2 days before
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is not None
        assert result['event_type'] == 'WINDOW'
        assert result['event_subtype'] == 'FREE_AGENCY_START'
        assert result['days_until'] == 2
        assert 'Free Agency' in result['display_name']
        assert 'Opening' in result['display_name']

    def test_ignores_free_agency_window_end(self):
        """Ignores WINDOW END events (only START is interactive)."""
        window_date = datetime(2025, 7, 15)
        window_start_ms = int(window_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= window_start_ms <= end_ms:
                return [{
                    'event_type': 'WINDOW',
                    'data': {
                        'parameters': {
                            'window_name': 'FREE_AGENCY',
                            'window_type': 'END'  # END events are not interactive
                        },
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-07-14",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # END events should be ignored
        assert result is None

    def test_ignores_non_interactive_window(self):
        """Ignores window types that are not interactive."""
        window_date = datetime(2025, 5, 1)
        window_start_ms = int(window_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= window_start_ms <= end_ms:
                return [{
                    'event_type': 'WINDOW',
                    'data': {
                        'parameters': {
                            'window_name': 'MINICAMP',  # Not interactive
                            'window_type': 'START'
                        },
                        'results': None
                    }
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-30",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # Non-interactive window should be ignored
        assert result is None


class TestMilestoneDetectorLookaheadWindow:
    """Test lookahead window behavior."""

    def test_returns_none_when_no_milestones_in_window(self):
        """Returns None when no milestones exist in lookahead window."""
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-05-01",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=lambda d, s, e: [],  # No events
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)
        assert result is None

    def test_milestone_outside_window_not_detected(self):
        """Milestone 10 days ahead not detected with 7-day window."""
        draft_date = datetime(2025, 4, 30)  # 10 days from current
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {'parameters': {'season': 2025}, 'results': None}
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",  # 10 days before draft
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        # With 7-day window, should NOT find event 10 days away
        result = detector.check_upcoming_milestones(days_ahead=7)
        assert result is None

        # With 14-day window, SHOULD find it
        result = detector.check_upcoming_milestones(days_ahead=14)
        assert result is not None
        assert result['days_until'] == 10

    def test_finds_closest_milestone_first(self):
        """When multiple milestones exist, returns the closest one."""
        # FA opens on day 2, Draft on day 5
        fa_date = datetime(2025, 4, 22)
        draft_date = datetime(2025, 4, 25)
        fa_start_ms = int(fa_date.timestamp() * 1000)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            events = []
            if start_ms <= fa_start_ms <= end_ms:
                events.append({
                    'event_type': 'WINDOW',
                    'data': {
                        'parameters': {
                            'window_name': 'FREE_AGENCY',
                            'window_type': 'START'
                        },
                        'results': None
                    }
                })
            if start_ms <= draft_start_ms <= end_ms:
                events.append({
                    'event_type': 'DRAFT_DAY',
                    'data': {'parameters': {'season': 2025}, 'results': None}
                })
            return events

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",  # FA in 2 days, Draft in 5
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # Should find FA first (closer)
        assert result is not None
        assert result['event_type'] == 'WINDOW'
        assert result['event_subtype'] == 'FREE_AGENCY_START'
        assert result['days_until'] == 2


class TestMilestoneDetectorEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_empty_event_data(self):
        """Handles events with missing or empty data field."""
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {}  # Empty data - no parameters or results
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # Should still detect draft day (results is None by default)
        assert result is not None
        assert result['event_type'] == 'DRAFT_DAY'

    def test_handles_missing_data_field(self):
        """Handles events with missing data field entirely."""
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY'
                    # No 'data' field at all
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # Should still detect draft day
        assert result is not None
        assert result['event_type'] == 'DRAFT_DAY'

    def test_single_day_lookahead(self):
        """Works correctly with days_ahead=1 (just today)."""
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {'parameters': {'season': 2025}, 'results': None}
                }]
            return []

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",  # Same day
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=1)

        assert result is not None
        assert result['days_until'] == 0

    def test_zero_day_lookahead_finds_nothing(self):
        """With days_ahead=0, finds nothing (empty range)."""
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-24",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=lambda d, s, e: [{
                'event_type': 'DRAFT_DAY',
                'data': {'parameters': {}, 'results': None}
            }],
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=0)

        # Range(0) produces no iterations, so nothing found
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
