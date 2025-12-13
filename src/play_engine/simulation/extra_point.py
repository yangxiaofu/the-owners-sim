"""
Extra point (PAT) and 2-point conversion simulation

Implements realistic extra point and 2-point conversion simulation with:
1. PAT attempts with ~94% success rate (post-2015 rule change to 33-yard line)
2. Block probability (~1-2%)
3. Snap/hold issues (~1%)
4. 2-point conversion attempts with ~48-50% success rate
5. Integration with existing pass/run simulation logic
6. Individual player statistics attribution
"""

import random
from typing import List, Optional, Dict
from .stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from .base_simulator import BasePlaySimulator
from .pass_plays import PassPlaySimulator
from .run_plays import RunPlaySimulator
from ..mechanics.formations import OffensiveFormation, DefensiveFormation
from ..play_types.base_types import PlayType
from team_management.players.player import Position
from ..mechanics.penalties.penalty_engine import PenaltyEngine, PlayContext
from ..config.config_loader import config
from ..config.timing_config import NFLTimingConfig


class ExtraPointResult:
    """Result data structure for extra point attempts"""

    def __init__(self, outcome: str, points_scored: int = 0, is_two_point: bool = False,
                 conversion_type: str = None, yards_gained: int = 0):
        """
        Initialize extra point result

        Args:
            outcome: Result outcome ("pat_made", "pat_missed", "pat_blocked",
                     "two_point_good", "two_point_failed", "two_point_intercepted")
            points_scored: Points scored (1 for PAT, 2 for 2pt conversion, 0 for failed)
            is_two_point: Whether this was a 2-point conversion attempt
            conversion_type: Type of 2-point conversion ("pass" or "run") if applicable
            yards_gained: Yards gained on 2-point conversion attempt (usually 0 or 2)
        """
        self.outcome = outcome
        self.points_scored = points_scored
        self.is_two_point = is_two_point
        self.conversion_type = conversion_type
        self.yards_gained = yards_gained

        # Time elapsed (PAT is quick, 2pt conversion takes longer)
        min_time, max_time = NFLTimingConfig.get_extra_point_timing(is_two_point=is_two_point)
        self.time_elapsed = random.uniform(min_time, max_time)

        # Individual player stats
        self.player_stats = {}
        self.penalty_occurred = False
        self.penalty_instance = None


class ExtraPointSimulator(BasePlaySimulator):
    """Simulates extra point (PAT) and 2-point conversion attempts"""

    def __init__(self, offensive_players: List, defensive_players: List,
                 offensive_formation: str = "FIELD_GOAL",
                 defensive_formation: str = "FIELD_GOAL_BLOCK",
                 offensive_team_id: int = None, defensive_team_id: int = None,
                 weather_condition: str = "clear",
                 crowd_noise_level: int = 0,
                 is_away_team: bool = False):
        """
        Initialize extra point simulator

        Args:
            offensive_players: List of 11 offensive Player objects
            defensive_players: List of 11 defensive Player objects
            offensive_formation: Offensive formation (typically "FIELD_GOAL" for PAT)
            defensive_formation: Defensive formation for PAT defense
            offensive_team_id: Team ID for the kicking team (1-32)
            defensive_team_id: Team ID for the defending team (1-32)
            weather_condition: Weather condition ("clear", "rain", "snow", "heavy_wind")
            crowd_noise_level: Crowd noise intensity (0-100)
            is_away_team: Whether the kicking team is the away team
        """
        self.offensive_players = offensive_players
        self.defensive_players = defensive_players
        self.offensive_formation = offensive_formation
        self.defensive_formation = defensive_formation
        self.offensive_team_id = offensive_team_id
        self.defensive_team_id = defensive_team_id

        # Environmental modifiers
        self.weather_condition = weather_condition
        self.crowd_noise_level = crowd_noise_level
        self.is_away_team = is_away_team

        # Initialize penalty engine
        self.penalty_engine = PenaltyEngine()

        # Identify key special teams players
        self._identify_special_teams_players()

    def _identify_special_teams_players(self):
        """Identify key players in extra point unit"""
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
                elif player.primary_position in [Position.LT, Position.LG, Position.C,
                                                Position.RG, Position.RT, Position.TE]:
                    self.protection_unit.append(player)

        # Fallback assignments if positions not properly set
        if not self.kicker and len(self.offensive_players) > 0:
            self.kicker = self.offensive_players[0]
        if not self.holder and len(self.offensive_players) > 1:
            self.holder = self.offensive_players[1]
        if not self.long_snapper and len(self.offensive_players) > 2:
            self.long_snapper = self.offensive_players[2]

    def simulate_pat(self, context: Optional[PlayContext] = None) -> PlayStatsSummary:
        """
        Simulate a point-after-touchdown (PAT) attempt

        Args:
            context: Game situation context for penalty determination

        Returns:
            PlayStatsSummary with PAT outcome and player statistics
        """
        # Default context if none provided
        if context is None:
            context = PlayContext(
                play_type="extra_point",
                offensive_formation=self.offensive_formation,
                defensive_formation=self.defensive_formation
            )

        # Phase 1: Simulate PAT execution
        result = self._simulate_pat_execution()

        # Phase 2: Check for penalties
        penalty_result = self.penalty_engine.check_for_penalty(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            context=context,
            original_play_yards=0  # PAT attempts don't gain yards
        )

        # Adjust outcome if play negated by penalty
        points_scored = result.points_scored
        if penalty_result.play_negated:
            points_scored = 0

        # Phase 3: Attribute player statistics
        player_stats = self._attribute_pat_statistics(result)

        # Create comprehensive PlayStatsSummary
        summary = PlayStatsSummary(
            play_type="extra_point",
            yards_gained=0,  # PAT doesn't gain yards
            time_elapsed=result.time_elapsed,
            points_scored=points_scored,
            extra_point_outcome=result.outcome
        )

        # Add penalty information if applicable
        if penalty_result.penalty_occurred:
            summary.penalty_occurred = True
            summary.penalty_instance = penalty_result.penalty_instance
            summary.play_negated = penalty_result.play_negated

        # Add all player stats
        for stats in player_stats:
            summary.add_player_stats(stats)

        return summary

    def simulate_two_point_conversion(self, conversion_type: str = None,
                                     context: Optional[PlayContext] = None) -> PlayStatsSummary:
        """
        Simulate a 2-point conversion attempt

        Args:
            conversion_type: Type of conversion ("pass" or "run"). If None, randomly selected.
            context: Game situation context for penalty determination

        Returns:
            PlayStatsSummary with 2-point conversion outcome and player statistics
        """
        # Determine conversion type if not specified
        if conversion_type is None:
            # NFL 2-point conversions are roughly 60% pass, 40% run
            conversion_type = "pass" if random.random() < 0.6 else "run"

        # Default context if none provided
        if context is None:
            context = PlayContext(
                play_type="two_point_conversion",
                offensive_formation=self.offensive_formation,
                defensive_formation=self.defensive_formation,
                field_position=98,  # 2-point conversions from the 2-yard line
                distance=2
            )
        else:
            # Override field position and distance for 2-point conversions
            context.field_position = 98
            context.distance = 2

        # Execute conversion based on type
        if conversion_type == "pass":
            return self._simulate_two_point_pass(context)
        else:
            return self._simulate_two_point_run(context)

    def _simulate_pat_execution(self) -> ExtraPointResult:
        """
        Simulate PAT execution with realistic success rates

        Returns:
            ExtraPointResult with kick outcome
        """
        # NFL PAT success rate: ~94% (post-2015 rule change, 33-yard attempt)
        base_success_rate = 0.94

        # Phase 1: Check for snap/hold issues (~1% of PATs affected)
        # NFL snap/hold errors are rare - only catastrophic failures cause misses
        snap_quality = self._evaluate_snap_quality()
        hold_quality = self._evaluate_hold_quality(snap_quality)

        # Only truly terrible snap/hold causes instant miss (very rare)
        # Threshold lowered from 0.90 to 0.80, and chance reduced from 50% to 10%
        if snap_quality < 0.80 or hold_quality < 0.80:
            if random.random() < 0.10:  # 10% chance catastrophic snap/hold causes miss
                return ExtraPointResult(
                    outcome="pat_missed",
                    points_scored=0,
                    is_two_point=False
                )

        # Phase 2: Check for block (~1-2%)
        block_probability = 0.015  # 1.5% block rate
        if self._check_for_block():
            return ExtraPointResult(
                outcome="pat_blocked",
                points_scored=0,
                is_two_point=False
            )

        # Phase 3: Execute kick
        # Use ADDITIVE modifiers to prevent excessive compounding
        # Base rate is 0.94, modifiers subtract from 1.0
        kicker_penalty = 1.0 - self._get_kicker_modifier()  # Elite: -0.05, Poor: +0.06
        env_penalty = 1.0 - self._get_environmental_modifier(distance=33)  # Clear: 0, Heavy wind: +0.03

        # Snap/hold already handled above with early exit
        # Only apply kicker skill and environmental factors
        total_penalty = kicker_penalty + env_penalty
        final_success_rate = base_success_rate - total_penalty

        # Ensure reasonable bounds (85-98%)
        final_success_rate = max(0.85, min(0.98, final_success_rate))

        # Determine outcome
        if random.random() < final_success_rate:
            return ExtraPointResult(
                outcome="pat_made",
                points_scored=1,
                is_two_point=False
            )
        else:
            return ExtraPointResult(
                outcome="pat_missed",
                points_scored=0,
                is_two_point=False
            )

    def _simulate_two_point_pass(self, context: PlayContext) -> PlayStatsSummary:
        """
        Simulate 2-point conversion via pass play

        Args:
            context: Game situation context

        Returns:
            PlayStatsSummary with pass conversion outcome
        """
        # Use existing pass play simulator
        pass_simulator = PassPlaySimulator(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            offensive_formation="shotgun",  # Common 2pt formation
            defensive_formation="nickel",
            weather_condition=self.weather_condition,
            crowd_noise_level=self.crowd_noise_level,
            is_away_team=self.is_away_team,
            field_position=98  # 2-yard line
        )

        # Simulate the pass play
        summary = pass_simulator.simulate_pass_play(context)

        # Determine if conversion successful (must reach end zone)
        conversion_successful = summary.yards_gained >= 2

        # Update summary for 2-point conversion context
        summary.play_type = "two_point_conversion"
        summary.two_point_conversion_type = "pass"

        if conversion_successful:
            summary.points_scored = 2
            summary.two_point_conversion_outcome = "two_point_good"
        else:
            summary.points_scored = 0
            summary.two_point_conversion_outcome = "two_point_failed"

        return summary

    def _simulate_two_point_run(self, context: PlayContext) -> PlayStatsSummary:
        """
        Simulate 2-point conversion via run play

        Args:
            context: Game situation context

        Returns:
            PlayStatsSummary with run conversion outcome
        """
        # Use existing run play simulator
        run_simulator = RunPlaySimulator(
            offensive_players=self.offensive_players,
            defensive_players=self.defensive_players,
            offensive_formation="i_formation",  # Strong formation for 2pt
            defensive_formation="4_3_base",  # Note: underscore not hyphen
            weather_condition=self.weather_condition,
            crowd_noise_level=self.crowd_noise_level,
            is_away_team=self.is_away_team,
            field_position=98  # 2-yard line
        )

        # Simulate the run play
        summary = run_simulator.simulate_run_play(context)

        # Determine if conversion successful (must reach end zone)
        conversion_successful = summary.yards_gained >= 2

        # Update summary for 2-point conversion context
        summary.play_type = "two_point_conversion"
        summary.two_point_conversion_type = "run"

        if conversion_successful:
            summary.points_scored = 2
            summary.two_point_conversion_outcome = "two_point_good"
        else:
            summary.points_scored = 0
            summary.two_point_conversion_outcome = "two_point_failed"

        return summary

    def _evaluate_snap_quality(self) -> float:
        """
        Evaluate long snapper performance

        Returns:
            Quality multiplier (0.85-0.99)
        """
        if not self.long_snapper:
            return 0.95  # Average snap

        snap_accuracy = (self.long_snapper.get_rating('awareness')
                        if hasattr(self.long_snapper, 'get_rating') else 75)

        # Convert rating to quality score
        if snap_accuracy >= 90:
            return 0.99
        elif snap_accuracy >= 80:
            return 0.97
        elif snap_accuracy >= 70:
            return 0.95
        elif snap_accuracy >= 60:
            return 0.92
        else:
            return 0.88

    def _evaluate_hold_quality(self, snap_quality: float) -> float:
        """
        Evaluate holder performance based on snap quality

        Args:
            snap_quality: Quality of the snap (affects hold difficulty)

        Returns:
            Quality multiplier (0.85-0.99)
        """
        if not self.holder:
            return 0.95  # Average hold

        hold_skill = (self.holder.get_rating('awareness')
                     if hasattr(self.holder, 'get_rating') else 75)

        # Base hold quality affected by snap
        base_quality = min(0.99, snap_quality * 1.02)

        # Adjust for holder skill
        if hold_skill >= 90:
            return min(0.99, base_quality * 1.03)
        elif hold_skill >= 80:
            return min(0.99, base_quality * 1.01)
        elif hold_skill >= 70:
            return base_quality
        elif hold_skill >= 60:
            return base_quality * 0.97
        else:
            return base_quality * 0.93

    def _check_for_block(self) -> bool:
        """
        Check if PAT attempt is blocked

        Returns:
            True if blocked, False otherwise
        """
        # Base block probability for PAT (~1.5%)
        block_probability = 0.015

        # Defensive line pressure increases block chance
        defensive_line_strength = self._get_defensive_line_strength()
        offensive_line_strength = self._get_offensive_line_strength()

        # Adjust block probability based on line matchup
        strength_ratio = defensive_line_strength / max(offensive_line_strength, 1)
        adjusted_block_prob = block_probability * strength_ratio

        # Cap at reasonable maximum (5%)
        adjusted_block_prob = min(adjusted_block_prob, 0.05)

        return random.random() < adjusted_block_prob

    def _get_defensive_line_strength(self) -> float:
        """
        Calculate defensive line strength for block attempts

        Returns:
            Strength rating (50-100)
        """
        if not self.defensive_players:
            return 75.0

        # Get edge rushers and interior linemen
        rushers = [p for p in self.defensive_players
                  if hasattr(p, 'primary_position') and
                  p.primary_position in [Position.DE, Position.DT, Position.NT, Position.LEO,
                                       Position.OLB]]  # Edge rushers

        if not rushers:
            return 75.0

        # Average their pass rush ratings
        total_rating = sum(p.get_rating('pass_rush') if hasattr(p, 'get_rating') else 75
                          for p in rushers)
        return total_rating / len(rushers)

    def _get_offensive_line_strength(self) -> float:
        """
        Calculate offensive line strength for protection

        Returns:
            Strength rating (50-100)
        """
        if not self.protection_unit:
            return 75.0

        # Average pass blocking ratings
        total_rating = sum(p.get_rating('pass_blocking') if hasattr(p, 'get_rating') else 75
                          for p in self.protection_unit)
        return total_rating / len(self.protection_unit)

    def _get_kicker_modifier(self) -> float:
        """
        Get accuracy modifier based on kicker attributes

        Returns:
            Modifier (0.92-1.08)
        """
        if not self.kicker:
            return 1.0

        # Use shared utility for rating fallback (accuracy -> overall -> 75)
        kicker_accuracy = self._get_player_rating_with_fallback(
            self.kicker, 'accuracy', 'overall', default=75
        )

        # Kicker skill affects PAT success
        if kicker_accuracy >= 90:
            return 1.05  # Elite kicker
        elif kicker_accuracy >= 80:
            return 1.02  # Good kicker
        elif kicker_accuracy >= 70:
            return 1.0   # Average kicker
        elif kicker_accuracy >= 60:
            return 0.97  # Below average
        else:
            return 0.94  # Poor kicker

    def _get_environmental_modifier(self, distance: int) -> float:
        """
        Get environmental modifier for kicking conditions

        Args:
            distance: Distance of kick in yards (33 for PAT)

        Returns:
            Environmental modifier (0.7-1.0)
        """
        if self.weather_condition == "clear":
            return 1.0

        # Distance scaling (shorter kicks less affected by weather)
        distance_factor = 0.3 + (distance / 50.0) * 0.7  # 0.3-1.0 range

        base_modifier = 1.0

        if self.weather_condition == "rain":
            base_modifier = 1.0 - (0.05 * distance_factor)  # -1.5% to -5%
        elif self.weather_condition == "snow":
            base_modifier = 1.0 - (0.08 * distance_factor)  # -2.4% to -8%
        elif self.weather_condition == "heavy_wind":
            base_modifier = 1.0 - (0.10 * distance_factor)  # -3% to -10%

        return max(base_modifier, 0.7)  # Minimum 70% of base accuracy

    def _attribute_pat_statistics(self, result: ExtraPointResult) -> List[PlayerStats]:
        """
        Attribute individual player statistics for PAT attempt

        Args:
            result: ExtraPointResult with outcome information

        Returns:
            List of PlayerStats objects
        """
        player_stats = []

        # Kicker statistics
        if self.kicker:
            kicker_stats = create_player_stats_from_player(self.kicker)
            kicker_stats.extra_points_attempted = 1

            if result.outcome == "pat_made":
                kicker_stats.extra_points_made = 1
            elif result.outcome == "pat_blocked":
                # Blocked XP doesn't count as missed
                pass
            # else: pat_missed counts as attempt but not made

            player_stats.append(kicker_stats)

        # Holder statistics
        if self.holder:
            holder_stats = create_player_stats_from_player(self.holder)
            holder_stats.field_goal_holds = 1  # Track holds for PATs too
            player_stats.append(holder_stats)

        # Long snapper statistics
        if self.long_snapper:
            ls_stats = create_player_stats_from_player(self.long_snapper)
            ls_stats.long_snaps = 1
            player_stats.append(ls_stats)

        # Protection unit statistics
        for protector in self.protection_unit:
            protector_stats = create_player_stats_from_player(protector)
            protector_stats.special_teams_snaps = 1

            if result.outcome == "pat_blocked":
                # Random assignment of block responsibility
                if random.random() < 0.2:  # 20% chance
                    protector_stats.blocks_allowed = 1

            player_stats.append(protector_stats)

        # Track special teams snaps for all defensive players
        for defender in self.defensive_players:
            defender_stats = create_player_stats_from_player(defender)
            defender_stats.special_teams_snaps = 1

            # Credit block if applicable
            if result.outcome == "pat_blocked":
                # Random assignment of block credit
                if random.random() < 0.3:  # 30% chance for any defender
                    # Note: Would need to add 'kicks_blocked' stat to PlayerStats
                    pass

            player_stats.append(defender_stats)

        return player_stats
