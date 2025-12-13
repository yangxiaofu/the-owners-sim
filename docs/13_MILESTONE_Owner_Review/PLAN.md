# Milestone 13: Owner Review Page Revamp

## Executive Summary

**Objective:** Transform the Owner Review page from a placeholder to a fully functional strategic control center where owners can hire/fire their GM and Head Coach, set season win targets, and define strategic direction that influences GM behavior throughout the offseason.

**Vision:** Create an authentic ownership experience where:
- Owner evaluates season performance against expectations
- Owner can fire underperforming GM/HC and select from procedurally generated replacement candidates
- Owner sets strategic direction (win targets, position priorities, player wishlists)
- Owner's directives persist to database and flow through all offseason stages
- GM behavior in draft, free agency, and re-signing reflects owner's strategic vision

**Key Differentiators from Current System:**
- **From**: Placeholder UI with non-functional keep/fire buttons
- **To**: Fully functional staff management + persistent strategic directives

**Pattern:** Follows Milestone 10 (GM FA) hybrid guidance model with database persistence

---

## User Stories

### Staff Management

**US-1: View Current Staff**
> As an Owner, I want to see my current GM and Head Coach's profile (name, archetype, tenure, background), so I can evaluate their fit with my franchise vision.

**Acceptance Criteria:**
- Display GM section: name, archetype (Win-Now, Rebuilder, etc.), hire season, background history
- Display HC section: name, archetype (Aggressive, Balanced, etc.), hire season, background history
- Show tenure duration (e.g., "3 seasons with team")

**US-2: Fire GM**
> As an Owner, I want to fire my GM and choose from replacement candidates, so I can change my front office direction.

**Acceptance Criteria:**
- Click "Fire GM" button → Generate 3-5 procedural GM candidates
- Each candidate has: unique name, archetype, trait variations, background history
- Candidates exclude current GM's archetype (variety)
- Show candidate list with details for selection
- Select candidate → Hire as new GM

**US-3: Fire Head Coach**
> As an Owner, I want to fire my Head Coach and choose from replacement candidates, so I can change my on-field philosophy.

**Acceptance Criteria:**
- Click "Fire HC" button → Generate 3-5 procedural HC candidates
- Each candidate has: unique name, archetype, trait variations, background history
- HC archetypes: Aggressive, Balanced, Conservative, real-coach styles (McVay, Belichick, etc.)
- Show candidate list with details for selection
- Select candidate → Hire as new HC

---

### Strategic Directives

**US-4: Set Win Target**
> As an Owner, I want to set a win target for next season, so my GM understands my performance expectations.

**Acceptance Criteria:**
- SpinBox input for target wins (0-17)
- Target displayed in next season's Owner Review for comparison
- Win target influences GM urgency in offseason decisions

**US-5: Set Priority Positions**
> As an Owner, I want to specify 1-5 priority positions, so my GM focuses draft and FA resources on these needs.

**Acceptance Criteria:**
- 5 dropdown selectors for priority positions (None, QB, RB, WR, TE, OT, etc.)
- Priorities passed to DraftDirection and FAGuidance
- +15 bonus to candidates at priority positions in GM scoring

**US-6: Set Draft Strategy**
> As an Owner, I want to choose a draft strategy, so my GM follows my preferred approach.

**Acceptance Criteria:**
- Dropdown: Best Player Available, Balanced (default), Needs-Based, Position Focus
- Strategy passed to DraftService via owner directives
- Maps to existing DraftStrategy enum

**US-7: Set FA Philosophy**
> As an Owner, I want to choose a free agency philosophy, so my GM aligns spending approach with my vision.

**Acceptance Criteria:**
- Dropdown: Aggressive, Balanced (default), Conservative
- Philosophy passed to FAGuidance via owner directives
- Maps to existing FAPhilosophy enum

**US-8: Create Player Wishlists**
> As an Owner, I want to specify target players for FA and draft, so my GM prioritizes acquiring these specific players.

**Acceptance Criteria:**
- Text input for FA target names (comma-separated)
- Text input for draft prospect names (comma-separated)
- Wishlists passed to respective services
- GM proposal engine gives bonus to wishlist players

---

### Persistence

**US-9: Persist Directives**
> As an Owner, I want my strategic directives to persist across app restarts, so I don't lose my season plan.

**Acceptance Criteria:**
- Save directives to `owner_directives` database table
- Directives survive app close/reopen
- Directives loaded at start of each offseason stage
- Directives apply to NEXT season (set during post-season review)

**US-10: Persist Staff Assignments**
> As an Owner, I want my GM and HC assignments to persist, so hired staff remain across sessions.

**Acceptance Criteria:**
- Save staff assignments to `team_staff_assignments` table
- Staff data includes: ID, name, archetype, custom traits, history, hire season
- Staff loaded at app startup
- Staff carried forward season-to-season unless fired

---

## Current State Analysis

### Existing Owner View (`game_cycle_ui/views/owner_view.py`)

**Current Implementation:**
- Placeholder UI with keep/fire buttons for GM and HC
- Buttons toggle visual state only (no persistence)
- No actual staff management functionality
- No strategic directives capability
- "Continue to Franchise Tag" button advances stage

**Code Structure:**
```python
class OwnerView(QWidget):
    continue_clicked = Signal()
    _gm_decision: str = "keep"  # Visual only
    _hc_decision: str = "keep"  # Visual only
```

**Gaps:**
- No database persistence
- No procedural candidate generation
- No strategic direction inputs
- No connection to GM behavior systems

### Existing Patterns to Follow

**Draft Direction System:**
- `src/game_cycle/models/draft_direction.py` - Ephemeral guidance dataclass
- `game_cycle_ui/dialogs/draft_direction_dialog.py` - Strategy selection UI
- Pattern: Owner input → Dialog → Signal → Handler → Service

**FA Guidance System:**
- `src/game_cycle/models/fa_guidance.py` - Ephemeral guidance dataclass
- `game_cycle_ui/dialogs/fa_guidance_dialog.py` - Philosophy selection UI
- Pattern: Owner input → Dialog → Signal → Handler → Service

**GM Archetype System:**
- `src/team_management/gm_archetype.py` - 11 GM personality traits
- `src/config/gm_archetypes/base_archetypes.json` - 7 base archetypes
- Used by: draft_service, gm_fa_proposal_engine, free_agency_service

**HC Archetype System:**
- `src/play_engine/play_calling/head_coach.py` - HC traits and game management
- `src/config/coaching_staff/head_coaches/` - 10 archetype JSON configs
- `src/play_engine/play_calling/staff_factory.py` - HC instantiation

---

## Technical Architecture

### Database Schema

```sql
-- GM and HC assignments per dynasty/team/season
CREATE TABLE IF NOT EXISTS team_staff_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    -- GM Assignment
    gm_id TEXT NOT NULL,
    gm_name TEXT NOT NULL,
    gm_archetype_key TEXT NOT NULL,
    gm_custom_traits TEXT,  -- JSON overrides
    gm_history TEXT,
    gm_hire_season INTEGER NOT NULL,

    -- HC Assignment
    hc_id TEXT NOT NULL,
    hc_name TEXT NOT NULL,
    hc_archetype_key TEXT NOT NULL,
    hc_custom_traits TEXT,  -- JSON overrides
    hc_history TEXT,
    hc_hire_season INTEGER NOT NULL,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Owner strategic directives (persistent)
CREATE TABLE IF NOT EXISTS owner_directives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL CHECK(team_id BETWEEN 1 AND 32),
    season INTEGER NOT NULL,

    target_wins INTEGER CHECK(target_wins BETWEEN 0 AND 17),
    priority_positions TEXT,  -- JSON array
    fa_wishlist TEXT,         -- JSON array
    draft_wishlist TEXT,      -- JSON array
    draft_strategy TEXT DEFAULT 'balanced',
    fa_philosophy TEXT DEFAULT 'balanced',
    max_contract_years INTEGER DEFAULT 5,
    max_guaranteed_percent REAL DEFAULT 0.75,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
    UNIQUE(dynasty_id, team_id, season)
);

-- Staff candidate pool (generated when firing)
CREATE TABLE IF NOT EXISTS staff_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,

    candidate_id TEXT NOT NULL,
    staff_type TEXT NOT NULL CHECK(staff_type IN ('GM', 'HC')),
    name TEXT NOT NULL,
    archetype_key TEXT NOT NULL,
    custom_traits TEXT,  -- JSON
    history TEXT NOT NULL,
    is_selected INTEGER DEFAULT 0,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_staff_assignments_lookup
    ON team_staff_assignments(dynasty_id, team_id, season);
CREATE INDEX IF NOT EXISTS idx_owner_directives_lookup
    ON owner_directives(dynasty_id, team_id, season);
CREATE INDEX IF NOT EXISTS idx_staff_candidates_lookup
    ON staff_candidates(dynasty_id, team_id, season, staff_type);
```

### Data Models

**OwnerDirectives** (`src/game_cycle/models/owner_directives.py`)
```python
@dataclass
class OwnerDirectives:
    """Persistent owner strategic guidance."""
    dynasty_id: str
    team_id: int
    season: int
    target_wins: Optional[int] = None
    priority_positions: List[str] = field(default_factory=list)
    fa_wishlist: List[str] = field(default_factory=list)
    draft_wishlist: List[str] = field(default_factory=list)
    draft_strategy: str = "balanced"
    fa_philosophy: str = "balanced"
    max_contract_years: int = 5
    max_guaranteed_percent: float = 0.75

    def to_draft_direction(self) -> DraftDirection: ...
    def to_fa_guidance(self) -> FAGuidance: ...
```

**StaffMember** (`src/game_cycle/models/staff_member.py`)
```python
class StaffType(Enum):
    GM = "GM"
    HEAD_COACH = "HC"

@dataclass
class StaffMember:
    """GM or HC with procedural identity."""
    staff_id: str  # UUID
    staff_type: StaffType
    name: str
    archetype_key: str
    custom_traits: Dict[str, float]  # ±0.1 variations
    history: str
    hire_season: int
```

### Service Architecture

**StaffGeneratorService** (`src/game_cycle/services/staff_generator_service.py`)
```python
class StaffGeneratorService:
    """Procedural generation of GM/HC candidates."""

    FIRST_NAMES = ["John", "Mike", "Tom", ...]  # 30 names
    LAST_NAMES = ["Smith", "Johnson", ...]       # 40 names
    GM_ARCHETYPES = ["win_now", "rebuilder", "balanced", ...]
    HC_ARCHETYPES = ["balanced", "aggressive", "sean_mcvay", ...]

    def generate_gm_candidates(count=5, exclude=[]) -> List[Dict]
    def generate_hc_candidates(count=5, exclude=[]) -> List[Dict]
    def _generate_unique_name(used: set) -> str
    def _generate_trait_variations(archetype) -> Dict[str, float]
    def _generate_history(staff_type, archetype) -> str
```

**OwnerService** (`src/game_cycle/services/owner_service.py`)
```python
class OwnerService:
    """Business logic for Owner Review stage."""

    def get_current_staff(team_id) -> Optional[Dict]
    def fire_gm(team_id) -> List[Dict]  # Returns candidates
    def fire_hc(team_id) -> List[Dict]  # Returns candidates
    def hire_gm(team_id, candidate_id) -> Dict
    def hire_hc(team_id, candidate_id) -> Dict
    def get_directives(team_id) -> Optional[Dict]
    def save_directives(team_id, directives) -> None
    def initialize_default_staff(team_id) -> None
```

### UI Architecture

**OwnerView** - Three-tab interface:

1. **Season Summary Tab**
   - Season record display
   - Target vs Actual wins comparison
   - Visual indicators for met/missed expectations

2. **Staff Decisions Tab**
   - GM Section (stacked widget: current view ↔ candidates view)
   - HC Section (stacked widget: current view ↔ candidates view)
   - Keep/Fire buttons trigger candidate generation
   - Candidate list with Hire button

3. **Strategic Direction Tab**
   - Win Target: QSpinBox (0-17)
   - Priority Positions: 5 QComboBox (None/QB/RB/WR/...)
   - Draft Strategy: QComboBox
   - FA Philosophy: QComboBox
   - Wishlists: QLineEdit (comma-separated)
   - Save Directives button

**Signals:**
- `gm_fired` / `hc_fired` - Trigger candidate generation
- `gm_hired(str)` / `hc_hired(str)` - Complete hire with candidate_id
- `directives_saved(dict)` - Persist directives

---

## Implementation Plan

### Tollgate 1: Database Schema & Models
**Objective:** Foundation for data persistence

**Tasks:**
1. Add 3 new tables to `schema.sql` and `full_schema.sql`
2. Create `owner_directives.py` model with validation
3. Create `staff_member.py` model with StaffType enum
4. Write unit tests for model serialization/deserialization

**Files:**
- `src/game_cycle/database/schema.sql` (modify)
- `src/game_cycle/database/full_schema.sql` (modify)
- `src/game_cycle/models/owner_directives.py` (create)
- `src/game_cycle/models/staff_member.py` (create)
- `tests/game_cycle/models/test_owner_directives.py` (create)

**Acceptance Criteria:**
- [ ] Tables created in schema files
- [ ] Models have to_dict/from_dict methods
- [ ] OwnerDirectives.to_draft_direction() works
- [ ] OwnerDirectives.to_fa_guidance() works
- [ ] Unit tests pass

---

### Tollgate 2: Database API Classes
**Objective:** CRUD operations for owner data

**Tasks:**
1. Create `OwnerDirectivesAPI` with get/save/clear methods
2. Create `StaffAPI` with staff assignment and candidate methods
3. Write integration tests with test database

**Files:**
- `src/game_cycle/database/owner_directives_api.py` (create)
- `src/game_cycle/database/staff_api.py` (create)
- `tests/game_cycle/database/test_owner_directives_api.py` (create)
- `tests/game_cycle/database/test_staff_api.py` (create)

**Acceptance Criteria:**
- [ ] get_directives returns None for missing, Dict for existing
- [ ] save_directives uses upsert (INSERT OR REPLACE)
- [ ] get_staff_assignment returns gm + hc data
- [ ] save_candidates clears old candidates before inserting
- [ ] Integration tests pass with actual SQLite

---

### Tollgate 3: Staff Generator Service
**Objective:** Procedural candidate generation

**Tasks:**
1. Implement name generation with uniqueness guarantee
2. Implement trait variation (±0.1 on 2-3 traits)
3. Implement history generation from templates
4. Create candidate generation methods for GM and HC
5. Write unit tests for generation variety

**Files:**
- `src/game_cycle/services/staff_generator_service.py` (create)
- `tests/game_cycle/services/test_staff_generator_service.py` (create)

**Acceptance Criteria:**
- [ ] 5 candidates have 5 unique names
- [ ] Candidates have varied archetypes (excludes current)
- [ ] Trait variations are within ±0.1 of baseline
- [ ] History strings are grammatically correct
- [ ] Unit tests verify variety across 100 generations

---

### Tollgate 4: Owner Service
**Objective:** Business logic orchestration

**Tasks:**
1. Implement staff retrieval and initialization
2. Implement fire flow (generate + save candidates)
3. Implement hire flow (select candidate + update assignment)
4. Implement directive get/save
5. Write integration tests

**Files:**
- `src/game_cycle/services/owner_service.py` (create)
- `tests/game_cycle/services/test_owner_service.py` (create)

**Acceptance Criteria:**
- [ ] get_current_staff returns None for new dynasty
- [ ] fire_gm generates candidates and saves to DB
- [ ] hire_gm updates staff assignment with selected candidate
- [ ] save_directives persists to database
- [ ] Integration tests pass end-to-end

---

### Tollgate 5: UI Implementation
**Objective:** Fully functional Owner Review page

**Tasks:**
1. Rewrite `owner_view.py` with 3-tab structure
2. Implement Season Summary tab with record display
3. Implement Staff Decisions tab with stacked widgets
4. Implement Strategic Direction tab with all inputs
5. Wire signals to controller/main window

**Files:**
- `game_cycle_ui/views/owner_view.py` (rewrite)
- `game_cycle_ui/controllers/stage_controller.py` (modify signals)

**Acceptance Criteria:**
- [ ] 3 tabs display correctly
- [ ] Fire button switches to candidate list
- [ ] Hire button selects candidate and switches back
- [ ] Save Directives button emits signal with data
- [ ] Continue button advances to Franchise Tag

---

### Tollgate 6: Handler Integration
**Objective:** Connect UI to backend

**Tasks:**
1. Update `_execute_owner` in offseason handler
2. Initialize default staff for new dynasties
3. Load previous directives for display
4. Wire main_window signals to OwnerService

**Files:**
- `src/game_cycle/handlers/offseason.py` (modify)
- `game_cycle_ui/main_window.py` (modify)

**Acceptance Criteria:**
- [ ] New dynasty gets default GM and HC
- [ ] Owner view displays current staff from database
- [ ] Fire/hire actions persist to database
- [ ] Directives persist across app restart

---

### Tollgate 7: Service Integration
**Objective:** Directives influence GM behavior

**Tasks:**
1. Draft service loads owner directives and converts to DraftDirection
2. FA service loads owner directives and converts to FAGuidance
3. Verify priority positions affect scoring
4. Verify wishlists affect candidate selection

**Files:**
- `src/game_cycle/services/draft_service.py` (modify)
- `src/game_cycle/services/free_agency_service.py` (modify)
- `src/game_cycle/services/gm_fa_proposal_engine.py` (modify)

**Acceptance Criteria:**
- [ ] Draft picks reflect owner's draft_strategy
- [ ] FA proposals reflect owner's fa_philosophy
- [ ] Priority positions get +15 bonus in scoring
- [ ] Wishlist players get additional bonus
- [ ] Integration test verifies end-to-end flow

---

## File Structure

### New Files

```
src/game_cycle/models/
  owner_directives.py
  staff_member.py

src/game_cycle/database/
  owner_directives_api.py
  staff_api.py

src/game_cycle/services/
  staff_generator_service.py
  owner_service.py

tests/game_cycle/models/
  test_owner_directives.py
  test_staff_member.py

tests/game_cycle/database/
  test_owner_directives_api.py
  test_staff_api.py

tests/game_cycle/services/
  test_staff_generator_service.py
  test_owner_service.py
```

### Modified Files

```
src/game_cycle/database/schema.sql
src/game_cycle/database/full_schema.sql
game_cycle_ui/views/owner_view.py
src/game_cycle/handlers/offseason.py
game_cycle_ui/main_window.py
src/game_cycle/services/draft_service.py
src/game_cycle/services/free_agency_service.py
src/game_cycle/services/gm_fa_proposal_engine.py
```

---

## Testing Strategy

**Unit Tests (25+ tests):**
- OwnerDirectives serialization (5 tests)
- StaffMember serialization (5 tests)
- StaffGeneratorService variety (8 tests)
- API CRUD operations (7 tests)

**Integration Tests (10+ tests):**
- End-to-end hire flow (3 tests)
- Directive persistence across restart (2 tests)
- Draft service directive loading (2 tests)
- FA service directive loading (2 tests)
- Full offseason flow (1 test)

---

## Dependencies

**Required:**
- Milestone 9: Draft Direction (DraftStrategy enum, pattern reference)
- Milestone 10: GM FA (FAPhilosophy enum, pattern reference)
- GM Archetype system (`src/team_management/gm_archetype.py`)
- HC Archetype system (`src/play_engine/play_calling/head_coach.py`)

**Optional:**
- Milestone 8: Team Statistics (for season summary display)

---

## Success Metrics

- [ ] Owner can fire GM and select replacement from 3-5 candidates
- [ ] Owner can fire HC and select replacement from 3-5 candidates
- [ ] Owner can set win target (0-17)
- [ ] Owner can set 1-5 priority positions
- [ ] Owner can set draft strategy and FA philosophy
- [ ] Owner can add player wishlists
- [ ] All directives persist to database
- [ ] Directives survive app restart
- [ ] Draft service uses owner's draft direction
- [ ] FA service uses owner's FA guidance

---

## Summary

Milestone 13 transforms the Owner Review page from a placeholder to the strategic command center for the franchise. Key features:

1. **Staff Management:** Fire underperformers, hire from procedurally generated candidates
2. **Strategic Direction:** Set win targets, position priorities, player wishlists
3. **Full Persistence:** All decisions survive app restart
4. **GM Behavior Integration:** Directives flow through draft and FA systems

This completes the Owner → GM delegation model, giving owners meaningful control over franchise direction while letting the GM handle day-to-day execution.
