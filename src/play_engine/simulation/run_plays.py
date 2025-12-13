"""
Run play simulation with individual player statistics and penalty integration

Implements enhanced two-stage simulation with penalty system:
1. Determine play outcome using formation matchup matrix
2. Check for penalties and apply effects
3. Attribute individual player statistics based on final outcome
"""

import random
from typing import List, Tuple, Dict, Optional
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from .base_simulator import BasePlaySimulator
from .modifiers import EnvironmentalModifiers
from .tackler_selection import TacklerSelector
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..play_types.base_types import PlayType
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config, get_run_formation_matchup
from ..config.timing_config import NFLTimingConfig


class RunPlaySimulator(BasePlaySimulator):
    """Simulates run plays with individual player stat attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str,
                 offensive_team_id: int = None, defensive_team_id: int = None,
                 coverage_scheme: str = None, momentum_modifier: float = 1.0,
                 weather_condition: str = "clear", crowd_noise_level: int = 0,
                 is_away_team: bool = False, selected_ball_carrier=None,
                 performance_tracker=None, clutch_factor: float = 0.0,
                 primetime_variance: float = 0.0, field_position: int = 50):
        """
        Initialize run play simulator

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
            is_away_team: Whether the offensive team is the away team (for crowd noise penalties)
            selected_ball_carrier: Pre-selected RB for this play (for workload distribution)
            performance_tracker: PlayerPerformanceTracker for hot/cold streaks (Tollgate 7)
            clutch_factor: Clutch pressure level (0.0-1.0 from urgency analyzer, Tollgate 6)
            primetime_variance: Additional outcome variance for primetime games (0.0-0.15, Tollgate 6)
            field_position: Current yard line (0-100, where 100 is opponent's goal line)
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id
        self.coverage_scheme = coverage_scheme  # Store coverage scheme
        self.momentum_modifier = momentum_modifier  # Store momentum modifier
        self.field_position = field_position  # Store field position for touchdown detection

        # Environmental modifiers (Tollgate 6: Environmental & Situational Modifiers)
        self.weather_condition = weather_condition
        self.crowd_noise_level = crowd_noise_level
        self.is_away_team = is_away_team
        self.clutch_factor = clutch_factor
        self.primetime_variance = primetime_variance

        # Variance & Unpredictability (Tollgate 7)
        self.performance_tracker = performance_tracker

        # RB rotation - use pre-selected ball carrier if provided
        self.selected_ball_carrier = selected_ball_carrier

        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()
    
    def simulate_run_play(self, context: Optional[PlayContext] = None) -> PlayStatsSummary:
        """
        Simulate complete run play with individual player stats and penalty system
        
        Args:
            context: Game situation context for penalty determination
        
        Returns:
            PlayStatsSummary with play outcome, individual player stats, and penalty information
        """
        # Default context if none provided
        if context is None:
            context = PlayContext(
                play_type=PlayType.RUN,
                offensive_formation=self.offensive_formation,
                defensive_formation=self.defensive_formation
            )
        
        # Phase 1: Determine base play outcome
        original_yards, time_elapsed = self._determine_play_outcome()

        # Phase 1B: Check for fumble (before penalties, as fumbles happen during play)
        running_back = self._find_player_by_position(Position.RB)
        fumble_occurred, defense_recovered = self._check_fumble(running_back)

        if fumble_occurred and defense_recovered:
            # Fumble lost - create turnover result
            player_stats = self._attribute_player_stats(original_yards, penalty_result=None)
            player_stats = self._track_snaps_for_all_players(player_stats)

            # Add fumble stats to RB and forced fumble to defender
            self._attribute_fumble_stats(player_stats, running_back)

            summary = PlayStatsSummary(
                play_type="fumble",  # Engine detects 'fumble' in outcome for is_turnover
                yards_gained=original_yards,  # Yards gained before fumble
                time_elapsed=time_elapsed,
                points_scored=0
            )
            for stats in player_stats:
                summary.add_player_stats(stats)
            return summary

        # Phase 2A: Check for penalties and apply effects
        penalty_result = self.penalty_engine.check_for_penalty(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            context=context,
            original_play_yards=original_yards
        )
        
        # Determine final play result
        final_yards = penalty_result.modified_yards
        play_negated = penalty_result.play_negated

        # NEW (Tollgate 7): Record RB performance for hot/cold streak tracking
        if self.performance_tracker:
            running_back = self._find_player_by_position(Position.RB)
            if running_back:
                rb_id = getattr(running_back, 'player_id', None)
                if rb_id:
                    # Successful run: 4+ yards (above average)
                    if final_yards >= 4:
                        self.performance_tracker.record_success(rb_id)
                    # Failed run: 2 or fewer yards (below average)
                    else:
                        self.performance_tracker.record_failure(rb_id)

        # Phase 2B: Attribute player stats based on final outcome
        player_stats = self._attribute_player_stats(final_yards, penalty_result)

        # Phase 2C: Track snaps for ALL players on the field (offensive and defensive)
        player_stats = self._track_snaps_for_all_players(player_stats)

        # ✅ FIX 1: Detect touchdown BEFORE penalty adjustment
        # Check if ORIGINAL play reached end zone (penalties don't negate TDs in most cases)
        original_target = self.field_position + original_yards
        original_was_touchdown = original_target >= 100

        if original_was_touchdown and not play_negated:
            # TD stands - penalty will be enforced on PAT/kickoff
            actual_yards = 100 - self.field_position
            points_scored = 6
        else:
            # Non-TD play or play was negated by penalty - use penalty-adjusted yards
            target_yard_line = self.field_position + final_yards
            is_touchdown = target_yard_line >= 100

            if is_touchdown:
                actual_yards = 100 - self.field_position
                points_scored = 6
            else:
                actual_yards = final_yards
                points_scored = 0

        # Create play summary with penalty information
        summary = PlayStatsSummary(
            play_type=PlayType.RUN,
            yards_gained=actual_yards,
            time_elapsed=time_elapsed,
            points_scored=points_scored
        )
        
        # Add penalty information to summary if penalty occurred
        if penalty_result.penalty_occurred:
            summary.penalty_occurred = True
            summary.penalty_instance = penalty_result.penalty_instance
            summary.original_yards = original_yards
            summary.play_negated = play_negated
            # NEW: Attach enforcement result for downstream ball placement
            summary.enforcement_result = getattr(penalty_result, 'enforcement_result', None)
        
        for stats in player_stats:
            summary.add_player_stats(stats)

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
                    # Player had rushing attempts, credit them with rushing TD
                    player_stat.add_rushing_touchdown()
                    break  # Only one player should get the rushing TD
    
    def _determine_play_outcome(self) -> Tuple[int, float]:
        """
        Phase 1: Determine yards gained and time elapsed using matchup matrix + player attributes
        
        Returns:
            Tuple of (yards_gained, time_elapsed)
        """
        # Get base matchup parameters from configuration
        matchup_params = get_run_formation_matchup(self.offensive_formation, self.defensive_formation)
        
        if matchup_params:
            base_avg_yards = matchup_params.get('avg_yards', 3.5)
            base_variance = matchup_params.get('variance', 2.2)
        else:
            # Use configured default if specific matchup not found
            run_config = config.get_run_play_config()
            default_matchup = run_config.get('formation_matchups', {}).get('default_matchup', {})
            base_avg_yards = default_matchup.get('avg_yards', 3.5)
            base_variance = default_matchup.get('variance', 2.2)
        
        # Apply player attribute modifiers
        modified_avg_yards, modified_variance = self._apply_player_attribute_modifiers(
            base_avg_yards, base_variance)

        # Apply red zone penalty - compressed field makes yards harder to gain
        # NFL red zone rushing average is ~3.3 YPC vs ~4.4 YPC overall (~25% reduction)
        if self.field_position >= 80:  # Red zone (within 20 yards of goal)
            red_zone_penalty = 0.80  # 20% reduction in expected yards
            modified_avg_yards *= red_zone_penalty

        # Generate yards with modified distribution
        # Use round() instead of int() to preserve statistical mean (int() truncates, losing ~0.4 yards avg)
        # Allow TFL up to -3 yards for realistic tackles behind the line
        yards_gained = max(-3, round(random.gauss(modified_avg_yards, modified_variance)))
        
        # Time elapsed - use realistic NFL timing (includes huddle, play clock, execution)
        min_time, max_time = NFLTimingConfig.get_run_play_timing()
        time_elapsed = round(random.uniform(min_time, max_time), 1)
        
        return yards_gained, time_elapsed
    
    def _apply_player_attribute_modifiers(self, base_avg_yards: float, base_variance: float) -> Tuple[float, float]:
        """
        Modify play outcome based on real player attributes
        
        Args:
            base_avg_yards: Base expected yards from formation matchup
            base_variance: Base variance from formation matchup
            
        Returns:
            Tuple of (modified_avg_yards, modified_variance)
        """
        offensive_modifier = 1.0
        defensive_modifier = 1.0
        
        # Get configured thresholds and modifiers
        player_config = config.get_player_attribute_config('run_play')
        thresholds = player_config.get('rating_thresholds', {})
        rb_modifiers = player_config.get('running_back_modifiers', {})
        
        elite_threshold = thresholds.get('elite', 90)
        good_threshold = thresholds.get('good', 80) 
        poor_threshold = thresholds.get('poor', 65)
        
        elite_bonus = rb_modifiers.get('elite_bonus', 0.30)
        good_bonus = rb_modifiers.get('good_bonus', 0.15)
        poor_penalty = rb_modifiers.get('poor_penalty', -0.20)
        
        # Find key offensive players and their impact
        running_back = self._find_player_by_position(Position.RB)
        if running_back and hasattr(running_back, 'ratings'):
            # RB overall rating impacts yards gained
            rb_overall = running_back.get_rating('overall')
            if rb_overall >= elite_threshold:  # Elite RB
                offensive_modifier += elite_bonus
            elif rb_overall >= good_threshold:  # Good RB
                offensive_modifier += good_bonus
            elif rb_overall <= poor_threshold:  # Poor RB
                offensive_modifier += poor_penalty  # Note: poor_penalty is already negative

            # NEW (Tollgate 7): Apply RB hot/cold streak modifier
            if self.performance_tracker:
                rb_id = getattr(running_back, 'player_id', None)
                if rb_id:
                    performance_modifier = self.performance_tracker.get_modifier(rb_id)
                    offensive_modifier *= performance_modifier  # 0.85 (ICE_COLD), 1.0 (NEUTRAL), or 1.15 (ON_FIRE)
        
        # Find key defensive players and their impact
        lb_modifiers = player_config.get('linebacker_modifiers', {})
        lb_elite_bonus = lb_modifiers.get('elite_bonus', 0.25)
        lb_good_bonus = lb_modifiers.get('good_bonus', 0.10)
        lb_poor_penalty = lb_modifiers.get('poor_penalty', -0.15)
        
        linebackers = self._find_defensive_players_by_positions([Position.MIKE, Position.SAM, Position.WILL])
        if linebackers:
            # Average LB rating impacts run defense
            lb_ratings = []
            for lb in linebackers:
                if hasattr(lb, 'ratings'):
                    lb_ratings.append(lb.get_rating('overall'))
            
            if lb_ratings:
                avg_lb_rating = sum(lb_ratings) / len(lb_ratings)
                if avg_lb_rating >= elite_threshold:  # Elite LB corps
                    defensive_modifier += lb_elite_bonus
                elif avg_lb_rating >= good_threshold:  # Good LB corps
                    defensive_modifier += lb_good_bonus
                elif avg_lb_rating <= poor_threshold:  # Poor LB corps
                    defensive_modifier += lb_poor_penalty  # Note: already negative

        # Find defensive line and their run defense impact
        # Elite DL (like Myles Garrett) should reduce yards allowed
        dl_modifiers = player_config.get('defensive_line_modifiers', {
            'elite_bonus': 0.15,
            'good_bonus': 0.08,
            'poor_penalty': -0.10
        })
        dl_elite_bonus = dl_modifiers.get('elite_bonus', 0.15)
        dl_good_bonus = dl_modifiers.get('good_bonus', 0.08)
        dl_poor_penalty = dl_modifiers.get('poor_penalty', -0.10)

        defensive_line = self._find_defensive_players_by_positions([
            Position.DE, Position.DT, Position.NT, "defensive_end", "defensive_tackle", "nose_tackle"
        ])
        if defensive_line:
            # Average DL run_defense rating impacts run stopping (DL dominate at line of scrimmage)
            dl_ratings = []
            for dl in defensive_line:
                if hasattr(dl, 'ratings'):
                    # Prefer run_defense, fall back to overall
                    if hasattr(dl, 'get_rating'):
                        dl_rating = dl.get_rating('run_defense') or dl.get_rating('overall') or 70
                    else:
                        dl_rating = dl.ratings.get('run_defense', dl.ratings.get('overall', 70))
                    dl_ratings.append(dl_rating)

            if dl_ratings:
                avg_dl_rating = sum(dl_ratings) / len(dl_ratings)
                if avg_dl_rating >= elite_threshold:  # Elite DL corps (e.g., Myles Garrett)
                    defensive_modifier += dl_elite_bonus
                elif avg_dl_rating >= good_threshold:  # Good DL corps
                    defensive_modifier += dl_good_bonus
                elif avg_dl_rating <= poor_threshold:  # Poor DL corps
                    defensive_modifier += dl_poor_penalty  # Note: already negative

        # Apply modifiers (offense increases yards, defense decreases yards)
        final_modifier = offensive_modifier / defensive_modifier
        modified_avg_yards = base_avg_yards * final_modifier

        # Use configured variance cap
        stats_config = config.get_statistical_attribution_config('run_play')
        variance_cap = stats_config.get('variance_cap', 1.2)
        modified_variance = base_variance * min(final_modifier, variance_cap)

        # NEW: Apply prevent defense modifiers
        if self.coverage_scheme == "Prevent":
            # Prevent defense is weak against the run:
            # - Only 3-4 players in the box (everyone else in deep coverage)
            # - Light box = easier running lanes, more explosive runs

            # Increase average yards per carry
            modified_avg_yards += 1.0  # +1.0 yards per carry

            # Increase variance (more explosive runs possible with light box)
            modified_variance *= 1.2  # +20% variance

        # NEW: Apply momentum modifiers (applied after player/coverage modifiers)
        if self.momentum_modifier != 1.0:
            # Momentum affects offensive running performance:
            # - Positive momentum (+20 → 1.05): +5% yards per carry
            # - Negative momentum (-20 → 0.95): -5% yards per carry
            modified_avg_yards *= self.momentum_modifier
            # Variance stays the same (momentum doesn't affect unpredictability)

        # NEW: Apply environmental modifiers (Tollgate 6: Environmental & Situational Modifiers)
        # Applied in order: weather → crowd noise

        # Step 6: Apply weather modifiers
        if self.weather_condition in ['rain', 'snow']:
            # Wet conditions reduce run effectiveness (ball handling, footing)
            if self.weather_condition == 'rain':
                modified_avg_yards *= 0.95  # -5% yards in rain
            elif self.weather_condition == 'snow':
                modified_avg_yards *= 0.90  # -10% yards in snow
                modified_variance *= 1.15   # More slips and big plays

        # Step 7: Apply crowd noise modifiers (minimal for run plays)
        if self.is_away_team and self.crowd_noise_level > 0:
            # Crowd affects snap timing slightly
            noise_factor = self.crowd_noise_level / 100.0
            modified_avg_yards *= (1.0 - noise_factor * 0.03)  # Up to -3% yards

        return modified_avg_yards, modified_variance
    
    def _attribute_player_stats(self, yards_gained: int, penalty_result: Optional[PenaltyResult] = None) -> List[PlayerStats]:
        """
        Phase 2B: Attribute statistics to individual players based on final play outcome

        Args:
            yards_gained: Final yards gained on the play (after penalty effects)
            penalty_result: Penalty result if a penalty occurred

        Returns:
            List of PlayerStats objects for players who recorded stats
        """
        player_stats = []
        
        # Find key players by position
        running_back = self._find_player_by_position(Position.RB)
        offensive_line = self._find_players_by_positions([Position.LT, Position.LG, Position.C, Position.RG, Position.RT])

        # Include all linebacker variations (specific and generic)
        linebackers = self._find_defensive_players_by_positions([
            Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB, "linebacker"
        ])
        safeties = self._find_defensive_players_by_positions([Position.FS, Position.SS, "safety"])

        # Include defensive line for potential tackles behind the line
        defensive_line = self._find_defensive_players_by_positions([
            Position.DE, Position.DT, Position.NT, "defensive_end", "defensive_tackle", "nose_tackle"
        ])
        
        # Attribute RB stats
        if running_back:
            rb_stats = create_player_stats_from_player(running_back, team_id=self.offensive_team_id)
            rb_stats.add_carry(yards_gained)

            # Calculate yards after contact (YAC) for RB power/elusiveness grading
            # Contact typically occurs 40-60% into the run; YAC is yards gained after first hit
            if yards_gained > 0:
                # Calculate yards before contact (approximately 40-60% of total yards)
                yards_before_contact = int(yards_gained * random.uniform(0.4, 0.6))
                yac = max(0, yards_gained - yards_before_contact)

                # Adjust YAC based on RB elusiveness/power ratings if available
                if hasattr(running_back, 'ratings'):
                    elusiveness = running_back.get_rating('elusiveness') if hasattr(running_back, 'get_rating') else 70
                    # Higher elusiveness = more likely to gain extra YAC
                    if elusiveness >= 85:
                        yac = int(yac * 1.2)  # +20% YAC for elite elusiveness
                    elif elusiveness >= 80:
                        yac = int(yac * 1.1)  # +10% YAC for good elusiveness
                    elif elusiveness <= 60:
                        yac = int(yac * 0.85)  # -15% YAC for poor elusiveness

                rb_stats.add_yards_after_contact(yac)
            elif yards_gained <= 0:
                # Negative or zero yards - no yards after contact (tackled behind line)
                rb_stats.add_yards_after_contact(0)

            player_stats.append(rb_stats)
        
        # Attribute comprehensive offensive line stats
        if offensive_line:
            oline_stats = self._attribute_advanced_oline_stats(yards_gained, offensive_line)
            player_stats.extend(oline_stats)
        
        # Attribute defensive stats (tackles) - ONLY if not a touchdown
        # You can't tackle someone who scored - they crossed the goal line
        target_yard_line = self.field_position + yards_gained
        is_touchdown = target_yard_line >= 100

        if not is_touchdown:
            # All potential tacklers: linebackers, safeties, defensive line
            potential_tacklers = linebackers + safeties + defensive_line
            tacklers = self._select_tacklers(yards_gained, potential_tacklers)

            # === PFF STATS: Generate missed tackles based on yards gained ===
            missed_tacklers = self._generate_missed_tackles(
                yards_gained=yards_gained,
                ball_carrier=running_back,
                potential_tacklers=potential_tacklers,
                actual_tacklers=[t[0] for t in tacklers]  # Exclude actual tacklers
            )

            # Attribute missed tackles to defenders
            for missed_defender in missed_tacklers:
                missed_stats = create_player_stats_from_player(missed_defender, team_id=self.defensive_team_id)
                missed_stats.add_missed_tackle()
                player_stats.append(missed_stats)

                # Track from ball carrier perspective (broken tackle)
                rb_stats.add_tackle_faced(broken=True)

            # === Attribute successful tackles ===
            for tackler_info in tacklers:
                player, is_assisted = tackler_info
                tackler_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
                tackler_stats.add_tackle(assisted=is_assisted)

                # Add TFL for negative yardage plays
                if yards_gained < 0:
                    tackler_stats.tackles_for_loss = 1

                player_stats.append(tackler_stats)

                # Track from ball carrier perspective (successful tackle)
                rb_stats.add_tackle_faced(broken=False)

        # Add sacks for significant negative yardage plays (TFL of 5+ yards likely indicates sack)
        if yards_gained <= -5:
            # Defensive line players more likely to get sacks - use skill-weighted selection
            potential_sackers = defensive_line + [p for p in linebackers if "outside" in p.primary_position.lower()]
            if potential_sackers:
                sacker = self._select_tfl_sacker_weighted(potential_sackers)

                # Check if sacker already has stats object
                existing_stat = None
                for stat in player_stats:
                    if stat.player_name == sacker.name:
                        existing_stat = stat
                        break

                if existing_stat:
                    existing_stat.sacks += 1.0
                else:
                    sacker_stats = create_player_stats_from_player(sacker, team_id=self.defensive_team_id)
                    sacker_stats.sacks = 1.0
                    player_stats.append(sacker_stats)

        # Validation removed for performance - team_id consistency should be guaranteed by player loading

        return [stats for stats in player_stats if stats.get_total_stats()]

    def _attribute_advanced_oline_stats(self, yards_gained: int, offensive_line: List) -> List[PlayerStats]:
        """
        Attribute comprehensive offensive line statistics for run plays

        Args:
            yards_gained: Yards gained on the run play
            offensive_line: List of offensive line players

        Returns:
            List of PlayerStats objects for offensive linemen with comprehensive stats
        """
        oline_stats = []

        # Get configuration for O-line attribution
        stats_config = config.get_statistical_attribution_config('run_play')
        blocking_config = stats_config.get('blocking', {})

        # Base configuration values
        min_blockers = blocking_config.get('min_blockers', 3)
        max_blockers = blocking_config.get('max_blockers', 5)
        base_success_rate = blocking_config.get('base_success_rate', 0.75)

        # Advanced O-line thresholds
        pancake_threshold = 8    # 8+ yard runs can generate pancakes
        big_run_threshold = 15   # 15+ yard runs are "big runs"
        tfl_threshold = -2       # -2 yards or worse is potential missed assignment

        # Select participating blockers (more for longer runs)
        if yards_gained >= big_run_threshold:
            num_blockers = min(len(offensive_line), max_blockers)  # All hands on deck for big runs
        elif yards_gained >= pancake_threshold:
            num_blockers = min(len(offensive_line), random.randint(max_blockers-1, max_blockers))
        else:
            num_blockers = min(len(offensive_line), random.randint(min_blockers, max_blockers))

        selected_blockers = random.sample(offensive_line, num_blockers)

        for i, blocker in enumerate(selected_blockers):
            blocker_stats = create_player_stats_from_player(blocker, team_id=self.offensive_team_id)

            # Calculate run blocking grade based on play outcome AND individual player ratings
            run_blocking_grade = self._calculate_run_blocking_grade(yards_gained, blocker)  # Pass player for individual ratings
            blocker_stats.set_run_blocking_grade(run_blocking_grade)

            # Determine block outcome and advanced stats
            success_rate = base_success_rate + (yards_gained * 0.04)  # Better success rate for longer runs
            is_successful_block = random.random() < success_rate

            if is_successful_block:
                blocker_stats.add_block(successful=True)

                # Pancake opportunities on long runs
                if yards_gained >= pancake_threshold:
                    pancake_chance = self._calculate_pancake_chance(yards_gained, blocker)
                    if random.random() < pancake_chance:
                        blocker_stats.add_pancake()

                # Double team blocks on power runs (short yardage, goal line)
                if 1 <= yards_gained <= 4 and len(selected_blockers) >= 4:
                    if random.random() < 0.15:  # 15% chance of double team credit
                        blocker_stats.add_double_team_block()

                # Downfield blocks on big runs
                if yards_gained >= big_run_threshold and i < 2:  # Lead blockers
                    if random.random() < 0.3:  # 30% chance
                        blocker_stats.add_downfield_block()

            else:
                blocker_stats.add_block(successful=False)

                # Missed assignments on negative plays
                if yards_gained <= tfl_threshold:
                    if random.random() < 0.25:  # 25% chance of missed assignment on TFL
                        blocker_stats.add_missed_assignment()

            oline_stats.append(blocker_stats)

        return oline_stats

    def _calculate_run_blocking_grade(self, yards_gained: int, blocker=None) -> float:
        """
        Calculate run blocking grade based on play outcome AND INDIVIDUAL player ratings.

        Args:
            yards_gained: Yards gained on the play
            blocker: The player object (used for ratings and position)

        Returns:
            Grade from 0-100
        """
        # Get individual player rating - this is the KEY differentiator
        player_rating = 75  # Default
        if blocker is not None:
            if hasattr(blocker, 'get_rating'):
                player_rating = blocker.get_rating('run_blocking') or blocker.get_rating('run_block') or 75
            elif hasattr(blocker, 'ratings'):
                player_rating = blocker.ratings.get('run_blocking', blocker.ratings.get('run_block', 75))

        # Get player position for position-specific modifiers
        position = ''
        if blocker is not None:
            position = getattr(blocker, 'primary_position', getattr(blocker, 'position', '')).lower()

        # Position-specific modifiers (guards/center valued more in run blocking)
        position_modifiers = {
            'left_guard': 5,    # Run blocking premium
            'lg': 5,
            'right_guard': 4,   # Run blocking premium
            'rg': 4,
            'center': 3,        # Calls plays + run blocking
            'c': 3,
            'left_tackle': 0,   # Pass protection focused
            'lt': 0,
            'right_tackle': 0,  # Pass protection focused
            'rt': 0,
        }
        position_bonus = position_modifiers.get(position, 0)

        # Rating adjustment: Rating of 75 = neutral, 90 = +6, 60 = -6
        rating_adjustment = (player_rating - 75) * 0.4

        # Outcome-based grade (team outcome affects all, but rating modifies impact)
        if yards_gained >= 15:
            outcome_grade = 85.0  # Excellent
            rating_impact = rating_adjustment  # Full impact on good outcomes
        elif yards_gained >= 8:
            outcome_grade = 75.0  # Good
            rating_impact = rating_adjustment
        elif yards_gained >= 4:
            outcome_grade = 65.0  # Above average
            rating_impact = rating_adjustment
        elif yards_gained >= 1:
            outcome_grade = 55.0  # Slightly above average
            rating_impact = rating_adjustment * 0.8
        elif yards_gained == 0:
            outcome_grade = 45.0  # Below average
            rating_impact = rating_adjustment * 0.6
        elif yards_gained >= -2:
            outcome_grade = 35.0  # Poor
            rating_impact = rating_adjustment * 0.5  # Reduced impact on bad outcomes
        else:
            outcome_grade = 25.0  # Very poor
            rating_impact = rating_adjustment * 0.4

        # Combine all factors
        base_grade = outcome_grade + rating_impact + position_bonus

        # Add LARGER randomness for individual variation (±8 instead of ±5)
        grade = base_grade + random.uniform(-8.0, 8.0)

        return max(0.0, min(100.0, grade))

    def _calculate_pancake_chance(self, yards_gained: int, blocker) -> float:
        """
        Calculate chance of pancake block based on play outcome and player attributes

        Args:
            yards_gained: Yards gained on the play
            blocker: The blocking player

        Returns:
            Probability of pancake (0.0 to 1.0)
        """
        base_chance = 0.0

        # Base chance increases with yards gained
        if yards_gained >= 20:
            base_chance = 0.25  # 25% chance on huge runs
        elif yards_gained >= 15:
            base_chance = 0.15  # 15% chance on big runs
        elif yards_gained >= 10:
            base_chance = 0.08  # 8% chance on good runs
        elif yards_gained >= 8:
            base_chance = 0.04  # 4% chance on decent runs

        # Adjust based on player attributes if available
        if hasattr(blocker, 'ratings'):
            strength = blocker.get_rating('strength') if hasattr(blocker, 'get_rating') else 70
            physicality = blocker.get_rating('physicality') if hasattr(blocker, 'get_rating') else 70

            # Elite strength players get pancake bonus
            if strength >= 90:
                base_chance *= 1.5
            elif strength >= 80:
                base_chance *= 1.2
            elif strength <= 60:
                base_chance *= 0.5

        return min(0.3, base_chance)  # Cap at 30% max chance

    def _find_player_by_position(self, position: str):
        """
        Find player with specified position.

        For RB position, uses pre-selected ball carrier if available (for workload distribution).
        For other positions, returns first match.
        """
        # Use pre-selected ball carrier for RB if available (RB rotation system)
        if position == Position.RB and self.selected_ball_carrier is not None:
            return self.selected_ball_carrier

        # Default: find first matching player
        for player in self.offensive_players:
            if player.primary_position == position:
                return player
        return None
    
    # Inherited from BasePlaySimulator:
    # - _find_players_by_positions()
    # - _find_defensive_players_by_positions()
    
    def _select_tacklers(self, yards_gained: int, potential_tacklers: List) -> List[Tuple]:
        """
        Select which defenders made tackles based on yards gained with position-weighted probabilities.

        Realistic NFL tackle distribution:
        - Linebackers: 65% (primary run stoppers)
        - Safeties: 25% (second level, deep plays)
        - Defensive Line: 8% (TFLs, stuff plays only)
        - Cornerbacks: 2% (rare, mostly edge runs)

        Args:
            yards_gained: Yards gained on play
            potential_tacklers: List of defensive players who could make tackles

        Returns:
            List of (player, is_assisted) tuples
        """
        if not potential_tacklers:
            return []

        tacklers = []

        # Get configured tackling parameters
        stats_config = config.get_statistical_attribution_config('run_play')
        tackling_config = stats_config.get('tackling', {})
        long_run_threshold = tackling_config.get('long_run_threshold', 5)
        assisted_tackle_prob = tackling_config.get('assisted_tackle_probability', 0.6)

        # All runs get a primary tackler (pass yards_gained for TFL-aware weighting)
        primary_tackler = self._select_tackler_by_position_weight(potential_tacklers, yards_gained)
        tacklers.append((primary_tackler, False))

        # Assisted tackle probability varies by run length
        # NFL reality: ~40-50% of tackles are assisted (gang tackles common)
        if yards_gained >= long_run_threshold:
            # Long run: high chance of assisted tackle (pursuit angles)
            effective_assist_prob = assisted_tackle_prob
        else:
            # Short run: moderate chance of assisted tackle (pile tackles)
            effective_assist_prob = assisted_tackle_prob * 0.6

        if random.random() < effective_assist_prob:
            remaining = [p for p in potential_tacklers if p != primary_tackler]
            if remaining:
                assisted_tackler = self._select_tackler_by_position_weight(remaining, yards_gained)
                tacklers.append((assisted_tackler, True))

        return tacklers

    def _select_tackler_by_position_weight(self, potential_tacklers: List, yards_gained: int = 5):
        """
        Select a tackler using position AND skill-weighted probabilities.

        Weight distribution mirrors NFL reality, with dynamic DL weight for TFL situations:
        - Linebackers: 50% base weight (primary run stoppers), reduced to 35% on TFLs
        - Defensive Line: 25% base weight normally, 40% on TFL plays (DL dominate stuffs)
        - Safeties: 20% base weight (cleanup, deep plays)
        - Cornerbacks: 5% base weight (edge contain)

        Within each position group, players are weighted by their tackle/pursuit ratings.
        Elite tacklers (90+) get 2x multiplier, poor tacklers (<65) get 0.5x.

        Args:
            potential_tacklers: List of defensive players
            yards_gained: Yards gained on the play (used for TFL-aware weighting)

        Returns:
            Selected player based on position and skill-weighted probability
        """
        if not potential_tacklers:
            return None

        # Categorize tacklers by position
        linebackers = []
        safeties = []
        defensive_line = []
        cornerbacks = []

        lb_positions = ['mike_linebacker', 'sam_linebacker', 'will_linebacker', 'linebacker',
                       'inside_linebacker', 'outside_linebacker', 'ilb', 'olb']
        safety_positions = ['safety', 'free_safety', 'strong_safety', 'fs', 'ss']
        dl_positions = ['defensive_end', 'defensive_tackle', 'nose_tackle', 'de', 'dt', 'nt']
        cb_positions = ['cornerback', 'cb']

        for player in potential_tacklers:
            pos = player.primary_position.lower()
            if pos in lb_positions:
                linebackers.append(player)
            elif pos in safety_positions:
                safeties.append(player)
            elif pos in dl_positions:
                defensive_line.append(player)
            elif pos in cb_positions:
                cornerbacks.append(player)

        def get_tackle_weight(player, base_position_weight: float, group_size: int) -> float:
            """Calculate skill-weighted tackle probability for a player."""
            # Get tackle rating (or related attributes as fallback)
            rating = 70  # Default
            if hasattr(player, 'get_rating'):
                rating = player.get_rating('tackle') or player.get_rating('pursuit') or \
                         player.get_rating('block_shedding') or player.get_rating('play_recognition') or \
                         player.get_rating('overall') or 70
            elif hasattr(player, 'ratings'):
                rating = player.ratings.get('tackle', player.ratings.get('pursuit',
                         player.ratings.get('block_shedding', player.ratings.get('overall', 70))))

            # Base weight from position group
            base_weight = base_position_weight / group_size

            # Skill multiplier - elite tacklers dominate tackle totals
            if rating >= 90:
                skill_mult = 2.0  # Elite tacklers dominate
            elif rating >= 85:
                skill_mult = 1.5
            elif rating >= 75:
                skill_mult = 1.0
            elif rating >= 65:
                skill_mult = 0.75
            else:
                skill_mult = 0.5  # Poor tacklers rarely make plays

            return base_weight * skill_mult

        # Build weighted selection pool with skill-based weights
        candidates = []
        weights = []

        # Dynamic weights based on play outcome (TFL situations favor DL)
        is_tfl_situation = yards_gained <= 0
        if is_tfl_situation:
            # TFL: DL dominate stuffs at the line
            lb_base_weight = 0.35   # Reduced from 50%
            dl_base_weight = 0.40   # Increased from 25%
            safety_base_weight = 0.20
            cb_base_weight = 0.05
        else:
            # Normal play: standard distribution
            lb_base_weight = 0.50
            dl_base_weight = 0.25
            safety_base_weight = 0.20
            cb_base_weight = 0.05

        # Linebackers: Primary run stoppers
        if linebackers:
            for lb in linebackers:
                candidates.append(lb)
                weights.append(get_tackle_weight(lb, lb_base_weight, len(linebackers)))

        # Defensive Line: TFLs, penetration, pursuit
        if defensive_line:
            for dl in defensive_line:
                candidates.append(dl)
                weights.append(get_tackle_weight(dl, dl_base_weight, len(defensive_line)))

        # Safeties: Second level
        if safeties:
            for s in safeties:
                candidates.append(s)
                weights.append(get_tackle_weight(s, safety_base_weight, len(safeties)))

        # Cornerbacks: Edge contain, pursuit
        if cornerbacks:
            for cb in cornerbacks:
                candidates.append(cb)
                weights.append(get_tackle_weight(cb, cb_base_weight, len(cornerbacks)))

        # Fallback to uniform if no categorized players
        if not candidates:
            return random.choice(potential_tacklers)

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Use weighted random selection
        return random.choices(candidates, weights=normalized_weights, k=1)[0]

    def _select_tfl_sacker_weighted(self, potential_sackers: List):
        """
        Select a player for TFL/sack credit using pass_rush-weighted probabilities.

        Unlike general tackle selection, TFL/sack plays are dominated by defensive
        linemen who penetrate the backfield. This method:
        - Uses pass_rush as primary rating (most relevant for backfield penetration)
        - Gives DL higher base weight (50%) since TFLs are DL-dominant plays
        - Adds position bonus for DE/EDGE (+10) over DT (+5) and LBs (0)
        - Applies elite (2.0x) and poor (0.5x) multipliers

        Args:
            potential_sackers: List of defensive players (typically DL + OLBs)

        Returns:
            Selected player based on pass_rush-weighted probability
        """
        if not potential_sackers:
            return None

        # Position categories for TFL/sack attribution
        dl_positions = ['defensive_end', 'defensive_tackle', 'nose_tackle', 'de', 'dt', 'nt', 'edge']
        olb_positions = ['outside_linebacker', 'olb']

        candidates = []
        weights = []

        for player in potential_sackers:
            pos = player.primary_position.lower()

            # Get pass_rush rating (primary for TFL/sack plays)
            rating = 70  # Default
            if hasattr(player, 'get_rating'):
                rating = player.get_rating('pass_rush') or player.get_rating('power_moves') or \
                         player.get_rating('finesse_moves') or player.get_rating('block_shedding') or \
                         player.get_rating('overall') or 70
            elif hasattr(player, 'ratings'):
                rating = player.ratings.get('pass_rush', player.ratings.get('power_moves',
                         player.ratings.get('finesse_moves', player.ratings.get('overall', 70))))

            # Position bonus - DEs/EDGEs dominate TFL stats
            if pos in dl_positions:
                if pos in ['defensive_end', 'de', 'edge']:
                    position_bonus = 10  # Edge rushers highest bonus
                else:
                    position_bonus = 5   # Interior DL moderate bonus
            elif pos in olb_positions:
                position_bonus = 3       # OLBs can rush but less often
            else:
                position_bonus = 0       # Other positions (ILBs, etc.)

            base_weight = rating + position_bonus

            # Elite/poor multipliers - elite pass rushers dominate TFL totals
            if rating >= 90:
                base_weight *= 2.0  # Elite rushers dominate (e.g., Myles Garrett)
            elif rating >= 85:
                base_weight *= 1.5  # Good rushers get more
            elif rating >= 75:
                base_weight *= 1.0  # Average
            elif rating >= 65:
                base_weight *= 0.75
            else:
                base_weight *= 0.5  # Poor rushers rarely make TFL plays

            candidates.append(player)
            weights.append(base_weight)

        # Fallback to random if no candidates with weights
        if not candidates or sum(weights) == 0:
            return random.choice(potential_sackers) if potential_sackers else None

        # Normalize and select
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        return random.choices(candidates, weights=normalized_weights, k=1)[0]

    def _generate_missed_tackles(
        self,
        yards_gained: int,
        ball_carrier,
        potential_tacklers: List,
        actual_tacklers: List
    ) -> List:
        """
        Generate missed tackle attempts based on play outcome.

        Used for PFF-style grading - tracks defenders who attempted but failed
        to bring down the ball carrier. More realistic tackle attribution.

        Logic:
        - More yards gained = more likely someone missed a tackle
        - Higher elusiveness rating = more broken tackles
        - Exclude players who actually made the tackle

        Args:
            yards_gained: Final yards on the play
            ball_carrier: The RB/ball carrier player object
            potential_tacklers: List of defensive players who could have attempted
            actual_tacklers: List of players who successfully made the tackle

        Returns:
            List of players who missed tackles on this play
        """
        missed = []

        # Base probability by yards gained
        if yards_gained <= 3:
            base_prob = 0.05  # 5% - stuffed at line, unlikely anyone missed
        elif yards_gained <= 9:
            base_prob = 0.15  # 15% - decent gain, maybe one miss
        elif yards_gained <= 19:
            base_prob = 0.35  # 35% - big play, likely broken tackle
        else:
            base_prob = 0.55  # 55% - explosive play, multiple misses likely

        # Adjust for ball carrier elusiveness
        elusiveness = 70  # default
        if hasattr(ball_carrier, 'get_rating'):
            elusiveness = ball_carrier.get_rating('elusiveness', 70)
        elif hasattr(ball_carrier, 'ratings'):
            elusiveness = ball_carrier.ratings.get('elusiveness', 70)

        elusiveness_modifier = (elusiveness - 70) / 100  # ±0.15 for ratings 55-85
        adjusted_prob = min(0.7, max(0.02, base_prob + elusiveness_modifier))

        # Select potential miss candidates (exclude actual tacklers)
        candidates = [p for p in potential_tacklers if p not in actual_tacklers]

        # Roll for each candidate (max 2 missed tackles per play)
        for candidate in candidates[:4]:  # Check up to 4 candidates
            if len(missed) >= 2:
                break
            if random.random() < adjusted_prob:
                missed.append(candidate)
                adjusted_prob *= 0.5  # Diminishing returns for additional misses

        return missed

    # Inherited from BasePlaySimulator:
    # - _track_snaps_for_all_players() - formation-based snap tracking for 22 players

    def _check_fumble(self, rb_player) -> Tuple[bool, bool]:
        """
        Check if ball carrier fumbles and whether defense recovers.

        NFL fumble rates:
        - ~1.5% per rush attempt (base rate)
        - Elite ball carriers fumble less (high carrying rating)
        - Poor ball carriers fumble more

        Args:
            rb_player: Running back player object

        Returns:
            Tuple of (fumble_occurred: bool, defense_recovered: bool)
        """
        # Get fumble config from run_play_config.json
        run_config = config.get_run_play_config()
        fumble_config = run_config.get('fumble_rates', {})

        base_rate = fumble_config.get('base_fumble_rate', 0.018)
        rb_modifiers = fumble_config.get('rb_skill_modifiers', {})
        recovery_rate = fumble_config.get('recovery_rate', 0.50)

        # Adjust for player skill (carrying/ball security rating)
        carrying_rating = 75  # Default
        if rb_player and hasattr(rb_player, 'get_rating'):
            carrying_rating = rb_player.get_rating('carrying', 75)
        elif rb_player and hasattr(rb_player, 'ratings'):
            carrying_rating = rb_player.ratings.get('carrying', 75)

        # Apply rating thresholds from config
        player_config = config.get_player_attribute_config('run_play')
        thresholds = player_config.get('rating_thresholds', {})
        elite_threshold = thresholds.get('elite', 90)
        good_threshold = thresholds.get('good', 80)
        poor_threshold = thresholds.get('poor', 65)

        if carrying_rating >= elite_threshold:
            base_rate -= rb_modifiers.get('elite_reduction', 0.006)
        elif carrying_rating >= good_threshold:
            base_rate -= rb_modifiers.get('good_reduction', 0.003)
        elif carrying_rating <= poor_threshold:
            base_rate += rb_modifiers.get('poor_increase', 0.004)

        # Roll for fumble
        fumble_occurred = random.random() < base_rate

        if not fumble_occurred:
            return False, False

        # Fumble occurred - check recovery
        # ~50% recovery rate for offense (NFL average)
        defense_recovered = random.random() < recovery_rate

        return True, defense_recovered

    def _attribute_fumble_stats(self, player_stats: List[PlayerStats], running_back) -> None:
        """
        Add fumble statistics to player stats.

        - RB gets fumble_lost stat
        - Random defender gets forced_fumble stat
        - Random defender gets fumble_recovery stat

        Args:
            player_stats: List of PlayerStats objects to update
            running_back: The ball carrier who fumbled
        """
        # Find or create RB stats and add fumble lost
        rb_stats = None
        for stats in player_stats:
            if stats.player_name == running_back.name:
                rb_stats = stats
                break

        if rb_stats:
            rb_stats.fumbles_lost = getattr(rb_stats, 'fumbles_lost', 0) + 1

        # Select a defender for forced fumble (linebackers and safeties most likely)
        linebackers = self._find_defensive_players_by_positions([
            Position.MIKE, Position.SAM, Position.WILL, Position.ILB, Position.OLB
        ])
        safeties = self._find_defensive_players_by_positions([Position.FS, Position.SS])
        defensive_line = self._find_defensive_players_by_positions([
            Position.DE, Position.DT, Position.NT
        ])

        potential_forcers = linebackers + safeties + defensive_line
        if potential_forcers:
            forcer = random.choice(potential_forcers)
            forcer_stats = create_player_stats_from_player(forcer, team_id=self.defensive_team_id)
            forcer_stats.forced_fumbles = 1
            forcer_stats.fumble_recoveries = 1  # Defense recovered
            player_stats.append(forcer_stats)