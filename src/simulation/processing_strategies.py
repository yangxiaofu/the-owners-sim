"""
Processing Strategies

Pre-configured processing strategies for different simulation modes and use cases.
Provides convenient factory methods for common simulation scenarios.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .processors.base_processor import ProcessorConfig, ProcessingStrategy


class SimulationMode(Enum):
    """High-level simulation modes for different use cases"""
    QUICK_STATS = "quick_stats"              # Statistics collection only, minimal processing
    SEASON_SIMULATION = "season_simulation"  # Full season progression with all features
    DEVELOPMENT_FOCUS = "development_focus"  # Focus on player/team development tracking
    ANALYTICS_MODE = "analytics_mode"        # Enhanced statistics and trend analysis
    NARRATIVE_MODE = "narrative_mode"        # Focus on storylines and highlights
    LIGHTWEIGHT = "lightweight"             # Minimal overhead for performance
    CUSTOM = "custom"                        # User-defined configuration


@dataclass
class StrategyProfile:
    """Complete strategy profile for configuring simulation processing"""
    name: str
    description: str
    processing_strategy: ProcessingStrategy
    processor_config: ProcessorConfig
    season_tracking_enabled: bool = True
    
    # Feature toggles
    enable_player_development: bool = True
    enable_injury_tracking: bool = True
    enable_chemistry_changes: bool = True
    enable_narrative_events: bool = True
    enable_detailed_statistics: bool = True
    
    # Performance settings
    max_side_effects_per_result: int = 10
    enable_verbose_logging: bool = False
    
    def to_processor_config(self) -> ProcessorConfig:
        """Convert to ProcessorConfig for use with processors"""
        return ProcessorConfig(
            strategy=self.processing_strategy,
            enable_statistics=self.enable_detailed_statistics,
            enable_state_updates=True,
            enable_side_effects=self.enable_narrative_events,
            update_standings=True,
            update_player_stats=self.enable_detailed_statistics,
            process_injuries=self.enable_injury_tracking,
            update_chemistry=self.enable_chemistry_changes,
            process_development=self.enable_player_development,
            max_side_effects_per_result=self.max_side_effects_per_result,
            verbose_logging=self.enable_verbose_logging
        )


class ProcessingStrategyFactory:
    """
    Factory for creating pre-configured processing strategies for different simulation modes.
    
    Provides convenient methods to get optimal configurations for common use cases
    without requiring users to manually configure all processor settings.
    """
    
    _STRATEGY_PROFILES: Dict[SimulationMode, StrategyProfile] = {
        
        SimulationMode.QUICK_STATS: StrategyProfile(
            name="Quick Statistics",
            description="Fast statistics collection with minimal processing overhead",
            processing_strategy=ProcessingStrategy.STATISTICS_ONLY,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.STATISTICS_ONLY,
                enable_statistics=True,
                enable_state_updates=False,
                enable_side_effects=False,
                update_player_stats=True,
                process_injuries=False,
                update_chemistry=False,
                process_development=False,
                max_side_effects_per_result=0,
                verbose_logging=False
            ),
            season_tracking_enabled=False,
            enable_player_development=False,
            enable_injury_tracking=False,
            enable_chemistry_changes=False,
            enable_narrative_events=False,
            enable_detailed_statistics=True,
            max_side_effects_per_result=0,
            enable_verbose_logging=False
        ),
        
        SimulationMode.SEASON_SIMULATION: StrategyProfile(
            name="Full Season Simulation",
            description="Complete season progression with all features enabled",
            processing_strategy=ProcessingStrategy.FULL_PROGRESSION,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.FULL_PROGRESSION,
                enable_statistics=True,
                enable_state_updates=True,
                enable_side_effects=True,
                update_standings=True,
                update_player_stats=True,
                process_injuries=True,
                update_chemistry=True,
                process_development=True,
                max_side_effects_per_result=15,
                verbose_logging=False
            ),
            season_tracking_enabled=True,
            enable_player_development=True,
            enable_injury_tracking=True,
            enable_chemistry_changes=True,
            enable_narrative_events=True,
            enable_detailed_statistics=True,
            max_side_effects_per_result=15,
            enable_verbose_logging=False
        ),
        
        SimulationMode.DEVELOPMENT_FOCUS: StrategyProfile(
            name="Development Focus",
            description="Emphasis on player and team development tracking",
            processing_strategy=ProcessingStrategy.DEVELOPMENT_FOCUS,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.DEVELOPMENT_FOCUS,
                enable_statistics=True,
                enable_state_updates=True,
                enable_side_effects=True,
                update_standings=False,  # Less focus on standings
                update_player_stats=True,
                process_injuries=True,
                update_chemistry=True,
                process_development=True,
                max_side_effects_per_result=8,
                verbose_logging=False
            ),
            season_tracking_enabled=True,
            enable_player_development=True,
            enable_injury_tracking=True,
            enable_chemistry_changes=True,
            enable_narrative_events=True,
            enable_detailed_statistics=True,
            max_side_effects_per_result=8,
            enable_verbose_logging=False
        ),
        
        SimulationMode.ANALYTICS_MODE: StrategyProfile(
            name="Analytics Mode",
            description="Enhanced statistics collection and analysis",
            processing_strategy=ProcessingStrategy.FULL_PROGRESSION,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.FULL_PROGRESSION,
                enable_statistics=True,
                enable_state_updates=True,
                enable_side_effects=False,  # Focus on data, not narrative
                update_standings=True,
                update_player_stats=True,
                process_injuries=True,
                update_chemistry=True,
                process_development=True,
                max_side_effects_per_result=3,
                stat_aggregation_threshold=0.05,  # More sensitive aggregation
                verbose_logging=False
            ),
            season_tracking_enabled=True,
            enable_player_development=True,
            enable_injury_tracking=True,
            enable_chemistry_changes=True,
            enable_narrative_events=False,
            enable_detailed_statistics=True,
            max_side_effects_per_result=3,
            enable_verbose_logging=False
        ),
        
        SimulationMode.NARRATIVE_MODE: StrategyProfile(
            name="Narrative Mode",
            description="Focus on storylines, highlights, and narrative events",
            processing_strategy=ProcessingStrategy.FULL_PROGRESSION,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.FULL_PROGRESSION,
                enable_statistics=True,
                enable_state_updates=True,
                enable_side_effects=True,
                update_standings=True,
                update_player_stats=True,
                process_injuries=True,
                update_chemistry=True,
                process_development=True,
                max_side_effects_per_result=20,  # More narrative events
                verbose_logging=False
            ),
            season_tracking_enabled=True,
            enable_player_development=True,
            enable_injury_tracking=True,
            enable_chemistry_changes=True,
            enable_narrative_events=True,
            enable_detailed_statistics=True,
            max_side_effects_per_result=20,
            enable_verbose_logging=False
        ),
        
        SimulationMode.LIGHTWEIGHT: StrategyProfile(
            name="Lightweight Mode",
            description="Minimal processing for maximum performance",
            processing_strategy=ProcessingStrategy.STATISTICS_ONLY,
            processor_config=ProcessorConfig(
                strategy=ProcessingStrategy.STATISTICS_ONLY,
                enable_statistics=True,
                enable_state_updates=False,
                enable_side_effects=False,
                update_standings=False,
                update_player_stats=False,
                process_injuries=False,
                update_chemistry=False,
                process_development=False,
                max_side_effects_per_result=0,
                verbose_logging=False
            ),
            season_tracking_enabled=False,
            enable_player_development=False,
            enable_injury_tracking=False,
            enable_chemistry_changes=False,
            enable_narrative_events=False,
            enable_detailed_statistics=False,
            max_side_effects_per_result=0,
            enable_verbose_logging=False
        )
    }
    
    @classmethod
    def get_strategy_profile(cls, mode: SimulationMode) -> StrategyProfile:
        """
        Get a pre-configured strategy profile for a simulation mode
        
        Args:
            mode: The simulation mode to get configuration for
            
        Returns:
            StrategyProfile: Complete configuration for the mode
            
        Raises:
            ValueError: If the mode is not supported or is CUSTOM
        """
        if mode == SimulationMode.CUSTOM:
            raise ValueError("CUSTOM mode requires manual configuration - use create_custom_profile()")
        
        if mode not in cls._STRATEGY_PROFILES:
            raise ValueError(f"Unsupported simulation mode: {mode}")
        
        return cls._STRATEGY_PROFILES[mode]
    
    @classmethod
    def create_custom_profile(cls, name: str, description: str, **config_overrides) -> StrategyProfile:
        """
        Create a custom strategy profile with specific overrides
        
        Args:
            name: Name for the custom profile
            description: Description of the custom profile
            **config_overrides: Specific configuration overrides
            
        Returns:
            StrategyProfile: Custom configured profile
        """
        # Start with season simulation as base
        base_profile = cls._STRATEGY_PROFILES[SimulationMode.SEASON_SIMULATION]
        
        # Apply overrides
        custom_config = {
            "name": name,
            "description": description,
            "processing_strategy": config_overrides.get("processing_strategy", base_profile.processing_strategy),
            "processor_config": base_profile.processor_config,  # Will be updated below
            "season_tracking_enabled": config_overrides.get("season_tracking_enabled", base_profile.season_tracking_enabled),
            "enable_player_development": config_overrides.get("enable_player_development", base_profile.enable_player_development),
            "enable_injury_tracking": config_overrides.get("enable_injury_tracking", base_profile.enable_injury_tracking),
            "enable_chemistry_changes": config_overrides.get("enable_chemistry_changes", base_profile.enable_chemistry_changes),
            "enable_narrative_events": config_overrides.get("enable_narrative_events", base_profile.enable_narrative_events),
            "enable_detailed_statistics": config_overrides.get("enable_detailed_statistics", base_profile.enable_detailed_statistics),
            "max_side_effects_per_result": config_overrides.get("max_side_effects_per_result", base_profile.max_side_effects_per_result),
            "enable_verbose_logging": config_overrides.get("enable_verbose_logging", base_profile.enable_verbose_logging)
        }
        
        custom_profile = StrategyProfile(**custom_config)
        
        # Update processor config with custom settings
        custom_profile.processor_config = custom_profile.to_processor_config()
        
        return custom_profile
    
    @classmethod
    def get_available_modes(cls) -> Dict[SimulationMode, str]:
        """
        Get all available simulation modes and their descriptions
        
        Returns:
            Dictionary mapping modes to their descriptions
        """
        return {
            mode: profile.description 
            for mode, profile in cls._STRATEGY_PROFILES.items()
        }
    
    @classmethod
    def get_processor_config(cls, mode: SimulationMode) -> ProcessorConfig:
        """
        Get processor configuration for a specific mode
        
        Args:
            mode: Simulation mode
            
        Returns:
            ProcessorConfig: Processor configuration for the mode
        """
        profile = cls.get_strategy_profile(mode)
        return profile.to_processor_config()
    
    @classmethod
    def create_calendar_manager_config(cls, mode: SimulationMode, 
                                     start_date, season_year: int = 2024) -> Dict[str, Any]:
        """
        Create calendar manager initialization configuration for a mode
        
        Args:
            mode: Simulation mode
            start_date: Start date for the calendar
            season_year: Season year
            
        Returns:
            Dictionary of configuration parameters for CalendarManager
        """
        profile = cls.get_strategy_profile(mode)
        
        return {
            "start_date": start_date,
            "enable_result_processing": profile.season_tracking_enabled,
            "processing_strategy": profile.processing_strategy,
            "season_year": season_year
        }


def get_quick_stats_config() -> ProcessorConfig:
    """Convenience function to get quick stats configuration"""
    return ProcessingStrategyFactory.get_processor_config(SimulationMode.QUICK_STATS)


def get_full_season_config() -> ProcessorConfig:
    """Convenience function to get full season configuration"""
    return ProcessingStrategyFactory.get_processor_config(SimulationMode.SEASON_SIMULATION)


def get_development_config() -> ProcessorConfig:
    """Convenience function to get development-focused configuration"""
    return ProcessingStrategyFactory.get_processor_config(SimulationMode.DEVELOPMENT_FOCUS)