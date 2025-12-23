"""
Defensive Coordinator - Defensive scheme management and play calling

The defensive coordinator is responsible for defensive formation selection,
coverage schemes, pressure packages, and defensive game planning.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
from .coach_archetype import BaseCoachArchetype, CoachType
from ..mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext


class DefensiveCoverageType(Enum):
    """Defensive coverage scheme types"""
    COVER_0 = "Cover-0"
    COVER_1 = "Cover-1"
    COVER_2 = "Cover-2"
    COVER_3 = "Cover-3"
    MAN_TO_MAN = "Man-to-Man"
    MAN_FREE = "Man-Free"
    PREVENT = "Prevent"
    PUNT_RETURN_COVERAGE = "Punt Return Coverage"
    FIELD_GOAL_BLOCK_COVERAGE = "Field Goal Block Coverage"
    KICKOFF_RETURN_COVERAGE = "Kickoff Return Coverage"


@dataclass
class DefensivePhilosophy:
    """Defensive coordinator specific philosophical traits"""
    # Base defensive scheme preferences (0.0-1.0)
    four_three_preference: float = 0.6          # 4-3 base defense preference
    three_four_preference: float = 0.4          # 3-4 base defense preference
    nickel_heavy_preference: float = 0.7        # Sub package usage (nickel/dime)
    
    # Coverage philosophy (0.0-1.0)
    zone_coverage_preference: float = 0.6       # Zone vs man coverage preference
    man_coverage_confidence: float = 0.4        # Comfort with man coverage
    press_coverage_aggression: float = 0.5      # Press vs off coverage
    safety_help_reliance: float = 0.6           # Two-high safety preference
    
    # Pressure philosophy (0.0-1.0)
    blitz_frequency: float = 0.3                # How often to send extra rushers  
    creative_pressure_usage: float = 0.4        # Exotic blitz packages
    four_man_rush_confidence: float = 0.6       # Confidence in base rush
    timing_blitz_mastery: float = 0.5          # Situational pressure timing


@dataclass
class PersonnelUsage:
    """How the DC manages defensive personnel packages and player rotation.

    Rotation Settings (0.0-1.0):
    - Higher values = MORE rotation = lower starter snap share
    - These affect DefensiveRotationManager snap distribution per position group:
      * edge_rusher_rotation: DL rotates 55-75% (most rotation to keep pass rush fresh)
      * linebacker_versatility: LB rotates 70-85% (moderate rotation)
      * safety_flexibility: DB rotates 82-95% (least rotation for coverage continuity)
    """
    # Personnel package usage (0.0-1.0)
    base_defense_reliance: float = 0.5          # Stick with base 11 personnel
    nickel_package_comfort: float = 0.7         # 5 DB packages
    dime_package_usage: float = 0.4             # 6 DB packages
    goal_line_personnel_aggression: float = 0.6 # Heavy personnel in goal line

    # Player rotation settings (0.0=minimal rotation, 1.0=heavy rotation)
    # These directly affect DefensiveRotationManager.from_defensive_coordinator()
    edge_rusher_rotation: float = 0.6           # DL rotation: 0.0→75% starter, 1.0→55% starter
    linebacker_versatility: float = 0.5         # LB rotation: 0.0→85% starter, 1.0→70% starter
    safety_flexibility: float = 0.6             # DB rotation: 0.0→95% starter, 1.0→82% starter
    cornerback_shadowing: float = 0.3           # Shadow top receivers (not rotation-related)


@dataclass
class SituationalDefense:
    """Situational defensive calling tendencies"""
    # Down and distance responses
    first_down_aggression: float = 0.4          # Pressure on 1st down
    second_and_long_creativity: float = 0.6     # Exotic looks on 2nd & long
    third_down_pressure_rate: float = 0.7       # Blitz frequency on 3rd down
    
    # Field position adjustments
    red_zone_goal_line_aggression: float = 0.6  # Aggressive goal line defense
    red_zone_coverage_tightness: float = 0.8    # Tighter coverage in red zone
    backed_up_defense_conservatism: float = 0.7 # Conservative when opponent is backed up
    
    # Game situation responses
    prevent_defense_usage: float = 0.3          # Prevent defense frequency
    two_minute_drill_aggression: float = 0.5    # Pressure in two-minute drill
    fourth_down_stop_aggression: float = 0.8    # All-out rush on 4th down


@dataclass
class DefensiveCoordinator(BaseCoachArchetype):
    """
    Defensive coordinator focused on defensive scheme management
    
    Handles defensive formation selection, coverage schemes, pressure packages,
    and implements defensive game plans with situational awareness.
    """
    
    # Specialized traits for defensive coordinators
    philosophy: DefensivePhilosophy = field(default_factory=DefensivePhilosophy)
    personnel: PersonnelUsage = field(default_factory=PersonnelUsage)
    defensive_situational: SituationalDefense = field(default_factory=SituationalDefense)
    
    # Defensive playbook preferences
    preferred_defensive_playbooks: List[str] = field(default_factory=lambda: ["balanced_defense"])
    
    def __post_init__(self):
        """Initialize defensive coordinator with proper type and validation"""
        self.coach_type = CoachType.DEFENSIVE_COORDINATOR
        super().__post_init__()
    
    def get_defensive_formation(self, offensive_formation: str, situation: str, context: Dict[str, Any] = None) -> UnifiedDefensiveFormation:
        """
        Select defensive formation based on offensive formation and situation
        
        Args:
            offensive_formation: Offensive formation being defended
            situation: Game situation ('first_down', 'red_zone', 'two_minute', etc.)
            context: Additional context (down, distance, personnel, etc.)
        
        Returns:
            UnifiedDefensiveFormation enum (callers use .for_context() to get appropriate string)
        """
        if not context:
            context = {}
        
        # Base formation preferences using unified enum system
        formations = {
            UnifiedDefensiveFormation.FOUR_THREE_BASE: self.philosophy.four_three_preference,
            UnifiedDefensiveFormation.THREE_FOUR_BASE: self.philosophy.three_four_preference,
            UnifiedDefensiveFormation.NICKEL_DEFENSE: self.philosophy.nickel_heavy_preference,
            UnifiedDefensiveFormation.DIME_DEFENSE: self.personnel.dime_package_usage,
        }
        
        # Adjust based on offensive formation
        if offensive_formation in ['shotgun', 'four_wide']:
            # More sub packages against spread formations
            formations[UnifiedDefensiveFormation.NICKEL_DEFENSE] *= 1.4
            formations[UnifiedDefensiveFormation.DIME_DEFENSE] *= 1.3
            formations[UnifiedDefensiveFormation.FOUR_THREE_BASE] *= 0.7
            formations[UnifiedDefensiveFormation.THREE_FOUR_BASE] *= 0.8
            
        elif offensive_formation == 'i_formation':
            # More base defense against power formations
            formations[UnifiedDefensiveFormation.FOUR_THREE_BASE] *= 1.3
            formations[UnifiedDefensiveFormation.THREE_FOUR_BASE] *= 1.2
            formations[UnifiedDefensiveFormation.NICKEL_DEFENSE] *= 0.6
            formations[UnifiedDefensiveFormation.DIME_DEFENSE] *= 0.3
        
        # Situational adjustments
        # NOTE: Kickoff logic removed - kickoffs handled at drive management level, not coordinator level
        
        if situation == 'red_zone':
            if self.defensive_situational.red_zone_goal_line_aggression > 0.6:
                # Use base defense as goal line equivalent
                formations[UnifiedDefensiveFormation.FOUR_THREE_BASE] *= 1.5
                
        elif situation == 'two_minute':
            # More sub packages in two-minute drill
            formations[UnifiedDefensiveFormation.NICKEL_DEFENSE] *= 1.2
            formations[UnifiedDefensiveFormation.DIME_DEFENSE] *= 1.4
            
        elif situation == 'third_and_long':
            # Pass-focused formations
            formations[UnifiedDefensiveFormation.NICKEL_DEFENSE] *= 1.3
            formations[UnifiedDefensiveFormation.DIME_DEFENSE] *= 1.5
            
        # NOTE: Fourth down special teams logic removed in new architecture
        # Fourth down PUNT and FIELD_GOAL decisions are now handled by SpecialTeamsCoordinator
        # Fourth down GO_FOR_IT decisions are handled here as regular conversion defense
        
        # Select highest weighted formation and return enum
        selected_enum = max(formations.items(), key=lambda x: x[1])[0]
        return selected_enum
    
    def get_coverage_scheme(self, formation: str, situation: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Select coverage scheme based on formation and situation
        
        Args:
            formation: Selected defensive formation
            situation: Game situation
            context: Additional context
        
        Returns:
            Coverage scheme details
        """
        if not context:
            context = {}
        
        # Base coverage preferences
        zone_weight = self.philosophy.zone_coverage_preference
        man_weight = self.philosophy.man_coverage_confidence
        
        # Default coverage selection
        primary_coverage = "Cover-1" if zone_weight > man_weight else "Man-to-Man"
        
        # Adjust based on situation
        if situation == 'red_zone':
            # Tighter coverage in red zone - prefer man coverage
            if man_weight > 0.4:
                primary_coverage = "Man-Free" if self.philosophy.safety_help_reliance > 0.6 else "Man-to-Man"
            else:
                primary_coverage = "Cover-2"  # Safe zone coverage
            
        elif situation == 'third_and_long':
            # Coverage based on DC philosophy
            if zone_weight > 0.6:
                primary_coverage = "Cover-3" if self.philosophy.safety_help_reliance > 0.6 else "Cover-2"
            else:
                primary_coverage = "Man-Free" if self.philosophy.safety_help_reliance > 0.6 else "Man-to-Man"
                
        elif situation == 'two_minute':
            # Prevent defense: only when PROTECTING a small lead (1-7 points)
            # Real NFL prevent = soft coverage to prevent big plays when ahead late
            score_differential = self._get_defensive_score_differential(context)

            # Prevent when: defending 1-7 point lead AND DC has prevent philosophy
            if (0 < score_differential <= 7 and
                    self.defensive_situational.prevent_defense_usage > 0.4):
                primary_coverage = "Prevent"
            else:
                # Not protecting small lead - use normal two-minute coverage
                primary_coverage = "Cover-2" if zone_weight > man_weight else "Man-Free"

        # NEW: Respond to opponent's game script
        override_pressure = None  # Track if we should override normal pressure logic
        game_context = context.get('game_context')
        if game_context:
            from ..mechanics.game_script_modifiers import GameScriptModifiers

            # Infer opponent's script (flip score differential)
            opponent_script = self._infer_opponent_script(game_context)

            defensive_response = GameScriptModifiers.get_defensive_response(
                opponent_script=opponent_script,
                prevent_defense_usage=self.defensive_situational.prevent_defense_usage
            )

            # Override coverage if prevent should be used
            if defensive_response.get('use_prevent'):
                primary_coverage = 'Prevent'
                override_pressure = False  # 3-man rush, drop 8 into coverage
            elif defensive_response.get('coverage_adjustment'):
                primary_coverage = defensive_response['coverage_adjustment']
                if defensive_response.get('pressure') is not None:
                    override_pressure = defensive_response.get('pressure')

        # NOTE: Special teams coverage logic removed in new architecture
        # Kickoff and special teams coverage now handled by SpecialTeamsCoordinator
        # Fourth down GO_FOR_IT coverage handled as regular conversion defense below

        # Add pressure considerations
        should_blitz = self._should_send_pressure(situation, context)

        # Apply game script pressure override if set
        if override_pressure is not None:
            should_blitz = override_pressure
        
        # NOTE: Special teams return logic removed in new architecture
        # All kickoff and special teams coverage handled by SpecialTeamsCoordinator
        
        # Standard return for regular defensive situations (1st-3rd down, or 4th down GO_FOR_IT)
        return {
            'primary_coverage': primary_coverage,
            'press_coverage': self.philosophy.press_coverage_aggression > 0.6,
            'safety_help': self.philosophy.safety_help_reliance > 0.5,
            'send_pressure': should_blitz,
            'coverage_confidence': zone_weight if 'Cover' in primary_coverage else man_weight
        }

    def _get_defensive_score_differential(self, context: Dict[str, Any]) -> int:
        """
        Get score differential from defense perspective (positive = winning).

        Args:
            context: Play calling context with raw_game_state or game_context

        Returns:
            Score differential (positive if defense is winning)
        """
        # Try raw_game_state first (from game_loop_controller)
        raw_state = context.get('raw_game_state', {})
        if raw_state:
            home_score = raw_state.get('home_score', 0)
            away_score = raw_state.get('away_score', 0)
            possessing_team_id = raw_state.get('possessing_team_id')
            home_team_id = raw_state.get('home_team_id')

            if possessing_team_id and home_team_id:
                # Offense is possessing - defense is the other team
                if possessing_team_id == home_team_id:
                    # Home team has ball -> defense is away team
                    return away_score - home_score
                else:
                    # Away team has ball -> defense is home team
                    return home_score - away_score

        # Fallback: try game_context
        game_context = context.get('game_context')
        if game_context and hasattr(game_context, 'score_differential'):
            # game_context.score_differential is from offense perspective
            # So defense perspective is the negative
            return -game_context.score_differential

        # Default: no lead (neutral)
        return 0

    def _infer_opponent_script(self, game_context):
        """
        Infer opponent's game script by flipping score differential.

        Args:
            game_context: Current GameContext

        Returns:
            Opponent's likely GameScript
        """
        from .game_situation_analyzer import GameSituationAnalyzer

        # Opponent's perspective = inverse of our differential
        flipped_differential = -game_context.score_differential

        # Use same logic as GameSituationAnalyzer
        return GameSituationAnalyzer._determine_game_script(
            flipped_differential,
            game_context.game_phase
        )

    def _should_send_pressure(self, situation: str, context: Dict[str, Any]) -> bool:
        """
        Determine if defense should send pressure (blitz more than 4-man rush).

        NFL Reality: Teams blitz on about 25-35% of passing plays.
        To achieve realistic sack distribution (63% DL, 28% LB, 9% DB), we need
        ~40-50% blitz rate since blitzes produce proportionally more sacks.

        Args:
            situation: Game situation
            context: Additional context

        Returns:
            True if should send pressure/blitz (more than 4 rushers)
        """
        import random

        # Base blitz rate boosted to achieve NFL sack distribution
        # Original philosophy.blitz_frequency is 0.2-0.8, we add 0.3 baseline
        base_blitz_rate = self.philosophy.blitz_frequency + 0.3

        # Situational adjustments
        if situation == 'third_down':
            pressure_rate = max(self.defensive_situational.third_down_pressure_rate, base_blitz_rate * 1.3)
        elif situation == 'two_minute':
            pressure_rate = self.defensive_situational.two_minute_drill_aggression
        elif situation == 'fourth_down':
            pressure_rate = max(self.defensive_situational.fourth_down_stop_aggression, base_blitz_rate * 1.5)
        else:
            pressure_rate = base_blitz_rate

        # Adjust based on field position
        field_position = context.get('field_position', 50)
        if field_position > 80:  # Opponent in red zone
            pressure_rate *= 1.2  # More aggressive when backed up
        elif field_position < 20:  # Opponent backed up
            pressure_rate *= self.defensive_situational.backed_up_defense_conservatism

        # Factor in coordinator aggression (scales from 0.7x to 1.1x - narrower range)
        adjusted_pressure_rate = pressure_rate * (0.7 + self.aggression * 0.4)

        # Cap at 80% to maintain some coverage plays
        adjusted_pressure_rate = min(0.8, adjusted_pressure_rate)

        # Probabilistic blitz decision
        return random.random() < adjusted_pressure_rate

    def select_blitz_package(self, situation: str, context: Dict[str, Any] = None):
        """
        Select a specific blitz package based on DC philosophy and situation.

        This replaces the simple boolean blitz decision with named blitz packages
        that define exactly WHO is rushing the passer, enabling:
        - DBs to get sacks when they blitz
        - LBs in coverage to NOT get sacks
        - Realistic sack attribution based on play call

        Args:
            situation: Game situation ('third_down', 'red_zone', 'two_minute', etc.)
            context: Additional context (field_position, etc.)

        Returns:
            BlitzPackageType enum value
        """
        from ..play_types.blitz_types import BlitzPackageType
        import random

        if not context:
            context = {}

        # First determine if we should blitz at all
        should_blitz = self._should_send_pressure(situation, context)

        if not should_blitz:
            # Not blitzing - choose between base 4-man rush or prevent
            coverage_scheme = context.get('coverage_scheme', {})
            primary_coverage = coverage_scheme.get('primary_coverage', '') if isinstance(coverage_scheme, dict) else ''

            if primary_coverage == 'Prevent' or situation == 'prevent':
                return BlitzPackageType.THREE_MAN_RUSH
            return BlitzPackageType.FOUR_MAN_BASE

        # Build weighted selection for blitz packages
        weights = self._calculate_blitz_weights(situation, context)

        # Weighted random selection
        packages = list(weights.keys())
        weight_values = list(weights.values())
        total_weight = sum(weight_values)

        if total_weight <= 0:
            return BlitzPackageType.MIKE_BLITZ  # Fallback

        normalized = [w / total_weight for w in weight_values]
        selected = random.choices(packages, weights=normalized, k=1)[0]

        return selected

    def _calculate_blitz_weights(self, situation: str, context: Dict[str, Any]) -> Dict:
        """
        Calculate probability weights for each blitz package.

        Uses DC philosophy traits:
        - creative_pressure_usage: Higher = more exotic packages (DB blitzes)
        - four_man_rush_confidence: Higher = fewer blitzes, simpler packages
        - aggression: Higher = more 6-man blitzes

        Args:
            situation: Game situation
            context: Additional context

        Returns:
            Dictionary of BlitzPackageType -> weight
        """
        from ..play_types.blitz_types import BlitzPackageType

        weights = {}

        # Get philosophy values
        creativity = self.philosophy.creative_pressure_usage
        four_man_confidence = self.philosophy.four_man_rush_confidence
        aggression = self.aggression

        # Base weights for standard LB blitzes (most common)
        # NFL Reality: ~28% of sacks come from LBs, so LB blitzes need to be very frequent
        # Lower four_man_confidence = more LB blitzes
        lb_blitz_factor = 1.0 - four_man_confidence

        # LB blitz weights significantly increased to achieve 28% LB sack target
        weights[BlitzPackageType.MIKE_BLITZ] = 150 * lb_blitz_factor + 50    # Was 100 * factor + 30
        weights[BlitzPackageType.SAM_BLITZ] = 100 * lb_blitz_factor + 35     # Was 70 * factor + 20
        weights[BlitzPackageType.WILL_BLITZ] = 100 * lb_blitz_factor + 35    # Was 70 * factor + 20
        weights[BlitzPackageType.OLB_BLITZ] = 130 * lb_blitz_factor + 45     # Was 90 * factor + 25
        weights[BlitzPackageType.A_GAP_BLITZ] = 120 * lb_blitz_factor + 40   # Was 80 * factor + 20

        # 6-man blitzes (LB heavy) - increased frequency
        if aggression > 0.4:  # Lowered threshold from 0.5
            weights[BlitzPackageType.DOUBLE_A_GAP] = 60 * aggression   # Was 40
            weights[BlitzPackageType.DOUBLE_LB] = 50 * aggression      # Was 35

        # DB blitzes require moderate creativity (exotic packages)
        # NFL Reality: ~9% of sacks come from DBs - reduced to balance LB increase
        if creativity >= 0.3:
            weights[BlitzPackageType.CORNER_BLITZ] = creativity * 60 + 12    # Was creativity * 100 + 20
            weights[BlitzPackageType.SAFETY_BLITZ] = creativity * 70 + 15    # Was creativity * 120 + 25
            weights[BlitzPackageType.NICKEL_BLITZ] = creativity * 50 + 10    # Was creativity * 80 + 15

        # Ultra-exotic packages (LB+DB combos)
        if creativity >= 0.4:  # Lowered threshold
            weights[BlitzPackageType.ZONE_DOG] = creativity * 50 + 10
            weights[BlitzPackageType.FIRE_ZONE] = creativity * 50 + 10
            weights[BlitzPackageType.LB_DB_COMBO] = creativity * aggression * 60 + 10

        # Cover-0/Double safety - aggressive DBs blitzing
        if aggression > 0.5 and creativity > 0.4:
            weights[BlitzPackageType.COVER_0_BLITZ] = aggression * creativity * 50 + 10
            weights[BlitzPackageType.DOUBLE_SAFETY] = aggression * creativity * 40 + 8

        # Situational adjustments
        if situation == 'third_down' or situation == 'third_and_long':
            # More aggressive on third down
            for pkg in [BlitzPackageType.CORNER_BLITZ, BlitzPackageType.COVER_0_BLITZ]:
                if pkg in weights:
                    weights[pkg] *= 1.5

        elif situation == 'red_zone':
            # A-gap blitzes effective in tight spaces
            weights[BlitzPackageType.A_GAP_BLITZ] *= 1.5
            weights[BlitzPackageType.DOUBLE_A_GAP] = weights.get(BlitzPackageType.DOUBLE_A_GAP, 0) * 1.5

        elif situation == 'fourth_down':
            # All-out pressure on 4th down
            for pkg in [BlitzPackageType.COVER_0_BLITZ, BlitzPackageType.DOUBLE_SAFETY]:
                if pkg in weights:
                    weights[pkg] *= 2.0
            # Add Cover-0 even for less aggressive DCs on 4th down
            if BlitzPackageType.COVER_0_BLITZ not in weights:
                weights[BlitzPackageType.COVER_0_BLITZ] = 15 * aggression

        # Ensure all weights are positive
        return {k: max(0.1, v) for k, v in weights.items() if v > 0}

    def get_personnel_package(self, offensive_personnel: str, situation: str) -> str:
        """
        Select defensive personnel package to match offensive personnel
        
        Args:
            offensive_personnel: Offensive personnel package (e.g., "11", "12", "21")
            situation: Game situation
        
        Returns:
            Defensive personnel package description
        """
        # Base personnel matching
        personnel_map = {
            '11': 'Base Nickel',    # 3 WR -> 5 DB
            '12': 'Base Defense',   # 2 WR -> 4 DB  
            '21': 'Heavy Defense',  # 2 WR, 2 RB -> Run stuffing
            '10': 'Dime Package',   # 4 WR -> 6 DB
        }
        
        base_package = personnel_map.get(offensive_personnel, 'Base Defense')
        
        # Adjust based on situation and preferences
        if situation in ['red_zone', 'goal_line']:
            if self.personnel.goal_line_personnel_aggression > 0.6:
                return 'Goal Line Defense'  # Extra big bodies
                
        elif situation == 'two_minute':
            if self.personnel.dime_package_usage > 0.5:
                return 'Dime Package'  # More DBs for passing situations
        
        # Apply coordinator preferences
        if base_package == 'Base Nickel' and self.personnel.nickel_package_comfort < 0.5:
            return 'Base Defense'  # Fall back to base if uncomfortable with sub packages
        
        return base_package
    
    def evaluate_head_coach_influence(self, hc_influence: float, situation: str) -> float:
        """
        Evaluate how head coach influence affects defensive calling
        
        Args:
            hc_influence: Head coach influence level (0.0-1.0)
            situation: Current situation
        
        Returns:
            Adjusted influence factor for this coordinator
        """
        # Base acceptance of head coach input
        acceptance = self.adaptability * 0.6 + (1.0 - self.conservatism) * 0.4
        
        # Defensive coordinators are often more autonomous
        autonomy_factor = 0.8  # DCs typically have more independence
        
        # In critical defensive situations, accept more input
        critical_defensive_situations = ['red_zone', 'fourth_down', 'two_minute']
        if situation in critical_defensive_situations:
            acceptance *= 1.2  # More willing to coordinate in critical moments
        
        # Return effective influence
        return hc_influence * acceptance * autonomy_factor
    
    def _predict_opponent_fourth_down_decision(self, context: Dict[str, Any]) -> 'FourthDownDecisionType':
        """
        Predict what the opponent is likely to do on 4th down
        
        Uses same FourthDownMatrix logic to scout opponent tendencies
        
        Args:
            context: Game context with field position, downs, etc.
        
        Returns:
            FourthDownDecisionType enum value
        """
        from .fourth_down_matrix import FourthDownMatrix, FourthDownDecisionType
        
        # Extract situation details
        field_position = context.get('field_position', 50)
        yards_to_go = context.get('yards_to_go', 10) 
        score_differential = context.get('score_differential', 0)
        time_remaining = context.get('time_remaining', 900)
        quarter = context.get('quarter', 4)
        
        # Estimate opponent coach aggression (could be enhanced with scouting data)
        opponent_aggression = self._estimate_opponent_aggression(context)
        
        # Use matrix to predict opponent's decision
        decision = FourthDownMatrix.calculate_fourth_down_decision(
            field_position=field_position,
            yards_to_go=yards_to_go,
            score_differential=-score_differential,  # Flip perspective
            time_remaining=time_remaining,
            quarter=quarter,
            coach_aggression=opponent_aggression
        )
        
        return decision.recommendation
    
    def _estimate_opponent_aggression(self, context: Dict[str, Any]) -> 'CoachAggressionLevel':
        """
        Estimate opponent coach aggression level
        
        In a complete system, this would use scouting data.
        For now, use league average with contextual adjustments.
        
        Args:
            context: Game context
        
        Returns:
            CoachAggressionLevel enum value
        """
        from .fourth_down_matrix import CoachAggressionLevel
        
        # Start with balanced baseline (league average)
        base_aggression = CoachAggressionLevel.BALANCED
        
        # Adjust based on game context (teams get more aggressive when desperate)
        score_differential = context.get('score_differential', 0) 
        time_remaining = context.get('time_remaining', 900)
        
        # If opponent is behind late, assume more aggressive
        if score_differential > 7 and time_remaining < 600:  # Down by 7+ in final 10 min
            return CoachAggressionLevel.AGGRESSIVE
        elif score_differential > 14 and time_remaining < 900:  # Down by 14+ in 4th Q
            return CoachAggressionLevel.ULTRA_AGGRESSIVE
        # If opponent has big lead, assume conservative  
        elif score_differential < -14:  # Up by 14+
            return CoachAggressionLevel.CONSERVATIVE
        
        return base_aggression
    
    # NOTE: _predict_opponent_kickoff_decision method removed in new architecture
    # Kickoff decisions handled at drive management level, not coordinator level
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert defensive coordinator to dictionary for JSON serialization"""
        base_dict = super().to_dict()
        
        # Add defensive coordinator specific data
        base_dict['coach_type'] = self.coach_type.value
        base_dict['philosophy'] = {
            'four_three_preference': self.philosophy.four_three_preference,
            'three_four_preference': self.philosophy.three_four_preference,
            'nickel_heavy_preference': self.philosophy.nickel_heavy_preference,
            'zone_coverage_preference': self.philosophy.zone_coverage_preference,
            'man_coverage_confidence': self.philosophy.man_coverage_confidence,
            'press_coverage_aggression': self.philosophy.press_coverage_aggression,
            'safety_help_reliance': self.philosophy.safety_help_reliance,
            'blitz_frequency': self.philosophy.blitz_frequency,
            'creative_pressure_usage': self.philosophy.creative_pressure_usage,
            'four_man_rush_confidence': self.philosophy.four_man_rush_confidence,
            'timing_blitz_mastery': self.philosophy.timing_blitz_mastery,
        }
        base_dict['personnel'] = {
            'base_defense_reliance': self.personnel.base_defense_reliance,
            'nickel_package_comfort': self.personnel.nickel_package_comfort,
            'dime_package_usage': self.personnel.dime_package_usage,
            'goal_line_personnel_aggression': self.personnel.goal_line_personnel_aggression,
            'edge_rusher_rotation': self.personnel.edge_rusher_rotation,
            'linebacker_versatility': self.personnel.linebacker_versatility,
            'safety_flexibility': self.personnel.safety_flexibility,
            'cornerback_shadowing': self.personnel.cornerback_shadowing,
        }
        base_dict['situational'] = {
            'first_down_aggression': self.defensive_situational.first_down_aggression,
            'second_and_long_creativity': self.defensive_situational.second_and_long_creativity,
            'third_down_pressure_rate': self.defensive_situational.third_down_pressure_rate,
            'red_zone_goal_line_aggression': self.defensive_situational.red_zone_goal_line_aggression,
            'red_zone_coverage_tightness': self.defensive_situational.red_zone_coverage_tightness,
            'backed_up_defense_conservatism': self.defensive_situational.backed_up_defense_conservatism,
            'prevent_defense_usage': self.defensive_situational.prevent_defense_usage,
            'two_minute_drill_aggression': self.defensive_situational.two_minute_drill_aggression,
            'fourth_down_stop_aggression': self.defensive_situational.fourth_down_stop_aggression,
        }
        base_dict['preferred_defensive_playbooks'] = self.preferred_defensive_playbooks.copy()
        
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DefensiveCoordinator':
        """Create DefensiveCoordinator from dictionary (JSON loading)"""
        # Extract specialized data
        philosophy_data = data.get('philosophy', {})
        personnel_data = data.get('personnel', {})
        situational_data = data.get('situational', {})
        preferred_playbooks = data.get('preferred_defensive_playbooks', ['balanced_defense'])
        
        # Use base class method for common traits
        base_coach = BaseCoachArchetype.from_dict(data)
        
        # Create defensive coordinator with specialized traits
        return cls(
            name=base_coach.name,
            description=base_coach.description,
            coach_type=CoachType.DEFENSIVE_COORDINATOR,
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
            philosophy=DefensivePhilosophy(**philosophy_data),
            personnel=PersonnelUsage(**personnel_data),
            defensive_situational=SituationalDefense(**situational_data),
            preferred_defensive_playbooks=preferred_playbooks,
        )