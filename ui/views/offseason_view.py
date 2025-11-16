"""
Offseason View for The Owner's Sim

Displays offseason dashboard with deadlines, free agency, draft, and roster management.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QTableView, QPushButton, QComboBox, QLineEdit, QFrame,
    QGridLayout, QGroupBox, QScrollArea, QListWidget
)
from PySide6.QtCore import Qt

import sys
import os

# Add parent directories to path
ui_path = os.path.dirname(os.path.dirname(__file__))
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

from models.roster_table_model import RosterTableModel
from controllers.player_controller import PlayerController

# Add src to path for database imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.draft_class_api import DraftClassAPI


class OffseasonView(QWidget):
    """
    Offseason management view.

    Phase 1: Placeholder
    Phase 4: Full implementation with offseason dashboard and dialogs
    """

    def __init__(self, parent=None, db_path=None, dynasty_id=None):
        super().__init__(parent)
        self.main_window = parent
        self.db_path = db_path or "data/database/nfl_simulation.db"
        self.dynasty_id = dynasty_id or "default"

        # Initialize controller
        self.controller = PlayerController(self.db_path, self.dynasty_id, main_window=parent)

        # Initialize draft class API
        self.draft_api = DraftClassAPI(self.db_path)

        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Offseason Management")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        # Tab widget for sub-sections
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._create_free_agents_tab(), "Free Agents")
        self.tabs.addTab(self._create_draft_tab(), "Draft")

        layout.addWidget(self.tabs)

    @property
    def season(self) -> int:
        """Current season year (proxied from parent/main window)."""
        if self.parent() is not None and hasattr(self.parent(), 'season'):
            return self.parent().season
        return 2025  # Fallback for testing/standalone usage

    def _create_dashboard_tab(self) -> QWidget:
        """Create dashboard tab with offseason overview (wireframe only)."""
        # Main container with scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # === TOP SECTION: Current Date and Phase ===
        header_section = self._create_header_section()
        main_layout.addWidget(header_section)

        # === MIDDLE SECTION: 3-column layout ===
        middle_layout = QHBoxLayout()
        middle_layout.setSpacing(15)

        # LEFT COLUMN: Deadlines and Calendar Controls
        left_column = QVBoxLayout()
        left_column.addWidget(self._create_deadlines_section())
        left_column.addWidget(self._create_calendar_controls_section())
        left_column.addStretch()
        middle_layout.addLayout(left_column, stretch=1)

        # MIDDLE COLUMN: Salary Cap Status
        middle_column = QVBoxLayout()
        middle_column.addWidget(self._create_salary_cap_section())
        middle_column.addStretch()
        middle_layout.addLayout(middle_column, stretch=1)

        # RIGHT COLUMN: Team Scouting Report
        right_column = QVBoxLayout()
        right_column.addWidget(self._create_team_scouting_report_section())
        right_column.addStretch()
        middle_layout.addLayout(right_column, stretch=1)

        main_layout.addLayout(middle_layout)

        # === BOTTOM SECTION: Franchise Tags, FA Strategy, Draft, Staff Feed ===
        bottom_layout = QVBoxLayout()
        bottom_layout.setSpacing(15)

        # Franchise Tag Recommendations
        bottom_layout.addWidget(self._create_franchise_tag_section())

        # Free Agency Strategy
        bottom_layout.addWidget(self._create_free_agency_strategy_section())

        # Draft Prospects Board
        bottom_layout.addWidget(self._create_draft_prospects_section())

        # Staff Recommendations Feed
        bottom_layout.addWidget(self._create_staff_recommendations_feed())

        main_layout.addLayout(bottom_layout)

        scroll.setWidget(container)

        # Wrap in widget
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(scroll)

        return wrapper

    def _create_header_section(self) -> QGroupBox:
        """Create header section with current date and phase."""
        group = QGroupBox("Current Status")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QHBoxLayout(group)

        # Current date display
        date_frame = QFrame()
        date_frame.setFrameShape(QFrame.Box)
        date_frame.setStyleSheet("QFrame { background-color: #f5f5f5; padding: 10px; border: 1px solid #ccc; }")
        date_layout = QVBoxLayout(date_frame)

        date_label = QLabel("📅 Current Date")
        date_label.setStyleSheet("font-weight: normal; color: #666;")
        date_value = QLabel("February 5, 2026")
        date_value.setStyleSheet("font-size: 16px; font-weight: bold;")

        date_layout.addWidget(date_label)
        date_layout.addWidget(date_value)
        layout.addWidget(date_frame)

        # Current phase display
        phase_frame = QFrame()
        phase_frame.setFrameShape(QFrame.Box)
        phase_frame.setStyleSheet("QFrame { background-color: #E8EFF5; padding: 10px; border: 1px solid #7B9DB8; }")
        phase_layout = QVBoxLayout(phase_frame)

        phase_label = QLabel("⚙️ Offseason Phase")
        phase_label.setStyleSheet("font-weight: normal; color: #6C757D;")
        phase_value = QLabel("Legal Tampering Period")
        phase_value.setStyleSheet("font-size: 16px; font-weight: bold; color: #6B8FA8;")

        phase_layout.addWidget(phase_label)
        phase_layout.addWidget(phase_value)
        layout.addWidget(phase_frame)

        # Week of offseason
        week_frame = QFrame()
        week_frame.setFrameShape(QFrame.Box)
        week_frame.setStyleSheet("QFrame { background-color: #f5f5f5; padding: 10px; border: 1px solid #ccc; }")
        week_layout = QVBoxLayout(week_frame)

        week_label = QLabel("📊 Offseason Progress")
        week_label.setStyleSheet("font-weight: normal; color: #666;")
        week_value = QLabel("Week 3 of 24")
        week_value.setStyleSheet("font-size: 16px; font-weight: bold;")

        week_layout.addWidget(week_label)
        week_layout.addWidget(week_value)
        layout.addWidget(week_frame)

        return group

    def _create_deadlines_section(self) -> QGroupBox:
        """Create deadlines countdown section."""
        group = QGroupBox("⏰ Upcoming Deadlines")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        # Deadline cards
        deadlines = [
            ("Franchise Tag Deadline", "March 5, 2026", "28 days", "#C6847A"),
            ("Start of Free Agency", "March 12, 2026", "35 days", "#4A9D7F"),
            ("NFL Draft - Round 1", "April 24, 2026", "78 days", "#6B8FA8"),
        ]

        for title, date, countdown, color in deadlines:
            deadline_frame = QFrame()
            deadline_frame.setFrameShape(QFrame.Box)
            deadline_frame.setStyleSheet(f"QFrame {{ background-color: #fafafa; padding: 8px; border-left: 4px solid {color}; }}")
            deadline_layout = QVBoxLayout(deadline_frame)
            deadline_layout.setSpacing(2)

            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: bold; font-size: 13px;")

            date_label = QLabel(date)
            date_label.setStyleSheet("color: #666; font-size: 11px;")

            countdown_label = QLabel(f"⏱️ {countdown} remaining")
            countdown_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12px;")

            deadline_layout.addWidget(title_label)
            deadline_layout.addWidget(date_label)
            deadline_layout.addWidget(countdown_label)

            layout.addWidget(deadline_frame)

        return group

    def _create_calendar_controls_section(self) -> QGroupBox:
        """Create calendar advancement controls."""
        group = QGroupBox("📆 Advance Calendar")
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        # Info label
        info = QLabel("Simulate forward through the offseason:")
        info.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(info)

        # Advance buttons
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        advance_day_btn = QPushButton("▶ Advance 1 Day")
        advance_day_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A9D7F;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3E8A6D;
            }
        """)

        advance_week_btn = QPushButton("▶▶ Advance 1 Week")
        advance_week_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B8FA8;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A7D92;
            }
        """)

        advance_deadline_btn = QPushButton("⏩ Advance to Next Deadline")
        advance_deadline_btn.setStyleSheet("""
            QPushButton {
                background-color: #D4A574;
                color: white;
                padding: 8px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C29563;
            }
        """)

        btn_layout.addWidget(advance_day_btn)
        btn_layout.addWidget(advance_week_btn)
        btn_layout.addWidget(advance_deadline_btn)

        layout.addLayout(btn_layout)

        return group

    def _create_salary_cap_section(self) -> QGroupBox:
        """Create salary cap health panel (owner-friendly high-level view)."""
        group = QGroupBox("💼 Salary Cap Health")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Cap space summary card
        summary_frame = QFrame()
        summary_frame.setFrameShape(QFrame.Box)
        summary_frame.setStyleSheet("QFrame { background-color: #F0F7F4; padding: 12px; border: 2px solid #4A9D7F; }")
        summary_layout = QVBoxLayout(summary_frame)

        cap_space_label = QLabel("Cap Space")
        cap_space_label.setStyleSheet("color: #6C757D; font-size: 11px;")
        cap_space_value = QLabel("$12.5M")
        cap_space_value.setStyleSheet("font-size: 24px; font-weight: bold; color: #4A9D7F;")

        status_label = QLabel("✓ Healthy")
        status_label.setStyleSheet("color: #4A9D7F; font-size: 12px; font-weight: bold;")

        summary_layout.addWidget(cap_space_label)
        summary_layout.addWidget(cap_space_value)
        summary_layout.addWidget(status_label)
        layout.addWidget(summary_frame)

        # Projected 2026 cap space
        projection_frame = QFrame()
        projection_frame.setStyleSheet("QFrame { background-color: white; padding: 8px; }")
        projection_layout = QVBoxLayout(projection_frame)

        projection_label = QLabel("Projected 2026 Cap Space")
        projection_label.setStyleSheet("color: #6C757D; font-size: 10px;")
        projection_value = QLabel("$94.5M available")
        projection_value.setStyleSheet("color: #2C3E50; font-weight: bold; font-size: 12px;")

        projection_layout.addWidget(projection_label)
        projection_layout.addWidget(projection_value)
        layout.addWidget(projection_frame)

        # Key concerns section
        concerns_label = QLabel("Key Concerns:")
        concerns_label.setStyleSheet("color: #6C757D; font-size: 11px; font-weight: bold; margin-top: 8px;")
        layout.addWidget(concerns_label)

        concerns = [
            "• 3 starters need extensions",
            "• Franchise tag decisions due",
            "• Limited FA budget available"
        ]

        for concern in concerns:
            concern_label = QLabel(concern)
            concern_label.setStyleSheet("color: #D4A574; font-size: 10px; padding-left: 8px;")
            layout.addWidget(concern_label)

        layout.addStretch()

        return group

    def _create_team_scouting_report_section(self) -> QGroupBox:
        """Create team scouting report with position grades."""
        group = QGroupBox("📊 Team Scouting Report")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Overall assessment
        assessment_label = QLabel("Roster Strength Assessment")
        assessment_label.setStyleSheet("color: #6C757D; font-size: 11px; font-weight: bold;")
        layout.addWidget(assessment_label)

        # Position grades (placeholder data)
        position_grades = [
            ("QB", "B+", "#7B9DB8"),
            ("RB", "A-", "#4A9D7F"),
            ("WR", "A", "#4A9D7F"),
            ("TE", "B", "#7B9DB8"),
            ("OL", "C+", "#D4A574"),
            ("DL", "B-", "#7B9DB8"),
            ("LB", "B", "#7B9DB8"),
            ("DB", "A-", "#4A9D7F"),
        ]

        # Position grades grid
        grades_grid = QGridLayout()
        grades_grid.setSpacing(8)

        row = 0
        col = 0
        for position, grade, color in position_grades:
            # Position grade card
            grade_frame = QFrame()
            grade_frame.setFrameShape(QFrame.Box)
            grade_frame.setStyleSheet(f"QFrame {{ background-color: white; padding: 8px; border-left: 3px solid {color}; }}")
            grade_layout = QHBoxLayout(grade_frame)
            grade_layout.setContentsMargins(6, 4, 6, 4)

            pos_label = QLabel(position)
            pos_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #2C3E50;")
            pos_label.setFixedWidth(30)

            grade_label = QLabel(grade)
            grade_label.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {color};")
            grade_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            grade_layout.addWidget(pos_label)
            grade_layout.addWidget(grade_label)

            grades_grid.addWidget(grade_frame, row, col)

            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        layout.addLayout(grades_grid)

        # Overall assessment text
        assessment_text = QLabel(
            "Strengths: Offense skilled positions (WR, RB), Secondary\n"
            "Needs: Offensive line depth, Defensive line pressure"
        )
        assessment_text.setStyleSheet("color: #6C757D; font-size: 11px; padding: 8px; background-color: #F0F7F4; border-radius: 3px;")
        assessment_text.setWordWrap(True)
        layout.addWidget(assessment_text)

        layout.addStretch()

        return group

    def _create_franchise_tag_section(self) -> QGroupBox:
        """Create franchise tag recommendations panel with staff rationale."""
        group = QGroupBox("🏷️ Franchise Tag Recommendations")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Deadline reminder
        deadline_label = QLabel("Deadline: March 5, 2026 (21 days)")
        deadline_label.setStyleSheet("color: #C6847A; font-size: 11px; font-weight: bold;")
        layout.addWidget(deadline_label)

        # #1 Recommended player
        rec1_frame = QFrame()
        rec1_frame.setFrameShape(QFrame.Box)
        rec1_frame.setStyleSheet("QFrame { background-color: white; padding: 10px; border-left: 4px solid #4A9D7F; }")
        rec1_layout = QVBoxLayout(rec1_frame)
        rec1_layout.setSpacing(6)

        rec1_title = QLabel("⭐ #1 RECOMMENDED: J. Sweat (DE, OVR 89)")
        rec1_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #2C3E50;")

        rec1_cost = QLabel("Tag Cost: $19.7M")
        rec1_cost.setStyleSheet("color: #6C757D; font-size: 11px;")

        rec1_gm = QLabel('GM: "Elite pass rusher, critical to defense. Market value $22M+."')
        rec1_gm.setStyleSheet("color: #6B8FA8; font-size: 10px; font-style: italic;")
        rec1_gm.setWordWrap(True)

        rec1_coach = QLabel('Coaching Staff: "Must keep. Top 5 in sacks last 2 years."')
        rec1_coach.setStyleSheet("color: #7B9DB8; font-size: 10px; font-style: italic;")
        rec1_coach.setWordWrap(True)

        # Action buttons for #1
        rec1_btn_layout = QHBoxLayout()
        rec1_btn_layout.setSpacing(6)

        apply_tag_btn = QPushButton("Apply Franchise Tag")
        apply_tag_btn.setStyleSheet("""
            QPushButton {
                background-color: #4A9D7F;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #3E8A6D;
            }
        """)

        negotiate_btn = QPushButton("Negotiate Extension")
        negotiate_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B8FA8;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5A7D92;
            }
        """)

        rec1_btn_layout.addWidget(apply_tag_btn)
        rec1_btn_layout.addWidget(negotiate_btn)
        rec1_btn_layout.addStretch()

        rec1_layout.addWidget(rec1_title)
        rec1_layout.addWidget(rec1_cost)
        rec1_layout.addWidget(rec1_gm)
        rec1_layout.addWidget(rec1_coach)
        rec1_layout.addLayout(rec1_btn_layout)

        layout.addWidget(rec1_frame)

        # #2 Consider player
        rec2_frame = QFrame()
        rec2_frame.setFrameShape(QFrame.Box)
        rec2_frame.setStyleSheet("QFrame { background-color: white; padding: 10px; border-left: 4px solid #D4A574; }")
        rec2_layout = QVBoxLayout(rec2_frame)
        rec2_layout.setSpacing(6)

        rec2_title = QLabel("#2 CONSIDER: D. Goedert (TE, OVR 84)")
        rec2_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #2C3E50;")

        rec2_cost = QLabel("Tag Cost: $11.3M")
        rec2_cost.setStyleSheet("color: #6C757D; font-size: 11px;")

        rec2_gm = QLabel('GM: "Solid starter, but could find replacement in draft. Recommend extension talks first."')
        rec2_gm.setStyleSheet("color: #6B8FA8; font-size: 10px; font-style: italic;")
        rec2_gm.setWordWrap(True)

        # Action buttons for #2
        rec2_btn_layout = QHBoxLayout()
        rec2_btn_layout.setSpacing(6)

        apply_tag_btn2 = QPushButton("Apply Tag")
        apply_tag_btn2.setStyleSheet("""
            QPushButton {
                background-color: #D4A574;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #C29563;
            }
        """)

        extension_btn2 = QPushButton("Extension Talks")
        extension_btn2.setStyleSheet("""
            QPushButton {
                background-color: #6B8FA8;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #5A7D92;
            }
        """)

        let_walk_btn = QPushButton("Let Walk")
        let_walk_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #C6847A;
                padding: 6px 12px;
                border: 1px solid #C6847A;
                border-radius: 3px;
                font-weight: bold;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #FFF5F3;
            }
        """)

        rec2_btn_layout.addWidget(apply_tag_btn2)
        rec2_btn_layout.addWidget(extension_btn2)
        rec2_btn_layout.addWidget(let_walk_btn)
        rec2_btn_layout.addStretch()

        rec2_layout.addWidget(rec2_title)
        rec2_layout.addWidget(rec2_cost)
        rec2_layout.addWidget(rec2_gm)
        rec2_layout.addLayout(rec2_btn_layout)

        layout.addWidget(rec2_frame)

        layout.addStretch()

        return group

    def _create_free_agency_strategy_section(self) -> QGroupBox:
        """Create free agency strategy panel with priority targets."""
        group = QGroupBox("🎯 Free Agency Strategy")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # FA dates
        dates_label = QLabel("Legal Tampering: March 11 | FA Opens: March 13")
        dates_label.setStyleSheet("color: #6C757D; font-size: 10px;")
        layout.addWidget(dates_label)

        # Priority needs header
        needs_header = QLabel("Priority Needs (from Scouting Director):")
        needs_header.setStyleSheet("color: #2C3E50; font-size: 11px; font-weight: bold; margin-top: 6px;")
        layout.addWidget(needs_header)

        # Critical priority: OL
        critical_frame = QFrame()
        critical_frame.setFrameShape(QFrame.Box)
        critical_frame.setStyleSheet("QFrame { background-color: white; padding: 10px; border-left: 4px solid #C6847A; }")
        critical_layout = QVBoxLayout(critical_frame)
        critical_layout.setSpacing(6)

        critical_title = QLabel("🔴 CRITICAL: Offensive Line (LG position)")
        critical_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #C6847A;")

        critical_subtitle = QLabel("Recommended Targets:")
        critical_subtitle.setStyleSheet("color: #6C757D; font-size: 10px; font-weight: bold;")

        # Target 1
        target1 = QLabel("• Q. Nelson (OVR 92) - Est. $18M/yr - \"Elite guard, top priority\"")
        target1.setStyleSheet("color: #2C3E50; font-size: 10px; padding-left: 12px;")

        # Target 2
        target2 = QLabel("• C. Lindstrom (OVR 88) - Est. $14M/yr - \"Solid fit for zone scheme\"")
        target2.setStyleSheet("color: #2C3E50; font-size: 10px; padding-left: 12px;")

        critical_layout.addWidget(critical_title)
        critical_layout.addWidget(critical_subtitle)
        critical_layout.addWidget(target1)
        critical_layout.addWidget(target2)

        layout.addWidget(critical_frame)

        # Moderate priority: LB
        moderate_frame = QFrame()
        moderate_frame.setFrameShape(QFrame.Box)
        moderate_frame.setStyleSheet("QFrame { background-color: white; padding: 10px; border-left: 4px solid #D4A574; }")
        moderate_layout = QVBoxLayout(moderate_frame)
        moderate_layout.setSpacing(6)

        moderate_title = QLabel("🟡 MODERATE: Linebacker depth")
        moderate_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #D4A574;")

        moderate_subtitle = QLabel("Recommended Targets:")
        moderate_subtitle.setStyleSheet("color: #6C757D; font-size: 10px; font-weight: bold;")

        # Target
        target3 = QLabel("• B. Wagner (OVR 85) - Est. $8M/yr - \"Veteran leader, strong coverage\"")
        target3.setStyleSheet("color: #2C3E50; font-size: 10px; padding-left: 12px;")

        moderate_layout.addWidget(moderate_title)
        moderate_layout.addWidget(moderate_subtitle)
        moderate_layout.addWidget(target3)

        layout.addWidget(moderate_frame)

        # Optional priority: ST
        optional_frame = QFrame()
        optional_frame.setFrameShape(QFrame.Box)
        optional_frame.setStyleSheet("QFrame { background-color: white; padding: 8px; border-left: 4px solid #7B9DB8; }")
        optional_layout = QVBoxLayout(optional_frame)
        optional_layout.setSpacing(4)

        optional_title = QLabel("🟢 OPTIONAL: Special teams specialists")
        optional_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #7B9DB8;")

        optional_note = QLabel("(Can address in late draft rounds)")
        optional_note.setStyleSheet("color: #6C757D; font-size: 9px; font-style: italic;")

        optional_layout.addWidget(optional_title)
        optional_layout.addWidget(optional_note)

        layout.addWidget(optional_frame)

        layout.addStretch()

        return group

    def _create_draft_prospects_section(self) -> QGroupBox:
        """Create draft prospects board with team fit scores."""
        group = QGroupBox("📋 Draft Prospects Board")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        # Board header
        board_header = QLabel("Team Needs Aligned to Draft Board:")
        board_header.setStyleSheet("color: #2C3E50; font-size: 11px; font-weight: bold;")
        layout.addWidget(board_header)

        # Round 1 prospects
        round1_frame = QFrame()
        round1_frame.setFrameShape(QFrame.Box)
        round1_frame.setStyleSheet("QFrame { background-color: white; padding: 10px; border-left: 4px solid #6B8FA8; }")
        round1_layout = QVBoxLayout(round1_frame)
        round1_layout.setSpacing(6)

        round1_title = QLabel("Round 1 (Pick #15): Offensive Line")
        round1_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #2C3E50;")

        top3_label = QLabel("Top 3 Prospects Available:")
        top3_label.setStyleSheet("color: #6C757D; font-size: 10px; font-weight: bold; margin-top: 4px;")

        # Prospect 1
        prospect1 = QLabel("1. O. Fashanu (OT, Penn St.) - Grade: A | Fit: 95%")
        prospect1.setStyleSheet("color: #4A9D7F; font-size: 10px; font-weight: bold; padding-left: 12px;")

        # Prospect 2
        prospect2 = QLabel("2. J. Latham (OT, Alabama) - Grade: A- | Fit: 90%")
        prospect2.setStyleSheet("color: #4A9D7F; font-size: 10px; font-weight: bold; padding-left: 12px;")

        # Prospect 3
        prospect3 = QLabel("3. T. Fautanu (OG, Washington) - Grade: B+ | Fit: 88%")
        prospect3.setStyleSheet("color: #7B9DB8; font-size: 10px; font-weight: bold; padding-left: 12px;")

        round1_layout.addWidget(round1_title)
        round1_layout.addWidget(top3_label)
        round1_layout.addWidget(prospect1)
        round1_layout.addWidget(prospect2)
        round1_layout.addWidget(prospect3)

        layout.addWidget(round1_frame)

        # Round 2 prospects
        round2_frame = QFrame()
        round2_frame.setFrameShape(QFrame.Box)
        round2_frame.setStyleSheet("QFrame { background-color: white; padding: 8px; border-left: 4px solid #8FA8A3; }")
        round2_layout = QVBoxLayout(round2_frame)
        round2_layout.setSpacing(4)

        round2_title = QLabel("Round 2 (Pick #46): Linebacker or BPA")
        round2_title.setStyleSheet("font-weight: bold; font-size: 11px; color: #2C3E50;")

        round2_note = QLabel("Scouting report available closer to draft")
        round2_note.setStyleSheet("color: #6C757D; font-size: 9px; font-style: italic;")

        round2_layout.addWidget(round2_title)
        round2_layout.addWidget(round2_note)

        layout.addWidget(round2_frame)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        view_board_btn = QPushButton("View Full Draft Board")
        view_board_btn.setStyleSheet("""
            QPushButton {
                background-color: #6B8FA8;
                color: white;
                padding: 8px 14px;
                border: none;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #5A7D92;
            }
        """)

        mock_draft_btn = QPushButton("Run Mock Draft")
        mock_draft_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #6B8FA8;
                padding: 8px 14px;
                border: 1px solid #6B8FA8;
                border-radius: 3px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #E8EFF5;
            }
        """)

        btn_layout.addWidget(view_board_btn)
        btn_layout.addWidget(mock_draft_btn)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        layout.addStretch()

        return group

    def _create_staff_recommendations_feed(self) -> QGroupBox:
        """Create staff recommendations feed with advisor timeline."""
        group = QGroupBox("💬 Staff Recommendations Feed")
        group.setStyleSheet("QGroupBox { font-weight: bold; background-color: #F8F9FA; }")
        layout = QVBoxLayout(group)

        # Recommendations list
        feed_list = QListWidget()
        feed_list.setMaximumHeight(220)
        feed_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #E0E4E8;
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #F0F2F4;
                color: #2C3E50;
            }
            QListWidget::item:hover {
                background-color: #F8F9FA;
            }
        """)

        # Staff recommendations (forward-looking advice)
        recommendations = [
            ("Mar 1", "GM", "Begin extension talks with J. Kelce before FA opens"),
            ("Feb 28", "OC", "QB needs better pass protection - OL is top priority"),
            ("Feb 25", "DC", "Consider re-signing F. Cox on 1-year vet deal"),
            ("Feb 22", "Scout", "OL class is deep in draft, could wait until Round 2"),
            ("Feb 20", "GM", "Target Q. Nelson in FA if cap space allows"),
            ("Feb 18", "DC", "Need edge rusher depth - evaluate UFA market"),
        ]

        for date, source, message in recommendations:
            item_text = f"{date} | {source}: {message}"
            feed_list.addItem(item_text)

        layout.addWidget(feed_list)

        # Note about feed purpose
        feed_note = QLabel("Timeline of staff recommendations and strategic advice")
        feed_note.setStyleSheet("color: #6C757D; font-size: 9px; font-style: italic; margin-top: 4px;")
        layout.addWidget(feed_note)

        return group

    def _create_free_agents_tab(self) -> QWidget:
        """Create free agents tab with player list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Filter bar
        filter_layout = QHBoxLayout()

        # Position filter
        position_label = QLabel("Position:")
        self.fa_position_filter = QComboBox()
        self.fa_position_filter.addItems([
            "All Positions", "QB", "RB", "WR", "TE", "OL",
            "DL", "LB", "DB", "K", "P"
        ])
        self.fa_position_filter.currentTextChanged.connect(self._filter_free_agents)

        # Search box
        search_label = QLabel("Search:")
        self.fa_search_box = QLineEdit()
        self.fa_search_box.setPlaceholderText("Player name...")
        self.fa_search_box.textChanged.connect(self._filter_free_agents)

        filter_layout.addWidget(position_label)
        filter_layout.addWidget(self.fa_position_filter)
        filter_layout.addWidget(search_label)
        filter_layout.addWidget(self.fa_search_box)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Free agents table
        self.fa_table = QTableView()
        self.fa_model = RosterTableModel(self)
        self.fa_table.setModel(self.fa_model)
        self.fa_table.setAlternatingRowColors(True)
        self.fa_table.setSelectionBehavior(QTableView.SelectRows)
        self.fa_table.setSortingEnabled(True)

        layout.addWidget(self.fa_table)

        # Action buttons (placeholders)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.sign_player_btn = QPushButton("Sign Player")
        self.sign_player_btn.setToolTip("Contract signing coming in Phase 4")
        self.sign_player_btn.setEnabled(False)  # Placeholder
        button_layout.addWidget(self.sign_player_btn)

        layout.addLayout(button_layout)

        # Load free agents
        self._load_free_agents()

        return widget

    def _create_draft_tab(self) -> QWidget:
        """Create draft tab with draft prospects list."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header = QLabel("Draft Prospects")
        header.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(header)

        # Create table view
        from PySide6.QtWidgets import QHeaderView
        from PySide6.QtGui import QStandardItemModel, QStandardItem
        from PySide6.QtCore import Qt as QtCore

        self.draft_table = QTableView()
        self.draft_table.setAlternatingRowColors(True)
        self.draft_table.setSelectionBehavior(QTableView.SelectRows)
        self.draft_table.setSelectionMode(QTableView.SingleSelection)
        self.draft_table.setEditTriggers(QTableView.NoEditTriggers)

        # Create model
        self.draft_model = QStandardItemModel()
        self.draft_model.setHorizontalHeaderLabels([
            "Name", "Position", "Overall", "College", "Round", "Pick"
        ])
        self.draft_table.setModel(self.draft_model)

        # Configure headers
        header = self.draft_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Name stretches
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)

        self.draft_table.setColumnWidth(1, 80)   # Position
        self.draft_table.setColumnWidth(2, 80)   # Overall
        self.draft_table.setColumnWidth(4, 80)   # Round
        self.draft_table.setColumnWidth(5, 80)   # Pick

        layout.addWidget(self.draft_table)

        # Load button
        load_button = QPushButton("Refresh Draft Class")
        load_button.clicked.connect(self._load_draft_prospects)
        layout.addWidget(load_button)

        # Load prospects on creation
        self._load_draft_prospects()

        return widget

    def _load_free_agents(self):
        """Load free agents from database."""
        try:
            free_agents = self.controller.get_free_agents()
            self.fa_model.set_roster(free_agents)
            self.fa_table.viewport().update()
        except Exception as e:
            print(f"Error loading free agents: {e}")

    def _filter_free_agents(self):
        """Filter free agents table (placeholder)."""
        # TODO: Implement filtering logic
        pass

    def _load_draft_prospects(self):
        """Load draft prospects from database."""
        try:
            from PySide6.QtGui import QStandardItem
            from PySide6.QtCore import Qt as QtCore

            # Clear existing data
            self.draft_model.removeRows(0, self.draft_model.rowCount())

            # Get prospects from database
            prospects = self.draft_api.get_all_prospects(
                dynasty_id=self.dynasty_id,
                season=self.season,
                available_only=True  # Only show undrafted prospects
            )

            if not prospects:
                # No draft class generated yet - show message
                row = [
                    QStandardItem("No draft class generated"),
                    QStandardItem(""),
                    QStandardItem(""),
                    QStandardItem(""),
                    QStandardItem(""),
                    QStandardItem("")
                ]
                self.draft_model.appendRow(row)
                return

            # Populate table with prospect data
            for prospect in prospects:
                # Format name
                name = f"{prospect.get('first_name', '')} {prospect.get('last_name', '')}"

                # Create row items
                row = [
                    QStandardItem(name),
                    QStandardItem(prospect.get('position', '')),
                    QStandardItem(str(prospect.get('overall', 0))),
                    QStandardItem(prospect.get('college', '')),
                    QStandardItem(str(prospect.get('draft_round', ''))),
                    QStandardItem(str(prospect.get('draft_pick', '')))
                ]

                # Center align numeric columns
                for i in [2, 4, 5]:  # Overall, Round, Pick
                    row[i].setTextAlignment(QtCore.AlignmentFlag.AlignCenter)

                self.draft_model.appendRow(row)

            print(f"[DEBUG OffseasonView] Loaded {len(prospects)} draft prospects")

        except Exception as e:
            print(f"Error loading draft prospects: {e}")
            import traceback
            traceback.print_exc()
