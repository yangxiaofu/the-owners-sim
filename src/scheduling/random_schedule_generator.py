"""
Random Schedule Generator

Generates a complete 17-week random NFL schedule (272 games).
Each week consists of 16 games with all 32 teams playing exactly once.

Game timing follows realistic NFL patterns:
- Thursday Night Football (1 game, 8:00 PM)
- Sunday games (13 games, various time slots)
- Monday Night Football (2 games, 8:00 PM)
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Tuple, Set
import random
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from constants.team_ids import TeamIDs
from events.event_database_api import EventDatabaseAPI
from events.game_event import GameEvent


class RandomScheduleGenerator:
    """
    Generates random but valid NFL schedules for simulation purposes.

    The generator ensures:
    - 17 weeks of regular season games
    - Each week has exactly 16 games (all 32 teams play)
    - No team plays twice in the same week
    - Realistic game timing (Thursday, Sunday, Monday)
    - All games stored in EventDatabaseAPI
    """

    # NFL season timing constants
    DEFAULT_SEASON_START = datetime(2024, 9, 5, 20, 0)  # Thursday, Sept 5, 2024, 8:00 PM
    TOTAL_WEEKS = 17
    GAMES_PER_WEEK = 16
    TOTAL_TEAMS = 32

    # Game timing templates for realistic NFL schedule
    GAME_SLOTS = {
        'thursday_night': {'day_offset': 0, 'hour': 20, 'minute': 0, 'count': 1},
        'sunday_early_1': {'day_offset': 3, 'hour': 13, 'minute': 0, 'count': 6},
        'sunday_early_2': {'day_offset': 3, 'hour': 13, 'minute': 0, 'count': 1},
        'sunday_late_1': {'day_offset': 3, 'hour': 16, 'minute': 5, 'count': 2},
        'sunday_late_2': {'day_offset': 3, 'hour': 16, 'minute': 25, 'count': 2},
        'sunday_night': {'day_offset': 3, 'hour': 20, 'minute': 20, 'count': 2},
        'monday_night_1': {'day_offset': 4, 'hour': 20, 'minute': 15, 'count': 1},
        'monday_night_2': {'day_offset': 4, 'hour': 20, 'minute': 15, 'count': 1},
    }

    def __init__(self, event_db: EventDatabaseAPI, dynasty_id: str = "default", logger: logging.Logger = None):
        """
        Initialize random schedule generator.

        Args:
            event_db: Event database API for storing generated games
            dynasty_id: Dynasty context for game event isolation
            logger: Optional logger for tracking generation progress
        """
        self.event_db = event_db
        self.dynasty_id = dynasty_id
        print(f"[DYNASTY_TRACE] RandomScheduleGenerator.__init__(): dynasty_id={dynasty_id}")
        self.logger = logger or logging.getLogger(__name__)

        # Get all team IDs and remove duplicates (work around any potential bugs)
        raw_ids = TeamIDs.get_all_team_ids()
        self._all_team_ids = sorted(list(set(raw_ids)))

        # Validate team count
        if len(self._all_team_ids) != self.TOTAL_TEAMS:
            raise ValueError(
                f"Expected {self.TOTAL_TEAMS} teams, got {len(self._all_team_ids)}. "
                f"Team IDs: {self._all_team_ids}"
            )

    def generate_season(
        self,
        season_year: int = 2024,
        start_date: datetime = None,
        seed: int = None
    ) -> List[GameEvent]:
        """
        Generate a complete 17-week NFL season with random matchups.

        Args:
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            start_date: Optional custom start date (defaults to Sept 5, 2024)
            seed: Optional random seed for reproducible schedules

        Returns:
            List of all 272 generated GameEvent objects

        Raises:
            ValueError: If schedule generation fails validation
        """
        self.logger.info(f"Generating random {season_year} NFL schedule...")

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            self.logger.info(f"Using random seed: {seed}")

        # Use provided start date or default
        if start_date is None:
            start_date = self.DEFAULT_SEASON_START.replace(year=season_year)

        all_games: List[GameEvent] = []

        # Generate each week
        for week_number in range(1, self.TOTAL_WEEKS + 1):
            self.logger.info(f"Generating Week {week_number}...")

            # Calculate week start date (each week starts on Thursday)
            week_start = start_date + timedelta(days=(week_number - 1) * 7)

            # Generate matchups for this week
            week_games = self._generate_week_schedule(
                week_number=week_number,
                week_start=week_start,
                season_year=season_year
            )

            # Validate week has correct number of games
            if len(week_games) != self.GAMES_PER_WEEK:
                raise ValueError(
                    f"Week {week_number} generated {len(week_games)} games, "
                    f"expected {self.GAMES_PER_WEEK}"
                )

            all_games.extend(week_games)

            # Store games in database
            self._store_games(week_games)

            self.logger.info(f"Week {week_number} complete: {len(week_games)} games")

        # Final validation
        self._validate_season_schedule(all_games)

        self.logger.info(
            f"Season generation complete! Total games: {len(all_games)} "
            f"({self.TOTAL_WEEKS} weeks × {self.GAMES_PER_WEEK} games)"
        )

        return all_games

    def _generate_week_schedule(
        self,
        week_number: int,
        week_start: datetime,
        season_year: int
    ) -> List[GameEvent]:
        """
        Generate all 16 games for a single week.

        Args:
            week_number: Week number (1-17)
            week_start: Start date of the week (Thursday)
            season_year: NFL season year

        Returns:
            List of 16 GameEvent objects for this week
        """
        # Generate random matchups (16 games = all 32 teams)
        matchups = self._generate_random_matchups()

        # Assign games to time slots
        week_games = self._assign_game_times(
            matchups=matchups,
            week_number=week_number,
            week_start=week_start,
            season_year=season_year
        )

        return week_games

    def _generate_random_matchups(self) -> List[Tuple[int, int]]:
        """
        Generate random matchups ensuring each team plays exactly once.

        Returns:
            List of 16 tuples (away_team_id, home_team_id)

        Algorithm:
        1. Shuffle all 32 teams randomly
        2. Pair them sequentially (0-1, 2-3, 4-5, etc.)
        3. Randomly assign home/away for each pair
        """
        # Shuffle teams randomly
        teams = self._all_team_ids.copy()
        random.shuffle(teams)

        matchups: List[Tuple[int, int]] = []

        # Pair teams sequentially
        for i in range(0, len(teams), 2):
            team1 = teams[i]
            team2 = teams[i + 1]

            # Randomly assign home/away
            if random.random() < 0.5:
                away_team, home_team = team1, team2
            else:
                away_team, home_team = team2, team1

            matchups.append((away_team, home_team))

        # Validate matchups
        self._validate_matchups(matchups)

        return matchups

    def _validate_matchups(self, matchups: List[Tuple[int, int]]) -> None:
        """
        Validate that matchups are valid (no duplicate teams).

        Args:
            matchups: List of (away_team_id, home_team_id) tuples

        Raises:
            ValueError: If validation fails
        """
        teams_used: Set[int] = set()

        for away_team, home_team in matchups:
            # Check for self-play
            if away_team == home_team:
                raise ValueError(f"Team {away_team} cannot play itself")

            # Check for duplicate usage
            if away_team in teams_used:
                raise ValueError(f"Team {away_team} used multiple times in same week")
            if home_team in teams_used:
                raise ValueError(f"Team {home_team} used multiple times in same week")

            teams_used.add(away_team)
            teams_used.add(home_team)

        # Verify all teams are used
        if len(teams_used) != self.TOTAL_TEAMS:
            raise ValueError(
                f"Not all teams used: {len(teams_used)}/{self.TOTAL_TEAMS}"
            )

    def _assign_game_times(
        self,
        matchups: List[Tuple[int, int]],
        week_number: int,
        week_start: datetime,
        season_year: int
    ) -> List[GameEvent]:
        """
        Assign matchups to specific game times following NFL patterns.

        Args:
            matchups: List of (away_team_id, home_team_id) tuples
            week_number: Week number for these games
            week_start: Thursday start date for the week
            season_year: NFL season year

        Returns:
            List of GameEvent objects with assigned times
        """
        games: List[GameEvent] = []
        matchup_index = 0

        # Assign games to each time slot
        for slot_name, slot_config in self.GAME_SLOTS.items():
            slot_count = slot_config['count']

            for _ in range(slot_count):
                if matchup_index >= len(matchups):
                    raise ValueError(
                        f"Ran out of matchups at slot {slot_name} "
                        f"(index {matchup_index})"
                    )

                away_team, home_team = matchups[matchup_index]
                matchup_index += 1

                # Calculate game datetime
                game_date = week_start + timedelta(days=slot_config['day_offset'])
                game_date = game_date.replace(
                    hour=slot_config['hour'],
                    minute=slot_config['minute']
                )

                # Create GameEvent
                print(f"[DYNASTY_TRACE] Creating GameEvent with dynasty_id={self.dynasty_id}")
                game = GameEvent(
                    away_team_id=away_team,
                    home_team_id=home_team,
                    game_date=game_date,
                    week=week_number,
                    dynasty_id=self.dynasty_id,
                    season=season_year,
                    season_type="regular_season",
                    game_type="regular",
                    overtime_type="regular_season"
                )

                games.append(game)

        # Verify all matchups were assigned
        if matchup_index != len(matchups):
            raise ValueError(
                f"Not all matchups assigned: {matchup_index}/{len(matchups)}"
            )

        return games

    def _store_games(self, games: List[GameEvent]) -> None:
        """
        Store games in the event database.

        Args:
            games: List of GameEvent objects to store

        Raises:
            Exception: If database storage fails
        """
        try:
            # Use batch insert for performance (10-50x faster than individual inserts)
            self.event_db.insert_events(games)
            self.logger.debug(f"Stored {len(games)} games in database")

        except Exception as e:
            self.logger.error(f"Failed to store games: {e}")
            raise

    def _validate_season_schedule(self, all_games: List[GameEvent]) -> None:
        """
        Validate complete season schedule for correctness.

        Args:
            all_games: All games in the season

        Raises:
            ValueError: If validation fails
        """
        total_expected = self.TOTAL_WEEKS * self.GAMES_PER_WEEK

        if len(all_games) != total_expected:
            raise ValueError(
                f"Invalid total games: {len(all_games)}, expected {total_expected}"
            )

        # Validate each team plays correct number of games (17)
        team_game_counts: dict[int, int] = {}

        for game in all_games:
            team_game_counts[game.away_team_id] = \
                team_game_counts.get(game.away_team_id, 0) + 1
            team_game_counts[game.home_team_id] = \
                team_game_counts.get(game.home_team_id, 0) + 1

        for team_id in self._all_team_ids:
            games_played = team_game_counts.get(team_id, 0)
            if games_played != self.TOTAL_WEEKS:
                raise ValueError(
                    f"Team {team_id} plays {games_played} games, "
                    f"expected {self.TOTAL_WEEKS}"
                )

        self.logger.info("✅ Season schedule validation passed")

    def get_schedule_summary(self) -> dict:
        """
        Get summary statistics of the generated schedule.

        Returns:
            Dictionary with schedule statistics
        """
        stats = self.event_db.get_statistics()

        return {
            'total_games': stats.get('total_events', 0),
            'expected_games': self.TOTAL_WEEKS * self.GAMES_PER_WEEK,
            'weeks': self.TOTAL_WEEKS,
            'games_per_week': self.GAMES_PER_WEEK,
            'total_teams': self.TOTAL_TEAMS,
            'games_per_team': self.TOTAL_WEEKS
        }

    def clear_schedule(self) -> int:
        """
        Clear all game events from the database.

        Useful for regenerating schedules or testing.

        Returns:
            Number of events deleted
        """
        self.logger.info("Clearing existing schedule...")

        # Get all GAME events
        all_games = self.event_db.get_events_by_type("GAME")

        # Extract unique game IDs
        game_ids = set(event['game_id'] for event in all_games)

        # Delete all games
        deleted_count = 0
        for game_id in game_ids:
            deleted = self.event_db.delete_events_by_game_id(game_id)
            deleted_count += deleted

        self.logger.info(f"Cleared {deleted_count} game events")

        return deleted_count

    def print_week_schedule(self, week_number: int) -> None:
        """
        Print formatted schedule for a specific week.

        Args:
            week_number: Week to display (1-17)
        """
        # Get all GAME events
        all_games = self.event_db.get_events_by_type("GAME")

        # Filter for this week
        week_games = [
            event for event in all_games
            if event['data'].get('parameters', {}).get('week') == week_number
        ]

        if not week_games:
            print(f"\nNo games found for Week {week_number}")
            return

        # Sort by date
        week_games.sort(key=lambda x: x['timestamp'])

        print(f"\n{'='*80}")
        print(f"WEEK {week_number} SCHEDULE".center(80))
        print(f"{'='*80}\n")

        current_day = None

        for event in week_games:
            game_date = event['timestamp']
            params = event['data'].get('parameters', {})

            away_id = params.get('away_team_id')
            home_id = params.get('home_team_id')

            # Print day header if changed
            day_name = game_date.strftime('%A, %B %d, %Y')
            if day_name != current_day:
                print(f"\n{day_name}")
                print(f"{'-'*80}")
                current_day = day_name

            # Print game
            time_str = game_date.strftime('%I:%M %p')
            print(f"  {time_str} - Team {away_id} @ Team {home_id}")

        print(f"\n{'='*80}")
        print(f"Total games: {len(week_games)}")
        print(f"{'='*80}\n")


def create_schedule_generator(
    database_path: str = "data/events.db",
    logger: logging.Logger = None
) -> RandomScheduleGenerator:
    """
    Factory function to create a schedule generator with database.

    Args:
        database_path: Path to events database
        logger: Optional logger instance

    Returns:
        Configured RandomScheduleGenerator instance
    """
    event_db = EventDatabaseAPI(database_path)
    return RandomScheduleGenerator(event_db, logger)


# Demo/testing entry point
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)

    print("="*80)
    print("RANDOM NFL SCHEDULE GENERATOR DEMO".center(80))
    print("="*80)

    # Create generator with temporary file database for demo
    # Note: in-memory databases don't work well with batch inserts
    import tempfile
    import os
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    event_db = EventDatabaseAPI(temp_db.name)
    generator = RandomScheduleGenerator(event_db, logger)

    print(f"\nGenerating random 17-week NFL schedule...")
    print(f"Total teams: {generator.TOTAL_TEAMS}")
    print(f"Games per week: {generator.GAMES_PER_WEEK}")
    print(f"Total games: {generator.TOTAL_WEEKS * generator.GAMES_PER_WEEK}")

    # Generate season with fixed seed for reproducibility
    all_games = generator.generate_season(season_year=2024, seed=42)

    print(f"\n✅ Season generation complete!")

    # Print summary
    summary = generator.get_schedule_summary()
    print(f"\n{'='*80}")
    print("SCHEDULE SUMMARY".center(80))
    print(f"{'='*80}")
    print(f"Total games generated: {summary['total_games']}")
    print(f"Expected games: {summary['expected_games']}")
    print(f"Weeks: {summary['weeks']}")
    print(f"Games per week: {summary['games_per_week']}")
    print(f"Total teams: {summary['total_teams']}")
    print(f"Games per team: {summary['games_per_team']}")

    # Print Week 1 schedule
    generator.print_week_schedule(1)

    # Print Week 17 schedule
    generator.print_week_schedule(17)

    print(f"\n{'='*80}")
    print("DEMO COMPLETE".center(80))
    print(f"{'='*80}\n")

    # Clean up temporary database
    os.unlink(temp_db.name)
    print(f"Temporary database cleaned up: {temp_db.name}")
