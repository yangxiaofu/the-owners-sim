"""
Staff Tab Widget for Team View

Displays coaching staff information including head coach, coordinators, and position coaches.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton
)
from PySide6.QtCore import Qt


class StaffTabWidget(QWidget):
    """
    Staff sub-tab widget for Team View.

    Displays:
    - Head coach with detailed information
    - Offensive, defensive, and special teams coordinators
    - Position coaches grid
    - Action buttons for staff management
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header
        header = QLabel("Coaching Staff - Detroit Lions")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #333333;")
        main_layout.addWidget(header)

        # Head Coach Panel
        head_coach_group = self._create_head_coach_panel()
        main_layout.addWidget(head_coach_group)

        # Coordinators Grid
        coordinators_group = self._create_coordinators_panel()
        main_layout.addWidget(coordinators_group)

        # Position Coaches Panel
        position_coaches_group = self._create_position_coaches_panel()
        main_layout.addWidget(position_coaches_group)

        # Action Buttons
        button_layout = self._create_action_buttons()
        main_layout.addLayout(button_layout)

        # Add stretch to push content to top
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_head_coach_panel(self) -> QGroupBox:
        """Create the head coach information panel."""
        group = QGroupBox("Head Coach")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Name
        name_label = QLabel("Dan Campbell")
        name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333333;")
        layout.addWidget(name_label)

        # Overall and Philosophy
        overall_philosophy = QLabel("Overall: <b>82</b> | Philosophy: <span style='color: #0066cc;'>AGGRESSIVE</span>")
        overall_philosophy.setTextFormat(Qt.RichText)
        layout.addWidget(overall_philosophy)

        # Years and Record
        years_record = QLabel("Years with Team: 3 | Career Record: 24-17")
        years_record.setStyleSheet("color: #666666;")
        layout.addWidget(years_record)

        # Strengths
        strengths = QLabel("Strengths: Offensive Mind, Player Development")
        strengths.setStyleSheet("color: #006600; font-style: italic;")
        layout.addWidget(strengths)

        # Weaknesses
        weaknesses = QLabel("Weaknesses: Clock Management, Challenge Decisions")
        weaknesses.setStyleSheet("color: #cc0000; font-style: italic;")
        layout.addWidget(weaknesses)

        group.setLayout(layout)
        return group

    def _create_coordinators_panel(self) -> QGroupBox:
        """Create the coordinators grid panel."""
        group = QGroupBox("Coordinators")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # Offensive Coordinator
        oc_widget = self._create_coordinator_widget(
            "Offensive Coordinator",
            "Ben Johnson",
            79,
            "BALANCED",
            "Specialty: Pass Heavy"
        )
        grid_layout.addWidget(oc_widget, 0, 0)

        # Defensive Coordinator
        dc_widget = self._create_coordinator_widget(
            "Defensive Coordinator",
            "Aaron Glenn",
            81,
            "AGGRESSIVE",
            "Specialty: Zone Coverage"
        )
        grid_layout.addWidget(dc_widget, 0, 1)

        # Special Teams Coordinator
        st_widget = self._create_coordinator_widget(
            "Special Teams Coordinator",
            "Jack Fox",
            75,
            "CONSERVATIVE",
            ""
        )
        grid_layout.addWidget(st_widget, 0, 2)

        group.setLayout(grid_layout)
        return group

    def _create_coordinator_widget(
        self,
        title: str,
        name: str,
        overall: int,
        philosophy: str,
        specialty: str
    ) -> QWidget:
        """Create a widget for a single coordinator."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(10, 10, 10, 10)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: #666666; font-size: 11px;")
        layout.addWidget(title_label)

        # Name
        name_label = QLabel(name)
        name_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333333;")
        layout.addWidget(name_label)

        # Overall
        overall_label = QLabel(f"OVR: <b>{overall}</b>")
        overall_label.setTextFormat(Qt.RichText)
        layout.addWidget(overall_label)

        # Philosophy
        philosophy_label = QLabel(f"Philosophy: <span style='color: #0066cc;'>{philosophy}</span>")
        philosophy_label.setTextFormat(Qt.RichText)
        layout.addWidget(philosophy_label)

        # Specialty (if provided)
        if specialty:
            specialty_label = QLabel(specialty)
            specialty_label.setStyleSheet("color: #666666; font-style: italic; font-size: 11px;")
            layout.addWidget(specialty_label)

        # Add border styling
        widget.setStyleSheet("""
            QWidget {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
            }
        """)

        widget.setLayout(layout)
        return widget

    def _create_position_coaches_panel(self) -> QGroupBox:
        """Create the position coaches grid panel."""
        group = QGroupBox("Position Coaches")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)

        # Position coaches data: (position, name, overall)
        coaches = [
            ("QB", "Mark Brunell", 74),
            ("RB", "Duce Staley", 72),
            ("WR", "Anquan Boldin", 76),
            ("TE", "Ben Johnson", 73),
            ("OL", "Hank Fraley", 78),
            ("DL", "Todd Wash", 77),
            ("LB", "Kelvin Sheppard", 75),
            ("DB", "Aubrey Pleasant", 79),
        ]

        # Create grid: 2 rows x 4 columns
        for idx, (position, name, overall) in enumerate(coaches):
            row = idx // 4
            col = idx % 4
            coach_widget = self._create_position_coach_widget(position, name, overall)
            grid_layout.addWidget(coach_widget, row, col)

        group.setLayout(grid_layout)
        return group

    def _create_position_coach_widget(
        self,
        position: str,
        name: str,
        overall: int
    ) -> QWidget:
        """Create a widget for a single position coach."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(3)
        layout.setContentsMargins(8, 8, 8, 8)

        # Position
        position_label = QLabel(position)
        position_label.setStyleSheet("font-weight: bold; color: #0066cc; font-size: 12px;")
        layout.addWidget(position_label)

        # Name
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #333333; font-size: 11px;")
        layout.addWidget(name_label)

        # Overall
        overall_label = QLabel(f"<b>{overall}</b>")
        overall_label.setTextFormat(Qt.RichText)
        overall_label.setStyleSheet("color: #666666; font-size: 11px;")
        layout.addWidget(overall_label)

        # Add border styling
        widget.setStyleSheet("""
            QWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
            }
        """)

        widget.setLayout(layout)
        return widget

    def _create_action_buttons(self) -> QHBoxLayout:
        """Create the action buttons at the bottom."""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # View Staff Details button
        details_btn = QPushButton("View Staff Details")
        details_btn.setEnabled(False)
        layout.addWidget(details_btn)

        # Staff Performance Report button
        report_btn = QPushButton("Staff Performance Report")
        report_btn.setEnabled(False)
        layout.addWidget(report_btn)

        # Add stretch to push buttons to the left
        layout.addStretch()

        return layout
