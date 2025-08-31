# Situational Matchup Matrix Algorithm Implementation Plan

## Overview

This plan implements a **Situational Matchup Matrix Algorithm** for calculating rushing yards in `run_play.py`. The algorithm uses **situation-specific formulas** that match real NFL run concepts, following KISS, SOLID, and YAGNI principles.

## Core Principles Applied

### **KISS (Keep It Simple, Stupid)**
- Single responsibility: Replace one method (`_simulate_personnel_run`) with cleaner logic
- Simple data structures: Use dictionaries for matchup matrices (no complex classes)
- Clear flow: Run type → RB effectiveness → Yards calculation

### **SOLID Principles**
- **Single Responsibility**: Each method has one clear purpose
- **Open/Closed**: New run types can be added via configuration without modifying existing code
- **Liskov Substitution**: All run type calculators follow the same interface
- **Interface Segregation**: Clean separation between run classification and yards calculation
- **Dependency Inversion**: Algorithm depends on abstractions (RB attributes) not concrete implementations

### **YAGNI (You Aren't Gonna Need It)**
- Only implement 5 core run types (not 15+ variations)
- Simple breakaway logic (not complex physics)
- Basic situational modifiers (not weather, crowd noise, etc.)
- No caching or optimization until needed

## Files to be Modified

### **Primary Changes**

#### 1. `/src/game_engine/plays/run_play.py`
**Modifications:**
- Replace `_simulate_personnel_run()` method with new matchup matrix logic
- Add 4 new helper methods:
  - `_determine_run_type()`
  - `_calculate_rb_effectiveness_for_run_type()`
  - `_calculate_yards_from_matchup_matrix()`
  - `_apply_situational_modifiers()`
- Add `MATCHUP_MATRICES` constant (configuration data)

**Lines affected:** ~65 lines (current method ~64 lines, replacement ~80 lines)

### **Testing Files**

#### 2. `/test_run_algorithm.py` (new file)
**Purpose:** Comprehensive testing of the new algorithm
- Unit tests for each run type
- RB attribute effectiveness tests
- Situational modifier validation
- Statistical distribution validation

#### 3. Update existing `/test_personnel_selection.py`
**Modifications:** Add test cases for new run type classification

### **No Changes Required**
- PersonnelPackage interface remains unchanged
- FieldState interface remains unchanged  
- PlayResult structure unchanged
- Database models unchanged

## Implementation Details

### **1. Run Type Classification (KISS)**
```python
def _determine_run_type(self, formation: str, field_state: FieldState) -> str:
    """Simple classification based on formation and situation"""
    
    # Goal line situations (YAGNI: only basic goal line logic)
    if field_state.is_goal_line() and field_state.is_short_yardage():
        return "goal_line_power"
    
    # Formation-based classification (SOLID: Open/Closed via dictionary)
    formation_to_run_type = {
        "I_formation": "power_run",
        "goal_line": "goal_line_power", 
        "singleback": "inside_zone",
        "shotgun": "draw_play",
        "pistol": "inside_zone"
    }
    
    return formation_to_run_type.get(formation, "inside_zone")  # Safe default
```

### **2. Matchup Matrices (KISS Configuration)**
```python
# Simple dictionary structure - easy to understand and modify
MATCHUP_MATRICES = {
    "power_run": {
        "rb_attributes": ["power", "vision"],  # Only essential attributes
        "base_yards": 3.5,
        "ol_modifier": 1.3,
        "dl_modifier": 1.2,
        "variance": 0.8
    },
    "outside_zone": {
        "rb_attributes": ["speed", "agility"], 
        "base_yards": 3.0,
        "ol_modifier": 1.0,
        "dl_modifier": 0.8, 
        "variance": 1.3
    },
    "inside_zone": {
        "rb_attributes": ["vision", "agility"],
        "base_yards": 3.8,
        "ol_modifier": 1.1,
        "dl_modifier": 1.0,
        "variance": 1.0
    },
    "draw_play": {
        "rb_attributes": ["vision", "elusiveness"],
        "base_yards": 4.5,
        "ol_modifier": 0.9,
        "dl_modifier": 0.7,
        "variance": 1.4
    },
    "goal_line_power": {
        "rb_attributes": ["power", "strength"],
        "base_yards": 1.5,
        "ol_modifier": 1.4,
        "dl_modifier": 1.3,
        "variance": 0.6
    }
}
```

### **3. RB Effectiveness Calculator (SOLID: Single Responsibility)**
```python
def _calculate_rb_effectiveness_for_run_type(self, rb, run_type: str) -> float:
    """Calculate RB effectiveness for specific run type"""
    
    if not rb:
        return 0.5  # Default
    
    # SOLID: Dependency Inversion - depends on RB interface, not implementation
    matrix = MATCHUP_MATRICES[run_type]
    total_rating = 0
    
    for attribute in matrix["rb_attributes"]:
        rating = getattr(rb, attribute, 50)  # Safe attribute access
        total_rating += rating
    
    # Simple average calculation (KISS)
    avg_rating = total_rating / len(matrix["rb_attributes"])
    return avg_rating / 100  # Normalize to 0-1
```

### **4. Main Yards Calculation (KISS Logic Flow)**
```python
def _calculate_yards_from_matchup_matrix(self, offense_ratings, defense_ratings, 
                                       personnel, formation_modifier, field_state):
    """Main calculation method - clear single responsibility"""
    
    # Step 1: Determine run type
    run_type = self._determine_run_type(personnel.formation, field_state)
    matrix = MATCHUP_MATRICES[run_type]
    
    # Step 2: Calculate RB effectiveness  
    rb_effectiveness = self._calculate_rb_effectiveness_for_run_type(
        personnel.rb_on_field, run_type
    )
    
    # Step 3: Calculate blocking effectiveness (KISS formula)
    ol_rating = offense_ratings.get('ol', 50)
    dl_rating = defense_ratings.get('dl', 50) 
    blocking_effectiveness = (ol_rating * matrix["ol_modifier"]) / (dl_rating * matrix["dl_modifier"])
    
    # Step 4: Combine factors (simple weighted average)
    combined_effectiveness = (rb_effectiveness * 0.5 + blocking_effectiveness * 0.5) * formation_modifier
    
    # Step 5: Apply to base yards with variance
    base_yards = matrix["base_yards"] * combined_effectiveness
    variance = random.uniform(0.7, 1.0 + matrix["variance"] * 0.3)
    final_yards = base_yards * variance
    
    # Step 6: Apply situational modifiers
    final_yards = self._apply_situational_modifiers(final_yards, field_state, run_type)
    
    return max(0, int(final_yards))
```

## Testing Strategy (Testable Design)

### **Unit Tests**
```python
class TestSituationalMatchupMatrix:
    
    def test_run_type_classification(self):
        """Test run type determination"""
        # Test each formation -> run type mapping
        # Test goal line situations
        # Test edge cases with invalid formations
    
    def test_rb_effectiveness_calculation(self):
        """Test RB attribute integration"""  
        # Test power back vs power runs (should be high effectiveness)
        # Test speed back vs outside zone (should be high effectiveness)
        # Test mismatched RB types (should be lower effectiveness)
        
    def test_yards_calculation_ranges(self):
        """Test yards fall within expected ranges"""
        # Power runs: 1-8 yards typical
        # Outside zone: 0-12 yards typical  
        # Goal line: 0-3 yards typical
        
    def test_statistical_distribution(self):
        """Test 1000 runs produce realistic distributions"""
        # Average yards per attempt by run type
        # Variance matches expected ranges
        # Breakaway frequency appropriate
```

### **Integration Tests**
```python
def test_personnel_integration():
    """Test with real PersonnelPackage objects"""
    # Test individual_players mode
    # Test team ratings mode
    # Test fatigue impact
    
def test_field_state_integration():
    """Test situational modifiers"""
    # Test goal line scenarios
    # Test short yardage situations  
    # Test down/distance impacts
```

## Implementation Timeline

### **Week 1: Core Implementation (3 days)**
- Day 1: Implement `_determine_run_type()` and `MATCHUP_MATRICES`
- Day 2: Implement `_calculate_rb_effectiveness_for_run_type()`
- Day 3: Implement main `_calculate_yards_from_matchup_matrix()` method

### **Week 1: Testing (2 days)**
- Day 4: Write comprehensive unit tests
- Day 5: Integration testing and statistical validation

## Success Metrics

### **Functional Requirements**
- ✅ Power backs perform better on power runs than speed backs
- ✅ Speed backs perform better on outside zone than power backs  
- ✅ Goal line situations produce shorter, more consistent gains
- ✅ Draw plays have higher variance (boom/bust nature)
- ✅ All run types produce realistic yard distributions

### **Technical Requirements**
- ✅ Maintains existing interface (`personnel` → `PlayResult`)
- ✅ No performance regression (<2ms execution time)
- ✅ 100% unit test coverage for new methods
- ✅ Statistical validation passes (realistic NFL-like distributions)

### **Quality Requirements**
- ✅ Code follows SOLID principles
- ✅ New run types can be added via configuration only
- ✅ Methods have single, clear responsibilities
- ✅ No unnecessary complexity (YAGNI compliance)

## Risk Mitigation

### **Low Risk**
- **Breaking changes**: Same interface maintained
- **Performance**: Simple calculations, no complex operations
- **Testing**: Isolated, testable methods

### **Medium Risk** 
- **Statistical accuracy**: Requires tuning matchup matrices
- **Mitigation**: Extensive testing with 1000+ simulation runs

### **Rollback Plan**
- Keep existing `_simulate_personnel_run()` method as `_simulate_personnel_run_legacy()`
- Feature flag to switch between old/new algorithms
- Quick rollback if issues discovered

## Expected Outcomes

### **Immediate Benefits**
- More realistic rushing performance based on RB types
- Authentic NFL run concepts (power vs speed vs vision)
- Situational awareness (goal line, short yardage)

### **Long-term Benefits**  
- Easy to add new run types via configuration
- Clear separation of concerns for future enhancements
- Solid foundation for more advanced features

### **Code Quality Improvements**
- Better adherence to SOLID principles
- More testable architecture
- Cleaner, more maintainable code

## Conclusion

This plan delivers a **realistic, testable, and maintainable** rushing algorithm that follows software engineering best practices while staying true to authentic NFL concepts. The implementation focuses on **essential features only** (YAGNI) with **simple, clear logic** (KISS) and **proper separation of concerns** (SOLID).