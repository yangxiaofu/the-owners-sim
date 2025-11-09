"""
Calendar Sync Recovery Dialog

This dialog provides UI for recovering from calendar-database synchronization failures.
Displays drift information, error context, and recovery options to the user.

Handles two main exception types:
1. CalendarSyncPersistenceException: Database write failures
2. CalendarSyncDriftException: Calendar-database drift detection

Usage Example:
    try:
        controller.advance_day()
    except CalendarSyncPersistenceException as e:
        dialog = CalendarSyncRecoveryDialog(e, parent=self)
        if dialog.exec() == QDialog.Accepted:
            # User chose recovery action
            recovery_action = dialog.get_recovery_action()
            if recovery_action == "retry":
                controller.advance_day()  # Retry
            elif recovery_action == "reload":
                controller._load_state()  # Reload from database
"""

from typing import Optional, Any
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QDialogButtonBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from src.database.sync_exceptions import (
    CalendarSyncPersistenceException,
    CalendarSyncDriftException
)


class CalendarSyncRecoveryDialog(QDialog):
    """
    Dialog for calendar-database sync error recovery.

    Displays:
    - Error type and severity
    - Drift information (if applicable)
    - Error context (dynasty_id, date, phase, etc.)
    - Recovery options (retry, reload, abort)

    Attributes:
        _exception: The sync exception that triggered this dialog
        _recovery_action: Selected recovery action ("retry", "reload", "abort")
    """

    def __init__(
        self,
        exception: Any,
        parent: Optional[Any] = None
    ):
        """
        Initialize recovery dialog.

        Args:
            exception: CalendarSyncPersistenceException or CalendarSyncDriftException
            parent: Parent widget (optional)
        """
        super().__init__(parent)

        self._exception = exception
        self._recovery_action = "abort"  # Default action

        self._setup_ui()
        self._populate_exception_details()

    def _setup_ui(self):
        """Setup dialog UI structure"""
        self.setWindowTitle("Calendar Sync Error - Recovery Options")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)

        # Main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Title with error icon
        title_layout = QHBoxLayout()
        title_label = QLabel("⚠️ Calendar-Database Synchronization Error")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        # Error summary
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        main_layout.addWidget(self.summary_label)

        # Drift information (for drift exceptions)
        self.drift_group = QGroupBox("Drift Information")
        drift_layout = QVBoxLayout()
        self.drift_info_label = QLabel()
        self.drift_info_label.setWordWrap(True)
        drift_layout.addWidget(self.drift_info_label)
        self.drift_group.setLayout(drift_layout)
        main_layout.addWidget(self.drift_group)

        # Error details
        details_group = QGroupBox("Error Details")
        details_layout = QVBoxLayout()

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(200)
        details_layout.addWidget(self.details_text)

        details_group.setLayout(details_layout)
        main_layout.addWidget(details_group)

        # Recovery options
        recovery_group = QGroupBox("Recovery Options")
        recovery_layout = QVBoxLayout()

        self.radio_retry = QRadioButton("Retry operation")
        self.radio_retry.setToolTip("Attempt the same operation again (use if error was transient)")

        self.radio_reload = QRadioButton("Reload from database")
        self.radio_reload.setToolTip("Reload simulation state from database (use if calendar drifted)")

        self.radio_abort = QRadioButton("Abort and return to safe state")
        self.radio_abort.setToolTip("Cancel operation and remain at current position")
        self.radio_abort.setChecked(True)  # Default option

        # Button group for exclusive selection
        self.recovery_button_group = QButtonGroup()
        self.recovery_button_group.addButton(self.radio_retry, 1)
        self.recovery_button_group.addButton(self.radio_reload, 2)
        self.recovery_button_group.addButton(self.radio_abort, 3)

        recovery_layout.addWidget(self.radio_retry)
        recovery_layout.addWidget(self.radio_reload)
        recovery_layout.addWidget(self.radio_abort)

        recovery_group.setLayout(recovery_layout)
        main_layout.addWidget(recovery_group)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _populate_exception_details(self):
        """Populate dialog with exception-specific information"""
        if isinstance(self._exception, CalendarSyncDriftException):
            self._populate_drift_exception()
        elif isinstance(self._exception, CalendarSyncPersistenceException):
            self._populate_persistence_exception()
        else:
            self._populate_generic_exception()

    def _populate_drift_exception(self):
        """Populate dialog for CalendarSyncDriftException"""
        exc = self._exception

        # Summary
        severity_color = self._get_severity_color(exc.drift_severity)
        summary_html = (
            f"<b>Error Type:</b> Calendar-Database Drift<br>"
            f"<b>Severity:</b> <span style='color: {severity_color};'>{exc.drift_severity.upper()}</span><br>"
            f"<b>Drift Days:</b> {exc.drift_days} days"
        )
        self.summary_label.setText(summary_html)

        # Drift information
        drift_html = (
            f"<b>Calendar Date:</b> {exc.state_info.get('calendar_date', 'N/A')}<br>"
            f"<b>Database Date:</b> {exc.state_info.get('db_date', 'N/A')}<br>"
            f"<b>Drift:</b> {exc.drift_days} days ahead<br>"
            f"<br>"
            f"<b>Recommended Action:</b> {exc.recovery_action}"
        )
        self.drift_info_label.setText(drift_html)
        self.drift_group.setVisible(True)

        # Error details
        details_text = (
            f"Error Code: {exc.error_code}\n"
            f"Sync Point: {exc.sync_point}\n"
            f"Sync Type: {exc.sync_type}\n"
            f"Timestamp: {exc.timestamp}\n"
            f"\n"
            f"State Information:\n"
        )
        for key, value in exc.state_info.items():
            details_text += f"  {key}: {value}\n"

        self.details_text.setText(details_text)

        # Configure recovery options based on severity
        if exc.drift_severity == "minor":
            # Minor drift: Suggest auto-correct (retry with correction)
            self.radio_retry.setChecked(True)
            self.radio_retry.setEnabled(True)
            self.radio_reload.setEnabled(True)
        elif exc.drift_severity == "major":
            # Major drift: Suggest reload from database
            self.radio_reload.setChecked(True)
            self.radio_retry.setEnabled(False)  # Don't retry with major drift
            self.radio_reload.setEnabled(True)
        else:  # severe
            # Severe drift: Only allow abort (need manual intervention)
            self.radio_abort.setChecked(True)
            self.radio_retry.setEnabled(False)
            self.radio_reload.setEnabled(False)

    def _populate_persistence_exception(self):
        """Populate dialog for CalendarSyncPersistenceException"""
        exc = self._exception

        # Summary
        summary_html = (
            f"<b>Error Type:</b> Database Persistence Failure<br>"
            f"<b>Operation:</b> {exc.operation}<br>"
            f"<b>Sync Point:</b> {exc.sync_point}"
        )
        self.summary_label.setText(summary_html)

        # Hide drift group (not applicable)
        self.drift_group.setVisible(False)

        # Error details
        details_text = (
            f"Error Code: {exc.error_code}\n"
            f"Operation: {exc.operation}\n"
            f"Sync Point: {exc.sync_point}\n"
            f"Sync Type: {exc.sync_type}\n"
            f"Timestamp: {exc.timestamp}\n"
            f"Recovery Action: {exc.recovery_action}\n"
            f"\n"
            f"State Information:\n"
        )
        for key, value in exc.state_info.items():
            details_text += f"  {key}: {value}\n"

        self.details_text.setText(details_text)

        # Configure recovery options
        # Persistence failures: Allow retry (might be transient DB lock)
        self.radio_retry.setEnabled(True)
        self.radio_reload.setEnabled(True)
        self.radio_abort.setChecked(True)  # Default to safe option

    def _populate_generic_exception(self):
        """Populate dialog for generic sync exception"""
        exc = self._exception

        # Summary
        summary_html = (
            f"<b>Error Type:</b> {type(exc).__name__}<br>"
            f"<b>Message:</b> {str(exc)}"
        )
        self.summary_label.setText(summary_html)

        # Hide drift group
        self.drift_group.setVisible(False)

        # Error details
        details_text = f"{type(exc).__name__}: {str(exc)}"
        if hasattr(exc, 'to_dict'):
            details_text += "\n\nException Details:\n"
            for key, value in exc.to_dict().items():
                details_text += f"  {key}: {value}\n"

        self.details_text.setText(details_text)

        # Configure recovery options
        # Generic exceptions: Only allow abort
        self.radio_retry.setEnabled(False)
        self.radio_reload.setEnabled(False)
        self.radio_abort.setChecked(True)

    def _get_severity_color(self, severity: str) -> str:
        """
        Get color for severity level.

        Args:
            severity: "minor", "major", or "severe"

        Returns:
            HTML color code
        """
        severity_colors = {
            "minor": "#FFA500",      # Orange
            "major": "#FF6347",      # Tomato red
            "severe": "#DC143C",     # Crimson
            "error": "#8B0000"       # Dark red
        }
        return severity_colors.get(severity, "#000000")

    def _on_accept(self):
        """Handle OK button click"""
        # Determine selected recovery action
        selected_id = self.recovery_button_group.checkedId()

        if selected_id == 1:
            self._recovery_action = "retry"
        elif selected_id == 2:
            self._recovery_action = "reload"
        else:
            self._recovery_action = "abort"

        self.accept()

    def get_recovery_action(self) -> str:
        """
        Get selected recovery action.

        Returns:
            "retry", "reload", or "abort"
        """
        return self._recovery_action


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    # Example 1: Drift exception
    print("=" * 80)
    print("Example 1: Calendar Drift Exception")
    print("=" * 80)

    drift_exception = CalendarSyncDriftException(
        calendar_date="2026-03-03",
        db_date="2025-11-09",
        drift_days=116,
        sync_point="advance_to_end_of_phase",
        state_info={
            "dynasty_id": "1st",
            "season": 2025,
            "calendar_phase": "offseason",
            "db_phase": "playoffs"
        }
    )

    dialog1 = CalendarSyncRecoveryDialog(drift_exception)
    result = dialog1.exec()

    if result == QDialog.Accepted:
        print(f"User selected: {dialog1.get_recovery_action()}")
    else:
        print("User cancelled")

    # Example 2: Persistence exception
    print("\n" + "=" * 80)
    print("Example 2: Persistence Exception")
    print("=" * 80)

    persistence_exception = CalendarSyncPersistenceException(
        operation="dynasty_state_update",
        sync_point="advance_day",
        state_info={
            "current_date": "2025-09-15",
            "current_phase": "regular_season",
            "current_week": 3,
            "dynasty_id": "test_dynasty",
            "error": "SQLite database is locked"
        }
    )

    dialog2 = CalendarSyncRecoveryDialog(persistence_exception)
    result = dialog2.exec()

    if result == QDialog.Accepted:
        print(f"User selected: {dialog2.get_recovery_action()}")
    else:
        print("User cancelled")

    print("\n" + "=" * 80)
    print("Calendar Sync Recovery Dialog examples completed!")
