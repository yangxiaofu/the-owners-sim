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
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..play_types.base_types import PlayType
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from ..mechanics.penalties.penalty_data_structures import PenaltyInstance
from ..config.config_loader import config, get_run_formation_matchup
from ..config.timing_config import NFLTimingConfig


class RunPlaySimulator:
    """Simulates run plays with individual player stat attribution"""
    
    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str, defensive_formation: str,
                 offensive_team_id: int = None, defensive_team_id: int = None):
        """
        Initialize run play simulator

        Args:
            offensive_players: List of 11 offensive Player objects
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation string
            defensive_formation: Defensive formation string
            offensive_team_id: Team ID of the offensive team (1-32)
            defensive_team_id: Team ID of the defensive team (1-32)
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id
        
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

        # Phase 2C: Track snaps for ALL players on the field (offensive and defensive)
        player_stats = self._track_snaps_for_all_players(player_stats)

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

        # Add touchdown attribution if points were scored
        self._add_touchdown_attribution(summary)

        return summary

    def _add_touchdown_attribution(self, summary: PlayStatsSummary):
        """Add touchdown attribution to player stats if points were scored"""
        # DEBUG: Check what points_scored actually is
        points = getattr(summary, 'points_scored', 0)
        if summary.yards_gained > 15:  # Debug big gains
            print(f"DEBUG RUN ATTRIBUTION: yards={summary.yards_gained}, points_scored={points}")

        if points == 6:
            print(f"🏈 TOUCHDOWN DETECTED in run play! Adding rushing TD to player stats")
            # This is a touchdown - add touchdown stats to appropriate players
            for player_stat in summary.player_stats:
                if player_stat.rushing_attempts > 0:
                    # Player had rushing attempts, credit them with rushing TD
                    player_stat.add_rushing_touchdown()
                    print(f"✅ Added rushing TD to {player_stat.player_name}")
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
            player_stats.append(rb_stats)
        
        # Attribute comprehensive offensive line stats
        if offensive_line:
            oline_stats = self._attribute_advanced_oline_stats(yards_gained, offensive_line)
            player_stats.extend(oline_stats)
        
        # Attribute defensive stats (tackles)
        # All potential tacklers: linebackers, safeties, defensive line
        potential_tacklers = linebackers + safeties + defensive_line
        tacklers = self._select_tacklers(yards_gained, potential_tacklers)

        for tackler_info in tacklers:
            player, is_assisted = tackler_info
            tackler_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
            tackler_stats.add_tackle(assisted=is_assisted)

            # Add TFL for negative yardage plays
            if yards_gained < 0:
                tackler_stats.tackles_for_loss = 1

            player_stats.append(tackler_stats)

        # Add sacks for significant negative yardage plays (TFL of 5+ yards likely indicates sack)
        if yards_gained <= -5:
            # Defensive line players more likely to get sacks
            potential_sackers = defensive_line + [p for p in linebackers if "outside" in p.primary_position.lower()]
            if potential_sackers:
                sacker = random.choice(potential_sackers)

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

            # Calculate run blocking grade based on play outcome
            run_blocking_grade = self._calculate_run_blocking_grade(yards_gained, i == 0)  # Lead blocker gets extra credit
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

    def _calculate_run_blocking_grade(self, yards_gained: int, is_lead_blocker: bool = False) -> float:
        """
        Calculate run blocking grade based on play outcome

        Args:
            yards_gained: Yards gained on the play
            is_lead_blocker: Whether this is the lead/key blocker

        Returns:
            Grade from 0-100
        """
        base_grade = 50.0  # Average grade

        # Adjust based on yards gained
        if yards_gained >= 15:
            base_grade = 85.0  # Excellent
        elif yards_gained >= 8:
            base_grade = 75.0  # Good
        elif yards_gained >= 4:
            base_grade = 65.0  # Above average
        elif yards_gained >= 1:
            base_grade = 55.0  # Slightly above average
        elif yards_gained == 0:
            base_grade = 45.0  # Below average
        elif yards_gained >= -2:
            base_grade = 35.0  # Poor
        else:
            base_grade = 25.0  # Very poor

        # Lead blocker bonus
        if is_lead_blocker:
            base_grade += 5.0

        # Add some randomness
        grade = base_grade + random.uniform(-5.0, 5.0)

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

        # More yards = more likely to have assisted tackles
        if yards_gained >= long_run_threshold:
            # Long run: likely 1 primary tackler + 1 assisted
            primary_tackler = self._select_tackler_by_position_weight(potential_tacklers)
            tacklers.append((primary_tackler, False))

            # Configured chance of assisted tackle
            if random.random() < assisted_tackle_prob:
                remaining = [p for p in potential_tacklers if p != primary_tackler]
                if remaining:
                    assisted_tackler = self._select_tackler_by_position_weight(remaining)
                    tacklers.append((assisted_tackler, True))
        else:
            # Short run: likely just 1 tackler
            primary_tackler = self._select_tackler_by_position_weight(potential_tacklers)
            tacklers.append((primary_tackler, False))

        return tacklers

    def _select_tackler_by_position_weight(self, potential_tacklers: List):
        """
        Select a tackler using position-weighted probabilities to create realistic tackle distributions.

        Weight distribution mirrors NFL reality:
        - Linebackers dominate with 65% of run tackles
        - Safeties get 25% (cleanup, deep plays)
        - Defensive line gets 8% (TFLs, penetration)
        - Cornerbacks get 2% (edge contain)

        Args:
            potential_tacklers: List of defensive players

        Returns:
            Selected player based on position-weighted probability
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

        # Build weighted selection pool
        candidates = []
        weights = []

        # Linebackers: 65% weight (heavily favored)
        if linebackers:
            candidates.extend(linebackers)
            weights.extend([0.65 / len(linebackers)] * len(linebackers))

        # Safeties: 25% weight (second line)
        if safeties:
            candidates.extend(safeties)
            weights.extend([0.25 / len(safeties)] * len(safeties))

        # Defensive Line: 8% weight (TFLs only)
        if defensive_line:
            candidates.extend(defensive_line)
            weights.extend([0.08 / len(defensive_line)] * len(defensive_line))

        # Cornerbacks: 2% weight (rare)
        if cornerbacks:
            candidates.extend(cornerbacks)
            weights.extend([0.02 / len(cornerbacks)] * len(cornerbacks))

        # Fallback to uniform if no categorized players
        if not candidates:
            return random.choice(potential_tacklers)

        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Use weighted random selection
        return random.choices(candidates, weights=normalized_weights, k=1)[0]

    def _track_snaps_for_all_players(self, player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Track snaps for ALL 22 players on the field during this run play

        Args:
            player_stats: List of PlayerStats objects (may be empty or contain only players with statistical attribution)

        Returns:
            Updated list of PlayerStats objects ensuring all 22 players have snap tracking
        """
        # Create a dictionary to track existing PlayerStats objects by player name
        existing_stats = {stats.player_name: stats for stats in player_stats}

        # Track offensive snaps for all 11 offensive players
        for player in self.offensive_players:
            player_name = player.name
            if player_name in existing_stats:
                # Player already has stats object, just add the snap
                existing_stats[player_name].add_offensive_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, team_id=self.offensive_team_id)
                new_stats.add_offensive_snap()
                existing_stats[player_name] = new_stats
                player_stats.append(new_stats)

        # Track defensive snaps for all 11 defensive players
        for player in self.defensive_players:
            player_name = player.name
            if player_name in existing_stats:
                # Player already has stats object, just add the snap
                existing_stats[player_name].add_defensive_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
                new_stats.add_defensive_snap()
                existing_stats[player_name] = new_stats
                player_stats.append(new_stats)

        return player_stats