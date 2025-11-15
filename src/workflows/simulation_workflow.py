"""
Simulation Workflow

Reusable 3-stage simulation workflow orchestrator for NFL game simulation.
Encapsulates the proven pattern: Simulation → Statistics → Persistence.

Supports toggleable persistence, flexible configuration, and standardized results.
Designed for use across demos, testing, and production season simulation.
"""

import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

# ============ FAST MODE DEBUG LOGGING ============
# Create dedicated debug logger for tracing fast mode standings issues
import os
_debug_log_path = os.path.join(os.getcwd(), 'fast_mode_debug.log')
_debug_logger = logging.getLogger('fast_mode_debug')
_debug_logger.setLevel(logging.DEBUG)
_debug_handler = logging.FileHandler(_debug_log_path, mode='a')
_debug_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
_debug_logger.addHandler(_debug_handler)
_debug_logger.info("=" * 80)
_debug_logger.info("NEW SIMULATION SESSION STARTED")
_debug_logger.info("=" * 80)
# =================================================

from events.base_event import EventResult
from events.game_event import GameEvent
from play_engine.simulation.stats import PlayerStats
from game_management.player_stats_query_service import PlayerStatsQueryService

# Use try/except to handle both production and test imports
try:
    from persistence.demo.base_demo_persister import DemoPersister
    from persistence.demo.database_demo_persister import DatabaseDemoPersister
    from persistence.demo.game_persistence_orchestrator import GamePersistenceOrchestrator
    from persistence.demo.persistence_result import CompositePersistenceResult, PersistenceStatus
except ModuleNotFoundError:
    from src.persistence.demo.base_demo_persister import DemoPersister
    from src.persistence.demo.database_demo_persister import DatabaseDemoPersister
    from src.persistence.demo.game_persistence_orchestrator import GamePersistenceOrchestrator
    from src.persistence.demo.persistence_result import CompositePersistenceResult, PersistenceStatus

from .workflow_result import WorkflowResult, WorkflowConfiguration


class SimulationWorkflow:
    """
    Reusable 3-stage simulation workflow orchestrator.

    Encapsulates the standard simulation pattern:
    1. Stage 1: Simulation - Execute game simulation using GameEvent
    2. Stage 2: Statistics - Gather player and team statistics
    3. Stage 3: Persistence - Save data to database (toggleable)

    Key Features:
    - Toggleable persistence for testing and development
    - Configurable database paths and dynasty isolation
    - Standardized result objects for consistent API
    - Integration with existing persistence infrastructure
    - Comprehensive logging and progress indicators

    Usage Examples:
        # With persistence (production/demo)
        workflow = SimulationWorkflow(
            enable_persistence=True,
            database_path="season_2024.db",
            dynasty_id="user_dynasty"
        )
        result = workflow.execute(game_event)

        # Without persistence (testing)
        workflow = SimulationWorkflow(enable_persistence=False)
        result = workflow.execute(game_event)
    """

    def __init__(self,
                 enable_persistence: bool = True,
                 database_path: Optional[str] = None,
                 dynasty_id: str = "default",
                 persister_strategy: Optional[DemoPersister] = None,
                 verbose_logging: bool = True,
                 fast_mode: bool = False):
        """
        Initialize simulation workflow.

        Args:
            enable_persistence: Whether to persist data after simulation
            database_path: Database file path (required if enable_persistence=True)
            dynasty_id: Dynasty context for data isolation
            persister_strategy: Custom persistence strategy (optional)
            verbose_logging: Whether to print progress messages
            fast_mode: Skip actual simulations, generate fake results for ultra-fast testing
        """
        self.config = WorkflowConfiguration(
            enable_persistence=enable_persistence,
            database_path=database_path,
            dynasty_id=dynasty_id,
            verbose_logging=verbose_logging,
            fast_mode=fast_mode
        )

        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize persistence components if enabled
        if self.config.enable_persistence:
            if persister_strategy:
                self.persister = persister_strategy
            else:
                if not database_path:
                    raise ValueError("database_path is required when enable_persistence=True")
                self.persister = DatabaseDemoPersister(database_path)
            self.orchestrator = GamePersistenceOrchestrator(self.persister)
        else:
            self.persister = None
            self.orchestrator = None

    @classmethod
    def for_testing(cls) -> 'SimulationWorkflow':
        """Create workflow optimized for testing (no persistence, minimal logging)."""
        return cls(
            enable_persistence=False,
            verbose_logging=False
        )

    @classmethod
    def for_demo(cls, database_path: str = "demo.db", dynasty_id: str = "demo_dynasty") -> 'SimulationWorkflow':
        """Create workflow optimized for demos."""
        return cls(
            enable_persistence=True,
            database_path=database_path,
            dynasty_id=dynasty_id,
            verbose_logging=True
        )

    @classmethod
    def for_season(cls, database_path: str, dynasty_id: str) -> 'SimulationWorkflow':
        """Create workflow optimized for season simulation (minimal logging for performance)."""
        return cls(
            enable_persistence=True,
            database_path=database_path,
            dynasty_id=dynasty_id,
            verbose_logging=True  # TEMPORARILY ENABLED FOR DEBUGGING
        )

    def execute(self, game_event: GameEvent) -> WorkflowResult:
        """
        Execute complete 3-stage workflow.

        Args:
            game_event: GameEvent to simulate

        Returns:
            WorkflowResult containing all stage results and metadata

        Raises:
            ValueError: If game_event is invalid
            RuntimeError: If simulation fails critically
        """
        if not isinstance(game_event, GameEvent):
            raise ValueError("game_event must be a GameEvent instance")

        if self.config.verbose_logging:
            self._print_workflow_header()

        workflow_start_time = time.time()

        try:
            # Stage 1: Simulation
            simulation_result = self._run_simulation(game_event)

            # Stage 2: Statistics
            player_stats = self._gather_statistics(simulation_result, game_event)

            # Stage 3: Persistence (conditional)
            persistence_result = self._persist_if_enabled(simulation_result, player_stats, game_event)

            # Create final result
            result = WorkflowResult(
                simulation_result=simulation_result,
                player_stats=player_stats,
                persistence_result=persistence_result,
                workflow_config=self.config.to_dict()
            )

            workflow_duration = time.time() - workflow_start_time

            if self.config.verbose_logging:
                self._print_workflow_summary(result, workflow_duration)

            return result

        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            if self.config.verbose_logging:
                print(f"❌ Workflow failed: {e}")
            raise RuntimeError(f"Simulation workflow failed: {e}") from e

    def _print_workflow_header(self):
        """Print workflow execution header."""
        print(f"\n{'='*80}")
        print(f"{'🔄 SIMULATION WORKFLOW EXECUTION'.center(80)}")
        print(f"{'='*80}")
        print(f"Persistence: {'ENABLED' if self.config.enable_persistence else 'DISABLED'}")
        if self.config.enable_persistence:
            print(f"Database: {self.config.database_path}")
            print(f"Dynasty: {self.config.dynasty_id}")

    def _run_simulation(self, game_event: GameEvent) -> EventResult:
        """
        Stage 1: Execute game simulation.

        Args:
            game_event: GameEvent to simulate

        Returns:
            EventResult from simulation

        Raises:
            RuntimeError: If simulation fails
        """
        if self.config.verbose_logging:
            if self.config.fast_mode:
                print(f"\n🚀 Stage 1: FAST MODE - Generating Fake Result...")
            else:
                print(f"\n🎮 Stage 1: Running Simulation...")
            print(f"   Teams: {game_event.away_team_id} @ {game_event.home_team_id}")

        start_time = time.time()

        try:
            # Fast mode: Generate instant fake result without running simulation
            if self.config.fast_mode:
                simulation_result = self._generate_fake_result(game_event)

                # CRITICAL: Store fake result in GameEvent for database persistence
                # This ensures _get_results() returns data instead of None, which is
                # required for playoff completion detection to work correctly.
                game_event._cached_result = simulation_result

                duration = time.time() - start_time

                if self.config.verbose_logging:
                    away_score = simulation_result.data.get('away_score', 0)
                    home_score = simulation_result.data.get('home_score', 0)
                    print(f"   🚀 FAKE SIM complete ({duration:.4f}s)")
                    print(f"   Final Score: {away_score}-{home_score}")

                return simulation_result

            # Normal mode: Run actual simulation
            simulation_result = game_event.simulate()

            if not simulation_result.success:
                raise RuntimeError(f"Simulation failed: {simulation_result.error_message}")

            duration = time.time() - start_time

            if self.config.verbose_logging:
                away_score = simulation_result.data.get('away_score', 0)
                home_score = simulation_result.data.get('home_score', 0)
                total_plays = simulation_result.data.get('total_plays', 0)

                print(f"   ✅ Simulation complete ({duration:.2f}s)")
                print(f"   Final Score: {away_score}-{home_score}")
                print(f"   Total Plays: {total_plays}")

            return simulation_result

        except Exception as e:
            self.logger.error(f"Simulation stage failed: {e}")
            raise RuntimeError(f"Game simulation failed: {e}") from e

    def _generate_fake_result(self, game_event: GameEvent) -> EventResult:
        """
        Generate instant fake game result for fast_mode testing.

        Creates realistic-looking NFL scores without running actual simulation.
        ~5000x faster than real simulation (0.001s vs 2-5s).

        Args:
            game_event: GameEvent to generate result for

        Returns:
            EventResult with randomized scores and minimal data
        """
        import random

        # Generate realistic NFL scores (10-35 point range)
        away_score = random.randint(10, 35)
        home_score = random.randint(10, 35)

        # Fake game data matching real simulation structure
        fake_data = {
            'away_score': away_score,
            'home_score': home_score,
            'total_plays': random.randint(120, 150),  # Realistic play count
            'game_duration_minutes': 180,  # Standard 3-hour game
            'overtime_periods': 0,
            'home_team_id': game_event.home_team_id,
            'away_team_id': game_event.away_team_id
        }

        # DEBUG: Log fake result generation
        _debug_logger.info(f"FAKE RESULT GENERATED: Away Team {game_event.away_team_id} ({away_score}) @ Home Team {game_event.home_team_id} ({home_score})")
        _debug_logger.debug(f"  Full fake_data: {fake_data}")

        # Create successful EventResult (matching real simulation signature)
        return EventResult(
            event_id=game_event.event_id,
            event_type="GAME",
            success=True,
            timestamp=game_event.game_date,
            data=fake_data
        )

    def _gather_statistics(self, simulation_result: EventResult, game_event: GameEvent) -> List[PlayerStats]:
        """
        Stage 2: Gather comprehensive player statistics.

        Args:
            simulation_result: Result from simulation stage
            game_event: Original GameEvent

        Returns:
            List of PlayerStats objects

        Raises:
            RuntimeError: If statistics gathering fails
        """
        # Fast mode: Skip statistics gathering (no simulator available)
        # Return empty list - this is OK! Standings update (Stage 3) only needs
        # game result data (scores) from Stage 1, not player stats.
        if self.config.fast_mode:
            if self.config.verbose_logging:
                print(f"\n⏭️  Stage 2: Player Statistics SKIPPED (fast_mode)")
                print(f"   Note: Game results will still persist for standings")
            return []

        if self.config.verbose_logging:
            print(f"\n📊 Stage 2: Gathering Statistics...")

        try:
            # Extract simulator from game event for live stats
            if not hasattr(game_event, '_simulator') or game_event._simulator is None:
                raise RuntimeError("GameEvent simulator not available for statistics gathering")

            simulator = game_event._simulator

            # Use existing PlayerStatsQueryService for statistics
            all_player_stats = PlayerStatsQueryService.get_live_stats(simulator)

            # WARNING: Check for empty player stats
            if len(all_player_stats) == 0:
                self.logger.warning("⚠️  No player stats found! Game may not have been simulated properly")
                print("⚠️  WARNING: No player stats found! Player stats will NOT be persisted.")

            if self.config.verbose_logging:
                print(f"   ✅ Statistics gathered for {len(all_player_stats)} players")

                if len(all_player_stats) > 0:
                    # Get team breakdowns for additional info
                    home_players = PlayerStatsQueryService.get_stats_by_team(
                        all_player_stats, game_event.home_team_id
                    )
                    away_players = PlayerStatsQueryService.get_stats_by_team(
                        all_player_stats, game_event.away_team_id
                    )

                    print(f"   Home team players: {len(home_players)}")
                    print(f"   Away team players: {len(away_players)}")

                    # Show sample player for debugging
                    sample_player = all_player_stats[0]
                    print(f"   Sample player: {sample_player.player_name} (Team {sample_player.team_id}, {sample_player.position})")

            return all_player_stats

        except Exception as e:
            self.logger.error(f"Statistics gathering failed: {e}")
            raise RuntimeError(f"Statistics gathering failed: {e}") from e

    def _persist_if_enabled(self, simulation_result: EventResult,
                          player_stats: List[PlayerStats],
                          game_event: GameEvent) -> Optional[CompositePersistenceResult]:
        """
        Stage 3: Conditional data persistence.

        Args:
            simulation_result: Result from simulation stage
            player_stats: Statistics from statistics stage
            game_event: Original GameEvent

        Returns:
            CompositePersistenceResult if persistence enabled, None otherwise

        Raises:
            RuntimeError: If persistence fails when enabled
        """
        # DEBUG: Log Stage 3 entry
        _debug_logger.info(f"STAGE 3: Persistence check - enable_persistence={self.config.enable_persistence}")

        if not self.config.enable_persistence:
            if self.config.verbose_logging:
                print(f"\n⏭️  Stage 3: Persistence SKIPPED (disabled)")
            _debug_logger.warning("STAGE 3: Persistence SKIPPED (enable_persistence=False)")
            return None

        _debug_logger.info(f"STAGE 3: Persistence ENABLED - Starting data persistence")
        _debug_logger.info(f"  Database: {self.config.database_path}")
        _debug_logger.info(f"  Dynasty: {self.config.dynasty_id}")

        if self.config.verbose_logging:
            print(f"\n💾 Stage 3: Persisting Data...")
            print(f"   Database: {self.config.database_path}")
            print(f"   Dynasty: {self.config.dynasty_id}")

        try:
            # Use the game_id from the GameEvent to maintain consistency
            # This ensures scheduled events and completed games have matching IDs
            # for proper calendar deduplication
            game_id = game_event.get_game_id()

            # Prepare game result data structure
            game_result_data = {
                'home_team_id': game_event.home_team_id,
                'away_team_id': game_event.away_team_id,
                'home_score': simulation_result.data['home_score'],
                'away_score': simulation_result.data['away_score'],
                'total_plays': simulation_result.data['total_plays'],
                'game_duration_minutes': simulation_result.data.get('game_duration_minutes', 180),
                'overtime_periods': simulation_result.data.get('overtime_periods', 0),
                'season': getattr(game_event, 'season', 2024),
                'week': getattr(game_event, 'week', 1),
                'season_type': getattr(game_event, 'season_type', 'regular_season'),
                'game_type': getattr(game_event, 'game_type', 'regular'),
                'game_date': game_event.game_date  # Include game date for calendar display
            }

            # DEBUG: Log game result data being persisted
            _debug_logger.info(f"STAGE 3: Prepared game_result_data for persistence:")
            _debug_logger.info(f"  Game ID: {game_id}")
            _debug_logger.info(f"  Teams: Away {game_result_data['away_team_id']} @ Home {game_result_data['home_team_id']}")
            _debug_logger.info(f"  Scores: {game_result_data['away_score']}-{game_result_data['home_score']}")
            _debug_logger.info(f"  Season: {game_result_data['season']}, Week: {game_result_data['week']}, Type: {game_result_data['season_type']}")
            _debug_logger.info(f"  Dynasty: {self.config.dynasty_id}")
            _debug_logger.info(f"  Player stats count: {len(player_stats)}")

            if self.config.verbose_logging:
                print(f"   Game ID: {game_id}")
                print(f"   Persisting: Game result + {len(player_stats)} player stats")

            # Execute persistence using orchestrator
            _debug_logger.info(f"STAGE 3: Calling orchestrator.persist_complete_game()...")
            persistence_result = self.orchestrator.persist_complete_game(
                game_id=game_id,
                game_result=game_result_data,
                player_stats=player_stats,
                dynasty_id=self.config.dynasty_id,
                season=game_result_data['season'],
                week=game_result_data['week'],
                simulation_date=game_event.game_date
            )
            _debug_logger.info(f"STAGE 3: persist_complete_game() returned - Status: {persistence_result.overall_status}")

            if self.config.verbose_logging:
                print(f"   ✅ Persistence complete")
                print(f"   Status: {persistence_result.overall_status.value}")

                # Show any warnings or errors
                if persistence_result.overall_status != PersistenceStatus.SUCCESS:
                    print(f"   ⚠️  Some operations had issues - check result details")

            # DEBUG: Log return
            _debug_logger.info(f"STAGE 3: Returning persistence_result - Status: {persistence_result.overall_status}")
            return persistence_result

        except Exception as e:
            _debug_logger.error(f"STAGE 3: EXCEPTION during persistence: {e}", exc_info=True)
            self.logger.error(f"Persistence stage failed: {e}")
            raise RuntimeError(f"Data persistence failed: {e}") from e

    def _print_workflow_summary(self, result: WorkflowResult, duration: float):
        """Print workflow execution summary."""
        print(f"\n{'='*80}")
        print(f"{'✅ WORKFLOW COMPLETE'.center(80)}")
        print(f"{'='*80}")
        print(f"Total Duration: {duration:.2f}s")
        print(f"Simulation Success: {result.simulation_result.success}")
        print(f"Player Stats Count: {len(result.player_stats)}")

        if result.persistence_result:
            print(f"Persistence Status: {result.persistence_result.overall_status.value}")
        else:
            print(f"Persistence: Skipped")

        scores = result.get_game_score()
        winner = result.get_game_winner()
        print(f"Final Score: {scores['away_score']}-{scores['home_score']} (Winner: {winner})")
        print(f"{'='*80}")

    def get_configuration(self) -> WorkflowConfiguration:
        """Get current workflow configuration."""
        return self.config

    def is_persistence_enabled(self) -> bool:
        """Check if persistence is enabled."""
        return self.config.enable_persistence

    def get_database_path(self) -> Optional[str]:
        """Get configured database path."""
        return self.config.database_path

    def get_dynasty_id(self) -> str:
        """Get configured dynasty ID."""
        return self.config.dynasty_id