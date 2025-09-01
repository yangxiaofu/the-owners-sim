from typing import Optional, Dict
import logging
from ..plays.play_factory import PlayFactory
from ..plays.data_structures import PlayResult
from ..plays.play_calling import PlayCaller
from ..field.game_state import GameState
from ..personnel.player_selector import PlayerSelector
from ..coaching.clock.clock_strategy_manager import ClockStrategyManager


class PlayExecutor:
    """
    Orchestrates play execution using the Strategy pattern.
    This class coordinates all the pieces but doesn't contain simulation logic.
    """
    
    def __init__(self, config: Dict = None):
        """
        Initialize the PlayExecutor
        
        Args:
            config: Configuration dict for simulation options
        """
        self.config = config or {}
        self.player_selector = PlayerSelector()
        self.play_caller = PlayCaller()
        self.clock_strategy_manager = ClockStrategyManager()
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        
    def execute_play(self, offense_team: Dict, defense_team: Dict, game_state: GameState) -> PlayResult:
        """
        Execute a single play by coordinating all components
        
        Args:
            offense_team: Dict containing offensive team ratings and data
            defense_team: Dict containing defensive team ratings and data
            game_state: Current game state (field, clock, score)
            
        Returns:
            PlayResult: Complete result of the play execution
        """
        
        # 1. Determine play type using intelligent archetype-based system
        # Use dynamic coaching staff for realistic, adaptive coaching behavior
        coaching_staff = offense_team.get('coaching_staff')
        if coaching_staff:
            # New dynamic coaching system - coaches adapt based on context
            game_context = {
                'opponent': defense_team,
                'score_differential': game_state.get_score_differential() if hasattr(game_state, 'get_score_differential') else 0,
                'time_remaining': game_state.clock.get_time_remaining() if hasattr(game_state.clock, 'get_time_remaining') else 900,
                'field_position': game_state.field.field_position,
                'down': game_state.field.down,
                'yards_to_go': game_state.field.yards_to_go
            }
            offensive_coordinator = coaching_staff.get_offensive_coordinator_for_situation(game_state.field, game_context)
            
            # Get defensive coaching staff for counter-intelligence
            defensive_coaching_staff = defense_team.get('coaching_staff') 
            if defensive_coaching_staff:
                defensive_coordinator = defensive_coaching_staff.get_defensive_coordinator_for_situation(game_state.field, game_context)
            else:
                # Fallback to static defensive archetype
                defensive_coordinator = defense_team.get('coaching', {}).get('defensive_coordinator', {'archetype': 'balanced_defense'})
        else:
            # Fallback to legacy system for backward compatibility
            offensive_coordinator = offense_team.get('coaching', {}).get('offensive_coordinator', {'archetype': 'balanced'})
            defensive_coordinator = defense_team.get('coaching', {}).get('defensive_coordinator', {'archetype': 'balanced_defense'})
        play_type = self._determine_play_type(game_state.field, offensive_coordinator, defensive_coordinator)
        
        # 2. Get personnel for both teams
        personnel = self.player_selector.get_personnel(
            offense_team, defense_team, play_type, game_state.field, self.config
        )

        """
        Each archetype will have a preferred set of playbooks that they can use. But the playbooks will b
        """
        # 3. Create the appropriate play type instance
        play_instance = PlayFactory.create_play(play_type, self.config)
        
        # 4. Execute the play simulation using selected personnel
        play_result = play_instance.simulate(personnel, game_state.field)
        
        # 5. Calculate intelligent time elapsed using ClockStrategyManager
        try:
            # Extract team archetype with validation and fallback
            offense_archetype = self._extract_team_archetype(offense_team)
            
            # Build comprehensive game context
            game_context = self._build_game_context(game_state, offense_team, defense_team)
            
            # Extract completion status for pass plays
            completion_status = self._extract_completion_status(play_result)
            
            # Calculate archetype-based time elapsed
            calculated_time = self.clock_strategy_manager.get_time_elapsed(
                offense_archetype, play_result.play_type, game_context, completion_status
            )
            
            # Update PlayResult with intelligent time calculation
            play_result.time_elapsed = calculated_time
            
            self.logger.debug(f"Clock calculation: archetype={offense_archetype}, "
                           f"play_type={play_result.play_type}, "
                           f"completion_status={completion_status}, "
                           f"calculated_time={calculated_time}s")
            
        except Exception as e:
            self.logger.error(f"Error in clock calculation, using original time: {e}")
            # Keep original time_elapsed from simulation as fallback
            
        # 6. Enrich the play result with analytical metadata
        self._enrich_play_result_with_metadata(play_result, personnel, game_state)
        
        # 7. Apply play-specific fatigue based on actual effort exerted
        self.player_selector.apply_play_fatigue(personnel, play_result)
        
        return play_result
    
    def _determine_play_type(self, field_state, offensive_coordinator: Dict, defensive_coordinator: Optional[Dict] = None) -> str:
        """
        Determine play type using archetype-based intelligent play calling
        
        Args:
            field_state: Current game situation (down, distance, field position)
            offensive_coordinator: Offensive coordinator archetype data
            defensive_coordinator: Optional defensive coordinator data for counter-effects
            
        Returns:
            str: Intelligent play type selection based on coaching archetypes
        """
        return self.play_caller.determine_play_type(field_state, offensive_coordinator, defensive_coordinator)
    
    def _extract_team_archetype(self, team: Dict) -> str:
        """
        Extract team archetype with proper fallback logic
        
        Args:
            team: Team dictionary containing coaching staff or legacy coaching data
            
        Returns:
            str: Team archetype or fallback to 'balanced'
        """
        try:
            # Try new dynamic coaching staff system first
            coaching_staff = team.get('coaching_staff')
            if coaching_staff and hasattr(coaching_staff, 'get_offensive_coordinator'):
                # Get coordinator for current situation - for archetype extraction we can use minimal context
                minimal_context = {'down': 1, 'yards_to_go': 10}
                coordinator = coaching_staff.get_offensive_coordinator_for_situation(None, minimal_context)
                if coordinator and isinstance(coordinator, dict):
                    archetype = coordinator.get('archetype')
                    if archetype:
                        return archetype
            
            # Fallback to legacy coaching system
            coaching = team.get('coaching', {})
            if coaching:
                coordinator = coaching.get('offensive_coordinator', {})
                archetype = coordinator.get('archetype')
                if archetype:
                    return archetype
            
            # Final fallback
            self.logger.warning(f"Could not extract archetype from team, using 'balanced' fallback")
            return 'balanced'
            
        except Exception as e:
            self.logger.error(f"Error extracting team archetype: {e}")
            return 'balanced'
    
    def _build_game_context(self, game_state: GameState, offense_team: Dict, defense_team: Dict) -> Dict:
        """
        Build comprehensive game context for ClockStrategyManager
        
        Args:
            game_state: Current game state
            offense_team: Offensive team data
            defense_team: Defensive team data
            
        Returns:
            Dict: Comprehensive game context
        """
        try:
            # Build base context from game state
            context = {
                'field_state': game_state.field,
                'down': game_state.field.down,
                'distance': game_state.field.yards_to_go,
                'quarter': game_state.clock.quarter,
                'clock': game_state.clock.clock,
                'field_position': game_state.field.field_position,
                'score_differential': self._calculate_score_differential(game_state, offense_team),
                'timeout_situation': False  # TODO: Add timeout detection when available
            }
            
            # Add team context
            context['offense_team'] = offense_team
            context['defense_team'] = defense_team
            
            # Add situational context
            context['red_zone'] = game_state.field.field_position >= 80
            context['goal_line'] = game_state.field.is_goal_line()
            context['two_minute_warning'] = (context['quarter'] in [2, 4] and context['clock'] <= 120)
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error building game context: {e}")
            # Return minimal fallback context
            return {
                'field_state': game_state.field,
                'down': getattr(game_state.field, 'down', 1),
                'distance': getattr(game_state.field, 'yards_to_go', 10),
                'quarter': getattr(game_state.clock, 'quarter', 1),
                'clock': getattr(game_state.clock, 'clock', 900),
                'field_position': getattr(game_state.field, 'field_position', 50),
                'score_differential': 0,
                'timeout_situation': False
            }
    
    def _calculate_score_differential(self, game_state: GameState, offense_team: Dict) -> int:
        """
        Calculate score differential from the perspective of the offensive team
        
        Args:
            game_state: Current game state with scoreboard
            offense_team: Offensive team to calculate differential for
            
        Returns:
            int: Score differential (positive = leading, negative = trailing)
        """
        try:
            # Use the scoreboard's built-in score differential method
            if hasattr(game_state, 'scoreboard') and hasattr(game_state.scoreboard, 'get_score_differential'):
                scoreboard = game_state.scoreboard
                
                # Get team identifier - try multiple approaches for robustness
                team_id = offense_team.get('team_id')
                if team_id is None:
                    team_id = offense_team.get('name', 'offense')
                
                # Use the built-in score differential calculation
                differential = scoreboard.get_score_differential(team_id)
                self.logger.debug(f"Score differential for team {team_id}: {differential}")
                return differential
            
            # Fallback: manually calculate if get_score_differential not available
            elif hasattr(game_state, 'scoreboard'):
                scoreboard = game_state.scoreboard
                team_id = offense_team.get('team_id', offense_team.get('name', 'offense'))
                
                # Check if this team is home or away
                if hasattr(scoreboard, 'home_team_id') and hasattr(scoreboard, 'away_team_id'):
                    if team_id == scoreboard.home_team_id:
                        return scoreboard.home_score - scoreboard.away_score
                    elif team_id == scoreboard.away_team_id:
                        return scoreboard.away_score - scoreboard.home_score
            
            # Final fallback - neutral score
            self.logger.debug("Could not calculate score differential, using neutral (0)")
            return 0
            
        except Exception as e:
            self.logger.warning(f"Error calculating score differential, using neutral: {e}")
            return 0
    
    def _extract_completion_status(self, play_result: PlayResult) -> Optional[str]:
        """
        Extract completion status from play result for pass plays.
        
        Args:
            play_result: The play result containing outcome information
            
        Returns:
            Optional[str]: Completion status ('complete', 'incomplete', 'touchdown', 'interception', etc.)
        """
        # Only relevant for pass plays
        if play_result.play_type != 'pass':
            return None
            
        # Map play outcomes to completion status
        outcome = getattr(play_result, 'outcome', None)
        
        if outcome:
            # Direct mapping for obvious cases
            outcome_mapping = {
                'complete': 'complete',
                'incomplete': 'incomplete', 
                'touchdown': 'touchdown',
                'interception': 'interception',
                'sack': 'incomplete',  # Sacks behave like incomplete passes for clock
                'fumble': 'complete'   # Fumbles happen after completion, so clock runs
            }
            
            completion_status = outcome_mapping.get(outcome)
            if completion_status:
                return completion_status
        
        # If no clear outcome, check other indicators
        # If yards gained > 0, likely a completion
        if hasattr(play_result, 'yards_gained') and play_result.yards_gained > 0:
            return 'complete'
        
        # If yards gained <= 0, likely incomplete or sack
        return 'incomplete'
    
    def _enrich_play_result_with_metadata(self, play_result: PlayResult, personnel, game_state: GameState):
        """
        Enrich the play result with analytical metadata for statistics and reporting.
        
        This method adds contextual information that wasn't part of the core simulation
        but is needed for game analysis, play-by-play reporting, and statistical tracking.
        
        Args:
            play_result: The basic play result from simulation
            personnel: Personnel package used for the play
            game_state: Current game state for context
        """
        # Add formation and defensive call information
        play_result.formation = personnel.formation
        play_result.defensive_call = personnel.defensive_call
        
        # Add game context
        play_result.down = game_state.field.down
        play_result.distance = game_state.field.yards_to_go
        play_result.field_position = game_state.field.field_position
        play_result.quarter = game_state.clock.quarter
        play_result.game_clock = game_state.clock.clock
        
        # Add advanced metrics
        play_result.big_play = play_result.yards_gained >= 20
        play_result.goal_line_play = game_state.field.is_goal_line()
        
        # TODO: Add player tracking when individual players are implemented
        # play_result.primary_player = get_primary_player(personnel, play_result)
        # play_result.tackler = get_tackler(personnel, play_result)