"""
Team Needs Widget

Displays team positional needs analysis with urgency indicators and player lists.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QFrame, QScrollArea, QPushButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

from offseason.team_needs_analyzer import TeamNeedsAnalyzer, NeedUrgency
from depth_chart.depth_chart_api import DepthChartAPI


class TeamNeedsWidget(QWidget):
    """
    Widget displaying team positional needs analysis.

    Shows:
    - Overall needs summary with urgency breakdown
    - Position groups (OFFENSE, DEFENSE, SPECIAL TEAMS)
    - Individual position cards with:
        - Urgency indicator emoji
        - Starter and depth info
        - Color-coded player ratings
        - Expiring contract warnings
    """

    # Overall rating colors (matching roster_table_model.py)
    RATING_COLORS = {
        'elite': '#1976D2',      # Blue - 90+
        'starter': '#388E3C',    # Green - 80-89
        'backup': '#FBC02D',     # Yellow - 70-79
        'depth': '#F57C00',      # Orange - 60-69
        'practice': '#757575',   # Gray - <60 (changed from red to neutral gray)
    }

    # Urgency emojis
    URGENCY_EMOJIS = {
        NeedUrgency.CRITICAL: "🔴",
        NeedUrgency.HIGH: "🟠",
        NeedUrgency.MEDIUM: "🟡",
        NeedUrgency.LOW: "🟢",
        NeedUrgency.NONE: "✅",
    }

    # Position groups
    OFFENSE_POSITIONS = [
        'quarterback', 'running_back', 'wide_receiver', 'tight_end',
        'left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle'
    ]

    DEFENSE_POSITIONS = [
        'defensive_end', 'defensive_tackle', 'linebacker',
        'cornerback', 'safety'
    ]

    SPECIAL_TEAMS_POSITIONS = [
        'kicker', 'punter'
    ]

    def __init__(self, db_path: str, dynasty_id: str, season: int, parent=None):
        """
        Initialize Team Needs widget.

        Args:
            db_path: Path to database
            dynasty_id: Dynasty identifier
            season: Current season year
            parent: Parent widget
        """
        super().__init__(parent)

        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        # Initialize backend components
        self.needs_analyzer = TeamNeedsAnalyzer(db_path, dynasty_id)
        self.depth_chart_api = DepthChartAPI(db_path)

        # Current team and data
        self.current_team_id = None
        self.needs_data = []
        self.depth_chart_data = {}

        # Current view (OFFENSE or DEFENSE)
        self.current_view = "OFFENSE"

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        # Container widget for scrollable content
        container = QWidget()
        self.container_layout = QVBoxLayout(container)
        self.container_layout.setContentsMargins(12, 12, 12, 12)  # Reduced from 16
        self.container_layout.setSpacing(10)  # Reduced from 16

        # Summary section (at top)
        self.summary_widget = self._create_summary_section()
        self.container_layout.addWidget(self.summary_widget)

        # Toggle widget for Offense/Defense
        self.toggle_widget = self._create_toggle_widget()
        self.container_layout.addWidget(self.toggle_widget)

        # Position groups sections (only show active view)
        self.offense_group = self._create_position_group_section("OFFENSE", self.OFFENSE_POSITIONS)
        self.container_layout.addWidget(self.offense_group)

        self.defense_group = self._create_position_group_section("DEFENSE", self.DEFENSE_POSITIONS)
        self.container_layout.addWidget(self.defense_group)

        self.special_teams_group = self._create_position_group_section("SPECIAL TEAMS", self.SPECIAL_TEAMS_POSITIONS)
        self.container_layout.addWidget(self.special_teams_group)

        # Initially hide defense and special teams
        self.defense_group.setVisible(False)
        self.special_teams_group.setVisible(False)

        # Stretch at bottom
        self.container_layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_summary_section(self) -> QGroupBox:
        """
        Create summary section with overall needs overview.

        Returns:
            QGroupBox with summary information
        """
        group = QGroupBox("NEEDS SUMMARY")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #0066cc;
                border-radius: 6px;
                margin-top: 0ex;
                padding: 20px 12px 12px 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: content;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 8px;
                top: 6px;
                color: #0066cc;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Dynasty and season info
        self.dynasty_info_label = QLabel("Dynasty: - | Season: -")
        info_font = QFont()
        info_font.setPointSize(10)
        info_font.setItalic(True)
        self.dynasty_info_label.setFont(info_font)
        self.dynasty_info_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.dynasty_info_label)

        # Urgency breakdown (horizontal layout)
        urgency_container = QWidget()
        urgency_layout = QHBoxLayout(urgency_container)
        urgency_layout.setContentsMargins(0, 0, 0, 0)
        urgency_layout.setSpacing(20)

        self.critical_count_label = QLabel("🔴 Critical: 0")
        self.high_count_label = QLabel("🟠 High: 0")
        self.medium_count_label = QLabel("🟡 Medium: 0")
        self.low_count_label = QLabel("🟢 Low: 0")
        self.strong_count_label = QLabel("✅ Strong: 0")

        count_font = QFont()
        count_font.setPointSize(11)
        count_font.setBold(True)

        for label in [self.critical_count_label, self.high_count_label,
                     self.medium_count_label, self.low_count_label, self.strong_count_label]:
            label.setFont(count_font)
            urgency_layout.addWidget(label)

        urgency_layout.addStretch()
        layout.addWidget(urgency_container)

        # Total positions analyzed
        self.total_positions_label = QLabel("Positions analyzed: 0")
        total_font = QFont()
        total_font.setPointSize(10)
        self.total_positions_label.setFont(total_font)
        self.total_positions_label.setStyleSheet("color: #666666;")
        layout.addWidget(self.total_positions_label)

        return group

    def _create_toggle_widget(self) -> QWidget:
        """
        Create toggle buttons for switching between Offense and Defense views.

        Returns:
            QWidget with toggle buttons
        """
        toggle_container = QWidget()
        toggle_layout = QHBoxLayout(toggle_container)
        toggle_layout.setContentsMargins(0, 8, 0, 8)
        toggle_layout.setSpacing(8)

        # Button group for exclusive selection
        self.view_button_group = QButtonGroup(self)

        # Offense button
        self.offense_btn = QPushButton("OFFENSE")
        self.offense_btn.setCheckable(True)
        self.offense_btn.setChecked(True)  # Default to offense
        self.offense_btn.setMinimumHeight(36)
        self.offense_btn.clicked.connect(lambda: self._switch_view("OFFENSE"))
        self.view_button_group.addButton(self.offense_btn)

        # Defense button
        self.defense_btn = QPushButton("DEFENSE")
        self.defense_btn.setCheckable(True)
        self.defense_btn.setMinimumHeight(36)
        self.defense_btn.clicked.connect(lambda: self._switch_view("DEFENSE"))
        self.view_button_group.addButton(self.defense_btn)

        # Style buttons
        button_style = """
            QPushButton {
                background-color: #f5f5f5;
                border: 2px solid #cccccc;
                border-radius: 4px;
                padding: 8px 24px;
                font-size: 12px;
                font-weight: bold;
                color: #666666;
            }
            QPushButton:checked {
                background-color: #0066cc;
                border-color: #0066cc;
                color: white;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #0066cc;
            }
            QPushButton:checked:hover {
                background-color: #0052a3;
            }
        """
        self.offense_btn.setStyleSheet(button_style)
        self.defense_btn.setStyleSheet(button_style)

        toggle_layout.addWidget(self.offense_btn)
        toggle_layout.addWidget(self.defense_btn)
        toggle_layout.addStretch()

        return toggle_container

    def _switch_view(self, view: str):
        """
        Switch between OFFENSE and DEFENSE views.

        Args:
            view: "OFFENSE" or "DEFENSE"
        """
        self.current_view = view

        if view == "OFFENSE":
            self.offense_group.setVisible(True)
            self.defense_group.setVisible(False)
            self.special_teams_group.setVisible(False)
        else:  # DEFENSE
            self.offense_group.setVisible(False)
            self.defense_group.setVisible(True)
            self.special_teams_group.setVisible(True)  # Show special teams with defense

    def _create_position_group_section(self, title: str, positions: list) -> QGroupBox:
        """
        Create collapsible position group section (OFFENSE/DEFENSE/SPECIAL TEAMS).

        Args:
            title: Section title (e.g., "OFFENSE")
            positions: List of position keys (e.g., ['quarterback', 'running_back'])

        Returns:
            QGroupBox containing position cards
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 4px;
                margin-top: 0ex;
                padding: 18px 12px 12px 12px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: content;
                subcontrol-position: top left;
                padding: 0 8px;
                left: 8px;
                top: 4px;
                color: #0066cc;
            }
        """)

        layout = QVBoxLayout(group)
        layout.setSpacing(4)  # Reduced from 8 for tighter spacing

        # Create placeholder - will be populated in update_team()
        placeholder = QLabel(f"Select a team to view {title.lower()} needs")
        placeholder.setStyleSheet("color: #999999; padding: 16px;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)

        return group

    def update_team(self, team_id: int):
        """
        Update display for selected team.

        Args:
            team_id: NFL team ID (1-32)
        """
        self.current_team_id = team_id

        # Fetch needs data
        self.needs_data = self.needs_analyzer.analyze_team_needs(
            team_id,
            self.season,
            include_future_contracts=True
        )

        # Fetch depth chart data
        self.depth_chart_data = self.depth_chart_api.get_full_depth_chart(
            self.dynasty_id,
            team_id
        )

        # Update summary
        self._update_summary()

        # Update position groups
        self._update_position_group(self.offense_group, "OFFENSE", self.OFFENSE_POSITIONS)
        self._update_position_group(self.defense_group, "DEFENSE", self.DEFENSE_POSITIONS)
        self._update_position_group(self.special_teams_group, "SPECIAL TEAMS", self.SPECIAL_TEAMS_POSITIONS)

    def _update_summary(self):
        """Update summary section with current needs data."""
        # Update dynasty/season info
        self.dynasty_info_label.setText(f"Dynasty: {self.dynasty_id} | Season: {self.season}")

        # Count needs by urgency
        critical_count = sum(1 for n in self.needs_data if n['urgency'] == NeedUrgency.CRITICAL)
        high_count = sum(1 for n in self.needs_data if n['urgency'] == NeedUrgency.HIGH)
        medium_count = sum(1 for n in self.needs_data if n['urgency'] == NeedUrgency.MEDIUM)
        low_count = sum(1 for n in self.needs_data if n['urgency'] == NeedUrgency.LOW)

        # Count strong positions (positions NOT in needs_data)
        all_positions = set(self.OFFENSE_POSITIONS + self.DEFENSE_POSITIONS + self.SPECIAL_TEAMS_POSITIONS)
        needs_positions = set(n['position'] for n in self.needs_data)
        strong_count = len(all_positions - needs_positions)

        # Update labels
        self.critical_count_label.setText(f"🔴 Critical: {critical_count}")
        self.high_count_label.setText(f"🟠 High: {high_count}")
        self.medium_count_label.setText(f"🟡 Medium: {medium_count}")
        self.low_count_label.setText(f"🟢 Low: {low_count}")
        self.strong_count_label.setText(f"✅ Strong: {strong_count}")

        # Total positions
        self.total_positions_label.setText(f"Positions analyzed: {len(all_positions)}")

    def _update_position_group(self, group: QGroupBox, title: str, positions: list):
        """
        Update position group section with current needs data.

        Args:
            group: QGroupBox to update
            title: Section title
            positions: List of positions in this group
        """
        # Clear existing layout
        layout = group.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create position cards
        has_positions = False
        for position in positions:
            # Find need for this position
            need = next((n for n in self.needs_data if n['position'] == position), None)

            # Get depth chart for this position
            depth_players = self.depth_chart_data.get(position, [])

            if need or depth_players:
                has_positions = True
                position_card = self._create_position_card(position, need, depth_players)
                layout.addWidget(position_card)

        # Show placeholder if no positions
        if not has_positions:
            placeholder = QLabel(f"No {title.lower()} data available")
            placeholder.setStyleSheet("color: #999999; padding: 16px;")
            placeholder.setAlignment(Qt.AlignCenter)
            layout.addWidget(placeholder)

    def _create_position_card(self, position: str, need: dict, depth_players: list) -> QFrame:
        """
        Create individual position need card.

        Args:
            position: Position key (e.g., 'quarterback')
            need: Need dict from TeamNeedsAnalyzer (or None if no need)
            depth_players: List of players at this position from depth chart

        Returns:
            QFrame containing position information
        """
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)  # Reduced from 12
        layout.setSpacing(6)  # Reduced from 8

        # Header row: Position name + urgency indicator
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)  # Reduced from 8

        # Urgency emoji
        if need:
            urgency_emoji = self.URGENCY_EMOJIS.get(need['urgency'], "⚪")
            urgency_label = QLabel(urgency_emoji)
            urgency_font = QFont()
            urgency_font.setPointSize(14)  # Reduced from 16
            urgency_label.setFont(urgency_font)
            header_layout.addWidget(urgency_label)

        # Position name
        position_display = position.replace('_', ' ').title()
        position_label = QLabel(position_display)
        position_font = QFont()
        position_font.setPointSize(11)  # Reduced from 12
        position_font.setBold(True)
        position_label.setFont(position_font)
        header_layout.addWidget(position_label, stretch=1)

        # Expiring contract warning
        if need and need.get('starter_leaving', False):
            warning_label = QLabel("⚠️ Contract Expiring")
            warning_font = QFont()
            warning_font.setPointSize(9)
            warning_font.setBold(True)
            warning_label.setFont(warning_font)
            warning_label.setStyleSheet("color: #FF6F00; background-color: #FFF3E0; padding: 2px 6px; border-radius: 3px;")
            header_layout.addWidget(warning_label)

        layout.addLayout(header_layout)

        # Need info (if exists)
        if need:
            # Reason
            reason_label = QLabel(f"• {need['reason']}")
            reason_font = QFont()
            reason_font.setPointSize(9)  # Reduced from 10
            reason_font.setItalic(True)
            reason_label.setFont(reason_font)
            reason_label.setStyleSheet("color: #666666;")
            layout.addWidget(reason_label)

            # Starter info
            starter_overall = need['starter_overall']
            starter_color = self._get_rating_color(starter_overall)
            starter_info = QLabel(f"Starter: <span style='color: {starter_color}; font-weight: bold;'>{starter_overall} OVR</span>")
            starter_font = QFont()
            starter_font.setPointSize(9)  # Reduced from 10
            starter_info.setFont(starter_font)
            layout.addWidget(starter_info)

            # Depth info
            depth_count = need['depth_count']
            avg_depth = need['avg_depth_overall']
            depth_color = self._get_rating_color(avg_depth) if avg_depth > 0 else "#999999"
            depth_info = QLabel(f"Depth: {depth_count} backups (avg <span style='color: {depth_color}; font-weight: bold;'>{avg_depth:.0f} OVR</span>)")
            depth_font = QFont()
            depth_font.setPointSize(9)  # Reduced from 10
            depth_info.setFont(depth_font)
            layout.addWidget(depth_info)

        # Player list
        if depth_players:
            # Sort by depth order
            sorted_players = sorted(depth_players, key=lambda p: p.get('depth_order', 99))

            # Create player list
            players_container = QWidget()
            players_layout = QVBoxLayout(players_container)
            players_layout.setContentsMargins(0, 4, 0, 0)
            players_layout.setSpacing(4)

            for player in sorted_players[:1]:  # Show only starter
                player_row = self._create_player_row(player)
                players_layout.addWidget(player_row)

            layout.addWidget(players_container)

        return card

    def _create_player_row(self, player: dict) -> QLabel:
        """
        Create player row with color-coded rating.

        Args:
            player: Player dict with keys: player_name, overall, depth_order

        Returns:
            QLabel with formatted player info
        """
        depth_order = player.get('depth_order', 0)
        player_name = player.get('player_name', 'Unknown')
        overall = player.get('overall', 0)

        # Get rating color
        rating_color = self._get_rating_color(overall)

        # Depth indicator
        depth_text = f"{depth_order}." if depth_order > 0 else "•"

        # Create label
        label = QLabel(f"   {depth_text} {player_name} - <span style='color: {rating_color}; font-weight: bold;'>{overall} OVR</span>")

        font = QFont()
        font.setPointSize(9)  # Reduced from 10
        label.setFont(font)

        # Highlight starter
        if depth_order == 1:
            label.setStyleSheet("background-color: #E3F2FD; padding: 2px 4px; border-radius: 2px;")

        return label

    def _get_rating_color(self, overall: int) -> str:
        """
        Get color for overall rating.

        Args:
            overall: Overall rating (0-99)

        Returns:
            Hex color string
        """
        if overall >= 90:
            return self.RATING_COLORS['elite']
        elif overall >= 80:
            return self.RATING_COLORS['starter']
        elif overall >= 70:
            return self.RATING_COLORS['backup']
        elif overall >= 60:
            return self.RATING_COLORS['depth']
        else:
            return self.RATING_COLORS['practice']
