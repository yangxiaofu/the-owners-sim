"""
SocialPostCard - Individual social media post display widget.

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 6.

Displays a single social media post with:
- User handle + display name
- Personality badge (FAN/MEDIA)
- Post text content
- Reaction bar (likes/retweets)
- Sentiment-based styling
- Hover effect

Layout:
    [@handle] Display Name     [FAN]
    Post text content here (supports multi-line)
    ♥ 234  ↻ 67

Inspired by Twitter/X card design with ESPN color scheme.
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.widgets.personality_badge import PersonalityBadge
from game_cycle_ui.widgets.reaction_bar import ReactionBar


# Color scheme
ESPN_CARD_BG = "#1a1a1a"
ESPN_CARD_HOVER = "#252525"
ESPN_BORDER = "#333333"
ESPN_TEXT_PRIMARY = "#FFFFFF"
ESPN_TEXT_SECONDARY = "#888888"
ESPN_TEXT_MUTED = "#666666"

# Sentiment border colors (subtle left accent)
SENTIMENT_BORDER_COLORS = {
    "positive": "#4CAF50",   # Green
    "negative": "#F44336",   # Red
    "neutral": "#666666",    # Darker gray for dark background
}


class SocialPostCard(QWidget):
    """
    Individual social media post card with hover effect.

    Displays user info, post content, and engagement metrics.
    Sentiment-based left border accent for visual interest.

    Signals:
        clicked: Emitted when card is clicked (optional interaction)
    """

    clicked = Signal(int)  # post_id

    def __init__(
        self,
        post_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the social post card.

        Args:
            post_data: Dictionary containing post information:
                - id: Post ID
                - handle: User handle (e.g., "@AlwaysBelievinBill")
                - display_name: Display name (e.g., "Always Believin' Bills")
                - personality_type: Type ("FAN", "MEDIA", etc.)
                - post_text: Post content text
                - sentiment: Sentiment score (-1.0 to 1.0)
                - likes: Number of likes
                - retweets: Number of retweets
            parent: Parent widget
        """
        super().__init__(parent)
        self._post_data = post_data
        self._post_id = post_data.get('id', 0)
        self._setup_ui()

    def _setup_ui(self):
        """Build the post card UI."""
        # Set height constraints
        self.setMinimumHeight(80)
        self.setMaximumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Container frame with sentiment accent border
        self._container = QFrame()
        self._container.setObjectName("social_post_card")
        self._apply_style(hovered=False)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(8)

        # Top row: User info + badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        # User info (handle + display name)
        user_info = self._create_user_info()
        top_row.addWidget(user_info)

        # Spacer
        top_row.addStretch()

        # Personality badge
        personality_type = self._post_data.get('personality_type', 'FAN')
        badge = PersonalityBadge(personality_type)
        top_row.addWidget(badge)

        container_layout.addLayout(top_row)

        # Post text content
        post_text = self._post_data.get('post_text', '')
        text_label = QLabel(post_text)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"""
            QLabel {{
                color: {ESPN_TEXT_PRIMARY};
                font-size: 13px;
                line-height: 1.4;
                padding: 4px 0;
            }}
        """)
        text_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        container_layout.addWidget(text_label)

        # Reaction bar
        likes = self._post_data.get('likes', 0)
        retweets = self._post_data.get('retweets', 0)
        reaction_bar = ReactionBar(likes, retweets)
        container_layout.addWidget(reaction_bar)

        layout.addWidget(self._container)

    def _create_user_info(self) -> QWidget:
        """
        Create user info section (handle + display name).

        Returns:
            Widget containing user info
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Handle (bold, slightly larger)
        handle = self._post_data.get('handle', '@unknown')
        handle_label = QLabel(handle)
        handle_label.setStyleSheet(f"""
            QLabel {{
                color: {ESPN_TEXT_PRIMARY};
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(handle_label)

        # Display name (muted, smaller)
        display_name = self._post_data.get('display_name', '')
        if display_name:
            name_label = QLabel(display_name)
            name_label.setStyleSheet(f"""
                QLabel {{
                    color: {ESPN_TEXT_MUTED};
                    font-size: 11px;
                }}
            """)
            layout.addWidget(name_label)

        return container

    def _get_sentiment_color(self) -> str:
        """
        Get border accent color based on sentiment.

        Returns:
            Color hex code
        """
        sentiment = self._post_data.get('sentiment', 0.0)

        if sentiment > 0.3:
            return SENTIMENT_BORDER_COLORS['positive']
        elif sentiment < -0.3:
            return SENTIMENT_BORDER_COLORS['negative']
        else:
            return SENTIMENT_BORDER_COLORS['neutral']

    def _apply_style(self, hovered: bool):
        """
        Apply card styling with sentiment accent.

        Args:
            hovered: Whether card is currently hovered
        """
        bg_color = ESPN_CARD_HOVER if hovered else ESPN_CARD_BG
        border_color = self._get_sentiment_color()

        self._container.setStyleSheet(f"""
            QFrame#social_post_card {{
                background-color: {bg_color};
                border: 1px solid {ESPN_BORDER};
                border-left: 3px solid {border_color};
                border-radius: 4px;
            }}
        """)

    def enterEvent(self, event):
        """Handle mouse enter (hover effect)."""
        self._apply_style(hovered=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave (remove hover effect)."""
        self._apply_style(hovered=False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._post_id)
        super().mousePressEvent(event)
