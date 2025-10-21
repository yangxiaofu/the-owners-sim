# Offseason UI Demo

Interactive desktop UI demo for testing offseason functionality with placeholder events.

## Quick Start

```bash
# From project root
python demo/offseason_demo/main_offseason_demo.py
```

The demo will automatically:
1. Check if `offseason_demo.db` exists
2. Create database and generate mock data if needed
3. Launch desktop UI in offseason demo mode

## What's This Demo?

This is a **demonstration mode** of the desktop UI that starts directly in the offseason phase without needing to simulate a full season first. It's designed for incremental development and testing of offseason features.

### Philosophy

Instead of simulating 18 weeks of regular season + playoffs to reach the offseason, this demo:
- **Starts on February 9, 2025** (day after Super Bowl)
- **Pre-loads mock data**: 540+ players, 32 teams, realistic contracts
- **Pre-schedules 14 offseason events**: Franchise tags → Free agency → Draft → Roster cuts
- **Uses placeholder handlers**: Events show "Simulating: [Event]" modals instead of executing real logic

This approach allows you to:
- Rapidly iterate on UI without waiting for simulations
- Test event scheduling and calendar integration
- Build placeholder handlers that will be replaced with real logic incrementally
- See the complete offseason timeline immediately

## Demo Features

### What's Functional

#### ✅ Calendar Tab
- View all scheduled offseason events from Feb 9 → Sept 5, 2025
- Calendar widget with month/year navigation
- Event list showing upcoming deadlines, windows, and milestones
- Color-coded event types:
  - 🔴 **Deadline Events**: Franchise tag deadline, Free agency opens, Draft start/end, Roster cuts
  - 🔵 **Window Events**: Legal tampering period, Free agency window
  - 🟢 **Milestone Events**: Super Bowl, Combine, OTAs, Training Camp, Season start
- Click events to see details (date, type, description)

#### ✅ Team Tab
- View mock team rosters for all 32 NFL teams
- Realistic player data with position-based distributions
- Contract information with salary/cap hit/years
- Salary cap summary showing cap space, usage, and remaining space
- All data reads from `offseason_demo.db` database

#### ✅ Offseason Tab
- Current offseason phase display (starts in "post_super_bowl")
- Upcoming deadlines list
- Phase progression as calendar advances
- NFL offseason timeline overview

### What's Placeholder

#### ⚠️ Event Execution
When you trigger an event (e.g., advance calendar to a deadline), a modal dialog appears:

```
[Event Icon] Franchise Tag Deadline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulating: Franchise Tag Deadline

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Date: March 05, 2025
Type: deadline
Phase: franchise_tag_period

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Event simulation complete (placeholder)

                    [OK]
```

This is a **placeholder** - the actual event logic isn't implemented yet. The real handlers will:
- Apply franchise tags for AI teams
- Process free agent signings
- Simulate draft rounds
- Execute roster cuts

But for now, the placeholder lets you see the UI flow without implementing all the business logic first.

### What's Disabled

The following tabs are disabled in demo mode:
- ❌ **Season Tab**: No active regular season
- ❌ **Player Tab**: Individual player focus not needed for demo
- ❌ **League Tab**: League-wide stats not populated
- ❌ **Playoffs Tab**: No playoffs in offseason
- ❌ **Game Tab**: No games being played

These tabs will be enabled in the full application once you have a complete dynasty with regular season simulation.

## Mock Data Details

### Players (540-550 total)
- **Distribution by Position**:
  - QB: 64 (2 per team)
  - RB: 96 (3 per team)
  - WR: 128 (4 per team)
  - TE: 64 (2 per team)
  - OL: 128 (4 per team)
  - DL: 32 (1 per team)
  - LB: 32 (1 per team)
  - DB: 32 (1 per team)

- **Realistic Attributes**:
  - Overall rating: 40-99 (weighted toward 70-85 starters)
  - Age: 22-35 years old
  - Experience: 0-15 years
  - Position-specific attributes (speed, strength, awareness, etc.)

### Contracts (540-550 total)
- **Realistic Salary Ranges**:
  - QB: $1M - $50M
  - RB: $800K - $15M
  - WR: $900K - $25M
  - TE: $850K - $12M
  - OL: $800K - $18M
  - DL: $850K - $20M
  - LB: $850K - $15M
  - DB: $900K - $18M

- **Contract Structure**:
  - Years: 1-5 year deals
  - Cap Hit: Matches annual salary (no bonuses in mock data)
  - Total Value: Annual salary × years

### Salary Cap (32 teams)
- **2025 Salary Cap**: $255.4M per team
- **Team Usage**: 85-95% of available cap (realistic variance)
- **Remaining Space**: $12M - $38M per team
- **Deterministic Generation**: Uses seeded random for consistency

### Events (14 scheduled)
1. **Super Bowl** (Feb 9) - Season ends
2. **NFL Combine** (March 1) - Pre-draft evaluation
3. **Franchise Tag Deadline** (March 5) - Tag deadline
4. **Legal Tampering START** (March 11) - Pre-FA negotiations
5. **Legal Tampering END** (March 13) - Window closes
6. **Free Agency Opens** (March 13) - UFA signing begins
7. **Free Agency Window START** (March 13) - Window opens
8. **Draft Start** (April 24) - Round 1 begins
9. **Draft End** (April 27) - Round 7 complete
10. **OTAs Begin** (May 20) - Offseason workouts
11. **Training Camp** (July 23) - Camp opens
12. **Roster Cuts** (August 26) - 53-man deadline
13. **Season Begins** (Sept 5) - Week 1 kickoff
14. **Free Agency Window END** (Sept 5) - FA period ends

## Running the Demo

### First Time Setup

```bash
# From project root
python demo/offseason_demo/main_offseason_demo.py
```

You'll see:
1. Initialization progress (creating database, generating data)
2. Welcome dialog explaining demo features
3. Desktop UI with 3 functional tabs

### Resetting Demo Data

If you want to start fresh with new mock data:

```bash
# Delete database and reinitialize
python demo/offseason_demo/initialize_demo.py --reset
```

### Changing Demo Configuration

```bash
# Custom dynasty ID
python demo/offseason_demo/main_offseason_demo.py --dynasty "my_demo"

# Custom season year
python demo/offseason_demo/main_offseason_demo.py --season 2025
```

## Demo Workflow

### Recommended Testing Sequence

1. **Start Demo**: Launch `main_offseason_demo.py`

2. **Explore Calendar**:
   - Switch to Calendar tab (active by default)
   - Browse February 2025 (should show Super Bowl on Feb 9)
   - Advance through months to see all scheduled events
   - Click an event to see details

3. **Check Team Data**:
   - Switch to Team tab
   - View roster for your user team (defaults to team_id=9)
   - Check salary cap summary
   - Browse different positions

4. **Monitor Offseason Progress**:
   - Switch to Offseason tab
   - View current phase ("post_super_bowl" initially)
   - See upcoming deadlines
   - Understand phase transitions

5. **Advance Calendar** (when implemented):
   - Click "Advance to Deadline" button
   - Select "Franchise Tag Deadline" (March 5)
   - Watch placeholder modal appear
   - Verify calendar advances to March 5
   - Verify phase changes to "franchise_tag_period"

6. **Test Event Triggering** (when implemented):
   - Continue advancing through events
   - See placeholder modals for each event type
   - Verify status bar date updates
   - Verify phase label updates

## Next Steps for Implementation

This demo provides the foundation for incremental implementation. Here's how to proceed:

### Phase 1: Complete UI Integration (Current)
- ✅ Created entry point and initialization system
- ✅ Created placeholder event handlers
- ✅ Created demo domain models
- ⏳ **TODO**: Wire calendar advancement to event triggering
- ⏳ **TODO**: Connect offseason controller to calendar
- ⏳ **TODO**: Integrate placeholder handlers with event execution

### Phase 2: Implement Real Event Logic
Replace placeholder handlers with real business logic:

1. **Franchise Tag Events**:
   - Calculate tag amounts (non-exclusive, exclusive, transition)
   - AI team decision logic (which players to tag)
   - Cap space validation
   - Contract creation

2. **Free Agency Events**:
   - Player market value calculation
   - AI team decision logic (which FAs to sign)
   - Contract negotiations
   - Cap space validation
   - RFA tender handling

3. **Draft Events**:
   - Draft class generation
   - AI team draft board creation
   - Pick-by-pick simulation
   - Rookie contract generation

4. **Roster Events**:
   - Roster size validation
   - Cut player logic
   - Dead money calculation
   - Position requirement checking

### Phase 3: Connect to Full Season Loop
Once individual events work, integrate with full season simulation:

1. **Regular Season → Offseason Transition**:
   - Detect season end
   - Initialize offseason phase
   - Schedule offseason events
   - Preserve player/team state

2. **Offseason → Next Season Transition**:
   - Finalize rosters
   - Initialize new season
   - Generate regular season schedule
   - Reset to Week 1

## Architecture Notes

### Database Isolation
- Uses separate database: `data/database/offseason_demo.db`
- Dynasty ID: `ui_offseason_demo`
- Completely independent from main application
- Safe to delete and recreate for testing

### MVC Pattern
The demo follows proper MVC architecture:

```
View (Calendar/Team/Offseason) → Controller → Domain Model → Database API
```

- **Views**: PySide6/Qt widgets (calendar, roster tables, etc.)
- **Controllers**: Thin orchestration layer (≤10-20 lines per method)
- **Domain Models**: Business logic and data access
- **Database APIs**: Raw SQL queries and database operations

### Domain Models
Created but not yet fully integrated:
- `OffseasonDemoDataModel`: Wraps OffseasonController
- `CalendarDemoDataModel`: Manages event queries
- `TeamDemoDataModel`: Mock team/roster/cap data

These will be used when wiring up controllers to views.

### Event System
Uses existing event infrastructure:
- `DeadlineEvent`: Time-specific deadlines (franchise tags, draft start, etc.)
- `WindowEvent`: Time-bounded windows (legal tampering, free agency period)
- `MilestoneEvent`: Informational markers (Super Bowl, combine, OTAs)

All events stored in `events` table with `dynasty_id` isolation.

## Troubleshooting

### Demo Won't Launch
```
Error: Failed to create main window
```
**Solution**: Check that initialization completed successfully. Try:
```bash
python demo/offseason_demo/initialize_demo.py --reset
```

### Wrong Date/Phase Showing
```
Date shows regular season instead of offseason
```
**Solution**: Dynasty state may be incorrect. Reset:
```bash
python demo/offseason_demo/initialize_demo.py --reset
```

### Tabs Not Disabled
```
All tabs are enabled instead of just Calendar/Team/Offseason
```
**Solution**: Check `configure_demo_window()` in `main_offseason_demo.py`. The tab disabling logic may have failed silently.

### Events Not Showing in Calendar
```
Calendar is empty or missing events
```
**Solution**: Database may be missing events. Reinitialize:
```bash
python demo/offseason_demo/initialize_demo.py --reset
```

### "Placeholder" Modals Not Appearing
```
Clicking events does nothing
```
**Solution**: Placeholder handlers not wired up yet. This is expected - they need to be integrated with the calendar view's event triggering logic.

## Demo vs. Production

### Demo Characteristics
- ❌ No season simulation required
- ✅ Instant offseason access
- ✅ Placeholder event handlers
- ✅ Mock data (not real generated players)
- ✅ Separate database (safe testing)
- ⚠️ Limited functionality (only 3 tabs)

### Production Characteristics
- ✅ Full season simulation (regular season → playoffs → offseason)
- ✅ Real event execution (cap calculations, AI decisions, etc.)
- ✅ Procedurally generated players
- ✅ All 8 tabs functional
- ✅ Dynasty persistence across seasons
- ✅ Complete feature set

## Support

For questions or issues:
1. Check initialization logs: The demo prints detailed output during database setup
2. Verify database: `sqlite3 data/database/offseason_demo.db ".tables"`
3. Check event scheduling: `sqlite3 data/database/offseason_demo.db "SELECT * FROM events LIMIT 5;"`
4. Review CLAUDE.md for project architecture

## Related Documentation

- **`README.md`**: Terminal-based offseason demo (separate from UI demo)
- **`INITIALIZATION_README.md`**: Database initialization system docs
- **`docs/plans/ui_development_plan.md`**: Complete UI development roadmap
- **`docs/plans/offseason_plan.md`**: Offseason system implementation plan
- **`docs/architecture/ui_layer_separation.md`**: UI MVC architecture details

## Development Notes

### Why This Approach?

Traditional approaches would require:
1. Implement full season simulation (weeks of work)
2. Implement playoffs (more weeks)
3. Finally start on offseason features

With this demo approach:
1. ✅ Build offseason UI immediately
2. ✅ Test event scheduling and triggering
3. ✅ Implement features incrementally
4. ✅ See progress without simulating full seasons
5. ✅ Rapid iteration cycle (modify code → run demo → see results)

### Incremental Implementation
Each feature can be built independently:
- Franchise tags don't need free agency to work
- Free agency doesn't need draft to work
- Draft doesn't need roster cuts to work

Build one feature, test it with the demo, move to the next.

### Testing Strategy
- **Unit Tests**: Test individual event handlers
- **Integration Tests**: Test event triggering through calendar
- **UI Demo**: Manual testing of complete user workflows
- **Full Season**: Eventually test in production context

## Conclusion

This offseason UI demo provides a **working foundation** for incremental development. You can:
- See the complete offseason timeline
- Test calendar and event systems
- Build features one at a time
- Rapidly iterate without full simulations

As you implement real event logic, the placeholders get replaced with actual functionality, and the demo gradually becomes the production offseason experience.
