# Offseason Dashboard UI Specification

**Version:** 1.0.0
**Last Updated:** 2025-10-13
**Status:** High-Level Design Specification
**Target Phase:** Phase 4 (Offseason Interface)

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [Dashboard Layout](#dashboard-layout)
4. [Key Sections](#key-sections)
5. [Color Palette](#color-palette)
6. [Technical Architecture](#technical-architecture)
7. [Implementation Plan](#implementation-plan)

---

## Overview

The **Offseason Dashboard** provides the franchise owner with a strategic overview of the team's offseason needs, staff recommendations, and key deadlines. This dashboard emphasizes **advisory systems** where the owner reviews expert opinions from their scouting director, general manager, and coaching staff rather than micromanaging individual transactions.

### Key Features

- **Owner perspective**: Strategic oversight, not tactical micromanagement
- **Staff recommendations**: Scouting director, GM, and coaching staff provide advice
- **Softer color palette**: Professional executive colors (muted blues, sage greens, warm grays)
- **Team scouting report**: Position-by-position grades and needs assessment
- **Franchise tag recommendations**: Staff identifies top candidates with rationale
- **Free agency strategy**: Advisor-driven target list with cap considerations
- **Draft prospects board**: Prospects aligned to team needs and gaps
- **Salary cap dashboard**: High-level cap health (owner-friendly, not technical)

---

## Design Philosophy

### Owner vs GM Perspective

**OLD (GM Perspective)**:
- Action buttons for every transaction
- Manual control over every decision
- Technical cap details exposed
- Harsh alert colors (red, orange, purple)
- Micromanagement focused

**NEW (Owner Perspective)**:
- Advisory panels with staff recommendations
- Strategic overview and approval workflow
- High-level cap health indicators
- Softer professional colors
- Delegation and trust in staff expertise

### User Experience Goals

1. **Trust your staff**: GM and scouts provide recommendations, owner approves/disapproves
2. **Strategic thinking**: Focus on roster gaps, cap health, long-term team building
3. **Informed decisions**: Staff provides context, rationale, and risk assessment
4. **Professional interface**: Executive dashboard feel, not technical control panel
5. **Calm and focused**: Softer colors reduce stress, improve readability

---

## Dashboard Layout

### High-Level Wireframe

```
┌─────────────────────────────────────────────────────────────────────┐
│ Offseason Dashboard - Detroit Lions                  Season: 2025   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ ┌────────────────────────┐  ┌────────────────────────────────────┐  │
│ │ 📊 TEAM SCOUTING       │  │ 💼 SALARY CAP HEALTH               │  │
│ │      REPORT            │  │                                    │  │
│ │                        │  │  Cap Space: $12.5M                 │  │
│ │ Position Grades:       │  │  Status: ✓ Healthy                 │  │
│ │ QB: B+ | RB: A-        │  │  Projected 2026: $94M available    │  │
│ │ WR: A  | TE: B         │  │                                    │  │
│ │ OL: C+ | DL: B-        │  │  Key Concerns:                     │  │
│ │ LB: B  | DB: A-        │  │  • 3 starters need extensions      │  │
│ │                        │  │  • Franchise tag decisions due     │  │
│ └────────────────────────┘  └────────────────────────────────────┘  │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🏷️  FRANCHISE TAG RECOMMENDATIONS                                │ │
│ │                                                                   │ │
│ │ Deadline: March 5, 2025 (21 days)                                │ │
│ │                                                                   │ │
│ │ ┌─────────────────────────────────────────────────────────────┐ │ │
│ │ │ ⭐ #1 RECOMMENDED: J. Sweat (DE, OVR 89)                     │ │ │
│ │ │ Tag Cost: $19.7M | GM Rationale: "Elite pass rusher,       │ │ │
│ │ │ critical to defense. Open market value $22M+."              │ │ │
│ │ │ Coaching Staff: "Must keep. Top 5 in sacks last 2 years."  │ │ │
│ │ │ [Apply Franchise Tag] [Negotiate Long-Term Deal]            │ │ │
│ │ └─────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ ┌─────────────────────────────────────────────────────────────┐ │ │
│ │ │ #2 CONSIDER: D. Goedert (TE, OVR 84)                        │ │ │
│ │ │ Tag Cost: $11.3M | GM Notes: "Solid starter, but could     │ │ │
│ │ │ find replacement in draft. Recommend extension talks."      │ │ │
│ │ │ [Apply Franchise Tag] [Begin Extension Talks] [Let Walk]    │ │ │
│ │ └─────────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🎯 FREE AGENCY STRATEGY                                          │ │
│ │                                                                   │ │
│ │ Legal Tampering: March 11 | FA Opens: March 13                  │ │
│ │                                                                   │ │
│ │ Priority Needs (from Scouting Director):                         │ │
│ │                                                                   │ │
│ │ 🔴 CRITICAL: Offensive Line (LG position)                        │ │
│ │    Recommended Targets:                                          │ │
│ │    • Q. Nelson (OVR 92) - Est. $18M/yr - "Elite guard"          │ │
│ │    • C. Lindstrom (OVR 88) - Est. $14M/yr - "Solid fit"         │ │
│ │                                                                   │ │
│ │ 🟡 MODERATE: Linebacker depth                                    │ │
│ │    Recommended Targets:                                          │ │
│ │    • B. Wagner (OVR 85) - Est. $8M/yr - "Veteran leader"        │ │
│ │                                                                   │ │
│ │ 🟢 OPTIONAL: Special teams specialists                           │ │
│ │    (Can address in late draft rounds)                            │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 📋 DRAFT PROSPECTS BOARD                                         │ │
│ │                                                                   │ │
│ │ Team Needs Aligned to Draft Board:                               │ │
│ │                                                                   │ │
│ │ Round 1 (Pick #15): Offensive Line                               │ │
│ │ ┌─────────────────────────────────────────────────────────────┐ │ │
│ │ │ Top 3 Prospects Available:                                   │ │ │
│ │ │ 1. O. Fashanu (OT, Penn St.) - Grade: A | Fit: 95%          │ │ │
│ │ │ 2. J. Latham (OT, Alabama) - Grade: A- | Fit: 90%           │ │ │
│ │ │ 3. T. Fautanu (OG, Washington) - Grade: B+ | Fit: 88%       │ │ │
│ │ └─────────────────────────────────────────────────────────────┘ │ │
│ │                                                                   │ │
│ │ Round 2 (Pick #46): Linebacker or BPA                            │ │
│ │ [View Full Draft Board] [Run Mock Draft]                         │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 💬 STAFF RECOMMENDATIONS FEED                                    │ │
│ │                                                                   │ │
│ │ Mar 1 | GM: "Begin extension talks with J. Kelce before FA"     │ │
│ │ Feb 28 | OC: "QB needs better pass protection - OL is priority" │ │
│ │ Feb 25 | DC: "Consider re-signing F. Cox on 1-year vet deal"    │ │
│ │ Feb 22 | Scout: "OL class deep in draft, could wait til Rd 2"   │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Sections

### 1. Team Scouting Report (Top Left)

**Purpose**: High-level position group grades

**Content**:
- Position-by-position letter grades (A+, A, A-, B+, etc.)
- Overall team strength/weakness summary
- Roster needs at a glance

**Data Source**: `ui/domain_models/scouting_data_model.py`

---

### 2. Salary Cap Health (Top Right)

**Purpose**: Owner-friendly cap overview

**Content**:
- Current cap space (simple number)
- Status indicator (✓ Healthy, ⚠️ Tight, ⚠️ Over Cap)
- Projected next year cap space
- Key concerns (expiring contracts, tag decisions)

**NOT Included**: Technical cap details (proration, dead money calculations)

**Data Source**: `src/salary_cap/cap_calculator.py`

---

### 3. Franchise Tag Recommendations

**Purpose**: Staff-driven tag recommendations with rationale

**Content**:
- Ranked list of tag candidates (#1, #2, #3)
- GM rationale for each player
- Coaching staff input
- Tag cost and market value comparison
- Action buttons (Apply Tag, Begin Extension, Let Walk)

**Data Source**: `ui/domain_models/offseason_advisory_model.py`

---

### 4. Free Agency Strategy

**Purpose**: Prioritized FA targets aligned to team needs

**Content**:
- Priority levels (Critical, Moderate, Optional)
- Position needs from scouting director
- Recommended FA targets with estimated cost
- Scouting director notes on each player
- Cap space considerations

**Data Source**: `ui/domain_models/free_agency_advisory_model.py`

---

### 5. Draft Prospects Board

**Purpose**: Draft prospects matched to team needs

**Content**:
- Round-by-round recommendations
- Top 3 prospects at need positions
- Prospect grades and team fit scores
- Ability to view full draft board
- Mock draft simulator access

**Data Source**: `ui/domain_models/draft_advisory_model.py`

---

### 6. Staff Recommendations Feed

**Purpose**: Timeline of staff advice and memos

**Content**:
- Chronological feed of staff recommendations
- Source identification (GM, OC, DC, Scout)
- Short actionable advice
- Date stamps

**Data Source**: `ui/domain_models/staff_advisory_model.py`

---

## Color Palette

### Softer Professional Colors

**Background & Base**:
- **Primary Background**: `#F8F9FA` (Soft white)
- **Panel Background**: `#FFFFFF` (Pure white)
- **Border/Divider**: `#E0E4E8` (Subtle gray)

**Text Colors**:
- **Primary Text**: `#2C3E50` (Soft charcoal)
- **Secondary Text**: `#6C757D` (Muted gray)
- **Accent Text**: `#5A6C7D` (Slate gray)

**Status Indicators**:
- **Healthy/Positive**: `#4A9D7F` (Sage green, not bright green)
- **Warning/Caution**: `#D4A574` (Warm gold, not orange)
- **Critical/Negative**: `#C6847A` (Muted terracotta, not red)

**Priority Markers**:
- **Critical Priority**: `#C6847A` (Muted terracotta)
- **Moderate Priority**: `#D4A574` (Warm gold)
- **Optional Priority**: `#7B9DB8` (Soft blue)

**Accent Colors**:
- **Primary Accent**: `#6B8FA8` (Muted blue)
- **Secondary Accent**: `#8FA8A3` (Soft teal)
- **Highlight**: `#E8EFF5` (Very light blue)

**Panel Headers**:
- **Scouting Report**: `#7B9DB8` (Soft blue)
- **Cap Health**: `#8FA8A3` (Soft teal)
- **Franchise Tags**: `#A89CA8` (Soft purple)
- **Free Agency**: `#A8987B` (Soft brown)
- **Draft**: `#7B9DA8` (Steel blue)
- **Staff Feed**: `#9DA89D` (Sage)

### Design Principles

- **No harsh reds, oranges, or purples**
- **Soft, professional tones throughout**
- **Sufficient contrast for readability**
- **Calming, executive-friendly palette**

---

## Technical Architecture

### MVC Pattern

```
OffseasonView (QWidget)
    ↓ calls methods
OffseasonController (thin orchestration)
    ↓ delegates to
OffseasonAdvisoryModel (domain model - owns advisory logic)
    ↓ queries
Multiple Data Sources (ScoutingAPI, CapCalculator, DraftAPI, etc.)
```

### Domain Models (NEW)

**OffseasonAdvisoryModel** (`ui/domain_models/offseason_advisory_model.py`):
- Owns all offseason recommendation logic
- Aggregates data from multiple APIs
- Generates staff recommendations
- Calculates position needs and priorities

**ScoutingDataModel** (`ui/domain_models/scouting_data_model.py`):
- Position group grading system
- Roster strength/weakness analysis
- Team needs assessment

**FreeAgencyAdvisoryModel** (`ui/domain_models/free_agency_advisory_model.py`):
- FA target identification
- Market value estimation
- Priority ranking system

**DraftAdvisoryModel** (`ui/domain_models/draft_advisory_model.py`):
- Prospect-to-need matching
- Draft board generation
- Team fit scoring

**StaffAdvisoryModel** (`ui/domain_models/staff_advisory_model.py`):
- Staff recommendation feed
- Advisor message aggregation
- Timeline management

### Controller Layer

**OffseasonController** (`ui/controllers/offseason_controller.py`):
- Thin orchestration (≤10-20 lines per method)
- Delegates to domain models
- No business logic

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**Deliverables**:
- Offseason dashboard layout structure
- Softer color palette implementation
- Panel placeholders (6 sections)
- Basic styling and spacing

**Files**:
- Update `ui/views/offseason_view.py`
- Apply new color scheme to QSS stylesheet

### Phase 2: Domain Models (Week 2)

**Deliverables**:
- Create all 5 domain models
- Implement advisory recommendation logic
- Position grading system
- Staff recommendation feed

**Files**:
- `ui/domain_models/offseason_advisory_model.py`
- `ui/domain_models/scouting_data_model.py`
- `ui/domain_models/free_agency_advisory_model.py`
- `ui/domain_models/draft_advisory_model.py`
- `ui/domain_models/staff_advisory_model.py`

### Phase 3: UI Integration (Week 3)

**Deliverables**:
- Connect domain models to UI panels
- Display staff recommendations
- Franchise tag recommendation panel
- Free agency strategy panel
- Draft prospects board

**Files**:
- Enhanced `ui/views/offseason_view.py`
- Custom widgets for recommendation panels

### Phase 4: Interactivity (Week 4)

**Deliverables**:
- Action buttons (Apply Tag, Begin Extension, etc.)
- Staff feed interactions
- Mock draft simulator access
- Navigation to detailed views (Player, FA, Draft)

**Files**:
- Action handlers in controller
- Integration with transaction system

---

## Integration Points

### Salary Cap System
- `src/salary_cap/cap_calculator.py` - Cap space calculations
- `src/salary_cap/tag_manager.py` - Franchise tag operations

### Player/Roster System
- `src/database/player_roster_api.py` - Roster data
- Position group analysis

### Free Agency System
- Free agent pool queries
- Market value estimation

### Draft System
- Draft board data
- Prospect scouting reports

### Event System
- `src/events/contract_events.py` - Franchise tag events
- `src/events/free_agency_events.py` - FA signing events

---

**Document Version**: 1.0.0
**Last Updated**: 2025-10-13
**Next Review**: After Phase 4 implementation begins
**Status**: High-Level Design - Ready for Review
