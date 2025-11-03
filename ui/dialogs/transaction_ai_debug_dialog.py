"""
Transaction AI Debug Dialog

Modal dialog for displaying comprehensive transaction AI activity logs.
Shows probability calculations, proposal generation details, and filter results
for all 32 teams.
"""

from typing import Dict, List, Any, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QComboBox, QLabel, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class TransactionAIDebugDialog(QDialog):
    """
    Dialog for viewing transaction AI debug logs.

    Displays formatted debug data collected during daily transaction evaluation,
    including:
    - Probability calculations for all 32 teams
    - Proposal generation attempts and results
    - Filter pass/fail status (GM personality, validation, cap compliance)
    - Daily summary with aggregate statistics
    """

    def __init__(self, debug_data: List[Dict[str, Any]], parent=None):
        """
        Initialize debug dialog.

        Args:
            debug_data: List of debug data dicts from TransactionAIManager._debug_data
            parent: Parent widget
        """
        super().__init__(parent)

        self.debug_data = debug_data
        self.setWindowTitle("Transaction AI Activity Log")
        self.setModal(True)
        self.resize(1200, 800)

        self._setup_ui()
        self._display_debug_data()

    def _setup_ui(self):
        """Setup dialog UI."""
        layout = QVBoxLayout()

        # Header with filter controls
        header_layout = QHBoxLayout()

        # Filter dropdown
        filter_label = QLabel("View:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Teams (Detailed)",
            "Evaluated Teams Only",
            "Proposals Generated",
            "Summary Only"
        ])
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)

        header_layout.addWidget(filter_label)
        header_layout.addWidget(self.filter_combo)
        header_layout.addStretch()

        # Export button
        export_btn = QPushButton("Export to HTML")
        export_btn.clicked.connect(self._export_to_html)
        header_layout.addWidget(export_btn)

        layout.addLayout(header_layout)

        # Text display area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("Courier", 10))  # Monospace for alignment
        layout.addWidget(self.text_display)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _display_debug_data(self):
        """Display formatted debug data."""
        filter_mode = self.filter_combo.currentText()

        if not self.debug_data:
            self.text_display.setHtml("<p>No transaction AI activity recorded yet.</p>")
            return

        # Format data based on filter
        if filter_mode == "Summary Only":
            html = self._format_summary_only()
        elif filter_mode == "Proposals Generated":
            html = self._format_proposals_only()
        elif filter_mode == "Evaluated Teams Only":
            html = self._format_evaluated_only()
        else:  # "All Teams (Detailed)"
            html = self._format_full_report()

        self.text_display.setHtml(html)

    def _format_full_report(self) -> str:
        """Format complete debug report with all teams."""
        html = []

        # Header
        html.append(self._get_css())
        html.append('<div class="header">')
        html.append('<h2>Transaction AI Activity Log</h2>')
        html.append('<p class="meta">Complete debug trace for all 32 teams</p>')
        html.append('</div>')

        # Process each team's debug data
        evaluated_teams = []
        skipped_teams = []

        for team_data in self.debug_data:
            prob_check = team_data.get('probability_check', {})
            decision = prob_check.get('decision', 'UNKNOWN')

            if decision == 'EVALUATE':
                evaluated_teams.append(team_data)
            else:
                skipped_teams.append(team_data)

        # Summary section
        html.append(self._format_summary_section(evaluated_teams, skipped_teams))

        # Evaluated teams (detailed)
        if evaluated_teams:
            html.append('<h3 class="section-header">Teams Evaluated ({} teams)</h3>'.format(len(evaluated_teams)))
            for team_data in evaluated_teams:
                html.append(self._format_team_detailed(team_data))

        # Skipped teams (compact)
        if skipped_teams:
            html.append('<h3 class="section-header">Teams Skipped ({} teams)</h3>'.format(len(skipped_teams)))
            html.append('<p class="note">Probability check failed - no trades evaluated</p>')
            for team_data in skipped_teams[:5]:  # Show first 5 as examples
                html.append(self._format_team_compact(team_data))

            if len(skipped_teams) > 5:
                html.append('<p class="note">... and {} more teams skipped</p>'.format(len(skipped_teams) - 5))

        return ''.join(html)

    def _format_evaluated_only(self) -> str:
        """Format report showing only evaluated teams."""
        html = []

        html.append(self._get_css())
        html.append('<div class="header">')
        html.append('<h2>Transaction AI Activity Log</h2>')
        html.append('<p class="meta">Evaluated teams only (probability check passed)</p>')
        html.append('</div>')

        evaluated_teams = [
            team_data for team_data in self.debug_data
            if team_data.get('probability_check', {}).get('decision') == 'EVALUATE'
        ]

        if not evaluated_teams:
            html.append('<p class="note">No teams evaluated (all probability checks failed)</p>')
            return ''.join(html)

        for team_data in evaluated_teams:
            html.append(self._format_team_detailed(team_data))

        return ''.join(html)

    def _format_proposals_only(self) -> str:
        """Format report showing only teams that generated proposals."""
        html = []

        html.append(self._get_css())
        html.append('<div class="header">')
        html.append('<h2>Transaction AI Activity Log</h2>')
        html.append('<p class="meta">Teams with trade proposals only</p>')
        html.append('</div>')

        teams_with_proposals = [
            team_data for team_data in self.debug_data
            if team_data.get('proposals_generated', 0) > 0
        ]

        if not teams_with_proposals:
            html.append('<p class="note">No trade proposals generated</p>')
            return ''.join(html)

        for team_data in teams_with_proposals:
            html.append(self._format_team_proposals(team_data))

        return ''.join(html)

    def _format_summary_only(self) -> str:
        """Format summary statistics only."""
        html = []

        html.append(self._get_css())
        html.append('<div class="header">')
        html.append('<h2>Transaction AI Activity Log - Summary</h2>')
        html.append('</div>')

        evaluated_teams = [
            t for t in self.debug_data
            if t.get('probability_check', {}).get('decision') == 'EVALUATE'
        ]
        skipped_teams = [
            t for t in self.debug_data
            if t.get('probability_check', {}).get('decision') != 'EVALUATE'
        ]

        total_proposals = sum(t.get('proposals_generated', 0) for t in self.debug_data)
        total_accepted = sum(t.get('proposals_accepted', 0) for t in self.debug_data)

        html.append('<table class="summary-table">')
        html.append('<tr><th>Metric</th><th>Value</th></tr>')
        html.append('<tr><td>Teams Evaluated</td><td class="success">{}/32 ({:.1f}%)</td></tr>'.format(
            len(evaluated_teams), len(evaluated_teams) / 32 * 100
        ))
        html.append('<tr><td>Teams Skipped</td><td class="error">{}/32 ({:.1f}%)</td></tr>'.format(
            len(skipped_teams), len(skipped_teams) / 32 * 100
        ))
        html.append('<tr><td>Total Proposals Generated</td><td class="warning">{}</td></tr>'.format(total_proposals))
        html.append('<tr><td>Proposals Accepted</td><td class="success">{}</td></tr>'.format(total_accepted))
        html.append('<tr><td>Proposals Rejected</td><td class="error">{}</td></tr>'.format(
            total_proposals - total_accepted
        ))
        html.append('</table>')

        return ''.join(html)

    def _format_summary_section(self, evaluated_teams: List[Dict], skipped_teams: List[Dict]) -> str:
        """Format summary section at top of report."""
        total_proposals = sum(t.get('proposals_generated', 0) for t in self.debug_data)
        total_accepted = sum(t.get('proposals_accepted', 0) for t in self.debug_data)

        html = []
        html.append('<div class="summary">')
        html.append('<h3>Daily Summary</h3>')
        html.append('<table class="summary-table">')
        html.append('<tr><th>Metric</th><th>Value</th></tr>')
        html.append('<tr><td>Teams Evaluated</td><td class="success">{}/32</td></tr>'.format(len(evaluated_teams)))
        html.append('<tr><td>Teams Skipped</td><td class="neutral">{}/32</td></tr>'.format(len(skipped_teams)))
        html.append('<tr><td>Total Proposals</td><td class="warning">{}</td></tr>'.format(total_proposals))
        html.append('<tr><td>Accepted</td><td class="success">{}</td></tr>'.format(total_accepted))
        html.append('<tr><td>Rejected</td><td class="error">{}</td></tr>'.format(total_proposals - total_accepted))
        html.append('</table>')
        html.append('</div>')
        return ''.join(html)

    def _format_team_detailed(self, team_data: Dict[str, Any]) -> str:
        """Format detailed view of evaluated team."""
        team_id = team_data.get('team_id', '?')
        team_name = team_data.get('team_name', f'Team {team_id}')
        prob_check = team_data.get('probability_check', {})

        html = []
        html.append('<div class="team-card evaluated">')
        html.append('<h4 class="team-header">✓ Team {} ({}): EVALUATED</h4>'.format(team_id, team_name))

        # Probability details
        base_prob = prob_check.get('base_prob', 0)
        final_prob = prob_check.get('final_prob', 0)
        random_roll = prob_check.get('random_roll', 0)

        html.append('<div class="probability-section">')
        html.append('<p><strong>Probability Calculation:</strong></p>')
        html.append('<ul>')
        html.append('<li>Base Probability: <span class="warning">{:.3f}</span></li>'.format(base_prob))

        # Modifiers
        modifiers = prob_check.get('modifiers', {})
        for mod_name, mod_data in modifiers.items():
            if mod_data.get('applied', False):
                value = mod_data.get('value', 1.0)
                reason = mod_data.get('reason', '')
                html.append('<li>{}: <span class="warning">{:.2f}×</span> ({})</li>'.format(
                    mod_name.replace('_', ' ').title(), value, reason
                ))

        html.append('<li>Final Probability: <span class="warning">{:.3f}</span></li>'.format(final_prob))
        html.append('<li>Random Roll: <span class="info">{:.3f}</span> → <span class="success">EVALUATE</span></li>'.format(random_roll))
        html.append('</ul>')
        html.append('</div>')

        # Proposals
        proposals_generated = team_data.get('proposals_generated', 0)
        proposals_accepted = team_data.get('proposals_accepted', 0)

        if proposals_generated > 0:
            html.append('<div class="proposals-section">')
            html.append('<p><strong>Proposals:</strong> {} generated, {} accepted</p>'.format(
                proposals_generated, proposals_accepted
            ))
            html.append('</div>')
        else:
            early_exit = team_data.get('early_exit_reason', 'Unknown reason')
            html.append('<div class="proposals-section">')
            html.append('<p><strong>No proposals generated:</strong> {}</p>'.format(early_exit))
            html.append('</div>')

        html.append('</div>')
        return ''.join(html)

    def _format_team_compact(self, team_data: Dict[str, Any]) -> str:
        """Format compact view of skipped team."""
        team_id = team_data.get('team_id', '?')
        team_name = team_data.get('team_name', f'Team {team_id}')
        prob_check = team_data.get('probability_check', {})
        final_prob = prob_check.get('final_prob', 0)
        random_roll = prob_check.get('random_roll', 0)

        html = []
        html.append('<div class="team-card skipped">')
        html.append('<p class="team-compact">✗ Team {} ({}): SKIPPED - Prob: {:.3f} | Roll: {:.3f}</p>'.format(
            team_id, team_name, final_prob, random_roll
        ))
        html.append('</div>')
        return ''.join(html)

    def _format_team_proposals(self, team_data: Dict[str, Any]) -> str:
        """Format team view focusing on proposals."""
        team_id = team_data.get('team_id', '?')
        team_name = team_data.get('team_name', f'Team {team_id}')
        proposals_generated = team_data.get('proposals_generated', 0)
        proposals_accepted = team_data.get('proposals_accepted', 0)

        html = []
        html.append('<div class="team-card proposals">')
        html.append('<h4 class="team-header">Team {} ({}): {} Proposals ({} Accepted)</h4>'.format(
            team_id, team_name, proposals_generated, proposals_accepted
        ))

        # Show proposal details if available
        proposal_generation = team_data.get('proposal_generation', {})
        if proposal_generation:
            targets = proposal_generation.get('potential_targets', [])
            if targets:
                html.append('<p><strong>Targets Considered:</strong></p>')
                html.append('<ul>')
                for target in targets[:5]:  # Show first 5
                    html.append('<li>{} - {} (OVR: {}, Value: {})</li>'.format(
                        target.get('player_name', 'Unknown'),
                        target.get('position', '?'),
                        target.get('overall', '?'),
                        target.get('value', '?')
                    ))
                html.append('</ul>')

        html.append('</div>')
        return ''.join(html)

    def _get_css(self) -> str:
        """Get CSS stylesheet for HTML formatting."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #1e1e1e;
                color: #d4d4d4;
                margin: 10px;
                padding: 0;
            }
            .header {
                background-color: #2d2d30;
                padding: 15px;
                margin-bottom: 20px;
                border-left: 4px solid #007acc;
            }
            .header h2 {
                margin: 0 0 5px 0;
                color: #ffffff;
            }
            .header .meta {
                margin: 0;
                color: #858585;
                font-size: 0.9em;
            }
            .summary {
                background-color: #252526;
                padding: 15px;
                margin-bottom: 20px;
                border: 1px solid #3e3e42;
            }
            .summary h3 {
                margin-top: 0;
                color: #ffffff;
            }
            .summary-table {
                width: 100%;
                border-collapse: collapse;
            }
            .summary-table th {
                background-color: #2d2d30;
                color: #ffffff;
                text-align: left;
                padding: 8px;
                border: 1px solid #3e3e42;
            }
            .summary-table td {
                padding: 8px;
                border: 1px solid #3e3e42;
            }
            .section-header {
                color: #ffffff;
                margin-top: 30px;
                margin-bottom: 10px;
                padding: 5px 0;
                border-bottom: 2px solid #3e3e42;
            }
            .team-card {
                background-color: #252526;
                border: 1px solid #3e3e42;
                padding: 15px;
                margin-bottom: 15px;
                border-radius: 4px;
            }
            .team-card.evaluated {
                border-left: 4px solid #4ec9b0;
            }
            .team-card.skipped {
                border-left: 4px solid #858585;
            }
            .team-card.proposals {
                border-left: 4px solid #dcdcaa;
            }
            .team-header {
                margin: 0 0 10px 0;
                color: #ffffff;
            }
            .team-compact {
                margin: 5px 0;
                color: #858585;
            }
            .probability-section, .proposals-section {
                margin-top: 10px;
            }
            .probability-section ul, .proposals-section ul {
                margin: 5px 0;
                padding-left: 20px;
            }
            .note {
                color: #858585;
                font-style: italic;
                margin: 10px 0;
            }
            .success {
                color: #4ec9b0;
                font-weight: bold;
            }
            .error {
                color: #f48771;
                font-weight: bold;
            }
            .warning {
                color: #dcdcaa;
                font-weight: bold;
            }
            .info {
                color: #569cd6;
            }
            .neutral {
                color: #858585;
            }
        </style>
        """

    def _on_filter_changed(self):
        """Handle filter selection change."""
        self._display_debug_data()

    def _export_to_html(self):
        """Export debug log to HTML file."""
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Transaction AI Debug Log",
            f"transaction_ai_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
            "HTML Files (*.html)"
        )

        if filename:
            try:
                html_content = self.text_display.toHtml()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                QMessageBox.information(
                    self,
                    "Export Successful",
                    f"Debug log exported to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"Failed to export log:\n{str(e)}"
                )
