# Team Needs Assignment System - Design Documentation

Complete design documentation for the NFL Team Needs Assignment system. These documents provide comprehensive guidance for implementing realistic positional need evaluation across all 32 teams.

## Documents in This Series

### 1. **TEAM_NEEDS_ASSIGNMENT_SYSTEM.md** (Main Design Document)
The complete design specification covering:
- All 28 NFL positions organized by tier and category
- 5 realistic team needs templates (Contenders, Rebuilding, QB Hunt, Star Loss, Balanced)
- Dynamic assignment algorithm for 32 teams
- Urgency calculation logic (CRITICAL → NONE)
- Output formats (JSON, CLI, Draft Board UI)
- Position matching algorithm with detailed examples
- Pick evaluation highlighting system
- Integration points with draft, free agency, and trades

**File Size**: ~8,000 words  
**Time to Read**: 30-45 minutes  
**Best For**: Overall understanding of the system

### 2. **TEAM_NEEDS_QUICK_REFERENCE.md** (Quick Lookup Guide)
Condensed reference guide with:
- Position tier quick reference
- Starter rating thresholds table
- Urgency decision tree flowchart
- Position matching rules (Exact, Hierarchy, Group)
- Real-world need examples by team type
- Highlight decision matrix with color codes
- Draft timeline and common scenarios
- Position abbreviations dictionary
- Integration checklist

**File Size**: ~4,000 words  
**Time to Read**: 10-15 minutes  
**Best For**: Quick lookups during implementation

### 3. **TEAM_NEEDS_IMPLEMENTATION_EXAMPLES.md** (Code Examples)
Practical implementation patterns showing:
- Basic usage examples (analyze single team, all 32 teams)
- Draft integration (evaluate prospects, AI selection)
- Free agency integration (prioritize targets, tier grouping)
- Display examples (CLI output, pick evaluation UI)
- Database query examples (read/write needs)
- Complete draft simulation with needs display
- Unit test examples

**File Size**: ~3,500 words  
**Time to Read**: 20-30 minutes (with code reading)  
**Best For**: Implementation and integration

## Key Concepts

### Position Tiers

| Tier | Positions | Threshold | Urgency Weight |
|------|-----------|-----------|---|
| **1** | QB, DE, LT, RT | 75+ | Premium - highest priority |
| **2** | WR, CB, C, FS, S | 72+ | High value - almost always needed |
| **3** | RB, LB, LG, RG, SS | 70+ | Standard - frequently needed |
| **4** | TE, DT, K, P, LS, FB | 68+ | Lower - rarely CRITICAL |

### Urgency Levels

- **CRITICAL (5)**: No starter OR starter way below threshold OR starter leaving with no replacement
- **HIGH (4)**: Poor starter OR leaving with backup OR no depth for premium position
- **MEDIUM (3)**: Weak depth OR insufficient backups for premium position
- **LOW (2)**: Adequate starter (80-85 OVR) and depth
- **NONE (1)**: Excellent starter (85+ OVR) and good depth

### Key Insight: Not All Teams Need QB

Unlike fantasy football drafts, not every team in the NFL Draft needs a QB:
- Only 5-8 teams per draft have CRITICAL QB need
- Every team values DE/CB (nearly 100% of teams have HIGH+ need)
- Tier 1 and 2 positions are always in demand
- Tier 4 positions rarely become CRITICAL needs

## How to Use These Documents

### For Design Review
1. Read TEAM_NEEDS_ASSIGNMENT_SYSTEM.md (Section 1-3)
2. Review quick reference tables in QUICK_REFERENCE.md
3. Ask questions about design decisions

### For Implementation
1. Review TEAM_NEEDS_ASSIGNMENT_SYSTEM.md (Sections 4-6)
2. Use IMPLEMENTATION_EXAMPLES.md for code patterns
3. Reference QUICK_REFERENCE.md during coding

### For Integration Testing
1. Check integration examples in IMPLEMENTATION_EXAMPLES.md
2. Use decision tree in QUICK_REFERENCE.md
3. Verify against test scenarios in TEAM_NEEDS_ASSIGNMENT_SYSTEM.md (Section 8)

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
- [x] Design completed
- [ ] Verify TeamNeedsAnalyzer existing implementation
- [ ] Create unit tests for position matching
- [ ] Create unit tests for urgency calculation

### Phase 2: Draft Integration (Week 2)
- [ ] Implement prospect evaluation function
- [ ] Integrate needs analysis into DraftManager
- [ ] Add pick highlighting system
- [ ] Create draft board display with needs

### Phase 3: Free Agency Integration (Week 3)
- [ ] Implement FA target prioritization
- [ ] Integrate needs analysis into FreeAgencyManager
- [ ] Add target recommendation system
- [ ] Create FA display with needs

### Phase 4: UI Integration (Week 4)
- [ ] Add needs display to draft board UI
- [ ] Add needs display to free agency UI
- [ ] Add pick evaluation popup
- [ ] Visual highlighting (green/yellow/red)

### Phase 5: Testing & Refinement (Week 5)
- [ ] Integration testing across all 32 teams
- [ ] Verify realistic need distribution
- [ ] Verify AI decision-making with needs
- [ ] Gather feedback and iterate

## Core Files Referenced

- `src/offseason/team_needs_analyzer.py` - Main needs analysis engine
- `src/offseason/draft_manager.py` - Draft operations
- `src/offseason/free_agency_manager.py` - Free agency operations
- `src/constants/position_hierarchy.py` - Position hierarchy system
- `src/constants/position_abbreviations.py` - Position naming

## Key Design Decisions

1. **Dynamic Analysis**: Needs are computed from actual roster state, not static templates
2. **Position Tiers**: Premium positions (QB, DE, LT) have higher urgency thresholds than standard positions
3. **Highlighting**: Color-coded visual feedback (green/yellow/red) for pick quality
4. **Position Matching**: Supports exact, hierarchy, and group-level matching for flexibility
5. **Extensibility**: Easy to add new positions or adjust thresholds without breaking changes

## Testing Strategy

All three documents include test examples:
- Unit tests for position matching and urgency calculation
- Integration tests for all 32 teams
- Realistic NFL scenario validation
- See TEAM_NEEDS_ASSIGNMENT_SYSTEM.md Section 8 for complete test suite

## FAQ

**Q: Why do some teams have 5 needs and others 3?**
A: Number varies based on roster composition. Teams with glaring holes have many HIGH+ needs. Well-staffed teams have fewer critical needs.

**Q: Can a position appear in multiple teams' top 5?**
A: Yes! Positions like CB and DE are high-value so many teams may list them. The urgency level varies by team.

**Q: How are the tier thresholds determined?**
A: Based on NFL reality - QB needs 75+ to avoid CRITICAL, while DT can get by with 68+. Tiers reflect actual positional scarcity.

**Q: What if a prospect doesn't match any need?**
A: Still shows as "no match" but not highlighted. AI may take value prospect if no needs remain.

**Q: How does GM personality affect needs?**
A: TeamNeedsAnalyzer gives objective needs. GM personality affects how important each need is to specific GM (handled separately).

## Document Versions

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 2025 | Initial design document |

## Contact & Questions

These design documents were created for The Owners Sim development team. For questions about specific sections, reference the main design document and quick reference guide.

**Total Documentation**: ~15,500 words across 3 documents  
**Estimated Reading Time**: 60-90 minutes for full understanding
