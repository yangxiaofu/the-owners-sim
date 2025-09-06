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
from play_engine.simulation.stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
from play_engine.mechanics.unified_formations import UnifiedDefensiveFormation, SimulatorContext
from play_engine.play_types.base_types import PlayType
from play_engine.play_types.offensive_types import PuntPlayType
from play_engine.play_types.defensive_types import DefensivePlayType
from play_engine.play_types.punt_types import PuntOutcome
from team_management.players.player import Position
from play_engine.mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from play_engine.mechanics.penalties.penalty_data_structures import PenaltyInstance
from play_engine.config.config_loader import config
from play_engine.config.timing_config import NFLTimingConfig


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


class PuntSimulator:
    """Simulates punt plays with comprehensive four-phase penalty integration and individual player attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str):
        """
        Initialize punt simulator
        
        Args:
            offensive_players: List of 11 offensive Player objects (punt unit)
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation (typically "PUNT")
            defensive_formation: Defensive formation (PUNT_RETURN, PUNT_BLOCK, PUNT_SAFE, SPREAD_RETURN)
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        
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
                
                # For real punts, check return scenarios
                if result.outcome == "returnable":
                    result = self._execute_return_sequence(result, formation_matchup, context)
                    
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
        
        # Convert result to PlayStatsSummary
        summary = PlayStatsSummary(
            play_type=PlayType.PUNT,
            yards_gained=result.net_yards,  # Net punt yards (punt - return)
            time_elapsed=result.time_elapsed
        )
        
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
        """Check if punt attempt is blocked based on formation matchup"""
        block_probability = formation_matchup.get('block_probability', 0.05)
        return random.random() < block_probability
    
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
        punt_distance = self._calculate_punt_distance()
        
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
    
    def _calculate_punt_distance(self) -> int:
        """Calculate punt distance based on punter skill and conditions"""
        base_config = self.punt_config.get('punt_execution', {}).get('base_punt_distance', {})
        base_avg = base_config.get('avg', 45)
        base_min = base_config.get('min', 35)
        base_max = base_config.get('max', 65)
        
        # Apply punter skill modifier
        punter_modifier = self._get_punter_distance_modifier()
        
        # Apply environmental modifiers (wind, weather, etc.)
        environmental_modifier = self._get_environmental_modifier()
        
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
    
    def _calculate_return_yards(self, punt_distance: int, formation_matchup: Dict) -> int:
        """Calculate punt return yards based on multiple factors"""
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
    
    def _get_environmental_modifier(self) -> float:
        """Get environmental modifier for conditions (wind, weather, etc.)"""
        # For now, return baseline - could be expanded with weather context from PlayContext
        return 1.0
    
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
            
            result.player_stats[self.punter.name] = punter_stats
        
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
            
            result.player_stats[self.returner.name] = returner_stats
        
        # Coverage team statistics
        for player in self.coverage_unit[:3]:  # Top 3 coverage players get credit
            coverage_stats = create_player_stats_from_player(player)
            coverage_stats.special_teams_snaps = 1
            
            if result.outcome == PuntOutcome.DOWNED:
                # Randomly assign downed punt credit
                if random.random() < 0.3:  # 30% chance any coverage player gets credit
                    coverage_stats.punts_downed = 1
                    
            if result.outcome == PuntOutcome.PUNT_RETURN:
                # Coverage tackle attribution
                if random.random() < 0.4:  # 40% chance coverage player gets tackle
                    coverage_stats.solo_tackles = 1
            
            result.player_stats[player.name] = coverage_stats


class PuntResult:
    """Result data structure for punt attempts - internal use only"""
    
    def __init__(self, outcome: str, punt_yards: int = 0, return_yards: int = 0, time_elapsed: float = 4.5):
        self.outcome = outcome
        self.punt_yards = punt_yards
        self.return_yards = return_yards
        self.net_yards = punt_yards - return_yards  # Key punt metric
        self.time_elapsed = time_elapsed
        
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