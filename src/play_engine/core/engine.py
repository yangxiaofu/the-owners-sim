# play_engine.py - Simple Football Simulation

from .play_result import PlayResult
from .params import PlayEngineParams
from ..play_types.base_types import PlayType
from ..play_types.offensive_types import OffensivePlayType, PuntPlayType
from ..play_types.defensive_types import DefensivePlayType
from ..simulation.run_plays import RunPlaySimulator
from ..simulation.pass_plays import PassPlaySimulator
from ..simulation.spike_play import SpikePlaySimulator
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
    coverage_scheme = defensive_play_call.get_coverage()  # NEW: Extract coverage scheme
    
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
                defensive_formation=defensive_formation,
                offensive_team_id=play_engine_params.get_offensive_team_id(),
                defensive_team_id=play_engine_params.get_defensive_team_id(),
                coverage_scheme=coverage_scheme,  # Pass coverage scheme to simulator
                momentum_modifier=play_engine_params.get_momentum_modifier(),  # Pass momentum modifier

                # Environmental context (Tollgate 6: Environmental & Situational Modifiers)
                weather_condition=play_engine_params.get_weather_condition(),
                crowd_noise_level=play_engine_params.get_crowd_noise_level(),
                clutch_factor=play_engine_params.get_clutch_factor(),  # NEW: Clutch performance
                primetime_variance=play_engine_params.get_primetime_variance(),  # NEW: Primetime variance
                is_away_team=play_engine_params.is_away_team_offensive(),

                # RB rotation: Pre-selected ball carrier for workload distribution
                selected_ball_carrier=play_engine_params.get_selected_ball_carrier(),

                # NEW: Variance & unpredictability trackers (Tollgate 7)
                performance_tracker=play_engine_params.get_performance_tracker(),  # RB hot/cold streaks

                # ✅ FIX 1: Pass field position for touchdown detection
                field_position=play_engine_params.get_field_position()
            )
            
            # Create context with actual field position for penalty calculations
            run_context = PlayContext(
                play_type=PlayType.RUN,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation,
                field_position=play_engine_params.get_field_position(),
                down=play_engine_params.get_down(),
                distance=play_engine_params.get_distance()
            )

            # Get comprehensive simulation results
            play_summary = simulator.simulate_run_play(context=run_context)

            # Preserve the detailed outcome from RunPlaySimulator
            # (e.g., "run_success", "tackle_for_loss", "fumble", etc.)
            detailed_outcome = getattr(play_summary, 'play_type', OffensivePlayType.RUN)

            # Detect turnovers from outcome (fumbles on run plays)
            outcome_str = str(detailed_outcome).lower() if detailed_outcome else ""
            is_fumble = 'fumble' in outcome_str
            is_turnover = is_fumble

            # Determine if first down achieved (yards gained >= yards to go, and not a turnover)
            yards_to_go = play_engine_params.get_distance()
            achieved_first_down = (
                play_summary.yards_gained >= yards_to_go
                and yards_to_go > 0
                and not is_turnover
                and not play_summary.points_scored > 0  # TDs don't count as first downs
            )

            # Convert to backward-compatible PlayResult with player stats
            # Transfer penalty info from play_summary to PlayResult
            result = PlayResult(
                outcome=detailed_outcome,  # ✅ Preserve specific outcome
                yards=play_summary.yards_gained,
                time_elapsed=play_summary.time_elapsed,
                player_stats_summary=play_summary,
                points=play_summary.points_scored,
                is_scoring_play=(play_summary.points_scored > 0),
                penalty_occurred=getattr(play_summary, 'penalty_occurred', False),
                penalty_yards=getattr(play_summary, 'original_yards', 0) - play_summary.yards_gained if getattr(play_summary, 'penalty_occurred', False) else 0,
                play_negated=getattr(play_summary, 'play_negated', False),  # For penalty down handling
                # Turnover detection
                is_turnover=is_turnover,
                turnover_type="fumble" if is_fumble else None,
                change_of_possession=is_turnover,
                # First down tracking
                achieved_first_down=achieved_first_down,
                # NEW: Transfer enforcement result for ball placement
                enforcement_result=getattr(play_summary, 'enforcement_result', None)
            )
            return result

        case OffensivePlayType.PASS:
            # Use comprehensive PassPlaySimulator for realistic pass play simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create and run simulator with formations from play calls
            simulator = PassPlaySimulator(
                offensive_players=offensive_players,
                defensive_players=defensive_players,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation,
                offensive_team_id=play_engine_params.get_offensive_team_id(),
                defensive_team_id=play_engine_params.get_defensive_team_id(),
                coverage_scheme=coverage_scheme,  # Pass coverage scheme to simulator
                momentum_modifier=play_engine_params.get_momentum_modifier(),  # Pass momentum modifier

                # NEW: Pass environmental context (Tollgate 6: Environmental & Situational Modifiers)
                weather_condition=play_engine_params.get_weather_condition(),
                crowd_noise_level=play_engine_params.get_crowd_noise_level(),
                clutch_factor=play_engine_params.get_clutch_factor(),
                primetime_variance=play_engine_params.get_primetime_variance(),
                is_away_team=play_engine_params.is_away_team_offensive(),

                # NEW: Pass variance & unpredictability trackers (Tollgate 7)
                performance_tracker=play_engine_params.get_performance_tracker(),

                # ✅ FIX 1: Pass field position for touchdown detection
                field_position=play_engine_params.get_field_position()
            )
            
            # Create context with actual field position for penalty calculations
            pass_context = PlayContext(
                play_type=PlayType.PASS,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation,
                field_position=play_engine_params.get_field_position(),
                down=play_engine_params.get_down(),
                distance=play_engine_params.get_distance()
            )

            # Get comprehensive simulation results
            play_summary = simulator.simulate_pass_play(context=pass_context)

            # Preserve the detailed outcome from PassPlaySimulator
            # (e.g., "completion", "incomplete", "sack", "interception", etc.)
            detailed_outcome = getattr(play_summary, 'play_type', OffensivePlayType.PASS)

            # Detect turnovers from outcome
            outcome_str = str(detailed_outcome).lower() if detailed_outcome else ""
            is_interception = 'interception' in outcome_str
            is_fumble = 'fumble' in outcome_str
            is_turnover = is_interception or is_fumble

            # Determine if first down achieved (yards gained >= yards to go, and not a turnover)
            yards_to_go = play_engine_params.get_distance()
            achieved_first_down = (
                play_summary.yards_gained >= yards_to_go
                and yards_to_go > 0
                and not is_turnover
                and not play_summary.points_scored > 0  # TDs don't count as first downs
            )

            # Convert to backward-compatible PlayResult with player stats
            # Transfer penalty info from play_summary to PlayResult
            result = PlayResult(
                outcome=detailed_outcome,  # ✅ Preserve specific outcome
                yards=play_summary.yards_gained,
                time_elapsed=play_summary.time_elapsed,
                player_stats_summary=play_summary,
                points=play_summary.points_scored,
                is_scoring_play=(play_summary.points_scored > 0),
                penalty_occurred=getattr(play_summary, 'penalty_occurred', False),
                penalty_yards=getattr(play_summary, 'original_yards', 0) - play_summary.yards_gained if getattr(play_summary, 'penalty_occurred', False) else 0,
                play_negated=getattr(play_summary, 'play_negated', False),  # For penalty down handling
                # Turnover detection
                is_turnover=is_turnover,
                turnover_type="interception" if is_interception else ("fumble" if is_fumble else None),
                change_of_possession=is_turnover,
                # First down tracking
                achieved_first_down=achieved_first_down,
                # NEW: Transfer enforcement result for ball placement
                enforcement_result=getattr(play_summary, 'enforcement_result', None)
            )
            return result

        case OffensivePlayType.SPIKE:
            # Handle spike plays for clock management
            simulator = SpikePlaySimulator()

            # Validate spike is legal
            down = play_engine_params.down_state.current_down
            quarter = play_engine_params.game_context.quarter

            if not simulator.can_spike(down, quarter):
                # Illegal spike (4th down) - treat as incomplete pass
                import logging
                logging.warning("Illegal spike attempted, treating as incomplete pass")
                # Fall back to incomplete pass outcome
                return PlayResult(
                    outcome="incomplete",
                    yards=0,
                    points=0,
                    time_elapsed=6.0,
                    is_scoring_play=False,
                    is_turnover=False,
                    achieved_first_down=False,
                    change_of_possession=False
                )

            # Execute legal spike play
            return simulator.simulate_spike()

        case OffensivePlayType.FIELD_GOAL:
            # Use comprehensive FieldGoalSimulator for realistic field goal and fake attempts
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create field goal context with actual field position, down, and distance
            fg_context = PlayContext(
                play_type=PlayType.FIELD_GOAL,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation,
                field_position=play_engine_params.get_field_position(),
                down=play_engine_params.get_down(),
                distance=play_engine_params.get_distance()
            )
            
            try:
                # ✅ FIXED: Pass string formations directly like run/pass plays (no enum conversion)
                from ..simulation.field_goal import FieldGoalPlayParams
                fg_params = FieldGoalPlayParams(
                    fg_type="real_fg",  # Default to real field goal
                    defensive_formation=defensive_formation,  # Pass string directly
                    context=fg_context
                )
                
                # Create and run simulator with formations AND environmental params
                simulator = FieldGoalSimulator(
                    offensive_players=offensive_players,
                    defensive_players=defensive_players,
                    offensive_formation=offensive_formation,
                    defensive_formation=defensive_formation,

                    # NEW: Pass environmental context (subset - no clutch/primetime for FG)
                    weather_condition=play_engine_params.get_weather_condition(),
                    crowd_noise_level=play_engine_params.get_crowd_noise_level(),
                    is_away_team=play_engine_params.is_away_team_offensive()
                )
                
                # Get comprehensive simulation results using validated enum params
                fg_result = simulator.simulate_field_goal_play(fg_params)
                
                # Convert to backward-compatible PlayResult
                # Map field goal outcomes to appropriate result format
                if fg_result.field_goal_outcome == "made":
                    outcome = "field_goal_made"
                elif fg_result.is_fake_field_goal:
                    # ✅ FIX: Strip "fake_" prefix from outcome to avoid duplication (e.g., "fake_run_fake_failed" → "fake_run_failed")
                    clean_outcome = fg_result.field_goal_outcome.replace("fake_", "")
                    outcome = f"fake_{fg_result.fake_field_goal_type}_{clean_outcome}"
                else:
                    outcome = f"field_goal_{fg_result.field_goal_outcome}"
                
                return PlayResult(
                    outcome=outcome,
                    yards=fg_result.yards_gained,
                    points=fg_result.points_scored,
                    time_elapsed=fg_result.time_elapsed,
                    player_stats_summary=fg_result,
                    is_scoring_play=(fg_result.points_scored > 0)  # Mark scoring field goals
                )
                
            except ValueError as e:
                # Formation validation failed - return generic field goal missed outcome
                return PlayResult(
                    outcome="field_goal_execution_failed",
                    yards=0,
                    points=0,
                    time_elapsed=30.0,
                    is_scoring_play=False
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
                defensive_formation=defensive_formation,
                field_position=play_engine_params.get_field_position(),
                down=play_engine_params.get_down(),
                distance=play_engine_params.get_distance()
            )
            
            # TODO: In future, get punt_type from play_engine_params.get_punt_params()
            # For now, default to real punt for compatibility
            try:
                # ✅ FIXED: Pass string formations directly like run/pass plays (no enum conversion)
                punt_params = PuntPlayParams(
                    punt_type=PuntPlayType.REAL_PUNT,  # Default to real punt
                    defensive_formation=defensive_formation,  # Pass string directly
                    context=punt_context
                )
                
                # Create and run simulator with formations from play calls
                simulator = PuntSimulator(
                    offensive_players=offensive_players,
                    defensive_players=defensive_players,
                    offensive_formation=offensive_formation,
                    defensive_formation=defensive_formation,
                    random_event_checker=play_engine_params.get_random_event_checker()  # NEW (Tollgate 7)
                )
                
                # Get comprehensive simulation results
                punt_result = simulator.simulate_punt_play(punt_params)
                
                # Convert PlayStatsSummary to enhanced PlayResult with two-stage data
                return PlayResult(
                    outcome=punt_result.play_type,  # Specific punt outcome
                    yards=punt_result.yards_gained,  # Net punt yards (punt distance - return yards)
                    time_elapsed=punt_result.time_elapsed,
                    player_stats_summary=punt_result,
                    is_punt=True,  # Mark as punt for drive management
                    change_of_possession=True,  # ✅ Punts always change possession
                    is_turnover=False,  # Normal punt is not a turnover (unless blocked/muffed)
                    punt_distance=getattr(punt_result, 'punt_distance', None),
                    return_yards=getattr(punt_result, 'return_yards', None),
                    hang_time=getattr(punt_result, 'hang_time', None),
                    coverage_pressure=getattr(punt_result, 'coverage_pressure', None)
                )
                
            except Exception as e:
                # Any punt execution failure - preserve punt context using utility
                from .play_result import create_failed_punt_result
                return create_failed_punt_result(str(e))
        
        case OffensivePlayType.KICKOFF:
            # Use comprehensive KickoffSimulator for NFL 2024 Dynamic Kickoff simulation
            offensive_players = play_engine_params.get_offensive_players()
            defensive_players = play_engine_params.get_defensive_players()
            
            # Create kickoff context with actual field position, down, and distance
            kickoff_context = PlayContext(
                play_type=PlayType.KICKOFF,
                offensive_formation=offensive_formation,
                defensive_formation=defensive_formation,
                field_position=play_engine_params.get_field_position(),
                down=play_engine_params.get_down(),
                distance=play_engine_params.get_distance()
            )
            
            try:
                # ✅ FIXED: Pass string formations directly like run/pass plays (no enum conversion)
                from ..simulation.kickoff import KickoffPlayParams
                kickoff_params = KickoffPlayParams(
                    kickoff_type="regular_kickoff",  # Default to regular kickoff
                    defensive_formation=defensive_formation,  # Pass string directly
                    context=kickoff_context
                )
                
                # Create and run simulator with formations from play calls
                simulator = KickoffSimulator(
                    offensive_players=offensive_players,
                    defensive_players=defensive_players,
                    offensive_formation=offensive_formation,
                    defensive_formation=defensive_formation,
                    offensive_team_id=play_engine_params.get_offensive_team_id(),
                    defensive_team_id=play_engine_params.get_defensive_team_id()
                )
                
                # Get comprehensive simulation results using validated enum params
                kickoff_result = simulator.simulate_kickoff_play(kickoff_params)
                
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
                    player_stats_summary=kickoff_result,
                    is_scoring_play=(kickoff_result.points_scored > 0)  # Mark kickoff return touchdowns
                )
                
            except ValueError as e:
                # Formation validation failed - return generic kickoff failed outcome
                return PlayResult(
                    outcome="kickoff_execution_failed",
                    yards=0,
                    points=0,
                    time_elapsed=25.0,
                    is_scoring_play=False
                )


        case _:
            # Error for unhandled play types
            raise ValueError(f"Unhandled play type: {offensive_play_type}")