"""
Workflow Result Data Classes

Data structures for standardized workflow results across the simulation system.
Provides consistent interfaces for accessing simulation, statistics, and persistence results.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime

from events.base_event import EventResult
from play_engine.simulation.stats import PlayerStats
from persistence.demo.persistence_result import CompositePersistenceResult, PersistenceStatus


@dataclass
class WorkflowResult:
    """
    Complete result from 3-stage simulation workflow.

    Contains results from all workflow stages:
    - Stage 1: Simulation execution
    - Stage 2: Statistics gathering
    - Stage 3: Data persistence (optional)

    Provides convenient access to all workflow outputs and metadata.
    """
    simulation_result: EventResult
    player_stats: List[PlayerStats]
    persistence_result: Optional[CompositePersistenceResult]
    workflow_config: Dict[str, Any]
    execution_timestamp: datetime = field(default_factory=datetime.now)

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of workflow execution.

        Returns:
            Dictionary with workflow execution summary including success status,
            data counts, and configuration details.
        """
        return {
            'execution_timestamp': self.execution_timestamp.isoformat(),
            'simulation_success': self.simulation_result.success,
            'simulation_error': self.simulation_result.error_message,
            'player_count': len(self.player_stats),
            'persistence_executed': self.persistence_result is not None,
            'persistence_success': self._get_persistence_success(),
            'persistence_status': self._get_persistence_status(),
            'workflow_config': self.workflow_config
        }

    def _get_persistence_success(self) -> Optional[bool]:
        """Get persistence success status."""
        if self.persistence_result is None:
            return None
        return self.persistence_result.overall_status == PersistenceStatus.SUCCESS

    def _get_persistence_status(self) -> Optional[str]:
        """Get persistence status as string."""
        if self.persistence_result is None:
            return None
        return self.persistence_result.overall_status.value

    def get_game_score(self) -> Dict[str, int]:
        """
        Get game score from simulation result.

        Returns:
            Dictionary with away_score and home_score
        """
        return {
            'away_score': self.simulation_result.data.get('away_score', 0),
            'home_score': self.simulation_result.data.get('home_score', 0)
        }

    def get_game_winner(self) -> Optional[str]:
        """
        Determine game winner from scores.

        Returns:
            'away', 'home', or 'tie'
        """
        scores = self.get_game_score()
        away_score = scores['away_score']
        home_score = scores['home_score']

        if away_score > home_score:
            return 'away'
        elif home_score > away_score:
            return 'home'
        else:
            return 'tie'

    def get_player_stats_by_team(self, team_id: int) -> List[PlayerStats]:
        """
        Filter player stats by team.

        Args:
            team_id: Team ID to filter by

        Returns:
            List of PlayerStats for the specified team
        """
        return [
            player for player in self.player_stats
            if getattr(player, 'team_id', None) == team_id
        ]

    def get_total_plays(self) -> int:
        """Get total plays from simulation result."""
        return self.simulation_result.data.get('total_plays', 0)

    def get_game_duration(self) -> int:
        """Get game duration in minutes from simulation result."""
        return self.simulation_result.data.get('game_duration_minutes', 0)

    def was_successful(self) -> bool:
        """
        Check if entire workflow was successful.

        Returns:
            True if simulation succeeded and persistence succeeded (if enabled)
        """
        if not self.simulation_result.success:
            return False

        if self.persistence_result is not None:
            return self.persistence_result.overall_status == PersistenceStatus.SUCCESS

        return True

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of any errors that occurred during workflow.

        Returns:
            Dictionary with error information from each stage
        """
        errors = {
            'simulation_error': self.simulation_result.error_message,
            'persistence_errors': []
        }

        if self.persistence_result and hasattr(self.persistence_result, 'operation_results'):
            for op_result in self.persistence_result.operation_results:
                if op_result.status != PersistenceStatus.SUCCESS:
                    errors['persistence_errors'].append({
                        'operation': op_result.operation_type,
                        'status': op_result.status.value,
                        'error': op_result.error_message
                    })

        return errors


@dataclass
class WorkflowConfiguration:
    """
    Configuration settings for simulation workflow.

    Encapsulates all workflow behavior settings including persistence options,
    database configuration, and execution parameters.
    """
    enable_persistence: bool = True
    database_path: Optional[str] = None
    dynasty_id: str = "default"
    persist_player_stats: bool = True
    persist_team_stats: bool = True
    persist_standings: bool = True
    verbose_logging: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'enable_persistence': self.enable_persistence,
            'database_path': self.database_path,
            'dynasty_id': self.dynasty_id,
            'persist_player_stats': self.persist_player_stats,
            'persist_team_stats': self.persist_team_stats,
            'persist_standings': self.persist_standings,
            'verbose_logging': self.verbose_logging
        }

    @classmethod
    def for_testing(cls) -> 'WorkflowConfiguration':
        """Create configuration optimized for testing (no persistence)."""
        return cls(
            enable_persistence=False,
            verbose_logging=False
        )

    @classmethod
    def for_demo(cls, database_path: str = "demo.db") -> 'WorkflowConfiguration':
        """Create configuration optimized for demos."""
        return cls(
            enable_persistence=True,
            database_path=database_path,
            dynasty_id="demo_dynasty",
            verbose_logging=True
        )

    @classmethod
    def for_season(cls, database_path: str, dynasty_id: str) -> 'WorkflowConfiguration':
        """Create configuration optimized for season simulation."""
        return cls(
            enable_persistence=True,
            database_path=database_path,
            dynasty_id=dynasty_id,
            verbose_logging=False  # Reduced logging for batch processing
        )