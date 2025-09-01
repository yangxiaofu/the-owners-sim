# Comprehensive Player Statistics & Play Tracking Enhancement Plan

## Overview
Enhance PlayResult to capture comprehensive NFL statistics including pancakes, passes defended, hurries, QB hits, and other advanced metrics that can be extracted from existing play simulation data.

## Current Code Analysis

### ✅ Existing Data We Can Extract:

**From Pass Plays:**
- `qb_effectiveness`, `wr_effectiveness`, `protection_effectiveness` 
- `coverage_effectiveness`, `coverage_modifier`
- `rush_advantage` (pass rush vs protection)
- `sack_probability`, `final_completion`
- Route concept vs coverage matchup data

**From Run Plays:**
- `BlockingResult` objects with individual matchup success/failure
- `rb_vs_defenders` matchups
- `impact_factor` for each block (0.0-1.0)
- Direction and play type information

**From Blocking System:**
- Individual blocker vs defender matchups
- Success/failure rates by position
- Impact factors for each block

### ❌ Statistics We Can Add:

## Enhanced PlayResult Data Structure

```python
@dataclass
class PlayResult:
    # Existing core fields...
    
    # === COMPREHENSIVE PLAYER TRACKING ===
    quarterback: Optional[str] = None
    receiver: Optional[str] = None        # Primary receiver
    rusher: Optional[str] = None
    tackler: Optional[str] = None         # Primary tackler
    assist_tackler: Optional[str] = None  # Secondary tackler
    
    # === PASSING STATISTICS ===
    pass_rusher: Optional[str] = None     # Primary pass rusher
    coverage_defender: Optional[str] = None
    passes_defended_by: List[str] = field(default_factory=list)  # All DBs who defended
    quarterback_hits_by: List[str] = field(default_factory=list) # DL who hit QB
    quarterback_hurries_by: List[str] = field(default_factory=list) # DL who hurried QB
    
    # Pass protection tracking
    protection_breakdowns: List[Dict] = field(default_factory=list) # Which blocks failed
    clean_pocket: bool = False            # No pressure on QB
    
    # === RUNNING STATISTICS ===
    pancakes_by: List[str] = field(default_factory=list)        # OL who pancaked defenders
    key_blocks_by: List[str] = field(default_factory=list)      # Critical successful blocks
    missed_tackles_by: List[str] = field(default_factory=list)  # Defenders who missed tackles
    broken_tackles: int = 0               # Number of tackles broken by RB
    
    # === DEFENSIVE STATISTICS ===  
    tackles_for_loss_by: List[str] = field(default_factory=list)
    fumbles_forced_by: Optional[str] = None
    fumbles_recovered_by: Optional[str] = None
    interceptions_by: Optional[str] = None
    
    # === ADVANCED METRICS ===
    pressure_applied: bool = False
    coverage_beaten: bool = False
    big_play: bool = False               # 20+ yards
    explosive_play: bool = False         # 40+ yards
    missed_tackle: bool = False
    perfect_protection: bool = False      # All blocks successful
    
    # === MATCHUP ANALYSIS ===
    key_matchup_winner: Optional[str] = None    # Player who won critical matchup
    key_matchup_loser: Optional[str] = None     # Player who lost critical matchup
    
    # === SITUATIONAL CONTEXT ===
    down_conversion: bool = False         # Did play result in first down/TD
    red_zone_play: bool = False
    goal_line_play: bool = False
    two_minute_drill: bool = False
```

## Implementation Strategy

### Phase 1: Enhanced Statistics Extraction Classes

**New File**: `src/game_engine/plays/statistics_extractor.py`

```python
class StatisticsExtractor:
    """Extracts comprehensive statistics from play simulation data"""
    
    def extract_pass_statistics(self, personnel, effectiveness_data, 
                               sack_data, coverage_data, route_concept) -> Dict:
        """Extract all pass-related statistics"""
        
        stats = {}
        
        # Pass rush statistics
        if sack_data['rush_advantage'] > 1.2:  # High pressure situation
            stats['pressure_applied'] = True
            stats['pass_rusher'] = self._identify_primary_rusher(personnel, sack_data)
            
            # Differentiate between sack, hit, hurry
            if sack_data['outcome'] == 'sack':
                stats['sack_by'] = stats['pass_rusher']
            elif effectiveness_data['qb_effectiveness'] < 0.6:  # QB affected by pressure
                if sack_data['rush_advantage'] > 1.5:
                    stats['quarterback_hits_by'] = [stats['pass_rusher']]
                else:
                    stats['quarterback_hurries_by'] = [stats['pass_rusher']]
        
        # Coverage statistics
        if coverage_data['coverage_effectiveness'] > 0.8:  # Good coverage
            coverage_defender = self._identify_coverage_defender(personnel, route_concept)
            if coverage_data['outcome'] == 'incomplete':
                stats['passes_defended_by'] = [coverage_defender]
            elif coverage_data['outcome'] == 'interception':
                stats['interceptions_by'] = coverage_defender
        
        # Protection analysis
        protection_breakdowns = self._analyze_protection(personnel, sack_data)
        stats['protection_breakdowns'] = protection_breakdowns
        stats['clean_pocket'] = len(protection_breakdowns) == 0
        stats['perfect_protection'] = sack_data['protection_effectiveness'] > 0.9
        
        return stats
    
    def extract_run_statistics(self, personnel, blocking_results, 
                              rb_effectiveness, yards_gained) -> Dict:
        """Extract all run-related statistics"""
        
        stats = {}
        
        # Blocking analysis
        pancakes = []
        key_blocks = []
        protection_failures = []
        
        for block_result in blocking_results:
            if block_result.success and block_result.impact_factor > 0.8:
                # High-impact successful block = potential pancake
                if block_result.blocker_rating - block_result.defender_rating > 15:
                    pancakes.append(block_result.blocker_position)
                else:
                    key_blocks.append(block_result.blocker_position)
            elif not block_result.success and block_result.impact_factor > 0.6:
                protection_failures.append({
                    'blocker': block_result.blocker_position,
                    'defender': block_result.defender_position
                })
        
        stats['pancakes_by'] = pancakes
        stats['key_blocks_by'] = key_blocks
        stats['protection_breakdowns'] = protection_failures
        
        # RB performance analysis
        expected_yards = self._calculate_expected_yards(blocking_results)
        yards_over_expected = yards_gained - expected_yards
        
        if yards_over_expected > 3:  # RB created extra yards
            stats['broken_tackles'] = min(2, max(0, int(yards_over_expected / 4)))
            # Identify which defenders missed tackles
            stats['missed_tackles_by'] = self._identify_missed_tacklers(
                personnel, yards_over_expected
            )
        
        # Defensive performance
        if yards_gained < 0:
            stats['tackles_for_loss_by'] = [self._identify_tfl_player(personnel, blocking_results)]
        
        return stats
```

### Phase 2: Integration with Existing Play Simulations

**Pass Play Enhancement** - `pass_play.py`:
```python
def simulate(self, personnel, field_state: FieldState) -> PlayResult:
    # ... existing simulation logic ...
    
    # NEW: Extract comprehensive statistics
    extractor = StatisticsExtractor()
    
    # Collect all effectiveness data during simulation
    simulation_data = {
        'qb_effectiveness': qb_effectiveness,
        'wr_effectiveness': wr_effectiveness,
        'protection_effectiveness': protection_effectiveness,
        'coverage_effectiveness': coverage_effectiveness,
        'rush_advantage': self._get_rush_advantage(total_protection, total_rush),
        'coverage_modifier': coverage_modifier,
        'route_concept': route_concept,
        'coverage_type': coverage_type
    }
    
    # Extract comprehensive stats
    play_stats = extractor.extract_pass_statistics(
        personnel, simulation_data, sack_outcome, coverage_data, route_concept
    )
    
    return PlayResult(
        # ... existing fields ...
        
        # Comprehensive statistics
        quarterback=self._get_player_name(personnel.qb_on_field),
        receiver=play_stats.get('receiver'),
        pass_rusher=play_stats.get('pass_rusher'),
        coverage_defender=play_stats.get('coverage_defender'),
        passes_defended_by=play_stats.get('passes_defended_by', []),
        quarterback_hits_by=play_stats.get('quarterback_hits_by', []),
        quarterback_hurries_by=play_stats.get('quarterback_hurries_by', []),
        protection_breakdowns=play_stats.get('protection_breakdowns', []),
        clean_pocket=play_stats.get('clean_pocket', False),
        perfect_protection=play_stats.get('perfect_protection', False),
        pressure_applied=play_stats.get('pressure_applied', False),
        coverage_beaten=final_completion > matrix['base_completion']
    )
```

**Run Play Enhancement** - `run_play.py`:
```python
def simulate(self, personnel, field_state: FieldState) -> PlayResult:
    # ... existing simulation logic ...
    
    # NEW: Get detailed blocking results from simulation
    blocking_simulator = BlockingSimulator(ZoneBlockingStrategy())
    blocking_results = blocking_simulator.simulate_matchups(
        blocker_ratings, defender_ratings, context
    )
    
    # Extract comprehensive statistics
    extractor = StatisticsExtractor()
    play_stats = extractor.extract_run_statistics(
        personnel, blocking_results, rb_effectiveness, yards_gained
    )
    
    return PlayResult(
        # ... existing fields ...
        
        # Comprehensive statistics
        rusher=self._get_player_name(personnel.rb_on_field),
        tackler=play_stats.get('tackler'),
        assist_tackler=play_stats.get('assist_tackler'),
        pancakes_by=play_stats.get('pancakes_by', []),
        key_blocks_by=play_stats.get('key_blocks_by', []),
        missed_tackles_by=play_stats.get('missed_tackles_by', []),
        broken_tackles=play_stats.get('broken_tackles', 0),
        tackles_for_loss_by=play_stats.get('tackles_for_loss_by', []),
        perfect_protection=len(play_stats.get('protection_breakdowns', [])) == 0
    )
```

### Phase 3: Advanced Commentary System

**New File**: `src/game_engine/plays/commentary_generator.py`

```python
class CommentaryGenerator:
    """Generates rich play-by-play commentary from comprehensive statistics"""
    
    def generate_detailed_commentary(self, play_result: PlayResult) -> str:
        """Generate comprehensive play description with all statistics"""
        
        if play_result.play_type == "pass":
            return self._generate_pass_commentary(play_result)
        elif play_result.play_type == "run":
            return self._generate_run_commentary(play_result)
        
        return play_result.get_summary()
    
    def _generate_pass_commentary(self, result: PlayResult) -> str:
        """Generate detailed passing play commentary"""
        
        base_action = f"{result.quarterback} passes to {result.receiver}"
        
        # Add outcome and yardage
        if result.outcome == "touchdown":
            description = f"{base_action} for a {result.yards_gained}-yard touchdown"
        elif result.outcome == "incomplete":
            description = f"{base_action}, incomplete"
            if result.passes_defended_by:
                description += f" - pass defended by {result.passes_defended_by[0]}"
        elif result.outcome == "sack":
            if result.pass_rusher:
                description = f"{result.pass_rusher} sacks {result.quarterback} for {abs(result.yards_gained)} yards"
            else:
                description = f"{result.quarterback} sacked for {abs(result.yards_gained)} yards"
        else:
            description = f"{base_action} for {result.yards_gained} yards"
            if result.tackler:
                description += f", tackled by {result.tackler}"
        
        # Add pressure information
        if result.quarterback_hits_by:
            description += f" - {result.quarterback_hits_by[0]} hits the quarterback"
        elif result.quarterback_hurries_by:
            description += f" - {result.quarterback_hurries_by[0]} hurries the quarterback"
        elif result.clean_pocket:
            description += " - clean pocket"
        
        # Add broken protection details
        if result.protection_breakdowns:
            breakdown = result.protection_breakdowns[0]
            description += f" - protection breakdown: {breakdown['blocker']} beaten by {breakdown['defender']}"
        
        return description
    
    def _generate_run_commentary(self, result: PlayResult) -> str:
        """Generate detailed running play commentary"""
        
        base_action = f"{result.rusher} rushes"
        
        # Add outcome and yardage  
        if result.outcome == "touchdown":
            description = f"{base_action} for a {result.yards_gained}-yard touchdown"
        else:
            description = f"{base_action} for {result.yards_gained} yards"
            if result.tackler:
                description += f", tackled by {result.tackler}"
                if result.assist_tackler:
                    description += f" and {result.assist_tackler}"
        
        # Add blocking highlights
        if result.pancakes_by:
            description += f" - {result.pancakes_by[0]} pancakes his defender"
        elif result.key_blocks_by:
            description += f" - key block by {result.key_blocks_by[0]}"
        
        # Add RB performance details
        if result.broken_tackles > 0:
            description += f" - breaks {result.broken_tackles} tackle{'s' if result.broken_tackles > 1 else ''}"
        
        if result.missed_tackles_by:
            description += f" - {result.missed_tackles_by[0]} misses the tackle"
        
        return description
```

## Expected Output Examples

### Pass Play Examples:

**Basic Completion**:
- Current: "15-yard pass completion"  
- Enhanced: "Patrick Mahomes passes to Travis Kelce for 15 yards, tackled by Roquan Smith - clean pocket"

**Sack with Details**:
- Current: "Sack for -7 yards"
- Enhanced: "Aaron Donald sacks Josh Allen for 7 yards - protection breakdown: RT beaten by DE"

**Defended Pass**:
- Current: "Pass incomplete"
- Enhanced: "Josh Allen passes to Stefon Diggs, incomplete - pass defended by Jaire Alexander, Aaron Donald hurries the quarterback"

### Run Play Examples:

**Power Run**:
- Current: "8-yard rush"  
- Enhanced: "Derrick Henry rushes for 8 yards, tackled by Fred Warner - key block by LG Quenton Nelson"

**Big Run with Pancake**:
- Current: "22-yard rush"
- Enhanced: "Jonathan Taylor rushes for 22 yards, tackled by Jordan Hicks - Quenton Nelson pancakes his defender, breaks 1 tackle"

**Stuffed Run**:
- Current: "-2-yard rush"
- Enhanced: "Saquon Barkley rushes for -2 yards, tackled for loss by Chris Jones - protection breakdown: C beaten by DT"

## Implementation Timeline

1. **Phase 1**: Enhanced PlayResult structure (1 hour)
2. **Phase 2**: StatisticsExtractor class (3 hours)  
3. **Phase 3**: Integration with pass/run simulations (2 hours)
4. **Phase 4**: Commentary generator (2 hours)
5. **Phase 5**: Testing and refinement (1 hour)

**Total Estimated Time**: 9 hours

## Benefits

- **Comprehensive Player Statistics**: Track every meaningful action
- **Rich Commentary**: NFL-quality play descriptions  
- **Advanced Analytics**: Pancakes, hurries, coverage beats, etc.
- **Defensive Statistics**: Equal tracking for defensive players
- **Matchup Analysis**: Identify key player battles
- **Fantasy Football Integration**: Individual player performance metrics

## Implementation Status

- [x] Enhanced PlayResult data structure
- [x] StatisticsExtractor class implementation
- [x] Pass play simulation integration
- [x] Run play simulation integration  
- [x] Commentary generator system
- [x] Enhanced player name mapping system (Phase 6)
- [x] Testing and validation
- [x] Documentation updates

## Phase 6: Enhanced Player Name Mapping (NEW - COMPLETED)

### Problem Solved
Previously, enhanced play descriptions showed generic position names like "LE_Player" and "LG_Player" instead of actual player names, reducing immersion and realism.

### Solution: Enhanced PersonnelPackage Position Mapping
Implemented a comprehensive position-to-player mapping dictionary system that allows direct mapping of position codes (e.g., "LE", "LG", "MLB") to actual player objects.

### Implementation Details

**Enhanced PersonnelPackage Structure:**
- Added `position_player_map: Dict[str, Any]` field for direct position-to-player mapping
- `set_position_player(position_code, player)` method for manual mapping
- `get_player_by_position(position_code)` method for player lookup
- `auto_populate_position_map()` method for automatic mapping from existing player lists

**StatisticsExtractor Integration:**
- Enhanced `_get_position_player_name()` to use direct position mapping first
- Maintains backward compatibility with existing fallback logic
- Returns actual player names instead of generic position placeholders

**Play Simulation Integration:**
- Both PassPlay and RunPlay now call `auto_populate_position_map()` before statistics extraction
- Ensures position mapping is populated for realistic player names in all scenarios

**Test Enhancement:**
- Updated `test_enhanced_play_results.py` with realistic NFL player names
- Direct position mapping setup for star players (Khalil Mack, Aaron Donald, Quenton Nelson, etc.)

### Expected Enhanced Output

**Before:**
- `"Jonathan Taylor rushes for 5 yards, tackled by LE_Player - key block by LG_Player"`
- `"Player_Josh Allen sacked for 7 yards by LE_Player"`

**After:**
- `"Jonathan Taylor rushes for 5 yards, tackled by Khalil Mack - key block by Quenton Nelson"`
- `"Josh Allen sacked for 7 yards by Khalil Mack"`

### Technical Benefits
- **Immersive Commentary**: Real NFL player names throughout all play descriptions
- **Clean Architecture**: Separation between position identification and player lookup
- **Backward Compatibility**: Existing code continues to work without modification
- **Extensible Design**: Easy to add new positions or mapping rules
- **Performance Optimized**: Direct dictionary lookup for position-to-player resolution

### Validation Results
✅ All tests pass with realistic player names in enhanced commentary
✅ Both automatic and manual position mapping work correctly
✅ Fallback system maintains compatibility with unmapped positions

## Future Extensions

- **Special Teams Statistics**: Kickoff/punt coverage, return yards, blocks
- **Penalty Tracking**: Individual player penalties and their impact
- **Advanced Metrics**: EPA (Expected Points Added), Win Probability Added
- **Situational Statistics**: Red zone performance, 3rd down success rates by player
- **Injury Simulation**: Player health impact on statistics
- **Dynamic Player Ratings**: Performance-based rating adjustments during games