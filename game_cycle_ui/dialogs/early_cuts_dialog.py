"""
Early Cuts Dialog - GM-proposed roster cuts for cap space (Owner approval pattern).

Part of Owner-GM Flow: GM analyzes roster and recommends cuts to create cap space
during re-signing phase. Owner can approve, reject, or manually override.

Pattern:
- GM generates cut proposals using EarlyCutsProposalGenerator
- Owner reviews proposals with GM reasoning
- Owner can approve individual cuts or batch approve all
- Owner can view all players and make manual cuts if desired
"""

from typing import Dict, List, Optional, Set
import json

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
    QGroupBox, QWidget, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from game_cycle_ui.theme import (
    apply_table_style,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    DANGER_BUTTON_STYLE,
    Colors,
    Typography,
    FontSizes
)

# Alias PRIMARY as SUCCESS (both are green)
SUCCESS_BUTTON_STYLE = PRIMARY_BUTTON_STYLE
from game_cycle_ui.utils.table_utils import NumericTableWidgetItem
from constants.position_abbreviations import get_position_abbreviation
from game_cycle.models.persistent_gm_proposal import PersistentGMProposal
from game_cycle.models.proposal_enums import ProposalStatus


class EarlyCutsDialog(QDialog):
    """
    Dialog for reviewing and approving GM-recommended roster cuts.

    Workflow:
    1. Display GM recommendations with reasoning and savings
    2. Allow owner to approve/reject individual cuts
    3. Show running total of approved savings
    4. Provide collapsible "Manual Override" section for all players
    """

    # Signal emitted when a player is cut (approved)
    player_cut = Signal(int, int, int)  # player_id, dead_money, cap_savings

    def __init__(
        self,
        team_id: int,
        excluded_player_ids: Set[int],
        db_path: str,
        dynasty_id: str,
        season: int,
        cap_shortfall: int = 0,
        parent=None
    ):
        super().__init__(parent)
        self._team_id = team_id
        self._excluded_player_ids = excluded_player_ids or set()
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._cap_shortfall = cap_shortfall

        # State tracking
        self._proposals: List[PersistentGMProposal] = []
        self._approved_savings = 0
        self._approved_count = 0
        self._all_players: List[Dict] = []

        # UI components
        self._manual_section_visible = False

        self.setWindowTitle("GM Recommended Roster Cuts")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(650)

        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header section
        self._create_header(layout)

        # GM Recommendations table
        self._create_recommendations_table(layout)

        # Summary section
        self.summary_label = QLabel("Loading GM recommendations...")
        self.summary_label.setStyleSheet(f"color: {Colors.INFO}; font-size: {FontSizes.BODY}; padding: 8px;")
        layout.addWidget(self.summary_label)

        # Manual override section (collapsible)
        self._create_manual_override_section(layout)

        # Buttons
        self._create_buttons(layout)

    def _create_header(self, parent_layout: QVBoxLayout):
        """Create the header with title and instructions."""
        header = QLabel("GM Recommended Roster Cuts")
        header.setStyleSheet(f"font-size: {FontSizes.H3}; font-weight: bold; color: {Colors.TEXT_PRIMARY};")
        parent_layout.addWidget(header)

        # Dynamic subtitle showing GM summary
        self.subtitle_label = QLabel("Analyzing roster...")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.BODY}; padding: 4px 0;")
        parent_layout.addWidget(self.subtitle_label)

        # Info/warning
        info = QLabel(
            "Your GM has analyzed the roster and recommends the following cuts to create cap space. "
            "Review each recommendation and approve or reject. You can also view all players below "
            "to make manual cuts if needed."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION}; padding: 8px; background: {Colors.BG_SECONDARY}; border-radius: 4px;")
        parent_layout.addWidget(info)

    def _create_recommendations_table(self, parent_layout: QVBoxLayout):
        """Create the GM recommendations table."""
        # Action bar with Approve All button
        action_bar = QHBoxLayout()
        action_bar.addWidget(QLabel("GM Recommendations:"))
        action_bar.addStretch()

        self.approve_all_btn = QPushButton("Approve All")
        self.approve_all_btn.setStyleSheet(SUCCESS_BUTTON_STYLE)
        self.approve_all_btn.clicked.connect(self._on_approve_all)
        action_bar.addWidget(self.approve_all_btn)

        parent_layout.addLayout(action_bar)

        # Table
        self.recommendations_table = QTableWidget()
        self.recommendations_table.setColumnCount(8)
        self.recommendations_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Net Savings", "GM Reasoning", "Status", "Action"
        ])

        apply_table_style(self.recommendations_table)
        self.recommendations_table.setSortingEnabled(False)  # Disable during population
        self.recommendations_table.verticalHeader().setDefaultSectionSize(48)

        # Column widths
        header = self.recommendations_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Player
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Net Savings
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # GM Reasoning
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Status
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)    # Action

        self.recommendations_table.setColumnWidth(0, 150)  # Player
        self.recommendations_table.setColumnWidth(1, 50)   # Pos
        self.recommendations_table.setColumnWidth(2, 50)   # Age
        self.recommendations_table.setColumnWidth(3, 50)   # OVR
        self.recommendations_table.setColumnWidth(4, 100)  # Net Savings
        self.recommendations_table.setColumnWidth(6, 90)   # Status
        self.recommendations_table.setColumnWidth(7, 150)  # Action

        parent_layout.addWidget(self.recommendations_table, stretch=2)

    def _create_manual_override_section(self, parent_layout: QVBoxLayout):
        """Create collapsible manual override section."""
        # Toggle button
        self.manual_toggle_btn = QPushButton("▼ View All Players (Manual Override)")
        self.manual_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.BG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                padding: 8px;
                text-align: left;
                font-size: {FontSizes.BODY};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background: {Colors.BG_HOVER};
            }}
        """)
        self.manual_toggle_btn.clicked.connect(self._toggle_manual_section)
        parent_layout.addWidget(self.manual_toggle_btn)

        # Collapsible content (hidden by default)
        self.manual_section = QGroupBox()
        self.manual_section.setStyleSheet(f"border: 1px solid {Colors.BORDER}; border-radius: 4px; padding: 8px;")
        self.manual_section.setVisible(False)

        manual_layout = QVBoxLayout()

        # Manual override table
        self.manual_table = QTableWidget()
        self.manual_table.setColumnCount(9)
        self.manual_table.setHorizontalHeaderLabels([
            "Player", "Pos", "Age", "OVR", "Current Salary",
            "Dead Money", "Cap Savings", "Net Impact", "Action"
        ])

        apply_table_style(self.manual_table)
        self.manual_table.setSortingEnabled(True)
        self.manual_table.verticalHeader().setDefaultSectionSize(44)

        # Column widths
        header = self.manual_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Player
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)    # Pos
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Age
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # OVR
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # Salary
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Dead
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Savings
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)    # Net
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)    # Action

        self.manual_table.setColumnWidth(1, 50)   # Pos
        self.manual_table.setColumnWidth(2, 50)   # Age
        self.manual_table.setColumnWidth(3, 50)   # OVR
        self.manual_table.setColumnWidth(4, 100)  # Salary
        self.manual_table.setColumnWidth(5, 100)  # Dead
        self.manual_table.setColumnWidth(6, 100)  # Savings
        self.manual_table.setColumnWidth(7, 100)  # Net
        self.manual_table.setColumnWidth(8, 80)   # Action

        manual_layout.addWidget(self.manual_table)
        self.manual_section.setLayout(manual_layout)
        parent_layout.addWidget(self.manual_section, stretch=1)

    def _create_buttons(self, parent_layout: QVBoxLayout):
        """Create bottom button row."""
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        parent_layout.addLayout(btn_layout)

    def _toggle_manual_section(self):
        """Toggle manual override section visibility."""
        self._manual_section_visible = not self._manual_section_visible
        self.manual_section.setVisible(self._manual_section_visible)

        # Update button text
        if self._manual_section_visible:
            self.manual_toggle_btn.setText("▲ Hide Manual Override")
        else:
            self.manual_toggle_btn.setText("▼ View All Players (Manual Override)")

    def _load_data(self):
        """Load GM proposals and all players."""
        try:
            # Load all cuttable players first
            self._load_all_players()

            # Generate GM proposals
            self._generate_gm_proposals()

            # Populate tables
            self._populate_recommendations_table()
            self._populate_manual_table()

            # Update summary
            self._update_summary()

        except Exception as e:
            self.subtitle_label.setText(f"Error loading data: {str(e)}")
            self.subtitle_label.setStyleSheet(f"color: {Colors.ERROR};")

    def _load_all_players(self):
        """Load all players eligible for early cuts."""
        from game_cycle.services.cap_helper import CapHelper
        from database.player_roster_api import PlayerRosterAPI

        # During offseason, cap calculations are for NEXT league year
        cap_helper = CapHelper(self._db_path, self._dynasty_id, self._season + 1)
        roster_api = PlayerRosterAPI(self._db_path)

        # Get all players on the team
        roster = roster_api.get_team_roster(self._dynasty_id, self._team_id)
        print(f"[DEBUG EarlyCuts] dynasty={self._dynasty_id}, team={self._team_id}, season={self._season}")
        print(f"[DEBUG EarlyCuts] Roster count: {len(roster)}, excluded: {len(self._excluded_player_ids)}")

        # Fetch season stats (snaps, games played) for all players
        player_stats = self._fetch_season_stats()

        # If no stats available (fast-forwarded season), estimate starter status from roster depth
        has_stats = any(s.get("total_snaps", 0) > 0 for s in player_stats.values())
        if not has_stats:
            print("[DEBUG EarlyCuts] No game stats found - estimating starter status from roster depth")

        self._all_players = []
        skipped_excluded = 0
        skipped_cant_release = 0

        for player in roster:
            player_id = player.get("player_id")

            # Skip players in extension recommendations
            if player_id in self._excluded_player_ids:
                skipped_excluded += 1
                continue

            # Parse JSON fields from database
            positions = player.get("positions", [])
            if isinstance(positions, str):
                try:
                    positions = json.loads(positions)
                except (json.JSONDecodeError, TypeError):
                    positions = []

            attributes = player.get("attributes", {})
            if isinstance(attributes, str):
                try:
                    attributes = json.loads(attributes)
                except (json.JSONDecodeError, TypeError):
                    attributes = {}

            # Build player name
            first_name = player.get("first_name", "")
            last_name = player.get("last_name", "")
            player_name = f"{first_name} {last_name}".strip() or "Unknown"

            # Get position
            position = positions[0] if positions else ""

            # Calculate age from birthdate
            birthdate_str = player.get("birthdate")
            if birthdate_str:
                from datetime import datetime
                try:
                    birthdate = datetime.strptime(birthdate_str, "%Y-%m-%d")
                    # Use Sept 1 of season year for age calculation (start of NFL season)
                    today = datetime(self._season, 9, 1)
                    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                except (ValueError, TypeError):
                    age = 0
            else:
                age = 0
            overall = attributes.get("overall", 0)

            # Calculate release impact
            release_impact = cap_helper.calculate_release_impact(
                player_id=player_id,
                team_id=self._team_id
            )

            if not release_impact.get("can_release", False):
                skipped_cant_release += 1
                if skipped_cant_release <= 3:  # Only log first few
                    print(f"[DEBUG EarlyCuts] Player {player_id} can't release: {release_impact}")
                continue

            cap_savings = release_impact.get("cap_savings", 0)
            dead_money = release_impact.get("dead_money", 0)
            net_change = release_impact.get("net_cap_change", cap_savings - dead_money)

            # Get current salary
            current_salary = player.get("salary", 0)
            if current_salary == 0:
                current_salary = cap_savings  # Fallback

            # Get season stats for this player
            stats = player_stats.get(str(player_id), {})

            self._all_players.append({
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "age": age,
                "overall": overall,
                "current_salary": current_salary,
                "dead_money": dead_money,
                "cap_savings": cap_savings,
                "net_change": net_change,
                # Season production stats
                "snaps": stats.get("total_snaps", 0),
                "games_played": stats.get("games_played", 0),
            })

        # Sort by net cap savings (highest first)
        self._all_players.sort(key=lambda x: x["net_change"], reverse=True)

        # If no game stats, estimate starter status from roster depth
        if not has_stats and self._all_players:
            self._estimate_starter_status()

        print(f"[DEBUG EarlyCuts] Final: {len(self._all_players)} players loaded, {skipped_excluded} excluded, {skipped_cant_release} can't release")

    def _fetch_season_stats(self) -> Dict[str, Dict]:
        """
        Fetch aggregated season stats for all players on the team.

        Returns:
            Dict mapping player_id (str) to stats dict with:
                - total_snaps: int
                - games_played: int
        """
        from game_cycle.database.connection import GameCycleDatabase

        stats_by_player = {}

        try:
            with GameCycleDatabase(self._db_path) as conn:
                conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

                # Aggregate stats from player_game_stats for the previous season
                # (We're in offseason, so look at the season that just ended)
                cursor = conn.execute('''
                    SELECT
                        player_id,
                        COUNT(DISTINCT game_id) as games_played,
                        SUM(COALESCE(snap_counts_offense, 0) +
                            COALESCE(snap_counts_defense, 0) +
                            COALESCE(snap_counts_special_teams, 0)) as total_snaps
                    FROM player_game_stats
                    WHERE dynasty_id = ?
                      AND team_id = ?
                      AND season_type = 'regular_season'
                    GROUP BY player_id
                ''', (self._dynasty_id, self._team_id))

                for row in cursor.fetchall():
                    stats_by_player[str(row["player_id"])] = {
                        "games_played": row["games_played"] or 0,
                        "total_snaps": row["total_snaps"] or 0,
                    }

                print(f"[DEBUG EarlyCuts] Fetched stats for {len(stats_by_player)} players")

        except Exception as e:
            print(f"[DEBUG EarlyCuts] Error fetching season stats: {e}")

        return stats_by_player

    def _estimate_starter_status(self):
        """
        Estimate starter vs backup status when no game stats are available.

        Groups players by position and marks the top player(s) by OVR as starters.
        Updates each player dict with 'is_likely_starter' and estimated 'snaps'.
        """
        from collections import defaultdict

        # Group by position
        by_position = defaultdict(list)
        for player in self._all_players:
            pos = player.get("position", "")
            if pos:
                by_position[pos].append(player)

        # Determine starters per position (top by OVR)
        # Most positions have 1-2 starters
        starters_per_position = {
            "CB": 2, "WR": 3, "LB": 3, "OL": 5, "DL": 3, "S": 2,
            "LT": 1, "LG": 1, "C": 1, "RG": 1, "RT": 1,
            "LE": 1, "RE": 1, "DT": 2, "NT": 1,
            "LOLB": 1, "MLB": 1, "ROLB": 1,
            "FS": 1, "SS": 1,
        }

        for pos, players in by_position.items():
            # Sort by OVR descending
            players.sort(key=lambda x: x.get("overall", 0), reverse=True)

            num_starters = starters_per_position.get(pos, 1)

            for i, player in enumerate(players):
                if i < num_starters:
                    # Starter - estimate high snaps
                    player["is_likely_starter"] = True
                    player["snaps"] = 1000  # Estimated starter snaps
                    player["games_played"] = 17
                else:
                    # Backup - estimate low snaps
                    player["is_likely_starter"] = False
                    player["snaps"] = 200  # Estimated backup snaps
                    player["games_played"] = 10

        print(f"[DEBUG EarlyCuts] Estimated starter status for {len(self._all_players)} players")

    def _generate_gm_proposals(self):
        """Generate GM cut proposals using EarlyCutsProposalGenerator."""
        from game_cycle.services.proposal_generators.early_cuts_generator import EarlyCutsProposalGenerator

        print(f"[DEBUG EarlyCuts] Generating proposals: cap_shortfall={self._cap_shortfall}, players={len(self._all_players)}")
        # Show top 3 players by net_change
        for i, p in enumerate(self._all_players[:3]):
            print(f"[DEBUG EarlyCuts] Top {i+1}: {p['player_name']} net_change={p['net_change']}, snaps={p.get('snaps', 0)}, games={p.get('games_played', 0)}")

        generator = EarlyCutsProposalGenerator(
            db_path=self._db_path,
            dynasty_id=self._dynasty_id,
            season=self._season,
            team_id=self._team_id,
            cap_shortfall=self._cap_shortfall,
        )

        self._proposals = generator.generate_proposals(
            roster_players=self._all_players,
            excluded_player_ids=self._excluded_player_ids,
        )
        print(f"[DEBUG EarlyCuts] Generated {len(self._proposals)} proposals")

    def _populate_recommendations_table(self):
        """Populate GM recommendations table."""
        if not self._proposals:
            self.recommendations_table.setRowCount(1)
            self.recommendations_table.setSpan(0, 0, 1, 8)
            msg_item = QTableWidgetItem("No GM recommendations - roster looks solid for cap space")
            msg_item.setTextAlignment(Qt.AlignCenter)
            msg_item.setForeground(QColor(Colors.MUTED))
            self.recommendations_table.setItem(0, 0, msg_item)
            self.approve_all_btn.setEnabled(False)
            return

        self.recommendations_table.setRowCount(len(self._proposals))

        for row, proposal in enumerate(self._proposals):
            self._populate_recommendation_row(row, proposal)

    def _populate_recommendation_row(self, row: int, proposal: PersistentGMProposal):
        """Populate a single recommendation row."""
        details = proposal.details

        # Player name
        name_item = QTableWidgetItem(details.get("player_name", "Unknown"))
        name_item.setData(Qt.UserRole, proposal)  # Store proposal in UserRole
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.recommendations_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(get_position_abbreviation(details.get("position", "")))
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.recommendations_table.setItem(row, 1, pos_item)

        # Age (color coded)
        age = details.get("age", 0)
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        self.recommendations_table.setItem(row, 2, age_item)

        # Overall (color coded)
        ovr = details.get("overall", 0)
        ovr_item = NumericTableWidgetItem(ovr)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        ovr_item.setFlags(ovr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if ovr >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif ovr >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.recommendations_table.setItem(row, 3, ovr_item)

        # Net Savings (green, prominent)
        net = details.get("net_change", 0)
        net_text = f"+${net / 1_000_000:.1f}M"
        net_item = QTableWidgetItem(net_text)
        net_item.setTextAlignment(Qt.AlignCenter)
        net_item.setForeground(QColor(Colors.SUCCESS))
        net_item.setFlags(net_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        font = net_item.font()
        font.setBold(True)
        net_item.setFont(font)
        self.recommendations_table.setItem(row, 4, net_item)

        # GM Reasoning
        reasoning_item = QTableWidgetItem(proposal.gm_reasoning)
        reasoning_item.setFlags(reasoning_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.recommendations_table.setItem(row, 5, reasoning_item)

        # Status
        status_item = QTableWidgetItem("Pending")
        status_item.setTextAlignment(Qt.AlignCenter)
        status_item.setForeground(QColor(Colors.WARNING))
        status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.recommendations_table.setItem(row, 6, status_item)

        # Action buttons
        self._create_action_buttons(row, proposal)

    def _create_action_buttons(self, row: int, proposal: PersistentGMProposal):
        """Create Approve/Reject buttons for a proposal."""
        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(4, 2, 4, 2)
        button_layout.setSpacing(4)

        approve_btn = QPushButton("Approve")
        approve_btn.setStyleSheet(SUCCESS_BUTTON_STYLE)
        approve_btn.clicked.connect(lambda: self._on_approve_proposal(row, proposal))

        reject_btn = QPushButton("Reject")
        reject_btn.setStyleSheet(SECONDARY_BUTTON_STYLE)
        reject_btn.clicked.connect(lambda: self._on_reject_proposal(row, proposal))

        button_layout.addWidget(approve_btn)
        button_layout.addWidget(reject_btn)

        self.recommendations_table.setCellWidget(row, 7, button_widget)

    def _populate_manual_table(self):
        """Populate manual override table with all players."""
        # Filter out players already in GM recommendations
        proposal_player_ids = {
            int(p.details.get("player_id")) for p in self._proposals
        }

        manual_players = [
            p for p in self._all_players
            if p["player_id"] not in proposal_player_ids
        ]

        if not manual_players:
            self.manual_table.setRowCount(1)
            self.manual_table.setSpan(0, 0, 1, 9)
            msg_item = QTableWidgetItem("All cuttable players are in GM recommendations")
            msg_item.setTextAlignment(Qt.AlignCenter)
            msg_item.setForeground(QColor(Colors.MUTED))
            self.manual_table.setItem(0, 0, msg_item)
            return

        self.manual_table.setRowCount(len(manual_players))

        for row, player in enumerate(manual_players):
            self._populate_manual_row(row, player)

    def _populate_manual_row(self, row: int, player: Dict):
        """Populate a single manual override row."""
        player_id = player["player_id"]

        # Player name
        name_item = QTableWidgetItem(player["player_name"])
        name_item.setData(Qt.UserRole, player_id)
        name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 0, name_item)

        # Position
        pos_item = QTableWidgetItem(get_position_abbreviation(player["position"]))
        pos_item.setTextAlignment(Qt.AlignCenter)
        pos_item.setFlags(pos_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 1, pos_item)

        # Age (color coded)
        age = player["age"]
        age_item = NumericTableWidgetItem(age)
        age_item.setTextAlignment(Qt.AlignCenter)
        age_item.setFlags(age_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if age >= 32:
            age_item.setForeground(QColor(Colors.ERROR))
        elif age >= 30:
            age_item.setForeground(QColor(Colors.WARNING))
        self.manual_table.setItem(row, 2, age_item)

        # Overall (color coded)
        ovr = player["overall"]
        ovr_item = NumericTableWidgetItem(ovr)
        ovr_item.setTextAlignment(Qt.AlignCenter)
        ovr_item.setFlags(ovr_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        if ovr >= 85:
            ovr_item.setForeground(QColor(Colors.SUCCESS))
        elif ovr >= 75:
            ovr_item.setForeground(QColor(Colors.INFO))
        self.manual_table.setItem(row, 3, ovr_item)

        # Current salary
        salary = player["current_salary"]
        salary_item = QTableWidgetItem(f"${salary / 1_000_000:.1f}M")
        salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        salary_item.setFlags(salary_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 4, salary_item)

        # Dead money (red/warning)
        dead = player["dead_money"]
        dead_item = QTableWidgetItem(f"${dead / 1_000_000:.1f}M")
        dead_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if dead > 0:
            dead_item.setForeground(QColor(Colors.ERROR))
        dead_item.setFlags(dead_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 5, dead_item)

        # Cap savings (green)
        savings = player["cap_savings"]
        savings_item = QTableWidgetItem(f"${savings / 1_000_000:.1f}M")
        savings_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        savings_item.setForeground(QColor(Colors.SUCCESS))
        savings_item.setFlags(savings_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 6, savings_item)

        # Net impact (color based on positive/negative)
        net = player["net_change"]
        net_text = f"+${net / 1_000_000:.1f}M" if net >= 0 else f"-${abs(net) / 1_000_000:.1f}M"
        net_item = QTableWidgetItem(net_text)
        net_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        if net > 0:
            net_item.setForeground(QColor(Colors.SUCCESS))
        elif net < 0:
            net_item.setForeground(QColor(Colors.ERROR))
        net_item.setFlags(net_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.manual_table.setItem(row, 7, net_item)

        # Action button
        cut_btn = QPushButton("Cut")
        cut_btn.setStyleSheet(DANGER_BUTTON_STYLE)
        cut_btn.clicked.connect(
            lambda checked, pid=player_id, d=dead, s=savings, r=row, n=player["player_name"]:
            self._on_manual_cut_player(pid, d, s, r, n)
        )
        self.manual_table.setCellWidget(row, 8, cut_btn)

    def _on_approve_proposal(self, row: int, proposal: PersistentGMProposal):
        """Handle approving a GM cut proposal."""
        details = proposal.details
        player_name = details.get("player_name", "Unknown")
        net_change = details.get("net_change", 0)
        dead_money = details.get("dead_money", 0)
        cap_savings = details.get("cap_savings", 0)
        player_id = details.get("player_id")

        # Confirm
        msg = (
            f"Approve GM recommendation to cut {player_name}?\n\n"
            f"Net Cap Savings: ${net_change / 1_000_000:.1f}M\n"
            f"GM Reasoning: {proposal.gm_reasoning}\n\n"
            "This will immediately release the player."
        )

        reply = QMessageBox.question(
            self,
            "Approve Cut",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Execute the cut
        if self._execute_cut(player_id):
            # Update proposal status
            proposal.approve()

            # Update UI
            status_item = self.recommendations_table.item(row, 6)
            status_item.setText("Approved")
            status_item.setForeground(QColor(Colors.SUCCESS))

            # Replace buttons with label
            approved_label = QLabel("Executed")
            approved_label.setAlignment(Qt.AlignCenter)
            approved_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
            self.recommendations_table.setCellWidget(row, 7, approved_label)

            # Update tracking
            self._approved_count += 1
            self._approved_savings += net_change

            # Emit signal
            self.player_cut.emit(player_id, dead_money, cap_savings)

            # Update summary
            self._update_summary()

    def _on_reject_proposal(self, row: int, proposal: PersistentGMProposal):
        """Handle rejecting a GM cut proposal."""
        details = proposal.details
        player_name = details.get("player_name", "Unknown")

        # Confirm
        msg = f"Reject GM recommendation to cut {player_name}?\n\nPlayer will remain on roster."

        reply = QMessageBox.question(
            self,
            "Reject Recommendation",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Update proposal status
        proposal.reject()

        # Update UI
        status_item = self.recommendations_table.item(row, 6)
        status_item.setText("Rejected")
        status_item.setForeground(QColor(Colors.MUTED))

        # Replace buttons with label
        rejected_label = QLabel("Kept")
        rejected_label.setAlignment(Qt.AlignCenter)
        rejected_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        self.recommendations_table.setCellWidget(row, 7, rejected_label)

        # Update summary
        self._update_summary()

    def _on_approve_all(self):
        """Approve all pending GM recommendations at once."""
        pending_proposals = [
            (row, p) for row, p in enumerate(self._proposals)
            if p.status == ProposalStatus.PENDING
        ]

        if not pending_proposals:
            QMessageBox.information(self, "No Pending", "All recommendations have been reviewed.")
            return

        total_savings = sum(p.details.get("net_change", 0) for _, p in pending_proposals)

        # Confirm batch approval
        msg = (
            f"Approve all {len(pending_proposals)} GM recommendations?\n\n"
            f"Total Net Savings: ${total_savings / 1_000_000:.1f}M\n\n"
            "This will immediately release all recommended players."
        )

        reply = QMessageBox.question(
            self,
            "Approve All",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Execute all cuts
        for row, proposal in pending_proposals:
            details = proposal.details
            player_id = details.get("player_id")
            dead_money = details.get("dead_money", 0)
            cap_savings = details.get("cap_savings", 0)
            net_change = details.get("net_change", 0)

            if self._execute_cut(player_id):
                # Update proposal
                proposal.approve()

                # Update UI
                status_item = self.recommendations_table.item(row, 6)
                status_item.setText("Approved")
                status_item.setForeground(QColor(Colors.SUCCESS))

                approved_label = QLabel("Executed")
                approved_label.setAlignment(Qt.AlignCenter)
                approved_label.setStyleSheet(f"color: {Colors.SUCCESS}; font-weight: bold;")
                self.recommendations_table.setCellWidget(row, 7, approved_label)

                # Update tracking
                self._approved_count += 1
                self._approved_savings += net_change

                # Emit signal
                self.player_cut.emit(player_id, dead_money, cap_savings)

        # Update summary
        self._update_summary()

    def _on_manual_cut_player(
        self,
        player_id: int,
        dead_money: int,
        cap_savings: int,
        row: int,
        player_name: str
    ):
        """Handle manual cut button click (owner override)."""
        net = cap_savings - dead_money
        msg = (
            f"Are you sure you want to cut {player_name}?\n\n"
            f"Cap Savings: ${cap_savings / 1_000_000:.1f}M\n"
            f"Dead Money: ${dead_money / 1_000_000:.1f}M\n"
            f"Net Cap Impact: ${net / 1_000_000:.1f}M\n\n"
            "This is a manual override (GM did not recommend). "
            "This action cannot be undone."
        )

        reply = QMessageBox.question(
            self,
            "Confirm Manual Cut",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        if self._execute_cut(player_id):
            # Update row to show completed
            done_label = QLabel("Cut")
            done_label.setAlignment(Qt.AlignCenter)
            done_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
            self.manual_table.setCellWidget(row, 8, done_label)

            # Update tracking (manual cuts count separately)
            self._approved_savings += net

            # Emit signal
            self.player_cut.emit(player_id, dead_money, cap_savings)

            # Update summary
            self._update_summary()

    def _execute_cut(self, player_id: int) -> bool:
        """
        Execute the actual player cut.

        Args:
            player_id: Player to release

        Returns:
            True if successful, False otherwise
        """
        try:
            from game_cycle.services.resigning_service import ResigningService

            resigning_svc = ResigningService(
                db_path=self._db_path,
                dynasty_id=self._dynasty_id,
                season=self._season
            )

            result = resigning_svc.release_player(player_id, self._team_id)

            if result.get("success", False):
                return True
            else:
                error = result.get("error_message", "Unknown error")
                QMessageBox.warning(self, "Cut Failed", f"Could not cut player: {error}")
                return False

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to cut player: {str(e)}")
            return False

    def _update_summary(self):
        """Update header subtitle and summary label."""
        total_recommendations = len(self._proposals)

        if total_recommendations == 0:
            self.subtitle_label.setText("Your GM has no cut recommendations - roster is healthy.")
            self.summary_label.setText("")
            return

        # Calculate potential total savings
        total_potential = sum(p.details.get("net_change", 0) for p in self._proposals)

        # Update subtitle
        self.subtitle_label.setText(
            f"Your GM recommends cutting {total_recommendations} player{'s' if total_recommendations != 1 else ''} "
            f"to save ${total_potential / 1_000_000:.1f}M in cap space."
        )

        # Update summary based on approved cuts
        pending_count = sum(1 for p in self._proposals if p.status == ProposalStatus.PENDING)
        approved_count = sum(1 for p in self._proposals if p.status == ProposalStatus.APPROVED)
        rejected_count = sum(1 for p in self._proposals if p.status == ProposalStatus.REJECTED)

        summary_parts = []

        if approved_count > 0:
            summary_parts.append(
                f"<span style='color: {Colors.SUCCESS}; font-weight: bold;'>"
                f"Approved {approved_count}: ${self._approved_savings / 1_000_000:.1f}M saved</span>"
            )

        if rejected_count > 0:
            summary_parts.append(f"Rejected: {rejected_count}")

        if pending_count > 0:
            summary_parts.append(f"Pending: {pending_count}")

        if summary_parts:
            self.summary_label.setText(" | ".join(summary_parts))
        else:
            self.summary_label.setText("All recommendations reviewed")
