"""
Transaction Debug Report Formatter

Formats transaction debug data into beautiful, readable console reports.
Shows complete visibility into AI transaction decision-making process.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class DebugReportFormatter:
    """Formats transaction debug data into console reports with color coding."""

    # ANSI color codes for terminal output
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'green': '\033[92m',
        'red': '\033[91m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'gray': '\033[90m'
    }

    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.

        Args:
            use_colors: Whether to use ANSI color codes (disable for log files)
        """
        self.use_colors = use_colors

    def _color(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        if not self.use_colors:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def format_daily_report(self, debug_data: Dict[str, Any]) -> str:
        """
        Format complete daily transaction report.

        Args:
            debug_data: Complete debug data for a single day

        Returns:
            Formatted report string
        """
        lines = []

        # Header
        lines.append(self._format_header(debug_data))
        lines.append("")

        # Probability evaluation section
        lines.append(self._format_probability_section(debug_data))
        lines.append("")

        # Proposal generation section
        lines.append(self._format_proposal_section(debug_data))
        lines.append("")

        # Daily summary
        lines.append(self._format_summary(debug_data))

        return "\n".join(lines)

    def _format_header(self, debug_data: Dict[str, Any]) -> str:
        """Format report header."""
        lines = []
        lines.append(self._color("═" * 80, 'cyan'))
        lines.append(self._color("TRANSACTION DEBUG REPORT".center(80), 'bold'))
        lines.append(self._color(f"Date: {debug_data.get('date', 'Unknown')}".center(80), 'white'))
        phase = debug_data.get('phase', 'UNKNOWN')
        week = debug_data.get('week', '?')
        lines.append(self._color(f"Phase: {phase} Week {week}".center(80), 'white'))
        lines.append(self._color("═" * 80, 'cyan'))
        return "\n".join(lines)

    def _format_probability_section(self, debug_data: Dict[str, Any]) -> str:
        """Format probability evaluation section showing all 32 teams."""
        lines = []
        lines.append(self._color("PROBABILITY EVALUATION (32 teams)", 'bold'))
        lines.append(self._color("─" * 80, 'gray'))

        teams_data = debug_data.get('teams_evaluated', [])

        # Show evaluated teams first, then skipped teams
        evaluated_teams = [t for t in teams_data if t.get('probability_check', {}).get('decision') == 'EVALUATE']
        skipped_teams = [t for t in teams_data if t.get('probability_check', {}).get('decision') != 'EVALUATE']

        # Evaluated teams (verbose)
        for team_data in evaluated_teams:
            lines.append(self._format_team_probability(team_data, verbose=True))

        # Skipped teams (compact)
        if len(skipped_teams) > 0:
            lines.append("")
            lines.append(self._color(f"[{len(skipped_teams)} teams skipped - probability check failed]", 'gray'))
            for team_data in skipped_teams[:5]:  # Show first 5 as examples
                lines.append(self._format_team_probability(team_data, verbose=False))

            if len(skipped_teams) > 5:
                lines.append(self._color(f"  ... and {len(skipped_teams) - 5} more teams skipped", 'gray'))

        return "\n".join(lines)

    def _format_team_probability(self, team_data: Dict[str, Any], verbose: bool = True) -> str:
        """Format a single team's probability evaluation."""
        lines = []
        team_id = team_data.get('team_id', '?')
        team_name = team_data.get('team_name', f'Team {team_id}')
        prob_check = team_data.get('probability_check', {})

        decision = prob_check.get('decision', 'UNKNOWN')

        if decision == 'EVALUATE':
            symbol = self._color("✓", 'green')
            status = self._color("EVALUATED", 'green')
        else:
            symbol = self._color("✗", 'red')
            status = self._color("SKIPPED", 'red')

        lines.append(f"\n{symbol} TEAM {team_id} ({team_name}): {status}")

        if verbose:
            # Show detailed breakdown
            base_prob = prob_check.get('base_prob', 0)
            final_prob = prob_check.get('final_prob', 0)
            random_roll = prob_check.get('random_roll', 0)

            lines.append(f"  Base Probability: {self._color(f'{base_prob:.3f}', 'yellow')}")

            # Show modifiers
            modifiers = prob_check.get('modifiers', {})
            if modifiers:
                lines.append(f"  Modifiers Applied:")
                for mod_name, mod_data in modifiers.items():
                    if mod_data.get('applied', False):
                        value = mod_data.get('value', 1.0)
                        reason = mod_data.get('reason', '')
                        lines.append(f"    • {mod_name}: {self._color(f'{value:.2f}×', 'yellow')} ({reason})")

            lines.append(f"  Final Probability: {self._color(f'{final_prob:.3f}', 'yellow')}")
            lines.append(f"  Random Roll: {self._color(f'{random_roll:.3f}', 'cyan')} → {status}")

            reason = prob_check.get('reason', '')
            if reason:
                lines.append(f"  {self._color(f'Reason: {reason}', 'gray')}")
        else:
            # Compact format for skipped teams
            final_prob = prob_check.get('final_prob', 0)
            random_roll = prob_check.get('random_roll', 0)
            lines.append(f"  Prob: {final_prob:.2f} | Roll: {random_roll:.2f} → {status}")

        return "\n".join(lines)

    def _format_proposal_section(self, debug_data: Dict[str, Any]) -> str:
        """Format proposal generation section."""
        lines = []
        lines.append(self._color("PROPOSAL GENERATION", 'bold'))
        lines.append(self._color("─" * 80, 'gray'))

        teams_data = debug_data.get('teams_evaluated', [])
        evaluated_teams = [t for t in teams_data if t.get('probability_check', {}).get('decision') == 'EVALUATE']

        if len(evaluated_teams) == 0:
            lines.append(self._color("  No teams evaluated today (all probability checks failed)", 'gray'))
            return "\n".join(lines)

        lines.append(self._color(f"  {len(evaluated_teams)} teams evaluated", 'white'))
        lines.append("")

        for team_data in evaluated_teams:
            lines.append(self._format_team_proposals(team_data))

        return "\n".join(lines)

    def _format_team_proposals(self, team_data: Dict[str, Any]) -> str:
        """Format a single team's proposal generation."""
        lines = []
        team_id = team_data.get('team_id', '?')
        team_name = team_data.get('team_name', f'Team {team_id}')

        proposals_generated = team_data.get('proposals_generated', 0)
        proposals_accepted = team_data.get('proposals_accepted', 0)

        lines.append(self._color(f"TEAM {team_id} ({team_name}): ", 'bold') +
                    f"{proposals_generated} proposals generated, " +
                    self._color(f"{proposals_accepted} accepted", 'green' if proposals_accepted > 0 else 'gray'))

        proposals = team_data.get('proposals', [])

        if len(proposals) == 0:
            lines.append(self._color("  No proposals generated (no viable targets or assets)", 'gray'))
            return "\n".join(lines)

        for idx, proposal in enumerate(proposals, 1):
            lines.append(self._format_single_proposal(proposal, idx))

        return "\n".join(lines)

    def _format_single_proposal(self, proposal: Dict[str, Any], index: int) -> str:
        """Format a single trade proposal."""
        lines = []

        final_status = proposal.get('final_status', 'UNKNOWN')

        if final_status == 'ACCEPTED':
            status_color = 'green'
            status_symbol = '✓'
        else:
            status_color = 'red'
            status_symbol = '✗'

        lines.append(f"\n  Proposal #{index}: {self._color(final_status, status_color)} {status_symbol}")

        # Target player info
        target = proposal.get('target_player', 'Unknown')
        target_value = proposal.get('target_value', 0)
        lines.append(f"    Target: {self._color(target, 'cyan')} (Value: {target_value})")

        # Assets offered
        assets = proposal.get('assets_offered', [])
        total_value = proposal.get('total_value', 0)
        if assets:
            assets_str = ", ".join(assets)
            lines.append(f"    Offering: {assets_str}")
        lines.append(f"    Total Value: {total_value}")

        # Fairness ratio
        fairness_ratio = proposal.get('fairness_ratio', 0)
        ratio_color = 'green' if 0.90 <= fairness_ratio <= 1.10 else 'yellow'
        lines.append(f"    Fairness Ratio: {self._color(f'{fairness_ratio:.2f}', ratio_color)}")

        # Filter results
        filter_results = proposal.get('filter_results', {})
        if filter_results:
            lines.append(f"    Filters:")
            for filter_name, result in filter_results.items():
                if result == 'PASS':
                    lines.append(f"      • {filter_name}: {self._color('PASS', 'green')} ✓")
                elif result == 'FAIL':
                    lines.append(f"      • {filter_name}: {self._color('FAIL', 'red')} ✗")
                else:
                    lines.append(f"      • {filter_name}: {self._color(result, 'gray')}")

        # Rejection reason
        if final_status != 'ACCEPTED':
            rejection_reason = proposal.get('rejection_reason', 'Unknown')
            lines.append(f"    {self._color(f'Rejection: {rejection_reason}', 'red')}")

        return "\n".join(lines)

    def _format_summary(self, debug_data: Dict[str, Any]) -> str:
        """Format daily summary section."""
        lines = []
        lines.append(self._color("DAILY SUMMARY", 'bold'))
        lines.append(self._color("─" * 80, 'gray'))

        teams_data = debug_data.get('teams_evaluated', [])
        evaluated_count = len([t for t in teams_data if t.get('probability_check', {}).get('decision') == 'EVALUATE'])

        total_proposals = sum(t.get('proposals_generated', 0) for t in teams_data)
        total_accepted = sum(t.get('proposals_accepted', 0) for t in teams_data)
        total_rejected = total_proposals - total_accepted

        lines.append(f"Teams Evaluated: {self._color(f'{evaluated_count}/32', 'cyan')} ({evaluated_count/32*100:.1f}%)")
        lines.append(f"Total Proposals Generated: {self._color(str(total_proposals), 'yellow')}")
        lines.append(f"Proposals Accepted: {self._color(str(total_accepted), 'green')}")
        lines.append(f"Proposals Rejected: {self._color(str(total_rejected), 'red')}")

        # Rejection breakdown
        if total_rejected > 0:
            lines.append("")
            lines.append("Rejection Reasons:")
            rejection_counts = {}
            for team_data in teams_data:
                for proposal in team_data.get('proposals', []):
                    if proposal.get('final_status') != 'ACCEPTED':
                        reason = proposal.get('rejection_reason', 'Unknown')
                        rejection_counts[reason] = rejection_counts.get(reason, 0) + 1

            for reason, count in sorted(rejection_counts.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  • {reason}: {count}")

        lines.append(self._color("═" * 80, 'cyan'))

        return "\n".join(lines)

    def format_multi_day_summary(self, all_debug_data: List[Dict[str, Any]]) -> str:
        """
        Format multi-day summary report.

        Args:
            all_debug_data: List of debug data dicts, one per day

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append(self._color("═" * 80, 'cyan'))
        lines.append(self._color("MULTI-DAY TRANSACTION SUMMARY".center(80), 'bold'))
        lines.append(self._color(f"{len(all_debug_data)} Days Simulated".center(80), 'white'))
        lines.append(self._color("═" * 80, 'cyan'))
        lines.append("")

        # Aggregate statistics
        total_evaluated = 0
        total_proposals = 0
        total_accepted = 0

        for day_data in all_debug_data:
            teams_data = day_data.get('teams_evaluated', [])
            evaluated_count = len([t for t in teams_data if t.get('probability_check', {}).get('decision') == 'EVALUATE'])
            total_evaluated += evaluated_count
            total_proposals += sum(t.get('proposals_generated', 0) for t in teams_data)
            total_accepted += sum(t.get('proposals_accepted', 0) for t in teams_data)

        avg_evaluated = total_evaluated / len(all_debug_data) if all_debug_data else 0
        avg_proposals = total_proposals / len(all_debug_data) if all_debug_data else 0
        avg_accepted = total_accepted / len(all_debug_data) if all_debug_data else 0

        lines.append(f"Average Teams Evaluated per Day: {self._color(f'{avg_evaluated:.1f}', 'cyan')}")
        lines.append(f"Average Proposals per Day: {self._color(f'{avg_proposals:.1f}', 'yellow')}")
        lines.append(f"Average Accepted per Day: {self._color(f'{avg_accepted:.1f}', 'green')}")
        lines.append(f"Total Trades Executed: {self._color(str(total_accepted), 'green')}")
        lines.append("")

        # Day-by-day breakdown
        lines.append(self._color("Day-by-Day Breakdown:", 'bold'))
        lines.append("")
        for idx, day_data in enumerate(all_debug_data, 1):
            teams_data = day_data.get('teams_evaluated', [])
            evaluated_count = len([t for t in teams_data if t.get('probability_check', {}).get('decision') == 'EVALUATE'])
            proposals_count = sum(t.get('proposals_generated', 0) for t in teams_data)
            accepted_count = sum(t.get('proposals_accepted', 0) for t in teams_data)

            date = day_data.get('date', f'Day {idx}')
            lines.append(f"  {date}: {evaluated_count} teams → {proposals_count} proposals → {self._color(f'{accepted_count} trades', 'green' if accepted_count > 0 else 'gray')}")

        lines.append("")
        lines.append(self._color("═" * 80, 'cyan'))

        return "\n".join(lines)
