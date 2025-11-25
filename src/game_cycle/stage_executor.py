"""
Stage Executor - Executes all events/games for a given stage.

This is a simpler replacement for SimulationExecutor that works
with stages instead of individual days.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from .stage_definitions import Stage, StageType, SeasonPhase, GAME_STAGES


@dataclass
class ExecutionResult:
    """Result of executing a stage's events."""
    games_played: List[Dict[str, Any]] = field(default_factory=list)
    events_processed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    stage_name: str = ""  # Display name of the stage that was executed

    def add_game(self, game_result: Dict[str, Any]) -> None:
        """Add a game result."""
        self.games_played.append(game_result)

    def add_event(self, event_name: str) -> None:
        """Record a processed event."""
        self.events_processed.append(event_name)

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)

    @property
    def success(self) -> bool:
        """True if no errors occurred."""
        return len(self.errors) == 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for handler protocol."""
        return {
            "games_played": self.games_played,
            "events_processed": self.events_processed,
            "errors": self.errors,
            "stage_name": self.stage_name,
        }


class StageExecutor:
    """
    Executes all events and games for a given stage.

    This replaces the day-by-day SimulationExecutor with batch
    execution of an entire stage's worth of content.
    """

    def __init__(self, dynasty_id: str, database_path: str):
        """
        Initialize the executor.

        Args:
            dynasty_id: The dynasty to operate on
            database_path: Path to the SQLite database
        """
        self._dynasty_id = dynasty_id
        self._database_path = database_path

    def execute_stage(self, stage: Stage) -> ExecutionResult:
        """
        Execute all events/games for a stage.

        Args:
            stage: The stage to execute

        Returns:
            ExecutionResult with all outcomes
        """
        result = ExecutionResult(stage_name=stage.display_name)

        if stage.stage_type in GAME_STAGES:
            self._execute_games(stage, result)
        else:
            self._execute_offseason_events(stage, result)

        return result

    def _execute_games(self, stage: Stage, result: ExecutionResult) -> None:
        """Execute all games for a game stage (week or playoff round)."""
        # TODO: Implement game execution
        # This will:
        # 1. Query games for this stage from schedule
        # 2. Simulate each game using FullGameSimulator
        # 3. Record results
        pass

    def _execute_offseason_events(self, stage: Stage, result: ExecutionResult) -> None:
        """Execute offseason events for a stage."""
        # TODO: Implement offseason event execution
        # This will dispatch to appropriate handlers based on stage type:
        # - OFFSEASON_FRANCHISE_TAG: Process all franchise tag decisions
        # - OFFSEASON_FREE_AGENCY: Process free agency signings
        # - OFFSEASON_DRAFT: Execute draft (may need interactive hook)
        # - etc.
        pass

    def get_stage_games(self, stage: Stage) -> List[Dict[str, Any]]:
        """
        Get all games scheduled for a stage.

        Args:
            stage: The stage to query

        Returns:
            List of game info dictionaries
        """
        # TODO: Implement game querying
        # Will query schedule table for games matching:
        # - dynasty_id
        # - season_year
        # - week number (for regular season) or playoff round
        return []

    def get_stage_preview(self, stage: Stage) -> Dict[str, Any]:
        """
        Get a preview of what will happen in a stage.

        Useful for UI to show upcoming games/events before execution.

        Args:
            stage: The stage to preview

        Returns:
            Preview info including game matchups, events, etc.
        """
        preview = {
            "stage": stage.display_name,
            "season_year": stage.season_year,
            "phase": stage.phase.name,
            "games": [],
            "events": [],
        }

        if stage.stage_type in GAME_STAGES:
            preview["games"] = self.get_stage_games(stage)
        else:
            preview["events"] = self._get_offseason_events(stage)

        return preview

    def _get_offseason_events(self, stage: Stage) -> List[str]:
        """Get list of events for an offseason stage."""
        # Map stage types to their events
        event_map = {
            StageType.OFFSEASON_RESIGNING: [
                "Review expiring contracts",
                "Re-sign players you want to keep",
            ],
            StageType.OFFSEASON_FREE_AGENCY: [
                "Free Agency Opens",
                "Sign available free agents",
            ],
            StageType.OFFSEASON_DRAFT: [
                "NFL Draft (Rounds 1-7)",
            ],
            StageType.OFFSEASON_ROSTER_CUTS: [
                "Cut roster from 90 to 53",
            ],
            StageType.OFFSEASON_TRAINING_CAMP: [
                "Finalize depth charts",
                "Final roster preparations",
            ],
            StageType.OFFSEASON_PRESEASON: [
                "Exhibition games (optional)",
            ],
        }

        return event_map.get(stage.stage_type, [])