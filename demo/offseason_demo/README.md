# NFL Offseason Simulation Demo

Interactive terminal demo for testing the `OffseasonController` system.

## Quick Start

```bash
# From project root
PYTHONPATH=src python demo/offseason_demo/offseason_demo.py
```

## Overview

This demo allows you to navigate through the complete NFL offseason cycle:

- **Franchise Tag Period** (March 1-5) - Apply franchise/transition tags
- **Free Agency** (March 11+) - Browse and sign free agents
- **NFL Draft** (April 24-27) - Make draft selections
- **Roster Cuts** (August 26) - Finalize 53-man roster
- **Training Camp** (September) - Prepare for next season

## Features

### 1. Calendar Advancement

Navigate through the offseason timeline:

- **Advance 1 Day** - Move forward day-by-day
- **Advance 1 Week** - Skip ahead 7 days
- **Advance to Deadline** - Jump to specific NFL deadlines
- **Jump to Training Camp** - Fast-forward to season start

The system automatically:
- Detects phase transitions
- Triggers deadline events
- Updates available operations based on current phase

### 2. Franchise Tag Operations

Test franchise tag functionality:

- **View Candidates** - See eligible players for franchise tags
- **Apply Franchise Tag** - Test non-exclusive and exclusive tags
- **Apply Transition Tag** - Test transition tag mechanics
- **Check Tag Status** - Verify team tag usage limits

**Demo Notes:**
- Consecutive tag escalators (120%, 144%) work automatically
- Phase validation ensures tags only applied March 1-5
- Cap space integration validates all transactions

### 3. Free Agency Operations

Test free agent signing:

- **Browse Free Agent Pool** - View available free agents
- **Sign Free Agent** - Create contracts with cap validation
- **Apply RFA Tender** - Test 4 RFA tender levels
- **Simulate AI Activity** - Let AI teams sign free agents

**Demo Notes:**
- Legal tampering vs. open signing period validation
- Cap space checked before all signings
- Contract term validation (1-7 years)

### 4. Draft Operations

Test NFL Draft simulation:

- **View Draft Board** - See team's prospect rankings
- **Make Draft Selection** - Execute individual picks
- **Simulate Draft Round** - Auto-complete a full round
- **Simulate Entire Draft** - Auto-complete all 7 rounds

**Demo Notes:**
- 7 rounds, 32 picks per round (224+ total)
- Overall pick calculation automatic
- Round/pick validation enforced

### 5. Roster Management

Test roster operations:

- **View Team Roster** - See current roster (active + practice squad)
- **Cut Player** - Release players with dead money calculation
- **Finalize 53-Man Roster** - Validate roster for season start

**Demo Notes:**
- June 1 designation support for spreading dead money
- Roster size validation (53 active, 16 practice squad)
- Position requirement checking

## Demo Mode Notes

This is a **functional demo** of the `OffseasonController` API. Some features are stubbed:

### Working Now:
✅ Calendar advancement and phase detection
✅ Deadline tracking and triggering
✅ Phase validation for all operations
✅ Franchise/transition tag integration with salary cap system
✅ RFA tender calculations with compensation levels
✅ Contract term validation
✅ Cap space checking
✅ Action tracking

### Stubbed (Returns Empty Lists):
⚠️ Franchise tag candidates (awaits player/contract data)
⚠️ Free agent pool (awaits player free agency status)
⚠️ Draft board/class generation (awaits player generation system)
⚠️ Roster queries (awaits player roster data)

### Coming Soon:
🔜 Player/contract database integration
🔜 Draft class generation via player generation system
🔜 AI free agency decision logic
🔜 AI draft selection logic
🔜 Roster validation rules

## Example Session

```
NFL OFFSEASON DEMO - MAIN MENU
================================================================================

Current Date: February 16, 2025 (Sunday)
Current Phase: Post Super Bowl
Actions Taken: 0

Next Deadline: Franchise tag deadline
  Date: March 05, 2025
  Days Away: 17

--------------------------------------------------------------------------------
1. View State Summary
2. Advance Calendar
3. Franchise Tag Operations
4. Free Agency Operations
5. Draft Operations
6. Roster Management
7. View Actions Taken
Q. Quit
--------------------------------------------------------------------------------

Enter choice: 2

CALENDAR ADVANCEMENT
================================================================================

1. Advance 1 Day
2. Advance 1 Week
3. Advance to Next Deadline
4. Advance to Specific Deadline
5. Jump to Training Camp
B. Back to Main Menu

Enter choice: 3

Advancing to Franchise tag deadline...
Advanced to March 05, 2025
Phase changed: post_super_bowl → franchise_tag_period

Advanced 17 days
Current Phase: franchise_tag_period

[Return to main menu, now in franchise tag period]

Enter choice: 3

FRANCHISE TAG OPERATIONS
================================================================================

1. View Tag Candidates
2. Apply Franchise Tag (Non-Exclusive)
3. Apply Franchise Tag (Exclusive)
4. Apply Transition Tag
5. Check Team Tag Status
B. Back to Main Menu

Enter choice: 2

NON_EXCLUSIVE FRANCHISE TAG DEMO
--------------------------------------------------------------------------------

This is a demo. Enter a test player_id and team_id.
Player ID: 101
Team ID (1-32): 9

Applied NON_EXCLUSIVE franchise tag to player 101: $32,400,000

✓ NON_EXCLUSIVE Franchise Tag Applied!
  Tag Salary: $32,400,000
  Consecutive Tag #: 1
  Cap Space Remaining: $187,600,000
```

## Testing Different Scenarios

### Scenario 1: Franchise Tag a Star Player
1. Advance to March 5 (franchise tag deadline)
2. Apply franchise tag to player (test with player_id=101, team_id=9)
3. Check team tag status (should show 1 tag used)
4. Try to apply another tag (should fail - 1 tag limit)

### Scenario 2: Free Agency Signing Spree
1. Advance to March 13 (free agency opens)
2. Sign multiple free agents with different contract terms
3. Monitor cap space decreasing with each signing
4. Try to sign player without enough cap space (should fail)

### Scenario 3: Complete NFL Draft
1. Advance to April 24 (draft starts)
2. Make manual selections for user team
3. Simulate remaining rounds with AI
4. View complete draft results

### Scenario 4: Roster Cuts
1. Advance to August 26 (roster cut deadline)
2. Cut players to reach 53-man roster
3. Test June 1 designation for spreading dead money
4. Finalize roster for season start

## Architecture Notes

The demo uses the full `OffseasonController` API:

```python
controller = OffseasonController(
    database_path="data/database/nfl_simulation.db",
    dynasty_id="offseason_demo",
    season_year=2024,
    user_team_id=9,
    super_bowl_date=datetime(2025, 2, 9),
    enable_persistence=True,
    verbose_logging=True
)
```

All operations go through the controller, which delegates to:
- `TagManager` - Franchise/transition tags, RFA tenders
- `CapCalculator` - Cap space validation
- `DraftManager` - Draft operations (stub)
- `FreeAgencyManager` - Free agency operations (stub)
- `RosterManager` - Roster management (stub)

## Error Handling

The demo demonstrates proper error handling:

- **Phase Validation** - "Cannot sign free agents during legal tampering period"
- **Cap Space Validation** - "Insufficient cap space. Need $15M, have $10M"
- **Tag Limits** - "Team has already used their tag this season"
- **Contract Validation** - "Invalid contract length: 10 years (must be 1-7)"

## Next Steps

After testing the demo, the next steps are:

1. **Implement Manager Logic** - Fill in stub methods in DraftManager, FreeAgencyManager, RosterManager
2. **Player Data Integration** - Connect to player/contract database tables
3. **AI Decision Logic** - Implement AI team decision making for tags, FA, draft
4. **Full Season Integration** - Connect to SeasonCycleController for complete season loop

## Troubleshooting

**Demo crashes on startup:**
- Ensure database exists: `data/database/nfl_simulation.db`
- Check PYTHONPATH is set correctly: `PYTHONPATH=src`

**Phase validation errors:**
- Operations are locked to specific phases (e.g., can't sign FAs before March 13)
- Use calendar advancement to reach correct phase

**Empty results for candidates/pool:**
- This is expected - player data not yet integrated
- Focus on testing calendar, validation, and action tracking

## Support

This demo is part of the offseason implementation plan. See:
- `docs/plans/offseason_terminal_implementation_plan.md` - High-level plan
- `docs/plans/offseason_controller_implementation.md` - Controller spec
- `src/offseason/` - Implementation code
