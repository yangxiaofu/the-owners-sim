"""
Scheduling Module

Handles all NFL schedule generation including:
- Regular season schedules (17 weeks, 272 games)
- Preseason schedules (3 weeks, 48 games)
- Playoff bracket scheduling
- Dynamic date calculations (Labor Day, season start dates)
"""

from .random_schedule_generator import RandomScheduleGenerator, create_schedule_generator

__all__ = ['RandomScheduleGenerator', 'create_schedule_generator']
