# play_engine.py - Simple Football Simulation

from .result import PlayResult
from .params import PlayEngineParams
from ..play_types.base_types import PlayType
from ..play_types.offensive_types import OffensivePlayType, PuntPlayType
from ..play_types.defensive_types import DefensivePlayType
from ..simulation.run_plays import RunPlaySimulator
from ..simulation.pass_plays import PassPlaySimulator
from ..simulation.field_goal import FieldGoalSimulator
from ..simulation.kickoff import KickoffSimulator
from ..simulation.punt import PuntSimulator, PuntPlayParams
from ..mechanics.penalties.penalty_engine import PlayContext
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
            
            # Convert to backward-compatible PlayResult with player stats
            return PlayResult(outcome=OffensivePlayType.RUN, yards=play_summary.yards_gained, time_elapsed=play_summary.time_elapsed, player_stats_summary=play_summary)

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
            
            # Convert to backward-compatible PlayResult with player stats
            return PlayResult(outcome=OffensivePlayType.PASS, yards=play_summary.yards_gained, time_elapsed=play_summary.time_elapsed, player_stats_summary=play_summary)
        
        case OffensivePlayType.FIELD_GOAL:
            # Use comprehensive FieldGoalSimulator for realistic field goal and fake attempts
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create and run simulator with formations from play calls
            simulator = FieldGoalSimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # Get comprehensive simulation results
            fg_result = simulator.simulate_field_goal_play()
            
            # Convert to backward-compatible PlayResult
            # Map field goal outcomes to appropriate result format
            if fg_result.field_goal_outcome == "made":
                outcome = OffensivePlayType.FIELD_GOAL
            elif fg_result.is_fake_field_goal:
                outcome = f"fake_{fg_result.fake_field_goal_type}_{fg_result.field_goal_outcome}"
            else:
                outcome = f"field_goal_{fg_result.field_goal_outcome}"
            
            return PlayResult(
                outcome=outcome,
                yards=fg_result.yards_gained,
                points=fg_result.points_scored,
                time_elapsed=fg_result.time_elapsed,
                player_stats_summary=fg_result
            )
        
        case OffensivePlayType.PUNT:
            # Use comprehensive PuntSimulator for realistic punt play simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create punt play parameters from external play calling
            # For now, default to real punt - external systems should provide punt_params
            punt_context = PlayContext(
                play_type=PlayType.PUNT,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # TODO: In future, get punt_type from play_engine_params.get_punt_params()
            # For now, default to real punt for compatibility
            punt_params = PuntPlayParams(
                punt_type=PuntPlayType.REAL_PUNT,  # Default to real punt
                defensive_formation=defensive_formation,
                context=punt_context
            )
            
            # Create and run simulator with formations from play calls
            simulator = PuntSimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # Get comprehensive simulation results
            punt_result = simulator.simulate_punt_play(punt_params)
            
            # Convert PlayStatsSummary to backward-compatible PlayResult with player stats
            return PlayResult(
                outcome=punt_result.play_type,  # Will be PlayType.PUNT 
                yards=punt_result.yards_gained,  # Net punt yards (punt distance - return yards)
                time_elapsed=punt_result.time_elapsed,
                player_stats_summary=punt_result
            )
        
        case OffensivePlayType.KICKOFF:
            # Use comprehensive KickoffSimulator for NFL 2024 Dynamic Kickoff simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create and run simulator with formations from play calls
            simulator = KickoffSimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation
            )
            
            # Get comprehensive simulation results
            kickoff_result = simulator.simulate_kickoff_play()
            
            # Convert to backward-compatible PlayResult
            # Map kickoff outcomes to appropriate result format
            if kickoff_result.outcome.name in ["TOUCHBACK_END_ZONE", "TOUCHBACK_LANDING_ZONE"]:
                outcome = "touchback"
            elif kickoff_result.outcome.name == "ONSIDE_RECOVERY":
                outcome = "onside_recovery"
            elif kickoff_result.outcome.name == "RETURN_TOUCHDOWN":
                outcome = "kickoff_return_touchdown"
            else:
                outcome = f"kickoff_{kickoff_result.outcome.name.lower()}"
            
            return PlayResult(
                outcome=outcome,
                yards=kickoff_result.yards_gained,
                points=kickoff_result.points_scored,
                time_elapsed=kickoff_result.time_elapsed,
                player_stats_summary=kickoff_result
            )


        case _:
            # Error for unhandled play types
            raise ValueError(f"Unhandled play type: {offensive_play_type}")