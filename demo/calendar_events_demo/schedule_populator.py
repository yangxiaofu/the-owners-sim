"""
Schedule Populator

Helper utility to create and populate scheduled games into the events database.
Creates realistic NFL game schedules for testing the day simulation system.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
from src.calendar.date_models import Date
from events import EventDatabaseAPI, GameEvent
from constants.team_ids import TeamIDs


class SchedulePopulator:
    """
    Creates and populates game schedules into the events database.

    Provides convenient methods to generate test schedules for demos
    without needing a full schedule generation system.
    """

    def __init__(self, event_db: EventDatabaseAPI, dynasty_id: str = "default"):
        """
        Initialize schedule populator.

        Args:
            event_db: Event database API for storing events
            dynasty_id: Dynasty identifier for game event isolation (default: "default")
        """
        self.event_db = event_db
        self.dynasty_id = dynasty_id

    def create_single_game(
        self,
        away_team_id: int,
        home_team_id: int,
        game_date: datetime,
        week: int,
        season: int = 2024,
        season_type: str = "regular_season"
    ) -> GameEvent:
        """
        Create and store a single game event.

        Args:
            away_team_id: Away team ID (1-32)
            home_team_id: Home team ID (1-32)
            game_date: Date and time of game
            week: Week number
            season: Season year
            season_type: Type of season (regular_season, playoffs, preseason)

        Returns:
            Created GameEvent
        """
        game_event = GameEvent(
            away_team_id=away_team_id,
            home_team_id=home_team_id,
            game_date=game_date,
            week=week,
            dynasty_id=self.dynasty_id,
            season=season,
            season_type=season_type
        )

        # Store in database
        self.event_db.insert_event(game_event)

        print(f"✅ Created game: Week {week} - Team {away_team_id} @ Team {home_team_id} on {game_date.strftime('%Y-%m-%d')}")

        return game_event

    def create_week_1_schedule(self, season: int = 2024) -> List[GameEvent]:
        """
        Create a realistic Week 1 NFL schedule.

        Generates games for Thursday night, Sunday, and Monday night.

        Args:
            season: Season year

        Returns:
            List of created GameEvent objects
        """
        print(f"\n{'='*80}")
        print(f"CREATING WEEK 1 SCHEDULE FOR {season} SEASON")
        print(f"{'='*80}\n")

        games = []

        # Week 1 typically starts on a Thursday in early September
        # Using September 5, 2024 (Thursday) as the kickoff
        week_1_thursday = datetime(season, 9, 5, 20, 0)  # 8:00 PM kickoff

        # Thursday Night Football (1 game)
        games.append(self.create_single_game(
            away_team_id=TeamIDs.BALTIMORE_RAVENS,
            home_team_id=TeamIDs.KANSAS_CITY_CHIEFS,
            game_date=week_1_thursday,
            week=1,
            season=season
        ))

        # Sunday games (September 8, 2024)
        sunday = week_1_thursday + timedelta(days=3)

        # Early games (1:00 PM ET)
        early_games = [
            (TeamIDs.PITTSBURGH_STEELERS, TeamIDs.ATLANTA_FALCONS),
            (TeamIDs.HOUSTON_TEXANS, TeamIDs.INDIANAPOLIS_COLTS),
            (TeamIDs.CHICAGO_BEARS, TeamIDs.TENNESSEE_TITANS),
            (TeamIDs.NEW_ENGLAND_PATRIOTS, TeamIDs.CINCINNATI_BENGALS),
            (TeamIDs.JACKSONVILLE_JAGUARS, TeamIDs.MIAMI_DOLPHINS),
            (TeamIDs.CAROLINA_PANTHERS, TeamIDs.NEW_ORLEANS_SAINTS),
            (TeamIDs.MINNESOTA_VIKINGS, TeamIDs.NEW_YORK_GIANTS),
        ]

        for away, home in early_games:
            game_time = sunday.replace(hour=13, minute=0)
            games.append(self.create_single_game(
                away_team_id=away,
                home_team_id=home,
                game_date=game_time,
                week=1,
                season=season
            ))

        # Late afternoon games (4:05 PM and 4:25 PM ET)
        late_games = [
            (TeamIDs.CLEVELAND_BROWNS, TeamIDs.DALLAS_COWBOYS),
            (TeamIDs.DENVER_BRONCOS, TeamIDs.SEATTLE_SEAHAWKS),
            (TeamIDs.WASHINGTON_COMMANDERS, TeamIDs.TAMPA_BAY_BUCCANEERS),
            (TeamIDs.LAS_VEGAS_RAIDERS, TeamIDs.LOS_ANGELES_CHARGERS),
        ]

        for i, (away, home) in enumerate(late_games):
            # Alternate between 4:05 and 4:25 kickoffs
            hour = 16
            minute = 5 if i % 2 == 0 else 25
            game_time = sunday.replace(hour=hour, minute=minute)
            games.append(self.create_single_game(
                away_team_id=away,
                home_team_id=home,
                game_date=game_time,
                week=1,
                season=season
            ))

        # Sunday Night Football (8:20 PM ET)
        snf_time = sunday.replace(hour=20, minute=20)
        games.append(self.create_single_game(
            away_team_id=TeamIDs.LOS_ANGELES_RAMS,
            home_team_id=TeamIDs.DETROIT_LIONS,
            game_date=snf_time,
            week=1,
            season=season
        ))

        # Monday Night Football (September 9, 2024 - 8:15 PM ET)
        monday = sunday + timedelta(days=1)
        mnf_time = monday.replace(hour=20, minute=15)

        games.append(self.create_single_game(
            away_team_id=TeamIDs.NEW_YORK_JETS,
            home_team_id=TeamIDs.SAN_FRANCISCO_49ERS,
            game_date=mnf_time,
            week=1,
            season=season
        ))

        # Monday Night Football - Second game (8:15 PM ET)
        games.append(self.create_single_game(
            away_team_id=TeamIDs.PHILADELPHIA_EAGLES,
            home_team_id=TeamIDs.GREEN_BAY_PACKERS,
            game_date=mnf_time,
            week=1,
            season=season
        ))

        print(f"\n{'='*80}")
        print(f"WEEK 1 SCHEDULE CREATED: {len(games)} games")
        print(f"{'='*80}")
        print(f"Thursday Night: 1 game")
        print(f"Sunday: 13 games")
        print(f"Monday Night: 2 games")

        return games

    def create_simple_test_schedule(self, test_date: datetime, num_games: int = 3) -> List[GameEvent]:
        """
        Create a simple test schedule with a few games on a specific date.

        Args:
            test_date: Date to schedule games
            num_games: Number of games to create

        Returns:
            List of created GameEvent objects
        """
        print(f"\n{'='*80}")
        print(f"CREATING SIMPLE TEST SCHEDULE")
        print(f"{'='*80}\n")

        games = []

        # Simple matchups for testing
        matchups = [
            (TeamIDs.DETROIT_LIONS, TeamIDs.GREEN_BAY_PACKERS),
            (TeamIDs.KANSAS_CITY_CHIEFS, TeamIDs.BUFFALO_BILLS),
            (TeamIDs.DALLAS_COWBOYS, TeamIDs.PHILADELPHIA_EAGLES),
            (TeamIDs.SAN_FRANCISCO_49ERS, TeamIDs.SEATTLE_SEAHAWKS),
            (TeamIDs.BALTIMORE_RAVENS, TeamIDs.CINCINNATI_BENGALS),
        ]

        for i in range(min(num_games, len(matchups))):
            away, home = matchups[i]
            game_time = test_date.replace(hour=13 + i, minute=0)

            games.append(self.create_single_game(
                away_team_id=away,
                home_team_id=home,
                game_date=game_time,
                week=1,
                season=test_date.year
            ))

        print(f"\n{'='*80}")
        print(f"TEST SCHEDULE CREATED: {len(games)} games on {test_date.strftime('%Y-%m-%d')}")
        print(f"{'='*80}")

        return games

    def clear_all_events(self) -> int:
        """
        Clear all events from the database (useful for testing).

        Returns:
            Number of events deleted
        """
        # Get statistics to see how many events exist
        stats = self.event_db.get_statistics()
        total_events = stats.get('total_events', 0)

        if total_events == 0:
            print("No events to clear.")
            return 0

        # Clear events by getting all unique game IDs and deleting them
        all_events = self.event_db.get_events_by_type("GAME")
        deleted_count = 0

        game_ids = set()
        for event in all_events:
            game_ids.add(event['game_id'])

        for game_id in game_ids:
            deleted = self.event_db.delete_events_by_game_id(game_id)
            deleted_count += deleted

        print(f"✅ Cleared {deleted_count} events from database")
        return deleted_count

    def get_schedule_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all scheduled games in the database.

        Returns:
            Dictionary with schedule statistics
        """
        stats = self.event_db.get_statistics()
        all_games = self.event_db.get_events_by_type("GAME")

        # Group by week
        games_by_week = {}
        for event in all_games:
            params = event['data'].get('parameters', event['data'])
            week = params.get('week', 0)
            if week not in games_by_week:
                games_by_week[week] = []
            games_by_week[week].append(event)

        return {
            "total_games": stats.get('total_events', 0),
            "games_by_week": {week: len(games) for week, games in games_by_week.items()},
            "weeks_with_games": sorted(games_by_week.keys())
        }
