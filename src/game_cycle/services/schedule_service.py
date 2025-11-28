"""
Schedule Service - Generates NFL regular season schedules.

Isolated, testable service for schedule generation.
Currently uses random matchups; will be enhanced for realistic NFL scheduling.

Architecture:
    ScheduleService (business logic) → UnifiedDatabaseAPI (events table)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


class ScheduleService:
    """
    Generates 18-week NFL regular season schedules.

    Business logic for generating schedules. Uses UnifiedDatabaseAPI to persist
    game events to the events table (where RegularSeasonHandler expects them).

    Usage:
        service = ScheduleService(db_path, dynasty_id, season=2026)
        games_created = service.generate_schedule()
        print(f"Created {games_created} games")  # 288 games
    """

    TOTAL_WEEKS = 18
    TOTAL_TEAMS = 32
    GAMES_PER_WEEK = 16  # All 32 teams play each week

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the schedule service.

        Args:
            db_path: Path to the game_cycle database
            dynasty_id: Dynasty identifier for event isolation
            season: Season year for the schedule (e.g., 2026)
        """
        self._db_path = db_path
        self._dynasty_id = dynasty_id
        self._season = season
        self._teams_data: Dict[str, Any] = {}
        self._load_teams_data()

    def _load_teams_data(self) -> None:
        """Load team data from JSON file."""
        teams_path = Path(__file__).parent.parent.parent / "data" / "teams.json"
        with open(teams_path, 'r') as f:
            self._teams_data = json.load(f).get("teams", {})

    def generate_schedule(self, clear_existing: bool = True) -> int:
        """
        Generate an 18-week NFL schedule as game events.

        Creates game events in the events table for RegularSeasonHandler to process.

        Args:
            clear_existing: If True, clears existing regular season game events first

        Returns:
            Number of games created (288 = 18 weeks × 16 games)
        """
        from database.unified_api import UnifiedDatabaseAPI

        api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)

        if clear_existing:
            # Use API method to clear existing games
            deleted = api.events_delete_regular_season_by_dynasty(self._season)
            if deleted > 0:
                print(f"[ScheduleService] Cleared {deleted} existing game events")

        # Generate game events
        game_events = self._generate_all_game_events()

        # Insert into events table using API
        api.events_insert_batch(game_events)

        print(f"[ScheduleService] Created {len(game_events)} game events for season {self._season}")
        return len(game_events)

    def _generate_all_game_events(self) -> List[Dict[str, Any]]:
        """Generate game events for all 18 weeks."""
        events = []
        team_info = self._build_team_info()

        # Calculate season start date (first Thursday after Labor Day)
        season_start = self._calculate_season_start()

        for week in range(1, self.TOTAL_WEEKS + 1):
            week_events = self._generate_week_events(week, team_info, season_start)
            events.extend(week_events)

        return events

    def _generate_week_events(
        self,
        week: int,
        team_info: Dict[int, Dict[str, str]],
        season_start: datetime
    ) -> List[Dict[str, Any]]:
        """
        Generate game events for a single week (random matchups).

        Args:
            week: Week number (1-18)
            team_info: Dict mapping team_id to conference/division info
            season_start: Season start date

        Returns:
            List of game event dicts ready for events_insert_batch
        """
        events = []
        all_teams = list(range(1, self.TOTAL_TEAMS + 1))
        random.shuffle(all_teams)

        # Calculate week start date
        week_start = season_start + timedelta(days=(week - 1) * 7)

        game_num = 0
        for i in range(0, self.TOTAL_TEAMS, 2):
            home_team = all_teams[i]
            away_team = all_teams[i + 1]
            game_num += 1

            # Create game event
            game_id = f"regular_{self._season}_{week}_{game_num}"
            event_id = str(uuid.uuid4())

            # Calculate game datetime (Sunday 1pm for simplicity)
            game_date = week_start + timedelta(days=3)  # Thursday + 3 = Sunday
            game_date = game_date.replace(hour=13, minute=0, second=0, microsecond=0)

            # Determine if divisional/conference game
            home_conf = team_info[home_team]["conference"]
            away_conf = team_info[away_team]["conference"]
            home_div = team_info[home_team]["division"]
            away_div = team_info[away_team]["division"]

            is_conference = home_conf == away_conf
            is_divisional = is_conference and home_div == away_div

            event = {
                "event_id": event_id,
                "event_type": "GAME",
                "timestamp": int(game_date.timestamp() * 1000),
                "game_id": game_id,
                "data": {
                    "parameters": {
                        "away_team_id": away_team,
                        "home_team_id": home_team,
                        "week": week,
                        "season": self._season,
                        "season_type": "regular_season",
                        "game_type": "regular",
                        "game_date": game_date.isoformat(),
                        "overtime_type": "regular_season"
                    },
                    "results": None,
                    "metadata": {
                        "matchup_description": f"Week {week}: Team {away_team} @ Team {home_team}",
                        "is_playoff_game": False,
                        "is_divisional": is_divisional,
                        "is_conference": is_conference
                    }
                }
            }

            events.append(event)

        return events

    def _calculate_season_start(self) -> datetime:
        """
        Calculate NFL regular season start date.

        The NFL season starts the Thursday after Labor Day.
        Labor Day is the first Monday in September.

        Returns:
            datetime of first regular season game
        """
        # Start with September 1st of the season year
        sept_1 = datetime(self._season, 9, 1)

        # Find Labor Day (first Monday in September)
        weekday = sept_1.weekday()
        if weekday == 0:  # Sept 1 is Monday
            days_until_monday = 0
        else:
            days_until_monday = (7 - weekday) % 7

        labor_day = sept_1 + timedelta(days=days_until_monday)

        # Season starts Thursday after Labor Day
        season_start = labor_day + timedelta(days=3)
        return season_start.replace(hour=20, minute=0, second=0, microsecond=0)

    def _build_team_info(self) -> Dict[int, Dict[str, str]]:
        """Build team conference/division lookup."""
        team_info = {}
        for team_id_str, team in self._teams_data.items():
            team_info[team["team_id"]] = {
                "conference": team["conference"],
                "division": team["division"]
            }
        return team_info