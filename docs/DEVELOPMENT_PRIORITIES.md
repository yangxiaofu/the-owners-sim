# Development Priorities

## Completed Milestones
- ✅ **Milestone 1:** Game Cycle (stage-based progression)
- ✅ **Milestone 2:** Salary Cap & Contracts

---

## Priority Roadmap

### Core Simulation (Must Have)
| # | Milestone | Status | Dependencies |
|---|-----------|--------|--------------|
| 1 | Player Progression & Regression | Not Started | Training Camp (done) |
| 2 | Statistics & Record Keeping | Not Started | Game engine (done) |
| 3 | Injuries & IR System | Not Started | Stats |
| 4 | Trade System | Not Started | Cap (done), Stats |

### Simulation Realism
| # | Milestone | Status | Dependencies |
|---|-----------|--------|--------------|
| 5 | Realistic Game Scenarios | Not Started | Stats, Progression |
| 6 | Awards System (MVP, All-Pro) | Not Started | Stats |
| 7 | Schedule & Rivalries | Not Started | None |
| 8 | Draft Class Variation | Not Started | Stats |

### Intelligence Layer
| # | Milestone | Status | Dependencies |
|---|-----------|--------|--------------|
| 9 | GM Behaviors & Team Building | Not Started | Stats, Trades, Progression |
| 10 | Coach AI & Game Management | Not Started | Game Scenarios |
| 11 | Market Dynamics | Not Started | Stats, GM Behaviors |

---

## Dependency Flow

```
1. Player Progression  ─┐
                        ├─► 5. Game Scenarios ─┐
2. Statistics          ─┤                      │
                        ├─► 6. Awards          ├─► 9. GM Behaviors
3. Injuries            ─┤                      │
                        │                      │
4. Trades             ─┴─► 8. Draft Quality  ─┘
```

---

## Guiding Principle

**Core mechanics first, intelligence later.** AI decisions are only as good as the systems they operate on.