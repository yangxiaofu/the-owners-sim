# Draft Order Demo

Interactive terminal-based demonstration of the NFL draft order calculation system.

## Overview

This demo showcases how the NFL draft order is calculated based on:
- Regular season records (wins, losses, ties)
- Playoff results (round of elimination)
- Strength of schedule (tiebreaker)

## Features

### Main Menu Options

1. **View Round 1 (Picks 1-32)**
   - Complete Round 1 draft board
   - Color-coded by playoff elimination round
   - Shows team names, records, SOS values, and draft reasons

2. **View Other Rounds (2-7)**
   - View any round from 2-7
   - Same order as Round 1 (standard NFL draft rules)
   - Shows overall pick numbers

3. **View All Picks for a Team**
   - See all 7 picks for any team
   - Summary of team's record and draft position
   - Listed by round with overall pick numbers

4. **Show SOS Calculation Details**
   - Detailed breakdown of strength of schedule calculation
   - Lists all 17 opponents with their records
   - Shows how SOS is computed (average opponent win %)
   - Explains what the SOS value means for draft position

5. **Explain Tiebreaker Rules**
   - Complete NFL draft order rules
   - Draft order by playoff elimination round
   - Strength of schedule tiebreaker explanation
   - Examples of how tiebreakers work

6. **Draft Summary**
   - Total picks across all 7 rounds (224 picks)
   - Breakdown of Round 1 by draft reason
   - Quick statistics

## Usage

### Basic Usage

```bash
# From project root
PYTHONPATH=src python demo/draft_order_demo.py

# Or directly (if src is in PYTHONPATH)
python demo/draft_order_demo.py
```

### Interactive Navigation

The demo presents a numbered menu. Simply enter the option number and follow the prompts:

```
NFL DRAFT ORDER DEMO - MAIN MENU

Options:
  1. View Round 1 (Picks 1-32)
  2. View Other Rounds (2-7)
  3. View All Picks for a Team
  4. Show SOS Calculation Details
  5. Explain Tiebreaker Rules
  6. Draft Summary
  7. Exit

Select option (1-7):
```

### Example Sessions

**View Round 1:**
```
Select option: 1

2025 NFL DRAFT - ROUND 1

Pick   Team                         Record       SOS      Reason
-----------------------------------------------------------------------------------------------
1 (#1) New York Giants              4-13-0       0.564    Non-Playoff Team
2 (#2) Carolina Panthers            4-13-0       0.599    Non-Playoff Team
...
31 (#31) San Francisco 49ers        14-3-0       0.522    Super Bowl Loss
32 (#32) Kansas City Chiefs         14-3-0       0.536    Super Bowl Winner
```

**View Team Picks:**
```
Select option: 3
Enter team ID (1-32): 18

DRAFT PICKS: New York Giants

Total Picks: 7
Record: 4-13-0
SOS: 0.564
Reason: Non-Playoff Team

Round    Pick            Overall
-----------------------------------
Round 1  Pick 1          #1
Round 2  Pick 1          #33
Round 3  Pick 1          #65
...
```

**View SOS Details:**
```
Select option: 4
Enter team ID (1-32): 14

STRENGTH OF SCHEDULE DETAILS: Kansas City Chiefs

Opponents (17 games):
Opponent                     Record       Win %
--------------------------------------------------
New York Jets                7-10-0       0.412
Chicago Bears                8-9-0        0.471
...

SOS Calculation:
  Total opponent win percentage: 9.118
  Number of games: 17
  Strength of Schedule: 0.536

What does this mean?
  Average schedule - Opponents had average records
```

## Mock Data

The demo uses realistic mock data:
- 32 NFL teams with varied records (4-13 to 14-3)
- Complete playoff bracket:
  - 18 non-playoff teams
  - 6 Wild Card losers
  - 4 Divisional losers
  - 2 Conference Championship losers
  - 1 Super Bowl loser
  - 1 Super Bowl winner
- Realistic strength of schedule values (0.450-0.650 range)
- Mock schedules for SOS calculation

## Color Coding

The demo uses color-coded output for better readability:
- **Red**: Non-playoff teams (picks 1-18)
- **Yellow**: Wild Card losses (picks 19-24)
- **Cyan**: Divisional losses (picks 25-28)
- **Blue**: Conference losses (picks 29-30)
- **Green**: Super Bowl loser (pick 31)
- **Magenta**: Super Bowl winner (pick 32)

## NFL Draft Order Rules

### Round 1 Order (Picks 1-32)

1. **Picks 1-18**: Non-playoff teams
   - Sorted worst → best by record
   - Tiebreaker: Strength of schedule (easier schedule picks first)

2. **Picks 19-24**: Wild Card Round losers
   - Sorted worst → best by record
   - Tiebreaker: Strength of schedule

3. **Picks 25-28**: Divisional Round losers
   - Sorted worst → best by record
   - Tiebreaker: Strength of schedule

4. **Picks 29-30**: Conference Championship losers
   - Sorted worst → best by record
   - Tiebreaker: Strength of schedule

5. **Pick 31**: Super Bowl loser

6. **Pick 32**: Super Bowl winner

### Rounds 2-7

- Same order as Round 1
- 262 total picks (7 rounds × 32 teams)

### Strength of Schedule (SOS)

- **Formula**: Average win percentage of all opponents faced
- **Calculation**: (Sum of opponent win %) / 17 games
- **Usage**: Only for breaking ties between teams with identical records
- **Rule**: Lower SOS (easier schedule) = Higher draft pick

### Tiebreaker Example

If two teams have the same record:
- Team A: 4-13 record, SOS = 0.520 (harder schedule)
- Team B: 4-13 record, SOS = 0.480 (easier schedule)
- **Result**: Team B picks first (easier schedule)

## Technical Details

### Dependencies

- `offseason.draft_order_service`: Draft order calculation service
- `team_management.teams.team_loader`: Team name lookup

### Mock Data Generation

The demo generates:
- 32 team records with realistic win/loss distributions
- Playoff results matching 14-team playoff format
- 17-game schedules for each team (for SOS calculation)
- Pre-calculated SOS values for all teams

### Service Usage

```python
from offseason.draft_order_service import DraftOrderService, TeamRecord

# Create service
service = DraftOrderService(dynasty_id="demo_dynasty", season_year=2025)

# Calculate draft order
draft_picks = service.calculate_draft_order(standings, playoff_results)

# Result: 224 DraftPickOrder objects (7 rounds × 32 picks)
```

## Team ID Reference

Common team IDs for testing:
- 1: Buffalo Bills
- 14: Kansas City Chiefs
- 18: New York Giants
- 22: Detroit Lions
- 26: Carolina Panthers
- 31: San Francisco 49ers

See `src/constants/team_ids.py` for complete mapping.

## Implementation Notes

- No database dependencies - uses mock data only
- Color-coded terminal output using ANSI codes
- Interactive menu-driven interface
- Demonstrates complete 7-round draft calculation
- Shows realistic tiebreaker scenarios

## Future Enhancements

Potential additions:
- Trade pick simulation
- Compensatory pick calculation
- Historical draft order comparison
- Export draft board to CSV
- Multi-year draft order tracking
