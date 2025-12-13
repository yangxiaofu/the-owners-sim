"""
ArticleDetailDialog - ESPN-style modal dialog for displaying full article content.

Part of Milestone 12: Media Coverage, Tollgate 7.

Displays full headline content including:
- Headline and subheadline
- Full body text
- Sentiment indicator
- Related teams/players
"""

from typing import Any, Dict, Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QWidget,
    QFrame,
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import (
    UITheme,
    SENTIMENT_COLORS,
    SENTIMENT_BADGES,
    ESPN_RED,
    ESPN_DARK_BG,
    ESPN_CARD_BG,
    ESPN_TEXT_PRIMARY,
    ESPN_TEXT_SECONDARY,
    ESPN_BORDER,
    get_headline_category_display,
)


class ArticleDetailDialog(QDialog):
    """
    ESPN-style modal dialog for displaying full article/headline content.

    Shows:
    - Headline with sentiment badge
    - Subheadline
    - Full body text (scrollable)
    - Headline type and metadata
    """

    def __init__(
        self,
        headline_data: Dict[str, Any],
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the article detail dialog.

        Args:
            headline_data: Dictionary containing headline info:
                - headline: str
                - subheadline: Optional[str]
                - body_text: Optional[str]
                - sentiment: str
                - headline_type: str
                - team_ids: List[int]
                - player_ids: List[int]
            parent: Parent widget
        """
        super().__init__(parent)
        self._data = headline_data
        self._setup_ui()

    def _setup_ui(self):
        """Build the ESPN-style dialog UI."""
        self.setWindowTitle("Article")
        self.setMinimumSize(650, 550)
        self.setModal(True)

        # ESPN dark theme styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {ESPN_DARK_BG};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header image placeholder with red accent bar
        header_bg = QFrame()
        header_bg.setFixedHeight(80)
        header_bg.setStyleSheet(f"""
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a1a1a, stop:0.5 #252525, stop:1 #1a1a1a
            );
            border-bottom: 4px solid {ESPN_RED};
        """)

        header_layout = QVBoxLayout(header_bg)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel("NFL COVERAGE")
        icon_label.setStyleSheet(f"""
            color: {ESPN_RED};
            font-size: 14px;
            font-weight: bold;
            letter-spacing: 3px;
            background: transparent;
        """)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(icon_label)

        layout.addWidget(header_bg)

        # Content area
        content_container = QWidget()
        content_container.setStyleSheet(f"background-color: {ESPN_DARK_BG};")
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(24, 20, 24, 16)
        content_layout.setSpacing(12)

        # Category badge row
        self._create_category_row(content_layout)

        # Headline
        self._create_headline(content_layout)

        # Divider
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background-color: {ESPN_BORDER};")
        content_layout.addWidget(divider)

        # Body content (scrollable)
        self._create_body(content_layout)

        layout.addWidget(content_container, 1)

        # Footer with close button
        self._create_footer(layout)

    def _create_category_row(self, parent_layout: QVBoxLayout):
        """Create the category badge row."""
        row = QHBoxLayout()
        row.setSpacing(12)

        headline_type = self._data.get("headline_type", "NEWS")
        category = get_headline_category_display(headline_type)

        category_badge = QLabel(category.upper())
        category_badge.setStyleSheet(f"""
            background-color: {ESPN_RED};
            color: {ESPN_TEXT_PRIMARY};
            font-size: 10px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 2px;
            letter-spacing: 1px;
        """)
        row.addWidget(category_badge)

        row.addStretch()

        parent_layout.addLayout(row)

    def _create_headline(self, parent_layout: QVBoxLayout):
        """Create the headline section."""
        # Main headline
        headline_text = self._data.get("headline", "Untitled")
        headline_label = QLabel(headline_text)
        headline_label.setWordWrap(True)
        headline_label.setStyleSheet(f"""
            font-size: 22px;
            font-weight: bold;
            color: {ESPN_TEXT_PRIMARY};
            line-height: 1.3;
            background: transparent;
        """)
        parent_layout.addWidget(headline_label)

        # Subheadline
        subheadline = self._data.get("subheadline", "")
        if subheadline:
            sub_label = QLabel(subheadline)
            sub_label.setWordWrap(True)
            sub_label.setStyleSheet(f"""
                font-size: 14px;
                color: {ESPN_TEXT_SECONDARY};
                font-style: italic;
                margin-top: 4px;
                background: transparent;
            """)
            parent_layout.addWidget(sub_label)

    def _create_body(self, parent_layout: QVBoxLayout):
        """Create the scrollable body section."""
        # Scroll area for body text
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {ESPN_CARD_BG};
                width: 10px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #444444;
                border-radius: 5px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {ESPN_RED};
            }}
        """)

        # Body container
        body_container = QWidget()
        body_container.setStyleSheet("background-color: transparent;")
        body_layout = QVBoxLayout(body_container)
        body_layout.setContentsMargins(0, 12, 0, 0)
        body_layout.setSpacing(16)

        body_text = self._data.get("body_text", "")
        if body_text:
            # Split body text into paragraphs
            paragraphs = body_text.split("\n\n")
            for i, para in enumerate(paragraphs):
                if para.strip():
                    para_label = QLabel(para.strip())
                    para_label.setWordWrap(True)
                    para_label.setTextFormat(Qt.TextFormat.PlainText)

                    # First paragraph slightly larger
                    if i == 0:
                        para_label.setStyleSheet(f"""
                            font-size: 15px;
                            color: {ESPN_TEXT_PRIMARY};
                            line-height: 1.7;
                            background-color: transparent;
                        """)
                    else:
                        para_label.setStyleSheet(f"""
                            font-size: 14px;
                            color: #CCCCCC;
                            line-height: 1.6;
                            background-color: transparent;
                        """)
                    body_layout.addWidget(para_label)
        else:
            # No body text
            no_content = QLabel("Full article content not available.")
            no_content.setStyleSheet(f"""
                color: {ESPN_TEXT_SECONDARY};
                font-style: italic;
                padding: 30px;
            """)
            no_content.setAlignment(Qt.AlignmentFlag.AlignCenter)
            body_layout.addWidget(no_content)

        body_layout.addStretch()
        scroll.setWidget(body_container)
        parent_layout.addWidget(scroll, stretch=1)

    def _create_footer(self, parent_layout: QVBoxLayout):
        """Create the ESPN-styled footer with close button."""
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(f"""
            background-color: {ESPN_CARD_BG};
            border-top: 1px solid {ESPN_BORDER};
        """)

        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 0, 24, 0)
        footer_layout.addStretch()

        close_btn = QPushButton("CLOSE")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_RED};
                color: {ESPN_TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 10px 30px;
                font-weight: bold;
                font-size: 12px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: #990000;
            }}
            QPushButton:pressed {{
                background-color: #660000;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        footer_layout.addWidget(close_btn)

        parent_layout.addWidget(footer)
