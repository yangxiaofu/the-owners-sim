# Testing Guide

## Overview

The Owners Sim employs a comprehensive testing strategy combining unit tests, integration tests, performance benchmarks, and interactive validation scripts. This guide covers testing approaches, patterns, and best practices for the simulation system.

## Testing Philosophy

- **Comprehensive Coverage**: Test all critical paths and edge cases
- **Fast Execution**: Tests should run quickly for rapid development
- **Clear Failures**: Test failures should clearly indicate the problem
- **Realistic Scenarios**: Use actual NFL data and scenarios when possible
- **Maintainable Tests**: Keep tests simple and well-documented

## Test Categories

### 1. Unit Tests
Focus on individual components in isolation.

**Location**: `tests/test_*.py`

**Examples**:
- `test_penalty_system.py` - Penalty calculation logic
- `test_field_tracker.py` - Field position tracking
- `test_down_tracker.py` - Down and distance management

**Running Unit Tests**:
```bash
# All unit tests
python -m pytest tests/

# Specific test file
python -m pytest tests/test_game_state_manager.py

# With verbose output
python -m pytest tests/test_game_state_manager.py -v
```

### 2. Integration Tests
Test multiple components working together.

**Location**: `tests/test_*_integration.py`

**Examples**:
- `test_drive_flow_integration.py` - Complete drive simulation
- `test_enhanced_play_call_integration.py` - Play calling system
- `test_game_loop_controller.py` - Full game orchestration

**Running Integration Tests**:
```bash
# Drive integration
python tests/test_drive_flow_integration.py

# Game loop controller
python tests/test_game_loop_controller.py
```

### 3. System Tests
Test complete system functionality end-to-end.

**Location**: `tests/test_*_comprehensive.py`

**Examples**:
- `test_phase_4_comprehensive.py` - Full system validation
- `test_comprehensive_play_execution.py` - All play types

**Running System Tests**:
```bash
# Phase 4 comprehensive
python tests/test_phase_4_comprehensive.py

# With performance metrics
python -m pytest tests/test_phase_4_comprehensive.py --benchmark
```

### 4. Schedule Generator Tests
Test the NFL schedule generation system.

**Location**: `tests/test_scheduling/`

**Test Structure**:
```python
# tests/test_scheduling/test_phase0.py
class TestNFLStructure:
    """Test NFL division structure"""
    
class TestScheduleModels:
    """Test schedule data models"""
    
class TestConfiguration:
    """Test configuration system"""
    
class TestDateUtils:
    """Test date utilities"""
    
class TestIntegration:
    """Integration tests"""
```

**Running Schedule Tests**:
```bash
# All scheduling tests
python -m pytest tests/test_scheduling/

# Phase 0 validation
python -m pytest tests/test_scheduling/test_phase0.py -v
```

### 5. Simulation System Tests
Test the calendar-based simulation infrastructure.

**Location**: `tests/test_result_processing_system.py`

**Test Coverage**:
- Calendar manager operations
- Event scheduling and conflicts
- Result processing strategies
- Season state management

**Running Simulation Tests**:
```bash
# Result processing system
python tests/test_result_processing_system.py

# With coverage report
python -m pytest tests/test_result_processing_system.py --cov=src/simulation
```

### 6. Interactive Validation
Manual testing scripts for validation and debugging.

**Location**: `tests/simple_*.py`

**Examples**:
- `simple_penalty_validation.py` - Interactive penalty testing

**Running Validation Scripts**:
```bash
# Penalty validation
python tests/simple_penalty_validation.py
```

## Testing Patterns

### 1. Fixture Pattern
Use fixtures for common test data:

```python
import pytest
from datetime import datetime

@pytest.fixture
def sample_game():
    """Create a sample game for testing"""
    return ScheduledGame(
        game_id="TEST001",
        week=1,
        game_date=datetime(2024, 9, 8, 13, 0),
        home_team_id=22,
        away_team_id=23,
        time_slot=TimeSlot.SUNDAY_EARLY,
        game_type=GameType.DIVISION
    )

def test_game_creation(sample_game):
    """Test game is created correctly"""
    assert sample_game.week == 1
    assert sample_game.home_team_id == 22
```

### 2. Parametrized Tests
Test multiple scenarios efficiently:

```python
@pytest.mark.parametrize("week,expected_date", [
    (1, date(2024, 9, 8)),
    (2, date(2024, 9, 15)),
    (17, date(2024, 12, 29)),
])
def test_week_to_date(week, expected_date):
    """Test week to date conversion"""
    result = week_to_date(2024, week, GameDay.SUNDAY)
    assert result == expected_date
```

### 3. Mock Pattern
Mock external dependencies:

```python
from unittest.mock import Mock, patch

def test_calendar_loading():
    """Test loading schedule into calendar"""
    mock_calendar = Mock()
    mock_calendar.schedule_event.return_value = (True, "Success")
    
    adapter = ScheduleCalendarAdapter(mock_calendar)
    result = adapter.load_games_list([sample_game])
    
    assert result.successful_games == 1
    mock_calendar.schedule_event.assert_called_once()
```

### 4. Data-Driven Tests
Use real NFL data for realistic testing:

```python
def test_all_nfl_teams():
    """Test all 32 NFL teams are mapped correctly"""
    structure = NFLStructure()
    
    # Test each team
    for team_id in range(1, 33):
        division = structure.get_division_for_team(team_id)
        assert division is not None
        
        conference = structure.get_conference_for_team(team_id)
        assert conference in [Conference.AFC, Conference.NFC]
```

## Test Organization

### Directory Structure
```
tests/
├── test_scheduling/           # Schedule generator tests
│   ├── __init__.py
│   ├── test_phase0.py        # Foundation tests
│   └── fixtures/             # Test data
├── test_simulation/          # Simulation system tests
├── test_game_engine/         # Game engine tests
├── test_integration/         # Integration tests
└── fixtures/                 # Shared test data
```

### Naming Conventions
- Test files: `test_*.py`
- Test classes: `TestClassName`
- Test methods: `test_method_name`
- Fixtures: `sample_*` or `mock_*`

## Performance Testing

### Benchmarking
Use pytest-benchmark for performance testing:

```python
def test_schedule_validation_performance(benchmark):
    """Benchmark schedule validation"""
    schedule = create_full_season_schedule()
    
    result = benchmark(schedule.validate)
    
    assert result[0] == True  # Valid schedule
    assert benchmark.stats['mean'] < 0.1  # Under 100ms
```

### Load Testing
Test system under load:

```python
def test_calendar_load():
    """Test calendar with full season load"""
    calendar = CalendarManager(date(2024, 9, 1))
    
    # Load 272 games (full season)
    for game in generate_season_games():
        calendar.schedule_event(game)
    
    # Verify performance
    start = time.time()
    calendar.simulate_day(date(2024, 9, 8))
    elapsed = time.time() - start
    
    assert elapsed < 1.0  # Under 1 second
```

## Coverage Requirements

### Target Coverage
- Unit tests: 80% minimum
- Integration tests: 70% minimum
- Critical paths: 100% required

### Running Coverage Reports
```bash
# Generate coverage report
python -m pytest --cov=src --cov-report=html

# View report
open htmlcov/index.html
```

## Continuous Testing

### Pre-commit Checks
Run before committing:
```bash
# Quick test suite
python -m pytest tests/ -x --tb=short

# Specific module
python -m pytest tests/test_scheduling/ -v
```

### Full Test Suite
Run for comprehensive validation:
```bash
# All tests with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

## Demo Scripts

Interactive demonstrations for testing and validation:

### Available Demos
- `full_game_demo.py` - Complete game simulation
- `calendar_manager_demo.py` - Calendar system demonstration
- `result_processing_demo.py` - Result processing showcase
- `phase_4_demo.py` - Comprehensive system demo

### Running Demos
```bash
# Full game simulation
python full_game_demo.py

# Calendar manager
python calendar_manager_demo.py
```

## Debugging Tests

### Verbose Output
```bash
# Show print statements
python -m pytest tests/test_file.py -s

# Detailed failure info
python -m pytest tests/test_file.py -vv
```

### Stop on First Failure
```bash
# Exit on first failure
python -m pytest tests/ -x

# With traceback
python -m pytest tests/ -x --tb=short
```

### Debug with pdb
```python
def test_complex_logic():
    """Test with debugger"""
    import pdb; pdb.set_trace()
    
    result = complex_function()
    assert result == expected
```

## Best Practices

### 1. Test Independence
Each test should be independent and not rely on other tests.

### 2. Clear Assertions
Make assertions specific and meaningful:
```python
# Good
assert game.week == 1, "Game should be in week 1"

# Bad
assert game.week
```

### 3. Test Data Management
Use fixtures and factories for test data:
```python
@pytest.fixture
def season_schedule():
    """Create a complete season schedule"""
    return SeasonScheduleFactory.create()
```

### 4. Test Documentation
Document what each test validates:
```python
def test_bye_week_distribution():
    """
    Verify bye weeks are distributed correctly:
    - Each team has exactly one bye
    - Byes occur between weeks 6-14
    - Maximum 6 teams on bye per week
    """
```

### 5. Error Testing
Test error conditions explicitly:
```python
def test_invalid_team_id():
    """Test handling of invalid team IDs"""
    with pytest.raises(ValueError, match="Team 33 not found"):
        structure.get_division_for_team(33)
```

## Troubleshooting

### Common Issues

**Import Errors**:
```bash
# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

**Slow Tests**:
- Use pytest markers to skip slow tests
- Run subset of tests during development
- Profile slow tests to identify bottlenecks

**Flaky Tests**:
- Remove randomness or use fixed seeds
- Mock external dependencies
- Ensure proper test isolation

## Summary

The testing framework ensures reliability and maintainability of The Owners Sim. By following these guidelines and patterns, developers can contribute high-quality, well-tested code that maintains the system's integrity while enabling rapid development and iteration.