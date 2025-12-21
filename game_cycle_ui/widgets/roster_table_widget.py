"""
Roster Table Widget - Displays team roster with attributes and stats.

Shows player roster with core attributes (OVR, SPD, STR, AWR),
position-specific attributes, and condensed season stats.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont

from game_cycle_ui.theme import (
    ESPN_THEME, TABLE_HEADER_STYLE, Colors,
    PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, DANGER_BUTTON_STYLE,
    WARNING_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors, apply_table_style
)
from utils.player_field_extractors import extract_overall_rating


# Position groups for filtering
OFFENSE_POSITIONS = {
    'quarterback', 'qb', 'running_back', 'halfback', 'rb', 'hb', 'fullback', 'fb',
    'wide_receiver', 'wr', 'tight_end', 'te',
    'left_tackle', 'lt', 'left_guard', 'lg', 'center', 'c',
    'right_guard', 'rg', 'right_tackle', 'rt'
}

DEFENSE_POSITIONS = {
    'left_end', 'le', 'defensive_tackle', 'dt', 'nose_tackle', 'nt', 'right_end', 're',
    'defensive_end', 'de', 'edge',
    'left_outside_linebacker', 'lolb', 'middle_linebacker', 'mlb', 'mike', 'linebacker', 'lb',
    'right_outside_linebacker', 'rolb', 'inside_linebacker', 'ilb',
    'cornerback', 'cb', 'free_safety', 'fs', 'strong_safety', 'ss', 'safety', 's'
}

SPECIAL_TEAMS_POSITIONS = {
    'kicker', 'k', 'punter', 'p', 'long_snapper', 'ls',
    'kick_returner', 'kr', 'punt_returner', 'pr'
}

# Position abbreviation mapping
POSITION_ABBREV = {
    'quarterback': 'QB', 'qb': 'QB',
    'running_back': 'RB', 'halfback': 'RB', 'rb': 'RB', 'hb': 'RB',
    'fullback': 'FB', 'fb': 'FB',
    'wide_receiver': 'WR', 'wr': 'WR',
    'tight_end': 'TE', 'te': 'TE',
    'left_tackle': 'LT', 'lt': 'LT',
    'left_guard': 'LG', 'lg': 'LG',
    'center': 'C', 'c': 'C',
    'right_guard': 'RG', 'rg': 'RG',
    'right_tackle': 'RT', 'rt': 'RT',
    'guard': 'G', 'g': 'G',
    'tackle': 'T', 't': 'T',
    'offensive_line': 'OL', 'ol': 'OL',
    'offensive_guard': 'OG', 'og': 'OG',
    'offensive_tackle': 'OT', 'ot': 'OT',
    'left_end': 'LE', 'le': 'LE',
    'defensive_tackle': 'DT', 'dt': 'DT',
    'nose_tackle': 'NT', 'nt': 'NT',
    'right_end': 'RE', 're': 'RE',
    'defensive_end': 'DE', 'de': 'DE',
    'edge': 'EDGE',
    'left_outside_linebacker': 'LOLB', 'lolb': 'LOLB',
    'middle_linebacker': 'MLB', 'mlb': 'MLB', 'mike': 'MLB',
    'linebacker': 'LB', 'lb': 'LB',
    'right_outside_linebacker': 'ROLB', 'rolb': 'ROLB',
    'inside_linebacker': 'ILB', 'ilb': 'ILB',
    'cornerback': 'CB', 'cb': 'CB',
    'free_safety': 'FS', 'fs': 'FS',
    'strong_safety': 'SS', 'ss': 'SS',
    'safety': 'S', 's': 'S',
    'kicker': 'K', 'k': 'K',
    'punter': 'P', 'p': 'P',
    'long_snapper': 'LS', 'ls': 'LS',
    'kick_returner': 'KR', 'kr': 'KR',
    'punt_returner': 'PR', 'pr': 'PR',
}

# Position-specific attributes to display (attr_key, display_abbrev)
POSITION_ATTRIBUTES = {
    'QB': [('accuracy', 'ACC'), ('arm_strength', 'ARM')],
    'RB': [('vision', 'VIS'), ('elusiveness', 'ELU')],
    'FB': [('run_blocking', 'RBK'), ('power', 'PWR')],
    'WR': [('catching', 'CTH'), ('route_running', 'RTE')],
    'TE': [('catching', 'CTH'), ('run_blocking', 'BLK')],
    'LT': [('pass_blocking', 'PBK'), ('run_blocking', 'RBK')],
    'LG': [('pass_blocking', 'PBK'), ('run_blocking', 'RBK')],
    'C': [('pass_blocking', 'PBK'), ('run_blocking', 'RBK')],
    'RG': [('pass_blocking', 'PBK'), ('run_blocking', 'RBK')],
    'RT': [('pass_blocking', 'PBK'), ('run_blocking', 'RBK')],
    'LE': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'DT': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'NT': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'RE': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'DE': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'EDGE': [('pass_rush', 'PRU'), ('run_defense', 'RDF')],
    'LOLB': [('coverage', 'COV'), ('tackling', 'TAC')],
    'MLB': [('coverage', 'COV'), ('tackling', 'TAC')],
    'LB': [('coverage', 'COV'), ('tackling', 'TAC')],
    'ROLB': [('coverage', 'COV'), ('tackling', 'TAC')],
    'ILB': [('coverage', 'COV'), ('tackling', 'TAC')],
    'CB': [('man_coverage', 'COV'), ('ball_skills', 'BLS')],
    'FS': [('zone_coverage', 'COV'), ('ball_skills', 'BLS')],
    'SS': [('zone_coverage', 'COV'), ('tackling', 'TAC')],
    'S': [('zone_coverage', 'COV'), ('tackling', 'TAC')],
    'K': [('kick_power', 'PWR'), ('kick_accuracy', 'ACC')],
    'P': [('punt_power', 'PWR'), ('hang_time', 'HNG')],
    'LS': [('snap_accuracy', 'ACC'), ('awareness', 'AWR')],
    'KR': [('speed', 'SPD'), ('elusiveness', 'ELU')],
    'PR': [('speed', 'SPD'), ('elusiveness', 'ELU')],
}

# Color thresholds for ratings
COLOR_ELITE = Colors.SUCCESS      # Green - 85+
COLOR_SOLID = Colors.INFO          # Blue - 75-84
COLOR_AVERAGE = "#FFFFFF"          # White - 65-74
COLOR_BELOW = Colors.ERROR         # Red - <65


class RosterTableWidget(QWidget):
    """
    Widget displaying team roster in a table format.

    Shows player name, position, age, core attributes (OVR, SPD, STR, AWR),
    position-specific attributes, and condensed season stats.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._players: List[Dict[str, Any]] = []
        self._season_stats: Dict[int, Dict[str, Any]] = {}  # player_id -> stats
        self._current_filter: str = "all"
        self._season: int = 2025  # Game season for age calculation

        self._setup_ui()

    def set_season(self, season: int):
        """Set the game season for age calculations."""
        self._season = season

    def _setup_ui(self):
        """Build the widget layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Filter buttons row
        filter_row = QHBoxLayout()
        filter_row.setSpacing(4)

        self.filter_buttons: Dict[str, QPushButton] = {}
        for filter_name, label in [
            ("all", "All"),
            ("offense", "Offense"),
            ("defense", "Defense"),
            ("special_teams", "Special Teams")
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(filter_name == "all")
            btn.clicked.connect(lambda checked, f=filter_name: self._on_filter_clicked(f))
            btn.setStyleSheet(self._get_filter_button_style(filter_name == "all"))
            self.filter_buttons[filter_name] = btn
            filter_row.addWidget(btn)

        filter_row.addStretch()

        # Player count label
        self.count_label = QLabel("0 players")
        self.count_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']}; font-size: {FontSizes.BODY};")
        filter_row.addWidget(self.count_label)

        layout.addLayout(filter_row)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "SPD", "STR", "AWR", "Position Attrs", "Key Stats"
        ])

        # Configure header
        header = self.table.horizontalHeader()
        header.setStyleSheet(TABLE_HEADER_STYLE)

        # Column sizing
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Player name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        header.resizeSection(7, 120)  # Position attrs
        header.setSectionResizeMode(8, QHeaderView.Fixed)
        header.resizeSection(8, 150)  # Key stats

        # Table appearance
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)

        # Apply standard table styling
        apply_table_style(self.table)

        layout.addWidget(self.table)

    def _get_filter_button_style(self, is_selected: bool) -> str:
        """Get style for filter button based on selection state."""
        if is_selected:
            # Blue button for selected filter
            return SECONDARY_BUTTON_STYLE.replace("padding: 8px 16px;", "padding: 6px 12px;")
        # Gray button for unselected filters
        return """
            QPushButton {
                background-color: #333;
                color: #666666;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover { background-color: #3a3a3a; color: white; }
            QPushButton:pressed { background-color: #444444; }
        """

    def set_roster(self, players: List[Dict[str, Any]], season_stats: Optional[Dict[int, Dict[str, Any]]] = None):
        """
        Set the roster data to display.

        Args:
            players: List of player dicts with attributes
            season_stats: Optional dict of player_id -> season stats
        """
        self._players = players or []
        self._season_stats = season_stats or {}
        self._populate_table()

    def set_filter(self, unit: str):
        """
        Set position filter.

        Args:
            unit: "all", "offense", "defense", or "special_teams"
        """
        self._current_filter = unit

        # Update button states
        for filter_name, btn in self.filter_buttons.items():
            is_selected = filter_name == unit
            btn.setChecked(is_selected)
            btn.setStyleSheet(self._get_filter_button_style(is_selected))

        self._populate_table()

    def _on_filter_clicked(self, filter_name: str):
        """Handle filter button click."""
        self.set_filter(filter_name)

    def _populate_table(self):
        """Populate the table with filtered player data."""
        # Filter players
        filtered_players = self._filter_players(self._players)

        # Sort by overall rating descending
        filtered_players.sort(key=lambda p: extract_overall_rating(p, default=0), reverse=True)

        self.table.setRowCount(len(filtered_players))
        self.count_label.setText(f"{len(filtered_players)} players")

        for row, player in enumerate(filtered_players):
            self._populate_row(row, player)

    def _filter_players(self, players: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter players by current filter setting."""
        if self._current_filter == "all":
            return players

        filtered = []
        for player in players:
            positions = player.get('positions', [])
            if not positions:
                continue

            pos = positions[0].lower() if positions else ''

            if self._current_filter == "offense" and pos in OFFENSE_POSITIONS:
                filtered.append(player)
            elif self._current_filter == "defense" and pos in DEFENSE_POSITIONS:
                filtered.append(player)
            elif self._current_filter == "special_teams" and pos in SPECIAL_TEAMS_POSITIONS:
                filtered.append(player)

        return filtered

    def _populate_row(self, row: int, player: Dict[str, Any]):
        """Populate a single table row."""
        attrs = player.get('attributes', {})
        positions = player.get('positions', [])
        pos_raw = positions[0].lower() if positions else 'unknown'
        pos_abbrev = POSITION_ABBREV.get(pos_raw, pos_raw.upper()[:3])

        # Player name (store player_id in UserRole for retrieval on click)
        name = f"{player.get('first_name', '')} {player.get('last_name', '')}".strip()
        name_item = QTableWidgetItem(name)
        name_item.setForeground(QColor("white"))
        name_item.setData(Qt.UserRole, player.get('player_id'))
        # Store full player dict for easy access
        name_item.setData(Qt.UserRole + 1, player)
        self.table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(pos_abbrev)
        pos_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 1, pos_item)

        # Age
        age = self._calculate_age(player.get('birthdate'))
        age_item = QTableWidgetItem(str(age) if age else "--")
        age_item.setTextAlignment(Qt.AlignCenter)
        self.table.setItem(row, 2, age_item)

        # Core attributes with color coding
        for col, attr_key in enumerate(['overall', 'speed', 'strength', 'awareness'], start=3):
            value = attrs.get(attr_key, 0)
            item = QTableWidgetItem(str(value) if value else "--")
            item.setTextAlignment(Qt.AlignCenter)
            item.setForeground(QColor(self._get_rating_color(value)))
            self.table.setItem(row, col, item)

        # Position-specific attributes
        pos_attrs_str = self._format_position_attributes(pos_abbrev, attrs)
        pos_attrs_item = QTableWidgetItem(pos_attrs_str)
        pos_attrs_item.setTextAlignment(Qt.AlignCenter)
        pos_attrs_item.setForeground(QColor("#AAAAAA"))
        self.table.setItem(row, 7, pos_attrs_item)

        # Key stats
        player_id = player.get('player_id')
        stats = self._season_stats.get(player_id, {})
        stats_str = self._format_key_stats(pos_abbrev, stats)
        stats_item = QTableWidgetItem(stats_str)
        stats_item.setTextAlignment(Qt.AlignCenter)
        stats_item.setForeground(QColor("#AAAAAA"))
        self.table.setItem(row, 8, stats_item)

    def _calculate_age(self, birthdate_str: Optional[str]) -> Optional[int]:
        """Calculate age from birthdate using game season (not real-world date)."""
        if not birthdate_str:
            return None
        try:
            birth_year = int(birthdate_str.split("-")[0])
            return self._season - birth_year
        except (ValueError, TypeError, IndexError):
            return None

    def _get_rating_color(self, rating: int) -> str:
        """Get color for rating value."""
        if rating >= 85:
            return COLOR_ELITE
        elif rating >= 75:
            return COLOR_SOLID
        elif rating >= 65:
            return COLOR_AVERAGE
        else:
            return COLOR_BELOW

    def _format_position_attributes(self, pos_abbrev: str, attrs: Dict[str, Any]) -> str:
        """Format position-specific attributes as 'ABR:XX ABR:XX'."""
        pos_attrs = POSITION_ATTRIBUTES.get(pos_abbrev, [])
        if not pos_attrs:
            return "--"

        parts = []
        for attr_key, display_abbrev in pos_attrs:
            value = attrs.get(attr_key, 0)
            if value:
                parts.append(f"{display_abbrev}:{value}")

        return " ".join(parts) if parts else "--"

    def _format_key_stats(self, pos_abbrev: str, stats: Dict[str, Any]) -> str:
        """Format position-specific key stats."""
        if not stats:
            return "--"

        # QB stats
        if pos_abbrev == 'QB':
            yds = stats.get('passing_yards', 0)
            tds = stats.get('passing_tds', 0)
            if yds or tds:
                return f"{yds:,} YDS {tds} TD"

        # RB stats
        elif pos_abbrev in ('RB', 'HB', 'FB'):
            yds = stats.get('rushing_yards', 0)
            tds = stats.get('rushing_tds', 0)
            if yds or tds:
                return f"{yds:,} YDS {tds} TD"

        # WR/TE stats
        elif pos_abbrev in ('WR', 'TE'):
            rec = stats.get('receptions', 0)
            yds = stats.get('receiving_yards', 0)
            if rec or yds:
                return f"{rec} REC {yds:,} YDS"

        # OL stats
        elif pos_abbrev in ('LT', 'LG', 'C', 'RG', 'RT'):
            games = stats.get('games_played', 0)
            if games:
                return f"{games} GP"

        # DL/LB stats
        elif pos_abbrev in ('LE', 'DT', 'NT', 'RE', 'DE', 'EDGE', 'LOLB', 'MLB', 'LB', 'ROLB', 'ILB'):
            tkl = stats.get('tackles_total', 0) or stats.get('tackles', 0)
            sacks = stats.get('sacks', 0)
            if tkl or sacks:
                return f"{tkl} TKL {sacks:.1f} SK" if isinstance(sacks, float) else f"{tkl} TKL {sacks} SK"

        # CB/S stats
        elif pos_abbrev in ('CB', 'FS', 'SS', 'S'):
            tkl = stats.get('tackles_total', 0) or stats.get('tackles', 0)
            ints = stats.get('interceptions', 0)
            if tkl or ints:
                return f"{tkl} TKL {ints} INT"

        # K stats
        elif pos_abbrev == 'K':
            fgm = stats.get('field_goals_made', 0)
            fga = stats.get('field_goals_attempted', 0)
            if fga:
                return f"{fgm}/{fga} FG"

        # P stats
        elif pos_abbrev == 'P':
            punts = stats.get('punts', 0)
            avg = stats.get('punt_avg', 0) or stats.get('punt_yards', 0) / punts if punts else 0
            if punts:
                return f"{punts} P {avg:.1f} AVG"

        return "--"

    def clear(self):
        """Clear all data."""
        self._players = []
        self._season_stats = {}
        self.table.setRowCount(0)
        self.count_label.setText("0 players")
