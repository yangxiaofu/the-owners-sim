"""
Run play simulation with individual player statistics and penalty integration

Implements enhanced two-stage simulation with penalty system:
1. Determine play outcome using formation matchup matrix
2. Check for penalties and apply effects
3. Attribute individual player statistics based on final outcome
"""

import random
from typing import List, Tuple, Dict, Optional
from .play_stats import PlayerStats, PlayStatsSummary, create_player_stats_from_player
from formation import OffensiveFormation, DefensiveFormation
from play_type import PlayType
from player import Position
from penalties.penalty_engine import PenaltyEngine, PlayContext, PenaltyResult
from penalties.penalty_data_structures import PenaltyInstance


class RunPlaySimulator:
    """Simulates run plays with individual player stat attribution"""
    
    # Simple matchup matrix: (offensive_formation, defensive_formation) -> (avg_yards, variance)
    MATCHUP_MATRIX = {
        (OffensiveFormation.I_FORMATION, DefensiveFormation.FOUR_THREE): (4.2, 2.5),
        (OffensiveFormation.I_FORMATION, DefensiveFormation.NICKEL): (5.1, 2.8),
        (OffensiveFormation.I_FORMATION, DefensiveFormation.GOAL_LINE): (2.3, 1.8),
        (OffensiveFormation.SINGLEBACK, DefensiveFormation.FOUR_THREE): (3.8, 2.3),
        (OffensiveFormation.SINGLEBACK, DefensiveFormation.NICKEL): (4.6, 2.6),
        (OffensiveFormation.SHOTGUN, DefensiveFormation.FOUR_THREE): (3.2, 2.1),
        (OffensiveFormation.SHOTGUN, DefensiveFormation.NICKEL): (3.5, 2.2),
        (OffensiveFormation.PISTOL, DefensiveFormation.FOUR_THREE): (4.0, 2.4),
    }
    
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
        Phase 1: Determine yards gained and time elapsed using matchup matrix
        
        Returns:
            Tuple of (yards_gained, time_elapsed)
        """
        # Get matchup parameters
        matchup_key = (self.offensive_formation, self.defensive_formation)
        
        if matchup_key in self.MATCHUP_MATRIX:
            avg_yards, variance = self.MATCHUP_MATRIX[matchup_key]
        else:
            # Default matchup if not found
            avg_yards, variance = (3.5, 2.2)
        
        # Generate yards with normal distribution
        yards_gained = max(0, int(random.gauss(avg_yards, variance)))
        
        # Time elapsed (3-5 seconds for run plays)
        time_elapsed = round(random.uniform(2.8, 4.5), 1)
        
        return yards_gained, time_elapsed
    
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
        
        # Attribute offensive line blocking stats (select 2-3 random linemen)
        if offensive_line:
            num_blockers = min(len(offensive_line), random.randint(2, 3))
            selected_blockers = random.sample(offensive_line, num_blockers)
            
            for blocker in selected_blockers:
                blocker_stats = create_player_stats_from_player(blocker)
                # Higher success rate for longer runs
                success_rate = 0.7 + (yards_gained * 0.05)
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
        
        # More yards = more likely to have assisted tackles
        if yards_gained >= 5:
            # Long run: likely 1 primary tackler + 1 assisted
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
            
            # 60% chance of assisted tackle
            if random.random() < 0.6:
                remaining = [p for p in potential_tacklers if p != primary_tackler]
                if remaining:
                    assisted_tackler = random.choice(remaining)
                    tacklers.append((assisted_tackler, True))
        else:
            # Short run: likely just 1 tackler
            primary_tackler = random.choice(potential_tacklers)
            tacklers.append((primary_tackler, False))
        
        return tacklers