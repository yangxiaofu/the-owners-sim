"""
Inbox Message Models

Data models for the Owner Inbox feature.
Messages from GM, Coach, and Media with associated actions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class MessageAction:
    """
    An action that can be taken on an inbox message.

    Attributes:
        id: Unique identifier for the action
        label: Display text for the action button (e.g., "Approve", "Decline")
        style: Button style - "primary", "danger", "secondary", "warning"
        callback_key: Key for routing to the appropriate handler
    """
    id: str
    label: str
    style: str = "secondary"
    callback_key: str = ""

    def __post_init__(self):
        if not self.callback_key:
            self.callback_key = self.id


@dataclass
class InboxMessage:
    """
    A message in the owner's inbox.

    Attributes:
        id: Unique identifier for the message
        sender_type: Type of sender - "gm", "coach", "media"
        sender_name: Display name (e.g., "Mike Thompson (GM)")
        subject: Message subject line
        body: Full message content
        timestamp: When the message was sent
        is_read: Whether the message has been read
        priority: Message priority - "high", "normal", "low"
        actions: List of available actions for this message
    """
    id: str
    sender_type: str  # "gm", "coach", "media"
    sender_name: str
    subject: str
    body: str
    timestamp: datetime = field(default_factory=datetime.now)
    is_read: bool = False
    priority: str = "normal"  # "high", "normal", "low"
    actions: List[MessageAction] = field(default_factory=list)

    @property
    def sender_color(self) -> str:
        """Get the color associated with the sender type."""
        colors = {
            "gm": "#1976D2",      # Blue
            "coach": "#2E7D32",   # Green
            "media": "#F57C00",   # Orange
        }
        return colors.get(self.sender_type, "#666666")

    @property
    def sender_icon(self) -> str:
        """Get the icon/emoji for the sender type."""
        icons = {
            "gm": "GM",
            "coach": "HC",
            "media": "PR",
        }
        return icons.get(self.sender_type, "?")

    @property
    def time_ago(self) -> str:
        """Get a human-readable time difference."""
        now = datetime.now()
        diff = now - self.timestamp

        if diff.days > 0:
            if diff.days == 1:
                return "Yesterday"
            return f"{diff.days} days ago"

        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"

        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes} min ago"

        return "Just now"
