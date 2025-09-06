"""
Pass play simulation with comprehensive statistics and player attribute integration

Implements enhanced multi-phase simulation with comprehensive NFL statistics:
1. Determine pressure/protection outcome using formation matchup matrix
2. Select target receiver based on formation and routes
3. Resolve pass outcome (complete/incomplete/sack/INT) with player attributes
4. Calculate yards (air yards + YAC) based on player matchups
5. Attribute comprehensive individual player statistics
"""

import random
from typing import List, Tuple, Dict, Optional
from play_engine.simulation.stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
from play_engine.play_types.base_types import PlayType
from team_management.players.player import Position
from play_engine.mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from play_engine.mechanics.penalties.penalty_data_structures import PenaltyInstance
from play_engine.config.config_loader import config, get_pass_formation_matchup
from play_engine.config.timing_config import NFLTimingConfig


class PassPlaySimulator:
    """Simulates pass plays with comprehensive NFL statistics and individual player attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str):
        """
        Initialize pass play simulator
        
        Args:
            offensive_players: List of 11 offensive Player objects
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation string  
            defensive_formation: Defensive formation string
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        
        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()
    
    def simulate_pass_play(self, context: Optional[PlayContext] = None) -> PlayStatsSummary:
        """
        Simulate complete pass play with comprehensive NFL statistics
        
        Args:
            context: Game situation context for penalty determination
            
        Returns:
            PlayStatsSummary with pass outcome, individual player stats, and penalty information
        """
        # Default context if none provided
        if context is None:
            context = PlayContext(
                play_type=PlayType.PASS,
                offensive_formation=self.offensive_formation,
                defensive_formation=self.defensive_formation
            )
        
        # Phase 1: Multi-stage pass play simulation
        pass_outcome = self._simulate_pass_outcome()
        
        # Phase 2: Check for penalties and apply effects  
        original_yards = pass_outcome.get('yards', 0)
        penalty_result = self.penalty_engine.check_for_penalty(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            context=context,
            original_play_yards=original_yards
        )
        
        # Determine final play result
        final_yards = penalty_result.modified_yards if penalty_result.penalty_occurred else original_yards
        play_negated = penalty_result.play_negated if penalty_result.penalty_occurred else False
        
        # Phase 3: Attribute comprehensive player statistics
        player_stats = self._attribute_player_stats(pass_outcome, penalty_result)
        
        # Create comprehensive play summary
        summary = PlayStatsSummary(
            play_type=PlayType.PASS,
            yards_gained=final_yards,
            time_elapsed=pass_outcome.get('time_elapsed', 3.0)
        )
        
        # Add penalty information to summary if penalty occurred
        if penalty_result.penalty_occurred:
            summary.penalty_occurred = True
            summary.penalty_instance = penalty_result.penalty_instance
            summary.original_yards = original_yards
            summary.play_negated = play_negated
        
        for stats in player_stats:
            summary.add_player_stats(stats)
        
        return summary
    
    def _simulate_pass_outcome(self) -> Dict:
        """
        Multi-phase pass play outcome simulation
        
        Returns:
            Dictionary containing outcome details (completion, yards, participants, etc.)
        """
        # Get base formation matchup parameters from configuration
        matchup_params = get_pass_formation_matchup(self.offensive_formation, self.defensive_formation)
        
        if matchup_params:
            base_params = matchup_params.copy()
        else:
            # Use configured default if specific matchup not found
            pass_config = config.get_pass_play_config()
            default_matchup = pass_config.get('formation_matchups', {}).get('default_matchup', {})
            base_params = default_matchup.copy() if default_matchup else {
                'completion_rate': 0.65, 'sack_rate': 0.09, 'pressure_rate': 0.24, 'deflection_rate': 0.06, 'int_rate': 0.025,
                'avg_air_yards': 8.0, 'avg_yac': 4.5, 'avg_time_to_throw': 2.5
            }
        
        # Phase 1: Apply player attribute modifiers
        modified_params = self._apply_player_attribute_modifiers(base_params)
        
        # Phase 2: Determine pressure outcome
        pressure_outcome = self._determine_pressure_outcome(modified_params)
        
        # Phase 3: If not sacked, determine pass outcome
        if pressure_outcome['sacked']:
            # Use configured time range for sacks
            mechanics_config = config.get_play_mechanics_config('pass_play')
            time_ranges = mechanics_config.get('time_ranges', {})
            sack_time_min = time_ranges.get('sack_time_min', 2.0)
            sack_time_max = time_ranges.get('sack_time_max', 3.5)
            
            return {
                'outcome_type': 'sack',
                'yards': -pressure_outcome['sack_yards'],
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'qb_sacked': True,
                'pressure_applied': True
            }
        
        # Phase 4: Select target receiver
        target_receiver = self._select_target_receiver()
        
        # Phase 5: Determine pass completion outcome
        pass_result = self._determine_pass_completion(modified_params, target_receiver, pressure_outcome)
        
        return pass_result
    
    def _apply_player_attribute_modifiers(self, base_params: Dict) -> Dict:
        """
        Modify base formation parameters based on real player attributes
        
        Args:
            base_params: Base parameters from formation matchup matrix
            
        Returns:
            Modified parameters accounting for player strengths/weaknesses
        """
        modified_params = base_params.copy()
        
        # Get configured player attributes
        player_config = config.get_player_attribute_config('pass_play')
        thresholds = player_config.get('rating_thresholds', {})
        qb_modifiers = player_config.get('quarterback_modifiers', {})
        
        elite_threshold = thresholds.get('elite', 90)
        good_threshold = thresholds.get('good', 80)
        poor_threshold = thresholds.get('poor', 65)
        very_good_threshold = thresholds.get('very_good', 85)
        below_avg_threshold = thresholds.get('below_average', 60)
        
        # Find key players
        quarterback = self._find_player_by_position(Position.QB)
        receivers = self._find_players_by_positions([Position.WR, Position.TE])
        offensive_line = self._find_players_by_positions([Position.LT, Position.LG, Position.C, Position.RG, Position.RT])
        pass_rushers = self._find_defensive_players_by_positions([Position.DE, Position.DT, Position.OLB])
        defensive_backs = self._find_defensive_players_by_positions([Position.CB, Position.FS, Position.SS, Position.NCB])
        
        # QB attributes affect completion rate and decision making
        if quarterback and hasattr(quarterback, 'ratings'):
            qb_accuracy = quarterback.get_rating('overall')
            qb_pressure_rating = quarterback.get_rating('composure') or 75
            
            elite_acc_bonus = qb_modifiers.get('elite_accuracy_bonus', 0.08)
            good_acc_bonus = qb_modifiers.get('good_accuracy_bonus', 0.04)
            poor_acc_penalty = qb_modifiers.get('poor_accuracy_penalty', -0.06)
            elite_pressure_resist = qb_modifiers.get('elite_pressure_resistance', 0.7)
            good_pressure_resist = qb_modifiers.get('good_pressure_resistance', 0.85)
            poor_pressure_vuln = qb_modifiers.get('poor_pressure_vulnerability', 1.3)
            
            if qb_accuracy >= elite_threshold:  # Elite QB
                modified_params['completion_rate'] += elite_acc_bonus
                modified_params['int_rate'] *= elite_pressure_resist
            elif qb_accuracy >= good_threshold:  # Good QB  
                modified_params['completion_rate'] += good_acc_bonus
                modified_params['int_rate'] *= good_pressure_resist
            elif qb_accuracy <= poor_threshold:  # Poor QB
                modified_params['completion_rate'] += poor_acc_penalty  # Note: already negative
                modified_params['int_rate'] *= poor_pressure_vuln
            
            # Pressure handling affects sack rate
            if qb_pressure_rating >= very_good_threshold:
                modified_params['sack_rate'] *= 0.8
            elif qb_pressure_rating <= below_avg_threshold:
                modified_params['sack_rate'] *= 1.2
        
        # OL pass blocking affects pressure and sack rates
        ol_modifiers = player_config.get('offensive_line_modifiers', {})
        ol_elite_protection = ol_modifiers.get('elite_protection_bonus', 0.04)
        ol_poor_protection = ol_modifiers.get('poor_protection_penalty', -0.8)
        
        if offensive_line:
            ol_ratings = [p.get_rating('overall') for p in offensive_line if hasattr(p, 'ratings')]
            if ol_ratings:
                avg_ol_rating = sum(ol_ratings) / len(ol_ratings)
                average_threshold = thresholds.get('average', 75)
                
                if avg_ol_rating >= very_good_threshold:  # Elite OL
                    modified_params['sack_rate'] *= 0.7
                    modified_params['pressure_rate'] *= 0.8
                elif avg_ol_rating >= average_threshold:  # Good OL
                    modified_params['sack_rate'] *= 0.85
                    modified_params['pressure_rate'] *= 0.9
                elif avg_ol_rating <= poor_threshold:  # Poor OL
                    modified_params['sack_rate'] *= 1.3
                    modified_params['pressure_rate'] *= 1.2
        
        # Receiver quality affects completion rate and YAC
        receiver_modifiers = player_config.get('receiver_modifiers', {})
        elite_catch_bonus = receiver_modifiers.get('elite_catch_bonus', 0.8)
        good_catch_bonus = receiver_modifiers.get('good_catch_bonus', 0.9) 
        poor_catch_penalty = receiver_modifiers.get('poor_catch_penalty', 1.2)
        elite_yac_bonus = receiver_modifiers.get('elite_yac_bonus', 0.05)
        speed_threshold = receiver_modifiers.get('speed_threshold', 85)
        speed_yac_multiplier = receiver_modifiers.get('speed_yac_multiplier', 1.2)
        
        if receivers:
            wr_ratings = [p.get_rating('overall') for p in receivers if hasattr(p, 'ratings')]
            if wr_ratings:
                avg_wr_rating = sum(wr_ratings) / len(wr_ratings)
                if avg_wr_rating >= very_good_threshold:  # Elite receivers
                    modified_params['completion_rate'] += elite_yac_bonus
                    modified_params['avg_yac'] *= speed_yac_multiplier
                elif avg_wr_rating <= poor_threshold:  # Poor receivers  
                    modified_params['completion_rate'] -= 0.04
                    modified_params['avg_yac'] *= 0.8
        
        # Defensive back quality affects completion and interception rates
        defensive_modifiers = player_config.get('defensive_modifiers', {})
        elite_coverage_bonus = defensive_modifiers.get('elite_coverage_bonus', 0.9)
        poor_coverage_penalty = defensive_modifiers.get('poor_coverage_penalty', 1.4)
        elite_rush_bonus = defensive_modifiers.get('elite_rush_bonus', 1.3)
        good_rush_bonus = defensive_modifiers.get('good_rush_bonus', 1.08)
        poor_rush_penalty = defensive_modifiers.get('poor_rush_penalty', 0.7)
        
        if defensive_backs:
            db_ratings = [p.get_rating('overall') for p in defensive_backs if hasattr(p, 'ratings')]
            if db_ratings:
                avg_db_rating = sum(db_ratings) / len(db_ratings)
                if avg_db_rating >= very_good_threshold:  # Elite secondary
                    modified_params['completion_rate'] *= elite_coverage_bonus
                    modified_params['int_rate'] *= poor_coverage_penalty
                    modified_params['deflection_rate'] *= elite_rush_bonus
                elif avg_db_rating <= poor_threshold:  # Poor secondary
                    modified_params['completion_rate'] *= good_rush_bonus
                    modified_params['int_rate'] *= poor_rush_penalty
        
        return modified_params
    
    def _determine_pressure_outcome(self, params: Dict) -> Dict:
        """
        Determine if QB is sacked or pressured
        
        Returns:
            Dictionary with pressure outcome details
        """
        sack_roll = random.random()
        pressure_roll = random.random()
        
        sacked = sack_roll < params['sack_rate']
        pressured = pressure_roll < params['pressure_rate'] and not sacked
        
        outcome = {
            'sacked': sacked,
            'pressured': pressured,
            'clean_pocket': not (sacked or pressured)
        }
        
        if sacked:
            # Sack yardage loss - use configured range
            mechanics_config = config.get_play_mechanics_config('pass_play')
            sack_mechanics = mechanics_config.get('sack_mechanics', {})
            min_sack_yards = sack_mechanics.get('min_yards_lost', 5)
            max_sack_yards = sack_mechanics.get('max_yards_lost', 12)
            outcome['sack_yards'] = random.randint(min_sack_yards, max_sack_yards)
        
        return outcome
    
    def _select_target_receiver(self) -> Optional:
        """
        Select which receiver is targeted based on formation and routes
        
        Returns:
            Target receiver Player object or None
        """
        # Find available receivers
        receivers = self._find_players_by_positions([Position.WR, Position.TE])
        
        if not receivers:
            return None
        
        # Simple targeting based on position priority (can be enhanced later)
        # WRs get targeted more frequently than TEs in most formations
        wr_players = [p for p in receivers if p.primary_position == Position.WR]
        te_players = [p for p in receivers if p.primary_position == Position.TE]
        
        # Use configured target selection probability
        mechanics_config = config.get_play_mechanics_config('pass_play')
        target_selection = mechanics_config.get('target_selection', {})
        wr_target_probability = target_selection.get('primary_target_probability', 0.75)
        
        if wr_players and random.random() < wr_target_probability:
            return random.choice(wr_players)
        elif te_players:
            return random.choice(te_players)
        elif wr_players:
            return random.choice(wr_players)
        
        return None
    
    def _determine_pass_completion(self, params: Dict, target_receiver, pressure_outcome: Dict) -> Dict:
        """
        Determine if pass is completed and calculate yards
        
        Args:
            params: Modified formation parameters
            target_receiver: Selected receiver
            pressure_outcome: Pressure/sack outcome
            
        Returns:
            Dictionary with pass completion outcome
        """
        # Adjust completion rate based on pressure
        completion_rate = params['completion_rate']
        if pressure_outcome['pressured']:
            # Use configured pressure effect
            mechanics_config = config.get_play_mechanics_config('pass_play')
            pressure_effects = mechanics_config.get('pressure_effects', {})
            accuracy_impact = pressure_effects.get('accuracy_impact', 0.75)
            completion_rate *= accuracy_impact
        
        # Determine outcome type
        completion_roll = random.random()
        int_roll = random.random()
        deflection_roll = random.random()
        
        # Get configured time ranges and variances
        mechanics_config = config.get_play_mechanics_config('pass_play')
        time_ranges = mechanics_config.get('time_ranges', {})
        variance_config = config.get_variance_ranges_config('pass_play')
        
        # Check for interception first (worst outcome)
        if int_roll < params['int_rate']:
            int_time_min = time_ranges.get('interception_time_min', 2.5)
            int_time_max = time_ranges.get('interception_time_max', 4.0)
            
            return {
                'outcome_type': 'interception',
                'yards': 0,
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'intercepted': True
            }
        
        # Check for deflection/tip
        if deflection_roll < params['deflection_rate']:
            defl_time_min = time_ranges.get('deflection_time_min', 2.0)
            defl_time_max = time_ranges.get('deflection_time_max', 3.5)
            
            return {
                'outcome_type': 'deflected_incomplete', 
                'yards': 0,
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'pass_deflected': True
            }
        
        # Determine completion
        if completion_roll < completion_rate:
            # Completed pass - calculate yards using configured variances
            air_yards_variance = variance_config.get('air_yards_variance', 3.0)
            yac_variance = variance_config.get('yac_variance', 2.5)
            
            air_yards = max(1, int(random.gauss(params['avg_air_yards'], air_yards_variance)))
            yac = max(0, int(random.gauss(params['avg_yac'], yac_variance)))
            total_yards = air_yards + yac
            
            comp_time_min = time_ranges.get('completion_time_min', 2.5)
            comp_time_max = time_ranges.get('completion_time_max', 5.0)
            
            return {
                'outcome_type': 'completion',
                'yards': total_yards,
                'air_yards': air_yards,
                'yac': yac,
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'completed': True
            }
        else:
            # Incomplete pass
            inc_time_min = time_ranges.get('incompletion_time_min', 2.0)
            inc_time_max = time_ranges.get('incompletion_time_max', 3.5)
            
            return {
                'outcome_type': 'incomplete',
                'yards': 0,  
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'incomplete': True
            }
    
    def _attribute_player_stats(self, pass_outcome: Dict, penalty_result: Optional[PenaltyResult] = None) -> List[PlayerStats]:
        """
        Attribute comprehensive NFL statistics to individual players
        
        Args:
            pass_outcome: Pass play outcome details
            penalty_result: Penalty result if penalty occurred
            
        Returns:
            List of PlayerStats objects for players who recorded stats
        """
        player_stats = []
        
        # Find key players
        quarterback = self._find_player_by_position(Position.QB)
        offensive_line = self._find_players_by_positions([Position.LT, Position.LG, Position.C, Position.RG, Position.RT])
        pass_rushers = self._find_defensive_players_by_positions([Position.DE, Position.DT, Position.OLB])
        linebackers = self._find_defensive_players_by_positions([Position.MIKE, Position.SAM, Position.WILL, Position.ILB])
        defensive_backs = self._find_defensive_players_by_positions([Position.CB, Position.FS, Position.SS, Position.NCB])
        
        # QB Statistics
        if quarterback:
            qb_stats = create_player_stats_from_player(quarterback)
            qb_stats.pass_attempts = 1
            
            if pass_outcome.get('completed'):
                qb_stats.completions = 1
                qb_stats.passing_yards = pass_outcome.get('yards', 0)
                qb_stats.air_yards = pass_outcome.get('air_yards', 0)
            elif pass_outcome.get('intercepted'):
                qb_stats.interceptions_thrown = 1
            
            if pass_outcome.get('qb_sacked'):
                qb_stats.sacks_taken = 1
                qb_stats.sack_yards_lost = abs(pass_outcome.get('yards', 0))
            
            if pass_outcome.get('pressure_applied'):
                qb_stats.pressures_faced = 1
            
            player_stats.append(qb_stats)
        
        # Target Receiver Statistics
        target_receiver = pass_outcome.get('target_receiver')
        if target_receiver:
            receiver_stats = create_player_stats_from_player(target_receiver)
            receiver_stats.targets = 1
            
            if pass_outcome.get('completed'):
                receiver_stats.receptions = 1
                receiver_stats.receiving_yards = pass_outcome.get('yards', 0)
                receiver_stats.yac = pass_outcome.get('yac', 0)
            
            player_stats.append(receiver_stats)
        
        # Offensive Line Statistics (pass protection)
        if offensive_line and not pass_outcome.get('qb_sacked'):
            # Use configured blocking parameters
            mechanics_config = config.get_play_mechanics_config('pass_play')
            blocking_config = mechanics_config.get('blocking', {})
            ol_modifiers = config.get_player_attribute_config('pass_play').get('offensive_line_modifiers', {})
            
            min_blockers = blocking_config.get('min_blockers', 2)
            max_blockers = blocking_config.get('max_blockers', 3)
            pressure_allowance = ol_modifiers.get('pressure_allowance_base', 0.3)
            
            num_blockers = min(len(offensive_line), random.randint(min_blockers, max_blockers))
            selected_blockers = random.sample(offensive_line, num_blockers)
            
            for blocker in selected_blockers:
                blocker_stats = create_player_stats_from_player(blocker)
                blocker_stats.pass_blocks = 1
                if pass_outcome.get('pressure_applied'):
                    if random.random() < pressure_allowance:  # Configured chance blocker allowed pressure
                        blocker_stats.pressures_allowed = 1
                player_stats.append(blocker_stats)
        
        # Pass Rush Statistics
        if pass_rushers:
            if pass_outcome.get('qb_sacked'):
                # Use configured number of pass rushers for sacks
                mechanics_config = config.get_play_mechanics_config('pass_play')
                blocking_config = mechanics_config.get('blocking', {})
                min_rushers = blocking_config.get('min_pass_rushers', 1)
                max_rushers = blocking_config.get('max_pass_rushers', 2)
                
                sack_participants = random.sample(pass_rushers, min(len(pass_rushers), random.randint(min_rushers, max_rushers)))
                for rusher in sack_participants:
                    rusher_stats = create_player_stats_from_player(rusher)
                    rusher_stats.sacks = 1 if len(sack_participants) == 1 else 0.5  # Split sack
                    rusher_stats.tackles_for_loss = 1
                    player_stats.append(rusher_stats)
            elif pass_outcome.get('pressure_applied'):
                # Select 1 player who applied pressure
                pressure_player = random.choice(pass_rushers)
                pressure_stats = create_player_stats_from_player(pressure_player)
                pressure_stats.qb_pressures = 1
                
                # Use configured pressure-to-hit conversion rate
                pressure_effects = mechanics_config.get('pressure_effects', {})
                hit_conversion_rate = pressure_effects.get('pressure_to_hit_conversion', 0.4)
                
                if random.random() < hit_conversion_rate:
                    pressure_stats.qb_hits = 1
                player_stats.append(pressure_stats)
        
        # Defensive Back Statistics
        if defensive_backs:
            if pass_outcome.get('intercepted'):
                # Select DB who got the interception
                int_player = random.choice(defensive_backs)
                int_stats = create_player_stats_from_player(int_player)
                int_stats.interceptions = 1
                int_stats.passes_defended = 1
                player_stats.append(int_stats)
            elif pass_outcome.get('pass_deflected'):
                # Select DB who deflected the pass
                deflection_player = random.choice(defensive_backs)
                deflection_stats = create_player_stats_from_player(deflection_player)
                deflection_stats.passes_deflected = 1
                deflection_stats.passes_defended = 1
                player_stats.append(deflection_stats)
            elif pass_outcome.get('completed'):
                # Select tackling players
                tacklers = self._select_tacklers_after_catch(pass_outcome.get('yac', 0), defensive_backs + linebackers)
                for tackler_info in tacklers:
                    player, is_assisted = tackler_info
                    tackler_stats = create_player_stats_from_player(player)
                    tackler_stats.add_tackle(assisted=is_assisted)
                    player_stats.append(tackler_stats)
        
        return [stats for stats in player_stats if self._has_meaningful_stats(stats)]
    
    def _select_tacklers_after_catch(self, yac_yards: int, potential_tacklers: List) -> List[Tuple]:
        """
        Select which defenders made tackles after the catch
        
        Args:
            yac_yards: Yards after catch gained
            potential_tacklers: List of defensive players who could make tackles
            
        Returns:
            List of (player, is_assisted) tuples
        """
        if not potential_tacklers or yac_yards <= 0:
            return []
        
        tacklers = []
        
        # Use configured tackling parameters
        mechanics_config = config.get_play_mechanics_config('pass_play')
        tackling_config = mechanics_config.get('tackling', {})
        long_yac_threshold = tackling_config.get('long_yac_threshold', 8)
        assisted_tackle_prob = tackling_config.get('assisted_tackle_probability', 0.6)
        
        # More YAC = more likely to have multiple tacklers
        if yac_yards >= long_yac_threshold:
            # Long YAC: likely 1 primary tackler + 1 assisted
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
            
            # Configured chance of assisted tackle
            if random.random() < assisted_tackle_prob:
                remaining = [p for p in potential_tacklers if p != primary_tackler]
                if remaining:
                    assisted_tackler = random.choice(remaining)
                    tacklers.append((assisted_tackler, True))
        else:
            # Short YAC: likely just 1 tackler
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
        
        return tacklers
    
    def _has_meaningful_stats(self, player_stats: PlayerStats) -> bool:
        """
        Check if player has any meaningful statistics to report
        
        Args:
            player_stats: PlayerStats object to check
            
        Returns:
            True if player has stats worth reporting
        """
        stats_dict = player_stats.get_total_stats()
        return len(stats_dict) > 0
    
    # Helper methods (same pattern as RunPlaySimulator)
    def _find_player_by_position(self, position: str):
        """Find first player with specified position"""
        for player in self.offensive_players:
            if player.primary_position == position:
                return player
        return None
    
    def _find_players_by_positions(self, positions: List[str]) -> List:
        """Find all players matching specified positions"""
        found_players = []
        for player in self.offensive_players:
            if player.primary_position in positions:
                found_players.append(player)
        return found_players
    
    def _find_defensive_players_by_positions(self, positions: List[str]) -> List:
        """Find defensive players matching specified positions"""
        found_players = []
        for player in self.defensive_players:
            if player.primary_position in positions:
                found_players.append(player)
        return found_players