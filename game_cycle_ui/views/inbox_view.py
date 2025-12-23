"""
Inbox View

Full page inbox view for owner messages from GM, Coach, and Media.
Master-detail layout with message list on left and detail panel on right.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSplitter, QScrollArea, QPushButton, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from game_cycle_ui.models.inbox_message import InboxMessage, MessageAction
from game_cycle_ui.theme import (
    ESPN_THEME, Typography, PRIMARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, WARNING_BUTTON_STYLE
)


# Sample messages for placeholder display
def get_sample_messages() -> List[InboxMessage]:
    """Generate sample inbox messages for demonstration."""
    return [
        InboxMessage(
            id="msg_001",
            sender_type="gm",
            sender_name="Mike Thompson (GM)",
            subject="Trade Proposal: Star WR Available",
            body="""I've identified an opportunity to acquire a Pro Bowl wide receiver from the Titans.

They're looking for draft capital and we have the assets to make this happen. The player would immediately become our WR1 and give us a legitimate deep threat.

Terms being discussed:
- We send: 2025 1st Round Pick + 2025 4th Round Pick
- We receive: Jaylen Woods (WR, 94 OVR, 26 years old)

His contract is $18M/year with 3 years remaining. This fits within our cap situation.

I recommend we move forward with this trade. Let me know your decision.""",
            timestamp=datetime.now() - timedelta(hours=2),
            is_read=False,
            priority="high",
            actions=[
                MessageAction("approve", "Approve Trade", "primary", "approve_trade"),
                MessageAction("decline", "Decline", "danger", "decline_trade"),
                MessageAction("defer", "Review Later", "secondary", "defer_trade"),
            ]
        ),
        InboxMessage(
            id="msg_002",
            sender_type="media",
            sender_name="ESPN Sports Desk",
            subject="Interview Request: Season Preview",
            body="""Dear Owner,

We'd like to schedule an interview for our preseason coverage segment "Owners Speak."

This would be a 15-minute segment discussing:
- Your expectations for the upcoming season
- Recent roster moves and their impact
- Your vision for the franchise's future

The interview would air during our Sunday NFL Countdown show, reaching millions of viewers.

Please let us know if you're interested in participating.

Best regards,
ESPN Sports Desk""",
            timestamp=datetime.now() - timedelta(days=1),
            is_read=True,
            priority="normal",
            actions=[
                MessageAction("accept", "Accept Interview", "primary", "accept_interview"),
                MessageAction("decline", "Decline", "secondary", "decline_interview"),
            ]
        ),
        InboxMessage(
            id="msg_003",
            sender_type="coach",
            sender_name="John Williams (HC)",
            subject="Roster Concern: CB Depth",
            body="""I wanted to bring to your attention that we're thin at cornerback heading into the season.

Current situation:
- CB1: Marcus Johnson (83 OVR) - Healthy
- CB2: Devon Smith (74 OVR) - Healthy
- CB3: Rookie - Still developing

If either starter goes down, we'll be in trouble. The division has strong passing attacks and we need insurance.

I recommend we explore the free agent market or trade options before Week 1.

Let me know if you'd like to discuss further.

- Coach Williams""",
            timestamp=datetime.now() - timedelta(days=3),
            is_read=True,
            priority="normal",
            actions=[
                MessageAction("ack", "Acknowledge", "primary", "acknowledge_concern"),
                MessageAction("meeting", "Schedule Meeting", "secondary", "schedule_meeting"),
            ]
        ),
        InboxMessage(
            id="msg_004",
            sender_type="gm",
            sender_name="Mike Thompson (GM)",
            subject="Free Agency Target: Elite Pass Rusher",
            body="""I've been monitoring the free agent market and there's an elite pass rusher available.

Player: Terrell Adams (EDGE, 91 OVR, 28 years old)
- Led the league in sacks last season (14.5)
- 3x Pro Bowl selection
- Asking price: ~$22M/year

He would transform our defense and put pressure on opposing QBs. We have the cap space to make this signing.

Should I pursue negotiations?""",
            timestamp=datetime.now() - timedelta(days=5),
            is_read=True,
            priority="normal",
            actions=[
                MessageAction("pursue", "Pursue Signing", "primary", "pursue_fa"),
                MessageAction("pass", "Pass", "secondary", "pass_fa"),
            ]
        ),
    ]


class MessageListItem(QFrame):
    """Single row in the message list."""

    clicked = Signal(str)  # message_id

    def __init__(self, message: InboxMessage, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.message = message
        self._is_selected = False
        self._setup_ui()

    def _setup_ui(self):
        """Build the list item UI."""
        self.setObjectName("MessageListItem")
        self.setCursor(Qt.PointingHandCursor)
        self._update_style()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # Sender badge (colored circle with initials)
        badge = QLabel(self.message.sender_icon)
        badge.setFixedSize(36, 36)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFont(QFont("Arial", 10, QFont.Bold))
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {self.message.sender_color};
                color: white;
                border-radius: 18px;
            }}
        """)
        layout.addWidget(badge)

        # Message info (subject + sender name)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Subject line
        subject_label = QLabel(self.message.subject)
        font_weight = QFont.Bold if not self.message.is_read else QFont.Normal
        subject_font = QFont("Arial", 12, font_weight)
        subject_label.setFont(subject_font)
        subject_label.setStyleSheet(f"color: {'#ffffff' if not self.message.is_read else '#cccccc'};")
        info_layout.addWidget(subject_label)

        # Sender name
        sender_label = QLabel(self.message.sender_name)
        sender_label.setFont(QFont("Arial", 10))
        sender_label.setStyleSheet("color: #888888;")
        info_layout.addWidget(sender_label)

        layout.addLayout(info_layout, 1)

        # Timestamp + unread dot
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)

        time_label = QLabel(self.message.time_ago)
        time_label.setFont(QFont("Arial", 9))
        time_label.setStyleSheet("color: #666666;")
        right_layout.addWidget(time_label)

        # Unread indicator
        if not self.message.is_read:
            unread_dot = QLabel()
            unread_dot.setFixedSize(8, 8)
            unread_dot.setStyleSheet(f"""
                QLabel {{
                    background-color: {self.message.sender_color};
                    border-radius: 4px;
                }}
            """)
            right_layout.addWidget(unread_dot, alignment=Qt.AlignRight)

        layout.addLayout(right_layout)

    def _update_style(self):
        """Update the item's background style."""
        if self._is_selected:
            self.setStyleSheet(f"""
                QFrame#MessageListItem {{
                    background-color: #3a3a3a;
                    border-left: 3px solid #cc0000;
                    border-bottom: 1px solid #444444;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#MessageListItem {{
                    background-color: #2a2a2a;
                    border-bottom: 1px solid #444444;
                }}
                QFrame#MessageListItem:hover {{
                    background-color: #333333;
                }}
            """)

    def set_selected(self, selected: bool):
        """Set the selected state of this item."""
        self._is_selected = selected
        self._update_style()

    def mousePressEvent(self, event):
        """Handle mouse click."""
        self.clicked.emit(self.message.id)
        super().mousePressEvent(event)


class MessageDetailPanel(QFrame):
    """Panel showing full message content and actions."""

    action_clicked = Signal(str, str)  # message_id, action_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_message: Optional[InboxMessage] = None
        self._setup_ui()

    def _setup_ui(self):
        """Build the detail panel UI."""
        self.setObjectName("MessageDetailPanel")
        self.setStyleSheet(f"""
            QFrame#MessageDetailPanel {{
                background-color: #1a1a1a;
                border-left: 1px solid #444444;
            }}
        """)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(20, 20, 20, 20)
        self._layout.setSpacing(16)

        # Header section
        self._header_widget = QWidget()
        header_layout = QVBoxLayout(self._header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._from_label = QLabel()
        self._from_label.setFont(QFont("Arial", 11))
        self._from_label.setStyleSheet("color: #888888;")
        header_layout.addWidget(self._from_label)

        self._subject_label = QLabel()
        self._subject_label.setFont(QFont("Arial", 18, QFont.Bold))
        self._subject_label.setStyleSheet("color: #ffffff;")
        self._subject_label.setWordWrap(True)
        header_layout.addWidget(self._subject_label)

        self._time_label = QLabel()
        self._time_label.setFont(QFont("Arial", 10))
        self._time_label.setStyleSheet("color: #666666;")
        header_layout.addWidget(self._time_label)

        self._layout.addWidget(self._header_widget)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #444444;")
        divider.setFixedHeight(1)
        self._layout.addWidget(divider)

        # Body section (scrollable)
        body_scroll = QScrollArea()
        body_scroll.setWidgetResizable(True)
        body_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
            QWidget { background: transparent; }
        """)

        body_widget = QWidget()
        body_layout = QVBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self._body_label = QLabel()
        self._body_label.setFont(QFont("Arial", 12))
        self._body_label.setStyleSheet("color: #e0e0e0; line-height: 1.6;")
        self._body_label.setWordWrap(True)
        self._body_label.setTextFormat(Qt.PlainText)
        body_layout.addWidget(self._body_label)
        body_layout.addStretch()

        body_scroll.setWidget(body_widget)
        self._layout.addWidget(body_scroll, 1)

        # Actions section
        self._actions_widget = QWidget()
        self._actions_layout = QHBoxLayout(self._actions_widget)
        self._actions_layout.setContentsMargins(0, 16, 0, 0)
        self._actions_layout.setSpacing(12)
        self._actions_layout.addStretch()
        self._layout.addWidget(self._actions_widget)

        # Empty state
        self._empty_label = QLabel("Select a message to read")
        self._empty_label.setFont(QFont("Arial", 14))
        self._empty_label.setStyleSheet("color: #666666;")
        self._empty_label.setAlignment(Qt.AlignCenter)

        self.clear()

    def set_message(self, message: InboxMessage):
        """Display the given message."""
        self._current_message = message

        # Show content, hide empty state
        self._header_widget.show()
        self._body_label.parent().parent().show()  # body scroll area
        self._actions_widget.show()
        self._empty_label.hide()

        # Update content
        self._from_label.setText(f"From: {message.sender_name}")
        self._subject_label.setText(message.subject)
        self._time_label.setText(message.timestamp.strftime("%B %d, %Y at %I:%M %p"))
        self._body_label.setText(message.body)

        # Clear and rebuild actions
        while self._actions_layout.count() > 1:  # Keep the stretch
            item = self._actions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add action buttons
        for action in message.actions:
            btn = QPushButton(action.label)
            btn.setMinimumWidth(120)

            # Apply style based on action type
            if action.style == "primary":
                btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
            elif action.style == "danger":
                btn.setStyleSheet(DANGER_BUTTON_STYLE)
            elif action.style == "warning":
                btn.setStyleSheet(WARNING_BUTTON_STYLE)
            else:
                btn.setStyleSheet(SECONDARY_BUTTON_STYLE)

            btn.clicked.connect(
                lambda checked, mid=message.id, aid=action.id: self.action_clicked.emit(mid, aid)
            )
            self._actions_layout.insertWidget(self._actions_layout.count() - 1, btn)

    def clear(self):
        """Show empty state."""
        self._current_message = None
        self._header_widget.hide()
        self._body_label.parent().parent().hide()  # body scroll area
        self._actions_widget.hide()

        # Show empty label
        if self._empty_label.parent() is None:
            self._layout.insertWidget(0, self._empty_label)
        self._empty_label.show()


class InboxView(QWidget):
    """
    Full page inbox view with master-detail layout.

    Shows messages from GM, Coach, and Media with action buttons.
    """

    action_triggered = Signal(str, str)  # message_id, action_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._messages: Dict[str, InboxMessage] = {}
        self._list_items: Dict[str, MessageListItem] = {}
        self._selected_id: Optional[str] = None
        self._setup_ui()
        self._load_sample_messages()

    def _setup_ui(self):
        """Build the inbox view UI."""
        self.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: #1a1a1a;
                border-bottom: 2px solid #cc0000;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)

        title = QLabel("Inbox")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        layout.addWidget(header)

        # Splitter for master-detail
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #444444;
                width: 1px;
            }
        """)

        # Left panel - Message list
        list_panel = QFrame()
        list_panel.setStyleSheet(f"background-color: {ESPN_THEME['card_bg']};")
        list_layout = QVBoxLayout(list_panel)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)

        # Message list scroll area
        self._list_scroll = QScrollArea()
        self._list_scroll.setWidgetResizable(True)
        self._list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list_scroll.setStyleSheet("""
            QScrollArea { background: transparent; border: none; }
        """)

        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch()

        self._list_scroll.setWidget(self._list_widget)
        list_layout.addWidget(self._list_scroll)

        splitter.addWidget(list_panel)

        # Right panel - Message detail
        self._detail_panel = MessageDetailPanel()
        self._detail_panel.action_clicked.connect(self._on_action_clicked)
        splitter.addWidget(self._detail_panel)

        # Set initial sizes (35% / 65%)
        splitter.setSizes([350, 650])

        layout.addWidget(splitter, 1)

    def _load_sample_messages(self):
        """Load sample messages for demonstration."""
        self.set_messages(get_sample_messages())

    def set_messages(self, messages: List[InboxMessage]):
        """Populate the inbox with messages."""
        # Clear existing
        self._messages.clear()
        self._list_items.clear()
        self._selected_id = None

        # Clear list layout (keep stretch at end)
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add new messages
        for msg in messages:
            self._messages[msg.id] = msg

            list_item = MessageListItem(msg)
            list_item.clicked.connect(self._on_message_selected)
            self._list_items[msg.id] = list_item

            self._list_layout.insertWidget(self._list_layout.count() - 1, list_item)

        # Select first message if available
        if messages:
            self._on_message_selected(messages[0].id)

    def _on_message_selected(self, message_id: str):
        """Handle message selection."""
        # Update selection state
        if self._selected_id and self._selected_id in self._list_items:
            self._list_items[self._selected_id].set_selected(False)

        self._selected_id = message_id

        if message_id in self._list_items:
            self._list_items[message_id].set_selected(True)

        # Show message in detail panel
        if message_id in self._messages:
            msg = self._messages[message_id]
            msg.is_read = True  # Mark as read
            self._detail_panel.set_message(msg)

    def _on_action_clicked(self, message_id: str, action_id: str):
        """Handle action button click."""
        print(f"[InboxView] Action '{action_id}' triggered on message '{message_id}'")
        self.action_triggered.emit(message_id, action_id)

        # Placeholder: Show feedback
        msg = self._messages.get(message_id)
        if msg:
            action_labels = {a.id: a.label for a in msg.actions}
            label = action_labels.get(action_id, action_id)
            print(f"[InboxView] Placeholder: Would execute '{label}' for message from {msg.sender_name}")
