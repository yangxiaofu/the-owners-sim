"""
Milestone detection service.

Pure Python service for detecting upcoming interactive milestones during simulation.
Uses dependency injection to be fully testable without Qt or database dependencies.

This follows the same pattern as PhaseCompletionChecker in the codebase.
"""
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional


# Module-level logger for diagnostic output
_logger = logging.getLogger(__name__)


class MilestoneDetector:
    """
    Pure Python milestone detection service.

    Uses dependency injection for database queries, making it fully testable
    without Qt or real database dependencies.

    Example usage:
        detector = MilestoneDetector(
            get_current_date=lambda: "2025-04-20",
            get_current_phase=lambda: "offseason",
            get_events_for_date_range=event_db.get_events_by_dynasty_and_timestamp,
            dynasty_id="my_dynasty"
        )

        milestone = detector.check_upcoming_milestones(days_ahead=7)
        if milestone:
            print(f"Found {milestone['event_type']} in {milestone['days_until']} days")
    """

    # Define which event types and subtypes are interactive
    # Note: ALL DEADLINE events are now interactive by default (simpler, safer)

    INTERACTIVE_WINDOW_NAMES = {
        'FREE_AGENCY'  # Only START events, not END
    }

    def __init__(
        self,
        get_current_date: Callable[[], str],
        get_current_phase: Callable[[], str],
        get_events_for_date_range: Callable[[str, int, int], List[Dict]],
        dynasty_id: str,
        verbose: bool = False
    ):
        """
        Initialize MilestoneDetector with injected dependencies.

        Args:
            get_current_date: Callable returning current date as ISO string (e.g., '2025-04-20')
            get_current_phase: Callable returning current phase as string (e.g., 'offseason')
            get_events_for_date_range: Callable that takes (dynasty_id, start_timestamp_ms, end_timestamp_ms)
                                       and returns list of event dicts
            dynasty_id: Dynasty identifier for event queries
            verbose: Enable verbose diagnostic logging (default: False)
        """
        self._get_current_date = get_current_date
        self._get_current_phase = get_current_phase
        self._get_events = get_events_for_date_range
        self._dynasty_id = dynasty_id
        self._verbose = verbose

    def set_verbose(self, verbose: bool) -> None:
        """
        Enable or disable verbose diagnostic logging.

        Args:
            verbose: True to enable, False to disable
        """
        self._verbose = verbose

    def check_upcoming_milestones(self, days_ahead: int = 7) -> Optional[Dict[str, Any]]:
        """
        Check if any interactive milestones exist in the next N days.

        This method enables UI-layer milestone detection, allowing the UI to stop
        simulation BEFORE reaching interactive events. This is the CORRECT pattern
        for MVC separation - UI checks calendar, backend just simulates.

        Args:
            days_ahead: Number of days to look ahead (default: 7 for week simulation)

        Returns:
            Dict with milestone info if found, None otherwise:
            {
                'days_until': int,           # Days until milestone (0 = today, 1 = tomorrow, etc.)
                'milestone_date': str,       # ISO date of milestone (e.g., '2025-04-24')
                'event_type': str,           # 'DRAFT_DAY', 'DEADLINE', 'WINDOW'
                'event_subtype': str,        # Specific type (e.g., 'FRANCHISE_TAG', 'FREE_AGENCY_START')
                'display_name': str,         # UI-friendly label (e.g., 'Draft Day', 'Franchise Tag')
                'event': Dict[str, Any]      # Full event dict from database
            }

        Examples:
            # Check next 7 days before simulating week
            milestone = detector.check_upcoming_milestones(days_ahead=7)
            if milestone:
                # Stop before milestone, show dialog
                days_to_sim = milestone['days_until']
                controller.advance_days(days_to_sim)  # Simulate up to milestone
                handle_milestone_dialog(milestone['event'])
            else:
                # No milestone, simulate full week
                controller.advance_week()
        """
        # DIAGNOSTIC: Log entry point
        if self._verbose:
            print(f"\n[MILESTONE_DETECTOR] ===== check_upcoming_milestones(days_ahead={days_ahead}) =====")
            _logger.info(f"check_upcoming_milestones called with days_ahead={days_ahead}")

        # Only check in offseason (milestones are offseason-only)
        current_phase = self._get_current_phase()

        # DIAGNOSTIC: Log phase check
        if self._verbose:
            print(f"[MILESTONE_DETECTOR] Current phase: '{current_phase}' (expected: 'offseason')")
            print(f"[MILESTONE_DETECTOR] Phase check result: {current_phase == 'offseason'}")
            _logger.info(f"Phase check: current='{current_phase}', expected='offseason'")

        if current_phase != "offseason":
            if self._verbose:
                print(f"[MILESTONE_DETECTOR] ❌ NOT in offseason - returning None")
                print(f"[MILESTONE_DETECTOR] =================================================\n")
            return None

        current_date = self._get_current_date()
        current_dt = datetime.fromisoformat(current_date)

        # DIAGNOSTIC: Log current date
        if self._verbose:
            print(f"[MILESTONE_DETECTOR] Current date: {current_date}")
            print(f"[MILESTONE_DETECTOR] Checking dates: {current_date} to {(current_dt + timedelta(days=days_ahead-1)).date().isoformat()}")

        # Check each day in the lookahead window
        for day_offset in range(days_ahead):
            check_date_dt = current_dt + timedelta(days=day_offset)
            check_date_str = check_date_dt.date().isoformat()

            # Calculate timestamp range for this date
            start_dt = datetime.fromisoformat(check_date_str)
            end_dt = datetime.fromisoformat(f"{check_date_str}T23:59:59")
            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            # Query for events on this date
            events = self._get_events(self._dynasty_id, start_ms, end_ms)

            # DIAGNOSTIC: Log event query results
            if self._verbose:
                event_types = [e.get('event_type', 'UNKNOWN') for e in events]
                print(f"[MILESTONE_DETECTOR] Day {day_offset} ({check_date_str}): {len(events)} events {event_types}")

            # Check each event on this date
            milestone = self._check_events_for_milestone(events, check_date_str, day_offset)
            if milestone:
                if self._verbose:
                    print(f"[MILESTONE_DETECTOR] ✓ MILESTONE FOUND: {milestone['display_name']} on {milestone['milestone_date']}")
                    print(f"[MILESTONE_DETECTOR] =================================================\n")
                return milestone

        # No milestone found in next N days
        if self._verbose:
            print(f"[MILESTONE_DETECTOR] ❌ No milestones found in next {days_ahead} days")
            print(f"[MILESTONE_DETECTOR] =================================================\n")
        return None

    def _check_events_for_milestone(
        self,
        events: List[Dict],
        check_date_str: str,
        day_offset: int
    ) -> Optional[Dict[str, Any]]:
        """
        Check a list of events for interactive milestones.

        Args:
            events: List of event dicts to check
            check_date_str: ISO date string being checked
            day_offset: Days from current date (0 = today)

        Returns:
            Milestone info dict if found, None otherwise
        """
        for event in events:
            event_type = event.get('event_type')
            event_data = event.get('data', {})
            parameters = event_data.get('parameters', {})

            # Skip if already executed
            if event_data.get('results') is not None:
                continue

            # Check for interactive milestone types
            if event_type == 'DRAFT_DAY':
                return {
                    'days_until': day_offset,
                    'milestone_date': check_date_str,
                    'event_type': 'DRAFT_DAY',
                    'event_subtype': None,
                    'display_name': 'Draft Day',
                    'event': event
                }

            elif event_type == 'DEADLINE':
                # ALL deadlines are interactive (simpler, no whitelist to maintain)
                deadline_type = parameters.get('deadline_type', 'UNKNOWN')
                display_name = deadline_type.replace('_', ' ').title()
                return {
                    'days_until': day_offset,
                    'milestone_date': check_date_str,
                    'event_type': 'DEADLINE',
                    'event_subtype': deadline_type,
                    'display_name': f"Deadline: {display_name}",
                    'event': event
                }

            elif event_type == 'WINDOW':
                window_name = parameters.get('window_name')
                stage = parameters.get('window_type')  # 'START' or 'END'
                if window_name in self.INTERACTIVE_WINDOW_NAMES and stage == 'START':
                    display_name = window_name.replace('_', ' ').title()
                    return {
                        'days_until': day_offset,
                        'milestone_date': check_date_str,
                        'event_type': 'WINDOW',
                        'event_subtype': f"{window_name}_START",
                        'display_name': f"{display_name} Opening",
                        'event': event
                    }

        return None
