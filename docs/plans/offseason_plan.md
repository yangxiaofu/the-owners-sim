# NFL Offseason Implementation Plan

**Version:** 2.0.0
**Last Updated:** 2025-10-04
**Status:** Phase 1 Complete (Event Infrastructure Created)

## Overview

This document outlines the implementation strategy for the NFL offseason simulation system, leveraging the existing calendar and events infrastructure to handle the complex 7-month period between the Super Bowl and regular season start.

**Reference**: See `docs/specifications/offseason_spec.md` for complete NFL offseason timeline and rules.
**Architecture**: See `docs/architecture/offseason_event_system.md` for detailed event system documentation.

---

## Architecture Approach: Event-Based Deadline System

### Core Principle: **DeadlineEvent Pattern**

The offseason is implemented as a series of **independent deadline and action events** scheduled in the events table, triggered automatically by the existing `SimulationExecutor` date-based event retrieval system.

**Key Design Decisions**:
- ✅ **Events are independent**: No event depends on another event's state
- ✅ **Date-driven triggering**: Calendar date advancement triggers events automatically
- ✅ **Leverages existing infrastructure**: Uses `EventDatabaseAPI`, `SimulationExecutor`, `SeasonPhaseTracker`
- ✅ **Flexible scheduling**: Events can be rescheduled if needed (e.g., Super Bowl date changes)
- ✅ **Query-able**: Can retrieve upcoming deadlines for UI display

---

## Event Type Hierarchy

### 1. **DeadlineEvent** (Marker Events)
Non-executable events that mark important dates and trigger decision logic.

**Purpose**:
- Mark NFL deadlines (e.g., franchise tag deadline March 4, 4PM ET)
- Execute compliance checking
- Trigger AI team decision-making
- Generate notifications for user

**Implementation**:
```python
class DeadlineEvent(BaseEvent):
    """
    Deadline marker event that triggers logic without simulating games.

    Examples:
    - Franchise tag deadline (March 4)
    - Salary cap compliance deadline (March 12)
    - Roster cuts deadline (August 26)
    """

    def __init__(
        self,
        deadline_type: str,           # "FRANCHISE_TAG", "SALARY_CAP", etc.
        deadline_date: datetime,       # When deadline occurs
        actions_to_trigger: List[str], # What logic to execute
        event_id: Optional[str] = None,
        game_id: str = "offseason_deadline"
    ):
        super().__init__(event_id=event_id, timestamp=deadline_date)
        self.deadline_type = deadline_type
        self.deadline_date = deadline_date
        self.actions = actions_to_trigger
        self._game_id = game_id

    def get_event_type(self) -> str:
        return "DEADLINE"

    def simulate(self) -> EventResult:
        """
        Execute deadline logic:
        1. Check team compliance
        2. Apply penalties if needed
        3. Trigger AI decisions
        4. Log deadline occurrence
        """
        results = []

        for action in self.actions:
            if action == "check_franchise_tags":
                results.append(self._check_franchise_tag_compliance())
            elif action == "check_salary_cap":
                results.append(self._check_salary_cap_compliance())
            elif action == "process_roster_cuts":
                results.append(self._process_roster_cuts())
            # ... more actions

        return EventResult(
            event_id=self.event_id,
            event_type="DEADLINE",
            success=True,
            timestamp=datetime.now(),
            data={
                "deadline_type": self.deadline_type,
                "actions_executed": self.actions,
                "results": results
            }
        )
```

**Deadline Types Needed**:
- `FRANCHISE_TAG_DEADLINE` - March 4, 4PM ET
- `SALARY_CAP_COMPLIANCE` - March 12, 4PM ET
- `RFA_OFFER_SHEET_DEADLINE` - April 22
- `FIFTH_YEAR_OPTION_DEADLINE` - May 1-2
- `FRANCHISE_TAG_EXTENSION_DEADLINE` - Mid-July
- `ROSTER_CUTS_DEADLINE` - August 26, 4PM ET
- `WAIVER_CLAIM_DEADLINE` - August 27, Noon ET

---

### 2. **WindowEvent** (Window Start/End)
Events marking the start and end of time-bounded periods.

**Purpose**:
- Mark beginning/end of windows (e.g., legal tampering, OTAs)
- Enable/disable certain actions during window
- Track which windows are currently active

**Implementation**:
```python
class WindowEvent(BaseEvent):
    """
    Marks the start or end of a time window.

    Examples:
    - Legal tampering window (March 10 - March 12)
    - OTA period (May - June)
    - Training camp window (July - August)
    """

    def __init__(
        self,
        window_type: str,      # "LEGAL_TAMPERING", "OTA", etc.
        window_action: str,    # "START" or "END"
        window_date: datetime,
        event_id: Optional[str] = None
    ):
        super().__init__(event_id=event_id, timestamp=window_date)
        self.window_type = window_type
        self.window_action = window_action  # "START" or "END"
        self._game_id = f"offseason_window_{window_type.lower()}"

    def get_event_type(self) -> str:
        return "WINDOW"

    def simulate(self) -> EventResult:
        """
        Update active window state:
        - START: Enable window, allow related actions
        - END: Disable window, prevent related actions
        """
        if self.window_action == "START":
            # Enable window (e.g., allow free agent signings)
            self._enable_window(self.window_type)
        else:
            # Disable window
            self._disable_window(self.window_type)

        return EventResult(
            event_id=self.event_id,
            event_type="WINDOW",
            success=True,
            timestamp=datetime.now(),
            data={
                "window_type": self.window_type,
                "action": self.window_action
            }
        )
```

**Window Types Needed**:
- `LEGAL_TAMPERING` - March 10 (Noon) → March 12 (4PM)
- `FREE_AGENCY_SIGNING` - March 12 (4PM) → ongoing
- `OTA_PERIOD` - May → June
- `MANDATORY_MINICAMP` - 3 days during OTA period
- `TRAINING_CAMP` - July → August

---

### 3. **ActionEvent** (Executable Actions)
Events that represent actual offseason transactions and actions.

**Purpose**:
- Execute team actions (signings, cuts, tags, draft picks)
- Modify rosters and contracts
- Update salary cap
- Persist changes to database

**Implementation Examples**:

#### FranchiseTagEvent
```python
class FranchiseTagEvent(BaseEvent):
    """
    Team applies franchise tag to a player.

    Executed when AI team decides to use franchise tag,
    or when user chooses to tag a player.
    """

    def __init__(
        self,
        team_id: int,
        player_id: int,
        tag_type: str,  # "FRANCHISE" or "TRANSITION"
        tag_date: datetime,
        season: int
    ):
        super().__init__(timestamp=tag_date)
        self.team_id = team_id
        self.player_id = player_id
        self.tag_type = tag_type
        self.season = season
        self._game_id = f"franchise_tag_{team_id}_{player_id}"

    def get_event_type(self) -> str:
        return "FRANCHISE_TAG"

    def simulate(self) -> EventResult:
        """
        Apply franchise tag:
        1. Mark player as franchise tagged
        2. Calculate tag salary (position average)
        3. Update team salary cap
        4. Set extension deadline (mid-July)
        5. Log transaction
        """
        # Calculate franchise tag salary for player's position
        tag_salary = self._calculate_franchise_tag_salary()

        # Apply tag to player contract
        self._apply_franchise_tag(
            player_id=self.player_id,
            tag_type=self.tag_type,
            tag_salary=tag_salary,
            season=self.season
        )

        # Update team salary cap
        self._update_team_cap(self.team_id, tag_salary)

        return EventResult(
            event_id=self.event_id,
            event_type="FRANCHISE_TAG",
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "tag_type": self.tag_type,
                "tag_salary": tag_salary
            }
        )
```

#### UFASigningEvent
```python
class UFASigningEvent(BaseEvent):
    """
    Team signs unrestricted free agent.

    Can only occur during free agency window (after March 12, 4PM).
    """

    def __init__(
        self,
        signing_team_id: int,
        player_id: int,
        contract_years: int,
        contract_value: int,
        signing_date: datetime,
        season: int
    ):
        super().__init__(timestamp=signing_date)
        self.signing_team_id = signing_team_id
        self.player_id = player_id
        self.contract_years = contract_years
        self.contract_value = contract_value
        self.season = season
        self._game_id = f"ufa_signing_{signing_team_id}_{player_id}"

    def get_event_type(self) -> str:
        return "UFA_SIGNING"

    def simulate(self) -> EventResult:
        """
        Execute free agent signing:
        1. Validate free agency window is active
        2. Check team has salary cap space
        3. Create player contract
        4. Add player to team roster
        5. Update salary cap
        6. Log transaction
        """
        # Validate preconditions
        if not self._is_free_agency_active():
            return EventResult(
                event_id=self.event_id,
                event_type="UFA_SIGNING",
                success=False,
                timestamp=datetime.now(),
                data={},
                error_message="Free agency window not active"
            )

        # Check cap space
        cap_space = self._get_team_cap_space(self.signing_team_id)
        if cap_space < self.contract_value:
            return EventResult(
                event_id=self.event_id,
                event_type="UFA_SIGNING",
                success=False,
                timestamp=datetime.now(),
                data={},
                error_message=f"Insufficient cap space: ${cap_space} < ${self.contract_value}"
            )

        # Execute signing
        self._create_player_contract(
            player_id=self.player_id,
            team_id=self.signing_team_id,
            years=self.contract_years,
            value=self.contract_value
        )

        self._add_player_to_roster(self.player_id, self.signing_team_id)
        self._update_team_cap(self.signing_team_id, -self.contract_value)

        return EventResult(
            event_id=self.event_id,
            event_type="UFA_SIGNING",
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.signing_team_id,
                "player_id": self.player_id,
                "contract_years": self.contract_years,
                "contract_value": self.contract_value
            }
        )
```

#### DraftPickEvent
```python
class DraftPickEvent(BaseEvent):
    """
    Team makes draft selection.

    Executed during NFL Draft (April 24-26).
    """

    def __init__(
        self,
        team_id: int,
        draft_round: int,
        draft_pick: int,
        player_selected_id: int,
        draft_date: datetime,
        season: int
    ):
        super().__init__(timestamp=draft_date)
        self.team_id = team_id
        self.draft_round = draft_round
        self.draft_pick = draft_pick
        self.player_selected_id = player_selected_id
        self.season = season
        self._game_id = f"draft_pick_{season}_{draft_round}_{draft_pick}"

    def get_event_type(self) -> str:
        return "DRAFT_PICK"

    def simulate(self) -> EventResult:
        """
        Execute draft pick:
        1. Remove player from draft pool
        2. Create rookie contract (4 years)
        3. Add player to team roster
        4. Update draft order
        5. Log selection
        """
        # Create rookie contract (4 years, slotted by pick)
        rookie_contract_value = self._calculate_rookie_contract(
            round_num=self.draft_round,
            pick_num=self.draft_pick
        )

        self._create_player_contract(
            player_id=self.player_selected_id,
            team_id=self.team_id,
            years=4,  # All draft picks get 4-year deals
            value=rookie_contract_value
        )

        self._add_player_to_roster(self.player_selected_id, self.team_id)
        self._remove_from_draft_pool(self.player_selected_id)

        return EventResult(
            event_id=self.event_id,
            event_type="DRAFT_PICK",
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "round": self.draft_round,
                "pick": self.draft_pick,
                "player_id": self.player_selected_id,
                "contract_value": rookie_contract_value
            }
        )
```

#### RosterCutEvent
```python
class RosterCutEvent(BaseEvent):
    """
    Team releases player from roster.

    Can occur at any time, but mandatory cuts August 26.
    """

    def __init__(
        self,
        team_id: int,
        player_id: int,
        cut_designation: str,  # "PRE_JUNE_1", "POST_JUNE_1", "FINAL_CUTS"
        cut_date: datetime,
        season: int
    ):
        super().__init__(timestamp=cut_date)
        self.team_id = team_id
        self.player_id = player_id
        self.cut_designation = cut_designation
        self.season = season
        self._game_id = f"roster_cut_{team_id}_{player_id}"

    def get_event_type(self) -> str:
        return "ROSTER_CUT"

    def simulate(self) -> EventResult:
        """
        Execute player release:
        1. Calculate dead cap hit (based on cut designation)
        2. Remove player from roster
        3. Update salary cap
        4. Make player available (FA or waivers based on experience)
        5. Log transaction
        """
        # Calculate dead money impact
        dead_cap = self._calculate_dead_cap(
            player_id=self.player_id,
            cut_designation=self.cut_designation
        )

        # Remove from roster
        self._remove_player_from_roster(self.player_id, self.team_id)

        # Update cap (dead money still counts)
        self._update_team_cap(self.team_id, dead_cap)

        # Determine player availability (waivers vs FA)
        accrued_seasons = self._get_player_accrued_seasons(self.player_id)
        if accrued_seasons < 4:
            # Subject to waivers
            self._place_on_waivers(self.player_id)
        else:
            # Immediate free agent
            self._make_free_agent(self.player_id)

        return EventResult(
            event_id=self.event_id,
            event_type="ROSTER_CUT",
            success=True,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id,
                "cut_designation": self.cut_designation,
                "dead_cap": dead_cap
            }
        )
```

**Action Event Types Needed**:
- `FRANCHISE_TAG` - Apply franchise/transition tag
- `PLAYER_RELEASE` - Cut player from roster
- `UFA_SIGNING` - Sign unrestricted free agent
- `RFA_OFFER_SHEET` - Submit RFA offer sheet
- `RFA_MATCH` - Match RFA offer
- `DRAFT_PICK` - Make draft selection
- `UDFA_SIGNING` - Sign undrafted free agent
- `CONTRACT_RESTRUCTURE` - Convert salary to bonus
- `FIFTH_YEAR_OPTION` - Exercise 5th year option
- `ROSTER_CUT` - Release player
- `PRACTICE_SQUAD_SIGNING` - Sign to practice squad
- `WAIVER_CLAIM` - Claim player off waivers

---

### 4. **MilestoneEvent** (Informational)
Events marking major milestones but with no executable logic.

**Purpose**:
- Mark major dates (new league year, schedule release)
- Generate notifications
- Provide context for UI display

**Implementation**:
```python
class MilestoneEvent(BaseEvent):
    """
    Informational milestone event.

    Examples:
    - New league year begins (March 12)
    - Schedule released (May 14)
    - Scouting combine (Feb 24-Mar 3)
    """

    def __init__(
        self,
        milestone_type: str,
        milestone_date: datetime,
        description: str,
        event_id: Optional[str] = None
    ):
        super().__init__(event_id=event_id, timestamp=milestone_date)
        self.milestone_type = milestone_type
        self.description = description
        self._game_id = f"milestone_{milestone_type.lower()}"

    def get_event_type(self) -> str:
        return "MILESTONE"

    def simulate(self) -> EventResult:
        """
        Log milestone occurrence.
        No game logic executed.
        """
        print(f"\n📅 MILESTONE: {self.description}")

        return EventResult(
            event_id=self.event_id,
            event_type="MILESTONE",
            success=True,
            timestamp=datetime.now(),
            data={
                "milestone_type": self.milestone_type,
                "description": self.description
            }
        )
```

**Milestone Types Needed**:
- `NEW_LEAGUE_YEAR` - March 12, 4PM ET
- `SALARY_CAP_ANNOUNCEMENT` - Late February
- `SCHEDULE_RELEASE` - May 14, 8PM ET
- `SCOUTING_COMBINE` - Feb 24 - Mar 3

---

## Scheduling System

### Offseason Initialization Flow

**Trigger**: After Super Bowl completes

```python
def initialize_offseason_events(
    super_bowl_date: Date,
    season_year: int,
    dynasty_id: str,
    event_db: EventDatabaseAPI
):
    """
    Called once after Super Bowl to schedule all offseason events.

    Steps:
    1. Calculate all milestone dates dynamically based on Super Bowl date
    2. Create deadline, window, and milestone events
    3. Insert all events into database
    4. Events will be triggered automatically by SimulationExecutor
    """

    # Calculate milestone dates using existing SeasonMilestoneCalculator
    milestone_calculator = SeasonMilestoneCalculator()
    milestones = milestone_calculator.calculate_milestones_for_season(
        season_year=season_year + 1,  # Next season's offseason
        super_bowl_date=super_bowl_date
    )

    # Schedule deadline events
    _schedule_deadline_events(milestones, dynasty_id, event_db)

    # Schedule window events
    _schedule_window_events(milestones, dynasty_id, event_db)

    # Schedule milestone events
    _schedule_milestone_events(milestones, dynasty_id, event_db)

    print(f"✅ Offseason events scheduled for {season_year + 1} season")


def _schedule_deadline_events(
    milestones: List[SeasonMilestone],
    dynasty_id: str,
    event_db: EventDatabaseAPI
):
    """Schedule all deadline events."""

    # Franchise tag deadline (March 4, 4PM ET)
    franchise_tag_milestone = next(
        (m for m in milestones if m.milestone_type == MilestoneType.FRANCHISE_TAG_DEADLINE),
        None
    )
    if franchise_tag_milestone:
        deadline = DeadlineEvent(
            deadline_type="FRANCHISE_TAG",
            deadline_date=franchise_tag_milestone.date.to_python_date(),
            actions_to_trigger=["check_franchise_tags", "apply_penalties"],
            game_id=f"deadline_franchise_tag_{dynasty_id}"
        )
        event_db.insert_event(deadline)

    # Salary cap compliance (March 12, 4PM ET)
    salary_cap_milestone = next(
        (m for m in milestones if m.milestone_type == MilestoneType.SALARY_CAP_DEADLINE),
        None
    )
    if salary_cap_milestone:
        deadline = DeadlineEvent(
            deadline_type="SALARY_CAP_COMPLIANCE",
            deadline_date=salary_cap_milestone.date.to_python_date(),
            actions_to_trigger=["check_salary_cap", "force_compliance"],
            game_id=f"deadline_salary_cap_{dynasty_id}"
        )
        event_db.insert_event(deadline)

    # ... more deadline events (RFA offers, 5th year options, roster cuts, etc.)


def _schedule_window_events(
    milestones: List[SeasonMilestone],
    dynasty_id: str,
    event_db: EventDatabaseAPI
):
    """Schedule window start/end events."""

    # Legal tampering window (March 10 Noon → March 12 4PM)
    legal_tampering_start = WindowEvent(
        window_type="LEGAL_TAMPERING",
        window_action="START",
        window_date=datetime(2025, 3, 10, 12, 0, 0)  # Noon ET
    )
    event_db.insert_event(legal_tampering_start)

    legal_tampering_end = WindowEvent(
        window_type="LEGAL_TAMPERING",
        window_action="END",
        window_date=datetime(2025, 3, 12, 16, 0, 0)  # 4PM ET
    )
    event_db.insert_event(legal_tampering_end)

    # Free agency signing period (March 12 4PM → ongoing)
    free_agency_start = WindowEvent(
        window_type="FREE_AGENCY_SIGNING",
        window_action="START",
        window_date=datetime(2025, 3, 12, 16, 0, 0)
    )
    event_db.insert_event(free_agency_start)

    # ... more window events (OTAs, training camp, etc.)


def _schedule_milestone_events(
    milestones: List[SeasonMilestone],
    dynasty_id: str,
    event_db: EventDatabaseAPI
):
    """Schedule informational milestone events."""

    # New league year
    new_league_year = MilestoneEvent(
        milestone_type="NEW_LEAGUE_YEAR",
        milestone_date=datetime(2025, 3, 12, 16, 0, 0),
        description="New League Year Begins - Free Agency Opens"
    )
    event_db.insert_event(new_league_year)

    # Schedule release
    schedule_release = MilestoneEvent(
        milestone_type="SCHEDULE_RELEASE",
        milestone_date=datetime(2025, 5, 14, 20, 0, 0),  # 8PM ET
        description="Full Regular Season Schedule Released"
    )
    event_db.insert_event(schedule_release)

    # ... more milestone events
```

---

## Integration with Existing Systems

### 1. **SimulationExecutor** (Already Working!)

The existing `SimulationExecutor.simulate_day()` method already handles event retrieval and execution:

```python
# FROM: src/calendar/simulation_executor.py

def simulate_day(self, target_date: Optional[Date] = None):
    """
    Simulate all events for a specific day.
    """
    # Get events for this date
    events_for_day = self._get_events_for_date(target_date)

    # Simulate each event
    for event_data in events_for_day:
        # Reconstruct event from database
        event = reconstruct_event_from_database(event_data)

        # Execute event (polymorphic)
        if isinstance(event, GameEvent):
            # Simulate game
        elif isinstance(event, DeadlineEvent):
            # ✅ Execute deadline logic (NEW)
        elif isinstance(event, WindowEvent):
            # ✅ Update window state (NEW)
        elif isinstance(event, ActionEvent):
            # ✅ Execute action (NEW)
        elif isinstance(event, MilestoneEvent):
            # ✅ Log milestone (NEW)
```

**Required Changes**:
- Add offseason event type handling to `reconstruct_event_from_database()`
- No other changes needed - existing date-based event retrieval already works!

---

### 2. **SeasonPhaseTracker** (Add Offseason Phases)

Extend `SeasonPhase` enum to track offseason sub-phases:

```python
class SeasonPhase(Enum):
    REGULAR_SEASON = "regular_season"
    PLAYOFFS = "playoffs"

    # Add Offseason Sub-Phases
    OFFSEASON_POST_SUPER_BOWL = "offseason_post_super_bowl"  # Feb - Early March
    OFFSEASON_FREE_AGENCY = "offseason_free_agency"          # March 10 - April
    OFFSEASON_DRAFT = "offseason_draft"                      # April 24-26
    OFFSEASON_OTA = "offseason_ota"                          # May - June
    OFFSEASON_TRAINING_CAMP = "offseason_training_camp"      # July - August
    PRESEASON = "preseason"                                   # August (games)
```

Add phase transition triggers:

```python
class OffseasonPhaseTransitionTrigger(TransitionTrigger):
    """Trigger offseason phase transitions based on dates."""

    def check_trigger(self, current_date, completed_events):
        # Super Bowl → Post-Super Bowl
        if self._is_super_bowl_just_completed(completed_events):
            return PhaseTransition(
                from_phase=SeasonPhase.PLAYOFFS,
                to_phase=SeasonPhase.OFFSEASON_POST_SUPER_BOWL,
                trigger_date=current_date
            )

        # Post-Super Bowl → Free Agency (March 10)
        if current_date >= Date(2025, 3, 10):
            return PhaseTransition(
                from_phase=SeasonPhase.OFFSEASON_POST_SUPER_BOWL,
                to_phase=SeasonPhase.OFFSEASON_FREE_AGENCY,
                trigger_date=current_date
            )

        # Free Agency → Draft (April 24)
        if current_date >= Date(2025, 4, 24):
            return PhaseTransition(
                from_phase=SeasonPhase.OFFSEASON_FREE_AGENCY,
                to_phase=SeasonPhase.OFFSEASON_DRAFT,
                trigger_date=current_date
            )

        # ... more transitions
```

---

### 3. **SeasonMilestoneCalculator** (Extend with Offseason)

Add offseason milestone types and definitions:

```python
# Add to MilestoneType enum
class MilestoneType(Enum):
    # Existing
    DRAFT = "draft"
    FREE_AGENCY = "free_agency"

    # Add Offseason Milestones
    FRANCHISE_TAG_WINDOW_START = "franchise_tag_start"
    FRANCHISE_TAG_DEADLINE = "franchise_tag_deadline"
    LEGAL_TAMPERING_START = "legal_tampering_start"
    NEW_LEAGUE_YEAR = "new_league_year"
    SALARY_CAP_DEADLINE = "salary_cap_deadline"
    RFA_OFFER_DEADLINE = "rfa_offer_deadline"
    FIFTH_YEAR_OPTION_DEADLINE = "fifth_year_option"
    SCHEDULE_RELEASE = "schedule_release"
    ROOKIE_MINICAMP = "rookie_minicamp"
    OTA_START = "ota_start"
    MANDATORY_MINICAMP = "mandatory_minicamp"
    TRAINING_CAMP_START = "training_camp_start"
    ROSTER_CUTS_DEADLINE = "roster_cuts"
    WAIVER_CLAIM_DEADLINE = "waiver_claim"
    # ... 20+ more
```

Add offset calculators for each milestone:

```python
def _calculate_franchise_tag_deadline(
    self,
    base_date: Date,
    context: Dict[str, Any]
) -> Date:
    """
    Franchise tag deadline is March 4, 4PM ET.
    Fixed date regardless of Super Bowl timing.
    """
    season_year = context['season_year']
    return Date(season_year + 1, 3, 4)  # Next year's March 4


def _calculate_new_league_year(
    self,
    base_date: Date,
    context: Dict[str, Any]
) -> Date:
    """
    New league year is March 12, 4PM ET.
    Fixed date regardless of Super Bowl timing.
    """
    season_year = context['season_year']
    return Date(season_year + 1, 3, 12)  # Next year's March 12


def _calculate_roster_cuts_deadline(
    self,
    base_date: Date,
    context: Dict[str, Any]
) -> Date:
    """
    Roster cuts are August 26, 4PM ET.
    Day before preseason Week 4 / regular season Week 0.
    """
    season_year = context['season_year']
    return Date(season_year + 1, 8, 26)  # Next year's August 26
```

---

## AI Decision Making

### Team AI Offseason Logic

AI teams make decisions at deadlines and during windows:

```python
class OffseasonAIManager:
    """
    AI decision-making for computer-controlled teams during offseason.
    """

    def make_franchise_tag_decisions(self, team_id: int, deadline_date: Date):
        """
        Decide which players (if any) to franchise tag.

        Called by FRANCHISE_TAG_DEADLINE event.
        """
        # Get team's pending free agents
        pending_fas = self._get_pending_free_agents(team_id)

        # Evaluate each player
        for player in pending_fas:
            # Should we tag this player?
            if self._should_franchise_tag(team_id, player):
                # Create and schedule FranchiseTagEvent
                tag_event = FranchiseTagEvent(
                    team_id=team_id,
                    player_id=player.player_id,
                    tag_type="FRANCHISE",
                    tag_date=deadline_date,
                    season=self.current_season
                )

                # Execute immediately (before deadline)
                tag_event.simulate()

    def make_free_agency_decisions(self, team_id: int, current_date: Date):
        """
        Decide which free agents to pursue.

        Called daily during free agency window.
        """
        # Get available free agents
        available_fas = self._get_available_free_agents()

        # Identify team needs
        team_needs = self._analyze_team_needs(team_id)

        # Evaluate fits
        for fa in available_fas:
            if self._is_good_fit(fa, team_needs):
                # Calculate offer
                offer = self._calculate_contract_offer(team_id, fa)

                # Create signing event
                signing_event = UFASigningEvent(
                    signing_team_id=team_id,
                    player_id=fa.player_id,
                    contract_years=offer['years'],
                    contract_value=offer['value'],
                    signing_date=current_date,
                    season=self.current_season
                )

                # Try to execute (may fail due to cap space)
                result = signing_event.simulate()

                if result.success:
                    break  # Signed one player, move on

    def make_draft_decisions(self, team_id: int, pick_number: int):
        """
        Decide which player to draft.

        Called when team is on the clock during draft.
        """
        # Get draft board
        draft_board = self._get_team_draft_board(team_id)

        # Get best available player
        best_available = self._get_best_available(draft_board, pick_number)

        # Create draft pick event
        draft_event = DraftPickEvent(
            team_id=team_id,
            draft_round=self._get_round_from_pick(pick_number),
            draft_pick=pick_number,
            player_selected_id=best_available.player_id,
            draft_date=datetime.now(),
            season=self.current_season
        )

        # Execute pick
        draft_event.simulate()

    def make_roster_cut_decisions(self, team_id: int, deadline_date: Date):
        """
        Decide which players to cut to reach 53-man roster.

        Called by ROSTER_CUTS_DEADLINE event.
        """
        # Get current roster
        roster = self._get_team_roster(team_id)

        # Must cut to 53
        current_size = len(roster)
        cuts_needed = current_size - 53

        if cuts_needed <= 0:
            return  # Already compliant

        # Rank players by value
        ranked_players = self._rank_players_by_value(roster)

        # Cut lowest-ranked players
        for i in range(cuts_needed):
            player_to_cut = ranked_players[-(i+1)]  # Start from bottom

            cut_event = RosterCutEvent(
                team_id=team_id,
                player_id=player_to_cut.player_id,
                cut_designation="FINAL_CUTS",
                cut_date=deadline_date,
                season=self.current_season
            )

            cut_event.simulate()
```

**AI Integration Points**:
- `FRANCHISE_TAG_DEADLINE` → Trigger `make_franchise_tag_decisions()`
- `FREE_AGENCY_SIGNING` window → Daily `make_free_agency_decisions()`
- `DRAFT_PICK` events → Per-pick `make_draft_decisions()`
- `ROSTER_CUTS_DEADLINE` → Trigger `make_roster_cut_decisions()`

---

## User Interaction Flow

### Offseason UI Design

```
╔═══════════════════════════════════════════════════════════════╗
║                    OFFSEASON DASHBOARD                         ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║  Current Date: March 3, 2025                                  ║
║  Current Phase: Post-Super Bowl                               ║
║                                                                ║
║  📅 UPCOMING DEADLINES                                         ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │ ⏰ Franchise Tag Deadline      March 4 (4PM ET)  [1 day]│ ║
║  │ ⏰ Legal Tampering Begins       March 10 (Noon ET) [7 days]│ ║
║  │ ⏰ Free Agency Opens             March 12 (4PM ET) [9 days]│ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
║  💰 SALARY CAP STATUS                                          ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │ Team Cap:        $225,000,000                            │ ║
║  │ Current Spending: $198,450,000                           │ ║
║  │ Cap Space:        $26,550,000                            │ ║
║  │ Status: ✅ COMPLIANT                                      │ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
║  🏈 PENDING FREE AGENTS (Your Team)                            ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │ • QB Tom Brady (Age 38) - UFA                            │ ║
║  │ • WR Calvin Johnson (Age 29) - UFA                       │ ║
║  │ • LB Ray Lewis (Age 35) - UFA                            │ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
║  ACTIONS                                                       ║
║  [1] Apply Franchise Tag                                      ║
║  [2] Re-sign Own Players                                      ║
║  [3] View Free Agent Market                                   ║
║  [4] Manage Salary Cap                                        ║
║  [5] Advance 1 Day                                            ║
║  [6] Advance to Next Deadline                                 ║
║  [0] Exit                                                      ║
╚═══════════════════════════════════════════════════════════════╝
```

### User Decision Points

**Franchise Tag Window** (Feb 17 - March 4):
- Review pending free agents
- Apply franchise tag to up to 1 player
- Apply transition tag to up to 1 player

**Free Agency** (March 12+):
- Browse available free agents
- Filter by position, age, salary
- Make contract offers
- Sign players

**Draft** (April 24-26):
- View draft board
- Make selections when on the clock
- Trade draft picks

**Training Camp/Cuts** (July - August):
- Evaluate roster
- Make roster cuts to 53
- Sign practice squad players

---

## Implementation Phases

### ✅ Phase 1: Foundation (Week 1) - COMPLETE
**Goal**: Create event infrastructure for offseason

**Tasks**:
1. ✅ Create `DeadlineEvent` class (`src/events/deadline_event.py`)
2. ✅ Create `WindowEvent` class (`src/events/window_event.py`)
3. ✅ Create `MilestoneEvent` class (`src/events/milestone_event.py`)
4. ✅ Create all contract event classes (`src/events/contract_events.py`)
   - `FranchiseTagEvent`
   - `TransitionTagEvent`
   - `PlayerReleaseEvent`
   - `ContractRestructureEvent`
5. ✅ Create all free agency event classes (`src/events/free_agency_events.py`)
   - `UFASigningEvent`
   - `RFAOfferSheetEvent`
   - `CompensatoryPickEvent`
6. ✅ Create all draft event classes (`src/events/draft_events.py`)
   - `DraftPickEvent`
   - `UDFASigningEvent`
   - `DraftTradeEvent`
7. ✅ Create all roster management event classes (`src/events/roster_events.py`)
   - `RosterCutEvent`
   - `WaiverClaimEvent`
   - `PracticeSquadEvent`
8. ✅ Update `src/events/__init__.py` to export all new event classes
9. ✅ Create architecture documentation (`docs/architecture/offseason_event_system.md`)

**Success Criteria**:
- ✅ All 16 offseason event classes created as thin wrappers
- ✅ All events extend `BaseEvent` with proper interface implementation
- ✅ All events return placeholder `EventResult` (business logic deferred)
- ✅ Events follow thin wrapper pattern (no cap/contract dependencies)
- ✅ Comprehensive architecture documentation created

**Implementation Notes**:
- All events are lightweight wrappers that define WHEN things happen
- Business logic (salary cap, contracts, AI) intentionally deferred to separate systems
- Events ready to integrate with existing `SimulationExecutor`
- Dynasty isolation supported via `dynasty_id` parameter

---

### Phase 2: Business Logic Integration (Week 2-3)
**Goal**: Implement business logic for contract and salary cap systems

**Tasks**:
1. ✅ Design and implement salary cap tracking system
   - ✅ Database schema for team salary caps (`002_salary_cap_schema.sql`)
   - ✅ Cap calculation logic (`CapCalculator` class)
   - ✅ Cap compliance validation (`CapValidator` class)
   - ✅ Dynasty isolation support across all cap tables
2. ✅ Design and implement contract management system
   - ✅ Database schema for player contracts (8 tables created)
   - ✅ Contract creation and modification (`ContractManager` class)
   - ✅ Dead cap calculations (standard & June 1 designation)
   - ✅ Bonus proration logic (5-year maximum rule enforced)
   - ✅ Franchise tag and RFA tender tracking
3. ⏳ Integrate business logic with event classes
   - ⏳ Update `FranchiseTagEvent.simulate()` with real contract logic
   - ⏳ Update `PlayerReleaseEvent.simulate()` with cap calculations
   - ⏳ Update `ContractRestructureEvent.simulate()` with restructure logic
   - ⏳ Update `UFASigningEvent.simulate()` with contract creation
4. ⏳ Create offseason event factory
   - Helper methods to create properly configured events
   - Validation logic for event parameters
5. ⏳ Test contract events with real business logic

**Success Criteria**:
- ✅ Salary cap system tracks all 32 teams accurately
- ✅ Contract events modify database correctly (infrastructure ready)
- ✅ Cap space validated before signings (validation methods implemented)
- ✅ Dead cap calculated correctly for releases (calculator complete)

**Implementation Status** (October 2025):
- ✅ **Salary Cap Phase 1 Complete** - Core cap system fully implemented
  - `src/salary_cap/cap_calculator.py` (500+ lines) - All calculation formulas
  - `src/salary_cap/cap_database_api.py` (600+ lines) - Complete CRUD operations
  - `src/salary_cap/contract_manager.py` (500+ lines) - Contract lifecycle management
  - `src/salary_cap/cap_validator.py` (400+ lines) - NFL compliance rules
  - `src/salary_cap/cap_utils.py` (300+ lines) - Display formatting utilities
  - `src/database/migrations/002_salary_cap_schema.sql` (400+ lines) - Complete schema
  - Comprehensive test suite: 2,600+ lines of tests across 4 test files
  - Real-world validation: Mahomes contract, Russell Wilson dead money scenarios
- ⏳ **Event Integration Pending** - Business logic ready to integrate with offseason events
  - Cap system provides all needed APIs for event classes
  - Contract creation, restructuring, and release methods available
  - Franchise tag and RFA tender database tables ready
  - Next: Connect event classes to cap system methods

---

### Phase 3: Offseason Initialization & Scheduling (Week 4) - ✅ COMPLETE
**Goal**: Implement automatic offseason event scheduling after Super Bowl

**Completed Tasks**:
1. ✅ Created `OffseasonEventScheduler` class (`src/offseason/offseason_event_scheduler.py`)
   - Schedules 5 deadline events for the offseason
   - Schedules 13 window start/end events (6 pairs + 1 start-only)
   - Schedules 7 milestone events
   - Total: 25 events scheduled automatically after Super Bowl
2. ✅ Extended `SeasonMilestoneCalculator` with offseason milestone types
   - Added 14 new `MilestoneType` enum values (franchise tag, free agency, combine, etc.)
   - Added 14 milestone definitions with offset calculators
   - Added 14 calculation methods for dynamic/fixed date computation
   - Supports both fixed dates (March 4) and dynamic dates (2 weeks after Super Bowl)
3. ✅ Integrated with `SeasonCycleController`
   - Post-Super Bowl trigger in `_transition_to_offseason()` method
   - Calls `OffseasonEventScheduler` automatically after Super Bowl completes
   - Persists all events to database via `EventDatabaseAPI`
   - Verbose logging shows event counts (deadline/window/milestone)
4. ✅ Extended full season demo (`demo/full_season_demo/full_season_sim.py`)
   - New 8-option offseason menu with calendar controls
   - Event display methods for triggered events
   - "Advance 1 Day" and "Advance 1 Week" with event triggering
   - "Advance to Next Event" automatically jumps to next scheduled event
   - "View Upcoming Events" shows next 10 scheduled events with countdown
5. ✅ Tested offseason initialization
   - Events scheduled correctly after Super Bowl
   - Dates calculated accurately using milestone calculator
   - Dynasty isolation works correctly
   - Events trigger when calendar advances in offseason phase

**Success Criteria Met**:
- ✅ All offseason events auto-scheduled after Super Bowl (25 events total)
- ✅ Events trigger on correct dates when calendar advances
- ✅ Dynasty-specific events isolated correctly
- ✅ Placeholder events demonstrate triggering mechanism works
- ✅ Full season demo supports offseason calendar advancement
- ✅ Event infrastructure proven ready for Phase 4 (AI decisions + real logic)

**Implementation Details**:
- **OffseasonEventScheduler** creates events using milestone calculator results
- **SeasonMilestoneCalculator** now supports 22 total milestone types (8 original + 14 offseason)
- **SeasonCycleController** automatically schedules events in `_transition_to_offseason()`
- **SimulationExecutor** successfully retrieves and executes events by date during offseason
- **Full Season Demo** provides interactive calendar advancement with event visibility

**Files Created/Modified**:
- Created: `src/offseason/offseason_event_scheduler.py` (new scheduler class)
- Created: `src/offseason/__init__.py` (module initialization)
- Modified: `src/calendar/season_milestones.py` (+14 milestone types, +14 definitions, +14 methods)
- Modified: `src/season/season_cycle_controller.py` (offseason event scheduling integration)
- Modified: `demo/full_season_demo/full_season_sim.py` (offseason calendar advancement UI)

**Proof of Concept Validated**:
This phase successfully proves that:
1. ✅ Event-based architecture works for offseason
2. ✅ Date-driven triggering mechanism is sound
3. ✅ Calendar advancement correctly retrieves events from database
4. ✅ SimulationExecutor handles offseason event types (DEADLINE, WINDOW, MILESTONE)
5. ✅ Dynasty isolation works in offseason context
6. ✅ Infrastructure is ready for business logic integration in Phase 4

**Next Steps**: Phase 4 (AI Decision Engine) - Connect event placeholders to real business logic

---

### Phase 4: AI Decision Engine (Week 5-6)
**Goal**: Implement AI decision-making for computer-controlled teams

**Tasks**:
1. ⏳ Create `OffseasonAIManager` class
   - Franchise tag decisions (which players to tag)
   - Player release decisions (salary cap management)
   - Free agency decisions (which players to sign)
   - Draft decisions (player selection)
   - Roster cut decisions (90→53)
2. ⏳ Implement player evaluation system
   - Player value calculations
   - Position need analysis
   - Contract value projections
3. ⏳ Integrate AI with deadline events
   - Franchise tag deadline → trigger AI tag decisions
   - Free agency window → daily AI signing decisions
   - Draft day → AI pick selections
   - Roster cuts deadline → AI cut decisions
4. ⏳ Test AI decision-making
   - AI teams make logical decisions
   - AI stays under salary cap
   - AI fills roster needs

**Success Criteria**:
- All 31 AI teams manage their own offseason
- AI makes reasonable franchise tag decisions
- AI signs appropriate free agents
- AI makes draft selections
- AI completes roster cuts on time

---

### Phase 5: User Interface & Interaction (Week 7-8)
**Goal**: Create user-facing offseason interface for dynasty mode

**Tasks**:
1. ⏳ Create offseason dashboard
   - Display current date and phase
   - Show upcoming deadlines with countdowns
   - Display salary cap status
   - Show pending free agents
2. ⏳ Implement user decision points
   - Franchise tag selection UI
   - Free agent browsing and signing
   - Draft board and pick selection
   - Roster management and cuts
3. ⏳ Add calendar advancement controls
   - Advance 1 day
   - Advance to next deadline
   - Advance to next phase
4. ⏳ Add transaction logging and history
   - Show all offseason moves by team
   - Show league-wide transaction feed
5. ⏳ Test complete user experience
   - User can complete full offseason
   - All decisions work correctly
   - UI is intuitive and responsive

**Success Criteria**:
- User can navigate all offseason stages
- All deadlines visible with countdowns
- User can make all key decisions (tag, sign, draft, cut)
- AI teams handle their own offseason independently
- User sees real-time transaction updates

---

### Phase 6: Testing & Polish (Week 9)
**Goal**: Comprehensive testing and refinement

**Tasks**:
1. ⏳ Unit tests for all event classes
2. ⏳ Integration tests for complete offseason flow
3. ⏳ Performance testing (simulate 100+ offseasons)
4. ⏳ Bug fixes and edge case handling
5. ⏳ Documentation updates
6. ⏳ User acceptance testing

**Success Criteria**:
- All tests passing
- No critical bugs
- Performance acceptable
- Documentation complete

---

## Testing Strategy

### Unit Tests
```python
def test_franchise_tag_event():
    """Test franchise tag application."""
    event = FranchiseTagEvent(
        team_id=1,
        player_id=100,
        tag_type="FRANCHISE",
        tag_date=datetime(2025, 3, 1),
        season=2024
    )

    result = event.simulate()

    assert result.success
    assert player_has_franchise_tag(100)
    assert team_cap_updated(1)


def test_deadline_event_triggers_ai():
    """Test deadline event triggers AI decisions."""
    deadline = DeadlineEvent(
        deadline_type="FRANCHISE_TAG",
        deadline_date=datetime(2025, 3, 4),
        actions_to_trigger=["check_franchise_tags"]
    )

    result = deadline.simulate()

    assert result.success
    assert ai_decisions_were_made()
```

### Integration Tests
```python
def test_full_free_agency_flow():
    """Test complete free agency simulation."""
    # Initialize offseason
    initialize_offseason_events(
        super_bowl_date=Date(2025, 2, 9),
        season_year=2024,
        dynasty_id="test"
    )

    # Advance to free agency
    advance_to_date(Date(2025, 3, 12))

    # Verify window active
    assert is_free_agency_active()

    # Simulate free agent signing
    signing = UFASigningEvent(
        signing_team_id=1,
        player_id=100,
        contract_years=3,
        contract_value=15000000,
        signing_date=datetime(2025, 3, 12),
        season=2024
    )

    result = signing.simulate()

    assert result.success
    assert player_on_team(100, 1)


def test_complete_offseason_simulation():
    """Test simulating entire offseason."""
    # Initialize offseason
    initialize_offseason_events(
        super_bowl_date=Date(2025, 2, 9),
        season_year=2024,
        dynasty_id="test"
    )

    # Advance from Feb 10 → Sep 5 (full offseason)
    current_date = Date(2025, 2, 10)
    while current_date < Date(2025, 9, 5):
        simulate_day(current_date)
        current_date = current_date.add_days(1)

    # Verify all milestones hit
    assert franchise_tags_applied()
    assert free_agents_signed()
    assert draft_completed()
    assert rosters_at_53()
```

---

## Database Schema Extensions

### New Tables Needed

```sql
-- Player contracts
CREATE TABLE player_contracts (
    contract_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    start_year INTEGER NOT NULL,
    end_year INTEGER NOT NULL,
    total_value INTEGER NOT NULL,
    signing_bonus INTEGER,
    guaranteed_money INTEGER,
    contract_type TEXT, -- 'ROOKIE', 'VETERAN', 'FRANCHISE_TAG', 'TRANSITION_TAG'
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Franchise tags
CREATE TABLE franchise_tags (
    tag_id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    tag_type TEXT NOT NULL, -- 'FRANCHISE' or 'TRANSITION'
    tag_salary INTEGER NOT NULL,
    deadline_date DATE NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(player_id),
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Salary cap tracking
CREATE TABLE team_salary_cap (
    cap_id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    cap_limit INTEGER NOT NULL,
    current_spending INTEGER NOT NULL,
    cap_space INTEGER GENERATED ALWAYS AS (cap_limit - current_spending) VIRTUAL,
    FOREIGN KEY (team_id) REFERENCES teams(team_id)
);

-- Active offseason windows
CREATE TABLE active_windows (
    window_id INTEGER PRIMARY KEY,
    window_type TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

-- Draft prospects
CREATE TABLE draft_prospects (
    prospect_id INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    position TEXT NOT NULL,
    college TEXT,
    draft_grade TEXT,
    draft_round_projection INTEGER,
    is_drafted BOOLEAN DEFAULT FALSE
);

-- Draft picks
CREATE TABLE draft_picks (
    pick_id INTEGER PRIMARY KEY,
    season INTEGER NOT NULL,
    round_number INTEGER NOT NULL,
    pick_number INTEGER NOT NULL,
    original_team_id INTEGER NOT NULL,
    current_team_id INTEGER NOT NULL, -- May be traded
    player_selected_id INTEGER,
    is_compensatory BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (original_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (current_team_id) REFERENCES teams(team_id),
    FOREIGN KEY (player_selected_id) REFERENCES players(player_id)
);
```

---

## Key Design Principles (Summary)

1. **Events are Independent**
   - No event depends on another event's execution state
   - Events can be reordered without breaking logic
   - Events can be canceled or rescheduled

2. **Date-Driven Triggering**
   - Calendar advancement triggers events automatically
   - No manual event execution needed
   - SimulationExecutor handles all scheduling

3. **Polymorphic Event Handling**
   - All events extend `BaseEvent`
   - SimulationExecutor handles all types uniformly
   - Easy to add new event types

4. **Separation of Concerns**
   - Calendar manages dates
   - Events manage logic
   - Database stores state
   - UI displays information

5. **AI Autonomy**
   - AI teams make their own decisions at deadlines
   - User only manages their team
   - 31 AI teams operate independently

6. **Flexible Scheduling**
   - Milestones calculated dynamically from Super Bowl date
   - Can reschedule entire offseason if Super Bowl moves
   - No hardcoded dates in logic (only in milestone definitions)

---

## Progress Summary

### ✅ Completed (Phase 1)
- **16 offseason event classes created** in `src/events/`
  - 3 foundation events (DeadlineEvent, WindowEvent, MilestoneEvent)
  - 4 contract events (FranchiseTagEvent, TransitionTagEvent, PlayerReleaseEvent, ContractRestructureEvent)
  - 3 free agency events (UFASigningEvent, RFAOfferSheetEvent, CompensatoryPickEvent)
  - 3 draft events (DraftPickEvent, UDFASigningEvent, DraftTradeEvent)
  - 3 roster events (RosterCutEvent, WaiverClaimEvent, PracticeSquadEvent)
- **All events follow thin wrapper pattern** (no business logic dependencies)
- **Events ready for integration** with existing `SimulationExecutor`
- **Comprehensive architecture documentation** created

### ⏳ Next Steps (Phase 2-6)

1. **Phase 2: Business Logic Integration** (Week 2-3)
   - Implement salary cap tracking system
   - Implement contract management system
   - Integrate business logic with event classes

2. **Phase 3: Offseason Initialization** (Week 4)
   - Create `OffseasonEventScheduler` to auto-schedule events after Super Bowl
   - Integrate with `SeasonMilestoneCalculator`
   - Test automatic event scheduling

3. **Phase 4: AI Decision Engine** (Week 5-6)
   - Implement `OffseasonAIManager` for computer-controlled teams
   - Implement player evaluation and decision-making
   - Integrate AI with deadline events

4. **Phase 5: User Interface** (Week 7-8)
   - Create offseason dashboard for dynasty mode
   - Implement user decision points (tag, sign, draft, cut)
   - Add transaction logging and history

5. **Phase 6: Testing & Polish** (Week 9)
   - Comprehensive testing (unit, integration, performance)
   - Bug fixes and edge case handling
   - Final documentation updates

**Estimated Timeline**: 9 weeks for full implementation (Phase 1 complete)

**Dependencies**: None - builds entirely on existing infrastructure

**Current Status**: Foundation complete, ready for business logic integration