"""
Social Widgets Demo - Visual test of T6 widgets.

Tests rendering of:
- PersonalityBadge
- ReactionBar
- SocialPostCard
- SocialFilterBar

Run this to verify all widgets display correctly with ESPN theme.
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'game_cycle_ui'))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QLabel,
)
from PySide6.QtCore import Qt

from game_cycle_ui.widgets.personality_badge import PersonalityBadge
from game_cycle_ui.widgets.reaction_bar import ReactionBar
from game_cycle_ui.widgets.social_post_card import SocialPostCard
from game_cycle_ui.widgets.social_filter_bar import SocialFilterBar


class SocialWidgetsDemo(QMainWindow):
    """Demo window showing all social widgets."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Social Widgets Demo - T6")
        self.setGeometry(100, 100, 600, 800)
        self._setup_ui()

    def _setup_ui(self):
        """Build the demo UI."""
        # Central widget with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(24)
        layout.setContentsMargins(20, 20, 20, 20)

        # ===== SECTION 1: Personality Badges =====
        layout.addWidget(self._create_section_header("1. Personality Badges"))

        badge_layout = QVBoxLayout()
        badge_layout.setSpacing(8)

        for personality_type in ["FAN", "MEDIA", "BEAT_REPORTER", "HOT_TAKE", "STATS_ANALYST"]:
            badge = PersonalityBadge(personality_type)
            badge_layout.addWidget(badge)

        layout.addLayout(badge_layout)

        # ===== SECTION 2: Reaction Bar =====
        layout.addWidget(self._create_section_header("2. Reaction Bar"))

        reaction_bar_1 = ReactionBar(likes=234, retweets=67)
        layout.addWidget(reaction_bar_1)

        reaction_bar_2 = ReactionBar(likes=1250, retweets=340)
        layout.addWidget(reaction_bar_2)

        reaction_bar_3 = ReactionBar(likes=45600, retweets=12300)
        layout.addWidget(reaction_bar_3)

        # ===== SECTION 3: Social Post Cards =====
        layout.addWidget(self._create_section_header("3. Social Post Cards"))

        # Positive sentiment post
        positive_post = {
            'id': 1,
            'handle': '@AlwaysBelievinBill',
            'display_name': "Always Believin' Bills",
            'personality_type': 'FAN',
            'post_text': "LET'S GOOOOO! Bills win 28-17! Josh Allen is HIM! 🔥🔥🔥",
            'sentiment': 0.8,
            'likes': 1234,
            'retweets': 456,
        }
        card1 = SocialPostCard(positive_post)
        layout.addWidget(card1)

        # Negative sentiment post
        negative_post = {
            'id': 2,
            'handle': '@SameOldJets',
            'display_name': 'Same Old Jets',
            'personality_type': 'FAN',
            'post_text': "Pathetic. This team will never learn. Fire everyone.",
            'sentiment': -0.7,
            'likes': 234,
            'retweets': 89,
        }
        card2 = SocialPostCard(negative_post)
        layout.addWidget(card2)

        # Neutral/analytical post
        neutral_post = {
            'id': 3,
            'handle': '@PFFAnalyst',
            'display_name': 'PFF Analyst',
            'personality_type': 'STATS_ANALYST',
            'post_text': "QB posted a 72.4 PFF grade with 280 yards. Above average but not elite. Pressured on 32% of dropbacks.",
            'sentiment': 0.1,
            'likes': 567,
            'retweets': 123,
        }
        card3 = SocialPostCard(neutral_post)
        layout.addWidget(card3)

        # Media post
        media_post = {
            'id': 4,
            'handle': '@NYGBeatReporter',
            'display_name': 'NYG Beat Reporter',
            'personality_type': 'BEAT_REPORTER',
            'post_text': "Breaking: Giants trade WR to Cowboys for 2nd round pick. GM says \"We're building for the future.\"",
            'sentiment': 0.0,
            'likes': 3456,
            'retweets': 1234,
        }
        card4 = SocialPostCard(media_post)
        layout.addWidget(card4)

        # ===== SECTION 4: Social Filter Bar =====
        layout.addWidget(self._create_section_header("4. Social Filter Bar"))

        # Mock teams data
        teams_data = [
            {'id': 1, 'abbreviation': 'BUF'},
            {'id': 2, 'abbreviation': 'MIA'},
            {'id': 3, 'abbreviation': 'NE'},
            {'id': 4, 'abbreviation': 'NYJ'},
            {'id': 5, 'abbreviation': 'BAL'},
        ]

        filter_bar = SocialFilterBar(teams_data)
        filter_bar.filter_changed.connect(self._on_filter_changed)
        layout.addWidget(filter_bar)

        # Add stretch at the end
        layout.addStretch()

        # Set content widget to scroll area
        scroll.setWidget(content)
        self.setCentralWidget(scroll)

    def _create_section_header(self, text: str) -> QLabel:
        """Create a section header label."""
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #1a1a1a;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 0;
                border-bottom: 2px solid #E0E0E0;
            }
        """)
        return label

    def _on_filter_changed(self, team_id: int, event_type: str, sentiment: str):
        """Handle filter change signal."""
        print(f"Filter changed: team_id={team_id}, event_type={event_type}, sentiment={sentiment}")


def main():
    """Run the demo application."""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    # Create and show demo window
    demo = SocialWidgetsDemo()
    demo.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
