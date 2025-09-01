# Play Calling Logic Architecture

**High-Level Documentation of Play Calling Flow and Decision Making**

*Version: 1.0 | Last Updated: Current Implementation*

---

## Executive Summary

The play calling system implements **intelligent, archetype-based coaching decisions** that simulate realistic NFL play calling patterns. The system processes game situation through multiple layers of decision-making logic to determine the most appropriate play type (run, pass, punt, field goal) based on coaching philosophy, defensive matchups, and contextual factors.

---

## 1. High-Level Flow Overview

```
GAME LOOP REQUEST
       ↓
PLAY EXECUTOR (Orchestrator)
       ↓
PLAY CALLING SYSTEM
       ↓
[6-Step Decision Pipeline]
       ↓
PLAY TYPE SELECTION
       ↓
PLAY FACTORY & EXECUTION
       ↓
PLAY RESULT
```

### Primary Entry Point: `PlayExecutor.execute_play()`

**Location**: `src/game_engine/core/play_executor.py`

The PlayExecutor serves as the **orchestrator** that coordinates all play execution components:

1. **Input Processing**: Receives offense team, defense team, and current game state
2. **Play Type Determination**: Uses intelligent play calling system 
3. **Personnel Selection**: Selects appropriate players for the play
4. **Play Execution**: Creates and executes the specific play instance
5. **Time Management**: Applies archetype-based clock usage
6. **Result Processing**: Returns complete play result

---

## 2. Play Calling Decision Pipeline (6 Steps)

**Location**: `src/game_engine/plays/play_calling.py`

The core intelligence resides in `PlayCaller.determine_play_type()` which follows this **6-step pipeline**:

### Step 1: Situation Classification
```python
situation = self._classify_game_situation(field_state)
```

**Purpose**: Categorize current game context into discrete situations

**Logic**:
- Analyzes **Down** (1st, 2nd, 3rd, 4th) 
- Analyzes **Distance** (short ≤3, medium 4-7, long 8+)
- Creates situation keys: `"1st_and_10"`, `"3rd_and_long"`, `"4th_and_short"`, etc.

**Output**: Situation string for probability lookup

---

### Step 2: Base Probability Retrieval
```python
base_probabilities = PlayCallingBalance.BASE_PLAY_TENDENCIES[situation]
```

**Purpose**: Establish NFL-realistic baseline probabilities

**Data Source**: `PlayCallingBalance.BASE_PLAY_TENDENCIES`
- Contains **NFL-average probabilities** for each situation
- Examples:
  - `"1st_and_10": {"run": 0.45, "pass": 0.55}`
  - `"3rd_and_long": {"pass": 0.75, "run": 0.25}`
  - `"4th_and_short": {"run": 0.30, "pass": 0.15, "field_goal": 0.30, "punt": 0.25}`

**Configuration**: Centralized in `PlayCallingBalance` class with validation

---

### Step 3: Offensive Archetype Modification
```python
modified_probabilities = self._apply_offensive_archetype(base_probabilities, offensive_coordinator, field_state)
```

**Purpose**: Apply coaching philosophy to base probabilities

**Archetype System**: Six distinct offensive philosophies:

#### 3a. Conservative Archetype
- **Philosophy**: `"minimize_risk_maximize_field_position"`
- **Key Traits**:
  - Low 4th down aggressiveness (12%)
  - Prefers field goals in red zone
  - Punts more frequently
  - Runs more in own territory

#### 3b. Aggressive Archetype  
- **Philosophy**: `"maximum_scoring_opportunities"`
- **Key Traits**:
  - High 4th down attempts (25%)
  - Red zone touchdown focus (80% passing)
  - Goes for it instead of field goals
  - Deep passing emphasis

#### 3c. West Coast Archetype
- **Philosophy**: `"short_passing_precision_offense"`
- **Key Traits**:
  - 80% short pass emphasis
  - High play action usage (35%)
  - Pass-heavy on all downs
  - YAC-focused route concepts

#### 3d. Run Heavy Archetype
- **Philosophy**: `"ground_and_pound_control"`
- **Key Traits**:
  - 60% run play ratio
  - Power formation preference
  - Time of possession focus
  - Runs in short yardage situations

#### 3e. Air Raid Archetype
- **Philosophy**: `"high_tempo_passing_attack"`
- **Key Traits**:
  - 70% pass frequency
  - 25% deep pass rate
  - High tempo preference
  - Vertical route emphasis

#### 3f. Balanced Archetype
- **Philosophy**: `"situational_football"`
- **Key Traits**:
  - High adaptability (85%)
  - Minimal extreme modifiers
  - Sticks close to base probabilities
  - Situationally appropriate decisions

**Modifier Application**:
```python
# Situation-specific modifiers
if situation in situation_modifiers:
    modified_probs[play_type] += modifier

# Field position modifiers  
if position_context in field_position_modifiers:
    modified_probs[play_type] += modifier

# Custom modifiers from team data
modified_probs[play_type] += custom_modifier_value
```

---

### Step 4: Defensive Influence Application
```python
modified_probabilities = self._apply_defensive_influence(modified_probabilities, defensive_coordinator, field_state)
```

**Purpose**: Counter-adjust play calling based on defensive schemes

**Defensive Archetype System**: Six defensive philosophies that **influence offensive decisions**:

#### 4a. Blitz Heavy Defense
- **Counter-Effects on Offense**:
  - `+15% quick passes` (beat the pressure)
  - `+10% screen frequency` (use aggression against them)
  - `-20% deep passes` (no time for routes to develop)
  - `+15% shotgun formations` (faster release)

#### 4b. Run Stuffing Defense
- **Counter-Effects on Offense**:
  - `+20% pass frequency` (avoid strong run defense)
  - `-25% power runs` (their strength)
  - `+15% outside runs` (get away from interior)
  - `+10% short passes` (quick game as run replacement)

#### 4c. Zone Coverage Defense
- **Counter-Effects on Offense**:
  - `+20% underneath passes` (exploit zone holes)
  - `-15% deep passes` (safety help over top)
  - `+15% crossing routes` (attack zone seams)
  - `+8% run frequency` (zones vulnerable to run)

#### 4d. Man Coverage Defense
- **Counter-Effects on Offense**:
  - `+25% pick plays` (rubs/screens vs man)
  - `+15% speed routes` (beat man coverage with speed)
  - `+12% motion plays` (create mismatches)
  - `-15% comeback routes` (tough vs tight coverage)

#### 4e. Bend Don't Break Defense
- **Counter-Effects on Offense**:
  - `+15% red zone aggression` (can't settle for FGs)
  - `-10% field goals` (defense forces tough decisions)
  - `+8% 4th down attempts` (need TDs vs bend-don't-break)
  - `+15% quick slants` (attack tight coverage quickly)

#### 4f. Balanced Defense
- **Counter-Effects on Offense**:
  - Minimal adjustments (no major weaknesses to exploit)
  - `+5% situational awareness` (execution becomes key)

---

### Step 5: Enhanced Contextual Factor Application with Game Context Detection
```python
final_probabilities = self._apply_contextual_factors(modified_probabilities, field_state, game_context)
```

**Purpose**: Apply advanced game context adjustments with intelligent scenario detection

**Enhanced Contextual Intelligence**:

#### 5a. Game Context Detection Framework
The system now detects and responds to critical game contexts:

- **Desperation Mode** (Trailing by 14+ with <8 minutes):
  - `+25% pass frequency` (must throw to catch up)
  - `+15% 4th down attempts` (aggressive play calling)
  - `-30% field goal attempts` (need touchdowns, not field goals)

- **Protect Lead Mode** (Leading by 10+ with <6 minutes):
  - `+20% run frequency` (control clock and field position)
  - `+10% field goal acceptance` (take points when available)
  - `-15% 4th down attempts` (avoid turnovers)

- **Two-Minute Drill** (Final 2 minutes of half/game):
  - `+30% pass frequency` (stop clock on incompletions)
  - `+50% timeout usage intelligence` (manage clock effectively)
  - `+20% deep pass attempts` (maximize yards per play)

- **Goal Line Situations** (Field Position 95+):
  - `+40% power run attempts` (punch it in)
  - `+20% play action frequency` (capitalize on run fake)
  - `+15% quarterback sneak probability` (short yardage specialist)

#### 5b. Advanced Field Position Context
- **Red Zone** (Field Position 80+):
  - `+8% pass attempts` (increased from +5% - go for TDs)
  - `-15% punt probability` (increased from -10% - almost never punt)
  - `+12% play action usage` (defense expects run in red zone)

- **Deep Territory** (Field Position ≤20):
  - `+5% run plays` (increased from +3% - more conservative)
  - `-4% pass plays` (increased from -2% - reduce turnover risk)
  - `+8% punt acceptance` (field position is critical)

- **Field Goal Range** (Field Position 60-79):
  - `+15% field goal consideration` (points are valuable)
  - `+5% conservative play calling` (don't risk losing field goal range)
  - `-10% 4th down attempts` (take the points)

#### 5c. Score Differential Intelligence
- **Close Games** (Score differential ≤3):
  - `+10% field goal acceptance` (every point matters)
  - `+8% conservative play calling` (avoid turnovers)
  - `+15% situational awareness` (field position emphasis)

- **Blowouts** (Score differential ≥21):
  - `+25% run frequency` (control game tempo)
  - `-20% deep pass attempts` (don't run up score)
  - `+30% backup player usage` (rest starters)

#### 5d. Time Remaining Context
- **Early Game** (1st-2nd Quarter):
  - Standard play calling with slight script emphasis
  - `+5% establish-the-run mentality`

- **Crunch Time** (4th Quarter, <10 minutes):
  - Context becomes primary decision factor
  - Score differential weighs heavily in decisions
  - Clock management becomes critical

#### 5e. Strategic Field Goal Logic
Intelligent field goal decision making based on multiple factors:

- **Range Assessment**:
  - 0-35 yards: 95% make probability consideration
  - 36-45 yards: 85% make probability consideration  
  - 46-55 yards: 70% make probability consideration
  - 56+ yards: Situational only (desperation, end of half)

- **Situational Modifiers**:
  - End of half: `+40% field goal attempts` (points before halftime)
  - 4th down in range: Weigh field goal vs. going for it
  - Weather conditions: Reduce long field goal attempts in bad weather

#### 5f. Enhanced 4th Down Intelligence
Sophisticated 4th down decision trees:

- **4th and 1-2 (Short)**:
  - Field position ≥35: 65% go for it
  - Field position 20-34: 45% go for it  
  - Field position ≤19: 25% go for it

- **4th and 3-5 (Medium)**:
  - Red zone: 70% go for it (need touchdowns)
  - Opponent territory: 35% go for it
  - Own territory: 15% go for it

- **Context Override Factors**:
  - Desperation mode: +50% go for it frequency
  - Protect lead mode: -30% go for it frequency
  - Two-minute drill: Situational based on field position and timeouts

---

### Step 6: Selection and Normalization
```python
return self._make_weighted_selection(final_probabilities)
```

**Purpose**: Convert probabilities into actual play type selection

**Process**:
1. **Bounds Enforcement**:
   - Minimum probability: 1% (no play type completely eliminated)
   - Maximum probability: 95% (always some uncertainty)

2. **Probability Normalization**:
   - Ensures all probabilities sum to 1.0
   - Handles edge cases where modifiers create invalid totals

3. **Weighted Random Selection**:
   - Uses cumulative probability distribution
   - Provides deterministic randomness for realistic variability

4. **Fallback Protection**:
   - Returns safe default if probability calculation fails

---

## 3. Integration Points

### 3.1 Coaching Staff Integration

**Dynamic Coaching System**: `PlayExecutor` integrates with `CoachingStaff` for contextual adaptation:

```python
# Dynamic coaching - adapts to game context
coaching_staff = offense_team.get('coaching_staff')
if coaching_staff:
    game_context = {
        'opponent': defense_team,
        'score_differential': game_state.get_score_differential(),
        'time_remaining': game_state.clock.get_time_remaining(),
        'field_position': game_state.field.field_position,
        'down': game_state.field.down,
        'yards_to_go': game_state.field.yards_to_go
    }
    offensive_coordinator = coaching_staff.get_offensive_coordinator_for_situation(game_state.field, game_context)
```

**Features**:
- **Adaptive Coordination**: Coaches adjust based on opponent and game flow
- **Situational Specialization**: Different coordinators for different situations
- **Bidirectional Intelligence**: Offensive and defensive coordinators counter each other

### 3.2 Personnel Selection Integration

After play type determination:
```python
personnel = self.player_selector.get_personnel(offense_team, defense_team, play_type, game_state.field, config)
```

**Integration Flow**:
- Play calling determines **WHAT** to do (run/pass/punt/kick)
- Personnel selection determines **WHO** executes it
- Play factory determines **HOW** it's executed

### 3.3 Clock Management Integration

```python
time_elapsed = clock_strategy_manager.calculate_time_usage(
    play_result, offense_archetype, game_context, completion_status
)
```

**Features**:
- **Archetype-based timing**: Different coaches use clock differently
- **Situational awareness**: Time usage varies by game situation
- **Realistic pacing**: Matches NFL timing patterns per coaching style

---

## 4. Configuration and Tuning

### 4.1 Centralized Configuration

**Location**: `PlayCallingBalance` class

**Purpose**: Single location for all tuning parameters

**Key Configuration Areas**:
```python
# Distance thresholds
SHORT_YARDAGE_THRESHOLD = 3
MEDIUM_YARDAGE_MAX = 7
LONG_YARDAGE_THRESHOLD = 8

# Field position thresholds  
RED_ZONE_THRESHOLD = 80
FIELD_GOAL_RANGE_THRESHOLD = 65
DEEP_TERRITORY_THRESHOLD = 20

# Influence weights
FIELD_POSITION_WEIGHT = 0.15
SCORE_DIFFERENTIAL_WEIGHT = 0.10
TIME_REMAINING_WEIGHT = 0.12
PERSONNEL_MATCHUP_WEIGHT = 0.08

# Modifier limits
MAX_SITUATION_MODIFIER = 0.30
MIN_PROBABILITY = 0.01
MAX_PROBABILITY = 0.95
```

### 4.2 Validation System

**Configuration Validation**: Ensures system integrity
```python
@classmethod
def validate_configuration(cls):
    # Probabilities sum to 1.0
    # Weights are reasonable (0-1)
    # Thresholds make logical sense
    # Modifier limits are safe
```

**Runtime Validation**: Called on system initialization

---

## 5. Data Flow Architecture

### 5.1 Input Data Structure

**Offensive Team Structure**:
```python
offense_team = {
    'coaching_staff': CoachingStaff,           # Dynamic coaching system
    'coaching': {                              # Legacy fallback
        'offensive_coordinator': {
            'archetype': 'aggressive',
            'custom_modifiers': {...}
        }
    },
    'ratings': {...},                          # Team capabilities
    'players': {...}                           # Individual player data
}
```

**Game State Structure**:
```python  
game_state = {
    'field': {
        'down': 1-4,
        'yards_to_go': int,
        'field_position': 0-100,
        'possession_team_id': int
    },
    'clock': {
        'quarter': 1-5+,
        'time_remaining': int,
        'is_playoff_game': bool
    },
    'scoreboard': {
        'home_score': int,
        'away_score': int,
        'score_differential': int
    }
}
```

### 5.2 Output Data Structure

**Play Type Selection**:
```python
play_type = "run" | "pass" | "punt" | "field_goal"
```

**Decision Audit Trail** (implicit):
- Base probabilities from NFL data
- Archetype modifications applied
- Defensive influence factors
- Contextual adjustments
- Final normalized probabilities

---

## 6. System Architecture Patterns

### 6.1 Strategy Pattern Implementation

**Play Calling Strategy**: Different archetypes implement different strategies
```python
# Each archetype defines its own modification strategy
OFFENSIVE_ARCHETYPES = {
    'conservative': {strategy_definition},
    'aggressive': {strategy_definition},
    'west_coast': {strategy_definition}
}
```

**Benefits**:
- Easy to add new coaching archetypes
- Clear separation of concerns
- Testable strategy components

### 6.2 Configuration-Driven Design

**Centralized Configuration**: All tuning parameters in one location
- Easy for game designers to balance
- Clear validation and bounds checking
- Single source of truth for all constants

**Archetype Matrix System**: Similar to established punt/pass patterns
- Consistent architecture across all play types
- Proven pattern for complex decision-making
- Extensible for additional factors

### 6.3 Layered Decision Making

**Multi-Layer Processing**: Each layer adds intelligence
1. **Base Layer**: NFL statistical reality
2. **Philosophy Layer**: Coaching archetype preferences  
3. **Counter-Intelligence Layer**: Defensive matchup considerations
4. **Context Layer**: Game situation adjustments
5. **Selection Layer**: Probabilistic decision making

**Benefits**:
- Realistic baseline behavior
- Coaching personality expression
- Dynamic adaptation to opponents
- Contextual intelligence

---

## 7. Extensibility Framework

### 7.1 Adding New Archetypes

**Process**:
1. Add archetype to `OFFENSIVE_ARCHETYPES` dict
2. Define philosophy and key traits
3. Specify situation modifiers
4. Add field position modifiers
5. Define game situation modifiers

**Example Template**:
```python
"new_archetype": {
    "philosophy": "description_of_approach",
    "key_trait_1": value,
    "key_trait_2": value,
    "situation_modifiers": {
        "3rd_and_long": {"pass": +0.10, "run": -0.05}
    },
    "field_position_modifiers": {...},
    "game_situation_modifiers": {...}
}
```

### 7.2 Adding New Contextual Factors

**Framework Exists** in `_apply_contextual_factors()`:
- Score differential logic
- Time remaining urgency
- Weather conditions
- Personnel mismatches
- Injury situations

**Implementation Pattern**:
```python
# Add new contextual check
if new_context_condition:
    modified_probs[play_type] += context_modifier
```

### 7.3 Adding New Defensive Archetypes

**Process**: Similar to offensive archetypes
- Define defensive philosophy
- Specify offensive counter-effects
- Add situational specializations

---

## 8. Testing and Validation

### 8.1 Configuration Validation

**Automatic Validation**: Run on system initialization
- Probability consistency checks
- Parameter bounds verification
- Logical relationship validation

### 8.2 Probability Distribution Testing

**Recommended Tests**:
- Verify archetype probability distributions match expectations
- Test defensive influence effects
- Validate contextual adjustments
- Ensure no impossible probability combinations

### 8.3 Integration Testing

**Full Pipeline Tests**:
- Test complete play calling pipeline
- Verify coaching staff integration
- Validate personnel selection integration
- Test with various game state scenarios

---

## 9. Performance Considerations

### 9.1 Computational Efficiency

**Design Optimizations**:
- Dictionary lookups for archetype data (O(1))
- Minimal computational overhead per decision
- No complex mathematical operations
- Efficient probability normalization

### 9.2 Memory Usage

**Memory Efficiency**:
- Static configuration data (loaded once)
- Minimal temporary objects during calculation
- No persistent state between decisions

---

## 10. Future Enhancement Opportunities

### 10.1 Machine Learning Integration

**Potential Enhancements**:
- Train on real NFL play-by-play data
- Dynamic archetype learning from coach behavior
- Opponent-specific adaptation over multiple games

### 10.2 Advanced Contextual Intelligence

**Additional Context Factors**:
- Player fatigue and substitution patterns
- Injury report impact on play calling
- Weather and field condition considerations
- Historical matchup data

### 10.3 Analytics and Reporting

**Potential Analytics**:
- Play calling tendency reports per archetype
- Effectiveness analysis vs. different defenses
- Situational success rate tracking
- Archetype vs. archetype matchup matrices

### Section 2.7: Post-Play Decision Logic (Two-Point Conversions)

**Location**: `PlayExecutor.post_play_decisions()` (future implementation)

**Purpose**: Handle post-touchdown decisions including two-point conversion attempts

#### Two-Point Conversion Decision Matrix

The system evaluates two-point conversion attempts based on:

**Score Differential Analysis**:
- Down by 14: Always kick extra point (need two TDs regardless)
- Down by 15: Consider two-point (get within 13, then TD + XP ties)
- Down by 8: High two-point consideration (ties game with single score)
- Down by 2: Always go for two (takes the lead)
- Down by 1: Game-winning two-point attempt

**Time Remaining Factors**:
- >10 minutes: Conservative, usually kick extra point
- 5-10 minutes: Moderate two-point consideration based on score
- <5 minutes: Aggressive two-point based on game theory
- <2 minutes: Maximum two-point consideration if it changes strategy

**Archetype Influence**:
- **Aggressive**: +25% two-point attempt rate
- **Conservative**: -15% two-point attempt rate  
- **Analytics-driven**: Game theory optimal decisions
- **Traditional**: Rare two-point attempts except obvious situations

**Field Goal Range Consideration**:
- If opponent likely to respond with field goal: Factor in 3-point deficit
- If opponent must score touchdown: Different strategic calculation

---

## 3. Enhanced Critical Context Integration Points

### 3.1 Dynamic Coaching Staff Integration

**Advanced Coaching System**: `PlayExecutor` now integrates with sophisticated `CoachingStaff` for contextual adaptation:

```python
# Enhanced dynamic coaching - deep contextual adaptation
coaching_staff = offense_team.get('coaching_staff')
if coaching_staff:
    game_context = {
        'opponent': defense_team,
        'score_differential': game_state.get_score_differential(),
        'time_remaining': game_state.clock.get_time_remaining(),
        'field_position': game_state.field.field_position,
        'down': game_state.field.down,
        'yards_to_go': game_state.field.yards_to_go,
        'quarter': game_state.clock.quarter,
        'game_situation': self._detect_game_situation(game_state),  # New
        'momentum': self._calculate_momentum(recent_plays),         # New
        'weather': game_state.get_weather(),                       # New
        'injury_report': team.get_injury_status()                  # New
    }
    offensive_coordinator = coaching_staff.get_offensive_coordinator_for_situation(
        game_state.field, game_context
    )
```

**Enhanced Features**:
- **Adaptive Coordination**: Coaches adjust based on opponent, game flow, and momentum
- **Situational Specialization**: Different coordinator "personalities" for different contexts
- **Counter-Intelligence**: Offensive and defensive coordinators actively counter each other
- **Learning System**: Coaches learn from previous plays and adapt within the game
- **Memory System**: Coaches remember opponent tendencies from previous games

### 3.2 Enhanced Personnel Selection Integration

After contextual play type determination:
```python
personnel = self.player_selector.get_personnel(
    offense_team, defense_team, play_type, game_state.field, config,
    context_factors=context_analysis  # New parameter
)
```

**Enhanced Integration Flow**:
- Play calling determines **WHAT** to do with contextual intelligence
- Personnel selection determines **WHO** executes it based on matchups
- Play factory determines **HOW** it's executed with situational adjustments
- Clock management applies **WHEN** timing based on game context

### 3.3 Advanced Clock Management Integration

```python
time_elapsed = clock_strategy_manager.calculate_time_usage(
    play_result, offense_archetype, game_context, 
    completion_status, contextual_urgency  # New parameter
)
```

**Enhanced Features**:
- **Context-Aware Timing**: Clock usage varies dramatically by game situation
- **Urgency Detection**: Automatic detection of hurry-up vs. control situations
- **Archetype-Situation Matrix**: Different timing patterns per archetype per situation
- **Opponent Awareness**: Adjust tempo based on opponent's preferred pace

---

## 11. Critical Scenario Decision Trees

**Location**: `PlayCaller._evaluate_critical_scenarios()` (enhanced method)

**Purpose**: Handle high-stakes situations with specialized decision logic

### 11.1 Two-Minute Drill Decision Tree

```
TWO-MINUTE SITUATION
├── Leading by 3+
│   ├── Run clock, protect lead
│   ├── Conservative play calling
│   └── Take field goals if available
├── Trailing by 3-7
│   ├── Aggressive passing
│   ├── Timeout management critical
│   └── Field goal acceptable if time allows
├── Trailing by 8-14
│   ├── Must score touchdowns
│   ├── No field goals unless desperate
│   └── Maximum aggression on 4th down
└── Trailing by 15+
    ├── Onside kicks after scores
    ├── Go for everything
    └── Hail Mary situations
```

### 11.2 4th Down Decision Tree with Context

```
4TH DOWN SITUATION
├── 4th & 1-2 (Short)
│   ├── Own territory ≤30
│   │   ├── Punt (75%)
│   │   └── Go if desperate (25%)
│   ├── Midfield 31-50
│   │   ├── Team archetype dependent
│   │   └── Score/time dependent
│   └── Opponent territory 51+
│       ├── Go for it (65%)
│       └── Field goal if in range (35%)
├── 4th & 3-5 (Medium)
│   ├── Context heavily weighted
│   ├── Archetype determines baseline
│   └── Game situation overrides archetype
└── 4th & 6+ (Long)
    ├── Punt unless desperate
    ├── Field goal if reasonable range
    └── Go for it only in desperation
```

### 11.3 Red Zone Decision Tree

```
RED ZONE SITUATION (Field Position 80+)
├── Goal Line (95+)
│   ├── Power running emphasis (60%)
│   ├── Play action opportunities (25%)
│   └── Quick passes if run stuffed (15%)
├── Short Red Zone (85-94)
│   ├── Balanced but pass-heavy (55%)
│   ├── Exploit mismatches (30%)
│   └── Draw plays vs. pass rush (15%)
└── Long Red Zone (80-84)
    ├── Standard red zone (50/50)
    ├── Deep back corner routes (35%)
    └── Screen passes (15%)
```

---

## 12. Game Context Detection Framework

**Location**: `ContextAnalyzer` (new class)

**Purpose**: Automatically detect and classify game situations for intelligent response

### 12.1 Context Detection Modes

#### Primary Contexts:
- **Normal Flow**: Standard play calling applies
- **Two-Minute Drill**: Clock management critical, aggressive passing
- **Protect Lead**: Conservative play calling, clock control
- **Desperation Mode**: Maximum aggression, ignore traditional strategy
- **Garbage Time**: Rest players, control tempo, avoid injuries
- **Close Game**: Field position critical, turnover avoidance paramount

#### Secondary Contexts:
- **Momentum Shift**: Recent big plays affect decision making
- **Weather Impact**: Conditions affect play type preferences
- **Injury Concerns**: Key player availability affects strategy
- **Matchup Exploitation**: Specific personnel advantages

### 12.2 Context Detection Logic

```python
def detect_game_context(game_state: GameState, team_data: Dict) -> List[str]:
    contexts = []
    
    # Time-based contexts
    if game_state.is_two_minute_drill():
        contexts.append('two_minute_drill')
    
    # Score-based contexts  
    score_diff = game_state.get_score_differential()
    time_remaining = game_state.get_total_time_remaining()
    
    if score_diff >= 14 and time_remaining < 480:  # 8 minutes
        contexts.append('protect_lead')
    elif score_diff <= -14 and time_remaining < 480:
        contexts.append('desperation_mode')
    elif abs(score_diff) <= 3:
        contexts.append('close_game')
    elif abs(score_diff) >= 21:
        contexts.append('garbage_time')
    
    # Field position contexts
    if game_state.field.field_position >= 95:
        contexts.append('goal_line')
    elif game_state.field.field_position >= 80:
        contexts.append('red_zone')
    elif game_state.field.field_position <= 20:
        contexts.append('deep_territory')
    
    return contexts
```

---

## 13. Archetype Context Response Matrix

**Location**: `ArchetypeContextMatrix` (enhanced configuration)

**Purpose**: Define how each archetype responds to different game contexts

### 13.1 Context Response Mapping

#### Conservative Archetype Responses:
- **Two-Minute Drill**: Moderate aggression, field goal acceptable
- **Protect Lead**: Maximum clock control, ultra-conservative
- **Desperation**: Reluctant aggression, still punt in borderline situations  
- **Close Game**: Field position emphasis, avoid turnovers at all costs

#### Aggressive Archetype Responses:
- **Two-Minute Drill**: Maximum aggression, go for it on 4th
- **Protect Lead**: Still relatively aggressive, trust offense
- **Desperation**: All-out aggression, never punt
- **Close Game**: Go for the win, not the tie

#### Balanced Archetype Responses:
- **Two-Minute Drill**: Situational awareness, game theory optimal
- **Protect Lead**: Context-appropriate clock management
- **Desperation**: Calculated risks, strategic aggression
- **Close Game**: Field position and score differential balanced

### 13.2 Context Override Matrix

```python
CONTEXT_OVERRIDE_MATRIX = {
    'desperation_mode': {
        'conservative': {'pass_frequency': +0.35, '4th_down_aggression': +0.60},
        'aggressive': {'pass_frequency': +0.25, '4th_down_aggression': +0.40},
        'balanced': {'pass_frequency': +0.30, '4th_down_aggression': +0.50}
    },
    'protect_lead': {
        'conservative': {'run_frequency': +0.25, 'field_goal_acceptance': +0.30},
        'aggressive': {'run_frequency': +0.15, 'field_goal_acceptance': +0.20},
        'balanced': {'run_frequency': +0.20, 'field_goal_acceptance': +0.25}
    },
    'two_minute_drill': {
        'conservative': {'pass_frequency': +0.20, 'timeout_usage': +0.15},
        'aggressive': {'pass_frequency': +0.30, 'deep_pass_rate': +0.25},
        'balanced': {'pass_frequency': +0.25, 'situational_awareness': +0.20}
    }
}
```

---

## 14. Critical Decision Override System

**Location**: `DecisionOverrideManager` (new class)

**Purpose**: Handle situations where context overrides normal archetype behavior

### 14.1 Override Triggers

#### Automatic Overrides:
- **Game-Winning Field Goal**: Always attempt if <50 yards, regardless of archetype
- **Prevent Safety**: Never punt from own end zone, always go for it
- **Clock Exhaustion**: Final play scenarios override normal play calling
- **Injury Emergency**: Key player injury forces immediate strategy adjustment

#### Contextual Overrides:
- **Desperation Trailing**: Conservative coaches become aggressive
- **Protect Big Lead**: Aggressive coaches become conservative
- **Weather Emergency**: Outdoor game with severe conditions
- **Momentum Crisis**: Multiple consecutive failures force change

### 14.2 Override Decision Logic

```python
def evaluate_override_necessity(game_context: Dict, archetype: Dict) -> Optional[Dict]:
    overrides = {}
    
    # Critical game-winning scenarios
    if game_context.get('game_winning_opportunity'):
        overrides.update({
            'field_goal_range': 'always_attempt_if_makeable',
            '4th_down_aggression': 'context_dependent',
            'timeout_usage': 'maximize_opportunity'
        })
    
    # Prevent disaster scenarios
    if game_context.get('field_position') <= 5:
        overrides.update({
            'punt_frequency': 0.0,  # Never punt from own 5
            'safety_prevention': 'maximum_priority',
            'conservative_override': 'force_aggressive'
        })
    
    # Weather emergency overrides
    if game_context.get('weather_severity') >= 8:
        overrides.update({
            'run_frequency': +0.40,  # Heavy run emphasis
            'field_goal_range': -15,  # Reduce kicking range
            'punt_hang_time': 'wind_adjusted'
        })
    
    return overrides if overrides else None
```

### 14.3 Override Priority System

**Priority Levels** (highest to lowest):
1. **Safety Prevention**: Prevent safeties at all costs
2. **Game-Winning Opportunity**: Win the game when possible
3. **Clock Management Critical**: Proper time usage in crucial moments
4. **Score Differential Emergency**: Respond to game situation demands
5. **Weather/Injury Emergency**: External factor accommodations
6. **Momentum Shift Response**: Adapt to game flow changes

---

## Summary

The play calling system implements **advanced, contextually-intelligent NFL-style coaching decisions** through a sophisticated 6-step pipeline enhanced with contextual intelligence, dynamic coaching adaptation, and critical scenario handling that processes game situation, applies coaching philosophy, considers defensive matchups, and incorporates comprehensive contextual factors to make probabilistic play type selections.

**Enhanced Key Strengths**:
- **NFL Statistical Foundation**: Realistic baseline probabilities with contextual adjustments
- **Dynamic Coaching Intelligence**: Six distinct archetype philosophies with adaptive learning
- **Advanced Counter-Intelligence**: Bidirectional offensive/defensive coordinator adaptation
- **Comprehensive Contextual Awareness**: Game context detection, momentum tracking, and situational intelligence
- **Critical Scenario Handling**: Specialized decision trees for two-minute drill, 4th down, red zone, and desperation situations
- **Context Override System**: Automatic overrides for critical game situations
- **Archetype Context Response Matrix**: How each coaching style adapts to different game contexts
- **Post-Play Decision Logic**: Two-point conversion and strategic decision intelligence
- **Enhanced Clock Management**: Context-aware timing with urgency detection
- **Extensible Architecture**: Easy to add new contexts, archetypes, and decision factors
- **Configuration-Driven**: Centralized tuning for all contextual intelligence parameters

**Advanced Integration Points**:
- **Dynamic Coaching Staff System**: Adaptive coordinators with opponent memory and game flow learning
- **Enhanced Personnel Selection**: Context-aware player selection with matchup exploitation
- **Intelligent Clock Management**: Archetype and context-driven timing decisions
- **Game Context Detection**: Automatic situation recognition and response
- **Decision Override Management**: Critical situation handling with priority systems
- **Play Factory Execution Pipeline**: Context-enriched play execution

**Contextual Intelligence Modes**:
- **Normal Flow**: Standard archetype-based decisions
- **Two-Minute Drill**: Clock management and aggressive passing emphasis
- **Protect Lead**: Conservative clock control and field position focus
- **Desperation Mode**: Maximum aggression with traditional strategy abandonment
- **Close Game**: Field position critical with turnover avoidance
- **Garbage Time**: Player management and tempo control
- **Goal Line**: Power running and play action emphasis
- **Red Zone**: Touchdown priority with field goal fallbacks

The system provides the **advanced strategic intelligence layer** that creates highly realistic, contextually-appropriate coaching decisions that adapt dynamically to game flow, opponent strategies, and critical situations while maintaining NFL-authentic statistical distributions and coaching behaviors. Each game feels unique not just based on base coaching philosophies, but on how those philosophies adapt and evolve throughout the game based on context, momentum, and opponent responses.