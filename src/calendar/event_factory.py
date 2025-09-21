"""
Event Factory

Factory class for creating properly structured simulation events.
Ensures consistent metadata structure and validation for different event types.
"""

from datetime import date
from typing import List, Optional, Dict, Any
import logging

from .event import Event


class EventFactory:
    """
    Factory for creating properly structured simulation events.

    Provides static methods for creating different types of events with
    consistent metadata structure and proper configuration.
    """

    logger = logging.getLogger("EventFactory")

    @staticmethod
    def create_game_event(
        name: str,
        event_date: date,
        away_team_id: int,
        home_team_id: int,
        week: int,
        season: int,
        dynasty_id: str,
        overtime_type: str = "regular_season",
        database_path: Optional[str] = None,
        enable_persistence: bool = True,
        weather_conditions: Optional[str] = None,
        **additional_config
    ) -> Event:
        """
        Create a game simulation event with proper metadata structure.

        Args:
            name: Game name (e.g., "Week 1: Browns @ Texans")
            event_date: Date the game is scheduled
            away_team_id: Team ID for away team (1-32)
            home_team_id: Team ID for home team (1-32)
            week: Week number in season
            season: Season year
            dynasty_id: Dynasty identifier
            overtime_type: Type of overtime rules ("regular_season" or "playoffs")
            database_path: Optional custom database path
            enable_persistence: Whether to enable statistics persistence
            weather_conditions: Optional weather description
            **additional_config: Additional simulation configuration

        Returns:
            Event: Properly structured game event

        Raises:
            ValueError: If team IDs are invalid or the same
        """
        # Validate team IDs
        if not (1 <= away_team_id <= 32):
            raise ValueError(f"Invalid away_team_id: {away_team_id}. Must be between 1-32.")

        if not (1 <= home_team_id <= 32):
            raise ValueError(f"Invalid home_team_id: {home_team_id}. Must be between 1-32.")

        if away_team_id == home_team_id:
            raise ValueError("Away and home teams cannot be the same.")

        # Create event
        event = Event(name=name, event_date=event_date)

        # Set basic metadata
        event.set_event_type("game_simulation")
        event.set_dynasty_id(dynasty_id)
        event.set_season(season)
        event.set_week(week)

        # Build simulation configuration
        simulation_config = {
            "away_team_id": away_team_id,
            "home_team_id": home_team_id,
            "overtime_type": overtime_type,
            "database_path": database_path or f"dynasty_{dynasty_id}.db",
            "enable_persistence": enable_persistence
        }

        # Add optional weather conditions
        if weather_conditions:
            simulation_config["weather_conditions"] = weather_conditions

        # Add any additional configuration
        simulation_config.update(additional_config)

        event.set_simulation_config(simulation_config)

        EventFactory.logger.info(f"Created game event: {name} ({away_team_id} @ {home_team_id})")
        return event

    @staticmethod
    def create_draft_event(
        season: int,
        dynasty_id: str,
        draft_date: date,
        draft_type: str = "nfl_draft",
        rounds: int = 7,
        teams_participating: Optional[List[int]] = None,
        **additional_config
    ) -> Event:
        """
        Create a draft simulation event.

        Args:
            season: Season year for the draft
            dynasty_id: Dynasty identifier
            draft_date: Date of the draft
            draft_type: Type of draft ("nfl_draft", "supplemental", etc.)
            rounds: Number of draft rounds
            teams_participating: List of team IDs participating (default: all 32 teams)
            **additional_config: Additional draft configuration

        Returns:
            Event: Properly structured draft event
        """
        event = Event(
            name=f"{season} NFL Draft",
            event_date=draft_date
        )

        # Set basic metadata
        event.set_event_type("draft_simulation")
        event.set_dynasty_id(dynasty_id)
        event.set_season(season)

        # Build simulation configuration
        simulation_config = {
            "draft_type": draft_type,
            "rounds": rounds,
            "teams_participating": teams_participating or list(range(1, 33))
        }

        # Add any additional configuration
        simulation_config.update(additional_config)

        event.set_simulation_config(simulation_config)

        EventFactory.logger.info(f"Created draft event: {season} {draft_type}")
        return event

    @staticmethod
    def create_scouting_event(
        name: str,
        event_date: date,
        scout_team_id: int,
        scouting_type: str,
        dynasty_id: str,
        targets: Optional[List[str]] = None,
        budget: int = 50000,
        **additional_config
    ) -> Event:
        """
        Create a scouting simulation event.

        Args:
            name: Scouting event name
            event_date: Date of the scouting activity
            scout_team_id: Team ID conducting the scouting
            scouting_type: Type of scouting ("college_quarterback", "free_agent", etc.)
            dynasty_id: Dynasty identifier
            targets: List of player names or IDs to scout
            budget: Budget allocated for scouting
            **additional_config: Additional scouting configuration

        Returns:
            Event: Properly structured scouting event
        """
        # Validate scout team ID
        if not (1 <= scout_team_id <= 32):
            raise ValueError(f"Invalid scout_team_id: {scout_team_id}. Must be between 1-32.")

        event = Event(name=name, event_date=event_date)

        # Set basic metadata
        event.set_event_type("scouting_activity")
        event.set_dynasty_id(dynasty_id)

        # Build simulation configuration
        simulation_config = {
            "scout_team_id": scout_team_id,
            "scouting_type": scouting_type,
            "targets": targets or [],
            "budget_allocated": budget
        }

        # Add any additional configuration
        simulation_config.update(additional_config)

        event.set_simulation_config(simulation_config)

        EventFactory.logger.info(f"Created scouting event: {name} for team {scout_team_id}")
        return event

    @staticmethod
    def create_training_camp_event(
        season: int,
        team_id: int,
        dynasty_id: str,
        camp_start_date: date,
        duration_days: int = 14,
        focus_areas: Optional[List[str]] = None,
        **additional_config
    ) -> Event:
        """
        Create a training camp simulation event.

        Args:
            season: Season year
            team_id: Team conducting training camp
            dynasty_id: Dynasty identifier
            camp_start_date: Start date of training camp
            duration_days: How many days the camp lasts
            focus_areas: Areas of focus (e.g., ["passing", "run_defense"])
            **additional_config: Additional camp configuration

        Returns:
            Event: Properly structured training camp event
        """
        # Validate team ID
        if not (1 <= team_id <= 32):
            raise ValueError(f"Invalid team_id: {team_id}. Must be between 1-32.")

        event = Event(
            name=f"{season} Training Camp - Team {team_id}",
            event_date=camp_start_date
        )

        # Set basic metadata
        event.set_event_type("training_camp")
        event.set_dynasty_id(dynasty_id)
        event.set_season(season)

        # Build simulation configuration
        simulation_config = {
            "team_id": team_id,
            "duration_days": duration_days,
            "focus_areas": focus_areas or ["general_conditioning"],
        }

        # Add any additional configuration
        simulation_config.update(additional_config)

        event.set_simulation_config(simulation_config)

        EventFactory.logger.info(f"Created training camp event for team {team_id}, season {season}")
        return event

    @staticmethod
    def create_injury_recovery_event(
        player_name: str,
        team_id: int,
        dynasty_id: str,
        recovery_date: date,
        injury_type: str,
        severity: str,
        **additional_config
    ) -> Event:
        """
        Create an injury recovery simulation event.

        Args:
            player_name: Name of the injured player
            team_id: Team the player belongs to
            dynasty_id: Dynasty identifier
            recovery_date: Expected recovery date
            injury_type: Type of injury
            severity: Severity level ("minor", "moderate", "severe")
            **additional_config: Additional recovery configuration

        Returns:
            Event: Properly structured injury recovery event
        """
        # Validate team ID
        if not (1 <= team_id <= 32):
            raise ValueError(f"Invalid team_id: {team_id}. Must be between 1-32.")

        event = Event(
            name=f"Injury Recovery: {player_name} ({injury_type})",
            event_date=recovery_date
        )

        # Set basic metadata
        event.set_event_type("injury_recovery")
        event.set_dynasty_id(dynasty_id)

        # Build simulation configuration
        simulation_config = {
            "player_name": player_name,
            "team_id": team_id,
            "injury_type": injury_type,
            "severity": severity
        }

        # Add any additional configuration
        simulation_config.update(additional_config)

        event.set_simulation_config(simulation_config)

        EventFactory.logger.info(f"Created injury recovery event: {player_name} - {injury_type}")
        return event

    @staticmethod
    def validate_event_for_creation(event: Event) -> tuple[bool, Optional[str]]:
        """
        Validate an event has proper structure for the calendar system.

        Args:
            event: Event to validate

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check required fields
        if not event.name or not event.name.strip():
            return False, "Event name is required"

        if not event.event_date:
            return False, "Event date is required"

        if not event.get_event_type():
            return False, "Event type is required"

        if not event.get_dynasty_id():
            return False, "Dynasty ID is required"

        # Validate simulation config exists
        sim_config = event.get_simulation_config()
        if not sim_config:
            return False, "Simulation configuration is required"

        # Event type specific validation
        event_type = event.get_event_type()

        if event_type == "game_simulation":
            required_fields = ["away_team_id", "home_team_id", "overtime_type"]
            for field in required_fields:
                if field not in sim_config:
                    return False, f"Game event missing required field: {field}"

        elif event_type == "draft_simulation":
            if "draft_type" not in sim_config:
                return False, "Draft event missing required field: draft_type"

        elif event_type == "scouting_activity":
            required_fields = ["scout_team_id", "scouting_type"]
            for field in required_fields:
                if field not in sim_config:
                    return False, f"Scouting event missing required field: {field}"

        return True, None