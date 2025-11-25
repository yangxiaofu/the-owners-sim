# Milestone 1: Game Cycle - Full Season Loop

## Goal
Simulate a complete NFL season from Week 1 through the offseason, then start the next year. Mimics Madden's simple stage-based progression.

---

## Season Flow (Madden-Style)

```
REGULAR SEASON (18 stages)
    Week 1 → Week 2 → ... → Week 18
            ↓
PLAYOFFS (4 stages)
    Wild Card → Divisional → Conference → Super Bowl
            ↓
OFFSEASON (6 stages)
    Re-signing → Free Agency → Draft → Roster Cuts → Training Camp → Preseason
            ↓
NEXT SEASON (Year + 1)
    Week 1 ...
```

---

## Stages Breakdown

### Regular Season
- **18 weeks** (Week 1 - Week 18)
- Each week: Simulate all games for that week
- Simple: Click "Advance" → all games play → move to next week

### Playoffs
- **Wild Card Weekend** (6 games)
- **Divisional Round** (4 games)
- **Conference Championships** (2 games)
- **Super Bowl** (1 game)

### Offseason (Madden-style, simplified)

| Stage | What Happens |
|-------|--------------|
| **Re-signing** | - View your expiring contracts<br>- Re-sign players you want to keep<br>- Players not re-signed become free agents |
| **Free Agency** | - All unsigned players hit the market<br>- AI teams sign players<br>- User can sign free agents |
| **NFL Draft** | - 7 rounds, 32 picks per round<br>- AI teams auto-pick<br>- User makes picks for their team |
| **Roster Cuts** | - Cut roster from 90 to 53<br>- AI auto-cuts lowest rated<br>- User can manually cut |
| **Training Camp** | - Ratings adjustments (optional)<br>- Finalize depth charts |
| **Preseason** | - Optional: 3 exhibition games<br>- Can skip entirely |

---

## Tollgates

### Tollgate 1: Stage Progression Works
- [ ] Click "Simulate" advances Week 1 → Week 2
- [ ] Continue through all 18 weeks
- [ ] UI shows correct week number
- [ ] Progress bar updates

### Tollgate 2: Playoffs Work
- [ ] After Week 18 → Wild Card
- [ ] Advance through all 4 playoff rounds
- [ ] Super Bowl completes → Offseason begins

### Tollgate 3: Offseason Stages Work
- [ ] Free Agency stage shows (placeholder OK)
- [ ] Draft stage shows (placeholder OK)
- [ ] Roster Cuts stage shows
- [ ] Training Camp stage shows
- [ ] Preseason stage shows (or skip option)

### Tollgate 4: Year Increment
- [ ] After Preseason → Year increments by 1
- [ ] New season starts at Week 1
- [ ] Status bar shows new year (e.g., "2026 Season")

### Tollgate 5: Free Agency (Basic)
- [ ] Expiring contracts flagged as free agents
- [ ] AI teams sign free agents (simple logic)
- [ ] User can view and sign free agents

### Tollgate 6: Draft (Basic)
- [ ] Draft class exists (can be placeholder/generated)
- [ ] 7 rounds execute
- [ ] AI teams pick based on needs
- [ ] User can make picks

### Tollgate 7: Roster Management
- [ ] Roster cuts reduce to 53
- [ ] AI auto-cuts work
- [ ] User can manually cut players

---

## Out of Scope (Future Milestones)
- Trade system
- Contract negotiations/extensions
- Franchise tags
- Salary cap enforcement
- Player progression/regression
- Injuries
- Scouting

---

## Files Involved

### Backend (`src/game_cycle/`)
- `stage_definitions.py` - Define all stages
- `stage_controller.py` - Orchestrate progression
- `stage_executor.py` - Execute stage logic
- `handlers/offseason.py` - Free agency, draft, cuts logic

### UI (`ui/`)
- `views/stage_view.py` - Main progression UI
- `controllers/stage_controller.py` - Connect UI to backend
- `game_cycle_window.py` - Main window

### Entry Point
- `main2.py` - Launch the game cycle UI

---

## Success Criteria

**Milestone is COMPLETE when:**
1. Can click through entire season (Week 1 → Super Bowl)
2. Offseason stages all advance correctly
3. Year increments and new season starts
4. Can repeat for multiple seasons
5. Free Agency and Draft have basic functionality (even if simple)