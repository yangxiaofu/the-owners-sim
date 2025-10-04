"""
NFL Contract Generator

Converts simple player contract data into detailed year-by-year contract structures
with realistic salary cap calculations following NFL collective bargaining rules.

This module handles:
- Signing bonus proration (max 5 years per NFL CBA)
- Realistic salary escalation based on contract type
- Guaranteed money distribution across early years
- Annual cap hit calculations
- Multiple contract types (extension, rookie, veteran minimum, practice squad)

Usage Example:
    from contract_generator import ContractGenerator

    simple_contract = {
        "contract_years": 10,
        "annual_salary": 45000000,
        "signing_bonus": 10000000,
        "guaranteed_money": 141481905,
        "contract_type": "extension",
        "cap_hit_2025": 28062269
    }

    generator = ContractGenerator()
    detailed_contract = generator.generate_contract_details(
        simple_contract,
        start_year=2025
    )

    print(f"Total Value: ${detailed_contract['total_value']:,}")
    for year_detail in detailed_contract['year_details']:
        print(f"Year {year_detail['year']}: Cap Hit ${year_detail['cap_hit']:,}")
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum


class ContractType(Enum):
    """NFL contract type classifications."""
    EXTENSION = "extension"
    ROOKIE = "rookie"
    VETERAN_MINIMUM = "veteran_minimum"
    PRACTICE_SQUAD = "practice_squad"
    FREE_AGENT = "free_agent"
    RESTRUCTURE = "restructure"


@dataclass
class YearDetail:
    """
    Detailed breakdown of a single contract year.

    Attributes:
        year: Contract year (e.g., 2025)
        base_salary: Base salary for the year
        base_guaranteed: Portion of base salary that is guaranteed
        proration: Signing bonus proration amount
        cap_hit: Total cap hit (base + proration + other charges)
        guaranteed_total: Total guaranteed money for the year
    """
    year: int
    base_salary: int
    base_guaranteed: int
    proration: int
    cap_hit: int
    guaranteed_total: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'year': self.year,
            'base_salary': self.base_salary,
            'base_guaranteed': self.base_guaranteed,
            'proration': self.proration,
            'cap_hit': self.cap_hit,
            'guaranteed_total': self.guaranteed_total
        }


class ContractGenerator:
    """
    Generates detailed NFL contract structures from simple contract data.

    This class handles the conversion of basic contract parameters (total years,
    average salary, bonuses) into realistic year-by-year breakdowns following
    NFL collective bargaining agreement rules.

    Key Features:
    - Signing bonus proration (max 5 years per NFL CBA)
    - Realistic salary escalation patterns
    - Guaranteed money distribution
    - Contract type-specific logic
    - Cap hit calculations

    Attributes:
        MAX_PRORATION_YEARS: Maximum years for signing bonus proration (5 per NFL rules)
        ESCALATION_RATES: Salary escalation percentages by contract type
    """

    # NFL CBA Rule: Signing bonuses can be prorated over max 5 years
    MAX_PRORATION_YEARS = 5

    # Salary escalation rates by contract type
    ESCALATION_RATES = {
        ContractType.EXTENSION: 0.04,  # 4% annual increase (typical star extension)
        ContractType.FREE_AGENT: 0.035,  # 3.5% annual increase
        ContractType.RESTRUCTURE: 0.03,  # 3% annual increase
        ContractType.ROOKIE: 0.0,  # Flat (rookie contracts have set scales)
        ContractType.VETERAN_MINIMUM: 0.0,  # Flat
        ContractType.PRACTICE_SQUAD: 0.0  # Flat
    }

    def __init__(self):
        """Initialize the ContractGenerator."""
        pass

    def generate_contract_details(
        self,
        simple_contract: Dict[str, Any],
        start_year: int = 2025,
        use_actual_cap_hit: bool = True
    ) -> Dict[str, Any]:
        """
        Generate detailed year-by-year contract breakdown from simple contract data.

        This method converts a simple contract structure into a comprehensive
        breakdown including signing bonus proration, base salary by year,
        guaranteed money distribution, and annual cap hits.

        Args:
            simple_contract: Dictionary containing:
                - contract_years (int): Total contract length
                - annual_salary (int): Average annual salary
                - signing_bonus (int): Signing bonus amount
                - guaranteed_money (int): Total guaranteed money
                - contract_type (str): Type of contract
                - cap_hit_2025 (int, optional): Known first year cap hit
            start_year: First year of the contract (default: 2025)
            use_actual_cap_hit: If True and cap_hit provided, use it for validation

        Returns:
            Dictionary containing:
                - total_value (int): Total contract value
                - signing_bonus (int): Signing bonus amount
                - signing_bonus_proration (int): Annual proration amount
                - proration_years (int): Number of years bonus is prorated
                - guaranteed_money (int): Total guaranteed money
                - contract_type (str): Contract type
                - year_details (List[Dict]): Year-by-year breakdown

        Example:
            >>> generator = ContractGenerator()
            >>> contract = {
            ...     "contract_years": 10,
            ...     "annual_salary": 45000000,
            ...     "signing_bonus": 10000000,
            ...     "guaranteed_money": 141481905,
            ...     "contract_type": "extension"
            ... }
            >>> details = generator.generate_contract_details(contract)
            >>> print(f"Total: ${details['total_value']:,}")
            Total: $450,000,000
        """
        # Extract contract parameters
        contract_years = simple_contract['contract_years']
        annual_salary = simple_contract['annual_salary']
        signing_bonus = simple_contract['signing_bonus']
        guaranteed_money = simple_contract['guaranteed_money']
        contract_type_str = simple_contract['contract_type']
        known_cap_hit = simple_contract.get('cap_hit_2025')

        # Convert contract type string to enum
        contract_type = self._parse_contract_type(contract_type_str)

        # Calculate signing bonus proration
        proration_years = min(contract_years, self.MAX_PRORATION_YEARS)
        signing_bonus_proration = signing_bonus // proration_years if signing_bonus > 0 else 0

        # Generate base salaries for each year
        base_salaries = self._generate_base_salaries(
            contract_years,
            annual_salary,
            signing_bonus,
            contract_type
        )

        # Distribute guaranteed money across years
        guaranteed_by_year = self._distribute_guaranteed_money(
            guaranteed_money,
            base_salaries,
            signing_bonus,
            proration_years
        )

        # Generate year-by-year details
        year_details = []
        for year_index in range(contract_years):
            year = start_year + year_index
            base_salary = base_salaries[year_index]
            base_guaranteed = guaranteed_by_year[year_index]

            # Calculate proration for this year
            proration = signing_bonus_proration if year_index < proration_years else 0

            # Calculate cap hit (base + proration)
            cap_hit = base_salary + proration

            # Total guaranteed for the year (base + proration if in proration window)
            guaranteed_total = base_guaranteed + (proration if year_index < proration_years else 0)

            year_detail = YearDetail(
                year=year,
                base_salary=base_salary,
                base_guaranteed=base_guaranteed,
                proration=proration,
                cap_hit=cap_hit,
                guaranteed_total=guaranteed_total
            )
            year_details.append(year_detail)

        # Validate against known cap hit if provided
        if use_actual_cap_hit and known_cap_hit is not None:
            calculated_first_year_cap = year_details[0].cap_hit
            if abs(calculated_first_year_cap - known_cap_hit) > 1000:  # Allow $1k variance
                # Adjust first year base salary to match known cap hit
                adjustment = known_cap_hit - calculated_first_year_cap
                year_details[0].base_salary += adjustment
                year_details[0].cap_hit = known_cap_hit
                base_salaries[0] += adjustment

        # Calculate total contract value
        total_value = sum(base_salaries) + signing_bonus

        return {
            'total_value': total_value,
            'signing_bonus': signing_bonus,
            'signing_bonus_proration': signing_bonus_proration,
            'proration_years': proration_years,
            'guaranteed_money': guaranteed_money,
            'contract_type': contract_type_str,
            'start_year': start_year,
            'end_year': start_year + contract_years - 1,
            'year_details': [detail.to_dict() for detail in year_details]
        }

    def _parse_contract_type(self, contract_type_str: str) -> ContractType:
        """
        Parse contract type string to ContractType enum.

        Args:
            contract_type_str: Contract type as string

        Returns:
            ContractType enum value
        """
        try:
            return ContractType(contract_type_str.lower())
        except ValueError:
            # Default to free agent if unknown type
            return ContractType.FREE_AGENT

    def _generate_base_salaries(
        self,
        contract_years: int,
        annual_salary: int,
        signing_bonus: int,
        contract_type: ContractType
    ) -> List[int]:
        """
        Generate realistic base salary for each contract year.

        Different contract types have different salary structures:
        - Extensions: Escalating salaries (3-5% per year)
        - Rookie: Flat salaries based on draft slot
        - Veteran Minimum: Flat minimum salary
        - Practice Squad: Flat practice squad rate

        Args:
            contract_years: Number of contract years
            annual_salary: Average annual salary
            signing_bonus: Signing bonus (affects base salary calculation)
            contract_type: Type of contract

        Returns:
            List of base salaries for each year
        """
        escalation_rate = self.ESCALATION_RATES.get(contract_type, 0.0)

        # Calculate total base salary pool (total value - signing bonus)
        total_base_pool = (annual_salary * contract_years) - signing_bonus

        if escalation_rate == 0.0:
            # Flat salary structure
            base_per_year = total_base_pool // contract_years
            return [base_per_year] * contract_years

        # Escalating salary structure
        # Use geometric series formula to find starting salary
        # Sum = a(1 - r^n) / (1 - r), where a = starting salary, r = 1 + escalation_rate
        r = 1 + escalation_rate
        geometric_factor = (1 - r**contract_years) / (1 - r)
        starting_salary = total_base_pool / geometric_factor

        # Generate escalating salaries
        base_salaries = []
        for year in range(contract_years):
            salary = int(starting_salary * (r ** year))
            base_salaries.append(salary)

        # Adjust for rounding errors (add/subtract from middle years)
        total_generated = sum(base_salaries)
        difference = total_base_pool - total_generated
        if difference != 0:
            mid_year = contract_years // 2
            base_salaries[mid_year] += difference

        return base_salaries

    def _distribute_guaranteed_money(
        self,
        guaranteed_money: int,
        base_salaries: List[int],
        signing_bonus: int,
        proration_years: int
    ) -> List[int]:
        """
        Distribute guaranteed money across contract years.

        NFL contracts typically guarantee money in early years, with the
        signing bonus proration always guaranteed. Additional guaranteed
        base salary is frontloaded.

        Strategy:
        1. Signing bonus proration is always guaranteed (first N years)
        2. Remaining guaranteed money comes from base salaries
        3. Early years get fully guaranteed base
        4. Later years may be partially or not guaranteed

        Args:
            guaranteed_money: Total guaranteed money in contract
            base_salaries: Base salary for each year
            signing_bonus: Signing bonus amount
            proration_years: Number of years signing bonus is prorated

        Returns:
            List of guaranteed base salary for each year
        """
        # Signing bonus is always fully guaranteed and prorated
        guaranteed_from_bonus = signing_bonus

        # Remaining guaranteed money comes from base salaries
        remaining_guaranteed = guaranteed_money - guaranteed_from_bonus

        guaranteed_by_year = []
        remaining_to_allocate = remaining_guaranteed

        for i, base_salary in enumerate(base_salaries):
            if remaining_to_allocate <= 0:
                guaranteed_by_year.append(0)
            elif remaining_to_allocate >= base_salary:
                # Fully guarantee this year
                guaranteed_by_year.append(base_salary)
                remaining_to_allocate -= base_salary
            else:
                # Partially guarantee this year
                guaranteed_by_year.append(remaining_to_allocate)
                remaining_to_allocate = 0

        return guaranteed_by_year

    def format_contract_summary(self, contract_details: Dict[str, Any]) -> str:
        """
        Format contract details into a readable summary string.

        Args:
            contract_details: Output from generate_contract_details()

        Returns:
            Formatted multi-line string summary
        """
        lines = []
        lines.append("=" * 70)
        lines.append("NFL CONTRACT DETAILS")
        lines.append("=" * 70)
        lines.append(f"Contract Type: {contract_details['contract_type'].upper()}")
        lines.append(f"Total Value: ${contract_details['total_value']:,}")
        lines.append(f"Signing Bonus: ${contract_details['signing_bonus']:,}")
        lines.append(f"Guaranteed Money: ${contract_details['guaranteed_money']:,}")
        lines.append(f"Years: {contract_details['start_year']}-{contract_details['end_year']}")
        lines.append(f"Signing Bonus Proration: ${contract_details['signing_bonus_proration']:,}/year over {contract_details['proration_years']} years")
        lines.append("")
        lines.append("-" * 70)
        lines.append(f"{'Year':<6} {'Base Salary':<15} {'Guaranteed':<15} {'Proration':<12} {'Cap Hit':<15}")
        lines.append("-" * 70)

        for year_detail in contract_details['year_details']:
            lines.append(
                f"{year_detail['year']:<6} "
                f"${year_detail['base_salary']:<14,} "
                f"${year_detail['base_guaranteed']:<14,} "
                f"${year_detail['proration']:<11,} "
                f"${year_detail['cap_hit']:<14,}"
            )

        lines.append("=" * 70)
        return "\n".join(lines)


def main():
    """
    Demonstration of ContractGenerator with various contract types.
    """
    print("\n" + "=" * 80)
    print("NFL CONTRACT GENERATOR DEMONSTRATION")
    print("=" * 80 + "\n")

    generator = ContractGenerator()

    # Example 1: Star Player Extension (Patrick Mahomes style)
    print("\n--- EXAMPLE 1: Star QB Extension ---\n")
    mahomes_contract = {
        "contract_years": 10,
        "annual_salary": 45000000,
        "signing_bonus": 10000000,
        "guaranteed_money": 141481905,
        "contract_type": "extension",
        "cap_hit_2025": 28062269
    }

    mahomes_details = generator.generate_contract_details(mahomes_contract, start_year=2025)
    print(generator.format_contract_summary(mahomes_details))

    # Example 2: Rookie Contract (1st Round Pick)
    print("\n--- EXAMPLE 2: First Round Rookie ---\n")
    rookie_contract = {
        "contract_years": 4,
        "annual_salary": 8000000,
        "signing_bonus": 12000000,
        "guaranteed_money": 32000000,
        "contract_type": "rookie"
    }

    rookie_details = generator.generate_contract_details(rookie_contract, start_year=2025)
    print(generator.format_contract_summary(rookie_details))

    # Example 3: Veteran Minimum
    print("\n--- EXAMPLE 3: Veteran Minimum ---\n")
    vet_min_contract = {
        "contract_years": 1,
        "annual_salary": 1165000,
        "signing_bonus": 0,
        "guaranteed_money": 0,
        "contract_type": "veteran_minimum"
    }

    vet_min_details = generator.generate_contract_details(vet_min_contract, start_year=2025)
    print(generator.format_contract_summary(vet_min_details))

    # Example 4: Practice Squad
    print("\n--- EXAMPLE 4: Practice Squad Player ---\n")
    practice_squad_contract = {
        "contract_years": 1,
        "annual_salary": 216000,
        "signing_bonus": 0,
        "guaranteed_money": 0,
        "contract_type": "practice_squad"
    }

    ps_details = generator.generate_contract_details(practice_squad_contract, start_year=2025)
    print(generator.format_contract_summary(ps_details))

    # Example 5: Mid-tier Free Agent
    print("\n--- EXAMPLE 5: Mid-Tier Free Agent ---\n")
    free_agent_contract = {
        "contract_years": 3,
        "annual_salary": 12000000,
        "signing_bonus": 5000000,
        "guaranteed_money": 20000000,
        "contract_type": "free_agent"
    }

    fa_details = generator.generate_contract_details(free_agent_contract, start_year=2025)
    print(generator.format_contract_summary(fa_details))

    print("\n" + "=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
