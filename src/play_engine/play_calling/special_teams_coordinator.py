"""
Special Teams Coordinator - Dedicated special teams play calling

The special teams coordinator is responsible for all special teams decisions:
- Punt execution and punt coverage/return
- Field goal attempts and field goal block/defense
- Clean separation from regular offensive/defensive coordinators

This matches real NFL organizational structure where special teams coordinators
handle all aspects of special teams play calling and personnel decisions.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from .coach_archetype import BaseCoachArchetype, CoachType
from .fourth_down_matrix import FourthDownDecisionType
from ..play_calls.offensive_play_call import OffensivePlayCall
from ..play_calls.defensive_play_call import DefensivePlayCall
from ..play_types.offensive_types import OffensivePlayType
from ..play_types.defensive_types import DefensivePlayType
from ..mechanics.unified_formations import UnifiedOffensiveFormation, UnifiedDefensiveFormation, SimulatorContext
from ..mechanics.formations import OffensiveFormation


class SpecialTeamsPhilosophy(Enum):
    """Special teams coordinator philosophical approaches"""
    AGGRESSIVE = "aggressive"      # Go for blocks, aggressive returns
    CONSERVATIVE = "conservative"  # Prioritize coverage, safe returns  
    BALANCED = "balanced"         # Mix of aggression and safety


@dataclass
class SpecialTeamsTraits:
    """Special teams coordinator specific traits"""
    # Punt philosophy (0.0-1.0)
    punt_block_aggression: float = 0.4          # How often to rush the punter
    punt_return_aggression: float = 0.6         # Aggressive returns vs safe catches
    punt_fake_detection: float = 0.7            # Ability to detect fake punts
    
    # Field goal philosophy (0.0-1.0)  
    field_goal_block_aggression: float = 0.5    # How often to rush field goals
    field_goal_fake_detection: float = 0.8      # Ability to detect fake field goals
    field_goal_return_preparedness: float = 0.6 # Preparation for missed FG returns
    
    # Coverage philosophy (0.0-1.0)
    coverage_discipline: float = 0.7             # Maintain lanes vs pursuit
    special_teams_personnel_trust: float = 0.6   # Trust in ST units vs starters


@dataclass
class SpecialTeamsCoordinator(BaseCoachArchetype):
    """
    Special teams coordinator focused exclusively on special teams decisions
    
    Handles all punt and field goal situations (both offensive and defensive sides)
    with clean separation from regular offensive/defensive coordinators.
    """
    
    # Specialized traits for special teams coordinators
    philosophy: SpecialTeamsPhilosophy = SpecialTeamsPhilosophy.BALANCED
    special_teams_traits: SpecialTeamsTraits = field(default_factory=SpecialTeamsTraits)
    
    def __post_init__(self):
        """Initialize special teams coordinator with proper type"""
        self.coach_type = CoachType.SPECIAL_TEAMS_COORDINATOR
        super().__post_init__()
    
    def select_offensive_special_teams_play(self, decision_type: FourthDownDecisionType, context: Dict[str, Any]) -> OffensivePlayCall:
        """
        Select offensive special teams play based on head coach's strategic decision
        
        Args:
            decision_type: Head coach's strategic decision (PUNT or FIELD_GOAL)
            context: Game context for situational adjustments
        
        Returns:
            OffensivePlayCall for special teams execution
        """
        if decision_type == FourthDownDecisionType.PUNT:
            return self._select_punt_play(context)
        elif decision_type == FourthDownDecisionType.FIELD_GOAL:
            return self._select_field_goal_play(context)
        else:
            raise ValueError(f"SpecialTeamsCoordinator cannot handle decision type: {decision_type}")
    
    def select_defensive_special_teams_play(self, opponent_decision: FourthDownDecisionType, context: Dict[str, Any]) -> DefensivePlayCall:
        """
        Select defensive special teams play based on predicted opponent decision
        
        Args:
            opponent_decision: Predicted opponent special teams decision
            context: Game context for situational adjustments
        
        Returns:
            DefensivePlayCall for special teams defense
        """
        if opponent_decision == FourthDownDecisionType.PUNT:
            return self._select_punt_defense(context)
        elif opponent_decision == FourthDownDecisionType.FIELD_GOAL:
            return self._select_field_goal_defense(context)
        else:
            raise ValueError(f"SpecialTeamsCoordinator cannot handle opponent decision: {opponent_decision}")
    
    def _select_punt_play(self, context: Dict[str, Any]) -> OffensivePlayCall:
        """Select punt execution strategy"""
        # Determine punt strategy based on field position and game situation
        field_position = context.get('field_position', 50)
        time_remaining = context.get('time_remaining', 900)
        score_differential = context.get('score_differential', 0)
        
        # Punt strategy selection
        if field_position <= 40:  # Deep in own territory
            concept = "directional_punt"  # Punt away from returner
        elif field_position >= 65:  # In opponent territory  
            concept = "coffin_corner_punt"  # Pin them deep
        else:
            concept = "standard_punt"  # Regular punt
        
        # Consider fake punt based on coordinator aggression and situation
        fake_punt_consideration = self._should_consider_fake_punt(context)
        if fake_punt_consideration:
            concept = "fake_punt_run"  # Could expand with more fake options
        
        return OffensivePlayCall(
            play_type=OffensivePlayType.PUNT,
            formation=OffensiveFormation.PUNT,
            concept=concept,
            personnel_package="punt_team"
        )
    
    def _select_field_goal_play(self, context: Dict[str, Any]) -> OffensivePlayCall:
        """Select field goal attempt strategy"""
        field_position = context.get('field_position', 50)
        yards_to_go = context.get('yards_to_go', 10)
        
        # Determine field goal type based on distance and situation
        fg_distance = 100 - field_position + 17  # Add 17 for end zone + holder depth
        
        if fg_distance > 50:
            concept = "long_field_goal"
        elif fg_distance < 30:
            concept = "chip_shot_field_goal" 
        else:
            concept = "standard_field_goal"
        
        # Consider fake field goal in short yardage situations
        fake_fg_consideration = self._should_consider_fake_field_goal(context)
        if fake_fg_consideration:
            concept = "fake_field_goal_run"  # Could expand with pass options
        
        return OffensivePlayCall(
            play_type=OffensivePlayType.FIELD_GOAL,
            formation=OffensiveFormation.FIELD_GOAL,
            concept=concept,
            personnel_package="field_goal_team"
        )
    
    def _select_punt_defense(self, context: Dict[str, Any]) -> DefensivePlayCall:
        """Select punt return/coverage strategy"""
        # Determine punt return strategy
        punt_block_decision = self._should_rush_punt(context)
        
        if punt_block_decision:
            # Aggressive punt block attempt
            formation = UnifiedDefensiveFormation.PUNT_BLOCK.for_context(SimulatorContext.COORDINATOR)
            coverage = "punt_block_rush"
            play_type = DefensivePlayType.PUNT_BLOCK
        else:
            # Standard punt return formation
            formation = UnifiedDefensiveFormation.PUNT_RETURN.for_context(SimulatorContext.COORDINATOR)
            
            # Determine return strategy
            return_aggression = self.special_teams_traits.punt_return_aggression
            if return_aggression > 0.7:
                coverage = "aggressive_punt_return"
                play_type = DefensivePlayType.PUNT_RETURN
            else:
                coverage = "safe_punt_return"
                play_type = DefensivePlayType.PUNT_RETURN
        
        return DefensivePlayCall(
            play_type=play_type,
            formation=formation,
            coverage=coverage,
            blitz_package="punt_rush" if punt_block_decision else None
        )
    
    def _select_field_goal_defense(self, context: Dict[str, Any]) -> DefensivePlayCall:
        """Select field goal block/defense strategy"""
        # Determine field goal defense strategy
        block_decision = self._should_rush_field_goal(context)
        fake_preparation = self.special_teams_traits.field_goal_fake_detection
        
        if block_decision:
            # Aggressive field goal block attempt
            formation = UnifiedDefensiveFormation.FIELD_GOAL_BLOCK.for_context(SimulatorContext.COORDINATOR)
            coverage = "field_goal_block_rush"
            play_type = DefensivePlayType.PUNT_BLOCK  # Use compatible block tactics
        elif fake_preparation > 0.7:
            # Prepare for fake field goal with mixed coverage
            formation = UnifiedDefensiveFormation.PUNT_RETURN.for_context(SimulatorContext.COORDINATOR)
            coverage = "fake_field_goal_defense"
            play_type = DefensivePlayType.PUNT_RETURN  # Use compatible punt return tactics
        else:
            # Conservative field goal defense (prepare for miss return)
            formation = UnifiedDefensiveFormation.PUNT_SAFE.for_context(SimulatorContext.COORDINATOR)
            coverage = "field_goal_return_coverage"
            play_type = DefensivePlayType.PUNT_SAFE  # Use compatible safe punt tactics
        
        return DefensivePlayCall(
            play_type=play_type,
            formation=formation,
            coverage=coverage,
            blitz_package="field_goal_rush" if block_decision else None
        )
    
    def _should_rush_punt(self, context: Dict[str, Any]) -> bool:
        """Determine if special teams should rush the punt"""
        base_aggression = self.special_teams_traits.punt_block_aggression
        
        # Adjust based on game situation
        score_differential = context.get('score_differential', 0)
        time_remaining = context.get('time_remaining', 900)
        field_position = context.get('field_position', 50)
        
        # More aggressive when behind late in game
        if score_differential > 7 and time_remaining < 300:  # Down by 7+ with 5 min left
            base_aggression *= 1.5
        
        # More aggressive when opponent is backed up (better field position if successful)
        if field_position >= 80:  # Opponent deep in their territory
            base_aggression *= 1.2
        
        # Factor in coordinator's overall aggression
        effective_aggression = base_aggression * (0.5 + self.aggression * 0.5)
        
        return effective_aggression > 0.6
    
    def _should_rush_field_goal(self, context: Dict[str, Any]) -> bool:
        """Determine if special teams should rush the field goal"""
        base_aggression = self.special_teams_traits.field_goal_block_aggression
        
        # Calculate field goal distance
        field_position = context.get('field_position', 50)
        fg_distance = 100 - field_position + 17
        
        # More aggressive on longer field goals (higher miss probability)
        if fg_distance > 45:
            base_aggression *= 1.3
        elif fg_distance < 30:
            base_aggression *= 0.7  # Less rushing on chip shots
        
        # Game situation adjustments
        score_differential = context.get('score_differential', 0)
        time_remaining = context.get('time_remaining', 900)
        
        # More aggressive when the field goal would significantly impact game
        if abs(score_differential) <= 3 and time_remaining < 300:  # Close game, late
            base_aggression *= 1.4
        
        # Factor in coordinator's overall aggression  
        effective_aggression = base_aggression * (0.5 + self.aggression * 0.5)
        
        return effective_aggression > 0.5
    
    def _should_consider_fake_punt(self, context: Dict[str, Any]) -> bool:
        """Determine if offense should consider fake punt"""
        # Very conservative fake punt logic - special teams coordinators rarely call fakes
        base_fake_rate = 0.05  # 5% base fake rate
        
        yards_to_go = context.get('yards_to_go', 10)
        field_position = context.get('field_position', 50)
        score_differential = context.get('score_differential', 0)
        time_remaining = context.get('time_remaining', 900)
        
        # More likely on short yardage
        if yards_to_go <= 3:
            base_fake_rate *= 2.0
        
        # More likely when desperate (behind late)
        if score_differential > 14 and time_remaining < 600:  # Down by 14+ in final 10 min
            base_fake_rate *= 3.0
        
        # Factor in coordinator risk tolerance
        effective_fake_rate = base_fake_rate * self.risk_tolerance
        
        return effective_fake_rate > 0.1 and self.aggression > 0.7  # Requires high aggression
    
    def _should_consider_fake_field_goal(self, context: Dict[str, Any]) -> bool:
        """Determine if offense should consider fake field goal"""
        # Even more conservative than fake punts
        base_fake_rate = 0.02  # 2% base fake rate
        
        yards_to_go = context.get('yards_to_go', 10)
        field_position = context.get('field_position', 50)
        
        # Only consider on very short yardage near goal line
        if yards_to_go <= 2 and field_position >= 85:  # 2 yards or less, very close to goal
            base_fake_rate *= 4.0
        
        # Factor in coordinator risk tolerance and aggression
        effective_fake_rate = base_fake_rate * self.risk_tolerance * self.aggression
        
        return effective_fake_rate > 0.08  # Very high threshold
    
    def get_personnel_package(self, play_type: str, situation: str) -> str:
        """
        Select personnel package for special teams plays
        
        Args:
            play_type: Type of special teams play
            situation: Game situation context
        
        Returns:
            Personnel package description
        """
        if play_type == "punt":
            return "Punt Team (1 punter, 2 gunners, 8 blockers/coverage)"
        elif play_type == "field_goal":
            return "Field Goal Team (1 kicker, 1 holder, 1 long snapper, 8 blockers)"
        else:
            return "Standard Special Teams Unit"
    
    def evaluate_head_coach_influence(self, hc_influence: float, situation: str) -> float:
        """
        Evaluate how head coach influence affects special teams calling
        
        Args:
            hc_influence: Head coach influence level (0.0-1.0)
            situation: Current situation
        
        Returns:
            Adjusted influence factor for special teams coordinator
        """
        # Special teams coordinators typically have moderate autonomy
        # Head coaches usually make the strategic decision (punt vs FG vs go for it)
        # but ST coordinator handles the execution details
        
        base_acceptance = 0.7  # More collaborative than defensive coordinators
        
        # In critical special teams situations, defer more to head coach
        critical_st_situations = ['long_field_goal', 'fake_consideration', 'block_decision']
        if situation in critical_st_situations:
            base_acceptance *= 1.3
        
        # Factor in coordinator's adaptability
        acceptance = base_acceptance * self.adaptability
        
        return hc_influence * acceptance
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert special teams coordinator to dictionary for JSON serialization"""
        base_dict = super().to_dict()
        
        # Add special teams coordinator specific data
        base_dict['coach_type'] = self.coach_type.value
        base_dict['philosophy'] = self.philosophy.value
        base_dict['special_teams_traits'] = {
            'punt_block_aggression': self.special_teams_traits.punt_block_aggression,
            'punt_return_aggression': self.special_teams_traits.punt_return_aggression,
            'punt_fake_detection': self.special_teams_traits.punt_fake_detection,
            'field_goal_block_aggression': self.special_teams_traits.field_goal_block_aggression,
            'field_goal_fake_detection': self.special_teams_traits.field_goal_fake_detection,
            'field_goal_return_preparedness': self.special_teams_traits.field_goal_return_preparedness,
            'coverage_discipline': self.special_teams_traits.coverage_discipline,
            'special_teams_personnel_trust': self.special_teams_traits.special_teams_personnel_trust,
        }
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpecialTeamsCoordinator':
        """Create SpecialTeamsCoordinator from dictionary (JSON loading)"""
        # Extract specialized data
        philosophy_str = data.get('philosophy', 'balanced')
        philosophy = SpecialTeamsPhilosophy(philosophy_str)
        
        st_traits_data = data.get('special_teams_traits', {})
        st_traits = SpecialTeamsTraits(**st_traits_data)
        
        # Use base class method for common traits
        base_coach = BaseCoachArchetype.from_dict(data)
        
        # Create special teams coordinator with specialized traits
        return cls(
            name=base_coach.name,
            description=base_coach.description,
            coach_type=CoachType.SPECIAL_TEAMS_COORDINATOR,
            aggression=base_coach.aggression,
            risk_tolerance=base_coach.risk_tolerance,
            adaptability=base_coach.adaptability,
            conservatism=base_coach.conservatism,
            run_preference=base_coach.run_preference,
            fourth_down_aggression=base_coach.fourth_down_aggression,
            red_zone_aggression=base_coach.red_zone_aggression,
            game_script_adherence=base_coach.game_script_adherence,
            momentum_responsiveness=base_coach.momentum_responsiveness,
            pressure_handling=base_coach.pressure_handling,
            situational=base_coach.situational,
            formations=base_coach.formations,
            play_types=base_coach.play_types,
            philosophy=philosophy,
            special_teams_traits=st_traits,
        )


def create_aggressive_special_teams_coordinator(team_name: str = "Team") -> SpecialTeamsCoordinator:
    """Create an aggressive special teams coordinator"""
    return SpecialTeamsCoordinator(
        name=f"{team_name} Special Teams Coordinator",
        description="Aggressive special teams coordinator who goes for blocks and big returns",
        aggression=0.8,
        risk_tolerance=0.7,
        conservatism=0.3,
        philosophy=SpecialTeamsPhilosophy.AGGRESSIVE,
        special_teams_traits=SpecialTeamsTraits(
            punt_block_aggression=0.7,
            punt_return_aggression=0.8,
            field_goal_block_aggression=0.7,
            coverage_discipline=0.6  # Less disciplined, more pursuit-oriented
        )
    )


def create_conservative_special_teams_coordinator(team_name: str = "Team") -> SpecialTeamsCoordinator:
    """Create a conservative special teams coordinator"""
    return SpecialTeamsCoordinator(
        name=f"{team_name} Special Teams Coordinator",
        description="Conservative special teams coordinator who prioritizes coverage and field position",
        aggression=0.3,
        risk_tolerance=0.3,
        conservatism=0.7,
        philosophy=SpecialTeamsPhilosophy.CONSERVATIVE,
        special_teams_traits=SpecialTeamsTraits(
            punt_block_aggression=0.2,
            punt_return_aggression=0.3,
            field_goal_block_aggression=0.3,
            coverage_discipline=0.9  # Very disciplined coverage
        )
    )


def create_balanced_special_teams_coordinator(team_name: str = "Team") -> SpecialTeamsCoordinator:
    """Create a balanced special teams coordinator"""
    return SpecialTeamsCoordinator(
        name=f"{team_name} Special Teams Coordinator",
        description="Balanced special teams coordinator with situational approach",
        aggression=0.5,
        risk_tolerance=0.5,
        conservatism=0.5,
        philosophy=SpecialTeamsPhilosophy.BALANCED,
        special_teams_traits=SpecialTeamsTraits()  # Use default balanced values
    )