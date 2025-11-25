# NFL Draft Event UI Integration - Test Plan

**Phase**: Phase 2 - Draft Controller and Dialog Integration
**Created**: 2025-11-23
**Status**: Test Infrastructure Complete

---

## Test Infrastructure

### Automated Test Files

1. **`tests/ui/test_draft_controller.py`** - Controller Unit Tests
   - 30+ test function signatures scaffolded
   - Comprehensive mock fixtures for all dependencies
   - Tests initialization, pick execution, dynasty isolation, error handling

2. **`tests/ui/test_draft_dialog_integration.py`** - Integration Tests
   - Dialog-controller integration testing
   - UI interaction and signal emission tests
   - State persistence and error handling tests

3. **`tests/ui/conftest.py`** - Shared Pytest Fixtures
   - Mock database fixtures
   - Sample draft class data (20 prospects)
   - Sample draft order data (round 1 + full 7 rounds)
   - Mock DraftManager with realistic behavior
   - Sample team needs data

### Test Data Files

Located in `tests/ui/fixtures/`:

1. **`sample_draft_class.json`** - 20 realistic prospects
   - 3 QBs, 4 WRs, 3 CBs, 3 EDGEs, 3 OTs, 2 RBs, 2 TEs
   - Complete attributes (overall, speed, strength, awareness, position-specific)
   - Projected draft ranges for each prospect

2. **`sample_draft_order_round1.json`** - First round draft order
   - All 32 picks with team names
   - Realistic team order based on reverse standings

### Standalone Testing

**`test_draft_dialog_standalone.py`** - Manual Testing Script
- Launches dialog with real database
- Command-line arguments for database path, dynasty, season, team
- Database validation and helpful error messages
- Comprehensive manual testing instructions

---

## Test Coverage

### Controller Unit Tests (30 Tests)

#### Initialization (3 tests)
- ✅ `test_controller_initialization` - Verify all dependencies injected
- ✅ `test_controller_initialization_missing_draft_class` - Error handling
- ✅ `test_controller_initialization_missing_draft_order` - Error handling

#### Draft Order Management (3 tests)
- 🔲 `test_load_draft_order` - Load complete draft order from database
- ✅ `test_get_current_pick` - Get current pick information
- ✅ `test_get_current_pick_draft_complete` - Handle draft completion
- ✅ `test_is_user_pick` - Detect user vs AI pick

#### Prospects Retrieval (2 tests)
- ✅ `test_get_available_prospects` - Get available prospects sorted by overall
- ✅ `test_get_available_prospects_respects_limit` - Limit parameter works

#### Team Needs (1 test)
- ✅ `test_get_team_needs` - Retrieve team needs by urgency

#### User Pick Execution (5 tests)
- ✅ `test_execute_pick_user_team` - Execute user pick successfully
- ✅ `test_execute_pick_not_user_team` - Error when not user's pick
- ✅ `test_execute_pick_draft_complete` - Error when draft complete
- ✅ `test_execute_pick_invalid_player` - Error for invalid player ID
- ✅ `test_execute_pick_already_drafted_player` - Error for already drafted

#### AI Pick Execution (3 tests)
- ✅ `test_execute_pick_ai_team` - Execute AI pick with needs evaluation
- ✅ `test_execute_pick_ai_current_pick_is_user` - Error when user's pick
- ✅ `test_execute_pick_ai_no_prospects` - Error when no prospects available

#### Pick History (3 tests)
- 🔲 `test_simulate_next_pick` - Simulate single pick (user or AI)
- ✅ `test_get_pick_history` - Retrieve pick history in reverse order
- ✅ `test_get_pick_history_respects_limit` - Limit parameter works

#### Draft Progress (3 tests)
- 🔲 `test_save_draft_progress` - Save draft state to database
- ✅ `test_get_draft_progress` - Get draft statistics
- ✅ `test_is_draft_complete` - Detect draft completion

#### Error Handling (1 test)
- 🔲 `test_error_handling_invalid_pick` - General error handling

#### Dynasty Isolation (1 test)
- ✅ `test_dynasty_isolation` - Verify dynasty_id passed to all APIs

**Status**: 25/30 tests implemented, 5 marked TODO

---

### Integration Tests (15+ Tests)

#### Dialog Initialization (2 tests)
- ✅ `test_dialog_controller_integration` - Dialog stores controller reference
- ✅ `test_dialog_opens_with_data` - Data loads on dialog open

#### Pick Execution Flow (3 tests)
- 🔲 `test_pick_execution_flow` - Complete pick flow (select + execute)
- 🔲 `test_user_pick_execution` - User pick through UI
- 🔲 `test_ai_pick_execution` - AI pick through UI

#### Signal Emissions (1 test)
- 🔲 `test_dialog_signals` - Verify signal emissions (pick_made, draft_complete)

#### State Persistence (1 test)
- 🔲 `test_close_event_saves_state` - Close event saves draft state

#### Error Handling (2 tests)
- 🔲 `test_invalid_pick_error_handling` - UI handles pick errors gracefully
- 🔲 `test_controller_error_handling` - UI handles controller errors gracefully

#### Full Integration (6 tests)
- 🔲 `test_complete_round_simulation` - Simulate full round (32 picks)
- 🔲 `test_draft_completion_flow` - Handle draft completion UI state
- 🔲 `test_prospects_table_sorting` - Table sorting by columns
- 🔲 `test_prospects_table_selection` - Selection enables/disables buttons
- 🔲 `test_team_needs_display_updates` - Needs update on pick change
- 🔲 `test_pick_history_display_updates` - History updates after picks

#### Auto-Simulation (2 tests)
- 🔲 `test_auto_sim_to_user_pick` - Auto-sim stops at user pick
- 🔲 `test_auto_sim_complete_round` - Auto-sim complete round

**Status**: 2/15 tests implemented, 13 marked TODO

---

## Manual Testing Checklist

Use `test_draft_dialog_standalone.py` for manual testing:

### Pre-Flight Checks
- [ ] Database exists with draft class and draft order
- [ ] Run `python demo/draft_day_demo/setup_draft_data.py` if needed
- [ ] Launch standalone script successfully

### UI Display
- [ ] Dialog opens with correct title (dynasty + season)
- [ ] Current pick label shows correct information
- [ ] User team label displays correctly
- [ ] Prospects table loads with data
- [ ] Team needs list populates
- [ ] Pick history table exists (empty initially)
- [ ] Buttons are visible and properly styled

### Prospects Table
- [ ] All 20+ prospects displayed
- [ ] Columns: Name, Pos, Overall, College, Age, Speed, Str, Awa
- [ ] Click column headers to sort (ascending/descending)
- [ ] Sort by Overall works correctly
- [ ] Sort by Position works correctly
- [ ] Sort by College works correctly
- [ ] Numeric sorting works (not alphabetic)
- [ ] Selected row highlights properly

### Team Needs Display
- [ ] Shows needs for current pick's team
- [ ] Updates when pick advances to new team
- [ ] Displays urgency level (CRITICAL, HIGH, MEDIUM, LOW)
- [ ] Shows position and reason

### User Pick Execution
- [ ] Wait for user's pick (pick #7 for Detroit if default)
- [ ] "Make Pick" button enables when user's turn
- [ ] Select prospect in table
- [ ] Click "Make Pick" button
- [ ] Confirmation dialog appears (if implemented)
- [ ] Pick executes successfully
- [ ] Current pick advances to next pick
- [ ] Prospects table updates (drafted player removed)
- [ ] Pick appears in history table

### AI Pick Execution
- [ ] "Make Pick" button disabled when AI's turn
- [ ] Click "Simulate Next Pick" button
- [ ] AI pick executes with needs-based evaluation
- [ ] Console shows AI pick reasoning
- [ ] Current pick advances
- [ ] Prospects table updates
- [ ] Pick appears in history table

### Pick History
- [ ] History table shows most recent picks (15 max)
- [ ] Columns: Rd, Pick, Team, Player, Pos, Overall, College
- [ ] Most recent pick at top
- [ ] Updates after each pick
- [ ] Scrolls properly if > 15 picks

### Auto-Simulation
- [ ] Click "Auto-Sim to My Pick" button
- [ ] Simulation runs automatically
- [ ] Stops at user's next pick
- [ ] All AI picks appear in history
- [ ] Prospects table updated correctly
- [ ] Can manually make pick when stopped

### Draft Progress
- [ ] Progress label shows picks completed/remaining
- [ ] Completion percentage updates
- [ ] Current round number correct
- [ ] Progress bar updates (if implemented)

### Draft Completion
- [ ] Simulate all 224 picks to completion
- [ ] Completion dialog appears
- [ ] Buttons disabled after completion
- [ ] Can still review pick history
- [ ] Can close dialog normally

### Error Handling
- [ ] Try to pick when not user's turn → error message
- [ ] Try to pick already drafted player → error message
- [ ] Try to pick with no selection → error message
- [ ] Database errors handled gracefully
- [ ] All errors show user-friendly messages

### Close Event
- [ ] Click "X" to close dialog
- [ ] Draft state saves to database (if implemented)
- [ ] Can reopen dialog and resume draft
- [ ] Dialog closes cleanly without errors

---

## Success Criteria

### Phase 2 Complete When:

1. **All Controller Unit Tests Pass** (30/30)
   - All test functions implemented (not TODO)
   - All assertions passing
   - 100% controller functionality covered

2. **All Integration Tests Pass** (15/15)
   - Dialog-controller integration working
   - UI interactions functional
   - Signal emissions verified
   - State persistence working

3. **Manual Testing Checklist 100% Complete**
   - All 50+ checklist items verified
   - No critical bugs discovered
   - User experience smooth and intuitive

4. **Code Quality Standards Met**
   - All tests follow pytest best practices
   - Proper mock isolation (no real database in unit tests)
   - Clear test names and documentation
   - Fixtures reusable and maintainable

5. **Documentation Complete**
   - Test plan finalized (this document)
   - README updated with testing instructions
   - Known issues documented
   - Test coverage report generated

---

## Testing Commands

### Run All UI Tests
```bash
python -m pytest tests/ui/ -v
```

### Run Controller Tests Only
```bash
python -m pytest tests/ui/test_draft_controller.py -v
```

### Run Integration Tests Only
```bash
python -m pytest tests/ui/test_draft_dialog_integration.py -v
```

### Run Specific Test
```bash
python -m pytest tests/ui/test_draft_controller.py::test_controller_initialization -v
```

### Run Tests with Coverage
```bash
python -m pytest tests/ui/ --cov=draft_demo_controller --cov=draft_day_dialog --cov-report=html
```

### Run Standalone Manual Test
```bash
# Default settings
python test_draft_dialog_standalone.py

# Custom settings
python test_draft_dialog_standalone.py --db data/database/nfl_simulation.db --dynasty my_dynasty --season 2025 --team 7
```

---

## Test Data Management

### Mock Data (Unit Tests)
- Uses `conftest.py` fixtures
- No database required
- Fast execution
- Completely isolated

### Sample JSON Data (Integration Tests)
- Uses `tests/ui/fixtures/*.json` files
- Realistic but static data
- Good for UI testing
- Can be version controlled

### Real Database (Manual Tests)
- Uses actual game database
- Requires setup script
- Full end-to-end validation
- Slower but most realistic

---

## Known Issues & Limitations

### Current Test Limitations
1. **Integration tests mostly TODO** - Need UI implementation complete first
2. **Qt testing complexity** - Some UI interactions hard to automate
3. **Signal testing** - Requires dialog signals to be defined first
4. **Auto-sim testing** - Timing-dependent, may need QTest.qWait()

### Testing Best Practices
1. **Always use mocks for unit tests** - Never touch real database
2. **Isolate test cases** - Each test should be independent
3. **Use descriptive test names** - Clear what's being tested
4. **Document TODO tests** - Note why implementation is pending
5. **Keep fixtures reusable** - DRY principle for test data

---

## Next Steps

### Immediate (Phase 2)
1. ✅ Complete test infrastructure setup (DONE)
2. 🔲 Implement remaining controller unit tests (5 TODO)
3. 🔲 Complete draft dialog UI implementation
4. 🔲 Implement integration tests (13 TODO)
5. 🔲 Run manual testing checklist
6. 🔲 Fix any bugs discovered
7. 🔲 Generate test coverage report

### Phase 3 (Future)
1. UI controller integration tests
2. Main window integration tests
3. End-to-end simulation tests
4. Performance testing
5. Load testing (multiple dynasties)

---

## Test Metrics

### Coverage Goals
- **Controller Unit Tests**: 95%+ code coverage
- **Integration Tests**: 80%+ workflow coverage
- **Manual Tests**: 100% checklist completion

### Success Metrics
- All automated tests passing
- No critical bugs in manual testing
- Test execution time < 5 seconds for unit tests
- Test execution time < 30 seconds for integration tests
- Code review approved
- Documentation complete

---

## Appendix

### Test File Locations
```
tests/ui/
├── conftest.py                          # Shared fixtures
├── test_draft_controller.py             # Controller unit tests (30 tests)
├── test_draft_dialog_integration.py     # Integration tests (15 tests)
└── fixtures/
    ├── sample_draft_class.json          # 20 prospects
    └── sample_draft_order_round1.json   # Round 1 picks

test_draft_dialog_standalone.py          # Manual testing script

docs/project/nfl_draft_event/
└── test_plan.md                         # This document
```

### Fixture Summary
- `mock_database_path` - Memory database path
- `mock_dynasty_id` - Test dynasty ID
- `mock_season` - Test season (2025)
- `mock_user_team_id` - User team (7 = Detroit)
- `sample_draft_class` - 20 realistic prospects
- `sample_draft_order_round_1` - First round (32 picks)
- `sample_draft_order_full` - All 7 rounds (224 picks)
- `mock_draft_manager` - Mocked DraftManager
- `sample_team_needs` - Team needs for testing

---

**Document Version**: 1.0
**Last Updated**: 2025-11-23
**Author**: Testing Infrastructure Specialist
