from typing import Optional, Dict
from ..plays.play_factory import PlayFactory
from ..plays.data_structures import PlayResult
from ..plays.play_calling import PlayCaller
from ..field.game_state import GameState
from ..personnel.player_selector import PlayerSelector


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
        # Extract coaching data from teams (with fallback to balanced archetypes)
        # TODO: Crate a more sophisticated system for the archetype. It needs to rotate depending on who the team is.
        offensive_coordinator = offense_team.get('coaching', {}).get('offensive_coordinator', {'archetype': 'balanced'})
        defensive_coordinator = defense_team.get('coaching', {}).get('defensive_coordinator', {'archetype': 'balanced_defense'})


        """
        Updated and more sophisticaed as of 9/1/25
        """
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
        
        # 5. Enrich the play result with analytical metadata
        self._enrich_play_result_with_metadata(play_result, personnel, game_state)
        
        # 6. Apply play-specific fatigue based on actual effort exerted
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