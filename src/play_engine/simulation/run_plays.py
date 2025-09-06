"""
Run play simulation with individual player statistics and penalty integration

Implements enhanced two-stage simulation with penalty system:
1. Determine play outcome using formation matchup matrix
2. Check for penalties and apply effects
3. Attribute individual player statistics based on final outcome
"""

import random
from typing import List, Tuple, Dict, Optional
from play_engine.simulation.stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
from play_engine.play_types.base_types import PlayType
from team_management.players.player import Position
from play_engine.mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from play_engine.mechanics.penalties.penalty_data_structures import PenaltyInstance
from play_engine.config.config_loader import config, get_run_formation_matchup
from play_engine.config.timing_config import NFLTimingConfig


class RunPlaySimulator:
    """Simulates run plays with individual player stat attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List, 
                 offensive_formation: str, defensive_formation: str):
        """
        Initialize run play simulator
        
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
        
        # Phase 2B: Attribute player stats based on final outcome
        player_stats = self._attribute_player_stats(final_yards, penalty_result)
        
        # Create play summary with penalty information
        summary = PlayStatsSummary(
            play_type=PlayType.RUN,
            yards_gained=final_yards,
            time_elapsed=time_elapsed
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
        
        # Generate yards with modified distribution
        yards_gained = max(0, int(random.gauss(modified_avg_yards, modified_variance)))
        
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
        
        # Apply modifiers (offense increases yards, defense decreases yards)  
        final_modifier = offensive_modifier / defensive_modifier
        modified_avg_yards = base_avg_yards * final_modifier
        
        # Use configured variance cap
        stats_config = config.get_statistical_attribution_config('run_play')
        variance_cap = stats_config.get('variance_cap', 1.2)
        modified_variance = base_variance * min(final_modifier, variance_cap)
        
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
        linebackers = self._find_defensive_players_by_positions([Position.MIKE, Position.SAM, Position.WILL])
        safeties = self._find_defensive_players_by_positions([Position.FS, Position.SS])
        
        # Attribute RB stats
        if running_back:
            rb_stats = create_player_stats_from_player(running_back)
            rb_stats.add_carry(yards_gained)
            player_stats.append(rb_stats)
        
        # Attribute offensive line blocking stats - use configured parameters
        if offensive_line:
            stats_config = config.get_statistical_attribution_config('run_play')
            blocking_config = stats_config.get('blocking', {})
            
            min_blockers = blocking_config.get('min_blockers', 2)
            max_blockers = blocking_config.get('max_blockers', 3)
            base_success_rate = blocking_config.get('base_success_rate', 0.7)
            yards_bonus_multiplier = blocking_config.get('yards_bonus_multiplier', 0.05)
            
            num_blockers = min(len(offensive_line), random.randint(min_blockers, max_blockers))
            selected_blockers = random.sample(offensive_line, num_blockers)
            
            for blocker in selected_blockers:
                blocker_stats = create_player_stats_from_player(blocker)
                # Higher success rate for longer runs
                success_rate = base_success_rate + (yards_gained * yards_bonus_multiplier)
                blocker_stats.add_block(random.random() < success_rate)
                player_stats.append(blocker_stats)
        
        # Attribute defensive stats (tackles)
        tacklers = self._select_tacklers(yards_gained, linebackers + safeties)
        for tackler_info in tacklers:
            player, is_assisted = tackler_info
            tackler_stats = create_player_stats_from_player(player)
            tackler_stats.add_tackle(assisted=is_assisted)
            player_stats.append(tackler_stats)
        
        return [stats for stats in player_stats if stats.get_total_stats()]
    
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
    
    def _select_tacklers(self, yards_gained: int, potential_tacklers: List) -> List[Tuple]:
        """
        Select which defenders made tackles based on yards gained
        
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
        
        # More yards = more likely to have assisted tackles
        if yards_gained >= long_run_threshold:
            # Long run: likely 1 primary tackler + 1 assisted
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
            
            # Configured chance of assisted tackle
            if random.random() < assisted_tackle_prob:
                remaining = [p for p in potential_tacklers if p != primary_tackler]
                if remaining:
                    assisted_tackler = random.choice(remaining)
                    tacklers.append((assisted_tackler, True))
        else:
            # Short run: likely just 1 tackler
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
        
        return tacklers