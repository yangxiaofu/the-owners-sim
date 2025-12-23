"""
FA Guidance Dialog - Owner's strategic guidance for Free Agency.

Part of Milestone 10: GM-Driven Free Agency with Owner Oversight.
Phase 1 MVP: Philosophy selection and priority positions.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton, QComboBox,
    QLabel, QPushButton, QGroupBox, QButtonGroup, QMessageBox, QSlider
)
from PySide6.QtCore import Signal, Qt

from game_cycle.models import FAGuidance, FAPhilosophy
from game_cycle_ui.theme import Colors, FontSizes


class FAGuidanceDialog(QDialog):
    """
    Dialog for configuring free agency guidance (Phase 1 MVP).

    Allows owner to set:
    - Overall FA philosophy (Aggressive/Balanced/Conservative)
    - Priority positions (1-3 positions to focus on)
    - Contract constraints (max years, max guaranteed %)

    Emits:
        guidance_saved: FAGuidance object when saved
    """

    guidance_saved = Signal(object)  # FAGuidance

    def __init__(
        self,
        current_guidance: FAGuidance = None,
        parent=None
    ):
        """
        Initialize dialog.

        Args:
            current_guidance: Existing guidance to load (None = default Balanced)
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Free Agency Strategy Configuration")
        self.resize(700, 650)

        self._current_guidance = current_guidance or FAGuidance.create_default()

        # Available positions for priority selection
        self._available_positions = [
            "None",  # Option to leave empty
            "QB", "RB", "WR", "TE", "OT", "OG", "C",
            "EDGE", "DT", "LB", "CB", "S", "K", "P"
        ]

        self._setup_ui()
        self._load_current_guidance()

    def _setup_ui(self):
        """Create the dialog UI."""
        layout = QVBoxLayout(self)

        # Info header
        info_label = QLabel(
            "Set your strategic direction for free agency. Your GM will use this "
            "guidance when proposing signings, but you'll have final approval on all moves."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 10px; font-size: {FontSizes.CAPTION};")
        layout.addWidget(info_label)

        # Philosophy section
        philosophy_group = self._create_philosophy_group()
        layout.addWidget(philosophy_group)

        # Priority positions section
        priorities_group = self._create_priorities_group()
        layout.addWidget(priorities_group)

        # Contract constraints section
        constraints_group = self._create_constraints_group()
        layout.addWidget(constraints_group)

        # Preview section
        preview_group = self._create_preview_group()
        layout.addWidget(preview_group)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        skip_btn = QPushButton("Skip (Use Defaults)")
        skip_btn.clicked.connect(self._skip_guidance)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save Guidance")
        save_btn.clicked.connect(self._save_guidance)
        save_btn.setDefault(True)

        button_layout.addWidget(skip_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _create_philosophy_group(self) -> QGroupBox:
        """Create the philosophy selection group."""
        group = QGroupBox("Free Agency Philosophy")
        layout = QVBoxLayout()

        self._philosophy_group = QButtonGroup(self)

        # Aggressive
        aggressive_radio = QRadioButton("Aggressive - Chase Stars")
        aggressive_desc = QLabel(
            "   → GM will pursue elite players, offer top market AAV, prioritize impact signings"
        )
        aggressive_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._philosophy_group.addButton(aggressive_radio, 0)  # ID 0
        layout.addWidget(aggressive_radio)
        layout.addWidget(aggressive_desc)
        layout.addSpacing(10)

        # Balanced (recommended)
        balanced_radio = QRadioButton("Balanced - Best Value (Recommended)")
        balanced_desc = QLabel(
            "   → GM will find best value across tiers, mix of stars and depth, controlled spending"
        )
        balanced_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._philosophy_group.addButton(balanced_radio, 1)  # ID 1
        layout.addWidget(balanced_radio)
        layout.addWidget(balanced_desc)
        layout.addSpacing(10)

        # Conservative
        conservative_radio = QRadioButton("Conservative - Low Risk Depth")
        conservative_desc = QLabel(
            "   → GM will focus on depth players, short contracts, avoid expensive risks"
        )
        conservative_desc.setStyleSheet(f"color: {Colors.MUTED}; font-size: {FontSizes.CAPTION};")

        self._philosophy_group.addButton(conservative_radio, 2)  # ID 2
        layout.addWidget(conservative_radio)
        layout.addWidget(conservative_desc)

        group.setLayout(layout)

        # Connect philosophy change to update preview
        self._philosophy_group.buttonClicked.connect(self._update_preview)

        return group

    def _create_priorities_group(self) -> QGroupBox:
        """Create the priority positions selection group."""
        group = QGroupBox("Priority Positions (Optional)")
        layout = QVBoxLayout()

        desc = QLabel(
            "Select 1-3 positions to prioritize. GM will give +15 bonus to proposals "
            "for these positions."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.CAPTION}; padding-bottom: 10px;")
        layout.addWidget(desc)

        # Three dropdowns for priority positions
        priority_layout = QHBoxLayout()

        self._priority_combos = []
        for i in range(3):
            combo = QComboBox()
            combo.addItems(self._available_positions)
            combo.currentIndexChanged.connect(self._update_preview)
            self._priority_combos.append(combo)
            priority_layout.addWidget(QLabel(f"Priority {i+1}:"))
            priority_layout.addWidget(combo)

        layout.addLayout(priority_layout)

        group.setLayout(layout)
        return group

    def _create_constraints_group(self) -> QGroupBox:
        """Create the contract constraints group."""
        group = QGroupBox("Contract Constraints (Optional)")
        layout = QVBoxLayout()

        desc = QLabel(
            "Set maximum contract terms you're comfortable with. GM will not propose "
            "contracts exceeding these limits."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: {FontSizes.CAPTION}; padding-bottom: 10px;")
        layout.addWidget(desc)

        # Max contract years slider
        years_layout = QHBoxLayout()
        years_layout.addWidget(QLabel("Max Contract Years:"))

        self._years_slider = QSlider(Qt.Horizontal)
        self._years_slider.setMinimum(1)
        self._years_slider.setMaximum(5)
        self._years_slider.setValue(5)
        self._years_slider.setTickPosition(QSlider.TicksBelow)
        self._years_slider.setTickInterval(1)
        self._years_slider.valueChanged.connect(self._update_years_label)
        self._years_slider.valueChanged.connect(self._update_preview)

        self._years_label = QLabel("5 years")
        self._years_label.setMinimumWidth(60)

        years_layout.addWidget(self._years_slider)
        years_layout.addWidget(self._years_label)
        layout.addLayout(years_layout)

        # Max guaranteed % slider
        guaranteed_layout = QHBoxLayout()
        guaranteed_layout.addWidget(QLabel("Max Guaranteed %:"))

        self._guaranteed_slider = QSlider(Qt.Horizontal)
        self._guaranteed_slider.setMinimum(0)
        self._guaranteed_slider.setMaximum(100)
        self._guaranteed_slider.setValue(75)
        self._guaranteed_slider.setTickPosition(QSlider.TicksBelow)
        self._guaranteed_slider.setTickInterval(25)
        self._guaranteed_slider.valueChanged.connect(self._update_guaranteed_label)
        self._guaranteed_slider.valueChanged.connect(self._update_preview)

        self._guaranteed_label = QLabel("75%")
        self._guaranteed_label.setMinimumWidth(60)

        guaranteed_layout.addWidget(self._guaranteed_slider)
        guaranteed_layout.addWidget(self._guaranteed_label)
        layout.addLayout(guaranteed_layout)

        group.setLayout(layout)
        return group

    def _create_preview_group(self) -> QGroupBox:
        """Create the preview/explanation group."""
        group = QGroupBox("Preview: What This Means")
        layout = QVBoxLayout()

        self._preview_label = QLabel("Select your guidance to see what it means")
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self._preview_label)

        group.setLayout(layout)
        return group

    def _update_years_label(self, value: int):
        """Update the years label when slider changes."""
        self._years_label.setText(f"{value} year{'s' if value > 1 else ''}")

    def _update_guaranteed_label(self, value: int):
        """Update the guaranteed label when slider changes."""
        self._guaranteed_label.setText(f"{value}%")

    def _update_preview(self):
        """Update the preview text based on selected guidance."""
        selected_id = self._philosophy_group.checkedId()

        # Get philosophy text
        if selected_id == 0:  # Aggressive
            philosophy_text = (
                "AGGRESSIVE Philosophy:\n"
                "• GM will target elite-tier players\n"
                "• Willing to pay top market AAV (95-110% of market value)\n"
                "• Longer contracts with higher guarantees\n"
                "• Focus on impact signings over depth"
            )
        elif selected_id == 1:  # Balanced
            philosophy_text = (
                "BALANCED Philosophy:\n"
                "• GM will seek best value across all tiers\n"
                "• Reasonable AAV offers (90-100% of market value)\n"
                "• Mix of impact players and depth pieces\n"
                "• This is the recommended default approach"
            )
        elif selected_id == 2:  # Conservative
            philosophy_text = (
                "CONSERVATIVE Philosophy:\n"
                "• GM will focus on depth-tier players\n"
                "• Below-market AAV offers (85-95% of market value)\n"
                "• Shorter contracts with lower guarantees\n"
                "• Minimize risk, build through depth"
            )
        else:
            philosophy_text = "Select a philosophy to see what it means"

        # Get priority positions
        priorities = self._get_selected_priorities()
        if priorities:
            priority_text = f"\n\nPRIORITY POSITIONS: {', '.join(priorities)}\n"
            priority_text += "• GM will give +15 bonus to proposals for these positions\n"
            priority_text += "• Higher chance of GM proposing signings at these spots"
        else:
            priority_text = "\n\nNo priority positions set - GM has full discretion"

        # Get contract constraints
        max_years = self._years_slider.value()
        max_guaranteed = self._guaranteed_slider.value()
        constraints_text = (
            f"\n\nCONTRACT CONSTRAINTS:\n"
            f"• Max contract length: {max_years} year{'s' if max_years > 1 else ''}\n"
            f"• Max guaranteed: {max_guaranteed}%"
        )

        # Combine
        full_text = philosophy_text + priority_text + constraints_text
        self._preview_label.setText(full_text)

    def _get_selected_priorities(self) -> list:
        """Get list of selected priority positions (excluding 'None')."""
        priorities = []
        for combo in self._priority_combos:
            position = combo.currentText()
            if position != "None" and position not in priorities:
                priorities.append(position)
        return priorities

    def _load_current_guidance(self):
        """Load current guidance into UI."""
        # Map philosophy enum to button ID
        philosophy_to_id = {
            FAPhilosophy.AGGRESSIVE: 0,
            FAPhilosophy.BALANCED: 1,
            FAPhilosophy.CONSERVATIVE: 2,
        }

        button_id = philosophy_to_id.get(
            self._current_guidance.philosophy, 1
        )  # Default to Balanced
        button = self._philosophy_group.button(button_id)
        if button:
            button.setChecked(True)

        # Load priority positions
        priorities = self._current_guidance.priority_positions[:3]  # Max 3
        for i, combo in enumerate(self._priority_combos):
            if i < len(priorities):
                position = priorities[i]
                index = combo.findText(position)
                if index >= 0:
                    combo.setCurrentIndex(index)
            else:
                combo.setCurrentIndex(0)  # "None"

        # Load contract constraints
        self._years_slider.setValue(self._current_guidance.max_contract_years)
        guaranteed_percent = int(self._current_guidance.max_guaranteed_percent * 100)
        self._guaranteed_slider.setValue(guaranteed_percent)

        # Update preview
        self._update_preview()

    def _skip_guidance(self):
        """Skip guidance and use defaults."""
        # Create default guidance
        guidance = FAGuidance.create_default()

        # Emit and close
        self.guidance_saved.emit(guidance)
        self.accept()

    def _save_guidance(self):
        """Validate and save the guidance."""
        # Get selected philosophy
        selected_id = self._philosophy_group.checkedId()
        if selected_id == -1:
            QMessageBox.warning(
                self, "No Philosophy", "Please select a free agency philosophy"
            )
            return

        # Map button ID to philosophy enum
        id_to_philosophy = {
            0: FAPhilosophy.AGGRESSIVE,
            1: FAPhilosophy.BALANCED,
            2: FAPhilosophy.CONSERVATIVE,
        }

        philosophy = id_to_philosophy.get(selected_id, FAPhilosophy.BALANCED)

        # Get priority positions
        priorities = self._get_selected_priorities()

        # Get contract constraints
        max_years = self._years_slider.value()
        max_guaranteed = self._guaranteed_slider.value() / 100.0  # Convert to 0.0-1.0

        # Create guidance
        try:
            guidance = FAGuidance(
                philosophy=philosophy,
                budget_by_position_group={},  # Phase 1: No budget allocation yet
                priority_positions=priorities,
                max_contract_years=max_years,
                max_guaranteed_percent=max_guaranteed,
            )
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Configuration", str(e))
            return

        # Emit and close
        self.guidance_saved.emit(guidance)
        self.accept()
