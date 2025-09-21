"""
Simulation Executor

Executes simulations based on calendar events with proper integration
to the FullGameSimulator and other simulation systems.
"""

from datetime import date
from typing import Dict, Any, Optional, List
import logging
import sys
import os

from .event import Event
from .calendar_manager import CalendarManager


class SimulationExecutor:
    """
    Executes simulations based on calendar events.

    Reads event metadata and coordinates with appropriate simulation systems
    to execute games, scouting, drafts, and other dynasty activities.
    """

    def __init__(self, calendar_manager: CalendarManager):
        """
        Initialize the simulation executor.

        Args:
            calendar_manager: CalendarManager instance for event access
        """
        self.calendar_manager = calendar_manager
        self.logger = logging.getLogger("SimulationExecutor")

    def execute_event(self, event: Event) -> Dict[str, Any]:
        """
        Execute a simulation based on an event's metadata.

        Args:
            event: Event to execute

        Returns:
            Dict[str, Any]: Simulation results

        Raises:
            ValueError: If event type is not supported
        """
        if event.is_completed():
            self.logger.warning(f"Event {event.event_id} is already completed")
            return {"status": "already_completed", "result": event.get_simulation_result()}

        event_type = event.get_event_type()

        if event_type == "game_simulation":
            return self._execute_game_simulation(event)
        elif event_type == "draft_simulation":
            return self._execute_draft_simulation(event)
        elif event_type == "scouting_activity":
            return self._execute_scouting_simulation(event)
        elif event_type == "training_camp":
            return self._execute_training_camp_simulation(event)
        elif event_type == "injury_recovery":
            return self._execute_injury_recovery_simulation(event)
        else:
            raise ValueError(f"Unsupported event type: {event_type}")

    def execute_daily_simulations(self, target_date: date, dynasty_id: str) -> Dict[str, Any]:
        """
        Execute all simulations for a specific date and dynasty.

        Args:
            target_date: Date to execute simulations for
            dynasty_id: Dynasty identifier

        Returns:
            Dict[str, Any]: Summary of all executions
        """
        self.logger.info(f"Executing daily simulations for {dynasty_id} on {target_date}")

        # Get all events for the target date
        events = self.calendar_manager.get_events_for_date(target_date)

        # Filter for this dynasty
        dynasty_events = [
            event for event in events
            if event.get_dynasty_id() == dynasty_id and not event.is_completed()
        ]

        if not dynasty_events:
            self.logger.info(f"No events to execute for dynasty {dynasty_id} on {target_date}")
            return {
                "date": target_date.isoformat(),
                "dynasty_id": dynasty_id,
                "events_found": 0,
                "events_executed": 0,
                "results": []
            }

        # Execute each event
        execution_results = []
        successful_executions = 0

        for event in dynasty_events:
            try:
                self.logger.info(f"Executing event: {event.name}")
                result = self.execute_event(event)

                # Update event with results
                if result.get("status") == "success":
                    simulation_result = result.get("simulation_data", {})
                    success = self.calendar_manager.mark_event_completed(
                        event.event_id,
                        simulation_result
                    )

                    if success:
                        successful_executions += 1
                        self.logger.info(f"Successfully completed event: {event.name}")
                    else:
                        self.logger.error(f"Failed to mark event {event.name} as completed")

                execution_results.append({
                    "event_id": event.event_id,
                    "event_name": event.name,
                    "event_type": event.get_event_type(),
                    "status": result.get("status"),
                    "result": result
                })

            except Exception as e:
                self.logger.error(f"Failed to execute event {event.name}: {e}")
                execution_results.append({
                    "event_id": event.event_id,
                    "event_name": event.name,
                    "event_type": event.get_event_type(),
                    "status": "error",
                    "error": str(e)
                })

        return {
            "date": target_date.isoformat(),
            "dynasty_id": dynasty_id,
            "events_found": len(dynasty_events),
            "events_executed": successful_executions,
            "results": execution_results
        }

    def _execute_game_simulation(self, event: Event) -> Dict[str, Any]:
        """
        Execute a game simulation using FullGameSimulator.

        Args:
            event: Game event to execute

        Returns:
            Dict[str, Any]: Game simulation results
        """
        try:
            # Import FullGameSimulator here to avoid circular imports
            from ..game_management.full_game_simulator import FullGameSimulator

            config = event.get_simulation_config()

            # Validate required configuration
            required_fields = ["away_team_id", "home_team_id"]
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required configuration: {field}")

            # Create and configure simulator
            simulator = FullGameSimulator(
                away_team_id=config["away_team_id"],
                home_team_id=config["home_team_id"],
                overtime_type=config.get("overtime_type", "regular_season"),
                enable_persistence=config.get("enable_persistence", True),
                database_path=config.get("database_path"),
                dynasty_id=event.get_dynasty_id()
            )

            # Execute game simulation
            game_result = simulator.simulate_game(date=event.event_date)

            # Extract key results for event storage
            simulation_data = {
                "final_score": game_result.final_score,
                "winner_id": game_result.winner.team_id if game_result.winner else None,
                "total_plays": game_result.total_plays,
                "total_drives": game_result.total_drives,
                "game_duration_minutes": game_result.game_duration_minutes
            }

            # Add detailed statistics if available
            if game_result.final_statistics:
                simulation_data["detailed_statistics"] = game_result.final_statistics

            self.logger.info(f"Game simulation completed: {game_result.final_score}")

            return {
                "status": "success",
                "simulation_type": "game",
                "simulation_data": simulation_data,
                "game_result": game_result  # Full result for immediate access
            }

        except Exception as e:
            self.logger.error(f"Game simulation failed: {e}")
            return {
                "status": "error",
                "simulation_type": "game",
                "error": str(e)
            }

    def _execute_draft_simulation(self, event: Event) -> Dict[str, Any]:
        """
        Execute a draft simulation (placeholder for future implementation).

        Args:
            event: Draft event to execute

        Returns:
            Dict[str, Any]: Draft simulation results
        """
        self.logger.info(f"Draft simulation not yet implemented: {event.name}")

        # Placeholder implementation
        config = event.get_simulation_config()

        simulation_data = {
            "draft_type": config.get("draft_type", "nfl_draft"),
            "rounds_completed": config.get("rounds", 7),
            "teams_participated": len(config.get("teams_participating", [])),
            "status": "completed_placeholder"
        }

        return {
            "status": "success",
            "simulation_type": "draft",
            "simulation_data": simulation_data,
            "note": "Draft simulation is a placeholder implementation"
        }

    def _execute_scouting_simulation(self, event: Event) -> Dict[str, Any]:
        """
        Execute a scouting simulation (placeholder for future implementation).

        Args:
            event: Scouting event to execute

        Returns:
            Dict[str, Any]: Scouting simulation results
        """
        self.logger.info(f"Scouting simulation not yet implemented: {event.name}")

        config = event.get_simulation_config()

        simulation_data = {
            "scout_team_id": config.get("scout_team_id"),
            "scouting_type": config.get("scouting_type"),
            "targets_scouted": len(config.get("targets", [])),
            "budget_used": config.get("budget_allocated", 0),
            "reports_generated": len(config.get("targets", [])),
            "status": "completed_placeholder"
        }

        return {
            "status": "success",
            "simulation_type": "scouting",
            "simulation_data": simulation_data,
            "note": "Scouting simulation is a placeholder implementation"
        }

    def _execute_training_camp_simulation(self, event: Event) -> Dict[str, Any]:
        """
        Execute a training camp simulation (placeholder for future implementation).

        Args:
            event: Training camp event to execute

        Returns:
            Dict[str, Any]: Training camp simulation results
        """
        self.logger.info(f"Training camp simulation not yet implemented: {event.name}")

        config = event.get_simulation_config()

        simulation_data = {
            "team_id": config.get("team_id"),
            "duration_days": config.get("duration_days", 14),
            "focus_areas": config.get("focus_areas", []),
            "players_improved": 0,  # Placeholder
            "injuries_occurred": 0,  # Placeholder
            "status": "completed_placeholder"
        }

        return {
            "status": "success",
            "simulation_type": "training_camp",
            "simulation_data": simulation_data,
            "note": "Training camp simulation is a placeholder implementation"
        }

    def _execute_injury_recovery_simulation(self, event: Event) -> Dict[str, Any]:
        """
        Execute an injury recovery simulation (placeholder for future implementation).

        Args:
            event: Injury recovery event to execute

        Returns:
            Dict[str, Any]: Injury recovery simulation results
        """
        self.logger.info(f"Injury recovery simulation not yet implemented: {event.name}")

        config = event.get_simulation_config()

        simulation_data = {
            "player_name": config.get("player_name"),
            "team_id": config.get("team_id"),
            "injury_type": config.get("injury_type"),
            "recovery_success": True,  # Placeholder
            "recovery_percentage": 100,  # Placeholder
            "return_to_play": True,  # Placeholder
            "status": "completed_placeholder"
        }

        return {
            "status": "success",
            "simulation_type": "injury_recovery",
            "simulation_data": simulation_data,
            "note": "Injury recovery simulation is a placeholder implementation"
        }

    def simulate_dynasty_day(self, dynasty_id: str, advance_calendar: bool = True) -> Dict[str, Any]:
        """
        Simulate a full day for a dynasty, executing all events and optionally advancing the calendar.

        Args:
            dynasty_id: Dynasty identifier
            advance_calendar: Whether to advance the calendar to the next day

        Returns:
            Dict[str, Any]: Day simulation summary
        """
        current_date = self.calendar_manager.get_current_date()

        self.logger.info(f"Simulating day {current_date} for dynasty {dynasty_id}")

        # Execute all events for today
        day_results = self.execute_daily_simulations(current_date, dynasty_id)

        # Advance calendar if requested
        if advance_calendar:
            next_date = self.calendar_manager.advance_date()
            day_results["calendar_advanced"] = True
            day_results["next_date"] = next_date.isoformat()
        else:
            day_results["calendar_advanced"] = False

        return day_results

    def simulate_dynasty_week(self, dynasty_id: str, days: int = 7) -> Dict[str, Any]:
        """
        Simulate multiple days for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            days: Number of days to simulate

        Returns:
            Dict[str, Any]: Week simulation summary
        """
        start_date = self.calendar_manager.get_current_date()

        self.logger.info(f"Simulating {days} days for dynasty {dynasty_id} starting {start_date}")

        week_results = {
            "start_date": start_date.isoformat(),
            "dynasty_id": dynasty_id,
            "days_simulated": 0,
            "total_events": 0,
            "total_games": 0,
            "daily_results": []
        }

        for day in range(days):
            day_result = self.simulate_dynasty_day(dynasty_id, advance_calendar=True)
            week_results["daily_results"].append(day_result)
            week_results["days_simulated"] += 1
            week_results["total_events"] += day_result.get("events_executed", 0)

            # Count games specifically
            for result in day_result.get("results", []):
                if result.get("event_type") == "game_simulation":
                    week_results["total_games"] += 1

        end_date = self.calendar_manager.get_current_date()
        week_results["end_date"] = end_date.isoformat()

        self.logger.info(f"Week simulation completed: {week_results['total_events']} events executed")

        return week_results

    def get_execution_status(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get the current execution status for a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict[str, Any]: Status information
        """
        current_date = self.calendar_manager.get_current_date()

        # Get upcoming events
        upcoming_events = self.calendar_manager.get_upcoming_games(dynasty_id, limit=5)

        # Get dynasty summary
        dynasty_summary = self.calendar_manager.get_dynasty_summary(dynasty_id)

        return {
            "current_date": current_date.isoformat(),
            "dynasty_id": dynasty_id,
            "upcoming_events": [
                {
                    "event_id": event.event_id,
                    "name": event.name,
                    "date": event.event_date.isoformat(),
                    "type": event.get_event_type(),
                    "status": event.get_status()
                }
                for event in upcoming_events
            ],
            "dynasty_summary": dynasty_summary
        }