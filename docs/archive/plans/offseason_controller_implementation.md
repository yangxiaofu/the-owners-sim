# OffseasonController Implementation Plan

**Version:** 1.0.0
**Created:** 2025-10-18
**Status:** Technical Specification
**Parent Plan:** `offseason_terminal_implementation_plan.md`

---

## Overview

This document provides the detailed technical specification for implementing the **OffseasonController** class, the central orchestrator for the NFL offseason simulation phase.

### Purpose

The OffseasonController manages the complete offseason lifecycle from Super Bowl through training camp, coordinating franchise tags, free agency, the draft, and roster finalization.

### Scope

**In Scope:**
- Offseason phase orchestration and state management
- Calendar advancement through offseason deadlines
- Integration with event system (tags, FA, draft, cuts)
- Deadline tracking and notifications
- Phase transition logic

**Out of Scope (Delegated to Other Components):**
- UI implementation (terminal or desktop)
- Detailed salary cap calculations (CapCalculator)
- Player generation logic (PlayerGenerator)
- Event execution details (individual event classes)

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────┐
│              FullSeasonController                           │
│  (Season → Playoffs → Offseason → Next Season)             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              OffseasonController                            │
│  - Calendar management (Feb → Aug)                         │
│  - Phase tracking (Tags → FA → Draft → Cuts)              │
│  - Deadline detection and triggering                       │
│  - User action validation and execution                    │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬────────────┐
        ↓            ↓            ↓            ↓
   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
   │  Event  │  │Calendar │  │Salary   │  │Database │
   │ System  │  │Component│  │  Cap    │  │  APIs   │
   └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

### Design Principles

1. **Orchestration, not implementation** - Delegates work to specialized managers
2. **Phase-driven state machine** - Clear transitions between offseason phases
3. **Event-based actions** - All user/AI actions trigger events
4. **Calendar continuity** - Seamless date progression from playoffs
5. **Dynasty isolation** - All operations scoped to specific dynasty

---

## Class Design

### OffseasonController

**Location:** `src/offseason/offseason_controller.py`

```python
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum

from calendar.calendar_component import CalendarComponent
from offseason.offseason_phases import OffseasonPhase
from offseason.draft_manager import DraftManager
from offseason.roster_manager import RosterManager
from offseason.free_agency_manager import FreeAgencyManager
from salary_cap.tag_manager import TagManager
from salary_cap.cap_calculator import CapCalculator
from database.api import DatabaseAPI
from database.dynasty_state_api import DynastyStateAPI


class OffseasonController:
    """
    Orchestrates the NFL offseason simulation phase.

    Manages the complete offseason lifecycle:
    - Franchise tag period (March 1-5)
    - Free agency (March 11 onwards)
    - Draft (late April)
    - Roster finalization (August)

    Responsibilities:
    - Track current offseason phase and upcoming deadlines
    - Advance calendar through offseason dates
    - Validate and execute user/AI offseason actions
    - Trigger automatic events at deadlines
    - Provide data for UI display (terminal or desktop)
    """

    def __init__(
        self,
        database_path: str,
        dynasty_id: str,
        season_year: int,
        user_team_id: int,
        calendar: Optional[CalendarComponent] = None,
        super_bowl_date: Optional[datetime] = None,
        enable_persistence: bool = True,
        verbose_logging: bool = True
    ):
        """
        Initialize offseason controller.

        Args:
            database_path: Path to SQLite database
            dynasty_id: Unique dynasty identifier
            season_year: NFL season year (e.g., 2024)
            user_team_id: Team ID of user-controlled team (1-32)
            calendar: Shared calendar instance (or create new)
            super_bowl_date: Date of Super Bowl (for calculating offseason start)
            enable_persistence: Whether to save actions to database
            verbose_logging: Whether to print progress messages
        """
        self.database_path = database_path
        self.dynasty_id = dynasty_id
        self.season_year = season_year
        self.user_team_id = user_team_id
        self.enable_persistence = enable_persistence
        self.verbose_logging = verbose_logging

        # Calendar management
        if calendar:
            self.calendar = calendar
        else:
            # If no calendar provided, start at Super Bowl + 1 week
            start_date = super_bowl_date or datetime(season_year + 1, 2, 9)
            self.calendar = CalendarComponent(start_date, season_year)

        # Database APIs
        self.db_api = DatabaseAPI(database_path)
        self.dynasty_api = DynastyStateAPI(database_path)

        # Specialized managers
        self.tag_manager = TagManager(database_path, dynasty_id)
        self.cap_calculator = CapCalculator(database_path, dynasty_id)
        self.draft_manager = DraftManager(database_path, dynasty_id, season_year)
        self.roster_manager = RosterManager(database_path, dynasty_id)
        self.fa_manager = FreeAgencyManager(database_path, dynasty_id, season_year)

        # State tracking
        self.current_phase = self._detect_current_phase()
        self.deadlines = self._initialize_deadlines()
        self.offseason_complete = False

        # Statistics
        self.actions_taken = []
        self.deadlines_passed = []

    # ========== Public API: Phase Management ==========

    def get_current_phase(self) -> OffseasonPhase:
        """Get current offseason phase."""
        return self.current_phase

    def get_current_date(self) -> datetime:
        """Get current calendar date."""
        return self.calendar.get_current_date()

    def get_upcoming_deadlines(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get upcoming deadlines.

        Args:
            limit: Maximum number of deadlines to return

        Returns:
            List of deadline dictionaries with date, type, days_remaining
        """
        current_date = self.get_current_date()
        upcoming = [
            d for d in self.deadlines
            if d['date'] >= current_date
        ]
        upcoming.sort(key=lambda x: x['date'])

        # Add days remaining
        for deadline in upcoming:
            days_remaining = (deadline['date'] - current_date).days
            deadline['days_remaining'] = days_remaining

        return upcoming[:limit]

    def is_offseason_complete(self) -> bool:
        """Check if offseason is complete (ready for next season)."""
        return self.offseason_complete

    # ========== Public API: Calendar Advancement ==========

    def advance_day(self) -> Dict[str, Any]:
        """
        Advance calendar by 1 day.

        Returns:
            Dictionary with:
            - date: Current date
            - phase: Current phase
            - deadlines_triggered: List of deadlines that occurred
            - phase_changed: Whether phase changed
        """
        # Advance calendar
        self.calendar.advance(1)
        current_date = self.get_current_date()

        # Check for deadline triggers
        deadlines_triggered = self._check_deadlines(current_date)

        # Check for phase transition
        old_phase = self.current_phase
        self.current_phase = self._detect_current_phase()
        phase_changed = (old_phase != self.current_phase)

        # Check if offseason complete
        if self.current_phase == OffseasonPhase.COMPLETE:
            self.offseason_complete = True

        if self.verbose_logging and deadlines_triggered:
            for deadline in deadlines_triggered:
                print(f"⏰ Deadline: {deadline['type']}")

        return {
            'date': current_date,
            'phase': self.current_phase.value,
            'deadlines_triggered': deadlines_triggered,
            'phase_changed': phase_changed,
            'offseason_complete': self.offseason_complete
        }

    def advance_to_deadline(self, deadline_type: str) -> Dict[str, Any]:
        """
        Fast-forward to next occurrence of specific deadline.

        Args:
            deadline_type: Type of deadline to advance to

        Returns:
            Same as advance_day, with days_advanced added
        """
        current_date = self.get_current_date()

        # Find next deadline of this type
        target_deadline = None
        for deadline in self.deadlines:
            if deadline['type'] == deadline_type and deadline['date'] > current_date:
                target_deadline = deadline
                break

        if not target_deadline:
            raise ValueError(f"No upcoming deadline of type '{deadline_type}'")

        # Calculate days to advance
        days_to_advance = (target_deadline['date'] - current_date).days

        # Advance day by day (to trigger intermediate deadlines)
        results = []
        for _ in range(days_to_advance):
            result = self.advance_day()
            results.append(result)

        # Return summary of final state
        all_deadlines_triggered = []
        for r in results:
            all_deadlines_triggered.extend(r['deadlines_triggered'])

        return {
            'date': self.get_current_date(),
            'phase': self.current_phase.value,
            'days_advanced': days_to_advance,
            'deadlines_triggered': all_deadlines_triggered,
            'offseason_complete': self.offseason_complete
        }

    def advance_to_training_camp(self) -> Dict[str, Any]:
        """
        Fast-forward through entire offseason to training camp.

        Returns:
            Summary of all actions and deadlines during offseason
        """
        all_deadlines = []
        days_advanced = 0

        while not self.is_offseason_complete():
            result = self.advance_day()
            days_advanced += 1
            if result['deadlines_triggered']:
                all_deadlines.extend(result['deadlines_triggered'])

        return {
            'days_advanced': days_advanced,
            'deadlines_triggered': all_deadlines,
            'final_date': self.get_current_date(),
            'offseason_complete': True
        }

    # ========== Public API: Franchise Tags ==========

    def get_franchise_tag_candidates(self) -> List[Dict[str, Any]]:
        """
        Get list of players eligible for franchise tag.

        Returns:
            List of player dictionaries with tag cost and recommendations
        """
        return self.tag_manager.get_tag_candidates(
            team_id=self.user_team_id,
            season=self.season_year
        )

    def apply_franchise_tag(
        self,
        player_id: str,
        tag_type: str = "FRANCHISE"
    ) -> Dict[str, Any]:
        """
        Apply franchise or transition tag to player.

        Args:
            player_id: Player to tag
            tag_type: "FRANCHISE" or "TRANSITION"

        Returns:
            Result with success status and details
        """
        # Validate deadline
        if self.current_phase != OffseasonPhase.FRANCHISE_TAG_PERIOD:
            return {
                'success': False,
                'error': 'Franchise tag period has ended'
            }

        # Validate cap space
        tag_cost = self.tag_manager.calculate_tag_cost(player_id, tag_type)
        cap_space = self.cap_calculator.get_cap_space(self.user_team_id)

        if tag_cost > cap_space:
            return {
                'success': False,
                'error': f'Insufficient cap space. Need ${tag_cost:,}, have ${cap_space:,}'
            }

        # Execute via tag manager
        result = self.tag_manager.apply_tag(
            team_id=self.user_team_id,
            player_id=player_id,
            tag_type=tag_type,
            season=self.season_year
        )

        # Log action
        if result['success']:
            self.actions_taken.append({
                'type': 'FRANCHISE_TAG',
                'player_id': player_id,
                'tag_type': tag_type,
                'cost': tag_cost,
                'date': self.get_current_date()
            })

        return result

    # ========== Public API: Free Agency ==========

    def get_free_agent_pool(
        self,
        position: Optional[str] = None,
        min_overall: int = 0,
        max_age: int = 99,
        max_market_value: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get available free agents with optional filters.

        Args:
            position: Filter by position (e.g., 'QB', 'WR')
            min_overall: Minimum overall rating
            max_age: Maximum player age
            max_market_value: Maximum estimated annual value

        Returns:
            List of free agent dictionaries
        """
        return self.fa_manager.get_available_free_agents(
            position=position,
            min_overall=min_overall,
            max_age=max_age,
            max_market_value=max_market_value
        )

    def sign_free_agent(
        self,
        player_id: str,
        years: int,
        annual_salary: int,
        signing_bonus: int = 0
    ) -> Dict[str, Any]:
        """
        Sign unrestricted free agent.

        Args:
            player_id: Player to sign
            years: Contract length (1-5 years)
            annual_salary: Annual salary
            signing_bonus: Upfront signing bonus

        Returns:
            Result with success status
        """
        # Validate phase
        if self.current_phase not in [
            OffseasonPhase.FREE_AGENCY_LEGAL_TAMPERING,
            OffseasonPhase.FREE_AGENCY_OPEN
        ]:
            return {
                'success': False,
                'error': 'Free agency has not started yet'
            }

        # Validate cap space
        cap_impact = self.cap_calculator.calculate_contract_cap_hit(
            annual_salary=annual_salary,
            signing_bonus=signing_bonus,
            years=years
        )

        cap_space = self.cap_calculator.get_cap_space(self.user_team_id)

        if cap_impact > cap_space:
            return {
                'success': False,
                'error': f'Insufficient cap space. Need ${cap_impact:,}, have ${cap_space:,}'
            }

        # Execute signing
        result = self.fa_manager.sign_free_agent(
            team_id=self.user_team_id,
            player_id=player_id,
            years=years,
            annual_salary=annual_salary,
            signing_bonus=signing_bonus
        )

        # Log action
        if result['success']:
            self.actions_taken.append({
                'type': 'FREE_AGENT_SIGNING',
                'player_id': player_id,
                'years': years,
                'annual_salary': annual_salary,
                'signing_bonus': signing_bonus,
                'date': self.get_current_date()
            })

        return result

    # ========== Public API: Draft ==========

    def get_draft_board(
        self,
        round_num: Optional[int] = None,
        position: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get draft prospects with optional filters.

        Args:
            round_num: Filter by projected round (1-7)
            position: Filter by position
            limit: Maximum prospects to return

        Returns:
            List of prospect dictionaries with grades and fit scores
        """
        return self.draft_manager.get_draft_board(
            round_num=round_num,
            position=position,
            limit=limit
        )

    def make_draft_selection(
        self,
        round_num: int,
        pick_num: int,
        player_id: str
    ) -> Dict[str, Any]:
        """
        Select player in draft.

        Args:
            round_num: Draft round (1-7)
            pick_num: Overall pick number
            player_id: Prospect to select

        Returns:
            Result with success status
        """
        # Validate phase
        if self.current_phase != OffseasonPhase.DRAFT:
            return {
                'success': False,
                'error': 'Draft has not started yet'
            }

        # Execute draft pick
        result = self.draft_manager.make_selection(
            team_id=self.user_team_id,
            round_num=round_num,
            pick_num=pick_num,
            player_id=player_id
        )

        # Log action
        if result['success']:
            self.actions_taken.append({
                'type': 'DRAFT_SELECTION',
                'round': round_num,
                'pick': pick_num,
                'player_id': player_id,
                'date': self.get_current_date()
            })

        return result

    def simulate_draft(self) -> Dict[str, Any]:
        """
        Auto-simulate entire draft (AI picks for all teams including user).

        Returns:
            Summary of all draft picks
        """
        return self.draft_manager.simulate_full_draft()

    # ========== Public API: Roster Management ==========

    def get_roster(self, include_practice_squad: bool = False) -> List[Dict[str, Any]]:
        """
        Get current team roster.

        Args:
            include_practice_squad: Whether to include practice squad

        Returns:
            List of player dictionaries
        """
        return self.roster_manager.get_team_roster(
            team_id=self.user_team_id,
            include_practice_squad=include_practice_squad
        )

    def cut_player(
        self,
        player_id: str,
        june_1_designation: bool = False
    ) -> Dict[str, Any]:
        """
        Release player from roster.

        Args:
            player_id: Player to cut
            june_1_designation: Use June 1 designation for cap savings

        Returns:
            Result with dead money impact
        """
        # Calculate dead money
        dead_money = self.cap_calculator.calculate_dead_money(
            player_id=player_id,
            june_1_designation=june_1_designation
        )

        # Execute cut
        result = self.roster_manager.release_player(
            team_id=self.user_team_id,
            player_id=player_id,
            june_1_designation=june_1_designation
        )

        # Log action
        if result['success']:
            self.actions_taken.append({
                'type': 'PLAYER_CUT',
                'player_id': player_id,
                'dead_money': dead_money,
                'june_1_designation': june_1_designation,
                'date': self.get_current_date()
            })

        return result

    def finalize_roster(self) -> Dict[str, Any]:
        """
        Validate and finalize 53-man roster for season start.

        Returns:
            Result with validation details
        """
        return self.roster_manager.finalize_53_man_roster(
            team_id=self.user_team_id
        )

    # ========== Public API: Cap Status ==========

    def get_cap_status(self) -> Dict[str, Any]:
        """
        Get salary cap status for user team.

        Returns:
            Dictionary with cap space, committed salary, status
        """
        return self.cap_calculator.get_team_cap_summary(
            team_id=self.user_team_id
        )

    # ========== Private Methods ==========

    def _detect_current_phase(self) -> OffseasonPhase:
        """
        Determine current offseason phase based on calendar date.

        Returns:
            Current OffseasonPhase
        """
        current_date = self.get_current_date()

        # Define phase boundaries (2025 calendar)
        # Adjust year based on season_year
        year = self.season_year + 1  # Offseason is year after season

        if current_date < datetime(year, 3, 1):
            return OffseasonPhase.POST_SUPER_BOWL
        elif current_date < datetime(year, 3, 6):
            return OffseasonPhase.FRANCHISE_TAG_PERIOD
        elif current_date < datetime(year, 3, 11):
            return OffseasonPhase.PRE_FREE_AGENCY
        elif current_date < datetime(year, 3, 13):
            return OffseasonPhase.FREE_AGENCY_LEGAL_TAMPERING
        elif current_date < datetime(year, 4, 24):
            return OffseasonPhase.FREE_AGENCY_OPEN
        elif current_date < datetime(year, 4, 28):
            return OffseasonPhase.DRAFT
        elif current_date < datetime(year, 8, 26):
            return OffseasonPhase.POST_DRAFT
        elif current_date < datetime(year, 8, 30):
            return OffseasonPhase.ROSTER_CUTS
        else:
            return OffseasonPhase.COMPLETE

    def _initialize_deadlines(self) -> List[Dict[str, Any]]:
        """
        Initialize offseason deadline tracking.

        Returns:
            List of deadline dictionaries
        """
        year = self.season_year + 1

        deadlines = [
            {
                'type': 'FRANCHISE_TAG_DEADLINE',
                'date': datetime(year, 3, 5, 16, 0),  # 4 PM ET
                'description': 'Franchise tag deadline',
                'action': 'check_franchise_tags_applied'
            },
            {
                'type': 'LEGAL_TAMPERING_START',
                'date': datetime(year, 3, 11, 12, 0),  # Noon ET
                'description': 'Legal tampering period begins',
                'action': 'enable_free_agency_negotiations'
            },
            {
                'type': 'FREE_AGENCY_START',
                'date': datetime(year, 3, 13, 16, 0),  # 4 PM ET
                'description': 'Free agency opens',
                'action': 'enable_free_agency_signings'
            },
            {
                'type': 'DRAFT_START',
                'date': datetime(year, 4, 24, 20, 0),  # 8 PM ET (Thursday)
                'description': 'NFL Draft begins',
                'action': 'initialize_draft'
            },
            {
                'type': 'DRAFT_END',
                'date': datetime(year, 4, 27, 18, 0),  # 6 PM ET (Saturday)
                'description': 'NFL Draft concludes',
                'action': 'finalize_draft_class'
            },
            {
                'type': 'ROSTER_CUT_DEADLINE',
                'date': datetime(year, 8, 26, 16, 0),  # 4 PM ET
                'description': 'Final roster cuts to 53',
                'action': 'validate_53_man_rosters'
            },
            {
                'type': 'SEASON_START',
                'date': datetime(year, 9, 5, 20, 0),  # Thursday Night Football
                'description': 'Regular season begins',
                'action': 'transition_to_season'
            }
        ]

        return deadlines

    def _check_deadlines(self, current_date: datetime) -> List[Dict[str, Any]]:
        """
        Check if any deadlines occurred on current date.

        Args:
            current_date: Date to check

        Returns:
            List of triggered deadlines
        """
        triggered = []

        for deadline in self.deadlines:
            # Check if deadline is today (ignore time for daily advancement)
            if deadline['date'].date() == current_date.date():
                # Only trigger once
                if deadline not in self.deadlines_passed:
                    triggered.append(deadline)
                    self.deadlines_passed.append(deadline)

                    # Execute deadline action
                    if self.enable_persistence:
                        self._execute_deadline_action(deadline)

        return triggered

    def _execute_deadline_action(self, deadline: Dict[str, Any]):
        """
        Execute automatic action for deadline.

        Args:
            deadline: Deadline dictionary with action to execute
        """
        action = deadline.get('action')

        if action == 'check_franchise_tags_applied':
            # Log teams that applied tags
            pass

        elif action == 'enable_free_agency_negotiations':
            # Update phase state
            pass

        elif action == 'enable_free_agency_signings':
            # Update phase state
            pass

        elif action == 'initialize_draft':
            # Generate draft class if not already done
            self.draft_manager.generate_draft_class()

        elif action == 'finalize_draft_class':
            # Mark draft as complete
            pass

        elif action == 'validate_53_man_rosters':
            # Check all teams have valid 53-man rosters
            pass

        elif action == 'transition_to_season':
            # Mark offseason complete
            self.offseason_complete = True

    # ========== Public API: State Summary ==========

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive current state summary.

        Returns:
            Dictionary with all key state information
        """
        return {
            'dynasty_id': self.dynasty_id,
            'season_year': self.season_year,
            'current_date': self.get_current_date(),
            'current_phase': self.current_phase.value,
            'offseason_complete': self.offseason_complete,
            'upcoming_deadlines': self.get_upcoming_deadlines(3),
            'actions_taken': len(self.actions_taken),
            'cap_space': self.cap_calculator.get_cap_space(self.user_team_id),
            'roster_count': len(self.get_roster())
        }
```

---

## Supporting Components

### OffseasonPhase Enum

**Location:** `src/offseason/offseason_phases.py`

```python
from enum import Enum

class OffseasonPhase(Enum):
    """NFL offseason phases based on calendar dates."""

    POST_SUPER_BOWL = "post_super_bowl"
    FRANCHISE_TAG_PERIOD = "franchise_tag_period"
    PRE_FREE_AGENCY = "pre_free_agency"
    FREE_AGENCY_LEGAL_TAMPERING = "free_agency_legal_tampering"
    FREE_AGENCY_OPEN = "free_agency_open"
    DRAFT = "draft"
    POST_DRAFT = "post_draft"
    ROSTER_CUTS = "roster_cuts"
    COMPLETE = "complete"
```

### Specialized Managers

**DraftManager** (`src/offseason/draft_manager.py`):
- Generate draft class with PlayerGenerator
- Maintain draft board with prospect rankings
- Execute draft selections
- Calculate draft order from standings

**RosterManager** (`src/offseason/roster_manager.py`):
- Track roster size (53 → 90 → 53)
- Execute player cuts with cap implications
- Validate roster composition (position limits)
- Finalize 53-man roster

**FreeAgencyManager** (`src/offseason/free_agency_manager.py`):
- Generate UFA pool from expired contracts
- Filter available free agents
- Estimate market values
- Execute signings via events

---

## Implementation Steps

### Step 1: Create Module Structure (30 min)

```bash
# Create offseason module
mkdir -p src/offseason
touch src/offseason/__init__.py
touch src/offseason/offseason_controller.py
touch src/offseason/offseason_phases.py
touch src/offseason/draft_manager.py
touch src/offseason/roster_manager.py
touch src/offseason/free_agency_manager.py
```

### Step 2: Implement OffseasonPhase Enum (15 min)

**File:** `src/offseason/offseason_phases.py`

**Test:**
```python
def test_offseason_phases():
    assert OffseasonPhase.FRANCHISE_TAG_PERIOD.value == "franchise_tag_period"
    assert len(OffseasonPhase) == 9
```

### Step 3: Implement OffseasonController Skeleton (1 hour)

**Tasks:**
1. Create `__init__` method with all dependencies
2. Implement `_detect_current_phase()` with date logic
3. Implement `_initialize_deadlines()` with all NFL dates
4. Add basic getters (get_current_phase, get_current_date)

**Test:**
```python
def test_offseason_controller_initialization():
    controller = OffseasonController(
        database_path=":memory:",
        dynasty_id="test",
        season_year=2024,
        user_team_id=22,
        super_bowl_date=datetime(2025, 2, 9)
    )

    assert controller.season_year == 2024
    assert controller.current_phase == OffseasonPhase.POST_SUPER_BOWL
    assert len(controller.deadlines) == 7
```

### Step 4: Implement Calendar Advancement (1 hour)

**Tasks:**
1. Implement `advance_day()` with deadline checking
2. Implement `advance_to_deadline()` with fast-forward
3. Implement `_check_deadlines()` trigger detection
4. Test phase transitions

**Test:**
```python
def test_advance_day():
    controller = OffseasonController(...)

    result = controller.advance_day()
    assert result['date'] > controller.get_current_date()

def test_advance_to_deadline():
    controller = OffseasonController(...)

    result = controller.advance_to_deadline("FRANCHISE_TAG_DEADLINE")
    assert result['days_advanced'] > 0
    assert controller.current_phase == OffseasonPhase.PRE_FREE_AGENCY
```

### Step 5: Implement Franchise Tag Methods (2 hours)

**Tasks:**
1. Implement `get_franchise_tag_candidates()`
2. Implement `apply_franchise_tag()` with validation
3. Integrate with TagManager
4. Add cap space checking
5. Test tag application flow

**Test:**
```python
def test_apply_franchise_tag():
    controller = OffseasonController(...)

    # Advance to tag period
    controller.advance_to_deadline("FRANCHISE_TAG_DEADLINE")

    # Apply tag
    result = controller.apply_franchise_tag(
        player_id="DE_22_1",
        tag_type="FRANCHISE"
    )

    assert result['success'] == True
    assert len(controller.actions_taken) == 1
```

### Step 6: Implement Free Agency Methods (2 hours)

**Tasks:**
1. Implement `get_free_agent_pool()` with filters
2. Implement `sign_free_agent()` with validation
3. Integrate with FreeAgencyManager
4. Test FA signing flow

**Test:**
```python
def test_sign_free_agent():
    controller = OffseasonController(...)

    # Advance to FA
    controller.advance_to_deadline("FREE_AGENCY_START")

    # Get FA pool
    free_agents = controller.get_free_agent_pool(position="OL")
    assert len(free_agents) > 0

    # Sign player
    result = controller.sign_free_agent(
        player_id=free_agents[0]['player_id'],
        years=3,
        annual_salary=12000000
    )

    assert result['success'] == True
```

### Step 7: Implement Draft Methods (3 hours)

**Tasks:**
1. Implement `get_draft_board()`
2. Implement `make_draft_selection()`
3. Implement `simulate_draft()`
4. Integrate with DraftManager
5. Test draft flow

### Step 8: Implement Roster Management (2 hours)

**Tasks:**
1. Implement `get_roster()`
2. Implement `cut_player()` with dead money
3. Implement `finalize_roster()`
4. Integrate with RosterManager
5. Test roster cut flow

### Step 9: Integration Testing (2 hours)

**Tasks:**
1. Test complete offseason cycle
2. Test phase transitions
3. Test deadline triggers
4. Test dynasty persistence

---

## Testing Strategy

### Unit Tests

**Location:** `tests/offseason/test_offseason_controller.py`

```python
import pytest
from datetime import datetime
from src.offseason.offseason_controller import OffseasonController
from src.offseason.offseason_phases import OffseasonPhase

class TestOffseasonController:

    @pytest.fixture
    def controller(self):
        return OffseasonController(
            database_path=":memory:",
            dynasty_id="test_dynasty",
            season_year=2024,
            user_team_id=22,
            super_bowl_date=datetime(2025, 2, 9)
        )

    def test_initialization(self, controller):
        """Test controller initializes correctly."""
        assert controller.dynasty_id == "test_dynasty"
        assert controller.season_year == 2024
        assert controller.current_phase == OffseasonPhase.POST_SUPER_BOWL

    def test_phase_detection_march_1(self):
        """Test phase detection on March 1."""
        controller = OffseasonController(
            database_path=":memory:",
            dynasty_id="test",
            season_year=2024,
            user_team_id=22,
            super_bowl_date=datetime(2025, 3, 1)
        )

        assert controller.current_phase == OffseasonPhase.FRANCHISE_TAG_PERIOD

    def test_advance_day(self, controller):
        """Test advancing calendar by one day."""
        initial_date = controller.get_current_date()
        result = controller.advance_day()

        assert result['date'] > initial_date
        assert 'phase' in result
        assert 'deadlines_triggered' in result

    def test_deadline_detection(self, controller):
        """Test deadline detection when advancing to specific date."""
        # Advance to franchise tag deadline
        result = controller.advance_to_deadline("FRANCHISE_TAG_DEADLINE")

        assert result['days_advanced'] > 0
        assert any(d['type'] == 'FRANCHISE_TAG_DEADLINE'
                  for d in result['deadlines_triggered'])

    def test_franchise_tag_validation(self, controller):
        """Test franchise tag fails outside of tag period."""
        # Should fail - not in tag period
        result = controller.apply_franchise_tag("DE_22_1")

        assert result['success'] == False
        assert 'period has ended' in result['error'].lower()

    def test_complete_offseason_cycle(self, controller):
        """Test full offseason progression."""
        # Advance through entire offseason
        result = controller.advance_to_training_camp()

        assert controller.is_offseason_complete() == True
        assert controller.current_phase == OffseasonPhase.COMPLETE
        assert result['days_advanced'] > 150  # ~5-6 months
```

### Integration Tests

**Location:** `tests/integration/test_full_offseason.py`

```python
def test_full_offseason_with_actions():
    """Test complete offseason with user actions."""

    controller = OffseasonController(...)

    # 1. Advance to franchise tag period
    controller.advance_to_deadline("FRANCHISE_TAG_DEADLINE")

    # 2. Apply franchise tag
    tag_result = controller.apply_franchise_tag("DE_22_1")
    assert tag_result['success']

    # 3. Advance to free agency
    controller.advance_to_deadline("FREE_AGENCY_START")

    # 4. Sign free agent
    fa_result = controller.sign_free_agent("OL_FA_1", years=3, annual_salary=12000000)
    assert fa_result['success']

    # 5. Advance to draft
    controller.advance_to_deadline("DRAFT_START")

    # 6. Make draft selection
    draft_result = controller.make_draft_selection(round_num=1, pick_num=15, player_id="OT_DRAFT_1")
    assert draft_result['success']

    # 7. Advance to roster cuts
    controller.advance_to_deadline("ROSTER_CUT_DEADLINE")

    # 8. Finalize roster
    final_result = controller.finalize_roster()
    assert final_result['success']

    # 9. Verify offseason complete
    assert controller.is_offseason_complete()
    assert len(controller.actions_taken) == 4  # tag, FA, draft, finalize
```

---

## Error Handling

### Common Error Cases

1. **Action Outside Valid Phase**
   ```python
   if self.current_phase != OffseasonPhase.FRANCHISE_TAG_PERIOD:
       return {'success': False, 'error': 'Franchise tag period has ended'}
   ```

2. **Insufficient Cap Space**
   ```python
   if cost > cap_space:
       return {'success': False, 'error': f'Need ${cost:,}, have ${cap_space:,}'}
   ```

3. **Invalid Player ID**
   ```python
   if not player_exists:
       return {'success': False, 'error': f'Player {player_id} not found'}
   ```

4. **Roster Limit Exceeded**
   ```python
   if roster_count >= 53:
       return {'success': False, 'error': 'Roster full (53/53)'}
   ```

---

## Performance Considerations

### Optimization Strategies

1. **Cache Free Agent Pool**: Generate once per phase, filter on demand
2. **Lazy Draft Class Generation**: Only generate when user enters draft
3. **Batch Database Queries**: Minimize round-trips when getting roster
4. **Index Deadline List**: Sort by date once during initialization

### Expected Performance

- **Calendar advancement**: < 10ms per day
- **Get free agent pool**: < 100ms (500+ players)
- **Apply franchise tag**: < 50ms (single event)
- **Complete offseason**: < 30 seconds (with persistence)

---

## Future Enhancements

### Post-MVP Features

1. **AI Team Decision-Making**
   - Auto-tag players for AI teams
   - AI free agency signings based on team needs
   - AI draft selections with BPA/need logic

2. **Advanced Draft Features**
   - Trade draft picks between teams
   - Mock draft simulator
   - Prospect scouting reports

3. **Contract Extensions**
   - Negotiate extensions before free agency
   - Avoid franchise tag by locking in long-term

4. **Transaction History**
   - View all offseason moves by any team
   - League-wide transaction feed
   - Filter by team, position, date

---

## Success Criteria

### Definition of Done

✅ OffseasonController class fully implemented
✅ All public API methods working
✅ Phase detection accurate
✅ Deadline tracking functional
✅ Integration with TagManager, CapCalculator, DraftManager
✅ Unit tests passing (>90% coverage)
✅ Integration tests passing
✅ Can execute complete offseason cycle
✅ Dynasty persistence working

---

## Appendix: Method Reference

### Public Methods Summary

| Method | Purpose | Returns |
|--------|---------|---------|
| `get_current_phase()` | Get current offseason phase | OffseasonPhase |
| `get_current_date()` | Get calendar date | datetime |
| `get_upcoming_deadlines()` | Get next deadlines | List[Dict] |
| `advance_day()` | Advance 1 day | Dict (result) |
| `advance_to_deadline()` | Fast-forward to deadline | Dict (result) |
| `get_franchise_tag_candidates()` | Get taggable players | List[Dict] |
| `apply_franchise_tag()` | Tag player | Dict (result) |
| `get_free_agent_pool()` | Get available FAs | List[Dict] |
| `sign_free_agent()` | Sign UFA | Dict (result) |
| `get_draft_board()` | Get prospects | List[Dict] |
| `make_draft_selection()` | Draft player | Dict (result) |
| `get_roster()` | Get team roster | List[Dict] |
| `cut_player()` | Release player | Dict (result) |
| `finalize_roster()` | Lock 53-man roster | Dict (result) |
| `get_cap_status()` | Get cap summary | Dict |
| `get_state_summary()` | Get all state | Dict |

---

**Document Version**: 1.0.0
**Created**: 2025-10-18
**Status**: Technical Specification - Ready for Implementation
**Next Steps**: Begin Step 1 (Module Structure Creation)
**Estimated Implementation Time**: 16-20 hours
