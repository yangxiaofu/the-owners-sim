# Milestone: Free Agency Depth

> **Status:** 🔄 In Progress (Tollgates 1-5 Complete, 165 tests)
> **Dependencies:** Player Personas (done), Salary Cap (done)

## Overview

Transform the current monolithic free agency stage into a **5-wave system** with realistic offer/decision windows, surprise signings, and database persistence.

## Status

| Tollgate | Description | Status |
|----------|-------------|--------|
| 1 | Database Schema | ✅ Complete (41 tests) |
| 2 | FA Wave Service | ✅ Complete (32 tests) |
| 3 | Offer System Integration | ✅ Complete (28 tests) |
| 4 | UI Controller Integration | ✅ Complete (31 tests) |
| 5 | UI Wave Display | ✅ Complete (33 tests) |
| 6 | Offer Dialog | Not Started |
| 7 | Integration Testing | Not Started |

**Total Tests:** 165 passing

---

## Tollgate 1: Database Schema (Foundation)

**Goal**: Add `pending_offers` and `fa_wave_state` tables

### Deliverables

- [x] Add `pending_offers` table to `schema.sql`
- [x] Add `fa_wave_state` table to `schema.sql`
- [x] Create `PendingOffersAPI` class (16 tests)
- [x] Create `FAWaveStateAPI` class (25 tests)
- [x] Write unit tests (41 total)

### Schema - pending_offers

```sql
CREATE TABLE IF NOT EXISTS pending_offers (
    offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    wave INTEGER NOT NULL CHECK(wave BETWEEN 0 AND 4),
    player_id INTEGER NOT NULL,
    offering_team_id INTEGER NOT NULL,
    aav INTEGER NOT NULL,
    total_value INTEGER NOT NULL,
    years INTEGER NOT NULL,
    guaranteed INTEGER NOT NULL,
    signing_bonus INTEGER DEFAULT 0,
    decision_deadline INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    UNIQUE(dynasty_id, season, wave, player_id, offering_team_id)
);
```

### Schema - fa_wave_state

```sql
CREATE TABLE IF NOT EXISTS fa_wave_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dynasty_id TEXT NOT NULL,
    season INTEGER NOT NULL,
    current_wave INTEGER DEFAULT 0,
    current_day INTEGER DEFAULT 1,
    wave_complete INTEGER DEFAULT 0,
    post_draft_available INTEGER DEFAULT 0,
    UNIQUE(dynasty_id, season)
);
```

---

## Tollgate 2: FA Wave Service (Core Logic)

**Goal**: Create `FAWaveService` to manage wave progression and offer lifecycle

**File**: `src/game_cycle/services/fa_wave_service.py`

### Deliverables

- [x] Create FAWaveService class with constructor pattern
- [x] Implement wave state management (get, advance)
- [x] Implement player tier filtering by OVR
- [x] Implement offer submission with validation
- [x] Implement offer withdrawal
- [x] Implement AI offer generation per wave
- [x] Implement surprise signing logic (20% probability)
- [x] Implement offer resolution using PreferenceEngine
- [x] Write unit tests (32 tests)

### Wave Configuration

| Wave | Name | OVR Range | Days | Signing Allowed |
|------|------|-----------|------|-----------------|
| 0 | Legal Tampering | All | 1 | No |
| 1 | Wave 1 - Elite | 85+ | 3 | Yes |
| 2 | Wave 2 - Quality | 75-84 | 2 | Yes |
| 3 | Wave 3 - Depth | 65-74 | 2 | Yes |
| 4 | Post-Draft | All | 1 | Yes |

### Key Methods

- `get_current_wave_state()` → Dict with wave, day, totals
- `advance_day()` → Process day, check wave completion
- `advance_wave()` → Move to next wave
- `get_available_players_for_wave(wave)` → Filter by OVR tier
- `submit_offer(player_id, team_id, aav, years, guaranteed)` → Create pending offer
- `withdraw_offer(offer_id)` → Cancel offer
- `process_day_end(user_team_id)` → AI offers + surprise signings
- `process_wave_end()` → Resolve all pending decisions
- `resolve_player_offers(player_id)` → Use PreferenceEngine to pick winner

---

## Tollgate 3: Offer System Integration

**Goal**: Create testable orchestrator with Separation of Concerns

**File**: `src/game_cycle/services/fa_wave_executor.py`

### Deliverables

- [x] Create FAWaveExecutor orchestrator class with DI
- [x] Create result dataclasses (OfferResult, SigningResult, WaveExecutionResult)
- [x] Implement focused executor methods
- [x] Update OffseasonHandler to use executor (thin wrapper)
- [x] Update can_advance() for FA stage completion check
- [x] Update get_stage_preview() with wave data
- [x] Write unit tests for FAWaveExecutor (28 tests)

### Architecture

```python
# Dependency injection for testability
class FAWaveExecutor:
    def __init__(self, wave_service: "FAWaveService"):  # Inject dependency
        self._wave_service = wave_service

    @classmethod
    def create(cls, db_path, dynasty_id, season):  # Factory for production
        wave_service = FAWaveService(db_path, dynasty_id, season)
        return cls(wave_service)
```

### Result Dataclasses

- `OfferResult` - player_id, outcome (enum), offer_id, error
- `SigningResult` - player_id, player_name, team_id, aav, years, is_surprise
- `WaveExecutionResult` - Complete turn result with all data

### Context Keys (Handler)

- `fa_wave_actions`: Dict with `submit_offers`, `withdraw_offers` lists
- `wave_control`: Dict with `advance_day`, `advance_wave`, `enable_post_draft` bools

---

## Tollgate 4: Stage Handler Updates

**Goal**: Modify `OffseasonHandler` for wave-based progression

**File**: `src/game_cycle/handlers/offseason.py`

### Context Keys

- `process_day`: Advance day, trigger surprises
- `process_wave`: End wave, resolve decisions
- `offer_submission`: User submitting new offer
- `offer_withdrawal`: User withdrawing offer

### Surprise Signing Logic

- 20% chance per day per AI team with pending target
- Only triggers if AI team has offer on same player as user
- Creates realistic uncertainty

---

## Tollgate 5: UI Updates - Wave Display

**Goal**: Update `FreeAgencyView` for wave info and offer status

### New UI Layout

```
+------------------------------------------------------------------+
| FREE AGENCY - Wave 1 (Elite Players)                    Day 2/3  |
| Days Remaining: 1 | Players Available: 47 | Pending Offers: 3    |
+------------------------------------------------------------------+
| Player | Pos | Age | OVR | Est AAV | Interest | Status   | Action |
|--------|-----|-----|-----|---------|----------|----------|--------|
| Star QB| QB  | 29  | 99  | $50M    | 72       | 2 Offers | [Offer]|
+------------------------------------------------------------------+
| [Process Day]                              [Process Wave]         |
+------------------------------------------------------------------+
```

### New Signals

- `offer_submitted(player_id, offer_details)`
- `offer_withdrawn(offer_id)`
- `process_day_requested()`
- `process_wave_requested()`

---

## Tollgate 6: UI Updates - Offer Dialog

**Goal**: Create `OfferDialog` for custom offer submission

**File**: `game_cycle_ui/dialogs/offer_dialog.py`

### UI Elements

- Player header (name, position, overall, age)
- Market value reference display
- AAV slider (70%-150% of market)
- Years slider (1-5)
- Guaranteed % slider (30%-100%)
- Live acceptance probability (updates as values change)
- Cap impact display
- Submit/Cancel buttons

---

## Tollgate 7: Integration Testing

**Goal**: End-to-end testing and edge cases

### Test Scenarios

- Full wave cycle (Legal Tampering → Wave 3)
- Post-draft wave activation
- User wins bidding war
- Surprise signing steals target
- No offers on player (remains FA)
- Money-first persona behavior
- Ring chaser persona behavior
- App restart persistence

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/game_cycle/database/schema.sql` | Add tables (DONE) |
| `src/game_cycle/services/free_agency_service.py` | Add wave offer methods |
| `src/game_cycle/handlers/offseason.py` | Update FA execution |
| `game_cycle_ui/views/free_agency_view.py` | Wave header, buttons |
| `game_cycle_ui/controllers/stage_controller.py` | Wave handlers |
| `game_cycle_ui/dialogs/__init__.py` | Export OfferDialog |

## Files to Create

| File | Purpose |
|------|---------|
| `src/game_cycle/services/fa_wave_service.py` | Wave management |
| `src/game_cycle/database/pending_offers_api.py` | Offers DB API |
| `src/game_cycle/database/fa_wave_state_api.py` | Wave state API |
| `game_cycle_ui/dialogs/offer_dialog.py` | Offer submission |
| `tests/game_cycle/services/test_fa_wave_service.py` | Unit tests |
| `tests/game_cycle/database/test_pending_offers_api.py` | API tests |
| `tests/game_cycle/services/test_fa_wave_integration.py` | Integration tests |
