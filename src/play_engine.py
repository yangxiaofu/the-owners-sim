# play_engine.py - Simple Football Simulation

from play_result import PlayResult
from play_engine_params import PlayEngineParams
from offensive_play_type import OffensivePlayType
from defensive_play_type import DefensivePlayType
from plays.run_play import RunPlaySimulator
from formation import OffensiveFormation, DefensiveFormation

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
    if offensive_play_type == OffensivePlayType.RUN:
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



    elif offensive_play_type == OffensivePlayType.PASS:
        # Pass play simulation  
        return PlayResult(outcome=OffensivePlayType.PASS, yards=8)
    
    elif offensive_play_type == OffensivePlayType.PUNT:
        # Punt play simulation
        return PlayResult(outcome=OffensivePlayType.PUNT, yards=40)
    
    elif offensive_play_type == OffensivePlayType.FIELD_GOAL:
        # Field goal simulation
        return PlayResult(outcome=OffensivePlayType.FIELD_GOAL, yards=0)
    
    elif offensive_play_type == OffensivePlayType.KICKOFF:
        # Kickoff simulation
        return PlayResult(outcome=OffensivePlayType.KICKOFF, yards=25)
    
    elif offensive_play_type == OffensivePlayType.PLAY_ACTION_PASS:
        # Play action simulation
        return PlayResult(outcome=OffensivePlayType.PLAY_ACTION_PASS, yards=12)
    
    elif offensive_play_type == OffensivePlayType.SCREEN_PASS:
        # Screen pass simulation
        return PlayResult(outcome=OffensivePlayType.SCREEN_PASS, yards=6)
    
    else:
        # Default case
        return PlayResult(outcome="incomplete", yards=0)