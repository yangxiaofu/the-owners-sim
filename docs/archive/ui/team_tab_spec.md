# Team Tab UI Specification

**Version:** 1.0.0
**Last Updated:** 2025-10-05
**Status:** Specification - Ready for Implementation
**Target Phase:** Phase 2 (Primary Implementation)

---

## Table of Contents

1. [Overview](#overview)
2. [Purpose & Goals](#purpose--goals)
3. [Data Sources & Integration](#data-sources--integration)
4. [UI Layout & Components](#ui-layout--components)
5. [Roster Tab Specification](#roster-tab-specification)
6. [Finances Tab Specification](#finances-tab-specification)
7. [Depth Chart Tab Specification](#depth-chart-tab-specification)
8. [Staff Tab Specification](#staff-tab-specification)
9. [Technical Architecture](#technical-architecture)
10. [User Interactions](#user-interactions)
11. [Visual Design](#visual-design)
12. [Implementation Plan](#implementation-plan)
13. [Integration Points](#integration-points)

---

## Overview

The **Team Tab** provides comprehensive team management capabilities, including roster inspection, contract/salary cap analysis, depth chart organization, and coaching staff oversight. This is the central hub for all team-related operations in franchise mode.

### Key Features

- **Team selector**: Browse all 32 NFL teams (user team pre-selected in dynasty mode)
- **Multi-tab interface**: Roster, Depth Chart, Finances, Staff, Strategy sub-tabs
- **Roster management**: View complete 53-man roster with stats, contracts, and status
- **Salary cap tracking**: Real-time cap space, contract details, dead money analysis
- **Depth chart**: Visual position-based depth chart (drag-and-drop in Phase 5)
- **Contract details**: Year-by-year breakdown, guarantees, cap hits
- **Position filtering**: Filter roster by position groups or specific positions
- **Context actions**: Right-click menu for player operations (view, cut, trade, edit depth)

---

## Purpose & Goals

### Primary Goals

1. **Provide roster visibility**: Users see complete team roster with key information at a glance
2. **Enable cap management**: Users understand cap situation, contract commitments, available space
3. **Support roster decisions**: Users can identify cuts, trades, or depth chart adjustments needed
4. **Facilitate team building**: Users plan roster construction within cap constraints
5. **Track player contracts**: Users see contract details, years remaining, guaranteed money

### User Stories

- *"As a user, I want to see my team's complete roster so I can evaluate roster needs"*
- *"As a user, I want to view my cap space and contract commitments so I can plan free agency"*
- *"As a user, I want to see contract details for each player so I can make cut/trade decisions"*
- *"As a user, I want to filter roster by position so I can evaluate depth at QB, WR, etc."*
- *"As a user, I want to sort roster by overall rating to identify best/worst players"*
- *"As a user, I want to see depth chart so I know who starts and who backs up"*
- *"As a user, I want to switch teams to scout opponents or evaluate trade partners"*
- *"As a user, I want to right-click a player to view stats, cut, or trade them"*

---

## Data Sources & Integration

### Player Data (`src/team_management/players/`)

Player roster information:

```python
# Player attributes (from player.py):
- name: Player name
- number: Jersey number
- primary_position: Position (QB, RB, WR, etc.)
- ratings: Dict of player ratings (overall, speed, strength, position-specific)
- team_id: Team assignment (1-32)
```

**Key Position Types**:
- Offense: QB, RB, FB, WR, TE, OL (LT, LG, C, RG, RT)
- Defense: DL (DE, DT, NT), LB (MIKE, SAM, WILL, ILB, OLB), DB (CB, NCB, FS, SS)
- Special Teams: K, P, LS, KR, PR

### Contract Data (`src/database/` - Tables: `player_contracts`, `contract_year_details`)

Contract information for cap management:

```sql
-- player_contracts table:
- contract_id: Unique contract identifier
- player_id: Link to player
- team_id: Team (1-32)
- contract_type: ROOKIE, VETERAN, FRANCHISE_TAG, TRANSITION_TAG, EXTENSION
- start_year, end_year, contract_years: Duration
- total_value: Total contract value ($)
- signing_bonus, signing_bonus_proration: Bonus structure
- guaranteed_at_signing, injury_guaranteed, total_guaranteed: Guarantees
- is_active: Contract status

-- contract_year_details table:
- base_salary: Annual base salary
- roster_bonus, workout_bonus, option_bonus: Additional bonuses
- signing_bonus_proration: Annual proration hit
- cap_hit: Total cap impact for year
- dead_money_if_cut: Dead cap if released
```

### Salary Cap Data (`src/salary_cap/`)

Cap calculation and validation:

```python
# CapCalculator methods:
- calculate_team_cap_space(team_id, season, roster_mode)
- calculate_dead_money(contract_id, release_year, june_1_designation)
- get_top_51_contracts(team_id, season)  # Offseason cap calculation
- validate_transaction(team_id, season, cap_impact)
```

### Team Metadata (`src/team_management/teams/`)

Team information:

```python
# Team attributes (from team_loader.py):
- team_id: Numerical ID (1-32)
- city: City name
- nickname: Team name
- full_name: "{city} {nickname}"
- abbreviation: 3-letter code (e.g., "PHI", "DAL")
- division: Division name
- conference: NFC/AFC
- primary_color, secondary_color: Team colors
```

---

## UI Layout & Components

### Main Layout (Team Tab)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Team: [Detroit Lions ▼]                Dynasty: Eagles | Season: 2025│
├─────────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────────────────────────────────────────────┐│
│ │ [Roster] [Depth Chart] [Finances] [Staff] [Strategy]            ││
│ └──────────────────────────────────────────────────────────────────┘│
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                                                                   │ │
│ │                     [Sub-Tab Content Area]                        │ │
│ │                                                                   │ │
│ │                  (Roster/Depth Chart/Finances/etc.)               │ │
│ │                                                                   │ │
│ │                                                                   │ │
│ │                                                                   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ Roster: 53/53   Cap Space: $12,547,332   Dead Money: $0             │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Hierarchy

```
TeamView (QWidget)
├── Team Selector (QComboBox) - All 32 NFL teams
├── Dynasty Info Label - Dynasty ID, Season
├── Sub-Tab Widget (QTabWidget)
│   ├── Roster Tab
│   ├── Depth Chart Tab
│   ├── Finances Tab
│   ├── Staff Tab
│   └── Strategy Tab
└── Status Bar
    ├── Roster Size Indicator (53/53)
    ├── Cap Space Display
    └── Dead Money Display
```

---

## Roster Tab Specification

### Primary Interface (Default Sub-Tab)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Position: [All Positions ▼]  Group: [All ▼]  Sort: [Overall ▼]      │
│ Search: [____________]  [🔍]                                         │
├─────────────────────────────────────────────────────────────────────┤
│ ┌───┬──┬─────────────────┬─────┬───┬─────┬──────────┬─────────┬────┐│
│ │Sel│# │ Name            │ Pos │Age│ OVR │ Contract │  Salary │Stat││
│ ├───┼──┼─────────────────┼─────┼───┼─────┼──────────┼─────────┼────┤│
│ │ □ │ 9│ M. Stafford     │ QB  │ 35│  87 │ 2yr/$45M │ $22.5M  │ACT ││
│ │ □ │26│ S. Barkley      │ RB  │ 27│  91 │ 4yr/$40M │ $10.0M  │ACT ││
│ │ □ │11│ A. Brown        │ WR  │ 26│  93 │ 3yr/$75M │ $25.0M  │ACT ││
│ │ □ │88│ D. Goedert      │ TE  │ 29│  84 │ 3yr/$36M │ $12.0M  │ACT ││
│ │ □ │77│ T. Williams     │ LT  │ 32│  82 │ 1yr/$8M  │  $8.0M  │ACT ││
│ │ □ │62│ J. Kelce        │ C   │ 36│  96 │ 1yr/$14M │ $14.0M  │ACT ││
│ │ □ │91│ F. Cox          │ DT  │ 33│  88 │ 1yr/$10M │ $10.0M  │ACT ││
│ │ □ │94│ J. Sweat        │ DE  │ 27│  89 │ 4yr/$72M │ $18.0M  │ACT ││
│ │ □ │53│ S. Bradley      │ LB  │ 27│  78 │ 2yr/$6M  │  $3.0M  │IR  ││
│ │ □ │24│ J. Bradberry    │ CB  │ 30│  85 │ 3yr/$38M │ $12.7M  │ACT ││
│ │   │  │ ... (43 more players)                                      ││
│ └───┴──┴─────────────────┴─────┴───┴─────┴──────────────────────────┘│
│                                                                       │
│ Right-click player for actions: [View Details] [View Stats] [Cut]   │
│                                 [Trade] [Edit Depth Chart]           │
└─────────────────────────────────────────────────────────────────────┘
```

### Table Columns

| Column | Width | Description | Sortable | Format |
|--------|-------|-------------|----------|--------|
| **Sel** | 30px | Checkbox for bulk operations | No | Checkbox |
| **#** | 40px | Jersey number | Yes | Integer |
| **Name** | 180px | Player name (Last, First) | Yes | Text |
| **Pos** | 50px | Position abbreviation | Yes | Text (QB, RB, etc.) |
| **Age** | 50px | Player age | Yes | Integer |
| **OVR** | 50px | Overall rating (0-99) | Yes | Integer with color coding |
| **Contract** | 120px | Years remaining / Total value | Yes | "Xyrs/$XXM" |
| **Salary** | 100px | Current year cap hit | Yes | "$XX.XM" |
| **Stat** | 50px | Player status | Yes | ACT/IR/PUP/SUS |

### Filtering Options

**Position Filter Dropdown**:
```
All Positions
────────────────
Offense
  Quarterbacks (QB)
  Running Backs (RB, FB)
  Wide Receivers (WR)
  Tight Ends (TE)
  Offensive Line (LT, LG, C, RG, RT)
Defense
  Defensive Line (DE, DT, NT)
  Linebackers (MIKE, SAM, WILL, ILB, OLB)
  Secondary (CB, NCB, FS, SS)
Special Teams
  Kickers/Punters (K, P, LS)
  Returners (KR, PR)
```

**Position Group Filter**:
- All
- Offense
- Defense
- Special Teams

**Sort Options**:
- Overall (High to Low)
- Overall (Low to High)
- Name (A-Z)
- Name (Z-A)
- Position
- Age (Youngest First)
- Age (Oldest First)
- Salary (High to Low)
- Salary (Low to High)
- Contract Years Remaining

### Context Menu (Right-Click Player)

```
┌─────────────────────────┐
│ View Player Details     │
│ View Season Stats       │
│ View Career Stats       │
├─────────────────────────┤
│ Set as Starter          │
│ Edit Depth Chart Pos    │
├─────────────────────────┤
│ View Contract Details   │
│ Restructure Contract    │
│ Extend Contract         │
├─────────────────────────┤
│ Place on IR             │
│ Activate from IR        │
├─────────────────────────┤
│ Initiate Trade          │
│ Release Player          │
└─────────────────────────┘
```

### Status Indicators

| Status Code | Full Name | Color | Description |
|-------------|-----------|-------|-------------|
| **ACT** | Active | Green | Active roster, available to play |
| **IR** | Injured Reserve | Red | On IR, not available for games |
| **PUP** | Physically Unable to Perform | Orange | PUP list, not practicing |
| **SUS** | Suspended | Dark Red | League suspension |
| **NFI** | Non-Football Injury | Yellow | NFI list |
| **RES** | Reserved | Gray | Other reserve list |

---

## Finances Tab Specification

### Cap Summary Panel

```
┌─────────────────────────────────────────────────────────────────────┐
│ 💰 SALARY CAP SUMMARY - 2025                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   Team Salary Cap:      $224,800,000                                 │
│   Current Spending:     $212,252,668                                 │
│   ───────────────────────────────────                               │
│   Cap Space:             $12,547,332  ✅ COMPLIANT                   │
│                                                                       │
│   Top-51 Rule (Offseason):    ACTIVE                                 │
│   Roster Count:              53 / 53                                 │
│   Dead Money:                     $0                                 │
│                                                                       │
│   Projected 2026 Cap:   $238,200,000                                 │
│   2026 Commitments:     $143,678,000                                 │
│   2026 Projected Space:  $94,522,000                                 │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Contract List

```
┌─────────────────────────────────────────────────────────────────────┐
│ Player Contracts (Sorted by Cap Hit)                                 │
├──────────────────┬────────┬────────────┬────────────┬──────────────┤
│ Player           │ Pos    │ 2025 Hit   │ Years Left │ Dead $ (Cut) │
├──────────────────┼────────┼────────────┼────────────┼──────────────┤
│ A. Brown         │ WR     │ $25,000,000│     3      │  $15,000,000 │
│ M. Stafford      │ QB     │ $22,500,000│     2      │   $8,500,000 │
│ J. Sweat         │ DE     │ $18,000,000│     4      │   $4,000,000 │
│ J. Kelce         │ C      │ $14,000,000│     1      │          $0  │
│ J. Bradberry     │ CB     │ $12,700,000│     3      │   $6,200,000 │
│ D. Goedert       │ TE     │ $12,000,000│     3      │   $3,800,000 │
│ S. Barkley       │ RB     │ $10,000,000│     4      │   $2,500,000 │
│ F. Cox           │ DT     │ $10,000,000│     1      │          $0  │
│ ... (45 more)                                                        │
└──────────────────┴────────┴────────────┴────────────┴──────────────┘

[Export to CSV] [Cap Projection Tool] [Contract Simulator]
```

### Cap Hit Breakdown (Selected Player Detail)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Contract Details: A.J. Brown                                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ Contract Type:        VETERAN                                        │
│ Years:               3 (2025-2027)                                   │
│ Total Value:         $75,000,000                                     │
│ Guaranteed:          $54,000,000                                     │
│ Signing Bonus:       $20,000,000 (prorated $4M/year over 5 years)   │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Year-by-Year Breakdown:                                          │ │
│ ├──────┬────────────┬─────────┬──────────┬─────────┬─────────────┤ │
│ │ Year │ Base Salary│ Bonuses │ Proration│ Cap Hit │ Dead $ (Cut)│ │
│ ├──────┼────────────┼─────────┼──────────┼─────────┼─────────────┤ │
│ │ 2025 │ $15,000,000│ $6,000K │$4,000,000│$25,000K │ $15,000,000 │ │
│ │ 2026 │ $18,000,000│ $6,000K │$4,000,000│$28,000K │  $8,000,000 │ │
│ │ 2027 │ $18,000,000│ $6,000K │$4,000,000│$28,000K │  $4,000,000 │ │
│ └──────┴────────────┴─────────┴──────────┴─────────┴─────────────┘ │
│                                                                       │
│ [Restructure Contract] [Extend Contract] [Release Player]            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Depth Chart Tab Specification

### Layout (Position-Based Grid)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Depth Chart - Detroit Lions                       Scheme: 3-4 Defense│
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ OFFENSE                                                               │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                                                                   │ │
│ │  QB              RB              WR1             WR2              │ │
│ │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │ │
│ │  │1. Stafford│   │1. Barkley │   │1. A.Brown │   │1. D.Smith │   │ │
│ │  │   (87)    │   │   (91)    │   │   (93)    │   │   (88)    │   │ │
│ │  ├──────────┤    ├──────────┤    ├──────────┤    ├──────────┤   │ │
│ │  │2. Hurts   │   │2. Gainwell│   │2. Watkins │   │2. Quez    │   │ │
│ │  │   (79)    │   │   (75)    │   │   (76)    │   │   (73)    │   │ │
│ │  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │ │
│ │                                                                   │ │
│ │  TE              LT              LG              C                │ │
│ │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │ │
│ │  │1. Goedert │   │1. Mailata │   │1. Dickerson  │1. Kelce   │   │ │
│ │  │   (84)    │   │   (85)    │   │   (78)    │   │   (96)    │   │ │
│ │  ├──────────┤    ├──────────┤    ├──────────┤    ├──────────┤   │ │
│ │  │2. Calcaterra│  │2. Becton  │   │2. Sills   │   │2. Jurgens │   │ │
│ │  │   (72)    │   │   (74)    │   │   (70)    │   │   (75)    │   │ │
│ │  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │ │
│ │                                                                   │ │
│ │  RG              RT                                               │ │
│ │  ┌──────────┐    ┌──────────┐                                    │ │
│ │  │1. Seumalo │   │1. Johnson │                                   │ │
│ │  │   (81)    │   │   (87)    │                                   │ │
│ │  ├──────────┤    ├──────────┤                                    │ │
│ │  │2. Herbig  │   │2. Driscoll│                                   │ │
│ │  │   (72)    │   │   (69)    │                                   │ │
│ │  └──────────┘    └──────────┘                                    │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ DEFENSE (3-4 Base)                                                    │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │                                                                   │ │
│ │  DE              DT              DE                               │ │
│ │  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │ │
│ │  │1. Sweat   │   │1. Cox     │   │1. Graham  │                   │ │
│ │  │   (89)    │   │   (88)    │   │   (85)    │                   │ │
│ │  ├──────────┤    ├──────────┤    ├──────────┤                   │ │
│ │  │2. Barnett │   │2. Hargrave│   │2. Williams│                   │ │
│ │  │   (79)    │   │   (82)    │   │   (77)    │                   │ │
│ │  └──────────┘    └──────────┘    └──────────┘                   │ │
│ │                                                                   │ │
│ │  OLB             ILB             ILB             OLB              │ │
│ │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │ │
│ │  │1. Reddick │   │1. White   │   │1. Dean    │   │1. Carter  │   │ │
│ │  │   (86)    │   │   (83)    │   │   (80)    │   │   (78)    │   │ │
│ │  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │ │
│ │                                                                   │ │
│ │  CB              FS              SS              CB               │ │
│ │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │ │
│ │  │1.Bradberry│   │1. Gardner │   │1. Maddox  │   │1. Slay    │   │ │
│ │  │   (85)    │   │   (81)    │   │   (84)    │   │   (88)    │   │ │
│ │  └──────────┘    └──────────┘    └──────────┘    └──────────┘   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ SPECIAL TEAMS                                                         │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │  K: J. Elliott (83)   P: A. Siposs (78)   LS: R. Lovato (82)     │ │
│ │  KR: K. Gainwell (75) PR: D. Smith (88)                          │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ [Edit Depth Chart] [Auto-Set by Overall] [Save Changes]              │
└─────────────────────────────────────────────────────────────────────┘
```

### Depth Chart Features

**Visual Indicators**:
- **Position Box**: Shows position label (QB, RB, etc.)
- **Starter**: First player listed, highlighted background
- **Backup**: Second/third players, normal background
- **Overall Rating**: Displayed in parentheses (87)
- **Injury Status**: Red border for injured players

**Interaction (Phase 5)**:
- Drag player card to different position
- Drop zones highlight when dragging
- Validation: Can't place WR at QB position
- Auto-save on changes

**Scheme Switching**:
- Defense: 3-4 Base vs 4-3 Base
- Changes available positions (3-4 OLB vs 4-3 DE)

---

## Staff Tab Specification

### Coaching Staff Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│ Coaching Staff - Detroit Lions                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ HEAD COACH                                                            │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Dan Campbell                                                      │ │
│ │ Overall: 82 | Philosophy: AGGRESSIVE                             │ │
│ │ Years with Team: 3 | Career Record: 24-17                        │ │
│ │ ──────────────────────────────────────────────────────────────── │ │
│ │ Strengths: Offensive Mind, Player Development                    │ │
│ │ Weaknesses: Clock Management, Challenge Decisions                │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ COORDINATORS                                                          │
│ ┌──────────────────────────┐  ┌──────────────────────────┐          │
│ │ Offensive Coordinator    │  │ Defensive Coordinator    │          │
│ │ Ben Johnson              │  │ Aaron Glenn              │          │
│ │ Overall: 79              │  │ Overall: 81              │          │
│ │ Philosophy: BALANCED     │  │ Philosophy: AGGRESSIVE   │          │
│ │ Specialty: Pass Heavy    │  │ Specialty: Zone Coverage │          │
│ └──────────────────────────┘  └──────────────────────────┘          │
│                                                                       │
│ ┌──────────────────────────┐                                         │
│ │ Special Teams Coord.     │                                         │
│ │ Jack Fox                 │                                         │
│ │ Overall: 75              │                                         │
│ │ Philosophy: CONSERVATIVE │                                         │
│ └──────────────────────────┘                                         │
│                                                                       │
│ POSITION COACHES                                                      │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ QB: Mark Brunell (74)   │ RB: Duce Staley (72)                  │ │
│ │ WR: Anquan Boldin (76)  │ TE: Ben Johnson (73)                  │ │
│ │ OL: Hank Fraley (78)    │ DL: Todd Wash (77)                    │ │
│ │ LB: Kelvin Sheppard (75)│ DB: Aubrey Pleasant (79)              │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ [View Staff Details] [Hire/Fire Staff] [Staff Performance Report]    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Technical Architecture

### MVC Pattern

```
TeamView (QWidget)
    ↓ calls methods
TeamController (thin orchestration)
    ↓ delegates to
TeamDataModel (domain model - owns all database APIs)
    ↓ queries
Database APIs (DatabaseAPI, CapCalculator, TeamDataLoader)
```

### TeamController (`ui/controllers/team_controller.py`)

**Responsibilities** (thin orchestration only):
```python
class TeamController:
    def __init__(self, db_path: str, dynasty_id: str, season: int):
        self.data_model = TeamDataModel(db_path, dynasty_id, season)

    def get_team_roster(self, team_id: int) -> List[Dict]:
        """Get complete roster for team."""
        return self.data_model.get_team_roster(team_id)

    def get_team_contracts(self, team_id: int) -> List[Dict]:
        """Get all contracts for team."""
        return self.data_model.get_team_contracts(team_id)

    def get_cap_summary(self, team_id: int) -> Dict:
        """Get salary cap summary."""
        return self.data_model.get_cap_summary(team_id)

    def get_depth_chart(self, team_id: int) -> Dict:
        """Get team depth chart."""
        return self.data_model.get_depth_chart(team_id)

    def release_player(self, player_id: int, june_1: bool = False) -> bool:
        """Release player with optional June 1 designation."""
        return self.data_model.release_player(player_id, june_1)
```

### TeamDataModel (`ui/domain_models/team_data_model.py`)

**Responsibilities** (owns all database access and business logic):
```python
class TeamDataModel:
    def __init__(self, db_path: str, dynasty_id: str, season: int):
        # OWNS database API instances
        self.player_loader = PlayerDataLoader()
        self.team_loader = TeamDataLoader()
        self.cap_calculator = CapCalculator(db_path)
        self.database_api = DatabaseAPI(db_path)
        self.dynasty_id = dynasty_id
        self.season = season

    def get_team_roster(self, team_id: int) -> List[Dict]:
        """
        Get complete roster with player data, contracts, and status.

        BUSINESS LOGIC:
        1. Load players for team from player files
        2. Fetch contracts from database
        3. Calculate cap hits for current year
        4. Merge player data with contract data
        5. Add status indicators (ACT, IR, etc.)
        6. Sort by position and overall rating
        """
        # Complex business logic here
        players = self.player_loader.load_team_players(team_id)
        contracts = self.database_api.get_team_contracts(team_id, self.season)
        # ... merge and format logic ...
        return formatted_roster

    def get_cap_summary(self, team_id: int) -> Dict:
        """Calculate salary cap summary with top-51 logic."""
        return self.cap_calculator.calculate_team_cap_space(
            team_id, self.season, roster_mode="regular_season"
        )
```

### Qt Models (Display Layer)

**RosterTableModel** (`ui/models/roster_model.py`):
```python
class RosterTableModel(QAbstractTableModel):
    """Qt table model for roster display."""

    def __init__(self):
        super().__init__()
        self._roster_data = []

    def set_roster(self, roster: List[Dict]):
        """Receive roster data from controller."""
        self.beginResetModel()
        self._roster_data = roster
        self.endResetModel()

    def data(self, index, role):
        """Format data for Qt table display."""
        if role == Qt.BackgroundRole:
            # Color coding for status
            status = self._roster_data[row]['status']
            if status == 'IR':
                return QColor("#FFE0E0")  # Light red

        if role == Qt.DisplayRole:
            # Format contract as "Xyrs/$XXM"
            return self._format_contract(self._roster_data[row])
```

---

## User Interactions

### Team Selection

**Team Selector Dropdown**:
- Shows all 32 NFL teams
- User's team (dynasty mode) pre-selected
- Teams grouped by division (optional)
- Search/filter capability for quick selection

**Behavior**:
- Changing team loads new roster, contracts, depth chart
- All sub-tabs update to show selected team
- Cap summary updates to selected team

### Sub-Tab Navigation

**Tab Switching**:
- Click tab to switch view
- Tab state preserved when switching back
- Auto-refresh data when switching to tab

**Default Tab**: Roster (most commonly used)

### Roster Table Interactions

**Sorting**:
- Click column header to sort
- Click again to reverse sort
- Multi-column sort with Shift+Click

**Filtering**:
- Position dropdown filters visible players
- Search box filters by name
- Multiple filters combine (AND logic)

**Row Selection**:
- Single-click to select player
- Double-click to view player details
- Checkbox for bulk operations

**Context Menu**:
- Right-click player for actions menu
- Actions enabled/disabled based on context
- Confirmation dialogs for destructive actions

### Contract Operations

**View Contract**:
- Click contract cell to expand details
- Shows year-by-year breakdown
- Displays dead money calculations

**Restructure Contract**:
- Opens restructure dialog
- Shows before/after cap impact
- Validates against cap space

**Release Player**:
- Confirmation dialog with dead money impact
- Option for June 1 designation
- Updates roster and cap immediately

---

## Visual Design

### Color Scheme

**Status Colors**:
- **Active (Green)**: `#4CAF50`
- **Injured Reserve (Red)**: `#F44336`
- **PUP (Orange)**: `#FF9800`
- **Suspended (Dark Red)**: `#C62828`
- **Background (Hover)**: `#E3F2FD`

**Overall Rating Colors**:
- **Elite (90+)**: `#1976D2` (Blue)
- **Starter (80-89)**: `#388E3C` (Green)
- **Backup (70-79)**: `#FBC02D` (Yellow)
- **Depth (60-69)**: `#F57C00` (Orange)
- **Practice Squad (<60)**: `#D32F2F` (Red)

**Cap Space Indicators**:
- **Healthy (>$10M)**: Green text
- **Tight ($1M-$10M)**: Yellow text
- **Over Cap (<$0)**: Red text with warning icon

### Typography

**Headers**:
- Font: System default, Bold, 18px
- Team name: 24px, Bold

**Table**:
- Font: Monospace for numbers, Sans-serif for text
- Size: 12px (readable but compact)
- Row height: 32px (comfortable for reading)

**Contract Details**:
- Font: Sans-serif, 11px
- Numbers: Monospace for alignment
- Currency: Right-aligned

### Spacing

- **Tab padding**: 20px all sides
- **Table row padding**: 8px vertical, 12px horizontal
- **Panel margins**: 16px
- **Button spacing**: 8px between buttons

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Deliverables**:
- TeamView widget structure
- Team selector dropdown (all 32 teams)
- Sub-tab widget (empty tabs)
- Basic layout and styling

**Files**:
- `ui/views/team_view.py`
- `ui/controllers/team_controller.py`
- `ui/domain_models/team_data_model.py`

### Phase 2: Roster Tab (Weeks 2-3)

**Week 2**:
- Roster table model (QAbstractTableModel)
- Load player data from team files
- Display basic roster (name, position, number)
- Position filtering dropdown

**Week 3**:
- Contract data integration
- Cap hit calculations
- Sorting functionality
- Search/filter implementation

**Files**:
- `ui/models/roster_model.py`
- Enhanced `team_data_model.py`

### Phase 3: Finances Tab (Week 4)

**Deliverables**:
- Cap summary panel
- Contract list table
- Dead money calculations
- Contract detail expansion

**Files**:
- Finance panel widgets
- Integration with CapCalculator

### Phase 4: Depth Chart Tab (Week 5)

**Deliverables**:
- Position-based layout
- Display starters and backups
- Depth chart data model
- Read-only view (drag-and-drop in Phase 5)

**Files**:
- `ui/widgets/depth_chart_widget.py`
- Depth chart model

### Phase 5: Advanced Features (Week 6)

**Deliverables**:
- Context menu actions (view, cut, trade)
- Player detail dialog
- Contract restructure dialog
- Drag-and-drop depth chart

**Files**:
- Action dialogs
- Enhanced depth chart widget

### Phase 6: Staff & Strategy Tabs (Week 7)

**Deliverables**:
- Coaching staff display
- Staff details view
- Strategy/playbook overview (placeholder)

**Files**:
- `ui/widgets/staff_widget.py`

---

## Integration Points

### Player View Integration

**Navigation**:
- Click player name → Opens Player View tab
- Player View shows detailed stats, bio, contract
- Back button returns to Team View

**Data Sharing**:
- Selected player ID passed to Player View
- Player View can edit player (updates Team View)

### Offseason View Integration

**Free Agency**:
- "Browse Free Agents" button → Opens Offseason View
- Free agent signings update Team View roster
- Cap space updates in real-time

**Draft**:
- Draft picks reflected in roster
- Rookie contracts added to Finances tab

### Season View Integration

**Game Roster**:
- Team View shows player availability for games
- Injuries from games update player status
- Stats from games update player stats

### Transaction System

**Cuts**:
- Release player → Updates roster
- Dead money added to Finances tab
- Cap space recalculated

**Trades**:
- Initiate trade → Opens trade dialog
- Completed trade updates both teams' rosters
- Contract moves to new team

**Signings**:
- Free agent signing → Adds to roster
- Cap space decreases
- Contract added to Finances

---

## Testing & Validation

### Unit Tests

**TeamDataModel Tests**:
```python
def test_get_team_roster():
    """Test roster retrieval with contracts."""
    model = TeamDataModel(db_path, "test_dynasty", 2025)
    roster = model.get_team_roster(team_id=7)

    assert len(roster) == 53  # Full roster
    assert all('name' in p for p in roster)
    assert all('contract' in p for p in roster)
    assert all('cap_hit' in p for p in roster)

def test_cap_summary():
    """Test cap space calculation."""
    model = TeamDataModel(db_path, "test_dynasty", 2025)
    summary = model.get_cap_summary(team_id=7)

    assert 'cap_space' in summary
    assert 'total_spending' in summary
    assert summary['cap_space'] + summary['total_spending'] == 224_800_000
```

### Integration Tests

**UI Workflow Tests**:
- Load team → Verify roster displays
- Switch teams → Verify data updates
- Filter by position → Verify filtered results
- Sort by column → Verify sort order
- Release player → Verify cap update

### Manual Testing Checklist

- [ ] All 32 teams load correctly
- [ ] Roster displays complete data
- [ ] Contract details accurate
- [ ] Cap calculations correct
- [ ] Sorting works on all columns
- [ ] Filtering works correctly
- [ ] Context menu actions functional
- [ ] Depth chart displays properly
- [ ] Staff tab shows coaches
- [ ] Navigation between tabs smooth

---

## Future Enhancements (Post-Phase 2)

### Advanced Features

1. **Player Comparison Tool**
   - Compare 2-3 players side-by-side
   - Stats, contracts, ratings comparison

2. **Trade Analyzer**
   - Simulate trade scenarios
   - Cap impact analysis
   - Trade value calculator

3. **Contract Simulator**
   - Test different contract structures
   - Optimize cap allocation
   - Multi-year planning

4. **Roster Builder**
   - Build ideal 53-man roster
   - Position need identifier
   - Draft/FA target list

5. **Performance Dashboard**
   - Team stats over time
   - Player development tracking
   - Coaching impact analysis

### Data Visualizations

- **Cap Space Chart**: Visual cap allocation by position
- **Salary Distribution**: Player salary histogram
- **Age Distribution**: Team age profile
- **Contract Timeline**: Visual contract expiration dates
- **Depth Chart Heatmap**: Position strength visualization

---

## Appendix

### Database Queries

**Get Team Roster with Contracts**:
```sql
SELECT
    p.player_id,
    p.name,
    p.number,
    p.position,
    p.age,
    p.overall_rating,
    c.contract_years,
    c.total_value,
    cyd.cap_hit,
    cyd.dead_money_if_cut,
    p.status
FROM players p
LEFT JOIN player_contracts c ON p.player_id = c.player_id
    AND c.is_active = TRUE
LEFT JOIN contract_year_details cyd ON c.contract_id = cyd.contract_id
    AND cyd.season_year = ?
WHERE p.team_id = ?
    AND p.dynasty_id = ?
ORDER BY p.position, p.overall_rating DESC
```

**Get Cap Summary**:
```sql
SELECT
    SUM(cap_hit) as total_spending,
    224800000 - SUM(cap_hit) as cap_space,
    COUNT(*) as roster_count
FROM contract_year_details cyd
JOIN player_contracts c ON cyd.contract_id = c.contract_id
WHERE c.team_id = ?
    AND c.is_active = TRUE
    AND cyd.season_year = ?
    AND c.dynasty_id = ?
```

### UI Component Specs

**Team Selector**:
- Component: `QComboBox`
- Data: All 32 teams (ID, name, logo)
- Sort: Alphabetical or by division
- Width: 250px

**Roster Table**:
- Component: `QTableView` with `RosterTableModel`
- Rows: 53 (roster size)
- Columns: 9 (Sel, #, Name, Pos, Age, OVR, Contract, Salary, Stat)
- Features: Sortable, filterable, searchable, right-click menu

**Cap Summary Panel**:
- Component: Custom `QWidget` with `QVBoxLayout`
- Displays: Cap amount, spending, space, compliance
- Updates: Real-time when roster changes

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-05
**Next Review**: After Phase 2 implementation
**Status**: Ready for Implementation

