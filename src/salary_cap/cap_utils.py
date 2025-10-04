"""
Salary Cap Utilities

Helper functions for displaying cap information, formatting reports,
and converting between data structures.

Provides user-friendly output formatting for cap summaries, contracts,
and compliance reports.
"""

from typing import Dict, List, Any, Optional
from datetime import date


def format_currency(amount: int) -> str:
    """
    Format integer amount as currency string.

    Args:
        amount: Amount in dollars

    Returns:
        Formatted string (e.g., "$25,000,000" or "-$5,000,000")
    """
    if amount >= 0:
        return f"${amount:,}"
    else:
        return f"-${abs(amount):,}"


def format_cap_summary(cap_summary: Dict[str, Any]) -> str:
    """
    Format team cap summary for display.

    Args:
        cap_summary: Cap summary dict from CapDatabaseAPI

    Returns:
        Formatted multi-line string
    """
    if not cap_summary:
        return "No cap data available"

    lines = []
    lines.append("=" * 60)
    lines.append(f"SALARY CAP SUMMARY - Team {cap_summary['team_id']} - Season {cap_summary['season']}")
    lines.append("=" * 60)
    lines.append("")

    # Cap limits
    lines.append(f"Salary Cap Limit:      {format_currency(cap_summary['salary_cap_limit'])}")
    lines.append(f"Carryover:             {format_currency(cap_summary['carryover_from_previous'])}")
    lines.append(f"Total Available:       {format_currency(cap_summary['total_cap_available'])}")
    lines.append("")

    # Current usage
    lines.append(f"Active Contracts:      {format_currency(cap_summary['active_contracts_total'])}")
    lines.append(f"Dead Money:            {format_currency(cap_summary['dead_money_total'])}")
    lines.append(f"LTBE Incentives:       {format_currency(cap_summary['ltbe_incentives_total'])}")
    lines.append(f"Practice Squad:        {format_currency(cap_summary['practice_squad_total'])}")
    lines.append(f"Total Used:            {format_currency(cap_summary['total_cap_used'])}")
    lines.append("")

    # Available space
    cap_space = cap_summary['cap_space_available']
    compliance_status = "✓ COMPLIANT" if cap_space >= 0 else "✗ OVER CAP"

    lines.append(f"Cap Space:             {format_currency(cap_space)}  {compliance_status}")

    if cap_summary.get('is_top_51_active'):
        lines.append(f"\n(Top-51 Rule Active - Offseason Mode)")

    lines.append("=" * 60)

    return "\n".join(lines)


def format_contract_details(contract_details: Dict[str, Any]) -> str:
    """
    Format contract details for display.

    Args:
        contract_details: Contract details dict from ContractManager

    Returns:
        Formatted multi-line string
    """
    contract = contract_details['contract']
    year_details = contract_details['year_details']

    lines = []
    lines.append("=" * 80)
    lines.append(f"CONTRACT #{contract['contract_id']} - Player {contract['player_id']}")
    lines.append(f"Type: {contract['contract_type']} | Team: {contract['team_id']}")
    lines.append(f"Years: {contract['contract_years']} ({contract['start_year']}-{contract['end_year']})")
    lines.append("=" * 80)
    lines.append("")

    # Financial overview
    lines.append("FINANCIAL OVERVIEW:")
    lines.append(f"  Total Value:         {format_currency(contract['total_value'])}")
    lines.append(f"  Signing Bonus:       {format_currency(contract['signing_bonus'])}")
    lines.append(f"  Total Guaranteed:    {format_currency(contract['total_guaranteed'])}")
    lines.append(f"  Status:              {'Active' if contract['is_active'] else 'Inactive'}")
    lines.append("")

    # Year-by-year breakdown
    lines.append("YEAR-BY-YEAR BREAKDOWN:")
    lines.append(f"{'Year':<6} {'Season':<8} {'Base Salary':<15} {'Bonuses':<12} {'Cap Hit':<15} {'Cash':<15}")
    lines.append("-" * 80)

    for detail in year_details:
        year = detail['contract_year']
        season = detail['season_year']
        base = detail['base_salary']
        bonuses = (
            detail['roster_bonus'] +
            detail['workout_bonus'] +
            detail['signing_bonus_proration']
        )
        cap_hit = detail['total_cap_hit']
        cash = detail['cash_paid']

        lines.append(
            f"{year:<6} {season:<8} {format_currency(base):<15} "
            f"{format_currency(bonuses):<12} {format_currency(cap_hit):<15} "
            f"{format_currency(cash):<15}"
        )

    lines.append("")

    # Dead money projections
    if 'dead_money_projections' in contract_details:
        lines.append("DEAD MONEY IF RELEASED:")
        lines.append(f"{'Year':<8} {'Standard':<18} {'June 1 (Current)':<20} {'June 1 (Next)':<15}")
        lines.append("-" * 80)

        for season, proj in contract_details['dead_money_projections'].items():
            lines.append(
                f"{season:<8} {format_currency(proj['standard']):<18} "
                f"{format_currency(proj['june_1_current']):<20} "
                f"{format_currency(proj['june_1_next']):<15}"
            )

    lines.append("=" * 80)

    return "\n".join(lines)


def format_compliance_report(report: Dict[str, Any]) -> str:
    """
    Format compliance report for display.

    Args:
        report: Compliance report dict from CapValidator

    Returns:
        Formatted multi-line string
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"SALARY CAP COMPLIANCE REPORT")
    lines.append(f"Team: {report['team_id']} | Season: {report['season']}")
    lines.append(f"Generated: {report['generated_date']}")
    lines.append("=" * 70)
    lines.append("")

    # Cap Compliance
    cap_comp = report['cap_compliance']
    status = "✓ COMPLIANT" if cap_comp['is_compliant'] else "✗ NON-COMPLIANT"
    lines.append(f"CAP STATUS: {status}")
    lines.append(f"  {cap_comp['message']}")
    lines.append("")

    # Cap Space
    if report.get('cap_space') is not None:
        lines.append(f"Available Cap Space: {format_currency(report['cap_space'])}")
        lines.append("")

    # Violations
    if report.get('violations'):
        lines.append("VIOLATIONS:")
        for violation in report['violations']:
            lines.append(f"  [{violation['severity']}] {violation['type']}")
            lines.append(f"    {violation['message']}")
        lines.append("")

    # Warnings
    if report.get('warnings'):
        lines.append("WARNINGS:")
        for warning in report['warnings']:
            lines.append(f"  {warning['type']}: {warning['message']}")
        lines.append("")

    # Recommendations
    if report.get('recommendations'):
        lines.append("RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def format_league_compliance_report(report: Dict[str, Any]) -> str:
    """
    Format league-wide compliance report for display.

    Args:
        report: League compliance report dict from CapValidator

    Returns:
        Formatted multi-line string
    """
    lines = []
    lines.append("=" * 70)
    lines.append(f"LEAGUE-WIDE SALARY CAP COMPLIANCE REPORT")
    lines.append(f"Season: {report['season']} | Dynasty: {report['dynasty_id']}")
    lines.append(f"Generated: {report['generated_date']}")
    lines.append("=" * 70)
    lines.append("")

    # Summary statistics
    lines.append("SUMMARY:")
    lines.append(f"  Total Teams:         {report['total_teams']}")
    lines.append(f"  Compliant Teams:     {report['compliant_teams']}")
    lines.append(f"  Non-Compliant:       {len(report['non_compliant_teams'])}")
    lines.append(f"  Compliance Rate:     {report['compliance_rate']:.1f}%")
    lines.append(f"  League Cap Space:    {format_currency(report['league_total_cap_space'])}")
    lines.append("")

    # Non-compliant teams
    if report['non_compliant_teams']:
        lines.append("NON-COMPLIANT TEAMS:")
        for team_info in report['non_compliant_teams']:
            lines.append(f"  Team {team_info['team_id']}: {team_info['message']}")
        lines.append("")

    lines.append("=" * 70)

    return "\n".join(lines)


def calculate_contract_summary_stats(year_details: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculate summary statistics for a contract.

    Args:
        year_details: List of contract year detail dicts

    Returns:
        Dict with summary stats:
        - total_cap_hits: Sum of all cap hits
        - total_cash: Sum of all cash payments
        - average_cap_hit: Average annual cap hit
        - max_cap_hit: Highest single-year cap hit
        - min_cap_hit: Lowest single-year cap hit
    """
    if not year_details:
        return {
            'total_cap_hits': 0,
            'total_cash': 0,
            'average_cap_hit': 0,
            'max_cap_hit': 0,
            'min_cap_hit': 0
        }

    cap_hits = [d['total_cap_hit'] for d in year_details]
    cash_payments = [d['cash_paid'] for d in year_details]

    return {
        'total_cap_hits': sum(cap_hits),
        'total_cash': sum(cash_payments),
        'average_cap_hit': sum(cap_hits) // len(cap_hits),
        'max_cap_hit': max(cap_hits),
        'min_cap_hit': min(cap_hits),
        'years': len(year_details)
    }


def format_top_contracts(
    contracts: List[Dict[str, Any]],
    limit: int = 10
) -> str:
    """
    Format top contracts by cap hit for display.

    Args:
        contracts: List of contract dicts with year details
        limit: Number of contracts to display

    Returns:
        Formatted table string
    """
    if not contracts:
        return "No contracts found"

    lines = []
    lines.append(f"TOP {limit} CONTRACTS BY CAP HIT")
    lines.append("=" * 80)
    lines.append(f"{'Rank':<6} {'Player':<12} {'Position':<10} {'Cap Hit':<15} {'Years':<8}")
    lines.append("-" * 80)

    for i, contract in enumerate(contracts[:limit], 1):
        # This is simplified - in reality, would join with player data
        player_id = contract.get('player_id', 'Unknown')
        cap_hit = contract.get('total_cap_hit', 0)
        years = contract.get('contract_years', 0)

        lines.append(
            f"{i:<6} Player {player_id:<12} {'N/A':<10} "
            f"{format_currency(cap_hit):<15} {years:<8}"
        )

    lines.append("=" * 80)

    return "\n".join(lines)


def validate_contract_inputs(
    contract_years: int,
    total_value: int,
    signing_bonus: int,
    base_salaries: List[int]
) -> Tuple[bool, str]:
    """
    Validate contract creation inputs.

    Args:
        contract_years: Number of years
        total_value: Total contract value
        signing_bonus: Signing bonus
        base_salaries: List of base salaries

    Returns:
        Tuple of (is_valid, error_message)
    """
    if contract_years <= 0:
        return (False, "Contract must have at least 1 year")

    if contract_years > 10:
        return (False, "Contract cannot exceed 10 years")

    if total_value <= 0:
        return (False, "Total value must be positive")

    if signing_bonus < 0:
        return (False, "Signing bonus cannot be negative")

    if signing_bonus > total_value:
        return (False, "Signing bonus cannot exceed total value")

    if len(base_salaries) != contract_years:
        return (False, f"Must provide exactly {contract_years} base salaries")

    if any(salary < 0 for salary in base_salaries):
        return (False, "Base salaries cannot be negative")

    sum_base = sum(base_salaries)
    if sum_base + signing_bonus != total_value:
        return (
            False,
            f"Base salaries ({format_currency(sum_base)}) + signing bonus "
            f"({format_currency(signing_bonus)}) must equal total value "
            f"({format_currency(total_value)})"
        )

    return (True, "")


def calculate_cap_percentage(amount: int, cap_limit: int) -> float:
    """
    Calculate what percentage of the cap an amount represents.

    Args:
        amount: Dollar amount
        cap_limit: Salary cap limit

    Returns:
        Percentage (0.0 to 100.0)
    """
    if cap_limit <= 0:
        return 0.0

    return (amount / cap_limit) * 100.0


def format_cap_percentage(amount: int, cap_limit: int) -> str:
    """
    Format cap percentage for display.

    Args:
        amount: Dollar amount
        cap_limit: Salary cap limit

    Returns:
        Formatted string (e.g., "10.5% of cap")
    """
    percentage = calculate_cap_percentage(amount, cap_limit)
    return f"{percentage:.1f}% of cap"
