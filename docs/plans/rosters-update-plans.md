# NFL Roster Update Plans

This document outlines the comprehensive plan and methodology for updating NFL team rosters in "The Owners Sim" project, documenting the research process, file structure standards, and implementation guidelines.

## Project Overview

### Purpose
Create detailed roster documentation for all 32 NFL teams in the simulation, providing comprehensive player data that integrates seamlessly with the game's player management and simulation systems.

### Scope
- **Documentation**: Detailed markdown files for each team's 53-man roster
- **Data Integration**: Individual JSON files per team for modular player data management
- **Standardization**: Consistent format and attribute systems across all teams
- **Maintenance**: Guidelines for keeping rosters current with real NFL changes

### Current Status
- ✅ **Cleveland Browns** (Team ID: 7) - Complete roster documentation and player data
- ✅ **Buffalo Bills** (Team ID: 1) - Complete roster documentation and player data
- ✅ **Miami Dolphins** (Team ID: 2) - Complete roster documentation and player data
- 🔄 **Remaining Teams**: 29 teams pending implementation

---

## Research Methodology

### Data Sources
Primary sources for roster information include:
1. **Official Team Websites** - Most current roster information
2. **NFL.com** - Official league roster data and statistics
3. **ESPN** - Comprehensive player statistics and injury reports
4. **Pro Football Reference** - Historical performance data and advanced metrics
5. **Sports Illustrated** - Depth chart analysis and roster breakdowns

### Information Gathering Process
1. **Current Roster Validation** - Verify 53-man roster composition
2. **Player Details Collection** - Names, jersey numbers, positions, college background
3. **Performance Analysis** - 2024 season statistics and performance metrics
4. **Experience Assessment** - Years in NFL, team tenure, leadership roles
5. **Attribute Estimation** - Based on performance data and positional requirements

### Quality Assurance
- Cross-reference multiple sources for accuracy
- Validate jersey numbers and position assignments
- Ensure roster composition matches NFL standards (position limits, total players)
- Verify no duplicate player entries within team

---

## File Structure Standards

### Roster Documentation Template (`docs/rosters/[team_name].md`)

#### Header Section
```markdown
# [Team Name] 2025 53-Man Roster

**Team:** [Full Team Name]
**Season:** 2025 NFL Season
**Head Coach:** [Coach Name]
**Team ID:** [Numeric ID] (for simulation purposes)
**Last Updated:** [Date]
```

#### Team Leadership Section
```markdown
## Team Leadership (2025)
- **Head Coach:** [Name] - [Brief description]
- **Offensive Coordinator:** [Name] - [Brief description]
- **Defensive Coordinator:** [Name] - [Brief description]
- **General Manager:** [Name] - [Brief description]
```

#### Position Group Tables
Each position group should include:
- Jersey number
- Player name
- Experience level
- College
- 2024 performance/stats
- Overall rating (estimated)
- Key attributes (3-4 specific skills)

**Example Table Format:**
```markdown
### Quarterbacks (3)
| # | Name | Experience | College | 2024 Stats | Overall Rating | Key Attributes |
|---|------|------------|---------|-------------|----------------|----------------|
| 1 | Player Name | X years | University | Stats summary | XX | Attribute1: XX, Attribute2: XX, Attribute3: XX |
```

#### Required Position Groups
1. **Quarterbacks** (typically 2-3 players)
2. **Running Backs** (typically 3-4 players, include FB if applicable)
3. **Wide Receivers** (typically 5-6 players)
4. **Tight Ends** (typically 2-4 players)
5. **Offensive Line** (typically 8-10 players)
6. **Defensive Line** (typically 6-8 players)
7. **Linebackers/Edge Rushers** (typically 6-8 players total)
8. **Defensive Backs** (typically 8-10 players, separate CBs and Safeties)
9. **Specialists** (K, P, LS - typically 3 players)

#### Analysis Sections
```markdown
## 2025 Season Notable Changes
### Key Additions
### Notable Departures
### Rookie Class

## Roster Analysis
### Strengths
### Areas of Focus
### Coaching Philosophy

## Notes for Simulation Use
### Team ID Mapping
### Key Players for Simulation
### Special Considerations
```

---

## Data Integration Process

### Modular Team-Based JSON Structure (`src/data/teams/`)

#### New Architecture Overview
Each NFL team has its own dedicated JSON file for improved modularity, maintainability, and performance:

```
src/data/teams/
├── team_01_buffalo_bills.json
├── team_02_miami_dolphins.json
├── team_03_new_england_patriots.json
├── team_04_new_york_jets.json
├── team_05_baltimore_ravens.json
├── team_06_cincinnati_bengals.json
├── team_07_cleveland_browns.json
├── team_08_pittsburgh_steelers.json
├── team_09_houston_texans.json
├── team_10_indianapolis_colts.json
├── team_11_jacksonville_jaguars.json
├── team_12_tennessee_titans.json
├── team_13_denver_broncos.json
├── team_14_kansas_city_chiefs.json
├── team_15_las_vegas_raiders.json
├── team_16_los_angeles_chargers.json
├── team_17_dallas_cowboys.json
├── team_18_new_york_giants.json
├── team_19_philadelphia_eagles.json
├── team_20_washington_commanders.json
├── team_21_chicago_bears.json
├── team_22_detroit_lions.json
├── team_23_green_bay_packers.json
├── team_24_minnesota_vikings.json
├── team_25_atlanta_falcons.json
├── team_26_carolina_panthers.json
├── team_27_new_orleans_saints.json
├── team_28_tampa_bay_buccaneers.json
├── team_29_arizona_cardinals.json
├── team_30_los_angeles_rams.json
├── team_31_san_francisco_49ers.json
└── team_32_seattle_seahawks.json
```

#### Team File Structure Template
```json
{
  "team_info": {
    "team_id": [numeric_id],
    "team_name": "[Full Team Name]",
    "city": "[City]",
    "abbreviation": "[3-letter code]",
    "conference": "[AFC/NFC]",
    "division": "[East/North/South/West]",
    "head_coach": "[Coach Name]",
    "last_updated": "[YYYY-MM-DD]"
  },
  "players": {
    "[player_id]": {
      "player_id": [numeric_id],
      "first_name": "[First Name]",
      "last_name": "[Last Name]",
      "number": [jersey_number],
      "positions": ["[position_name]"],
      "team_id": [team_numeric_id],
      "attributes": {
        // Position-specific and universal attributes
      }
    }
    // ... additional players
  },
  "metadata": {
    "total_players": [count],
    "version": "1.0",
    "roster_type": "53_man_active",
    "season": "2025"
  }
}
```

#### Team ID Assignments
Reference `src/constants/team_ids.py` for official team ID mappings:
- AFC East: Bills (1), Dolphins (2), Patriots (3), Jets (4)
- AFC North: Ravens (5), Bengals (6), Browns (7), Steelers (8)
- AFC South: Texans (9), Colts (10), Jaguars (11), Titans (12)
- AFC West: Broncos (13), Chiefs (14), Raiders (15), Chargers (16)
- NFC East: Cowboys (17), Giants (18), Eagles (19), Commanders (20)
- NFC North: Bears (21), Lions (22), Packers (23), Vikings (24)
- NFC South: Falcons (25), Panthers (26), Saints (27), Buccaneers (28)
- NFC West: Cardinals (29), Rams (30), 49ers (31), Seahawks (32)

#### Player ID Allocation Strategy
- **Team-Based Ranges**: Each team gets a dedicated 100-player ID range for future expansion
- **Team 1 (Bills)**: 100-199
- **Team 2 (Dolphins)**: 200-299
- **Team 3 (Patriots)**: 300-399
- **Team 15 (Raiders)**: 1500-1599
- **Team 32 (Seahawks)**: 3200-3299
- **Formula**: `team_id * 100` to `(team_id * 100) + 99`
- **Active Roster**: Use first 53 IDs in team range (e.g., Raiders: 1500-1552)
- **Future Expansion**: Remaining 47 IDs reserved for practice squad, IR, future additions

---

## Attribute Rating Guidelines

### Universal Attributes (All Players)
- **overall**: Overall player rating (60-99 scale)
- **speed**: Player speed/40-yard dash performance (40-99)
- **awareness**: Football IQ and game awareness (50-99)
- **discipline**: Penalty avoidance and technique (60-99)
- **composure**: Performance under pressure (60-99)
- **experience**: NFL experience and game knowledge (60-99)
- **penalty_technique**: Specific penalty avoidance skills (60-99)

### Position-Specific Attributes

#### Quarterbacks
- **accuracy**: Pass completion accuracy (60-99)
- **arm_strength**: Throwing power and deep ball ability (60-99)
- **leadership**: Team leadership and communication (60-99)
- **pocket_presence**: Ability to perform under pressure (60-99)

#### Running Backs
- **strength**: Physical power for breaking tackles (60-99)
- **agility**: Change of direction and elusiveness (60-99)
- **hands**: Pass catching ability (60-99)
- **power**: Goal line and short yardage effectiveness (60-99)
- **elusiveness**: Ability to avoid tackles in open field (60-99)
- **vision**: Field vision and hole recognition (60-99)

#### Wide Receivers/Tight Ends
- **hands**: Catching ability and ball security (60-99)
- **route_running**: Route precision and technique (60-99)
- **release**: Getting off the line vs press coverage (60-99)
- **catching**: Red zone and contested catch ability (60-99)
- **blocking**: Run blocking and pass protection (TEs) (60-99)

#### Offensive Line
- **strength**: Physical power for blocking (70-99)
- **pass_blocking**: Pass protection technique (60-99)
- **run_blocking**: Run blocking effectiveness (60-99)
- **snap_accuracy**: Center-specific snapping accuracy (80-99)

#### Defensive Line
- **strength**: Physical power for rush/run defense (70-99)
- **pass_rush**: Pass rushing ability and technique (60-99)
- **run_defense**: Run stopping effectiveness (60-99)
- **power_moves**: Bull rush and power move effectiveness (60-99)

#### Linebackers
- **tackling**: Open field tackling ability (60-99)
- **coverage**: Pass coverage skills (60-99)
- **pass_rush**: Edge rushing ability (60-99)
- **run_defense**: Run fit and stopping ability (60-99)

#### Defensive Backs
- **man_coverage**: Man-to-man coverage ability (60-99)
- **zone_coverage**: Zone coverage and route recognition (60-99)
- **ball_skills**: Interception and pass breakup ability (60-99)
- **tackling**: Open field tackling (60-99)

#### Specialists
- **leg_strength**: Kicking/punting power (70-99)
- **accuracy**: Kicking/punting accuracy (70-99)
- **snap_accuracy**: Long snapper precision (85-99)

### Rating Scale Guidelines
- **90-99**: Elite/Pro Bowl level
- **85-89**: Star/Above average starter
- **80-84**: Solid starter
- **75-79**: Quality depth/Rotational starter
- **70-74**: Depth/Special teams contributor
- **65-69**: Practice squad/Development level
- **60-64**: Minimum NFL level

---

## Implementation Workflow

### Step-by-Step Process

#### Phase 1: Research and Documentation
1. **Select Target Team** from remaining 29 teams
2. **Gather Current Roster Data** from primary sources
3. **Cross-Reference Information** across multiple sources
4. **Create Roster Documentation** following template structure
5. **Review and Validate** completeness and accuracy

#### Phase 2: Team JSON File Creation
1. **Create Team Directory Structure** if not exists (`src/data/teams/`)
2. **Generate Team-Specific JSON File** following naming convention (`team_[id]_[name].json`)
3. **Calculate Player ID Range** using team-based allocation (team_id * 100)
4. **Create Player Entries** for all 53 players within team range
5. **Assign Appropriate Attributes** based on performance and position
6. **Validate JSON Structure** and syntax
7. **Update Team Metadata** (total_players count, team info, version)

#### Phase 3: Quality Assurance
1. **Test Player Loading** in simulation system
2. **Verify Team ID Mapping** and player associations
3. **Cross-Check Roster Completeness** (all positions covered)
4. **Review Attribute Consistency** across similar players
5. **Document Any Special Considerations** or known issues

### Batch Processing Strategy
- **AFC Divisions First**: Complete AFC teams before moving to NFC
- **Division Groups**: Process teams within same division together for rivalry context
- **Priority Teams**: Focus on playoff teams and popular franchises first
- **Quality Over Speed**: Ensure each team is thoroughly researched and documented

---

## Maintenance Schedule

### Regular Updates
- **Weekly During Season**: Injury reports and roster moves
- **Monthly During Offseason**: Free agency and trade updates
- **Post-Draft**: Rookie additions and roster cuts
- **Pre-Season**: Final 53-man roster adjustments

### Seasonal Milestones
1. **NFL Draft** (April/May) - Add rookie players
2. **Training Camp** (July/August) - Update depth charts
3. **Roster Cuts** (September) - Finalize 53-man rosters
4. **Trade Deadline** (November) - Mid-season roster changes
5. **Free Agency** (March) - Major roster turnover

### Version Control
- **Document Dates**: Update "Last Updated" field in all roster files
- **Change Tracking**: Note major roster changes in documentation
- **Backup Strategy**: Maintain previous versions for reference
- **Player ID Preservation**: Never reuse player IDs from removed players

---

## Future Expansion Plans

### Additional Teams Priority List
**Phase 2 (AFC Completion):**
1. New England Patriots (Team ID: 3)
2. New York Jets (Team ID: 4)
3. Baltimore Ravens (Team ID: 5)
4. Cincinnati Bengals (Team ID: 6)
5. Pittsburgh Steelers (Team ID: 8)

**Phase 3 (AFC South/West):**
6. Houston Texans (Team ID: 9)
7. Indianapolis Colts (Team ID: 10)
8. Jacksonville Jaguars (Team ID: 11)
9. Tennessee Titans (Team ID: 12)
10. Denver Broncos (Team ID: 13)
11. Kansas City Chiefs (Team ID: 14)
12. Las Vegas Raiders (Team ID: 15)
13. Los Angeles Chargers (Team ID: 16)

**Phase 4 (NFC East/North):**
14. Dallas Cowboys (Team ID: 17)
15. New York Giants (Team ID: 18)
16. Philadelphia Eagles (Team ID: 19)
17. Washington Commanders (Team ID: 20)
18. Chicago Bears (Team ID: 21)
19. Detroit Lions (Team ID: 22)
20. Green Bay Packers (Team ID: 23)
21. Minnesota Vikings (Team ID: 24)

**Phase 5 (NFC South/West):**
22. Atlanta Falcons (Team ID: 25)
23. Carolina Panthers (Team ID: 26)
24. New Orleans Saints (Team ID: 27)
25. Tampa Bay Buccaneers (Team ID: 28)
26. Arizona Cardinals (Team ID: 29)
27. Los Angeles Rams (Team ID: 30)
28. San Francisco 49ers (Team ID: 31)
29. Seattle Seahawks (Team ID: 32)

### Enhanced Features
- **Draft Class Integration**: Automated rookie player addition
- **Injury Tracking**: Dynamic injury status updates
- **Performance Metrics**: Season statistics integration
- **Contract Information**: Salary cap and contract details
- **Historical Data**: Multi-season player performance tracking

---

## Technical Considerations

### New Modular Architecture Advantages
- **Reduced File Size**: Individual team files (~53 players) vs. single massive file (~1,700 players)
- **Faster Loading**: Load only required teams for simulation rather than entire league
- **Parallel Processing**: Multiple teams can be updated simultaneously without conflicts
- **Easier Maintenance**: Team-specific updates don't affect other teams' data
- **Version Control**: Git-friendly smaller files with cleaner diffs and merge conflicts
- **Scalability**: Easy addition of practice squads, IR lists, and historical rosters per team

### Modular File Management
- **Directory Structure**: Organized `/teams/` directory with consistent naming
- **Individual Validation**: Each team file can be validated independently
- **Incremental Updates**: Update only changed teams during roster moves
- **Backup Strategy**: Team-specific backups and rollback capabilities
- **Performance Monitoring**: Track individual file sizes and loading times

### Integration Points
- **Team Roster Loader**: Update to dynamically load from team-specific files
- **Simulation Engine**: Validate all attributes are utilized properly across modular structure
- **Database API**: Enhance to retrieve players from appropriate team files
- **Statistics System**: Verify player stats attribution works with distributed data
- **Caching Strategy**: Implement team-based caching for frequently accessed rosters

### Error Handling
- **File-Level Validation**: Validate each team file independently
- **Cross-Team Consistency**: Ensure player IDs don't conflict across teams
- **Missing Team Files**: Graceful handling of missing team data
- **JSON Schema Validation**: Consistent structure validation across all team files
- **Data Integrity Checks**: Verify team metadata matches player team_id assignments

### Migration Strategy
- **Legacy Support**: Maintain backward compatibility during transition
- **Data Conversion**: Scripts to migrate from consolidated to modular format
- **Testing Framework**: Validate data integrity across old and new formats
- **Rollback Plan**: Ability to revert to consolidated format if issues arise

---

## Success Metrics

### Completion Indicators
- ✅ All 32 teams have complete roster documentation
- ✅ All players loaded successfully in simulation
- ✅ No JSON syntax errors or missing data
- ✅ Consistent attribute distributions across positions
- ✅ Real-world accuracy of player information

### Quality Benchmarks
- **Roster Accuracy**: >95% accurate player names and numbers
- **Attribute Realism**: Ratings align with real-world performance
- **System Integration**: No loading errors or missing player data
- **Documentation Completeness**: All required sections filled for each team
- **Update Timeliness**: Roster changes reflected within 1 week of NFL moves

---

## Miami Dolphins Implementation Summary

The Miami Dolphins roster update serves as the template and proof of concept for this systematic approach:

### Completed Elements
- ✅ **Comprehensive Research**: 53-man roster from multiple reliable sources
- ✅ **Detailed Documentation**: Complete `miami_dolphins.md` file following template
- ✅ **Full Player Database Integration**: 50 players added (IDs 35013-35062)
- ✅ **Accurate Attribute Assignment**: Position-specific attributes for all players
- ✅ **Metadata Updates**: Player count and team inclusion properly updated

### Key Players Added
- **Elite Level**: Tyreek Hill (93), Minkah Fitzpatrick (92)
- **Star Level**: Tua Tagovailoa (88), Jaylen Waddle (87), Zach Sieler (86)
- **Starter Level**: Bradley Chubb (82), James Daniels (82), Jaelan Phillips (83)
- **Depth/Development**: 35+ additional players across all positions

### Template Validation
The Miami Dolphins implementation validates:
- Research methodology effectiveness
- Documentation template completeness
- Player database integration process
- Attribute rating system consistency
- Quality assurance procedures

This successful implementation provides the foundation for completing all remaining 29 NFL teams using the same proven methodology and standards.

---

**Last Updated:** September 20, 2025
**Next Priority:** New England Patriots (Team ID: 3)
**Estimated Completion**: Q4 2025 for all 32 teams