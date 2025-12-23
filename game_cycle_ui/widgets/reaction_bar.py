"""
ReactionBar - Compact display of post engagement metrics.

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 6.

Displays likes and retweets counts with icons in a compact horizontal bar:
- ♥ 234 likes
- ↻ 67 retweets

Uses muted gray colors for non-intrusive display.
"""

from typing import Optional

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class ReactionBar(QWidget):
    """
    Compact horizontal bar displaying engagement metrics.

    Shows likes and retweets with simple icons and counts.
    Uses muted styling to not compete with post content.

    Example:
        bar = ReactionBar(likes=234, retweets=67)
        # Displays: "♥ 234  ↻ 67"
    """

    def __init__(
        self,
        likes: int,
        retweets: int,
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the reaction bar.

        Args:
            likes: Number of likes
            retweets: Number of retweets
            parent: Parent widget
        """
        super().__init__(parent)
        self._likes = likes
        self._retweets = retweets
        self._setup_ui()

    def _setup_ui(self):
        """Build the reaction bar UI."""
        # Main horizontal layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Likes section
        likes_label = self._create_metric_label(
            icon="♥",
            count=self._likes,
            color="#888888"
        )
        layout.addWidget(likes_label)

        # Retweets section
        retweets_label = self._create_metric_label(
            icon="↻",
            count=self._retweets,
            color="#888888"
        )
        layout.addWidget(retweets_label)

        # Spacer to push everything left
        layout.addStretch()

    def _create_metric_label(self, icon: str, count: int, color: str) -> QLabel:
        """
        Create a metric label with icon and count.

        Args:
            icon: Icon character (e.g., "♥", "↻")
            count: Metric count
            color: Text color

        Returns:
            Configured QLabel
        """
        # Format count with K/M abbreviations for large numbers
        formatted_count = self._format_count(count)

        # Create label with icon + count
        label = QLabel(f"{icon} {formatted_count}")
        label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                font-weight: 500;
            }}
        """)

        return label

    def _format_count(self, count: int) -> str:
        """
        Format count with K/M abbreviations.

        Args:
            count: Raw count

        Returns:
            Formatted string (e.g., "1.2K", "4.5M", "234")
        """
        if count >= 1_000_000:
            return f"{count / 1_000_000:.1f}M"
        elif count >= 1_000:
            return f"{count / 1_000:.1f}K"
        else:
            return str(count)

    def update_counts(self, likes: int, retweets: int):
        """
        Update reaction counts dynamically.

        Args:
            likes: New likes count
            retweets: New retweets count
        """
        self._likes = likes
        self._retweets = retweets

        # Rebuild UI with new counts
        # Clear existing widgets
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Rebuild
        self._setup_ui()
