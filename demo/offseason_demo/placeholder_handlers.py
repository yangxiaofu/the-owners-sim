"""
Placeholder Event Handlers for Offseason Demo

This module provides placeholder event handlers that display modal dialogs
instead of executing real game logic. Used for demonstrating the offseason
event system UI flow without implementing full event execution logic.

Components:
- EventSimulationDialog: Modal dialog showing event simulation details
- PlaceholderEventHandler: Routes events to placeholder handlers
- EventDispatcher: Dispatches events and shows dialogs

All handlers return standardized result dictionaries with simulated=True.
"""

from typing import Dict, Any, Optional
from datetime import date
import logging

from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.events.deadline_event import DeadlineEvent
from src.events.window_event import WindowEvent
from src.events.milestone_event import MilestoneEvent

logger = logging.getLogger(__name__)


class EventSimulationDialog(QDialog):
    """
    Modal dialog for displaying event simulation information.

    Shows event name, description, metadata, and simulation status.
    Blocks user interaction until closed.
    """

    def __init__(
        self,
        event_name: str,
        event_description: str,
        event_date: date,
        event_type: str,
        event_phase: Optional[str] = None,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize event simulation dialog.

        Args:
            event_name: Display name of the event
            event_description: Detailed event description
            event_date: Date the event occurs
            event_type: Type of event (DEADLINE, WINDOW, MILESTONE)
            event_phase: Optional offseason phase
            parent: Parent widget (for modal behavior)
        """
        super().__init__(parent)
        self.setWindowTitle("Simulating Event")
        self.setModal(True)  # Block interaction with parent
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)

        self._event_name = event_name
        self._event_description = event_description
        self._event_date = event_date
        self._event_type = event_type
        self._event_phase = event_phase

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup dialog UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Icon and title header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Event type icon
        icon_label = QLabel(self._get_event_icon())
        icon_font = QFont()
        icon_font.setPointSize(32)
        icon_label.setFont(icon_font)
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(self._event_name)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, stretch=1)

        layout.addLayout(header_layout)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Description
        desc_label = QLabel("Description:")
        desc_font = QFont()
        desc_font.setBold(True)
        desc_label.setFont(desc_font)
        layout.addWidget(desc_label)

        description_text = QLabel(self._event_description)
        description_text.setWordWrap(True)
        description_text.setStyleSheet("padding: 5px; background-color: #f5f5f5;")
        layout.addWidget(description_text)

        # Event metadata details
        details_label = QLabel("Event Details:")
        details_label.setFont(desc_font)
        layout.addWidget(details_label)

        details_text = QTextEdit()
        details_text.setReadOnly(True)
        details_text.setMaximumHeight(100)
        details_content = self._format_event_details()
        details_text.setPlainText(details_content)
        details_text.setStyleSheet("background-color: #f5f5f5;")
        layout.addWidget(details_text)

        # Simulation status
        status_label = QLabel("✓ Event simulation complete (placeholder)")
        status_font = QFont()
        status_font.setItalic(True)
        status_label.setFont(status_font)
        status_label.setStyleSheet("color: #28a745; padding: 10px;")
        layout.addWidget(status_label)

        # Add stretch to push button to bottom
        layout.addStretch()

        # OK button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("OK")
        ok_button.setMinimumWidth(100)
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        layout.addLayout(button_layout)

    def _get_event_icon(self) -> str:
        """
        Get emoji icon for event type.

        Returns:
            Emoji string representing event type
        """
        icon_map = {
            "DEADLINE": "⚠️",
            "WINDOW": "📅",
            "MILESTONE": "📌",
        }
        return icon_map.get(self._event_type, "📋")

    def _format_event_details(self) -> str:
        """
        Format event metadata for display.

        Returns:
            Formatted string with event details
        """
        details = [
            f"Date: {self._event_date.strftime('%B %d, %Y')}",
            f"Type: {self._event_type}",
        ]

        if self._event_phase:
            details.append(f"Phase: {self._event_phase}")

        details.append("\nThis is a placeholder simulation.")
        details.append("No actual game logic has been executed.")

        return "\n".join(details)


class PlaceholderEventHandler:
    """
    Placeholder event handler that shows dialogs instead of executing logic.

    Routes different event types to appropriate placeholder handlers.
    Each handler returns a standardized result dictionary.
    """

    def __init__(self):
        """Initialize placeholder event handler."""
        self._logger = logging.getLogger(__name__)

    def handle_deadline_event(
        self,
        event: DeadlineEvent,
        parent: Optional[QWidget] = None
    ) -> Dict[str, Any]:
        """
        Handle deadline event with placeholder dialog.

        Args:
            event: DeadlineEvent to simulate
            parent: Parent widget for modal dialog

        Returns:
            Result dictionary with simulated=True
        """
        self._logger.info(f"Simulating deadline event: {event.name}")

        dialog = EventSimulationDialog(
            event_name=event.name,
            event_description=event.description,
            event_date=event.event_date,
            event_type="DEADLINE",
            event_phase=event.phase,
            parent=parent
        )

        dialog.exec()  # Show modal dialog (blocks until closed)

        result = {
            "simulated": True,
            "event_id": event.id,
            "event_name": event.name,
            "event_type": "DEADLINE",
            "message": f"Deadline simulated: {event.name} on {event.event_date}",
            "cap_compliant_teams": 32,  # Placeholder
            "non_compliant_teams": [],
        }

        self._logger.info(f"Deadline event simulated: {event.name}")
        return result

    def handle_window_event(
        self,
        event: WindowEvent,
        parent: Optional[QWidget] = None
    ) -> Dict[str, Any]:
        """
        Handle window event with placeholder dialog.

        Args:
            event: WindowEvent to simulate
            parent: Parent widget for modal dialog

        Returns:
            Result dictionary with simulated=True
        """
        self._logger.info(f"Simulating window event: {event.name}")

        # Enhance description with window dates
        description = event.description
        if event.start_date and event.end_date:
            description += f"\n\nWindow: {event.start_date} to {event.end_date}"

        dialog = EventSimulationDialog(
            event_name=event.name,
            event_description=description,
            event_date=event.event_date,
            event_type="WINDOW",
            event_phase=event.phase,
            parent=parent
        )

        dialog.exec()

        result = {
            "simulated": True,
            "event_id": event.id,
            "event_name": event.name,
            "event_type": "WINDOW",
            "message": f"Window simulated: {event.name} on {event.event_date}",
            "start_date": event.start_date,
            "end_date": event.end_date,
        }

        self._logger.info(f"Window event simulated: {event.name}")
        return result

    def handle_milestone_event(
        self,
        event: MilestoneEvent,
        parent: Optional[QWidget] = None
    ) -> Dict[str, Any]:
        """
        Handle milestone event with placeholder dialog.

        Args:
            event: MilestoneEvent to simulate
            parent: Parent widget for modal dialog

        Returns:
            Result dictionary with simulated=True
        """
        self._logger.info(f"Simulating milestone event: {event.name}")

        dialog = EventSimulationDialog(
            event_name=event.name,
            event_description=event.description,
            event_date=event.event_date,
            event_type="MILESTONE",
            event_phase=event.phase,
            parent=parent
        )

        dialog.exec()

        result = {
            "simulated": True,
            "event_id": event.id,
            "event_name": event.name,
            "event_type": "MILESTONE",
            "message": f"Milestone simulated: {event.name} on {event.event_date}",
        }

        self._logger.info(f"Milestone event simulated: {event.name}")
        return result


class EventDispatcher:
    """
    Dispatches events to appropriate placeholder handlers.

    Routes events based on type and shows modal dialogs.
    Returns standardized result dictionaries.
    """

    def __init__(self):
        """Initialize event dispatcher with placeholder handler."""
        self._handler = PlaceholderEventHandler()
        self._logger = logging.getLogger(__name__)

    def dispatch_event(
        self,
        event: Any,
        parent: Optional[QWidget] = None
    ) -> Dict[str, Any]:
        """
        Dispatch event to appropriate placeholder handler.

        Args:
            event: Event to dispatch (DeadlineEvent, WindowEvent, MilestoneEvent)
            parent: Parent widget for modal dialogs

        Returns:
            Result dictionary from handler

        Raises:
            ValueError: If event type is not supported
        """
        self._logger.info(f"Dispatching event: {event.name} (type: {type(event).__name__})")

        # Route to appropriate handler based on event type
        if isinstance(event, DeadlineEvent):
            return self._handler.handle_deadline_event(event, parent)
        elif isinstance(event, WindowEvent):
            return self._handler.handle_window_event(event, parent)
        elif isinstance(event, MilestoneEvent):
            return self._handler.handle_milestone_event(event, parent)
        else:
            error_msg = f"Unsupported event type: {type(event).__name__}"
            self._logger.error(error_msg)
            raise ValueError(error_msg)

    def dispatch_multiple_events(
        self,
        events: list[Any],
        parent: Optional[QWidget] = None
    ) -> list[Dict[str, Any]]:
        """
        Dispatch multiple events in sequence.

        Each event shows its own modal dialog before proceeding to next.

        Args:
            events: List of events to dispatch
            parent: Parent widget for modal dialogs

        Returns:
            List of result dictionaries, one per event
        """
        results = []

        for event in events:
            try:
                result = self.dispatch_event(event, parent)
                results.append(result)
            except Exception as e:
                self._logger.error(f"Failed to dispatch event {event.name}: {e}")
                results.append({
                    "simulated": False,
                    "event_id": getattr(event, "id", None),
                    "event_name": getattr(event, "name", "Unknown"),
                    "error": str(e),
                    "message": f"Event simulation failed: {e}",
                })

        return results
