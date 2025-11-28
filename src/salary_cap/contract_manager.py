"""
Contract Manager

Handles creation, modification, and lifecycle management of player contracts.
Integrates with CapCalculator for all calculations and CapDatabaseAPI for persistence.

Supports:
- Rookie contracts (4-year slotted deals)
- Veteran contracts (custom terms)
- Contract extensions
- Contract restructuring
- Player releases
"""

from typing import List, Dict, Any, Optional
from datetime import date
import logging

from .cap_calculator import CapCalculator
from .cap_database_api import CapDatabaseAPI


class ContractManager:
    """
    Manages all player contract operations.

    Provides high-level interface for contract lifecycle:
    - Creating new contracts (rookie, veteran, extension)
    - Restructuring contracts for cap relief
    - Releasing players and calculating dead money
    - Retrieving contract details and projections

    Integrates CapCalculator for formulas and CapDatabaseAPI for persistence.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize Contract Manager.

        Args:
            database_path: Path to database
        """
        self.db_api = CapDatabaseAPI(database_path)
        self.calculator = CapCalculator(database_path)
        self.logger = logging.getLogger(__name__)

    # ========================================================================
    # CONTRACT CREATION
    # ========================================================================

    def create_contract(
        self,
        player_id: int,
        team_id: int,
        dynasty_id: str,
        contract_years: int,
        total_value: int,
        signing_bonus: int,
        base_salaries: List[int],
        guaranteed_amounts: Optional[List[int]] = None,
        contract_type: str = "VETERAN",
        season: int = 2025,
        roster_bonuses: Optional[List[int]] = None,
        workout_bonuses: Optional[List[int]] = None,
        ltbe_incentives: Optional[List[int]] = None,
        nltbe_incentives: Optional[List[int]] = None
    ) -> int:
        """
        Create new player contract.

        Args:
            player_id: Player ID
            team_id: Team ID
            dynasty_id: Dynasty identifier
            contract_years: Number of years
            total_value: Total contract value
            signing_bonus: Signing bonus amount
            base_salaries: List of base salaries per year
            guaranteed_amounts: List of guaranteed amounts per year (optional)
            contract_type: ROOKIE, VETERAN, FRANCHISE_TAG, EXTENSION
            season: Starting season
            roster_bonuses: List of roster bonuses per year (optional)
            workout_bonuses: List of workout bonuses per year (optional)
            ltbe_incentives: List of LTBE incentives per year (optional)
            nltbe_incentives: List of NLTBE incentives per year (optional)

        Returns:
            contract_id of newly created contract

        Raises:
            ValueError: If input validation fails
        """
        # Validate inputs
        if contract_years != len(base_salaries):
            raise ValueError(f"Must provide {contract_years} base salaries")

        if guaranteed_amounts and len(guaranteed_amounts) != contract_years:
            raise ValueError(f"Must provide {contract_years} guarantee amounts")

        # Calculate signing bonus proration
        signing_bonus_proration = self.calculator.calculate_signing_bonus_proration(
            signing_bonus, contract_years
        )

        # Calculate total guaranteed
        guaranteed_at_signing = signing_bonus
        if guaranteed_amounts:
            guaranteed_at_signing += sum(guaranteed_amounts)

        # Create contract record
        contract_id = self.db_api.insert_contract(
            player_id=player_id,
            team_id=team_id,
            dynasty_id=dynasty_id,
            start_year=season,
            end_year=season + contract_years - 1,
            contract_years=contract_years,
            contract_type=contract_type,
            total_value=total_value,
            signing_bonus=signing_bonus,
            signing_bonus_proration=signing_bonus_proration,
            guaranteed_at_signing=guaranteed_at_signing,
            total_guaranteed=guaranteed_at_signing,
            signed_date=date.today()
        )

        # Create year-by-year details
        for year_idx in range(contract_years):
            contract_year = year_idx + 1
            season_year = season + year_idx
            base_salary = base_salaries[year_idx]

            # Get optional components for this year
            roster_bonus = roster_bonuses[year_idx] if roster_bonuses else 0
            workout_bonus = workout_bonuses[year_idx] if workout_bonuses else 0
            ltbe = ltbe_incentives[year_idx] if ltbe_incentives else 0
            nltbe = nltbe_incentives[year_idx] if nltbe_incentives else 0
            guarantee_amount = guaranteed_amounts[year_idx] if guaranteed_amounts else 0

            # Calculate total cap hit
            total_cap_hit = (
                base_salary +
                roster_bonus +
                workout_bonus +
                signing_bonus_proration +
                ltbe  # LTBE counts against cap
                # NLTBE does NOT count against current cap
            )

            # Calculate cash paid (signing bonus paid in Year 1 only)
            cash_paid = base_salary + roster_bonus + workout_bonus
            if year_idx == 0:
                cash_paid += signing_bonus

            # Determine if base salary is guaranteed
            base_salary_guaranteed = guarantee_amount > 0

            self.db_api.insert_contract_year_details(
                contract_id=contract_id,
                contract_year=contract_year,
                season_year=season_year,
                base_salary=base_salary,
                roster_bonus=roster_bonus,
                workout_bonus=workout_bonus,
                ltbe_incentives=ltbe,
                nltbe_incentives=nltbe,
                base_salary_guaranteed=base_salary_guaranteed,
                guarantee_type="FULL" if base_salary_guaranteed else "NONE",
                signing_bonus_proration=signing_bonus_proration,
                total_cap_hit=total_cap_hit,
                cash_paid=cash_paid
            )

        # Log transaction
        self.db_api.log_transaction(
            team_id=team_id,
            season=season,
            dynasty_id=dynasty_id,
            transaction_type="SIGNING",
            transaction_date=date.today(),
            player_id=player_id,
            contract_id=contract_id,
            cap_impact_current=-total_cap_hit if contract_years > 0 else 0,
            cash_impact=-signing_bonus,
            description=f"{contract_type} contract: {contract_years} years, ${total_value:,}"
        )

        self.logger.info(
            f"Created {contract_type} contract {contract_id} for player {player_id}: "
            f"{contract_years} years, ${total_value:,}"
        )

        return contract_id

    def create_rookie_contract(
        self,
        player_id: int,
        team_id: int,
        dynasty_id: str,
        draft_pick: int,
        salary_cap: int,
        season: int = 2025
    ) -> int:
        """
        Create 4-year rookie contract based on draft slot and salary cap.

        Uses formula-based calculation that scales with salary cap growth,
        mirroring actual NFL CBA mechanics. Contract values are calculated
        as percentages of the cap, so they auto-scale year over year.

        Args:
            player_id: Player ID
            team_id: Team ID
            dynasty_id: Dynasty identifier
            draft_pick: Overall draft pick number (1-224)
            salary_cap: Current year's salary cap for scaling
            season: Draft season

        Returns:
            contract_id of created contract

        Raises:
            ValueError: If draft_pick or salary_cap is invalid
        """
        from .rookie_scale import RookieScaleCalculator

        # Calculate contract values using formula-based scale
        calculator = RookieScaleCalculator(salary_cap)
        values = calculator.calculate_contract(draft_pick)

        self.logger.info(
            f"Creating rookie contract for pick #{draft_pick}: "
            f"total=${values.total_value:,}, bonus=${values.signing_bonus:,}, "
            f"5th-year option={values.has_fifth_year_option}"
        )

        return self.create_contract(
            player_id=player_id,
            team_id=team_id,
            dynasty_id=dynasty_id,
            contract_years=4,
            total_value=values.total_value,
            signing_bonus=values.signing_bonus,
            base_salaries=values.base_salaries,
            guaranteed_amounts=values.guaranteed_amounts,
            contract_type="ROOKIE",
            season=season
        )

    # ========================================================================
    # CONTRACT RESTRUCTURING
    # ========================================================================

    def restructure_contract(
        self,
        contract_id: int,
        year_to_restructure: int,
        amount_to_convert: int
    ) -> Dict[str, Any]:
        """
        Restructure contract by converting base salary to signing bonus.

        This creates immediate cap relief by spreading base salary over
        remaining contract years as bonus proration.

        Args:
            contract_id: Contract ID
            year_to_restructure: Contract year to restructure (1-based)
            amount_to_convert: Amount of base salary to convert to bonus

        Returns:
            Dict with:
            - cap_savings: Immediate cap savings this year
            - new_cap_hits: Updated cap hits for all years
            - dead_money_increase: Additional dead money if cut
            - restructure_details: Full calculation breakdown

        Raises:
            ValueError: If restructure is invalid

        Example:
            Year 2 of 4-year contract, $12M base salary
            Convert $9M to bonus:
            - Immediate savings: $6M ($9M - $3M proration)
            - Future years: Add $3M each year
            - Dead money risk: +$6M if cut after this year
        """
        # Get contract
        contract = self.db_api.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        # Get current year details
        year_details = self.db_api.get_contract_year_details(contract_id)
        current_year_detail = next(
            (d for d in year_details if d['contract_year'] == year_to_restructure),
            None
        )

        if not current_year_detail:
            raise ValueError(f"Year {year_to_restructure} not found for contract {contract_id}")

        # Validate amount
        if amount_to_convert > current_year_detail['base_salary']:
            raise ValueError(
                f"Cannot convert ${amount_to_convert:,}, base salary is only "
                f"${current_year_detail['base_salary']:,}"
            )

        # Calculate restructure impact
        remaining_years = contract['contract_years'] - year_to_restructure + 1
        restructure_impact = self.calculator.calculate_restructure_impact(
            amount_to_convert, remaining_years
        )

        # Update database
        # 1. Update current year: reduce base salary, add new proration
        new_base_salary = current_year_detail['base_salary'] - amount_to_convert
        new_proration_total = current_year_detail['signing_bonus_proration'] + restructure_impact['new_proration']
        new_cap_hit = (
            new_base_salary +
            current_year_detail['roster_bonus'] +
            current_year_detail['workout_bonus'] +
            new_proration_total +
            current_year_detail['ltbe_incentives']
        )

        # Update current year
        with self.db_api.db_api.database_path:
            import sqlite3
            conn = sqlite3.connect(self.db_api.database_path)
            conn.execute('''
                UPDATE contract_year_details
                SET base_salary = ?,
                    signing_bonus_proration = ?,
                    total_cap_hit = ?
                WHERE detail_id = ?
            ''', (new_base_salary, new_proration_total, new_cap_hit, current_year_detail['detail_id']))

            # 2. Update future years: add new proration to each
            for detail in year_details:
                if detail['contract_year'] > year_to_restructure:
                    updated_proration = detail['signing_bonus_proration'] + restructure_impact['new_proration']
                    updated_cap_hit = detail['total_cap_hit'] + restructure_impact['new_proration']

                    conn.execute('''
                        UPDATE contract_year_details
                        SET signing_bonus_proration = ?,
                            total_cap_hit = ?
                        WHERE detail_id = ?
                    ''', (updated_proration, updated_cap_hit, detail['detail_id']))

            # 3. Update contract record: increase signing bonus
            new_signing_bonus = contract['signing_bonus'] + amount_to_convert
            new_signing_bonus_proration = contract['signing_bonus_proration'] + restructure_impact['new_proration']

            conn.execute('''
                UPDATE player_contracts
                SET signing_bonus = ?,
                    signing_bonus_proration = ?,
                    modified_at = CURRENT_TIMESTAMP
                WHERE contract_id = ?
            ''', (new_signing_bonus, new_signing_bonus_proration, contract_id))

            conn.commit()
            conn.close()

        # Log transaction
        self.db_api.log_transaction(
            team_id=contract['team_id'],
            season=current_year_detail['season_year'],
            dynasty_id=contract['dynasty_id'],
            transaction_type="RESTRUCTURE",
            transaction_date=date.today(),
            player_id=contract['player_id'],
            contract_id=contract_id,
            cap_impact_current=restructure_impact['cap_savings_current_year'],
            dead_money_created=restructure_impact['dead_money_increase'],
            description=f"Restructure: converted ${amount_to_convert:,} to bonus"
        )

        # Build return dict
        result = {
            'cap_savings': restructure_impact['cap_savings_current_year'],
            'new_cap_hits': self.calculator.calculate_contract_cap_hit_by_year(contract_id),
            'dead_money_increase': restructure_impact['dead_money_increase'],
            'restructure_details': restructure_impact
        }

        self.logger.info(
            f"Restructured contract {contract_id}: converted ${amount_to_convert:,}, "
            f"saved ${result['cap_savings']:,} this year"
        )

        return result

    # ========================================================================
    # PLAYER RELEASE
    # ========================================================================

    def release_player(
        self,
        contract_id: int,
        release_date: Optional[date] = None,
        june_1_designation: bool = False
    ) -> Dict[str, Any]:
        """
        Release player and calculate cap impact.

        Args:
            contract_id: Contract ID
            release_date: Date of release
            june_1_designation: Whether to use June 1 designation

        Returns:
            Dict with:
            - dead_money: Total dead money created
            - current_year_dead_money: Dead money in current year
            - next_year_dead_money: Dead money in next year (if June 1)
            - cap_savings: Cap space freed up (base salary + bonuses)
            - cap_space_available: Net cap impact

        Raises:
            ValueError: If contract invalid or already voided
        """
        if release_date is None:
            release_date = date.today()

        # Get contract
        contract = self.db_api.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        if not contract['is_active']:
            raise ValueError(f"Contract {contract_id} is already inactive")

        # Determine release year
        release_year = release_date.year

        # Calculate dead money
        current_dead_money, next_year_dead_money = self.calculator.calculate_dead_money(
            contract_id, release_year, june_1_designation
        )

        total_dead_money = current_dead_money + next_year_dead_money

        # Get current year cap hit for savings calculation
        year_details = self.db_api.get_contract_year_details(contract_id, release_year)
        current_cap_hit = year_details[0]['total_cap_hit'] if year_details else 0

        # Cap savings = current cap hit - dead money
        cap_savings = current_cap_hit - current_dead_money

        # Void contract
        self.db_api.void_contract(contract_id, release_date)

        # Insert dead money record
        # Calculate breakdown
        contract_details = self.db_api.get_contract_year_details(contract_id)
        remaining_bonus = sum(
            d['signing_bonus_proration'] + d.get('option_bonus_proration', 0)
            for d in contract_details if d['season_year'] >= release_year
        )
        guaranteed_salary = sum(
            d['base_salary'] for d in contract_details
            if d['season_year'] >= release_year and d['base_salary_guaranteed']
        )

        self.db_api.insert_dead_money(
            team_id=contract['team_id'],
            player_id=contract['player_id'],
            season=release_year,
            dynasty_id=contract['dynasty_id'],
            contract_id=contract_id,
            release_date=release_date,
            dead_money_amount=total_dead_money,
            current_year_dead_money=current_dead_money,
            next_year_dead_money=next_year_dead_money,
            remaining_signing_bonus=remaining_bonus,
            guaranteed_salary=guaranteed_salary,
            is_june_1_designation=june_1_designation
        )

        # Log transaction
        self.db_api.log_transaction(
            team_id=contract['team_id'],
            season=release_year,
            dynasty_id=contract['dynasty_id'],
            transaction_type="RELEASE",
            transaction_date=release_date,
            player_id=contract['player_id'],
            contract_id=contract_id,
            cap_impact_current=cap_savings,
            dead_money_created=total_dead_money,
            description=f"Released player, dead money: ${total_dead_money:,}"
        )

        result = {
            'dead_money': total_dead_money,
            'current_year_dead_money': current_dead_money,
            'next_year_dead_money': next_year_dead_money,
            'cap_savings': cap_savings,
            'cap_space_available': cap_savings  # Net impact
        }

        self.logger.info(
            f"Released player contract {contract_id}: ${total_dead_money:,} dead money, "
            f"${cap_savings:,} cap savings"
        )

        return result

    # ========================================================================
    # CONTRACT RETRIEVAL
    # ========================================================================

    def get_contract_details(self, contract_id: int) -> Dict[str, Any]:
        """
        Retrieve complete contract breakdown.

        Args:
            contract_id: Contract ID

        Returns:
            Dict with:
            - contract: Base contract info
            - year_details: Year-by-year breakdown
            - cap_hits_by_year: Cap hit for each year
            - cash_by_year: Cash paid each year
            - dead_money_projections: Dead money if cut each year
            - total_guaranteed: Total guaranteed money
        """
        contract = self.db_api.get_contract(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        year_details = self.db_api.get_contract_year_details(contract_id)
        cap_hits = self.calculator.calculate_contract_cap_hit_by_year(contract_id)
        cash_by_year = self.calculator.calculate_contract_cash_by_year(contract_id)

        # Calculate dead money projections for each year
        dead_money_projections = {}
        for detail in year_details:
            release_year = detail['season_year']
            dead_money, next_year = self.calculator.calculate_dead_money(
                contract_id, release_year, june_1_designation=False
            )
            dead_money_projections[release_year] = {
                'standard': dead_money,
                'june_1_current': dead_money if next_year == 0 else self.calculator.calculate_dead_money(
                    contract_id, release_year, june_1_designation=True
                )[0],
                'june_1_next': next_year if next_year > 0 else self.calculator.calculate_dead_money(
                    contract_id, release_year, june_1_designation=True
                )[1]
            }

        return {
            'contract': contract,
            'year_details': year_details,
            'cap_hits_by_year': cap_hits,
            'cash_by_year': cash_by_year,
            'dead_money_projections': dead_money_projections,
            'total_guaranteed': contract['total_guaranteed']
        }
