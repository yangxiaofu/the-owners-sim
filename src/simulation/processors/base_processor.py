"""
Base Result Processor

Abstract base class for processing simulation results with different strategies
and season state management capabilities.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional, Type
from dataclasses import dataclass
from enum import Enum
import logging

from ..results.base_result import AnySimulationResult, ProcessingContext, ProcessingResult


class ProcessingStrategy(Enum):
    """Different strategies for processing simulation results"""
    STATISTICS_ONLY = "statistics_only"      # Only collect statistics, no state changes
    FULL_PROGRESSION = "full_progression"    # Full season progression with all state updates
    GAME_SIMULATION = "game_simulation"      # Focus on game-related processing only
    DEVELOPMENT_FOCUS = "development_focus"  # Focus on player/team development
    INTELLIGENCE_GATHERING = "intelligence_gathering"  # Focus on scouting and intelligence
    CUSTOM = "custom"                        # Custom processing rules


@dataclass
class ProcessorConfig:
    """Configuration for result processors"""
    strategy: ProcessingStrategy = ProcessingStrategy.FULL_PROGRESSION
    enable_statistics: bool = True
    enable_state_updates: bool = True
    enable_side_effects: bool = True
    
    # Specific feature toggles
    update_standings: bool = True
    update_player_stats: bool = True
    process_injuries: bool = True
    update_chemistry: bool = True
    process_development: bool = True
    
    # Thresholds and limits
    max_side_effects_per_result: int = 10
    stat_aggregation_threshold: float = 0.1
    state_change_threshold: float = 0.05
    
    # Logging and debugging
    verbose_logging: bool = False
    debug_mode: bool = False
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a specific feature is enabled"""
        return getattr(self, f"enable_{feature_name}", False) or getattr(self, f"update_{feature_name}", False)


class BaseResultProcessor(ABC):
    """
    Abstract base class for processing simulation results.
    
    Each event type should have its own processor that knows how to handle
    the specific data and requirements for that result type.
    """
    
    def __init__(self, config: Optional[ProcessorConfig] = None):
        """
        Initialize processor with configuration
        
        Args:
            config: Processing configuration, uses defaults if None
        """
        self.config = config or ProcessorConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Statistics and metrics tracking
        self.processed_results_count = 0
        self.successful_processing_count = 0
        self.total_processing_time = 0.0
        
        # Processing history for debugging
        self.processing_history: List[Dict[str, Any]] = []
    
    @abstractmethod
    def can_process(self, result: AnySimulationResult) -> bool:
        """
        Check if this processor can handle the given result type.
        
        Args:
            result: Simulation result to check
            
        Returns:
            bool: True if this processor can handle this result type
        """
        pass
    
    @abstractmethod 
    def process_result(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """
        Process a simulation result with the given context.
        
        This is the main processing method that each processor must implement.
        Should handle all the specific logic for processing this result type.
        
        Args:
            result: The simulation result to process
            context: Current season/game context for processing decisions
            
        Returns:
            ProcessingResult: Details about what was processed and updated
        """
        pass
    
    def process_with_error_handling(self, result: AnySimulationResult, context: ProcessingContext) -> ProcessingResult:
        """
        Process result with comprehensive error handling and logging.
        
        Args:
            result: Simulation result to process
            context: Processing context
            
        Returns:
            ProcessingResult: Processing outcome with error information if needed
        """
        start_time = datetime.now()
        
        try:
            # Validate inputs
            if not self.can_process(result):
                return ProcessingResult(
                    processed_successfully=False,
                    processing_type=self.__class__.__name__,
                    error_messages=[f"Processor {self.__class__.__name__} cannot handle result type {type(result).__name__}"]
                )
            
            # Pre-processing validation
            validation_errors = self._validate_result(result, context)
            if validation_errors:
                return ProcessingResult(
                    processed_successfully=False,
                    processing_type=self.__class__.__name__,
                    error_messages=validation_errors
                )
            
            # Execute main processing
            processing_result = self.process_result(result, context)
            
            # Post-processing validation and finalization
            self._finalize_processing(processing_result, result, context)
            
            # Update metrics
            self.processed_results_count += 1
            if processing_result.processed_successfully:
                self.successful_processing_count += 1
            
            # Log processing details if verbose
            if self.config.verbose_logging:
                self.logger.info(f"Processed {type(result).__name__}: {processing_result.get_summary()}")
            
            return processing_result
            
        except Exception as e:
            # Handle any unexpected errors
            error_message = f"Unexpected error processing {type(result).__name__}: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            
            return ProcessingResult(
                processed_successfully=False,
                processing_type=self.__class__.__name__,
                error_messages=[error_message]
            )
        
        finally:
            # Update timing metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.total_processing_time += processing_time
            
            # Store processing history if debug mode
            if self.config.debug_mode:
                self.processing_history.append({
                    "timestamp": start_time,
                    "result_type": type(result).__name__,
                    "processing_time_seconds": processing_time,
                    "success": getattr(processing_result, 'processed_successfully', False) if 'processing_result' in locals() else False
                })
    
    def _validate_result(self, result: AnySimulationResult, context: ProcessingContext) -> List[str]:
        """
        Validate result and context before processing.
        
        Args:
            result: Result to validate
            context: Context to validate
            
        Returns:
            List of validation error messages, empty if valid
        """
        errors = []
        
        # Basic result validation
        if not result.success and self.config.strategy != ProcessingStrategy.STATISTICS_ONLY:
            errors.append("Cannot process failed simulation result in current strategy")
        
        if not result.teams_affected:
            errors.append("Result must affect at least one team")
        
        # Context validation
        if context.current_date > datetime.now():
            errors.append("Processing context date cannot be in the future")
        
        if context.season_week < 0 or context.season_week > 30:
            errors.append(f"Invalid season week: {context.season_week}")
        
        return errors
    
    def _finalize_processing(self, processing_result: ProcessingResult, 
                           original_result: AnySimulationResult, 
                           context: ProcessingContext) -> None:
        """
        Finalize processing by applying any last-minute logic.
        
        Args:
            processing_result: The processing result to finalize
            original_result: Original simulation result
            context: Processing context
        """
        # Ensure teams_updated is populated
        if not processing_result.teams_updated and original_result.teams_affected:
            processing_result.teams_updated = original_result.teams_affected.copy()
        
        # Cap side effects if configured
        if len(processing_result.side_effects) > self.config.max_side_effects_per_result:
            excess_effects = len(processing_result.side_effects) - self.config.max_side_effects_per_result
            processing_result.side_effects = processing_result.side_effects[:self.config.max_side_effects_per_result]
            processing_result.add_side_effect(f"Truncated {excess_effects} additional side effects")
        
        # Add processor identification
        processing_result.add_state_change("processor_used", self.__class__.__name__)
        processing_result.add_state_change("processing_strategy", self.config.strategy.value)
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics and metrics.
        
        Returns:
            Dictionary with processing statistics
        """
        success_rate = 0.0
        if self.processed_results_count > 0:
            success_rate = self.successful_processing_count / self.processed_results_count
        
        avg_processing_time = 0.0
        if self.processed_results_count > 0:
            avg_processing_time = self.total_processing_time / self.processed_results_count
        
        return {
            "processor_type": self.__class__.__name__,
            "results_processed": self.processed_results_count,
            "successful_processing": self.successful_processing_count,
            "success_rate": success_rate,
            "total_processing_time_seconds": self.total_processing_time,
            "average_processing_time_seconds": avg_processing_time,
            "strategy": self.config.strategy.value,
            "features_enabled": {
                "statistics": self.config.enable_statistics,
                "state_updates": self.config.enable_state_updates,
                "side_effects": self.config.enable_side_effects
            }
        }
    
    def reset_stats(self) -> None:
        """Reset processing statistics"""
        self.processed_results_count = 0
        self.successful_processing_count = 0
        self.total_processing_time = 0.0
        self.processing_history.clear()
    
    def supports_strategy(self, strategy: ProcessingStrategy) -> bool:
        """
        Check if this processor supports a specific processing strategy.
        
        Args:
            strategy: Strategy to check
            
        Returns:
            bool: True if strategy is supported
        """
        # Base implementation - most processors support all strategies
        return True
    
    def __str__(self) -> str:
        """String representation of processor"""
        return f"{self.__class__.__name__}(strategy={self.config.strategy.value})"
    
    def __repr__(self) -> str:
        """Detailed representation for debugging"""
        return (f"{self.__class__.__name__}(processed={self.processed_results_count}, "
                f"success_rate={self.successful_processing_count/max(1, self.processed_results_count):.2f}, "
                f"strategy={self.config.strategy.value})")