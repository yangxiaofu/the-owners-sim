"""
Punt play simulation with comprehensive four-phase penalty integration

Implements enhanced multi-phase simulation with comprehensive NFL realism:
1. Pre-snap penalty check (false start, illegal formation, delay of game)
2. Base punt execution (real punt, fake punt pass, fake punt run)
3. During-play penalty check (roughing punter, holding on return, fair catch interference)  
4. Post-play penalty check (unsportsmanlike conduct, late hits)
5. Individual player statistics attribution for special teams units
"""

import random
import math
from typing import List, Tuple, Dict, Optional, Union
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from .base_simulator import BasePlaySimulator
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext
from ..play_types.base_types import PlayType
from ..play_types.offensive_types import PuntPlayType
from ..play_types.defensive_types import DefensivePlayType
from ..play_types.punt_types import PuntOutcome
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config
from ..config.timing_config import NFLTimingConfig
from game_management.random_events import RandomEventChecker


class PuntPlayParams:
    """Input parameters for punt simulator - received from external play calling systems"""
    
    def __init__(self, punt_type: str, defensive_formation: str, context: PlayContext):
        """
        Initialize punt play parameters
        
        Args:
            punt_type: One of PuntPlayType constants (REAL_PUNT, FAKE_PUNT_PASS, FAKE_PUNT_RUN)
            defensive_formation: String formation name (like run/pass plays)
            context: PlayContext with game situation information
        """
        # Validate punt_type against enum
        if punt_type not in PuntPlayType.get_all_types():
            raise ValueError(f"Invalid punt type: {punt_type}. Must be one of: {PuntPlayType.get_all_types()}")
        
        # Store string formation directly (like run/pass plays do)
        self.punt_type = punt_type
        self.defensive_formation = defensive_formation  # Store string, not enum
        self.context = context
    
    def get_defensive_formation_name(self) -> str:
        """Get the defensive formation name (already a string)"""
        return self.defensive_formation


class PuntSimulator(BasePlaySimulator):
    """Simulates punt plays with comprehensive four-phase penalty integration and individual player attribution"""

    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str,
                 offensive_team_id: int = None, defensive_team_id: int = None,
                 random_event_checker=None):
        """
        Initialize punt simulator

        Args:
            offensive_players: List of 11 offensive Player objects (punt unit)
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation (typically "PUNT")
            defensive_formation: Defensive formation (PUNT_RETURN, PUNT_BLOCK, PUNT_SAFE, SPREAD_RETURN)
            offensive_team_id: Team ID for the punting team (1-32)
            defensive_team_id: Team ID for the return team (1-32)
            random_event_checker: Optional RandomEventChecker for rare events (Tollgate 7)
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id

        # Variance & Unpredictability (Tollgate 7)
        self.random_event_checker = random_event_checker or RandomEventChecker()

        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()

        # Load punt configuration
        self.punt_config = config.get_punt_config()

        # Identify key special teams players
        self._identify_special_teams_players()
    
    def _identify_special_teams_players(self):
        """Identify key players in punt unit"""
        self.punter = None
        self.long_snapper = None
        self.upback = None
        self.coverage_unit = []
        
        # Returner and return team from defensive players
        self.returner = None
        self.return_blockers = []
        
        for player in self.offensive_players:
            if hasattr(player, 'primary_position'):
                if player.primary_position == Position.P:
                    self.punter = player
                elif player.primary_position == Position.LS:
                    self.long_snapper = player
                elif player.primary_position in [Position.FB, Position.RB]:
                    self.upback = player
                elif player.primary_position in [Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB, Position.CB, Position.FS, Position.SS]:
                    self.coverage_unit.append(player)
        
        for player in self.defensive_players:
            if hasattr(player, 'primary_position'):
                if player.primary_position in [Position.CB, Position.FS, Position.SS, Position.RB]:
                    if not self.returner:  # First eligible player becomes returner
                        self.returner = player
                    else:
                        self.return_blockers.append(player)
                elif player.primary_position in [Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB, Position.CB]:
                    self.return_blockers.append(player)
        
        # Fallback assignments if positions not properly set
        if not self.punter:
            self.punter = self.offensive_players[0]
        if not self.long_snapper:
            self.long_snapper = self.offensive_players[1]
        if not self.upback:
            self.upback = self.offensive_players[2]
        if not self.returner:
            self.returner = self.defensive_players[0]
    
    def simulate_punt_play(self, punt_params: PuntPlayParams) -> PlayStatsSummary:
        """
        Main simulation method for punt plays with four-phase penalty integration
        
        Args:
            punt_params: PuntPlayParams with punt type and defensive formation
            
        Returns:
            PlayStatsSummary with comprehensive outcome information and player stats
        """
        context = punt_params.context
        
        # Get formation matchup advantages
        formation_matchup = self._get_formation_matchup(punt_params.defensive_formation)
        
        # PHASE 1: Block check (formation-dependent)
        if self._check_for_block(formation_matchup, context):
            result = self._handle_blocked_punt(context)
        else:
            # PHASE 2: Execute specific punt type
            if punt_params.punt_type == PuntPlayType.REAL_PUNT:
                result = self._execute_real_punt(formation_matchup, context)
                
                # For real punts, use two-stage return system
                if result.outcome == "returnable":
                    # Stage 1: Punt physics and coverage setup
                    punt_physics, return_opportunity = self._simulate_stage_1_punt_physics(context, formation_matchup)
                    
                    # Stage 2: Return decision and execution
                    return_yards, final_outcome, total_time = self._simulate_stage_2_return_execution(
                        punt_physics, return_opportunity, context
                    )
                    
                    # Create enhanced result with two-stage data
                    result = PuntResult(
                        outcome=final_outcome,
                        punt_yards=punt_physics.distance,
                        return_yards=return_yards,
                        hang_time=punt_physics.hang_time,
                        coverage_pressure=return_opportunity.coverage_pressure,
                        time_elapsed=total_time
                    )
                    
            elif punt_params.punt_type == PuntPlayType.FAKE_PUNT_PASS:
                result = self._execute_fake_punt_pass(formation_matchup, context)
                
            elif punt_params.punt_type == PuntPlayType.FAKE_PUNT_RUN:
                result = self._execute_fake_punt_run(formation_matchup, context)
            else:
                # Safety fallback for unexpected punt types
                raise ValueError(f"Unknown punt type: {punt_params.punt_type}")
        
        # Check for penalties using proven API (same as other simulators)
        penalty_result = self.penalty_engine.check_for_penalty(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            context=context,
            original_play_yards=result.yards_gained
        )
        
        # Apply penalty effects if penalty occurred
        if penalty_result.penalty_occurred:
            result.penalty_occurred = True
            result.penalty_instance = penalty_result.penalty_instance
            result.original_yards = result.yards_gained
            result.yards_gained = penalty_result.modified_yards
            if penalty_result.play_negated:
                result.play_negated = True
        
        # PHASE 4: Attribute individual player statistics
        self._attribute_player_statistics(result, context)
        
        # Convert result to PlayStatsSummary with enhanced punt data
        summary = PlayStatsSummary(
            play_type=PlayType.PUNT,
            yards_gained=result.net_yards,  # Net punt yards (punt - return)
            time_elapsed=result.time_elapsed
        )
        
        # Add punt-specific fields to summary for engine.py access
        summary.punt_distance = getattr(result, 'punt_yards', None)
        summary.return_yards = getattr(result, 'return_yards', None)
        summary.hang_time = getattr(result, 'hang_time', None)
        summary.coverage_pressure = getattr(result, 'coverage_pressure', None)
        
        # Add penalty information if occurred
        if hasattr(result, 'penalty_occurred') and result.penalty_occurred:
            summary.penalty_occurred = True
            summary.penalty_instance = result.penalty_instance
            summary.original_yards = getattr(result, 'original_yards', result.net_yards)
            summary.play_negated = getattr(result, 'play_negated', False)
        
        if hasattr(result, 'post_play_penalty'):
            summary.post_play_penalty = result.post_play_penalty
        
        # Add individual player stats
        for player_name, stats in result.player_stats.items():
            summary.add_player_stats(stats)
        
        return summary
    
    def _get_formation_matchup(self, defensive_formation: str) -> Dict:
        """Get formation matchup data from configuration"""
        matchups = self.punt_config.get('formation_matchups', {}).get('matchups', {})
        punt_matchups = matchups.get('PUNT', {})
        
        if defensive_formation in punt_matchups:
            return punt_matchups[defensive_formation]
        else:
            return self.punt_config.get('formation_matchups', {}).get('default_matchup', {
                'block_probability': 0.05,
                'fake_advantage_pass': 0.70,
                'fake_advantage_run': 0.65,
                'return_advantage': 1.0
            })
    
    def _check_for_block(self, formation_matchup: Dict, context: PlayContext) -> bool:
        """
        Check if punt attempt is blocked.

        Uses random event checker for NFL-realistic 0.8% base probability,
        modified by formation matchup (e.g., PUNT_BLOCK formation increases chance).
        """
        # Base NFL-realistic block probability (0.8% per punt)
        if self.random_event_checker.check_blocked_punt():
            return True

        # Additional formation-based block chance (tactical decision)
        # This supplements the random rare event with strategic blocking attempts
        formation_block_modifier = formation_matchup.get('block_probability', 0.0)
        if formation_block_modifier > 0 and random.random() < formation_block_modifier:
            return True

        return False
    
    def _handle_blocked_punt(self, context: PlayContext) -> 'PuntResult':
        """Handle blocked punt scenario"""
        blocked_result = PuntResult(
            outcome=PuntOutcome.BLOCKED,
            punt_yards=0,
            return_yards=0,
            time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing())
        )
        blocked_result.blocked = True
        return blocked_result
    
    def _execute_real_punt(self, formation_matchup: Dict, context: PlayContext) -> 'PuntResult':
        """Execute a real punt attempt"""
        # Calculate punt distance based on punter skill and conditions
        punt_distance = self._calculate_punt_distance(context)
        
        # Determine initial punt placement
        field_position = getattr(context, 'field_position', 50)
        end_position = field_position + punt_distance
        
        # Check for touchback
        if end_position >= 100:
            touchback_distance = 100 - field_position
            return PuntResult(
                outcome=PuntOutcome.TOUCHBACK,
                punt_yards=touchback_distance,
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing())
            )
        
        # Check for out of bounds (including coffin corner)
        out_of_bounds_prob = self.punt_config.get('field_position_mechanics', {}).get('out_of_bounds_probability', {}).get('base_rate', 0.18)
        if random.random() < out_of_bounds_prob:
            # Determine if it's a coffin corner (near goal line)
            if end_position >= 85:
                return PuntResult(
                    outcome=PuntOutcome.COFFIN_CORNER,
                    punt_yards=punt_distance,
                    return_yards=0,
                    time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing())
                )
            else:
                return PuntResult(
                    outcome=PuntOutcome.OUT_OF_BOUNDS,
                    punt_yards=punt_distance,
                    return_yards=0,
                    time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing())
                )
        
        # Check for illegal touching by coverage team
        illegal_touching_prob = self.punt_config.get('field_position_mechanics', {}).get('illegal_touching_probability', {}).get('base_rate', 0.08)
        if random.random() < illegal_touching_prob:
            return PuntResult(
                outcome=PuntOutcome.ILLEGAL_TOUCHING,
                punt_yards=punt_distance,
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing())
            )
        
        # Punt is returnable - will be processed in return sequence
        return PuntResult(
            outcome="returnable",  # Internal state, will be updated in return sequence
            punt_yards=punt_distance,
            return_yards=0,
            time_elapsed=random.uniform(4.2, 5.8)
        )
    
    def _execute_return_sequence(self, punt_result: 'PuntResult', formation_matchup: Dict, context: PlayContext) -> 'PuntResult':
        """Execute punt return sequence (fair catch, return, muff, or downed)"""
        # Check for muff first
        muff_probability = self._calculate_muff_probability()
        if random.random() < muff_probability:
            punt_result.outcome = PuntOutcome.MUFFED
            punt_result.muffed = True
            return punt_result
        
        # Check for coverage team downing the punt
        downed_probability = self._calculate_downed_probability()
        if random.random() < downed_probability:
            punt_result.outcome = PuntOutcome.DOWNED
            return punt_result
        
        # Check for fair catch
        fair_catch_probability = self._calculate_fair_catch_probability(punt_result.punt_yards)
        if random.random() < fair_catch_probability:
            punt_result.outcome = PuntOutcome.FAIR_CATCH
            punt_result.fair_catch = True
            return punt_result
        
        # Execute return attempt
        return_yards = self._calculate_return_yards(punt_result.punt_yards, formation_matchup)
        punt_result.return_yards = return_yards
        punt_result.outcome = PuntOutcome.PUNT_RETURN
        
        # Update net yards
        punt_result.net_yards = punt_result.punt_yards - return_yards
        
        return punt_result
    
    def _execute_fake_punt_pass(self, formation_matchup: Dict, context: PlayContext) -> 'PuntResult':
        """Execute fake punt pass attempt"""
        fake_config = self.punt_config.get('fake_punt_execution', {}).get('fake_pass', {})
        
        # Get formation advantage for fake pass
        fake_advantage = formation_matchup.get('fake_advantage_pass', 0.70)
        
        # Base completion rate modified by formation advantage
        base_completion = fake_config.get('base_completion_rate', 0.65)
        punter_modifier = self._get_punter_passing_modifier()
        
        completion_probability = base_completion * fake_advantage * punter_modifier
        
        # Determine completion
        if random.random() < completion_probability:
            # Completed pass
            yards_config = fake_config.get('yards_range', {'min': 2, 'max': 20, 'avg': 9})
            yards_gained = max(0, int(random.gauss(yards_config['avg'], 
                                                 (yards_config['max'] - yards_config['min']) / 4)))
            
            # Determine if touchdown
            field_pos = getattr(context, 'field_position', 50)
            is_touchdown = field_pos + yards_gained >= 100
            
            result = PuntResult(
                outcome=PuntOutcome.FAKE_SUCCESS,
                punt_yards=0,  # No punt occurred
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing(is_fake=True))
            )
            result.is_fake = True
            result.fake_type = "pass"
            result.yards_gained = yards_gained
            result.net_yards = yards_gained  # For fake punts, net yards = yards gained
            
            if is_touchdown:
                result.points_scored = 6
            
            return result
        else:
            # Incomplete pass or interception
            outcome = PuntOutcome.FAKE_FAILED if random.random() < 0.9 else PuntOutcome.FAKE_INTERCEPTION
            
            result = PuntResult(
                outcome=outcome,
                punt_yards=0,
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing(is_fake=True))
            )
            result.is_fake = True
            result.fake_type = "pass"
            result.yards_gained = 0
            result.net_yards = 0
            
            return result
    
    def _execute_fake_punt_run(self, formation_matchup: Dict, context: PlayContext) -> 'PuntResult':
        """Execute fake punt run attempt"""
        fake_config = self.punt_config.get('fake_punt_execution', {}).get('fake_run', {})
        
        # Get formation advantage for fake run
        fake_advantage = formation_matchup.get('fake_advantage_run', 0.65)
        
        # Base success rate modified by formation advantage
        base_success = fake_config.get('base_success_rate', 0.62)
        punter_modifier = self._get_punter_running_modifier()
        
        success_probability = base_success * fake_advantage * punter_modifier
        
        # Determine success
        if random.random() < success_probability:
            # Successful run
            yards_config = fake_config.get('yards_range', {'min': 0, 'max': 15, 'avg': 5})
            yards_gained = max(0, int(random.gauss(yards_config['avg'], 
                                                 (yards_config['max'] - yards_config['min']) / 4)))
            
            # Determine if touchdown
            field_pos = getattr(context, 'field_position', 50)
            is_touchdown = field_pos + yards_gained >= 100
            
            result = PuntResult(
                outcome=PuntOutcome.FAKE_SUCCESS,
                punt_yards=0,
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing(is_fake=True))
            )
            result.is_fake = True
            result.fake_type = "run"
            result.yards_gained = yards_gained
            result.net_yards = yards_gained
            
            if is_touchdown:
                result.points_scored = 6
            
            return result
        else:
            # Failed run attempt
            yards_gained = max(0, random.randint(0, 2))  # Minimal gain on failure
            
            result = PuntResult(
                outcome=PuntOutcome.FAKE_FAILED,
                punt_yards=0,
                return_yards=0,
                time_elapsed=random.uniform(*NFLTimingConfig.get_punt_timing(is_fake=True))
            )
            result.is_fake = True
            result.fake_type = "run"
            result.yards_gained = yards_gained
            result.net_yards = yards_gained
            
            return result
    
    def _calculate_punt_distance(self, context: PlayContext) -> int:
        """Calculate punt distance based on punter skill and conditions"""
        base_config = self.punt_config.get('punt_execution', {}).get('base_punt_distance', {})
        base_avg = base_config.get('avg', 45)
        base_min = base_config.get('min', 35)
        base_max = base_config.get('max', 65)
        
        # Apply punter skill modifier
        punter_modifier = self._get_punter_distance_modifier()
        
        # Apply environmental modifiers (wind, weather, etc.)
        environmental_modifier = self._get_environmental_modifier(context)
        
        # Calculate final distance
        modified_avg = base_avg + punter_modifier
        distance = random.gauss(modified_avg, (base_max - base_min) / 6) * environmental_modifier
        
        return max(base_min, min(base_max + 10, int(distance)))  # Allow slight overflow for elite punters
    
    def _calculate_muff_probability(self) -> float:
        """Calculate probability of muffed punt based on returner and conditions"""
        base_muff_rate = self.punt_config.get('return_mechanics', {}).get('muff_probability', {}).get('base_rate', 0.02)
        
        # Apply returner skill modifier
        if self.returner and hasattr(self.returner, 'get_rating'):
            ball_security = self.returner.get_rating('ball_security')
            if ball_security >= 90:
                base_muff_rate -= 0.015  # Elite returners muff less
            elif ball_security <= 60:
                base_muff_rate += 0.012  # Poor returners muff more
        
        return max(0.005, min(0.05, base_muff_rate))  # Cap between 0.5% and 5%
    
    def _calculate_downed_probability(self) -> float:
        """Calculate probability of punt being downed by coverage team"""
        base_downed_rate = self.punt_config.get('field_position_mechanics', {}).get('downed_punt_probability', {}).get('base_rate', 0.25)
        
        # Coverage team quality affects downed rate
        coverage_modifier = self._get_coverage_quality_modifier()
        
        return base_downed_rate * coverage_modifier
    
    def _calculate_fair_catch_probability(self, punt_distance: int) -> float:
        """Calculate probability of fair catch based on punt characteristics"""
        base_fair_catch = self.punt_config.get('return_mechanics', {}).get('fair_catch_probability', {}).get('base_rate', 0.35)
        
        # Modify based on punt distance and hang time
        modifiers = self.punt_config.get('return_mechanics', {}).get('fair_catch_probability', {}).get('modifiers', {})
        
        if punt_distance <= modifiers.get('short_punt', {}).get('distance_threshold', 35):
            base_fair_catch += modifiers.get('short_punt', {}).get('fair_catch_bonus', 0.15)
        elif punt_distance >= modifiers.get('long_punt', {}).get('distance_threshold', 55):
            base_fair_catch += modifiers.get('long_punt', {}).get('fair_catch_penalty', -0.10)
        
        return max(0.1, min(0.8, base_fair_catch))  # Cap between 10% and 80%
    
    def _simulate_stage_1_punt_physics(self, context: PlayContext, formation_matchup: Dict) -> tuple:
        """Stage 1: Simulate punt flight physics and coverage setup"""
        # Calculate punt distance using existing logic
        base_distance_config = self.punt_config.get('punt_execution', {}).get('base_punt_distance', {})
        base_distance = base_distance_config.get('avg', 45)
        
        # Apply punter skill (additive bonus) and environmental factors (multiplicative)
        punter_bonus = self._get_punter_distance_modifier()  # Returns +8, +4, 0, or -6 yards
        environmental_modifier = self._get_environmental_modifier(context)

        # Punter bonus is additive, environmental is multiplicative
        base_with_skill = base_distance + punter_bonus  # 45 + 8 = 53 for elite punter
        punt_distance = int(base_with_skill * environmental_modifier)
        punt_distance = max(25, min(75, punt_distance))  # Realistic bounds
        
        # Calculate hang time based on distance (physics-based)
        if punt_distance < 35:
            hang_time = random.uniform(3.8, 4.2)
        elif punt_distance < 50:
            hang_time = random.uniform(4.2, 4.8)
        else:
            hang_time = random.uniform(4.8, 5.5)
        
        # Determine punt placement strategy
        placement = self._determine_punt_placement(context)
        
        # Calculate coverage pressure based on hang time and distance
        coverage_pressure = self._calculate_coverage_pressure(punt_distance, hang_time, formation_matchup)
        
        # Calculate blocking quality based on return formation
        blocking_quality = self._calculate_blocking_quality(formation_matchup)
        
        # Determine available return lanes
        available_lanes = self._get_available_return_lanes(placement, formation_matchup)
        
        # Create return opportunity assessment
        return_opportunity = ReturnOpportunity(
            coverage_pressure=coverage_pressure,
            blocking_quality=blocking_quality,
            available_lanes=available_lanes,
            field_position_factor=context.field_position / 100.0
        )
        
        punt_physics = PuntPhysics(punt_distance, hang_time, placement)
        
        return punt_physics, return_opportunity
    
    def _simulate_stage_2_return_execution(self, punt_physics: 'PuntPhysics',
                                         return_opportunity: 'ReturnOpportunity',
                                         context: PlayContext) -> tuple:
        """
        Stage 2: Simulate return decision making and execution

        Includes random muffed punt check (Tollgate 7: Variance & Unpredictability)
        """
        # NEW (Tollgate 7): Check for muffed punt (2% probability)
        if self.random_event_checker.check_muffed_return():
            # Muffed punt! Kicking team recovers, return team loses possession
            # Return 0 yards (turnover at punt landing spot)
            return 0, PuntOutcome.MUFFED, punt_physics.hang_time

        # Returner decision: fair catch vs attempt return
        fair_catch_prob = return_opportunity.get_fair_catch_probability()
        
        # Adjust for game situation (aggressive when behind, conservative when ahead)
        score_differential = getattr(context, 'score_differential', 0)
        time_remaining = getattr(context, 'time_remaining', 900)
        
        if score_differential > 10 and time_remaining < 300:  # Behind late
            fair_catch_prob *= 0.6  # More aggressive
        elif score_differential < -10:  # Ahead by a lot
            fair_catch_prob *= 1.4  # More conservative
            
        # Fair catch decision
        if random.random() < fair_catch_prob:
            return 0, PuntOutcome.FAIR_CATCH, punt_physics.hang_time
        
        # Return attempt - simulate execution
        return_yards = self._execute_return_attempt(punt_physics, return_opportunity)
        
        # Calculate total play time (hang time + return time)
        return_time = max(1.5, return_yards * 0.15 + random.uniform(1.0, 3.0))
        total_time = punt_physics.hang_time + return_time
        
        return return_yards, PuntOutcome.PUNT_RETURN, total_time
    
    def _calculate_coverage_pressure(self, punt_distance: int, hang_time: float, formation_matchup: Dict) -> float:
        """Calculate coverage team pressure level based on physics"""
        # Coverage team needs to travel punt_distance in hang_time
        required_speed = punt_distance / hang_time  # yards per second
        
        # Base coverage quality from formation matchup
        base_pressure = formation_matchup.get('coverage_advantage', 0.5)
        
        # Physics modifier: longer hang time = better coverage
        if hang_time > 5.0:
            physics_modifier = 1.2  # Great coverage
        elif hang_time < 4.0:
            physics_modifier = 0.7  # Poor coverage (short hang time)
        else:
            physics_modifier = 1.0
        
        coverage_pressure = base_pressure * physics_modifier
        return min(1.0, max(0.1, coverage_pressure))
    
    def _calculate_blocking_quality(self, formation_matchup: Dict) -> float:
        """Calculate return blocking quality"""
        return formation_matchup.get('return_advantage', 0.5)
    
    def _get_available_return_lanes(self, placement: str, formation_matchup: Dict) -> list:
        """Determine available return lanes based on punt placement and formation"""
        if placement == "sideline":
            return ["middle", "far_side"]  # Limited options
        elif placement == "corner":
            return ["middle"]  # Very limited
        else:
            return ["left", "middle", "right"]  # Full options
    
    def _determine_punt_placement(self, context: PlayContext) -> str:
        """Determine punt placement strategy"""
        field_position = getattr(context, 'field_position', 50)
        
        if field_position > 60:  # In opponent territory
            return "corner" if random.random() < 0.3 else "sideline"
        else:
            return "middle" if random.random() < 0.6 else "sideline"
    
    def _execute_return_attempt(self, punt_physics: 'PuntPhysics', return_opportunity: 'ReturnOpportunity') -> int:
        """Execute the actual return based on Stage 1 conditions"""
        base_return = 8.1  # NFL average
        
        # Primary factor: coverage pressure vs blocking quality
        advantage = return_opportunity.blocking_quality - return_opportunity.coverage_pressure
        
        # Apply returner skill
        returner_modifier = self._get_returner_skill_modifier()
        
        # Calculate expected return
        expected_return = base_return * (1.0 + advantage) * returner_modifier
        
        # Add variance
        return_yards = random.gauss(expected_return, expected_return * 0.4)
        
        # Explosive play check (5% chance based on advantage)
        if advantage > 0.3 and random.random() < 0.05:
            return_yards += random.randint(15, 40)  # Breakaway potential
        
        return max(0, int(return_yards))
    
    def _calculate_return_yards(self, punt_distance: int, formation_matchup: Dict) -> int:
        """Legacy method - kept for compatibility"""
        base_return_config = self.punt_config.get('return_mechanics', {}).get('return_yards', {})
        base_return = base_return_config.get('base_return', {}).get('avg', 8.1)
        
        # Apply formation advantage
        return_advantage = formation_matchup.get('return_advantage', 1.0)
        
        # Apply returner skill modifier
        returner_modifier = self._get_returner_skill_modifier()
        
        # Apply coverage quality modifier
        coverage_modifier = self._get_coverage_quality_modifier()
        
        # Calculate final return yards
        expected_return = base_return * return_advantage * returner_modifier / coverage_modifier
        return_yards = random.gauss(expected_return, expected_return * 0.4)
        
        return max(0, int(return_yards))
    
    def _get_punter_distance_modifier(self) -> float:
        """Get punter distance modifier based on punter attributes"""
        if not self.punter or not hasattr(self.punter, 'get_rating'):
            return 0
        
        punter_power = self.punter.get_rating('punt_distance')
        player_config = self.punt_config.get('player_attributes', {}).get('punter_modifiers', {}).get('punt_distance', {})
        
        if punter_power >= 90:
            return player_config.get('elite_bonus', 8)
        elif punter_power >= 80:
            return player_config.get('good_bonus', 4)
        elif punter_power <= 60:
            return player_config.get('poor_penalty', -6)
        
        return 0
    
    def _get_punter_passing_modifier(self) -> float:
        """Get punter's fake passing ability modifier"""
        if not self.punter or not hasattr(self.punter, 'get_rating'):
            return 1.0
        
        fake_passing = self.punter.get_rating('fake_passing') if hasattr(self.punter, 'get_rating') else 70
        
        if fake_passing >= 90:
            return 1.25  # Elite fake passing
        elif fake_passing <= 60:
            return 0.70  # Poor fake passing
        
        return 1.0
    
    def _get_punter_running_modifier(self) -> float:
        """Get punter's fake running ability modifier"""
        if not self.punter or not hasattr(self.punter, 'get_rating'):
            return 1.0
        
        fake_running = self.punter.get_rating('fake_running') if hasattr(self.punter, 'get_rating') else 70
        
        if fake_running >= 90:
            return 1.20  # Elite fake running
        elif fake_running <= 60:
            return 0.75  # Poor fake running
        
        return 1.0
    
    def _get_returner_skill_modifier(self) -> float:
        """Get returner skill modifier for return yards"""
        if not self.returner or not hasattr(self.returner, 'get_rating'):
            return 1.0
        
        return_ability = self.returner.get_rating('return_ability')
        player_config = self.punt_config.get('player_attributes', {}).get('returner_modifiers', {}).get('return_ability', {})
        
        if return_ability >= 90:
            return 1.0 + (player_config.get('elite_yards_bonus', 4.5) / 10)
        elif return_ability >= 80:
            return 1.0 + (player_config.get('good_yards_bonus', 2.2) / 10)
        elif return_ability <= 60:
            return 1.0 + (player_config.get('poor_yards_penalty', -2.8) / 10)
        
        return 1.0
    
    def _get_coverage_quality_modifier(self) -> float:
        """Get coverage team quality modifier"""
        if not self.coverage_unit:
            return 1.0
        
        # Average coverage team speed and tackling
        total_coverage_rating = 0
        coverage_count = 0
        
        for player in self.coverage_unit[:4]:  # Top 4 coverage players
            if hasattr(player, 'get_rating'):
                coverage_speed = player.get_rating('coverage_speed')
                tackling = player.get_rating('tackling')
                avg_rating = (coverage_speed + tackling) / 2
                total_coverage_rating += avg_rating
                coverage_count += 1
        
        if coverage_count == 0:
            return 1.0
        
        avg_coverage = total_coverage_rating / coverage_count
        
        if avg_coverage >= 85:
            return 1.4  # Excellent coverage reduces return yards significantly
        elif avg_coverage >= 75:
            return 1.2  # Good coverage
        elif avg_coverage <= 60:
            return 0.7  # Poor coverage allows more return yards
        
        return 1.0
    
    def _get_environmental_modifier(self, context: PlayContext, kick_distance: int = 45) -> float:
        """Get environmental modifier for conditions (wind, weather, etc.)

        Uses inherited BasePlaySimulator._get_environmental_modifier() for weather effects.

        Args:
            context: PlayContext with optional weather_condition attribute
            kick_distance: Punt distance in yards (affects weather scaling)

        Returns:
            Environmental modifier (0.4-1.0, where 1.0 = no weather effect)
        """
        weather_condition = getattr(context, 'weather_condition', 'clear')
        return super()._get_environmental_modifier(
            weather_condition=weather_condition,
            kick_distance=kick_distance
        )
    
    def _attribute_player_statistics(self, result: 'PuntResult', context: PlayContext):
        """Attribute individual player statistics based on play outcome"""
        result.player_stats = {}
        
        # Punter statistics
        if self.punter:
            punter_stats = create_player_stats_from_player(self.punter)
            
            if result.is_fake:
                # Fake punt stats
                if result.fake_type == "pass":
                    punter_stats.pass_attempts = 1
                    if result.outcome == PuntOutcome.FAKE_SUCCESS:
                        punter_stats.pass_completions = 1
                        punter_stats.passing_yards = result.yards_gained
                        if getattr(result, 'points_scored', 0) == 6:
                            punter_stats.passing_touchdowns = 1
                elif result.fake_type == "run":
                    punter_stats.carries = 1
                    punter_stats.rushing_yards = result.yards_gained
                    if getattr(result, 'points_scored', 0) == 6:
                        punter_stats.rushing_touchdowns = 1
            else:
                # Real punt stats
                punter_stats.punts = 1
                punter_stats.punt_yards = result.punt_yards
                punter_stats.net_punt_yards = result.net_yards

                if result.punt_yards >= 55:  # Long punt threshold
                    punter_stats.long_punts = 1

                if result.outcome in [PuntOutcome.COFFIN_CORNER, PuntOutcome.DOWNED]:
                    punter_stats.punts_inside_20 = 1  # Assume good placement

            # Add special teams snap credit for punter (ensures punter appears in box score)
            punter_stats.add_special_teams_snap()

            result.player_stats[self.punter.name] = punter_stats

        # Punt Protection Statistics (Offensive Line)
        protection_stats = self._attribute_punt_protection_stats(result)
        for player_name, stats in protection_stats.items():
            result.player_stats[player_name] = stats

        # Returner statistics
        if self.returner and result.outcome in [PuntOutcome.PUNT_RETURN, PuntOutcome.FAIR_CATCH, PuntOutcome.MUFFED]:
            returner_stats = create_player_stats_from_player(self.returner)

            if result.outcome == PuntOutcome.PUNT_RETURN:
                returner_stats.punt_returns = 1
                returner_stats.punt_return_yards = result.return_yards

                if result.return_yards >= 20:  # Long return threshold
                    returner_stats.long_punt_returns = 1

            elif result.outcome == PuntOutcome.FAIR_CATCH:
                returner_stats.fair_catches = 1

            elif result.outcome == PuntOutcome.MUFFED:
                returner_stats.muffed_punts = 1

            # Add special teams snap credit for returner
            returner_stats.add_special_teams_snap()

            result.player_stats[self.returner.name] = returner_stats
        
        # Coverage team statistics
        for player in self.coverage_unit[:3]:  # Top 3 coverage players get credit
            coverage_stats = create_player_stats_from_player(player)

            # Add special teams snap credit for coverage player
            coverage_stats.add_special_teams_snap()

            if result.outcome == PuntOutcome.DOWNED:
                # Randomly assign downed punt credit
                if random.random() < 0.3:  # 30% chance any coverage player gets credit
                    coverage_stats.punts_downed = 1

            if result.outcome == PuntOutcome.PUNT_RETURN:
                # Coverage tackle attribution
                if random.random() < 0.4:  # 40% chance coverage player gets tackle
                    coverage_stats.tackles = 1  # Solo tackle (use 'tackles' field, not 'solo_tackles')

            result.player_stats[player.name] = coverage_stats

        # Track special teams snaps for ALL 22 players on the field
        # Uses inherited method from BasePlaySimulator
        self._track_special_teams_snaps_for_all_players(result.player_stats)

    def _attribute_punt_protection_stats(self, result: 'PuntResult') -> Dict[str, PlayerStats]:
        """
        Attribute comprehensive punt protection statistics to offensive line players

        Args:
            result: PuntResult containing punt outcome information

        Returns:
            Dictionary mapping player names to PlayerStats objects with punt protection stats
        """
        protection_stats = {}

        # Get offensive line players for punt protection
        # In punt formation, typically 5-7 players are involved in protection
        offensive_players = [p for p in self.offensive_players if hasattr(p, 'primary_position')]
        protection_positions = ['left_tackle', 'left_guard', 'center', 'right_guard', 'right_tackle',
                              'tight_end', 'fullback', 'linebacker']  # LBs often help in punt protection

        protection_players = []
        for player in offensive_players:
            if any(pos in player.primary_position.lower() for pos in protection_positions):
                protection_players.append(player)

        # Limit to realistic punt protection unit size
        max_protectors = min(7, len(protection_players))
        if protection_players:
            selected_protectors = random.sample(protection_players, min(max_protectors, len(protection_players)))

            for protector in selected_protectors:
                protector_stats = create_player_stats_from_player(protector)

                # Punt protection stats based on outcome
                if result.blocked:
                    # Blocked punt - someone missed assignment
                    if random.random() < 0.3:  # 30% chance this protector allowed block
                        protector_stats.blocks_allowed += 1
                        protector_stats.add_missed_assignment()
                    protector_stats.add_block(successful=False)
                else:
                    # Good protection - successful punt
                    protector_stats.add_block(successful=True)

                    # Calculate punt protection grade
                    protection_grade = self._calculate_punt_protection_grade(result)
                    protector_stats.set_pass_blocking_efficiency(protection_grade)  # Use pass blocking efficiency for punt protection

                    # Pancake opportunities on excellent protection (coffin corner punts)
                    if result.outcome in [PuntOutcome.COFFIN_CORNER, PuntOutcome.DOWNED]:
                        if random.random() < 0.05:  # 5% chance of pancake on excellent punt
                            protector_stats.add_pancake()

                protection_stats[protector.name] = protector_stats

        return protection_stats

    def _calculate_punt_protection_grade(self, result: 'PuntResult') -> float:
        """
        Calculate punt protection grade based on punt outcome

        Args:
            result: PuntResult containing punt information

        Returns:
            Protection grade (0-100)
        """
        base_grade = 50.0

        if result.blocked:
            base_grade = 20.0  # Very poor - punt was blocked
        elif result.outcome == PuntOutcome.MUFFED:
            base_grade = 75.0  # Good protection - returner error
        elif result.outcome in [PuntOutcome.COFFIN_CORNER, PuntOutcome.DOWNED]:
            base_grade = 85.0  # Excellent - perfect punt execution
        elif result.outcome == PuntOutcome.TOUCHBACK:
            base_grade = 70.0  # Good - clean punt but maybe too much distance
        elif result.outcome == PuntOutcome.PUNT_RETURN:
            # Grade based on return yards allowed
            if result.return_yards <= 5:
                base_grade = 80.0  # Excellent coverage
            elif result.return_yards <= 10:
                base_grade = 70.0  # Good coverage
            elif result.return_yards <= 15:
                base_grade = 60.0  # Average coverage
            else:
                base_grade = 45.0  # Poor coverage
        else:
            base_grade = 65.0  # Fair catch or other neutral outcome

        # Add some randomness
        grade = base_grade + random.uniform(-5.0, 5.0)
        return max(0.0, min(100.0, grade))

    # NOTE: _track_special_teams_snaps_for_all_players is inherited from BasePlaySimulator


class PuntPhysics:
    """Stage 1: Punt flight physics and trajectory data"""
    
    def __init__(self, distance: int, hang_time: float, placement: str):
        self.distance = distance
        self.hang_time = hang_time
        self.placement = placement  # "middle", "sideline", "corner"


class CoverageSetup:
    """Stage 1: Coverage team rush and pressure assessment"""
    
    def __init__(self, pressure_level: float, arrival_time: float):
        self.pressure_level = pressure_level  # 0.0-1.0 (higher = more pressure)
        self.arrival_time = arrival_time      # How long coverage takes to reach returner


class ReturnOpportunity:
    """Stage 1 Output: The situation returner inherits when catching punt"""
    
    def __init__(self, coverage_pressure: float, blocking_quality: float, 
                 available_lanes: list, field_position_factor: float):
        self.coverage_pressure = coverage_pressure
        self.blocking_quality = blocking_quality
        self.available_lanes = available_lanes  # ["fair_catch"] or ["left", "middle", "right"]
        self.field_position_factor = field_position_factor
        
    def get_fair_catch_probability(self) -> float:
        """Calculate probability of fair catch based on Stage 1 conditions"""
        base_fair_catch = 0.25
        pressure_factor = self.coverage_pressure * 0.4
        blocking_factor = (1.0 - self.blocking_quality) * 0.2
        return min(0.85, base_fair_catch + pressure_factor + blocking_factor)


class PuntResult:
    """Result data structure for punt attempts - internal use only"""
    
    def __init__(self, outcome: str, punt_yards: int = 0, return_yards: int = 0, 
                 hang_time: float = 4.5, coverage_pressure: float = 0.5, time_elapsed: float = 4.5):
        self.outcome = outcome
        self.punt_yards = punt_yards          # Stage 1: Punt distance
        self.return_yards = return_yards      # Stage 2: Return yards
        self.net_yards = punt_yards - return_yards  # Net punt effect
        self.hang_time = hang_time           # Stage 1: Coverage rush time
        self.coverage_pressure = coverage_pressure  # Stage 1: Coverage quality
        self.time_elapsed = time_elapsed     # Total play time (Stage 1 + Stage 2)
        
        # Punt-specific flags
        self.is_fake = False
        self.fake_type = None
        self.fair_catch = False
        self.touchback = False
        self.blocked = False
        self.muffed = False
        
        # Fake punt specific
        self.yards_gained = 0  # For fake punts
        self.points_scored = 0  # For fake punt TDs
        
        # Penalty integration
        self.penalty_occurred = False
        self.penalty_instance = None
        self.original_yards = None
        self.play_negated = False
        self.post_play_penalty = None
        
        # Individual player stats
        self.player_stats = {}