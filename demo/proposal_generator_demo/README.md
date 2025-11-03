# Trade Proposal Generator Demo

Interactive demonstration of the Phase 1.4 Trade Proposal Generator system.

## Overview

This demo showcases the complete trade proposal generation pipeline, including:
- **League-wide scanning** (32 teams, ~1,696 players)
- **Fair value construction** (greedy algorithm: 1-for-1 → 2-for-1 → 3-for-1)
- **GM personality filtering** (4 personality traits)
- **Validation pipeline** (6 validation checks)
- **Realistic NFL scenarios** (contenders, rebuilders, various GM styles)

## Quick Start

**IMPORTANT**: This demo requires an initialized database with player rosters. To run the demo:

### Option 1: Use Existing Dynasty Database
```bash
# If you have an existing dynasty with rosters loaded
PYTHONPATH=src python demo/proposal_generator_demo/proposal_generator_demo.py
```

### Option 2: Initialize a New Dynasty First
```bash
# Initialize a new dynasty with rosters (run full season demo first)
PYTHONPATH=src python demo/full_season_demo/full_season_sim.py

# Then run this demo
PYTHONPATH=src python demo/proposal_generator_demo/proposal_generator_demo.py
```

**Note**: Unlike the Trade Value Calculator demo (Phase 1.2), the Proposal Generator requires a fully populated database because it performs league-wide roster scanning across all 32 teams. This is by design - the generator analyzes real roster depth to identify surplus assets.

## Demo Scenarios

### Scenario 1: Contender Seeking Impact Player
- **Team**: 8-1 record (playoff contender)
- **Need**: Elite pass rusher (DE, CRITICAL urgency)
- **GM Style**: Aggressive (win-now mode)
- **Cap Space**: $25M
- **Demonstrates**: How contending teams target elite players for playoff push

### Scenario 2: Rebuilder Trading Veterans
- **Team**: 1-6 record (rebuilding)
- **Need**: Young talent at multiple positions
- **GM Style**: Youth Movement (long-term focus)
- **Cap Space**: $45M
- **Demonstrates**: How rebuilding teams trade veterans for youth

### Scenario 3: Star Chaser Targeting Elite Players
- **Team**: 5-2 record (competing)
- **Need**: Elite WR (85+ OVR)
- **GM Style**: Star Chaser (targets big names)
- **Cap Space**: $20M
- **Demonstrates**: GM personality impact (star_chasing = 0.95)

### Scenario 4: Conservative GM
- **Team**: 4-3 record (middling)
- **Need**: Linebacker depth (HIGH urgency)
- **GM Style**: Conservative (rarely trades)
- **Cap Space**: $15M
- **Demonstrates**: How conservative GMs generate fewer proposals

### Scenario 5: Multiple Team Needs
- **Team**: 3-4 record (struggling)
- **Needs**: CB (CRITICAL), LB (HIGH), OL (MEDIUM)
- **GM Style**: Balanced
- **Cap Space**: $30M
- **Demonstrates**: Multi-position need prioritization (CRITICAL > HIGH > MEDIUM)

### Scenario 6: GM Personality Comparison
- **Setup**: Same team, same need, different GM personalities
- **GMs Tested**: Conservative, Balanced, Aggressive
- **Demonstrates**: Direct comparison of how GM personality affects proposal count and quality

## System Features Demonstrated

### 7-Step Generation Pipeline
1. **Filter Priority Needs**: CRITICAL + HIGH urgency only
2. **League-Wide Scan**: All 32 teams filtered by needed positions
3. **Identify Surplus Assets**: Find tradeable players beyond position minimums
4. **Construct Fair Value**: Greedy combination search (0.80-1.20 value ratio)
5. **Apply GM Filters**: trade_frequency, star_chasing, cap_management, veteran_preference
6. **Validation Pipeline**: 6 checks (duplicates, free agents, ratios, cap, positions, rosters)
7. **Sort by Priority**: Value ratio proximity to 1.0, then asset count

### GM Personality Filters

**1. Trade Frequency**
- Conservative (0.3): Max 1-2 proposals
- Balanced (0.5): Max 2-3 proposals
- Aggressive (0.9): Max 4-5 proposals

**2. Star Chasing**
- High (>0.6): Prefer 85+ OVR players
- Low (<0.4): Avoid 88+ OVR players (too expensive)

**3. Cap Management**
- High (>0.7): Max 50% cap consumption
- Medium (0.4-0.7): Max 70% cap consumption
- Win-now teams: Allow up to 80% cap consumption

**4. Veteran Preference**
- High (>0.7): Prefer age 27+ players
- Low (<0.3): Prefer age <29 players

### Performance Metrics

- **League-Wide Scan**: <150ms (target: <500ms) ✅
- **Single Team Evaluation**: <50ms average
- **Max Proposals**: 5 per call
- **Value Ratio Range**: 0.80 - 1.20 (fair trades only)

## Integration with Phase 1.3

The demo uses mock data for simplicity, but the system integrates with:

- **TradeValueCalculator** (Phase 1.2): Objective asset valuation
- **TradeEvaluator** (Phase 1.3 Week 2): Compatible proposal structure
- **NegotiatorEngine** (Phase 1.3 Week 3): Ready for multi-round negotiation

## Output Format

Each proposal includes:
```
PROPOSAL #1:
────────────────────────────────────────────────────────────────────────────
Team 22 sends: Player A (WR, 80 OVR, Age 26)
  Total Value: 240.0 units
Team 15 sends: Player B (LB, 85 OVR, Age 27)
  Total Value: 255.0 units

Value Ratio: 1.063 (VERY_FAIR)
Acceptable: ✓ YES
Cap Valid: ✓ YES
```

## Understanding the Results

### Proposal Count
- **0 proposals**: No viable trade partners found, or GM filters too restrictive
- **1-2 proposals**: Conservative GM or limited trade opportunities
- **3-5 proposals**: Balanced to aggressive GM with good trade options

### Value Ratio
- **0.95-1.05**: VERY_FAIR (perfectly balanced)
- **0.80-1.20**: FAIR (acceptable range)
- **Outside range**: Rejected by validation pipeline

### GM Impact
- **Conservative GMs**: Fewer proposals, avoid expensive players, strict cap limits
- **Aggressive GMs**: More proposals, target stars, flexible with cap
- **Star Chasers**: Only target 85+ OVR players
- **Youth GMs**: Avoid veterans, prefer players under 29

## Testing

The demo uses in-memory databases (`:memory:`) for isolation. For full testing:

```bash
# Run comprehensive test suite (56 tests)
python -m pytest tests/transactions/test_trade_proposal_generator.py -v

# Run specific test categories
python -m pytest tests/transactions/test_trade_proposal_generator.py -k "integration" -v
python -m pytest tests/transactions/test_trade_proposal_generator.py -k "personality" -v
```

## Files

- `proposal_generator_demo.py`: Main demo script (~600 lines)
- `README.md`: This file

## Next Steps

After running this demo, explore:

1. **Phase 1.5**: Transaction AI Manager (daily orchestration)
2. **Phase 2.0**: Draft pick integration with value charts
3. **Phase 3.0**: Multi-team trades (3+ teams)
4. **Phase 4.0**: Counter-offer generation system

## Documentation

For complete system documentation:

- **Implementation Details**: `PHASE_1_4_COMPLETE.md`
- **Test Suite**: `tests/transactions/test_trade_proposal_generator.py` (56 tests)
- **Architecture**: `docs/plans/ai_transactions_plan.md`
- **Data Models**: `src/transactions/models.py`

## Known Limitations

- **Mock Data**: Demo uses in-memory database with mock rosters
- **No Draft Picks**: AssetType.DRAFT_PICK exists but unused in Phase 1.4
- **Position Minimums**: Validation placeholder (not enforced)
- **Roster Minimums**: 53+ player check not enforced

For production usage with real player data, see the test suite for database integration examples.
