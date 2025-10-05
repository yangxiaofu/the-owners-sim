"""
Salary Cap Validator

Enforces NFL salary cap rules and compliance requirements including:
- League year compliance (March 12 deadline)
- 89% spending floor over 4 years
- Cap violation detection
- Compliance reporting

Provides methods for both validation and enforcement.
"""

from typing import Tuple, List, Dict, Any, Optional
from datetime import date
import logging

from .cap_calculator import CapCalculator
from .cap_database_api import CapDatabaseAPI


class CapValidator:
    """
    Validates salary cap compliance and enforces NFL rules.

    Key Responsibilities:
    - Check cap compliance at league year start
    - Validate 89% spending floor over 4-year periods
    - Generate compliance reports
    - Enforce compliance (for AI teams)
    """

    # NFL Compliance Constants
    LEAGUE_YEAR_COMPLIANCE_DAY = 12  # March 12
    LEAGUE_YEAR_COMPLIANCE_MONTH = 3  # March
    SPENDING_FLOOR_PERCENTAGE = 0.89  # 89% over 4 years
    SPENDING_FLOOR_PERIOD = 4  # 4-year periods

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Cap Validator.

        Args:
            database_path: Path to database
        """
        self.calculator = CapCalculator(database_path)
        self.db_api = CapDatabaseAPI(database_path)
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # LEAGUE YEAR COMPLIANCE
    # ========================================================================

    def check_league_year_compliance(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        deadline_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Validate team is cap-compliant at league year start (March 12).

        Teams must have positive cap space at 4:00 PM ET on the second
        Wednesday in March (effectively March 12-13).

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            deadline_date: Optional specific deadline date

        Returns:
            Tuple of (is_compliant, violation_message)

        Compliance Criteria:
            - Available cap space >= 0
            - Using 53-man roster accounting (not top-51)

        Penalties for Non-Compliance:
            - Fines up to $5M
            - Loss of draft picks
            - Contract voidances
        """
        try:
            # Check cap compliance (regular season mode = 53-man roster)
            is_compliant, message = self.calculator.check_cap_compliance(
                team_id, season, dynasty_id
            )

            if is_compliant:
                return (True, f"✓ Compliant: {message}")
            else:
                return (
                    False,
                    f"✗ VIOLATION: Team over salary cap at league year start. {message}. "
                    f"Must release players, restructure contracts, or void deals to comply."
                )

        except Exception as e:
            self.logger.error(f"Error checking league year compliance: {e}")
            return (False, f"Compliance check error: {str(e)}")

    def check_all_teams_compliance(
        self,
        season: int,
        dynasty_id: str
    ) -> Dict[int, Tuple[bool, str]]:
        """
        Check league year compliance for all 32 teams.

        Args:
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Dict mapping team_id → (is_compliant, message)
        """
        results = {}

        for team_id in range(1, 33):  # Teams 1-32
            is_compliant, message = self.check_league_year_compliance(
                team_id, season, dynasty_id
            )
            results[team_id] = (is_compliant, message)

        return results

    def get_non_compliant_teams(
        self,
        season: int,
        dynasty_id: str
    ) -> List[Tuple[int, str]]:
        """
        Get list of teams that are NOT cap-compliant.

        Args:
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            List of (team_id, violation_message) tuples
        """
        all_teams = self.check_all_teams_compliance(season, dynasty_id)

        non_compliant = [
            (team_id, message)
            for team_id, (is_compliant, message) in all_teams.items()
            if not is_compliant
        ]

        return non_compliant

    # ========================================================================
    # SPENDING FLOOR VALIDATION
    # ========================================================================

    def check_spending_floor(
        self,
        team_id: int,
        four_year_period: Tuple[int, int, int, int],
        dynasty_id: str
    ) -> Tuple[bool, int]:
        """
        Validate team met 89% spending floor over 4-year period.

        NFL Rule: Teams must spend at least 89% of the total salary cap
        over each 4-year period. This is measured in CASH, not cap accounting.

        Args:
            team_id: Team ID
            four_year_period: Tuple of (year1, year2, year3, year4)
            dynasty_id: Dynasty identifier

        Returns:
            Tuple of (is_compliant, shortfall_amount)
            - is_compliant: True if team spent >= 89%
            - shortfall_amount: 0 if compliant, positive if under floor

        Penalty:
            - Team must pay shortfall to NFLPA
            - Money distributed to players who were on team during period

        Example:
            4-year period: 2021-2024
            Total caps: $1.0B
            Required: $890M (89%)
            Team spent: $850M
            Shortfall: $40M (must pay to NFLPA)
        """
        if len(four_year_period) != 4:
            raise ValueError("Must provide exactly 4 years")

        start_year = four_year_period[0]
        end_year = four_year_period[3]

        try:
            is_compliant, shortfall = self.calculator.check_spending_floor_compliance(
                team_id, start_year, end_year, dynasty_id
            )

            return (is_compliant, shortfall)

        except Exception as e:
            self.logger.error(f"Error checking spending floor: {e}")
            return (False, 0)

    def check_all_teams_spending_floor(
        self,
        four_year_period: Tuple[int, int, int, int],
        dynasty_id: str
    ) -> Dict[int, Tuple[bool, int]]:
        """
        Check 89% spending floor for all teams.

        Args:
            four_year_period: Tuple of (year1, year2, year3, year4)
            dynasty_id: Dynasty identifier

        Returns:
            Dict mapping team_id → (is_compliant, shortfall)
        """
        results = {}

        for team_id in range(1, 33):
            is_compliant, shortfall = self.check_spending_floor(
                team_id, four_year_period, dynasty_id
            )
            results[team_id] = (is_compliant, shortfall)

        return results

    # ========================================================================
    # COMPLIANCE REPORTING
    # ========================================================================

    def generate_compliance_report(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Generate comprehensive compliance report for a team.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Dict with:
            - cap_compliance: Is team cap-compliant
            - cap_space: Available cap space
            - cap_summary: Full cap breakdown
            - violations: List of any violations
            - warnings: List of warnings (e.g., close to cap limit)
            - recommendations: Suggested actions if non-compliant
        """
        report = {
            'team_id': team_id,
            'season': season,
            'dynasty_id': dynasty_id,
            'generated_date': date.today().isoformat()
        }

        # Check cap compliance
        is_compliant, compliance_message = self.calculator.check_cap_compliance(
            team_id, season, dynasty_id
        )

        report['cap_compliance'] = {
            'is_compliant': is_compliant,
            'message': compliance_message
        }

        # Get cap space
        try:
            cap_space = self.calculator.calculate_team_cap_space(
                team_id, season, dynasty_id
            )
            report['cap_space'] = cap_space
        except Exception as e:
            report['cap_space'] = None
            report['error'] = str(e)

        # Get full cap summary
        cap_summary = self.db_api.get_team_cap_summary(team_id, season, dynasty_id)
        report['cap_summary'] = cap_summary

        # Identify violations
        violations = []
        warnings = []
        recommendations = []

        if not is_compliant:
            violations.append({
                'type': 'OVER_CAP',
                'severity': 'CRITICAL',
                'message': compliance_message
            })
            recommendations.append("Release players to create cap space")
            recommendations.append("Restructure contracts to reduce current year hit")
            recommendations.append("Consider June 1 designations for maximum relief")

        # Check for warnings (within 5% of cap)
        if cap_summary and cap_space is not None:
            cap_limit = cap_summary['salary_cap_limit']
            if 0 <= cap_space < (cap_limit * 0.05):
                warnings.append({
                    'type': 'LOW_CAP_SPACE',
                    'message': f"Only ${cap_space:,} remaining (< 5% of cap)"
                })

        report['violations'] = violations
        report['warnings'] = warnings
        report['recommendations'] = recommendations

        return report

    def generate_league_compliance_report(
        self,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Generate league-wide compliance report.

        Args:
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Dict with:
            - total_teams: 32
            - compliant_teams: Number of compliant teams
            - non_compliant_teams: List of teams over cap
            - total_violations: Number of violations
            - league_cap_space: Total available cap space across league
        """
        all_teams = self.check_all_teams_compliance(season, dynasty_id)

        compliant_teams = [
            team_id for team_id, (is_compliant, _) in all_teams.items()
            if is_compliant
        ]

        non_compliant_teams = [
            {'team_id': team_id, 'message': message}
            for team_id, (is_compliant, message) in all_teams.items()
            if not is_compliant
        ]

        # Calculate total league cap space
        total_cap_space = 0
        for team_id in range(1, 33):
            try:
                cap_space = self.calculator.calculate_team_cap_space(
                    team_id, season, dynasty_id
                )
                total_cap_space += cap_space
            except:
                pass

        report = {
            'season': season,
            'dynasty_id': dynasty_id,
            'generated_date': date.today().isoformat(),
            'total_teams': 32,
            'compliant_teams': len(compliant_teams),
            'non_compliant_teams': non_compliant_teams,
            'total_violations': len(non_compliant_teams),
            'league_total_cap_space': total_cap_space,
            'compliance_rate': len(compliant_teams) / 32 * 100
        }

        return report

    # ========================================================================
    # COMPLIANCE ENFORCEMENT (for AI teams)
    # ========================================================================

    def enforce_compliance(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Force team to become cap-compliant.

        This is called for AI-controlled teams that are over the cap.
        Uses automated strategies to achieve compliance.

        Strategies (in order):
        1. Release lowest-value players
        2. Restructure high-value contracts
        3. Use June 1 designations (max 2)

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Dict with:
            - actions_taken: List of actions
            - cap_space_before: Cap space before enforcement
            - cap_space_after: Cap space after enforcement
            - is_compliant: Whether team is now compliant

        Note:
            This is a placeholder for AI cap management logic.
            Full implementation would require integration with roster
            management and AI decision-making systems.
        """
        # Get initial cap space
        cap_space_before = self.calculator.calculate_team_cap_space(
            team_id, season, dynasty_id
        )

        actions_taken = []

        # If already compliant, nothing to do
        if cap_space_before >= 0:
            return {
                'actions_taken': [],
                'cap_space_before': cap_space_before,
                'cap_space_after': cap_space_before,
                'is_compliant': True,
                'message': "Team already compliant, no action needed"
            }

        # Placeholder: In full implementation, would:
        # 1. Get all contracts sorted by value/performance ratio
        # 2. Release lowest-value players until compliant
        # 3. If still over, restructure high-value deals
        # 4. If still over, use June 1 designations

        self.logger.warning(
            f"Enforcement called for team {team_id} in season {season}. "
            f"Over cap by ${abs(cap_space_before):,}. "
            f"AI enforcement logic not yet implemented."
        )

        return {
            'actions_taken': actions_taken,
            'cap_space_before': cap_space_before,
            'cap_space_after': cap_space_before,  # Would change after enforcement
            'is_compliant': False,
            'message': "Enforcement logic not yet implemented"
        }

    # ========================================================================
    # VALIDATION UTILITIES
    # ========================================================================

    def validate_june_1_designation_limit(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Tuple[bool, int]:
        """
        Check if team has used maximum June 1 designations (2 per year).

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Tuple of (can_use_june_1, designations_used)
        """
        # Query dead money records for June 1 designations this season
        dead_money_records = self.db_api.get_team_dead_money(team_id, season, dynasty_id)

        june_1_count = sum(
            1 for record in dead_money_records
            if record.get('is_june_1_designation', False)
        )

        can_use = june_1_count < 2

        return (can_use, june_1_count)
