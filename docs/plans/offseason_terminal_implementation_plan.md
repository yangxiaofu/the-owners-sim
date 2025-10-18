# Offseason Terminal Implementation Plan

**Version:** 1.0.0
**Created:** 2025-10-18
**Status:** Active Development Plan
**Target:** Complete NFL Season Cycle with Terminal Interface

---

## Executive Summary

### Goal

Complete the NFL season simulation cycle by implementing offseason functionality with a **terminal-based interface**, enabling a fully playable prototype from Week 1 → Super Bowl → Offseason → Next Season.

### Strategy

**Backend-First Approach:** Build offseason mechanics (franchise tags, free agency, draft, roster cuts) with a simple terminal UI for immediate testing and validation. Polished desktop UI comes later in Phase 2.

### Rationale

- ✅ **Fastest path to playable prototype** (2-4 weeks vs 6-8 weeks with UI)
- ✅ **Complete simulation loop** is more valuable than polished visuals
- ✅ **Terminal interface adequate for testing** franchise tags, FA, draft mechanics
- ✅ **Foundation built** - Phase 1 UI complete, can return to polish later
- ✅ **Natural checkpoint** - close the loop, then enhance presentation

---

## Current State vs Target State

### Current State (October 2025)

**Working Systems:**
- ✅ Complete regular season simulation (272 games)
- ✅ Playoff system (Wild Card → Super Bowl)
- ✅ Full season demo (`demo/full_season_demo/`) with automatic phase transitions
- ✅ Salary cap system with event integration
- ✅ Database persistence with dynasty isolation
- ✅ UI Phase 1 complete (tab structure, menus, styling)

**Missing:**
- ❌ Offseason mechanics (franchise tags, free agency, draft, cuts)
- ❌ Offseason phase integration into full season cycle
- ❌ Player generation system for draft classes
- ❌ Advisory/recommendation systems for AI teams

### Target State (4 Weeks)

**Deliverables:**
- ✅ Complete offseason backend implementation
- ✅ Terminal-based offseason interface (`demo/interactive_offseason_sim/`)
- ✅ Full season cycle: Regular Season → Playoffs → Offseason → Next Season
- ✅ Dynasty management with multi-season support
- ✅ Playable end-to-end NFL simulation

**Future (Weeks 5+):**
- Polish desktop UI (return to Phase 2)
- Implement beautiful offseason dashboard (spec exists)
- Advanced features and UX improvements

---

## Architecture Overview

### Offseason Phase Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Offseason Phase                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Franchise Tags (March 1-5)                             │
│     └─ TagManager + FranchiseTagEvent                      │
│                                                             │
│  2. Free Agency (March 11-13 onwards)                      │
│     └─ UFASigningEvent + RFAOfferSheetEvent                │
│                                                             │
│  3. Draft (Late April)                                     │
│     └─ PlayerGenerator + DraftEvent                        │
│                                                             │
│  4. Roster Cuts (August)                                   │
│     └─ PlayerReleaseEvent + Roster Management              │
│                                                             │
│  5. Calendar Advancement                                   │
│     └─ DeadlineEvent triggers at key dates                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Terminal Interface Structure

```
┌─────────────────────────────────────────────────────────────┐
│         Interactive Offseason Simulator (Terminal)          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Current Date: March 1, 2025                               │
│  Phase: Franchise Tag Period                               │
│  Dynasty: Eagles Rebuild                                   │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ OFFSEASON MENU                                        │ │
│  ├───────────────────────────────────────────────────────┤ │
│  │ 1. View Franchise Tag Candidates                     │ │
│  │ 2. Apply Franchise/Transition Tag                    │ │
│  │ 3. Browse Free Agents                                │ │
│  │ 4. Sign Free Agent                                   │ │
│  │ 5. View Draft Board                                  │ │
│  │ 6. Run Mock Draft                                    │ │
│  │ 7. View Roster (53-man)                              │ │
│  │ 8. Cut Player                                        │ │
│  │ 9. View Salary Cap Status                            │ │
│  │                                                       │ │
│  │ A. Advance 1 Day                                     │ │
│  │ B. Advance to Next Deadline                          │ │
│  │ C. Simulate to Training Camp                         │ │
│  │                                                       │ │
│  │ Q. Return to Main Menu / Save Dynasty                │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Enter choice:                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Integration with Full Season Demo

```
FullSeasonController (extended)
│
├─ Phase 1: REGULAR_SEASON → SeasonController
│
├─ Phase 2: PLAYOFFS → PlayoffController
│
├─ Phase 3: OFFSEASON → OffseasonController (NEW)
│   │
│   ├─ Franchise Tag Period (March 1-5)
│   ├─ Free Agency Period (March 11 onwards)
│   ├─ Draft (Late April)
│   └─ Roster Finalization (August)
│
└─ Phase 4: NEXT_SEASON → New cycle or exit
```

---

## Implementation Phases

### Week 1: Core Offseason Backend

**Focus:** Franchise tags and free agency mechanics

**Tasks:**
1. Implement `OffseasonController` base class
   - Calendar management for offseason dates
   - Deadline tracking and notifications
   - Phase state management

2. Franchise Tag System
   - Extend `TagManager` for offseason workflow
   - `FranchiseTagEvent` execution
   - Tag candidate identification logic
   - Consecutive tag escalation handling

3. Free Agency System
   - UFA pool generation (expired contracts)
   - `UFASigningEvent` with cap validation
   - RFA tender management
   - Simple market value estimation

**Deliverables:**
- `src/offseason/offseason_controller.py`
- Enhanced tag and FA event handlers
- Backend logic fully tested

---

### Week 2: Draft System & Player Generation

**Focus:** Draft class generation and selection mechanics

**Tasks:**
1. Player Generation Integration
   - Connect existing `PlayerGenerator` to draft
   - Generate realistic draft classes (7 rounds, 32 teams)
   - Position-based archetype selection

2. Draft Event System
   - `DraftSelectionEvent` implementation
   - Draft order calculation (reverse standings)
   - Pick trading logic (basic)

3. Roster Management
   - Roster expansion to 90 (training camp)
   - Roster cuts to final 53
   - `PlayerReleaseEvent` with dead money handling

**Deliverables:**
- `src/offseason/draft_manager.py`
- Draft class generation working
- Complete roster lifecycle

---

### Week 3: Terminal Interface

**Focus:** Build interactive terminal UI for offseason

**Tasks:**
1. Create `demo/interactive_offseason_sim/`
   - Menu system (similar to playoff sim)
   - User input handling
   - Clear display formatting

2. Implement Menu Options
   - Franchise tag candidate display
   - Free agent browser with filters
   - Draft board viewer
   - Salary cap status dashboard

3. Calendar Advancement
   - Day-by-day simulation
   - Jump to next deadline
   - Fast-forward through quiet periods

**Deliverables:**
- `demo/interactive_offseason_sim/offseason_sim.py`
- `demo/interactive_offseason_sim/display_utils.py`
- `demo/interactive_offseason_sim/README.md`
- Working terminal interface

---

### Week 4: Full Season Integration

**Focus:** Connect offseason to complete season cycle

**Tasks:**
1. Extend `FullSeasonController`
   - Add offseason phase detection
   - Transition from Super Bowl → Offseason
   - Transition from Offseason → Next Season

2. Dynasty Multi-Season Support
   - Season advancement logic
   - Persistent dynasty state across years
   - Team roster continuity

3. Testing & Polish
   - End-to-end season cycle test
   - Dynasty persistence validation
   - Bug fixes and edge cases

**Deliverables:**
- Complete season cycle working
- Multi-season dynasty support
- Comprehensive testing

---

## Key Features (Terminal UI)

### Franchise Tag Management
```
=================================================================
FRANCHISE TAG CANDIDATES - Detroit Lions
=================================================================
Deadline: March 5, 2025 (4 days remaining)

Tag Type    | Position | Cost      | Available
------------|----------|-----------|----------
Franchise   | DE       | $19.7M   | Yes
Franchise   | QB       | $32.4M   | Yes
Transition  | Any      | Varies   | Yes

Top Candidates (by contract expiration):
1. J. Sweat (DE, OVR 89) - Est. Market Value: $22M/yr
2. H. Reddick (LB, OVR 86) - Est. Market Value: $18M/yr
3. D. Goedert (TE, OVR 84) - Est. Market Value: $12M/yr

Cap Space Available: $12.5M
Status: ⚠️  CAUTION - Limited space for tags

Enter player number to tag (or 'b' for back):
```

### Free Agent Signing
```
=================================================================
FREE AGENT BROWSER - Offensive Line
=================================================================
Filter: Position=OL | Age=24-32 | Market Value ≤ $15M

Available Free Agents:
1. Q. Nelson (OG, OVR 92) - Market Value: $18M/yr [OVER BUDGET]
2. C. Lindstrom (OG, OVR 88) - Market Value: $14M/yr
3. J. Thuney (OG, OVR 85) - Market Value: $12M/yr
4. A. Norwell (OG, OVR 81) - Market Value: $8M/yr

Your Cap Space: $12.5M
Recommended: Option #4 or negotiate shorter deals

Enter player number to view details (or 'f' to change filter):
```

### Draft Board
```
=================================================================
DRAFT BOARD - Round 1, Pick #15
=================================================================
Team Needs: OL, LB, CB

Top Available Prospects:
1. O. Fashanu (OT, Penn St.) - Grade: 94 | Fit: 95%
   "Elite LT prospect, Day 1 starter potential"

2. J. Latham (OT, Alabama) - Grade: 92 | Fit: 90%
   "Strong RT/RG, high floor, versatile"

3. E. Cooper (LB, Texas A&M) - Grade: 91 | Fit: 88%
   "3-down linebacker, coverage skills excellent"

Your Selection: [Enter number or 't' for trade options]
```

---

## Data Flow & Persistence

### Offseason Timeline Storage

```sql
-- Events table already supports offseason events
INSERT INTO events (
    event_id,
    dynasty_id,
    event_type,
    event_date,
    event_data
) VALUES (
    'franchise_tag_deadline_2025',
    'eagles_rebuild',
    'DEADLINE',
    '2025-03-05',
    '{"deadline_type": "FRANCHISE_TAG", "actions": ["check_tags_applied"]}'
);
```

### Player Contract Updates

```sql
-- Franchise tag creates 1-year contract
UPDATE player_contracts
SET contract_years = 1,
    annual_salary = 19700000,
    contract_type = 'FRANCHISE_TAG'
WHERE player_id = 'DE_22_sweat'
  AND dynasty_id = 'eagles_rebuild';
```

### Draft Class Generation

```sql
-- New players created from draft
INSERT INTO players (player_id, name, position, overall, age, ...)
VALUES ('QB_DRAFT_2025_1', 'C. Williams', 'QB', 78, 22, ...);

-- Draft picks recorded
INSERT INTO draft_picks (dynasty_id, season, round, pick, team_id, player_id)
VALUES ('eagles_rebuild', 2025, 1, 15, 22, 'OT_DRAFT_2025_15');
```

---

## Testing Strategy

### Manual Testing Workflow

1. **Franchise Tag Period**
   - Run terminal sim to March 1
   - Apply tags to 2-3 players
   - Verify cap impact
   - Confirm tag appears in contracts

2. **Free Agency**
   - Browse FA pool
   - Sign 3-5 free agents
   - Validate cap space decreases
   - Confirm roster additions

3. **Draft**
   - View draft board
   - Make 7 selections
   - Verify rookies added to roster
   - Check draft order logic

4. **Roster Cuts**
   - Expand roster to 90 (post-draft)
   - Cut to final 53
   - Verify dead money calculations
   - Confirm roster compliance

### Automated Tests

```python
# tests/offseason/test_offseason_cycle.py
def test_complete_offseason_cycle():
    """Test full offseason: tags → FA → draft → cuts."""
    controller = OffseasonController(...)

    # March 1: Apply franchise tag
    tag_result = controller.apply_franchise_tag(player_id="DE_22_1")
    assert tag_result.success

    # March 13: Sign free agent
    fa_result = controller.sign_free_agent(player_id="OL_FA_1", years=3, salary=12000000)
    assert fa_result.success

    # April 24: Draft 7 rounds
    draft_result = controller.execute_draft()
    assert len(draft_result.selections) == 7

    # August 26: Cut to 53
    cut_result = controller.finalize_roster()
    assert controller.get_roster_count() == 53
```

---

## Success Criteria

### Functional Requirements

✅ **FR-1**: Apply franchise/transition tags to eligible players
✅ **FR-2**: Browse and sign unrestricted free agents with cap validation
✅ **FR-3**: Generate realistic draft classes (7 rounds, 224 players)
✅ **FR-4**: Execute draft with team needs consideration
✅ **FR-5**: Manage roster from 90 → 53 with cap implications
✅ **FR-6**: Advance calendar through offseason deadlines
✅ **FR-7**: Transition seamlessly from offseason to next season
✅ **FR-8**: Support multi-season dynasty progression

### User Experience Requirements

✅ **UX-1**: Terminal interface is intuitive and easy to navigate
✅ **UX-2**: Clear feedback on cap space and roster status
✅ **UX-3**: Helpful error messages when actions fail
✅ **UX-4**: Can complete full offseason in < 15 minutes
✅ **UX-5**: Dynasty saves and loads correctly across sessions

### Technical Requirements

✅ **TR-1**: All offseason events integrate with existing event system
✅ **TR-2**: Dynasty isolation maintained throughout offseason
✅ **TR-3**: Database schema supports multi-season data
✅ **TR-4**: Calendar continuity from playoffs through offseason
✅ **TR-5**: Player generation produces balanced, realistic prospects

---

## Future Work (Post-Completion)

### Immediate Next Steps (After Week 4)
1. Return to UI development (Phase 2: Season/Team views)
2. Implement offseason dashboard with advisory system
3. Polish and enhance terminal interface

### Long-Term Enhancements
- AI team decision-making for franchise tags/FA/draft
- Advanced draft scouting and prospect evaluation
- Contract negotiation system (extensions, restructures)
- Trade system (player trades, draft pick trades)
- Coaching changes and staff management
- Injury system and player development
- Multi-year statistical tracking and career progression

---

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Player generation complexity | Medium | Use existing `PlayerGenerator`, keep draft classes simple initially |
| Cap validation edge cases | Medium | Comprehensive unit tests, validate against known scenarios |
| Terminal UI tedious to use | Low | Keep menu options clear, provide shortcuts, good formatting |
| Integration bugs with full season | Low | Incremental testing, reuse proven season/playoff patterns |
| Dynasty persistence issues | Low | Database schema well-established, follow existing patterns |

---

## Timeline Summary

**Week 1**: Core backend (tags, FA)
**Week 2**: Draft system and player generation
**Week 3**: Terminal interface
**Week 4**: Integration and testing

**Total**: 4 weeks to complete offseason simulation cycle

**Post-4 Weeks**: Return to desktop UI development with fully working backend

---

## Appendix: Key File Locations

### New Files to Create

```
src/offseason/
├── offseason_controller.py       # Main offseason orchestrator
├── draft_manager.py               # Draft execution and logic
└── roster_manager.py              # Roster expansion/cuts

demo/interactive_offseason_sim/
├── offseason_sim.py               # Terminal UI entry point
├── display_utils.py               # Formatting and display helpers
├── menu_handler.py                # Menu system and input
└── README.md                      # Usage documentation
```

### Modified Files

```
demo/full_season_demo/
└── full_season_controller.py     # Add offseason phase

src/season/
└── season_cycle_controller.py    # Extend for multi-season support

src/player_generation/
└── (existing files)               # Integration for draft classes
```

---

**Document Version**: 1.0.0
**Created**: 2025-10-18
**Status**: Active Development Plan
**Next Review**: After Week 2 completion
**Owner**: The Owner's Sim Development Team
