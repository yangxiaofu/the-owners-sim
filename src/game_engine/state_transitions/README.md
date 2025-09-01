# Game State Transitions System

## 🎯 Overview

The Game State Transitions System provides a clean, testable, and maintainable approach to managing all game state changes in the football simulation. It separates the complex concerns of calculating, validating, and applying state changes into distinct, testable components.

## 🏗️ Architecture

### Core Design Principles

- **Immutable Transitions**: All changes represented as immutable objects
- **Pure Calculation**: Calculate what should happen without side effects  
- **Atomic Application**: Apply all changes or none (transactional)
- **Validation First**: Check legality before applying changes
- **Single Responsibility**: Each class has one clear purpose
- **Complete Testability**: Each component can be unit tested in isolation

### Data Flow

```
Play Result + Game State
    ↓
[Calculators] → Calculate required transitions (pure functions)
    ↓ 
[Validators] → Validate transitions are legal
    ↓
[Applicators] → Apply all changes atomically
    ↓
Updated Game State + Audit Trail
```

## 📁 Package Structure

```
state_transitions/
├── data_structures/          # Immutable transition objects
│   ├── game_state_transition.py    # Main container for all changes
│   ├── field_transition.py         # Field position, downs, yards
│   ├── possession_transition.py    # Team possession changes
│   ├── score_transition.py         # Score and touchdown logic
│   ├── clock_transition.py         # Time and quarter management
│   └── special_situation_transition.py  # Kickoffs, punts, turnovers
│
├── calculators/              # Pure business logic functions
│   ├── transition_calculator.py    # Main coordinator
│   ├── field_calculator.py         # Field position logic
│   ├── possession_calculator.py    # Possession change rules
│   ├── score_calculator.py         # Scoring calculations
│   ├── clock_calculator.py         # Time management logic
│   └── special_situations_calculator.py  # Complex scenarios
│
├── validators/               # Rule validation and consistency checks
│   ├── transition_validator.py     # Main validation orchestrator
│   ├── field_validator.py          # Field bounds and down/distance
│   ├── possession_validator.py     # Possession change legality
│   ├── score_validator.py          # Scoring rule compliance
│   └── nfl_rules_validator.py      # Official NFL rule compliance
│
├── applicators/              # Atomic state application
│   ├── transition_applicator.py    # Main application coordinator
│   ├── atomic_state_changer.py     # Handles rollback on failures
│   └── state_rollback_manager.py   # Error recovery operations
│
└── tracking/                 # Statistics and auditing
    ├── game_statistics_tracker.py  # Play counts, time tracking
    ├── play_by_play_auditor.py     # Complete audit trail
    └── performance_metrics.py      # System performance tracking
```

## 🚀 Quick Start

### Basic Usage Pattern

```python
from game_engine.state_transitions import GameStateManager

# Initialize the state manager
state_manager = GameStateManager()

# Process a play result
play_result = execute_play(offense, defense, game_state)
transition = state_manager.process_play_result(play_result, game_state)

# Apply the calculated changes atomically
state_manager.apply_transition(transition, game_state)

# Track statistics separately
statistics_tracker.record_play(play_result, transition)
```

### Creating Custom Transitions

```python
from game_engine.state_transitions.data_structures import FieldTransition

# Create an immutable field transition
field_transition = FieldTransition(
    new_yard_line=25,
    new_down=1,
    new_yards_to_go=10,
    possession_change=False,
    turnover=False,
    first_down_achieved=True
)

# Transition is immutable - this would raise an error:
# field_transition.new_yard_line = 30  # AttributeError!
```

## 📊 Data Structures

### GameStateTransition (Main Container)
Contains all the individual transitions that need to be applied as a single atomic operation.

### FieldTransition
Handles field position changes, downs, and yards to go:
- New field position (0-100 yard line)
- Down progression (1-4)
- Yards to go for first down
- First down achievements

### PossessionTransition
Manages team possession changes:
- Possession switches
- Turnover scenarios
- Change of possession reasons

### ScoreTransition
Handles all scoring scenarios:
- Touchdowns (6 points)
- Field goals (3 points)
- Safeties (2 points)
- Extra points and two-point conversions

### ClockTransition
Manages game time and quarters:
- Time progression
- Quarter changes
- Clock stopping scenarios
- Overtime handling

### SpecialSituationTransition
Complex scenarios like:
- Kickoffs (after scores)
- Punts (change of possession)
- Turnovers (fumbles, interceptions)
- Special teams plays

## 🧪 Testing

### Unit Testing Each Component

```python
def test_field_calculator():
    # Test pure calculation function
    game_state = create_mock_game_state()
    play_result = create_mock_play_result(yards=7)
    
    transition = calculate_field_transition(play_result, game_state)
    
    assert transition.new_yard_line == 32  # Started at 25
    assert transition.new_down == 2
    assert transition.new_yards_to_go == 3

def test_field_validator():
    # Test validation logic
    invalid_transition = FieldTransition(
        new_yard_line=105,  # Invalid: beyond field bounds
        new_down=1,
        new_yards_to_go=10
    )
    
    validator = FieldValidator()
    is_valid, errors = validator.validate(invalid_transition)
    
    assert not is_valid
    assert "Field position must be between 0-100" in errors
```

### Integration Testing

```python
def test_complete_touchdown_scenario():
    # Test full flow from play result to state update
    game_state = create_game_state_at_goal_line()
    play_result = create_touchdown_run()
    
    state_manager = GameStateManager()
    transition = state_manager.process_play_result(play_result, game_state)
    
    # Verify all expected transitions are present
    assert transition.score_transition.touchdown_scored
    assert transition.possession_transition.requires_kickoff
    assert transition.field_transition.new_yard_line == 35  # Kickoff position
```

## 🔧 Common Patterns

### Adding New Game Rules

1. **Add fields to existing transition objects** if the rule affects existing state
2. **Create new transition types** for entirely new game concepts
3. **Update calculators** with the new business logic
4. **Add validators** for the new rules
5. **Update applicators** to handle the new state changes

### Error Handling

All state changes are atomic. If any part of a transition fails validation or application, the entire operation is rolled back:

```python
try:
    state_manager.apply_transition(transition, game_state)
except TransitionValidationError as e:
    # Transition was invalid, game state unchanged
    logger.error(f"Invalid transition: {e.errors}")
except TransitionApplicationError as e:
    # Application failed, game state rolled back
    logger.error(f"Application failed: {e.message}")
```

### Performance Considerations

- **Immutable objects**: Memory overhead for large numbers of transitions
- **Pure functions**: Excellent for caching and memoization
- **Atomic operations**: Small performance cost for consistency guarantees
- **Validation**: Can be expensive for complex rules - consider caching

## 🐛 Troubleshooting

### Common Issues

**TransitionValidationError**: Check that all transition fields are within valid ranges and comply with NFL rules.

**TransitionApplicationError**: Usually indicates a bug in the applicator logic or an unexpected game state.

**Immutable object errors**: Remember that all transition objects are frozen - create new objects instead of modifying existing ones.

### Debugging Tips

1. **Use the audit trail**: Every transition is logged with full context
2. **Test calculators independently**: Pure functions are easy to debug
3. **Validate transitions manually**: Check each field against the rules
4. **Use mock objects**: Create specific game states for testing edge cases

## 📈 Benefits

### For Maintainability
- Single responsibility per class
- Clear interfaces between components
- Easy to modify individual concerns without affecting others

### For Testability
- Each component can be unit tested in isolation
- Immutable objects make assertions straightforward
- Pure functions eliminate testing complexity
- Complete scenario coverage possible

### For Reliability
- Atomic transactions prevent partial state updates
- Validation prevents illegal states
- Audit trail for debugging complex scenarios
- Rollback capability for error recovery

### For Extensibility
- Easy to add new game rules or situations
- New transition types can be added without affecting existing code
- Statistics and auditing can be enhanced independently

## 🤝 Contributing

When adding new features to the state transitions system:

1. **Start with data structures**: Define what state changes are needed
2. **Add calculators**: Implement the business logic as pure functions
3. **Create validators**: Ensure the new transitions follow game rules
4. **Update applicators**: Handle applying the new state changes
5. **Write comprehensive tests**: Test each component independently
6. **Update documentation**: Keep this README current with new features

The goal is to maintain clean separation of concerns while making the system easy to understand and extend.