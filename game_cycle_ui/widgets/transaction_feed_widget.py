"""
Transaction Feed Widget - Chronological feed of roster moves and transactions.

Displays:
- Date-grouped transaction cards
- Transaction type icons (Trade, Signing, Cut, Extension, Tag)
- Expandable cards for full details
- Filter by team/type
- Date range selector
- Search functionality

Layout:
    ┌────────────────────────────────────────┐
    │ [Filter] [Date Range] [Search]         │
    ├────────────────────────────────────────┤
    │ 📅 DECEMBER 14, 2025                   │
    │ ┌────────────────────────────────────┐ │
    │ │ 🔄 TRADE                            │ │
    │ │ Chiefs acquire WR Hopkins           │ │
    │ │ • KC gets: WR Hopkins               │ │
    │ │ • TEN gets: 2026 3rd                │ │
    │ └────────────────────────────────────┘ │
    │ ┌────────────────────────────────────┐ │
    │ │ ✍️ SIGNING                         │ │
    │ │ Bills sign CB Gilmore (2yr, $18M)   │ │
    │ └────────────────────────────────────┘ │
    └────────────────────────────────────────┘
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle_ui.theme import (
    ESPN_THEME,
    Colors,
    Typography,
    FontSizes,
    TextColors,
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_CARD_HOVER,
    ESPN_BORDER,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_TEXT_MUTED,
)


# Transaction type icons and colors
TRANSACTION_TYPES = {
    "TRADE": {"icon": "🔄", "label": "TRADE", "color": "#00838F"},
    "SIGNING": {"icon": "✍️", "label": "SIGNING", "color": "#00695C"},
    "CUT": {"icon": "✂️", "label": "CUT", "color": "#C62828"},
    "EXTENSION": {"icon": "📝", "label": "EXTENSION", "color": "#2E7D32"},
    "TAG": {"icon": "🏷️", "label": "TAG", "color": "#F9A825"},
}


class TransactionCard(QFrame):
    """
    Single transaction card displaying:
    - Transaction type icon and label
    - Primary description
    - Expandable details
    - Team colors (optional)
    """

    clicked = Signal(str)  # transaction_id

    def __init__(
        self,
        transaction_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        """
        Initialize transaction card.

        Args:
            transaction_data: Dictionary with keys:
                - transaction_id: str
                - type: str (TRADE, SIGNING, CUT, EXTENSION, TAG)
                - date: str (ISO format or display string)
                - primary_text: str (main description)
                - details: List[str] (detail lines)
                - team_colors: Optional[List[str]] (hex colors for accent)
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = transaction_data
        self._is_expanded = False
        self._setup_ui()

    def _setup_ui(self):
        """Build the transaction card UI."""
        # Card styling
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border: 1px solid {ESPN_BORDER};
                border-radius: 6px;
            }}
            QFrame:hover {{
                background-color: {ESPN_CARD_HOVER};
                border: 1px solid {ESPN_RED};
            }}
        """)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Header row: Icon + Type + Primary text
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Transaction type icon and label
        trans_type = self._data.get("type", "TRADE")
        type_info = TRANSACTION_TYPES.get(trans_type, TRANSACTION_TYPES["TRADE"])

        icon_label = QLabel(type_info["icon"])
        icon_label.setFont(Typography.H5)
        icon_label.setFixedWidth(30)
        header_layout.addWidget(icon_label)

        type_label = QLabel(type_info["label"])
        type_label.setFont(Typography.CAPTION_BOLD)
        type_label.setStyleSheet(f"""
            color: {type_info['color']};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        type_label.setFixedWidth(80)
        header_layout.addWidget(type_label)

        # Primary description
        primary_text = self._data.get("primary_text", "Transaction")
        primary_label = QLabel(primary_text)
        primary_label.setFont(Typography.BODY_BOLD)
        primary_label.setWordWrap(True)
        primary_label.setStyleSheet(f"color: {ESPN_TEXT_PRIMARY};")
        header_layout.addWidget(primary_label, 1)

        layout.addLayout(header_layout)

        # Details section (expandable)
        self._details_container = QWidget()
        details_layout = QVBoxLayout(self._details_container)
        details_layout.setContentsMargins(40, 0, 0, 0)  # Indent under icon
        details_layout.setSpacing(4)

        details = self._data.get("details", [])
        for detail in details:
            detail_label = QLabel(f"• {detail}")
            detail_label.setFont(Typography.BODY_SMALL)
            detail_label.setStyleSheet(f"color: {ESPN_TEXT_SECONDARY};")
            detail_label.setWordWrap(True)
            details_layout.addWidget(detail_label)

        # Show details by default if only a few lines
        if len(details) <= 2:
            self._is_expanded = True
            self._details_container.setVisible(True)
        else:
            self._is_expanded = False
            self._details_container.setVisible(False)

        layout.addWidget(self._details_container)

    def mousePressEvent(self, event):
        """Toggle expansion on click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_expanded = not self._is_expanded
            self._details_container.setVisible(self._is_expanded)

            # Adjust height
            if self._is_expanded:
                self.setMinimumHeight(150)
            else:
                self.setMinimumHeight(100)

            # Emit signal
            self.clicked.emit(self._data.get("transaction_id", ""))

        super().mousePressEvent(event)


class DateHeaderWidget(QFrame):
    """Date header for grouping transactions."""

    def __init__(self, date_str: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._date_str = date_str
        self._setup_ui()

    def _setup_ui(self):
        """Build date header UI."""
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_DARK_BG};
                border-bottom: 2px solid {ESPN_BORDER};
            }}
        """)
        self.setFixedHeight(40)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)

        icon = QLabel("📅")
        icon.setFont(Typography.BODY)
        layout.addWidget(icon)

        date_label = QLabel(self._date_str.upper())
        date_label.setFont(Typography.H6)
        date_label.setStyleSheet(f"""
            color: {ESPN_TEXT_PRIMARY};
            font-weight: bold;
            letter-spacing: 1px;
        """)
        layout.addWidget(date_label)

        layout.addStretch()


class TransactionFeedWidget(QWidget):
    """
    Widget displaying a chronological feed of transactions.

    Features:
    - Date-grouped transaction cards
    - Filter by team/type
    - Date range selector
    - Search by player/team name
    - Vertical scrolling feed
    """

    transaction_clicked = Signal(str)  # transaction_id

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._transactions: List[Dict] = []
        self._filtered_transactions: List[Dict] = []
        self._transaction_cards: List[TransactionCard] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the widget UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # =================================================================
        # FILTER BAR
        # =================================================================
        filter_bar = QFrame()
        filter_bar.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-bottom: 2px solid {ESPN_BORDER};
        """)
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(16, 12, 16, 12)
        filter_layout.setSpacing(12)

        # Type filter dropdown
        filter_layout.addWidget(QLabel("Type:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems([
            "All Types",
            "Trades",
            "Signings",
            "Cuts",
            "Extensions",
            "Tags"
        ])
        self.type_filter.setStyleSheet(self._get_combobox_style())
        self.type_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.type_filter)

        # Date range selector
        filter_layout.addWidget(QLabel("Period:"))
        self.date_range_filter = QComboBox()
        self.date_range_filter.addItems([
            "Last 7 Days",
            "Last 30 Days",
            "This Season",
            "All Time"
        ])
        self.date_range_filter.setStyleSheet(self._get_combobox_style())
        self.date_range_filter.currentTextChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self.date_range_filter)

        filter_layout.addStretch()

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search player or team...")
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {ESPN_DARK_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: {FontSizes.BODY};
            }}
            QLineEdit:focus {{
                border: 1px solid {ESPN_RED};
            }}
        """)
        self.search_input.setFixedWidth(250)
        self.search_input.textChanged.connect(self._on_search_changed)
        filter_layout.addWidget(self.search_input)

        main_layout.addWidget(filter_bar)

        # =================================================================
        # TRANSACTION FEED (Scrollable)
        # =================================================================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background-color: {ESPN_DARK_BG}; border: none;")

        self.feed_container = QWidget()
        self.feed_layout = QVBoxLayout(self.feed_container)
        self.feed_layout.setContentsMargins(16, 16, 16, 16)
        self.feed_layout.setSpacing(12)

        # Empty state placeholder
        self.empty_label = QLabel("No transactions to display")
        self.empty_label.setFont(Typography.H5)
        self.empty_label.setStyleSheet(f"color: {ESPN_TEXT_MUTED}; padding: 40px;")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.feed_layout.addWidget(self.empty_label)

        self.feed_layout.addStretch()

        scroll.setWidget(self.feed_container)
        main_layout.addWidget(scroll)

    def _get_combobox_style(self) -> str:
        """Get consistent combobox styling."""
        return f"""
            QComboBox {{
                background-color: {ESPN_DARK_BG};
                color: {ESPN_TEXT_PRIMARY};
                border: 1px solid {ESPN_BORDER};
                border-radius: 4px;
                padding: 6px 12px;
                font-size: {FontSizes.SMALL};
                min-width: 120px;
            }}
            QComboBox:hover {{
                border: 1px solid {ESPN_RED};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {ESPN_TEXT_SECONDARY};
            }}
        """

    def set_transactions(self, transactions: List[Dict]):
        """
        Set the transaction data to display.

        Args:
            transactions: List of transaction dicts, each containing:
                - transaction_id: str
                - type: str (TRADE, SIGNING, CUT, EXTENSION, TAG)
                - date: str (ISO format: YYYY-MM-DD)
                - primary_text: str
                - details: List[str]
                - team_ids: Optional[List[int]]
                - player_names: Optional[List[str]]
        """
        self._transactions = transactions
        self._apply_filters()

    def _apply_filters(self):
        """Apply current filters and rebuild the feed."""
        # Filter by type
        type_filter = self.type_filter.currentText()
        type_map = {
            "All Types": None,
            "Trades": "TRADE",
            "Signings": "SIGNING",
            "Cuts": "CUT",
            "Extensions": "EXTENSION",
            "Tags": "TAG"
        }
        selected_type = type_map.get(type_filter)

        # Filter by search text
        search_text = self.search_input.text().lower()

        # Apply filters
        filtered = []
        for trans in self._transactions:
            # Type filter
            if selected_type and trans.get("type") != selected_type:
                continue

            # Search filter
            if search_text:
                searchable = (
                    trans.get("primary_text", "").lower() +
                    " ".join(trans.get("details", [])).lower() +
                    " ".join(trans.get("player_names", [])).lower()
                )
                if search_text not in searchable:
                    continue

            filtered.append(trans)

        self._filtered_transactions = filtered
        self._rebuild_feed()

    def _rebuild_feed(self):
        """Rebuild the transaction feed display."""
        # Clear existing cards
        for card in self._transaction_cards:
            self.feed_layout.removeWidget(card)
            card.deleteLater()
        self._transaction_cards.clear()

        # Remove date headers
        while self.feed_layout.count() > 2:  # Keep empty label and stretch
            item = self.feed_layout.takeAt(0)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

        # Show empty state if no transactions
        if not self._filtered_transactions:
            self.empty_label.setVisible(True)
            return

        self.empty_label.setVisible(False)

        # Group transactions by date
        grouped = {}
        for trans in self._filtered_transactions:
            date_str = trans.get("date", "Unknown Date")
            if date_str not in grouped:
                grouped[date_str] = []
            grouped[date_str].append(trans)

        # Sort dates (most recent first)
        sorted_dates = sorted(grouped.keys(), reverse=True)

        # Build feed
        for date_str in sorted_dates:
            # Date header
            date_header = DateHeaderWidget(date_str)
            self.feed_layout.insertWidget(
                self.feed_layout.count() - 1,  # Before stretch
                date_header
            )

            # Transaction cards for this date
            for trans in grouped[date_str]:
                card = TransactionCard(trans)
                card.clicked.connect(self.transaction_clicked)
                self._transaction_cards.append(card)
                self.feed_layout.insertWidget(
                    self.feed_layout.count() - 1,
                    card
                )

    def _on_filter_changed(self, _text: str):
        """Handle filter dropdown changes."""
        self._apply_filters()

    def _on_search_changed(self, _text: str):
        """Handle search input changes."""
        self._apply_filters()

    def clear(self):
        """Clear all transactions and reset to default state."""
        self._transactions = []
        self._filtered_transactions = []
        self.search_input.clear()
        self.type_filter.setCurrentIndex(0)
        self.date_range_filter.setCurrentIndex(0)
        self._rebuild_feed()
