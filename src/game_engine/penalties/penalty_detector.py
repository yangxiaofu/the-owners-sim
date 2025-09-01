"""
Three-Phase Penalty Detector - Core penalty detection engine

This module implements the main penalty detection logic using a three-phase approach:
1. Pre-snap penalties (before play simulation)
2. During-play penalties (after play simulation)  
3. Post-play penalties (after play completion)

The detector uses player discipline ratings, situational modifiers, and position-specific
penalty tendencies to generate realistic penalty occurrences that match NFL statistics.
"""

import random
from typing import Optional, Dict, List, Any
import logging

from .data_structures import (
    Penalty, PenaltyResult, PenaltyType, PenaltyPhase, PenaltyConstants, 
    SituationalModifiers, create_penalty, get_penalty_summary_stats
)
from ..plays.data_structures import PlayResult
from ..field.game_state import GameState
from ...database.models.players.player import Player


class PenaltyDetector:
    """
    Three-phase penalty detection engine for realistic NFL penalty simulation.
    
    This class implements the core penalty detection logic, evaluating penalty
    probability based on player discipline, game situation, and position-specific
    tendencies across three distinct phases of play execution.
    """
    
    def __init__(self, config: Dict = None, enable_logging: bool = True):
        """
        Initialize the penalty detector.
        
        Args:
            config: Configuration dict for penalty rates and modifiers
            enable_logging: Whether to enable detailed penalty logging
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__) if enable_logging else None
        
        # Load penalty configuration
        self.penalty_rate_multiplier = self.config.get('penalty_rate_multiplier', 1.0)
        self.discipline_impact_strength = self.config.get('discipline_impact_strength', 1.0)
        self.situational_modifier_strength = self.config.get('situational_modifier_strength', 1.0)
        
        # Initialize modifiers
        self.situational_modifiers = SituationalModifiers()
        
        # Penalty detection statistics
        self.penalties_detected = 0
        self.penalties_by_phase = {'pre_snap': 0, 'during_play': 0, 'post_play': 0}
        self.penalties_by_type = {}
        
        if self.logger:
            self.logger.info("PenaltyDetector initialized with 3-phase detection system")
    
    def check_pre_snap_penalties(self, offense_team: Dict, defense_team: Dict, 
                                game_state: GameState) -> Optional[PenaltyResult]:
        """
        Check for pre-snap penalties that occur before play simulation.
        
        Pre-snap penalties immediately stop play execution and return a penalty result.
        Common pre-snap penalties: false start, offside, encroachment, delay of game.
        
        Args:
            offense_team: Offensive team data with personnel
            defense_team: Defensive team data with personnel  
            game_state: Current game state for situational context
            
        Returns:
            PenaltyResult if pre-snap penalty detected, None otherwise
        """
        if self.logger:
            self.logger.debug("Checking pre-snap penalties")
        
        # Get situational context for modifiers
        situation_context = self._analyze_game_situation(game_state)
        
        # Check offensive pre-snap penalties
        offensive_penalty = self._check_offensive_pre_snap(offense_team, situation_context)
        if offensive_penalty:
            return self._create_penalty_result(offensive_penalty, nullifies_play=True)
        
        # Check defensive pre-snap penalties  
        defensive_penalty = self._check_defensive_pre_snap(defense_team, situation_context)
        if defensive_penalty:
            return self._create_penalty_result(defensive_penalty, nullifies_play=False)
        
        return None
    
    def check_during_play_penalties(self, play_result: PlayResult, personnel: Dict,
                                  game_state: GameState) -> Optional[PenaltyResult]:
        """
        Check for penalties that occur during play execution.
        
        During-play penalties are evaluated after the play simulation completes
        and can modify the play result. Common during-play penalties: holding,
        pass interference, face mask.
        
        Args:
            play_result: Result of the completed play simulation
            personnel: Personnel involved in the play
            game_state: Current game state for situational context
            
        Returns:
            PenaltyResult if during-play penalty detected, None otherwise
        """
        if self.logger:
            self.logger.debug("Checking during-play penalties")
        
        # Get situational context
        situation_context = self._analyze_game_situation(game_state)
        situation_context.update(self._analyze_play_context(play_result))
        
        # Check for penalties based on play type
        if play_result.play_type == "pass":
            penalty = self._check_pass_play_penalties(play_result, personnel, situation_context)
        elif play_result.play_type == "run":  
            penalty = self._check_run_play_penalties(play_result, personnel, situation_context)
        else:
            penalty = self._check_special_teams_penalties(play_result, personnel, situation_context)
        
        if penalty:
            affects_outcome = self._penalty_affects_play_outcome(penalty, play_result)
            return self._create_penalty_result(penalty, affects_play_outcome=affects_outcome)
        
        return None
    
    def check_post_play_penalties(self, play_result: PlayResult, personnel: Dict,
                                game_state: GameState) -> Optional[PenaltyResult]:
        """
        Check for penalties that occur after play completion.
        
        Post-play penalties occur after the play is over and typically involve
        unsportsmanlike conduct, taunting, or excessive celebration.
        
        Args:
            play_result: Completed play result
            personnel: Personnel involved in the play
            game_state: Current game state for situational context
            
        Returns:
            PenaltyResult if post-play penalty detected, None otherwise
        """
        if self.logger:
            self.logger.debug("Checking post-play penalties")
        
        situation_context = self._analyze_game_situation(game_state)
        situation_context.update(self._analyze_play_context(play_result))
        
        # Check for unsportsmanlike conduct
        penalty = self._check_unsportsmanlike_conduct(play_result, personnel, situation_context)
        
        if penalty:
            return self._create_penalty_result(penalty, affects_play_outcome=False)
        
        return None
    
    def _check_offensive_pre_snap(self, offense_team: Dict, context: Dict) -> Optional[Penalty]:
        """Check for offensive pre-snap penalties."""
        players = offense_team.get('players', {})
        personnel = offense_team.get('personnel', {})
        
        # False start (most common offensive pre-snap penalty)
        ol_players = players.get('offensive_line', [])
        if ol_players and self._penalty_check(PenaltyType.FALSE_START, ol_players, context):
            player = self._select_penalty_player(ol_players)
            player_name = player.name if hasattr(player, 'name') else str(player)
            return create_penalty(PenaltyType.FALSE_START, player_name, PenaltyPhase.PRE_SNAP, "offense")
        
        # Delay of game
        qb_player = players.get('qb')
        if qb_player and self._penalty_check(PenaltyType.DELAY_OF_GAME, [qb_player], context):
            qb_name = qb_player.name if hasattr(qb_player, 'name') else str(qb_player)
            return create_penalty(PenaltyType.DELAY_OF_GAME, qb_name, PenaltyPhase.PRE_SNAP, "offense")
        
        # Too many men on field
        if self._penalty_check(PenaltyType.TOO_MANY_MEN, [], context, position_independent=True):
            player = "Team"  # Team penalty
            return create_penalty(PenaltyType.TOO_MANY_MEN, player, PenaltyPhase.PRE_SNAP, "offense")
        
        return None
    
    def _check_defensive_pre_snap(self, defense_team: Dict, context: Dict) -> Optional[Penalty]:
        """Check for defensive pre-snap penalties.""" 
        players = defense_team.get('players', {})
        personnel = defense_team.get('personnel', {})
        
        # Offside/Encroachment (most common defensive pre-snap penalties)
        dl_players = players.get('defensive_line', [])
        lb_players = players.get('linebackers', [])
        pass_rushers = dl_players + lb_players
        
        if pass_rushers and self._penalty_check(PenaltyType.OFFSIDE, pass_rushers, context):
            player = self._select_penalty_player(pass_rushers)
            player_name = player.name if hasattr(player, 'name') else str(player)
            return create_penalty(PenaltyType.OFFSIDE, player_name, PenaltyPhase.PRE_SNAP, "defense")
        
        if dl_players and self._penalty_check(PenaltyType.ENCROACHMENT, dl_players, context):
            player = self._select_penalty_player(dl_players)
            player_name = player.name if hasattr(player, 'name') else str(player)
            return create_penalty(PenaltyType.ENCROACHMENT, player_name, PenaltyPhase.PRE_SNAP, "defense")
        
        return None
    
    def _check_pass_play_penalties(self, play_result: PlayResult, personnel, 
                                 context: Dict) -> Optional[Penalty]:
        """Check for penalties specific to passing plays."""
        
        # Handle both PersonnelPackage objects and dict formats
        if hasattr(personnel, 'defensive_players'):
            # PersonnelPackage object - extract defensive players
            defensive_line = getattr(personnel, 'dl_on_field', [])
            secondary = []  # PersonnelPackage doesn't separate secondary from dl_on_field
        elif isinstance(personnel, dict):
            # Dict format
            secondary = personnel.get('defense', {}).get('secondary', [])
            defensive_line = personnel.get('defense', {}).get('defensive_line', [])
        else:
            # Fallback - assume no players available
            secondary = []
            defensive_line = []
        
        # Pass interference (most impactful penalty)
        if play_result.outcome in ["incomplete", "interception"] and play_result.receiver:
            # Use defensive line as proxy for secondary if secondary not available
            defenders = secondary if secondary else defensive_line
            if self._penalty_check(PenaltyType.PASS_INTERFERENCE, defenders, context):
                defender = self._select_penalty_player(defenders)
                return create_penalty(PenaltyType.PASS_INTERFERENCE, defender, 
                                    PenaltyPhase.DURING_PLAY, "defense")
        
        # Defensive holding
        if play_result.play_type == "pass":
            defenders = secondary if secondary else defensive_line
            if self._penalty_check(PenaltyType.DEFENSIVE_HOLDING, defenders, context):
                defender = self._select_penalty_player(defenders)
                return create_penalty(PenaltyType.DEFENSIVE_HOLDING, defender,
                                    PenaltyPhase.DURING_PLAY, "defense")
        
        # Offensive holding (pass protection)
        if play_result.outcome == "sack" or (play_result.yards_gained > 15):
            if hasattr(personnel, 'ol_on_field'):
                offensive_line = getattr(personnel, 'ol_on_field', [])
            elif isinstance(personnel, dict):
                offensive_line = personnel.get('offense', {}).get('offensive_line', [])
            else:
                offensive_line = []
                
            if self._penalty_check(PenaltyType.OFFENSIVE_HOLDING, offensive_line, context):
                blocker = self._select_penalty_player(offensive_line)
                return create_penalty(PenaltyType.OFFENSIVE_HOLDING, blocker,
                                    PenaltyPhase.DURING_PLAY, "offense")
        
        return None
    
    def _check_run_play_penalties(self, play_result: PlayResult, personnel,
                                context: Dict) -> Optional[Penalty]:
        """Check for penalties specific to running plays."""
        
        # Offensive holding (more common on big running gains)
        if play_result.yards_gained > 10:
            holding_modifier = 1.0 + (play_result.yards_gained - 10) * 0.02  # +2% per yard over 10
            context['big_gain_modifier'] = holding_modifier
        
        # Get offensive line based on personnel type
        if hasattr(personnel, 'ol_on_field'):
            offensive_line = getattr(personnel, 'ol_on_field', [])
        elif isinstance(personnel, dict):
            offensive_line = personnel.get('offense', {}).get('offensive_line', [])
        else:
            offensive_line = []
            
        if self._penalty_check(PenaltyType.OFFENSIVE_HOLDING, offensive_line, context):
            blocker = self._select_penalty_player(offensive_line)
            return create_penalty(PenaltyType.OFFENSIVE_HOLDING, blocker,
                                PenaltyPhase.DURING_PLAY, "offense")
        
        # Face mask (more common on tackles)
        if play_result.tackler:
            defenders = [play_result.tackler] + ([play_result.assist_tackler] if play_result.assist_tackler else [])
            if self._penalty_check(PenaltyType.FACE_MASK, defenders, context):
                defender = self._select_penalty_player(defenders)
                return create_penalty(PenaltyType.FACE_MASK, defender,
                                    PenaltyPhase.DURING_PLAY, "defense")
        
        # Clipping (rare but possible on run plays)
        if play_result.yards_gained > 20:  # Long runs have higher clipping risk
            if self._penalty_check(PenaltyType.CLIPPING, offensive_line, context):
                blocker = self._select_penalty_player(offensive_line)
                return create_penalty(PenaltyType.CLIPPING, blocker,
                                    PenaltyPhase.DURING_PLAY, "offense")
        
        return None
    
    def _check_special_teams_penalties(self, play_result: PlayResult, personnel,
                                     context: Dict) -> Optional[Penalty]:
        """Check for penalties on special teams plays."""
        # Basic implementation - can be expanded for specific ST penalties
        return None
    
    def _check_unsportsmanlike_conduct(self, play_result: PlayResult, personnel,
                                     context: Dict) -> Optional[Penalty]:
        """Check for post-play unsportsmanlike conduct penalties."""
        
        # Taunting after big plays
        if play_result.yards_gained > 20 or play_result.is_score:
            if play_result.primary_player:
                taunting_context = context.copy()
                taunting_context['big_play_modifier'] = 2.0 if play_result.is_score else 1.5
                
                if self._penalty_check(PenaltyType.TAUNTING, [play_result.primary_player], taunting_context):
                    return create_penalty(PenaltyType.TAUNTING, play_result.primary_player,
                                        PenaltyPhase.POST_PLAY, "offense")
        
        # Unsportsmanlike conduct (general) - extract players based on personnel type
        all_players = []
        if hasattr(personnel, 'ol_on_field'):
            # PersonnelPackage format
            if getattr(personnel, 'ol_on_field', None):
                all_players.extend(getattr(personnel, 'ol_on_field', []))
            if getattr(personnel, 'dl_on_field', None):
                all_players.extend(getattr(personnel, 'dl_on_field', []))
            if getattr(personnel, 'lb_on_field', None):
                all_players.extend(getattr(personnel, 'lb_on_field', []))
        elif isinstance(personnel, dict):
            # Dict format
            if 'offense' in personnel:
                all_players.extend(personnel['offense'].values() if isinstance(personnel['offense'], dict) else [])
            if 'defense' in personnel:
                all_players.extend(personnel['defense'].values() if isinstance(personnel['defense'], dict) else [])
        
        if all_players and self._penalty_check(PenaltyType.UNSPORTSMANLIKE_CONDUCT, all_players, context):
            player = self._select_penalty_player(all_players)
            team = "offense" if random.random() < 0.5 else "defense"  # Random team assignment
            return create_penalty(PenaltyType.UNSPORTSMANLIKE_CONDUCT, player,
                                PenaltyPhase.POST_PLAY, team)
        
        return None
    
    def _penalty_check(self, penalty_type: PenaltyType, candidate_players: List, 
                      context: Dict, position_independent: bool = False) -> bool:
        """
        Core penalty probability check with discipline and situational modifiers.
        
        Args:
            penalty_type: Type of penalty to check
            candidate_players: List of players who could commit this penalty
            context: Situational context for modifiers
            position_independent: Whether penalty is position-independent (team penalties)
            
        Returns:
            True if penalty occurred, False otherwise
        """
        if not candidate_players and not position_independent:
            return False
        
        # Get base penalty rate
        base_rate = PenaltyConstants.get_base_rate(penalty_type.value)
        if base_rate == 0:
            return False
        
        # Apply global rate multiplier
        modified_rate = base_rate * self.penalty_rate_multiplier
        
        # Apply discipline modifier (only for position-specific penalties)
        if not position_independent and candidate_players:
            discipline_modifier = self._calculate_discipline_modifier(candidate_players)
            modified_rate *= discipline_modifier
        
        # Apply situational modifiers
        situational_modifier = self._calculate_situational_modifier(penalty_type, context)
        modified_rate *= situational_modifier
        
        # Cap penalty rate to prevent unrealistic values
        modified_rate = min(0.15, modified_rate)  # Max 15% penalty rate on any single play
        
        # Random roll
        penalty_occurred = random.random() < modified_rate
        
        if penalty_occurred and self.logger:
            self.logger.debug(f"Penalty detected: {penalty_type.value}, rate: {modified_rate:.4f}")
            self._record_penalty_stats(penalty_type)
        
        return penalty_occurred
    
    def _calculate_discipline_modifier(self, players: List) -> float:
        """
        Calculate penalty rate modifier based on player discipline ratings.
        
        Args:
            players: List of players (could be Player objects or strings)
            
        Returns:
            Multiplier for penalty rate (1.0 = no change, >1.0 = more penalties)
        """
        if not players:
            return 1.0
        
        # Handle both Player objects and string names
        discipline_ratings = []
        for player in players:
            if isinstance(player, Player):
                discipline_ratings.append(player.discipline)
            elif hasattr(player, 'discipline'):  # Duck typing for player-like objects
                discipline_ratings.append(player.discipline) 
            else:
                # Default discipline for string names (average)
                discipline_ratings.append(75)
        
        # Use lowest discipline rating (worst behaved player)
        worst_discipline = min(discipline_ratings)
        
        # Convert discipline (0-100) to penalty modifier
        # 100 discipline = 0.5x penalties, 0 discipline = 2.0x penalties
        base_modifier = 2.0 - (worst_discipline / 100.0 * 1.5)
        
        # Apply discipline impact strength from config
        return 1.0 + (base_modifier - 1.0) * self.discipline_impact_strength
    
    def _calculate_situational_modifier(self, penalty_type: PenaltyType, context: Dict) -> float:
        """
        Calculate penalty rate modifier based on game situation.
        
        Args:
            penalty_type: Type of penalty being evaluated
            context: Dictionary of situational factors
            
        Returns:
            Multiplier for penalty rate based on situation
        """
        modifier = 1.0
        
        # Apply relevant situational modifiers
        if context.get('red_zone'):
            modifier *= self.situational_modifiers.red_zone
        if context.get('goal_line'):
            modifier *= self.situational_modifiers.goal_line
        if context.get('fourth_down'):
            modifier *= self.situational_modifiers.fourth_down
        if context.get('two_minute_drill'):
            modifier *= self.situational_modifiers.two_minute_drill
        if context.get('close_game'):
            modifier *= self.situational_modifiers.close_game
        
        # Apply custom modifiers from context
        if 'big_gain_modifier' in context:
            modifier *= context['big_gain_modifier']
        if 'big_play_modifier' in context:
            modifier *= context['big_play_modifier']
        
        # Apply situational modifier strength from config
        return 1.0 + (modifier - 1.0) * self.situational_modifier_strength
    
    def _analyze_game_situation(self, game_state: GameState) -> Dict[str, bool]:
        """
        Analyze current game situation for penalty modifiers.
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary of situational flags
        """
        situation = {}
        
        # Field position analysis
        field_pos = game_state.field.field_position
        situation['red_zone'] = field_pos <= 20
        situation['goal_line'] = field_pos <= 5
        
        # Down and distance analysis
        situation['fourth_down'] = game_state.field.down == 4
        situation['third_and_long'] = (game_state.field.down == 3 and 
                                     game_state.field.yards_to_go >= 7)
        situation['third_and_short'] = (game_state.field.down == 3 and
                                      game_state.field.yards_to_go <= 2)
        
        # Time analysis (if available)
        if hasattr(game_state.clock, 'clock'):
            time_remaining = game_state.clock.clock
            situation['two_minute_drill'] = time_remaining <= 120  # 2 minutes in seconds
        
        # Score analysis (if available)
        if hasattr(game_state, 'scoreboard'):
            score_diff = abs(game_state.scoreboard.home_score - game_state.scoreboard.away_score)
            situation['close_game'] = score_diff <= 7
            situation['blowout'] = score_diff >= 21
        
        return situation
    
    def _analyze_play_context(self, play_result: PlayResult) -> Dict[str, bool]:
        """
        Analyze play result for additional penalty context.
        
        Args:
            play_result: Completed play result
            
        Returns:
            Dictionary of play-specific context flags  
        """
        context = {}
        
        # Play outcome analysis
        context['big_gain'] = play_result.yards_gained > 15
        context['touchdown'] = play_result.is_score and play_result.outcome == "touchdown"
        context['sack'] = play_result.outcome == "sack"
        context['incomplete'] = play_result.outcome == "incomplete"
        context['interception'] = play_result.outcome == "interception"
        
        return context
    
    def _select_penalty_player(self, candidate_players: List) -> str:
        """
        Select which player committed the penalty from candidates.
        
        For simplicity, this randomly selects from candidates, but could be
        enhanced to weight selection based on discipline ratings.
        
        Args:
            candidate_players: List of players who could have committed penalty
            
        Returns:
            Name/ID of selected player
        """
        if not candidate_players:
            return "Unknown"
        
        # Convert Player objects to names if needed
        player_names = []
        for player in candidate_players:
            if isinstance(player, Player):
                player_names.append(player.name)
            else:
                player_names.append(str(player))
        
        return random.choice(player_names)
    
    def _penalty_affects_play_outcome(self, penalty: Penalty, play_result: PlayResult) -> bool:
        """
        Determine if penalty significantly affects the play outcome.
        
        This is used to decide whether to modify the play result or just
        add the penalty as additional information.
        """
        # Major penalties always affect outcome
        if penalty.penalty_yards >= 15:
            return True
        
        # Automatic first down penalties affect outcome
        if penalty.automatic_first_down:
            return True
        
        # Spot fouls affect outcome  
        if penalty.spot_foul:
            return True
        
        # Minor penalties may not significantly affect play
        return penalty.penalty_yards >= 10
    
    def _create_penalty_result(self, penalty: Penalty, affects_play_outcome: bool = True,
                             nullifies_play: bool = False) -> PenaltyResult:
        """
        Create a PenaltyResult with appropriate enforcement context.
        
        Args:
            penalty: The detected penalty
            affects_play_outcome: Whether penalty changes play result  
            nullifies_play: Whether penalty cancels the play entirely
            
        Returns:
            Configured PenaltyResult
        """
        return PenaltyResult(
            penalty=penalty,
            affects_play_outcome=affects_play_outcome,
            nullifies_play=nullifies_play,
            enforcement_context={
                'phase': penalty.phase,
                'penalty_type': penalty.penalty_type,
                'yards': penalty.penalty_yards,
                'auto_first_down': penalty.automatic_first_down
            }
        )
    
    def _record_penalty_stats(self, penalty_type: PenaltyType) -> None:
        """Record penalty statistics for analysis."""
        self.penalties_detected += 1
        
        penalty_str = penalty_type.value
        self.penalties_by_type[penalty_str] = self.penalties_by_type.get(penalty_str, 0) + 1
    
    def get_penalty_statistics(self) -> Dict[str, Any]:
        """
        Get penalty detection statistics for analysis and debugging.
        
        Returns:
            Dictionary with penalty statistics and rates
        """
        expected_stats = get_penalty_summary_stats()
        
        return {
            'penalties_detected': self.penalties_detected,
            'penalties_by_phase': self.penalties_by_phase.copy(),
            'penalties_by_type': self.penalties_by_type.copy(),
            'expected_penalties_per_game': expected_stats['expected_penalties_per_game'],
            'expected_yards_per_game': expected_stats['expected_yards_per_game'],
            'penalty_rate_multiplier': self.penalty_rate_multiplier,
            'discipline_impact_strength': self.discipline_impact_strength
        }
    
    def reset_statistics(self) -> None:
        """Reset penalty statistics counters."""
        self.penalties_detected = 0
        self.penalties_by_phase = {'pre_snap': 0, 'during_play': 0, 'post_play': 0}
        self.penalties_by_type = {}
    
    def set_penalty_rate_multiplier(self, multiplier: float) -> None:
        """
        Adjust the global penalty rate multiplier for tuning.
        
        Args:
            multiplier: Multiplier for all penalty rates (1.0 = default)
        """
        self.penalty_rate_multiplier = max(0.0, multiplier)
        if self.logger:
            self.logger.info(f"Penalty rate multiplier set to {multiplier}")