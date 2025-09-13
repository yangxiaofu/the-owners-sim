# CentralizedStatsAggregator Implementation Plan

## Overview
Design and implement the CentralizedStatsAggregator as a statistics coordination hub that bridges GameLoopController output with existing statistics components, providing unified access to all game statistics.

## Current Statistics Architecture Analysis

### Existing Components ✅
1. **`PlayerStats`** - Individual player statistics for single plays (comprehensive stat tracking)
2. **`PlayStatsSummary`** - Container for all PlayerStats from one play with penalty info
3. **`PlayerStatsAccumulator`** - Accumulates player stats across entire game (proven, tested)
4. **`TeamStatsAccumulator`** - Accumulates team-level stats from plays (proven, tested)
5. **`GameStatsReporter`** - Final comprehensive reporting system

### Current Data Flow ✅
```
Play Simulators → PlayStatsSummary → PlayerStatsAccumulator/TeamStatsAccumulator
```

### The Missing Link 🔨
**Problem:** GameLoopController receives `PlayResult` (basic) but existing accumulators expect `PlayStatsSummary` (detailed).

**Current Gap:**
```
GameLoopController._run_play() → PlayResult (basic: yards, outcome, time)
??? Missing Bridge ???
PlayerStatsAccumulator.add_play_stats() expects PlayStatsSummary (detailed: player stats)
```

## Root Cause Analysis

### The Statistics Disconnect
Looking at the current implementation:

1. **Play Simulators** (RunPlaySimulator, PassPlaySimulator, etc.) **already generate rich PlayerStats**
2. **PlayEngine.simulate()** returns only basic `PlayResult` - **detailed stats are lost!**
3. **GameLoopController** only receives basic play outcome
4. **Existing accumulators** never receive the detailed statistics they were designed for

### The Solution: Bridge the Gap
The CentralizedStatsAggregator serves as the missing bridge by:
1. **Enhancing PlayResult** to include detailed statistics
2. **Coordinating existing components** rather than replacing them
3. **Adding game-level tracking** that's currently missing
4. **Providing unified API** for external access

## Implementation Strategy

### Phase 1: Core CentralizedStatsAggregator

**Location:** `src/game_management/centralized_stats_aggregator.py`

**Role:** Statistics coordination hub - **not a replacement, but an orchestrator**

### Enhanced PlayResult Structure
```python
@dataclass
class PlayResult:
    # Existing basic fields
    outcome: str
    yards_gained: int
    time_elapsed: float
    is_touchdown: bool = False
    is_field_goal: bool = False
    is_punt: bool = False
    is_turnover: bool = False
    
    # NEW: Include rich statistics (the missing link!)
    detailed_stats: Optional[PlayStatsSummary] = None
    penalty_info: Optional[PenaltyInstance] = None
```

### GameLevelStats Class
```python
@dataclass
class GameLevelStats:
    """Game-wide statistics not tracked by player/team accumulators"""
    total_plays: int = 0
    total_drives: int = 0
    quarters_completed: int = 0
    game_time_elapsed: int = 0  # seconds
    total_penalties: int = 0
    total_penalty_yards: int = 0
    
    # Advanced game-level tracking
    red_zone_attempts: Dict[int, int] = field(default_factory=dict)  # team_id -> attempts
    red_zone_scores: Dict[int, int] = field(default_factory=dict)    # team_id -> scores
    third_down_attempts: Dict[int, int] = field(default_factory=dict)
    third_down_conversions: Dict[int, int] = field(default_factory=dict)
    fourth_down_attempts: Dict[int, int] = field(default_factory=dict)
    fourth_down_conversions: Dict[int, int] = field(default_factory=dict)
    turnovers: Dict[int, int] = field(default_factory=dict)  # team_id -> turnovers committed
    time_of_possession: Dict[int, int] = field(default_factory=dict)  # team_id -> seconds
```

### CentralizedStatsAggregator Core Implementation
```python
class CentralizedStatsAggregator:
    """
    Statistics coordination hub that bridges GameLoopController with existing 
    PlayerStatsAccumulator and TeamStatsAccumulator components.
    
    Key Principle: Coordinate, don't duplicate. Leverage proven components.
    """
    
    def __init__(self, home_team_id: int, away_team_id: int, game_identifier: Optional[str] = None):
        """
        Initialize with existing proven components
        
        Args:
            home_team_id: Home team ID for attribution logic
            away_team_id: Away team ID for attribution logic  
            game_identifier: Optional game ID for tracking
        """
        # Use existing proven components - don't reinvent the wheel
        self.player_stats = PlayerStatsAccumulator(game_identifier)
        self.team_stats = TeamStatsAccumulator(game_identifier)
        
        # NEW: Game-level tracking (the missing piece)
        self.game_level_stats = GameLevelStats()
        
        # Team identification for statistics attribution
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.game_identifier = game_identifier
    
    def record_play_result(self, play_result: PlayResult, possessing_team_id: int, 
                          down: int, yards_to_go: int, field_position: int) -> None:
        """
        Core method: Extract and record all statistics from a single play
        
        Args:
            play_result: PlayResult containing basic outcome and detailed stats
            possessing_team_id: Team ID of team with possession
            down: Current down (1-4)  
            yards_to_go: Yards needed for first down
            field_position: Current field position (0-100)
        """
        # Phase 1: Feed detailed stats into existing proven accumulators
        if play_result.detailed_stats:
            # Player-level statistics
            self.player_stats.add_play_stats(play_result.detailed_stats)
            
            # Team-level statistics (determine offensive vs defensive team)
            defensive_team_id = self.away_team_id if possessing_team_id == self.home_team_id else self.home_team_id
            self.team_stats.add_play_stats(play_result.detailed_stats, possessing_team_id, defensive_team_id)
        
        # Phase 2: Game-level tracking (the new functionality)
        self._update_game_level_stats(play_result, possessing_team_id, down, yards_to_go, field_position)
    
    def _update_game_level_stats(self, play_result: PlayResult, possessing_team_id: int,
                                down: int, yards_to_go: int, field_position: int) -> None:
        """Update game-level statistics tracking"""
        # Basic play counting
        self.game_level_stats.total_plays += 1
        self.game_level_stats.game_time_elapsed += int(play_result.time_elapsed)
        
        # Time of possession (approximate based on play time)
        if possessing_team_id not in self.game_level_stats.time_of_possession:
            self.game_level_stats.time_of_possession[possessing_team_id] = 0
        self.game_level_stats.time_of_possession[possessing_team_id] += int(play_result.time_elapsed)
        
        # Red zone tracking (field position >= 80 yards = red zone)
        if field_position >= 80:
            if possessing_team_id not in self.game_level_stats.red_zone_attempts:
                self.game_level_stats.red_zone_attempts[possessing_team_id] = 0
            self.game_level_stats.red_zone_attempts[possessing_team_id] += 1
            
            # Red zone scores
            if play_result.is_touchdown or play_result.is_field_goal:
                if possessing_team_id not in self.game_level_stats.red_zone_scores:
                    self.game_level_stats.red_zone_scores[possessing_team_id] = 0
                self.game_level_stats.red_zone_scores[possessing_team_id] += 1
        
        # Third down tracking
        if down == 3:
            if possessing_team_id not in self.game_level_stats.third_down_attempts:
                self.game_level_stats.third_down_attempts[possessing_team_id] = 0
            self.game_level_stats.third_down_attempts[possessing_team_id] += 1
            
            # Third down conversions (gained enough yards for first down)
            if play_result.yards_gained >= yards_to_go:
                if possessing_team_id not in self.game_level_stats.third_down_conversions:
                    self.game_level_stats.third_down_conversions[possessing_team_id] = 0
                self.game_level_stats.third_down_conversions[possessing_team_id] += 1
        
        # Fourth down tracking
        if down == 4:
            if possessing_team_id not in self.game_level_stats.fourth_down_attempts:
                self.game_level_stats.fourth_down_attempts[possessing_team_id] = 0
            self.game_level_stats.fourth_down_attempts[possessing_team_id] += 1
            
            # Fourth down conversions
            if play_result.yards_gained >= yards_to_go and not play_result.is_punt:
                if possessing_team_id not in self.game_level_stats.fourth_down_conversions:
                    self.game_level_stats.fourth_down_conversions[possessing_team_id] = 0
                self.game_level_stats.fourth_down_conversions[possessing_team_id] += 1
        
        # Turnover tracking
        if play_result.is_turnover:
            if possessing_team_id not in self.game_level_stats.turnovers:
                self.game_level_stats.turnovers[possessing_team_id] = 0
            self.game_level_stats.turnovers[possessing_team_id] += 1
        
        # Penalty tracking
        if play_result.penalty_info:
            self.game_level_stats.total_penalties += 1
            self.game_level_stats.total_penalty_yards += play_result.penalty_info.yards_assessed
    
    def record_drive_result(self, drive_result: DriveResult) -> None:
        """
        Record statistics from completed drive
        
        Args:
            drive_result: DriveResult containing drive summary
        """
        self.game_level_stats.total_drives += 1
        
        # Additional drive-level statistics can be added here
        # E.g., drive success rate, average drive length, etc.
    
    def record_quarter_end(self, quarter: int) -> None:
        """Record quarter completion for game flow tracking"""
        self.game_level_stats.quarters_completed = quarter
    
    # Public API Methods - Delegate to existing proven components
    
    def get_player_statistics(self, team_id: Optional[int] = None, 
                            player_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get player statistics with optional filtering
        
        Args:
            team_id: Filter by team (home_team_id or away_team_id)
            player_id: Filter by specific player
            
        Returns:
            Dictionary of player statistics
        """
        all_players = self.player_stats.get_all_players_with_stats()
        
        if team_id is None and player_id is None:
            return {player.player_name: player.get_total_stats() for player in all_players}
        
        # Apply filtering logic
        filtered_players = []
        for player in all_players:
            # Team filtering logic (would need to enhance PlayerStats to track team_id)
            if team_id is not None:
                # TODO: Add team_id tracking to PlayerStats for filtering
                pass
            
            if player_id is not None and player.player_id == player_id:
                filtered_players.append(player)
            elif player_id is None:
                filtered_players.append(player)
        
        return {player.player_name: player.get_total_stats() for player in filtered_players}
    
    def get_team_statistics(self, team_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get team statistics with optional filtering
        
        Args:
            team_id: Specific team ID, or None for both teams
            
        Returns:
            Dictionary of team statistics
        """
        if team_id is not None:
            team_stats = self.team_stats.get_team_stats(team_id)
            return team_stats.get_all_stats() if team_stats else {}
        else:
            all_teams = self.team_stats.get_all_teams_stats()
            return {team.team_id: team.get_all_stats() for team in all_teams}
    
    def get_game_level_statistics(self) -> Dict[str, Any]:
        """Get game-level statistics"""
        return {
            'total_plays': self.game_level_stats.total_plays,
            'total_drives': self.game_level_stats.total_drives,
            'quarters_completed': self.game_level_stats.quarters_completed,
            'game_duration_seconds': self.game_level_stats.game_time_elapsed,
            'total_penalties': self.game_level_stats.total_penalties,
            'total_penalty_yards': self.game_level_stats.total_penalty_yards,
            'red_zone_efficiency': self._calculate_red_zone_efficiency(),
            'third_down_conversion_rate': self._calculate_third_down_rate(),
            'fourth_down_conversion_rate': self._calculate_fourth_down_rate(),
            'turnovers_by_team': dict(self.game_level_stats.turnovers),
            'time_of_possession': dict(self.game_level_stats.time_of_possession)
        }
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive statistics report combining all sources"""
        return {
            'game_info': {
                'home_team_id': self.home_team_id,
                'away_team_id': self.away_team_id,
                'game_id': self.game_identifier
            },
            'game_level_stats': self.get_game_level_statistics(),
            'team_stats': self.get_team_statistics(),
            'player_stats': self.get_player_statistics(),
            'plays_processed': self.player_stats.get_plays_processed(),
            'statistical_summary': self._generate_statistical_summary()
        }
    
    # Helper methods for advanced statistics calculations
    
    def _calculate_red_zone_efficiency(self) -> Dict[int, float]:
        """Calculate red zone scoring efficiency by team"""
        efficiency = {}
        for team_id in [self.home_team_id, self.away_team_id]:
            attempts = self.game_level_stats.red_zone_attempts.get(team_id, 0)
            scores = self.game_level_stats.red_zone_scores.get(team_id, 0)
            efficiency[team_id] = (scores / attempts) if attempts > 0 else 0.0
        return efficiency
    
    def _calculate_third_down_rate(self) -> Dict[int, float]:
        """Calculate third down conversion rate by team"""
        rates = {}
        for team_id in [self.home_team_id, self.away_team_id]:
            attempts = self.game_level_stats.third_down_attempts.get(team_id, 0)
            conversions = self.game_level_stats.third_down_conversions.get(team_id, 0)
            rates[team_id] = (conversions / attempts) if attempts > 0 else 0.0
        return rates
    
    def _calculate_fourth_down_rate(self) -> Dict[int, float]:
        """Calculate fourth down conversion rate by team"""
        rates = {}
        for team_id in [self.home_team_id, self.away_team_id]:
            attempts = self.game_level_stats.fourth_down_attempts.get(team_id, 0)
            conversions = self.game_level_stats.fourth_down_conversions.get(team_id, 0)
            rates[team_id] = (conversions / attempts) if attempts > 0 else 0.0
        return rates
    
    def _generate_statistical_summary(self) -> Dict[str, Any]:
        """Generate high-level statistical summary"""
        return {
            'total_statistical_events': (
                self.game_level_stats.total_plays + 
                self.game_level_stats.total_penalties
            ),
            'average_play_time': (
                self.game_level_stats.game_time_elapsed / max(1, self.game_level_stats.total_plays)
            ),
            'penalty_rate': (
                self.game_level_stats.total_penalties / max(1, self.game_level_stats.total_plays)
            ),
            'unique_players_with_stats': len(self.player_stats.get_all_players_with_stats()),
            'teams_tracked': len(self.team_stats.get_all_teams_stats())
        }
```

## Integration with GameLoopController

### Required Changes to GameLoopController
```python
class GameLoopController:
    def __init__(self, ...):
        # Existing initialization...
        
        # NEW: Replace individual accumulators with centralized coordinator
        self.stats_aggregator = CentralizedStatsAggregator(
            home_team_id=home_team.team_id,
            away_team_id=away_team.team_id,
            game_identifier=f"{away_team.abbreviation}_vs_{home_team.abbreviation}"
        )
        
        # Remove old individual components (now coordinated by CentralizedStatsAggregator)
        # self.player_stats = PlayerStatsAccumulator()  # REMOVE
        # self.team_stats = TeamStatsAccumulator()      # REMOVE
    
    def _run_play(self, drive_manager, possessing_team_id) -> PlayResult:
        # Get current drive situation for statistics context
        current_situation = drive_manager.get_current_situation()
        down = current_situation.down
        yards_to_go = current_situation.yards_to_go
        field_position = drive_manager.field_tracker.current_position.yard_line
        
        # Existing play execution...
        play_result = simulate(play_params)
        
        # NEW: Record comprehensive statistics
        self.stats_aggregator.record_play_result(
            play_result, 
            possessing_team_id,
            down,
            yards_to_go,
            field_position
        )
        
        return play_result
    
    def _run_quarter(self, quarter: int) -> None:
        # Existing quarter logic...
        
        # NEW: Record quarter completion
        self.stats_aggregator.record_quarter_end(quarter)
    
    def _run_drive(self, possessing_team_id: int) -> DriveResult:
        # Existing drive logic...
        drive_result = # ... existing drive execution
        
        # NEW: Record drive statistics
        self.stats_aggregator.record_drive_result(drive_result)
        
        return drive_result
```

### Required Changes to PlayEngine/Simulators
The key missing piece - simulators need to populate `detailed_stats` in `PlayResult`:

```python
# In each simulator (RunPlaySimulator, PassPlaySimulator, etc.)
def simulate_run_play(self, context: Optional[PlayContext] = None) -> PlayResult:
    # Existing simulation logic that creates PlayStatsSummary
    play_stats_summary = # ... existing detailed stats creation
    
    # NEW: Include detailed stats in PlayResult
    return PlayResult(
        outcome=play_stats_summary.play_type,
        yards_gained=play_stats_summary.yards_gained,
        time_elapsed=play_stats_summary.time_elapsed,
        is_touchdown=(play_stats_summary.yards_gained >= yards_to_goal_line),
        # ... other basic fields
        
        # THE MISSING LINK: Include detailed statistics!
        detailed_stats=play_stats_summary,
        penalty_info=play_stats_summary.penalty_instance if play_stats_summary.penalty_occurred else None
    )
```

## Implementation Dependencies

### Phase 1 Requirements:
1. ✅ **PlayResult enhancement** - Add `detailed_stats` and `penalty_info` fields
2. ✅ **GameLevelStats class** - New data structure for game-wide tracking
3. ✅ **CentralizedStatsAggregator class** - Core coordinator implementation  
4. 🔨 **Play simulator updates** - Populate detailed stats in PlayResult
5. 🔨 **GameLoopController integration** - Use CentralizedStatsAggregator instead of individual components

### Testing Strategy:
1. **Unit tests for GameLevelStats** - Verify statistical calculations
2. **Unit tests for CentralizedStatsAggregator** - Test coordination logic  
3. **Integration tests** - Verify end-to-end statistics flow
4. **Statistics accuracy validation** - Compare with known expected outcomes

## Success Criteria

### Phase 1 Complete When:
1. ✅ CentralizedStatsAggregator successfully coordinates existing PlayerStatsAccumulator and TeamStatsAccumulator
2. ✅ Game-level statistics (red zone, third down, etc.) are accurately tracked
3. ✅ Public API methods provide unified access to all statistics
4. ✅ Integration with GameLoopController feeds comprehensive statistics
5. ✅ No duplication - existing proven components are leveraged, not replaced
6. ✅ Unit tests validate all statistical calculations and coordinations

### Key Validation Tests:
- Run a simulated game and verify player statistics match expected totals
- Verify team statistics aggregate correctly from individual plays
- Confirm game-level statistics (red zone efficiency, conversion rates) calculate accurately
- Validate that no statistics are lost in the coordination process

This approach bridges the current statistics gap while leveraging all existing, proven components to create a comprehensive statistics tracking system.