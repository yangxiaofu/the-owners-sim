# play_engine.py - Simple Football Simulation

from play_result import PlayResult
from play_engine_params import PlayEngineParams
from ..play_types.offensive_types import OffensivePlayType
from ..play_types.defensive_types import DefensivePlayType
from ..simulation.run_plays import RunPlaySimulator
from ..simulation.pass_plays import PassPlaySimulator
from ..mechanics.formations import OffensiveFormation, DefensiveFormation

def simulate(play_engine_params):
    """
    Simulate a play between two teams
    
    Args:
        play_engine_params: PlayEngineParams instance containing teams and play calls
        
    Returns:
        PlayResult: Result of the simulated play whether it's a run, pass, kickoff, punt, field goal.
    """
    
    # Get play call objects and extract information
    offensive_play_call = play_engine_params.get_offensive_play_call()
    defensive_play_call = play_engine_params.get_defensive_play_call()
    
    offensive_play_type = offensive_play_call.get_play_type()
    offensive_formation = offensive_play_call.get_formation()
    defensive_formation = defensive_play_call.get_formation()
    
    # Determine play type and simulate accordingly
    match offensive_play_type:
        case OffensivePlayType.RUN:
            # Use new RunPlaySimulator for comprehensive run play simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create and run simulator with formations from play calls
            simulator = RunPlaySimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # Get comprehensive simulation results
            play_summary = simulator.simulate_run_play()
            
            # Convert to backward-compatible PlayResult
            # TODO: In future, could return enhanced result with player stats
            return PlayResult(outcome=OffensivePlayType.RUN, yards=play_summary.yards_gained)

        case OffensivePlayType.PASS:
            # Use comprehensive PassPlaySimulator for realistic pass play simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create and run simulator with formations from play calls
            simulator = PassPlaySimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # Get comprehensive simulation results
            play_summary = simulator.simulate_pass_play()
            
            # Convert to backward-compatible PlayResult
            # TODO: In future, could return enhanced result with comprehensive pass stats
            return PlayResult(outcome=OffensivePlayType.PASS, yards=play_summary.yards_gained)
        
        case OffensivePlayType.FIELD_GOAL:
            # Field goal simulation
            return PlayResult(outcome=OffensivePlayType.FIELD_GOAL, yards=0)
        
        case OffensivePlayType.PUNT:
            # Punt play simulation
            return PlayResult(outcome=OffensivePlayType.PUNT, yards=40)
        
        case OffensivePlayType.KICKOFF:
            # Kickoff simulation
            return PlayResult(outcome=OffensivePlayType.KICKOFF, yards=25)
        
        case OffensivePlayType.TWO_POINT_CONVERSION:
            # Two-point conversion simulation
            return PlayResult(outcome=OffensivePlayType.TWO_POINT_CONVERSION, yards=0)
        
        case _:
            # Error for unhandled play types
            raise ValueError(f"Unhandled play type: {offensive_play_type}")