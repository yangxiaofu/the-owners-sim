"""
NFL 2024 Dynamic Kickoff simulation with comprehensive penalty integration

Implements enhanced four-phase simulation with NFL realism:
1. Pre-kick setup validation and penalty detection
2. Kick execution with hang time and landing zone determination  
3. Post-kick coverage/return interaction simulation
4. Final resolution with comprehensive player statistics attribution
"""

import random
import math
from typing import List, Tuple, Dict, Optional, Union
from enum import Enum
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext
from ..play_types.base_types import PlayType
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config


class KickoffPlayParams:
    """Input parameters for kickoff simulator - received from external play calling systems"""
    
    def __init__(self, kickoff_type: str, defensive_formation: str, context: PlayContext):
        """
        Initialize kickoff play parameters
        
        Args:
            kickoff_type: Type of kickoff attempt ("regular_kickoff", "onside_kick", "squib_kick")
            defensive_formation: String formation name (like run/pass plays)
            context: PlayContext with game situation information
        """
        # Store string formation directly (like run/pass plays do)
        self.kickoff_type = kickoff_type
        self.defensive_formation = defensive_formation  # Store string, not enum
        self.context = context
    
    def get_defensive_formation_name(self) -> str:
        """Get the defensive formation name (already a string)"""
        return self.defensive_formation


class KickoffOutcome(Enum):
    """Possible kickoff outcomes"""
    TOUCHBACK_END_ZONE = "touchback_end_zone"           # 30-yard line
    TOUCHBACK_LANDING_ZONE = "touchback_landing_zone"   # 20-yard line
    REGULAR_RETURN = "regular_return"                   # Normal return
    ONSIDE_RECOVERY = "onside_recovery"                 # Kicking team recovers onside
    ONSIDE_FAILED = "onside_failed"                     # Receiving team recovers onside
    OUT_OF_BOUNDS = "out_of_bounds"                     # 40-yard line or spot
    SHORT_KICK = "short_kick"                           # 40-yard line penalty
    RETURN_TOUCHDOWN = "return_touchdown"               # Full return for TD
    FUMBLE_RECOVERY = "fumble_recovery"                 # Fumble on return
    PENALTY_NEGATED = "penalty_negated"                 # Play negated by penalty


class KickoffResult:
    """Result data structure for kickoff attempts"""
    
    def __init__(self, outcome: KickoffOutcome, yards_gained: int = 0, 
                 points_scored: int = 0, field_position: int = 25):
        self.outcome = outcome
        self.yards_gained = yards_gained  # Return yardage (0 for touchbacks)
        self.points_scored = points_scored  # 6 for return TD
        self.field_position = field_position  # Where receiving team starts
        self.time_elapsed = 0.0
        
        # Kick details
        self.kick_distance = 0
        self.hang_time = 0.0
        self.landing_zone = None
        self.is_onside = False
        
        # Individual player stats
        self.player_stats = {}
        self.penalty_occurred = False
        self.penalty_instance = None
        self.original_outcome = None


class PreKickResult:
    """Result of pre-kick phase validation"""
    
    def __init__(self, is_valid: bool, penalty_occurred: bool = False, 
                 penalty_instance: Optional[PenaltyInstance] = None):
        self.is_valid = is_valid
        self.penalty_occurred = penalty_occurred
        self.penalty_instance = penalty_instance
        self.is_onside_declared = False


class KickExecution:
    """Result of kick execution phase"""
    
    def __init__(self, distance: int, hang_time: float, landing_zone: str,
                 directional_accuracy: float, is_onside: bool = False):
        self.distance = distance
        self.hang_time = hang_time
        self.landing_zone = landing_zone  # "end_zone", "landing_zone", "short", "out_of_bounds"
        self.directional_accuracy = directional_accuracy
        self.is_onside = is_onside
        self.kick_angle = 0.0  # Degrees left/right of center


class KickoffSimulator:
    """Simulates NFL 2024 Dynamic Kickoff with comprehensive penalty integration and individual player attribution"""

    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str,
                 offensive_team_id: int = None, defensive_team_id: int = None):
        """
        Initialize kickoff simulator

        Args:
            offensive_players: List of 11 kicking team Player objects
            defensive_players: List of 11 receiving team Player objects
            offensive_formation: Offensive formation (typically "KICKOFF")
            defensive_formation: Defensive formation ("KICKOFF_RETURN")
            offensive_team_id: Team ID for the kicking team
            defensive_team_id: Team ID for the receiving team
        """
        self.kicking_team = offensive_players
        self.receiving_team = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id

        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()
        
        # Load kickoff configuration
        self.kickoff_config = config.get_kickoff_config()
        
        # Identify key special teams players
        self._identify_special_teams_players()
    
    def _identify_special_teams_players(self):
        """Identify key players in kickoff units"""
        self.kicker = None
        self.coverage_unit = []
        self.returners = []
        self.return_blockers = []
        
        # Identify kicking team players
        for player in self.kicking_team:
            if hasattr(player, 'primary_position'):
                if player.primary_position == Position.K:
                    self.kicker = player
                else:
                    self.coverage_unit.append(player)
        
        # Identify receiving team players  
        for player in self.receiving_team:
            if hasattr(player, 'primary_position'):
                if player.primary_position in [Position.WR, Position.RB, Position.CB]:
                    # Potential returners (usually WRs, RBs, or CBs)
                    if len(self.returners) < 2:  # Max 2 returners per 2024 rules
                        self.returners.append(player)
                    else:
                        self.return_blockers.append(player)
                else:
                    self.return_blockers.append(player)
        
        # Fallback assignments
        if not self.kicker:
            self.kicker = self.kicking_team[0]
        if not self.coverage_unit:
            self.coverage_unit = self.kicking_team[1:]
        if not self.returners:
            self.returners = self.receiving_team[:2]
        if not self.return_blockers:
            self.return_blockers = self.receiving_team[2:]
    
    def simulate_kickoff_play(self, kickoff_params: Optional[KickoffPlayParams] = None, context: Optional[PlayContext] = None) -> KickoffResult:
        """
        Main simulation method for kickoff attempts
        
        Args:
            kickoff_params: KickoffPlayParams with validated enum formations (preferred method)
            context: PlayContext with game situation information (fallback for backward compatibility)
            
        Returns:
            KickoffResult with comprehensive outcome information
        """
        # Handle both new enum-based params and legacy string-based context
        if kickoff_params is not None:
            # ✅ NEW: Use validated enum from KickoffPlayParams
            defensive_formation_name = kickoff_params.get_defensive_formation_name()
            context = kickoff_params.context
        else:
            # ✅ LEGACY: Fallback to string-based formation for backward compatibility
            defensive_formation_name = self.defensive_formation
            if context is None:
                context = PlayContext(
                    play_type="kickoff",
                    offensive_formation=self.offensive_formation,
                    defensive_formation=self.defensive_formation
                )
        
        # Phase 1: Pre-kick setup validation and penalty detection
        pre_kick_result = self._execute_pre_kick_phase(context)
        if pre_kick_result.penalty_occurred:
            return self._resolve_pre_kick_penalty(pre_kick_result, context)
        
        # Phase 2: Kick execution mechanics
        kick_execution = self._execute_kick_phase(context, pre_kick_result)
        
        # Phase 3: Post-kick coverage and return simulation
        coverage_result = self._execute_post_kick_phase(kick_execution, context)
        
        # Phase 4: Final resolution and comprehensive statistics
        return self._resolve_final_outcome(coverage_result, kick_execution, context)
    
    def _execute_pre_kick_phase(self, context: PlayContext) -> PreKickResult:
        """
        Phase 1: Validate formation alignment and check for pre-kick penalties
        
        Args:
            context: Game situation context
            
        Returns:
            PreKickResult with validation status and any penalties
        """
        penalties_config = self.kickoff_config.get('pre_kick_penalties', {})
        
        # Check for various pre-kick penalties
        for penalty_type, penalty_data in penalties_config.items():
            # Skip non-dictionary items like "description"
            if not isinstance(penalty_data, dict):
                continue
                
            base_rate = penalty_data.get('base_rate', 0.01)
            
            # Adjust penalty rate based on game situation
            adjusted_rate = self._adjust_penalty_rate(base_rate, context)
            
            if random.random() < adjusted_rate:
                # Create penalty instance
                penalty_instance = PenaltyInstance(
                    penalty_type=penalty_type,
                    penalized_player_name="Unknown Player",
                    penalized_player_number=0,
                    penalized_player_position="unknown",
                    team_penalized="offense" if penalty_type in ['delay_of_game', 'false_start'] else "defense",
                    yards_assessed=penalty_data.get('penalty_yards', 5),
                    automatic_first_down=False,
                    automatic_loss_of_down=False,
                    negated_play=False,
                    quarter=context.quarter if context else 1,
                    time_remaining=context.time_remaining if context else "15:00",
                    down=1,
                    distance=10,
                    field_position=50,
                    score_differential=context.score_differential if context else 0,
                    penalty_timing="pre_kick"
                )
                return PreKickResult(False, True, penalty_instance)
        
        # Check if this is a declared onside kick (4th quarter, trailing)
        is_onside_declared = self._determine_onside_declaration(context)
        
        result = PreKickResult(True)
        result.is_onside_declared = is_onside_declared
        return result
    
    def _execute_kick_phase(self, context: PlayContext, pre_kick: PreKickResult) -> KickExecution:
        """
        Phase 2: Execute the actual kick with realistic physics
        
        Args:
            context: Game situation context
            pre_kick: Result of pre-kick phase
            
        Returns:
            KickExecution with kick details
        """
        # Determine if this is an onside kick attempt
        is_onside = pre_kick.is_onside_declared or self._should_surprise_onside(context)
        
        if is_onside:
            return self._execute_onside_kick(context)
        else:
            return self._execute_regular_kick(context)
    
    def _execute_regular_kick(self, context: PlayContext) -> KickExecution:
        """Execute a regular kickoff"""
        kick_config = self.kickoff_config.get('kick_mechanics', {})
        
        # Get kicker tier and associated parameters
        kicker_tier = self._get_kicker_tier()
        tier_config = kick_config.get('kicker_tiers', {}).get(kicker_tier, {})
        
        # Calculate kick distance with variance
        avg_distance = tier_config.get('avg_distance', 61)
        distance_variance = tier_config.get('distance_variance', 10)
        kick_distance = max(30, int(random.gauss(avg_distance, distance_variance)))
        
        # Calculate hang time
        hang_time_config = kick_config.get('hang_time', {})
        base_hang_time = hang_time_config.get('base_time_seconds', 4.2)
        distance_mod = hang_time_config.get('distance_modifier', -0.015)
        tier_bonus = tier_config.get('hang_time_bonus', 0.0)
        
        hang_time = base_hang_time + (distance_mod * (kick_distance - 60)) + tier_bonus
        hang_time = max(3.5, min(5.0, hang_time))
        
        # Determine directional accuracy
        directional_accuracy = tier_config.get('directional_accuracy', 0.78)
        
        # Determine landing zone based on distance
        landing_zone = self._determine_landing_zone(kick_distance)
        
        return KickExecution(kick_distance, hang_time, landing_zone, directional_accuracy)
    
    def _execute_onside_kick(self, context: PlayContext) -> KickExecution:
        """Execute an onside kick attempt"""
        onside_config = self.kickoff_config.get('onside_kick_mechanics', {})
        execution_config = onside_config.get('execution_parameters', {})
        
        # Onside kicks have different characteristics
        avg_distance = execution_config.get('avg_distance', 15)
        distance_variance = execution_config.get('distance_variance', 8)
        kick_distance = max(10, int(random.gauss(avg_distance, distance_variance)))
        
        # Shorter hang time for onside kicks
        hang_time = random.uniform(1.8, 3.5)
        
        # Lower directional accuracy due to intentional bouncing
        directional_accuracy = 0.6
        
        # Onside kicks land in "short" zone by design
        landing_zone = "onside_zone"
        
        return KickExecution(kick_distance, hang_time, landing_zone, directional_accuracy, True)
    
    def _execute_post_kick_phase(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """
        Phase 3: Simulate coverage team pursuit and return team execution
        
        Args:
            kick: Result of kick execution
            context: Game situation context
            
        Returns:
            Preliminary KickoffResult (before final resolution)
        """
        if kick.is_onside:
            return self._simulate_onside_recovery(kick, context)
        
        # Determine initial outcome based on landing zone
        if kick.landing_zone == "end_zone":
            return self._resolve_end_zone_outcome(kick, context)
        elif kick.landing_zone == "out_of_bounds":
            return self._resolve_out_of_bounds(kick, context)
        elif kick.landing_zone == "short":
            return self._resolve_short_kick(kick, context)
        else:
            # Regular return scenario
            return self._simulate_return_attempt(kick, context)
    
    def _simulate_return_attempt(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """Simulate a regular kickoff return"""
        # Get coverage and return team effectiveness
        coverage_effectiveness = self._get_coverage_effectiveness(kick.hang_time)
        return_effectiveness = self._get_return_effectiveness()
        
        # Determine returner decision (kneel vs return)
        return_config = self.kickoff_config.get('return_mechanics', {})
        returner_decisions = return_config.get('returner_decisions', {})
        
        # If kick reaches end zone, high probability of kneeling
        if kick.landing_zone == "end_zone_edge":
            kneel_prob = returner_decisions.get('end_zone_kneel_probability', 0.87)
            if random.random() < kneel_prob:
                return KickoffResult(KickoffOutcome.TOUCHBACK_LANDING_ZONE, 0, 0, 20)
        
        # Execute return attempt
        return_outcomes = return_config.get('return_outcomes', {})
        base_return = return_outcomes.get('base_return_average', 24)
        variance = return_outcomes.get('variance', 12)
        
        # Calculate actual return yardage with team effectiveness
        coverage_factor = 1.0 - (coverage_effectiveness - 0.7) * 0.5  # Normalize around 0.7
        return_factor = 1.0 + (return_effectiveness - 0.7) * 0.4
        
        raw_return = random.gauss(base_return, variance)
        final_return = max(0, int(raw_return * coverage_factor * return_factor))
        
        # Check for special outcomes
        big_return_threshold = return_outcomes.get('big_return_threshold', 40)
        big_return_prob = return_outcomes.get('big_return_probability', 0.085)
        td_prob = return_outcomes.get('touchdown_return_probability', 0.008)
        fumble_prob = return_outcomes.get('fumble_probability', 0.012)
        
        # Fumble check
        if random.random() < fumble_prob:
            # Determine fumble recovery
            if random.random() < 0.45:  # 45% chance kicking team recovers
                return KickoffResult(KickoffOutcome.FUMBLE_RECOVERY, 0, 0, 
                                   max(20, 100 - kick.distance + final_return))
        
        # Touchdown check
        kick_to_endzone_distance = 100 - kick.distance + 17  # From goalline
        if final_return >= kick_to_endzone_distance and random.random() < td_prob:
            return KickoffResult(KickoffOutcome.RETURN_TOUCHDOWN, final_return, 6, 100)
        
        # Calculate final field position
        kick_landing_spot = 100 - kick.distance + 17  # Approximate field position
        final_position = min(99, kick_landing_spot + final_return)
        
        return KickoffResult(KickoffOutcome.REGULAR_RETURN, final_return, 0, final_position)
    
    def _simulate_onside_recovery(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """Simulate onside kick recovery attempt"""
        onside_config = self.kickoff_config.get('onside_kick_mechanics', {})
        recovery_probs = onside_config.get('recovery_probabilities', {})
        
        # Different success rates for declared vs surprise onside
        if hasattr(context, 'is_onside_declared') and context.is_onside_declared:
            recovery_rate = recovery_probs.get('declared_onside', 0.25)
        else:
            recovery_rate = recovery_probs.get('surprise_onside', 0.65)
        
        # Check if kicking team recovers
        if random.random() < recovery_rate:
            # Kicking team recovers - they get possession
            recovery_spot = 50 + kick.distance  # Approximate recovery location
            return KickoffResult(KickoffOutcome.ONSIDE_RECOVERY, 0, 0, recovery_spot)
        else:
            # Receiving team recovers
            recovery_spot = 50 + kick.distance
            return KickoffResult(KickoffOutcome.ONSIDE_FAILED, 0, 0, recovery_spot)
    
    def _resolve_end_zone_outcome(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """Resolve kicks that reach the end zone"""
        # 2024 rule: End zone touchbacks go to 30-yard line
        return KickoffResult(KickoffOutcome.TOUCHBACK_END_ZONE, 0, 0, 30)
    
    def _resolve_out_of_bounds(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """Resolve out of bounds kicks"""
        # 2024 rule: Out of bounds = 40-yard line or spot of out of bounds
        return KickoffResult(KickoffOutcome.OUT_OF_BOUNDS, 0, 0, 40)
    
    def _resolve_short_kick(self, kick: KickExecution, context: PlayContext) -> KickoffResult:
        """Resolve kicks that don't reach landing zone"""
        # 2024 rule: Short kicks = 40-yard line penalty
        return KickoffResult(KickoffOutcome.SHORT_KICK, 0, 0, 40)
    
    def _resolve_final_outcome(self, coverage_result: KickoffResult, 
                             kick_execution: KickExecution, context: PlayContext) -> KickoffResult:
        """
        Phase 4: Final resolution with penalty checks and player statistics
        
        Args:
            coverage_result: Result from coverage/return phase
            kick_execution: Details of the kick
            context: Game situation context
            
        Returns:
            Final KickoffResult with all details
        """
        # Check for post-kick penalties if this was a return
        if coverage_result.outcome == KickoffOutcome.REGULAR_RETURN:
            penalty_result = self._check_post_kick_penalties(coverage_result, context)
            if penalty_result.penalty_occurred:
                coverage_result.penalty_occurred = True
                coverage_result.penalty_instance = penalty_result.penalty_instance
                coverage_result.original_outcome = coverage_result.outcome
                
                # Apply penalty effects
                coverage_result = self._apply_penalty_effects(coverage_result, penalty_result)
        
        # Set kick execution details
        coverage_result.kick_distance = kick_execution.distance
        coverage_result.hang_time = kick_execution.hang_time
        coverage_result.landing_zone = kick_execution.landing_zone
        coverage_result.is_onside = kick_execution.is_onside
        
        # Set play timing
        timing_config = self.kickoff_config.get('play_timing', {}).get('total_play_time', {})
        if coverage_result.outcome in [KickoffOutcome.TOUCHBACK_END_ZONE, KickoffOutcome.TOUCHBACK_LANDING_ZONE]:
            timing = timing_config.get('touchback', {'min': 4.0, 'max': 6.5})
        elif coverage_result.is_onside:
            timing = timing_config.get('onside_kick', {'min': 3.5, 'max': 8.0})
        else:
            timing = timing_config.get('regular_return', {'min': 6.5, 'max': 12.0})
        
        coverage_result.time_elapsed = random.uniform(timing['min'], timing['max'])
        
        # Attribute individual player statistics
        self._attribute_player_statistics(coverage_result, context)
        
        return coverage_result
    
    def _check_post_kick_penalties(self, result: KickoffResult, context: PlayContext) -> PenaltyResult:
        """Check for penalties during coverage and return phases"""
        penalties_config = self.kickoff_config.get('post_kick_penalties', {})
        
        # Combine coverage and return team penalties
        all_penalties = {}
        all_penalties.update(penalties_config.get('coverage_team_penalties', {}))
        all_penalties.update(penalties_config.get('return_team_penalties', {}))
        
        for penalty_type, penalty_data in all_penalties.items():
            # Skip non-dictionary items like "description"
            if not isinstance(penalty_data, dict):
                continue
                
            base_rate = penalty_data.get('base_rate', 0.01)
            
            # Apply situational modifiers
            situational_mods = penalties_config.get('situational_modifiers', {})
            if result.yards_gained > 30:  # Big return
                base_rate *= (1 + situational_mods.get('big_return_penalty_bonus', 0.25))
            
            if random.random() < base_rate:
                # Penalty occurred
                penalty_instance = PenaltyInstance(
                    penalty_type=penalty_type,
                    penalized_player_name="Unknown Player",
                    penalized_player_number=0,
                    penalized_player_position="unknown",
                    team_penalized="offense" if penalty_type in penalties_config.get('coverage_team_penalties', {}) else "defense",
                    yards_assessed=penalty_data.get('penalty_yards', 10),
                    automatic_first_down=penalty_data.get('automatic_first_down', False),
                    automatic_loss_of_down=False,
                    negated_play=False,
                    quarter=getattr(result, 'quarter', 1),
                    time_remaining=getattr(result, 'time_remaining', "15:00"),
                    down=1,
                    distance=10,
                    field_position=result.field_position if hasattr(result, 'field_position') else 50,
                    score_differential=getattr(result, 'score_differential', 0),
                    penalty_timing="post_kick"
                )
                
                return PenaltyResult(
                    penalty_occurred=True,
                    penalty_instance=penalty_instance,
                    modified_yards=result.yards_gained,  # Will be modified by _apply_penalty_effects
                    play_negated=False
                )
        
        return PenaltyResult(False, None, result.yards_gained, False)
    
    def _apply_penalty_effects(self, result: KickoffResult, penalty: PenaltyResult) -> KickoffResult:
        """Apply penalty effects to the kickoff result"""
        penalty_data = penalty.penalty_instance
        
        # Apply penalty from end of play (standard for kickoff penalties)
        if penalty_data.team_penalized == "offense":  # Coverage team
            # Penalty helps return team
            result.field_position = min(99, result.field_position + penalty_data.yards_assessed)
        else:  # Return team
            # Penalty hurts return team
            result.field_position = max(1, result.field_position - penalty_data.yards_assessed)
        
        return result
    
    def _attribute_player_statistics(self, result: KickoffResult, context: PlayContext):
        """Attribute individual player statistics based on kickoff outcome"""
        result.player_stats = {}
        
        # Kicker statistics
        if self.kicker:
            kicker_stats = create_player_stats_from_player(self.kicker, self.offensive_team_id)
            kicker_stats.kickoff_attempts = 1
            
            if result.outcome in [KickoffOutcome.TOUCHBACK_END_ZONE, KickoffOutcome.TOUCHBACK_LANDING_ZONE]:
                kicker_stats.touchbacks = 1
            elif result.outcome == KickoffOutcome.ONSIDE_RECOVERY:
                kicker_stats.onside_recoveries = 1
            
            result.player_stats[self.kicker.name] = kicker_stats
        
        # Coverage team statistics
        for player in self.coverage_unit:
            coverage_stats = create_player_stats_from_player(player, self.offensive_team_id)
            coverage_stats.special_teams_snaps = 1
            
            if result.outcome == KickoffOutcome.REGULAR_RETURN:
                # Randomly assign tackle credit
                if random.random() < 0.15:  # 15% chance any coverage player gets tackle
                    coverage_stats.tackles = 1
            
            result.player_stats[player.name] = coverage_stats
        
        # Returner statistics
        if result.outcome == KickoffOutcome.REGULAR_RETURN and self.returners:
            returner = self.returners[0]  # Primary returner
            returner_stats = create_player_stats_from_player(returner, self.defensive_team_id)
            returner_stats.kickoff_returns = 1
            returner_stats.kickoff_return_yards = result.yards_gained
            
            if result.outcome == KickoffOutcome.RETURN_TOUCHDOWN:
                returner_stats.kickoff_return_touchdowns = 1
            
            result.player_stats[returner.name] = returner_stats
        
        # Return blocking unit statistics
        for player in self.return_blockers:
            blocker_stats = create_player_stats_from_player(player, self.defensive_team_id)
            blocker_stats.special_teams_snaps = 1
            result.player_stats[player.name] = blocker_stats

        # Track special teams snaps for ALL 22 players on the field
        self._track_special_teams_snaps_for_all_players(result)

    def _track_special_teams_snaps_for_all_players(self, result):
        """
        Track special teams snaps for ALL 22 players on the field during this kickoff play

        Args:
            result: KickoffResult object with player_stats dictionary
        """
        # Track special teams snaps for all 11 offensive players (kickoff unit)
        for player in self.offensive_players:
            player_name = player.name
            if player_name in result.player_stats:
                # Player already has stats object, just add the snap
                result.player_stats[player_name].add_special_teams_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, self.offensive_team_id)
                new_stats.add_special_teams_snap()
                result.player_stats[player_name] = new_stats

        # Track special teams snaps for all 11 defensive players (kickoff return unit)
        for player in self.defensive_players:
            player_name = player.name
            if player_name in result.player_stats:
                # Player already has stats object, just add the snap
                result.player_stats[player_name].add_special_teams_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, self.defensive_team_id)
                new_stats.add_special_teams_snap()
                result.player_stats[player_name] = new_stats

    # Helper methods
    def _get_kicker_tier(self) -> str:
        """Determine kicker tier based on attributes"""
        if not self.kicker or not hasattr(self.kicker, 'get_rating'):
            return 'average'
        
        kicker_rating = self.kicker.get_rating('kicking_power')
        tiers = self.kickoff_config.get('kick_mechanics', {}).get('kicker_tiers', {})
        
        for tier_name, tier_config in tiers.items():
            if kicker_rating >= tier_config.get('rating_threshold', 70):
                return tier_name
        
        return 'poor'
    
    def _determine_landing_zone(self, distance: int) -> str:
        """Determine where kick lands based on distance"""
        if distance >= 75:  # Deep into end zone
            return "end_zone"
        elif distance >= 65:  # End zone edge
            return "end_zone_edge"  
        elif distance >= 45:  # Landing zone (20-goal line)
            return "landing_zone"
        elif distance >= 35:  # Short of landing zone
            return "short"
        else:  # Very short
            return "short"
    
    def _determine_onside_declaration(self, context: PlayContext) -> bool:
        """Determine if team should declare onside kick based on 2024 rules"""
        # 2024 rule: Must declare onside in 4th quarter when trailing
        if hasattr(context, 'quarter') and context.quarter == 4:
            if hasattr(context, 'score_differential') and context.score_differential < 0:
                # Trailing in 4th quarter - might declare onside
                return random.random() < 0.15  # 15% chance to declare
        return False
    
    def _should_surprise_onside(self, context: PlayContext) -> bool:
        """Determine if team should attempt surprise onside (very rare)"""
        return random.random() < 0.02  # 2% chance of surprise onside
    
    def _adjust_penalty_rate(self, base_rate: float, context: PlayContext) -> float:
        """Adjust penalty rate based on game situation"""
        # Could add adjustments based on game pressure, etc.
        return base_rate
    
    def _get_coverage_effectiveness(self, hang_time: float) -> float:
        """Calculate coverage team effectiveness based on hang time and player ratings"""
        coverage_config = self.kickoff_config.get('coverage_mechanics', {})
        
        # Get average coverage rating
        total_rating = sum(player.get_rating('speed') if hasattr(player, 'get_rating') else 75 
                          for player in self.coverage_unit)
        avg_rating = total_rating / len(self.coverage_unit) if self.coverage_unit else 75
        
        # Determine tier
        effectiveness_tiers = coverage_config.get('pursuit_effectiveness', {})
        for tier_name, tier_config in effectiveness_tiers.items():
            if avg_rating >= tier_config.get('rating_threshold', 0):
                base_effectiveness = tier_config.get('gap_discipline', 0.68)
                break
        else:
            base_effectiveness = 0.68
        
        # Adjust for hang time
        hang_time_effect = coverage_config.get('hang_time_effect', {})
        hang_time_bonus = (hang_time - 4.0) * hang_time_effect.get('coverage_time_multiplier', 0.85)
        
        return max(0.4, min(0.95, base_effectiveness + hang_time_bonus))
    
    def _get_return_effectiveness(self) -> float:
        """Calculate return team blocking effectiveness"""
        return_config = self.kickoff_config.get('return_mechanics', {})
        
        # Get average return blocking rating
        total_rating = sum(player.get_rating('run_blocking') if hasattr(player, 'get_rating') else 75 
                          for player in self.return_blockers)
        avg_rating = total_rating / len(self.return_blockers) if self.return_blockers else 75
        
        # Determine tier effectiveness
        blocking_tiers = return_config.get('blocking_effectiveness', {})
        for tier_name, tier_config in blocking_tiers.items():
            if avg_rating >= tier_config.get('rating_threshold', 0):
                return tier_config.get('block_success_rate', 0.66)
        
        return 0.66  # Default average effectiveness
    
    def _resolve_pre_kick_penalty(self, pre_kick: PreKickResult, context: PlayContext) -> KickoffResult:
        """Resolve pre-kick penalty (typically results in rekick)"""
        penalty = pre_kick.penalty_instance
        
        # Most pre-kick penalties result in rekick with yardage adjustment
        # For now, return penalty negated result
        return KickoffResult(
            outcome=KickoffOutcome.PENALTY_NEGATED,
            yards_gained=0,
            points_scored=0,
            field_position=25  # Default starting position after penalty
        )


def get_kickoff_formation_matchup(offensive_formation: str, defensive_formation_name: str) -> Dict:
    """
    Get kickoff formation matchup data from configuration
    
    Args:
        offensive_formation: Offensive formation name (string)
        defensive_formation_name: Defensive formation name (string, may come from enum.for_context())
        
    Returns:
        Dict with formation matchup effectiveness values
    """
    try:
        kickoff_config = config.get_kickoff_config()
        # Kickoffs don't use traditional formation matchups like other plays
        # Return default values for compatibility
        return {
            'effectiveness': 1.0,
            'coverage_advantage': 0.0,
            'return_advantage': 0.0
        }
    except Exception as e:
        print(f"Error loading kickoff formation matchup: {e}")
        return {
            'effectiveness': 1.0,
            'coverage_advantage': 0.0, 
            'return_advantage': 0.0
        }