# Milestone 1 Requirements: Offseason-to-Preseason Transition

**Last Updated:** 2025-11-09
**Status:** 🔴 Critical - Implementation Needed
**Related Documents:**
- [01_audit_report.md](./01_audit_report.md) - System audit findings
- [/docs/plans/statistics_preservation.md](../plans/statistics_preservation.md) - Statistics system
- [/docs/plans/salary_cap_plan.md](../plans/salary_cap_plan.md) - Salary cap architecture

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Critical Systems (Must Have - P0)](#critical-systems-must-have---p0)
3. [High Priority Systems (Should Have - P1)](#high-priority-systems-should-have---p1)
4. [Nice-to-Have Systems (Optional - P2)](#nice-to-have-systems-optional---p2)
5. [Already Implemented (Reference)](#already-implemented-reference)
6. [Cross-Cutting Concerns](#cross-cutting-concerns)
7. [Database Schema Requirements](#database-schema-requirements)
8. [Integration Points](#integration-points)
9. [Success Metrics](#success-metrics)

---

## Executive Summary

### Goal

Enable **repeatable multi-year season cycles** allowing users to simulate 10+ consecutive NFL seasons without manual intervention. The system must handle all necessary transitions from the end of one season's offseason (late August) to the start of the next season's preseason (early September).

### Current State

Based on [01_audit_report.md](./01_audit_report.md):
- ✅ **2 of 14 systems** implemented (14% complete)
- ✅ Core infrastructure production-ready (statistics, salary cap, player generation)
- ❌ **Year-over-year integration missing** - systems exist but don't coordinate
- ❌ **~2,150 LOC** needed across 12 missing systems

### Deliverables

**Phase 1 (Week 1-2):** Enable 2+ consecutive seasons
**Phase 2 (Week 2-3):** Add realistic player progression
**Phase 3 (Week 3-4):** Polish and comprehensive testing

---

## Critical Systems (Must Have - P0)

### System 1: Season Year Increment

**Priority:** P0 (Critical)
**Estimated LOC:** 50
**Owner:** `SeasonYearSynchronizer` (existing infrastructure)
**File:** `src/season/season_cycle_controller.py` (lines 2000+)

#### Functional Requirements

**FR-1.1:** Increment season year atomically during offseason-to-preseason transition
- Input: Current season year (e.g., 2024)
- Output: Incremented season year (e.g., 2025)
- Triggers: `OffseasonToPreseasonHandler.execute()` completion

**FR-1.2:** Update all dependent systems with new season year
- Controller state: `SeasonCycleController.season_year`
- Database state: `dynasty_state.season`
- Calendar year: Advance to next NFL season dates

**FR-1.3:** Validate synchronization after increment
- Controller year = Database year
- No drift between components
- Trigger auto-recovery if mismatch detected

#### Non-Functional Requirements

**NFR-1.1 Atomicity:** Season year increment must be atomic (all or nothing)
**NFR-1.2 Consistency:** No drift between controller/database allowed
**NFR-1.3 Performance:** Increment completes in <100ms

#### API Contract

```python
# Method signature (already exists in SeasonYearSynchronizer)
def increment_year(self) -> int:
    """
    Atomically increment season year across all systems.

    Returns:
        New season year

    Raises:
        YearIncrementError: If synchronization fails
    """
    pass

# Usage in handler
class OffseasonToPreseasonHandler:
    def execute(self, context: TransitionContext) -> TransitionResult:
        # Step 1: Increment year FIRST
        new_year = self._increment_season_year()

        # Step 2: Use new year for all subsequent operations
        self._validate_games_exist(new_year)
        self._reset_standings(new_year)
        # ... etc
```

#### Database Schema Changes

**No schema changes needed.** Uses existing infrastructure:
- `dynasty_state.season` column (already exists)
- `SeasonYearSynchronizer._update_database_year()` method (already exists)

#### Acceptance Criteria

✅ AC-1.1: Season year increments from 2024 → 2025 during transition
✅ AC-1.2: Controller and database remain synchronized (verified via guards)
✅ AC-1.3: No drift warnings triggered after increment
✅ AC-1.4: Statistics tagged with correct season year (2025, not 2024)
✅ AC-1.5: Second consecutive transition increments 2025 → 2026 correctly

#### Dependencies

- `SeasonYearSynchronizer` (exists - `src/season/year_management/season_year_synchronizer.py`)
- `DynastyStateAPI.update_state()` (exists - `src/database/dynasty_state_api.py`)
- Auto-recovery guards (exist - Phase 5 complete)

---

### System 2: Draft Class Generation Timing Fix

**Priority:** P0 (Critical)
**Estimated LOC:** 50
**Owner:** `OffseasonToPreseasonHandler`
**File:** `src/season/phase_transition/transition_handlers/offseason_to_preseason.py`

#### Functional Requirements

**FR-2.1:** Generate draft class for **next** season (N+1) during offseason of season N
- Current behavior: Generates for season N at season N start ❌
- Needed behavior: Generate for season N+1 during season N offseason ✅
- Example: During 2024 offseason → generate 2025 draft class

**FR-2.2:** Validate draft class exists before preseason starts
- Check: `DraftClassAPI.get_draft_class(season=N+1)` returns 224 prospects
- If missing: Generate emergency class (should never happen in production)

**FR-2.3:** Do NOT regenerate if draft class already exists
- Check database first
- Only generate if missing (idempotency)

#### Non-Functional Requirements

**NFR-2.1 Correctness:** Draft class must be for NEXT season, not current
**NFR-2.2 Idempotency:** Safe to call multiple times without duplication
**NFR-2.3 Performance:** Generation completes in <5 seconds for 224 prospects

#### API Contract

```python
# In OffseasonToPreseasonHandler
def _generate_draft_class(self, effective_year: int) -> None:
    """
    Generate draft class for next season if not already present.

    Args:
        effective_year: New season year (e.g., 2025)

    Raises:
        DraftGenerationError: If generation fails
    """
    # Check if already exists
    existing = self._draft_api.get_draft_class(
        season=effective_year,
        dynasty_id=self._dynasty_id
    )

    if existing and len(existing) >= 224:
        self.logger.info(f"Draft class for {effective_year} already exists ({len(existing)} prospects)")
        return

    # Generate new draft class
    self.logger.info(f"Generating draft class for season {effective_year}...")
    self._draft_generator.generate_class(
        season=effective_year,
        dynasty_id=self._dynasty_id,
        num_prospects=224  # 7 rounds × 32 picks
    )
```

#### Database Schema Changes

**No schema changes needed.** Uses existing tables:
- `draft_prospects` table (already exists)
- `dynasty_id` column for isolation (already exists)
- `season` column for year scoping (already exists)

#### Acceptance Criteria

✅ AC-2.1: Draft class generated during 2024 offseason has `season=2025`
✅ AC-2.2: 224 prospects generated (7 rounds × 32 picks)
✅ AC-2.3: Position distribution matches NFL realism (QB 15%, EDGE 20%, etc.)
✅ AC-2.4: Second call to generate is idempotent (no duplicates)
✅ AC-2.5: Draft prospects available for scouting before preseason starts

#### Dependencies

- `DraftClassGenerator` (exists - `src/player_generation/generators/draft_class_generator.py`)
- `DraftClassAPI` (exists - `src/database/draft_class_api.py`)
- `PlayerGenerationContext` (exists - `src/player_generation/core/generation_context.py`)

---

### System 3: Salary Cap Year Rollover

**Priority:** P0 (Critical)
**Estimated LOC:** 150
**Owner:** `CapYearRolloverService` (NEW - to be created)
**File:** `src/salary_cap/cap_year_rollover.py` (NEW)

#### Functional Requirements

**FR-3.1:** Load new salary cap limit for upcoming season
- Query: `CapDatabaseAPI.get_salary_cap_for_season(season=N+1)`
- Example: 2025 cap = $255.4M
- Store in `team_cap_summary` table for all 32 teams

**FR-3.2:** Calculate carryover from previous season
- Formula: `carryover = previous_cap_space` (if positive)
- Example: Team with $5M space in 2024 → +$5M carryover in 2025
- Negative space (over cap) → $0 carryover (dead money handles it)

**FR-3.3:** Switch roster mode from top-51 to 53-man
- Offseason end: Transition from top-51 calculation
- Preseason start: Use 53-man roster calculation
- Update `team_cap_summary.is_top_51_active = FALSE`

**FR-3.4:** Handle dead money carryover
- June 1 designations: Move Year 2 dead money to current year
- Standard cuts: All dead money already in current year
- Update `team_cap_summary.dead_money_total`

**FR-3.5:** Initialize cap structure for all 32 teams
- Create `team_cap_summary` records if missing
- Set base values: cap limit, carryover, dead money
- Enable 53-man roster mode

#### Non-Functional Requirements

**NFR-3.1 Correctness:** Cap calculations must match NFL CBA rules exactly
**NFR-3.2 Dynasty Isolation:** All operations scoped by `dynasty_id`
**NFR-3.3 Performance:** Rollover for 32 teams completes in <2 seconds
**NFR-3.4 Auditability:** All cap changes logged to transaction log

#### API Contract

```python
class CapYearRolloverService:
    """Service for transitioning salary cap to new season year."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        enable_logging: bool = True
    ):
        self.cap_api = CapDatabaseAPI(database_path)
        self.cap_calc = CapCalculator(database_path)
        self.dynasty_id = dynasty_id

    def rollover_all_teams(
        self,
        old_season: int,
        new_season: int
    ) -> Dict[str, Any]:
        """
        Execute salary cap rollover for all 32 NFL teams.

        Args:
            old_season: Ending season year (e.g., 2024)
            new_season: Starting season year (e.g., 2025)

        Returns:
            Dict with:
                - teams_processed: 32
                - total_carryover: Sum of all team carryovers
                - new_cap_limit: New season cap limit
                - dead_money_total: Total dead money across league

        Raises:
            CapRolloverError: If rollover fails for any team
        """
        pass

    def rollover_team_cap(
        self,
        team_id: int,
        old_season: int,
        new_season: int
    ) -> Dict[str, Any]:
        """
        Execute cap rollover for single team.

        Args:
            team_id: Team ID (1-32)
            old_season: Ending season year
            new_season: Starting season year

        Returns:
            Dict with:
                - team_id: Team ID
                - old_cap_space: Previous season cap space
                - carryover: Amount carried to new season
                - new_cap_limit: New season base cap
                - total_cap_available: new_cap_limit + carryover
                - dead_money: Dead money for new season
                - roster_mode: "53-man" (always for new season start)
        """
        pass
```

#### Database Schema Changes

**Existing tables (no changes needed):**
- `team_cap_summary` table (exists)
- `salary_caps` table (exists)
- `contracts` table (exists)
- `contract_year_details` table (exists)

**New columns needed:**
```sql
-- Add to team_cap_summary if missing
ALTER TABLE team_cap_summary
ADD COLUMN carryover_from_previous INTEGER DEFAULT 0;

ALTER TABLE team_cap_summary
ADD COLUMN is_top_51_active BOOLEAN DEFAULT TRUE;
```

#### Acceptance Criteria

✅ AC-3.1: All 32 teams have cap summary for new season
✅ AC-3.2: Cap limit matches NFL value (e.g., $255.4M for 2025)
✅ AC-3.3: Carryover calculated correctly for teams with cap space
✅ AC-3.4: Roster mode switched to 53-man for preseason
✅ AC-3.5: Dead money from June 1 cuts applied to Year 2
✅ AC-3.6: Transaction log shows all cap operations

#### Dependencies

- `CapCalculator` (exists - `src/salary_cap/cap_calculator.py`)
- `CapDatabaseAPI` (exists - `src/salary_cap/cap_database_api.py`)
- `ContractManager` (exists - `src/salary_cap/contract_manager.py`)

---

### System 4: Contract Year Increments

**Priority:** P0 (Critical)
**Estimated LOC:** 100
**Owner:** `ContractYearManager` (NEW - to be created)
**File:** `src/salary_cap/contract_year_manager.py` (NEW)

#### Functional Requirements

**FR-4.1:** Increment contract year for all active contracts
- Query: `SELECT * FROM contracts WHERE status='active' AND dynasty_id=?`
- Update: `SET current_year = current_year + 1`
- Filter: Only contracts with `current_year < total_years`

**FR-4.2:** Move expired contracts to history
- Condition: `current_year >= total_years` after increment
- Action: `UPDATE contracts SET status='expired', end_date=?`
- Archive: Copy to `contract_history` table for record-keeping

**FR-4.3:** Update free agent status for expired contracts
- Query: Contracts with `status='expired'` and `player_status IN ('UFA', 'RFA', 'ERFA')`
- Action: Add to `free_agents` table
- Remove: Delete from team rosters

**FR-4.4:** Recalculate dead money for active contracts
- For each active contract: Update `contract_year_details` for new year
- Recalculate: Remaining bonus proration, guaranteed salary
- Update: Dead money projections in `team_cap_summary`

#### Non-Functional Requirements

**NFR-4.1 Atomicity:** All contract updates in single transaction
**NFR-4.2 Data Integrity:** No orphaned contracts or roster entries
**NFR-4.3 Performance:** Process 32 teams × ~70 contracts/team in <5 seconds
**NFR-4.4 Reversibility:** Transaction rollback on any error

#### API Contract

```python
class ContractYearManager:
    """Manages contract year transitions and expiration handling."""

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        enable_persistence: bool = True
    ):
        self.db_api = CapDatabaseAPI(database_path)
        self.contract_mgr = ContractManager(database_path)
        self.dynasty_id = dynasty_id

    def increment_all_contracts(
        self,
        old_season: int,
        new_season: int
    ) -> Dict[str, Any]:
        """
        Increment contract years for all active contracts across all teams.

        Args:
            old_season: Ending season year
            new_season: Starting season year

        Returns:
            Dict with:
                - total_contracts_updated: Number of contracts incremented
                - contracts_expired: Number moved to expired status
                - new_free_agents: Number of players added to FA pool
                - errors: List of any errors encountered

        Raises:
            ContractIncrementError: If transaction fails
        """
        pass

    def expire_contracts_for_team(
        self,
        team_id: int,
        new_season: int
    ) -> List[int]:
        """
        Identify and expire contracts for a single team.

        Args:
            team_id: Team ID (1-32)
            new_season: New season year

        Returns:
            List of player_ids whose contracts expired
        """
        pass
```

#### Database Schema Changes

**Existing tables (use as-is):**
- `contracts` table (has `current_year`, `total_years` columns)
- `contract_year_details` table (has year-by-year cap hits)
- `free_agents` table (for expired contract players)

**New table needed:**
```sql
CREATE TABLE IF NOT EXISTS contract_history (
    contract_id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    start_season INTEGER NOT NULL,
    end_season INTEGER NOT NULL,
    total_years INTEGER NOT NULL,
    total_value INTEGER NOT NULL,
    aav INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,
    guaranteed_money INTEGER DEFAULT 0,
    contract_type TEXT,  -- 'veteran', 'rookie', 'franchise_tag', etc.
    expired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

CREATE INDEX idx_contract_history_player ON contract_history(player_id);
CREATE INDEX idx_contract_history_dynasty ON contract_history(dynasty_id);
```

#### Acceptance Criteria

✅ AC-4.1: All active contracts incremented from year 1 → year 2
✅ AC-4.2: 4-year contracts entering year 4 NOT expired (still have 1 year left)
✅ AC-4.3: 4-year contracts entering year 5 → moved to expired status
✅ AC-4.4: Expired UFA contracts → players added to `free_agents` table
✅ AC-4.5: Contract history table populated with expired contracts
✅ AC-4.6: No duplicate free agent entries created

#### Dependencies

- `CapDatabaseAPI.get_team_contracts()` (exists)
- `ContractManager.update_contract()` (exists)
- `DatabaseConnection` for transaction handling (exists)

---

## High Priority Systems (Should Have - P1)

### System 5: Player Retirements

**Priority:** P1 (High)
**Estimated LOC:** 200
**Owner:** `PlayerLifecycleManager` (NEW - to be created)
**File:** `src/player_management/player_lifecycle_manager.py` (NEW)

#### Functional Requirements

**FR-5.1:** Identify retirement candidates based on criteria
- **Age-based:** Players 35+ with declining ratings (overall < 75)
- **Injury-based:** Players with career-ending injuries (injury_status='retired')
- **Performance-based:** Veterans with 3+ consecutive years of minimal playing time
- **Voluntary:** Top players retiring at peak (rare, 1-2% chance if 10+ years pro)

**FR-5.2:** Calculate retirement probability
```python
def calculate_retirement_probability(player: Player) -> float:
    """
    NFL-realistic retirement probability.

    Factors:
    - Age: 35 (5%), 36 (15%), 37 (30%), 38 (50%), 39+ (75%)
    - Rating: <70 (+20%), 70-75 (+10%), 75-80 (+5%)
    - Years Pro: 10+ years (+5% per year over 10)
    - Injury History: Career-ending (100%), chronic (50%)
    - Position: RB retire younger, QB/K retire older

    Returns:
        Probability from 0.0 to 1.0
    """
```

**FR-5.3:** Execute retirement for selected players
- Update `players` table: `SET status='retired', retired_date=?`
- Remove from team rosters: `DELETE FROM player_rosters WHERE player_id=?`
- Calculate cap impact: Remaining bonus proration accelerates as dead money
- Add to `retired_players` history table

**FR-5.4:** Generate retirement announcements
- Create `PlayerRetirementEvent` for UI display
- Include: Player name, position, years pro, career stats summary
- Store in `events` table with `event_type='player_retirement'`

#### Non-Functional Requirements

**NFR-5.1 Realism:** Retirement rates match NFL averages (~10-15% of 35+ players)
**NFR-5.2 Cap Compliance:** Retirement dead money correctly applied
**NFR-5.3 Performance:** Process 32 teams × ~5 retirements/team in <3 seconds
**NFR-5.4 Transparency:** All retirements logged and visible to user

#### API Contract

```python
class PlayerLifecycleManager:
    """Manages player lifecycle events: retirements, aging, attribute decay."""

    def process_retirements(
        self,
        season: int,
        ai_controlled: bool = True
    ) -> Dict[str, Any]:
        """
        Process player retirements for all teams.

        Args:
            season: Current season year
            ai_controlled: If True, AI decides retirements. If False, user controls.

        Returns:
            Dict with:
                - total_retirements: Number of players retired
                - retirements_by_team: {team_id: count}
                - cap_impact_total: Total dead money across league
                - retired_players: List of {player_id, name, position, years_pro, cap_impact}
        """
        pass
```

#### Database Schema Changes

**New table needed:**
```sql
CREATE TABLE IF NOT EXISTS retired_players (
    player_id INTEGER PRIMARY KEY,
    dynasty_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT NOT NULL,
    team_id INTEGER,  -- Last team
    retired_season INTEGER NOT NULL,
    years_pro INTEGER NOT NULL,
    age_at_retirement INTEGER,
    career_stats_json TEXT,  -- JSON blob with career totals
    hall_of_fame_eligible BOOLEAN DEFAULT FALSE,
    retired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

CREATE INDEX idx_retired_players_dynasty ON retired_players(dynasty_id);
CREATE INDEX idx_retired_players_team ON retired_players(team_id);
```

**Update players table:**
```sql
ALTER TABLE players ADD COLUMN status TEXT DEFAULT 'active';  -- 'active', 'retired', 'suspended'
ALTER TABLE players ADD COLUMN retired_date TEXT;
```

#### Acceptance Criteria

✅ AC-5.1: 10-15% of 35+ players retire each offseason
✅ AC-5.2: Players with career-ending injuries retire immediately (100%)
✅ AC-5.3: Retirement cap hit equals remaining bonus proration
✅ AC-5.4: Retired players removed from active rosters
✅ AC-5.5: `retired_players` table populated with career stats
✅ AC-5.6: User notified of all retirements via events

#### Dependencies

- `PlayerDataLoader` (exists - `src/team_management/player_data_loader.py`)
- `CapCalculator.calculate_dead_money()` (exists)
- `EventDatabaseAPI.create_event()` (exists)

---

### System 6: Player Aging

**Priority:** P1 (High)
**Estimated LOC:** 150
**Owner:** `PlayerLifecycleManager` (same as System 5)
**File:** `src/player_management/player_lifecycle_manager.py`

#### Functional Requirements

**FR-6.1:** Increment `years_pro` for all active players
- Query: `SELECT * FROM players WHERE status='active'`
- Update: `SET years_pro = years_pro + 1`

**FR-6.2:** Calculate player age from birth year
```python
def calculate_age(birth_year: int, current_season: int) -> int:
    """
    Calculate player age at start of season.

    Season starts in September, so:
    - Player born 1995 → Age in 2025 season = 2025 - 1995 = 30
    """
    return current_season - birth_year
```

**FR-6.3:** Apply attribute decay for aging players
```python
def apply_attribute_decay(player: Player) -> Player:
    """
    Apply age-based attribute decay.

    Decay curves by attribute type:
    - Speed/Acceleration: Declines 25+ (peak: 23-24)
    - Strength/Power: Maintains 25-32, declines 33+
    - Awareness/IQ: Improves until 30, maintains until 35
    - Durability/Injury: Declines 28+

    Position-specific:
    - RB: Harsh decline after 27 (speed critical)
    - QB: Gradual decline, maintains mental attributes
    - OL/DL: Strength holds longer, mobility declines
    - K/P: Minimal decline until 35+
    """
```

**FR-6.4:** Update potential ratings
- Young players (age < 25): Potential may increase
- Prime players (age 25-29): Potential stable
- Declining players (age 30+): Potential decreases each year

#### Non-Functional Requirements

**NFR-6.1 Realism:** Decay curves match NFL player aging patterns
**NFR-6.2 Performance:** Age all ~2,500 players in <2 seconds
**NFR-6.3 Consistency:** Same player ages identically in all dynasties
**NFR-6.4 Transparency:** Attribute changes logged for user review

#### API Contract

```python
# In PlayerLifecycleManager
def age_all_players(
    self,
    season: int
) -> Dict[str, Any]:
    """
    Apply aging effects to all active players.

    Args:
        season: New season year

    Returns:
        Dict with:
            - total_players_aged: Count of players processed
            - average_age: League average age
            - attribute_changes: {player_id: {attribute: old_val → new_val}}
            - breakout_candidates: Young players with potential increases
    """
    pass
```

#### Database Schema Changes

**Update players table:**
```sql
-- Add columns if missing
ALTER TABLE players ADD COLUMN birth_year INTEGER;
ALTER TABLE players ADD COLUMN years_pro INTEGER DEFAULT 0;
ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 70;  -- 0-100 scale

-- Add attribute columns for decay tracking
ALTER TABLE players ADD COLUMN speed INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN acceleration INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN strength INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN awareness INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN durability INTEGER DEFAULT 70;
```

**New table for attribute history:**
```sql
CREATE TABLE IF NOT EXISTS player_attribute_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    age INTEGER NOT NULL,
    overall_rating INTEGER NOT NULL,
    speed INTEGER,
    acceleration INTEGER,
    strength INTEGER,
    awareness INTEGER,
    potential INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id)
);

CREATE INDEX idx_attribute_history_player ON player_attribute_history(player_id, season);
```

#### Acceptance Criteria

✅ AC-6.1: All active players have `years_pro` incremented by 1
✅ AC-6.2: Player ages calculated correctly from birth year
✅ AC-6.3: 30+ year old RBs show speed decline (-2 to -4 points/year)
✅ AC-6.4: QBs maintain awareness/intelligence ratings into mid-30s
✅ AC-6.5: Rookie potential can increase (e.g., 75 → 78 after strong season)
✅ AC-6.6: Attribute changes logged to `player_attribute_history`

#### Dependencies

- `PlayerDataLoader` (exists)
- Player attribute system (exists in `src/team_management/players/player.py`)

---

### System 7: Free Agent Pool Updates

**Priority:** P1 (High)
**Estimated LOC:** 100
**Owner:** `FreeAgencyManager` (exists - extend functionality)
**File:** `src/offseason/free_agency_manager.py` (extend)

#### Functional Requirements

**FR-7.1:** Move unsigned expired contracts to FA pool
- Query: Players with `contracts.status='expired'` AND NOT signed to new team
- Insert: `INSERT INTO free_agents (player_id, fa_type, previous_team_id, ...)`
- Type: Categorize as UFA, RFA, or ERFA based on accrued seasons

**FR-7.2:** Categorize free agent types
```python
def determine_fa_type(years_pro: int, drafted: bool) -> str:
    """
    Determine free agent type per NFL CBA.

    UFA (Unrestricted Free Agent): 4+ accrued seasons
    RFA (Restricted Free Agent): 3 accrued seasons
    ERFA (Exclusive Rights Free Agent): <3 accrued seasons

    Accrued season = 6+ games on active/IR in a season
    """
    if years_pro >= 4:
        return "UFA"
    elif years_pro == 3:
        return "RFA"
    else:
        return "ERFA"
```

**FR-7.3:** Update FA contract years
- Each year in FA pool decrements value
- After 2+ years unsigned: Significant value reduction
- After 3+ years unsigned: Minimum contract only

**FR-7.4:** Clear from team rosters
- Remove: `DELETE FROM player_rosters WHERE player_id IN (...)`
- Validate: No active roster entries for FA pool players

#### Non-Functional Requirements

**NFR-7.1 Accuracy:** FA type categorization matches NFL CBA rules
**NFR-7.2 Performance:** Update FA pool for ~500 players in <1 second
**NFR-7.3 Data Integrity:** No duplicate FA entries allowed

#### API Contract

```python
# Extend FreeAgencyManager
def update_free_agent_pool(
    self,
    old_season: int,
    new_season: int
) -> Dict[str, Any]:
    """
    Update free agent pool for new season.

    Args:
        old_season: Ending season
        new_season: Starting season

    Returns:
        Dict with:
            - new_free_agents: Number added to pool
            - ufas: Count of UFAs
            - rfas: Count of RFAs
            - erfas: Count of ERFAs
            - removed: Players who retired/left pool
    """
    pass
```

#### Database Schema Changes

**Update free_agents table:**
```sql
-- Add columns if missing
ALTER TABLE free_agents ADD COLUMN years_in_fa_pool INTEGER DEFAULT 0;
ALTER TABLE free_agents ADD COLUMN market_value_aav INTEGER;  -- Estimated AAV
ALTER TABLE free_agents ADD COLUMN market_value_years INTEGER;  -- Estimated years
```

#### Acceptance Criteria

✅ AC-7.1: All unsigned expired contracts → FA pool
✅ AC-7.2: FA types correctly categorized (UFA/RFA/ERFA)
✅ AC-7.3: No duplicate FA entries created
✅ AC-7.4: Players removed from active rosters
✅ AC-7.5: Market values estimated for all FAs

#### Dependencies

- `FreeAgencyManager` (exists - `src/offseason/free_agency_manager.py`)
- `MarketValueCalculator` (exists - `src/offseason/market_value_calculator.py`)
- `CapDatabaseAPI.get_pending_free_agents()` (exists)

---

### System 8: Rookie Contract Generation

**Priority:** P1 (High)
**Estimated LOC:** 150
**Owner:** `CapYearRolloverService` (extend from System 3)
**File:** `src/salary_cap/cap_year_rollover.py`

#### Functional Requirements

**FR-8.1:** Generate rookie contracts for drafted players
- Query: `SELECT * FROM draft_picks WHERE season=? AND dynasty_id=?`
- For each pick: Create contract based on slot value

**FR-8.2:** Apply NFL rookie wage scale
```python
def calculate_rookie_contract_value(overall_pick: int) -> Dict[str, int]:
    """
    Calculate rookie contract value per NFL wage scale.

    2024 Rookie Wage Scale (approximate):
    - Pick #1: 4 years, $41M, $27M guaranteed
    - Pick #10: 4 years, $19M, $12M guaranteed
    - Pick #32: 4 years, $11M, $7M guaranteed
    - Pick #100: 4 years, $4M, $0.5M guaranteed
    - Pick #200: 4 years, $3.5M, $0.1M guaranteed

    All rookie contracts:
    - Length: 4 years (5th year option for 1st rounders)
    - Signing bonus: 50-70% of guaranteed money
    - Annual escalators: 2-5% per year

    Returns:
        {
            'total_value': int,
            'aav': int,
            'guaranteed': int,
            'signing_bonus': int,
            'years': 4
        }
    """
```

**FR-8.3:** Link contracts to rosters
- Insert: `INSERT INTO contracts (...)`
- Link: `INSERT INTO player_rosters (player_id, team_id, depth_position, ...)`

**FR-8.4:** Apply to team cap
- Rookie contracts count against cap immediately
- Signing bonus prorated over 4 years
- Update `team_cap_summary` with new cap hits

#### Non-Functional Requirements

**NFR-8.1 Accuracy:** Contract values match NFL rookie wage scale
**NFR-8.2 Cap Compliance:** All rookie contracts fit within rookie pool allocations
**NFR-8.3 Performance:** Generate 224 contracts in <3 seconds

#### API Contract

```python
# In CapYearRolloverService
def generate_rookie_contracts(
    self,
    season: int
) -> Dict[str, Any]:
    """
    Generate rookie contracts for all drafted players.

    Args:
        season: Season year

    Returns:
        Dict with:
            - contracts_created: Number of contracts generated
            - total_cap_impact: Total cap hit across league
            - highest_contract: {player_id, team_id, value}
    """
    pass
```

#### Database Schema Changes

**No schema changes needed.** Uses existing tables:
- `contracts` table
- `contract_year_details` table
- `draft_picks` table (links picks to contracts)

#### Acceptance Criteria

✅ AC-8.1: All 224 draft picks have contracts created
✅ AC-8.2: Pick #1 contract value ≈ $41M (matches wage scale)
✅ AC-8.3: All contracts = 4 years (no 3-year or 5-year contracts)
✅ AC-8.4: Signing bonuses prorated correctly (4-year max)
✅ AC-8.5: Rookies added to team rosters with depth positions
✅ AC-8.6: Cap space reduced by Year 1 rookie cap hits

#### Dependencies

- `ContractManager.create_contract()` (exists)
- `DraftManager.get_draft_picks()` (exists - `src/offseason/draft_manager.py`)
- Rookie wage scale data (NEW - add to `src/config/rookie_wage_scale.json`)

---

## Nice-to-Have Systems (Optional - P2)

### System 9: Statistics Archival

**Priority:** P2 (Optional)
**Estimated LOC:** 500
**Owner:** `StatisticsArchivalService` (NEW)
**File:** `src/statistics/archival_service.py` (NEW)

#### Functional Requirements

**FR-9.1:** Archive old season statistics (hot → warm → cold storage)
- Hot: Current season + 2 previous seasons (fast queries)
- Warm: Seasons 3-10 ago (slower queries, compressed)
- Cold: Seasons 11+ ago (archival only, minimal access)

**FR-9.2:** Aggregate team/player statistics by season
- Sum: Totals for passing yards, rushing yards, etc.
- Avg: Averages for passer rating, YPC, etc.
- Store in `season_summary_stats` table

**FR-9.3:** Compress play-by-play data
- Keep box scores forever
- Archive detailed play data after 5 seasons
- Option to export before archival

**FR-9.4:** Maintain statistical leaderboards
- Career leaders (all-time)
- Single-season leaders (per season)
- Playoff leaders (separate from regular season)

#### Non-Functional Requirements

**NFR-9.1 Performance:** Archival runs in background, doesn't block gameplay
**NFR-9.2 Storage:** Reduce database size by 30-50% for 10+ season dynasties
**NFR-9.3 Reversibility:** Archived data can be restored if needed

#### API Contract

```python
class StatisticsArchivalService:
    def archive_season(self, season: int, retention_policy: str = "standard"):
        """Archive statistics for completed season."""
        pass
```

#### Acceptance Criteria

✅ AC-9.1: Statistics older than 10 seasons archived
✅ AC-9.2: Database size reduced by 40% after archival
✅ AC-9.3: Career leaderboards still functional
✅ AC-9.4: Season summaries remain queryable

---

### System 10: Event Cleanup

**Priority:** P2 (Optional)
**Estimated LOC:** 100
**Owner:** `EventCleanupService` (NEW)
**File:** `src/events/event_cleanup_service.py` (NEW)

#### Functional Requirements

**FR-10.1:** Delete completed game events from previous season
**FR-10.2:** Delete completed deadline events from offseason
**FR-10.3:** Archive milestone events to history table
**FR-10.4:** Maintain event count < 10,000 entries for performance

#### Acceptance Criteria

✅ AC-10.1: Old game events deleted
✅ AC-10.2: Event table size reduced by 80%
✅ AC-10.3: Calendar performance improved (queries <100ms)

---

### System 11: Depth Chart Initialization

**Priority:** P2 (Optional)
**Estimated LOC:** 150
**Owner:** `DepthChartManager` (exists - extend)
**File:** `src/team_management/depth_chart_manager.py` (extend)

#### Functional Requirements

**FR-11.1:** Re-evaluate depth charts for all teams
**FR-11.2:** Promote rookies based on ratings
**FR-11.3:** Handle retirements (auto-promote backups)
**FR-11.4:** Generate depth chart events for user review

#### Acceptance Criteria

✅ AC-11.1: All 32 teams have valid depth charts
✅ AC-11.2: No positions without starters
✅ AC-11.3: Rookies placed in appropriate depth positions

---

### System 12: Team Needs Re-analysis

**Priority:** P2 (Optional)
**Estimated LOC:** 100
**Owner:** `TeamNeedsAnalyzer` (exists - extend)
**File:** `src/offseason/team_needs_analyzer.py` (extend)

#### Functional Requirements

**FR-12.1:** Re-analyze team needs after roster changes
**FR-12.2:** Update scouting priorities
**FR-12.3:** Generate AI offseason strategy recommendations

#### Acceptance Criteria

✅ AC-12.1: Team needs updated for all 32 teams
✅ AC-12.2: AI draft boards reflect new needs
✅ AC-12.3: Free agency targets aligned with needs

---

## Already Implemented (Reference)

### Schedule Validation ✅

**File:** `src/season/phase_transition/transition_handlers/offseason_to_preseason.py` (lines 422-462)

**What it does:**
- Validates 320 games exist for new season (48 preseason + 272 regular)
- Checks `SCHEDULE_RELEASE` milestone executed successfully (mid-May timing)
- Throws error if games missing

**No changes needed** - Production ready.

---

### Standings Reset ✅

**File:** `src/database/api.py` (lines 192-245)

**What it does:**
- Resets all 32 teams to 0-0-0 for new season
- Creates separate standings records for `season_type='preseason'`, `'regular_season'`, `'playoffs'`
- Clears playoff flags, streaks, rankings

**No changes needed** - Production ready.

---

## Cross-Cutting Concerns

### Dynasty Isolation

**Requirement:** All systems MUST respect `dynasty_id` for data separation.

**Implementation:**
```python
# Every database query MUST include dynasty_id filter
query = "SELECT * FROM players WHERE dynasty_id = ? AND ..."
params = (self.dynasty_id, ...)
```

**Validation:**
- No cross-dynasty data leakage
- User A's retirements don't affect User B's dynasty
- Statistics never mix between dynasties

---

### Transaction Handling

**Requirement:** All year transition operations MUST be atomic.

**Implementation:**
```python
# Use TransactionContext for atomicity
from src.database.transaction_context import TransactionContext

with TransactionContext(db_path, mode="IMMEDIATE") as txn:
    # Step 1: Increment year
    increment_year()

    # Step 2: Rollover cap
    rollover_cap()

    # Step 3: Increment contracts
    increment_contracts()

    # If ANY step fails → automatic rollback
    txn.commit()
```

**Rollback Strategy:**
- On error: All changes reverted
- Database returns to pre-transition state
- User notified of failure
- Manual intervention available

---

### Error Handling and Logging

**Requirement:** All errors MUST be logged with full context.

**Logging Levels:**
- `INFO`: Normal operations (e.g., "Incremented season year: 2024 → 2025")
- `WARNING`: Non-critical issues (e.g., "Draft class already exists, skipping generation")
- `ERROR`: Critical failures (e.g., "Contract increment failed for team 22")
- `CRITICAL`: System-breaking errors (e.g., "Database connection lost during transition")

**Error Context:**
```python
try:
    increment_contracts()
except Exception as e:
    self.logger.error(
        f"Contract increment failed: {e}",
        extra={
            'dynasty_id': self.dynasty_id,
            'season': self.season_year,
            'operation': 'contract_increment',
            'traceback': traceback.format_exc()
        }
    )
    raise ContractIncrementError(f"Failed to increment contracts: {e}") from e
```

---

### Performance Requirements

**Benchmarks:**

| Operation | Target Time | Max Time |
|-----------|-------------|----------|
| Season year increment | <100ms | 500ms |
| Draft class generation | <5s | 10s |
| Cap rollover (32 teams) | <2s | 5s |
| Contract increments (all) | <5s | 10s |
| Player retirements | <3s | 8s |
| Player aging (2,500 players) | <2s | 5s |
| FA pool update | <1s | 3s |
| **Total Transition** | **<20s** | **45s** |

**Optimization Strategies:**
- Batch database operations (INSERT/UPDATE 100 rows at once)
- Use prepared statements
- Index optimization for common queries
- Parallel processing where possible (cap rollover per team)

---

### Testing Requirements

**Unit Tests (Required):**
- Each system has dedicated test file
- 80%+ code coverage minimum
- Mock database for fast tests
- Test both success and failure paths

**Integration Tests (Required):**
- 2-season simulation test
- 10-season simulation test
- Multi-dynasty isolation test
- Transaction rollback test

**Performance Tests (Required):**
- Benchmark each operation
- Validate meets performance targets
- Test with realistic data volumes (2,500 players, 32 teams)

**Manual Validation (Required):**
- Checklist-based validation
- User acceptance testing
- Edge case verification

---

## Database Schema Requirements

### Schema Version: 2.5.0 (Post-Milestone 1)

**New Tables:**
```sql
-- System 4: Contract Year Increments
CREATE TABLE contract_history (...);  -- See System 4

-- System 5: Player Retirements
CREATE TABLE retired_players (...);  -- See System 5

-- System 6: Player Aging
CREATE TABLE player_attribute_history (...);  -- See System 6

-- System 9: Statistics Archival (Optional)
CREATE TABLE season_summary_stats (...);
CREATE TABLE archived_play_data (...);
```

**Table Modifications:**
```sql
-- team_cap_summary (System 3)
ALTER TABLE team_cap_summary ADD COLUMN carryover_from_previous INTEGER DEFAULT 0;
ALTER TABLE team_cap_summary ADD COLUMN is_top_51_active BOOLEAN DEFAULT TRUE;

-- players (System 5, 6)
ALTER TABLE players ADD COLUMN status TEXT DEFAULT 'active';
ALTER TABLE players ADD COLUMN retired_date TEXT;
ALTER TABLE players ADD COLUMN birth_year INTEGER;
ALTER TABLE players ADD COLUMN years_pro INTEGER DEFAULT 0;
ALTER TABLE players ADD COLUMN potential INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN speed INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN acceleration INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN strength INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN awareness INTEGER DEFAULT 70;
ALTER TABLE players ADD COLUMN durability INTEGER DEFAULT 70;

-- free_agents (System 7)
ALTER TABLE free_agents ADD COLUMN years_in_fa_pool INTEGER DEFAULT 0;
ALTER TABLE free_agents ADD COLUMN market_value_aav INTEGER;
ALTER TABLE free_agents ADD COLUMN market_value_years INTEGER;
```

**Indexes (Performance):**
```sql
-- Contract history
CREATE INDEX idx_contract_history_player ON contract_history(player_id);
CREATE INDEX idx_contract_history_dynasty ON contract_history(dynasty_id);

-- Retired players
CREATE INDEX idx_retired_players_dynasty ON retired_players(dynasty_id);
CREATE INDEX idx_retired_players_team ON retired_players(team_id);

-- Player attribute history
CREATE INDEX idx_attribute_history_player ON player_attribute_history(player_id, season);
```

**Migration Strategy:**
1. Create new tables first
2. Add columns to existing tables (ALTER TABLE)
3. Backfill data for existing dynasties (if needed)
4. Create indexes last
5. Validate schema version in database

---

## Integration Points

### Orchestration Flow

```
SeasonCycleController.advance_to_next_season()
    ↓
PhaseTransitionManager.transition_to_preseason()
    ↓
OffseasonToPreseasonHandler.execute()
    ↓
    ├─→ 1. SeasonYearSynchronizer.increment_year()
    ├─→ 2. DraftClassGenerator.generate_class(new_year + 1)
    ├─→ 3. CapYearRolloverService.rollover_all_teams()
    ├─→ 4. ContractYearManager.increment_all_contracts()
    ├─→ 5. PlayerLifecycleManager.process_retirements()
    ├─→ 6. PlayerLifecycleManager.age_all_players()
    ├─→ 7. FreeAgencyManager.update_free_agent_pool()
    ├─→ 8. CapYearRolloverService.generate_rookie_contracts()
    ├─→ 9. _validate_games_exist(new_year)  [EXISTING]
    └─→ 10. _reset_standings(new_year)  [EXISTING]
```

### Dependency Graph

```
Season Year Increment (System 1)
    ↓ [new_year provided to all systems below]
    ├─→ Draft Class Generation (System 2)
    ├─→ Cap Rollover (System 3)
    │       ↓
    │   Contract Year Increments (System 4)
    │       ↓
    │   Player Retirements (System 5)
    │       ↓ [roster changes]
    │   Player Aging (System 6)
    │       ↓
    │   FA Pool Updates (System 7)
    │       ↓
    │   Rookie Contracts (System 8)
    │       ↓
    │   Schedule Validation (EXISTING)
    └─→ Standings Reset (EXISTING)
```

**Critical Path:**
1. Season year MUST increment first (all systems depend on new year)
2. Cap rollover BEFORE contract increments (need new cap limit)
3. Contract increments BEFORE retirements (expiring contracts → FA pool)
4. Retirements BEFORE aging (don't age retired players)
5. Aging BEFORE FA pool updates (attribute decay affects FA value)
6. Rookie contracts LAST (depend on draft completion)

---

## Success Metrics

### Functional Validation

**2-Season Test:**
```python
def test_two_consecutive_seasons():
    # Season 1: 2024
    controller.simulate_full_season()  # Regular → Playoffs → Offseason
    assert controller.season_year == 2024

    # Transition
    controller.advance_to_next_season()
    assert controller.season_year == 2025

    # Season 2: 2025
    controller.simulate_full_season()
    assert controller.season_year == 2025

    # Validate:
    # - Standings reset correctly
    # - Draft class for 2026 exists
    # - Contracts incremented
    # - Some players retired
    # - Cap space carried over
```

**10-Season Test:**
```python
@pytest.mark.slow
def test_ten_season_simulation():
    for year in range(2024, 2034):
        controller.simulate_full_season()
        assert controller.season_year == year

        controller.advance_to_next_season()

        # Validate each transition
        validate_year_increment(year, year + 1)
        validate_statistics_preserved(year)
        validate_cap_compliance_all_teams(year + 1)
```

### Performance Benchmarks

**Target: <20 seconds total transition time**

Breakdown:
- System 1 (Year increment): 0.1s
- System 2 (Draft class): 5.0s
- System 3 (Cap rollover): 2.0s
- System 4 (Contracts): 5.0s
- System 5 (Retirements): 3.0s
- System 6 (Aging): 2.0s
- System 7 (FA pool): 1.0s
- System 8 (Rookie contracts): 3.0s
- **Total: 21.1s** ✅

### Data Integrity Checks

**Post-Transition Validation:**
```python
def validate_transition_success(old_year: int, new_year: int):
    # Season year
    assert controller.season_year == new_year
    assert database.get_latest_season() == new_year

    # Draft class
    draft_class = database.get_draft_class(new_year + 1)
    assert len(draft_class) == 224

    # Cap compliance
    for team_id in range(1, 33):
        cap_status = cap_calculator.get_team_cap_status(team_id, new_year)
        assert cap_status['cap_space'] >= 0  # All teams under cap

    # Contracts
    active_contracts = database.get_active_contracts(new_year)
    for contract in active_contracts:
        assert contract['current_year'] <= contract['total_years']

    # Standings
    standings = database.get_standings(new_year, 'preseason')
    assert len(standings['teams']) == 32
    assert all(team['wins'] == 0 for team in standings['teams'])

    # Statistics
    stats = database.get_player_stats(old_year)
    assert len(stats) > 0  # Old season stats preserved
    new_stats = database.get_player_stats(new_year)
    assert len(new_stats) == 0  # New season stats empty
```

---

**End of Requirements Document**

*This requirements document provides complete specifications for Milestone 1 implementation.*
*For implementation planning, see next document: 03_implementation_plan.md (to be created)*
