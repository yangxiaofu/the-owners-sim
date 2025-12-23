"""
PlayoffPictureWidget - Two-column playoff picture display for League View.

Displays the NFL playoff picture with seeds, teams in the hunt, and eliminated teams.

Features:
- Two-column layout: AFC Seeds (1-7) and NFC Seeds (1-7)
- Each seed shows: seed number, team name, record, clinch indicator
- "In the Hunt" section showing teams still in contention
- "Eliminated" section showing mathematically eliminated teams
- Color coding: clinched (green), in hunt (yellow/warning), eliminated (red/muted)
"""

from typing import Dict, List, Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import ESPN_THEME, Colors, Typography, FontSizes, TextColors


class PlayoffPictureWidget(QWidget):
    """
    Displays the current playoff picture with AFC/NFC seeds and team status.

    Layout:
    ┌─────────────────────────────────────────────────┐
    │              PLAYOFF PICTURE                     │
    ├────────────────────┬────────────────────────────┤
    │    AFC SEEDS       │         NFC SEEDS          │
    ├────────────────────┼────────────────────────────┤
    │ 1. Chiefs (12-2)  x│ 1. Eagles (11-3)       x  │
    │ 2. Bills (10-4)   y│ 2. 49ers (10-4)        y  │
    │ 3. Bengals (9-5)  z│ 3. Cowboys (9-5)       z  │
    │ 4. Jaguars (8-6)   │ 4. Lions (8-6)            │
    │ 5. Browns (9-5)    │ 5. Seahawks (9-5)         │
    │ 6. Dolphins (8-6)  │ 6. Vikings (8-6)          │
    │ 7. Ravens (8-6)    │ 7. Packers (7-7)          │
    ├────────────────────┴────────────────────────────┤
    │              IN THE HUNT                         │
    │ AFC: Broncos (7-7), Raiders (6-8)              │
    │ NFC: Saints (7-7), Falcons (6-8)               │
    ├──────────────────────────────────────────────────┤
    │             ELIMINATED                           │
    │ AFC: Patriots, Jets, Titans...                  │
    │ NFC: Cardinals, Panthers, Giants...             │
    └──────────────────────────────────────────────────┘

    Clinch indicators:
    - x = clinched playoff berth
    - y = clinched division
    - z = clinched first-round bye
    """

    def __init__(self, parent: Optional[QWidget] = None):
        """
        Initialize the playoff picture widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._afc_seeds: List[Dict] = []
        self._nfc_seeds: List[Dict] = []
        self._in_hunt: List[Dict] = []
        self._eliminated: List[Dict] = []
        self._setup_ui()

    def _setup_ui(self):
        """Build the playoff picture UI."""
        self.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scrollable container
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background-color: {ESPN_THEME['dark_bg']};")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            background-color: {ESPN_THEME['card_bg']};
            border-bottom: 3px solid {ESPN_THEME['red']};
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 12, 16, 12)

        title = QLabel("PLAYOFF PICTURE")
        title.setFont(Typography.H5)
        title.setStyleSheet(f"""
            color: {ESPN_THEME['text_primary']};
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()

        layout.addWidget(header_frame)

        # Two-column seeds section
        seeds_container = self._create_seeds_section()
        layout.addWidget(seeds_container)

        # In the Hunt section
        self._hunt_section = self._create_hunt_section()
        layout.addWidget(self._hunt_section)

        # Eliminated section
        self._eliminated_section = self._create_eliminated_section()
        layout.addWidget(self._eliminated_section)

        # Bottom spacer
        layout.addStretch()

        scroll.setWidget(container)
        main_layout.addWidget(scroll)

    def _create_seeds_section(self) -> QWidget:
        """Create the two-column AFC/NFC seeds section."""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(1)

        # AFC Column
        afc_frame = self._create_conference_section("AFC SEEDS")
        self._afc_layout = afc_frame.layout().itemAt(1).layout()  # Get content layout
        container_layout.addWidget(afc_frame)

        # Divider
        divider = QFrame()
        divider.setFixedWidth(1)
        divider.setStyleSheet(f"background-color: {ESPN_THEME['border']};")
        container_layout.addWidget(divider)

        # NFC Column
        nfc_frame = self._create_conference_section("NFC SEEDS")
        self._nfc_layout = nfc_frame.layout().itemAt(1).layout()  # Get content layout
        container_layout.addWidget(nfc_frame)

        return container

    def _create_conference_section(self, title: str) -> QFrame:
        """
        Create a conference seeds section (AFC or NFC).

        Args:
            title: Section title ("AFC SEEDS" or "NFC SEEDS")

        Returns:
            QFrame containing the conference section
        """
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {ESPN_THEME['card_bg']};")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Section header
        header = QLabel(title)
        header.setFont(Typography.CAPTION_BOLD)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet(f"""
            background-color: {ESPN_THEME['card_bg']};
            color: {ESPN_THEME['text_secondary']};
            padding: 8px;
            border-bottom: 2px solid {ESPN_THEME['red']};
        """)
        layout.addWidget(header)

        # Content area (will be populated with seed rows)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        layout.addLayout(content)

        # Push seeds to top
        layout.addStretch()

        return frame

    def _create_seed_row(self, seed: int, team_data: Dict) -> QWidget:
        """
        Create a single seed row widget.

        Args:
            seed: Seed number (1-7)
            team_data: Dict with:
                - team_id: int
                - team_abbrev: str
                - team_name: str
                - wins: int
                - losses: int
                - ties: int (optional)
                - clinch_type: Optional[str] (None, 'division', 'playoff', 'bye')

        Returns:
            QWidget containing the seed row
        """
        row = QWidget()
        row.setFixedHeight(32)

        team_name = team_data.get("team_name", team_data.get("team_abbrev", "Team"))
        wins = team_data.get("wins", 0)
        losses = team_data.get("losses", 0)
        ties = team_data.get("ties", 0)
        clinch_type = team_data.get("clinch_type")

        # Record string
        if ties > 0:
            record = f"({wins}-{losses}-{ties})"
        else:
            record = f"({wins}-{losses})"

        # Clinch indicator
        clinch_indicator = ""
        clinch_color = ESPN_THEME['text_secondary']
        if clinch_type == "division":
            clinch_indicator = "y"
            clinch_color = Colors.SUCCESS
        elif clinch_type == "playoff":
            clinch_indicator = "x"
            clinch_color = Colors.SUCCESS
        elif clinch_type == "bye":
            clinch_indicator = "z"
            clinch_color = Colors.SUCCESS

        # Background color (alternate for readability)
        if seed % 2 == 1:
            bg_color = ESPN_THEME['card_bg']
        else:
            bg_color = "#1e1e1e"

        row.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-bottom: 1px solid {ESPN_THEME['border']};
            }}
        """)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(8)

        # Seed number
        seed_label = QLabel(f"{seed}.")
        seed_label.setFont(Typography.CAPTION_BOLD)
        seed_label.setFixedWidth(24)
        seed_label.setStyleSheet(f"color: {ESPN_THEME['text_primary']}; background: transparent; border: none;")
        layout.addWidget(seed_label)

        # Team name
        name_label = QLabel(team_name)
        name_label.setFont(Typography.CAPTION)
        name_label.setStyleSheet(f"color: {ESPN_THEME['text_primary']}; background: transparent; border: none;")
        layout.addWidget(name_label, 1)

        # Record
        record_label = QLabel(record)
        record_label.setFont(Typography.SMALL)
        record_label.setStyleSheet(f"color: {ESPN_THEME['text_secondary']}; background: transparent; border: none;")
        layout.addWidget(record_label)

        # Clinch indicator
        if clinch_indicator:
            clinch_label = QLabel(clinch_indicator)
            clinch_label.setFont(Typography.CAPTION_BOLD)
            clinch_label.setFixedWidth(16)
            clinch_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            clinch_label.setStyleSheet(f"color: {clinch_color}; background: transparent; border: none;")
            layout.addWidget(clinch_label)

        return row

    def _create_hunt_section(self) -> QFrame:
        """Create the 'In the Hunt' section."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {ESPN_THEME['card_bg']};
            border-top: 1px solid {ESPN_THEME['border']};
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Section header
        header = QLabel("IN THE HUNT")
        header.setFont(Typography.CAPTION_BOLD)
        header.setStyleSheet(f"color: {ESPN_THEME['text_secondary']}; letter-spacing: 1px;")
        layout.addWidget(header)

        # AFC teams
        self._afc_hunt_label = QLabel("AFC: --")
        self._afc_hunt_label.setFont(Typography.SMALL)
        self._afc_hunt_label.setStyleSheet(f"color: {Colors.WARNING};")
        self._afc_hunt_label.setWordWrap(True)
        layout.addWidget(self._afc_hunt_label)

        # NFC teams
        self._nfc_hunt_label = QLabel("NFC: --")
        self._nfc_hunt_label.setFont(Typography.SMALL)
        self._nfc_hunt_label.setStyleSheet(f"color: {Colors.WARNING};")
        self._nfc_hunt_label.setWordWrap(True)
        layout.addWidget(self._nfc_hunt_label)

        return frame

    def _create_eliminated_section(self) -> QFrame:
        """Create the 'Eliminated' section."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {ESPN_THEME['card_bg']};
            border-top: 1px solid {ESPN_THEME['border']};
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Section header
        header = QLabel("ELIMINATED")
        header.setFont(Typography.CAPTION_BOLD)
        header.setStyleSheet(f"color: {ESPN_THEME['text_secondary']}; letter-spacing: 1px;")
        layout.addWidget(header)

        # AFC teams
        self._afc_elim_label = QLabel("AFC: --")
        self._afc_elim_label.setFont(Typography.SMALL)
        self._afc_elim_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self._afc_elim_label.setWordWrap(True)
        layout.addWidget(self._afc_elim_label)

        # NFC teams
        self._nfc_elim_label = QLabel("NFC: --")
        self._nfc_elim_label.setFont(Typography.SMALL)
        self._nfc_elim_label.setStyleSheet(f"color: {ESPN_THEME['text_muted']};")
        self._nfc_elim_label.setWordWrap(True)
        layout.addWidget(self._nfc_elim_label)

        return frame

    def set_playoff_data(
        self,
        afc_seeds: List[Dict],
        nfc_seeds: List[Dict],
        in_hunt: List[Dict],
        eliminated: List[Dict]
    ):
        """
        Populate the playoff picture with data.

        Args:
            afc_seeds: List of AFC seed dicts (seeds 1-7)
            nfc_seeds: List of NFC seed dicts (seeds 1-7)
            in_hunt: List of teams still in playoff hunt with:
                - team_name: str
                - team_abbrev: str
                - conference: str ("AFC" or "NFC")
                - wins: int
                - losses: int
                - ties: int (optional)
            eliminated: List of eliminated teams with:
                - team_name: str
                - team_abbrev: str
                - conference: str ("AFC" or "NFC")
        """
        self._afc_seeds = afc_seeds
        self._nfc_seeds = nfc_seeds
        self._in_hunt = in_hunt
        self._eliminated = eliminated

        # Clear existing seed rows
        self._clear_layout(self._afc_layout)
        self._clear_layout(self._nfc_layout)

        # Populate AFC seeds (1-7)
        for i, seed_data in enumerate(afc_seeds[:7], start=1):
            row = self._create_seed_row(i, seed_data)
            self._afc_layout.addWidget(row)

        # Populate NFC seeds (1-7)
        for i, seed_data in enumerate(nfc_seeds[:7], start=1):
            row = self._create_seed_row(i, seed_data)
            self._nfc_layout.addWidget(row)

        # Populate "In the Hunt"
        afc_hunt = [t for t in in_hunt if t.get("conference") == "AFC"]
        nfc_hunt = [t for t in in_hunt if t.get("conference") == "NFC"]

        if afc_hunt:
            afc_names = []
            for team in afc_hunt:
                name = team.get("team_abbrev", team.get("team_name", "Team"))
                wins = team.get("wins", 0)
                losses = team.get("losses", 0)
                ties = team.get("ties", 0)
                if ties > 0:
                    record = f"({wins}-{losses}-{ties})"
                else:
                    record = f"({wins}-{losses})"
                afc_names.append(f"{name} {record}")
            self._afc_hunt_label.setText(f"AFC: {', '.join(afc_names)}")
        else:
            self._afc_hunt_label.setText("AFC: None")

        if nfc_hunt:
            nfc_names = []
            for team in nfc_hunt:
                name = team.get("team_abbrev", team.get("team_name", "Team"))
                wins = team.get("wins", 0)
                losses = team.get("losses", 0)
                ties = team.get("ties", 0)
                if ties > 0:
                    record = f"({wins}-{losses}-{ties})"
                else:
                    record = f"({wins}-{losses})"
                nfc_names.append(f"{name} {record}")
            self._nfc_hunt_label.setText(f"NFC: {', '.join(nfc_names)}")
        else:
            self._nfc_hunt_label.setText("NFC: None")

        # Populate "Eliminated"
        afc_elim = [t for t in eliminated if t.get("conference") == "AFC"]
        nfc_elim = [t for t in eliminated if t.get("conference") == "NFC"]

        if afc_elim:
            afc_names = [t.get("team_abbrev", t.get("team_name", "Team")) for t in afc_elim]
            self._afc_elim_label.setText(f"AFC: {', '.join(afc_names)}")
        else:
            self._afc_elim_label.setText("AFC: None")

        if nfc_elim:
            nfc_names = [t.get("team_abbrev", t.get("team_name", "Team")) for t in nfc_elim]
            self._nfc_elim_label.setText(f"NFC: {', '.join(nfc_names)}")
        else:
            self._nfc_elim_label.setText("NFC: None")

    def clear(self):
        """Clear all playoff picture data."""
        self._afc_seeds = []
        self._nfc_seeds = []
        self._in_hunt = []
        self._eliminated = []

        self._clear_layout(self._afc_layout)
        self._clear_layout(self._nfc_layout)

        self._afc_hunt_label.setText("AFC: --")
        self._nfc_hunt_label.setText("NFC: --")
        self._afc_elim_label.setText("AFC: --")
        self._nfc_elim_label.setText("NFC: --")

    def _clear_layout(self, layout):
        """Clear all items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())


# =============================================================================
# USAGE EXAMPLE
# =============================================================================
"""
Example usage in a League View:

    from game_cycle_ui.widgets import PlayoffPictureWidget

    # Create widget
    playoff_widget = PlayoffPictureWidget()

    # Prepare data
    afc_seeds = [
        {
            "team_id": 12,
            "team_abbrev": "KC",
            "team_name": "Kansas City Chiefs",
            "wins": 12,
            "losses": 2,
            "ties": 0,
            "clinch_type": "division",  # or 'playoff', 'bye', None
        },
        # ... seeds 2-7
    ]

    nfc_seeds = [
        # ... seeds 1-7 for NFC
    ]

    in_hunt = [
        {
            "team_name": "Denver Broncos",
            "team_abbrev": "DEN",
            "conference": "AFC",
            "wins": 7,
            "losses": 7,
            "ties": 0,
        },
        # ... other teams in hunt
    ]

    eliminated = [
        {
            "team_name": "New England Patriots",
            "team_abbrev": "NE",
            "conference": "AFC",
        },
        # ... other eliminated teams
    ]

    # Populate widget
    playoff_widget.set_playoff_data(afc_seeds, nfc_seeds, in_hunt, eliminated)

    # Clear data
    playoff_widget.clear()
"""
