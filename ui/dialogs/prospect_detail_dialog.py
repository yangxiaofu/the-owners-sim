"""
Prospect Detail Dialog for The Owner's Sim

Shows comprehensive information about a single draft prospect including:
- Basic info (name, position, college, age)
- Ratings (overall, potential, ceiling, floor)
- Physical measurements (height, weight)
- Attributes (speed, strength, awareness, etc.)
- Scouting information
- Draft projection
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt
from typing import Dict, Any
import json


class ProspectDetailDialog(QDialog):
    """
    Dialog displaying detailed information about a draft prospect.

    Shows all available prospect data in an organized, readable format.
    """

    def __init__(self, prospect: Dict[str, Any], parent=None):
        super().__init__(parent)

        self.prospect = prospect

        # Dialog setup
        self.setWindowTitle(f"Prospect: {prospect.get('first_name', '')} {prospect.get('last_name', '')}")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header section
        header = self._create_header()
        layout.addWidget(header)

        # Basic info section
        basic_info = self._create_basic_info_section()
        layout.addWidget(basic_info)

        # Ratings section
        ratings = self._create_ratings_section()
        layout.addWidget(ratings)

        # Attributes section
        attributes = self._create_attributes_section()
        layout.addWidget(attributes)

        # Scouting section
        scouting = self._create_scouting_section()
        layout.addWidget(scouting)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setMinimumWidth(100)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def _create_header(self) -> QWidget:
        """Create header with prospect name and position."""
        header = QGroupBox()
        header_layout = QVBoxLayout(header)

        # Name
        name = f"{self.prospect.get('first_name', '')} {self.prospect.get('last_name', '')}"
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(name_label)

        # Position and College
        position = self.prospect.get('position', '')
        college = self.prospect.get('college', 'Unknown')
        subtitle = f"{position} | {college}"
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 16px; color: #666;")
        header_layout.addWidget(subtitle_label)

        return header

    def _create_basic_info_section(self) -> QGroupBox:
        """Create basic information section."""
        group = QGroupBox("Basic Information")
        grid = QGridLayout(group)
        grid.setSpacing(10)

        row = 0

        # Age
        age = self.prospect.get('age', 'Unknown')
        grid.addWidget(QLabel("<b>Age:</b>"), row, 0)
        grid.addWidget(QLabel(str(age)), row, 1)
        row += 1

        # Height
        height_inches = self.prospect.get('height_inches')
        if height_inches:
            feet = height_inches // 12
            inches = height_inches % 12
            height_str = f"{feet}'{inches}\""
        else:
            height_str = "Unknown"
        grid.addWidget(QLabel("<b>Height:</b>"), row, 0)
        grid.addWidget(QLabel(height_str), row, 1)
        row += 1

        # Weight
        weight = self.prospect.get('weight_lbs', 'Unknown')
        grid.addWidget(QLabel("<b>Weight:</b>"), row, 0)
        grid.addWidget(QLabel(f"{weight} lbs" if weight != 'Unknown' else "Unknown"), row, 1)
        row += 1

        # Hometown
        hometown = self.prospect.get('hometown')
        home_state = self.prospect.get('home_state')
        if hometown and home_state:
            location = f"{hometown}, {home_state}"
        elif home_state:
            location = home_state
        else:
            location = "Unknown"
        grid.addWidget(QLabel("<b>Hometown:</b>"), row, 0)
        grid.addWidget(QLabel(location), row, 1)
        row += 1

        # Archetype
        archetype = self.prospect.get('archetype_id', 'Unknown')
        grid.addWidget(QLabel("<b>Archetype:</b>"), row, 0)
        grid.addWidget(QLabel(archetype), row, 1)
        row += 1

        grid.setColumnStretch(1, 1)

        return group

    def _create_ratings_section(self) -> QGroupBox:
        """Create ratings section."""
        group = QGroupBox("Ratings & Projections")
        grid = QGridLayout(group)
        grid.setSpacing(10)

        row = 0

        # Overall rating
        overall = self.prospect.get('overall', 0)
        overall_label = QLabel(f"<b style='font-size: 18px;'>{overall}</b>")
        grid.addWidget(QLabel("<b>Overall Rating:</b>"), row, 0)
        grid.addWidget(overall_label, row, 1)
        row += 1

        # Potential rating
        potential = self.prospect.get('potential', 0)
        potential_label = QLabel(f"<b style='font-size: 18px;'>{potential}</b>")
        grid.addWidget(QLabel("<b>Potential:</b>"), row, 0)
        grid.addWidget(potential_label, row, 1)
        row += 1

        # Ceiling
        ceiling = self.prospect.get('ceiling', 'Unknown')
        grid.addWidget(QLabel("<b>Ceiling:</b>"), row, 0)
        grid.addWidget(QLabel(str(ceiling)), row, 1)
        row += 1

        # Floor
        floor = self.prospect.get('floor', 'Unknown')
        grid.addWidget(QLabel("<b>Floor:</b>"), row, 0)
        grid.addWidget(QLabel(str(floor)), row, 1)
        row += 1

        # Draft round projection
        draft_round = self.prospect.get('draft_round')
        draft_pick = self.prospect.get('draft_pick')
        if draft_round and draft_pick:
            projection = f"Round {draft_round}, Pick {draft_pick}"
        else:
            projection = "Unknown"
        grid.addWidget(QLabel("<b>Projected:</b>"), row, 0)
        grid.addWidget(QLabel(projection), row, 1)
        row += 1

        # Projected pick range
        proj_min = self.prospect.get('projected_pick_min')
        proj_max = self.prospect.get('projected_pick_max')
        if proj_min and proj_max:
            pick_range = f"Picks {proj_min}-{proj_max}"
        else:
            pick_range = "Unknown"
        grid.addWidget(QLabel("<b>Pick Range:</b>"), row, 0)
        grid.addWidget(QLabel(pick_range), row, 1)
        row += 1

        grid.setColumnStretch(1, 1)

        return group

    def _create_attributes_section(self) -> QGroupBox:
        """Create attributes section from JSON data."""
        group = QGroupBox("Attributes")
        layout = QVBoxLayout(group)

        # Get attributes from JSON
        attributes_json = self.prospect.get('attributes', {})
        if isinstance(attributes_json, str):
            try:
                attributes = json.loads(attributes_json)
            except json.JSONDecodeError:
                attributes = {}
        else:
            attributes = attributes_json

        if attributes:
            # Create grid for attributes
            grid = QGridLayout()
            grid.setSpacing(10)

            # Sort attributes by name for consistent display
            sorted_attrs = sorted(attributes.items())

            # Display in 2 columns
            col = 0
            row = 0
            for attr_name, attr_value in sorted_attrs:
                # Format attribute name (capitalize, replace underscores)
                display_name = attr_name.replace('_', ' ').title()

                # Attribute label
                label = QLabel(f"<b>{display_name}:</b>")
                grid.addWidget(label, row, col * 2)

                # Attribute value
                value = QLabel(str(attr_value))
                grid.addWidget(value, row, col * 2 + 1)

                # Move to next row/column
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

            layout.addLayout(grid)
        else:
            # No attributes available
            no_attrs_label = QLabel("No attribute data available")
            no_attrs_label.setStyleSheet("font-style: italic; color: #666;")
            layout.addWidget(no_attrs_label)

        return group

    def _create_scouting_section(self) -> QGroupBox:
        """Create scouting information section."""
        group = QGroupBox("Scouting Report")
        layout = QVBoxLayout(group)

        # Scouted overall
        scouted_overall = self.prospect.get('scouted_overall')
        if scouted_overall and scouted_overall > 0:
            scouted_label = QLabel(f"<b>Scouted Rating:</b> {scouted_overall}")
        else:
            scouted_label = QLabel("<b>Scouted Rating:</b> Not yet scouted")
        layout.addWidget(scouted_label)

        # Scouting confidence
        confidence = self.prospect.get('scouting_confidence', 'Unknown')
        confidence_label = QLabel(f"<b>Scouting Confidence:</b> {confidence.title()}")
        layout.addWidget(confidence_label)

        # Development curve
        dev_curve = self.prospect.get('development_curve', 'Unknown')
        dev_label = QLabel(f"<b>Development Curve:</b> {dev_curve.title()}")
        layout.addWidget(dev_label)

        # Scouting notes (if available in future)
        notes_text = QTextEdit()
        notes_text.setPlainText(
            f"Prospect from {self.prospect.get('college', 'Unknown')} with {confidence} scouting confidence.\n\n"
            f"Overall Rating: {self.prospect.get('overall', 0)} | Potential: {self.prospect.get('potential', 0)}\n"
            f"Ceiling: {self.prospect.get('ceiling', 0)} | Floor: {self.prospect.get('floor', 0)}\n\n"
            f"Development curve: {dev_curve}\n"
            f"Archetype: {self.prospect.get('archetype_id', 'Unknown')}"
        )
        notes_text.setReadOnly(True)
        notes_text.setMaximumHeight(150)
        layout.addWidget(notes_text)

        return group
