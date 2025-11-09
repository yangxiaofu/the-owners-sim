"""
Schedule Release Event

Special milestone event that generates NFL regular season and preseason schedules
when the NFL schedule is released (mid-May).

This event executes game generation logic, creating all 320 games for the upcoming season:
- 48 preseason games (3 weeks, Aug 6-27)
- 272 regular season games (17 weeks, Sept 5 - Jan 5)
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .milestone_event import MilestoneEvent
from .base_event import EventResult
from events import EventDatabaseAPI
from scheduling import RandomScheduleGenerator

# Use try/except to handle both production and test imports
try:
    from src.calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


class ScheduleReleaseEvent(MilestoneEvent):
    """
    NFL Schedule Release milestone that generates all games for upcoming season.

    This event marks the mid-May schedule release and generates:
    - 48 preseason games (August 6-27)
    - 272 regular season games (September 5 - January 5)

    All games are inserted into the event database for the upcoming season.
    """

    def __init__(
        self,
        season_year: int,
        event_date: Date,
        dynasty_id: str,
        event_db: EventDatabaseAPI,
        preseason_start_date: Date,
        event_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize schedule release event.

        Args:
            season_year: Upcoming season year (e.g., 2026 for 2026 season)
            event_date: Date when schedule is released (mid-May)
            dynasty_id: Dynasty context for isolation
            event_db: Event database API for inserting games
            preseason_start_date: When preseason begins (first Thursday in August)
            event_id: Unique identifier (generated if not provided)
            metadata: Optional additional context
        """
        super().__init__(
            milestone_type="SCHEDULE_RELEASE",
            description=f"NFL Schedule Released for {season_year} Season",
            season_year=season_year,
            event_date=event_date,
            dynasty_id=dynasty_id,
            event_id=event_id,
            metadata=metadata
        )

        self.event_db = event_db
        self.preseason_start_date = preseason_start_date
        self._games_generated = False

    def get_event_type(self) -> str:
        """
        Return event type identifier.

        Returns SCHEDULE_RELEASE as a top-level event type (not nested under MILESTONE).
        This makes reconstruction simpler and consistent with other special events
        like DEADLINE and WINDOW.

        Returns:
            "SCHEDULE_RELEASE" instead of "MILESTONE"
        """
        return "SCHEDULE_RELEASE"

    def simulate(self) -> EventResult:
        """
        Execute schedule release - generate all 320 games for upcoming season.

        Generates:
        - 48 preseason games (3 weeks starting from preseason_start_date)
        - 272 regular season games (17 weeks, Thursday after Labor Day)

        Returns:
            EventResult with success=True and game counts
        """
        # DEBUG: Confirm simulate() was called
        print(f"[SCHEDULE_RELEASE_TRIGGERED] 🎬 simulate() method called!")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Season Year: {self.season_year}")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Dynasty: {self.dynasty_id}")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Already Generated: {self._games_generated}")

        # Prevent duplicate generation
        if self._games_generated:
            return EventResult(
                event_id=self.event_id,
                event_type=self.get_event_type(),
                success=True,
                timestamp=datetime.now(),
                data={
                    "milestone_type": "SCHEDULE_RELEASE",
                    "message": "Schedule already generated - skipping duplicate",
                    "season_year": self.season_year
                }
            )

        # DEBUG: Confirm we passed duplicate check
        print(f"[SCHEDULE_RELEASE_TRIGGERED] ✅ Duplicate check passed - proceeding to generate games")

        upcoming_season = self.season_year + 1
        print(f"\n[SCHEDULE_RELEASE] Generating {upcoming_season} NFL schedule...")
        print(f"  Dynasty: {self.dynasty_id}")
        print(f"  Event Season Year: {self.season_year} (offseason)")
        print(f"  Games Season Year: {upcoming_season} (upcoming season)")
        print(f"  Preseason starts: {self.preseason_start_date}")

        # Create schedule generator
        generator = RandomScheduleGenerator(
            event_db=self.event_db,
            dynasty_id=self.dynasty_id
        )

        # Convert Date to datetime for generator
        preseason_start_datetime = datetime(
            self.preseason_start_date.year,
            self.preseason_start_date.month,
            self.preseason_start_date.day,
            19, 0  # 7:00 PM default start time
        )

        # Generate preseason schedule (48 games)
        # DEBUG: Confirm we're about to call generator
        print(f"[SCHEDULE_RELEASE_TRIGGERED] 🏈 Calling generator.generate_preseason()")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Season: {self.season_year + 1} (upcoming season)")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Start Date: {preseason_start_datetime}")
        print(f"[SCHEDULE_RELEASE] Generating preseason schedule (48 games)...")
        preseason_games = generator.generate_preseason(
            season_year=self.season_year + 1,  # Generate for NEXT season (e.g., 2026 games during May 2026)
            start_date=preseason_start_datetime
        )
        print(f"[SCHEDULE_RELEASE] ✅ Preseason: {len(preseason_games)} games")

        # Generate regular season schedule (272 games)
        print(f"[SCHEDULE_RELEASE] Generating regular season schedule (272 games)...")
        regular_season_games = generator.generate_season(
            season_year=self.season_year + 1,  # Generate for NEXT season (calculates Sept 2026, not Sept 2025)
            start_date=None  # Uses dynamic Labor Day calculation for upcoming season year
        )
        print(f"[SCHEDULE_RELEASE] ✅ Regular season: {len(regular_season_games)} games")

        total_games = len(preseason_games) + len(regular_season_games)
        print(f"[SCHEDULE_RELEASE] ✅ Total: {total_games} games generated for {upcoming_season} season")

        # DEBUG: Final success confirmation
        print(f"[SCHEDULE_RELEASE_TRIGGERED] 🎉 GAME GENERATION COMPLETE!")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Preseason: {len(preseason_games)} games")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Regular Season: {len(regular_season_games)} games")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Total: {total_games} games for {upcoming_season} season")

        self._games_generated = True

        return EventResult(
            event_id=self.event_id,
            event_type=self.get_event_type(),
            success=True,
            timestamp=datetime.now(),
            data={
                "milestone_type": "SCHEDULE_RELEASE",
                "description": self.description,
                "season_year": self.season_year,  # Event belongs to this season's offseason
                "games_season_year": upcoming_season,  # But generates games for next season
                "dynasty_id": self.dynasty_id,
                "preseason_games_generated": len(preseason_games),
                "regular_season_games_generated": len(regular_season_games),
                "total_games_generated": total_games,
                "message": f"NFL {upcoming_season} schedule released: {total_games} games"
            }
        )

    def _get_parameters(self) -> Dict[str, Any]:
        """
        Return parameters needed to recreate this event.

        Returns:
            Dictionary with event parameters
        """
        return {
            "milestone_type": self.milestone_type,
            "season_year": self.season_year,
            "event_date": str(self.event_date),
            "preseason_start_date": str(self.preseason_start_date),
            "description": self.description
        }

    def _get_results(self) -> Optional[Dict[str, Any]]:
        """
        Return results after event execution.

        Returns:
            None before execution, game counts after
        """
        if not self._games_generated:
            return None

        return {
            "games_generated": True,
            "message": "Schedule generation complete"
        }

    def _get_metadata(self) -> Dict[str, Any]:
        """
        Return event metadata.

        Returns:
            Dictionary with additional context
        """
        return self.milestone_metadata or {}

    @classmethod
    def from_database(cls, event_data: Dict[str, Any]) -> 'ScheduleReleaseEvent':
        """
        Reconstruct ScheduleReleaseEvent from database data.

        Args:
            event_data: Dictionary from EventDatabaseAPI with:
                - dynasty_id: At top level (from events table column)
                - data: Nested dict with parameters/results/metadata

        Returns:
            Reconstructed ScheduleReleaseEvent instance
        """
        # DEBUG: Confirm from_database() was called
        print(f"[SCHEDULE_RELEASE_TRIGGERED] 📦 ScheduleReleaseEvent.from_database() called")

        from events import EventDatabaseAPI

        data = event_data['data']

        # Handle three-part structure (parameters/results/metadata)
        if 'parameters' in data:
            params = data['parameters']
        else:
            params = data

        # Dynasty ID from top-level event_data (events.dynasty_id column)
        dynasty_id = event_data.get('dynasty_id', params.get('dynasty_id', 'default'))

        # Parse event_date from string
        event_date_str = params.get('event_date', '')
        event_date_parts = event_date_str.split('-')
        event_date = Date(int(event_date_parts[0]), int(event_date_parts[1]), int(event_date_parts[2]))

        # Parse preseason_start_date from string
        preseason_start_str = params.get('preseason_start_date', '')
        preseason_parts = preseason_start_str.split('-')
        preseason_start_date = Date(int(preseason_parts[0]), int(preseason_parts[1]), int(preseason_parts[2]))

        # Get event database path from event_data if available
        # Otherwise use default path (assumes event was created with default db)
        db_path = event_data.get('db_path', 'data/database/nfl_simulation.db')
        event_db = EventDatabaseAPI(db_path)

        # DEBUG: Confirm reconstruction parameters
        print(f"[SCHEDULE_RELEASE_TRIGGERED] 📦 from_database() reconstructed:")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Season: {params.get('season_year')}")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Event Date: {event_date}")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Preseason Start: {preseason_start_date}")
        print(f"[SCHEDULE_RELEASE_TRIGGERED]   Dynasty: {dynasty_id}")

        return cls(
            season_year=params.get('season_year', 2025),
            event_date=event_date,
            dynasty_id=dynasty_id,
            event_db=event_db,
            preseason_start_date=preseason_start_date,
            event_id=event_data.get('event_id'),
            metadata=params.get('metadata')
        )
