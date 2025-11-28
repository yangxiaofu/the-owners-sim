# Tollgate 5: Re-signing Stage Implementation

**Status**: ✅ COMPLETE (Nov 25, 2025)
**Certainty**: 90%

## Summary

Implemented the Re-signing stage of the game_cycle offseason where users view expiring contracts and decide which players to re-sign vs. release to free agency.

## Scope

**In Scope (Tollgate 5):**
- ✅ User views expiring contracts in ResigningView (UI was already complete)
- ✅ User marks players as "Re-sign" or "Let Go"
- ✅ AI teams process their re-signing decisions on stage advance
- ✅ Released players become free agents (team_id = 0)
- ✅ Re-signed players get new contracts (via MarketValueCalculator)

**Out of Scope (Future Tollgates):**
- Free agency signing (Tollgate 5b)
- Contract negotiation terms
- Franchise tags

---

## Implementation

### New Files Created

| File | Purpose |
|------|---------|
| `src/game_cycle/services/__init__.py` | Package init |
| `src/game_cycle/services/resigning_service.py` | Re-signing business logic with MarketValueCalculator |

### Files Modified

| File | Changes |
|------|---------|
| `src/game_cycle/handlers/offseason.py` | Implemented `_execute_resigning()` with user + AI processing |
| `src/game_cycle/stage_controller.py` | Added `extra_context` parameter for user decisions |
| `game_cycle_ui/controllers/stage_controller.py` | Added `user_team_id`, decision tracking, `set_offseason_view()` |
| `game_cycle_ui/main_window.py` | Connected offseason view signals to stage controller |

---

## Architecture

### Data Flow

```
User clicks "Re-sign" or "Let Go" in ResigningView
    ↓
Signal emits player_id to StageUIController
    ↓
StageUIController stores decision in _user_decisions dict
    ↓
User clicks "Process Re-signing" button
    ↓
StageUIController._on_process_offseason_stage()
    ↓
Backend StageController.execute_current_stage(extra_context={user_decisions: {...}})
    ↓
OffseasonHandler._execute_resigning()
    ↓
ResigningService processes user decisions + AI teams
    ↓
Database updated: contracts created/voided, players moved to FA pool
```

### Key Components

**ResigningService** (`src/game_cycle/services/resigning_service.py`):
- `get_expiring_contracts(team_id)` - Gets players with contracts expiring this season
- `resign_player(player_id, team_id)` - Creates new market-value contract
- `release_player(player_id, team_id)` - Voids contract, sets team_id=0
- `process_ai_resignings(user_team_id)` - AI teams make decisions
- `_should_ai_resign(player)` - Simple algorithm based on overall/age/position

**AI Decision Algorithm**:
- Overall >= 85: Always re-sign (unless age >= 35)
- Age >= 32 AND overall < 80: Release
- Age >= 34: Release unless elite
- Overall >= 75: Re-sign
- Premium positions (QB, LT, DE, CB, WR): Re-sign if >= 68 OVR
- Default: Re-sign if >= 70 OVR

---

## Testing

### Manual Test Steps

1. `python main2.py`
2. Create or select dynasty
3. Click "Jump to Offseason" in toolbar
4. Verify you land on "Re-signing Period" stage
5. View expiring contracts table
6. Click "Re-sign" or "Let Go" for each player
7. Click "Process Re-signing"
8. Verify:
   - User decisions processed (console output)
   - AI teams process their re-signings
   - Summary shown in UI
   - Stage advances to "Free Agency"

### Verification Queries

```sql
-- Check free agents (team_id = 0)
SELECT p.first_name, p.last_name, p.team_id
FROM players p
WHERE p.dynasty_id='your_dynasty' AND p.team_id = 0;

-- Check new contracts created
SELECT * FROM player_contracts
WHERE dynasty_id='your_dynasty'
AND contract_type='VETERAN'
ORDER BY contract_id DESC LIMIT 10;
```

---

## Dependencies

**APIs Used:**
- `CapDatabaseAPI.get_team_contracts()` - Get contracts
- `CapDatabaseAPI.get_player_contract()` - Get specific contract
- `CapDatabaseAPI.void_contract()` - Deactivate contract
- `ContractManager.create_contract()` - Create new contract
- `PlayerRosterAPI.get_player_by_id()` - Get player info
- `PlayerRosterAPI.update_player_team()` - Move to FA pool
- `MarketValueCalculator.calculate_player_value()` - Auto-generate contract terms
- `TeamDataLoader.get_all_teams()` - Iterate all 32 teams

---

## Next Steps (Tollgate 5b - Free Agency)

1. Implement `_execute_free_agency()` in offseason handler
2. Create `FreeAgencyService` for FA pool management
3. Build FA signing UI (table of available FAs, bid interface)
4. AI teams sign FAs based on team needs
5. User team can browse and sign FAs