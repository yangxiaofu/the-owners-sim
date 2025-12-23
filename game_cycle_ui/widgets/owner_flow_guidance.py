"""
Owner Flow Guidance - Manages flow guidance banner and button state.

Extracts the complex banner/button state management logic from OwnerView
into a dedicated, testable class.
"""

from dataclasses import dataclass
from PySide6.QtWidgets import QFrame, QPushButton, QTabWidget, QLabel
from game_cycle_ui.theme import Colors, UITheme, FontSizes


@dataclass
class FlowState:
    """Represents completion state of Owner Review steps."""
    summary_reviewed: bool = False
    staff_decisions_complete: bool = False
    directives_saved: bool = False

    # Staff-specific state for detailed messages
    gm_fired_not_hired: bool = False
    hc_fired_not_hired: bool = False

    # Current wizard step (1 or 2)
    current_step: int = 1

    def is_complete(self) -> bool:
        """True if all owner review steps are done."""
        return (self.summary_reviewed and
                self.staff_decisions_complete and
                self.directives_saved)

    def can_proceed_to_step_2(self) -> bool:
        """True if Step 1 is complete and user can advance to Step 2."""
        return self.summary_reviewed and self.staff_decisions_complete

    def can_complete(self) -> bool:
        """True if directives are saved and user can continue to next stage."""
        return self.directives_saved


class OwnerFlowGuidance:
    """Manages flow guidance banner and button state for Owner Review."""

    def __init__(self, banner: QFrame, banner_icon: QLabel, banner_text: QLabel,
                 action_btn: QPushButton, tab_widget: QTabWidget):
        """
        Initialize flow guidance manager.

        Args:
            banner: The action banner frame
            banner_icon: Icon label within banner
            banner_text: Text label within banner
            action_btn: Action button within banner
            tab_widget: Tab widget for updating tab titles
        """
        self.banner = banner
        self.banner_icon = banner_icon
        self.banner_text = banner_text
        self.action_btn = action_btn
        self.tab_widget = tab_widget

    def update(self, state: FlowState):
        """
        Update banner based on current wizard step and completion state.

        Args:
            state: Current flow state
        """
        # Update banner based on current step
        if state.is_complete():
            self._show_complete_banner()
        elif state.current_step == 1:
            self._show_step1_banner(state)
        elif state.current_step == 2:
            self._show_step2_banner()

    def _show_complete_banner(self):
        """All steps complete - show success banner."""
        self.banner.setStyleSheet(f"""
            QFrame#action_banner {{
                background-color: {Colors.SUCCESS_DARK};
                border: 2px solid {Colors.SUCCESS};
                border-radius: 10px;
                padding: 12px;
            }}
        """)

        self.banner_icon.setText("\u2713")  # Checkmark
        self.banner_icon.setStyleSheet(f"""
            QLabel {{
                color: {Colors.SUCCESS};
                font-size: 24px;
                font-weight: bold;
                min-width: 40px;
                max-width: 40px;
            }}
        """)

        self.banner_text.setText(
            "Review complete! Continue to Franchise Tag stage."
        )
        self.banner_text.setStyleSheet(f"color: {Colors.SUCCESS};")

        # Hide action button (navigation is in footer)
        self.action_btn.setVisible(False)

    def _show_step1_banner(self, state: FlowState):
        """Step 1: Season Review banner."""
        self.banner.setStyleSheet(f"""
            QFrame#action_banner {{
                background-color: {Colors.INFO_DARK};
                border: 2px solid {Colors.INFO};
                border-radius: 10px;
                padding: 12px;
            }}
        """)

        self.banner_icon.setText("1")
        self.banner_icon.setStyleSheet(f"""
            QLabel {{
                color: {Colors.INFO};
                background-color: {Colors.INFO};
                border-radius: 10px;
                font-size: {FontSizes.BODY};
                font-weight: bold;
                padding: 2px 6px;
            }}
        """)

        # Show specific message if staff decisions are pending
        if state.gm_fired_not_hired:
            msg = "Step 1 of 2: You fired the GM - select a replacement before continuing."
        elif state.hc_fired_not_hired:
            msg = "Step 1 of 2: You fired the Head Coach - select a replacement before continuing."
        else:
            msg = "Step 1 of 2: Review your team's season performance and make staff decisions."

        self.banner_text.setText(msg)
        self.banner_text.setStyleSheet(f"color: {Colors.INFO};")

        # Hide action button (navigation is in footer)
        self.action_btn.setVisible(False)

    def _show_step2_banner(self):
        """Step 2: Strategic Direction banner."""
        self.banner.setStyleSheet(f"""
            QFrame#action_banner {{
                background-color: {Colors.INFO_DARK};
                border: 2px solid {Colors.INFO};
                border-radius: 10px;
                padding: 12px;
            }}
        """)

        self.banner_icon.setText("2")
        self.banner_icon.setStyleSheet(f"""
            QLabel {{
                color: {Colors.INFO};
                background-color: {Colors.INFO};
                border-radius: 10px;
                font-size: {FontSizes.BODY};
                font-weight: bold;
                padding: 2px 6px;
            }}
        """)

        self.banner_text.setText(
            "Step 2 of 2: Set strategic direction for the upcoming season."
        )
        self.banner_text.setStyleSheet(f"color: {Colors.INFO};")

        # Hide action button (navigation is in footer)
        self.action_btn.setVisible(False)
