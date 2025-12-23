# Re-signing View Mock Demo - Fast Testing Guide

## Overview
`resigning_view_mock_demo.py` - **Zero-database UI testing** for the ResigningView. Perfect for rapid iteration on layout, styling, and behavior without simulating through a full season.

**Startup Time**: ~1 second (vs. ~5+ minutes to simulate to re-signing stage)

## Quick Start

```bash
# Default scenario (8 players, cap compliant)
python demos/resigning_view_mock_demo.py

# Over cap scenario (needs restructures)
python demos/resigning_view_mock_demo.py --scenario over_cap

# Elite players only
python demos/resigning_view_mock_demo.py --scenario stars

# Many players (15+ contracts)
python demos/resigning_view_mock_demo.py --scenario many_players

# Minimal (2-3 players for simple testing)
python demos/resigning_view_mock_demo.py --scenario minimal
```

## Available Scenarios

### 1. `default` (Recommended for general testing)
- **8 expiring contracts** (mix of positions)
- **Cap compliant** ($45.2M available)
- **Mix of recommendations**: QB/WR/EDGE recommended, aging OL/CB not recommended
- **2 restructure proposals** (EDGE + CB) ✨
- **Full 53-man roster** for early cuts testing ✨
- **Best for**: General UI development, toggle behavior, cap calculations, restructures

### 2. `over_cap` (Test cap pressure)
- **3 expiring contracts**
- **OVER CAP** by $15.3M (needs cuts/restructures)
- **2 restructure proposals** from GM (WR and EDGE)
- **Full 53-man roster** for early cuts testing
- **Best for**: Cap relief UI, restructure cards, warning states, early cuts dialog

### 3. `stars` (Elite players only)
- **4 contracts** (all 90+ OVR)
- **Healthy cap** ($62M available)
- **All recommended** for extension
- **Best for**: High-value contracts, priority tier 1 players

### 4. `many_players` (Stress test)
- **17 expiring contracts** (full positional spread)
- **Moderate cap** ($38M available)
- **Mix of recommendations** (varies by position)
- **Best for**: Table scrolling, performance, layout with many rows

### 5. `minimal` (Simple testing)
- **2 contracts** (QB + WR)
- **Plenty of cap** ($50M available)
- **Mixed recommendations**
- **Full 53-man roster** included
- **Best for**: Quick layout checks, signal testing, debugging

**Note**: All scenarios now include a full 53-man roster for testing roster health display and early cuts dialog!

## What You Can Test

### ✅ Works (No Database Needed)
- **Layout & Styling**: All visual elements render correctly
- **Toggle Behavior**: Approve/reject switches work
- **Cap Calculations**: Projected cap updates in real-time
- **GM Reasoning**: Hover cards display correctly
- **Restructure Cards**: Collapsible proposal cards (default + over_cap scenarios) ✨
- **Roster Health Widget**: Position group bars display correctly ✨
- **Sorting**: Table columns sort correctly
- **Responsive Layout**: 50/50 split resizes properly
- **Early Cuts Button**: Button appears and is clickable ✨

### ⚠️ Limited (Mock Data Only)
- **Signal Emission**: Signals fire but don't persist
- **Dialog Interactions**: Dialogs open but can't save (no DB)
- **GM Re-evaluation**: Button works but data doesn't refresh

### ❌ Won't Work (Requires Database)
- **Contract Details**: Full contract history lookup
- **Actual Signings**: Persisting approved extensions
- **Cap Rollover**: Reading from previous season

## Development Workflow

### Fast Iteration Loop (RECOMMENDED)
1. **Launch mock demo** with desired scenario
2. **Make changes** to `resigning_view.py`
3. **Restart demo** (takes 1 second)
4. **See changes immediately**

```bash
# Terminal 1: Edit code
vim game_cycle_ui/views/resigning_view.py

# Terminal 2: Run demo (restart after each change)
python demos/resigning_view_mock_demo.py
```

### Testing Different States
```bash
# Test normal state
python demos/resigning_view_mock_demo.py --scenario default

# Test cap pressure
python demos/resigning_view_mock_demo.py --scenario over_cap

# Test many rows (scrolling, performance)
python demos/resigning_view_mock_demo.py --scenario many_players
```

## Customizing Mock Data

Edit `resigning_view_mock_demo.py` to add your own scenarios:

```python
def create_my_scenario() -> tuple[Dict, List[Dict], List[Dict]]:
    """My custom test scenario."""
    cap_data = {
        "available_space": 30_000_000,
        "salary_cap_limit": 255_400_000,
        "total_spending": 225_400_000,
        "dead_money": 0,
        "is_compliant": True,
        "carryover": 0
    }

    player_recommendations = [
        {
            "player_id": 999,
            "name": "My Test Player",
            "position": "QB",
            "age": 25,
            "overall": 95,
            "gm_recommends": True,
            "proposed_contract": {
                "aav": 50_000_000,
                "years": 5,
                "total": 250_000_000,
                "guaranteed": 150_000_000
            },
            "gm_reasoning": "My custom reasoning",
            "priority_tier": 1
        }
    ]

    restructure_proposals = []

    return cap_data, player_recommendations, restructure_proposals
```

Then add to `get_scenario_data()`:
```python
scenarios = {
    "my_scenario": create_my_scenario,
    # ... existing scenarios
}
```

## Comparison: Mock Demo vs. Full Simulation

| Aspect | Mock Demo | Full Simulation |
|--------|-----------|-----------------|
| **Startup** | ~1 second | ~5-10 minutes |
| **Database** | None (in-memory) | Real game_cycle.db |
| **Data** | Hardcoded | Realistic game data |
| **Iteration Speed** | Instant | Slow (re-simulate) |
| **Full Functionality** | ❌ Signals only | ✅ Complete |
| **Best For** | UI development | Integration testing |

## Tips

1. **Use `minimal` scenario** for quick layout checks
2. **Use `default` scenario** for general development
3. **Use `over_cap` scenario** to test cap relief UI
4. **Use `many_players` scenario** to test scrolling/performance
5. **Edit mock data** to create edge cases (e.g., all players same position)

## Next Steps

After testing with mock data:
1. Validate with **snapshot demo** (`offseason_demo.py --stage OFFSEASON_RESIGNING`)
2. Run **integration tests** with real database
3. Test in **full game cycle** (main2.py)

## Troubleshooting

**Q: Nothing happens when I click buttons**
A: Expected - signals emit but don't persist (no database). Use for UI testing only.

**Q: Can I test the full workflow?**
A: No - use `offseason_demo.py` with a snapshot for full workflow testing.

**Q: How do I add more test players?**
A: Edit the scenario function in `resigning_view_mock_demo.py` and add more dict entries.

**Q: Can I test GM re-evaluation?**
A: Partially - button works but data won't refresh (requires database + service layer).
