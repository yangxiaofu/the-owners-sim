"""
Field goal simulation with comprehensive fake field goal handling and penalty integration

Implements enhanced multi-phase simulation with comprehensive NFL realism:
1. Strategic fake decision based on situation and coaching tendencies
2. Real field goal simulation with distance-based accuracy and environmental factors
3. Fake field goal sub-simulations (pass and run) with formation advantages
4. Penalty system integration for all field goal scenarios
5. Individual player statistics attribution for special teams units
"""

import random
import math
from typing import List, Tuple, Dict, Optional, Union
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext
from ..play_types.base_types import PlayType
from ...team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config


class FieldGoalPlayParams:
    """Input parameters for field goal simulator - received from external play calling systems"""
    
    def __init__(self, fg_type: str, defensive_formation: str, context: PlayContext):
        """
        Initialize field goal play parameters
        
        Args:
            fg_type: Field goal attempt type ("real_fg", "fake_fg_pass", "fake_fg_run")
            defensive_formation: String formation name (like run/pass plays)
            context: PlayContext with game situation information
        """
        # Store string formation directly (like run/pass plays do)
        self.fg_type = fg_type
        self.defensive_formation = defensive_formation  # Store string, not enum
        self.context = context
    
    def get_defensive_formation_name(self) -> str:
        """Get the defensive formation name (already a string)"""
        return self.defensive_formation


class FieldGoalAttemptResult:
    """Result data structure for field goal attempts"""
    
    def __init__(self, outcome: str, yards_gained: int = 0, points_scored: int = 0,
                 is_fake: bool = False, fake_type: str = None, distance: int = None):
        self.outcome = outcome  # "made", "missed_wide_left", "missed_wide_right", "missed_short", "blocked", "fake_success", "fake_failed"
        self.yards_gained = yards_gained  # 0 for made FG, actual yards for fakes
        self.points_scored = points_scored  # 3 for made FG, 6 for fake TD, 0 for miss/block
        self.is_fake = is_fake
        self.fake_type = fake_type  # "pass" or "run" if fake
        self.distance = distance
        # Import timing config at module level to avoid circular imports
        from ..config.timing_config import NFLTimingConfig
        min_time, max_time = NFLTimingConfig.get_field_goal_timing(is_fake=is_fake)
        self.time_elapsed = random.uniform(min_time, max_time)
        
        # Individual player stats
        self.player_stats = {}
        self.penalty_occurred = False
        self.penalty_instance = None
        self.original_outcome = None


class FakeDecision:
    """Represents the coaching decision on whether to fake a field goal"""
    
    def __init__(self, is_fake: bool, fake_type: str = None, confidence: float = 0.0):
        self.is_fake = is_fake
        self.fake_type = fake_type  # "pass" or "run"
        self.confidence = confidence  # 0.0 to 1.0


class FieldGoalSimulator:
    """Simulates field goal attempts with comprehensive fake handling and individual player attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str):
        """
        Initialize field goal simulator
        
        Args:
            offensive_players: List of 11 offensive Player objects (field goal unit)
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation (typically "FIELD_GOAL")
            defensive_formation: Defensive formation ("FIELD_GOAL_BLOCK" or "PREVENT_FAKE")
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        
        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()
        
        # Load field goal configuration
        self.fg_config = config.get_field_goal_config()
        
        # Identify key special teams players
        self._identify_special_teams_players()
    
    def _identify_special_teams_players(self):
        """Identify key players in field goal unit"""
        self.kicker = None
        self.holder = None  
        self.long_snapper = None
        self.protection_unit = []
        
        for player in self.offensive_players:
            if hasattr(player, 'primary_position'):
                if player.primary_position == Position.K:
                    self.kicker = player
                elif player.primary_position == Position.H:
                    self.holder = player
                elif player.primary_position == Position.LS:
                    self.long_snapper = player
                elif player.primary_position in [Position.LT, Position.LG, Position.C, Position.RG, Position.RT, Position.TE]:
                    self.protection_unit.append(player)
        
        # Fallback assignments if positions not properly set
        if not self.kicker:
            self.kicker = self.offensive_players[0]  # First player as kicker
        if not self.holder:
            self.holder = self.offensive_players[1]  # Second player as holder
        if not self.long_snapper:
            self.long_snapper = self.offensive_players[2]  # Third player as long snapper
    
    def simulate_field_goal_play(self, fg_params: Optional[FieldGoalPlayParams] = None, context: Optional[PlayContext] = None) -> 'PlayStatsSummary':
        """
        Main simulation method for field goal attempts
        
        Args:
            fg_params: FieldGoalPlayParams with validated enum formations (preferred method)
            context: PlayContext with game situation information (fallback for backward compatibility)
            
        Returns:
            PlayStatsSummary with comprehensive field goal outcome and individual player stats
        """
        # Handle both new enum-based params and legacy string-based context
        if fg_params is not None:
            # ✅ NEW: Use validated enum from FieldGoalPlayParams
            defensive_formation_name = fg_params.get_defensive_formation_name()
            context = fg_params.context
        else:
            # ✅ LEGACY: Fallback to string-based formation for backward compatibility
            defensive_formation_name = self.defensive_formation
            if context is None:
                context = PlayContext(
                    play_type="field_goal",
                    offensive_formation=self.offensive_formation,
                    defensive_formation=self.defensive_formation
                )
        
        # Calculate field goal distance
        distance = self._calculate_field_goal_distance(context)
        
        # Phase 1: Determine fake decision
        fake_decision = self._determine_fake_attempt(context, distance)
        
        if fake_decision.is_fake:
            # Phase 2A: Execute fake field goal
            if fake_decision.fake_type == "pass":
                result = self._simulate_fake_fg_pass(context, distance, defensive_formation_name)
            else:  # fake run
                result = self._simulate_fake_fg_run(context, distance, defensive_formation_name)
        else:
            # Phase 2B: Execute real field goal
            result = self._simulate_real_field_goal(context, distance, defensive_formation_name)
        
        # Phase 3: Check for penalties
        original_yards = result.yards_gained
        penalty_result = self.penalty_engine.check_for_penalty(
            self.offensive_players, self.defensive_players, context, original_yards
        )
        
        # Determine final yards and negation
        final_yards = penalty_result.modified_yards if penalty_result.penalty_occurred else original_yards
        play_negated = penalty_result.play_negated if penalty_result.penalty_occurred else False
        
        # Adjust points if play negated
        points_scored = result.points_scored
        if play_negated:
            points_scored = 0
        
        # Phase 4: Attribute individual player statistics
        player_stats = self._attribute_player_statistics_list(result, context)
        
        # Create comprehensive PlayStatsSummary
        summary = PlayStatsSummary(
            play_type="field_goal",
            yards_gained=final_yards,
            time_elapsed=result.time_elapsed,
            field_goal_outcome=result.outcome,
            is_fake_field_goal=result.is_fake,
            fake_field_goal_type=result.fake_type,
            field_goal_distance=result.distance,
            points_scored=points_scored
        )
        
        # Add penalty information if penalty occurred
        if penalty_result.penalty_occurred:
            summary.penalty_occurred = True
            summary.penalty_instance = penalty_result.penalty_instance
            summary.original_yards = original_yards
            summary.play_negated = play_negated
        
        # Add all player stats
        for stats in player_stats:
            summary.add_player_stats(stats)
        
        return summary
    
    def _calculate_field_goal_distance(self, context: PlayContext) -> int:
        """Calculate field goal distance from field position"""
        # Field goal distance = (100 - field_position) + 17 (end zone depth + goalpost)
        field_position = getattr(context, 'field_position', 75)  # Default to 32-yard attempt
        return (100 - field_position) + 17
    
    def _determine_fake_attempt(self, context: PlayContext, distance: int) -> FakeDecision:
        """
        Determine if this should be a fake field goal attempt
        
        Args:
            context: Game situation context
            distance: Field goal distance in yards
            
        Returns:
            FakeDecision with coaching decision
        """
        fake_config = self.fg_config.get('fake_decision_probabilities', {})
        base_fake_rate = fake_config.get('base_fake_rate', 0.08)
        
        # Calculate situational modifiers
        fake_probability = base_fake_rate
        situational_mods = fake_config.get('situational_modifiers', {})
        
        # Short yardage bonus (4th and short)
        if hasattr(context, 'distance') and context.distance <= situational_mods.get('short_yardage', {}).get('distance_threshold', 2):
            fake_probability += situational_mods.get('short_yardage', {}).get('fake_bonus', 0.12)
        
        # Long distance attempts (harder kicks = more fakes)
        if distance >= situational_mods.get('long_distance', {}).get('distance_threshold', 55):
            fake_probability += situational_mods.get('long_distance', {}).get('fake_bonus', 0.03)
        
        # Fourth down bonus
        if hasattr(context, 'down') and context.down == 4:
            fake_probability += situational_mods.get('fourth_down', {}).get('fake_bonus', 0.07)
        
        # Red zone bonus
        field_pos = getattr(context, 'field_position', 50)
        if field_pos >= situational_mods.get('red_zone', {}).get('field_position_threshold', 80):
            fake_probability += situational_mods.get('red_zone', {}).get('fake_bonus', 0.15)
        
        # Goal line bonus
        if field_pos >= situational_mods.get('goal_line', {}).get('field_position_threshold', 95):
            fake_probability += situational_mods.get('goal_line', {}).get('fake_bonus', 0.25)
        
        # Make fake decision
        is_fake = random.random() < fake_probability
        
        if is_fake:
            # Determine fake type (pass vs run)
            fake_type_dist = fake_config.get('fake_type_distribution', {'pass': 0.65, 'run': 0.35})
            fake_type = 'pass' if random.random() < fake_type_dist['pass'] else 'run'
            return FakeDecision(True, fake_type, fake_probability)
        
        return FakeDecision(False, None, 1.0 - fake_probability)
    
    def _simulate_real_field_goal(self, context: PlayContext, distance: int, defensive_formation_name: str = None) -> FieldGoalAttemptResult:
        """
        Simulate a real field goal attempt
        
        Args:
            context: Game situation context  
            distance: Field goal distance in yards
            
        Returns:
            FieldGoalAttemptResult with kick outcome
        """
        # Phase 1: Snap and hold quality
        snap_quality = self._evaluate_snap_quality()
        hold_quality = self._evaluate_hold_quality(snap_quality)
        
        # Phase 2: Protection check (block probability)
        is_blocked = self._check_for_block(context, defensive_formation_name)
        
        if is_blocked:
            return FieldGoalAttemptResult(
                outcome="blocked",
                yards_gained=0,
                points_scored=0,
                is_fake=False,
                distance=distance
            )
        
        # Phase 3: Kick execution
        base_accuracy = self._get_distance_accuracy(distance)
        kicker_modifier = self._get_kicker_modifier()
        environmental_modifier = self._get_environmental_modifier(context)
        
        # Calculate final accuracy
        final_accuracy = base_accuracy * hold_quality * kicker_modifier * environmental_modifier
        
        # Determine kick outcome
        kick_result = random.random()
        
        if kick_result < final_accuracy:
            # Successful field goal
            return FieldGoalAttemptResult(
                outcome="made",
                yards_gained=0,
                points_scored=3,
                is_fake=False,
                distance=distance
            )
        else:
            # Miss - determine miss type
            miss_type = self._determine_miss_type(distance, final_accuracy)
            return FieldGoalAttemptResult(
                outcome=miss_type,
                yards_gained=0,
                points_scored=0,
                is_fake=False,
                distance=distance
            )
    
    def _simulate_fake_fg_pass(self, context: PlayContext, distance: int, defensive_formation_name: str = None) -> FieldGoalAttemptResult:
        """
        Simulate a fake field goal pass attempt
        
        Args:
            context: Game situation context
            distance: Original field goal distance
            
        Returns:
            FieldGoalAttemptResult with fake pass outcome
        """
        fake_config = self.fg_config.get('fake_field_goal_execution', {}).get('fake_pass', {})
        formation_config = self.fg_config.get('formation_matchups', {})
        
        # Get formation advantage using appropriate defensive formation name
        formation_name = defensive_formation_name or self.defensive_formation
        matchup = formation_config.get('matchups', {}).get(self.offensive_formation, {}).get(formation_name, {})
        fake_advantage = matchup.get('fake_advantage_pass', formation_config.get('default_matchup', {}).get('fake_advantage_pass', 0.7))
        
        # Base completion rate modified by formation advantage
        base_completion = fake_config.get('base_completion_rate', 0.70)
        holder_modifier = self._get_holder_passing_modifier()
        
        completion_probability = base_completion * fake_advantage * holder_modifier
        
        # Determine completion
        if random.random() < completion_probability:
            # Completed pass
            yards_config = fake_config.get('yards_range', {'min': 2, 'max': 15, 'avg': 7})
            yards_gained = max(0, int(random.gauss(yards_config['avg'], 
                                                 (yards_config['max'] - yards_config['min']) / 4)))
            
            # Determine if touchdown (if in red zone and good yardage)
            field_pos = getattr(context, 'field_position', 50)
            is_touchdown = field_pos + yards_gained >= 100
            
            return FieldGoalAttemptResult(
                outcome="fake_success",
                yards_gained=yards_gained,
                points_scored=6 if is_touchdown else 0,
                is_fake=True,
                fake_type="pass",
                distance=distance
            )
        else:
            # Incomplete pass or interception
            outcome = "fake_failed" if random.random() < 0.9 else "fake_interception"
            return FieldGoalAttemptResult(
                outcome=outcome,
                yards_gained=0,
                points_scored=0,
                is_fake=True,
                fake_type="pass",
                distance=distance
            )
    
    def _simulate_fake_fg_run(self, context: PlayContext, distance: int, defensive_formation_name: str = None) -> FieldGoalAttemptResult:
        """
        Simulate a fake field goal run attempt
        
        Args:
            context: Game situation context
            distance: Original field goal distance
            
        Returns:
            FieldGoalAttemptResult with fake run outcome
        """
        fake_config = self.fg_config.get('fake_field_goal_execution', {}).get('fake_run', {})
        formation_config = self.fg_config.get('formation_matchups', {})
        
        # Get formation advantage using appropriate defensive formation name
        formation_name = defensive_formation_name or self.defensive_formation
        matchup = formation_config.get('matchups', {}).get(self.offensive_formation, {}).get(formation_name, {})
        fake_advantage = matchup.get('fake_advantage_run', formation_config.get('default_matchup', {}).get('fake_advantage_run', 0.65))
        
        # Base success rate modified by formation advantage
        base_success = fake_config.get('base_success_rate', 0.68)
        holder_modifier = self._get_holder_running_modifier()
        
        success_probability = base_success * fake_advantage * holder_modifier
        
        # Determine success
        if random.random() < success_probability:
            # Successful run
            yards_config = fake_config.get('yards_range', {'min': 0, 'max': 12, 'avg': 4})
            yards_gained = max(0, int(random.gauss(yards_config['avg'], 
                                                 (yards_config['max'] - yards_config['min']) / 4)))
            
            # Determine if touchdown
            field_pos = getattr(context, 'field_position', 50)
            is_touchdown = field_pos + yards_gained >= 100
            
            return FieldGoalAttemptResult(
                outcome="fake_success",
                yards_gained=yards_gained,
                points_scored=6 if is_touchdown else 0,
                is_fake=True,
                fake_type="run",
                distance=distance
            )
        else:
            # Tackled for minimal/no gain
            yards_gained = max(0, random.randint(0, 2))
            return FieldGoalAttemptResult(
                outcome="fake_failed",
                yards_gained=yards_gained,
                points_scored=0,
                is_fake=True,
                fake_type="run",
                distance=distance
            )
    
    def _get_distance_accuracy(self, distance: int) -> float:
        """Get base accuracy for given distance"""
        distance_config = self.fg_config.get('distance_accuracy', {}).get('ranges', {})
        
        if distance <= 30:
            range_config = distance_config.get('0-30', {})
        elif distance <= 40:
            range_config = distance_config.get('31-40', {})
        elif distance <= 50:
            range_config = distance_config.get('41-50', {})
        elif distance <= 60:
            range_config = distance_config.get('51-60', {})
        else:
            range_config = distance_config.get('61+', {})
        
        base_accuracy = range_config.get('base_accuracy', self.fg_config.get('distance_accuracy', {}).get('default_accuracy', 0.75))
        variance = range_config.get('variance', 0.1)
        
        # Apply variance
        return max(0.1, min(0.99, random.gauss(base_accuracy, variance)))
    
    def _get_kicker_modifier(self) -> float:
        """Get accuracy modifier based on kicker attributes"""
        if not self.kicker:
            return 1.0
        
        kicker_config = self.fg_config.get('player_attributes', {}).get('kicker_modifiers', {})
        accuracy_config = kicker_config.get('kicking_accuracy', {})
        
        kicker_accuracy = self.kicker.get_rating('kicking_accuracy') if hasattr(self.kicker, 'get_rating') else 75
        
        if kicker_accuracy >= self.fg_config.get('player_attributes', {}).get('rating_thresholds', {}).get('elite', 90):
            return 1.0 + accuracy_config.get('elite_bonus', 0.08)
        elif kicker_accuracy >= self.fg_config.get('player_attributes', {}).get('rating_thresholds', {}).get('good', 80):
            return 1.0 + accuracy_config.get('good_bonus', 0.04)
        elif kicker_accuracy <= self.fg_config.get('player_attributes', {}).get('rating_thresholds', {}).get('poor', 60):
            return 1.0 + accuracy_config.get('poor_penalty', -0.08)
        
        return 1.0  # Average kicker
    
    def _get_environmental_modifier(self, context: PlayContext) -> float:
        """Get environmental modifier for conditions"""
        # For now, return baseline - could be expanded with weather context
        return 1.0
    
    def _evaluate_snap_quality(self) -> float:
        """Evaluate long snapper performance"""
        if not self.long_snapper:
            return 0.95  # Average snap
        
        snap_accuracy = self.long_snapper.get_rating('snap_accuracy') if hasattr(self.long_snapper, 'get_rating') else 75
        
        # Convert rating to quality score
        if snap_accuracy >= 90:
            return 0.99
        elif snap_accuracy >= 80:
            return 0.97
        elif snap_accuracy <= 60:
            return 0.90
        
        return 0.95
    
    def _evaluate_hold_quality(self, snap_quality: float) -> float:
        """Evaluate holder performance based on snap quality"""
        if not self.holder:
            return 0.95  # Average hold
        
        hold_skill = self.holder.get_rating('hold_skill') if hasattr(self.holder, 'get_rating') else 75
        
        # Base hold quality affected by snap
        base_quality = min(0.99, snap_quality * 1.02)  # Good holders can improve on good snaps
        
        # Adjust for holder skill
        if hold_skill >= 90:
            return min(0.99, base_quality * 1.03)
        elif hold_skill >= 80:
            return min(0.99, base_quality * 1.01)
        elif hold_skill <= 60:
            return base_quality * 0.95
        
        return base_quality
    
    def _check_for_block(self, context: PlayContext, defensive_formation_name: str = None) -> bool:
        """Check if field goal attempt is blocked"""
        formation_config = self.fg_config.get('formation_matchups', {})
        formation_name = defensive_formation_name or self.defensive_formation
        matchup = formation_config.get('matchups', {}).get(self.offensive_formation, {}).get(formation_name, {})
        
        block_probability = matchup.get('block_probability', formation_config.get('default_matchup', {}).get('block_probability', 0.05))
        
        return random.random() < block_probability
    
    def _determine_miss_type(self, distance: int, accuracy: float) -> str:
        """Determine type of miss for failed field goal"""
        # Miss types based on distance and accuracy
        if distance > 50:
            # Long kicks more likely to be short
            if random.random() < 0.4:
                return "missed_short"
            else:
                return "missed_wide_left" if random.random() < 0.5 else "missed_wide_right"
        else:
            # Shorter kicks more likely to be directional misses
            return "missed_wide_left" if random.random() < 0.5 else "missed_wide_right"
    
    def _get_holder_passing_modifier(self) -> float:
        """Get holder's fake passing ability modifier"""
        if not self.holder:
            return 1.0
        
        fake_passing = self.holder.get_rating('fake_passing') if hasattr(self.holder, 'get_rating') else 70
        holder_config = self.fg_config.get('player_attributes', {}).get('holder_modifiers', {}).get('fake_passing', {})
        
        if fake_passing >= 90:
            return 1.0 + holder_config.get('elite_completion_bonus', 0.25)
        elif fake_passing <= 60:
            return 1.0 + holder_config.get('poor_completion_penalty', -0.30)
        
        return 1.0
    
    def _get_holder_running_modifier(self) -> float:
        """Get holder's fake running ability modifier"""
        if not self.holder:
            return 1.0
        
        fake_running = self.holder.get_rating('fake_running') if hasattr(self.holder, 'get_rating') else 70
        holder_config = self.fg_config.get('player_attributes', {}).get('holder_modifiers', {}).get('fake_running', {})
        
        if fake_running >= 90:
            return 1.0 + holder_config.get('elite_yards_bonus', 2.5) / 10  # Convert to multiplier
        elif fake_running <= 60:
            return 1.0 + holder_config.get('poor_yards_penalty', -2.0) / 10  # Convert to multiplier
        
        return 1.0
    
    def _attribute_player_statistics(self, result: FieldGoalAttemptResult, context: PlayContext):
        """Attribute individual player statistics based on play outcome"""
        result.player_stats = {}
        
        # Always credit kicker with attempt
        if self.kicker:
            kicker_stats = create_player_stats_from_player(self.kicker)
            kicker_stats.field_goal_attempts = 1
            
            if result.outcome == "made":
                kicker_stats.field_goals_made = 1
                kicker_stats.longest_field_goal = result.distance
            elif result.outcome.startswith("missed"):
                kicker_stats.field_goals_missed = 1
            elif result.outcome == "blocked":
                kicker_stats.field_goals_blocked = 1
            
            # Fake run stats for kicker
            if result.is_fake and result.fake_type == "run":
                kicker_stats.carries = 1 if "kicker" in str(result.outcome) else 0
                kicker_stats.rushing_yards = result.yards_gained if kicker_stats.carries else 0
            
            result.player_stats[self.kicker.name] = kicker_stats
        
        # Holder statistics
        if self.holder:
            holder_stats = create_player_stats_from_player(self.holder)
            holder_stats.field_goal_holds = 1
            
            if result.is_fake:
                if result.fake_type == "pass":
                    holder_stats.pass_attempts = 1
                    if result.outcome == "fake_success":
                        holder_stats.pass_completions = 1
                        holder_stats.passing_yards = result.yards_gained
                        if result.points_scored == 6:
                            holder_stats.passing_touchdowns = 1
                elif result.fake_type == "run":
                    holder_stats.carries = 1
                    holder_stats.rushing_yards = result.yards_gained
                    if result.points_scored == 6:
                        holder_stats.rushing_touchdowns = 1
            
            result.player_stats[self.holder.name] = holder_stats
        
        # Long snapper statistics
        if self.long_snapper:
            ls_stats = create_player_stats_from_player(self.long_snapper)
            ls_stats.long_snaps = 1
            result.player_stats[self.long_snapper.name] = ls_stats
        
        # Protection unit statistics
        for blocker in self.protection_unit:
            blocker_stats = create_player_stats_from_player(blocker)
            blocker_stats.special_teams_snaps = 1
            if result.outcome == "blocked":
                # Randomly assign block responsibility
                if random.random() < 0.15:  # 15% chance any blocker gets blamed
                    blocker_stats.blocks_allowed = 1
            result.player_stats[blocker.name] = blocker_stats
    
    def _attribute_player_statistics_list(self, result: FieldGoalAttemptResult, context: PlayContext) -> List[PlayerStats]:
        """Attribute individual player statistics and return as list of PlayerStats objects"""
        player_stats = []
        
        # Always credit kicker with attempt
        if self.kicker:
            kicker_stats = create_player_stats_from_player(self.kicker)
            kicker_stats.field_goal_attempts = 1
            
            if result.outcome == "made":
                kicker_stats.field_goals_made = 1
                kicker_stats.longest_field_goal = result.distance
            elif result.outcome.startswith("missed"):
                kicker_stats.field_goals_missed = 1
            elif result.outcome == "blocked":
                kicker_stats.field_goals_blocked = 1
            
            # Fake run stats for kicker
            if result.is_fake and result.fake_type == "run":
                kicker_stats.carries = 1 if "kicker" in str(result.outcome) else 0
                kicker_stats.rushing_yards = result.yards_gained if kicker_stats.carries else 0
            
            player_stats.append(kicker_stats)
        
        # Holder statistics
        if self.holder:
            holder_stats = create_player_stats_from_player(self.holder)
            holder_stats.field_goal_holds = 1
            
            if result.is_fake:
                if result.fake_type == "pass":
                    holder_stats.pass_attempts = 1
                    if result.outcome == "fake_success":
                        holder_stats.completions = 1
                        holder_stats.passing_yards = result.yards_gained
                        if result.points_scored == 6:
                            holder_stats.passing_touchdowns = 1
                elif result.fake_type == "run":
                    holder_stats.carries = 1
                    holder_stats.rushing_yards = result.yards_gained
                    if result.points_scored == 6:
                        holder_stats.rushing_touchdowns = 1
            
            player_stats.append(holder_stats)
        
        # Long snapper statistics
        if self.long_snapper:
            ls_stats = create_player_stats_from_player(self.long_snapper)
            ls_stats.long_snaps = 1
            player_stats.append(ls_stats)
        
        # Protection unit statistics
        for blocker in self.protection_unit:
            blocker_stats = create_player_stats_from_player(blocker)
            blocker_stats.special_teams_snaps = 1
            if result.outcome == "blocked":
                # Randomly assign block responsibility
                if random.random() < 0.15:  # 15% chance any blocker gets blamed
                    blocker_stats.blocks_allowed = 1
            player_stats.append(blocker_stats)
        
        # Return only players who recorded stats
        return [stats for stats in player_stats if stats.get_total_stats()]


def get_field_goal_formation_matchup(offensive_formation: str, defensive_formation: Union[str, UnifiedDefensiveFormation]) -> Dict:
    """
    Get field goal formation matchup data from configuration
    
    Args:
        offensive_formation: Offensive formation string
        defensive_formation: Either string or UnifiedDefensiveFormation enum
    
    Returns:
        Dict with formation matchup data
    """
    try:
        # Convert enum to appropriate context name if needed
        if isinstance(defensive_formation, UnifiedDefensiveFormation):
            defensive_formation_name = defensive_formation.for_context(SimulatorContext.FIELD_GOAL_SIMULATOR)
        else:
            defensive_formation_name = defensive_formation
        
        fg_config = config.get_field_goal_config()
        matchups = fg_config.get('formation_matchups', {}).get('matchups', {})
        
        if offensive_formation in matchups and defensive_formation_name in matchups[offensive_formation]:
            return matchups[offensive_formation][defensive_formation_name]
        else:
            return fg_config.get('formation_matchups', {}).get('default_matchup', {
                'block_probability': 0.05,
                'fake_advantage_pass': 0.70,
                'fake_advantage_run': 0.65
            })
    except Exception as e:
        print(f"Error loading field goal formation matchup: {e}")
        return {
            'block_probability': 0.05,
            'fake_advantage_pass': 0.70,
            'fake_advantage_run': 0.65
        }