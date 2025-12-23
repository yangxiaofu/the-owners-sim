"""
Base Proposal Widget - Abstract base class for proposal type-specific widgets.

Part of Tollgate 4: Approval UI.

All proposal widgets inherit from this base class and implement:
- _setup_ui(): Build the type-specific UI
- get_summary(): Return one-line summary for batch view
"""

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGroupBox,
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import (
    Typography,
    FontSizes,
    Colors,
    TextColors,
)
from game_cycle_ui.widgets.stat_frame import create_stat_display

if TYPE_CHECKING:
    from game_cycle.models.persistent_gm_proposal import PersistentGMProposal


class BaseProposalWidget(QWidget):
    """
    Base class for proposal type-specific display widgets.

    Each subclass renders the proposal details for its specific type
    (SIGNING, EXTENSION, TRADE, etc.).

    Subclasses must implement:
    - _setup_ui(): Build the type-specific UI
    - get_summary(): Return one-line summary for batch view
    """

    def __init__(self, proposal: "PersistentGMProposal", parent=None):
        """
        Initialize the proposal widget.

        Args:
            proposal: PersistentGMProposal to display
            parent: Parent widget
        """
        super().__init__(parent)
        self._proposal = proposal
        self._setup_ui()

    @property
    def proposal(self) -> "PersistentGMProposal":
        """Get the proposal being displayed."""
        return self._proposal

    @property
    def details(self) -> dict:
        """Get the proposal details dict."""
        return self._proposal.details

    def _setup_ui(self) -> None:
        """Build the type-specific UI. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _setup_ui()")

    def get_summary(self) -> str:
        """
        Return a one-line summary for batch view display.

        Example: "WR John Smith (85 OVR) - $15M/yr"
        """
        raise NotImplementedError("Subclasses must implement get_summary()")

    # =========================================================================
    # Helper Methods for Subclasses
    # =========================================================================

    def _format_currency(self, amount: int) -> str:
        """Format an amount as currency (e.g., $15.0M, $850K)."""
        if amount is None:
            return "N/A"
        if abs(amount) >= 1_000_000:
            return f"${amount / 1_000_000:,.1f}M"
        elif abs(amount) >= 1_000:
            return f"${amount / 1_000:,.0f}K"
        else:
            return f"${amount:,}"

    def _create_info_group(self, title: str) -> tuple[QGroupBox, QHBoxLayout]:
        """
        Create a group box with horizontal layout for stat frames.

        Returns:
            Tuple of (QGroupBox, QHBoxLayout)
        """
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #444; "
            "border-radius: 4px; margin-top: 8px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 5px; }"
        )
        layout = QHBoxLayout(group)
        layout.setSpacing(20)
        return group, layout

    def _create_text_group(self, title: str) -> tuple[QGroupBox, QVBoxLayout]:
        """
        Create a group box with vertical layout for text content.

        Returns:
            Tuple of (QGroupBox, QVBoxLayout)
        """
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox { font-weight: bold; border: 1px solid #444; "
            "border-radius: 4px; margin-top: 8px; padding-top: 8px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; "
            "padding: 0 5px; }"
        )
        layout = QVBoxLayout(group)
        return group, layout

    def _create_stat_frame(
        self,
        parent_layout: QHBoxLayout,
        title: str,
        value: str,
        value_color: str = None,
    ) -> QLabel:
        """
        Create a stat display frame with title and value.

        Delegates to the centralized create_stat_display utility function.

        Args:
            parent_layout: Layout to add the frame to
            title: Stat title (e.g., "Age", "Overall")
            value: Stat value (e.g., "26", "85")
            value_color: Optional hex color for value

        Returns:
            The value QLabel for later updates
        """
        return create_stat_display(
            parent_layout,
            title,
            value,
            value_color=value_color,
        )

    def _create_header_label(self, text: str) -> QLabel:
        """Create a section header label."""
        label = QLabel(text)
        label.setFont(Typography.H4)
        label.setStyleSheet(f"color: {TextColors.ON_DARK};")
        return label

    def _create_body_label(self, text: str, word_wrap: bool = True) -> QLabel:
        """Create a body text label."""
        label = QLabel(text)
        label.setFont(Typography.BODY)
        label.setWordWrap(word_wrap)
        return label

    def _create_muted_label(self, text: str) -> QLabel:
        """Create a muted/secondary text label."""
        label = QLabel(text)
        label.setFont(Typography.CAPTION)
        label.setStyleSheet(f"color: {Colors.MUTED};")
        return label

    def _get_rating_color(self, rating: int) -> str:
        """Get color for a player rating (0-100)."""
        if rating >= 85:
            return Colors.SUCCESS  # Elite - green
        elif rating >= 75:
            return Colors.INFO  # Solid - blue
        elif rating >= 65:
            return Colors.MUTED  # Average - gray
        elif rating >= 50:
            return Colors.WARNING  # Below - orange
        else:
            return Colors.ERROR  # Poor - red

    def _create_contract_summary(self, contract: dict) -> str:
        """Create a one-line contract summary from contract dict."""
        years = contract.get("years", 0)
        total = contract.get("total", 0)
        aav = contract.get("aav", total // years if years > 0 else 0)
        guaranteed = contract.get("guaranteed", 0)

        return (
            f"{years}yr / {self._format_currency(total)} "
            f"({self._format_currency(aav)}/yr, "
            f"{self._format_currency(guaranteed)} gtd)"
        )