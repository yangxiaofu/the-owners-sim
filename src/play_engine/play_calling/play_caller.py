"""
PlayCaller - Main interface for intelligent AI-driven play calling

Provides sophisticated play calling that considers multi-level coaching staff,
and game situation to generate realistic NFL-style play calls using the
CoachingStaff system with head coaches, offensive coordinators, and defensive coordinators.
"""

from typing import Optional, Dict, Any, List
from abc import ABC, abstractmethod
from dataclasses import dataclass
import random
import json
from pathlib import Path

from ..play_calls.offensive_play_call import OffensivePlayCall
from ..play_calls.defensive_play_call import DefensivePlayCall
from ..game_state.drive_manager import DriveSituation
from .coaching_staff import CoachingStaff
from .coach_archetype import CoachArchetype  # Keep for backward compatibility
from .playbook_loader import PlaybookLoader
from .fourth_down_matrix import FourthDownDecisionType


@dataclass
class PlayCallContext:
    """Extended context for play calling decisions"""
    situation: DriveSituation
    game_flow: Optional[str] = None  # "momentum_home", "momentum_away", "neutral"
    recent_plays: Optional[List[str]] = None  # Last 3-5 play types for sequencing
    opponent_tendencies: Optional[Dict[str, Any]] = None  # Future expansion
    weather_conditions: Optional[str] = None  # Future expansion
    

class PlayCallerBase(ABC):
    """Abstract base class for play callers"""
    
    @abstractmethod
    def select_offensive_play(self, context: PlayCallContext) -> OffensivePlayCall:
        """Select offensive play based on context"""
        pass
    
    @abstractmethod
    def select_defensive_play(self, context: PlayCallContext) -> DefensivePlayCall:
        """Select defensive play based on context"""
        pass


class PlayCaller(PlayCallerBase):
    """
    Intelligent PlayCaller with multi-level coaching staff integration
    
    This class uses the sophisticated CoachingStaff system with head coaches,
    offensive coordinators, and defensive coordinators working together with
    realistic decision hierarchies and override capabilities.
    """
    
    def __init__(self, coaching_staff: CoachingStaff, playbook_name: str = "balanced"):
        """
        Initialize PlayCaller with coaching staff and playbook
        
        Args:
            coaching_staff: CoachingStaff with HC/OC/DC hierarchy
            playbook_name: Name of playbook to load (e.g., "aggressive", "conservative") 
        """
        if not isinstance(coaching_staff, CoachingStaff):
            raise ValueError("PlayCaller requires a CoachingStaff instance")
        
        self.coaching_staff = coaching_staff
        self.playbook_loader = PlaybookLoader()
        self.playbook = self.playbook_loader.load_playbook(playbook_name)
        self.recent_calls = []  # Track recent play calls for sequencing
    
    def select_offensive_play(self, context: PlayCallContext) -> OffensivePlayCall:
        """
        Select offensive play using multi-level coaching staff system with new 4th down routing
        
        New Architecture:
        - 4th down decisions route to HeadCoach first for strategic decision
        - If GO_FOR_IT → normal coordinators handle execution
        - If PUNT/FIELD_GOAL → SpecialTeamsCoordinator handles execution
        
        Args:
            context: PlayCallContext with situation and additional factors
            
        Returns:
            OffensivePlayCall from coaching staff decision hierarchy or special teams coordinator
        """
        # Check for 4th down and route through new architecture
        if context.situation.down == 4:
            return self._handle_fourth_down_offensive_play(context)
        
        # Normal flow for downs 1-3: Convert PlayCallContext to the format expected by CoachingStaff
        coaching_context = self._convert_context_for_coaching_staff(context)
        
        # Use the sophisticated coaching staff system for play selection
        selected_play = self.coaching_staff.select_offensive_play(coaching_context)
        
        # Update play history for sequencing analysis
        self._update_play_history(selected_play)
        
        return selected_play
    
    def select_defensive_play(self, context: PlayCallContext) -> DefensivePlayCall:
        """
        Select defensive play using multi-level coaching staff system with new 4th down routing
        
        New Architecture:
        - 4th down decisions predict opponent choice and route accordingly
        - If opponent GO_FOR_IT → normal coordinators handle defense
        - If opponent PUNT/FIELD_GOAL → SpecialTeamsCoordinator handles defense
        
        Args:
            context: PlayCallContext with situation and additional factors
            
        Returns:
            DefensivePlayCall from coaching staff decision hierarchy or special teams coordinator
        """
        # Check for 4th down and route through new architecture
        if context.situation.down == 4:
            return self._handle_fourth_down_defensive_play(context)
        
        # Normal flow for downs 1-3: Convert PlayCallContext to the format expected by CoachingStaff
        coaching_context = self._convert_context_for_coaching_staff(context)
        
        # Use the sophisticated coaching staff system for defensive play selection
        selected_play = self.coaching_staff.select_defensive_play(coaching_context)
        
        return selected_play
    
    def _convert_context_for_coaching_staff(self, context: PlayCallContext) -> Dict[str, Any]:
        """
        Convert PlayCallContext to format expected by CoachingStaff
        
        Args:
            context: PlayCallContext from external systems
            
        Returns:
            Dictionary format expected by CoachingStaff system
        """
        situation = context.situation
        
        coaching_context = {
            'down': situation.down,
            'yards_to_go': situation.yards_to_go,
            'field_position': situation.field_position,
            'possessing_team': situation.possessing_team
        }
        
        # Add time remaining if available
        if situation.time_remaining is not None:
            coaching_context['time_remaining'] = situation.time_remaining
            
        # Add additional context fields if provided
        if context.game_flow:
            coaching_context['game_flow'] = context.game_flow
            
        if context.recent_plays:
            coaching_context['recent_plays'] = context.recent_plays
            
        if context.opponent_tendencies:
            coaching_context['opponent_tendencies'] = context.opponent_tendencies
            
        if context.weather_conditions:
            coaching_context['weather_conditions'] = context.weather_conditions
            
        return coaching_context
    
    def _update_play_history(self, play_call: Any):
        """Update recent play history for potential future sequencing analysis"""
        self.recent_calls.append(play_call)
        # Keep only last 5 plays  
        if len(self.recent_calls) > 5:
            self.recent_calls.pop(0)
    
    def _handle_fourth_down_offensive_play(self, context: PlayCallContext) -> OffensivePlayCall:
        """
        Handle fourth down offensive play selection through new clean architecture
        
        Routes decision through HeadCoach strategic decision, then to appropriate coordinator.
        
        Args:
            context: PlayCallContext for 4th down situation
            
        Returns:
            OffensivePlayCall from strategic decision flow
        """
        # Convert context for HeadCoach decision making
        coaching_context = self._convert_context_for_coaching_staff(context)
        
        # HeadCoach makes strategic decision first
        game_management_decision = self.coaching_staff.head_coach.get_game_management_decision('fourth_down', coaching_context)
        fourth_down_decision = game_management_decision['fourth_down']
        strategic_decision = fourth_down_decision['recommendation']
        
        if strategic_decision == FourthDownDecisionType.GO_FOR_IT:
            # Route to normal coordinators for regular play execution
            selected_play = self.coaching_staff.select_offensive_play(coaching_context)
            self._update_play_history(selected_play)
            return selected_play
        
        elif strategic_decision in [FourthDownDecisionType.PUNT, FourthDownDecisionType.FIELD_GOAL]:
            # Route to SpecialTeamsCoordinator for special teams execution
            if self.coaching_staff.special_teams_coordinator is None:
                # Fallback to old system if no special teams coordinator available (backwards compatibility)
                selected_play = self.coaching_staff.select_offensive_play(coaching_context)
                self._update_play_history(selected_play)
                return selected_play
            
            # Use new clean architecture with special teams coordinator
            selected_play = self.coaching_staff.special_teams_coordinator.select_offensive_special_teams_play(
                strategic_decision, coaching_context
            )
            self._update_play_history(selected_play)
            return selected_play
        
        else:
            # Fallback for unexpected decisions
            selected_play = self.coaching_staff.select_offensive_play(coaching_context)
            self._update_play_history(selected_play)
            return selected_play
    
    def _handle_fourth_down_defensive_play(self, context: PlayCallContext) -> DefensivePlayCall:
        """
        Handle fourth down defensive play selection through new clean architecture
        
        Predicts opponent decision and routes to appropriate coordinator.
        
        Args:
            context: PlayCallContext for 4th down situation
            
        Returns:
            DefensivePlayCall from strategic prediction flow
        """
        # Convert context for decision prediction
        coaching_context = self._convert_context_for_coaching_staff(context)
        
        # Predict opponent's 4th down decision (use defensive coordinator's prediction logic)
        # This could be enhanced with dedicated game theory/scouting systems in the future
        predicted_opponent_decision = self._predict_opponent_fourth_down_decision(coaching_context)
        
        if predicted_opponent_decision == FourthDownDecisionType.GO_FOR_IT:
            # Route to normal coordinators for regular defensive play
            return self.coaching_staff.select_defensive_play(coaching_context)
        
        elif predicted_opponent_decision in [FourthDownDecisionType.PUNT, FourthDownDecisionType.FIELD_GOAL]:
            # Route to SpecialTeamsCoordinator for special teams defense
            if self.coaching_staff.special_teams_coordinator is None:
                # Fallback to old system if no special teams coordinator available (backwards compatibility)
                return self.coaching_staff.select_defensive_play(coaching_context)
            
            # Use new clean architecture with special teams coordinator
            return self.coaching_staff.special_teams_coordinator.select_defensive_special_teams_play(
                predicted_opponent_decision, coaching_context
            )
        
        else:
            # Fallback for unexpected predictions
            return self.coaching_staff.select_defensive_play(coaching_context)
    
    def _predict_opponent_fourth_down_decision(self, context: Dict[str, Any]) -> FourthDownDecisionType:
        """
        Predict opponent's fourth down decision using defensive coordinator's scouting logic
        
        This delegates to the defensive coordinator's existing prediction logic.
        Could be enhanced with dedicated game theory systems in the future.
        
        Args:
            context: Game context for prediction
            
        Returns:
            Predicted FourthDownDecisionType
        """
        # Use defensive coordinator's existing opponent prediction logic
        return self.coaching_staff.defensive_coordinator._predict_opponent_fourth_down_decision(context)
    
    def get_coaching_staff_summary(self) -> Dict[str, Any]:
        """Get summary of the coaching staff philosophy and characteristics"""
        return self.coaching_staff.get_coaching_philosophy_summary()


# Convenience factory functions for creating PlayCallers with common coaching staff types
class PlayCallerFactory:
    """Factory for creating PlayCallers with common coaching staff combinations"""
    
    @staticmethod
    def create_aggressive_caller(playbook_name: str = "aggressive") -> PlayCaller:
        """Create an aggressive PlayCaller with pass-heavy coaching staff"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        aggressive_staff = staff_factory.create_aggressive_staff("Aggressive Team")
        return PlayCaller(aggressive_staff, playbook_name)
    
    @staticmethod
    def create_conservative_caller(playbook_name: str = "conservative") -> PlayCaller:
        """Create a conservative PlayCaller with run-heavy coaching staff"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        conservative_staff = staff_factory.create_conservative_staff("Conservative Team")
        return PlayCaller(conservative_staff, playbook_name)
    
    @staticmethod  
    def create_balanced_caller(playbook_name: str = "balanced") -> PlayCaller:
        """Create a balanced PlayCaller with balanced coaching staff"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        balanced_staff = staff_factory.create_balanced_staff("Balanced Team")
        return PlayCaller(balanced_staff, playbook_name)
    
    @staticmethod
    def create_chiefs_style_caller(playbook_name: str = "balanced") -> PlayCaller:
        """Create a PlayCaller with Chiefs-style coaching staff (Reid system)"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        chiefs_staff = staff_factory.create_chiefs_style_staff()
        return PlayCaller(chiefs_staff, playbook_name)
    
    @staticmethod
    def create_patriots_style_caller(playbook_name: str = "balanced") -> PlayCaller:
        """Create a PlayCaller with Patriots-style coaching staff (Belichick system)"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        patriots_staff = staff_factory.create_patriots_dynasty_staff()
        return PlayCaller(patriots_staff, playbook_name)
    
    @staticmethod
    def create_rams_style_caller(playbook_name: str = "balanced") -> PlayCaller:
        """Create a PlayCaller with Rams-style coaching staff (McVay system)"""
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        rams_staff = staff_factory.create_rams_mcvay_staff()
        return PlayCaller(rams_staff, playbook_name)
    
    @staticmethod
    def create_for_team(team_id: int, playbook_name: str = "balanced") -> PlayCaller:
        """
        Create a PlayCaller with coaching staff based on real NFL team philosophies
        
        Args:
            team_id: NFL team ID (1-32)
            playbook_name: Name of playbook to load (default: "balanced")
            
        Returns:
            PlayCaller configured with team-specific coaching staff
            
        Raises:
            ValueError: If team_id is not valid (must be 1-32)
        """
        # Validate team ID
        if not isinstance(team_id, int) or team_id < 1 or team_id > 32:
            raise ValueError(f"Invalid team_id: {team_id}. Must be an integer between 1 and 32.")
        
        # Load team coaching styles configuration
        config_path = Path(__file__).parent.parent.parent / "config" / "team_coaching_styles.json"
        
        try:
            with open(config_path, 'r') as f:
                team_styles = json.load(f)
        except FileNotFoundError:
            # Fallback to balanced coaching for all teams if config file is missing
            return PlayCallerFactory.create_balanced_caller(playbook_name)
        
        # Get coaching style for this team
        team_style = team_styles.get(str(team_id))
        if not team_style:
            # Fallback to balanced coaching if team not found in config
            return PlayCallerFactory.create_balanced_caller(playbook_name)
        
        # Extract coaching philosophies
        hc_philosophy = team_style.get("head_coach", "balanced")
        oc_philosophy = team_style.get("offensive_coordinator", "balanced") 
        dc_philosophy = team_style.get("defensive_coordinator", "balanced")
        team_name = team_style.get("team_name", f"Team {team_id}")
        
        # Create coaching staff using StaffFactory based on team philosophy combination
        from .staff_factory import StaffFactory
        staff_factory = StaffFactory()
        
        try:
            # Map team philosophy combination to existing factory methods
            philosophy_key = f"{hc_philosophy}-{oc_philosophy}-{dc_philosophy}"
            
            # Use predefined combinations when possible
            if hc_philosophy == "aggressive" and oc_philosophy == "pass_heavy" and dc_philosophy == "aggressive":
                coaching_staff = staff_factory.create_aggressive_staff(team_name)
            elif hc_philosophy == "conservative" and dc_philosophy == "conservative":
                coaching_staff = staff_factory.create_conservative_staff(team_name)
            elif philosophy_key in ["balanced-balanced-balanced", "balanced-pass_heavy-balanced"]:
                coaching_staff = staff_factory.create_balanced_staff(team_name)
            else:
                # Create custom staff for unique team combinations
                coaching_staff = staff_factory._create_team_specific_staff(
                    team_name, hc_philosophy, oc_philosophy, dc_philosophy
                )
            
            return PlayCaller(coaching_staff, playbook_name)
            
        except Exception as e:
            # If custom staff creation fails, fall back to predefined combinations
            if hc_philosophy == "aggressive" and oc_philosophy == "pass_heavy":
                return PlayCallerFactory.create_aggressive_caller(playbook_name)
            elif hc_philosophy == "conservative":
                return PlayCallerFactory.create_conservative_caller(playbook_name)
            else:
                return PlayCallerFactory.create_balanced_caller(playbook_name)


# Legacy compatibility functions for backward compatibility with old CoachArchetype system
class LegacyPlayCallerFactory:
    """Legacy factory methods for backward compatibility with old CoachArchetype system"""
    
    @staticmethod
    def create_aggressive_caller_legacy(playbook_name: str = "aggressive") -> PlayCaller:
        """Create an aggressive play caller using legacy CoachArchetype (for backward compatibility)"""
        # Convert old-style coach archetype to new CoachingStaff system
        return PlayCallerFactory.create_aggressive_caller(playbook_name)
    
    @staticmethod
    def create_conservative_caller_legacy(playbook_name: str = "conservative") -> PlayCaller:
        """Create a conservative play caller using legacy CoachArchetype (for backward compatibility)"""
        return PlayCallerFactory.create_conservative_caller(playbook_name)
    
    @staticmethod  
    def create_balanced_caller_legacy(playbook_name: str = "balanced") -> PlayCaller:
        """Create a balanced play caller using legacy CoachArchetype (for backward compatibility)"""
        return PlayCallerFactory.create_balanced_caller(playbook_name)