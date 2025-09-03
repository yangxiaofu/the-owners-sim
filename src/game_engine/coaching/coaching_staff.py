import random
from typing import Dict, Optional, List, Tuple
from collections import defaultdict
from game_engine.field.field_state import FieldState
from game_engine.plays.play_calling import OFFENSIVE_ARCHETYPES, DEFENSIVE_ARCHETYPES
from game_engine.coaching.coaching_constants import (
    COACH_PERSONALITIES, ADAPTATION_THRESHOLDS, OPPONENT_MEMORY_BONUSES,
    EXPERIENCE_MULTIPLIERS, PERSONNEL_PREFERENCES, DECISION_WEIGHTS,
    COACHING_EFFECTIVENESS, SITUATIONAL_MODIFIERS, PHILOSOPHY_COMPATIBILITY
)


class CoachingBalance:
    """
    Centralized configuration for coaching staff behavior - easy for game designers to tune
    
    This class contains all the magic numbers that affect coaching intelligence and adaptation.
    Adjust these values to change coaching behavior:
    - Higher adaptation rates = more responsive coaches
    - Stronger memory bonuses = better opponent-specific preparation
    - Different pressure thresholds = varying performance under stress
    
    Following the established pattern from PlayCallingBalance and other balance classes.
    """
    
    # === ADAPTATION CONFIGURATION ===
    BASE_ADAPTATION_RATE = 0.15                    # 15% base adaptation per drive
    MAX_ADAPTATION_PER_GAME = 0.40                 # Maximum 40% adaptation in single game
    MIN_SAMPLE_SIZE_FOR_ADAPTATION = 3             # Need 3 plays minimum before adapting
    
    ADAPTATION_DECAY_RATE = 0.05                   # 5% decay in adaptation per week
    MEMORY_RETENTION_RATE = 0.90                   # 90% memory retention between games
    
    # === EXPERIENCE IMPACT THRESHOLDS ===
    ROOKIE_EXPERIENCE_THRESHOLD = 2                # 0-2 years = rookie coach
    VETERAN_EXPERIENCE_THRESHOLD = 10              # 10+ years = veteran coach
    
    # === PRESSURE SITUATION THRESHOLDS ===  
    HIGH_PRESSURE_SCORE_DIFF = 7                   # Within 7 points = high pressure
    CRITICAL_TIME_THRESHOLD = 300                  # Final 5 minutes = critical time
    DESPERATION_TIME_THRESHOLD = 120               # Final 2 minutes = desperation
    
    # === OPPONENT MEMORY WEIGHTS ===
    DIVISION_RIVAL_MEMORY_BOOST = 0.30             # +30% memory vs division rivals
    RECENT_OPPONENT_MEMORY_BOOST = 0.20            # +20% memory vs recent opponents
    PLAYOFF_OPPONENT_MEMORY_BOOST = 0.25           # +25% memory vs playoff teams
    
    # === ARCHETYPE MODIFICATION LIMITS ===
    MAX_ARCHETYPE_DEVIATION = 0.25                 # Maximum 25% deviation from base archetype
    MIN_ARCHETYPE_RETENTION = 0.50                 # Must retain 50% of base archetype
    
    # === CONTEXTUAL INTELLIGENCE WEIGHTS ===
    FIELD_POSITION_INFLUENCE = 0.20                # How much field position affects decisions
    SCORE_DIFFERENTIAL_INFLUENCE = 0.25            # How much score affects strategy
    TIME_REMAINING_INFLUENCE = 0.30                # How much time affects urgency
    MOMENTUM_INFLUENCE = 0.15                      # How much momentum affects decisions
    
    # === DECISION CONSISTENCY FACTORS ===
    BASE_DECISION_VARIANCE = 0.10                  # 10% base randomness in decisions
    PRESSURE_VARIANCE_MULTIPLIER = 1.5             # 50% more variance under pressure
    EXPERIENCE_VARIANCE_REDUCTION = 0.6            # Veterans have 40% less variance
    
    @classmethod
    def validate_configuration(cls):
        """Validate that configuration values make sense (following established pattern)"""
        # Adaptation rates should be reasonable
        if not 0 <= cls.BASE_ADAPTATION_RATE <= 1:
            raise ValueError(f"Base adaptation rate {cls.BASE_ADAPTATION_RATE} must be between 0 and 1")
        if not 0 <= cls.MAX_ADAPTATION_PER_GAME <= 1:
            raise ValueError(f"Max adaptation per game {cls.MAX_ADAPTATION_PER_GAME} must be between 0 and 1")
        
        # Memory and decay rates should be reasonable
        if not 0 <= cls.MEMORY_RETENTION_RATE <= 1:
            raise ValueError(f"Memory retention rate {cls.MEMORY_RETENTION_RATE} must be between 0 and 1")
        if not 0 <= cls.ADAPTATION_DECAY_RATE <= 1:
            raise ValueError(f"Adaptation decay rate {cls.ADAPTATION_DECAY_RATE} must be between 0 and 1")
        
        # Thresholds should make sense
        if cls.VETERAN_EXPERIENCE_THRESHOLD <= cls.ROOKIE_EXPERIENCE_THRESHOLD:
            raise ValueError("Veteran experience threshold must be greater than rookie threshold")
        
        # Influence weights should sum to something reasonable
        total_influence = (cls.FIELD_POSITION_INFLUENCE + cls.SCORE_DIFFERENTIAL_INFLUENCE + 
                          cls.TIME_REMAINING_INFLUENCE + cls.MOMENTUM_INFLUENCE)
        if total_influence > 1.5:  # Allow some overlap but not too much
            raise ValueError(f"Total contextual influences {total_influence} should not exceed 1.5")


# Validate configuration on import (following established pattern)
CoachingBalance.validate_configuration()


class OffensiveCoordinator:
    """
    Individual offensive coordinator with dynamic archetype adaptation
    
    Each coordinator has a base archetype, experience level, and personality that affects
    how they prepare for games and adapt during play. They remember opponent strategies
    and adjust their approach based on game flow and historical matchups.
    """
    
    def __init__(self, base_archetype: str, experience: int, adaptability: float, 
                 personality: str, name: str = None):
        """
        Initialize offensive coordinator
        
        Args:
            base_archetype: Base offensive archetype from OFFENSIVE_ARCHETYPES
            experience: Years of coaching experience (affects decision quality)
            adaptability: Coach's ability to adapt (0.0 - 1.0)
            personality: Coach personality from COACH_PERSONALITIES
            name: Optional coordinator name for tracking
        """
        if base_archetype not in OFFENSIVE_ARCHETYPES:
            raise ValueError(f"Unknown offensive archetype: {base_archetype}")
        if personality not in COACH_PERSONALITIES:
            raise ValueError(f"Unknown personality: {personality}")
        if not 0 <= adaptability <= 1:
            raise ValueError(f"Adaptability {adaptability} must be between 0 and 1")
        
        self.base_archetype = base_archetype
        self.experience = experience
        self.adaptability = adaptability
        self.personality = personality
        self.name = name or f"{personality.title()} OC"
        
        # Current dynamic archetype (starts as base, adapts during game)
        self.current_archetype = OFFENSIVE_ARCHETYPES[base_archetype].copy()
        
        # Game state tracking
        self.opponent_memory = {}  # Track strategies vs specific opponents
        self.game_adaptations = {}  # Current game adaptations
        self.current_opponent = None
        self.drives_this_game = 0
        self.plays_this_drive = 0
        
        # Performance tracking for adaptation
        self.play_success_history = []
        self.drive_success_history = []
        self.current_momentum = 0.0
        
        # Experience-based modifiers
        self.experience_level = self._determine_experience_level()
        self.experience_modifiers = EXPERIENCE_MULTIPLIERS[self.experience_level]
        self.personality_traits = COACH_PERSONALITIES[personality]
    
    def _determine_experience_level(self) -> str:
        """Determine experience level based on years"""
        if self.experience <= CoachingBalance.ROOKIE_EXPERIENCE_THRESHOLD:
            return 'rookie_coach'
        elif self.experience < CoachingBalance.VETERAN_EXPERIENCE_THRESHOLD:
            return 'experienced_coach'
        else:
            return 'veteran_coach'
    
    def prepare_for_game(self, opponent_id: str, opponent_defensive_coordinator: Dict = None):
        """
        Prepare for game by analyzing opponent and selecting strategy
        
        Args:
            opponent_id: Identifier for the opposing team
            opponent_defensive_coordinator: Optional opponent DC info for counter-preparation
        """
        self.current_opponent = opponent_id
        self.drives_this_game = 0
        self.plays_this_drive = 0
        self.game_adaptations = {}
        
        # Check opponent memory for historical data
        opponent_history = self.opponent_memory.get(opponent_id, {})
        
        # Calculate memory bonus based on opponent relationship
        memory_bonus = self._calculate_memory_bonus(opponent_id)
        
        # Adjust base archetype based on opponent history and memory
        if opponent_history and memory_bonus > 0:
            successful_strategies = opponent_history.get('successful_strategies', {})
            failed_strategies = opponent_history.get('failed_strategies', {})
            
            # Apply successful strategies with memory bonus
            for strategy, success_rate in successful_strategies.items():
                if strategy in self.current_archetype.get('situation_modifiers', {}):
                    bonus = success_rate * memory_bonus * self.adaptability
                    self._apply_archetype_adjustment(strategy, bonus)
        
        # Counter-prepare against opponent defensive coordinator
        if opponent_defensive_coordinator:
            self._prepare_counter_strategy(opponent_defensive_coordinator)
    
    def _calculate_memory_bonus(self, opponent_id: str) -> float:
        """Calculate memory bonus based on opponent relationship"""
        # This would be expanded with actual team relationship data
        # For now, simulate some relationships
        base_bonus = 0.0
        
        # Division rival check (would use real team data)
        if opponent_id.endswith('_division_rival'):  # Simulated check
            base_bonus += CoachingBalance.DIVISION_RIVAL_MEMORY_BOOST
        
        # Recent opponent check
        if opponent_id in getattr(self, '_recent_opponents', []):
            base_bonus += CoachingBalance.RECENT_OPPONENT_MEMORY_BOOST
        
        # Apply personality memory modifier
        personality_memory = self.personality_traits.get('opponent_memory', 0.7)
        return base_bonus * personality_memory
    
    def _prepare_counter_strategy(self, opponent_dc: Dict):
        """Prepare counter-strategy against opponent's defensive coordinator"""
        opponent_archetype = opponent_dc.get('archetype', 'balanced_defense')
        
        if opponent_archetype in DEFENSIVE_ARCHETYPES:
            defensive_traits = DEFENSIVE_ARCHETYPES[opponent_archetype]
            counter_effects = defensive_traits.get('offensive_counter_effects', {})
            
            # Apply counter-strategy preparations
            for effect_type, modifier in counter_effects.items():
                self._apply_preparation_modifier(effect_type, modifier)
    
    def _apply_preparation_modifier(self, effect_type: str, modifier: float):
        """Apply preparation modifier based on scouting"""
        # Reduce effect based on adaptability and experience
        actual_modifier = modifier * self.adaptability * self.experience_modifiers.get('adaptation_speed', 1.0)
        
        # Apply to appropriate archetype elements
        if effect_type == 'pass_frequency':
            self._adjust_situation_modifier('pass_emphasis', actual_modifier)
        elif effect_type == 'run_frequency':
            self._adjust_situation_modifier('run_emphasis', actual_modifier)
        elif effect_type == 'quick_passes':
            self._adjust_situation_modifier('quick_game', actual_modifier)
    
    def get_current_archetype(self, field_state: FieldState = None, 
                            game_context: Dict = None) -> Dict:
        """
        Get current dynamic archetype based on game situation
        
        Args:
            field_state: Current field state for contextual adjustments
            game_context: Additional game context (score, time, etc.)
            
        Returns:
            Dict: Current archetype with all adaptations applied
        """
        # Start with current adapted archetype
        dynamic_archetype = self.current_archetype.copy()
        
        # Apply real-time contextual adjustments
        if field_state and game_context:
            dynamic_archetype = self._apply_contextual_adjustments(
                dynamic_archetype, field_state, game_context
            )
        
        # Apply experience and personality modifiers
        dynamic_archetype = self._apply_experience_modifiers(dynamic_archetype)
        dynamic_archetype = self._apply_personality_modifiers(dynamic_archetype)
        
        return dynamic_archetype
    
    def _apply_contextual_adjustments(self, archetype: Dict, field_state: FieldState, 
                                    game_context: Dict) -> Dict:
        """Apply real-time contextual adjustments to archetype"""
        adjusted_archetype = archetype.copy()
        
        # Score differential adjustments
        score_diff = game_context.get('score_differential', 0)
        time_remaining = game_context.get('time_remaining', 3600)
        
        # Apply pressure situation modifiers
        if self._is_high_pressure_situation(score_diff, time_remaining):
            pressure_resistance = (self.personality_traits.get('pressure_resistance', 0.7) * 
                                 self.experience_modifiers.get('pressure_resistance', 1.0))
            
            # Less pressure resistance = more deviation from base strategy
            pressure_factor = 1.0 - pressure_resistance
            self._apply_pressure_adjustments(adjusted_archetype, pressure_factor)
        
        # Field position adjustments
        if field_state.field_position >= 80:  # Red zone
            red_zone_aggression = self.personality_traits['situational_modifiers'].get('red_zone_aggression', 1.0)
            self._apply_red_zone_adjustments(adjusted_archetype, red_zone_aggression)
        
        return adjusted_archetype
    
    def _apply_experience_modifiers(self, archetype: Dict) -> Dict:
        """Apply experience-based modifiers to archetype"""
        modified_archetype = archetype.copy()
        
        # Apply experience modifiers based on experience level
        experience_mods = self.experience_modifiers
        
        # Experience affects decision consistency and adaptation speed
        if 'situation_modifiers' in modified_archetype:
            for situation, modifiers in modified_archetype['situation_modifiers'].items():
                for play_type, modifier in modifiers.items():
                    # More experienced coaches have more consistent modifiers
                    consistency_factor = experience_mods.get('decision_consistency', 1.0)
                    modified_archetype['situation_modifiers'][situation][play_type] *= consistency_factor
        
        return modified_archetype
    
    def _apply_personality_modifiers(self, archetype: Dict) -> Dict:
        """Apply personality-based modifiers to archetype"""
        modified_archetype = archetype.copy()
        
        # Apply personality traits to archetype
        personality_traits = self.personality_traits
        
        # Add personality-specific adjustments here
        # This could be expanded based on specific personality implementations
        
        return modified_archetype
    
    def _apply_pressure_adjustments(self, archetype: Dict, pressure_factor: float):
        """Apply pressure situation adjustments to archetype"""
        # Under pressure, coaches may deviate more from their base strategy
        if 'situation_modifiers' in archetype:
            for situation, modifiers in archetype['situation_modifiers'].items():
                for play_type in modifiers:
                    # Apply pressure-induced variance
                    variance = pressure_factor * CoachingBalance.BASE_DECISION_VARIANCE
                    pressure_adjustment = random.uniform(-variance, variance)
                    archetype['situation_modifiers'][situation][play_type] += pressure_adjustment
    
    def _apply_red_zone_adjustments(self, archetype: Dict, aggression_factor: float):
        """Apply red zone specific adjustments"""
        if 'situation_modifiers' in archetype:
            if 'red_zone' not in archetype['situation_modifiers']:
                archetype['situation_modifiers']['red_zone'] = {}
            
            # Apply red zone aggression
            red_zone_mods = archetype['situation_modifiers']['red_zone']
            red_zone_mods['pass'] = red_zone_mods.get('pass', 0) + (aggression_factor - 1.0) * 0.1
            red_zone_mods['field_goal'] = red_zone_mods.get('field_goal', 0) - (aggression_factor - 1.0) * 0.1
    
    def _calculate_momentum(self, play_results: List[Dict], drive_results: List[Dict]) -> float:
        """Calculate current momentum based on recent results"""
        if not play_results:
            return 0.0
        
        # Calculate recent success rate
        recent_successes = sum(1 for result in play_results 
                             if result.get('yards_gained', 0) > result.get('expected_yards', 0))
        success_rate = recent_successes / len(play_results)
        
        # Convert to momentum scale (-1.0 to 1.0)
        momentum = (success_rate - 0.5) * 2.0
        
        # Weight recent plays more heavily
        weighted_momentum = 0.0
        total_weight = 0.0
        
        for i, result in enumerate(reversed(play_results[-10:])):  # Last 10 plays
            weight = i + 1  # More recent plays have higher weight
            play_success = 1.0 if result.get('yards_gained', 0) > result.get('expected_yards', 0) else -1.0
            weighted_momentum += play_success * weight
            total_weight += weight
        
        if total_weight > 0:
            momentum = weighted_momentum / total_weight
        
        return max(-1.0, min(1.0, momentum))
    
    def _apply_momentum_adjustments(self):
        """Apply momentum-based adjustments to current strategy"""
        momentum_influence = CoachingBalance.MOMENTUM_INFLUENCE
        
        # Positive momentum might encourage more aggressive play calling
        # Negative momentum might encourage more conservative approach
        momentum_adjustment = self.current_momentum * momentum_influence
        
        # Apply to current archetype (simplified implementation)
        if 'situation_modifiers' in self.current_archetype:
            for situation in self.current_archetype['situation_modifiers']:
                for play_type in self.current_archetype['situation_modifiers'][situation]:
                    if play_type in ['pass', 'run']:
                        self.current_archetype['situation_modifiers'][situation][play_type] += momentum_adjustment * 0.1
    
    def _analyze_failing_categories(self, play_results: List[Dict]) -> Dict[str, float]:
        """Analyze which categories of plays are failing"""
        category_results = defaultdict(list)
        
        for result in play_results:
            play_type = result.get('play_type', 'unknown')
            success = result.get('yards_gained', 0) > result.get('expected_yards', 0)
            category_results[play_type].append(success)
        
        failure_rates = {}
        for category, successes in category_results.items():
            if successes:
                failure_rate = 1.0 - (sum(successes) / len(successes))
                failure_rates[category] = failure_rate
        
        return failure_rates
    
    def _analyze_successful_categories(self, play_results: List[Dict]) -> Dict[str, float]:
        """Analyze which categories of plays are succeeding"""
        category_results = defaultdict(list)
        
        for result in play_results:
            play_type = result.get('play_type', 'unknown')
            success = result.get('yards_gained', 0) > result.get('expected_yards', 0)
            category_results[play_type].append(success)
        
        success_rates = {}
        for category, successes in category_results.items():
            if successes:
                success_rate = sum(successes) / len(successes)
                success_rates[category] = success_rate
        
        return success_rates
    
    def _adjust_situation_modifier(self, situation: str, adjustment: float):
        """Adjust a specific situation modifier"""
        if 'situation_modifiers' not in self.current_archetype:
            self.current_archetype['situation_modifiers'] = {}
        
        if situation not in self.current_archetype['situation_modifiers']:
            self.current_archetype['situation_modifiers'][situation] = {}
        
        current_value = self.current_archetype['situation_modifiers'][situation].get(situation, 0)
        self.current_archetype['situation_modifiers'][situation][situation] = current_value + adjustment
    
    def _is_high_pressure_situation(self, score_diff: int, time_remaining: int) -> bool:
        """Determine if current situation is high pressure"""
        return (abs(score_diff) <= CoachingBalance.HIGH_PRESSURE_SCORE_DIFF and 
                time_remaining <= CoachingBalance.CRITICAL_TIME_THRESHOLD)
    
    def adapt_to_game_flow(self, play_results: List[Dict], drive_results: List[Dict]):
        """
        Adapt strategy based on game flow and play results
        
        Args:
            play_results: Recent play results for analysis
            drive_results: Recent drive results for broader analysis
        """
        if len(play_results) < CoachingBalance.MIN_SAMPLE_SIZE_FOR_ADAPTATION:
            return  # Not enough data to adapt
        
        # Calculate recent effectiveness
        recent_success_rate = self._calculate_success_rate(play_results)
        
        # Determine if adaptation is needed
        if recent_success_rate < ADAPTATION_THRESHOLDS['effectiveness']['struggling_threshold']:
            self._adapt_struggling_strategy(play_results)
        elif recent_success_rate > ADAPTATION_THRESHOLDS['effectiveness']['dominating_threshold']:
            self._reinforce_successful_strategy(play_results)
        
        # Update momentum tracking
        self.current_momentum = self._calculate_momentum(play_results, drive_results)
        
        # Apply momentum-based adjustments
        self._apply_momentum_adjustments()
    
    def _calculate_success_rate(self, play_results: List[Dict]) -> float:
        """Calculate success rate from recent plays"""
        if not play_results:
            return 0.5  # Neutral assumption
        
        successful_plays = sum(1 for result in play_results 
                              if result.get('yards_gained', 0) > result.get('expected_yards', 0))
        return successful_plays / len(play_results)
    
    def _adapt_struggling_strategy(self, play_results: List[Dict]):
        """Adapt strategy when struggling"""
        adaptation_rate = (CoachingBalance.BASE_ADAPTATION_RATE * 
                          self.adaptability * 
                          self.experience_modifiers.get('adaptation_speed', 1.0))
        
        # Analyze what's failing and adjust
        failing_categories = self._analyze_failing_categories(play_results)
        
        for category, failure_rate in failing_categories.items():
            if failure_rate > 0.7:  # 70% failure rate
                adjustment = -adaptation_rate * failure_rate
                self._apply_archetype_adjustment(category, adjustment)
    
    def _reinforce_successful_strategy(self, play_results: List[Dict]):
        """Reinforce successful strategies"""
        reinforcement_rate = (CoachingBalance.BASE_ADAPTATION_RATE * 0.5 * 
                             self.adaptability)
        
        successful_categories = self._analyze_successful_categories(play_results)
        
        for category, success_rate in successful_categories.items():
            if success_rate > 0.7:  # 70% success rate
                adjustment = reinforcement_rate * success_rate
                self._apply_archetype_adjustment(category, adjustment)
    
    def _apply_archetype_adjustment(self, category: str, adjustment: float):
        """Apply adjustment to archetype while respecting limits"""
        # Ensure adjustment doesn't exceed maximum deviation
        max_adjustment = CoachingBalance.MAX_ARCHETYPE_DEVIATION
        adjustment = max(-max_adjustment, min(max_adjustment, adjustment))
        
        # Apply to appropriate archetype section
        if category in self.current_archetype.get('situation_modifiers', {}):
            current_value = self.current_archetype['situation_modifiers'].get(category, 0)
            new_value = current_value + adjustment
            
            # Ensure minimum archetype retention
            base_value = OFFENSIVE_ARCHETYPES[self.base_archetype]['situation_modifiers'].get(category, 0)
            min_retention = CoachingBalance.MIN_ARCHETYPE_RETENTION
            
            # Don't deviate too far from base archetype
            max_deviation = abs(base_value) * (1 - min_retention)
            new_value = max(base_value - max_deviation, min(base_value + max_deviation, new_value))
            
            self.current_archetype['situation_modifiers'][category] = new_value


class DefensiveCoordinator:
    """
    Individual defensive coordinator with dynamic archetype adaptation
    
    Similar structure to OffensiveCoordinator but focuses on defensive strategies,
    opponent offensive tendencies, and defensive adjustments.
    """
    
    def __init__(self, base_archetype: str, experience: int, adaptability: float, 
                 personality: str, name: str = None):
        """
        Initialize defensive coordinator
        
        Args:
            base_archetype: Base defensive archetype from DEFENSIVE_ARCHETYPES
            experience: Years of coaching experience
            adaptability: Coach's ability to adapt (0.0 - 1.0)
            personality: Coach personality from COACH_PERSONALITIES  
            name: Optional coordinator name for tracking
        """
        if base_archetype not in DEFENSIVE_ARCHETYPES:
            raise ValueError(f"Unknown defensive archetype: {base_archetype}")
        if personality not in COACH_PERSONALITIES:
            raise ValueError(f"Unknown personality: {personality}")
        if not 0 <= adaptability <= 1:
            raise ValueError(f"Adaptability {adaptability} must be between 0 and 1")
        
        self.base_archetype = base_archetype
        self.experience = experience
        self.adaptability = adaptability
        self.personality = personality
        self.name = name or f"{personality.title()} DC"
        
        # Current dynamic archetype
        self.current_archetype = DEFENSIVE_ARCHETYPES[base_archetype].copy()
        
        # Game state tracking
        self.opponent_memory = {}
        self.game_adaptations = {}
        self.current_opponent = None
        self.defensive_stops = 0
        self.plays_this_drive = 0
        
        # Performance tracking
        self.stop_success_history = []
        self.pressure_success_history = []
        self.current_momentum = 0.0
        
        # Experience and personality modifiers
        self.experience_level = self._determine_experience_level()
        self.experience_modifiers = EXPERIENCE_MULTIPLIERS[self.experience_level]
        self.personality_traits = COACH_PERSONALITIES[personality]
    
    def _determine_experience_level(self) -> str:
        """Determine experience level based on years"""
        if self.experience <= CoachingBalance.ROOKIE_EXPERIENCE_THRESHOLD:
            return 'rookie_coach'
        elif self.experience < CoachingBalance.VETERAN_EXPERIENCE_THRESHOLD:
            return 'experienced_coach'
        else:
            return 'veteran_coach'
    
    def prepare_for_game(self, opponent_id: str, opponent_offensive_coordinator: Dict = None):
        """
        Prepare for game by analyzing opponent's offensive tendencies
        
        Args:
            opponent_id: Identifier for the opposing team
            opponent_offensive_coordinator: Optional opponent OC info for preparation
        """
        self.current_opponent = opponent_id
        self.defensive_stops = 0
        self.plays_this_drive = 0
        self.game_adaptations = {}
        
        # Analyze opponent offensive history
        opponent_history = self.opponent_memory.get(opponent_id, {})
        memory_bonus = self._calculate_memory_bonus(opponent_id)
        
        # Apply historical knowledge
        if opponent_history and memory_bonus > 0:
            self._apply_historical_adjustments(opponent_history, memory_bonus)
        
        # Prepare specific counters for opponent OC
        if opponent_offensive_coordinator:
            self._prepare_offensive_counters(opponent_offensive_coordinator)
    
    def _calculate_memory_bonus(self, opponent_id: str) -> float:
        """Calculate memory bonus for opponent preparation"""
        base_bonus = 0.0
        
        # Division rival bonus
        if opponent_id.endswith('_division_rival'):
            base_bonus += CoachingBalance.DIVISION_RIVAL_MEMORY_BOOST
        
        # Recent opponent bonus
        if opponent_id in getattr(self, '_recent_opponents', []):
            base_bonus += CoachingBalance.RECENT_OPPONENT_MEMORY_BOOST
        
        # Apply personality memory modifier
        personality_memory = self.personality_traits.get('opponent_memory', 0.7)
        return base_bonus * personality_memory
    
    def _prepare_offensive_counters(self, opponent_oc: Dict):
        """Prepare specific counters for opponent's offensive coordinator"""
        opponent_archetype = opponent_oc.get('archetype', 'balanced')
        
        if opponent_archetype in OFFENSIVE_ARCHETYPES:
            offensive_traits = OFFENSIVE_ARCHETYPES[opponent_archetype]
            
            # Prepare counters based on opponent's likely strategies
            self._prepare_archetype_counters(offensive_traits)
    
    def _prepare_archetype_counters(self, offensive_traits: Dict):
        """Prepare defensive counters for offensive archetype"""
        # Counter high-passing offenses with more coverage
        if offensive_traits.get('pass_frequency', 0.5) > 0.65:
            self._adjust_coverage_emphasis(0.15)
        
        # Counter run-heavy offenses with run stopping
        if offensive_traits.get('run_pass_ratio', 0.5) > 0.55:
            self._adjust_run_stop_emphasis(0.20)
        
        # Counter aggressive offenses with more pressure
        if offensive_traits.get('risk_tolerance', 0.5) > 0.7:
            self._adjust_pressure_frequency(0.10)
    
    def get_current_archetype(self, field_state: FieldState = None, 
                            game_context: Dict = None) -> Dict:
        """
        Get current dynamic defensive archetype
        
        Args:
            field_state: Current field state
            game_context: Game context information
            
        Returns:
            Dict: Current defensive archetype with adaptations
        """
        dynamic_archetype = self.current_archetype.copy()
        
        # Apply contextual adjustments
        if field_state and game_context:
            dynamic_archetype = self._apply_defensive_context(
                dynamic_archetype, field_state, game_context
            )
        
        # Apply experience and personality modifiers
        dynamic_archetype = self._apply_experience_modifiers(dynamic_archetype)
        dynamic_archetype = self._apply_personality_modifiers(dynamic_archetype)
        
        return dynamic_archetype
    
    def adapt_to_game_flow(self, defensive_results: List[Dict], drive_results: List[Dict]):
        """
        Adapt defensive strategy based on game flow
        
        Args:
            defensive_results: Recent defensive play results
            drive_results: Recent drive results for analysis
        """
        if len(defensive_results) < CoachingBalance.MIN_SAMPLE_SIZE_FOR_ADAPTATION:
            return
        
        # Calculate defensive effectiveness
        stop_rate = self._calculate_stop_rate(defensive_results)
        pressure_rate = self._calculate_pressure_rate(defensive_results)
        
        # Adapt based on performance
        if stop_rate < ADAPTATION_THRESHOLDS['effectiveness']['struggling_threshold']:
            self._adapt_struggling_defense(defensive_results)
        elif stop_rate > ADAPTATION_THRESHOLDS['effectiveness']['dominating_threshold']:
            self._reinforce_successful_defense(defensive_results)
        
        # Update momentum
        self.current_momentum = self._calculate_defensive_momentum(defensive_results, drive_results)
    
    def _apply_experience_modifiers(self, archetype: Dict) -> Dict:
        """Apply experience-based modifiers to defensive archetype"""
        modified_archetype = archetype.copy()
        
        # Apply experience modifiers
        experience_mods = self.experience_modifiers
        consistency_factor = experience_mods.get('decision_consistency', 1.0)
        
        # More experienced defensive coordinators have more consistent strategies
        if 'situation_modifiers' in modified_archetype:
            for situation, modifiers in modified_archetype['situation_modifiers'].items():
                for coverage_type, modifier in modifiers.items():
                    modified_archetype['situation_modifiers'][situation][coverage_type] *= consistency_factor
        
        return modified_archetype
    
    def _apply_personality_modifiers(self, archetype: Dict) -> Dict:
        """Apply personality-based modifiers to defensive archetype"""
        modified_archetype = archetype.copy()
        
        # Apply personality traits to defensive strategy
        personality_traits = self.personality_traits
        
        # This could be expanded with specific personality implementations for defense
        
        return modified_archetype
    
    def _apply_defensive_context(self, archetype: Dict, field_state: FieldState, 
                                game_context: Dict) -> Dict:
        """Apply defensive context adjustments"""
        adjusted_archetype = archetype.copy()
        
        # Field position based adjustments
        if field_state.field_position >= 80:  # Red zone defense
            # More aggressive coverage in red zone
            if 'situation_modifiers' not in adjusted_archetype:
                adjusted_archetype['situation_modifiers'] = {}
            if 'red_zone' not in adjusted_archetype['situation_modifiers']:
                adjusted_archetype['situation_modifiers']['red_zone'] = {}
            
            adjusted_archetype['situation_modifiers']['red_zone']['tight_coverage'] = 0.15
        
        return adjusted_archetype
    
    def _calculate_stop_rate(self, defensive_results: List[Dict]) -> float:
        """Calculate defensive stop rate"""
        if not defensive_results:
            return 0.5
        
        stops = sum(1 for result in defensive_results 
                   if result.get('yards_allowed', 5) < result.get('expected_yards', 4))
        return stops / len(defensive_results)
    
    def _calculate_pressure_rate(self, defensive_results: List[Dict]) -> float:
        """Calculate pressure rate from defensive results"""
        if not defensive_results:
            return 0.5
        
        pressures = sum(1 for result in defensive_results 
                       if result.get('pressure_generated', False))
        return pressures / len(defensive_results)
    
    def _adapt_struggling_defense(self, defensive_results: List[Dict]):
        """Adapt defensive strategy when struggling"""
        adaptation_rate = (CoachingBalance.BASE_ADAPTATION_RATE * 
                          self.adaptability * 
                          self.experience_modifiers.get('adaptation_speed', 1.0))
        
        # Analyze what's being exploited and adjust
        # Simplified implementation for now
        if 'situation_modifiers' not in self.current_archetype:
            self.current_archetype['situation_modifiers'] = {}
    
    def _reinforce_successful_defense(self, defensive_results: List[Dict]):
        """Reinforce successful defensive strategies"""
        reinforcement_rate = (CoachingBalance.BASE_ADAPTATION_RATE * 0.5 * 
                             self.adaptability)
        
        # Reinforce what's working
        # Simplified implementation for now
        pass
    
    def _calculate_defensive_momentum(self, defensive_results: List[Dict], 
                                    drive_results: List[Dict]) -> float:
        """Calculate defensive momentum"""
        if not defensive_results:
            return 0.0
        
        # Calculate recent stop rate
        recent_stops = sum(1 for result in defensive_results 
                          if result.get('yards_allowed', 5) < result.get('expected_yards', 4))
        stop_rate = recent_stops / len(defensive_results)
        
        # Convert to momentum scale
        momentum = (stop_rate - 0.5) * 2.0
        return max(-1.0, min(1.0, momentum))
    
    def _apply_historical_adjustments(self, opponent_history: Dict, memory_bonus: float):
        """Apply historical adjustments based on opponent memory"""
        # Simplified implementation
        successful_counters = opponent_history.get('successful_counters', {})
        for counter_type, success_rate in successful_counters.items():
            adjustment = success_rate * memory_bonus * self.adaptability * 0.1
            # Apply adjustment to current archetype
    
    def _adjust_coverage_emphasis(self, adjustment: float):
        """Adjust coverage emphasis"""
        if 'situation_modifiers' not in self.current_archetype:
            self.current_archetype['situation_modifiers'] = {}
        if 'coverage' not in self.current_archetype['situation_modifiers']:
            self.current_archetype['situation_modifiers']['coverage'] = {}
        
        current_coverage = self.current_archetype['situation_modifiers']['coverage'].get('emphasis', 0)
        self.current_archetype['situation_modifiers']['coverage']['emphasis'] = current_coverage + adjustment
    
    def _adjust_run_stop_emphasis(self, adjustment: float):
        """Adjust run stopping emphasis"""
        if 'situation_modifiers' not in self.current_archetype:
            self.current_archetype['situation_modifiers'] = {}
        if 'run_defense' not in self.current_archetype['situation_modifiers']:
            self.current_archetype['situation_modifiers']['run_defense'] = {}
        
        current_emphasis = self.current_archetype['situation_modifiers']['run_defense'].get('emphasis', 0)
        self.current_archetype['situation_modifiers']['run_defense']['emphasis'] = current_emphasis + adjustment
    
    def _adjust_pressure_frequency(self, adjustment: float):
        """Adjust pressure frequency"""
        if 'situation_modifiers' not in self.current_archetype:
            self.current_archetype['situation_modifiers'] = {}
        if 'pressure' not in self.current_archetype['situation_modifiers']:
            self.current_archetype['situation_modifiers']['pressure'] = {}
        
        current_frequency = self.current_archetype['situation_modifiers']['pressure'].get('frequency', 0)
        self.current_archetype['situation_modifiers']['pressure']['frequency'] = current_frequency + adjustment


class CoachingStaff:
    """
    Main orchestrating class that manages both coordinators and provides unified interface
    
    This is the primary class that interfaces with the play executor, similar to how
    PlayCaller works but with much more sophisticated coaching intelligence.
    """
    
    def __init__(self, team_id: str, coaching_config: Dict = None):
        """
        Initialize coaching staff for a team
        
        Args:
            team_id: Team identifier
            coaching_config: Configuration for coaching staff setup
        """
        self.team_id = team_id
        self.config = coaching_config or {}
        
        # Initialize coordinators based on config
        self.offensive_coordinator = self._create_offensive_coordinator()
        self.defensive_coordinator = self._create_defensive_coordinator()
        
        # Game management tracking
        self.games_coached = 0
        self.opponent_history = {}
        self.season_adaptations = {}
        
        # Validate configuration on initialization
        CoachingBalance.validate_configuration()
    
    def _create_offensive_coordinator(self) -> OffensiveCoordinator:
        """Create offensive coordinator from configuration"""
        oc_config = self.config.get('offensive_coordinator', {})
        
        return OffensiveCoordinator(
            base_archetype=oc_config.get('archetype', 'balanced'),
            experience=oc_config.get('experience', 5),
            adaptability=oc_config.get('adaptability', 0.7),
            personality=oc_config.get('personality', 'balanced'),
            name=oc_config.get('name', None)
        )
    
    def _create_defensive_coordinator(self) -> DefensiveCoordinator:
        """Create defensive coordinator from configuration"""
        dc_config = self.config.get('defensive_coordinator', {})
        
        return DefensiveCoordinator(
            base_archetype=dc_config.get('archetype', 'balanced_defense'),
            experience=dc_config.get('experience', 5),
            adaptability=dc_config.get('adaptability', 0.7),
            personality=dc_config.get('personality', 'balanced'),
            name=dc_config.get('name', None)
        )
    
    def prepare_for_game(self, opponent_team_id: str, opponent_coaching_staff: 'CoachingStaff' = None):
        """
        Prepare coaching staff for upcoming game
        
        Args:
            opponent_team_id: ID of opposing team
            opponent_coaching_staff: Optional opponent coaching staff for scouting
        """
        # Prepare coordinators for game
        opponent_dc = None
        opponent_oc = None
        
        if opponent_coaching_staff:
            opponent_dc = {
                'archetype': opponent_coaching_staff.defensive_coordinator.base_archetype,
                'experience': opponent_coaching_staff.defensive_coordinator.experience,
                'personality': opponent_coaching_staff.defensive_coordinator.personality
            }
            opponent_oc = {
                'archetype': opponent_coaching_staff.offensive_coordinator.base_archetype,
                'experience': opponent_coaching_staff.offensive_coordinator.experience,
                'personality': opponent_coaching_staff.offensive_coordinator.personality
            }
        
        self.offensive_coordinator.prepare_for_game(opponent_team_id, opponent_dc)
        self.defensive_coordinator.prepare_for_game(opponent_team_id, opponent_oc)
        
        # Update historical opponent tracking
        self._update_opponent_history(opponent_team_id)
        
        self.games_coached += 1
    
    def get_offensive_coordinator_for_situation(self, field_state: FieldState, 
                                              game_context: Dict) -> Dict:
        """
        Get offensive coordinator archetype for current situation
        
        Args:
            field_state: Current field state
            game_context: Game context (score, time, etc.)
            
        Returns:
            Dict: Archetype data for play calling system
        """
        # Get dynamic archetype from coordinator
        current_archetype = self.offensive_coordinator.get_current_archetype(field_state, game_context)
        
        # Package for play calling system compatibility
        return {
            'archetype': self.offensive_coordinator.base_archetype,
            'current_archetype_data': current_archetype,
            'coordinator_name': self.offensive_coordinator.name,
            'experience': self.offensive_coordinator.experience,
            'adaptability': self.offensive_coordinator.adaptability,
            'personality': self.offensive_coordinator.personality,
            'custom_modifiers': self._extract_custom_modifiers(current_archetype)
        }
    
    def get_defensive_coordinator_for_situation(self, field_state: FieldState, 
                                              game_context: Dict) -> Dict:
        """
        Get defensive coordinator archetype for current situation
        
        Args:
            field_state: Current field state
            game_context: Game context information
            
        Returns:
            Dict: Defensive coordinator data for opponent analysis
        """
        current_archetype = self.defensive_coordinator.get_current_archetype(field_state, game_context)
        
        return {
            'archetype': self.defensive_coordinator.base_archetype,
            'current_archetype_data': current_archetype,
            'coordinator_name': self.defensive_coordinator.name,
            'experience': self.defensive_coordinator.experience,
            'adaptability': self.defensive_coordinator.adaptability,
            'personality': self.defensive_coordinator.personality
        }
    
    def adapt_during_game(self, offensive_results: List[Dict], defensive_results: List[Dict],
                         drive_results: List[Dict]):
        """
        Adapt coaching strategy during game based on results
        
        Args:
            offensive_results: Recent offensive play results
            defensive_results: Recent defensive play results
            drive_results: Recent drive results for context
        """
        # Adapt both coordinators based on their respective performance
        if offensive_results:
            self.offensive_coordinator.adapt_to_game_flow(offensive_results, drive_results)
        
        if defensive_results:
            self.defensive_coordinator.adapt_to_game_flow(defensive_results, drive_results)
        
        # Update game-level adaptations
        self._update_game_adaptations(offensive_results, defensive_results, drive_results)
    
    def _extract_custom_modifiers(self, archetype_data: Dict) -> Dict:
        """Extract custom modifiers from archetype for play calling compatibility"""
        custom_modifiers = {}
        
        # Extract relevant modifiers for play calling system
        situation_mods = archetype_data.get('situation_modifiers', {})
        
        # Convert to play calling system format - extract specific values, not entire dicts
        if 'red_zone' in situation_mods and isinstance(situation_mods['red_zone'], dict):
            red_zone_mods = situation_mods['red_zone']
            # Extract pass emphasis as aggression metric
            if 'pass' in red_zone_mods:
                custom_modifiers['red_zone_aggression'] = red_zone_mods['pass']
            elif 'aggression' in red_zone_mods:
                custom_modifiers['red_zone_aggression'] = red_zone_mods['aggression']
            else:
                custom_modifiers['red_zone_aggression'] = 0.1  # Default small boost
        
        if '4th_and_short' in situation_mods and isinstance(situation_mods['4th_and_short'], dict):
            fourth_mods = situation_mods['4th_and_short']
            # Calculate aggression as combination of run/pass vs punt/field_goal
            run_boost = fourth_mods.get('run', 0)
            pass_boost = fourth_mods.get('pass', 0)
            punt_penalty = abs(fourth_mods.get('punt', 0))
            fg_penalty = abs(fourth_mods.get('field_goal', 0))
            aggression = (run_boost + pass_boost + punt_penalty + fg_penalty) / 4
            custom_modifiers['fourth_down_aggression'] = aggression
        
        # Add other relevant modifiers safely
        game_situation_mods = archetype_data.get('game_situation_modifiers', {})
        for key, value in game_situation_mods.items():
            if isinstance(value, (int, float)):  # Only add numeric values
                custom_modifiers[key] = value
        
        return custom_modifiers
    
    def _update_opponent_history(self, opponent_id: str):
        """Update historical data for opponent"""
        if opponent_id not in self.opponent_history:
            self.opponent_history[opponent_id] = {
                'games_played': 0,
                'last_played': self.games_coached,
                'offensive_success': [],
                'defensive_success': []
            }
        
        opponent_data = self.opponent_history[opponent_id]
        opponent_data['games_played'] += 1
        opponent_data['last_played'] = self.games_coached
    
    def _update_game_adaptations(self, offensive_results: List[Dict], 
                               defensive_results: List[Dict], drive_results: List[Dict]):
        """Update game-level adaptations and learning"""
        # This would track broader strategic adjustments
        # For now, just update basic tracking
        current_game = f"game_{self.games_coached}"
        
        if current_game not in self.season_adaptations:
            self.season_adaptations[current_game] = {
                'offensive_adjustments': 0,
                'defensive_adjustments': 0,
                'total_plays': len(offensive_results) + len(defensive_results)
            }
        
        # Track adaptation frequency
        adaptation_data = self.season_adaptations[current_game]
        adaptation_data['offensive_adjustments'] += len([r for r in offensive_results if r.get('adapted', False)])
        adaptation_data['defensive_adjustments'] += len([r for r in defensive_results if r.get('adapted', False)])
    
    def get_coaching_intelligence_summary(self) -> Dict:
        """
        Get summary of coaching staff intelligence and adaptations
        
        Returns:
            Dict: Summary of coaching staff status and capabilities
        """
        return {
            'team_id': self.team_id,
            'games_coached': self.games_coached,
            'offensive_coordinator': {
                'name': self.offensive_coordinator.name,
                'base_archetype': self.offensive_coordinator.base_archetype,
                'experience': self.offensive_coordinator.experience,
                'adaptability': self.offensive_coordinator.adaptability,
                'personality': self.offensive_coordinator.personality,
                'current_momentum': self.offensive_coordinator.current_momentum
            },
            'defensive_coordinator': {
                'name': self.defensive_coordinator.name,
                'base_archetype': self.defensive_coordinator.base_archetype,
                'experience': self.defensive_coordinator.experience,
                'adaptability': self.defensive_coordinator.adaptability,
                'personality': self.defensive_coordinator.personality,
                'current_momentum': self.defensive_coordinator.current_momentum
            },
            'opponent_history_size': len(self.opponent_history),
            'season_adaptations': len(self.season_adaptations)
        }