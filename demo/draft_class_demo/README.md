# Draft Class Generation Demo

Interactive demonstration of the NFL draft class generation system.

## Quick Start

```bash
PYTHONPATH=src python demo/draft_class_demo/draft_class_generation_demo.py
```

**Note**: This demo uses test archetypes from `player_generator_demo`. In production, archetypes will be loaded from JSON configuration files (Sprint 3 feature).

## What This Demo Shows

This demo showcases the complete draft class workflow from generation to roster integration:

### 1. **Draft Class Generation** (Demo 1)
- Generate realistic 224-player draft classes (7 rounds × 32 picks)
- Position-weighted distributions matching NFL draft patterns
- Dynasty-isolated draft class storage
- Automatic player ID assignment

### 2. **Top Prospects View** (Demo 2)
- Display top 32 overall prospects (typical 1st round)
- Overall rating distributions
- Elite player identification (85+ overall)
- Statistical analysis of top talent

### 3. **Position Filtering** (Demo 3)
- Filter prospects by position (demonstrates with QBs)
- Position-specific statistics
- First-round caliber identification
- Complete positional depth analysis

### 4. **Draft Execution** (Demo 4)
- Simulate draft selections (5 picks)
- Mark prospects as drafted
- Convert prospects to active players
- Automatic roster assignment

### 5. **Roster Integration** (Demo 5)
- Verify drafted players appear in team rosters
- Check jersey number assignment
- Confirm database persistence
- Validate player data integrity

### 6. **Draft History Tracking** (Demo 6)
- Query draft history using player_id
- Access prospect information post-draft
- Track which team drafted each player
- View projected vs actual draft position

### 7. **ID System Verification** (Demo 7)
- Verify unified player_id across tables
- Confirm same ID in draft_prospects and players
- Validate data consistency
- Demonstrate no ID conversion needed

## Expected Output

### Demo 1: Draft Class Generation
```
================================================================================
  DEMO 1: Generate Draft Class
================================================================================

Generating draft class for dynasty 'demo_dynasty_2026', season 2026...
⏳ Creating 224 prospects (7 rounds × 32 picks)...

✅ Draft class generation complete!
   Total prospects created: 224

Draft Class Info:
   ID: DRAFT_demo_dynasty_2026_2026
   Season: 2026
   Status: active
   Generated: 2025-10-19 12:34:56
```

### Demo 2: Top Prospects
```
================================================================================
  DEMO 2: Top 32 Overall Prospects (1st Round)
================================================================================

Top prospects by overall rating (typical 1st round selections):

  1. Marcus Johnson          QB     OVR: 92  ID:  1001  (Alabama)
  2. Derek Williams          EDGE   OVR: 91  ID:  1002  (Ohio State)
  3. Anthony Davis           OT     OVR: 90  ID:  1003  (Georgia)
  4. James Martinez          WR     OVR: 89  ID:  1004  (USC)
  5. Robert Anderson         CB     OVR: 88  ID:  1005  (Clemson)
  ...

Top 32 Statistics:
   Average Overall: 84.3
   Range: 78 - 92
   Elite (85+): 18 players
```

### Demo 3: Position Filter
```
================================================================================
  DEMO 3: Position Filter - All Quarterbacks
================================================================================

All available QB prospects in draft class:

  1. Marcus Johnson          QB     OVR: 92  ID:  1001  (Alabama)
  2. Tyler Brown             QB     OVR: 85  ID:  1015  (LSU)
  3. Kevin Wilson            QB     OVR: 78  ID:  1042  (Oregon)
  ...

QB Draft Class Statistics:
   Total QBs: 15
   Average Overall: 74.2
   Range: 58 - 92
   First-round caliber (80+): 4 QBs
```

### Demo 4: Draft Selections
```
================================================================================
  DEMO 4: Execute Draft Selections
================================================================================

Simulating first 5 picks of the draft...

Available prospects:
  1. Marcus Johnson          QB     OVR: 92  ID:  1001  (Alabama)
  2. Derek Williams          EDGE   OVR: 91  ID:  1002  (Ohio State)
  ...

--------------------------------------------------------------------------------
  Executing Draft Picks
--------------------------------------------------------------------------------

Pick 1: Team 1 selects...
   Marcus Johnson (QB, Overall: 92)
   ✅ Player ID 1001 added to Team 1 roster

Pick 2: Team 2 selects...
   Derek Williams (EDGE, Overall: 91)
   ✅ Player ID 1002 added to Team 2 roster
   ...
```

### Demo 5: Drafted Players
```
================================================================================
  DEMO 5: Drafted Players in Team Rosters
================================================================================

Verifying drafted players appear in players table:

✅ Team 1 Roster - #10  Marcus Johnson          QB     (Player ID: 1001)
✅ Team 2 Roster - #90  Derek Williams          EDGE   (Player ID: 1002)
✅ Team 3 Roster - #70  Anthony Davis           OT     (Player ID: 1003)
✅ Team 4 Roster - #80  James Martinez          WR     (Player ID: 1004)
✅ Team 5 Roster - #20  Robert Anderson         CB     (Player ID: 1005)

✅ All drafted players successfully added to team rosters!
```

### Demo 6: Draft History
```
================================================================================
  DEMO 6: Draft History Lookup
================================================================================

Querying draft history using unified player_id:

Player ID 1001: Marcus Johnson
   Position: QB
   College: Alabama
   True Overall: 92
   Projected: Picks 1-16
   Drafted By: Team 1
   Round 1, Pick 1
   Draft Class: 2026
   ...
```

### Demo 7: ID Verification
```
================================================================================
  DEMO 7: Verify Unified Player ID System
================================================================================

Verifying same player_id exists in both draft_prospects and players tables:

Player ID | Draft Prospects | Players Table | Match
--------------------------------------------------------------------------------
     1001 | True            | True          | ✅
     1002 | True            | True          | ✅
     1003 | True            | True          | ✅
     1004 | True            | True          | ✅
     1005 | True            | True          | ✅

================================================================================
✅ SUCCESS: All player IDs are consistent across tables!
   The unified player_id system is working correctly.
```

## Key Features Demonstrated

### Realistic Draft Class Generation
- **224 Total Prospects**: Complete 7-round draft (32 picks per round)
- **Position Distributions**: Matches NFL draft patterns (premium positions in Round 1)
- **Overall Rating Ranges**: Round-appropriate talent levels
- **Player Attributes**: Full attribute sets for each prospect

### Dynasty Isolation
- Each dynasty has separate draft classes
- No cross-dynasty data contamination
- Season-specific draft class tracking
- Multiple dynasties can coexist

### Unified Player ID System
- **Single Source of Truth**: Same player_id in both draft_prospects and players
- **No ID Conversion**: Player ID assigned at generation, never changes
- **Seamless Integration**: Draft system integrates cleanly with roster system
- **History Tracking**: Can query draft history using player_id

### Database Persistence
- All data stored in SQLite database
- Foreign key constraints ensure data integrity
- Cascading deletes for draft class cleanup
- Transaction support for draft operations

## Database Schema

### Tables Used
1. **draft_classes**: Draft class metadata
   - draft_class_id, dynasty_id, season
   - generation_date, total_prospects, status

2. **draft_prospects**: Individual prospects
   - player_id (unified with players table)
   - first_name, last_name, position, age
   - overall, attributes (JSON), college
   - is_drafted, drafted_by_team_id
   - drafted_round, drafted_pick

3. **players**: Active player rosters
   - player_id (same as draft_prospects)
   - team_id, positions, number
   - attributes, contract info

## Use Cases

### 1. Dynasty Mode Setup
```python
# Generate draft class for upcoming season
draft_api.generate_draft_class(dynasty_id="user_dynasty", season=2026)
```

### 2. Scout Draft Prospects
```python
# View top QB prospects
qb_prospects = draft_api.get_prospects_by_position(
    dynasty_id="user_dynasty",
    season=2026,
    position="QB"
)
```

### 3. Execute Draft Picks
```python
# User makes draft pick
draft_api.mark_prospect_drafted(
    player_id=1001,
    team_id=user_team_id,
    actual_round=1,
    actual_pick=15,
    dynasty_id="user_dynasty"
)

# Add to roster
draft_api.convert_prospect_to_player(
    player_id=1001,
    team_id=user_team_id,
    dynasty_id="user_dynasty"
)
```

### 4. Review Draft History
```python
# Look up player's draft info
history = draft_api.get_prospect_history(player_id=1001, dynasty_id="user_dynasty")
print(f"Drafted by Team {history['drafted_by_team_id']} in Round {history['drafted_round']}")
```

## Integration Points

### Player Generation System
- Uses `DraftClassGenerator` from `src/player_generation/`
- Archetype-based player creation
- Position-specific attribute distributions
- Round-appropriate overall ratings

### Player Roster System
- Integrates with `PlayerRosterAPI`
- Unified player_id generation
- Automatic jersey number assignment
- Dynasty-aware roster management

### Future Integrations
- **Salary Cap System**: Rookie contract generation
- **Event System**: DraftPickEvent for history tracking
- **UI System**: Draft board interface
- **AI System**: Team draft strategies and needs

## Technical Notes

### In-Memory Database
- Demo uses temporary SQLite database
- Database deleted after demo completes
- No impact on production data
- Can inspect with: `sqlite3 <temp_path>`

### Error Handling
- Validates dynasty exists before generation
- Prevents duplicate draft class creation
- Checks prospect availability before drafting
- Verifies player ID consistency

### Performance
- Generates 224 players in ~1-2 seconds
- Uses batch inserts for efficiency
- Indexes for fast prospect queries
- Transaction support for draft operations

## Troubleshooting

### Import Errors
```bash
# Ensure PYTHONPATH is set correctly
PYTHONPATH=src python demo/draft_class_demo/draft_class_generation_demo.py
```

### Database Schema Issues
```python
# Run migration manually if needed
sqlite3 database.db < src/database/migrations/add_draft_tables.sql
```

### Player ID Conflicts
- Each dynasty has separate player ID sequence
- PlayerRosterAPI manages auto-incrementing IDs
- No manual ID assignment needed

## Related Documentation

- **Draft System Architecture**: `docs/architecture/draft_system.md` (if exists)
- **Player Generation**: `docs/specifications/player_generator_system.md`
- **Database Schema**: `docs/schema/database_schema.md`
- **Player Generator Demo**: `demo/player_generator_demo/README.md`

## Next Steps

After running this demo, explore:
1. **Offseason Demo**: See draft integrated with full offseason workflow
2. **UI Development**: Draft board interface in desktop application
3. **AI Draft Logic**: Team needs-based draft strategies
4. **Salary Cap Integration**: Rookie contract generation
