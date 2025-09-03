# Team ID System Overhaul - Comprehensive Plan

**Status**: Approved for Implementation  
**Priority**: Critical (Fixes 0-0 scoreboard bug)  
**Timeline**: 10 weeks (5 phases × 2 weeks each)  
**Created**: 2025-01-19  

## Executive Summary

This plan addresses the root cause of the scoreboard bug where touchdowns are detected correctly but never applied to the final score. The issue stems from systemic inconsistencies in team identification across the codebase, requiring a comprehensive overhaul of the team management system.

**Key Problem**: ScoreCalculator returns `scoring_team: 1` (integer) but TransitionApplicator expects `scoring_team: "home"` (string), causing all score applications to fail silently.

**Solution**: Implement a centralized, type-safe team identification system with clear ownership, consistent data types, and robust validation.

---

## Problem Analysis

### Current System Issues

#### 1. Type Inconsistencies
- **ScoreCalculator Output**: `scoring_team: 1` (integer)
- **TransitionApplicator Input**: expects `"home"` or `"away"` (string)  
- **Possession Tracking**: uses various formats (1, 2, 6, "1", "2")
- **Result**: Score application logic fails because `1 != "home"`

#### 2. Logic Fragmentation
- Team assignment logic scattered across multiple files
- No central authority for team identity resolution
- Each component makes independent assumptions about team IDs
- No clear mapping for dynamic team IDs (e.g., possession_team_id = 6)

#### 3. Architectural Weaknesses
- No team context awareness (setup vs runtime)
- No support for team metadata or validation
- No extensibility for different game modes
- Difficult debugging due to distributed team logic

### Evidence from Investigation

**Test Results Confirming the Bug**:
```
✅ Touchdown detection WORKS - Score calculator correctly detects touchdowns
✅ Manual scoreboard update WORKS - Scoreboard object functions properly  
❌ Score application FAILS - TransitionApplicator never applies calculated scores
🎯 Root Cause: Type mismatch in _apply_score_transition() method
```

**Specific Code Evidence**:
```python
# ScoreCalculator returns:
score_transition.scoring_team = 1  # integer

# TransitionApplicator checks:
if scoring_team == "home":           # 1 != "home" → FAILS
    game_state.scoreboard.home_score += points
elif scoring_team == "away":         # 1 != "away" → FAILS  
    game_state.scoreboard.away_score += points
# No points ever added to scoreboard
```

---

## Solution Architecture

### Design Principles

1. **Single Source of Truth**: Centralized team identity management
2. **Type Safety**: Consistent data types throughout the system
3. **Performance**: Fast lookups for hot code paths
4. **Extensibility**: Support for future game modes and features
5. **Debugging**: Clear, traceable team assignments
6. **Validation**: Early detection of invalid team operations
7. **Migration Safety**: Backward compatibility during transition

### System Components Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Team ID System Architecture              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────┐    ┌──────────────────┐               │
│  │   Core Types    │    │  Team Context    │               │
│  │                 │    │                  │               │
│  │ • TeamID (enum) │    │ • Game Setup     │               │
│  │ • TeamSide      │    │ • Home/Away Map  │               │
│  │ • TeamInfo      │    │ • Team Metadata  │               │
│  └─────────────────┘    └──────────────────┘               │
│           │                       │                        │
│           └───────────┬───────────┘                        │
│                       │                                    │
│  ┌─────────────────────────────────────────────────────────┤
│  │              Team Registry (Central Authority)          │
│  │                                                         │
│  │ • Possession → Team mapping                             │
│  │ • Team → Scoreboard mapping                             │
│  │ • Operation validation                                  │
│  │ • Event tracking                                        │
│  └─────────────────────────────────────────────────────────┤
│           │                       │                        │
│  ┌────────────────┐    ┌──────────────────────┐            │
│  │   TeamMapper   │    │    TeamValidator     │            │
│  │                │    │                      │            │
│  │ • Fast lookups │    │ • Business rules     │            │
│  │ • Caching      │    │ • Error detection    │            │
│  │ • Performance  │    │ • Audit trails       │            │
│  └────────────────┘    └──────────────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Updated Game Components                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ScoreCalculator ──→ TeamRegistry ──→ TransitionApplicator  │
│       │                   │                    │            │
│       │                   │                    │            │
│   Uses proper         Resolves team       Applies scores    │
│   team resolution     consistently        correctly         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Core Foundation (Weeks 1-2)

#### 1.1 Team Type System
**File**: `src/game_engine/teams/team_types.py`

```python
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union

class TeamSide(Enum):
    """Team sides in a game"""
    HOME = "home"
    AWAY = "away"  
    NEUTRAL = "neutral"  # For kickoffs, neutral possessions

class TeamID(IntEnum):
    """Standardized team identifiers"""
    NEUTRAL = 0  # For neutral possessions, kickoffs
    HOME = 1     # Home team
    AWAY = 2     # Away team
    
    @classmethod
    def from_any(cls, value: Union[int, str, 'TeamID']) -> 'TeamID':
        """Convert various formats to TeamID"""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            if value.lower() == "home":
                return cls.HOME
            elif value.lower() == "away":
                return cls.AWAY
            elif value.lower() == "neutral":
                return cls.NEUTRAL
            else:
                # Try to convert string number
                try:
                    return cls(int(value))
                except (ValueError, TypeError):
                    raise ValueError(f"Cannot convert '{value}' to TeamID")
        elif isinstance(value, int):
            return cls(value)
        else:
            raise TypeError(f"Cannot convert {type(value)} to TeamID")
    
    def to_side(self) -> TeamSide:
        """Convert TeamID to TeamSide"""
        if self == TeamID.HOME:
            return TeamSide.HOME
        elif self == TeamID.AWAY:
            return TeamSide.AWAY
        else:
            return TeamSide.NEUTRAL

@dataclass
class TeamInfo:
    """Complete team information"""
    team_id: TeamID
    side: TeamSide
    name: str
    abbreviation: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
```

#### 1.2 Team Context Manager
**File**: `src/game_engine/teams/team_context.py`

```python
from typing import Dict, Any, Optional
from .team_types import TeamID, TeamSide, TeamInfo

class TeamContext:
    """Manages team assignments for a specific game"""
    
    def __init__(self, home_team_data: Dict[str, Any], away_team_data: Dict[str, Any]):
        self.home_team = TeamInfo(
            team_id=TeamID.HOME,
            side=TeamSide.HOME,
            name=home_team_data.get("name", "Home Team"),
            abbreviation=home_team_data.get("abbreviation", "HOME"),
            metadata=home_team_data.get("metadata", {})
        )
        
        self.away_team = TeamInfo(
            team_id=TeamID.AWAY, 
            side=TeamSide.AWAY,
            name=away_team_data.get("name", "Away Team"),
            abbreviation=away_team_data.get("abbreviation", "AWAY"),
            metadata=away_team_data.get("metadata", {})
        )
        
        # Dynamic possession mappings for complex team IDs
        self._possession_mappings: Dict[Any, TeamID] = {
            1: TeamID.HOME,
            2: TeamID.AWAY, 
            "1": TeamID.HOME,
            "2": TeamID.AWAY,
            "home": TeamID.HOME,
            "away": TeamID.AWAY,
        }
    
    def get_team_info(self, team_id: TeamID) -> Optional[TeamInfo]:
        """Get complete team information"""
        if team_id == TeamID.HOME:
            return self.home_team
        elif team_id == TeamID.AWAY:
            return self.away_team
        return None
    
    def map_possession_to_team(self, possession_id: Any) -> TeamID:
        """Map possession team ID to standardized TeamID"""
        # Direct mapping first
        if possession_id in self._possession_mappings:
            return self._possession_mappings[possession_id]
        
        # Try TeamID conversion
        try:
            return TeamID.from_any(possession_id)
        except (ValueError, TypeError):
            # Handle complex cases (like possession_id = 6 from debug output)
            return self._resolve_complex_possession(possession_id)
    
    def register_possession_mapping(self, possession_id: Any, team_id: TeamID):
        """Register custom possession ID mapping"""
        self._possession_mappings[possession_id] = team_id
    
    def _resolve_complex_possession(self, possession_id: Any) -> TeamID:
        """Handle complex possession ID resolution"""
        # This can be extended for complex scenarios
        # For now, default to home team for unknown possessions
        # In production, might consult roster data, game setup, etc.
        return TeamID.HOME
```

#### 1.3 Team Registry (Central Authority)
**File**: `src/game_engine/teams/team_registry.py`

```python
from typing import Dict, Any, Optional, List
from .team_types import TeamID, TeamSide, TeamInfo
from .team_context import TeamContext

class TeamRegistry:
    """Single source of truth for all team operations"""
    
    def __init__(self, team_context: TeamContext):
        self.context = team_context
        self._event_log: List[Dict[str, Any]] = []
    
    def resolve_team_from_possession(self, possession_id: Any) -> TeamID:
        """Authoritative possession → team mapping"""
        team_id = self.context.map_possession_to_team(possession_id)
        
        # Log the resolution for debugging
        self._event_log.append({
            'event': 'possession_resolution',
            'possession_id': possession_id,
            'resolved_team': team_id,
            'timestamp': self._get_timestamp()
        })
        
        return team_id
    
    def resolve_scoring_team(self, possession_id: Any) -> TeamID:
        """Determine which team scores for given possession"""
        # For most cases, possessing team scores
        return self.resolve_team_from_possession(possession_id)
    
    def resolve_scoreboard_target(self, team_id: TeamID) -> str:
        """Map team ID to scoreboard field name"""
        if team_id == TeamID.HOME:
            return "home"
        elif team_id == TeamID.AWAY:  
            return "away"
        else:
            raise ValueError(f"Cannot map neutral team {team_id} to scoreboard")
    
    def validate_team_operation(self, team_id: TeamID, operation: str) -> bool:
        """Validate team-related operations"""
        # Basic validation - can be extended
        valid_teams = {TeamID.HOME, TeamID.AWAY}
        
        if operation in ["score", "possess"] and team_id not in valid_teams:
            return False
            
        return True
    
    def get_team_info(self, team_id: TeamID) -> Optional[TeamInfo]:
        """Get complete team information"""
        return self.context.get_team_info(team_id)
    
    def get_event_log(self) -> List[Dict[str, Any]]:
        """Get team operation event log for debugging"""
        return self._event_log.copy()
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for event logging"""
        from datetime import datetime
        return datetime.now().isoformat()
```

### Phase 2: Service Layer (Weeks 3-4)

#### 2.1 Team Mapping Service
**File**: `src/game_engine/teams/team_mapper.py`

```python
from typing import Dict, Any
from .team_types import TeamID
from .team_registry import TeamRegistry

class TeamMapper:
    """High-performance team ID translation service"""
    
    def __init__(self, registry: TeamRegistry):
        self.registry = registry
        # Pre-computed lookup tables for performance
        self._possession_to_team_cache: Dict[Any, TeamID] = {}
        self._team_to_scoreboard_cache: Dict[TeamID, str] = {}
        self._build_caches()
    
    def map_possession_to_team(self, possession_id: Any) -> TeamID:
        """Fast possession ID → TeamID lookup"""
        if possession_id not in self._possession_to_team_cache:
            # Cache miss - resolve and cache
            team_id = self.registry.resolve_team_from_possession(possession_id)
            self._possession_to_team_cache[possession_id] = team_id
            
        return self._possession_to_team_cache[possession_id]
    
    def map_team_to_scoreboard_field(self, team_id: TeamID) -> str:
        """Fast TeamID → scoreboard field lookup"""
        if team_id not in self._team_to_scoreboard_cache:
            # Cache miss - resolve and cache
            field = self.registry.resolve_scoreboard_target(team_id)
            self._team_to_scoreboard_cache[team_id] = field
            
        return self._team_to_scoreboard_cache[team_id]
    
    def invalidate_caches(self):
        """Clear caches when team context changes"""
        self._possession_to_team_cache.clear()
        self._team_to_scoreboard_cache.clear()
        self._build_caches()
    
    def _build_caches(self):
        """Pre-populate caches with common lookups"""
        # Pre-cache standard team mappings
        for team_id in [TeamID.HOME, TeamID.AWAY]:
            try:
                scoreboard_field = self.registry.resolve_scoreboard_target(team_id)
                self._team_to_scoreboard_cache[team_id] = scoreboard_field
            except ValueError:
                pass  # Skip invalid mappings
```

#### 2.2 Team Validation Framework
**File**: `src/game_engine/teams/team_validator.py`

```python
from typing import List, Optional
from dataclasses import dataclass
from .team_types import TeamID
from .team_registry import TeamRegistry

@dataclass
class ValidationResult:
    """Result of team validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

class TeamValidator:
    """Comprehensive team operation validation"""
    
    def __init__(self, registry: TeamRegistry):
        self.registry = registry
    
    def validate_possession_assignment(self, team_id: TeamID, context: dict) -> ValidationResult:
        """Validate possession assignments"""
        errors = []
        warnings = []
        
        # Check team validity
        if not self.registry.validate_team_operation(team_id, "possess"):
            errors.append(f"Team {team_id} cannot have possession")
        
        # Check team info exists
        team_info = self.registry.get_team_info(team_id)
        if team_info is None and team_id != TeamID.NEUTRAL:
            errors.append(f"No team information found for {team_id}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_scoring_assignment(self, scoring_team: TeamID, points: int, context: dict) -> ValidationResult:
        """Validate scoring assignments"""
        errors = []
        warnings = []
        
        # Check scoring team validity
        if not self.registry.validate_team_operation(scoring_team, "score"):
            errors.append(f"Team {scoring_team} cannot score")
        
        # Check points validity
        if points <= 0:
            errors.append(f"Invalid points value: {points}")
        elif points > 8:  # Maximum realistic NFL score in one play
            warnings.append(f"Unusually high score: {points} points")
        
        # Check scoreboard mapping exists
        try:
            self.registry.resolve_scoreboard_target(scoring_team)
        except ValueError as e:
            errors.append(f"Cannot map scoring team to scoreboard: {e}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_team_transition(self, from_team: TeamID, to_team: TeamID, reason: str) -> ValidationResult:
        """Validate team transitions (possession changes, etc.)"""
        errors = []
        warnings = []
        
        # Check both teams are valid
        for team in [from_team, to_team]:
            if team != TeamID.NEUTRAL:
                team_info = self.registry.get_team_info(team)
                if team_info is None:
                    errors.append(f"Invalid team in transition: {team}")
        
        # Check transition logic
        if from_team == to_team and reason != "continuation":
            warnings.append(f"Team transition from {from_team} to {to_team} with reason '{reason}'")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors, 
            warnings=warnings
        )
```

### Phase 3: Calculator Updates (Weeks 5-6)

#### 3.1 Enhanced Score Calculator
**File**: `src/game_engine/state_transitions/calculators/score_calculator.py` (Updates)

```python
# Add to existing ScoreCalculator class

from game_engine.teams.team_registry import TeamRegistry
from game_engine.teams.team_types import TeamID

class ScoreCalculator:
    def __init__(self, team_registry: Optional[TeamRegistry] = None):
        """Initialize with optional team registry for proper team resolution"""
        self.team_registry = team_registry
        # ... existing initialization
    
    def calculate_score_changes(self, play_result: PlayResult, game_state) -> ScoreTransition:
        """Calculate score changes with proper team assignment"""
        # ... existing logic for detecting scores
        
        if play_result.is_score and play_result.score_points > 0:
            # NEW: Use team registry for proper team resolution
            if self.team_registry:
                possession_id = game_state.field.possession_team_id
                scoring_team = self.team_registry.resolve_scoring_team(possession_id)
            else:
                # FALLBACK: Use old logic during migration
                scoring_team = self._legacy_determine_scoring_team(game_state)
            
            return ScoreTransition(
                score_occurred=True,
                score_type=self._determine_score_type(play_result),
                scoring_team=scoring_team,  # Now returns proper TeamID
                points_scored=play_result.score_points,
                # ... rest of fields
            )
        
        # ... rest of existing logic
    
    def _legacy_determine_scoring_team(self, game_state) -> TeamID:
        """Legacy team determination for backward compatibility"""
        # During migration, maintain existing behavior
        return TeamID.HOME  # This was the old behavior (always team 1)
```

### Phase 4: Applicator Updates (Weeks 7-8)

#### 4.1 Enhanced Transition Applicator
**File**: `src/game_engine/state_transitions/applicators/transition_applicator.py` (Updates)

```python
# Add to existing TransitionApplicator class

from game_engine.teams.team_mapper import TeamMapper
from game_engine.teams.team_types import TeamID

class TransitionApplicator:
    def __init__(self, team_mapper: Optional[TeamMapper] = None):
        """Initialize with optional team mapper for proper score application"""
        self.team_mapper = team_mapper
        # ... existing initialization
    
    def _apply_score_transition(self, score_transition, game_state: GameState) -> List[Dict[str, Any]]:
        """Apply calculated score transition to game state with proper team mapping"""
        changes = []
        
        if not score_transition or not score_transition.score_occurred:
            return changes
        
        old_home_score = game_state.scoreboard.home_score
        old_away_score = game_state.scoreboard.away_score
        
        scoring_team = score_transition.scoring_team
        points = score_transition.points_scored
        
        # NEW: Use team mapper for consistent score application
        if self.team_mapper:
            try:
                scoreboard_field = self.team_mapper.map_team_to_scoreboard_field(scoring_team)
                
                if scoreboard_field == "home":
                    game_state.scoreboard.home_score += points
                elif scoreboard_field == "away":
                    game_state.scoreboard.away_score += points
                else:
                    # Log unexpected scoreboard field
                    print(f"WARNING: Unexpected scoreboard field: {scoreboard_field}")
                    
            except Exception as e:
                # Fallback to legacy logic if team mapper fails
                print(f"Team mapper error, using fallback: {e}")
                self._legacy_apply_score(scoring_team, points, game_state)
        else:
            # ENHANCED FALLBACK: Handle both old and new formats during migration
            if isinstance(scoring_team, TeamID):
                if scoring_team == TeamID.HOME:
                    game_state.scoreboard.home_score += points
                elif scoring_team == TeamID.AWAY:
                    game_state.scoreboard.away_score += points
            elif scoring_team == "home" or scoring_team == 1:
                game_state.scoreboard.home_score += points
            elif scoring_team == "away" or scoring_team == 2:
                game_state.scoreboard.away_score += points
            else:
                # This was the original bug - log it clearly
                print(f"CRITICAL: Cannot apply score for team {scoring_team} ({type(scoring_team)})")
                print(f"Expected: TeamID enum, 'home'/'away' strings, or 1/2 integers")
        
        # ... rest of existing logging logic
```

### Phase 5: System Integration (Weeks 9-10)

#### 5.1 Service Provider
**File**: `src/game_engine/teams/team_service_provider.py`

```python
from dataclasses import dataclass
from typing import Dict, Any
from .team_context import TeamContext
from .team_registry import TeamRegistry
from .team_mapper import TeamMapper
from .team_validator import TeamValidator

@dataclass
class TeamServices:
    """Bundle of all team-related services"""
    context: TeamContext
    registry: TeamRegistry
    mapper: TeamMapper
    validator: TeamValidator

class TeamServiceProvider:
    """Factory for team services"""
    
    @staticmethod
    def create_services(home_team_data: Dict[str, Any], away_team_data: Dict[str, Any]) -> TeamServices:
        """Create complete team service suite for a game"""
        
        # Create team context
        context = TeamContext(home_team_data, away_team_data)
        
        # Handle special possession mappings from game data
        if 'possession_mappings' in home_team_data:
            for possession_id, team_side in home_team_data['possession_mappings'].items():
                if team_side == 'home':
                    context.register_possession_mapping(possession_id, TeamID.HOME)
        
        if 'possession_mappings' in away_team_data:
            for possession_id, team_side in away_team_data['possession_mappings'].items():
                if team_side == 'away':
                    context.register_possession_mapping(possession_id, TeamID.AWAY)
        
        # Create services
        registry = TeamRegistry(context)
        mapper = TeamMapper(registry)
        validator = TeamValidator(registry)
        
        return TeamServices(
            context=context,
            registry=registry,
            mapper=mapper,
            validator=validator
        )
```

#### 5.2 Game State Integration
**File**: `src/game_engine/field/game_state.py` (Updates)

```python
# Add to existing GameState class

from typing import Optional
from game_engine.teams.team_service_provider import TeamServices
from game_engine.teams.team_types import TeamID, TeamInfo

class GameState:
    def __init__(self, team_services: Optional[TeamServices] = None):
        # ... existing initialization
        self.team_services = team_services
    
    def get_possession_team_info(self) -> Optional[TeamInfo]:
        """Get complete information about team with current possession"""
        if not self.team_services:
            return None
            
        team_id = self.team_services.registry.resolve_team_from_possession(
            self.field.possession_team_id
        )
        return self.team_services.registry.get_team_info(team_id)
    
    def get_team_by_id(self, team_id: TeamID) -> Optional[TeamInfo]:
        """Get team information by TeamID"""
        if not self.team_services:
            return None
        return self.team_services.registry.get_team_info(team_id)
```

---

## Migration Strategy

### Backward Compatibility Approach

#### Stage 1: Parallel Implementation
- Implement new team system alongside existing code
- Both systems operational during transition
- New system used optionally via dependency injection

#### Stage 2: Enhanced Fallbacks  
- Update calculators and applicators with enhanced fallback logic
- Handle both old formats (integers, strings) and new formats (TeamID enum)
- Comprehensive logging of format usage for monitoring

#### Stage 3: Gradual Adoption
- GameOrchestrator updated to create team services
- Components gradually switch to new system
- Old system remains as fallback until migration complete

#### Stage 4: Full Migration
- All components using new team system
- Remove old fallback logic
- Clean up deprecated code paths

#### Stage 5: Advanced Features
- Add enhanced validation and event tracking
- Implement performance optimizations
- Add support for complex game modes

### Data Migration Considerations

#### Team Data Format
```python
# Current format support
{
    "home_team": {"name": "Team A", "id": 1},
    "away_team": {"name": "Team B", "id": 2}
}

# Enhanced format with team mappings
{
    "home_team": {
        "name": "Team A", 
        "abbreviation": "TMA",
        "possession_mappings": {6: "home"}  # Handle possession_id=6 case
    },
    "away_team": {
        "name": "Team B",
        "abbreviation": "TMB"
    }
}
```

#### Possession Mapping Migration
- Analyze existing game data for possession ID patterns
- Create automatic mapping rules for common cases
- Provide manual override capability for edge cases
- Maintain audit trail of all mapping decisions

---

## Testing Strategy

### Unit Testing Coverage

#### Team Type System
```python
def test_team_id_conversion():
    """Test all TeamID conversion scenarios"""
    assert TeamID.from_any(1) == TeamID.HOME
    assert TeamID.from_any("home") == TeamID.HOME
    assert TeamID.from_any("2") == TeamID.AWAY
    # ... comprehensive conversion tests

def test_team_context_mapping():
    """Test team context possession mapping"""
    context = TeamContext(home_data, away_data)
    assert context.map_possession_to_team(1) == TeamID.HOME
    assert context.map_possession_to_team(6) == TeamID.HOME  # Complex case
    # ... comprehensive mapping tests
```

#### Team Registry
```python
def test_team_registry_resolution():
    """Test team registry resolution accuracy"""
    registry = TeamRegistry(team_context)
    assert registry.resolve_team_from_possession(1) == TeamID.HOME
    assert registry.resolve_scoreboard_target(TeamID.HOME) == "home"
    # ... comprehensive resolution tests

def test_team_registry_validation():
    """Test team operation validation"""
    assert registry.validate_team_operation(TeamID.HOME, "score") == True
    assert registry.validate_team_operation(TeamID.NEUTRAL, "score") == False
    # ... comprehensive validation tests
```

### Integration Testing

#### Score Application Pipeline
```python
def test_complete_scoring_pipeline():
    """Test end-to-end scoring with team system"""
    game_state = GameState(team_services)
    touchdown_play = create_touchdown_play()
    
    # Execute complete pipeline
    score_calc = ScoreCalculator(team_services.registry)
    score_transition = score_calc.calculate_score_changes(touchdown_play, game_state)
    
    applicator = TransitionApplicator(team_services.mapper)
    applicator._apply_score_transition(score_transition, game_state)
    
    # Verify score applied correctly
    assert game_state.scoreboard.home_score == 6 or game_state.scoreboard.away_score == 6
    assert game_state.scoreboard.home_score + game_state.scoreboard.away_score == 6
```

#### Migration Compatibility
```python
def test_backward_compatibility():
    """Test that old team ID formats still work"""
    # Test with old integer format
    old_score_transition = ScoreTransition(scoring_team=1, points_scored=6)
    
    # Should still work with enhanced applicator
    applicator = TransitionApplicator()  # No team mapper
    applicator._apply_score_transition(old_score_transition, game_state)
    
    assert game_state.scoreboard.home_score == 6
```

### Performance Testing

#### Benchmark Requirements
- Team resolution: < 1ms for 99% of lookups
- Score application: < 0.5ms per operation
- Memory usage: < 10MB for team system overhead
- Cache hit rate: > 95% for common operations

#### Load Testing
```python
def test_team_system_performance():
    """Benchmark team system performance"""
    team_services = TeamServiceProvider.create_services(home_data, away_data)
    
    # Test 10,000 team resolutions
    start_time = time.time()
    for i in range(10000):
        team_id = team_services.registry.resolve_team_from_possession(random.choice([1, 2, 6]))
    end_time = time.time()
    
    avg_time = (end_time - start_time) / 10000
    assert avg_time < 0.001  # Less than 1ms average
```

---

## Advanced Features & Extensibility

### Multi-Game Mode Support

#### Standard NFL Game
```python
team_services = TeamServiceProvider.create_services(
    home_team_data={"name": "Home Team", "abbreviation": "HOM"},
    away_team_data={"name": "Away Team", "abbreviation": "AWY"}
)
```

#### Practice Scrimmage (Same Team)
```python
class PracticeTeamContext(TeamContext):
    """Team context for practice games"""
    def __init__(self, team_data):
        # Both "teams" are actually the same team
        super().__init__(team_data, team_data)
```

#### Tournament Mode
```python
class TournamentTeamContext(TeamContext):
    """Team context supporting multiple potential teams"""
    def __init__(self, team_pool: List[Dict]):
        self.team_pool = team_pool
        # Dynamic team assignment based on bracket position
```

### Dynamic Team Resolution

#### Complex Possession Mapping
```python
class AdvancedTeamContext(TeamContext):
    """Enhanced team context with complex resolution"""
    
    def _resolve_complex_possession(self, possession_id: Any) -> TeamID:
        """Advanced possession resolution using multiple data sources"""
        
        # Check roster data
        if hasattr(self, 'roster_data'):
            if possession_id in self.roster_data.home_player_ids:
                return TeamID.HOME
            elif possession_id in self.roster_data.away_player_ids:
                return TeamID.AWAY
        
        # Check game setup data
        if hasattr(self, 'game_setup'):
            team_mapping = self.game_setup.get('dynamic_team_mappings', {})
            if possession_id in team_mapping:
                return TeamID.from_any(team_mapping[possession_id])
        
        # Fallback to heuristic-based resolution
        return self._heuristic_team_resolution(possession_id)
```

### Performance Optimization

#### Advanced Caching
```python
from functools import lru_cache
from typing import LRU_CACHE_SIZE = 1000

class HighPerformanceTeamMapper(TeamMapper):
    """Optimized team mapper with advanced caching"""
    
    @lru_cache(maxsize=LRU_CACHE_SIZE)
    def cached_possession_to_team(self, possession_id: Any) -> TeamID:
        """LRU cached team resolution"""
        return super().map_possession_to_team(possession_id)
    
    def warm_caches(self, common_possession_ids: List[Any]):
        """Pre-warm caches with common possession IDs"""
        for possession_id in common_possession_ids:
            self.cached_possession_to_team(possession_id)
```

#### Batch Operations
```python
class BatchTeamOperations:
    """Batch team operations for performance"""
    
    def batch_resolve_teams(self, possession_ids: List[Any]) -> List[TeamID]:
        """Resolve multiple possession IDs in single operation"""
        
    def batch_validate_operations(self, operations: List[Dict]) -> List[ValidationResult]:
        """Validate multiple team operations efficiently"""
```

---

## Risk Mitigation

### Technical Risks

#### Performance Impact
- **Risk**: New team system introduces latency
- **Mitigation**: Comprehensive performance testing, caching, benchmarking
- **Monitoring**: Performance metrics tracking, alerting on regressions

#### Migration Bugs
- **Risk**: Bugs introduced during migration
- **Mitigation**: Extensive testing, gradual rollout, fallback mechanisms
- **Monitoring**: Error tracking, validation logging, rollback procedures

#### Integration Complexity
- **Risk**: Complex integration with existing systems
- **Mitigation**: Modular design, dependency injection, parallel implementation
- **Testing**: Integration tests, end-to-end validation

### Business Risks

#### Development Timeline
- **Risk**: 10-week timeline may be aggressive
- **Mitigation**: Phased approach, MVP focus, iterative delivery
- **Contingency**: Identify minimum viable solution for each phase

#### Compatibility Issues
- **Risk**: Breaking existing functionality
- **Mitigation**: Backward compatibility, comprehensive testing
- **Fallback**: Ability to revert to old system if needed

---

## Success Metrics

### Immediate Objectives (Phase 1-3)
- ✅ **Scoreboard Bug Fixed**: Touchdowns correctly applied to score
- ✅ **Type Safety**: All team operations use consistent data types
- ✅ **Test Coverage**: 100% unit test coverage for team system
- ✅ **Performance**: No measurable performance regression

### Long-term Objectives (Phase 4-5)
- ✅ **System Reliability**: Zero team-related bugs in production
- ✅ **Maintainability**: Clear ownership and debugging of team operations
- ✅ **Extensibility**: Support for new game modes and features
- ✅ **Documentation**: Comprehensive system documentation and examples

### Quality Gates
- All existing tests continue to pass
- New team system tests achieve 100% coverage
- Performance benchmarks meet requirements
- Code review approval from team leads
- Integration testing validation

---

## Future Enhancements

### Immediate Opportunities (Post-Implementation)
1. **Enhanced Team Statistics**: Track team-specific performance metrics
2. **Advanced Validation**: More sophisticated business rule validation
3. **Team Event Analytics**: Detailed analysis of team-related events
4. **Performance Monitoring**: Real-time team system performance tracking

### Long-term Possibilities
1. **Multi-Team Games**: Support for more than 2 teams (special events)
2. **Dynamic Team Changes**: Support for mid-game team modifications
3. **Team AI Integration**: AI-driven team behavior and decision making
4. **Advanced Simulation Modes**: Complex scenario simulation capabilities

---

## Conclusion

This comprehensive team ID system overhaul addresses the critical scoreboard bug while establishing a robust foundation for future team-related functionality. The phased approach ensures minimal risk while delivering maximum value, transforming a fragmented system into a cohesive, maintainable, and extensible team management architecture.

The investment in this system will pay dividends in reduced bugs, easier maintenance, improved performance, and enhanced capabilities for future game features. Most importantly, it will immediately fix the 0-0 scoreboard issue that currently undermines the game simulation's credibility.

**Next Steps**: Begin Phase 1 implementation with core team types system, following the detailed specifications outlined in this plan.