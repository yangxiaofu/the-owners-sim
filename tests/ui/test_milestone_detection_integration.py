"""
Integration tests for MilestoneDetector with SimulationController.

These tests verify the full integration path:
SimulationController -> MilestoneDetector -> EventDatabaseAPI

They help diagnose why 'simulate week' might not stop at milestones.
"""
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch, MagicMock

from src.season.milestone_detector import MilestoneDetector
from src.calendar.season_phase_tracker import SeasonPhase


class TestMilestoneDetectorIntegration:
    """
    Integration tests that simulate the full flow from UI to MilestoneDetector.

    These tests help diagnose issues where 'simulate week' doesn't stop at milestones.
    """

    def test_phase_value_compatibility(self):
        """
        Verify SeasonPhase enum values match MilestoneDetector expectations.

        This test catches case-sensitivity issues between the phase enum
        and MilestoneDetector's hardcoded phase check.
        """
        # MilestoneDetector expects lowercase "offseason"
        expected_offseason_value = "offseason"

        # SeasonPhase enum value
        actual_offseason_value = SeasonPhase.OFFSEASON.value

        assert actual_offseason_value == expected_offseason_value, (
            f"Phase value mismatch! "
            f"SeasonPhase.OFFSEASON.value = '{actual_offseason_value}', "
            f"but MilestoneDetector expects '{expected_offseason_value}'"
        )

    def test_milestone_detected_when_phase_is_offseason(self):
        """
        Verify milestone detection works when phase is 'offseason'.

        Simulates the exact flow from SimulationController.check_upcoming_milestones()
        """
        # Setup: Draft on April 24, current date April 20
        draft_date = datetime(2025, 4, 24)
        draft_start_ms = int(draft_date.timestamp() * 1000)
        draft_end_ms = int(datetime(2025, 4, 24, 23, 59, 59).timestamp() * 1000)

        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            """Return draft event if query overlaps with draft day."""
            if start_ms <= draft_start_ms <= end_ms:
                return [{
                    'event_type': 'DRAFT_DAY',
                    'data': {
                        'parameters': {'season': 2025},
                        'results': None  # Not yet executed
                    }
                }]
            return []

        # Create detector with exact same pattern as SimulationController
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",  # Matches SeasonPhase.OFFSEASON.value
            get_events_for_date_range=mock_get_events,
            dynasty_id="test_dynasty"
        )

        # Act
        result = detector.check_upcoming_milestones(days_ahead=7)

        # Assert
        assert result is not None, "Milestone should be detected in offseason"
        assert result['event_type'] == 'DRAFT_DAY'
        assert result['days_until'] == 4

    def test_milestone_not_detected_when_phase_is_regular_season(self):
        """
        Verify milestone detection returns None during regular season.

        This confirms the phase gate is working correctly.
        """
        # Setup: Draft exists but we're in regular season
        def mock_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            return [{
                'event_type': 'DRAFT_DAY',
                'data': {'parameters': {'season': 2025}, 'results': None}
            }]

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "regular_season",  # NOT offseason
            get_events_for_date_range=mock_get_events,
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        assert result is None, "Should return None when not in offseason"

    def test_milestone_not_detected_with_uppercase_phase(self):
        """
        Verify that uppercase phase values cause milestone detection to fail.

        This test documents the case-sensitivity issue that might occur if
        get_current_phase() returns "OFFSEASON" instead of "offseason".
        """
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "OFFSEASON",  # Uppercase - will fail!
            get_events_for_date_range=lambda d, s, e: [{
                'event_type': 'DRAFT_DAY',
                'data': {'parameters': {}, 'results': None}
            }],
            dynasty_id="test"
        )

        result = detector.check_upcoming_milestones(days_ahead=7)

        # This demonstrates the bug - uppercase phase causes failure
        assert result is None, "Uppercase 'OFFSEASON' does not match lowercase check"

    def test_milestone_skipped_when_already_executed(self):
        """
        Verify milestones with results populated are skipped.
        """
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

        assert result is None, "Already-executed milestones should be skipped"


class TestMilestoneDetectorDiagnostics:
    """
    Diagnostic tests to help trace milestone detection issues.

    These tests add logging/tracing to understand the detection flow.
    """

    def test_trace_phase_check_flow(self, capsys):
        """
        Trace what happens during phase check.

        This helps diagnose cases where phase check fails unexpectedly.
        """
        # Track calls to get_current_phase
        phase_calls = []

        def traced_get_phase():
            phase = "offseason"
            phase_calls.append(phase)
            print(f"[TRACE] get_current_phase() called, returning: '{phase}'")
            return phase

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=traced_get_phase,
            get_events_for_date_range=lambda d, s, e: [],
            dynasty_id="test"
        )

        detector.check_upcoming_milestones(days_ahead=7)

        # Verify phase was checked
        assert len(phase_calls) == 1, "get_current_phase should be called once"
        assert phase_calls[0] == "offseason"

        captured = capsys.readouterr()
        assert "[TRACE] get_current_phase()" in captured.out

    def test_trace_event_query_flow(self, capsys):
        """
        Trace event queries during milestone detection.

        This helps diagnose cases where events aren't being returned.
        """
        query_log = []

        def traced_get_events(dynasty_id: str, start_ms: int, end_ms: int) -> List[Dict]:
            # Convert timestamps to readable dates for debugging
            start_dt = datetime.fromtimestamp(start_ms / 1000)
            end_dt = datetime.fromtimestamp(end_ms / 1000)

            query_info = {
                'dynasty_id': dynasty_id,
                'start_date': start_dt.isoformat(),
                'end_date': end_dt.isoformat(),
                'start_ms': start_ms,
                'end_ms': end_ms
            }
            query_log.append(query_info)

            print(f"[TRACE] Event query: {start_dt.date()} to {end_dt.date()}")

            return []  # No events

        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=traced_get_events,
            dynasty_id="test_dynasty"
        )

        detector.check_upcoming_milestones(days_ahead=3)

        # Should query 3 days
        assert len(query_log) == 3, f"Expected 3 queries, got {len(query_log)}"

        # Verify dates queried
        expected_dates = ["2025-04-20", "2025-04-21", "2025-04-22"]
        for i, entry in enumerate(query_log):
            assert expected_dates[i] in entry['start_date'], (
                f"Query {i} should be for {expected_dates[i]}, got {entry['start_date']}"
            )


class TestSimulationControllerMilestoneFlow:
    """
    Tests simulating the full SimulationController -> MilestoneDetector flow.

    These tests don't require actual database or Qt dependencies.
    """

    def test_simulation_controller_milestone_detection_pattern(self):
        """
        Test the exact pattern used by SimulationController.

        SimulationController creates MilestoneDetector like this:
            self._milestone_detector = MilestoneDetector(
                get_current_date=self.get_current_date,
                get_current_phase=self.get_current_phase,
                get_events_for_date_range=self._query_events_for_date_range,
                dynasty_id=self.dynasty_id
            )

        This test replicates that pattern.
        """
        # Simulate SimulationController state
        class MockSimulationController:
            def __init__(self):
                self.current_date_str = "2025-04-20"
                self.dynasty_id = "test_dynasty"
                # Mock season_controller.phase_state.phase.value
                self.phase_value = "offseason"

                # Events in database
                self.events_db = {
                    "2025-04-24": [{
                        'event_type': 'DRAFT_DAY',
                        'data': {'parameters': {'season': 2025}, 'results': None}
                    }]
                }

            def get_current_date(self) -> str:
                return self.current_date_str

            def get_current_phase(self) -> str:
                return self.phase_value

            def _query_events_for_date_range(
                self,
                dynasty_id: str,
                start_timestamp_ms: int,
                end_timestamp_ms: int
            ) -> list:
                """Simulate EventDatabaseAPI.get_events_by_dynasty_and_timestamp()"""
                # Convert timestamps to date string
                query_date = datetime.fromtimestamp(start_timestamp_ms / 1000).date().isoformat()
                return self.events_db.get(query_date, [])

        # Create mock controller
        mock_controller = MockSimulationController()

        # Create detector exactly like SimulationController does
        detector = MilestoneDetector(
            get_current_date=mock_controller.get_current_date,
            get_current_phase=mock_controller.get_current_phase,
            get_events_for_date_range=mock_controller._query_events_for_date_range,
            dynasty_id=mock_controller.dynasty_id
        )

        # Test milestone detection
        result = detector.check_upcoming_milestones(days_ahead=7)

        # Should find Draft Day 4 days ahead
        assert result is not None, "Should detect draft day milestone"
        assert result['event_type'] == 'DRAFT_DAY'
        assert result['days_until'] == 4
        assert result['milestone_date'] == '2025-04-24'

    def test_why_milestone_might_not_be_detected(self):
        """
        Document common reasons why milestone detection fails.

        This test serves as documentation for debugging.
        """
        # Reason 1: Phase is not offseason
        detector1 = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "playoffs",  # Not offseason!
            get_events_for_date_range=lambda d, s, e: [
                {'event_type': 'DRAFT_DAY', 'data': {'results': None}}
            ],
            dynasty_id="test"
        )
        assert detector1.check_upcoming_milestones() is None, "Fails: not in offseason"

        # Reason 2: Event already executed (results not None)
        detector2 = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=lambda d, s, e: [
                {'event_type': 'DRAFT_DAY', 'data': {'results': {'done': True}}}  # Has results!
            ],
            dynasty_id="test"
        )
        assert detector2.check_upcoming_milestones() is None, "Fails: event already executed"

        # Reason 3: Event query returns empty (event not scheduled)
        detector3 = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=lambda d, s, e: [],  # No events!
            dynasty_id="test"
        )
        assert detector3.check_upcoming_milestones() is None, "Fails: no events returned"

        # Reason 4: Event type not interactive
        detector4 = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=lambda d, s, e: [
                {'event_type': 'SOME_OTHER_TYPE', 'data': {'results': None}}  # Not interactive
            ],
            dynasty_id="test"
        )
        assert detector4.check_upcoming_milestones() is None, "Fails: not an interactive event type"


class TestMilestoneDetectorWithRealPhaseState:
    """
    Tests that verify phase state handling matches SeasonCycleController.
    """

    def test_all_season_phase_values(self):
        """Verify all SeasonPhase enum values are handled correctly."""
        from src.calendar.season_phase_tracker import SeasonPhase

        # Only offseason should allow milestone detection
        offseason_phases = [SeasonPhase.OFFSEASON]
        non_offseason_phases = [
            SeasonPhase.PRESEASON,
            SeasonPhase.REGULAR_SEASON,
            SeasonPhase.PLAYOFFS
        ]

        def make_detector(phase_value: str):
            return MilestoneDetector(
                get_current_date=lambda: "2025-04-20",
                get_current_phase=lambda: phase_value,
                get_events_for_date_range=lambda d, s, e: [
                    {'event_type': 'DRAFT_DAY', 'data': {'results': None}}
                ],
                dynasty_id="test"
            )

        # Test offseason phases allow detection
        for phase in offseason_phases:
            detector = make_detector(phase.value)
            result = detector.check_upcoming_milestones()
            assert result is not None, f"Phase {phase.value} should allow milestone detection"

        # Test non-offseason phases block detection
        for phase in non_offseason_phases:
            detector = make_detector(phase.value)
            result = detector.check_upcoming_milestones()
            assert result is None, f"Phase {phase.value} should block milestone detection"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
