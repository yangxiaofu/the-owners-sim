"""
Head Coach - Game management and coordinator oversight

The head coach is responsible for overall game strategy, critical decision making,
and has override authority over coordinators in high-leverage situations.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .coach_archetype import BaseCoachArchetype, CoachType, SituationalTendencies
from .fourth_down_matrix import FourthDownMatrix, CoachAggressionLevel
from .game_situation_analyzer import GameSituationAnalyzer


@dataclass  
class GameManagementTraits:
    """Head coach specific game management traits"""
    # Critical decision making (0.0-1.0)
    fourth_down_decision_aggression: float = 0.4    # Go for it vs punt/kick
    two_minute_drill_aggression: float = 0.7        # Aggressive vs conservative clock management
    overtime_aggression: float = 0.6                # Risk taking in overtime
    
    # Game flow management
    timeout_usage_intelligence: float = 0.7         # Smart timeout usage
    challenge_flag_wisdom: float = 0.6              # When to throw challenge flags
    clock_management_skill: float = 0.7             # End-of-half/game clock management
    
    # Personnel decisions
    starter_loyalty: float = 0.6                    # Stick with starters vs rotate
    rookie_trust: float = 0.4                       # Willingness to play rookies
    injury_risk_tolerance: float = 0.3              # Playing hurt players


@dataclass
class CoordinatorInfluence:
    """How much the head coach trusts and influences coordinators"""
    # Trust levels (0.0-1.0)
    offensive_coordinator_trust: float = 0.7        # Trust OC's play calling
    defensive_coordinator_trust: float = 0.7        # Trust DC's scheme calling
    special_teams_coordinator_trust: float = 0.6    # Trust STC decisions
    
    # Override thresholds (0.0-1.0) - lower = more likely to override
    critical_situation_override_threshold: float = 0.3  # 4th down, 2-min, red zone
    momentum_shift_override_threshold: float = 0.4      # When momentum changes
    game_script_override_threshold: float = 0.5         # When behind/ahead by a lot


@dataclass
class TimeoutDecision:
    """Head coach timeout decision."""
    should_use_timeout: bool
    confidence: float  # 0.0-1.0
    reasoning: str
    urgency_level: float  # 0.0-1.0
    timeout_type: str  # "clock_stop", "regroup", "momentum", "challenge"


@dataclass
class HeadCoach(BaseCoachArchetype):
    """
    Head coach with game management focus and coordinator oversight
    
    The head coach makes high-level strategic decisions and can override
    coordinators in critical situations while delegating routine play calling.
    """
    
    # Specialized traits for head coaches
    game_management: GameManagementTraits = field(default_factory=GameManagementTraits)
    coordinator_influence: CoordinatorInfluence = field(default_factory=CoordinatorInfluence)
    
    def __post_init__(self):
        """Initialize head coach with proper type and validation"""
        self.coach_type = CoachType.HEAD_COACH
        super().__post_init__()
    
    def should_override_coordinator(self, situation: str, game_context: Dict[str, Any] = None) -> bool:
        """
        Determine if head coach should override coordinator decision
        
        Args:
            situation: Type of situation ('fourth_down', 'red_zone', 'two_minute', etc.)
            game_context: Additional context (score differential, momentum, etc.)
        
        Returns:
            True if head coach should make the call instead of coordinator
        """
        if not game_context:
            game_context = {}
        
        # Always override in critical situations if aggression is high
        critical_situations = ['fourth_down', 'overtime', 'game_winning_drive']
        if situation in critical_situations:
            override_threshold = self.coordinator_influence.critical_situation_override_threshold
            return self.aggression > override_threshold
        
        # Override in red zone based on aggression and red zone traits
        if situation == 'red_zone':
            red_zone_aggression = self.get_situational_aggression('red_zone')
            return red_zone_aggression > 0.7
        
        # Override during momentum shifts
        momentum = game_context.get('momentum_shift', False)
        if momentum:
            override_threshold = self.coordinator_influence.momentum_shift_override_threshold
            return self.momentum_responsiveness > override_threshold
        
        # Override when game script demands it (big lead/deficit)
        score_differential = abs(game_context.get('score_differential', 0))
        if score_differential > 14:  # More than 2 TD difference
            return self.game_script_adherence < 0.5  # Low adherence = more likely to override
        
        return False
    
    def get_override_influence(self, coordinator_type: str) -> float:
        """
        Get how much influence the head coach exerts over a coordinator
        
        Args:
            coordinator_type: 'offensive', 'defensive', or 'special_teams'
        
        Returns:
            Influence factor (0.0-1.0) where 1.0 = complete control
        """
        trust_mapping = {
            'offensive': self.coordinator_influence.offensive_coordinator_trust,
            'defensive': self.coordinator_influence.defensive_coordinator_trust,
            'special_teams': self.coordinator_influence.special_teams_coordinator_trust,
        }
        
        trust_level = trust_mapping.get(coordinator_type, 0.5)
        
        # Lower trust = higher influence (inverse relationship)
        influence = 1.0 - trust_level
        
        # Adjust based on head coach control tendencies
        control_factor = (1.0 - self.adaptability) * 0.5  # Less adaptable = more controlling
        
        return min(1.0, influence + control_factor)
    
    def _get_coach_aggression_level(self) -> CoachAggressionLevel:
        """
        Convert coach's aggression trait to CoachAggressionLevel enum
        
        Returns:
            CoachAggressionLevel based on coach's aggression and conservatism traits
        """
        # Use both aggression and conservatism to determine overall level
        effective_aggression = self.aggression - (self.conservatism * 0.5)
        
        if effective_aggression >= 0.8:
            return CoachAggressionLevel.ULTRA_AGGRESSIVE
        elif effective_aggression >= 0.6:
            return CoachAggressionLevel.AGGRESSIVE
        elif effective_aggression <= 0.2:
            return CoachAggressionLevel.ULTRA_CONSERVATIVE
        elif effective_aggression <= 0.4:
            return CoachAggressionLevel.CONSERVATIVE
        else:
            return CoachAggressionLevel.BALANCED
    
    def get_game_management_decision(self, situation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make head coach specific game management decisions
        
        Args:
            situation: Game situation requiring head coach decision
            context: Situation context (time, score, field position, etc.)
        
        Returns:
            Decision dictionary with recommendation and confidence
        """
        if not context:
            context = {}
        
        decisions = {}
        
        if situation == 'fourth_down':
            # Extract context information
            field_position = context.get('field_position', 50)
            yards_to_go = context.get('yards_to_go', 4)
            time_remaining = context.get('time_remaining', 900)
            score_differential = context.get('score_differential', 0)
            quarter = context.get('quarter', 4)

            # Get coach's aggression level for matrix system
            coach_aggression = self._get_coach_aggression_level()

            # Get momentum modifier from context (if available)
            # Momentum affects aggression: positive momentum = go for it more
            momentum_modifier = context.get('momentum_aggression_modifier', 1.0)

            # Analyze game situation for special modifiers
            game_context = GameSituationAnalyzer.analyze_game_context(context)
            special_situations = GameSituationAnalyzer.get_special_situations(game_context)

            # Use matrix-based decision system
            matrix_decision = FourthDownMatrix.calculate_fourth_down_decision(
                field_position=field_position,
                yards_to_go=yards_to_go,
                score_differential=score_differential,
                time_remaining=time_remaining,
                quarter=quarter,
                coach_aggression=coach_aggression,
                special_situations=special_situations,
                momentum_modifier=momentum_modifier
            )
            
            # Convert matrix decision to expected format
            decisions['fourth_down'] = {
                'go_for_it_probability': matrix_decision.go_for_it_probability,
                'recommendation': matrix_decision.recommendation,
                'confidence': matrix_decision.confidence,
                'matrix_breakdown': matrix_decision.breakdown,
                'decision_factors': matrix_decision.factors
            }
        
        elif situation == 'two_minute_drill':
            aggression = self.game_management.two_minute_drill_aggression
            timeout_usage = self.game_management.timeout_usage_intelligence

            decisions['two_minute'] = {
                'aggression_level': aggression,
                'timeout_strategy': 'aggressive' if timeout_usage > 0.6 else 'conservative',
                'clock_management': 'stop_clock' if aggression > 0.6 else 'control_clock'
            }

        elif situation == 'timeout_decision':
            timeout_decision = self.should_call_timeout(
                timeouts_remaining=context.get('timeouts_remaining', 3),
                time_remaining=context.get('time_remaining', 900),
                quarter=context.get('quarter', 4),
                score_differential=context.get('score_differential', 0),
                clock_running=context.get('clock_running', True),
                down=context.get('down', 1),
                possession=context.get('possession', True)
            )

            decisions['timeout'] = {
                'call_timeout': timeout_decision.should_use_timeout,
                'confidence': timeout_decision.confidence,
                'reasoning': timeout_decision.reasoning,
                'urgency': timeout_decision.urgency_level,
                'timeout_type': timeout_decision.timeout_type
            }

        return decisions

    def should_call_timeout(
        self,
        timeouts_remaining: int,
        time_remaining: int,
        quarter: int,
        score_differential: int,
        clock_running: bool = True,
        down: int = 1,
        possession: bool = True
    ) -> TimeoutDecision:
        """
        Determine if head coach should call a timeout.

        Args:
            timeouts_remaining: Timeouts left for this team (0-3)
            time_remaining: Seconds remaining in quarter
            quarter: Current quarter (1-4)
            score_differential: Points ahead (positive) or behind (negative)
            clock_running: Is play clock running?
            down: Current down (1-4)
            possession: Does this team have possession?

        Returns:
            TimeoutDecision with recommendation
        """
        # Can't call timeout with none remaining
        if timeouts_remaining <= 0:
            return TimeoutDecision(
                should_use_timeout=False,
                confidence=1.0,
                reasoning="No timeouts remaining",
                urgency_level=0.0,
                timeout_type="none"
            )

        # Get coach's timeout usage intelligence (0.0-1.0)
        intelligence = self.game_management.timeout_usage_intelligence

        # --- Scenario 1: Two-Minute Drill (Trailing) ---
        if quarter == 4 and time_remaining < 120 and score_differential < 0:
            # Need clock stops when trailing in final 2 minutes
            if clock_running and possession:
                # High intelligence coaches preserve timeouts more carefully
                preserve_threshold = 0.7 if intelligence > 0.7 else 0.5

                if timeouts_remaining >= 2:
                    # Have plenty, use aggressively
                    return TimeoutDecision(
                        should_use_timeout=True,
                        confidence=0.8,
                        reasoning="Two-minute drill: stop clock while trailing",
                        urgency_level=0.9,
                        timeout_type="clock_stop"
                    )
                elif timeouts_remaining == 1 and time_remaining < 60:
                    # Last timeout, only in final minute
                    return TimeoutDecision(
                        should_use_timeout=True,
                        confidence=0.6,
                        reasoning="Final timeout in critical situation",
                        urgency_level=1.0,
                        timeout_type="clock_stop"
                    )

        # --- Scenario 2: End of Half (Use It or Lose It) ---
        if time_remaining < 30 and quarter in [2, 4]:
            # Less than 30 seconds in half - use timeouts before they expire
            if clock_running and timeouts_remaining > 0:
                return TimeoutDecision(
                    should_use_timeout=True,
                    confidence=0.7,
                    reasoning="End of half: use timeout before it expires",
                    urgency_level=0.8,
                    timeout_type="clock_stop"
                )

        # --- Scenario 3: Defensive Timeout (Prevent Big Play) ---
        if not possession and quarter == 4 and abs(score_differential) <= 7:
            # Close game, on defense, could use timeout to regroup
            if intelligence > 0.6 and timeouts_remaining >= 2:
                # Smart coaches use defensive timeouts strategically
                return TimeoutDecision(
                    should_use_timeout=False,  # Will be overridden by specific situations
                    confidence=0.5,
                    reasoning="Strategic defensive timeout consideration",
                    urgency_level=0.5,
                    timeout_type="regroup"
                )

        # --- Scenario 4: Preserve Timeouts (Winning Late) ---
        if quarter == 4 and time_remaining < 120 and score_differential > 0:
            # Winning in final 2 minutes - don't use timeouts
            return TimeoutDecision(
                should_use_timeout=False,
                confidence=0.9,
                reasoning="Preserve timeouts when winning late",
                urgency_level=0.2,
                timeout_type="none"
            )

        # --- Default: Don't use timeout ---
        return TimeoutDecision(
            should_use_timeout=False,
            confidence=0.6,
            reasoning="No critical timeout situation",
            urgency_level=0.3,
            timeout_type="none"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert head coach to dictionary for JSON serialization"""
        base_dict = super().to_dict()
        
        # Add head coach specific data
        base_dict['coach_type'] = self.coach_type.value
        base_dict['game_management'] = {
            'fourth_down_decision_aggression': self.game_management.fourth_down_decision_aggression,
            'two_minute_drill_aggression': self.game_management.two_minute_drill_aggression,
            'overtime_aggression': self.game_management.overtime_aggression,
            'timeout_usage_intelligence': self.game_management.timeout_usage_intelligence,
            'challenge_flag_wisdom': self.game_management.challenge_flag_wisdom,
            'clock_management_skill': self.game_management.clock_management_skill,
            'starter_loyalty': self.game_management.starter_loyalty,
            'rookie_trust': self.game_management.rookie_trust,
            'injury_risk_tolerance': self.game_management.injury_risk_tolerance,
        }
        base_dict['coordinator_influence'] = {
            'offensive_coordinator_trust': self.coordinator_influence.offensive_coordinator_trust,
            'defensive_coordinator_trust': self.coordinator_influence.defensive_coordinator_trust,
            'special_teams_coordinator_trust': self.coordinator_influence.special_teams_coordinator_trust,
            'critical_situation_override_threshold': self.coordinator_influence.critical_situation_override_threshold,
            'momentum_shift_override_threshold': self.coordinator_influence.momentum_shift_override_threshold,
            'game_script_override_threshold': self.coordinator_influence.game_script_override_threshold,
        }
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeadCoach':
        """Create HeadCoach from dictionary (JSON loading)"""
        # Extract specialized data
        game_management_data = data.get('game_management', {})
        coordinator_influence_data = data.get('coordinator_influence', {})
        
        # Use base class method for common traits
        base_coach = BaseCoachArchetype.from_dict(data)
        
        # Create head coach with specialized traits
        return cls(
            name=base_coach.name,
            description=base_coach.description,
            coach_type=CoachType.HEAD_COACH,
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
            game_management=GameManagementTraits(**game_management_data),
            coordinator_influence=CoordinatorInfluence(**coordinator_influence_data),
        )