# AI Logic Demos

**Phase 2: Core AI Logic Demonstrations**

This directory contains runnable demos for all Phase 2 AI decision-making systems. Each demo can be run independently to test specific AI functionality.

---

## Quick Start

All demos are designed to run without database dependencies (uses mock data). Simply run from the project root:

```bash
# Run individual demos
PYTHONPATH=src python demo/ai_logic/demo_franchise_tag_ai.py
PYTHONPATH=src python demo/ai_logic/demo_free_agency_ai.py
PYTHONPATH=src python demo/ai_logic/demo_roster_cuts_ai.py

# Run complete integration demo
PYTHONPATH=src python demo/ai_logic/demo_full_ai_offseason.py
```

---

## Demo Files

### 1. `demo_franchise_tag_ai.py` - Gap 4: Franchise Tag AI

**What it demonstrates:**
- AI evaluating which players to franchise tag
- Tag cost vs market value analysis
- Team need integration
- Cap space validation

**Run time:** < 1 second

**Output:**
- Shows franchise tag candidates for all 32 NFL teams
- Displays tag cost, market value AAV, value score, and recommendation
- Highlights which positions are team needs

**Key takeaways:**
- AI correctly identifies high-value tag candidates
- Position value and team needs factor into decisions
- Cap space limits are enforced

---

### 2. `demo_free_agency_ai.py` - Gap 5: Free Agency AI

**What it demonstrates:**
- 30-day free agency simulation
- 3-tier FA period (Elite → Starters → Depth)
- AI teams signing FAs based on positional needs
- Contract offer generation

**Run time:** < 2 seconds

**Output:**
- Day-by-day FA signing activity
- Top contracts by AAV
- Signings breakdown by position
- FA pool depletion over time

**Key takeaways:**
- Elite FAs sign in first 3 days (legal tampering)
- AI prioritizes positional needs over best available
- Contract values align with player ratings and position

---

### 3. `demo_roster_cuts_ai.py` - Gap 7: Roster Cut AI

**What it demonstrates:**
- AI cutting 90-man roster to 53 players
- Value-based player ranking
- NFL position minimum enforcement
- Cap hit consideration in cuts

**Run time:** < 1 second

**Output:**
- Final 53-man roster composition
- 37 players cut
- Top 10 players kept (by value score)
- Position minimum validation

**Key takeaways:**
- AI keeps highest value players while meeting NFL minimums
- Premium positions (QB, DE, OT) ranked higher
- Expensive low-value players get cut first

---

### 4. `demo_full_ai_offseason.py` - Complete Integration

**What it demonstrates:**
- All 3 AI systems working together
- Complete offseason timeline:
  1. Franchise tag evaluation
  2. Free agency simulation (14 days)
  3. Roster finalization

**Run time:** < 3 seconds

**Output:**
- Summary of franchise tags applied
- Top FA signings across all teams
- Roster cut results for sample teams
- Overall offseason statistics

**Key takeaways:**
- All AI systems integrate seamlessly
- Realistic offseason progression
- Phase 2 implementation is complete and working

---

## Technical Details

### Mock Data
All demos use mock data to run independently:
- **Franchise Tags**: Simulates pending free agents (no database required)
- **Free Agency**: Creates 100 mock FAs with varying ratings
- **Roster Cuts**: Generates realistic 90-man roster

### No Database Writes
All demos run with `enable_persistence=False`:
- Safe to run multiple times
- No database modifications
- Immediate execution

### Dynasty Isolation
All demos use dynasty ID `"phase2_testing"` for isolation from production data.

---

## Expected Output Examples

### Franchise Tag Demo
```
📋 Detroit Lions
   Found 2 franchise tag candidate(s)

   #1. Patrick Mahomes - QUARTERBACK
       Overall: 95 OVR
       Tag Cost: $54,000,000
       Market AAV: $90.00M
       Value Score: 306.00
       Team Need: Yes ✓
       Recommendation: TAG
```

### Free Agency Demo
```
📅 DAY 1 RESULTS
   Signings: 45
   FAs Remaining: 55

   Notable Signings:
      • FA QB1 (90 OVR quarterback) → Kansas City Chiefs
        $72.00M/year for 4 years
      • FA DE2 (87 OVR defensive_end) → Dallas Cowboys
        $37.80M/year for 4 years
```

### Roster Cut Demo
```
✓ NFL POSITION MINIMUM VALIDATION
   ✓ QB: 3/1 (minimum)
   ✓ OL: 12/5 (minimum)
   ✓ DL: 12/4 (minimum)
   ✓ LB: 10/3 (minimum)
   ✓ DB: 14/3 (minimum)
   ✓ K: 1/1 (minimum)
   ✓ P: 1/1 (minimum)
```

---

## Troubleshooting

### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'offseason'`

**Solution**: Make sure to run with `PYTHONPATH=src` prefix:
```bash
PYTHONPATH=src python demo/ai_logic/demo_franchise_tag_ai.py
```

### No Output / Empty Results
**Problem**: Demo shows "No franchise tag candidates found" or "0 signings"

**Explanation**: This is expected when running with empty database. The demos use mock data where possible, but some outputs depend on database state.

**Solution**: Run `demo_full_ai_offseason.py` which uses fully mocked data for all phases.

---

## Next Steps

After running these demos:

1. **Verify AI Quality**: Review output to confirm realistic decisions
2. **Check SoC**: Code review to validate separation of concerns
3. **Integration Testing**: Wire AI into event system (Phase 4)
4. **Production Data**: Replace mock data with real database queries

---

## Code Architecture

All demos follow the same pattern:

```
Demo Script
    ↓
Manager/Controller (Orchestration Layer)
    ↓
┌─────────────────────────────────────┐
│ Gap 1: Contract Expiration Queries  │ (Data Layer)
│ Gap 2: Team Needs Analyzer          │ (Analysis Layer)
│ Gap 3: Market Value Calculator      │ (Calculation Layer)
└─────────────────────────────────────┘
    ↓
Pure Business Logic (Private Methods)
    ↓
Return Results
```

**Separation of Concerns**:
- **Data retrieval** → Database APIs (Gap 1)
- **Team analysis** → TeamNeedsAnalyzer (Gap 2)
- **Value calculation** → MarketValueCalculator (Gap 3)
- **Business logic** → Private helper methods (ultra-thin)
- **Orchestration** → Public methods (managers/controllers)

---

## Questions?

Check the implementation files for detailed comments:
- `src/offseason/offseason_controller.py` - Gap 4 implementation
- `src/offseason/free_agency_manager.py` - Gap 5 implementation
- `src/offseason/roster_manager.py` - Gap 7 implementation

See `docs/plans/offseason_ai_manager_plan.md` for complete Phase 2 architecture and plan.
