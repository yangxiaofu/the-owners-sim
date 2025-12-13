"""
Offseason Directive Dialog - Owner's strategic direction at start of offseason.

Part of Milestone 13: Owner Review - Tollgate 1.
Allows owners to set team philosophy, budget stance, position priorities,
protected/expendable players, notes, and trust GM settings.
"""

from typing import List, Dict, Optional, Tuple

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QRadioButton, QButtonGroup, QComboBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QTextEdit, QGroupBox,
    QHeaderView, QAbstractItemView, QFrame, QMessageBox, QWidget
)
from PySide6.QtCore import Signal, Qt

from game_cycle_ui.theme import Colors, FontSizes
from src.game_cycle.models.owner_directives import OwnerDirectives


class OffseasonDirectiveDialog(QDialog):
    """
    Modal dialog for setting offseason strategic direction.

    Allows owner to set:
    - Team Philosophy (Win-Now / Maintain / Rebuild)
    - Budget Stance (Aggressive / Moderate / Conservative)
    - Position Priorities (1-5 positions to focus on)
    - Protected Players (max 5, will not be traded/cut)
    - Expendable Players (max 10, available for trade)
    - Notes (free-form text to GM)
    - Trust GM (skip approval gates)

    Emits:
        directive_saved: OwnerDirectives object when saved
    """

    directive_saved = Signal(object)  # OwnerDirectives

    def __init__(
        self,
        dynasty_id: str,
        team_id: int,
        season: int,
        roster: List[Dict],
        existing_directives: Optional[OwnerDirectives] = None,
        parent=None
    ):
        """
        Initialize dialog.

        Args:
            dynasty_id: Dynasty identifier for isolation
            team_id: Team ID (1-32)
            season: Season year
            roster: List of player dicts with player_id, name, position, overall
            existing_directives: Existing directives to load (None = defaults)
            parent: Parent widget
        """
        super().__init__(parent)
        self.dynasty_id = dynasty_id
        self.team_id = team_id
        self.season = season
        self.roster = roster
        self.existing = existing_directives

        self.setWindowTitle(f"Offseason Direction - {season}")
        self.setMinimumSize(750, 850)

        # Available positions for priority selection
        self._available_positions = [
            "",  # Empty option
            "QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT",
            "LE", "DT", "RE", "LOLB", "MLB", "ROLB", "CB", "FS", "SS",
            "K", "P", "EDGE"
        ]

        self._setup_ui()
        self._connect_signals()
        self._load_existing()
        self._update_preview()

    def _setup_ui(self):
        """Build dialog layout with all sections."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Info header
        info_label = QLabel(
            "Set your strategic direction for this offseason. Your GM will use this "
            "guidance when making decisions about draft picks, free agent signings, and roster moves."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; padding: 10px; font-size: {FontSizes.CAPTION};"
        )
        layout.addWidget(info_label)

        # Team Philosophy section
        layout.addWidget(self._create_philosophy_section())

        # Budget Stance section
        layout.addWidget(self._create_budget_section())

        # Position Priorities section
        layout.addWidget(self._create_priorities_section())

        # Player tables row (side by side)
        tables_layout = QHBoxLayout()
        tables_layout.addWidget(self._create_protected_section())
        tables_layout.addWidget(self._create_expendable_section())
        layout.addLayout(tables_layout)

        # Notes section
        layout.addWidget(self._create_notes_section())

        # Trust GM checkbox
        layout.addWidget(self._create_trust_gm_section())

        # Preview section
        layout.addWidget(self._create_preview_section())

        # Spacer
        layout.addStretch()

        # Action buttons
        layout.addLayout(self._create_buttons())

    def _create_philosophy_section(self) -> QGroupBox:
        """Radio group: Win-Now / Maintain / Rebuild."""
        group = QGroupBox("Team Philosophy")
        layout = QVBoxLayout(group)

        self.philosophy_group = QButtonGroup(self)

        options = [
            ("win_now", "Win-Now", "Maximize this season's championship chances"),
            ("maintain", "Maintain (Recommended)", "Sustain competitiveness while building"),
            ("rebuild", "Rebuild", "Trade veterans, stockpile draft picks"),
        ]

        for i, (value, label, tooltip) in enumerate(options):
            radio = QRadioButton(label)
            desc = QLabel(f"   {tooltip}")
            desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

            radio.setProperty("value", value)
            self.philosophy_group.addButton(radio, i)
            layout.addWidget(radio)
            layout.addWidget(desc)
            layout.addSpacing(5)

            if value == "maintain":
                radio.setChecked(True)

        return group

    def _create_budget_section(self) -> QGroupBox:
        """Radio group: Aggressive / Moderate / Conservative."""
        group = QGroupBox("Budget Stance")
        layout = QVBoxLayout(group)

        self.budget_group = QButtonGroup(self)

        options = [
            ("aggressive", "Aggressive", "Spend to cap, maximize guaranteed money"),
            ("moderate", "Moderate (Recommended)", "Balanced approach to spending"),
            ("conservative", "Conservative", "Preserve cap flexibility, shorter contracts"),
        ]

        for i, (value, label, tooltip) in enumerate(options):
            radio = QRadioButton(label)
            desc = QLabel(f"   {tooltip}")
            desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

            radio.setProperty("value", value)
            self.budget_group.addButton(radio, i)
            layout.addWidget(radio)
            layout.addWidget(desc)
            layout.addSpacing(5)

            if value == "moderate":
                radio.setChecked(True)

        return group

    def _create_priorities_section(self) -> QGroupBox:
        """5 dropdowns for position priorities."""
        group = QGroupBox("Position Priorities (Optional)")
        layout = QVBoxLayout(group)

        desc = QLabel(
            "Select up to 5 positions to prioritize in draft and free agency. "
            "GM will give bonus consideration to these positions."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.CAPTION}; padding-bottom: 5px;"
        )
        layout.addWidget(desc)

        priority_layout = QHBoxLayout()
        self.priority_combos = []

        for i in range(5):
            priority_layout.addWidget(QLabel(f"#{i+1}:"))
            combo = QComboBox()
            combo.addItems(self._available_positions)
            combo.setMinimumWidth(70)
            self.priority_combos.append(combo)
            priority_layout.addWidget(combo)

        priority_layout.addStretch()
        layout.addLayout(priority_layout)
        return group

    def _create_protected_section(self) -> QGroupBox:
        """Checkbox table for protected players (max 5)."""
        group = QGroupBox("Protected Players (Max 5)")
        layout = QVBoxLayout(group)

        desc = QLabel("Players you want to keep - will not be traded or cut.")
        desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        layout.addWidget(desc)

        self.protected_table = self._create_player_table()
        layout.addWidget(self.protected_table)

        self.protected_count = QLabel("0/5 selected")
        self.protected_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.protected_count)

        return group

    def _create_expendable_section(self) -> QGroupBox:
        """Checkbox table for expendable players (max 10)."""
        group = QGroupBox("Expendable Players (Max 10)")
        layout = QVBoxLayout(group)

        desc = QLabel("Players you're willing to trade or cut if needed.")
        desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")
        layout.addWidget(desc)

        self.expendable_table = self._create_player_table()
        layout.addWidget(self.expendable_table)

        self.expendable_count = QLabel("0/10 selected")
        self.expendable_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        layout.addWidget(self.expendable_count)

        return group

    def _create_player_table(self) -> QTableWidget:
        """Create checkbox-enabled player table."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["", "Player", "Pos", "OVR"])
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setMaximumHeight(180)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        table.setColumnWidth(0, 30)
        table.setColumnWidth(2, 50)
        table.setColumnWidth(3, 45)

        # Sort roster by overall descending for easier selection
        sorted_roster = sorted(
            self.roster,
            key=lambda p: p.get("overall", 0),
            reverse=True
        )

        # Populate with roster
        table.setRowCount(len(sorted_roster))
        for row, player in enumerate(sorted_roster):
            # Checkbox in container widget for centering
            checkbox = QCheckBox()
            checkbox.setProperty("player_id", player.get("player_id"))
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            table.setCellWidget(row, 0, checkbox_widget)

            # Player name
            name = player.get("name", f"{player.get('first_name', '')} {player.get('last_name', '')}".strip())
            table.setItem(row, 1, QTableWidgetItem(name))

            # Position
            pos_item = QTableWidgetItem(player.get("position", ""))
            pos_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, pos_item)

            # Overall
            ovr_item = QTableWidgetItem(str(player.get("overall", 0)))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 3, ovr_item)

        return table

    def _create_notes_section(self) -> QGroupBox:
        """Free-form text area for owner notes."""
        group = QGroupBox("Notes to GM (Optional)")
        layout = QVBoxLayout(group)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMaximumHeight(70)
        self.notes_edit.setPlaceholderText(
            "Any specific instructions, targets, or notes for your GM..."
        )
        layout.addWidget(self.notes_edit)

        return group

    def _create_trust_gm_section(self) -> QFrame:
        """Trust GM checkbox."""
        frame = QFrame()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        self.trust_gm_checkbox = QCheckBox(
            "Trust GM to handle offseason (skip approval gates)"
        )
        self.trust_gm_checkbox.setToolTip(
            "When checked, GM makes draft picks, FA signings, and roster moves "
            "without asking for your approval. Recommended for quick simulation."
        )
        layout.addWidget(self.trust_gm_checkbox)
        layout.addStretch()

        return frame

    def _create_preview_section(self) -> QGroupBox:
        """Preview summary of selections."""
        group = QGroupBox("Preview")
        layout = QVBoxLayout(group)

        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self.preview_label)

        return group

    def _create_buttons(self) -> QHBoxLayout:
        """Save and Cancel buttons."""
        layout = QHBoxLayout()
        layout.addStretch()

        skip_btn = QPushButton("Skip (Use Defaults)")
        skip_btn.clicked.connect(self._on_skip)
        layout.addWidget(skip_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Direction")
        save_btn.setDefault(True)
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        return layout

    def _connect_signals(self):
        """Connect change signals to preview update."""
        self.philosophy_group.buttonClicked.connect(self._update_preview)
        self.budget_group.buttonClicked.connect(self._update_preview)
        for combo in self.priority_combos:
            combo.currentTextChanged.connect(self._update_preview)
        self.trust_gm_checkbox.stateChanged.connect(self._update_preview)

        # Player table checkboxes
        self._connect_table_checkboxes(self.protected_table, self._on_protected_changed)
        self._connect_table_checkboxes(self.expendable_table, self._on_expendable_changed)

    def _connect_table_checkboxes(self, table: QTableWidget, handler):
        """Connect all checkboxes in a table to a handler."""
        for row in range(table.rowCount()):
            checkbox_widget = table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.stateChanged.connect(handler)

    def _on_protected_changed(self):
        """Update protected count and enforce max."""
        selected = self._get_selected_player_ids(self.protected_table)
        count = len(selected)
        self.protected_count.setText(f"{count}/5 selected")

        # Visual feedback for over limit
        if count > 5:
            self.protected_count.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.protected_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

        self._update_preview()

    def _on_expendable_changed(self):
        """Update expendable count and enforce max."""
        selected = self._get_selected_player_ids(self.expendable_table)
        count = len(selected)
        self.expendable_count.setText(f"{count}/10 selected")

        # Visual feedback for over limit
        if count > 10:
            self.expendable_count.setStyleSheet(f"color: {Colors.ERROR};")
        else:
            self.expendable_count.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")

        self._update_preview()

    def _get_selected_player_ids(self, table: QTableWidget) -> List[int]:
        """Get list of selected player IDs from table."""
        selected = []
        for row in range(table.rowCount()):
            checkbox_widget = table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    player_id = checkbox.property("player_id")
                    if player_id is not None:
                        selected.append(player_id)
        return selected

    def _get_selected_radio_value(self, group: QButtonGroup) -> str:
        """Get value property of selected radio button."""
        checked = group.checkedButton()
        return checked.property("value") if checked else ""

    def _update_preview(self):
        """Update preview label with current selections."""
        philosophy = self._get_selected_radio_value(self.philosophy_group)
        budget = self._get_selected_radio_value(self.budget_group)
        priorities = [c.currentText() for c in self.priority_combos if c.currentText()]
        protected_count = len(self._get_selected_player_ids(self.protected_table))
        expendable_count = len(self._get_selected_player_ids(self.expendable_table))
        trust = self.trust_gm_checkbox.isChecked()

        lines = [
            f"Philosophy: {philosophy.replace('_', ' ').title()}",
            f"Budget: {budget.title()}",
            f"Priorities: {', '.join(priorities) if priorities else 'None set'}",
            f"Protected: {protected_count} player{'s' if protected_count != 1 else ''}",
            f"Expendable: {expendable_count} player{'s' if expendable_count != 1 else ''}",
            f"Trust GM: {'Yes - GM will auto-decide' if trust else 'No - You approve decisions'}",
        ]
        self.preview_label.setText("\n".join(lines))

    def _load_existing(self):
        """Load existing directives into form."""
        if not self.existing:
            return

        # Philosophy
        for btn in self.philosophy_group.buttons():
            if btn.property("value") == self.existing.team_philosophy:
                btn.setChecked(True)
                break

        # Budget
        for btn in self.budget_group.buttons():
            if btn.property("value") == self.existing.budget_stance:
                btn.setChecked(True)
                break

        # Priorities
        for i, pos in enumerate(self.existing.priority_positions[:5]):
            if i < len(self.priority_combos):
                index = self.priority_combos[i].findText(pos)
                if index >= 0:
                    self.priority_combos[i].setCurrentIndex(index)

        # Protected players
        self._set_table_selections(
            self.protected_table, self.existing.protected_player_ids
        )

        # Expendable players
        self._set_table_selections(
            self.expendable_table, self.existing.expendable_player_ids
        )

        # Notes
        self.notes_edit.setPlainText(self.existing.owner_notes or "")

        # Trust GM
        self.trust_gm_checkbox.setChecked(self.existing.trust_gm)

        # Update counts
        self._on_protected_changed()
        self._on_expendable_changed()

    def _set_table_selections(self, table: QTableWidget, player_ids: List[int]):
        """Set checkbox selections in table based on player IDs."""
        for row in range(table.rowCount()):
            checkbox_widget = table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    player_id = checkbox.property("player_id")
                    checkbox.setChecked(player_id in player_ids)

    def _validate(self) -> Tuple[bool, str]:
        """Validate selections before save."""
        protected = self._get_selected_player_ids(self.protected_table)
        expendable = self._get_selected_player_ids(self.expendable_table)

        if len(protected) > 5:
            return False, "Maximum 5 protected players allowed."

        if len(expendable) > 10:
            return False, "Maximum 10 expendable players allowed."

        overlap = set(protected) & set(expendable)
        if overlap:
            return False, "A player cannot be both protected and expendable."

        return True, ""

    def _on_skip(self):
        """Skip directive setting and use defaults."""
        directives = OwnerDirectives.create_default(
            dynasty_id=self.dynasty_id,
            team_id=self.team_id,
            season=self.season
        )
        self.directive_saved.emit(directives)
        self.accept()

    def _on_save(self):
        """Validate and save directives."""
        valid, error = self._validate()
        if not valid:
            QMessageBox.warning(self, "Validation Error", error)
            return

        priorities = [c.currentText() for c in self.priority_combos if c.currentText()]

        # Preserve existing fields if updating
        existing = self.existing or OwnerDirectives.create_default(
            self.dynasty_id, self.team_id, self.season
        )

        try:
            directives = OwnerDirectives(
                dynasty_id=self.dynasty_id,
                team_id=self.team_id,
                season=self.season,
                # Preserve existing draft/FA specific fields
                target_wins=existing.target_wins,
                priority_positions=priorities,
                fa_wishlist=existing.fa_wishlist,
                draft_wishlist=existing.draft_wishlist,
                draft_strategy=existing.draft_strategy,
                fa_philosophy=existing.fa_philosophy,
                max_contract_years=existing.max_contract_years,
                max_guaranteed_percent=existing.max_guaranteed_percent,
                # New fields from this dialog
                team_philosophy=self._get_selected_radio_value(self.philosophy_group),
                budget_stance=self._get_selected_radio_value(self.budget_group),
                protected_player_ids=self._get_selected_player_ids(self.protected_table),
                expendable_player_ids=self._get_selected_player_ids(self.expendable_table),
                owner_notes=self.notes_edit.toPlainText().strip(),
                trust_gm=self.trust_gm_checkbox.isChecked(),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return

        self.directive_saved.emit(directives)
        self.accept()
