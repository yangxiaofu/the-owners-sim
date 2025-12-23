# Re-signing Mock Demo - Changelog

## Latest Update: Restructures & Roster Cuts Support

### What's New ✨

#### 1. **Restructure Proposals Now Included**
- **Default scenario** now has 2 restructure proposals (Brandon Graham EDGE, Avonte Maddox CB)
- **Over cap scenario** already had restructures (now works with full roster)
- Test collapsible restructure cards, approve/reject buttons
- See cap savings calculations in real-time

#### 2. **Full 53-Man Roster in ALL Scenarios**
- Every scenario now generates a complete 53-player roster
- Roster includes all positions with realistic depth chart (starters, backups, depth)
- Player overalls vary by depth (starters: 75-92, backups: 70-81, depth: 65-74)

#### 3. **Roster Health Widget Populated**
- Right panel now shows position group health bars
- Green/yellow/red grades based on roster composition
- Warning indicators for expiring contracts at each position
- Click position groups to filter (UI element ready, backend mock)

#### 4. **Early Cuts Dialog Ready**
- "Early Roster Cuts..." button now functional
- Opens dialog with full roster (excluding expiring contract players)
- Can test UI layout and flow (won't persist without real DB)
- Perfect for testing cap relief workflows

### How to Test

#### Test Restructure Proposals
```bash
# Default scenario - 2 restructures
python demos/resigning_view_mock_demo.py

# Over cap scenario - 2 restructures + urgent need
python demos/resigning_view_mock_demo.py --scenario over_cap
```

**What to test**:
- Restructure cards appear in right panel
- Click "Approve" on restructure → card collapses, shows checkmark
- Click "Reject" on restructure → card collapses, shows X
- Cap savings update projected cap space

#### Test Roster Health & Early Cuts
```bash
# Any scenario works - all have full rosters
python demos/resigning_view_mock_demo.py
```

**What to test**:
- Right panel shows position group bars (QB, RB, WR, TE, OL, DL, LB, DB, ST)
- Bars colored by grade (A=green, B=blue, C=yellow, D=orange, F=red)
- Expiring contract indicators show at affected positions
- Click "Early Roster Cuts..." button → dialog opens

### Mock Data Structure

#### Restructure Proposal Format
```python
{
    "contract_id": 901,
    "player_name": "Brandon Graham",
    "position": "EDGE",
    "overall": 78,
    "current_cap_hit": 13_500_000,
    "new_cap_hit": 8_500_000,
    "cap_savings": 5_000_000,
    "dead_money_added": 10_000_000,
    "gm_reasoning": "Veteran pass rusher. Restructure to create cap flexibility...",
    "proposal_id": "restructure_901"
}
```

#### Roster Player Format
```python
{
    "player_id": 1001,
    "position": "QB",
    "overall": 85
}
```

### Updated Scenarios

All scenarios now return 4 values instead of 3:
```python
def create_scenario() -> tuple[Dict, List[Dict], List[Dict], List[Dict]]:
    # Returns: (cap_data, recommendations, restructures, roster_players)
    return cap_data, player_recommendations, restructure_proposals, roster_players
```

### What Still Needs Real Database

❌ **Early Cuts Dialog**:
- Opens correctly with roster data
- Cut selections won't persist (no DB to save to)
- Dead money calculations are mock only

❌ **Restructure Execution**:
- Approve/reject works in UI
- Contract modifications won't persist
- Use for UI testing only

❌ **Roster Health Filtering**:
- Position group clicks emit signals
- Filter won't apply (needs backend integration)

### Next Steps

1. **Test restructure card UI** - approve/reject flow, collapse animations
2. **Test roster health widget** - position bars, grades, expiring warnings
3. **Test early cuts dialog** - opens, displays roster, shows cap implications
4. **Add custom scenarios** - edit script to create specific test cases

### Tips for Development

**Quickly test restructures**:
```bash
python demos/resigning_view_mock_demo.py  # Has 2 restructures in default
```

**Test over-cap workflow**:
```bash
python demos/resigning_view_mock_demo.py --scenario over_cap
# Cap Relief section appears, restructures + early cuts both available
```

**Test roster health with minimal noise**:
```bash
python demos/resigning_view_mock_demo.py --scenario minimal
# Only 2 expiring contracts, easy to see roster health bars
```
