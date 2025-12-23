"""
SocialFeedWidget - Main social media feed container.

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 7.

Main container widget for the social feed that:
- Displays chronological feed of social posts
- Provides filtering (team, event type, sentiment)
- Supports pagination (20 posts per load)
- Collapsible sidebar with toggle button
- Always visible in right sidebar (300px width)

Layout:
    [Collapse/Expand Button]
    [Social Filter Bar]
    [Scrollable Feed]
        - SocialPostCard 1
        - SocialPostCard 2
        - ...
    [Load More Button]
"""

from typing import Optional, List, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QPushButton,
    QLabel,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QCursor

from game_cycle.database.connection import GameCycleDatabase
from game_cycle_ui.widgets.social_filter_bar import SocialFilterBar
from game_cycle_ui.widgets.social_post_card import SocialPostCard


# ESPN Dark Theme colors (matches game_cycle_ui/theme.py)
ESPN_PRIMARY = "#2E7D32"        # Green button (keep)
ESPN_DARK_BG = "#0d0d0d"        # Main background
ESPN_CARD_BG = "#1a1a1a"        # Card/container background
ESPN_CARD_HOVER = "#252525"     # Hover state
ESPN_BORDER = "#333333"         # Borders
ESPN_TEXT_PRIMARY = "#FFFFFF"   # Primary text
ESPN_TEXT_SECONDARY = "#888888" # Secondary text
ESPN_TEXT_MUTED = "#666666"     # Muted text


class SocialFeedWidget(QWidget):
    """
    Main social feed container widget.

    Displays a chronological feed of social media posts with filtering
    and pagination. Designed as a 300px right sidebar.

    Signals:
        post_clicked: Emitted when a post is clicked (post_id)
        filter_changed: Emitted when filters change
    """

    post_clicked = Signal(int)  # post_id
    filter_changed = Signal(int, str, str)  # team_id, event_type, sentiment

    def __init__(
        self,
        db: GameCycleDatabase,
        dynasty_id: str,
        teams_data: List[Dict[str, Any]],
        parent: Optional[QWidget] = None
    ):
        """
        Initialize the social feed widget.

        Args:
            db: GameCycleDatabase instance (injected from controller)
            dynasty_id: Dynasty identifier
            teams_data: List of team dicts for filter dropdown
            parent: Parent widget
        """
        super().__init__(parent)
        self._db = db
        self._dynasty_id = dynasty_id
        self._teams_data = teams_data

        # Feed state
        self._current_season = 2025  # TODO: Get from context
        self._current_week = 1
        self._posts_per_page = 20
        self._current_offset = 0
        self._all_posts_loaded = False
        self._is_collapsed = False

        # Current filters
        self._filter_team_id = 0  # 0 = all teams
        self._filter_event_type = "ALL"
        self._filter_sentiment = "ALL"

        # UI elements
        self._feed_container: Optional[QWidget] = None
        self._load_more_btn: Optional[QPushButton] = None
        self._collapse_btn: Optional[QPushButton] = None
        self._content_widget: Optional[QWidget] = None

        self._setup_ui()
        self._load_initial_posts()

    def _setup_ui(self):
        """Build the social feed UI."""
        # Fixed width for right sidebar
        self.setFixedWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # Main vertical layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Container frame
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {ESPN_CARD_BG};
                border-left: 1px solid {ESPN_BORDER};
            }}
        """)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Header with title and collapse button
        header = self._create_header()
        container_layout.addWidget(header)

        # Content widget (can be hidden when collapsed)
        self._content_widget = QWidget()
        content_layout = QVBoxLayout(self._content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Filter bar
        filter_bar = SocialFilterBar(self._teams_data)
        filter_bar.filter_changed.connect(self._on_filter_changed)
        content_layout.addWidget(filter_bar)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(f"background-color: {ESPN_BORDER};")
        separator.setFixedHeight(1)
        content_layout.addWidget(separator)

        # Scrollable feed area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Feed container (holds all post cards)
        self._feed_container = QWidget()
        self._feed_layout = QVBoxLayout(self._feed_container)
        self._feed_layout.setContentsMargins(8, 8, 8, 8)
        self._feed_layout.setSpacing(8)
        self._feed_layout.addStretch()

        scroll_area.setWidget(self._feed_container)
        content_layout.addWidget(scroll_area)

        # Load More button
        self._load_more_btn = QPushButton("Load More Posts")
        self._load_more_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ESPN_PRIMARY};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px;
                font-size: 12px;
                font-weight: bold;
                margin: 8px;
            }}
            QPushButton:hover {{
                background-color: #1B5E20;
            }}
            QPushButton:disabled {{
                background-color: #CCCCCC;
                color: #666666;
            }}
        """)
        self._load_more_btn.clicked.connect(self._load_more_posts)
        content_layout.addWidget(self._load_more_btn)

        container_layout.addWidget(self._content_widget)

        main_layout.addWidget(container)

    def _create_header(self) -> QWidget:
        """
        Create header with title and collapse button.

        Returns:
            Header widget
        """
        header = QWidget()
        header.setFixedHeight(50)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {ESPN_CARD_BG};
                border-bottom: 1px solid {ESPN_BORDER};
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        # Title
        title = QLabel("Social Feed")
        title.setStyleSheet(f"""
            QLabel {{
                color: {ESPN_TEXT_PRIMARY};
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title)

        # Spacer
        layout.addStretch()

        # Collapse/Expand button
        self._collapse_btn = QPushButton("◀")
        self._collapse_btn.setFixedSize(30, 30)
        self._collapse_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 14px;
                color: #666666;
            }
            QPushButton:hover {
                background-color: #F5F5F5;
                border-color: #999999;
            }
        """)
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        layout.addWidget(self._collapse_btn)

        return header

    def _toggle_collapse(self):
        """Toggle collapsed/expanded state."""
        self._is_collapsed = not self._is_collapsed

        if self._is_collapsed:
            # Collapse: Hide content, change button
            self._content_widget.hide()
            self._collapse_btn.setText("▶")
            self.setFixedWidth(50)  # Narrow collapsed width
        else:
            # Expand: Show content, change button
            self._content_widget.show()
            self._collapse_btn.setText("◀")
            self.setFixedWidth(300)  # Full width

    def _load_initial_posts(self):
        """Load initial set of posts."""
        self._current_offset = 0
        self._all_posts_loaded = False
        self._clear_feed()
        self._load_posts()

    def _load_posts(self):
        """Load posts from database with current filters and pagination."""
        try:
            from game_cycle.database.social_posts_api import SocialPostsAPI

            # Use injected database connection
            posts_api = SocialPostsAPI(self._db)

            # Build query filters
            posts = self._fetch_filtered_posts(posts_api)

            # Add posts to feed
            if posts:
                for post in posts:
                    self._add_post_card(post)
                self._current_offset += len(posts)

                # Check if all posts loaded
                if len(posts) < self._posts_per_page:
                    self._all_posts_loaded = True
                    self._load_more_btn.setEnabled(False)
                    self._load_more_btn.setText("All Posts Loaded")
            else:
                # No posts found
                if self._current_offset == 0:
                    self._show_empty_state()
                self._all_posts_loaded = True
                self._load_more_btn.setEnabled(False)

        except Exception as e:
            print(f"Error loading posts: {e}")
            import traceback
            traceback.print_exc()

    def _fetch_filtered_posts(self, posts_api) -> List[Any]:
        """
        Fetch posts with current filters applied at database level.

        Uses SocialPostsAPI.get_rolling_feed() for efficient filtering.

        Args:
            posts_api: SocialPostsAPI instance

        Returns:
            List of SocialPost objects
        """
        # Convert filter values for API (0/"ALL" → None)
        team_filter = self._filter_team_id if self._filter_team_id != 0 else None
        event_type_filter = self._filter_event_type if self._filter_event_type != "ALL" else None
        sentiment_filter = self._filter_sentiment if self._filter_sentiment != "ALL" else None

        # DEBUG: Print query parameters
        week_display = self._current_week if self._current_week is not None else "ALL"
        print(f"[SOCIAL_FEED] Querying posts: dynasty={self._dynasty_id}, season={self._current_season}, week={week_display}")

        # Use API method for database-level filtering
        posts = posts_api.get_rolling_feed(
            dynasty_id=self._dynasty_id,
            season=self._current_season,
            week=self._current_week,
            limit=self._posts_per_page,
            offset=self._current_offset,
            team_filter=team_filter,
            event_type_filter=event_type_filter,
            sentiment_filter=sentiment_filter
        )

        # DEBUG: Print results
        print(f"[SOCIAL_FEED] Found {len(posts)} posts (week={week_display})")

        return posts

    def _add_post_card(self, post):
        """
        Add a post card to the feed.

        Args:
            post: SocialPost object
        """
        # Convert SocialPost to dict for SocialPostCard
        post_data = {
            'id': post.id,
            'handle': post.handle,
            'display_name': post.display_name,
            'personality_type': post.personality_type,
            'post_text': post.post_text,
            'sentiment': post.sentiment,
            'likes': post.likes,
            'retweets': post.retweets,
        }

        # Create card
        card = SocialPostCard(post_data)
        card.clicked.connect(self.post_clicked.emit)

        # Add to feed layout (before the stretch)
        self._feed_layout.insertWidget(self._feed_layout.count() - 1, card)

    def _clear_feed(self):
        """Clear all post cards from feed."""
        # Remove all widgets except the stretch
        while self._feed_layout.count() > 1:
            item = self._feed_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _show_empty_state(self):
        """Show empty state message."""
        empty_label = QLabel("No posts found.\nTry adjusting your filters.")
        empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_label.setStyleSheet(f"""
            QLabel {{
                color: {ESPN_TEXT_SECONDARY};
                font-size: 13px;
                padding: 40px 20px;
            }}
        """)
        self._feed_layout.insertWidget(0, empty_label)

    def _load_more_posts(self):
        """Load next page of posts."""
        if not self._all_posts_loaded:
            self._load_posts()

    def _on_filter_changed(self, team_id: int, event_type: str, sentiment: str):
        """
        Handle filter change from filter bar.

        Args:
            team_id: Filtered team ID (0 = all)
            event_type: Filtered event type ("ALL" = all)
            sentiment: Filtered sentiment ("ALL" = all)
        """
        self._filter_team_id = team_id
        self._filter_event_type = event_type
        self._filter_sentiment = sentiment

        # Reload feed with new filters
        self._load_initial_posts()

        # Emit signal
        self.filter_changed.emit(team_id, event_type, sentiment)

    def refresh_feed(self):
        """Refresh the feed (reload from beginning)."""
        self._load_initial_posts()

    def set_context(self, season: int, week):
        """
        Update season/week context for feed.

        Args:
            season: Current season
            week: Current week (None = show all weeks for season)
        """
        print(f"[SOCIAL_FEED] set_context called: season={season}, week={week}")

        # Defensive fallback: If week is None, try to get current week from dynasty_state
        if week is None:
            print("[SOCIAL_FEED] WARNING: week is None, attempting fallback to dynasty_state")
            try:
                # Query dynasty_state for current_week
                row = self._db.query_one(
                    "SELECT current_week FROM dynasty_state WHERE dynasty_id = ? AND season = ?",
                    (self._dynasty_id, season)
                )
                if row and row['current_week'] is not None:
                    week = row['current_week']
                    print(f"[SOCIAL_FEED] Fallback successful: using week={week} from dynasty_state")
                else:
                    print(f"[SOCIAL_FEED] Fallback failed: no current_week in dynasty_state, showing all weeks")
                    # week remains None - will show all weeks for season
            except Exception as e:
                print(f"[SOCIAL_FEED] Fallback exception: {e}, showing all weeks")
                # week remains None - will show all weeks for season

        self._current_season = season
        self._current_week = week
        self.refresh_feed()
