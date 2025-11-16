# Strength of Schedule (SOS) Demo

## Overview

This demo script verifies the Strength of Schedule (SOS) calculation system used for NFL draft order tiebreakers. It demonstrates how SOS is calculated, how it affects draft position, and shows real examples of tiebreaker scenarios.

## Purpose

- **Verify SOS calculations** with comprehensive mock data
- **Demonstrate tiebreaker logic** for teams with identical records
- **Visualize draft order** with formatted tables and explanations
- **Educational tool** for understanding NFL draft order rules

## Usage

```bash
# Run the demo
PYTHONPATH=src python demo/sos_demo.py
```

## What This Demo Shows

### 1. SOS Formula Explanation
- Mathematical formula: `SOS = sum(opponent_win_pcts) / 17`
- Step-by-step calculation process
- Interpretation of SOS values (0.000 to 1.000 range)

### 2. NFL Draft Order Rules
- Primary tiebreaker: Lower win percentage
- Secondary tiebreaker: Lower SOS (easier schedule = higher pick)
- Tertiary tiebreakers: Division/conference rules

### 3. Complete SOS Table
- All 32 teams with records, win percentages, and SOS values
- Teams sorted by draft order (worst record to best)
- Highlighted tied teams to show SOS tiebreaker in action

### 4. Detailed Tiebreaker Demonstrations
- Multiple scenarios with 2-3 teams having identical records
- Opponent analysis for each team
- SOS comparison and draft order resolution
- Clear explanations of why one team picks before another

## Mock Data Design

### Team Records
- **32 realistic team records** distributed across win-loss scenarios
- **Multiple tied groups** (2-3 teams per record) to demonstrate tiebreakers
- Examples:
  - Teams 1 & 2: Both 4-13 (0.235 win%)
  - Teams 5, 6, 7: All 6-11 (0.353 win%)
  - Teams 14, 15, 16: All 10-7 (0.588 win%)

### Schedules
- **17-game schedules** for all 32 teams (matches NFL regular season)
- **Varied opponent strength** to create different SOS values
  - Bottom teams: Mix of easy/hard schedules
  - Top teams: Generally harder schedules (face better competition)
- **Designed tiebreakers**: Teams with identical records face different opponents

### SOS Value Distribution
- **Range**: 0.432 to 0.751 (realistic NFL range)
- **Interpretation**:
  - < 0.450: Easy schedule (below-average opponents)
  - 0.450-0.550: Average schedule
  - > 0.550: Hard schedule (above-average opponents)

## Example Output

```
================================================================================
STRENGTH OF SCHEDULE DEMONSTRATION
================================================================================

Team   Record       Win%     SOS      Notes
--------------------------------------------------------------------------------
32     2-15-0       0.118   0.702
31     3-14-0       0.176   0.498
2      4-13-0       0.235   0.751   TIED (SOS breaks tie)
1      4-13-0       0.235   0.536   TIED (SOS breaks tie)
...

================================================================================
TIEBREAKER DEMONSTRATIONS
================================================================================

────────────────────────────────────────────────────────────────────────────────
SCENARIO: 2 teams finished 4-13-0 (0.235 win%)
────────────────────────────────────────────────────────────────────────────────

Team 1:
  Record: 4-13-0
  Opponents: [31, 32, 3, 4, 5]... (first 5 of 17)
  Opponent avg win%: 0.536
  SOS: 0.536
  Difficulty: AVERAGE schedule

Team 2:
  Record: 4-13-0
  Opponents: [20, 22, 23, 24, 25]... (first 5 of 17)
  Opponent avg win%: 0.751
  SOS: 0.751
  Difficulty: HARDER schedule

────────────────────────────────────────
DRAFT ORDER RESULT:
────────────────────────────────────────
  #1: Team 1 picks FIRST (SOS: 0.536 - easiest schedule)
  #2: Team 2 picks LAST (SOS: 0.751 - hardest schedule)

Key Principle: LOWER SOS = HIGHER DRAFT PICK
(Teams that faced easier schedules pick before teams with harder schedules)
```

## Key Takeaways

1. **SOS = Average Opponent Win%**: Sum all 17 opponents' win percentages and divide by 17
2. **Lower SOS = Higher Pick**: Teams with easier schedules get higher draft picks
3. **Tiebreaker Importance**: Critical for teams with identical records (happens frequently in NFL)
4. **Fair System**: Can't game the schedule - opponent strength is predetermined

## Technical Details

### Dependencies
- `src/offseason/draft_order_service.py` - DraftOrderService for SOS calculation
- `TeamRecord` dataclass for team standings
- No database required (uses mock data)

### Mock Data Functions
- `create_mock_team_records()` - Generates 32 teams with realistic records
- `create_mock_schedules()` - Creates 17-game schedules with varied opponent strength
- `calculate_all_sos()` - Computes SOS for all teams using DraftOrderService
- `display_sos_table()` - Formats and displays results
- `demonstrate_tiebreaker()` - Shows detailed tiebreaker analysis

### Calculation Method
```python
service = DraftOrderService(dynasty_id="demo", season_year=2025)
sos = service.calculate_strength_of_schedule(
    team_id=team_id,
    all_standings=records,
    schedule=schedule
)
```

## Use Cases

### For Developers
- Verify SOS calculation correctness
- Test edge cases (identical SOS values, extreme schedules)
- Validate tiebreaker logic before database integration

### For Testing
- Standalone verification without database dependency
- Quick validation of formula changes
- Regression testing for draft order changes

### For Documentation
- Educational tool for understanding NFL draft order
- Visual demonstration of tiebreaker rules
- Reference for explaining SOS to users

## Related Files

- **Source**: `src/offseason/draft_order_service.py` - Production SOS calculation
- **Demo**: `demo/sos_demo.py` - This standalone demo
- **Tests**: `tests/offseason/test_draft_order_service.py` - Unit tests for SOS logic

## Future Enhancements

- [ ] Add interactive mode to modify team records/schedules
- [ ] Compare different tiebreaker scenarios (division rank, conference rank)
- [ ] Export results to CSV or JSON
- [ ] Add visualization (charts/graphs of SOS distribution)
- [ ] Support for custom season lengths (non-17 game schedules)
