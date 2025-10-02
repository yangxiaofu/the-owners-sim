# Simulation Workflow System

## Overview

The Simulation Workflow system provides a standardized, reusable pattern for executing NFL game simulations with optional data persistence. It encapsulates the proven 3-stage pattern used throughout the project:

1. **Stage 1: Simulation** - Execute game simulation using GameEvent
2. **Stage 2: Statistics** - Gather comprehensive player and team statistics
3. **Stage 3: Persistence** - Save data to database (toggleable)

## Key Features

- **Toggleable Persistence**: Enable or disable database operations for testing vs production
- **Configurable Database Paths**: Choose which database to persist to
- **Dynasty Isolation**: Complete statistical separation between different dynasties
- **Standardized Results**: Consistent API across all workflow executions
- **Factory Methods**: Pre-configured workflows for common use cases
- **Comprehensive Logging**: Optional verbose output for debugging and monitoring

## Core Components

### SimulationWorkflow

The main orchestrator class that manages the complete 3-stage workflow execution.

```python
from workflows import SimulationWorkflow

# Create workflow with custom configuration
workflow = SimulationWorkflow(
    enable_persistence=True,
    database_path="season_2024.db",
    dynasty_id="user_dynasty",
    verbose_logging=True
)

# Execute workflow
result = workflow.execute(game_event)
```

### WorkflowResult

A comprehensive result container that provides convenient access to all workflow outputs.

```python
# Access game results
scores = result.get_game_score()  # {'away_score': 21, 'home_score': 17}
winner = result.get_game_winner()  # 'away', 'home', or 'tie'
was_successful = result.was_successful()  # Boolean

# Access player statistics
all_stats = result.player_stats
team_stats = result.get_player_stats_by_team(team_id)

# Access persistence results
if result.persistence_result:
    status = result.persistence_result.overall_status
    records = result.persistence_result.total_records_persisted
```

### WorkflowConfiguration

Configuration management with factory methods for common scenarios.

```python
from workflows import WorkflowConfiguration

# Create configurations for different scenarios
testing_config = WorkflowConfiguration.for_testing()
demo_config = WorkflowConfiguration.for_demo("demo.db")
season_config = WorkflowConfiguration.for_season("season.db", "dynasty_id")
```

## Usage Patterns

### 1. Demo and Development

For demonstrations and development work where you want full visibility:

```python
# Factory method approach (recommended)
workflow = SimulationWorkflow.for_demo(
    database_path="demo.db",
    dynasty_id="demo_dynasty"
)

# Manual configuration approach
workflow = SimulationWorkflow(
    enable_persistence=True,
    database_path="demo.db",
    dynasty_id="demo_dynasty",
    verbose_logging=True
)

result = workflow.execute(game_event)
```

### 2. Testing

For unit tests and integration tests where persistence is not needed:

```python
# Factory method approach (recommended)
workflow = SimulationWorkflow.for_testing()

# Manual configuration approach
workflow = SimulationWorkflow(
    enable_persistence=False,
    verbose_logging=False
)

result = workflow.execute(game_event)
```

### 3. Season Simulation

For batch processing and season simulation where performance matters:

```python
# Factory method approach (recommended)
workflow = SimulationWorkflow.for_season(
    database_path="season_2024.db",
    dynasty_id="user_dynasty"
)

# Manual configuration approach
workflow = SimulationWorkflow(
    enable_persistence=True,
    database_path="season_2024.db",
    dynasty_id="user_dynasty",
    verbose_logging=False  # Reduced logging for performance
)

# Process multiple games
for game_event in season_games:
    result = workflow.execute(game_event)
    # Handle result as needed
```

### 4. Custom Persistence Strategy

For advanced use cases requiring custom persistence behavior:

```python
from persistence.demo import CustomDemoPersister

# Create custom persister
custom_persister = CustomDemoPersister(custom_config)

# Use with workflow
workflow = SimulationWorkflow(
    enable_persistence=True,
    persister_strategy=custom_persister,
    dynasty_id="custom_dynasty"
)

result = workflow.execute(game_event)
```

## Configuration Options

### Core Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `enable_persistence` | bool | True | Whether to persist data after simulation |
| `database_path` | str | None | Database file path (required if persistence enabled) |
| `dynasty_id` | str | "default" | Dynasty context for data isolation |
| `verbose_logging` | bool | True | Whether to print progress messages |

### Advanced Settings

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `persister_strategy` | DemoPersister | None | Custom persistence strategy |
| `persist_player_stats` | bool | True | Whether to save player statistics |
| `persist_team_stats` | bool | True | Whether to save team statistics |
| `persist_standings` | bool | True | Whether to update standings |

## Error Handling

The workflow system provides comprehensive error handling and reporting:

```python
result = workflow.execute(game_event)

if not result.was_successful():
    errors = result.get_error_summary()

    # Check simulation errors
    if errors['simulation_error']:
        print(f"Simulation failed: {errors['simulation_error']}")

    # Check persistence errors
    if errors['persistence_errors']:
        for error in errors['persistence_errors']:
            print(f"Persistence error: {error}")
```

## Performance Considerations

### For High-Performance Scenarios

1. **Disable Verbose Logging**: Set `verbose_logging=False` for batch processing
2. **Use Season Factory**: `SimulationWorkflow.for_season()` is optimized for performance
3. **Reuse Workflow Instances**: Create once, execute many times
4. **Consider Persistence Strategy**: Custom persisters can optimize for specific use cases

### For Development and Debugging

1. **Enable Verbose Logging**: Set `verbose_logging=True` for detailed output
2. **Use Demo Factory**: `SimulationWorkflow.for_demo()` provides full visibility
3. **Check Result Details**: Use `result.get_summary()` for comprehensive information

## Integration Examples

### With Season Manager

```python
class SeasonManager:
    def __init__(self, database_path: str, dynasty_id: str):
        self.workflow = SimulationWorkflow.for_season(database_path, dynasty_id)

    def simulate_week(self, week_games: List[GameEvent]) -> List[WorkflowResult]:
        results = []
        for game in week_games:
            result = self.workflow.execute(game)
            results.append(result)
        return results
```

### With Calendar System

```python
from calendar import CalendarComponent

class CalendarIntegration:
    def __init__(self, calendar: CalendarComponent, workflow: SimulationWorkflow):
        self.calendar = calendar
        self.workflow = workflow

    def process_scheduled_games(self):
        events = self.calendar.get_pending_events()
        for event in events:
            if isinstance(event, GameEvent):
                result = self.workflow.execute(event)
                # Handle result and mark event as processed
```

### With Demo Systems

```python
# Persistence demo integration
workflow = SimulationWorkflow.for_demo("demo.db", "demo_dynasty")
result = workflow.execute(game_event)

# Display results
scores = result.get_game_score()
print(f"Final Score: {scores['away_score']}-{scores['home_score']}")

if result.persistence_result:
    print(f"Persisted {result.persistence_result.total_records_persisted} records")
```

## Best Practices

### 1. Use Factory Methods

Always prefer factory methods over manual configuration:

```python
# Good
workflow = SimulationWorkflow.for_demo("demo.db")

# Avoid
workflow = SimulationWorkflow(
    enable_persistence=True,
    database_path="demo.db",
    dynasty_id="demo_dynasty",
    verbose_logging=True
)
```

### 2. Handle Results Properly

Always check if workflow execution was successful:

```python
result = workflow.execute(game_event)

if result.was_successful():
    # Process successful result
    scores = result.get_game_score()
else:
    # Handle errors
    errors = result.get_error_summary()
    # Log or handle errors appropriately
```

### 3. Reuse Workflow Instances

For batch processing, create workflow once and reuse:

```python
# Good - create once, use many times
workflow = SimulationWorkflow.for_season("season.db", "dynasty")
for game in games:
    result = workflow.execute(game)

# Avoid - creating new workflow for each game
for game in games:
    workflow = SimulationWorkflow.for_season("season.db", "dynasty")
    result = workflow.execute(game)
```

### 4. Choose Appropriate Verbosity

Match logging level to use case:

```python
# Development/debugging - verbose
workflow = SimulationWorkflow.for_demo("demo.db")

# Production/batch - minimal logging
workflow = SimulationWorkflow.for_season("season.db", "dynasty")

# Testing - no logging
workflow = SimulationWorkflow.for_testing()
```

## Troubleshooting

### Common Issues

1. **Database Path Required**: When `enable_persistence=True`, `database_path` must be provided
2. **Invalid Game Event**: Ensure GameEvent is properly constructed before passing to workflow
3. **Persistence Failures**: Check database permissions and disk space
4. **Dynasty Isolation**: Ensure consistent dynasty_id usage across related operations

### Debug Information

Access comprehensive debug information through the result object:

```python
result = workflow.execute(game_event)

# Get complete summary
summary = result.get_summary()
print(f"Execution timestamp: {summary['execution_timestamp']}")
print(f"Player count: {summary['player_count']}")
print(f"Persistence executed: {summary['persistence_executed']}")

# Get workflow configuration
config = result.workflow_config
print(f"Configuration: {config}")
```

## Future Enhancements

The workflow system is designed for extensibility. Planned enhancements include:

1. **Async Support**: Non-blocking workflow execution for UI applications
2. **Batch Processing**: Optimized multi-game execution with shared resources
3. **Custom Hooks**: Plugin system for custom pre/post-processing
4. **Metrics Collection**: Built-in performance and success metrics
5. **Configuration Validation**: Enhanced validation for workflow parameters