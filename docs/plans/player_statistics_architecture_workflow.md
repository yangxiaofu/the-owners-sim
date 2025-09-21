# Player Statistics Architecture Workflow

## Executive Summary

This document provides a comprehensive analysis of the player statistics system architecture, current issues, and proposed solutions. The system spans from individual play execution to season-long statistical aggregation, involving multiple architectural layers and data transformations.

### Current State vs. Desired State

| Aspect | Current State | Desired State |
|--------|---------------|---------------|
| **Data Flow** | Broken: PlayerStats objects → dictionaries → objects | Seamless: PlayerStats objects throughout |
| **Context Handling** | No team context in PlayerStats | Rich context-aware domain objects |
| **Method Availability** | Missing calculation methods | Rich statistical calculation API |
| **Error Handling** | AttributeError exceptions | Graceful validation and clear errors |
| **Architecture** | Anemic data containers | Rich domain objects with behavior |

### Key Issues Identified

1. **Context Mismatch**: Play-level objects used in game-level contexts
2. **Missing Methods**: `get_total_yards()`, `get_total_touchdowns()`, `team_id` attribute
3. **Data Format Inconsistency**: Object → Dict → Object transformations
4. **Domain Logic Scatter**: Statistical calculations spread across multiple classes

---

## Component Interaction Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NFL SEASON SIMULATION PIPELINE                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │
│  │   Play      │    │    Game     │    │   Season    │    │Database  │  │
│  │   Level     │───▶│    Level    │───▶│    Level    │───▶│  Storage │  │
│  │             │    │             │    │             │    │          │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────────┘  │
│                                                                         │
│  Individual play     Game aggregation   Season tracking   Persistence   │
│  statistics         and processing     and leaderboards  and queries    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Component Architecture

### 1. Play-Level Statistics Generation

```
PlayEngine.simulate()
        │
        ▼
┌─────────────────────────────────────────────────┐
│            PlayResult Generation                │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐                           │
│  │ PlayResult      │                           │
│  │                 │                           │
│  │ ├─ outcome       │                           │
│  │ ├─ yards         │                           │
│  │ ├─ points        │                           │
│  │ └─ player_stats_summary ─────────────────┐   │
│  └─────────────────┘                      │   │
│                                           │   │
│  ┌─────────────────────────────────────────▼─┐ │
│  │ PlayStatsSummary                        │ │
│  │                                         │ │
│  │ ├─ player_stats: List[PlayerStats]      │ │
│  │ ├─ play_type: PlayType                  │ │
│  │ ├─ yards_gained: int                    │ │
│  │ └─ time_elapsed: float                  │ │
│  └─────────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Key PlayerStats Fields (Play-Level):**
- `player_name: str`
- `position: str`
- `passing_yards: int`
- `rushing_yards: int`
- `receiving_yards: int`
- **Missing**: `team_id`, calculation methods

### 2. Game-Level Aggregation Process

```
GameLoopController.run_game()
        │
        ▼
┌─────────────────────────────────────────────────┐
│         CentralizedStatsAggregator              │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │ PlayerStats     │  │ TeamStats       │       │
│  │ Accumulator     │  │ Accumulator     │       │
│  │                 │  │                 │       │
│  │ ├─ add_play_    │  │ ├─ total_yards  │       │
│  │ │  stats()      │  │ ├─ turnovers    │       │
│  │ ├─ get_all_     │  │ └─ penalties    │       │
│  │ │  players()    │  │                 │       │
│  │ └─ get_player_  │  └─────────────────┘       │
│  │    count()      │                            │
│  └─────────────────┘                            │
│                                                 │
│  ┌─────────────────────────────────────────────┐ │
│  │ get_all_statistics() → Dict                 │ │
│  │                                             │ │
│  │ ├─ "player_statistics"                      │ │
│  │ │   └─ "all_players": [p.__dict__]  ←─ ISSUE│ │
│  │ ├─ "team_statistics"                        │ │
│  │ └─ "game_info"                              │ │
│  └─────────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│              GameResult Creation                │
├─────────────────────────────────────────────────┤
│                                                 │
│  Current (Broken):                              │
│  player_stats = comprehensive_stats             │
│                   .get('all_players', [])       │
│  Result: List[Dict] (missing .player_name)      │
│                                                 │
│  Fixed (Option 1A):                             │
│  player_stats = stats_aggregator                │
│                   .get_player_statistics()      │
│  Result: List[PlayerStats] (has .player_name)   │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 3. Game Result Processing Pipeline

```
GameResult (with PlayerStats objects)
        │
        ▼
┌─────────────────────────────────────────────────┐
│           GameResultProcessor                   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────────────────────────────────────┐ │
│  │ _update_player_statistics()                 │ │
│  │                                             │ │
│  │ for player_stats in game_result.player_stats│ │
│  │     player_key = f"player_{player_stats     │ │
│  │                     .player_name}"  ✓       │ │
│  │                                             │ │
│  │     total_yards = player_stats              │ │
│  │                     .get_total_yards() ✗    │ │
│  │                                             │ │
│  │     total_tds = player_stats                │ │
│  │                   .get_total_touchdowns() ✗ │ │
│  └─────────────────────────────────────────────┘ │
│                                                 │
│  Current Errors:                                │
│  • AttributeError: 'PlayerStats' object has    │
│    no attribute 'get_total_yards'               │
│  • AttributeError: 'PlayerStats' object has    │
│    no attribute 'get_total_touchdowns'          │
│                                                 │
└─────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│              Database Persistence               │
├─────────────────────────────────────────────────┤
│                                                 │
│  DailyDataPersister                             │
│  ├─ persist_player_statistics()                 │
│  └─ persist_team_standings()                    │
│                                                 │
│  DatabaseAPI                                    │
│  ├─ get_player_passing_leaders()                │
│  ├─ get_player_rushing_leaders()                │
│  └─ get_team_standings()                        │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## Data Transformation Analysis

### PlayerStats Object Lifecycle

```
1. CREATION (Play-Level)
   ┌─────────────────────────────────────┐
   │ PlayerStats                         │
   │ ├─ player_name: "Tom Brady"         │
   │ ├─ passing_yards: 25                │
   │ ├─ rushing_yards: 0                 │
   │ └─ context: "play"                  │
   └─────────────────────────────────────┘

2. ACCUMULATION (Game-Level)
   ┌─────────────────────────────────────┐
   │ PlayerStatsAccumulator              │
   │ ├─ Combines multiple play stats     │
   │ ├─ Creates aggregated PlayerStats   │
   │ └─ Still missing: team_id, methods  │
   └─────────────────────────────────────┘

3. TRANSFORMATION (Current - Broken)
   ┌─────────────────────────────────────┐
   │ comprehensive_stats                 │
   │ └─ "all_players": [p.__dict__]      │
   │    Result: Dict objects             │
   └─────────────────────────────────────┘

4. CONSUMPTION (GameResultProcessor)
   ┌─────────────────────────────────────┐
   │ Expects PlayerStats objects with:   │
   │ ├─ .player_name ✓                   │
   │ ├─ .get_total_yards() ✗             │
   │ ├─ .get_total_touchdowns() ✗        │
   │ └─ .team_id ✗                       │
   └─────────────────────────────────────┘
```

### Context Transitions

| Context | Purpose | Data Format | Team Info | Calculations |
|---------|---------|-------------|-----------|-------------|
| **Play** | Individual play tracking | PlayerStats object | None | Simple stats |
| **Game** | Game-wide aggregation | PlayerStats object | Required | Total calculations |
| **Season** | League-wide statistics | Database records | Required | Advanced metrics |

---

## Architectural Solutions Comparison

### Option A: Rich Domain Objects (RECOMMENDED)

```python
@dataclass
class PlayerStats:
    # Core identity
    player_name: str
    position: str
    team_id: Optional[int] = None  # Added for game context

    # Raw statistics (existing)
    passing_yards: int = 0
    rushing_yards: int = 0
    receiving_yards: int = 0
    # ... all existing fields

    # Rich domain methods (NEW)
    def get_total_yards(self) -> int:
        """Total offensive yards per NFL standards"""
        total = self.passing_yards + self.rushing_yards + self.receiving_yards
        total -= self.sack_yards_lost  # NFL standard
        return max(0, total)

    def get_total_touchdowns(self) -> int:
        """Total offensive touchdowns"""
        return (self.passing_tds + self.passing_touchdowns +
                self.rushing_touchdowns + self.receiving_tds)

    def is_significant_performance(self) -> bool:
        """NFL definition of significant performance"""
        return self.get_total_yards() >= 100 or self.get_total_touchdowns() >= 2
```

**Benefits:**
- ✅ Domain-driven design principles
- ✅ Statistical logic encapsulated in PlayerStats
- ✅ Rich behavior, not just data containers
- ✅ Testable calculation methods
- ✅ NFL-standard statistical definitions

**Implementation Impact:**
- **Files Modified**: `src/play_engine/simulation/stats.py`
- **Risk Level**: Low (additive changes only)
- **Testing Required**: Unit tests for new methods

### Option B: GameResultProcessor Adaptation

```python
# In GameResultProcessor._update_player_statistics()
def _calculate_total_yards(self, player_stats: PlayerStats) -> int:
    total = (player_stats.passing_yards +
             player_stats.rushing_yards +
             player_stats.receiving_yards)
    total -= getattr(player_stats, 'sack_yards_lost', 0)
    return max(0, total)

def _calculate_total_touchdowns(self, player_stats: PlayerStats) -> int:
    return (getattr(player_stats, 'passing_tds', 0) +
            getattr(player_stats, 'rushing_touchdowns', 0) +
            getattr(player_stats, 'receiving_tds', 0))
```

**Benefits:**
- ✅ No changes to PlayerStats class
- ✅ Quick fix for immediate issue

**Drawbacks:**
- ❌ Logic scattered across multiple classes
- ❌ Calculation logic not reusable
- ❌ Violates domain-driven design principles

### Option C: Service Layer Pattern

```python
class NFLStatisticsCalculator:
    def calculate_total_yards(self, player_stats: PlayerStats) -> int:
        # Centralized calculation logic

    def calculate_total_touchdowns(self, player_stats: PlayerStats) -> int:
        # Centralized calculation logic

# Inject into GameResultProcessor
class GameResultProcessor:
    def __init__(self, stats_calculator: NFLStatisticsCalculator):
        self.stats_calculator = stats_calculator
```

**Benefits:**
- ✅ Centralized statistical logic
- ✅ Dependency injection for testing
- ✅ Service-oriented architecture

**Drawbacks:**
- ❌ More complex architecture
- ❌ Additional abstraction layer
- ❌ May be overkill for current needs

---

## Implementation Roadmap

### Phase 1: Immediate Fix (Option A - Core Methods)
**Timeline**: 1-2 hours
**Risk**: Low

```python
# Add to PlayerStats class
def get_total_yards(self) -> int:
    return max(0, self.passing_yards + self.rushing_yards +
               self.receiving_yards - getattr(self, 'sack_yards_lost', 0))

def get_total_touchdowns(self) -> int:
    return (getattr(self, 'passing_tds', 0) +
            getattr(self, 'rushing_touchdowns', 0) +
            getattr(self, 'receiving_tds', 0))
```

**Testing:**
- Unit tests for calculation accuracy
- Integration test with GameResultProcessor
- End-to-end test with interactive demo

### Phase 2: Team Context Enhancement
**Timeline**: 2-4 hours
**Risk**: Medium

```python
# Option 2A: Add team_id during aggregation
class CentralizedStatsAggregator:
    def get_player_statistics(self) -> List[PlayerStats]:
        players = self.player_stats.get_all_players_with_stats()

        for player in players:
            # Inject team context based on player tracking
            player.team_id = self._determine_team_id(player)

        return players
```

**Testing:**
- Verify team assignment accuracy
- Test with multi-team games
- Validate GameResultProcessor team filtering

### Phase 3: Rich Domain Enhancement
**Timeline**: 4-8 hours
**Risk**: Medium-High

```python
# Additional domain methods
def get_passer_rating(self) -> float:
    """Official NFL passer rating calculation"""

def get_yards_per_carry(self) -> float:
    """Rushing efficiency metric"""

def get_yards_per_target(self) -> float:
    """Receiving efficiency metric"""
```

**Testing:**
- NFL statistical accuracy validation
- Performance benchmarking
- Integration with reporting systems

### Phase 4: Architecture Patterns
**Timeline**: 1-2 days
**Risk**: High

- Builder pattern for PlayerStats creation
- Interface segregation for different contexts
- Dependency injection for statistical services

---

## Error Scenarios and Solutions

### Current AttributeError Issues

```
Error 1: 'PlayerStats' object has no attribute 'get_total_yards'
├─ Root Cause: Missing method in PlayerStats class
├─ Impact: GameResultProcessor fails
├─ Solution: Add method (Phase 1)
└─ Prevention: Unit tests for expected interface

Error 2: 'PlayerStats' object has no attribute 'team_id'
├─ Root Cause: No team context in PlayerStats
├─ Impact: Team-specific processing fails
├─ Solution: Add team context (Phase 2)
└─ Prevention: Context validation in aggregator

Error 3: 'dict' object has no attribute 'player_name' (RESOLVED)
├─ Root Cause: Dictionary conversion in get_all_statistics()
├─ Impact: GameResultProcessor couldn't access player data
├─ Solution: Direct object access (Option 1A - COMPLETED)
└─ Prevention: Type annotations and interface contracts
```

### Error Handling Strategy

```python
class PlayerStats:
    def get_total_yards(self) -> int:
        try:
            total = self.passing_yards + self.rushing_yards + self.receiving_yards
            total -= getattr(self, 'sack_yards_lost', 0)
            return max(0, total)
        except (AttributeError, TypeError) as e:
            # Log error but return sensible default
            logger.warning(f"Error calculating total yards for {self.player_name}: {e}")
            return 0

    def validate_statistics(self) -> List[str]:
        """Validate statistical consistency and return error messages"""
        errors = []

        if self.passing_yards < 0:
            errors.append("Negative passing yards")

        if self.completions > self.pass_attempts:
            errors.append("More completions than attempts")

        return errors
```

---

## Performance Considerations

### Memory Usage Analysis

```
Current State:
├─ PlayerStats objects: ~200 bytes each
├─ Dictionary conversion: +100% memory overhead
├─ Game-level: ~25 players × 200 bytes = 5KB
└─ Season-level: 256 games × 5KB = 1.28MB

Optimized State:
├─ Rich PlayerStats objects: ~300 bytes each (50% increase)
├─ No dictionary conversion: 0% overhead
├─ Game-level: ~25 players × 300 bytes = 7.5KB
└─ Season-level: 256 games × 7.5KB = 1.92MB
```

### Calculation Performance

```python
# Performance-critical calculations
def get_total_yards(self) -> int:
    # Cache result for repeated access
    if not hasattr(self, '_cached_total_yards'):
        self._cached_total_yards = self._calculate_total_yards()
    return self._cached_total_yards

def _calculate_total_yards(self) -> int:
    # Actual calculation logic
    return max(0, self.passing_yards + self.rushing_yards +
              self.receiving_yards - getattr(self, 'sack_yards_lost', 0))
```

---

## Testing Strategy

### Unit Tests (Phase 1)

```python
class TestPlayerStats:
    def test_get_total_yards_basic(self):
        stats = PlayerStats(
            player_name="Test Player",
            passing_yards=200,
            rushing_yards=50,
            receiving_yards=30
        )
        assert stats.get_total_yards() == 280

    def test_get_total_yards_with_sacks(self):
        stats = PlayerStats(
            player_name="Test QB",
            passing_yards=200,
            sack_yards_lost=15
        )
        assert stats.get_total_yards() == 185

    def test_get_total_touchdowns(self):
        stats = PlayerStats(
            player_name="Test Player",
            passing_tds=2,
            rushing_touchdowns=1,
            receiving_tds=1
        )
        assert stats.get_total_touchdowns() == 4
```

### Integration Tests (Phase 2)

```python
def test_game_result_processor_with_player_stats():
    # Create mock game result with PlayerStats
    game_result = create_mock_game_result_with_stats()
    processor = GameResultProcessor()

    # Should not raise AttributeError
    result = processor.process_result(game_result, context)

    assert result.processed_successfully
    assert len(result.statistics_generated) > 0
```

### End-to-End Tests (Phase 3)

```python
def test_full_statistics_pipeline():
    # Run complete game simulation
    simulator = FullGameSimulator(away_team_id=1, home_team_id=2)
    game_result = simulator.simulate_game()

    # Process through GameResultProcessor
    processor = GameResultProcessor()
    processing_result = processor.process_result(game_result, context)

    # Verify statistics are persisted
    assert processing_result.processed_successfully

    # Verify database queries work
    db_api = DatabaseAPI()
    leaders = db_api.get_player_passing_leaders(limit=10)
    assert len(leaders) > 0
```

---

## Future Architecture Vision

### Domain-Driven Design Principles

```
Bounded Contexts:
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   Game Play     │  │  Game Analysis  │  │ Season Tracking │
│   Context       │  │    Context      │  │    Context      │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • PlayResult    │  │ • PlayerStats   │  │ • SeasonStats   │
│ • PlayerStats   │  │ • TeamStats     │  │ • Leaderboards  │
│ • FieldPosition │  │ • GameResult    │  │ • Awards        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Service Layer Architecture

```
Application Layer:
├─ GameSimulationService
├─ PlayerStatisticsService
├─ SeasonProgressionService
└─ ReportingService

Domain Layer:
├─ PlayerStats (Rich Domain Object)
├─ TeamStats (Rich Domain Object)
├─ GameResult (Aggregate Root)
└─ StatisticalCalculations (Domain Service)

Infrastructure Layer:
├─ DatabaseAPI (Repository)
├─ FileSystemPersistence
└─ CacheManager
```

### Interface Segregation

```python
# Consumer-specific interfaces
class PlayLevelPlayerStats(Protocol):
    def add_passing_yards(self, yards: int) -> None: ...
    def add_rushing_yards(self, yards: int) -> None: ...

class GameLevelPlayerStats(Protocol):
    def get_total_yards(self) -> int: ...
    def get_total_touchdowns(self) -> int: ...
    def get_team_id(self) -> int: ...

class SeasonLevelPlayerStats(Protocol):
    def get_season_passing_yards(self) -> int: ...
    def get_games_played(self) -> int: ...
    def get_average_per_game(self) -> float: ...
```

---

## Conclusion

The player statistics architecture requires a multi-phase approach to achieve architectural excellence:

1. **Immediate Fix**: Add missing methods to resolve current AttributeError issues
2. **Context Enhancement**: Inject team context for proper game-level processing
3. **Domain Enrichment**: Transform anemic data containers into rich domain objects
4. **Service Layer**: Extract complex statistical calculations into dedicated services

This approach provides immediate problem resolution while establishing patterns for long-term architectural health and maintainability.

**Next Steps:**
1. Implement Phase 1 (missing methods)
2. Validate with comprehensive tests
3. Monitor performance and error rates
4. Proceed with subsequent phases based on results

---

*This document serves as the architectural blueprint for the player statistics system enhancement and should be updated as implementation progresses.*