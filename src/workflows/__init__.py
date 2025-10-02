"""
Workflows Package

Reusable workflow orchestrators for NFL simulation system.
Provides standardized patterns for simulation execution, statistics gathering, and data persistence.

Key Components:
- SimulationWorkflow: 3-stage workflow orchestrator (Simulation → Statistics → Persistence)
- WorkflowResult: Standardized result container with convenience methods
- WorkflowConfiguration: Configuration management for workflow behavior

Usage:
    from workflows import SimulationWorkflow, WorkflowResult, WorkflowConfiguration

    # Create workflow for demo
    workflow = SimulationWorkflow.for_demo("demo.db", "demo_dynasty")

    # Execute complete workflow
    result = workflow.execute(game_event)

    # Access results
    scores = result.get_game_score()
    winner = result.get_game_winner()
    was_successful = result.was_successful()
"""

from .simulation_workflow import SimulationWorkflow
from .workflow_result import WorkflowResult, WorkflowConfiguration

__all__ = [
    'SimulationWorkflow',
    'WorkflowResult',
    'WorkflowConfiguration'
]