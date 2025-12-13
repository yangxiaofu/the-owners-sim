"""
Coaching Staff - Orchestrates Head Coach, Offensive Coordinator, and Defensive Coordinator

This class manages the interaction between different coach types and implements
the decision hierarchy where head coaches can override coordinators in critical situations.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import random
from .head_coach import HeadCoach
from .offensive_coordinator import OffensiveCoordinator  
from .defensive_coordinator import DefensiveCoordinator
from .special_teams_coordinator import SpecialTeamsCoordinator
from ..play_calls.offensive_play_call import OffensivePlayCall
from ..play_calls.defensive_play_call import DefensivePlayCall
from ..mechanics.formations import DefensiveFormation, OffensiveFormation
from ..play_types.offensive_types import OffensivePlayType
from ..mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext
from ..play_types.defensive_types import DefensivePlayType


@dataclass
class CoachingStaff:
    """
    Complete coaching staff with head coach and coordinators
    
    Manages the decision-making hierarchy where the head coach sets overall
    strategy and can override coordinators, while coordinators handle
    day-to-day play calling within their specializations.
    
    New architecture includes SpecialTeamsCoordinator for clean separation
    of special teams decisions from regular offensive/defensive play calling.
    """
    
    head_coach: HeadCoach
    offensive_coordinator: OffensiveCoordinator
    defensive_coordinator: DefensiveCoordinator
    special_teams_coordinator: Optional[SpecialTeamsCoordinator] = None
    
    def __post_init__(self):
        """Validate coaching staff composition"""
        if not isinstance(self.head_coach, HeadCoach):
            raise ValueError("head_coach must be a HeadCoach instance")
        if not isinstance(self.offensive_coordinator, OffensiveCoordinator):
            raise ValueError("offensive_coordinator must be an OffensiveCoordinator instance")
        if not isinstance(self.defensive_coordinator, DefensiveCoordinator):
            raise ValueError("defensive_coordinator must be a DefensiveCoordinator instance")
        if self.special_teams_coordinator is not None and not isinstance(self.special_teams_coordinator, SpecialTeamsCoordinator):
            raise ValueError("special_teams_coordinator must be a SpecialTeamsCoordinator instance or None")
    
    def _weighted_random_choice(self, weighted_dict: Dict[str, float]) -> str:
        """
        Weighted random selection from dictionary of choices and weights
        
        Args:
            weighted_dict: Dictionary with choices as keys and weights as values
            
        Returns:
            Randomly selected choice based on weights
            
        Raises:
            ValueError: If dictionary is empty or all weights are <= 0
        """
        if not weighted_dict:
            raise ValueError("Empty weighted dictionary provided to _weighted_random_choice")
        
        total_weight = sum(weighted_dict.values())
        if total_weight <= 0:
            raise ValueError(f"Total weight {total_weight} must be > 0. Weights: {weighted_dict}")
        
        # Generate random value between 0 and total_weight
        rand_value = random.uniform(0, total_weight)
        current_weight = 0
        
        # Select based on cumulative weights
        for choice, weight in weighted_dict.items():
            current_weight += weight
            if rand_value <= current_weight:
                return choice
        
        # Fallback to last choice (handles floating point precision issues)
        return list(weighted_dict.keys())[-1]
    
    def select_offensive_play(self, context: Dict[str, Any]) -> OffensivePlayCall:
        """
        Select offensive play through coaching staff hierarchy

        Args:
            context: Play calling context with situation, game state, etc.

        Returns:
            Selected offensive play call
        """
        situation = self._extract_situation(context)

        # Check for spike play first (two-minute drill clock management)
        spike_context = self._build_spike_context(context, situation)
        if self.offensive_coordinator.should_spike(spike_context):
            return OffensivePlayCall(
                play_type=OffensivePlayType.SPIKE,
                formation=OffensiveFormation.SHOTGUN,
                concept='spike'
            )

        # Check if head coach wants to override
        if self.head_coach.should_override_coordinator(situation, context):
            return self._head_coach_offensive_override(context, situation)
        
        # Delegate to offensive coordinator with head coach influence
        hc_influence = self.head_coach.get_override_influence('offensive')
        return self._offensive_coordinator_play_call(context, situation, hc_influence)
    
    def select_defensive_play(self, context: Dict[str, Any]) -> DefensivePlayCall:
        """
        Select defensive play through coaching staff hierarchy
        
        Args:
            context: Play calling context with situation, offensive formation, etc.
        
        Returns:
            Selected defensive play call
        """
        situation = self._extract_situation(context)
        
        # Check if head coach wants to override
        if self.head_coach.should_override_coordinator(situation, context):
            return self._head_coach_defensive_override(context, situation)
        
        # Delegate to defensive coordinator with head coach influence
        hc_influence = self.head_coach.get_override_influence('defensive')
        return self._defensive_coordinator_play_call(context, situation, hc_influence)
    
    def _extract_situation(self, context: Dict[str, Any]) -> str:
        """
        Extract primary situation type from context with granular down/distance detail.

        NEW: Enhanced to provide situation-specific pass rates for realistic
        down/distance strategy (e.g., second_and_short vs second_and_long).

        Args:
            context: Play calling context

        Returns:
            Granular situation string for decision making
        """
        field_position = context.get('field_position', 50)
        down = context.get('down', 1)
        yards_to_go = context.get('yards_to_go', 10)
        time_remaining = context.get('time_remaining', 1800)

        # Priority 1: Goal line (1-3 yards to goal)
        if field_position >= 97:
            return 'goal_line'

        # Priority 2: Red zone (inside 20)
        if field_position >= 80:
            return 'red_zone'

        # Priority 3: Two-minute drill (final 2 minutes of half)
        quarter = context.get('quarter', 1)
        if quarter in [2, 4] and time_remaining <= 120:
            return 'two_minute'

        # Priority 4: Down/distance situations (granular)

        # Fourth down (special teams/desperation)
        if down == 4:
            return 'fourth_down'

        # First down (balanced)
        if down == 1:
            return 'first_down'

        # Second down with distance breakdown
        if down == 2:
            if yards_to_go <= 4:
                return 'second_and_short'  # 2nd & 2-4 (run-leaning)
            elif yards_to_go <= 7:
                return 'second_and_medium'  # 2nd & 5-7 (balanced)
            else:
                return 'second_and_long'  # 2nd & 8+ (pass-heavy)

        # Third down with distance breakdown
        if down == 3:
            if yards_to_go <= 3:
                return 'third_and_short'  # 3rd & 1-3 (run-heavy)
            elif yards_to_go <= 7:
                return 'third_and_medium'  # 3rd & 4-7 (pass-favored)
            else:
                return 'third_and_long'  # 3rd & 8+ (pass-dominant)

        # Default fallback (should not happen)
        return 'normal'

    def _build_spike_context(self, context: Dict[str, Any], situation: str) -> Dict[str, Any]:
        """
        Build context dict for should_spike() check.

        Extracts required fields from PlayCallContext to match should_spike() signature:
        - time_remaining, quarter, score_differential, down, clock_running, timeouts_remaining

        Args:
            context: PlayCallContext (may be dict or dataclass)
            situation: Extracted situation string

        Returns:
            Dict with fields for should_spike() evaluation
        """
        # Handle both dict and PlayCallContext objects
        if hasattr(context, 'raw_game_state'):
            raw_state = context.raw_game_state or {}
            sit = context.situation if hasattr(context, 'situation') else None
        else:
            raw_state = context.get('raw_game_state', {}) if isinstance(context, dict) else {}
            sit = None

        # Extract game state
        quarter = raw_state.get('quarter', 1)
        time_remaining = raw_state.get('time_remaining', 900)
        home_score = raw_state.get('home_score', 0)
        away_score = raw_state.get('away_score', 0)
        possessing_team_id = raw_state.get('possessing_team_id')
        home_team_id = raw_state.get('home_team_id')

        # Calculate score differential from offense perspective
        if possessing_team_id and home_team_id:
            if possessing_team_id == home_team_id:
                score_differential = home_score - away_score
            else:
                score_differential = away_score - home_score
        else:
            score_differential = 0

        # Get down from situation or raw_state
        down = raw_state.get('down', 1)
        if sit and hasattr(sit, 'down'):
            down = sit.down

        return {
            'time_remaining': time_remaining,
            'quarter': quarter,
            'score_differential': score_differential,
            'down': down,
            'clock_running': True,  # Assume clock running (spike is a clock-stopping play)
            'timeouts_remaining': raw_state.get('timeouts_remaining', 3)
        }

    def _head_coach_offensive_override(self, context: Dict[str, Any], situation: str) -> OffensivePlayCall:
        """
        Head coach makes offensive play call decision
        
        Args:
            context: Play calling context
            situation: Identified situation
        
        Returns:
            Head coach's offensive play call
        """
        # Head coach uses their own decision-making but considers OC input
        hc_decision = self.head_coach.get_game_management_decision(situation, context)
        
        # Get OC's preferred approach for reference
        oc_formation_prefs = self.offensive_coordinator.get_formation_preference(situation, context)
        oc_concepts = self.offensive_coordinator.get_play_concept_preference(situation, context)
        
        # Head coach modifies based on their philosophy
        if situation == 'fourth_down':
            decision = hc_decision.get('fourth_down', {})
            if decision.get('recommendation') == 'go_for_it':
                # Aggressive head coach going for it - use OC's best conversion concepts
                formation = self._select_formation(oc_formation_prefs, bias_aggressive=True)
                concept = self._select_concept(oc_concepts, situation_filter='conversion')
            else:
                # Punting or field goal attempt
                formation = 'punt' if context.get('field_position', 50) < 60 else 'field_goal'
                concept = 'standard_punt' if formation == 'punt' else 'standard_kick'
        
        elif situation == 'two_minute':
            # Head coach clock management philosophy
            decision = hc_decision.get('two_minute', {})
            clock_strategy = decision.get('clock_management', 'stop_clock')
            
            if clock_strategy == 'stop_clock':
                formation = 'shotgun'  # Quick passes
                concept = self._select_concept(oc_concepts, situation_filter='quick_passing')
            else:
                formation = 'i_formation'  # Run to control clock  
                concept = 'power'
        
        else:
            # Use OC preferences but with head coach bias
            formation = self._select_formation(oc_formation_prefs, 
                                             bias_aggressive=self.head_coach.aggression > 0.6)
            concept = self._select_concept(oc_concepts)
        
        # Create play call with head coach override authority
        return OffensivePlayCall(
            play_type=self._concept_to_play_type(concept),
            formation=formation,
            concept=concept,
            personnel_package=self.offensive_coordinator.get_personnel_package(formation, situation)
        )
    
    def _head_coach_defensive_override(self, context: Dict[str, Any], situation: str) -> DefensivePlayCall:
        """
        Head coach makes defensive play call decision
        
        Args:
            context: Play calling context
            situation: Identified situation
        
        Returns:
            Head coach's defensive play call
        """
        # Get DC's recommended approach
        offensive_formation = context.get('offensive_formation', 'SHOTGUN')
        dc_formation = self.defensive_coordinator.get_defensive_formation(offensive_formation, situation, context)
        dc_coverage = self.defensive_coordinator.get_coverage_scheme(dc_formation, situation, context)
        
        # Head coach adjustments based on game management
        if situation == 'fourth_down':
            # All-out pressure to stop conversion
            formation = dc_formation
            coverage = 'Man-Free'  # Tight coverage
            send_pressure = True
            
        elif situation == 'two_minute' and context.get('score_differential', 0) > 0:
            # Protect the lead - prevent big plays
            formation = DefensiveFormation.DIME if self.defensive_coordinator.personnel.dime_package_usage > 0.5 else DefensiveFormation.NICKEL
            coverage = 'Prevent'
            send_pressure = False
            
        else:
            # Use DC recommendations with head coach influence
            formation = dc_formation
            coverage = dc_coverage['primary_coverage']
            send_pressure = dc_coverage['send_pressure']
            
            # Adjust pressure based on head coach aggression
            if self.head_coach.aggression > 0.7:
                send_pressure = True
            elif self.head_coach.conservatism > 0.7:
                send_pressure = False
        
        # Determine play type based on coverage and pressure
        if send_pressure:
            play_type = 'defensive_blitz'
        elif 'Cover-2' in coverage:
            play_type = 'defensive_cover_2'
        elif 'Cover-3' in coverage:
            play_type = 'defensive_cover_3'
        elif 'Man' in coverage:
            play_type = 'defensive_man_coverage'
        else:
            play_type = 'defensive_zone_coverage'
        
        # Convert enum to appropriate string for DefensivePlayCall (same fix as coordinator method)
        formation_name = formation.for_context(SimulatorContext.COORDINATOR)
            
        return DefensivePlayCall(
            play_type=play_type,
            formation=formation_name,
            coverage=coverage,
            blitz_package='pressure' if send_pressure else None
        )
    
    def _offensive_coordinator_play_call(self, context: Dict[str, Any], situation: str, 
                                       hc_influence: float) -> OffensivePlayCall:
        """
        Offensive coordinator makes play call with head coach influence
        
        Args:
            context: Play calling context
            situation: Identified situation  
            hc_influence: Head coach influence level (0.0-1.0)
        
        Returns:
            Offensive coordinator's play call
        """
        # NEW: Analyze game context if raw state available
        raw_context = context.get('raw_game_state', {})
        if raw_context:
            from .game_situation_analyzer import GameSituationAnalyzer
            game_context = GameSituationAnalyzer.analyze_game_context(raw_context)
            # Add to context for OC methods
            context['game_context'] = game_context

        # Get OC's natural preferences
        formation_prefs = self.offensive_coordinator.get_formation_preference(situation, context)
        concept_prefs = self.offensive_coordinator.get_play_concept_preference(situation, context)
        
        # Apply head coach influence
        effective_influence = self.offensive_coordinator.evaluate_head_coach_influence(hc_influence, situation)
        
        if effective_influence > 0.3:
            # Significant head coach influence - adjust for HC's style
            hc_aggression = self.head_coach.aggression
            
            if hc_aggression > 0.6:
                # Aggressive HC pushes for more aggressive concepts
                for concept in concept_prefs:
                    if concept in ['fade', 'deep_routes', 'four_verticals']:
                        concept_prefs[concept] *= (1.0 + effective_influence * 0.5)
            else:
                # Conservative HC prefers safer concepts
                for concept in concept_prefs:
                    if concept in ['power', 'slants', 'check_down']:
                        concept_prefs[concept] *= (1.0 + effective_influence * 0.5)
        
        # Select formation and concept
        formation = self._select_formation(formation_prefs)
        concept = self._select_concept(concept_prefs)
        
        return OffensivePlayCall(
            play_type=self._concept_to_play_type(concept),
            formation=formation,
            concept=concept,
            personnel_package=self.offensive_coordinator.get_personnel_package(formation, situation)
        )
    
    def _defensive_coordinator_play_call(self, context: Dict[str, Any], situation: str,
                                       hc_influence: float) -> DefensivePlayCall:
        """
        Defensive coordinator makes play call with head coach influence
        
        Args:
            context: Play calling context
            situation: Identified situation
            hc_influence: Head coach influence level (0.0-1.0)
        
        Returns:
            Defensive coordinator's play call
        """
        # NEW: Analyze game context if raw state available
        raw_context = context.get('raw_game_state', {})
        if raw_context:
            from .game_situation_analyzer import GameSituationAnalyzer
            game_context = GameSituationAnalyzer.analyze_game_context(raw_context)
            # Add to context for DC methods
            context['game_context'] = game_context

        offensive_formation = context.get('offensive_formation', 'SHOTGUN')
        
        # Get DC's natural approach
        formation = self.defensive_coordinator.get_defensive_formation(offensive_formation, situation, context)
        coverage_info = self.defensive_coordinator.get_coverage_scheme(formation, situation, context)
        
        # Apply head coach influence
        effective_influence = self.defensive_coordinator.evaluate_head_coach_influence(hc_influence, situation)
        
        if effective_influence > 0.3:
            hc_aggression = self.head_coach.aggression
            
            if hc_aggression > 0.6:
                # Aggressive HC wants more pressure
                coverage_info['send_pressure'] = True
            elif self.head_coach.conservatism > 0.6:
                # Conservative HC wants safer coverage
                coverage_info['send_pressure'] = False
                if 'Man' in coverage_info['primary_coverage']:
                    coverage_info['primary_coverage'] = 'Cover-2'  # Safer zone coverage
        
        # Determine play type based on coverage and pressure
        coverage = coverage_info['primary_coverage'] 
        send_pressure = coverage_info['send_pressure']
        
        # Enhanced enum-based play type selection using unified formations
        if formation == UnifiedDefensiveFormation.PUNT_RETURN:
            # Determine if this is punt return or punt block based on pressure
            if send_pressure:
                play_type = DefensivePlayType.PUNT_BLOCK
            else:
                play_type = DefensivePlayType.PUNT_RETURN
        elif formation == UnifiedDefensiveFormation.FIELD_GOAL_BLOCK:
            play_type = DefensivePlayType.GOAL_LINE_DEFENSE
        elif send_pressure:
            play_type = DefensivePlayType.BLITZ
        elif 'Cover-2' in coverage:
            play_type = DefensivePlayType.COVER_2
        elif 'Cover-3' in coverage:
            play_type = DefensivePlayType.COVER_3
        elif 'Man' in coverage:
            play_type = DefensivePlayType.MAN_COVERAGE
        else:
            play_type = DefensivePlayType.ZONE_COVERAGE
        
        # Convert enum to appropriate string for DefensivePlayCall
        # Use coordinator context since DefensivePlayCall is created by coaching system
        formation_name = formation.for_context(SimulatorContext.COORDINATOR)
            
        return DefensivePlayCall(
            play_type=play_type,
            formation=formation_name,
            coverage=coverage,
            blitz_package='pressure' if send_pressure else None
        )
    
    def _select_formation(self, formation_prefs: Dict[str, float], bias_aggressive: bool = False) -> str:
        """Select formation from weighted preferences using weighted random selection"""
        if not formation_prefs:
            raise ValueError(f"No formation preferences provided, bias_aggressive: {bias_aggressive}")
        
        # Apply aggressive bias if requested
        if bias_aggressive:
            # Bias toward more aggressive formations
            for formation in formation_prefs:
                if formation in ['shotgun', 'four_wide']:
                    formation_prefs[formation] *= 1.3
        
        return self._weighted_random_choice(formation_prefs)
    
    def _select_concept(self, concept_prefs: Dict[str, float], situation_filter: str = None) -> str:
        """Select concept from weighted preferences with optional filtering using weighted random selection"""
        if not concept_prefs:
            raise ValueError(f"No concept preferences provided for situation_filter: {situation_filter}")
        
        # Apply situation filtering if requested
        if situation_filter == 'conversion':
            # Filter to high-percentage conversion concepts
            conversion_concepts = ['power', 'slants', 'quick_out', 'fade']
            filtered_prefs = {k: v for k, v in concept_prefs.items() if k in conversion_concepts}
            if not filtered_prefs:
                raise ValueError(f"No conversion concepts found in preferences: {list(concept_prefs.keys())}")
            concept_prefs = filtered_prefs
                
        elif situation_filter == 'quick_passing':
            # Filter to quick passing concepts
            quick_concepts = ['slants', 'quick_out', 'quick_slant', 'check_down']
            filtered_prefs = {k: v for k, v in concept_prefs.items() if k in quick_concepts}
            if not filtered_prefs:
                raise ValueError(f"No quick passing concepts found in preferences: {list(concept_prefs.keys())}")
            concept_prefs = filtered_prefs
            
        return self._weighted_random_choice(concept_prefs)
    
    def _concept_to_play_type(self, concept: str) -> str:
        """Convert concept to play type using proper enum constants"""
        from ..play_types.offensive_types import OffensivePlayType

        # Comprehensive run concept list - any ground-based play
        run_concepts = [
            'power', 'sweep', 'off_tackle', 'draw', 'dive', 'sneak',
            'inside_zone', 'outside_zone', 'counter', 'trap', 'iso',
            'toss', 'pitch', 'option', 'qb_sneak', 'goal_line_power',
            'stretch', 'blast', 'lead', 'cutback'
        ]
        # Pass concepts - any throw-based play
        pass_concepts = [
            'slants', 'fade', 'deep_routes', 'quick_out', 'comeback',
            'four_verticals', 'crossing_routes', 'intermediate_routes',
            'sideline_routes', 'quick_slant', 'deep_comeback', 'out_routes',
            'play_action_short', 'play_action_deep', 'play_action_intermediate',
            'play_action_rollout', 'screen', 'check_down', 'short_routes',
            'deep_out', 'pick_play', 'smash', 'tight_end_out', 'slant'
        ]
        special_concepts = ['standard_punt', 'standard_kick', 'spike']

        # Handle the "standard" concept that many coordinators default to
        if concept == 'standard':
            return OffensivePlayType.PASS  # Default standard concept to pass (modern NFL is pass-first)
        elif concept in run_concepts:
            return OffensivePlayType.RUN
        elif concept in pass_concepts:
            return OffensivePlayType.PASS
        elif concept in special_concepts:
            if 'punt' in concept:
                return OffensivePlayType.PUNT
            elif 'kick' in concept:
                return OffensivePlayType.FIELD_GOAL
            else:
                return OffensivePlayType.PASS  # spike is technically a pass
        else:
            # Default to PASS for unknown concepts (modern NFL is pass-first)
            return OffensivePlayType.PASS
    
    def get_coaching_philosophy_summary(self) -> Dict[str, Any]:
        """
        Get summary of the coaching staff's combined philosophy
        
        Returns:
            Summary of coaching staff characteristics and tendencies
        """
        summary = {
            'head_coach': {
                'name': self.head_coach.name,
                'aggression': self.head_coach.aggression,
                'game_management_style': 'aggressive' if self.head_coach.game_management.fourth_down_decision_aggression > 0.6 else 'conservative',
                'coordinator_trust': {
                    'offensive': self.head_coach.coordinator_influence.offensive_coordinator_trust,
                    'defensive': self.head_coach.coordinator_influence.defensive_coordinator_trust,
                    'special_teams': self.head_coach.coordinator_influence.special_teams_coordinator_trust if self.special_teams_coordinator else None,
                }
            },
            'offensive_coordinator': {
                'name': self.offensive_coordinator.name,
                'philosophy': 'pass_heavy' if self.offensive_coordinator.run_preference < 0.4 else 'run_heavy' if self.offensive_coordinator.run_preference > 0.6 else 'balanced',
                'creativity': self.offensive_coordinator.philosophy.formation_creativity,
                'preferred_formations': ['SHOTGUN' if self.offensive_coordinator.formations.shotgun_preference > 0.6 else 'I_FORMATION']
            },
            'defensive_coordinator': {
                'name': self.defensive_coordinator.name,
                'base_scheme': '4-3' if self.defensive_coordinator.philosophy.four_three_preference > 0.5 else '3-4',
                'coverage_style': 'zone' if self.defensive_coordinator.philosophy.zone_coverage_preference > 0.5 else 'man',
                'aggression': self.defensive_coordinator.philosophy.blitz_frequency,
            },
            'staff_chemistry': {
                'head_coach_control': 'high' if max(
                    self.head_coach.coordinator_influence.offensive_coordinator_trust,
                    self.head_coach.coordinator_influence.defensive_coordinator_trust
                ) < 0.5 else 'collaborative',
                'overall_philosophy': self._get_overall_philosophy()
            }
        }
        
        # Add special teams coordinator info if available
        if self.special_teams_coordinator:
            summary['special_teams_coordinator'] = {
                'name': self.special_teams_coordinator.name,
                'philosophy': self.special_teams_coordinator.philosophy.value,
                'aggression': self.special_teams_coordinator.aggression,
                'punt_block_aggression': self.special_teams_coordinator.special_teams_traits.punt_block_aggression,
                'field_goal_block_aggression': self.special_teams_coordinator.special_teams_traits.field_goal_block_aggression,
            }
        
        return summary
    
    def _get_overall_philosophy(self) -> str:
        """Determine overall staff philosophy"""
        hc_aggression = self.head_coach.aggression
        oc_aggression = self.offensive_coordinator.aggression  
        dc_aggression = self.defensive_coordinator.aggression
        
        # Include special teams coordinator if available
        if self.special_teams_coordinator:
            st_aggression = self.special_teams_coordinator.aggression
            avg_aggression = (hc_aggression + oc_aggression + dc_aggression + st_aggression) / 4
        else:
            avg_aggression = (hc_aggression + oc_aggression + dc_aggression) / 3
        
        if avg_aggression > 0.6:
            return 'aggressive'
        elif avg_aggression < 0.4:
            return 'conservative'
        else:
            return 'balanced'