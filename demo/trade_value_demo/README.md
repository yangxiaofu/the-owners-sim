# Trade Value Calculator - Interactive Demo

Interactive demonstration of the NFL Trade Value Calculator system (Phase 1.2 of AI Transaction System).

## Overview

This demo showcases how the Trade Value Calculator evaluates players, draft picks, and complete trade proposals using realistic NFL scenarios. It demonstrates the core valuation algorithms before AI decision-making is integrated in Phase 1.3.

## Features

### 5 Pre-Built Scenarios

1. **Elite QB Trade** - Russell Wilson style blockbuster (QB for multiple 1st rounders)
2. **Star WR Trade** - Tyreek Hill style trade (elite WR for 1st + 2nd round picks)
3. **Draft Trade-Up** - Moving up 10 spots in the 1st round for franchise QB
4. **Salary Dump** - Trading aging player with bad contract for cap relief
5. **Blockbuster** - Complex 3-for-3 multi-asset trade

### Interactive Calculator Mode

- Evaluate individual player values
- Assess draft pick values with Jimmy Johnson chart
- Build your own trade proposals (simplified)

## Usage

```bash
# Run the interactive demo (works from project root)
python demo/trade_value_demo/trade_value_demo.py

# Or with PYTHONPATH (alternative method)
PYTHONPATH=src python demo/trade_value_demo/trade_value_demo.py

# Can also run from the demo directory
cd demo/trade_value_demo
python trade_value_demo.py
```

## What You'll See

Each scenario shows:

- **Asset Details**: Player ratings, ages, contracts, or draft pick information
- **Trade Value Breakdown**: Calculated values for each asset
- **Fairness Evaluation**: Whether the trade is acceptable (0.80-1.20 ratio)
- **Analysis**: Context on why trades are fair/unfair, value differences

### Example Output

```
================================================================================
  Scenario 1: Elite QB for Multiple First Round Picks
================================================================================

Simulating a blockbuster QB trade similar to Russell Wilson to Denver (2022)

Team A (Contender) wants elite QB to win now
Team B (Rebuilding) trades franchise QB for draft capital

--- TEAM A SENDS (Rebuilding Team) ---
  Elite Franchise QB (QB, 90 OVR, Age 30)
    Trade Value: 520.3 units
    Base Value (no contract): 650.1 units
    Contract: 4yr @ $48.0M/yr

--- TEAM B SENDS (Contending Team) ---
  Round 1 Pick #15 (2025)
    Trade Value: 86.7 units
    Jimmy Johnson Chart: 86.7 units

  Round 1 Pick #20 (2026)
    Trade Value: 67.9 units
    Jimmy Johnson Chart: 71.5 units
    Future Discount: 95.00% (1 year out)

  ... (more picks)

TRADE PROPOSAL:
Team 1 sends: Elite Franchise QB (QB, 90 OVR, Age 30)
  Total Value: 520.3 units
Team 2 sends: Round 1 Pick #15, Round 1 Pick #20 (2026), ...
  Total Value: 485.2 units

Value Ratio: 0.933 (FAIR)
Acceptable: ✓ YES

💡 Analysis:
   - Elite QB valued at 520.3 units
   - Four draft picks valued at 485.2 units total
   - This is a FAIR trade
   ✓ Trade would likely be accepted by both teams
```

## Key Concepts Demonstrated

### Player Valuation
- **Power Curve**: `(overall_rating - 50)^1.8 / 3.0` creates non-linear value scaling
- **Position Tiers**: QB/Edge/LT = 2.0x, WR/CB = 1.5x, RB = 1.2x, etc.
- **Age Curves**: Position-specific peak years and decline rates
- **Contract Adjustments**: Good contracts (+20%), bad contracts (-30%)

### Draft Pick Valuation
- **Jimmy Johnson Chart**: Industry-standard exponential decay (pick #1 = 3000 points)
- **Future Discounting**: 5% discount per year for future picks
- **Uncertainty Penalty**: Wide projection ranges reduce value

### Trade Fairness
- **0.95-1.05**: VERY_FAIR (nearly even value)
- **0.80-1.20**: FAIR (acceptable trade)
- **0.70-1.30**: SLIGHTLY_UNFAIR (borderline)
- **<0.70 or >1.30**: VERY_UNFAIR (reject)

## Value Scale Reference

- **600-800 units**: Elite franchise cornerstone (top 5 QB, All-Pro edge rusher)
- **400-600 units**: Star player (top 10-15 at position)
- **200-400 units**: Quality starter (above average)
- **100-200 units**: Solid starter (average NFL starter)
- **50-100 units**: Depth player / rotational starter
- **<50 units**: Backup / special teamer

## Technical Details

### Calculator Configuration
- **Current Year**: 2025 (configurable)
- **Database Integration**: Optional (supports team needs analysis)
- **GM Archetype Integration**: Ready for Phase 1.3

### Files Used
- `src/transactions/models.py`: DraftPick, TradeAsset, TradeProposal
- `src/transactions/trade_value_calculator.py`: Core calculator logic
- `tests/transactions/test_trade_value_calculator.py`: 31 unit tests (100% passing)

## Next Steps

After exploring these scenarios, the next phase will:

1. **Real-World Benchmarking**: Validate against 10 historical NFL trades
2. **Phase 1.3**: Integrate GM archetypes for AI decision-making
3. **Trade Logic**: Implement accept/reject/counter-offer AI logic

## Feedback

This demo is part of Phase 1.2 development. Try different scenarios and see how the calculator handles:
- Age cliffs (RB at 30 vs QB at 30)
- Contract status (expiring deals, overpaid veterans)
- Draft pick value decay (future picks vs current year)
- Position premiums (QB worth 2x RB)

## Related Documentation

- **Implementation Plan**: `docs/plans/phase_1_2_trade_value_calculator_detailed.md`
- **Test Suite**: `tests/transactions/test_trade_value_calculator.py`
- **Phase 1.1 (Complete)**: `PHASE_1_1_COMPLETE.md` - GM Archetype System
