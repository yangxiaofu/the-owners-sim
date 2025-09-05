# play_engine.py - Simple Football Simulation

from play_result import PlayResult
from play_engine_params import PlayEngineParams
from offensive_play_type import OffensivePlayType
from defensive_play_type import DefensivePlayType

def simulate(play_engine_params):
    """
    Simulate a play between two teams
    
    Args:
        play_engine_params: PlayEngineParams instance containing teams and play calls
        
    Returns:
        PlayResult: Result of the simulated play whether it's a run, pass, kickoff, punt, field goal.
    """

    

    """
    Steps
    1. Simulate PLay 
        Chooses between run, pass, punt, and kickoff
        The success of the play depends on the strength of the offense and the strength of the defense. 
        Then there's an output based the simulation. the
            The playresult will be yards gained, is_turnover_, is_score, time_elapsed, is_kick_off
        
    2. 
    
    """
    
    # Get the offensive play call params
    offensive_play_params = play_engine_params.get_offensive_play()
    offensive_play_type = offensive_play_params.get_play_type()
    
    # Determine play type and simulate accordingly
    if offensive_play_type == OffensivePlayType.RUN:
        # Run play simulation

        """
        In this section I want to understand how to simulate an offensive and defensive against each other. 
        """




        return PlayResult(outcome=OffensivePlayType.RUN, yards=3)
    
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