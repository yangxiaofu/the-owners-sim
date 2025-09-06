"""
Unified Formation System - Type-Safe Formation Architecture

This module provides a comprehensive enum-based formation system that:
1. Eliminates string-based formation handling
2. Provides type safety across all simulators  
3. Maintains context-appropriate naming for different simulator needs
4. Serves as single source of truth for all formation definitions
5. Prevents formation mismatch bugs between components

This replaces the previous class constant approach with proper Python enums
and context-aware value mapping for different simulator requirements.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List


class SimulatorContext(Enum):
    """Context types for different formation usage scenarios"""
    COORDINATOR = "coordinator"      # Used by DefensiveCoordinator for formation selection
    PUNT_SIMULATOR = "punt"         # Used by PuntSimulator for punt play validation  
    FIELD_GOAL_SIMULATOR = "fg"     # Used by FieldGoalSimulator for FG play validation
    KICKOFF_SIMULATOR = "kickoff"   # Used by KickoffSimulator for kickoff validation
    GENERAL_SIMULATOR = "general"   # Used by general play simulators


@dataclass
class FormationDefinition:
    """
    Defines formation names for different simulator contexts.
    
    This allows the same logical formation (e.g., punt return) to have
    appropriate naming conventions for different parts of the system:
    - DefensiveCoordinator uses "punt_return" 
    - PuntSimulator expects "defensive_punt_return"
    - Display systems use "Punt Return"
    """
    coordinator_name: str       # Name used by coordinators for formation selection
    punt_name: str             # Name expected by PuntSimulator
    field_goal_name: str       # Name expected by FieldGoalSimulator  
    kickoff_name: str          # Name expected by KickoffSimulator
    general_name: str          # Name used by general simulators
    display_name: str          # Human-readable name for UI/debugging
    personnel_requirements: Dict[str, int] = None  # Personnel package requirements


class UnifiedDefensiveFormation(Enum):
    """
    Unified defensive formation enum with context-aware naming.
    
    Each formation is defined once with appropriate names for all contexts,
    eliminating the previous formation/play-type naming mismatches.
    """
    
    # Base defensive formations
    FOUR_THREE_BASE = FormationDefinition(
        coordinator_name="4_3_base",
        punt_name="defensive_4_3_base", 
        field_goal_name="4_3_base",
        kickoff_name="4_3_base",
        general_name="4_3_base",
        display_name="4-3 Base Defense",
        personnel_requirements={"LB": 3, "DB": 4, "DL": 4}
    )
    
    THREE_FOUR_BASE = FormationDefinition(
        coordinator_name="3_4_base",
        punt_name="defensive_3_4_base",
        field_goal_name="3_4_base", 
        kickoff_name="3_4_base",
        general_name="3_4_base",
        display_name="3-4 Base Defense",
        personnel_requirements={"LB": 4, "DB": 4, "DL": 3}
    )
    
    # Coverage-based formations
    NICKEL_DEFENSE = FormationDefinition(
        coordinator_name="nickel_defense",
        punt_name="defensive_nickel",
        field_goal_name="nickel_defense",
        kickoff_name="nickel_defense", 
        general_name="nickel_defense",
        display_name="Nickel Defense",
        personnel_requirements={"LB": 2, "DB": 5, "DL": 4}
    )
    
    DIME_DEFENSE = FormationDefinition(
        coordinator_name="dime_defense",
        punt_name="defensive_dime",
        field_goal_name="dime_defense",
        kickoff_name="dime_defense",
        general_name="dime_defense", 
        display_name="Dime Defense",
        personnel_requirements={"LB": 1, "DB": 6, "DL": 4}
    )
    
    # Punt-specific formations (the key ones causing the current bug)
    PUNT_RETURN = FormationDefinition(
        coordinator_name="punt_return",           # What DefensiveCoordinator uses
        punt_name="defensive_punt_return",        # What PuntSimulator expects ✅
        field_goal_name="punt_return",
        kickoff_name="punt_return",
        general_name="punt_return",
        display_name="Punt Return", 
        personnel_requirements={"ST": 11}  # Special teams unit
    )
    
    PUNT_BLOCK = FormationDefinition(
        coordinator_name="punt_block",
        punt_name="defensive_punt_block",         # Matches PuntSimulator expectations
        field_goal_name="punt_block",
        kickoff_name="punt_block",
        general_name="punt_block",
        display_name="Punt Block Rush",
        personnel_requirements={"ST": 11}
    )
    
    PUNT_SAFE = FormationDefinition(
        coordinator_name="punt_safe", 
        punt_name="defensive_punt_safe",          # Matches PuntSimulator expectations
        field_goal_name="punt_safe",
        kickoff_name="punt_safe",
        general_name="punt_safe",
        display_name="Punt Safe Coverage",
        personnel_requirements={"ST": 11}
    )
    
    SPREAD_RETURN = FormationDefinition(
        coordinator_name="spread_return",
        punt_name="defensive_spread_return",      # Matches PuntSimulator expectations
        field_goal_name="spread_return",
        kickoff_name="spread_return", 
        general_name="spread_return",
        display_name="Spread Punt Return",
        personnel_requirements={"ST": 11}
    )
    
    # Field goal formations
    FIELD_GOAL_BLOCK = FormationDefinition(
        coordinator_name="field_goal_block",
        punt_name="defensive_fg_block",
        field_goal_name="defensive_field_goal_block",  # Context-specific naming
        kickoff_name="field_goal_block",
        general_name="field_goal_block",
        display_name="Field Goal Block",
        personnel_requirements={"ST": 11}
    )
    
    # Kickoff formations  
    KICK_RETURN = FormationDefinition(
        coordinator_name="kick_return",
        punt_name="defensive_kick_return",
        field_goal_name="kick_return",
        kickoff_name="defensive_kickoff_return",   # Context-specific naming
        general_name="kick_return",
        display_name="Kickoff Return",
        personnel_requirements={"ST": 11}
    )
    
    # Pressure formations
    BLITZ_PACKAGE = FormationDefinition(
        coordinator_name="blitz_package",
        punt_name="defensive_blitz",
        field_goal_name="blitz_package",
        kickoff_name="blitz_package",
        general_name="blitz_package",
        display_name="Blitz Package", 
        personnel_requirements={"LB": 2, "DB": 4, "DL": 5}  # Extra rusher
    )
    
    def for_context(self, context: SimulatorContext) -> str:
        """
        Get the appropriate formation name for a specific simulator context.
        
        This is the key method that eliminates formation naming mismatches.
        Instead of hardcoded strings, components get context-appropriate names.
        
        Args:
            context: SimulatorContext enum specifying which naming convention to use
            
        Returns:
            str: Formation name appropriate for the specified context
            
        Example:
            UnifiedDefensiveFormation.PUNT_RETURN.for_context(SimulatorContext.COORDINATOR) 
            # Returns "punt_return" (for DefensiveCoordinator)
            
            UnifiedDefensiveFormation.PUNT_RETURN.for_context(SimulatorContext.PUNT_SIMULATOR)
            # Returns "defensive_punt_return" (for PuntSimulator)
        """
        formation_def = self.value
        
        if context == SimulatorContext.COORDINATOR:
            return formation_def.coordinator_name
        elif context == SimulatorContext.PUNT_SIMULATOR:
            return formation_def.punt_name
        elif context == SimulatorContext.FIELD_GOAL_SIMULATOR:
            return formation_def.field_goal_name
        elif context == SimulatorContext.KICKOFF_SIMULATOR:
            return formation_def.kickoff_name
        elif context == SimulatorContext.GENERAL_SIMULATOR:
            return formation_def.general_name
        else:
            raise ValueError(f"Unknown simulator context: {context}")
    
    def get_display_name(self) -> str:
        """Get human-readable formation name for UI/debugging"""
        return self.value.display_name
    
    def get_personnel_requirements(self) -> Dict[str, int]:
        """Get personnel requirements for this formation"""
        return self.value.personnel_requirements or {}
    
    @classmethod
    def get_punt_formations(cls) -> List['UnifiedDefensiveFormation']:
        """Get all punt-related defensive formations"""
        return [
            cls.PUNT_RETURN,
            cls.PUNT_BLOCK, 
            cls.PUNT_SAFE,
            cls.SPREAD_RETURN
        ]
    
    @classmethod
    def get_field_goal_formations(cls) -> List['UnifiedDefensiveFormation']:
        """Get all field goal-related defensive formations"""
        return [
            cls.FIELD_GOAL_BLOCK,
            cls.PUNT_RETURN,  # Can also be used for FG situations
            cls.PUNT_SAFE
        ]
    
    @classmethod
    def get_kickoff_formations(cls) -> List['UnifiedDefensiveFormation']:
        """Get all kickoff-related defensive formations"""
        return [
            cls.KICK_RETURN,
            cls.PUNT_RETURN,  # Can also be used for kickoff situations
            cls.PUNT_SAFE     # Can be used for onside kick defense
        ]
    
    @classmethod  
    def get_base_formations(cls) -> List['UnifiedDefensiveFormation']:
        """Get core base defensive formations"""
        return [
            cls.FOUR_THREE_BASE,
            cls.THREE_FOUR_BASE,
            cls.NICKEL_DEFENSE,
            cls.DIME_DEFENSE
        ]
    
    @classmethod
    def from_coordinator_name(cls, coordinator_name: str) -> 'UnifiedDefensiveFormation':
        """
        Find formation enum by coordinator name (for backwards compatibility).
        
        Args:
            coordinator_name: Formation name used by DefensiveCoordinator
            
        Returns:
            UnifiedDefensiveFormation enum matching the coordinator name
            
        Raises:
            ValueError: If coordinator name not found
        """
        for formation in cls:
            if formation.value.coordinator_name == coordinator_name:
                return formation
        raise ValueError(f"No formation found for coordinator name: {coordinator_name}")
    
    @classmethod
    def from_punt_name(cls, punt_name: str) -> 'UnifiedDefensiveFormation':
        """
        Find formation enum by punt simulator name (for validation).
        
        Args:
            punt_name: Formation name used by PuntSimulator
            
        Returns:
            UnifiedDefensiveFormation enum matching the punt name
            
        Raises:
            ValueError: If punt name not found
        """
        for formation in cls:
            if formation.value.punt_name == punt_name:
                return formation
        raise ValueError(f"No formation found for punt name: {punt_name}")


class UnifiedOffensiveFormation(Enum):
    """
    Unified offensive formation enum (for completeness).
    
    While the current bug is in defensive formations, we should apply
    the same architecture to offensive formations for consistency.
    """
    
    I_FORMATION = FormationDefinition(
        coordinator_name="i_formation",
        punt_name="offensive_i_formation", 
        field_goal_name="i_formation",
        kickoff_name="i_formation",
        general_name="i_formation",
        display_name="I-Formation",
        personnel_requirements={"RB": 1, "FB": 1, "TE": 1, "WR": 2, "OL": 5, "QB": 1}
    )
    
    SHOTGUN = FormationDefinition(
        coordinator_name="shotgun",
        punt_name="offensive_shotgun",
        field_goal_name="shotgun",
        kickoff_name="shotgun", 
        general_name="shotgun",
        display_name="Shotgun",
        personnel_requirements={"RB": 1, "TE": 1, "WR": 3, "OL": 5, "QB": 1}
    )
    
    PUNT = FormationDefinition(
        coordinator_name="punt",
        punt_name="offensive_punt",         # Context-specific for punt plays
        field_goal_name="punt",
        kickoff_name="punt",
        general_name="punt", 
        display_name="Punt Formation",
        personnel_requirements={"ST": 11}   # Special teams punt unit
    )
    
    # Add for_context method similar to defensive formations
    def for_context(self, context: SimulatorContext) -> str:
        """Get appropriate offensive formation name for simulator context"""
        formation_def = self.value
        
        if context == SimulatorContext.COORDINATOR:
            return formation_def.coordinator_name
        elif context == SimulatorContext.PUNT_SIMULATOR:
            return formation_def.punt_name
        elif context == SimulatorContext.FIELD_GOAL_SIMULATOR:
            return formation_def.field_goal_name
        elif context == SimulatorContext.KICKOFF_SIMULATOR:
            return formation_def.kickoff_name
        elif context == SimulatorContext.GENERAL_SIMULATOR:
            return formation_def.general_name
        else:
            raise ValueError(f"Unknown simulator context: {context}")


# Helper functions for migration and backwards compatibility
def get_defensive_formation_by_old_name(old_name: str) -> UnifiedDefensiveFormation:
    """
    Migration helper: convert old string formation names to new enum.
    
    This helps during the transition period where some code still uses 
    the old string-based formation names.
    """
    # Map old formation names to new enum values
    old_name_mapping = {
        "punt_return": UnifiedDefensiveFormation.PUNT_RETURN,
        "punt_block": UnifiedDefensiveFormation.PUNT_BLOCK,
        "punt_safe": UnifiedDefensiveFormation.PUNT_SAFE,
        "spread_return": UnifiedDefensiveFormation.SPREAD_RETURN,
        "4_3_base": UnifiedDefensiveFormation.FOUR_THREE_BASE,
        "3_4_base": UnifiedDefensiveFormation.THREE_FOUR_BASE,
        "nickel_defense": UnifiedDefensiveFormation.NICKEL_DEFENSE,
        "dime_defense": UnifiedDefensiveFormation.DIME_DEFENSE,
        "field_goal_block": UnifiedDefensiveFormation.FIELD_GOAL_BLOCK,
        "kick_return": UnifiedDefensiveFormation.KICK_RETURN,
        "blitz_package": UnifiedDefensiveFormation.BLITZ_PACKAGE,
    }
    
    if old_name in old_name_mapping:
        return old_name_mapping[old_name]
    else:
        raise ValueError(f"Unknown old formation name: {old_name}")