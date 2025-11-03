# Transaction Debug System

Complete visibility into AI transaction decision-making with full trace logging and formatted reports.

## Overview

The Transaction Debug System provides comprehensive insight into how the AI evaluates and generates trade proposals for all 32 NFL teams. It shows:

- **Probability calculations** for each team (base probability, modifiers, random roll, pass/fail)
- **Proposal generation details** (targets considered, assets offered, fairness ratios)
- **Filter pipeline** (GM personality filters, validation checks, pass/fail status)
- **Daily and multi-day summaries** (aggregate statistics, trends over time)

## Features

✅ **Full Trace Logging** - See every calculation step, not just final results
✅ **All 32 Teams** - Shows evaluated AND skipped teams (probability check failures)
✅ **Proposal Details** - View ALL proposals generated, not just accepted ones
✅ **Color-Coded Output** - Green = pass, Red = fail, Yellow = probability values
✅ **Interactive Menu** - Simulate single days, multiple days, or custom periods
✅ **Multi-Day Summaries** - Aggregate statistics across simulation periods

## Quick Start

### 1. Run the Debug Script

```bash
PYTHONPATH=src python demo/transaction_debug/transaction_debug.py
```

### 2. Interactive Menu

```
TRANSACTION DEBUG MENU
═══════════════════════════════════════════════
Current Date: 2024-09-22 (Week 3)

1. Simulate 1 day with full transaction trace
2. Simulate 7 days (1 week) with daily reports
3. Simulate custom number of days
4. Show multi-day summary
5. Exit
═══════════════════════════════════════════════
```

### 3. Select an Option

- **Option 1**: Detailed single-day report showing all teams
- **Option 2**: Week-long simulation with daily reports
- **Option 3**: Custom simulation period (e.g., 14 days for 2 weeks)
- **Option 4**: Summary statistics across all simulated days
- **Option 5**: Exit

## Report Structure

### Daily Report

Each daily report contains three main sections:

#### 1. Probability Evaluation (All 32 Teams)

Shows probability calculations for every team, including:

```
✓ TEAM 1 (Bills): EVALUATED
  Base Probability: 0.150 (GM: 0.30 × System: 0.50)
  Modifiers Applied:
    • Playoff Push: 1.50× (Currently in playoff position)
    • Deadline Proximity: 2.00× (2 days until deadline)
  Final Probability: 0.450
  Random Roll: 0.310 → EVALUATE ✓

✗ TEAM 2 (Dolphins): SKIPPED
  Base Probability: 0.200
  Final Probability: 0.200
  Random Roll: 0.680 → SKIP ✗
```

**Evaluated Teams** (verbose): Full breakdown with all modifiers
**Skipped Teams** (compact): Quick summary showing why probability check failed

#### 2. Proposal Generation (Evaluated Teams Only)

Shows proposal details for teams that passed probability check:

```
TEAM 1 (Bills): 3 proposals generated, 1 accepted

  Proposal #1: REJECTED ✗
    Target: WR Jerry Rice (Value: 1200)
    Offering: QB Jim Kelly, 2025 2nd
    Total Value: 1050
    Fairness Ratio: 0.88
    Rejection: GM Star Chasing Filter (won't trade star QB)

  Proposal #2: ACCEPTED ✓
    Target: CB Deion Sanders (Value: 1000)
    Offering: CB Antoine Winfield, LB London Fletcher
    Total Value: 1000
    Fairness Ratio: 1.00
    Filters: GM ✓ | Validation ✓ | Cap ✓
```

**For Each Proposal**:
- Target player (name, position, OVR, value)
- Assets offered (players, draft picks)
- Total value and fairness ratio
- Filter results (GM philosophy, validation, cap compliance)
- Final status (ACCEPTED or REJECTED)
- Rejection reason (if rejected)

#### 3. Daily Summary

Aggregate statistics for the day:

```
DAILY SUMMARY
═══════════════════════════════════════════════
Teams Evaluated: 2/32 (6.25%)
Total Proposals Generated: 5
Proposals Accepted: 1
Proposals Rejected: 4

Rejection Reasons:
  • GM Filters: 2
  • Validation: 1
  • Cap Space: 1
═══════════════════════════════════════════════
```

### Multi-Day Summary

Aggregate statistics across multiple days:

```
MULTI-DAY TRANSACTION SUMMARY
═══════════════════════════════════════════════
7 Days Simulated

Average Teams Evaluated per Day: 2.3
Average Proposals per Day: 4.7
Average Accepted per Day: 0.9
Total Trades Executed: 6

Day-by-Day Breakdown:
  2024-09-22: 2 teams → 5 proposals → 1 trades
  2024-09-23: 3 teams → 7 proposals → 2 trades
  2024-09-24: 1 teams → 2 proposals → 0 trades
  ...
═══════════════════════════════════════════════
```

## Understanding Probability Calculations

### Base Probability

```
Base Probability = GM Trade Frequency × System Base Probability
                 = 0.30 × 0.05 = 0.015 (1.5% per day)
```

### Modifiers

1. **Playoff Push** (1.5×): Weeks 10+ for teams in playoff hunt
2. **Losing Streak** (1.25× per game): 3+ game losing streaks
3. **Cooldown** (0.2×): 7 days after last trade
4. **Deadline Proximity** (2.0×): Final 3 days before trade deadline

### Final Calculation

```
Final Probability = min(Base Probability × Modifiers, 1.0)
Random Roll = random.random()  # 0.0-1.0
Decision = Roll < Final Probability
```

## Common Use Cases

### 1. Debug Proposal Generation

**Problem**: "Why isn't Team X generating any trade proposals?"

**Solution**: Run single-day simulation and check:
1. Did Team X pass probability check? (Check "Probability Evaluation" section)
2. Does Team X have CRITICAL/HIGH needs? (Check "Proposal Generation" section)
3. Are there viable trade targets in the league?
4. Does Team X have surplus assets to offer?

### 2. Analyze Rejection Reasons

**Problem**: "Why are all proposals being rejected?"

**Solution**: Run multi-day simulation and check "Rejection Reasons":
- **GM Filters**: GM philosophy blocking trades (e.g., won't trade stars)
- **Validation**: Cap space, roster minimums, or contract issues
- **Fairness**: Trade value ratio outside acceptable range (0.80-1.20)

### 3. Tune Probability System

**Problem**: "Too many/too few trades happening"

**Solution**: Run 7-day simulation and check:
- Average teams evaluated per day (target: 2-4 teams)
- Average proposals per day (target: 4-8 proposals)
- Average accepted per day (target: 0.5-1.5 trades)

Adjust constants in `TransactionAIManager`:
- `BASE_EVALUATION_PROBABILITY` (default: 0.05 = 5% per day)
- Modifier values (playoff push, losing streak, etc.)

### 4. Test GM Personality Filters

**Problem**: "Do GM filters work correctly?"

**Solution**: Run single-day simulation for specific teams:
- Check "Proposal #X: REJECTED" entries
- Look for "GM Star Chasing Filter", "GM Cap Management", etc.
- Verify rejection reasons match GM archetype traits

## Architecture

### Components

```
transaction_debug.py
  │
  ├── TransactionAIManager (debug_mode=True)
  │   ├── _should_evaluate_today() → returns (bool, debug_data)
  │   └── evaluate_daily_transactions() → returns (proposals, debug_data)
  │
  ├── TradeProposalGenerator (debug_mode=True)
  │   └── generate_trade_proposals() → returns (proposals, debug_data)
  │
  └── DebugReportFormatter
      ├── format_daily_report()
      └── format_multi_day_summary()
```

### Debug Data Structure

```python
{
    "date": "2024-09-22",
    "phase": "REGULAR_SEASON",
    "week": 3,
    "teams_evaluated": [
        {
            "team_id": 1,
            "team_name": "Bills",
            "probability_check": {
                "base_prob": 0.15,
                "modifiers": {
                    "playoff_push": {"applied": True, "value": 1.5},
                    "losing_streak": {"applied": False},
                    ...
                },
                "final_prob": 0.45,
                "random_roll": 0.31,
                "decision": "EVALUATE"
            },
            "proposals_generated": 3,
            "proposals_accepted": 1,
            "proposal_generation": {
                "potential_targets": [...],
                "surplus_assets": [...],
                "proposal_attempts": [...]
            }
        },
        ...
    ]
}
```

## Tips and Best Practices

### 1. Use Color Output

The debug system uses ANSI color codes for better readability:
- 🟢 **Green**: Pass, success, positive outcome
- 🔴 **Red**: Fail, rejection, negative outcome
- 🟡 **Yellow**: Probabilities, modifiers, neutral values
- 🔵 **Cyan**: Structural elements, dates, metadata

**Note**: Colors may not display correctly in all terminals. If colors don't work, edit `DebugReportFormatter` constructor:

```python
formatter = DebugReportFormatter(use_colors=False)
```

### 2. Save Reports to File

Redirect output to save complete reports:

```bash
PYTHONPATH=src python demo/transaction_debug/transaction_debug.py > transaction_report.txt
```

Then select your simulation options and the output will be saved to file.

### 3. Focus on Specific Teams

To debug specific teams, modify `transaction_debug.py`:

```python
# Only evaluate specific teams
for team_id in [1, 7, 22]:  # Bills, Browns, Lions
    ...
```

### 4. Adjust Simulation Period

For comprehensive testing, simulate longer periods:
- **1 week (7 days)**: Quick check of basic functionality
- **2 weeks (14 days)**: Better statistical sample
- **1 month (30 days)**: Comprehensive trend analysis

## Troubleshooting

### Issue: No trades happening

**Check:**
1. Current week (trades only allowed Weeks 1-8)
2. Probability modifiers (too many cooldowns?)
3. Team needs (teams need CRITICAL/HIGH needs)
4. Available targets (are there players matching needs?)

### Issue: All proposals rejected

**Check:**
1. GM philosophy filters (too restrictive?)
2. Trade value fairness (ratio outside 0.80-1.20?)
3. Cap space (teams over cap can't acquire players)
4. Roster minimums (teams need depth at positions)

### Issue: Debug data missing

**Check:**
1. `debug_mode=True` in TransactionAIManager initialization
2. Return tuple unpacking: `proposals, debug_data = evaluate_daily_transactions(...)`
3. Check for exceptions in console output

## Future Enhancements

Planned features for future versions:

- [ ] Export reports to JSON/CSV for analysis
- [ ] Web-based UI for interactive report viewing
- [ ] Compare multiple simulation runs side-by-side
- [ ] Filter reports by team, position, or outcome
- [ ] Timeline visualization of probability trends
- [ ] Detailed trade value calculation breakdowns

## Support

For issues or questions:
1. Check this README for common solutions
2. Review `AI_TRANSACTION_DAILY_FLOW.md` for system architecture
3. Check transaction system logs in application output
4. Report bugs via project issue tracker

## Related Documentation

- `AI_TRANSACTION_DAILY_FLOW.md` - Transaction system architecture
- `docs/plans/ai_transactions_plan.md` - Original implementation plan
- `src/transactions/` - Transaction system source code
