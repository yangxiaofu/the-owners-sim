# UI Tests - NFL Draft Event Integration

Comprehensive testing infrastructure for the NFL Draft Event UI integration.

---

## Quick Start

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

### Run Standalone Manual Test
```bash
python test_draft_dialog_standalone.py --dynasty my_dynasty --season 2025 --team 7
```

---

## Test Files

### test_draft_controller.py
**Purpose**: Unit tests for DraftDemoController business logic

**Test Count**: 30 tests (25 implemented, 5 TODO)

**Coverage**:
- Controller initialization and validation
- Draft order loading and tracking
- Available prospects retrieval
- Team needs analysis
- User pick execution with validation
- AI pick execution with needs-based evaluation
- Pick history tracking
- Draft progress monitoring
- Dynasty isolation

**Key Tests**:
- `test_controller_initialization` - Verify all dependencies
- `test_execute_pick_user_team` - User pick flow
- `test_execute_pick_ai_team` - AI pick with needs evaluation
- `test_get_available_prospects` - Prospect retrieval and sorting
- `test_dynasty_isolation` - Dynasty separation

**Status**: ✅ Ready to run

---

### test_draft_dialog_integration.py
**Purpose**: Integration tests for DraftDayDialog UI

**Test Count**: 17 tests (2 implemented, 15 TODO)

**Coverage**:
- Dialog-controller integration
- UI data loading and display
- Pick execution through UI
- Signal emissions
- State persistence
- Error handling
- Auto-simulation

**Key Tests**:
- `test_dialog_controller_integration` - Dialog initialization
- `test_dialog_opens_with_data` - Data loading
- `test_pick_execution_flow` - Complete pick workflow
- `test_auto_sim_to_user_pick` - Auto-simulation

**Status**: 🔲 Pending dialog UI implementation

---

### conftest.py
**Purpose**: Shared pytest fixtures for all UI tests

**Fixtures**:
- `mock_database_path` - In-memory database
- `mock_dynasty_id` - Test dynasty ID
- `mock_season` - Test season (2025)
- `mock_user_team_id` - User team (Detroit Lions)
- `sample_draft_class` - 20 realistic prospects
- `sample_draft_order_round_1` - Round 1 (32 picks)
- `sample_draft_order_full` - All 7 rounds (224 picks)
- `mock_draft_manager` - DraftManager mock
- `sample_team_needs` - Team needs data

**Usage**:
```python
def test_example(sample_draft_class, mock_dynasty_id):
    assert len(sample_draft_class) == 20
    assert mock_dynasty_id == "test_dynasty_draft"
```

---

## Test Data

### fixtures/sample_draft_class.json
20 realistic NFL prospects with complete attributes:
- Positions: QB (3), WR (4), CB (3), EDGE (3), OT (3), RB (2), TE (2)
- Attributes: overall, speed, strength, awareness, position-specific
- Draft projections: min/max pick ranges
- College and physical data

**Usage**:
```python
import json
with open('tests/ui/fixtures/sample_draft_class.json') as f:
    prospects = json.load(f)
```

### fixtures/sample_draft_order_round1.json
32 first-round picks with team assignments:
- Complete pick metadata (round, pick number, overall pick)
- Team IDs and team names
- Realistic draft order (worst to best record)

**Usage**:
```python
import json
with open('tests/ui/fixtures/sample_draft_order_round1.json') as f:
    draft_order = json.load(f)
```

---

## Standalone Testing

### test_draft_dialog_standalone.py
Manual testing script for real database testing.

**Features**:
- Command-line arguments for configuration
- Database validation and error handling
- Launches dialog with real data
- Comprehensive testing instructions

**Usage**:
```bash
# Default settings (Detroit Lions, 2025)
python test_draft_dialog_standalone.py

# Custom settings
python test_draft_dialog_standalone.py \
  --db data/database/nfl_simulation.db \
  --dynasty my_dynasty \
  --season 2025 \
  --team 7

# Help
python test_draft_dialog_standalone.py --help
```

**Prerequisites**:
1. Database must exist
2. Draft class must be generated
3. Draft order must exist

Run setup if needed:
```bash
python demo/draft_day_demo/setup_draft_data.py
```

---

## Test Coverage

### Current Status
- **Controller Unit Tests**: 25/30 implemented (83%)
- **Integration Tests**: 2/17 implemented (12%)
- **Fixtures**: 10/10 complete (100%)
- **Test Data**: 2/2 complete (100%)
- **Documentation**: 100% complete

### Coverage Goals
- Controller: 95%+ code coverage
- Integration: 80%+ workflow coverage
- Manual: 100% checklist completion

---

## Best Practices

### Writing Tests
1. **Use fixtures** - Don't duplicate setup code
2. **Mock external dependencies** - Never touch real database in unit tests
3. **Clear test names** - Name tests `test_what_is_being_tested`
4. **One assertion per test** - Keep tests focused
5. **Document TODOs** - Explain why test is pending

### Running Tests
1. **Run frequently** - Test as you develop
2. **Use verbose mode** - See test names and results
3. **Check coverage** - Aim for 95%+ on new code
4. **Fix failures immediately** - Don't let tests stay red

### Test Isolation
1. **No shared state** - Each test independent
2. **No database** - Use mocks for unit tests
3. **No network** - Mock all external calls
4. **No file I/O** - Use in-memory data

---

## Common Commands

### Run Tests
```bash
# All UI tests
python -m pytest tests/ui/ -v

# Specific test file
python -m pytest tests/ui/test_draft_controller.py -v

# Specific test function
python -m pytest tests/ui/test_draft_controller.py::test_controller_initialization -v

# With coverage
python -m pytest tests/ui/ --cov=draft_demo_controller --cov=draft_day_dialog --cov-report=html

# Only failed tests
python -m pytest tests/ui/ --lf

# Stop on first failure
python -m pytest tests/ui/ -x
```

### Test Discovery
```bash
# List all tests without running
python -m pytest tests/ui/ --collect-only

# Show available fixtures
python -m pytest tests/ui/ --fixtures
```

### Debugging
```bash
# Show print statements
python -m pytest tests/ui/ -s

# Drop into debugger on failure
python -m pytest tests/ui/ --pdb

# Show full traceback
python -m pytest tests/ui/ --tb=long
```

---

## Troubleshooting

### Import Errors
```bash
# Ensure paths are set up
export PYTHONPATH=$PYTHONPATH:$(pwd)/src
export PYTHONPATH=$PYTHONPATH:$(pwd)/demo/draft_day_demo

# Or use pytest from project root
cd /path/to/the-owners-sim
python -m pytest tests/ui/ -v
```

### Mock Issues
If mocks aren't working:
1. Check patch paths match import locations
2. Verify mock is applied before function call
3. Use `return_value` for simple returns
4. Use `side_effect` for complex behavior

### Qt Issues
If Qt tests fail:
1. Ensure PySide6 is installed
2. Check QApplication is created (see `qapp` fixture)
3. Use `QTest.qWait()` for timing-dependent tests
4. Run with `--no-qt-log` to reduce Qt warnings

---

## Documentation

### Full Documentation
- **Test Plan**: `docs/project/nfl_draft_event/test_plan.md`
- **Completion Summary**: `docs/project/nfl_draft_event/PHASE_2_TEST_INFRASTRUCTURE_COMPLETE.md`
- **This README**: `tests/ui/README.md`

### Test Documentation
Each test file includes:
- Module docstring with overview
- Test function docstrings
- TODO markers for pending tests
- Type hints where applicable

---

## Next Steps

### For Developers
1. Run controller unit tests
2. Fix any failing tests
3. Implement TODO tests as features are added
4. Maintain 95%+ code coverage

### For QA
1. Execute manual testing checklist
2. Run all automated tests
3. Generate coverage reports
4. Document bugs found

### For Integration
1. Complete draft dialog UI
2. Implement integration test TODOs
3. Add signal emissions
4. Test end-to-end workflows

---

## Support

### Questions?
- Check test plan: `docs/project/nfl_draft_event/test_plan.md`
- Review conftest.py for available fixtures
- Look at existing tests for examples
- Run with `-v` for verbose output

### Found a Bug?
1. Write a failing test first
2. Fix the bug
3. Verify test now passes
4. Document in test plan if needed

---

**Last Updated**: 2025-11-23
**Test Infrastructure Version**: 1.0
**Status**: ✅ Complete and Ready
