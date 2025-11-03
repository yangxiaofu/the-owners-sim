"""
Run All Trade Value Calculator Scenarios (Non-Interactive)

Runs all 5 pre-built scenarios automatically for testing and demonstration purposes.

Usage:
    PYTHONPATH=src python demo/trade_value_demo/run_all_scenarios.py

    Or run from anywhere:
    python demo/trade_value_demo/run_all_scenarios.py
"""

import sys
from pathlib import Path

# Add src to path for imports (works from any directory)
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

from trade_value_demo import (
    scenario_1_elite_qb_trade,
    scenario_2_star_wr_trade,
    scenario_3_trade_up,
    scenario_4_salary_dump,
    scenario_5_blockbuster,
    print_header
)


def run_all_scenarios():
    """Run all 5 pre-built scenarios"""
    print("\n" + "🏈" * 40)
    print("\n  NFL TRADE VALUE CALCULATOR - ALL SCENARIOS")
    print("  Phase 1.2: AI Transaction System Development")
    print("\n" + "🏈" * 40)

    print("\n\nRunning all 5 pre-built trade scenarios...\n")

    # Scenario 1
    scenario_1_elite_qb_trade()
    print("\n" + "─" * 80 + "\n")

    # Scenario 2
    scenario_2_star_wr_trade()
    print("\n" + "─" * 80 + "\n")

    # Scenario 3
    scenario_3_trade_up()
    print("\n" + "─" * 80 + "\n")

    # Scenario 4
    scenario_4_salary_dump()
    print("\n" + "─" * 80 + "\n")

    # Scenario 5
    scenario_5_blockbuster()

    print_header("All Scenarios Complete!")
    print("✓ 5 trade scenarios evaluated successfully")
    print("\nKey Takeaways:")
    print("  - Player values scale non-linearly (elite players are exponentially more valuable)")
    print("  - Draft picks follow Jimmy Johnson chart with future year discounting")
    print("  - Age curves vary by position (QB ages better than RB)")
    print("  - Contract status significantly impacts value (bad contracts = negative value)")
    print("  - Trade fairness evaluated using 0.80-1.20 acceptable range")
    print("\nNext Steps:")
    print("  1. Run interactive mode: PYTHONPATH=src python demo/trade_value_demo/trade_value_demo.py")
    print("  2. Benchmark against real NFL trades")
    print("  3. Integrate with GM archetype system (Phase 1.3)")


if __name__ == "__main__":
    run_all_scenarios()
