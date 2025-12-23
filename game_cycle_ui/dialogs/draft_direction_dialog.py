"""
Draft Direction Dialog - Owner's strategic guidance for NFL Draft.

Phase 1 MVP: Basic strategy selection (BPA, Balanced, Needs-Based)
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QLabel, QPushButton, QGroupBox, QButtonGroup, QMessageBox,
    QComboBox
)
from PySide6.QtCore import Signal

from game_cycle.models import DraftDirection, DraftStrategy
from game_cycle_ui.theme import Colors, FontSizes


class DraftDirectionDialog(QDialog):
    """
    Dialog for configuring draft strategy (Phase 2).

    Allows owner to set overall strategy:
    - Best Player Available (BPA)
    - Balanced (Recommended)
    - Needs-Based
    - Position Focus (new in Phase 2)

    Phase 2 features:
    - Position priorities (1-5 positions)
    - Team needs display

    Emits:
        direction_saved: DraftDirection object when saved
    """

    direction_saved = Signal(object)  # DraftDirection

    def __init__(
        self,
        current_direction: DraftDirection = None,
        team_id: int = None,
        season: int = None,
        dynasty_id: str = None,
        db_path: str = None,
        parent=None
    ):
        """
        Initialize dialog.

        Args:
            current_direction: Existing direction to load (None = default Balanced)
            team_id: User's team ID (for team needs analysis)
            season: Current season
            dynasty_id: Dynasty ID
            db_path: Database path
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Draft Strategy Configuration")
        self.resize(600, 700)

        self._current_direction = current_direction or DraftDirection()
        self._team_id = team_id
        self._season = season
        self._dynasty_id = dynasty_id
        self._db_path = db_path

        self._setup_ui()
        self._load_current_direction()

        # Load team needs if context available
        if self._team_id is not None:
            self._load_team_needs()

    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Strategy section
        strategy_group = self._create_strategy_group()
        layout.addWidget(strategy_group)

        # Position priorities section (Phase 2)
        priorities_group = self._create_priorities_group()
        layout.addWidget(priorities_group)

        # Team needs section (Phase 2) - only if team context available
        if self._team_id is not None:
            needs_group = self._create_team_needs_group()
            layout.addWidget(needs_group)

        # Preview section
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        default_btn = QPushButton("Use Default")
        default_btn.clicked.connect(self._use_default)

        save_btn = QPushButton("Save Strategy")
        save_btn.clicked.connect(self._save_direction)
        save_btn.setDefault(True)

        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(default_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_strategy_group(self) -> QGroupBox:
        """Create the strategy selection group."""
        group = QGroupBox("Overall Strategy")
        layout = QVBoxLayout()

        self._strategy_group = QButtonGroup(self)

        # BPA
        bpa_radio = QRadioButton("Best Player Available (BPA)")
        bpa_desc = QLabel("   → Ignore needs, always pick highest-rated prospect")
        bpa_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._strategy_group.addButton(bpa_radio, 0)  # ID 0
        layout.addWidget(bpa_radio)
        layout.addWidget(bpa_desc)
        layout.addSpacing(10)

        # Balanced
        balanced_radio = QRadioButton("Balanced (Recommended)")
        balanced_desc = QLabel("   → Balance talent and need - current system behavior")
        balanced_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._strategy_group.addButton(balanced_radio, 1)  # ID 1
        layout.addWidget(balanced_radio)
        layout.addWidget(balanced_desc)
        layout.addSpacing(10)

        # Needs-Based
        needs_radio = QRadioButton("Needs-Based")
        needs_desc = QLabel("   → Aggressively fill holes, willing to reach for needed positions")
        needs_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._strategy_group.addButton(needs_radio, 2)  # ID 2
        layout.addWidget(needs_radio)
        layout.addWidget(needs_desc)
        layout.addSpacing(10)

        # Position Focus (Phase 2)
        focus_radio = QRadioButton("Position Focus")
        focus_desc = QLabel("   → Only consider specific positions (requires priority list)")
        focus_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._strategy_group.addButton(focus_radio, 3)  # ID 3
        layout.addWidget(focus_radio)
        layout.addWidget(focus_desc)

        group.setLayout(layout)

        # Connect strategy change to update preview
        self._strategy_group.buttonClicked.connect(self._update_preview)

        return group

    def _create_priorities_group(self) -> QGroupBox:
        """Create the position priorities group (Phase 2)."""
        group = QGroupBox("Position Priorities (Optional)")
        layout = QVBoxLayout()

        note_label = QLabel("Note: Required for Position Focus strategy")
        note_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
        layout.addWidget(note_label)

        # Position options for dropdowns
        self._position_options = [
            "None", "QB", "RB", "WR", "TE", "OT", "OG", "C",
            "EDGE", "DT", "LB", "CB", "S", "K", "P"
        ]

        # Create 5 priority dropdowns
        self._priority_combos = []
        for i in range(1, 6):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{i}."))

            combo = QComboBox()
            combo.setMinimumWidth(150)
            combo.addItems(self._position_options)
            self._priority_combos.append(combo)

            row.addWidget(combo)
            row.addStretch()
            layout.addLayout(row)

        group.setLayout(layout)
        return group

    def _create_team_needs_group(self) -> QGroupBox:
        """Create the team needs display group (Phase 2)."""
        group = QGroupBox("Your Team Needs (AI Analysis)")
        layout = QVBoxLayout()

        self._needs_label = QLabel("Loading team needs...")
        self._needs_label.setWordWrap(True)
        self._needs_label.setStyleSheet("padding: 5px;")
        layout.addWidget(self._needs_label)

        group.setLayout(layout)
        return group

    def _load_team_needs(self):
        """Load and display team needs from TeamNeedsAnalyzer."""
        if not self._team_id or not self._db_path or not self._dynasty_id or not self._season:
            self._needs_label.setText("Team context not available")
            return

        try:
            from offseason.team_needs_analyzer import TeamNeedsAnalyzer
            analyzer = TeamNeedsAnalyzer(self._db_path, self._dynasty_id)
            needs = analyzer.analyze_team_needs(
                team_id=self._team_id,
                season=self._season
            )

            # Group by urgency
            critical = [n for n in needs if n.get("urgency_score", 0) >= 5]
            high = [n for n in needs if n.get("urgency_score", 0) == 4]
            medium = [n for n in needs if n.get("urgency_score", 0) == 3]

            # Format text
            text_parts = []
            if critical:
                positions = ", ".join([n["position"] for n in critical[:5]])
                text_parts.append(f"🔴 Critical: {positions}")
            if high:
                positions = ", ".join([n["position"] for n in high[:5]])
                text_parts.append(f"🟠 High: {positions}")
            if medium:
                positions = ", ".join([n["position"] for n in medium[:5]])
                text_parts.append(f"🟡 Medium: {positions}")

            if text_parts:
                self._needs_label.setText("\n".join(text_parts))
            else:
                self._needs_label.setText("No significant needs detected")

        except Exception as e:
            self._needs_label.setText(f"Could not load team needs: {str(e)}")

    def _create_preview_group(self) -> QGroupBox:
        """Create the preview/explanation group."""
        group = QGroupBox("Preview: What This Means")
        layout = QVBoxLayout()

        self._preview_label = QLabel("Select a strategy to see what it does")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self._preview_label)

        group.setLayout(layout)

        return group

    def _update_preview(self):
        """Update the preview text based on selected strategy."""
        selected_id = self._strategy_group.checkedId()

        if selected_id == 0:  # BPA
            text = (
                "With BPA strategy:\n\n"
                "• AI will always pick the highest-rated prospect\n"
                "• Ignores team needs completely\n"
                "• Best for stockpiling talent\n"
                "• Trust trades/free agency to fill holes later"
            )
        elif selected_id == 1:  # Balanced
            text = (
                "With Balanced strategy:\n\n"
                "• AI will prefer prospects that fill team needs\n"
                "• Still considers overall prospect rating\n"
                "• Avoids reaching too early for needs\n"
                "• This is the recommended default strategy"
            )
        elif selected_id == 2:  # Needs-Based
            text = (
                "With Needs-Based strategy:\n\n"
                "• AI will aggressively target critical needs\n"
                "• Willing to reach for needed positions\n"
                "• Best when you have glaring holes\n"
                "• May sacrifice some overall talent for fit"
            )
        elif selected_id == 3:  # Position Focus
            text = (
                "With Position Focus strategy:\n\n"
                "• AI will ONLY consider your priority positions\n"
                "• All other positions are excluded\n"
                "• Higher priority = larger bonuses (1st: +25, 2nd: +20...)\n"
                "• REQUIRES: At least 1 priority position selected below"
            )
        else:
            text = "Select a strategy to see what it does"

        self._preview_label.setText(text)

    def _load_current_direction(self):
        """Load current direction into UI."""
        # Map strategy enum to button ID
        strategy_to_id = {
            DraftStrategy.BEST_PLAYER_AVAILABLE: 0,
            DraftStrategy.BALANCED: 1,
            DraftStrategy.NEEDS_BASED: 2,
            DraftStrategy.POSITION_FOCUS: 3,
        }

        button_id = strategy_to_id.get(self._current_direction.strategy, 1)  # Default to Balanced
        button = self._strategy_group.button(button_id)
        if button:
            button.setChecked(True)

        # Load priorities (Phase 2)
        for i, position in enumerate(self._current_direction.priority_positions):
            if i < 5:  # Max 5 priorities
                try:
                    index = self._priority_combos[i].findText(position)
                    if index >= 0:
                        self._priority_combos[i].setCurrentIndex(index)
                except (IndexError, ValueError):
                    pass

        # Update preview
        self._update_preview()

    def _use_default(self):
        """Reset to default Balanced strategy."""
        # Find Balanced button and check it
        button = self._strategy_group.button(1)  # ID 1 = Balanced
        if button:
            button.setChecked(True)

        # Clear priorities
        for combo in self._priority_combos:
            combo.setCurrentIndex(0)  # "None"

        self._update_preview()

    def _save_direction(self):
        """Validate and save the direction."""
        # Get selected strategy
        selected_id = self._strategy_group.checkedId()
        if selected_id == -1:
            QMessageBox.warning(self, "No Strategy", "Please select a draft strategy")
            return

        # Map button ID to strategy enum
        id_to_strategy = {
            0: DraftStrategy.BEST_PLAYER_AVAILABLE,
            1: DraftStrategy.BALANCED,
            2: DraftStrategy.NEEDS_BASED,
            3: DraftStrategy.POSITION_FOCUS,
        }

        strategy = id_to_strategy.get(selected_id, DraftStrategy.BALANCED)

        # Collect priorities (Phase 2)
        priority_positions = []
        for combo in self._priority_combos:
            pos = combo.currentText()
            if pos != "None":
                priority_positions.append(pos)

        # Create direction
        direction = DraftDirection(
            strategy=strategy,
            priority_positions=priority_positions,
            watchlist_prospect_ids=self._current_direction.watchlist_prospect_ids  # Preserve
        )

        # Validate
        is_valid, error_msg = direction.validate()
        if not is_valid:
            QMessageBox.warning(self, "Invalid Configuration", error_msg)
            return

        # Emit and close
        self.direction_saved.emit(direction)
        self.accept()
