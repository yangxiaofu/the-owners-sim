"""
State Transitions Tracking Module

This module provides comprehensive tracking and auditing capabilities for the game engine,
completely separated from game logic as a separate concern.

The tracking system observes but never modifies game state, providing:

1. **Game Statistics Tracking** (`GameStatisticsTracker`):
   - Play type distributions and effectiveness
   - Clock management and time usage patterns  
   - Situational analysis (red zone, third down, etc.)
   - Drive efficiency and team performance metrics
   - Advanced NFL-style analytics

2. **Play-by-Play Auditing** (`PlayByPlayAuditor`):
   - Complete immutable audit trail of all game events
   - State transition tracking for debugging
   - Replay capability from audit logs
   - Error and validation failure tracking
   - Performance monitoring integration

3. **Performance Metrics** (`PerformanceTracker`):
   - Real-time system performance monitoring
   - Bottleneck identification and analysis
   - Memory usage and resource tracking
   - Execution time profiling
   - Optimization recommendations

Design Principles:
- **Observer Pattern**: Tracks but never modifies game state
- **Clean Separation**: Completely independent of core game logic
- **Minimal Overhead**: Efficient tracking that doesn't impact gameplay
- **Comprehensive Coverage**: Every aspect of game simulation is tracked
- **Actionable Insights**: Metrics that inform optimization and analysis

Usage Example:
```python
# Initialize tracking system for a game
tracker = GameStatisticsTracker(home_team_id, away_team_id)
auditor = PlayByPlayAuditor(game_id, home_team_id, away_team_id)
performance = PerformanceTracker()

# Track play execution
tracker.record_play(play_result, possession_team_id)
auditor.record_play(play_result, game_state)

with performance.measure_operation("execute_play", PerformanceCategory.PLAY_EXECUTION):
    play_result = execute_play_logic()

# Get comprehensive analysis
stats_summary = tracker.get_current_summary()
audit_trail = auditor.export_to_json()
performance_report = performance.get_performance_summary()
```

Integration Points:
- Called from GameOrchestrator after each play
- Receives PlayResults and GameStateTransitions
- Provides analytics for post-game analysis
- Supports debugging and optimization workflows
"""

from game_engine.state_transitions.tracking.game_statistics_tracker import (
    GameStatisticsTracker,
    GameStatisticsSummary,
    PlayTypeStats,
    DriveStats,
    SituationalStats,
    GamePhase
)

from game_engine.state_transitions.tracking.play_by_play_auditor import (
    PlayByPlayAuditor,
    AuditEntry,
    AuditQuery,
    AuditEventType,
    GameContext
)

from game_engine.state_transitions.tracking.performance_metrics import (
    PerformanceTracker,
    PerformanceMetric,
    ExecutionProfile,
    SystemResourceMetrics,
    PerformanceCategory
)

# Convenience imports for common functionality
__all__ = [
    # Game Statistics
    "GameStatisticsTracker",
    "GameStatisticsSummary", 
    "PlayTypeStats",
    "DriveStats",
    "SituationalStats",
    "GamePhase",
    
    # Auditing
    "PlayByPlayAuditor",
    "AuditEntry",
    "AuditQuery", 
    "AuditEventType",
    "GameContext",
    
    # Performance
    "PerformanceTracker",
    "PerformanceMetric",
    "ExecutionProfile",
    "SystemResourceMetrics", 
    "PerformanceCategory",
    
    # Integrated tracking
    "create_integrated_tracker",
    "TrackingSystem"
]


class TrackingSystem:
    """
    Integrated tracking system that combines statistics, auditing, and performance monitoring.
    
    Provides a unified interface for all tracking concerns while maintaining
    separation between the different tracking responsibilities.
    """
    
    def __init__(self, game_id: str, home_team_id: str, away_team_id: str, 
                 enable_performance_monitoring: bool = True):
        """
        Initialize integrated tracking system.
        
        Args:
            game_id: Unique identifier for this game
            home_team_id: Home team identifier
            away_team_id: Away team identifier  
            enable_performance_monitoring: Whether to track system performance metrics
        """
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Initialize all tracking components
        self.statistics = GameStatisticsTracker(home_team_id, away_team_id)
        self.auditor = PlayByPlayAuditor(game_id, home_team_id, away_team_id)
        self.performance = PerformanceTracker(enable_system_monitoring=enable_performance_monitoring)
        
        # Track system initialization
        self.auditor.record_system_event(
            "tracking_system_initialized",
            f"Integrated tracking system initialized for game {game_id}",
            tags=["system", "initialization"]
        )
    
    def record_play(self, play_result, possession_team_id: str, game_state, 
                   execution_time: float = 0.0) -> None:
        """
        Record a play across all tracking systems.
        
        Args:
            play_result: PlayResult object with play details
            possession_team_id: Team that had possession
            game_state: Current game state for context
            execution_time: Time taken to execute the play (for performance tracking)
        """
        # Record in statistics tracker
        self.statistics.record_play(play_result, possession_team_id)
        
        # Record in audit trail  
        self.auditor.record_play(play_result, game_state)
        
        # Record performance metrics if execution time provided
        if execution_time > 0:
            self.performance.record_play_performance(play_result, execution_time)
    
    def record_state_transition(self, transition, game_state, description: str) -> None:
        """Record state transition across applicable tracking systems."""
        # Record in audit trail
        self.auditor.record_state_transition(transition, game_state, description)
    
    def record_possession_change(self, old_team: str, new_team: str, reason: str, game_state) -> None:
        """Record possession change event."""
        # Start new drive tracking
        field_position = getattr(game_state.field, 'field_position', 50)
        game_time = getattr(game_state.clock, 'time_remaining', 3600)
        
        self.statistics.start_new_drive(new_team, field_position, game_time)
        self.auditor.record_possession_change(old_team, new_team, reason, game_state)
    
    def record_score(self, team_id: str, points: int, play_type: str, game_state) -> None:
        """Record scoring event across all tracking systems."""
        self.auditor.record_score(team_id, points, play_type, game_state)
        
        # System metrics snapshot on scoring plays
        self.performance.record_system_metrics()
    
    def record_error(self, error_type: str, error_message: str, 
                    error_data: dict = None, game_state=None) -> None:
        """Record error condition."""
        self.auditor.record_error(error_type, error_message, error_data, game_state)
    
    def get_comprehensive_summary(self) -> dict:
        """Get comprehensive summary from all tracking systems."""
        return {
            "game_id": self.game_id,
            "teams": {
                "home": self.home_team_id,
                "away": self.away_team_id
            },
            "statistics": self.statistics.get_current_summary(),
            "performance": self.performance.get_performance_summary(),
            "audit_summary": {
                "total_entries": len(self.auditor.audit_trail),
                "errors": self.auditor.get_error_summary(),
                "drives": self.auditor.get_drive_summary()
            }
        }
    
    def export_all_data(self, base_filename: str) -> dict:
        """
        Export all tracking data to files.
        
        Returns:
            Dictionary with filenames of exported data
        """
        files_created = {}
        
        # Export statistics
        stats_data = self.statistics.get_current_summary()
        stats_file = f"{base_filename}_statistics.json"
        
        import json
        with open(stats_file, 'w') as f:
            json.dump(stats_data, f, indent=2, default=str)
        files_created["statistics"] = stats_file
        
        # Export audit trail  
        audit_file = f"{base_filename}_audit.json"
        self.auditor.export_to_json(audit_file)
        files_created["audit"] = audit_file
        
        # Export performance metrics
        perf_file = f"{base_filename}_performance.json"  
        self.performance.export_metrics(perf_file)
        files_created["performance"] = perf_file
        
        return files_created
    
    def reset(self) -> None:
        """Reset all tracking systems for a new game."""
        self.statistics.reset()
        self.auditor.reset()
        self.performance.reset()


def create_integrated_tracker(game_id: str, home_team_id: str, away_team_id: str,
                            enable_performance_monitoring: bool = True) -> TrackingSystem:
    """
    Convenience function to create a fully configured tracking system.
    
    Args:
        game_id: Unique identifier for the game
        home_team_id: Home team identifier
        away_team_id: Away team identifier
        enable_performance_monitoring: Whether to enable system performance tracking
        
    Returns:
        Configured TrackingSystem instance
    """
    return TrackingSystem(
        game_id=game_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        enable_performance_monitoring=enable_performance_monitoring
    )


# Example usage and testing utilities
def create_test_tracker() -> TrackingSystem:
    """Create a tracker for testing purposes."""
    return create_integrated_tracker("test_game", "HOME", "AWAY", enable_performance_monitoring=False)