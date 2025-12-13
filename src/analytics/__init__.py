"""
Advanced Analytics & PFF Grades Package

This package provides comprehensive player grading inspired by Pro Football Focus (PFF),
calculating per-play grades (0-100 scale) and advanced metrics like EPA and Success Rate.

Key Components:
- models: Dataclasses for PlayGrade, GameGrade, SeasonGrade, AdvancedMetrics
- grading_constants: Position-specific weights, thresholds, EPA lookup tables
- grading_algorithm: Core grading logic with context-aware modifiers
- advanced_metrics: EPA and Success Rate calculators
- position_graders: Position-specific grading modules
- services: AnalyticsService orchestration layer
"""

from .models import (
    PlayContext,
    PlayGrade,
    GameGrade,
    SeasonGrade,
    AdvancedMetrics,
)

__all__ = [
    "PlayContext",
    "PlayGrade",
    "GameGrade",
    "SeasonGrade",
    "AdvancedMetrics",
]
