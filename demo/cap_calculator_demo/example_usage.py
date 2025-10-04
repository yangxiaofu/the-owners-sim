"""
Example usage of ContractGenerator with player contract data.

This script demonstrates how to use the ContractGenerator to convert
simple player contract JSON data into detailed year-by-year breakdowns.
"""

from contract_generator import ContractGenerator


def example_from_player_json():
    """
    Example: Convert player contract JSON to detailed breakdown.

    This shows the exact use case from the requirements - taking simple
    contract data from a player JSON file and generating detailed year-by-year
    contract structures.
    """
    # Example player contract data (from JSON)
    player_contract = {
        "contract_years": 10,
        "annual_salary": 45000000,
        "signing_bonus": 10000000,
        "guaranteed_money": 141481905,
        "contract_type": "extension",
        "cap_hit_2025": 28062269
    }

    # Initialize generator
    generator = ContractGenerator()

    # Generate detailed contract breakdown
    detailed_contract = generator.generate_contract_details(
        player_contract,
        start_year=2025,
        use_actual_cap_hit=True  # Use the known cap_hit_2025 value
    )

    # Print formatted summary
    print(generator.format_contract_summary(detailed_contract))

    # Access individual year details
    print("\n--- PROGRAMMATIC ACCESS EXAMPLE ---\n")
    print(f"Total Contract Value: ${detailed_contract['total_value']:,}")
    print(f"Annual Proration: ${detailed_contract['signing_bonus_proration']:,}")
    print(f"\nFirst 3 Years Cap Hits:")

    for year_detail in detailed_contract['year_details'][:3]:
        print(f"  {year_detail['year']}: ${year_detail['cap_hit']:,}")

    # Calculate cap savings if cut after year 3
    print(f"\nCap Analysis:")
    year_3_guaranteed = detailed_contract['year_details'][3]['guaranteed_total']
    year_3_cap_hit = detailed_contract['year_details'][3]['cap_hit']

    # Dead money = remaining proration + guaranteed money
    remaining_proration_years = detailed_contract['proration_years'] - 3
    dead_money = (remaining_proration_years * detailed_contract['signing_bonus_proration']) + year_3_guaranteed
    cap_savings = year_3_cap_hit - dead_money

    print(f"  If cut after 2027:")
    print(f"    Dead Money: ${dead_money:,}")
    print(f"    Cap Savings: ${cap_savings:,}")


def example_multiple_contract_types():
    """
    Example: Compare different contract types side by side.
    """
    generator = ContractGenerator()

    contracts = [
        {
            "name": "Star Extension",
            "data": {
                "contract_years": 5,
                "annual_salary": 30000000,
                "signing_bonus": 20000000,
                "guaranteed_money": 100000000,
                "contract_type": "extension"
            }
        },
        {
            "name": "Rookie Deal",
            "data": {
                "contract_years": 4,
                "annual_salary": 6000000,
                "signing_bonus": 10000000,
                "guaranteed_money": 24000000,
                "contract_type": "rookie"
            }
        },
        {
            "name": "Veteran Min",
            "data": {
                "contract_years": 1,
                "annual_salary": 1165000,
                "signing_bonus": 0,
                "guaranteed_money": 0,
                "contract_type": "veteran_minimum"
            }
        }
    ]

    print("\n" + "=" * 80)
    print("COMPARING DIFFERENT CONTRACT TYPES")
    print("=" * 80 + "\n")

    for contract in contracts:
        details = generator.generate_contract_details(contract['data'], start_year=2025)

        print(f"\n{contract['name']}:")
        print(f"  Total: ${details['total_value']:,}")
        print(f"  GTD: ${details['guaranteed_money']:,}")
        print(f"  Year 1 Cap Hit: ${details['year_details'][0]['cap_hit']:,}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("CONTRACT GENERATOR - USAGE EXAMPLES")
    print("=" * 80 + "\n")

    # Example 1: Basic usage with player JSON
    print("\n### EXAMPLE 1: Converting Player Contract JSON ###\n")
    example_from_player_json()

    # Example 2: Comparing contract types
    print("\n### EXAMPLE 2: Comparing Contract Types ###")
    example_multiple_contract_types()

    print("\n" + "=" * 80 + "\n")
