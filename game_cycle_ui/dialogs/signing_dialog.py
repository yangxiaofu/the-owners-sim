"""
Signing Dialog - Shows player preferences before signing.

Displays detailed persona information, preference weights, team fit analysis,
and concerns to help users make informed signing decisions.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QFrame, QGridLayout, QGroupBox, QWidget
)
from PySide6.QtCore import Qt

from game_cycle_ui.theme import (
    Colors, PRIMARY_BUTTON_STYLE, NEUTRAL_BUTTON_STYLE,
    Typography, FontSizes, TextColors
)
from game_cycle_ui.widgets import (
    ValuationBreakdownWidget,
    CollapsibleSection,
)

if TYPE_CHECKING:
    from contract_valuation.models import ValuationResult


class SigningDialog(QDialog):
    """Dialog showing player preferences before signing."""

    def __init__(
        self,
        parent: QWidget,
        player_info: Dict[str, Any],
        interest_data: Dict[str, Any],
        persona_data: Dict[str, Any],
        team_name: str,
        valuation_result: Optional["ValuationResult"] = None
    ):
        """
        Initialize the signing dialog.

        Args:
            parent: Parent widget
            player_info: Player details (name, position, overall)
            interest_data: Interest evaluation results
            persona_data: Full persona preference weights
            team_name: User's team name
            valuation_result: Optional contract valuation breakdown for transparency
        """
        super().__init__(parent)
        self.setWindowTitle(f"Sign {player_info.get('name', 'Player')}?")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setMinimumHeight(500)

        self._player_info = player_info
        self._interest_data = interest_data
        self._persona_data = persona_data
        self._team_name = team_name
        self._valuation_result = valuation_result

        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Header: Player Info
        header = self._create_header()
        layout.addWidget(header)

        # Persona Type Section
        persona_group = self._create_persona_section()
        layout.addWidget(persona_group)

        # Preference Weights Section
        prefs_group = self._create_preferences_section()
        layout.addWidget(prefs_group)

        # Team Fit Analysis
        fit_group = self._create_fit_section()
        layout.addWidget(fit_group)

        # Concerns Section
        concerns_group = self._create_concerns_section()
        layout.addWidget(concerns_group)

        # Contract Valuation Section (if available)
        if self._valuation_result is not None:
            valuation_section = self._create_valuation_section()
            layout.addWidget(valuation_section)

        # Acceptance Probability Bar
        prob_widget = self._create_probability_bar()
        layout.addWidget(prob_widget)

        # Buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)

    def _create_header(self) -> QFrame:
        """Create player header with name, position, overall."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px; padding: 8px;")
        layout = QHBoxLayout(frame)

        name = self._player_info.get("name", "Unknown Player")
        position = self._player_info.get("position", "")
        overall = self._player_info.get("overall", 0)

        name_label = QLabel(f"<b>{name}</b>")
        name_label.setFont(Typography.H5)

        pos_ovr = QLabel(f"{position} | OVR: {overall}")
        pos_ovr.setStyleSheet(f"color: {Colors.MUTED};")

        layout.addWidget(name_label)
        layout.addStretch()
        layout.addWidget(pos_ovr)

        return frame

    def _create_persona_section(self) -> QGroupBox:
        """Show persona type with description."""
        group = QGroupBox("Player Personality")
        layout = QVBoxLayout(group)

        persona_type = self._persona_data.get("persona_type", "unknown")
        hint = self._get_persona_hint(persona_type)

        type_label = QLabel(f"<b>{persona_type.replace('_', ' ').title()}</b>")
        type_label.setFont(Typography.CAPTION_BOLD)
        layout.addWidget(type_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic;")
            layout.addWidget(hint_label)

        return group

    def _create_preferences_section(self) -> QGroupBox:
        """Show preference weights as progress bars."""
        group = QGroupBox("What Matters to This Player")
        layout = QGridLayout(group)
        layout.setSpacing(8)

        preferences = [
            ("Money", self._persona_data.get("money_importance", 50)),
            ("Winning", self._persona_data.get("winning_importance", 50)),
            ("Location", self._persona_data.get("location_importance", 50)),
            ("Playing Time", self._persona_data.get("playing_time_importance", 50)),
            ("Loyalty", self._persona_data.get("loyalty_importance", 50)),
            ("Market Size", self._persona_data.get("market_size_importance", 50)),
        ]

        for row, (name, value) in enumerate(preferences):
            label = QLabel(name)
            label.setMinimumWidth(90)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(value))
            bar.setTextVisible(True)
            bar.setFormat(f"{int(value)}")
            bar.setFixedHeight(18)

            # Color based on importance
            if value >= 70:
                bar.setStyleSheet(
                    "QProgressBar { border: 1px solid #ccc; border-radius: 3px; }"
                    f"QProgressBar::chunk {{ background-color: {Colors.SUCCESS}; }}"
                )
            elif value >= 40:
                bar.setStyleSheet(
                    "QProgressBar { border: 1px solid #ccc; border-radius: 3px; }"
                    f"QProgressBar::chunk {{ background-color: {Colors.INFO}; }}"
                )
            else:
                bar.setStyleSheet(
                    "QProgressBar { border: 1px solid #ccc; border-radius: 3px; }"
                    f"QProgressBar::chunk {{ background-color: {Colors.MUTED}; }}"
                )

            layout.addWidget(label, row, 0)
            layout.addWidget(bar, row, 1)

        return group

    def _create_fit_section(self) -> QGroupBox:
        """Show team fit analysis."""
        group = QGroupBox(f"Fit with {self._team_name}")
        layout = QVBoxLayout(group)

        interest_score = self._interest_data.get("interest_score", 50)
        interest_level = self._interest_data.get("interest_level", "medium")

        # Interest score bar
        score_layout = QHBoxLayout()
        score_label = QLabel("Interest Level:")
        score_label.setMinimumWidth(100)

        score_bar = QProgressBar()
        score_bar.setRange(0, 100)
        score_bar.setValue(int(interest_score))
        score_bar.setFormat(f"{int(interest_score)} - {interest_level.replace('_', ' ').title()}")
        score_bar.setFixedHeight(22)

        # Color based on interest
        if interest_score >= 80:
            color = Colors.SUCCESS
        elif interest_score >= 65:
            color = Colors.INFO
        elif interest_score >= 50:
            color = Colors.MUTED
        elif interest_score >= 35:
            color = Colors.WARNING
        else:
            color = Colors.ERROR

        score_bar.setStyleSheet(
            f"QProgressBar {{ border: 1px solid #ccc; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; }}"
        )

        score_layout.addWidget(score_label)
        score_layout.addWidget(score_bar)
        layout.addLayout(score_layout)

        return group

    def _create_concerns_section(self) -> QGroupBox:
        """Show player concerns about the team."""
        group = QGroupBox("Player Concerns")
        layout = QVBoxLayout(group)

        concerns = self._interest_data.get("concerns", [])

        if concerns:
            for concern in concerns[:4]:  # Show max 4 concerns
                concern_label = QLabel(f"• {concern}")
                concern_label.setStyleSheet(f"color: {Colors.ERROR};")
                concern_label.setWordWrap(True)
                layout.addWidget(concern_label)
        else:
            no_concerns = QLabel("No significant concerns")
            no_concerns.setStyleSheet(f"color: {Colors.SUCCESS}; font-style: italic;")
            layout.addWidget(no_concerns)

        return group

    def _create_probability_bar(self) -> QFrame:
        """Show acceptance probability."""
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("background-color: #f5f5f5; border-radius: 4px; padding: 8px;")
        layout = QVBoxLayout(frame)

        prob = self._interest_data.get("acceptance_probability", 0.5)
        prob_pct = int(prob * 100)

        label = QLabel(f"<b>Acceptance Likelihood: {prob_pct}%</b>")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(prob_pct)
        bar.setFixedHeight(24)
        bar.setTextVisible(False)

        # Color based on probability
        if prob_pct >= 70:
            color = Colors.SUCCESS
        elif prob_pct >= 50:
            color = Colors.INFO
        else:
            color = Colors.WARNING

        bar.setStyleSheet(
            f"QProgressBar {{ border: 1px solid #ccc; border-radius: 3px; }}"
            f"QProgressBar::chunk {{ background-color: {color}; }}"
        )

        layout.addWidget(bar)

        # Add suggestion text
        suggested_premium = self._interest_data.get("suggested_premium", 1.0)
        if suggested_premium > 1.0:
            premium_pct = int((suggested_premium - 1.0) * 100)
            suggestion = QLabel(f"Tip: Offer {premium_pct}% above market value to improve chances")
            suggestion.setStyleSheet(f"color: {Colors.MUTED}; font-style: italic; font-size: {FontSizes.SMALL};")
            suggestion.setAlignment(Qt.AlignCenter)
            layout.addWidget(suggestion)

        return frame

    def _create_buttons(self) -> QHBoxLayout:
        """Create Proceed/Cancel buttons."""
        layout = QHBoxLayout()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(NEUTRAL_BUTTON_STYLE)
        cancel_btn.clicked.connect(self.reject)

        proceed_btn = QPushButton("Proceed to Sign")
        proceed_btn.setDefault(True)
        proceed_btn.setStyleSheet(PRIMARY_BUTTON_STYLE)
        proceed_btn.clicked.connect(self.accept)

        layout.addStretch()
        layout.addWidget(cancel_btn)
        layout.addWidget(proceed_btn)

        return layout

    def _create_valuation_section(self) -> QFrame:
        """Create collapsible section showing contract valuation breakdown."""
        container = QFrame()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        section = CollapsibleSection("Contract Valuation Details", expanded=False)
        widget = ValuationBreakdownWidget()
        widget.set_valuation_result(self._valuation_result)
        section.content_layout().addWidget(widget)
        layout.addWidget(section)

        return container

    def _get_persona_hint(self, persona_type: str) -> str:
        """Get user-friendly description for persona type."""
        hints = {
            "ring_chaser": "Prioritizes winning championships over money",
            "hometown_hero": "Strongly prefers playing near birthplace or college",
            "money_first": "Follows the highest bidder",
            "big_market": "Wants exposure in major media markets",
            "small_market": "Prefers quieter, smaller market teams",
            "legacy_builder": "Values long-term loyalty to one franchise",
            "competitor": "Needs significant playing time to be happy",
            "system_fit": "Values coaching scheme compatibility"
        }
        return hints.get(persona_type.lower(), "Balanced approach to free agency")
