"""
Salary Cap Calculator

Core mathematical operations for NFL salary cap calculations including:
- Cap space calculations (top-51 vs 53-man roster)
- Signing bonus proration (5-year max rule)
- Dead money calculations
- June 1 designation splits
- Transaction validation

All calculations follow 2024-2025 NFL CBA rules.
"""

from typing import Tuple, Optional, List, Dict, Any
import logging

from .cap_database_api import CapDatabaseAPI


class CapCalculator:
    """
    Core salary cap calculation engine.

    Provides pure mathematical operations for all cap-related calculations.
    Follows NFL CBA rules for proration, dead money, and compliance.

    Key Rules:
    - Maximum 5-year proration for signing bonuses
    - Top-51 rule during offseason
    - 53-man roster during regular season
    - 89% spending floor over 4 years (cash-based)
    """

    # NFL Cap Rules Constants
    MAX_PRORATION_YEARS = 5
    ROSTER_SIZE_REGULAR_SEASON = 53
    TOP_51_SIZE = 51
    SPENDING_FLOOR_PERCENTAGE = 0.89  # 89% over 4 years

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Cap Calculator.

        Args:
            database_path: Path to database (for accessing contract data)
        """
        self.db_api = CapDatabaseAPI(database_path)
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # CORE CAP SPACE CALCULATIONS
    # ========================================================================

    def calculate_team_cap_space(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        roster_mode: str = "regular_season"
    ) -> int:
        """
        Calculate team's available cap space.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            roster_mode: "regular_season" (53-man) or "offseason" (top-51)

        Returns:
            Available cap space in dollars (can be negative if over cap)

        Formula:
            cap_space = (base_cap + carryover) - (active_contracts + dead_money + ltbe_incentives + practice_squad)

        In offseason mode, only top-51 contracts count toward cap.
        """
        # Get team cap summary
        cap_summary = self.db_api.get_team_cap_summary(team_id, season, dynasty_id)

        if not cap_summary:
            # Initialize if doesn't exist
            salary_cap = self.db_api.get_salary_cap_for_season(season)
            if not salary_cap:
                raise ValueError(f"No salary cap defined for season {season}")

            self.db_api.initialize_team_cap(team_id, season, dynasty_id, salary_cap, 0)
            cap_summary = self.db_api.get_team_cap_summary(team_id, season, dynasty_id)

        # Calculate total cap available
        total_cap_available = (
            cap_summary['salary_cap_limit'] +
            cap_summary['carryover_from_previous']
        )

        # Calculate committed cap based on roster mode
        if roster_mode == "offseason" and cap_summary['is_top_51_active']:
            # Use top-51 total if in offseason mode
            committed_cap = cap_summary.get('top_51_total', 0)
        else:
            # Use all active contracts for regular season
            committed_cap = cap_summary['active_contracts_total']

        # Add dead money, LTBE incentives, and practice squad (always count)
        committed_cap += cap_summary['dead_money_total']
        committed_cap += cap_summary['ltbe_incentives_total']
        committed_cap += cap_summary['practice_squad_total']

        # Calculate available space
        cap_space = total_cap_available - committed_cap

        return cap_space

    def calculate_top_51_total(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> int:
        """
        Calculate total cap hit of top-51 highest contracts.

        Used during offseason when only top-51 contracts count against cap.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Total cap hit of top-51 contracts
        """
        # Get all active contracts for team
        contracts = self.db_api.get_team_contracts(
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            active_only=True
        )

        if not contracts:
            return 0

        # Get cap hits for each contract in this season
        cap_hits = []
        for contract in contracts:
            year_details = self.db_api.get_contract_year_details(
                contract['contract_id'],
                season_year=season
            )
            if year_details:
                cap_hits.append(year_details[0]['total_cap_hit'])

        # Sort descending and take top 51
        cap_hits_sorted = sorted(cap_hits, reverse=True)
        top_51_hits = cap_hits_sorted[:self.TOP_51_SIZE]

        return sum(top_51_hits)

    # ========================================================================
    # BONUS PRORATION CALCULATIONS
    # ========================================================================

    def calculate_signing_bonus_proration(
        self,
        signing_bonus: int,
        contract_years: int
    ) -> int:
        """
        Calculate annual proration amount for signing bonus.

        NFL Rule: Signing bonuses are prorated over the life of the contract
        with a MAXIMUM of 5 years, regardless of contract length.

        Args:
            signing_bonus: Total signing bonus amount
            contract_years: Number of contract years

        Returns:
            Annual proration amount

        Examples:
            - 4-year, $20M bonus → $5M/year ($20M / 4 years)
            - 7-year, $35M bonus → $7M/year ($35M / 5 years, NOT 7!)

        Formula:
            annual_proration = signing_bonus / min(contract_years, 5)
        """
        if signing_bonus <= 0:
            return 0

        if contract_years <= 0:
            raise ValueError("Contract years must be positive")

        # Apply 5-year maximum proration rule
        proration_years = min(contract_years, self.MAX_PRORATION_YEARS)

        # Calculate annual amount (integer division, rounds down)
        annual_proration = signing_bonus // proration_years

        return annual_proration

    def calculate_option_bonus_proration(
        self,
        option_bonus: int,
        remaining_years: int
    ) -> int:
        """
        Calculate proration for option bonus.

        Option bonuses follow same rules as signing bonuses:
        prorated over remaining contract years with 5-year max.

        Args:
            option_bonus: Option bonus amount
            remaining_years: Remaining years when option exercised

        Returns:
            Annual proration amount
        """
        return self.calculate_signing_bonus_proration(option_bonus, remaining_years)

    # ========================================================================
    # DEAD MONEY CALCULATIONS
    # ========================================================================

    def calculate_dead_money(
        self,
        contract_id: int,
        release_year: int,
        june_1_designation: bool = False
    ) -> Tuple[int, int]:
        """
        Calculate dead money cap hit from releasing a player.

        Dead money consists of:
        1. Remaining signing bonus proration (accelerates to current year)
        2. Any guaranteed base salary not yet paid

        Args:
            contract_id: Contract ID
            release_year: Season year when released
            june_1_designation: Whether using June 1 designation

        Returns:
            Tuple of (current_year_dead_money, next_year_dead_money)

        Notes:
            - Without June 1: All dead money hits current year
            - With June 1: Split over 2 years (1 year proration now, rest next year)
        """
        # Get contract details
        contract = self.db_api.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Get year details for remaining years
        year_details = self.db_api.get_contract_year_details(contract_id)

        # Calculate remaining signing bonus proration
        remaining_proration = 0
        guaranteed_salary = 0

        for detail in year_details:
            if detail['season_year'] >= release_year:
                # Add remaining bonus proration
                remaining_proration += detail['signing_bonus_proration']
                remaining_proration += detail.get('option_bonus_proration', 0)

                # Add guaranteed base salary
                if detail['base_salary_guaranteed']:
                    guaranteed_salary += detail['base_salary']

        total_dead_money = remaining_proration + guaranteed_salary

        if not june_1_designation:
            # All dead money hits current year
            return (total_dead_money, 0)
        else:
            # June 1 split: Current year gets one year of proration + guarantees
            # Next year gets remaining proration
            annual_proration = contract.get('signing_bonus_proration', 0)
            current_year_dead_money = annual_proration + guaranteed_salary
            next_year_dead_money = total_dead_money - current_year_dead_money

            return (current_year_dead_money, next_year_dead_money)

    def calculate_dead_money_from_values(
        self,
        remaining_bonus_proration: int,
        guaranteed_salary: int,
        annual_proration: int,
        june_1_designation: bool = False
    ) -> Tuple[int, int]:
        """
        Calculate dead money from raw values (used for projections).

        Args:
            remaining_bonus_proration: Total remaining proration
            guaranteed_salary: Guaranteed salary to accelerate
            annual_proration: Annual proration amount
            june_1_designation: Whether using June 1 split

        Returns:
            Tuple of (current_year_dead_money, next_year_dead_money)
        """
        total_dead_money = remaining_bonus_proration + guaranteed_salary

        if not june_1_designation:
            return (total_dead_money, 0)
        else:
            current_year = annual_proration + guaranteed_salary
            next_year = total_dead_money - current_year
            return (current_year, next_year)

    # ========================================================================
    # CONTRACT RESTRUCTURE CALCULATIONS
    # ========================================================================

    def calculate_restructure_impact(
        self,
        base_salary_to_convert: int,
        remaining_contract_years: int
    ) -> Dict[str, Any]:
        """
        Calculate cap impact of restructuring contract.

        Restructure: Convert base salary to signing bonus to reduce current cap hit.

        Args:
            base_salary_to_convert: Amount of base salary to convert
            remaining_contract_years: Years remaining on contract

        Returns:
            Dict with:
            - cap_savings_current_year: Immediate cap savings
            - annual_increase_future_years: Added cap hit per future year
            - dead_money_increase: Additional dead money if cut later
            - new_proration: New annual proration amount

        Formula:
            - Current year savings: base_salary - (base_salary / min(years, 5))
            - Future year increase: base_salary / min(years, 5)

        Example:
            Convert $12M base with 3 years left:
            - New proration: $12M / 3 = $4M/year
            - Current savings: $12M - $4M = $8M
            - Future increase: $4M/year added to Years 2-3
        """
        if base_salary_to_convert <= 0:
            raise ValueError("Must convert positive amount")

        if remaining_contract_years <= 0:
            raise ValueError("Contract must have remaining years")

        # Calculate new annual proration
        new_proration = self.calculate_signing_bonus_proration(
            base_salary_to_convert,
            remaining_contract_years
        )

        # Current year savings (base salary → proration)
        cap_savings_current_year = base_salary_to_convert - new_proration

        # Future years each get additional proration
        annual_increase_future_years = new_proration

        # Dead money increase if cut (remaining proration)
        # After current year: (remaining_years - 1) × new_proration
        dead_money_increase = new_proration * (remaining_contract_years - 1)

        return {
            'cap_savings_current_year': cap_savings_current_year,
            'annual_increase_future_years': annual_increase_future_years,
            'dead_money_increase': dead_money_increase,
            'new_proration': new_proration,
            'remaining_years': remaining_contract_years
        }

    # ========================================================================
    # TRANSACTION VALIDATION
    # ========================================================================

    def validate_transaction(
        self,
        team_id: int,
        season: int,
        dynasty_id: str,
        cap_impact: int,
        roster_mode: str = "regular_season"
    ) -> Tuple[bool, str]:
        """
        Validate if team has cap space for a transaction.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier
            cap_impact: Negative number (reduces cap space)
            roster_mode: "regular_season" or "offseason"

        Returns:
            Tuple of (is_valid, error_message)

        Examples:
            - Signing $10M player: cap_impact = -10_000_000
            - Releasing player saving $5M: cap_impact = +5_000_000
        """
        try:
            # Calculate current cap space
            current_cap_space = self.calculate_team_cap_space(
                team_id, season, dynasty_id, roster_mode
            )

            # Check if transaction would put team over cap
            cap_space_after = current_cap_space + cap_impact

            if cap_space_after < 0:
                shortage = abs(cap_space_after)
                return (
                    False,
                    f"Insufficient cap space. Need ${shortage:,} more. "
                    f"Current space: ${current_cap_space:,}, "
                    f"Transaction cost: ${abs(cap_impact):,}"
                )

            return (True, "")

        except Exception as e:
            self.logger.error(f"Error validating transaction: {e}")
            return (False, f"Validation error: {str(e)}")

    def check_cap_compliance(
        self,
        team_id: int,
        season: int,
        dynasty_id: str
    ) -> Tuple[bool, str]:
        """
        Check if team is cap-compliant.

        A team is compliant if cap_space >= 0.

        Args:
            team_id: Team ID
            season: Season year
            dynasty_id: Dynasty identifier

        Returns:
            Tuple of (is_compliant, message)
        """
        try:
            cap_space = self.calculate_team_cap_space(
                team_id, season, dynasty_id, roster_mode="regular_season"
            )

            if cap_space >= 0:
                return (True, f"Compliant with ${cap_space:,} available")
            else:
                overage = abs(cap_space)
                return (False, f"Over cap by ${overage:,}")

        except Exception as e:
            self.logger.error(f"Error checking compliance: {e}")
            return (False, f"Compliance check error: {str(e)}")

    # ========================================================================
    # SPENDING FLOOR CALCULATIONS
    # ========================================================================

    def calculate_four_year_cash_spending(
        self,
        team_id: int,
        start_year: int,
        end_year: int,
        dynasty_id: str
    ) -> int:
        """
        Calculate total cash spending over 4-year period.

        Used for 89% spending floor compliance (cash, not cap).

        Args:
            team_id: Team ID
            start_year: Start of 4-year period
            end_year: End of 4-year period
            dynasty_id: Dynasty identifier

        Returns:
            Total cash spent over period
        """
        total_cash = 0

        for year in range(start_year, end_year + 1):
            cap_summary = self.db_api.get_team_cap_summary(team_id, year, dynasty_id)
            if cap_summary:
                total_cash += cap_summary.get('cash_spent_this_year', 0)

        return total_cash

    def check_spending_floor_compliance(
        self,
        team_id: int,
        start_year: int,
        end_year: int,
        dynasty_id: str
    ) -> Tuple[bool, int]:
        """
        Check if team met 89% spending floor over 4-year period.

        Args:
            team_id: Team ID
            start_year: Start of 4-year period
            end_year: End of 4-year period
            dynasty_id: Dynasty identifier

        Returns:
            Tuple of (is_compliant, shortfall_amount)
            shortfall_amount is 0 if compliant, positive if under floor
        """
        if end_year - start_year + 1 != 4:
            raise ValueError("Spending floor is calculated over exactly 4 years")

        # Calculate required spending (89% of total caps)
        total_cap_limit = 0
        for year in range(start_year, end_year + 1):
            cap_amount = self.db_api.get_salary_cap_for_season(year)
            if cap_amount:
                total_cap_limit += cap_amount

        required_spending = int(total_cap_limit * self.SPENDING_FLOOR_PERCENTAGE)

        # Calculate actual cash spending
        actual_spending = self.calculate_four_year_cash_spending(
            team_id, start_year, end_year, dynasty_id
        )

        # Check compliance
        if actual_spending >= required_spending:
            return (True, 0)
        else:
            shortfall = required_spending - actual_spending
            return (False, shortfall)

    # ========================================================================
    # UTILITY CALCULATIONS
    # ========================================================================

    def calculate_contract_cap_hit_by_year(
        self,
        contract_id: int
    ) -> Dict[int, int]:
        """
        Calculate cap hit for each year of a contract.

        Args:
            contract_id: Contract ID

        Returns:
            Dict mapping season_year → cap_hit
        """
        year_details = self.db_api.get_contract_year_details(contract_id)

        cap_hits = {}
        for detail in year_details:
            cap_hits[detail['season_year']] = detail['total_cap_hit']

        return cap_hits

    def calculate_contract_cash_by_year(
        self,
        contract_id: int
    ) -> Dict[int, int]:
        """
        Calculate cash paid for each year of a contract.

        Args:
            contract_id: Contract ID

        Returns:
            Dict mapping season_year → cash_paid
        """
        year_details = self.db_api.get_contract_year_details(contract_id)

        cash_paid = {}
        for detail in year_details:
            cash_paid[detail['season_year']] = detail['cash_paid']

        return cash_paid
