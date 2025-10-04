# Salary Cap Calculator Demo

A comprehensive demonstration of the **NFL Salary Cap System** showcasing real-world contract calculations, cap space management, and compliance validation.

## Overview

This demo tests the `CapCalculator` with realistic NFL player contracts, demonstrating:
- Signing bonus proration (5-year max rule)
- Dead money calculations (standard & June 1 designations)
- Contract restructuring mechanics
- Cap space calculations (top-51 vs 53-man roster)
- Transaction validation and compliance checking
- Real NFL contract validation (Mahomes, Wilson, etc.)

## Features

### What This Demo Shows

1. **Core Cap Calculations**
   - 5-year maximum proration rule enforcement
   - Annual signing bonus distribution
   - Cap hit calculations for multi-year contracts

2. **Dead Money Scenarios**
   - Standard player releases (immediate cap hit)
   - June 1 designation splits (deferred dead money)
   - Guaranteed salary acceleration
   - Real-world validation (Russell Wilson $85M dead cap)

3. **Contract Restructuring**
   - Convert base salary to signing bonus
   - Immediate cap relief calculations
   - Future year cap hit increases
   - Dead money risk analysis

4. **Cap Space Management**
   - Team cap space calculations
   - Top-51 rule (offseason) vs 53-man roster (regular season)
   - Transaction validation against available cap
   - Spending floor compliance (89% over 4 years)

5. **Real Contract Validation**
   - Patrick Mahomes 10-year, $450M contract
   - Russell Wilson $85M dead money scenario
   - Realistic multi-year contract structures

## Quick Start

### Prerequisites

```bash
# Ensure Python 3.13.5 and dependencies are installed
source .venv/bin/activate  # Activate virtual environment

# Install required dependencies
pip install pytest  # Testing framework (optional)
```

### Run the Demo

```bash
# Run the salary cap calculator demo
PYTHONPATH=src python demo/cap_calculator_demo/cap_calculator_demo.py
```

The demo will:
1. Initialize isolated demo database (`cap_demo.db`)
2. Create realistic NFL contracts (veteran, rookie, franchise tag)
3. Test core cap calculations (proration, dead money, restructures)
4. Validate against real NFL contracts
5. Display comprehensive cap summary reports
6. Clean up demo data

## Example Output

### Signing Bonus Proration

```
================================================================================
                        SIGNING BONUS PRORATION DEMO
================================================================================

Test 1: 4-Year Contract
   Signing Bonus: $20,000,000
   Contract Years: 4
   Annual Proration: $5,000,000 ✅
   Rule Applied: Standard proration

Test 2: 7-Year Contract (5-Year Max Rule)
   Signing Bonus: $35,000,000
   Contract Years: 7
   Annual Proration: $7,000,000 ✅
   Rule Applied: 5-year maximum proration

Test 3: Patrick Mahomes Contract Validation
   Signing Bonus: $141,000,000
   Contract Years: 10
   Annual Proration: $28,200,000 ✅
   Rule Applied: 5-year maximum (NOT prorated over 10 years!)

================================================================================
```

### Dead Money Calculations

```
================================================================================
                           DEAD MONEY CALCULATIONS
================================================================================

Scenario 1: Standard Release (Year 3 of 5-year contract)
   Contract: 5 years, $25M signing bonus ($5M/year proration)
   Release Year: 3
   Remaining Proration: 3 years × $5M = $15M

   Dead Money:
   - Current Year: $15,000,000
   - Next Year: $0
   - Total Dead Money: $15,000,000 ✅

Scenario 2: June 1 Designation (Same Contract)
   June 1 Split Activated ✓

   Dead Money:
   - Current Year: $5,000,000 (1 year proration)
   - Next Year: $10,000,000 (2 years proration)
   - Total Dead Money: $15,000,000 ✅
   - Cap Relief: Deferred $10M to next year

Scenario 3: Russell Wilson Validation
   Remaining Bonus: $50,000,000
   Guaranteed Salary: $35,000,000

   Dead Money:
   - Total Dead Cap Hit: $85,000,000 ✅
   - Matches Real NFL Contract ✓

================================================================================
```

### Contract Restructure Analysis

```
================================================================================
                         CONTRACT RESTRUCTURE DEMO
================================================================================

Original Contract (Year 2 of 4):
   Base Salary: $12,000,000
   Remaining Years: 3

Restructure Plan: Convert $9M base to signing bonus

Impact Analysis:
   New Proration: $9M / 3 years = $3,000,000/year

   Cap Savings (Year 2):
   - Old Base Salary: $12,000,000
   - New Proration: $3,000,000
   - Net Savings: $9,000,000 ✅

   Future Cap Hits (Years 3-4):
   - Each year increases by: +$3,000,000

   Dead Money Risk:
   - If released after Year 2: +$6,000,000 dead money
   - (2 remaining years × $3M proration)

================================================================================
```

### Team Cap Summary

```
================================================================================
                        DETROIT LIONS - CAP SUMMARY
================================================================================
Dynasty: demo_dynasty
Season: 2025

CAP BREAKDOWN
   Salary Cap:           $279,200,000
   Active Contracts:     $245,000,000
   Dead Money:           $8,500,000
   LTBE Incentives:      $2,200,000
   Practice Squad:       $3,900,000
   ────────────────────────────────────
   Total Used:           $259,600,000

   Cap Space Available:  $19,600,000 ✅ COMPLIANT

TOP CAP HITS (2025)
   1. QB Starting QB          $31,500,000
   2. EDGE Star Pass Rusher   $28,200,000
   3. WR Elite Receiver       $24,100,000
   4. OT Franchise Tackle     $22,800,000
   5. CB Top Corner          $18,500,000

COMPLIANCE STATUS
   League Year Compliance: ✅ PASS
   Spending Floor (89%): ✅ PASS
   June 1 Designations: 1 of 2 used

================================================================================
```

## Database

### Schema

The demo uses an isolated database (`cap_demo.db`) with the salary cap schema:

```sql
-- Core Tables
player_contracts          -- Contract storage
contract_year_details     -- Year-by-year cap hits
team_salary_cap          -- Team cap state
dead_money               -- Dead money tracking
cap_transactions         -- Transaction log
franchise_tags           -- Franchise/transition tags
rfa_tenders              -- RFA tender tracking
league_salary_cap_history -- Historical cap limits
```

### Database Isolation

The demo database:
- ✅ Does not affect production databases
- ✅ Can be safely deleted and regenerated
- ✅ Lives in `demo/cap_calculator_demo/data/cap_demo.db`
- ✅ Demonstrates dynasty-based data separation
- ✅ Shows realistic multi-contract scenarios

### Regenerating Database

```bash
# The demo automatically creates the database on first run
# To manually regenerate:

# 1. Delete existing database
rm demo/cap_calculator_demo/data/cap_demo.db

# 2. Run demo (will recreate automatically)
PYTHONPATH=src python demo/cap_calculator_demo/cap_calculator_demo.py
```

## File Structure

```
demo/cap_calculator_demo/
├── README.md                    # This file
├── cap_calculator_demo.py       # Main demo script
├── contract_examples.py         # Real NFL contract scenarios (planned)
├── cap_validator_demo.py        # Compliance validation demo (planned)
└── data/
    └── cap_demo.db              # Isolated demo database
```

## What Gets Tested

### 1. Core Calculations
- ✅ Signing bonus proration (including 5-year max rule)
- ✅ Cap hit calculations for multi-year contracts
- ✅ Dead money for all release scenarios
- ✅ June 1 designation mechanics

### 2. Contract Operations
- ✅ Contract creation (veteran, rookie, franchise tag)
- ✅ Contract restructuring for cap relief
- ✅ Player releases (standard & June 1)
- ✅ Contract extensions and modifications

### 3. Team Management
- ✅ Cap space calculations
- ✅ Top-51 vs 53-man roster accounting
- ✅ Transaction validation
- ✅ Multi-year cap projections

### 4. Compliance
- ✅ League year compliance (March 12 deadline)
- ✅ Spending floor validation (89% over 4 years)
- ✅ June 1 designation limits (2 per team)
- ✅ Real-world contract validation

## Real Contract Examples

The demo validates calculations against real NFL contracts:

### Patrick Mahomes (Chiefs)
- **Contract**: 10 years, $450M, $141M signing bonus
- **Key Test**: Proration over 5 years (max), not 10
- **Expected**: $28.2M annual proration

### Russell Wilson (Broncos Release)
- **Scenario**: One of largest dead cap hits in NFL history
- **Key Test**: $85M dead money calculation
- **Components**: Remaining bonus + guaranteed salary

### Typical Veteran Contract
- **Structure**: 4-5 year deal with backloaded salaries
- **Tests**: Restructure mechanics, cap savings, dead money risk

## Next Steps

After running this demo, explore:

1. **Contract Manager Demo** (planned)
   - Interactive contract creation
   - Multi-year cap planning
   - Extension negotiations

2. **Cap Validator Demo** (planned)
   - Compliance deadline validation
   - AI-driven cap management
   - Force compliance scenarios

3. **Integration with Free Agency** (future)
   - Cap-validated free agent signings
   - Competitive bidding with cap constraints
   - Trade deadline cap management

## Troubleshooting

### Database Errors

If you see "no such table" errors:
1. The demo automatically creates tables on first run
2. If issues persist, delete `data/cap_demo.db` and rerun
3. Check that SQLite3 is properly installed

### Import Errors

Ensure you run with proper Python path:
```bash
PYTHONPATH=src python demo/cap_calculator_demo/cap_calculator_demo.py
```

### Calculation Mismatches

If calculations don't match real NFL contracts:
- Check that you're using the correct CBA year (2024-2025 rules)
- Verify signing bonus and guaranteed amounts
- Review void years and option clauses (advanced features)

## Performance

Typical demo execution metrics:
- **Database Initialization**: ~50ms
- **Contract Creation**: ~5-10ms per contract
- **Cap Calculations**: <1ms per calculation
- **Full Demo Runtime**: ~500ms-1s

The cap calculator is optimized for real-time calculations during season simulation.

## Architecture

The demo uses the complete salary cap system:

```
CapCalculator          → Core mathematical operations
ContractManager        → Contract CRUD and modifications
CapDatabaseAPI         → Database persistence layer
CapValidator           → Compliance enforcement
CapUtils              → Reporting and formatting utilities
```

See `docs/plans/salary_cap_plan.md` for complete architecture documentation.

## Support

For questions or issues:
- Review salary cap documentation: `docs/plans/salary_cap_plan.md`
- Check test examples: `tests/salary_cap/test_cap_calculator.py`
- Review main project README: `CLAUDE.md`
- Examine demo code for implementation patterns

---

**Part of The Owners Sim - NFL Football Simulation Engine**
