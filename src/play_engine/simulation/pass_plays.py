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
from typing import List, Tuple, Dict, Optional, Any
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from .base_simulator import BasePlaySimulator
from .modifiers import EnvironmentalModifiers
from .tackler_selection import TacklerSelector
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..play_types.base_types import PlayType
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config, get_pass_formation_matchup
from ..config.timing_config import NFLTimingConfig
from .execution_variance import apply_variance_to_params


class PassPlaySimulator(BasePlaySimulator):
    """Simulates pass plays with comprehensive NFL statistics and individual player attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str,
                 offensive_team_id: int = None, defensive_team_id: int = None,
                 coverage_scheme: str = None, momentum_modifier: float = 1.0,
                 weather_condition: str = "clear", crowd_noise_level: int = 0,
                 clutch_factor: float = 0.0, primetime_variance: float = 0.0,
                 is_away_team: bool = False, performance_tracker = None,
                 field_position: int = 50, down: int = None,
                 blitz_package: str = None, rusher_assignments = None):
        """
        Initialize pass play simulator

        Args:
            offensive_players: List of 11 offensive Player objects
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation string
            defensive_formation: Defensive formation string
            offensive_team_id: Team ID of the offensive team (1-32)
            defensive_team_id: Team ID of the defensive team (1-32)
            coverage_scheme: Defensive coverage scheme (e.g., "Prevent", "Cover-2", "Man-Free")
            momentum_modifier: Performance multiplier from team momentum (0.95 to 1.05)
            weather_condition: Weather condition ("clear", "rain", "snow", "heavy_wind")
            crowd_noise_level: Crowd noise intensity (0-100, 0=quiet, 100=deafening)
            clutch_factor: Clutch pressure level (0.0-1.0 from urgency analyzer)
            primetime_variance: Additional outcome variance for primetime games (0.0-0.15)
            is_away_team: Whether the offensive team is the away team (for crowd noise penalties)
            performance_tracker: Optional PlayerPerformanceTracker for hot/cold streaks (Tollgate 7)
            field_position: Current yard line (0-100, where 100 is opponent's goal line)
            blitz_package: Named blitz package (e.g., "four_man_base", "corner_blitz", "safety_blitz")
            rusher_assignments: RusherAssignments tracking which positions are rushing vs covering
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id
        self.coverage_scheme = coverage_scheme
        self.momentum_modifier = momentum_modifier  # Store momentum modifier
        self.field_position = field_position  # Store field position for touchdown detection

        # Environmental modifiers (Tollgate 6: Environmental & Situational Modifiers)
        self.weather_condition = weather_condition
        self.crowd_noise_level = crowd_noise_level
        self.down = down  # Current down (1-4)
        self.clutch_factor = clutch_factor
        self.primetime_variance = primetime_variance
        self.is_away_team = is_away_team

        # Variance & Unpredictability (Tollgate 7)
        self.performance_tracker = performance_tracker  # Hot/cold streak tracking

        # NEW: Blitz package and rusher assignments for dynamic sack attribution
        # When set, these enable:
        # - DBs to get sacks when they blitz (safety/corner blitzes)
        # - LBs in coverage to NOT get sacks (only rushing LBs eligible)
        self.blitz_package = blitz_package
        self.rusher_assignments = rusher_assignments

        # Load balancing configs (Tier 1 refactoring)
        self.receiver_targeting_config = config.get_receiver_targeting_config()
        self.environmental_modifiers_config = config.get_environmental_modifiers_config()
        self.qb_scramble_config = config.get_qb_scramble_config()
        self.situational_modifiers_config = config.get_situational_modifiers_config()

        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()

    def _get_actual_pass_rushers(self) -> List:
        """
        Get pass rushers based on blitz package - REPLACES static pool.

        When rusher_assignments is set, only positions marked as rushing are eligible.
        This allows:
        - DBs (CB, FS, SS) to get sacks when they blitz
        - LBs in coverage to be excluded from sack attribution

        Fallback: 4-man rush (DL only) when no blitz info is provided.

        Returns:
            List of defensive players who are actually rushing the passer
        """
        # Fallback: 4-man rush (DL only) when no blitz package info
        if not self.rusher_assignments:
            return self._get_field_defensive_players_by_positions([
                Position.DE, Position.DT, "defensive_end", "defensive_tackle",
                "nose_tackle", "edge", "leo"
            ])

        # Dynamic pool: only players whose position is marked as rushing
        all_defenders = self._get_all_field_defensive_players()
        actual_rushers = []

        for player in all_defenders:
            pos = getattr(player, 'primary_position', '')
            if self.rusher_assignments.is_position_rushing(pos):
                actual_rushers.append(player)

        # Safety fallback: if no rushers found, use DL
        if not actual_rushers:
            return self._get_field_defensive_players_by_positions([
                Position.DE, Position.DT, "defensive_end", "defensive_tackle"
            ])

        return actual_rushers

    def _get_all_field_defensive_players(self) -> List:
        """Get all 11 defensive players currently on the field."""
        return self.defensive_players[:11] if self.defensive_players else []

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

        # Phase 1B: Record QB performance for hot/cold streak tracking (Tollgate 7)
        if self.performance_tracker:
            qb = self._find_player_by_position(Position.QB)
            qb_id = getattr(qb, 'player_id', None) if qb else None

            if qb_id:
                outcome_type = pass_outcome.get('outcome_type', '')
                # Success = completion or scramble (4+ yards), Failure = incomplete/interception/sack
                if outcome_type == 'completion':
                    self.performance_tracker.record_success(qb_id)
                elif outcome_type == 'scramble':
                    # Scrambles are success if 4+ yards gained (first down conversion)
                    if pass_outcome.get('yards', 0) >= 4:
                        self.performance_tracker.record_success(qb_id)
                    else:
                        self.performance_tracker.record_failure(qb_id)
                elif outcome_type in ['incomplete', 'interception', 'sack', 'deflected_incomplete']:
                    self.performance_tracker.record_failure(qb_id)

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

        # Phase 3B: Track snaps for ALL players on the field (offensive and defensive)
        player_stats = self._track_snaps_for_all_players(player_stats)

        # Calculate touchdown outcome using base class method
        actual_yards, points_scored = self._calculate_touchdown_outcome(
            original_yards, final_yards, play_negated
        )

        # Create play summary with penalty information and player stats
        summary = self._create_play_summary(
            play_type=pass_outcome.get('outcome_type', 'pass'),
            actual_yards=actual_yards,
            time_elapsed=pass_outcome.get('time_elapsed', 3.0),
            points_scored=points_scored,
            player_stats=player_stats,
            penalty_result=penalty_result,
            original_yards=original_yards
        )

        # Add touchdown attribution if points were scored
        self._add_touchdown_attribution(summary)

        return summary

    def _add_touchdown_attribution(self, summary: PlayStatsSummary):
        """Add touchdown attribution to player stats if points were scored"""
        points = getattr(summary, 'points_scored', 0)

        if points == 6:
            # This is a touchdown - add touchdown stats to appropriate players
            for player_stat in summary.player_stats:
                if player_stat.rushing_attempts > 0:
                    # QB scrambled for a rushing touchdown
                    player_stat.add_rushing_touchdown()
                elif player_stat.passing_attempts > 0:
                    # QB threw the touchdown pass
                    player_stat.add_passing_touchdown()
                elif player_stat.receptions > 0:
                    # Receiver caught the touchdown pass
                    player_stat.add_receiving_touchdown()
    
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
                'completion_rate': 0.65, 'sack_rate': 0.09, 'pressure_rate': 0.24, 'deflection_rate': 0.0021, 'int_rate': 0.025,
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

        # Phase 3.5: Handle QB scramble (mobile QBs escaping pressure)
        if pressure_outcome.get('scrambled'):
            scramble_yards = pressure_outcome.get('scramble_yards', 0)
            return {
                'outcome_type': 'scramble',
                'yards': scramble_yards,
                'time_elapsed': round(random.uniform(3.0, 5.5), 1),  # Scrambles take longer
                'qb_scrambled': True,
                'pressure_applied': True,
                'scramble_yards': scramble_yards
            }

        # Phase 4: Select target receiver
        target_receiver = self._select_target_receiver()

        # Phase 4.5: Assign coverage defender for DB/LB grading
        coverage_assignment = self._assign_coverage_defender(target_receiver)

        # Phase 5: Determine pass completion outcome
        pass_result = self._determine_pass_completion(modified_params, target_receiver, pressure_outcome)

        # Add coverage assignment to result for stats attribution
        pass_result['coverage_assignment'] = coverage_assignment

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
        
        # Find key players (using field-limited method to only get on-field players)
        quarterback = self._find_player_by_position(Position.QB)
        receivers = self._get_field_offensive_players_by_positions([Position.WR, Position.TE])
        offensive_line = self._get_field_offensive_players_by_positions([Position.LT, Position.LG, Position.C, Position.RG, Position.RT])
        pass_rushers = self._get_field_defensive_players_by_positions([Position.DE, Position.DT, Position.OLB])
        defensive_backs = self._get_field_defensive_players_by_positions([Position.CB, Position.FS, Position.SS, Position.NCB])
        
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

            # NEW: Receiver catch rating directly affects completion rate
            # Get hands/catch ratings - elite hands = more catches
            catch_ratings = []
            for p in receivers:
                if hasattr(p, 'get_rating'):
                    hands = p.get_rating('hands') or p.get_rating('catching') or p.get_rating('overall')
                    if hands:
                        catch_ratings.append(hands)

            if catch_ratings:
                avg_catch_rating = sum(catch_ratings) / len(catch_ratings)
                # Elite hands (90+): +6% completion rate
                if avg_catch_rating >= 90:
                    modified_params['completion_rate'] += 0.06
                # Good hands (80-89): +3% completion rate
                elif avg_catch_rating >= 80:
                    modified_params['completion_rate'] += 0.03
                # Stone hands (<65): -4% completion rate
                elif avg_catch_rating < 65:
                    modified_params['completion_rate'] -= 0.04
        
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
                    modified_params['deflection_rate'] *= elite_coverage_bonus  # Fixed: was elite_rush_bonus (1.3), now 0.95
                elif avg_db_rating <= poor_threshold:  # Poor secondary
                    modified_params['completion_rate'] *= good_rush_bonus
                    modified_params['int_rate'] *= poor_rush_penalty

        # NEW: Apply prevent defense modifiers
        if self.coverage_scheme == "Prevent":
            # Prevent defense characteristics:
            # - 3-man rush (weak pressure) → drastically lower sack rate
            # - 6 DBs in soft zone → higher completion rate overall
            # - Deep coverage prioritized → prevent deep passes

            # Increase completion rate (easier to complete passes vs prevent)
            # Average increase of ~20% (range: +15% to +25% depending on pass type)
            modified_params['completion_rate'] *= 1.20  # +20% completion

            # Drastically reduced sack rate (3-man rush can't generate pressure)
            modified_params['sack_rate'] *= 0.4  # -60% sacks

            # Clamp completion rate to realistic maximum
            modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)

        # NEW: Apply momentum modifiers (applied after all other modifiers)
        if self.momentum_modifier != 1.0:
            # Momentum affects offensive performance:
            # - Positive momentum (+20 → 1.05): +5% completion, fewer sacks/INTs
            # - Negative momentum (-20 → 0.95): -5% completion, more sacks/INTs
            modified_params['completion_rate'] *= self.momentum_modifier
            modified_params['sack_rate'] /= self.momentum_modifier  # Inverse for negative stats
            modified_params['int_rate'] /= self.momentum_modifier   # Inverse for negative stats

            # Clamp to realistic ranges
            modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
            modified_params['sack_rate'] = max(modified_params['sack_rate'], 0.01)
            modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        # Apply 3rd down defensive pressure (from config - Tier 1 refactoring)
        if self.down == 3:
            third_down_config = self.situational_modifiers_config['third_down']
            modified_params['pressure_rate'] *= third_down_config['pressure_multiplier']  # +30% pressure on 3rd down
            modified_params['completion_rate'] *= third_down_config['completion_multiplier']  # -8% completion on 3rd down

        # NEW: Apply environmental modifiers (Tollgate 6: Environmental & Situational Modifiers)
        # Applied in order: weather → crowd noise → clutch performance

        # Step 6: Apply weather modifiers
        if self.weather_condition != "clear":
            modified_params = self._apply_weather_modifiers(modified_params)

        # Step 7: Apply crowd noise modifiers
        if self.crowd_noise_level > 0 and self.is_away_team:
            modified_params = self._apply_crowd_noise_modifiers(modified_params)

        # Step 8: Apply clutch performance modifiers
        if self.clutch_factor >= 0.5:
            modified_params = self._apply_clutch_modifiers(modified_params)

        # Step 9: Apply hot/cold streak modifiers (Tollgate 7: Variance & Unpredictability)
        # Applied LAST to layer on top of all other modifiers
        if self.performance_tracker and quarterback:
            qb_id = getattr(quarterback, 'player_id', None)
            if qb_id:
                performance_modifier = self.performance_tracker.get_modifier(qb_id)
                # Apply to completion rate (primary QB stat)
                modified_params['completion_rate'] *= performance_modifier
                # Inverse for negative stats (hot QBs throw fewer INTs)
                modified_params['int_rate'] /= performance_modifier

                # Clamp to realistic ranges
                modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
                modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        # Step 10: Apply execution variance (Tollgate 7: Variance & Unpredictability)
        # Applied FINAL to add natural randomness to all play outcomes
        # NOTE: Play concept not available yet, defaults to medium complexity (±8% variance)
        modified_params = apply_variance_to_params(modified_params, play_concept=None)

        return modified_params

    def _apply_weather_modifiers(self, params: Dict) -> Dict:
        """
        Apply weather condition modifiers to pass play parameters.

        Weather effects based on NFL research:
        - Rain: Wet ball reduces grip (-10% accuracy, -15% deep passes)
        - Snow: Visibility + wet ball (-15% accuracy, -25% deep passes)
        - Heavy Wind: Affects ball trajectory (-30% deep passes, +15% air yards variance)

        Args:
            params: Current parameters with player/coverage/momentum modifiers applied

        Returns:
            Modified parameters with weather effects applied
        """
        if self.weather_condition == "clear":
            return params  # No modifiers for clear weather

        modified_params = params.copy()

        # Get environmental modifiers from config (Tier 1 refactoring)
        env_config = self.environmental_modifiers_config

        # Determine if this is a deep pass based on avg_air_yards parameter
        # Deep passes (15+ air yards) are more affected by weather conditions
        avg_air_yards = modified_params.get('avg_air_yards', 8.0)
        deep_pass_threshold = env_config['deep_pass_threshold']
        is_deep_pass = avg_air_yards >= deep_pass_threshold

        if self.weather_condition == "rain":
            # Wet ball reduces accuracy
            rain_config = env_config['rain']
            modified_params['completion_rate'] *= rain_config['completion_multiplier']
            if is_deep_pass:
                modified_params['completion_rate'] *= rain_config['deep_completion_multiplier']
            modified_params['int_rate'] *= rain_config['int_multiplier']

        elif self.weather_condition == "snow":
            # Visibility issues + wet ball
            snow_config = env_config['snow']
            modified_params['completion_rate'] *= snow_config['completion_multiplier']
            if is_deep_pass:
                modified_params['completion_rate'] *= snow_config['deep_completion_multiplier']
            modified_params['int_rate'] *= snow_config['int_multiplier']
            modified_params['avg_air_yards'] *= snow_config['air_yards_multiplier']

        elif self.weather_condition == "heavy_wind":
            # Wind affects ball trajectory
            wind_config = env_config['heavy_wind']
            if is_deep_pass:
                modified_params['completion_rate'] *= wind_config['deep_completion_multiplier']
                modified_params['avg_air_yards'] *= wind_config['air_yards_multiplier']
            modified_params['int_rate'] *= wind_config['int_multiplier']

        # Apply red zone penalty - compressed field makes passing harder
        # NFL red zone completion rate is ~5-8% lower than overall average
        # Defense can play more aggressively with less deep threat
        red_zone_config = env_config['red_zone']
        if self.field_position >= red_zone_config['field_position_threshold']:
            modified_params['completion_rate'] *= red_zone_config['completion_multiplier']
            modified_params['int_rate'] *= red_zone_config['int_multiplier']

        # Clamp completion rate to realistic range (weather can't make it impossible)
        min_completion = env_config['minimum_completion_rate']
        modified_params['completion_rate'] = max(modified_params['completion_rate'], min_completion)

        return modified_params

    def _apply_crowd_noise_modifiers(self, params: Dict) -> Dict:
        """
        Apply crowd noise modifiers to pass play parameters.

        Crowd noise affects away team:
        - Communication breakdowns increase false starts (handled in penalty engine)
        - QB audibles harder to hear → more sacks (confusion)
        - Cadence timing disrupted → lower completion rate

        Noise level: 0-100 (0=empty stadium, 50=normal, 100=deafening)
        Effects scale linearly from 0% at noise=0 to max% at noise=100.

        Args:
            params: Current parameters with player/coverage/momentum/weather modifiers applied

        Returns:
            Modified parameters with crowd noise effects applied
        """
        if not self.is_away_team or self.crowd_noise_level == 0:
            return params  # Home team unaffected, or no crowd

        modified_params = params.copy()

        # Scale effects based on crowd noise (0-100 scale)
        noise_factor = self.crowd_noise_level / 100.0  # 0.0 to 1.0

        # Away team communication issues
        modified_params['sack_rate'] *= (1.0 + noise_factor * 0.10)     # Up to +10% sacks
        modified_params['completion_rate'] *= (1.0 - noise_factor * 0.05)  # Up to -5% completion
        modified_params['pressure_rate'] *= (1.0 + noise_factor * 0.08)    # Up to +8% pressure

        # False start penalty increase handled by PenaltyEngine (already configured)

        return modified_params

    def _apply_clutch_modifiers(self, params: Dict) -> Dict:
        """
        Apply composure-based performance modifiers in clutch situations.

        Clutch situations (urgency >= 0.5):
        - 4th quarter, close game (score diff ≤7)
        - Final 2 minutes
        - Overtime

        Clutch factor: 0.0-1.0 from GameSituationAnalyzer.get_urgency_level()
        - 0.0-0.4: Not clutch (no effect)
        - 0.5-0.7: Moderate clutch
        - 0.8-1.0: Extreme clutch

        Composure modifiers:
        - High composure (90+): Up to +10% in extreme clutch
        - Low composure (<60): Up to -15% in extreme clutch
        - Medium composure (60-89): Linear scaling

        Args:
            params: Current parameters with all prior modifiers applied

        Returns:
            Modified parameters with clutch performance effects applied
        """
        if self.clutch_factor < 0.5:
            return params  # Not a clutch situation

        modified_params = params.copy()

        # Get QB composure (offensive_players[0] is QB)
        qb = self.offensive_players[0] if self.offensive_players else None
        qb_composure = getattr(qb, 'composure', 75) if qb else 75  # Default 75 if missing

        # Calculate composure modifier based on QB's composure rating
        # Composure scale: <60 = poor, 60-89 = average, 90+ = elite
        if qb_composure >= 90:
            # Elite composure: positive modifier in clutch
            composure_modifier = 1.0 + (self.clutch_factor - 0.5) * 0.20  # Up to +10% at urgency 1.0
        elif qb_composure < 60:
            # Poor composure: negative modifier in clutch
            composure_modifier = 1.0 - (self.clutch_factor - 0.5) * 0.30  # Up to -15% at urgency 1.0
        else:
            # Average composure: minimal effect, scales linearly
            # Composure 75 = neutral (1.0), 60 = slightly negative, 89 = slightly positive
            composure_delta = (qb_composure - 75) / 30.0  # -0.5 to +0.47
            composure_modifier = 1.0 + composure_delta * (self.clutch_factor - 0.5) * 0.15

        # Apply composure modifier to key stats
        modified_params['completion_rate'] *= composure_modifier
        modified_params['int_rate'] /= composure_modifier  # Inverse: better composure = fewer INTs

        # Clamp to realistic ranges
        modified_params['completion_rate'] = min(modified_params['completion_rate'], 0.95)
        modified_params['int_rate'] = max(modified_params['int_rate'], 0.005)

        return modified_params

    def _determine_pressure_outcome(self, params: Dict) -> Dict:
        """
        Determine if QB is sacked, scrambles, or pressured.

        Scramble check happens when QB would be sacked - mobile QBs can escape
        and run for positive yards instead of taking the sack.

        Returns:
            Dictionary with pressure outcome details including scramble info
        """
        sack_roll = random.random()
        pressure_roll = random.random()

        # Get base rates from params
        sack_rate = params['sack_rate']
        pressure_rate = params['pressure_rate']

        # Apply blitz package modifiers - blitzes have higher sack/pressure rates
        # NFL Reality: 5-man blitz = ~1.3x sack rate, Cover-0 = ~1.6x
        if self.rusher_assignments and hasattr(self.rusher_assignments, 'blitz_package'):
            from ..play_types.blitz_types import get_blitz_package_definition
            pkg_def = get_blitz_package_definition(self.rusher_assignments.blitz_package)
            if pkg_def:
                sack_rate *= pkg_def.sack_rate_modifier
                pressure_rate *= pkg_def.pressure_rate_modifier

        # Check if QB would be sacked
        would_be_sacked = sack_roll < sack_rate

        # Check for pressure (more common than sacks, ~30% of plays)
        is_pressured = pressure_roll < pressure_rate

        # Mobile QBs can scramble in TWO scenarios:
        # 1. When pressured (designed scrambles / feeling pressure)
        # 2. When about to be sacked (escape scrambles)
        scrambled = False
        scramble_yards = 0

        if is_pressured or would_be_sacked:
            scramble_chance = self._calculate_scramble_chance()
            # Boost scramble chance if about to be sacked (survival instinct)
            if would_be_sacked:
                # Use config for sack escape mechanics (Tier 1 refactoring)
                scramble_config = self.qb_scramble_config['scramble_chance']
                scramble_chance = min(
                    scramble_config['max_sack_escape_chance'],
                    scramble_chance * scramble_config['sack_escape_multiplier']
                )

            if random.random() < scramble_chance:
                # QB scrambles instead of staying in pocket or taking sack
                scrambled = True
                scramble_yards = self._calculate_scramble_yards()
                would_be_sacked = False  # Escaped the sack if applicable

        sacked = would_be_sacked
        pressured = is_pressured and not sacked and not scrambled

        # For elite mobile QBs, small chance to scramble even without pressure
        # This represents designed QB runs, read-option keepers, etc.
        if not scrambled and not sacked and not is_pressured:
            qb = self._find_player_by_position(Position.QB)
            if qb:
                # Use None default to enable proper fallback chain
                mobility = qb.get_rating('mobility', None)
                if mobility is None:
                    mobility = qb.get_rating('speed', None) or 70

                # Use config for designed scramble mechanics (Tier 1 refactoring)
                designed_config = self.qb_scramble_config['scramble_chance']['designed_scramble']
                if mobility >= designed_config['mobility_threshold']:  # Only for truly mobile QBs (Lamar, Josh Allen, etc.)
                    # 2.5-7.5% chance based on mobility (85=2.5%, 95=7.5%)
                    designed_scramble_chance = (
                        (mobility - designed_config['base_mobility_offset']) /
                        designed_config['chance_divisor']
                    )
                    if random.random() < designed_scramble_chance:
                        scrambled = True
                        scramble_yards = self._calculate_scramble_yards()

        outcome = {
            'sacked': sacked,
            'pressured': pressured,
            'scrambled': scrambled,
            'scramble_yards': scramble_yards,
            'clean_pocket': not (sacked or pressured or scrambled)
        }

        if sacked:
            # Sack yardage loss - use configured range
            mechanics_config = config.get_play_mechanics_config('pass_play')
            sack_mechanics = mechanics_config.get('sack_mechanics', {})
            min_sack_yards = sack_mechanics.get('min_yards_lost', 5)
            max_sack_yards = sack_mechanics.get('max_yards_lost', 12)
            outcome['sack_yards'] = random.randint(min_sack_yards, max_sack_yards)

        return outcome

    def _calculate_scramble_chance(self) -> float:
        """
        Calculate QB's scramble probability based on mobility rating.

        Uses QB attributes from archetypes:
        - dual_threat_qb: mobility 80-95 → HIGH scramble chance (35-50%)
        - pocket_passer_qb: mobility 40-60 → LOW scramble chance (5-10%)

        Returns:
            Float probability (0.05 to 0.50) of QB scrambling when pressured
        """
        # Get scramble chance config (Tier 1 refactoring)
        scramble_config = self.qb_scramble_config['scramble_chance']

        qb = self._find_player_by_position(Position.QB)
        if not qb:
            return scramble_config['fallback_chance']  # Base 10% if no QB found

        # Try mobility first (from archetype), fallback to speed
        # Use None default to enable proper fallback chain (default=50 breaks 'or' logic)
        mobility = qb.get_rating('mobility', None)
        if mobility is None:
            mobility = qb.get_rating('speed', None) or 70

        composure = qb.get_rating('composure', None) or 75

        # Base scramble chance when pressured (from config)
        base_chance = scramble_config['base_chance']

        # Mobility modifiers based on archetype ranges (from config)
        mobility_thresholds = scramble_config['mobility_thresholds']
        if mobility >= mobility_thresholds['elite_mobile']['min_rating']:  # Elite mobile QB (Lamar Jackson, dual_threat_qb high-end)
            base_chance += mobility_thresholds['elite_mobile']['bonus']  # 40% total
        elif mobility >= mobility_thresholds['very_mobile']['min_rating']:  # Very mobile (Jalen Hurts, Josh Allen)
            base_chance += mobility_thresholds['very_mobile']['bonus']  # 33% total
        elif mobility >= mobility_thresholds['mobile']['min_rating']:  # Mobile (Kyler Murray, dual_threat_qb mean)
            base_chance += mobility_thresholds['mobile']['bonus']  # 27% total
        elif mobility >= mobility_thresholds['above_average']['min_rating']:  # Above average
            base_chance += mobility_thresholds['above_average']['bonus']  # 20% total
        elif mobility < mobility_thresholds['statue']['max_rating']:  # Statue (Tom Brady, pocket_passer_qb)
            base_chance += mobility_thresholds['statue']['penalty']  # 7% total

        # Composure bonus (better decisions under pressure) (from config)
        composure_config = scramble_config['composure_bonus']
        if composure >= composure_config['high_threshold']:
            base_chance += composure_config['high_bonus']
        elif composure >= composure_config['medium_threshold']:
            base_chance += composure_config['medium_bonus']

        # Clamp to min/max range (from config)
        return min(scramble_config['max_chance'], max(scramble_config['min_chance'], base_chance))

    def _calculate_scramble_yards(self) -> int:
        """
        Calculate yards gained on QB scramble.

        Uses QB speed and agility for:
        - Base yards (Gaussian distribution centered on 4.5)
        - Variance adjustment for explosive plays
        - 10% chance of big scramble (10-20 yards)

        Returns:
            Integer yards gained (0 to ~20)
        """
        # Get scramble yards config (Tier 1 refactoring)
        yards_config = self.qb_scramble_config['scramble_yards']

        qb = self._find_player_by_position(Position.QB)

        # Base scramble yards (Gaussian distribution) (from config)
        base_yards = yards_config['base_yards']
        variance = yards_config['base_variance']

        if qb:
            # Use None default to enable proper fallback (default=50 breaks 'or' logic)
            speed = qb.get_rating('speed', None) or 70
            agility = qb.get_rating('agility', None) or 70

            # Speed modifier (+/- 30% yards based on speed) (from config)
            # speed 90 = +0.20 multiplier, speed 50 = -0.20 multiplier
            speed_mod = (speed - yards_config['speed_modifier_offset']) / yards_config['speed_modifier_divisor']
            base_yards *= (1 + speed_mod)

            # Agility affects variance (more agile = more big plays) (from config)
            agility_thresholds = yards_config['agility_thresholds']
            if agility >= agility_thresholds['high']['min_rating']:
                variance += agility_thresholds['high']['variance_bonus']
            elif agility >= agility_thresholds['medium']['min_rating']:
                variance += agility_thresholds['medium']['variance_bonus']

        yards = max(0, round(random.gauss(base_yards, variance)))

        # Chance of big scramble (10-20 yards) for mobile QBs (from config)
        big_scramble_config = yards_config['big_scramble']
        if qb and qb.get_rating('speed') and qb.get_rating('speed') >= big_scramble_config['speed_threshold']:
            if random.random() < big_scramble_config['probability']:
                yards = random.randint(big_scramble_config['min_yards'], big_scramble_config['max_yards'])

        return yards

    def _select_target_receiver(self) -> Optional:
        """
        Select which receiver is targeted using realistic NFL target distribution

        Returns:
            Target receiver Player object or None
        """
        # Find all available pass catchers (only those on field based on formation)
        wr_players = self._get_field_offensive_players_by_positions([Position.WR])
        te_players = self._get_field_offensive_players_by_positions([Position.TE])
        rb_players = self._find_receiving_backs()

        # Create weighted target pool
        target_candidates = []

        # Get targeting weights from config (Tier 1 refactoring)
        weights_config = self.receiver_targeting_config['depth_chart_weights']

        # Add WRs with depth chart position weighting (WR1 > WR2 > WR3+)
        for idx, wr in enumerate(wr_players):
            if idx == 0:
                depth_weight = weights_config['wr1_weight']
            elif idx == 1:
                depth_weight = weights_config['wr2_weight']
            else:
                depth_weight = weights_config['wr3_plus_weight']
            weight = self._calculate_receiver_weight(wr, base_weight=depth_weight)
            target_candidates.append((wr, weight))

        # Add TEs with depth chart weighting (TE1 > TE2+)
        for idx, te in enumerate(te_players):
            depth_weight = weights_config['te1_weight'] if idx == 0 else weights_config['te2_plus_weight']
            weight = self._calculate_receiver_weight(te, base_weight=depth_weight)
            target_candidates.append((te, weight))

        # Add receiving RBs with lower weight (check-downs, screens)
        for rb in rb_players:
            weight = self._calculate_receiver_weight(rb, base_weight=weights_config['rb_checkdown_weight'])
            target_candidates.append((rb, weight))

        if not target_candidates:
            return None

        # Use weighted random selection
        return self._weighted_random_selection(target_candidates)

    def _find_receiving_backs(self) -> List:
        """Find running backs who can catch passes (only those on field)"""
        rb_players = self._get_field_offensive_players_by_positions([Position.RB])
        receiving_backs = []

        # Get receiving back threshold from config (Tier 1 refactoring)
        receiving_back_threshold = self.receiver_targeting_config['receiving_back_threshold']

        for rb in rb_players:
            # Check if RB has decent hands for receiving
            if hasattr(rb, 'ratings') and rb.get_rating('hands') >= receiving_back_threshold:
                receiving_backs.append(rb)
            elif hasattr(rb, 'ratings'):  # Include all RBs if hands rating exists
                receiving_backs.append(rb)

        return receiving_backs

    def _calculate_receiver_weight(self, player, base_weight: float = 1.0) -> float:
        """Calculate target weight based on player ratings and position"""
        weight = base_weight

        if hasattr(player, 'ratings'):
            # Get rating conversion from config (Tier 1 refactoring)
            hands_threshold = self.receiver_targeting_config['hands_rating_threshold']
            conversion_config = self.receiver_targeting_config['rating_to_weight_conversion']
            base_multiplier = conversion_config['base_multiplier']
            rating_divisor = conversion_config['rating_divisor']

            # Use hands, route running, or overall rating to adjust weight
            hands_rating = player.get_rating('hands')
            overall_rating = player.get_rating('overall')

            # Convert rating to weight multiplier
            primary_rating = hands_rating if hands_rating > hands_threshold else overall_rating
            rating_multiplier = base_multiplier + (primary_rating / rating_divisor)
            weight *= rating_multiplier

        # Minimum weight to ensure all players can be targeted (from config)
        min_weight = self.receiver_targeting_config['minimum_target_weight']
        return max(weight, min_weight)

    def _weighted_random_selection(self, candidates: List[Tuple]) -> Optional:
        """Select receiver using weighted random selection"""
        if not candidates:
            return None

        total_weight = sum(weight for _, weight in candidates)
        if total_weight <= 0:
            return random.choice(candidates)[0]  # Fallback to equal probability

        # Weighted random selection
        random_value = random.random() * total_weight
        current_weight = 0

        for player, weight in candidates:
            current_weight += weight
            if random_value <= current_weight:
                return player

        # Fallback (should rarely happen)
        return candidates[-1][0]

    def _assign_coverage_defender(self, target_receiver) -> Dict[str, Any]:
        """
        Assign coverage defender to the target receiver for DB/LB grading attribution.

        This method determines which defensive player was responsible for covering
        the targeted receiver, enabling accurate coverage statistics attribution.

        Args:
            target_receiver: The receiver who was targeted on this play

        Returns:
            Dictionary containing:
            - primary_defender: Player object of defender covering target
            - coverage_type: 'man' or 'zone'
            - coverage_scheme: Full scheme name (e.g., 'Cover-2', 'Man-Free')
        """
        if not target_receiver:
            return None

        # Get defensive backs and linebackers who can cover (only on-field players)
        defensive_backs = self._get_field_defensive_players_by_positions([
            Position.CB, Position.FS, Position.SS, Position.NCB,
            'cornerback', 'free_safety', 'strong_safety', 'safety', 'nickel_cornerback'
        ])
        linebackers = self._get_field_defensive_players_by_positions([
            Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB,
            'mike_linebacker', 'sam_linebacker', 'will_linebacker', 'inside_linebacker',
            'outside_linebacker', 'linebacker'
        ])

        all_coverage_defenders = defensive_backs + linebackers

        if not all_coverage_defenders:
            return None

        # Determine coverage type from scheme
        coverage_type = self._determine_coverage_type(self.coverage_scheme)

        # Select primary defender based on coverage type and receiver position
        if coverage_type == 'man':
            primary_defender = self._assign_man_coverage_defender(
                target_receiver, defensive_backs, linebackers
            )
        else:  # zone
            primary_defender = self._assign_zone_coverage_defender(
                target_receiver, defensive_backs, linebackers
            )

        return {
            'primary_defender': primary_defender,
            'coverage_type': coverage_type,
            'coverage_scheme': self.coverage_scheme or 'base'
        }

    def _determine_coverage_type(self, coverage_scheme: str) -> str:
        """
        Determine if coverage scheme is man or zone.

        Args:
            coverage_scheme: Coverage scheme name (e.g., 'Cover-2', 'Man-Free')

        Returns:
            'man' or 'zone'
        """
        if not coverage_scheme:
            return 'zone'  # Default to zone

        scheme_lower = coverage_scheme.lower()

        # Man coverage schemes
        man_schemes = ['man-free', 'man', 'cover-0', 'cover-1', 'press-man']
        if any(scheme in scheme_lower for scheme in man_schemes):
            return 'man'

        # Zone coverage schemes (default)
        return 'zone'

    def _assign_man_coverage_defender(self, target_receiver, defensive_backs: List, linebackers: List):
        """
        Assign man coverage defender using NFL matchup logic.

        Man coverage assignments:
        - Outside WRs → CBs (CB1 on WR1, CB2 on WR2)
        - Slot WRs → Nickel CBs or Safeties
        - TEs → Safeties or LBs (based on TE position)
        - RBs → LBs

        Args:
            target_receiver: Receiver being covered
            defensive_backs: Available DBs
            linebackers: Available LBs

        Returns:
            Assigned defender
        """
        receiver_pos = getattr(target_receiver, 'primary_position', Position.WR)

        # WRs → CBs (prioritize corners)
        if receiver_pos in [Position.WR, 'wide_receiver']:
            cbs = [db for db in defensive_backs
                   if getattr(db, 'primary_position', '') in [Position.CB, 'cornerback', Position.NCB, 'nickel_cornerback']]
            if cbs:
                return random.choice(cbs)
            # Fallback to any DB
            if defensive_backs:
                return random.choice(defensive_backs)

        # TEs → Safeties or LBs (60% safeties, 40% LBs)
        elif receiver_pos in [Position.TE, 'tight_end']:
            safeties = [db for db in defensive_backs
                       if getattr(db, 'primary_position', '') in [Position.FS, Position.SS, 'free_safety', 'strong_safety', 'safety']]
            if safeties and random.random() < 0.6:
                return random.choice(safeties)
            if linebackers:
                return random.choice(linebackers)
            if defensive_backs:
                return random.choice(defensive_backs)

        # RBs → LBs
        elif receiver_pos in [Position.RB, 'running_back', Position.FB, 'fullback']:
            if linebackers:
                return random.choice(linebackers)
            if defensive_backs:
                return random.choice(defensive_backs)

        # Default: any coverage defender
        all_defenders = defensive_backs + linebackers
        return random.choice(all_defenders) if all_defenders else None

    def _assign_zone_coverage_defender(self, target_receiver, defensive_backs: List, linebackers: List):
        """
        Assign zone coverage defender based on route depth estimation.

        Zone coverage assignments:
        - Deep routes (15+ yards) → Safeties in deep zones
        - Medium routes (8-14 yards) → LBs or CBs in underneath zones
        - Short routes (0-7 yards) → LBs in flat/curl zones

        Args:
            target_receiver: Receiver being covered
            defensive_backs: Available DBs
            linebackers: Available LBs

        Returns:
            Assigned defender based on zone responsibility
        """
        # Estimate route depth randomly (we don't know actual depth yet)
        # Deep: 40%, Medium: 35%, Short: 25%
        route_depth_roll = random.random()

        if route_depth_roll < 0.4:
            # Deep zone → Safety
            safeties = [db for db in defensive_backs
                       if getattr(db, 'primary_position', '') in [Position.FS, Position.SS, 'free_safety', 'strong_safety', 'safety']]
            if safeties:
                return random.choice(safeties)

        elif route_depth_roll < 0.75:
            # Medium zone → CB or LB (50/50)
            if random.random() < 0.5:
                cbs = [db for db in defensive_backs
                       if getattr(db, 'primary_position', '') in [Position.CB, 'cornerback', Position.NCB, 'nickel_cornerback']]
                if cbs:
                    return random.choice(cbs)
            if linebackers:
                return random.choice(linebackers)

        else:
            # Short zone → LB
            if linebackers:
                return random.choice(linebackers)

        # Fallback
        all_defenders = defensive_backs + linebackers
        return random.choice(all_defenders) if all_defenders else None

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

        # NEW: Check for drop BEFORE other outcomes (Phase 4: Drop Architecture Fix)
        # This ensures drop checks apply to all non-sack attempts (not just the 14.5% that reach the old location)
        # Target: 2.8 drops/game = 35 attempts × 8% drop rate
        if target_receiver:
            hands_rating = getattr(target_receiver, 'hands', 75)
            # Base drop rate: 3.5% of ALL non-sack attempts (not just incomplete passes)
            base_drop_rate = 0.035
            # Hands modifier: worse hands = more drops (75 is average)
            hands_modifier = (75 - hands_rating) / 300
            drop_chance = max(0.025, min(0.08, base_drop_rate + hands_modifier))

            drop_roll = random.random()
            if drop_roll < drop_chance:
                # Dropped pass - return immediately
                inc_time_min = time_ranges.get('incompletion_time_min', 2.0)
                inc_time_max = time_ranges.get('incompletion_time_max', 3.5)

                return {
                    'outcome_type': 'incomplete',
                    'yards': 0,
                    'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                    'target_receiver': target_receiver,
                    'incomplete': True,
                    'dropped': True,  # NEW FLAG - distinguishes drops from other incompletions
                    'pressure_applied': pressure_outcome['pressured']
                }

        # Check for interception first (worst outcome)
        if int_roll < params['int_rate']:
            int_time_min = time_ranges.get('interception_time_min', 2.5)
            int_time_max = time_ranges.get('interception_time_max', 4.0)

            return {
                'outcome_type': 'interception',
                'yards': 0,
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'intercepted': True,
                'pressure_applied': pressure_outcome['pressured']
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
                'pass_deflected': True,
                'pressure_applied': pressure_outcome['pressured']
            }
        
        # Determine completion
        if completion_roll < completion_rate:
            # Completed pass - calculate yards using configured variances
            air_yards_variance = variance_config.get('air_yards_variance', 3.0)
            yac_variance = variance_config.get('yac_variance', 2.5)

            air_yards = max(1, int(random.gauss(params['avg_air_yards'], air_yards_variance)))
            yac = max(0, int(random.gauss(params['avg_yac'], yac_variance)))

            # TE YAC penalty - TEs average less YAC than WRs (slower, tackled near LOS)
            if target_receiver and hasattr(target_receiver, 'position') and target_receiver.position == 'TE':
                yac = int(yac * 0.70)
            # WR YAC adjustment - reduce slightly to match NFL averages
            elif target_receiver and hasattr(target_receiver, 'position') and target_receiver.position == 'WR':
                yac = int(yac * 0.90)

            total_yards = air_yards + yac

            # NEW: Apply primetime variance (Tollgate 6: Environmental & Situational Modifiers)
            if self.primetime_variance > 0:
                variance_factor = 1.0 + random.gauss(0, self.primetime_variance)
                # Completions always gain at least 1 yard (0-yard catches are extremely rare in NFL)
                total_yards = max(1, int(total_yards * variance_factor))

            comp_time_min = time_ranges.get('completion_time_min', 2.5)
            comp_time_max = time_ranges.get('completion_time_max', 5.0)

            # Determine if receiver went out of bounds (for clock management)
            receiver_awareness = target_receiver.get_rating('awareness') if target_receiver and hasattr(target_receiver, 'get_rating') else 75
            # TODO: Get concept from play context when available
            concept = ''  # Placeholder - will be passed from context in future
            field_position = 50  # Placeholder - middle of field

            went_oob = self._determine_out_of_bounds(
                concept=concept,
                yards_gained=total_yards,
                receiver_awareness=receiver_awareness,
                field_position=field_position
            )

            return {
                'outcome_type': 'completion',
                'yards': total_yards,
                'air_yards': air_yards,
                'yac': yac,
                'time_elapsed': round(random.uniform(*NFLTimingConfig.get_pass_play_timing()), 1),
                'target_receiver': target_receiver,
                'completed': True,
                'went_out_of_bounds': went_oob,  # Track OOB for clock management
                'pressure_applied': pressure_outcome['pressured']
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
                'incomplete': True,
                'pressure_applied': pressure_outcome['pressured']
            }

    def _determine_out_of_bounds(
        self,
        concept: str,
        yards_gained: int,
        receiver_awareness: int,
        field_position: int
    ) -> bool:
        """
        Determine if receiver went out of bounds on this completion.

        Factors:
        - Route concept (sideline routes = higher OOB chance)
        - Yards gained (more yards = more OOB opportunity)
        - Receiver awareness (smart players stay inbounds)
        - Field position (near sidelines = higher chance)

        Args:
            concept: Play concept (sideline_routes, out_routes, etc.)
            yards_gained: Total yards on the play
            receiver_awareness: Receiver awareness rating (0-100)
            field_position: Current field position (0-100)

        Returns:
            True if receiver went out of bounds
        """
        import random

        # Base OOB probability
        base_oob_chance = 0.0

        # Sideline route concepts have high OOB probability
        sideline_concepts = ['sideline_routes', 'out_routes', 'comeback', 'corner', 'fade']
        if concept in sideline_concepts:
            base_oob_chance = 0.35  # 35% base for sideline routes
        else:
            # Non-sideline routes rarely go OOB
            base_oob_chance = 0.05  # 5% for crossing routes, slants, etc.

        # Adjust for yards gained (longer plays = more OOB opportunity)
        if yards_gained > 15:
            base_oob_chance *= 1.3  # +30% for big plays
        elif yards_gained > 25:
            base_oob_chance *= 1.5  # +50% for huge plays

        # Adjust for receiver awareness (smart players stay inbounds)
        if receiver_awareness >= 90:
            base_oob_chance *= 0.7  # Elite awareness: -30% OOB
        elif receiver_awareness >= 80:
            base_oob_chance *= 0.85  # Good awareness: -15% OOB
        elif receiver_awareness < 60:
            base_oob_chance *= 1.2  # Poor awareness: +20% OOB

        # Adjust for field position (near sidelines)
        # Field position: 0 = own goal line, 100 = opponent goal line
        # Hash marks are ~18 yards from sideline, so we don't have exact sideline data
        # Use randomness to simulate some plays being near sideline
        near_sideline = random.random() < 0.3  # 30% of plays near sideline
        if near_sideline:
            base_oob_chance *= 1.4  # +40% when near sideline

        # Cap at 80% max OOB chance
        final_oob_chance = min(0.8, base_oob_chance)

        # Roll for OOB
        went_oob = random.random() < final_oob_chance

        return went_oob

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

        # Find key players (using field-limited method to only get on-field players)
        quarterback = self._find_player_by_position(Position.QB)
        offensive_line = self._get_field_offensive_players_by_positions([Position.LT, Position.LG, Position.C, Position.RG, Position.RT])

        # Get pass rushers dynamically based on blitz package
        # - With blitz info: Only positions actually rushing (DBs can blitz, LBs may cover)
        # - Without blitz info: Fallback to 4-man rush (DL only)
        pass_rushers = self._get_actual_pass_rushers()
        linebackers = self._get_field_defensive_players_by_positions([
            Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB, "linebacker"
        ])
        defensive_backs = self._get_field_defensive_players_by_positions([
            Position.CB, Position.FS, Position.SS, Position.NCB, "cornerback", "safety"
        ])
        
        # QB Statistics
        if quarterback:
            qb_stats = create_player_stats_from_player(quarterback, team_id=self.offensive_team_id)
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

            # QB scramble rushing stats (mobile QBs escaping pressure)
            if pass_outcome.get('qb_scrambled'):
                qb_stats.pass_attempts = 0  # Scrambles are not pass attempts
                qb_stats.rushing_attempts = 1
                qb_stats.rushing_yards = pass_outcome.get('yards', 0)
                # Estimate yards after contact (typically 30-50% of scramble yards)
                scramble_yards = pass_outcome.get('yards', 0)
                if scramble_yards > 0:
                    yac_ratio = random.uniform(0.3, 0.5)
                    qb_stats.yards_after_contact = int(scramble_yards * yac_ratio)

            player_stats.append(qb_stats)
        
        # Target Receiver Statistics
        target_receiver = pass_outcome.get('target_receiver')
        if target_receiver:
            receiver_stats = create_player_stats_from_player(target_receiver, team_id=self.offensive_team_id)
            receiver_stats.targets = 1

            if pass_outcome.get('completed'):
                receiver_stats.receptions = 1
                yards = pass_outcome.get('yards', 0)
                receiver_stats.receiving_yards = yards
                receiver_stats.yac = pass_outcome.get('yac', 0)
                receiver_stats.receiving_long = yards
                # Track explosive plays (20+ yards)
                if yards >= 20:
                    receiver_stats.receiving_20_plus = 1

            player_stats.append(receiver_stats)
        
        # Comprehensive Offensive Line Pass Protection Statistics
        if offensive_line and pass_outcome:
            oline_stats = self._attribute_advanced_pass_protection_stats(pass_outcome, offensive_line)
            player_stats.extend(oline_stats)
        
        # Pass Rush Statistics
        if pass_rushers:
            if pass_outcome.get('qb_sacked'):
                # Use configured number of pass rushers for sacks
                mechanics_config = config.get_play_mechanics_config('pass_play')
                blocking_config = mechanics_config.get('blocking', {})
                min_rushers = blocking_config.get('min_pass_rushers', 1)
                max_rushers = blocking_config.get('max_pass_rushers', 2)

                # Skill-weighted sack attribution: better pass rushers get more sacks
                num_sack_participants = min(len(pass_rushers), random.randint(min_rushers, max_rushers))
                sack_participants = self._select_sack_participants_weighted(pass_rushers, num_sack_participants)

                for rusher in sack_participants:
                    rusher_stats = create_player_stats_from_player(rusher, team_id=self.defensive_team_id)
                    rusher_stats.sacks = 1 if len(sack_participants) == 1 else 0.5  # Split sack
                    rusher_stats.tackles_for_loss = 1
                    rusher_stats.add_tackle()  # Sacks are tackles
                    player_stats.append(rusher_stats)
            elif pass_outcome.get('pressure_applied'):
                # Select 1 player who applied pressure
                pressure_player = random.choice(pass_rushers)
                pressure_stats = create_player_stats_from_player(pressure_player, team_id=self.defensive_team_id)
                pressure_stats.qb_pressures = 1

                # Use configured pressure-to-hit conversion rate
                mechanics_config = config.get_play_mechanics_config('pass_play')
                pressure_effects = mechanics_config.get('pressure_effects', {})
                hit_conversion_rate = pressure_effects.get('pressure_to_hit_conversion', 0.4)

                if random.random() < hit_conversion_rate:
                    pressure_stats.qb_hits = 1
                player_stats.append(pressure_stats)
            elif pass_outcome.get('qb_scrambled'):
                # QB scramble tackle attribution - primarily LBs and defensive linemen
                scramble_yards = pass_outcome.get('yards', 0)
                target_yard_line = self.field_position + scramble_yards
                is_touchdown = target_yard_line >= 100

                if not is_touchdown and scramble_yards >= 0:
                    # Scramble tackles come from LBs (70% chance) and DL (30% chance)
                    all_defenders = pass_rushers + linebackers
                    if all_defenders:
                        # Weight LBs higher for scramble tackles (they pursue better)
                        weighted_defenders = []
                        for defender in all_defenders:
                            pos = getattr(defender, 'primary_position', '') or getattr(defender, 'position', '')
                            pos_str = str(pos).lower()
                            # Linebackers are better at pursuit tackles
                            if 'linebacker' in pos_str or pos_str in ['mike', 'sam', 'will', 'ilb', 'olb']:
                                weighted_defenders.extend([defender] * 3)  # 3x weight for LBs
                            else:
                                weighted_defenders.append(defender)  # 1x weight for DL

                        if weighted_defenders:
                            tackler = random.choice(weighted_defenders)
                            tackler_stats = create_player_stats_from_player(tackler, team_id=self.defensive_team_id)
                            tackler_stats.add_tackle(assisted=False)
                            player_stats.append(tackler_stats)

        # === PFF STATS: Pass Rush Win/Loss Tracking ===
        # Attribute pass rush attempts, wins, and double-teams to all pass rushers
        if pass_rushers and offensive_line:
            pressure_outcome = {
                'sacked': pass_outcome.get('qb_sacked', False),
                'pressured': pass_outcome.get('pressure_applied', False),
                'time_to_throw': pass_outcome.get('time_in_pocket', 3.0)
            }
            self._attribute_pass_rush_stats(
                pass_rushers=pass_rushers,
                offensive_linemen=offensive_line,
                pressure_outcome=pressure_outcome,
                player_stats=player_stats
            )

        # Defensive Back Statistics
        if defensive_backs:
            if pass_outcome.get('intercepted'):
                # Skill-weighted INT attribution: better coverage DBs get more INTs
                int_player = self._select_interception_player_weighted(defensive_backs)
                if int_player:
                    int_stats = create_player_stats_from_player(int_player, team_id=self.defensive_team_id)
                    int_stats.interceptions = 1
                    int_stats.passes_defended = 1
                    player_stats.append(int_stats)
            elif pass_outcome.get('pass_deflected'):
                # Skill-weighted deflection attribution (same logic as INTs)
                deflection_player = self._select_interception_player_weighted(defensive_backs)
                if deflection_player:
                    deflection_stats = create_player_stats_from_player(deflection_player, team_id=self.defensive_team_id)
                    deflection_stats.passes_deflected = 1
                    deflection_stats.passes_defended = 1
                    player_stats.append(deflection_stats)
            elif pass_outcome.get('dropped'):
                # NEW: Handle drops from Phase 4 architecture fix
                # These drops were already determined in _simulate_pass_outcome (before INT/deflection checks)
                # Directly attribute drop to receiver - no further probability checks needed
                target_receiver = pass_outcome.get('target_receiver')
                if target_receiver:
                    # Find and update existing receiver_stats
                    for stats in player_stats:
                        if (stats.player_name == target_receiver.name and
                            stats.position == target_receiver.primary_position):
                            stats.drops = 1
                            break
            elif pass_outcome.get('incomplete'):
                # Tight coverage forcing incompletion - attribute pass defended
                # NFL counts ~10-15% of incompletions as exceptional coverage deserving PD credit
                # The rest are drops, throwaways, miscommunication, poor throws, etc.
                if random.random() < 0.10:  # 10% of incompletions credited to exceptional coverage
                    coverage_player = self._select_interception_player_weighted(defensive_backs)
                    if coverage_player:
                        coverage_stats = create_player_stats_from_player(coverage_player, team_id=self.defensive_team_id)
                        coverage_stats.passes_defended = 1
                        player_stats.append(coverage_stats)
                else:
                    # Remaining 55% - attribute drops based on receiver hands rating
                    target_receiver = pass_outcome.get('target_receiver')
                    if target_receiver:
                        # Calculate drop probability (NFL avg: 4-6% of targets)
                        # Elite (95 hands) = 2% drops, Poor (50 hands) = 10% drops
                        hands_rating = getattr(target_receiver, 'hands', 75)

                        # Convert hands rating to drop chance - INCREASED FOR NFL ACCURACY
                        base_drop_rate = 0.10  # 10% baseline (was 0.05)
                        hands_modifier = (75 - hands_rating) / 400  # ±0.0625 adjustment (was /500)
                        drop_chance = max(0.03, min(0.20, base_drop_rate + hands_modifier))

                        if random.random() < drop_chance:
                            # Find and update existing receiver_stats
                            for stats in player_stats:
                                if (stats.player_name == target_receiver.name and
                                    stats.position == target_receiver.primary_position):
                                    stats.drops = 1
                                    break
            elif pass_outcome.get('completed'):
                # Check if this is a touchdown - you can't tackle someone who scored
                total_yards = pass_outcome.get('yards', 0)
                target_yard_line = self.field_position + total_yards
                is_touchdown = target_yard_line >= 100

                # Select tackling players - ONLY if not a touchdown
                if not is_touchdown:
                    yac_yards = pass_outcome.get('yac', 0)
                    tacklers = self._select_tacklers_after_catch(yac_yards, defensive_backs + linebackers)

                    # === PFF STATS: Generate missed tackles for YAC plays ===
                    if yac_yards >= 5 and target_receiver:
                        missed_tacklers = self._generate_missed_tackles_yac(
                            yac_yards=yac_yards,
                            receiver=target_receiver,
                            potential_tacklers=defensive_backs + linebackers,
                            actual_tacklers=[t[0] for t in tacklers]
                        )

                        for missed_defender in missed_tacklers:
                            missed_stats = create_player_stats_from_player(missed_defender, team_id=self.defensive_team_id)
                            missed_stats.add_missed_tackle()
                            player_stats.append(missed_stats)

                            # Track from receiver perspective (broken tackle)
                            receiver_tackle_stats = create_player_stats_from_player(target_receiver, team_id=self.offensive_team_id)
                            receiver_tackle_stats.add_tackle_faced(broken=True)
                            player_stats.append(receiver_tackle_stats)

                    # Attribute successful tackles and track from receiver perspective
                    for tackler_info in tacklers:
                        player, is_assisted = tackler_info
                        tackler_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
                        tackler_stats.add_tackle(assisted=is_assisted)
                        player_stats.append(tackler_stats)

                        # Track successful tackle from receiver perspective
                        if target_receiver:
                            receiver_tackle_stats = create_player_stats_from_player(target_receiver, team_id=self.offensive_team_id)
                            receiver_tackle_stats.add_tackle_faced(broken=False)
                            player_stats.append(receiver_tackle_stats)

        # ✅ NEW: Coverage Attribution Statistics (Phase 2 Grading)
        # Attribute coverage stats to the defender who was covering the targeted receiver
        coverage_assignment = pass_outcome.get('coverage_assignment')
        if coverage_assignment and coverage_assignment.get('primary_defender'):
            coverage_stats = self._attribute_coverage_stats(pass_outcome, coverage_assignment)
            if coverage_stats:
                player_stats.append(coverage_stats)

        # Validation removed for performance - team_id consistency should be guaranteed by player loading

        return [stats for stats in player_stats if self._has_meaningful_stats(stats)]

    def _attribute_advanced_pass_protection_stats(self, pass_outcome: Dict[str, Any], offensive_line: List) -> List[PlayerStats]:
        """
        Attribute comprehensive offensive line pass protection statistics

        Args:
            pass_outcome: Dictionary containing pass play results
            offensive_line: List of offensive line players

        Returns:
            List of PlayerStats objects for offensive linemen with comprehensive pass protection stats
        """
        oline_stats = []

        # Get configuration for pass protection
        mechanics_config = config.get_play_mechanics_config('pass_play')
        blocking_config = mechanics_config.get('blocking', {})

        # Extract pass outcome information
        qb_sacked = pass_outcome.get('qb_sacked', False)
        pressure_applied = pass_outcome.get('pressure_applied', False)
        yards_gained = pass_outcome.get('yards_gained', 0)
        time_in_pocket = pass_outcome.get('time_in_pocket', 2.5)  # Default average pocket time

        # Pass protection thresholds
        clean_pocket_threshold = 3.0    # 3+ seconds is clean pocket
        quick_pressure_threshold = 2.0  # Pressure in < 2 seconds is immediate
        pancake_threshold = 4.0         # 4+ second pockets can generate pancakes

        # Select participating pass protectors (all 5 O-line usually involved)
        num_protectors = min(len(offensive_line), 5)  # Standard 5-man protection
        selected_protectors = random.sample(offensive_line, num_protectors)

        for i, protector in enumerate(selected_protectors):
            protector_stats = create_player_stats_from_player(protector, team_id=self.offensive_team_id)
            protector_stats.pass_blocks = 1  # All protectors get pass block attempt

            # Calculate pass blocking efficiency based on outcome AND individual player ratings
            pass_blocking_efficiency = self._calculate_pass_blocking_efficiency(
                qb_sacked, pressure_applied, time_in_pocket, protector  # Pass player for individual ratings
            )
            protector_stats.set_pass_blocking_efficiency(pass_blocking_efficiency)

            # Handle specific outcomes
            if qb_sacked:
                # Sack attribution logic
                if time_in_pocket < quick_pressure_threshold:
                    # Immediate pressure - blame specific rusher's assigned blocker
                    if random.random() < 0.4:  # 40% chance this protector allowed sack
                        protector_stats.add_sack_allowed()
                elif time_in_pocket < 3.0:
                    # Normal pocket time - someone missed assignment or got beat
                    if random.random() < 0.3:  # 30% chance this protector allowed sack
                        protector_stats.add_sack_allowed()
                else:
                    # Coverage sack - good protection, no blame
                    pass

            elif pressure_applied:
                # Pressure attribution
                if time_in_pocket < quick_pressure_threshold:
                    # Quick pressure
                    if random.random() < 0.35:  # 35% chance this protector allowed pressure
                        protector_stats.add_pressure_allowed()
                elif time_in_pocket < 2.5:
                    # Hurry - QB rushed into quick throw
                    if random.random() < 0.25:  # 25% chance this protector allowed hurry
                        protector_stats.add_hurry_allowed()

            else:
                # Clean pocket - potential for pancakes and good grades
                if time_in_pocket >= clean_pocket_threshold:
                    protector_stats.add_block(successful=True)

                    # Pancake opportunities on very clean pockets
                    if time_in_pocket >= pancake_threshold:
                        pancake_chance = self._calculate_pass_pancake_chance(time_in_pocket, protector)
                        if random.random() < pancake_chance:
                            protector_stats.add_pancake()

                    # Chip blocks for RBs/TEs before releasing to routes
                    if yards_gained > 10 and random.random() < 0.15:  # 15% chance on good plays
                        protector_stats.add_chip_block()

                else:
                    # Adequate protection
                    protector_stats.add_block(successful=True)

            oline_stats.append(protector_stats)

        return oline_stats

    def _calculate_pass_blocking_efficiency(self, qb_sacked: bool, pressure_applied: bool,
                                          time_in_pocket: float, protector=None) -> float:
        """
        Calculate pass blocking efficiency grade based on INDIVIDUAL player ratings.

        Args:
            qb_sacked: Whether QB was sacked
            pressure_applied: Whether pressure was applied
            time_in_pocket: Time QB had in pocket
            protector: The player object (used for ratings and position)

        Returns:
            Pass blocking efficiency grade (0-100)
        """
        # Get individual player rating - this is the KEY differentiator
        player_rating = 75  # Default
        if protector is not None:
            if hasattr(protector, 'get_rating'):
                player_rating = protector.get_rating('pass_blocking') or protector.get_rating('pass_block') or 75
            elif hasattr(protector, 'ratings'):
                player_rating = protector.ratings.get('pass_blocking', protector.ratings.get('pass_block', 75))

        # Get player position for position-specific modifiers
        position = ''
        if protector is not None:
            position = getattr(protector, 'primary_position', getattr(protector, 'position', '')).lower()

        # Position-specific modifiers (tackles valued more in pass protection)
        position_modifiers = {
            'left_tackle': 5,   # Blind side protection premium
            'lt': 5,
            'right_tackle': 3,  # Pass rush side
            'rt': 3,
            'center': 2,        # Mental/awareness premium
            'c': 2,
            'left_guard': 0,    # Interior blockers
            'lg': 0,
            'right_guard': 0,
            'rg': 0,
        }
        position_bonus = position_modifiers.get(position, 0)

        # Base grade calculation - starts with player rating influence
        # Rating of 75 = neutral (no adjustment), 90 = +6, 60 = -6
        rating_adjustment = (player_rating - 75) * 0.4

        # Outcome-based grade (team outcome affects all, but rating modifies impact)
        if qb_sacked:
            if time_in_pocket < 2.0:
                outcome_grade = 25.0  # Very poor - immediate pressure sack
            elif time_in_pocket < 2.5:
                outcome_grade = 35.0  # Poor - quick pressure sack
            else:
                outcome_grade = 60.0  # Coverage sack - not blocker's fault
            # Better players handle sacks better (less blame)
            rating_impact = rating_adjustment * 0.5  # Reduced impact on bad outcomes
        elif pressure_applied:
            if time_in_pocket < 2.0:
                outcome_grade = 40.0  # Poor - immediate pressure
            elif time_in_pocket < 2.5:
                outcome_grade = 50.0  # Below average - quick pressure
            else:
                outcome_grade = 65.0  # Average - late pressure
            rating_impact = rating_adjustment * 0.7
        else:
            # Clean pocket grades based on time given
            if time_in_pocket >= 4.0:
                outcome_grade = 90.0  # Excellent
            elif time_in_pocket >= 3.5:
                outcome_grade = 80.0  # Very good
            elif time_in_pocket >= 3.0:
                outcome_grade = 70.0  # Good
            else:
                outcome_grade = 60.0  # Adequate
            rating_impact = rating_adjustment  # Full impact on good outcomes

        # Combine all factors
        base_grade = outcome_grade + rating_impact + position_bonus

        # Add LARGER randomness for individual variation (±8 instead of ±3)
        grade = base_grade + random.uniform(-8.0, 8.0)

        return max(0.0, min(100.0, grade))

    def _calculate_pass_pancake_chance(self, time_in_pocket: float, protector) -> float:
        """
        Calculate chance of pancake block on pass protection

        Args:
            time_in_pocket: Time QB had in pocket
            protector: The protecting player

        Returns:
            Probability of pancake (0.0 to 1.0)
        """
        base_chance = 0.0

        # Pancakes more likely on very clean pockets
        if time_in_pocket >= 5.0:
            base_chance = 0.15  # 15% chance on huge pocket
        elif time_in_pocket >= 4.0:
            base_chance = 0.08  # 8% chance on excellent pocket
        elif time_in_pocket >= 3.5:
            base_chance = 0.04  # 4% chance on very good pocket

        # Adjust based on player attributes
        if hasattr(protector, 'ratings'):
            strength = protector.get_rating('strength') if hasattr(protector, 'get_rating') else 70
            pass_block = protector.get_rating('pass_block') if hasattr(protector, 'get_rating') else 70

            if strength >= 90 and pass_block >= 85:
                base_chance *= 1.8  # Elite combo
            elif strength >= 85 or pass_block >= 85:
                base_chance *= 1.3  # One elite attribute
            elif strength <= 60 and pass_block <= 60:
                base_chance *= 0.3  # Poor combo

        return min(0.2, base_chance)  # Cap at 20% max

    def _select_tacklers_after_catch(self, yac_yards: int, potential_tacklers: List) -> List[Tuple]:
        """
        Select which defenders made tackles after the catch with position-weighted probabilities.

        Pass play tackle distribution (differs from run plays):
        - Defensive Backs (CBs/Safeties): 70% (in coverage, closest to catch point)
        - Linebackers: 25% (second level, pursuit angles)
        - Defensive Line: 5% (rare, only on short completions)

        Args:
            yac_yards: Yards after catch gained
            potential_tacklers: List of defensive players who could make tackles

        Returns:
            List of (player, is_assisted) tuples
        """
        if not potential_tacklers:
            return []

        tacklers = []

        # Use configured tackling parameters
        mechanics_config = config.get_play_mechanics_config('pass_play')
        tackling_config = mechanics_config.get('tackling', {})
        long_yac_threshold = tackling_config.get('long_yac_threshold', 8)
        assisted_tackle_prob = tackling_config.get('assisted_tackle_probability', 0.6)

        # All completions get a primary tackler
        primary_tackler = self._select_pass_tackler_by_position_weight(potential_tacklers)
        tacklers.append((primary_tackler, False))

        # Assisted tackle probability varies by YAC
        # NFL reality: ~30-40% of tackles are assisted (reduced from 40-50%)
        if yac_yards >= long_yac_threshold:
            # Long YAC: moderate chance of assisted tackle (pursuit)
            effective_assist_prob = assisted_tackle_prob * 0.7  # REDUCED from 1.0 to 0.7 (42%)
        else:
            # Short/no YAC: low chance of assisted tackle
            effective_assist_prob = assisted_tackle_prob * 0.3  # REDUCED from 0.5 to 0.3 (18%)

        if random.random() < effective_assist_prob:
            remaining = [p for p in potential_tacklers if p != primary_tackler]
            if remaining:
                assisted_tackler = self._select_pass_tackler_by_position_weight(remaining)
                tacklers.append((assisted_tackler, True))

        return tacklers

    def _select_sack_participants_weighted(self, pass_rushers: List, num_participants: int) -> List:
        """
        Select sack participants using skill-weighted probabilities.

        Elite pass rushers (high pass_rush/overall rating) are more likely to get sacks.
        NFL Reality: Myles Garrett gets 15 sacks/season, average DT gets 2-3.

        Blitz Surprise Factor: When DBs or LBs blitz, they often come FREE (unblocked)
        because the offense wasn't expecting the pressure. This is why DB blitzes
        result in sacks ~9% of the time in the NFL despite DBs having lower pass rush skills.

        Weighting formula:
        - Base weight = player's pass_rush rating (or overall if unavailable)
        - Position bonus: EDGE/DE +10, OLB +5, DT +0, ILB -5
        - Blitz surprise bonus: DBs get +25, LBs get +15 (represents unblocked rushes)
        - Elite (90+) gets 1.5x weight multiplier (reduced from 2x to not overpower blitzers)
        - Poor (<65) gets 0.5x weight multiplier

        Args:
            pass_rushers: List of defensive players who can get sacks
            num_participants: Number of players to select (1 or 2)

        Returns:
            List of selected players for sack credit
        """
        if not pass_rushers:
            return []

        if len(pass_rushers) <= num_participants:
            return pass_rushers

        # Calculate weights for each pass rusher
        weights = []
        for rusher in pass_rushers:
            # Get pass rush rating (or overall as fallback)
            rating = 70  # Default
            if hasattr(rusher, 'get_rating'):
                rating = rusher.get_rating('pass_rush') or rusher.get_rating('power_moves') or \
                         rusher.get_rating('finesse_moves') or rusher.get_rating('overall') or 70
            elif hasattr(rusher, 'ratings'):
                rating = rusher.ratings.get('pass_rush', rusher.ratings.get('overall', 70))

            # Position-based bonus and blitz surprise factor
            # NFL Reality: ~63% of sacks from DL, ~28% from LB, ~9% from DB
            # DBs get sacks through surprise (unblocked) rather than skill
            pos = getattr(rusher, 'primary_position', '').lower()

            # Calculate position bonus based on natural pass rushing ability
            # and blitz surprise factor (unblocked rushers are very effective)
            # Blitz surprise factors calibrated to achieve NFL sack distribution:
            # DL: ~63%, LB: ~28%, DB: ~9%
            if pos in ['defensive_end', 'de', 'edge', 'leo']:
                position_bonus = 10   # Primary edge rushers - always rush
                blitz_surprise = 1.0  # No surprise (expected)
            elif pos in ['defensive_tackle', 'dt', 'nose_tackle', 'nt']:
                position_bonus = 0    # Interior rushers - always rush
                blitz_surprise = 1.0  # No surprise
            elif pos in ['outside_linebacker', 'olb']:
                position_bonus = 5    # Edge rushers/blitzers
                blitz_surprise = 15.0 # Was 11.0 - LBs need higher win rate on blitz plays
            elif pos in ['free_safety', 'fs', 'strong_safety', 'ss', 'safety']:
                position_bonus = 0    # Low natural rush ability (neutral)
                blitz_surprise = 7.0  # Was 9.0 - DBs unblocked but reduce to balance LB
            elif pos in ['cornerback', 'cb', 'nickel_cornerback', 'ncb']:
                position_bonus = 0    # Low natural rush ability
                blitz_surprise = 6.5  # Was 8.5 - Reduce CB to shift sacks to LB
            elif pos in ['inside_linebacker', 'ilb', 'middle_linebacker', 'mlb',
                        'mike', 'will', 'sam', 'linebacker', 'lb', 'mike_linebacker',
                        'will_linebacker', 'sam_linebacker']:
                position_bonus = 0    # Neutral - A-gap blitzes are quick paths to QB
                blitz_surprise = 16.0 # Was 12.0 - A-gap/interior blitzes often completely unblocked
            else:
                position_bonus = -10  # Unknown position
                blitz_surprise = 1.0

            # Calculate weight: rating + position bonus, then multiply by surprise factor
            base_weight = (rating + position_bonus) * blitz_surprise

            # Elite/poor multipliers (DL only - blitzing players already got bonus from surprise)
            if rating >= 90 and blitz_surprise == 1.0:  # Only for base rushers (DL)
                base_weight *= 1.3  # Elite DL still get bonus, but smaller
            elif rating < 65 and blitz_surprise == 1.0:  # Only penalize poor DL, not blitzing LB/DB
                base_weight *= 0.5  # Poor base rushers rarely get sacks

            weights.append(max(1, base_weight))  # Minimum weight of 1

        # Weighted selection without replacement
        selected = []
        remaining_rushers = list(pass_rushers)
        remaining_weights = list(weights)

        for _ in range(num_participants):
            if not remaining_rushers:
                break

            # Normalize weights
            total_weight = sum(remaining_weights)
            normalized = [w / total_weight for w in remaining_weights]

            # Select one player
            chosen = random.choices(remaining_rushers, weights=normalized, k=1)[0]
            selected.append(chosen)

            # Remove from pool for next selection
            idx = remaining_rushers.index(chosen)
            remaining_rushers.pop(idx)
            remaining_weights.pop(idx)

        return selected

    def _select_interception_player_weighted(self, defensive_backs: List):
        """
        Select the DB who gets the interception using skill-weighted probabilities.

        Elite coverage players (high coverage/awareness rating) are more likely to get INTs.
        NFL Reality: Top CBs like Sauce Gardner get 5-6 INTs/season, average DBs get 1-2.

        Weighting formula:
        - Base weight = player's coverage rating (or overall if unavailable)
        - Position bonus: CB +10 (more targets), FS +5 (centerfield), SS +0
        - Elite (90+) gets 2x weight multiplier
        - Poor (<65) gets 0.5x weight multiplier

        Args:
            defensive_backs: List of DBs who could make the interception

        Returns:
            Selected player for interception credit
        """
        if not defensive_backs:
            return None

        if len(defensive_backs) == 1:
            return defensive_backs[0]

        # Calculate weights for each DB
        weights = []
        for db in defensive_backs:
            # Get coverage rating (or overall as fallback)
            rating = 70  # Default
            if hasattr(db, 'get_rating'):
                rating = db.get_rating('man_coverage') or db.get_rating('zone_coverage') or \
                         db.get_rating('awareness') or db.get_rating('play_recognition') or \
                         db.get_rating('overall') or 70
            elif hasattr(db, 'ratings'):
                rating = db.ratings.get('man_coverage', db.ratings.get('zone_coverage',
                         db.ratings.get('awareness', db.ratings.get('overall', 70))))

            # Position-based bonus (CBs face more targets, get more INT opportunities)
            pos = getattr(db, 'primary_position', '').lower()
            if pos in ['cornerback', 'cb']:
                position_bonus = 10  # CBs get most interceptions
            elif pos in ['free_safety', 'fs']:
                position_bonus = 5   # Centerfield position, good INT opportunities
            elif pos in ['strong_safety', 'ss']:
                position_bonus = 0   # More run support focused
            else:
                position_bonus = 0

            # Calculate weight
            base_weight = rating + position_bonus

            # Elite/poor multipliers
            if rating >= 90:
                base_weight *= 2.0  # Elite DBs dominate INT totals
            elif rating >= 85:
                base_weight *= 1.5
            elif rating < 65:
                base_weight *= 0.5  # Poor DBs rarely get INTs

            weights.append(max(1, base_weight))  # Minimum weight of 1

        # Weighted selection
        total_weight = sum(weights)
        normalized = [w / total_weight for w in weights]
        chosen = random.choices(defensive_backs, weights=normalized, k=1)[0]

        return chosen

    def _select_pass_tackler_by_position_weight(self, potential_tacklers: List):
        """
        Select a tackler for pass plays using position AND skill-weighted probabilities.

        Pass plays differ from run plays - DBs are primary tacklers:
        - Defensive Backs: 55% base weight (covering receivers, closest to catch point)
        - Linebackers: 30% base weight (zone drops, underneath coverage)
        - Defensive Line: 15% base weight (screens, short completions, pursuit)

        Within each group, players are weighted by tackle rating.
        Elite tacklers (90+) get 2x multiplier, poor tacklers (<65) get 0.5x.

        Args:
            potential_tacklers: List of defensive players

        Returns:
            Selected player based on position and skill-weighted probability
        """
        if not potential_tacklers:
            return None

        # Track tackles per player per game (reset at start of game)
        if not hasattr(self, '_tackle_counts'):
            from collections import defaultdict
            self._tackle_counts = defaultdict(int)

        # Categorize tacklers by position
        # Separate coverage LBs from EDGE rushers for proper tackle attribution
        defensive_backs = []
        coverage_lbs = []
        edge_rushers = []
        defensive_line = []

        db_positions = ['cornerback', 'cb', 'safety', 'free_safety', 'strong_safety', 'fs', 'ss', 'nickel_cornerback', 'ncb']
        # Split linebacker positions: coverage LBs vs EDGE rushers
        coverage_lb_positions = ['mike_linebacker', 'sam_linebacker', 'will_linebacker', 'linebacker',
                                 'inside_linebacker', 'ilb']
        edge_lb_positions = ['outside_linebacker', 'olb']  # EDGE pass rushers
        dl_positions = ['defensive_end', 'defensive_tackle', 'nose_tackle', 'de', 'dt', 'nt', 'edge']

        for player in potential_tacklers:
            pos = player.primary_position.lower()
            if pos in db_positions:
                defensive_backs.append(player)
            elif pos in coverage_lb_positions:
                coverage_lbs.append(player)
            elif pos in edge_lb_positions:
                edge_rushers.append(player)
            elif pos in dl_positions:
                defensive_line.append(player)

        def get_tackle_weight(player, base_position_weight: float, group_size: int) -> float:
            """Calculate skill-weighted tackle probability for a player."""
            # Get tackle rating (or related attributes as fallback)
            # Prioritize run-stopping attributes over pass rush attributes
            rating = 70  # Default
            if hasattr(player, 'get_rating'):
                rating = player.get_rating('tackle') or \
                         player.get_rating('run_defense') or \
                         player.get_rating('pursuit') or \
                         player.get_rating('play_recognition') or \
                         player.get_rating('overall') or 70
            elif hasattr(player, 'ratings'):
                rating = player.ratings.get('tackle',
                         player.ratings.get('run_defense',
                         player.ratings.get('pursuit',
                         player.ratings.get('overall', 70))))

            # Base weight from position group
            base_weight = base_position_weight / group_size

            # Skill multiplier - elite tacklers get slight edge, not dominance
            if rating >= 90:
                skill_mult = 1.3  # REDUCED from 2.0 to 1.3 (elite, not dominant)
            elif rating >= 85:
                skill_mult = 1.15  # REDUCED from 1.5 to 1.15
            elif rating >= 75:
                skill_mult = 1.0
            elif rating >= 65:
                skill_mult = 0.85  # INCREASED from 0.75 to 0.85
            else:
                skill_mult = 0.7  # INCREASED from 0.5 to 0.7

            # Calculate base weight with skill multiplier
            final_weight = base_weight * skill_mult

            # Apply diminishing returns based on tackles already made this game
            player_key = getattr(player, 'player_id', player.name)
            tackles_made = self._tackle_counts.get(player_key, 0)

            # Progressive reduction to prevent unrealistic accumulation (Phase 3: more aggressive)
            if tackles_made >= 10:
                final_weight *= 0.2  # 80% reduction after 10 tackles (extreme rarity)
            elif tackles_made >= 8:
                final_weight *= 0.4  # 60% reduction after 8 tackles (elite max)
            elif tackles_made >= 6:
                final_weight *= 0.7  # 30% reduction after 6 tackles (good performance)
            # No reduction for 0-5 tackles (normal range)

            return final_weight

        # Build weighted selection pool with skill-based weights
        candidates = []
        weights = []

        # Defensive Backs: 55% base weight (in coverage, closest to catch point)
        if defensive_backs:
            for db in defensive_backs:
                candidates.append(db)
                weights.append(get_tackle_weight(db, 0.55, len(defensive_backs)))

        # Coverage Linebackers: 25% base weight (zone drops, underneath coverage)
        if coverage_lbs:
            for lb in coverage_lbs:
                candidates.append(lb)
                weights.append(get_tackle_weight(lb, 0.25, len(coverage_lbs)))

        # EDGE Rushers: 5% base weight (pass rushing, rarely make tackles after catch)
        if edge_rushers:
            for edge in edge_rushers:
                candidates.append(edge)
                weights.append(get_tackle_weight(edge, 0.05, len(edge_rushers)))

        # Defensive Line: 10% base weight (screens, short completions)
        if defensive_line:
            for dl in defensive_line:
                candidates.append(dl)
                weights.append(get_tackle_weight(dl, 0.10, len(defensive_line)))

        # Fallback to uniform if no categorized players
        if not candidates:
            return random.choice(potential_tacklers)

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Use weighted random selection
        selected_player = random.choices(candidates, weights=normalized_weights, k=1)[0]

        # Update tackle count for diminishing returns tracking
        player_key = getattr(selected_player, 'player_id', selected_player.name)
        self._tackle_counts[player_key] += 1

        return selected_player
    
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

    def _attribute_coverage_stats(self, pass_outcome: Dict, coverage_assignment: Dict) -> Optional[PlayerStats]:
        """
        Attribute coverage statistics to the defender covering the targeted receiver.

        This enables accurate DB/LB grading by tracking coverage targets, completions,
        and yards allowed on a per-player basis.

        Args:
            pass_outcome: Pass play outcome details (completed, intercepted, etc.)
            coverage_assignment: Coverage assignment from _assign_coverage_defender()

        Returns:
            PlayerStats object for the coverage defender with coverage stats
        """
        if not coverage_assignment:
            return None

        primary_defender = coverage_assignment.get('primary_defender')
        if not primary_defender:
            return None

        # Create stats for coverage defender
        defender_stats = create_player_stats_from_player(primary_defender, team_id=self.defensive_team_id)

        # Determine if this was a target at the coverage defender
        was_targeted = pass_outcome.get('completed') or pass_outcome.get('incomplete') or \
                      pass_outcome.get('intercepted') or pass_outcome.get('pass_deflected')
        was_completed = pass_outcome.get('completed', False)
        yards_allowed = pass_outcome.get('yards', 0) if was_completed else 0
        was_pass_defended = pass_outcome.get('pass_deflected') or pass_outcome.get('intercepted')

        # Use the add_coverage_target helper from PlayerStats
        if was_targeted:
            defender_stats.add_coverage_target(
                completed=was_completed,
                yards=yards_allowed
            )

        return defender_stats

    def _generate_missed_tackles_yac(
        self,
        yac_yards: int,
        receiver,
        potential_tacklers: List,
        actual_tacklers: List
    ) -> List:
        """
        Generate missed tackle attempts on YAC plays.

        Used for PFF-style grading - tracks defenders who attempted but failed
        to bring down the receiver after the catch.

        Args:
            yac_yards: Yards after catch gained
            receiver: The receiver player object
            potential_tacklers: List of defensive players who could have attempted
            actual_tacklers: List of players who successfully made the tackle

        Returns:
            List of players who missed tackles on this play
        """
        missed = []

        # Base probability by YAC yards
        if yac_yards < 8:
            base_prob = 0.10  # 10% - short YAC, minimal opportunity to miss
        elif yac_yards < 15:
            base_prob = 0.25  # 25% - moderate YAC, likely evaded someone
        else:
            base_prob = 0.45  # 45% - big YAC, definitely broke tackles

        # Adjust for receiver agility/elusiveness
        agility = 70  # default
        if hasattr(receiver, 'get_rating'):
            agility = receiver.get_rating('agility', 70) or receiver.get_rating('elusiveness', 70) or 70

        agility_modifier = (agility - 70) / 100  # ±0.15 for ratings 55-85
        adjusted_prob = min(0.6, max(0.05, base_prob + agility_modifier))

        # Select potential miss candidates (exclude actual tacklers)
        candidates = [p for p in potential_tacklers if p not in actual_tacklers]

        # Roll for each candidate (max 2 missed tackles per play)
        for candidate in candidates[:3]:  # Check up to 3 candidates
            if len(missed) >= 2:
                break
            if random.random() < adjusted_prob:
                missed.append(candidate)
                adjusted_prob *= 0.5  # Diminishing returns for additional misses

        return missed

    def _attribute_pass_rush_stats(
        self,
        pass_rushers: List,
        offensive_linemen: List,
        pressure_outcome: Dict,
        player_stats: List
    ) -> None:
        """
        Attribute pass rush wins/losses to individual rushers.

        Used for PFF-style DL grading - tracks each pass rusher's success rate
        against offensive line protection.

        Args:
            pass_rushers: List of DL/Edge players rushing the passer
            offensive_linemen: List of OL players pass blocking
            pressure_outcome: Dict with 'sacked', 'pressured', 'time_to_throw'
            player_stats: List to append stats to
        """
        was_sacked = pressure_outcome.get('sacked', False)
        was_pressured = pressure_outcome.get('pressured', False)
        time_to_throw = pressure_outcome.get('time_to_throw', 3.0)

        # Calculate average OL pass block rating
        avg_ol_rating = 70
        if offensive_linemen:
            ratings = []
            for ol in offensive_linemen:
                if hasattr(ol, 'get_rating'):
                    rating = ol.get_rating('pass_block', None) or ol.get_rating('pass_blocking', None) or 70
                    ratings.append(rating)
                elif hasattr(ol, 'ratings'):
                    ratings.append(ol.ratings.get('pass_block', ol.ratings.get('pass_blocking', 70)))
            if ratings:
                avg_ol_rating = sum(ratings) / len(ratings)

        # Process each pass rusher
        for rusher in pass_rushers:
            # Get rusher's pass rush rating
            rush_rating = 70
            if hasattr(rusher, 'get_rating'):
                rush_rating = rusher.get_rating('pass_rush', None) or \
                              rusher.get_rating('power_moves', None) or \
                              rusher.get_rating('finesse_moves', None) or 70
            elif hasattr(rusher, 'ratings'):
                rush_rating = rusher.ratings.get('pass_rush',
                              rusher.ratings.get('power_moves',
                              rusher.ratings.get('finesse_moves', 70)))

            # Calculate win probability
            # Base 15% + rating differential impact
            base_win_prob = 0.15
            rating_diff = (rush_rating - avg_ol_rating) / 100  # ±0.15 range
            win_prob = max(0.05, min(0.40, base_win_prob + rating_diff))

            # Boost win probability if there was a sack/pressure
            if was_sacked:
                win_prob = min(0.60, win_prob + 0.20)
            elif was_pressured:
                win_prob = min(0.45, win_prob + 0.10)

            # Elite rushers (90+) get double-teamed more often
            double_team_prob = 0.10
            if rush_rating >= 90:
                double_team_prob = 0.35
            elif rush_rating >= 85:
                double_team_prob = 0.25
            elif rush_rating >= 80:
                double_team_prob = 0.18

            is_double_teamed = random.random() < double_team_prob
            won_rep = random.random() < win_prob

            # If double-teamed, harder to win but still possible
            if is_double_teamed:
                won_rep = random.random() < (win_prob * 0.4)  # 40% of normal win rate

            # Create stats and record
            rusher_stats = create_player_stats_from_player(rusher, team_id=self.defensive_team_id)
            rusher_stats.add_pass_rush_attempt(won=won_rep, double_teamed=is_double_teamed)
            player_stats.append(rusher_stats)

    # Inherited from BasePlaySimulator:
    # - _find_player_by_position() - find first offensive player with specified position
    # - _find_players_by_positions() - find all offensive players matching positions
    # - _find_defensive_players_by_positions() - find all defensive players matching positions
    # - _track_snaps_for_all_players() - formation-based snap tracking for 22 players