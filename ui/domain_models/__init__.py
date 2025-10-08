"""
Domain Models for The Owner's Sim UI

This package contains domain models that encapsulate business logic and data access.
Domain models sit between controllers and database APIs, following proper MVC architecture.

Architecture Pattern:
    View Layer (Qt widgets)
        ↓ calls
    Controller Layer (thin orchestration, ui/controllers/)
        ↓ uses
    Domain Model Layer (business logic + data access, THIS PACKAGE)
        ↓ queries
    Database APIs (src/database/, src/events/)

Responsibilities of Domain Models:
    ✅ OWN: Database API instances (EventDatabaseAPI, DatabaseAPI, etc.)
    ✅ DO: All data access, business logic, data transformation
    ✅ RETURN: Clean DTOs/dicts to controllers
    ❌ NO: Qt dependencies, UI concerns, user interaction handling

Responsibilities of Controllers:
    ✅ OWN: Domain model instance(s)
    ✅ DO: Thin orchestration, model → view data transformation
    ✅ RETURN: View-ready data structures
    ❌ NO: Database access, complex logic (keep methods ≤10-20 lines)

Example Usage:
    # In controller
    from ui.domain_models import CalendarDataModel

    class CalendarController:
        def __init__(self, db_path, dynasty_id, season):
            self.data_model = CalendarDataModel(db_path, dynasty_id, season)

        def get_events_for_month(self, year, month, event_types=None):
            # Simple pass-through to domain model
            return self.data_model.get_events_for_month(year, month, event_types)

Available Domain Models:
    - CalendarDataModel: Calendar event data access and filtering
    - SeasonDataModel: Season, team, and standings data access
    - SimulationDataModel: Simulation state management and persistence
    - TeamDataModel: Team roster, salary cap, depth chart, and coaching staff data access
"""

from ui.domain_models.calendar_data_model import CalendarDataModel
from ui.domain_models.season_data_model import SeasonDataModel
from ui.domain_models.simulation_data_model import SimulationDataModel
from ui.domain_models.team_data_model import TeamDataModel

__all__ = [
    'CalendarDataModel',
    'SeasonDataModel',
    'SimulationDataModel',
    'TeamDataModel',
]
