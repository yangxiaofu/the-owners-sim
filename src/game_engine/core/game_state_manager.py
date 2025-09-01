"""
Game State Manager - Main Orchestrator for State Transitions

This is the central orchestrator that coordinates all state transition components:
- Calculates what changes should happen (pure functions)
- Validates transitions are legal (rule compliance)  
- Applies changes atomically (all-or-nothing)
- Tracks statistics and audit trail (separate concern)

The Game State Manager transforms the complex game loop from 9 tightly-coupled concerns
into 4 simple steps: Calculate → Validate → Apply → Track

Architecture:
    PlayResult + GameState → GameStateManager → Updated GameState + Statistics
    
    1. TransitionCalculator: Pure calculation of required changes
    2. TransitionValidator: Rule validation and compliance checking  
    3. TransitionApplicator: Atomic state application with rollback
    4. TrackingSystem: Statistics and audit trail (observer pattern)
"""

from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass

# Import transition system components with fallbacks
from ..state_transitions import GameStateTransition, TransitionCalculator, TransitionValidator, TransitionApplicator
from ..state_transitions.data_structures import BaseGameStateTransition, enhance_base_transition

# Try to import tracking system, use fallback if not available
try:
    from ..state_transitions import create_integrated_tracker
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False
    print("⚠️  Advanced tracking unavailable, using basic tracking fallback")
from ..plays.data_structures import PlayResult
from ..field.game_state import GameState


class BasicTrackingFallback:
    """
    Fallback tracking system when advanced tracking is unavailable.
    
    Provides the same interface as the full tracking system but with
    basic functionality and no external dependencies.
    """
    
    def __init__(self, game_id: str, home_team_id: str, away_team_id: str):
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        self.play_count = 0
        self.play_types = {}
        self.total_clock_used = 0.0
        self.clock_usage_by_type = {}
    
    def record_play(self, play_result, possession_team_id: str, game_state, execution_time: float = 0.0):
        """Record play with basic tracking"""
        self.play_count += 1
        self.total_clock_used += play_result.time_elapsed
        
        play_type = play_result.play_type
        self.play_types[play_type] = self.play_types.get(play_type, 0) + 1
        
        if play_type not in self.clock_usage_by_type:
            self.clock_usage_by_type[play_type] = []
        self.clock_usage_by_type[play_type].append(play_result.time_elapsed)
    
    def get_game_statistics(self):
        """Get basic game statistics"""
        return {
            'play_type_distribution': self.play_types.copy(),
            'clock_management': {
                'total_clock_used': self.total_clock_used,
                'avg_per_play': self.total_clock_used / self.play_count if self.play_count > 0 else 0.0,
                'play_count': self.play_count
            }
        }
    
    def get_audit_trail(self):
        """Get basic audit trail"""
        return [{"message": f"Basic tracking recorded {self.play_count} plays"}]
    
    def export_game_data(self, filename=None):
        """Export basic game data"""
        import json
        data = {
            'game_id': self.game_id,
            'statistics': self.get_game_statistics(),
            'tracking_type': 'basic_fallback'
        }
        return json.dumps(data, indent=2)


@dataclass
class StateTransitionResult:
    """
    Result of a complete state transition operation.
    
    Contains all information about what was calculated, validated, and applied,
    along with any errors or warnings that occurred during the process.
    """
    success: bool
    transition: Optional[GameStateTransition] = None
    validation_errors: List[str] = None
    application_errors: List[str] = None  
    execution_time_ms: float = 0.0
    changes_summary: str = ""
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.application_errors is None:
            self.application_errors = []
    
    @property 
    def has_errors(self) -> bool:
        """Check if any errors occurred during the transition"""
        return bool(self.validation_errors or self.application_errors)
    
    @property
    def all_errors(self) -> List[str]:
        """Get all errors from validation and application"""
        return self.validation_errors + self.application_errors
    
    def get_summary(self) -> str:
        """Get human-readable summary of the transition result"""
        if self.success:
            return f"✅ Success: {self.changes_summary} (took {self.execution_time_ms:.1f}ms)"
        else:
            error_count = len(self.all_errors)
            return f"❌ Failed with {error_count} error(s): {', '.join(self.all_errors[:2])}"


class GameStateManager:
    """
    Main orchestrator for all game state transitions.
    
    This class implements the Game State Manager pattern, providing:
    - Clean separation of concerns (calculate/validate/apply/track)
    - Atomic state transitions with rollback capability
    - Comprehensive validation and error handling
    - Complete audit trail and statistics tracking
    - Testable pure functions and immutable objects
    
    Usage:
        manager = GameStateManager(game_id, home_team_id, away_team_id)
        result = manager.process_play_result(play_result, game_state)
        
        if result.success:
            # State has been updated, statistics recorded
            print(f"Play processed: {result.changes_summary}")
        else:
            # Errors occurred, state unchanged  
            print(f"Play failed: {result.all_errors}")
    """
    
    def __init__(self, game_id: str, home_team_id: str, away_team_id: str):
        """
        Initialize the Game State Manager with all required components.
        
        Args:
            game_id: Unique identifier for this game
            home_team_id: ID of the home team
            away_team_id: ID of the away team
        """
        self.game_id = game_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id
        
        # Initialize all state transition components
        self.calculator = TransitionCalculator()
        self.validator = TransitionValidator()
        self.applicator = TransitionApplicator()
        
        # Initialize tracking system (separate concern) with fallback
        if TRACKING_AVAILABLE:
            self.tracking_system = create_integrated_tracker(game_id, home_team_id, away_team_id)
        else:
            # Fallback: basic tracking without advanced features
            self.tracking_system = BasicTrackingFallback(game_id, home_team_id, away_team_id)
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"GameStateManager initialized for game {game_id}: "
                        f"{home_team_id} vs {away_team_id}")
    
    def process_play_result(self, play_result: PlayResult, game_state: GameState, 
                          possession_team_id: str) -> StateTransitionResult:
        """
        Process a play result through the complete state transition pipeline.
        
        This is the main entry point that replaces the complex game loop logic.
        It follows the 4-step pattern: Calculate → Validate → Apply → Track
        
        Args:
            play_result: Result of the executed play
            game_state: Current game state (will be modified if successful)
            possession_team_id: ID of the team that had possession
            
        Returns:
            StateTransitionResult: Complete result with success/failure info
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: Calculate what changes should happen (pure functions)
            transition = self._calculate_transitions(play_result, game_state)
            
            # Step 2: Validate that transitions are legal (rule compliance)
            validation_result = self._validate_transitions(transition)
            if not validation_result.is_valid:
                return StateTransitionResult(
                    success=False,
                    transition=transition,
                    validation_errors=validation_result.get_error_messages(),
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Step 3: Apply changes atomically (all-or-nothing with rollback)
            application_result = self._apply_transitions(transition, game_state)
            if not application_result.success:
                return StateTransitionResult(
                    success=False,
                    transition=transition,
                    application_errors=[application_result.error_message],
                    execution_time_ms=(time.time() - start_time) * 1000
                )
            
            # Step 4: Track statistics and audit trail (separate concern)
            execution_time = (time.time() - start_time) * 1000
            self._track_play_result(play_result, possession_team_id, game_state, 
                                  transition, execution_time)
            
            # Success! Create summary of changes
            changes_summary = self._create_changes_summary(transition)
            
            self.logger.info(f"Play processed successfully: {changes_summary}")
            
            return StateTransitionResult(
                success=True,
                transition=transition,
                execution_time_ms=execution_time,
                changes_summary=changes_summary
            )
            
        except Exception as e:
            # Unexpected error - log and return failure
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"Unexpected error in state transition: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return StateTransitionResult(
                success=False,
                application_errors=[error_msg],
                execution_time_ms=execution_time
            )
    
    def _calculate_transitions(self, play_result: PlayResult, 
                             game_state: GameState) -> GameStateTransition:
        """
        Step 1: Calculate all required state changes (pure functions).
        
        This replaces the complex logic scattered throughout the game loop
        with clean, testable pure functions.
        """
        self.logger.debug("Calculating state transitions...")
        
        # Use the pure calculation functions to determine what should change
        base_transition = self.calculator.calculate_all_transitions(play_result, game_state)
        
        # Enhance the base transition with metadata for full system integration
        return self._enhance_transition(base_transition, play_result, game_state)
    
    def _enhance_transition(self, base_transition: BaseGameStateTransition, 
                          play_result: PlayResult, game_state: GameState) -> GameStateTransition:
        """
        Convert a BaseGameStateTransition to a full GameStateTransition with metadata.
        
        Args:
            base_transition: Lightweight transition from calculator
            play_result: Original play result that caused this transition
            game_state: Current game state for context
            
        Returns:
            Enhanced GameStateTransition with all metadata
        """
        # Determine possession team ID from game state
        possession_team_id = str(game_state.field.possession_team_id) if hasattr(game_state.field, 'possession_team_id') else "unknown"
        
        # Create descriptive transition reason
        transition_reason = f"{play_result.play_type} play: {play_result.outcome}"
        if play_result.yards_gained != 0:
            transition_reason += f" for {play_result.yards_gained} yards"
        if play_result.is_score:
            transition_reason += f" - SCORE ({play_result.score_points} points)"
        if play_result.is_turnover:
            transition_reason += " - TURNOVER"
        
        return enhance_base_transition(
            base_transition=base_transition,
            play_result=play_result,
            possession_team_id=possession_team_id,
            transition_reason=transition_reason
        )
    
    def _validate_transitions(self, transition: GameStateTransition):
        """
        Step 2: Validate that all transitions comply with NFL rules.
        
        This prevents illegal game states from being applied.
        """
        self.logger.debug("Validating state transitions...")
        
        # Comprehensive rule validation
        return self.validator.validate_transition(transition)
    
    def _apply_transitions(self, transition: GameStateTransition, 
                          game_state: GameState):
        """
        Step 3: Apply all changes atomically with rollback capability.
        
        This replaces the scattered state updates with atomic, transactional changes.
        """
        self.logger.debug("Applying state transitions...")
        
        # Atomic application with rollback on any failure
        return self.applicator.apply_transition(transition, game_state)
    
    def _track_play_result(self, play_result: PlayResult, possession_team_id: str,
                          game_state: GameState, transition: GameStateTransition,
                          execution_time: float):
        """
        Step 4: Record statistics and audit trail (separate concern).
        
        This replaces the scattered statistics tracking with a clean observer pattern.
        """
        self.logger.debug("Recording play statistics and audit trail...")
        
        # Observer pattern - tracking system observes but doesn't modify state
        self.tracking_system.record_play(play_result, possession_team_id, 
                                       game_state, execution_time)
        
        # Record transitions for debugging (if advanced tracking available)
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'auditor'):
            self.tracking_system.auditor.record_state_transition(transition)
    
    def _create_changes_summary(self, transition: GameStateTransition) -> str:
        """Create human-readable summary of what changed"""
        changes = []
        
        if transition.field_transition:
            ft = transition.field_transition
            if ft.field_position_change != 0:
                changes.append(f"field {ft.old_field_position}→{ft.new_field_position}")
            if ft.down_change:
                changes.append(f"down {ft.old_down}→{ft.new_down}")
        
        if transition.possession_transition and transition.possession_transition.possession_changed:
            changes.append("possession change")
        
        if transition.score_transition and transition.score_transition.points_scored > 0:
            changes.append(f"+{transition.score_transition.points_scored} points")
        
        if transition.clock_transition:
            ct = transition.clock_transition
            changes.append(f"-{ct.time_elapsed}s")
        
        return ", ".join(changes) if changes else "no changes"
    
    def get_game_statistics(self) -> Dict:
        """
        Get comprehensive game statistics.
        
        Returns complete statistics that previously required complex manual tracking.
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'get_comprehensive_summary'):
            return self.tracking_system.get_comprehensive_summary()
        else:
            # Fallback: use basic tracking
            return self.tracking_system.get_game_statistics()
    
    def get_audit_trail(self) -> List[Dict]:
        """
        Get complete audit trail of all game events.
        
        Useful for debugging, replay, and analysis.
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'auditor'):
            return self.tracking_system.auditor.get_complete_audit_trail()
        else:
            # Fallback: basic audit trail
            return self.tracking_system.get_audit_trail()
    
    def export_game_data(self, filename: Optional[str] = None) -> str:
        """
        Export complete game data including statistics and audit trail.
        
        Args:
            filename: Optional filename for export
            
        Returns:
            JSON string of complete game data
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'auditor'):
            return self.tracking_system.auditor.export_to_json(filename)
        else:
            # Fallback: basic export
            return self.tracking_system.export_game_data(filename)
    
    def get_comprehensive_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive summary from all tracking systems.
        
        Returns complete analytics including statistics, performance, and audit summary.
        This is the primary method for getting enhanced tracking data.
        
        Returns:
            Comprehensive tracking data if advanced tracking available, None otherwise
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'get_comprehensive_summary'):
            return self.tracking_system.get_comprehensive_summary()
        else:
            # Fallback: return None to indicate advanced tracking not available
            return None
    
    def get_performance_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Get performance analysis from tracking system.
        
        Returns:
            Performance metrics and bottleneck analysis if available
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'performance'):
            return self.tracking_system.performance.get_performance_summary()
        else:
            return None
    
    def get_bottleneck_analysis(self) -> Optional[Dict[str, Any]]:
        """
        Get performance bottleneck analysis.
        
        Returns:
            Detailed bottleneck analysis for optimization
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'performance'):
            return self.tracking_system.performance.get_bottleneck_analysis()
        else:
            return None
    
    def export_comprehensive_data(self, base_filename: str) -> Optional[Dict[str, str]]:
        """
        Export all tracking data to files.
        
        Args:
            base_filename: Base filename for exports (will be extended with suffixes)
            
        Returns:
            Dictionary mapping data types to filenames if advanced tracking available
        """
        if TRACKING_AVAILABLE and hasattr(self.tracking_system, 'export_all_data'):
            return self.tracking_system.export_all_data(base_filename)
        else:
            # Fallback: basic export to single file
            filename = f"{base_filename}_basic.json"
            data = self.tracking_system.export_game_data(filename)
            
            # Write data to file
            with open(filename, 'w') as f:
                f.write(data)
            
            return {"basic_tracking": filename}
    
    def has_advanced_tracking(self) -> bool:
        """
        Check if advanced tracking system is available.
        
        Returns:
            True if comprehensive tracking is available, False if using basic fallback
        """
        return TRACKING_AVAILABLE and hasattr(self.tracking_system, 'get_comprehensive_summary')
    
    def get_tracking_capabilities(self) -> Dict[str, bool]:
        """
        Get information about available tracking capabilities.
        
        Returns:
            Dictionary describing what tracking features are available
        """
        capabilities = {
            "basic_statistics": True,  # Always available
            "basic_audit_trail": True,  # Always available
            "comprehensive_statistics": False,
            "performance_monitoring": False,
            "detailed_audit_trail": False,
            "export_capabilities": True,  # Always available in some form
        }
        
        if TRACKING_AVAILABLE:
            capabilities.update({
                "comprehensive_statistics": hasattr(self.tracking_system, 'statistics'),
                "performance_monitoring": hasattr(self.tracking_system, 'performance'),
                "detailed_audit_trail": hasattr(self.tracking_system, 'auditor'),
            })
        
        return capabilities


def create_game_state_manager(game_id: str, home_team_id: str, 
                            away_team_id: str) -> GameStateManager:
    """
    Factory function to create a properly configured Game State Manager.
    
    Args:
        game_id: Unique identifier for the game
        home_team_id: ID of the home team  
        away_team_id: ID of the away team
        
    Returns:
        Fully configured GameStateManager ready for use
    """
    return GameStateManager(game_id, home_team_id, away_team_id)