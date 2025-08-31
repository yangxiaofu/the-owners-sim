# Enhanced Play Calculation Engine Architecture

## Executive Summary

This plan implements Option 1: Enhanced Strategy with Calculation Engines to create sophisticated, position-specific play calculations while maintaining clean architecture. The system will follow SOLID and YAGNI principles with comprehensive unit testing.

## Current State Analysis

**Problems with Current Implementation:**
- **Inconsistent complexity**: RunPlay has sophisticated logic, PassPlay has placeholders
- **Code duplication**: Each play type reimplements similar calculations differently
- **Limited attribute usage**: Only basic QB/RB/WR ratings, missing specific attributes
- **Hard to maintain**: Balance changes require updates in multiple places
- **Incomplete individual player logic**: Placeholder code in PassPlay (lines 68-72)

## Architecture Overview

### SOLID Principles Implementation

**Single Responsibility Principle (SRP):**
- `PlayCalculationEngine`: Handles complex football calculations
- `BlockingEngine`: Manages OL vs DL interactions
- `CoverageEngine`: Handles receiver vs defender matchups
- Each play type focuses only on play-specific outcome logic

**Open/Closed Principle (OCP):**
- New play types extend PlayType without modifying existing code
- New calculation methods added to engines without changing play classes
- Plugin architecture for specialized calculations

**Liskov Substitution Principle (LSP):**
- All play types implement identical PlayType interface
- Calculation engines return standardized result objects
- Consistent behavior across all implementations

**Interface Segregation Principle (ISP):**
- Separate interfaces for blocking, coverage, and outcome calculations
- Play types only depend on engines they actually use
- No forced dependencies on unused calculations

**Dependency Inversion Principle (DIP):**
- Play types depend on calculation engine abstractions
- Concrete engines injected via dependency injection
- Testable through mock implementations

### YAGNI Implementation

**Build Only What's Needed:**
- Start with core run/pass calculations
- Add complexity incrementally based on actual requirements
- Avoid speculative features like weather/crowd noise initially
- Focus on attributes that actually exist in player models

## Detailed Design

### Core Architecture

```python
# Calculation Engine Interfaces (ISP)
class IBlockingEngine(ABC):
    def calculate_blocking_efficiency(self, blockers: List[Player], 
                                    rushers: List[Player], 
                                    block_type: str) -> BlockingResult

class ICoverageEngine(ABC):
    def calculate_coverage_efficiency(self, receivers: List[Player],
                                    defenders: List[Player],
                                    coverage_scheme: str) -> CoverageResult

class IOutcomeEngine(ABC):
    def determine_play_outcome(self, offensive_advantage: float,
                             play_type: str, 
                             field_context: FieldState) -> PlayOutcome

# Calculation Results (SRP)
@dataclass
class BlockingResult:
    efficiency_rating: float  # 0.0 - 1.0
    pressure_generated: float
    individual_matchups: List[MatchupResult]

@dataclass 
class CoverageResult:
    coverage_rating: float    # 0.0 - 1.0
    separation_achieved: float
    big_play_potential: float

@dataclass
class PlayOutcome:
    success_probability: float
    yards_base: int
    outcome_modifiers: Dict[str, float]
```

### Enhanced Play Types

```python
class RunPlay(PlayType):
    def __init__(self, blocking_engine: IBlockingEngine, 
                 outcome_engine: IOutcomeEngine):
        self._blocking_engine = blocking_engine
        self._outcome_engine = outcome_engine
    
    def simulate(self, personnel: PersonnelPackage, 
                field_state: FieldState) -> PlayResult:
        
        # Use injected engines (DIP)
        blocking_result = self._blocking_engine.calculate_blocking_efficiency(
            personnel.get_offensive_line(),
            personnel.get_defensive_line(),
            self._get_blocking_scheme(personnel.formation)
        )
        
        # RB-specific calculations using actual attributes
        rb = personnel.get_running_back()
        rb_effectiveness = self._calculate_rb_effectiveness(rb, blocking_result)
        
        # Formation and situational modifiers
        formation_bonus = self._get_formation_modifier(
            personnel.formation, personnel.defensive_call, "run"
        )
        
        total_advantage = rb_effectiveness * blocking_result.efficiency_rating * formation_bonus
        
        # Delegate outcome determination (SRP)
        outcome = self._outcome_engine.determine_play_outcome(
            total_advantage, "run", field_state
        )
        
        return self._create_play_result(outcome, personnel)
    
    def _calculate_rb_effectiveness(self, rb: RunningBack, 
                                  blocking: BlockingResult) -> float:
        """RB-specific calculation using actual player attributes"""
        if not rb:
            return 0.5  # Default effectiveness
        
        # Use actual RB attributes from player model
        vision_factor = rb.vision / 100.0  # Find the best gap
        power_factor = rb.power / 100.0    # Break tackles
        elusiveness_factor = rb.elusiveness / 100.0  # Avoid tackles
        
        # Weight based on blocking quality
        if blocking.efficiency_rating > 0.7:  # Good blocking
            # Vision most important when gaps are available
            return (vision_factor * 0.4 + power_factor * 0.3 + elusiveness_factor * 0.3)
        else:  # Poor blocking
            # Power and elusiveness more important
            return (power_factor * 0.4 + elusiveness_factor * 0.4 + vision_factor * 0.2)

class PassPlay(PlayType):
    def __init__(self, blocking_engine: IBlockingEngine,
                 coverage_engine: ICoverageEngine,
                 outcome_engine: IOutcomeEngine):
        self._blocking_engine = blocking_engine
        self._coverage_engine = coverage_engine  
        self._outcome_engine = outcome_engine
    
    def simulate(self, personnel: PersonnelPackage, 
                field_state: FieldState) -> PlayResult:
        
        # Pass protection calculation
        protection_result = self._blocking_engine.calculate_blocking_efficiency(
            personnel.get_offensive_line(),
            personnel.get_defensive_line(),
            "pass_protection"
        )
        
        # Coverage battle calculation  
        coverage_result = self._coverage_engine.calculate_coverage_efficiency(
            personnel.get_receivers(),
            personnel.get_defensive_backs(),
            personnel.defensive_call
        )
        
        # QB-specific effectiveness
        qb = personnel.get_quarterback()
        qb_effectiveness = self._calculate_qb_effectiveness(
            qb, protection_result, coverage_result
        )
        
        total_advantage = qb_effectiveness * (1.0 - coverage_result.coverage_rating)
        
        outcome = self._outcome_engine.determine_play_outcome(
            total_advantage, "pass", field_state
        )
        
        return self._create_play_result(outcome, personnel)
    
    def _calculate_qb_effectiveness(self, qb: Quarterback, 
                                  protection: BlockingResult,
                                  coverage: CoverageResult) -> float:
        """QB-specific calculation using actual attributes"""
        # Will use actual QB attributes when QB class is implemented
        # For now, extract from personnel package
        qb_rating = 75  # Placeholder - will use qb.accuracy, qb.arm_strength, etc.
        
        # Pressure affects QB performance
        pressure_penalty = protection.pressure_generated * 0.3
        
        # Coverage affects completion probability
        coverage_difficulty = coverage.coverage_rating
        
        base_effectiveness = qb_rating / 100.0
        return max(0.1, base_effectiveness - pressure_penalty - coverage_difficulty)
```

### Calculation Engine Implementations

```python
class StandardBlockingEngine(IBlockingEngine):
    """Standard NFL-style blocking calculations"""
    
    def calculate_blocking_efficiency(self, blockers: List[OffensiveLineman],
                                    rushers: List[DefensiveLineman],
                                    block_type: str) -> BlockingResult:
        
        if not blockers or not rushers:
            return BlockingResult(0.5, 0.5, [])
        
        individual_matchups = []
        total_blocking_success = 0.0
        total_pressure = 0.0
        
        # Individual OL vs DL matchups
        for blocker, rusher in zip(blockers, rushers):
            matchup_result = self._calculate_individual_matchup(
                blocker, rusher, block_type
            )
            individual_matchups.append(matchup_result)
            total_blocking_success += matchup_result.blocker_success
            total_pressure += matchup_result.rusher_success
        
        # Normalize results
        avg_blocking = total_blocking_success / len(individual_matchups)
        avg_pressure = total_pressure / len(individual_matchups)
        
        return BlockingResult(
            efficiency_rating=avg_blocking,
            pressure_generated=avg_pressure,
            individual_matchups=individual_matchups
        )
    
    def _calculate_individual_matchup(self, blocker: OffensiveLineman,
                                    rusher: DefensiveLineman,
                                    block_type: str) -> MatchupResult:
        """Individual player vs player calculation"""
        
        if block_type == "run_blocking":
            blocker_skill = blocker.get_effective_attribute('run_blocking')
            rusher_skill = rusher.get_effective_attribute('run_defense')
        else:  # pass_protection
            blocker_skill = blocker.get_effective_attribute('pass_blocking')  
            rusher_skill = rusher.get_effective_attribute('pass_rushing')
        
        # Technique vs power considerations
        blocker_technique = blocker.get_effective_attribute('technique')
        rusher_power = rusher.get_effective_attribute('power_moves')
        
        # Calculate success rates
        skill_differential = (blocker_skill - rusher_skill) / 100.0
        technique_bonus = (blocker_technique - rusher_power) / 200.0
        
        blocker_success = max(0.1, min(0.9, 0.5 + skill_differential + technique_bonus))
        rusher_success = 1.0 - blocker_success
        
        return MatchupResult(
            blocker=blocker,
            rusher=rusher,
            blocker_success=blocker_success,
            rusher_success=rusher_success
        )
```

## Implementation Strategy

### Phase 1: Core Infrastructure (Week 1)
- **Create calculation engine interfaces** (IBlockingEngine, ICoverageEngine, IOutcomeEngine)
- **Implement result data classes** (BlockingResult, CoverageResult, PlayOutcome)
- **Create StandardBlockingEngine** with individual OL vs DL matchups
- **Update RunPlay** to use blocking engine
- **Unit tests for blocking calculations**

### Phase 2: Pass Play Enhancement (Week 2)  
- **Implement StandardCoverageEngine** with receiver vs defender matchups
- **Create QB effectiveness calculations** using existing attributes
- **Update PassPlay** to use both blocking and coverage engines
- **Add StandardOutcomeEngine** for consistent outcome determination
- **Unit tests for coverage and outcome calculations**

### Phase 3: Special Teams (Week 3)
- **Update KickPlay and PuntPlay** to use calculation engines where applicable
- **Add SpecialTeamsEngine** for kicking calculations
- **Implement distance-based field goal accuracy
- **Unit tests for special teams calculations**

### Phase 4: Integration & Polish (Week 4)
- **Dependency injection setup** for engine selection
- **Integration tests** with full play execution
- **Performance testing** and optimization
- **Documentation updates**

## Unit Testing Strategy

### Test Structure
```
tests/
├── unit/
│   ├── engines/
│   │   ├── test_blocking_engine.py
│   │   ├── test_coverage_engine.py
│   │   └── test_outcome_engine.py
│   ├── plays/
│   │   ├── test_run_play.py
│   │   ├── test_pass_play.py
│   │   ├── test_kick_play.py
│   │   └── test_punt_play.py
│   └── integration/
│       └── test_play_execution_flow.py
```

### Key Test Cases

**Blocking Engine Tests:**
```python
def test_individual_matchup_elite_vs_average():
    """Elite OL (90) vs Average DL (70) should favor blocker"""
    elite_ol = create_test_ol(run_blocking=90, technique=85)
    avg_dl = create_test_dl(run_defense=70, power_moves=75)
    
    result = engine.calculate_individual_matchup(elite_ol, avg_dl, "run_blocking")
    
    assert result.blocker_success > 0.6
    assert result.rusher_success < 0.4

def test_fatigue_affects_blocking():
    """Fatigued players should perform worse"""
    fresh_ol = create_test_ol(run_blocking=80, fatigue=100)
    tired_ol = create_test_ol(run_blocking=80, fatigue=60)
    same_dl = create_test_dl(run_defense=80)
    
    fresh_result = engine.calculate_individual_matchup(fresh_ol, same_dl, "run_blocking")
    tired_result = engine.calculate_individual_matchup(tired_ol, same_dl, "run_blocking")
    
    assert fresh_result.blocker_success > tired_result.blocker_success

def test_formation_modifier_applied():
    """Formation advantages should affect blocking efficiency"""
    goal_line_result = engine.calculate_with_formation("goal_line", "run")
    shotgun_result = engine.calculate_with_formation("shotgun", "run")
    
    assert goal_line_result.efficiency_rating > shotgun_result.efficiency_rating
```

**Play Type Tests:**
```python  
def test_run_play_uses_rb_attributes():
    """Run plays should factor in RB vision, power, elusiveness"""
    power_rb = create_test_rb(power=90, vision=60, elusiveness=60)
    elusive_rb = create_test_rb(power=60, vision=60, elusiveness=90)
    
    # Same blocking, different RB types
    power_result = run_play.simulate(personnel_with_rb(power_rb), field_state)
    elusive_result = run_play.simulate(personnel_with_rb(elusive_rb), field_state)
    
    # Both should be effective but in different ways
    assert power_result.yards_gained >= 0  # Power RB fights for yards
    assert elusive_result.big_play_chance > power_result.big_play_chance

def test_pass_play_pressure_affects_outcome():
    """Pass rush pressure should reduce completion probability"""
    good_protection = create_personnel_package(ol_rating=90, dl_rating=70)
    poor_protection = create_personnel_package(ol_rating=70, dl_rating=90)
    
    good_result = pass_play.simulate(good_protection, field_state)
    poor_result = pass_play.simulate(poor_protection, field_state)
    
    # Poor protection should lead to more sacks/incompletions
    assert good_result.completion_rate > poor_result.completion_rate
    assert poor_result.sack_probability > good_result.sack_probability
```

**Integration Tests:**
```python
def test_full_play_execution_with_engines():
    """End-to-end test of play execution with calculation engines"""
    personnel = create_realistic_personnel_package()
    field_state = create_test_field_state()
    
    result = play_executor.execute_play(offense_team, defense_team, game_state)
    
    assert result.formation is not None
    assert result.defensive_call is not None
    assert result.yards_gained is not None
    assert hasattr(result, 'blocking_efficiency')  # Engine results included
    assert hasattr(result, 'coverage_efficiency')
```

## Success Metrics

### Functional Success
- [ ] All play types use sophisticated individual player calculations
- [ ] Formation advantages create measurable tactical differences (10-25% impact)
- [ ] Fatigue affects performance consistently across all play types
- [ ] Individual player attributes (vision, power, technique) influence outcomes
- [ ] Calculation engines are reusable across multiple play types

### Code Quality Success  
- [ ] SOLID principles followed in all new code
- [ ] Unit test coverage > 90% for calculation engines
- [ ] Integration tests verify end-to-end functionality
- [ ] No code duplication in calculation logic
- [ ] Clean dependency injection for testability

### Performance Success
- [ ] Play simulation performance not degraded by engine complexity
- [ ] Individual player calculations complete in <10ms per play
- [ ] Memory usage reasonable with detailed player objects
- [ ] No performance regression in existing functionality

## Risk Mitigation

### Risk: Increased Complexity
- **Mitigation:** Incremental implementation, comprehensive testing
- **Monitoring:** Code complexity metrics, performance benchmarks

### Risk: Over-Engineering  
- **Mitigation:** YAGNI principles, build only what's needed now
- **Validation:** Regular review of actual usage vs planned features

### Risk: Performance Impact
- **Mitigation:** Profile before/after, optimize hot paths
- **Fallback:** Team rating mode for performance-critical scenarios

This architecture will create realistic, detailed play calculations while maintaining clean, testable code that follows best practices.