# Event-Cap System Integration Architecture

**Version:** 1.0.0
**Last Updated:** 2025-10-04
**Status:** Phase 3 Week 7 Complete - Event System Integration Implemented

## Overview

This document describes the architectural pattern used to integrate the NFL offseason event system with the salary cap management system. The integration provides a clean, maintainable bridge between calendar-based events and financial business logic while maintaining separation of concerns and dynasty isolation.

**Key Achievement**: All 16 offseason event types now execute real cap/contract business logic through a unified adapter pattern.

---

## Architecture Pattern

### The Event-Cap Bridge Pattern

The integration uses a **Facade + Handler** pattern to provide a clean interface between events and cap systems:

```
┌─────────────────────────────────────────────────────────────┐
│                    EVENT LAYER                              │
│  (FranchiseTagEvent, UFASigningEvent, PlayerReleaseEvent)   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Uses
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  EVENT CAP BRIDGE                           │
│  (Unified facade for all cap operations)                    │
│  - Dependency injection for cap/contract managers           │
│  - Dynasty isolation coordination                           │
│  - Error handling standardization                           │
└─────────┬───────────────┬───────────────┬───────────────────┘
          │               │               │
          │ Delegates     │ Delegates     │ Delegates
          ▼               ▼               ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│TagEventHandler│  │ContractEvent │  │ReleaseEvent  │
│              │  │Handler       │  │Handler       │
└─────┬────────┘  └─────┬────────┘  └──────┬───────┘
      │                 │                   │
      │ Calls           │ Calls             │ Calls
      ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────┐
│                    CAP SYSTEM LAYER                         │
│  (TagManager, ContractManager, CapValidator, CapCalculator) │
└─────────────────────────────────────────────────────────────┘
```

**Benefits**:
- **Separation of Concerns**: Events know WHEN things happen, cap system knows HOW they work
- **Single Responsibility**: Each handler manages one category of operations
- **Testability**: Bridge can be mocked for event testing, handlers can be unit tested
- **Dynasty Isolation**: Bridge coordinates dynasty_id propagation to all layers
- **Error Handling**: Consistent error structure across all event types

---

## Core Components

### 1. EventCapBridge

**File**: `src/salary_cap/event_cap_bridge.py`

**Purpose**: Central facade providing unified interface for all event-to-cap operations

**Responsibilities**:
- Initialize cap system components (TagManager, ContractManager, CapValidator)
- Provide high-level methods for each event type
- Coordinate dynasty isolation across all operations
- Standardize error handling and response format
- Manage database path configuration

**Key Methods**:

```python
class EventCapBridge:
    """
    Unified facade for event-to-cap system integration.

    Provides clean interface for all offseason event types to interact
    with salary cap, contract, and tag management systems.
    """

    def __init__(self, database_path: str = "data/database/nfl_simulation.db"):
        """Initialize bridge with all cap system components."""
        self.database_path = database_path
        self.tag_manager = TagManager(database_path)
        self.contract_manager = ContractManager(database_path)
        self.cap_validator = CapValidator(database_path)
        self.cap_calculator = CapCalculator(database_path)

    def execute_franchise_tag(
        self,
        team_id: int,
        player_id: str,
        player_position: str,
        season: int,
        tag_type: str,
        tag_date: date,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Execute franchise tag application through TagEventHandler.

        Returns:
            {
                "success": bool,
                "tag_salary": int,
                "contract_id": int,
                "cap_impact": int,
                "cap_space_remaining": int,
                "error_message": str (if failed)
            }
        """

    def execute_ufa_signing(
        self,
        team_id: int,
        player_id: str,
        contract_years: int,
        total_value: int,
        signing_bonus: int,
        base_salaries: List[int],
        guaranteed_amounts: List[int],
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Execute unrestricted free agent signing through ContractEventHandler.

        Returns:
            {
                "success": bool,
                "contract_id": int,
                "cap_impact": int,
                "cap_space_remaining": int,
                "error_message": str (if failed)
            }
        """

    def execute_player_release(
        self,
        team_id: int,
        player_id: str,
        contract_id: int,
        release_date: date,
        june_1_designation: bool,
        season: int,
        dynasty_id: str
    ) -> Dict[str, Any]:
        """
        Execute player release through ReleaseEventHandler.

        Returns:
            {
                "success": bool,
                "dead_money_current": int,
                "dead_money_next_year": int,
                "cap_savings": int,
                "cap_space_remaining": int,
                "error_message": str (if failed)
            }
        """
```

**Design Notes**:
- Bridge owns all cap system manager instances
- All methods return standardized dict format
- Dynasty ID passed to all underlying operations
- Database path configurable at construction

---

### 2. Event Handlers

Specialized handlers for different categories of cap operations:

#### TagEventHandler

**File**: `src/salary_cap/event_handlers/tag_event_handler.py`

**Purpose**: Handle franchise tag, transition tag, and RFA tender events

**Key Methods**:

```python
class TagEventHandler:
    """Handler for tag-related events."""

    def __init__(self, bridge: EventCapBridge):
        self.bridge = bridge
        self.tag_manager = bridge.tag_manager
        self.cap_validator = bridge.cap_validator

    def handle_franchise_tag(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process franchise tag application.

        Steps:
        1. Validate team has not already used franchise tag this season
        2. Calculate franchise tag salary for position
        3. Validate team has cap space for tag
        4. Apply tag via TagManager
        5. Create 1-year contract via ContractManager
        6. Update team cap
        7. Log transaction

        Returns:
            {
                "success": bool,
                "tag_salary": int,
                "contract_id": int,
                "cap_impact": int,
                "cap_space_remaining": int
            }
        """

    def handle_transition_tag(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process transition tag application (similar to franchise tag)."""

    def handle_rfa_tender(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process RFA tender application."""
```

**Validation Logic**:
- Check team hasn't exceeded tag limits (1 franchise OR 1 transition per year)
- Validate cap space sufficient for tag salary
- Verify player eligible for tag (accrued seasons, contract status)

---

#### ContractEventHandler

**File**: `src/salary_cap/event_handlers/contract_event_handler.py`

**Purpose**: Handle contract creation, modification, and signing events

**Key Methods**:

```python
class ContractEventHandler:
    """Handler for contract-related events."""

    def __init__(self, bridge: EventCapBridge):
        self.bridge = bridge
        self.contract_manager = bridge.contract_manager
        self.cap_validator = bridge.cap_validator
        self.cap_calculator = bridge.cap_calculator

    def handle_ufa_signing(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process UFA signing with cap validation.

        Steps:
        1. Validate free agency window is active
        2. Calculate Year 1 cap hit from contract terms
        3. Validate team has cap space
        4. Create contract via ContractManager
        5. Update team cap
        6. Log transaction

        Returns:
            {
                "success": bool,
                "contract_id": int,
                "cap_impact": int,
                "cap_space_remaining": int
            }
        """

    def handle_contract_restructure(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process contract restructure.

        Steps:
        1. Validate contract exists and is active
        2. Calculate cap savings from restructure
        3. Execute restructure via ContractManager
        4. Update team cap
        5. Log transaction

        Returns:
            {
                "success": bool,
                "cap_savings_current": int,
                "cap_increase_future": Dict[int, int],
                "dead_money_increase": int
            }
        """
```

**Cap Validation Flow**:
```
UFA Signing Request
    ↓
Calculate Year 1 Cap Hit
    ↓
Get Current Team Cap Space
    ↓
Is Cap Space >= Cap Hit?
    ├─ Yes → Create Contract → Update Cap → Success
    └─ No → Return Error (Insufficient Cap Space)
```

---

#### ReleaseEventHandler

**File**: `src/salary_cap/event_handlers/release_event_handler.py`

**Purpose**: Handle player releases with dead money calculations

**Key Methods**:

```python
class ReleaseEventHandler:
    """Handler for player release events."""

    def __init__(self, bridge: EventCapBridge):
        self.bridge = bridge
        self.contract_manager = bridge.contract_manager
        self.cap_calculator = bridge.cap_calculator

    def handle_player_release(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process player release with dead money calculation.

        Steps:
        1. Validate contract exists
        2. Calculate dead money (standard or June 1 designation)
        3. Validate June 1 designation limit (2 per team per year)
        4. Release player via ContractManager
        5. Apply dead money to team cap
        6. Log transaction

        Returns:
            {
                "success": bool,
                "dead_money_current": int,
                "dead_money_next_year": int (if June 1),
                "cap_savings": int,
                "cap_space_remaining": int
            }
        """
```

**June 1 Designation Logic**:
- Standard Release: All dead money hits current year
- June 1 Designation: Current year proration + remaining future proration next year
- Limit: Maximum 2 June 1 designations per team per season

---

#### RFAEventHandler

**File**: `src/salary_cap/event_handlers/rfa_event_handler.py`

**Purpose**: Handle RFA offer sheets and matching decisions

**Key Methods**:

```python
class RFAEventHandler:
    """Handler for RFA tender and offer sheet events."""

    def __init__(self, bridge: EventCapBridge):
        self.bridge = bridge
        self.tag_manager = bridge.tag_manager
        self.contract_manager = bridge.contract_manager
        self.cap_validator = bridge.cap_validator

    def handle_rfa_offer_sheet(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process RFA offer sheet submission.

        Steps:
        1. Validate player has RFA tender
        2. Validate offering team has cap space
        3. Create offer sheet
        4. Notify original team (5-day matching window)

        Returns:
            {
                "success": bool,
                "offer_sheet_id": int,
                "contract_terms": Dict,
                "compensation_draft_pick": str
            }
        """

    def handle_rfa_match(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process original team matching RFA offer.

        Steps:
        1. Validate team has cap space to match
        2. Create contract matching offer sheet terms
        3. Cancel offer sheet
        4. Update team cap

        Returns:
            {
                "success": bool,
                "contract_id": int,
                "cap_impact": int
            }
        """
```

---

### 3. ValidationMiddleware

**File**: `src/salary_cap/validation_middleware.py`

**Purpose**: Pre-execution validation for all event operations

**Key Validations**:

```python
class ValidationMiddleware:
    """Pre-execution validation for cap events."""

    @staticmethod
    def validate_franchise_tag(
        team_id: int,
        season: int,
        tag_salary: int,
        dynasty_id: str,
        cap_validator: CapValidator
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate franchise tag can be applied.

        Checks:
        1. Team hasn't already used franchise tag this season
        2. Team has cap space for tag salary
        3. League year hasn't started yet (before March 12)

        Returns:
            (is_valid, error_message)
        """
        # Check tag limit
        existing_tags = cap_validator.get_team_franchise_tags(team_id, season, dynasty_id)
        if existing_tags:
            return (False, "Team has already applied franchise tag this season")

        # Check cap space
        cap_space = cap_validator.calculate_team_cap_space(team_id, season, dynasty_id)
        if cap_space < tag_salary:
            return (False, f"Insufficient cap space: ${cap_space:,} < ${tag_salary:,}")

        return (True, None)

    @staticmethod
    def validate_ufa_signing(
        team_id: int,
        season: int,
        year_1_cap_hit: int,
        dynasty_id: str,
        cap_validator: CapValidator
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate UFA signing can proceed.

        Checks:
        1. Free agency window is active (after March 12)
        2. Team has cap space for Year 1 cap hit

        Returns:
            (is_valid, error_message)
        """

    @staticmethod
    def validate_june_1_release(
        team_id: int,
        season: int,
        dynasty_id: str,
        cap_validator: CapValidator
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate June 1 designation can be used.

        Checks:
        1. Team hasn't exceeded 2 June 1 designations for the season

        Returns:
            (is_valid, error_message)
        """
        can_use, count = cap_validator.validate_june_1_designation_limit(
            team_id, season, dynasty_id
        )

        if not can_use:
            return (False, f"Team has already used {count}/2 June 1 designations this season")

        return (True, None)
```

**Validation Sequence**:
```
Event Received
    ↓
ValidationMiddleware.validate_xxx()
    ↓
Is Valid?
    ├─ Yes → Pass to Handler → Execute Business Logic
    └─ No → Return Error (do not execute)
```

---

### 4. Enhanced Event Classes

All event classes follow this integration pattern:

```python
class FranchiseTagEvent(BaseEvent):
    """Event with cap integration."""

    def simulate(self) -> EventResult:
        """Execute event with full cap integration."""
        try:
            # 1. Initialize bridge and handler
            bridge = EventCapBridge(self.database_path)
            handler = TagEventHandler(bridge)

            # 2. Build event data dict
            event_data = {
                "team_id": self.team_id,
                "player_id": self.player_id,
                "player_position": self.player_position,
                "season": self.season,
                "tag_type": self.tag_type,
                "tag_date": self.event_date.to_python_date(),
                "dynasty_id": self.dynasty_id
            }

            # 3. Execute through handler (validation happens here)
            result = handler.handle_franchise_tag(event_data)

            # 4. Return standardized EventResult
            if result["success"]:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=True,
                    timestamp=datetime.now(),
                    data={
                        "tag_salary": result["tag_salary"],
                        "contract_id": result["contract_id"],
                        "cap_impact": result["cap_impact"],
                        "cap_space_remaining": result["cap_space_remaining"],
                        # ... event-specific data
                    }
                )
            else:
                return EventResult(
                    event_id=self.event_id,
                    event_type=self.get_event_type(),
                    success=False,
                    timestamp=datetime.now(),
                    data={},
                    error_message=result.get("error_message", "Unknown error")
                )

        except Exception as e:
            # Catch-all error handling
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=datetime.now(),
                data={},
                error_message=f"Event execution failed: {str(e)}"
            )
```

**Three-Layer Error Handling**:
1. **Handler Layer**: Business logic errors (cap violations, invalid state)
2. **Bridge Layer**: Coordination errors (missing managers, database errors)
3. **Event Layer**: Execution errors (exceptions, invalid parameters)

---

## Event Flow Diagrams

### Franchise Tag Event Flow

```
User/AI Decision: Apply Franchise Tag to Player X
    ↓
FranchiseTagEvent created with parameters
    ↓
Event scheduled in calendar (via EventDatabaseAPI)
    ↓
SimulationExecutor retrieves event on deadline date
    ↓
FranchiseTagEvent.simulate() called
    ↓
┌─────────────────────────────────────────────────────────┐
│ EventCapBridge.execute_franchise_tag()                  │
│    ↓                                                     │
│ ValidationMiddleware.validate_franchise_tag()           │
│    ├─ Check tag limit (1 per team)                      │
│    ├─ Check cap space sufficient                        │
│    └─ Check before league year deadline                 │
│    ↓                                                     │
│ Is Valid?                                                │
│    ├─ No → Return {"success": False, "error": "..."}    │
│    └─ Yes ↓                                              │
│                                                          │
│ TagEventHandler.handle_franchise_tag()                  │
│    ↓                                                     │
│ TagManager.calculate_franchise_tag_salary()             │
│    (Top 5 position average from previous season)        │
│    ↓                                                     │
│ TagManager.apply_franchise_tag()                        │
│    ├─ Insert into franchise_tags table                  │
│    ├─ Set tag_type, tag_salary, deadline_date           │
│    └─ Return tag_id                                      │
│    ↓                                                     │
│ ContractManager.create_contract()                       │
│    ├─ Contract type: FRANCHISE_TAG                      │
│    ├─ Contract years: 1                                 │
│    ├─ Total value: tag_salary                           │
│    ├─ Insert into player_contracts table                │
│    └─ Return contract_id                                │
│    ↓                                                     │
│ CapDatabaseAPI.log_transaction()                        │
│    ├─ Transaction type: FRANCHISE_TAG                   │
│    ├─ Cap impact: -tag_salary                           │
│    └─ Insert into cap_transactions table                │
│    ↓                                                     │
│ Return {                                                 │
│    "success": True,                                      │
│    "tag_salary": 35000000,                               │
│    "contract_id": 12345,                                 │
│    "cap_impact": 35000000,                               │
│    "cap_space_remaining": 15000000                       │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
    ↓
EventResult returned to SimulationExecutor
    ↓
Event marked as completed in events table
    ↓
User/AI notified of tag application
```

---

### UFA Signing Event Flow

```
User/AI Decision: Sign UFA Player Y to 3-year, $30M contract
    ↓
UFASigningEvent created with contract parameters
    ↓
Event scheduled in calendar
    ↓
SimulationExecutor retrieves event on signing date
    ↓
UFASigningEvent.simulate() called
    ↓
┌─────────────────────────────────────────────────────────┐
│ EventCapBridge.execute_ufa_signing()                    │
│    ↓                                                     │
│ ValidationMiddleware.validate_ufa_signing()             │
│    ├─ Check free agency window active (after 3/12)      │
│    ├─ Calculate Year 1 cap hit                          │
│    └─ Check team has cap space for Year 1 hit           │
│    ↓                                                     │
│ Is Valid?                                                │
│    ├─ No → Return {"success": False, "error": "..."}    │
│    └─ Yes ↓                                              │
│                                                          │
│ ContractEventHandler.handle_ufa_signing()               │
│    ↓                                                     │
│ CapCalculator.calculate_year_1_cap_hit()                │
│    ├─ Base salary: $8M                                  │
│    ├─ Signing bonus proration: $3M ($15M / 5 years)    │
│    └─ Year 1 cap hit: $11M                              │
│    ↓                                                     │
│ CapValidator.check_cap_compliance()                     │
│    ├─ Current cap space: $25M                           │
│    ├─ After signing: $14M                               │
│    └─ Still compliant ✓                                 │
│    ↓                                                     │
│ ContractManager.create_contract()                       │
│    ├─ Contract type: VETERAN                            │
│    ├─ Contract years: 3                                 │
│    ├─ Total value: $30M                                 │
│    ├─ Signing bonus: $15M                               │
│    ├─ Base salaries: [$8M, $10M, $12M]                 │
│    ├─ Insert player_contracts record                    │
│    ├─ Insert contract_year_details (3 rows)             │
│    └─ Return contract_id                                │
│    ↓                                                     │
│ CapDatabaseAPI.update_team_cap()                        │
│    ├─ Add $11M to team's committed cap                  │
│    └─ Update team_salary_cap table                      │
│    ↓                                                     │
│ CapDatabaseAPI.log_transaction()                        │
│    ├─ Transaction type: UFA_SIGNING                     │
│    ├─ Cap impact: -11000000 (Year 1)                    │
│    ├─ Future impact: {2026: -10M, 2027: -12M}           │
│    └─ Insert into cap_transactions table                │
│    ↓                                                     │
│ Return {                                                 │
│    "success": True,                                      │
│    "contract_id": 67890,                                 │
│    "cap_impact": 11000000,                               │
│    "cap_space_remaining": 14000000                       │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
    ↓
EventResult returned to SimulationExecutor
    ↓
Event marked as completed
    ↓
Player added to team roster
    ↓
User/AI notified of successful signing
```

---

### Player Release Event Flow

```
User/AI Decision: Release Player Z (June 1 designation)
    ↓
PlayerReleaseEvent created with June 1 flag
    ↓
Event scheduled in calendar
    ↓
SimulationExecutor retrieves event on release date
    ↓
PlayerReleaseEvent.simulate() called
    ↓
┌─────────────────────────────────────────────────────────┐
│ EventCapBridge.execute_player_release()                 │
│    ↓                                                     │
│ ValidationMiddleware.validate_june_1_release()          │
│    ├─ Check June 1 designation limit (2 per team/year)  │
│    └─ Current count: 1/2 ✓                              │
│    ↓                                                     │
│ Is Valid?                                                │
│    ├─ No → Return {"success": False, "error": "..."}    │
│    └─ Yes ↓                                              │
│                                                          │
│ ReleaseEventHandler.handle_player_release()             │
│    ↓                                                     │
│ CapCalculator.calculate_dead_money()                    │
│    ├─ Get contract details (3 years remaining)          │
│    ├─ Signing bonus proration: $5M/year × 3 = $15M     │
│    ├─ Guaranteed salary: $0 (none remaining)            │
│    ├─                                                    │
│    ├─ Standard Release:                                 │
│    │   Current year: $15M (all at once)                 │
│    │   Next year: $0                                    │
│    ├─                                                    │
│    └─ June 1 Designation:                               │
│        Current year: $5M (only Year 1 proration)        │
│        Next year: $10M (Years 2-3 proration)            │
│    ↓                                                     │
│ ContractManager.release_player()                        │
│    ├─ Mark contract as voided                           │
│    ├─ Set voided_date                                   │
│    ├─ Update player_contracts.is_active = FALSE         │
│    └─ Return release details                            │
│    ↓                                                     │
│ CapDatabaseAPI.insert_dead_money()                      │
│    ├─ Team ID: 7                                        │
│    ├─ Player ID: 999                                    │
│    ├─ Season: 2025                                      │
│    ├─ Dead money amount: $15M (total)                   │
│    ├─ Is June 1: TRUE                                   │
│    ├─ Current year dead money: $5M                      │
│    ├─ Next year dead money: $10M                        │
│    └─ Insert into dead_money table                      │
│    ↓                                                     │
│ CapDatabaseAPI.update_team_cap()                        │
│    ├─ Add $5M to team's dead money (2025)               │
│    ├─ Schedule $10M for next year (2026)                │
│    └─ Update team_salary_cap table                      │
│    ↓                                                     │
│ CapDatabaseAPI.log_transaction()                        │
│    ├─ Transaction type: PLAYER_RELEASE                  │
│    ├─ Dead money created: $15M                          │
│    ├─ Cap impact current: $5M                           │
│    ├─ Cap impact next year: $10M                        │
│    └─ Insert into cap_transactions table                │
│    ↓                                                     │
│ Return {                                                 │
│    "success": True,                                      │
│    "dead_money_current": 5000000,                        │
│    "dead_money_next_year": 10000000,                     │
│    "cap_savings": 0,  # No immediate savings             │
│    "cap_space_remaining": 20000000                       │
│ }                                                        │
└─────────────────────────────────────────────────────────┘
    ↓
EventResult returned to SimulationExecutor
    ↓
Event marked as completed
    ↓
Player removed from team roster
    ↓
User/AI notified of release and cap impact
```

---

## Data Flow

### Event Data Structure (Three-Part Design)

All event executions follow a three-part data structure:

#### 1. Input Parameters (Event Construction)
```python
{
    # Who and What
    "team_id": 7,  # Detroit Lions
    "player_id": "P_12345",
    "player_position": "QB",

    # When
    "season": 2025,
    "event_date": Date(2025, 3, 1),

    # How (event-specific)
    "tag_type": "FRANCHISE_NON_EXCLUSIVE",
    "contract_years": 3,
    "total_value": 45000000,

    # Context
    "dynasty_id": "my_dynasty_001",
    "database_path": "data/database/nfl_simulation.db"
}
```

#### 2. Handler Result (Business Logic Output)
```python
{
    # Success/Failure
    "success": True,

    # Primary Results
    "tag_salary": 35000000,
    "contract_id": 12345,

    # Cap Impact
    "cap_impact": 35000000,  # Current year
    "cap_space_remaining": 15000000,  # After transaction

    # Future Impact (optional)
    "future_cap_impact": {
        2026: -10000000,
        2027: -8000000
    },

    # Error (if failed)
    "error_message": "Insufficient cap space: $20M < $35M"
}
```

#### 3. EventResult (Standardized Response)
```python
EventResult(
    event_id="evt_franchise_tag_20250301_001",
    event_type="FRANCHISE_TAG",
    success=True,
    timestamp=datetime(2025, 3, 1, 14, 30, 0),

    data={
        # Event identification
        "team_id": 7,
        "player_id": "P_12345",
        "event_date": "2025-03-01",
        "dynasty_id": "my_dynasty_001",

        # Transaction details
        "tag_type": "FRANCHISE_NON_EXCLUSIVE",
        "tag_salary": 35000000,
        "contract_id": 12345,

        # Cap impact
        "cap_impact": 35000000,
        "cap_space_remaining": 15000000,

        # User-friendly message
        "message": "Applied FRANCHISE_NON_EXCLUSIVE tag: $35,000,000"
    },

    error_message=None  # Only set if success=False
)
```

---

### EventResult Structure by Event Type

#### Franchise Tag Event
```python
{
    "event_id": "evt_franchise_tag_xxx",
    "event_type": "FRANCHISE_TAG",
    "success": True,
    "timestamp": datetime,
    "data": {
        "team_id": int,
        "player_id": str,
        "player_position": str,
        "tag_type": str,  # "FRANCHISE_EXCLUSIVE" or "FRANCHISE_NON_EXCLUSIVE"
        "tag_salary": int,  # Calculated tag amount
        "contract_id": int,  # 1-year contract created
        "cap_impact": int,  # Same as tag_salary
        "cap_space_remaining": int,
        "consecutive_tag_number": int,  # 1, 2, or 3
        "extension_deadline": str,  # Mid-July deadline
        "event_date": str,
        "dynasty_id": str,
        "message": str
    },
    "error_message": None
}
```

#### UFA Signing Event
```python
{
    "event_id": "evt_ufa_signing_xxx",
    "event_type": "UFA_SIGNING",
    "success": True,
    "timestamp": datetime,
    "data": {
        "team_id": int,
        "player_id": str,
        "contract_years": int,
        "contract_value": int,  # Total contract value
        "signing_bonus": int,
        "base_salaries": List[int],
        "guaranteed_amounts": List[int],
        "avg_per_year": int,  # contract_value / contract_years
        "contract_id": int,
        "cap_impact": int,  # Year 1 cap hit
        "cap_space_remaining": int,
        "future_cap_impact": {  # Years 2+
            2026: int,
            2027: int,
            # ...
        },
        "event_date": str,
        "dynasty_id": str,
        "message": str
    },
    "error_message": None
}
```

#### Player Release Event
```python
{
    "event_id": "evt_player_release_xxx",
    "event_type": "PLAYER_RELEASE",
    "success": True,
    "timestamp": datetime,
    "data": {
        "team_id": int,
        "player_id": str,
        "contract_id": int,
        "release_date": str,
        "june_1_designation": bool,
        "dead_money_total": int,  # Total dead money
        "dead_money_current": int,  # Current year
        "dead_money_next_year": int,  # Next year (if June 1)
        "cap_savings": int,  # Immediate cap relief
        "cap_space_remaining": int,
        "event_date": str,
        "dynasty_id": str,
        "message": str
    },
    "error_message": None
}
```

---

## Integration Points

### Calendar System Integration

**How Events Are Scheduled**:

```python
# After Super Bowl completion
def initialize_offseason_events(
    super_bowl_date: Date,
    season_year: int,
    dynasty_id: str
):
    """Schedule all offseason deadline events."""

    # Calculate offseason dates
    milestone_calc = SeasonMilestoneCalculator()
    milestones = milestone_calc.calculate_milestones_for_season(
        season_year=season_year + 1,
        super_bowl_date=super_bowl_date
    )

    # Create deadline events
    franchise_tag_deadline = DeadlineEvent(
        deadline_type=DeadlineType.FRANCHISE_TAG,
        description="Franchise tag deadline (4:00 PM ET)",
        season_year=season_year + 1,
        event_date=Date(season_year + 1, 3, 4),  # March 4
        dynasty_id=dynasty_id
    )

    # Insert event into calendar
    event_db = EventDatabaseAPI()
    event_db.insert_event(franchise_tag_deadline)

    # ... schedule more events (free agency, draft, etc.)
```

**Event Retrieval**:

```python
# SimulationExecutor.simulate_day()
def simulate_day(self, target_date: Date):
    """Simulate all events for specific day."""

    # Get events scheduled for this date
    events_for_day = self.event_db.get_events_for_date(
        target_date,
        dynasty_id=self.dynasty_id
    )

    for event_data in events_for_day:
        # Reconstruct event object from database
        event = self._reconstruct_event(event_data)

        # Execute event (polymorphic)
        result = event.simulate()

        # Store result
        self.event_db.update_event_result(
            event_id=event.event_id,
            result=result
        )
```

**Dynasty Filtering**:
```sql
-- All calendar queries filter by dynasty
SELECT * FROM events
WHERE event_date = ?
  AND dynasty_id = ?
  AND is_completed = FALSE
ORDER BY event_time ASC;
```

---

### SimulationExecutor Integration

**Event Type Dispatching**:

```python
class SimulationExecutor:
    """Execute events from calendar."""

    def _reconstruct_event(self, event_data: Dict) -> BaseEvent:
        """
        Reconstruct event object from database record.

        Supports all event types:
        - GameEvent (existing)
        - DeadlineEvent (new)
        - WindowEvent (new)
        - MilestoneEvent (new)
        - FranchiseTagEvent (new)
        - UFASigningEvent (new)
        - PlayerReleaseEvent (new)
        - etc.
        """
        event_type = event_data["event_type"]
        parameters = json.loads(event_data["parameters"])

        # Dispatch to appropriate event class
        if event_type == "GAME":
            return GameEvent(**parameters)
        elif event_type == "DEADLINE":
            return DeadlineEvent(**parameters)
        elif event_type == "FRANCHISE_TAG":
            return FranchiseTagEvent(**parameters)
        elif event_type == "UFA_SIGNING":
            return UFASigningEvent(**parameters)
        elif event_type == "PLAYER_RELEASE":
            return PlayerReleaseEvent(**parameters)
        # ... more event types
        else:
            raise ValueError(f"Unknown event type: {event_type}")
```

**Result Persistence**:

```python
def _store_event_result(self, event: BaseEvent, result: EventResult):
    """Store event execution result in database."""

    self.event_db.update_event(
        event_id=event.event_id,
        updates={
            "is_completed": True,
            "completion_date": datetime.now(),
            "result_success": result.success,
            "result_data": json.dumps(result.data),
            "error_message": result.error_message
        }
    )
```

---

### Database Persistence

**Event Storage**:

All events stored in `events` table with JSON parameters:

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,  -- 'FRANCHISE_TAG', 'UFA_SIGNING', etc.
    event_date DATE NOT NULL,
    event_time TIME,
    dynasty_id TEXT NOT NULL,

    -- Event parameters (JSON)
    parameters TEXT NOT NULL,  -- Serialized event constructor args

    -- Execution status
    is_completed BOOLEAN DEFAULT FALSE,
    completion_date TIMESTAMP,
    result_success BOOLEAN,
    result_data TEXT,  -- JSON EventResult.data
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_date_dynasty ON events(event_date, dynasty_id);
CREATE INDEX idx_events_type ON events(event_type);
```

**Transaction Logging**:

All cap transactions logged in `cap_transactions` table:

```sql
CREATE TABLE cap_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,

    -- Transaction type
    transaction_type TEXT NOT NULL,  -- 'FRANCHISE_TAG', 'UFA_SIGNING', 'PLAYER_RELEASE'

    -- Related entities
    player_id TEXT,
    contract_id INTEGER,
    event_id TEXT,  -- Link back to originating event

    -- Cap impact
    cap_impact_current INTEGER DEFAULT 0,
    cap_impact_future TEXT,  -- JSON: {"2026": -10M, "2027": -8M}

    -- Transaction date
    transaction_date DATE NOT NULL,

    -- Description
    description TEXT,

    FOREIGN KEY (event_id) REFERENCES events(event_id)
);
```

**Dynasty Isolation**:

All cap-related queries filter by `dynasty_id`:

```python
# Example: Get team cap space
def calculate_team_cap_space(
    self,
    team_id: int,
    season: int,
    dynasty_id: str
) -> int:
    """Calculate available cap space for team."""

    # Query filters by dynasty_id
    contracts = self.db_api.get_team_contracts(
        team_id=team_id,
        season=season,
        dynasty_id=dynasty_id,
        active_only=True
    )

    dead_money = self.db_api.get_team_dead_money(
        team_id=team_id,
        season=season,
        dynasty_id=dynasty_id
    )

    # ... calculation
```

**Database Transaction Pattern**:

```python
def execute_franchise_tag(self, event_data: Dict) -> Dict:
    """Execute franchise tag with database transaction."""

    try:
        # Start transaction
        self.db_api.begin_transaction()

        # 1. Insert franchise tag record
        tag_id = self.db_api.insert_franchise_tag(...)

        # 2. Create contract
        contract_id = self.contract_manager.create_contract(...)

        # 3. Update team cap
        self.db_api.update_team_cap(...)

        # 4. Log transaction
        self.db_api.log_transaction(...)

        # Commit all changes atomically
        self.db_api.commit_transaction()

        return {"success": True, ...}

    except Exception as e:
        # Rollback on any error
        self.db_api.rollback_transaction()
        return {"success": False, "error_message": str(e)}
```

---

## Dynasty Isolation

### How It Works

Dynasty isolation ensures complete separation of data between different save files (dynasties):

**1. All Database Tables Include `dynasty_id`**:

```sql
-- player_contracts table
CREATE TABLE player_contracts (
    contract_id INTEGER PRIMARY KEY,
    player_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,  -- Isolates by save file
    -- ... other columns
);

-- franchise_tags table
CREATE TABLE franchise_tags (
    tag_id INTEGER PRIMARY KEY,
    player_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,  -- Isolates by save file
    -- ... other columns
);

-- team_salary_cap table
CREATE TABLE team_salary_cap (
    cap_id INTEGER PRIMARY KEY,
    team_id INTEGER NOT NULL,
    season INTEGER NOT NULL,
    dynasty_id TEXT NOT NULL,  -- Isolates by save file
    -- ... other columns
);
```

**2. All Queries Filter by `dynasty_id`**:

```python
# CapDatabaseAPI method example
def get_team_contracts(
    self,
    team_id: int,
    season: int,
    dynasty_id: str,  # Required parameter
    active_only: bool = True
) -> List[Dict]:
    """Get all contracts for team in given season and dynasty."""

    query = """
        SELECT * FROM player_contracts
        WHERE team_id = ?
          AND start_year <= ?
          AND end_year >= ?
          AND dynasty_id = ?  -- Dynasty filter
    """

    if active_only:
        query += " AND is_active = TRUE"

    return self.db.execute(query, (team_id, season, season, dynasty_id))
```

**3. `dynasty_id` Propagation Through All Layers**:

```
Event Layer:
    FranchiseTagEvent(dynasty_id="dynasty_eagles_2025")
        ↓
Bridge Layer:
    EventCapBridge.execute_franchise_tag(dynasty_id="dynasty_eagles_2025")
        ↓
Handler Layer:
    TagEventHandler.handle_franchise_tag(dynasty_id="dynasty_eagles_2025")
        ↓
Manager Layer:
    TagManager.apply_franchise_tag(dynasty_id="dynasty_eagles_2025")
        ↓
Database Layer:
    INSERT INTO franchise_tags (..., dynasty_id) VALUES (..., "dynasty_eagles_2025")
```

**4. Dynasty Context Example**:

```python
# User has two dynasty saves running simultaneously

# Dynasty 1: Eagles rebuild
eagles_tag_event = FranchiseTagEvent(
    team_id=21,  # Eagles
    player_id="P_12345",
    season=2025,
    dynasty_id="dynasty_eagles_rebuild_001"  # Isolated context
)

# Dynasty 2: Chiefs championship run
chiefs_tag_event = FranchiseTagEvent(
    team_id=12,  # Chiefs
    player_id="P_67890",
    season=2025,
    dynasty_id="dynasty_chiefs_championship_002"  # Different context
)

# Both events can execute independently
# Data never mixes between dynasties
```

**5. Multi-Dynasty Query Isolation**:

```sql
-- Query 1: Get Eagles cap space in Dynasty 1
SELECT * FROM team_salary_cap
WHERE team_id = 21
  AND season = 2025
  AND dynasty_id = 'dynasty_eagles_rebuild_001';  -- Only this dynasty

-- Query 2: Get Chiefs cap space in Dynasty 2
SELECT * FROM team_salary_cap
WHERE team_id = 12
  AND season = 2025
  AND dynasty_id = 'dynasty_chiefs_championship_002';  -- Different dynasty

-- Results completely isolated
-- No cross-contamination possible
```

---

## Error Handling

### Three-Tier Error Handling

All event executions go through three layers of error handling:

#### Tier 1: Handler Level (Business Logic Errors)

**Purpose**: Validate business rules and return structured errors

**Examples**:
- Cap space insufficient for signing
- Team already used franchise tag this season
- June 1 designation limit exceeded
- Player not eligible for tag

**Error Format**:
```python
{
    "success": False,
    "error_type": "CAP_VIOLATION",
    "error_message": "Insufficient cap space: Team has $20M, needs $35M",
    "error_details": {
        "current_cap_space": 20000000,
        "required_cap_space": 35000000,
        "shortfall": 15000000
    }
}
```

**Handler Code**:
```python
def handle_franchise_tag(self, event_data: Dict) -> Dict:
    """Process franchise tag with business logic validation."""

    # Calculate tag salary
    tag_salary = self.tag_manager.calculate_franchise_tag_salary(...)

    # Validate cap space
    cap_space = self.bridge.cap_calculator.calculate_team_cap_space(...)

    if cap_space < tag_salary:
        return {
            "success": False,
            "error_type": "CAP_VIOLATION",
            "error_message": f"Insufficient cap space: ${cap_space:,} < ${tag_salary:,}",
            "error_details": {
                "current_cap_space": cap_space,
                "required_cap_space": tag_salary,
                "shortfall": tag_salary - cap_space
            }
        }

    # Proceed with tag application...
```

---

#### Tier 2: Bridge Level (Coordination Errors)

**Purpose**: Handle system-level errors (database, missing managers, etc.)

**Examples**:
- Database connection failure
- Missing cap manager instance
- Invalid database path
- Transaction rollback errors

**Error Format**:
```python
{
    "success": False,
    "error_type": "SYSTEM_ERROR",
    "error_message": "Database connection failed: Unable to open database",
    "error_details": {
        "database_path": "data/database/nfl_simulation.db",
        "exception_type": "sqlite3.OperationalError"
    }
}
```

**Bridge Code**:
```python
def execute_franchise_tag(self, event_data: Dict) -> Dict:
    """Execute franchise tag with system-level error handling."""

    try:
        # Initialize handler
        handler = TagEventHandler(self)

        # Execute through handler
        result = handler.handle_franchise_tag(event_data)

        return result

    except DatabaseConnectionError as e:
        return {
            "success": False,
            "error_type": "SYSTEM_ERROR",
            "error_message": f"Database connection failed: {str(e)}",
            "error_details": {
                "database_path": self.database_path,
                "exception_type": type(e).__name__
            }
        }
    except Exception as e:
        # Catch-all for unexpected errors
        return {
            "success": False,
            "error_type": "UNKNOWN_ERROR",
            "error_message": f"Unexpected error: {str(e)}",
            "error_details": {
                "exception_type": type(e).__name__,
                "stack_trace": traceback.format_exc()
            }
        }
```

---

#### Tier 3: Event Level (Execution Errors)

**Purpose**: Wrap all errors in EventResult for consistent API

**Examples**:
- Event parameter validation failures
- Bridge initialization errors
- Uncaught exceptions

**Error Format**:
```python
EventResult(
    event_id="evt_franchise_tag_xxx",
    event_type="FRANCHISE_TAG",
    success=False,
    timestamp=datetime.now(),
    data={
        "team_id": 7,
        "player_id": "P_12345",
        "attempted_tag_type": "FRANCHISE_NON_EXCLUSIVE"
    },
    error_message="Insufficient cap space: $20,000,000 < $35,000,000"
)
```

**Event Code**:
```python
def simulate(self) -> EventResult:
    """Execute franchise tag event."""

    try:
        # Initialize bridge
        bridge = EventCapBridge(self.database_path)
        handler = TagEventHandler(bridge)

        # Build event data
        event_data = {
            "team_id": self.team_id,
            "player_id": self.player_id,
            # ... more parameters
        }

        # Execute through handler
        result = handler.handle_franchise_tag(event_data)

        # Convert to EventResult
        if result["success"]:
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=True,
                timestamp=datetime.now(),
                data={
                    "tag_salary": result["tag_salary"],
                    "contract_id": result["contract_id"],
                    # ... more data
                }
            )
        else:
            # Business logic error from handler
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=False,
                timestamp=datetime.now(),
                data={
                    "team_id": self.team_id,
                    "player_id": self.player_id
                },
                error_message=result["error_message"]
            )

    except Exception as e:
        # Execution error (bridge init, unexpected exception)
        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=False,
            timestamp=datetime.now(),
            data={
                "team_id": self.team_id,
                "player_id": self.player_id
            },
            error_message=f"Event execution failed: {str(e)}"
        )
```

---

### Error Types by Category

#### CAP_VIOLATION Errors
- Insufficient cap space for transaction
- Over cap limit at league year start
- Spending floor violation (89% over 4 years)

```python
{
    "error_type": "CAP_VIOLATION",
    "error_message": "Team over cap by $5,000,000 at league year start",
    "error_details": {
        "cap_limit": 279200000,
        "committed_cap": 284200000,
        "over_cap_amount": 5000000
    }
}
```

#### VALIDATION_ERROR Errors
- Team already used franchise tag
- June 1 designation limit exceeded
- Player not eligible for tag/tender
- Contract does not exist

```python
{
    "error_type": "VALIDATION_ERROR",
    "error_message": "Team has already used franchise tag this season",
    "error_details": {
        "team_id": 7,
        "season": 2025,
        "existing_tag_player_id": "P_99999"
    }
}
```

#### SYSTEM_ERROR Errors
- Database connection failure
- Transaction rollback
- Missing required data

```python
{
    "error_type": "SYSTEM_ERROR",
    "error_message": "Failed to create contract: Database locked",
    "error_details": {
        "operation": "insert_contract",
        "database_path": "data/database/nfl_simulation.db"
    }
}
```

---

### Error Messages by Scenario

| Scenario | Error Type | Message |
|----------|-----------|---------|
| Insufficient cap space for franchise tag | CAP_VIOLATION | "Insufficient cap space: $20,000,000 < $35,000,000" |
| Team already used franchise tag | VALIDATION_ERROR | "Team has already used franchise tag this season" |
| Team exceeded June 1 limit | VALIDATION_ERROR | "Team has already used 2/2 June 1 designations this season" |
| Free agency window not active | VALIDATION_ERROR | "Free agency window not active until March 12, 4PM ET" |
| Contract does not exist | VALIDATION_ERROR | "Contract ID 12345 not found or already voided" |
| Player not on team | VALIDATION_ERROR | "Player P_12345 is not on team 7" |
| Database connection error | SYSTEM_ERROR | "Database connection failed: Unable to open database" |
| Transaction rollback | SYSTEM_ERROR | "Transaction failed and was rolled back: Duplicate entry" |

---

## Usage Examples

### Example 1: Creating and Executing a Franchise Tag Event

```python
from events import FranchiseTagEvent
from calendar.date_models import Date
from datetime import datetime

# User decides to franchise tag their star quarterback

# Create franchise tag event
tag_event = FranchiseTagEvent(
    team_id=7,  # Detroit Lions
    player_id="P_QB_001",  # Quarterback ID
    player_position="QB",
    season=2025,
    tag_type="FRANCHISE_NON_EXCLUSIVE",  # Allows other teams to offer
    tag_amount=35000000,  # Calculated tag salary
    event_date=Date(2025, 3, 1),  # Applied on March 1
    event_id="evt_franchise_tag_det_qb_20250301",
    dynasty_id="dynasty_lions_rebuild_001",
    database_path="data/database/nfl_simulation.db"
)

# Execute event immediately (or schedule in calendar for later)
result = tag_event.simulate()

# Check result
if result.success:
    print(f"✅ Franchise tag applied!")
    print(f"Tag salary: ${result.data['tag_salary']:,}")
    print(f"Contract ID: {result.data['contract_id']}")
    print(f"Cap space remaining: ${result.data['cap_space_remaining']:,}")
    print(f"Message: {result.data['message']}")
else:
    print(f"❌ Franchise tag failed!")
    print(f"Error: {result.error_message}")
```

**Output (Success)**:
```
✅ Franchise tag applied!
Tag salary: $35,000,000
Contract ID: 45678
Cap space remaining: $15,000,000
Message: Applied FRANCHISE_NON_EXCLUSIVE tag: $35,000,000
```

**Output (Failure - Insufficient Cap)**:
```
❌ Franchise tag failed!
Error: Insufficient cap space: $20,000,000 < $35,000,000
```

---

### Example 2: Creating and Executing a UFA Signing Event

```python
from events import UFASigningEvent
from calendar.date_models import Date

# User signs a free agent wide receiver

# Define contract terms
contract_years = 3
total_value = 45000000  # $45M over 3 years
signing_bonus = 15000000  # $15M upfront
base_salaries = [8000000, 12000000, 15000000]  # Year-by-year
guaranteed_amounts = [15000000, 10000000, 5000000]  # Guarantees

# Create UFA signing event
signing_event = UFASigningEvent(
    team_id=7,  # Detroit Lions
    player_id="P_WR_100",  # Wide receiver ID
    contract_years=contract_years,
    contract_value=total_value,
    signing_bonus=signing_bonus,
    base_salaries=base_salaries,
    guaranteed_amounts=guaranteed_amounts,
    season=2025,
    event_date=Date(2025, 3, 15),  # Signed during free agency
    event_id="evt_ufa_signing_det_wr_20250315",
    dynasty_id="dynasty_lions_rebuild_001",
    database_path="data/database/nfl_simulation.db"
)

# Execute signing
result = signing_event.simulate()

# Check result
if result.success:
    print(f"✅ Player signed!")
    print(f"Contract: {result.data['contract_years']} years, ${result.data['contract_value']:,}")
    print(f"Average per year: ${result.data['avg_per_year']:,}")
    print(f"Year 1 cap hit: ${result.data['cap_impact']:,}")
    print(f"Cap space remaining: ${result.data['cap_space_remaining']:,}")
    print(f"Contract ID: {result.data['contract_id']}")
else:
    print(f"❌ Signing failed!")
    print(f"Error: {result.error_message}")
```

**Output (Success)**:
```
✅ Player signed!
Contract: 3 years, $45,000,000
Average per year: $15,000,000
Year 1 cap hit: $11,000,000
Cap space remaining: $14,000,000
Contract ID: 56789
```

---

### Example 3: Scheduling Multiple Events in Calendar

```python
from events import FranchiseTagEvent, UFASigningEvent, PlayerReleaseEvent, DeadlineEvent
from calendar.event_database_api import EventDatabaseAPI
from calendar.date_models import Date

# Initialize event database
event_db = EventDatabaseAPI(database_path="data/database/nfl_simulation.db")

dynasty_id = "dynasty_eagles_rebuild_001"
season = 2025

# === Schedule Deadline Events ===

# Franchise tag deadline (March 4, 4PM)
franchise_deadline = DeadlineEvent(
    deadline_type="FRANCHISE_TAG",
    description="Franchise tag deadline (4:00 PM ET)",
    season_year=season,
    event_date=Date(season, 3, 4),
    dynasty_id=dynasty_id
)
event_db.insert_event(franchise_deadline)

# Salary cap compliance deadline (March 12, 4PM)
cap_deadline = DeadlineEvent(
    deadline_type="SALARY_CAP_COMPLIANCE",
    description="Salary cap compliance deadline (4:00 PM ET)",
    season_year=season,
    event_date=Date(season, 3, 12),
    dynasty_id=dynasty_id
)
event_db.insert_event(cap_deadline)

# === Schedule Action Events ===

# 1. Release expensive veteran (March 10) to clear cap space
release_event = PlayerReleaseEvent(
    team_id=21,  # Eagles
    player_id="P_RB_500",
    contract_id=12345,
    release_date=Date(season, 3, 10),
    june_1_designation=True,  # Use June 1 to split dead money
    season=season,
    dynasty_id=dynasty_id
)
event_db.insert_event(release_event)

# 2. Apply franchise tag (March 1)
tag_event = FranchiseTagEvent(
    team_id=21,  # Eagles
    player_id="P_DE_200",  # Star defensive end
    player_position="DE",
    season=season,
    tag_type="FRANCHISE_NON_EXCLUSIVE",
    tag_amount=25000000,
    event_date=Date(season, 3, 1),
    dynasty_id=dynasty_id
)
event_db.insert_event(tag_event)

# 3. Sign free agent (March 15)
signing_event = UFASigningEvent(
    team_id=21,  # Eagles
    player_id="P_CB_300",  # Top cornerback
    contract_years=4,
    contract_value=60000000,
    signing_bonus=20000000,
    base_salaries=[10000000, 12000000, 14000000, 16000000],
    guaranteed_amounts=[20000000, 15000000, 10000000, 5000000],
    season=season,
    event_date=Date(season, 3, 15),
    dynasty_id=dynasty_id
)
event_db.insert_event(signing_event)

print("✅ All offseason events scheduled!")
print(f"Events will execute automatically as calendar advances through {season} offseason")
```

**Calendar Execution Flow**:
```
March 1:  Franchise tag event executes → Tag applied
March 4:  Franchise tag deadline event → Check all teams compliance
March 10: Player release event executes → Cap space cleared
March 12: Salary cap deadline event → Force all teams to compliance
March 15: UFA signing event executes → Player signed
```

---

## Testing Strategy

### Unit Testing

Test each component in isolation:

```python
# tests/salary_cap/test_event_cap_bridge.py

def test_franchise_tag_success(test_database):
    """Test successful franchise tag execution through bridge."""

    # Setup
    bridge = EventCapBridge(database_path=test_database)

    # Execute franchise tag
    result = bridge.execute_franchise_tag(
        team_id=1,
        player_id="P_QB_001",
        player_position="QB",
        season=2025,
        tag_type="FRANCHISE_NON_EXCLUSIVE",
        tag_date=date(2025, 3, 1),
        dynasty_id="test_dynasty"
    )

    # Assertions
    assert result["success"] is True
    assert "tag_salary" in result
    assert result["tag_salary"] > 0
    assert "contract_id" in result
    assert result["cap_impact"] == result["tag_salary"]
    assert result["cap_space_remaining"] >= 0


def test_franchise_tag_insufficient_cap(test_database):
    """Test franchise tag fails when team over cap."""

    # Setup: Create team with minimal cap space
    setup_team_near_cap_limit(team_id=1, season=2025, dynasty_id="test_dynasty")

    bridge = EventCapBridge(database_path=test_database)

    # Execute franchise tag
    result = bridge.execute_franchise_tag(
        team_id=1,
        player_id="P_QB_001",
        player_position="QB",
        season=2025,
        tag_type="FRANCHISE_NON_EXCLUSIVE",
        tag_date=date(2025, 3, 1),
        dynasty_id="test_dynasty"
    )

    # Assertions
    assert result["success"] is False
    assert "Insufficient cap space" in result["error_message"]
    assert "error_type" in result
    assert result["error_type"] == "CAP_VIOLATION"
```

```python
# tests/salary_cap/test_tag_event_handler.py

def test_handle_franchise_tag_validation(test_database):
    """Test franchise tag handler validates properly."""

    # Setup
    bridge = EventCapBridge(database_path=test_database)
    handler = TagEventHandler(bridge)

    event_data = {
        "team_id": 1,
        "player_id": "P_QB_001",
        "player_position": "QB",
        "season": 2025,
        "tag_type": "FRANCHISE_NON_EXCLUSIVE",
        "tag_date": date(2025, 3, 1),
        "dynasty_id": "test_dynasty"
    }

    # Execute
    result = handler.handle_franchise_tag(event_data)

    # Assertions
    assert "success" in result
    assert "tag_salary" in result
    if result["success"]:
        assert "contract_id" in result
        assert "cap_impact" in result
```

---

### Integration Testing

Test complete event-to-cap workflows:

```python
# tests/integration/test_franchise_tag_flow.py

def test_complete_franchise_tag_flow(test_database):
    """Test complete franchise tag from event creation to database persistence."""

    # 1. Create franchise tag event
    tag_event = FranchiseTagEvent(
        team_id=1,
        player_id="P_QB_001",
        player_position="QB",
        season=2025,
        tag_type="FRANCHISE_NON_EXCLUSIVE",
        tag_amount=35000000,
        event_date=Date(2025, 3, 1),
        dynasty_id="test_dynasty",
        database_path=test_database
    )

    # 2. Execute event
    result = tag_event.simulate()

    # 3. Verify EventResult
    assert result.success is True
    assert result.data["tag_salary"] == 35000000
    assert "contract_id" in result.data

    # 4. Verify database persistence
    db_api = CapDatabaseAPI(test_database)

    # Check franchise tag record
    tags = db_api.get_team_franchise_tags(
        team_id=1,
        season=2025,
        dynasty_id="test_dynasty"
    )
    assert len(tags) == 1
    assert tags[0]["tag_salary"] == 35000000

    # Check contract created
    contract = db_api.get_contract(result.data["contract_id"])
    assert contract is not None
    assert contract["contract_type"] == "FRANCHISE_TAG"
    assert contract["total_value"] == 35000000

    # Check cap updated
    cap_summary = db_api.get_team_cap_summary(
        team_id=1,
        season=2025,
        dynasty_id="test_dynasty"
    )
    assert cap_summary["committed_cap"] >= 35000000

    # Check transaction logged
    transactions = db_api.get_team_transactions(
        team_id=1,
        season=2025,
        dynasty_id="test_dynasty"
    )
    franchise_tags = [t for t in transactions if t["transaction_type"] == "FRANCHISE_TAG"]
    assert len(franchise_tags) == 1
    assert franchise_tags[0]["cap_impact_current"] == 35000000
```

---

### Test Data Patterns

Recommended test data structures for consistent testing:

```python
# tests/conftest.py

@pytest.fixture
def test_team_cap_data():
    """Standard test team with cap data."""
    return {
        "team_id": 1,
        "season": 2025,
        "dynasty_id": "test_dynasty",
        "cap_limit": 279200000,
        "committed_cap": 220000000,
        "cap_space": 59200000,
        "active_contracts": 45
    }


@pytest.fixture
def test_franchise_tag_data():
    """Standard franchise tag event data."""
    return {
        "team_id": 1,
        "player_id": "P_QB_001",
        "player_position": "QB",
        "season": 2025,
        "tag_type": "FRANCHISE_NON_EXCLUSIVE",
        "tag_salary": 35000000,
        "tag_date": date(2025, 3, 1),
        "dynasty_id": "test_dynasty"
    }


@pytest.fixture
def test_ufa_contract_data():
    """Standard UFA contract data."""
    return {
        "team_id": 1,
        "player_id": "P_WR_100",
        "contract_years": 3,
        "total_value": 45000000,
        "signing_bonus": 15000000,
        "base_salaries": [8000000, 12000000, 15000000],
        "guaranteed_amounts": [15000000, 10000000, 5000000],
        "season": 2025,
        "dynasty_id": "test_dynasty"
    }
```

---

## Performance Considerations

### Database Optimization

**Indexes for Fast Queries**:

```sql
-- Critical indexes for event-cap integration

-- Events table
CREATE INDEX idx_events_date_dynasty ON events(event_date, dynasty_id);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_completed ON events(is_completed);

-- Player contracts table
CREATE INDEX idx_contracts_team_season ON player_contracts(team_id, start_year, dynasty_id);
CREATE INDEX idx_contracts_player ON player_contracts(player_id, dynasty_id);
CREATE INDEX idx_contracts_active ON player_contracts(is_active);

-- Franchise tags table
CREATE INDEX idx_tags_team_season ON franchise_tags(team_id, season, dynasty_id);
CREATE INDEX idx_tags_player ON franchise_tags(player_id, season);

-- Team salary cap table
CREATE INDEX idx_cap_team_season ON team_salary_cap(team_id, season, dynasty_id);

-- Cap transactions table
CREATE INDEX idx_transactions_team_season ON cap_transactions(team_id, season, dynasty_id);
CREATE INDEX idx_transactions_type ON cap_transactions(transaction_type);
CREATE INDEX idx_transactions_date ON cap_transactions(transaction_date);
```

**Query Optimization Patterns**:

```python
# Batch queries when possible
def get_all_team_cap_data(team_id: int, season: int, dynasty_id: str) -> Dict:
    """Get all cap data in single query instead of multiple."""

    # Instead of:
    # contracts = get_team_contracts(...)
    # dead_money = get_team_dead_money(...)
    # tags = get_team_franchise_tags(...)

    # Do single JOIN query:
    query = """
        SELECT
            c.*,
            dm.dead_money_amount,
            ft.tag_salary
        FROM player_contracts c
        LEFT JOIN dead_money dm ON dm.contract_id = c.contract_id
        LEFT JOIN franchise_tags ft ON ft.player_id = c.player_id
        WHERE c.team_id = ?
          AND c.start_year <= ?
          AND c.end_year >= ?
          AND c.dynasty_id = ?
    """

    return db.execute(query, (team_id, season, season, dynasty_id))
```

---

### Caching Strategies

**What to Cache**:

```python
class EventCapBridge:
    """Bridge with caching for expensive calculations."""

    def __init__(self, database_path: str):
        self.database_path = database_path
        self.tag_manager = TagManager(database_path)
        self.contract_manager = ContractManager(database_path)

        # Cache for expensive calculations
        self._position_salary_cache = {}  # Cache top 5/10 salaries by position
        self._team_cap_cache = {}  # Cache team cap space (invalidate on transaction)

    def get_position_top_salaries(
        self,
        position: str,
        season: int,
        dynasty_id: str,
        top_n: int = 5
    ) -> List[int]:
        """Get top N salaries for position (with caching)."""

        cache_key = (position, season, dynasty_id, top_n)

        if cache_key in self._position_salary_cache:
            return self._position_salary_cache[cache_key]

        # Calculate if not cached
        salaries = self.tag_manager._get_top_position_salaries(
            position, season, dynasty_id, top_n
        )

        # Cache result
        self._position_salary_cache[cache_key] = salaries

        return salaries

    def invalidate_team_cap_cache(self, team_id: int, season: int, dynasty_id: str):
        """Invalidate cached cap space after transaction."""
        cache_key = (team_id, season, dynasty_id)
        if cache_key in self._team_cap_cache:
            del self._team_cap_cache[cache_key]
```

**When to Cache**:
- Position average salaries (rarely change within season)
- League cap limits (static per season)

**When NOT to Cache**:
- Team cap space (changes with every transaction)
- Contract details (can be modified)
- Dead money (changes with releases)

---

## Future Enhancements

### Planned Features (Post-MVP)

1. **AI Cap Management Integration**
   - Automatic cap compliance for AI teams
   - Smart restructuring recommendations
   - Cap-aware free agency bidding

2. **User UI Integration**
   - Interactive cap dashboard
   - Contract negotiation simulator
   - Dead money calculator tool
   - Restructure wizard

3. **Historical Analytics**
   - Cap space trends over time
   - Team spending patterns
   - Position value analysis

4. **What-If Scenarios**
   - Simulate contract signings without committing
   - Compare multiple restructure options
   - Forecast multi-year cap impact

---

### Extension Points

**Adding New Event Types**:

```python
# 1. Create new event class
class ContractExtensionEvent(BaseEvent):
    """Event for extending existing contracts."""

    def simulate(self) -> EventResult:
        bridge = EventCapBridge(self.database_path)
        handler = ContractEventHandler(bridge)
        result = handler.handle_contract_extension(self.event_data)
        # ... convert to EventResult

# 2. Add handler method
class ContractEventHandler:
    def handle_contract_extension(self, event_data: Dict) -> Dict:
        """Process contract extension."""
        # Business logic here
        return {"success": True, ...}

# 3. Update SimulationExecutor
def _reconstruct_event(self, event_data: Dict) -> BaseEvent:
    if event_type == "CONTRACT_EXTENSION":
        return ContractExtensionEvent(**parameters)
```

**Adding New Validation Rules**:

```python
class ValidationMiddleware:
    @staticmethod
    def validate_contract_extension(
        contract_id: int,
        extension_years: int,
        cap_validator: CapValidator
    ) -> Tuple[bool, Optional[str]]:
        """Validate contract extension rules."""

        # Example rule: Can't extend contracts with more than 2 years remaining
        contract = cap_validator.get_contract(contract_id)
        remaining_years = contract["end_year"] - contract["current_year"]

        if remaining_years > 2:
            return (False, "Cannot extend contract with more than 2 years remaining")

        return (True, None)
```

---

## Troubleshooting

### Common Issues and Solutions

#### Issue: "Insufficient cap space" error but team appears under cap

**Possible Causes**:
1. Top-51 vs 53-man roster accounting mode mismatch
2. Dead money not included in calculation
3. LTBE incentives not counted

**Solution**:
```python
# Check full cap breakdown
cap_validator = CapValidator()
report = cap_validator.generate_compliance_report(
    team_id=7,
    season=2025,
    dynasty_id="my_dynasty"
)

print(f"Cap limit: ${report['cap_summary']['salary_cap_limit']:,}")
print(f"Active contracts: ${report['cap_summary']['active_contracts_total']:,}")
print(f"Dead money: ${report['cap_summary']['dead_money_total']:,}")
print(f"LTBE incentives: ${report['cap_summary']['ltbe_incentives_total']:,}")
print(f"Total used: ${report['cap_summary']['total_cap_used']:,}")
print(f"Available: ${report['cap_space']:,}")
```

---

#### Issue: Franchise tag fails with "Team already used franchise tag"

**Possible Cause**: Team applied franchise tag earlier in same season

**Solution**:
```python
# Check existing tags
db_api = CapDatabaseAPI()
tags = db_api.get_team_franchise_tags(
    team_id=7,
    season=2025,
    dynasty_id="my_dynasty"
)

if tags:
    print(f"Team has already tagged player: {tags[0]['player_id']}")
    print(f"Tag type: {tags[0]['tag_type']}")
    print(f"Tag salary: ${tags[0]['tag_salary']:,}")
else:
    print("No existing franchise tags found")
```

---

#### Issue: Dynasty isolation not working (seeing other dynasty's data)

**Possible Cause**: `dynasty_id` not being passed through all layers

**Solution**:
```python
# Verify dynasty_id propagation
event = FranchiseTagEvent(
    team_id=7,
    player_id="P_QB_001",
    # ... other params
    dynasty_id="correct_dynasty_id"  # Ensure this is set!
)

# Check event data includes dynasty_id
assert event.dynasty_id == "correct_dynasty_id"

# Verify handler receives dynasty_id
event_data = event._build_event_data()
assert event_data["dynasty_id"] == "correct_dynasty_id"
```

---

### Debugging Tips

**Enable Detailed Logging**:

```python
import logging

# Enable debug logging for cap system
logging.basicConfig(level=logging.DEBUG)

cap_logger = logging.getLogger("salary_cap")
cap_logger.setLevel(logging.DEBUG)

# Now all cap operations will log details
bridge = EventCapBridge()
result = bridge.execute_franchise_tag(...)  # Will log each step
```

**Check Database State**:

```python
# Verify database records after event execution
db_api = CapDatabaseAPI()

# Check franchise tags
tags = db_api.execute_query(
    "SELECT * FROM franchise_tags WHERE dynasty_id = ? AND season = ?",
    ("my_dynasty", 2025)
)
print(f"Franchise tags: {tags}")

# Check contracts
contracts = db_api.execute_query(
    "SELECT * FROM player_contracts WHERE dynasty_id = ? AND is_active = TRUE",
    ("my_dynasty",)
)
print(f"Active contracts: {len(contracts)}")

# Check cap transactions
transactions = db_api.execute_query(
    "SELECT * FROM cap_transactions WHERE dynasty_id = ? ORDER BY transaction_date DESC LIMIT 10",
    ("my_dynasty",)
)
print(f"Recent transactions: {transactions}")
```

---

## References

**Related Documentation**:
- [Salary Cap System Plan](/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/docs/plans/salary_cap_plan.md) - Full salary cap implementation plan
- [Offseason Plan](/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/docs/plans/offseason_plan.md) - Complete offseason system architecture
- [Offseason Event System](/Users/fudong/Library/CloudStorage/OneDrive-Personal/1.Projects/the-owners-sim/docs/architecture/offseason_event_system.md) - Event infrastructure documentation

**API Documentation** (when created):
- `docs/api/event_cap_bridge_api.md` - Complete EventCapBridge API reference
- `docs/api/event_handlers_api.md` - Handler class documentation
- `docs/api/validation_middleware_api.md` - Validation rules reference

**Code References**:
- `src/salary_cap/event_cap_bridge.py` - Main bridge implementation
- `src/salary_cap/event_handlers/` - All handler classes
- `src/salary_cap/validation_middleware.py` - Validation logic
- `src/events/contract_events.py` - Contract event classes
- `src/events/free_agency_events.py` - Free agency event classes

---

**Document Version History**:
- **v1.0.0** (October 4, 2025): Initial comprehensive architecture documentation
