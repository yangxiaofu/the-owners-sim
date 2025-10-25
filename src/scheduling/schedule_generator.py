"""
NFL Schedule Generator

Generates complete NFL schedules with dynamic date calculations:
- Regular season: 17 weeks, 272 games
- Preseason: 3 weeks, 48 games
- Dynamic Labor Day calculation (first Monday in September)
- Dynamic season start (first Thursday AFTER Labor Day)

Game timing follows realistic NFL patterns:
- Thursday Night Football (1 game, 8:00 PM)
- Sunday games (13 games, various time slots)
- Monday Night Football (2 games, 8:00 PM)
"""

from datetime import datetime, timedelta
from typing import List, Tuple, Set
import random
import logging

from constants.team_ids import TeamIDs
from events.event_database_api import EventDatabaseAPI
from events.game_event import GameEvent


class RandomScheduleGenerator:
    """
    Generates random but valid NFL schedules for simulation purposes.

    The generator ensures:
    - 17 weeks of regular season games (272 total)
    - 3 weeks of preseason games (48 total)
    - Each week has exactly 16 games (all 32 teams play)
    - No team plays twice in the same week
    - Realistic game timing (Thursday, Sunday, Monday)
    - Dynamic date calculations (Labor Day, season starts)
    - All games stored in EventDatabaseAPI
    """

    # NFL regular season constants
    TOTAL_WEEKS = 17
    GAMES_PER_WEEK = 16
    TOTAL_TEAMS = 32

    # Preseason constants (modern NFL format, post-2021)
    PRESEASON_WEEKS = 3
    PRESEASON_GAMES_PER_WEEK = 16
    PRESEASON_TOTAL_GAMES = PRESEASON_WEEKS * PRESEASON_GAMES_PER_WEEK  # 48 games

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

    # Preseason game timing (mostly Saturday games)
    PRESEASON_GAME_SLOTS = {
        'thursday_evening': {'day_offset': 0, 'hour': 19, 'minute': 0, 'count': 2},
        'saturday_early': {'day_offset': 2, 'hour': 13, 'minute': 0, 'count': 6},
        'saturday_afternoon': {'day_offset': 2, 'hour': 16, 'minute': 0, 'count': 4},
        'saturday_evening': {'day_offset': 2, 'hour': 19, 'minute': 0, 'count': 2},
        'sunday_afternoon': {'day_offset': 3, 'hour': 16, 'minute': 0, 'count': 2},
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

    # ==================== Dynamic Date Calculation Methods ====================

    @staticmethod
    def _calculate_labor_day(year: int) -> datetime:
        """
        Calculate Labor Day for a given year.

        Labor Day is the first Monday in September.

        Args:
            year: Year to calculate for

        Returns:
            datetime of Labor Day at midnight
        """
        # Start with September 1st
        sept_1 = datetime(year, 9, 1)

        # Get weekday (0=Monday, 6=Sunday)
        weekday = sept_1.weekday()

        # Calculate days until first Monday
        if weekday == 0:  # Sept 1 is Monday
            days_until_monday = 0
        else:  # Sept 1 is Tue-Sun
            days_until_monday = (7 - weekday) % 7

        labor_day = sept_1 + timedelta(days=days_until_monday)
        return labor_day

    @staticmethod
    def _calculate_regular_season_start(year: int) -> datetime:
        """
        Calculate NFL regular season start date (first Thursday after Labor Day).

        The NFL regular season always starts on the Thursday following Labor Day,
        which falls between September 5-11 depending on when Labor Day occurs.

        Args:
            year: Year to calculate for

        Returns:
            datetime of first regular season game (Thursday, 8:00 PM ET)

        Examples:
            2024: Labor Day = Sept 2 (Mon) → First Thu = Sept 5
            2025: Labor Day = Sept 1 (Mon) → First Thu = Sept 4
            2026: Labor Day = Sept 7 (Mon) → First Thu = Sept 10
        """
        labor_day = RandomScheduleGenerator._calculate_labor_day(year)

        # Labor Day is Monday (weekday 0), so Thursday is 3 days later
        first_thursday = labor_day + timedelta(days=3)

        # Set time to 8:00 PM (NFL kickoff time)
        first_thursday = first_thursday.replace(hour=20, minute=0, second=0, microsecond=0)

        return first_thursday

    def _calculate_preseason_start(self, year: int) -> datetime:
        """
        Calculate preseason start date (mid-August, ~3.5 weeks before regular season).

        Preseason typically begins in mid-August, allowing 3 weeks of games
        plus ~4 days for final roster cuts before regular season starts.

        Args:
            year: Year to calculate for

        Returns:
            datetime of first preseason game (typically mid-August Thursday)
        """
        # Calculate regular season start
        regular_season_start = self._calculate_regular_season_start(year)

        # Preseason starts ~3.5 weeks before regular season
        # 3 weeks of preseason games + ~4 days buffer for final roster cuts
        preseason_start = regular_season_start - timedelta(days=25)  # ~3.5 weeks

        # Adjust to nearest Thursday (preseason traditionally starts Thursday)
        weekday = preseason_start.weekday()
        if weekday != 3:  # 3 = Thursday
            days_to_thursday = (3 - weekday) % 7
            preseason_start = preseason_start + timedelta(days=days_to_thursday)

        # Set time to 8:00 PM
        preseason_start = preseason_start.replace(hour=20, minute=0, second=0, microsecond=0)

        return preseason_start

    # ==================== Regular Season Generation ====================

    def generate_season(
        self,
        season_year: int = 2024,
        start_date: datetime = None,
        seed: int = None
    ) -> List[GameEvent]:
        """
        Generate a complete 17-week NFL regular season with random matchups.

        Args:
            season_year: NFL season year (e.g., 2024 for 2024-25 season)
            start_date: Optional custom start date (defaults to dynamic Labor Day calculation)
            seed: Optional random seed for reproducible schedules

        Returns:
            List of all 272 generated GameEvent objects

        Raises:
            ValueError: If schedule generation fails validation
        """
        self.logger.info(f"Generating random {season_year} NFL regular season schedule...")

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            self.logger.info(f"Using random seed: {seed}")

        # Use provided start date or calculate dynamically from Labor Day
        if start_date is None:
            start_date = self._calculate_regular_season_start(season_year)
            self.logger.info(
                f"Calculated regular season start: {start_date.strftime('%A, %B %d, %Y at %I:%M %p')} "
                f"(first Thursday after Labor Day)"
            )

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
                season_year=season_year,
                game_type="regular_season"
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
        self._validate_season_schedule(all_games, self.TOTAL_WEEKS)

        self.logger.info(
            f"Regular season generation complete! Total games: {len(all_games)} "
            f"({self.TOTAL_WEEKS} weeks × {self.GAMES_PER_WEEK} games)"
        )

        return all_games

    # ==================== Preseason Generation ====================

    def generate_preseason(
        self,
        season_year: int = 2024,
        seed: int = None
    ) -> List[GameEvent]:
        """
        Generate complete 3-week preseason schedule (48 total games).

        Creates realistic preseason schedule with:
        - 3 games per team (modern NFL format, post-2021)
        - Geographic proximity matchups (divisional/conference priority)
        - Separate preseason game_type for stat isolation
        - Thursday/Saturday/Sunday game timing

        Args:
            season_year: NFL season year
            seed: Optional random seed for reproducible schedules

        Returns:
            List of all 48 generated GameEvent objects (3 weeks × 16 games)

        Notes:
            - Preseason games have season_type='preseason' for filtering
            - Stats tracked separately from regular season
            - Games start ~3.5 weeks before regular season opener
        """
        self.logger.info(f"Generating {season_year} preseason schedule...")

        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
            self.logger.info(f"Using random seed: {seed}")

        # Calculate preseason start date
        preseason_start = self._calculate_preseason_start(season_year)
        self.logger.info(f"Preseason starts: {preseason_start.strftime('%A, %B %d, %Y')}")

        all_preseason_games = []

        # Generate each preseason week
        for week_number in range(1, self.PRESEASON_WEEKS + 1):
            self.logger.info(f"Generating Preseason Week {week_number}...")

            # Calculate week start (weeks are 7 days apart)
            week_start = preseason_start + timedelta(days=(week_number - 1) * 7)

            # Generate matchups (geographic proximity)
            matchups = self._generate_geographic_matchups()

            # Assign game times (use preseason time slots)
            week_games = self._assign_preseason_game_times(
                matchups=matchups,
                week_number=week_number,
                week_start=week_start,
                season_year=season_year
            )

            all_preseason_games.extend(week_games)

            # [PRESEASON_DEBUG Point 6a] Store Games Call
            print(f"\n[PRESEASON_DEBUG Point 6a] Storing Week {week_number} games...")
            print(f"  Games to store: {len(week_games)}")
            print(f"  Dynasty ID: {self.dynasty_id}")
            print(f"  Event DB: {self.event_db}")

            # Store in database
            self._store_games(week_games)

            print(f"[PRESEASON_DEBUG Point 6a] ✅ Week {week_number} games stored")

            self.logger.info(f"Preseason Week {week_number} complete: {len(week_games)} games")

        # Validate preseason schedule
        self._validate_season_schedule(all_preseason_games, self.PRESEASON_WEEKS)

        self.logger.info(
            f"Preseason generation complete! Total games: {len(all_preseason_games)} "
            f"({self.PRESEASON_WEEKS} weeks × {self.PRESEASON_GAMES_PER_WEEK} games)"
        )

        return all_preseason_games

    def _generate_geographic_matchups(self) -> List[Tuple[int, int]]:
        """
        Generate matchups based on geographic proximity for preseason realism.

        Groups teams by division and creates matchups favoring:
        1. Divisional opponents (most common in real NFL preseason)
        2. Conference opponents (secondary priority)
        3. Cross-conference geographic neighbors (tertiary)

        Returns:
            List of 16 tuples (away_team_id, home_team_id)

        Note: This is a simplified approximation. Real NFL preseason schedules
        are more complex and involve rotating patterns over multiple years.
        """
        from team_management.teams.team_loader import TeamDataLoader

        loader = TeamDataLoader()
        teams_by_division = {}

        # Organize teams by division
        for team_id in self._all_team_ids:
            team = loader.get_team_by_id(team_id)
            div_key = f"{team.conference}_{team.division}"
            if div_key not in teams_by_division:
                teams_by_division[div_key] = []
            teams_by_division[div_key].append(team_id)

        matchups = []
        used_teams = set()

        # Strategy: Pair teams within same division first, then conference, then cross-conference
        divisions = list(teams_by_division.keys())
        random.shuffle(divisions)  # Randomize division order

        for div_key in divisions:
            div_teams = [t for t in teams_by_division[div_key] if t not in used_teams]

            # Pair teams within division (if possible)
            while len(div_teams) >= 2:
                away = div_teams.pop(0)
                home = div_teams.pop(0)
                matchups.append((away, home))
                used_teams.add(away)
                used_teams.add(home)

        # Pair remaining teams randomly
        remaining = [t for t in self._all_team_ids if t not in used_teams]
        random.shuffle(remaining)

        while len(remaining) >= 2:
            away = remaining.pop(0)
            home = remaining.pop(0)
            matchups.append((away, home))
            used_teams.add(away)
            used_teams.add(home)

        # Validate all teams matched
        if len(used_teams) != self.TOTAL_TEAMS:
            raise ValueError(
                f"Matchup generation failed: {len(used_teams)} teams matched, expected {self.TOTAL_TEAMS}"
            )

        # Validate matchups
        self._validate_matchups(matchups)

        return matchups

    def _assign_preseason_game_times(
        self,
        matchups: List[Tuple[int, int]],
        week_number: int,
        week_start: datetime,
        season_year: int
    ) -> List[GameEvent]:
        """
        Assign time slots to preseason games.

        Preseason games typically air on:
        - Thursday: 1-2 games (Hall of Fame game week 0, then regular schedule)
        - Saturday: 10-12 games (main preseason day)
        - Sunday: 2-4 games (overflow)

        Args:
            matchups: List of (away_id, home_id) tuples
            week_number: Preseason week (1-3)
            week_start: Start datetime of the week
            season_year: Season year

        Returns:
            List of GameEvent objects with assigned times
        """
        games = []
        matchup_idx = 0

        # Assign games to preseason time slots
        for slot_name, slot_config in self.PRESEASON_GAME_SLOTS.items():
            for _ in range(slot_config['count']):
                if matchup_idx >= len(matchups):
                    break

                away_id, home_id = matchups[matchup_idx]

                # Calculate game datetime
                game_date = week_start + timedelta(days=slot_config['day_offset'])
                game_datetime = game_date.replace(
                    hour=slot_config['hour'],
                    minute=slot_config['minute']
                )

                # Create game ID: preseason_{year}_{week}_{number}
                game_id = f"preseason_{season_year}_{week_number}_{matchup_idx + 1}"

                # Create GameEvent with season_type='preseason'
                print(f"[DYNASTY_TRACE] Creating preseason GameEvent with dynasty_id={self.dynasty_id}")
                game = GameEvent(
                    away_team_id=away_id,
                    home_team_id=home_id,
                    game_date=game_datetime,
                    week=week_number,
                    dynasty_id=self.dynasty_id,
                    game_id=game_id,  # Pass the game_id
                    season=season_year,
                    season_type="preseason",  # ← Key: separate from regular season
                    game_type="preseason",
                    overtime_type="preseason"
                )

                games.append(game)
                matchup_idx += 1

        return games

    # ==================== Common Schedule Generation Methods ====================

    def _generate_week_schedule(
        self,
        week_number: int,
        week_start: datetime,
        season_year: int,
        game_type: str = "regular_season"
    ) -> List[GameEvent]:
        """
        Generate all 16 games for a single week.

        Args:
            week_number: Week number (1-17)
            week_start: Start date of the week (Thursday)
            season_year: NFL season year
            game_type: Game type ('regular_season' or 'preseason')

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
            season_year=season_year,
            game_type=game_type
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
        season_year: int,
        game_type: str = "regular_season"
    ) -> List[GameEvent]:
        """
        Assign matchups to specific game times following NFL patterns.

        Args:
            matchups: List of (away_team_id, home_team_id) tuples
            week_number: Week number for these games
            week_start: Thursday start date for the week
            season_year: NFL season year
            game_type: Game type ('regular_season' or 'preseason')

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
                    season_type=game_type,
                    game_type="regular" if game_type == "regular_season" else game_type,
                    overtime_type="regular_season" if game_type == "regular_season" else game_type
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
        # [PRESEASON_DEBUG Point 6b] _store_games Method
        print(f"\n[PRESEASON_DEBUG Point 6b] _store_games() called...")
        print(f"  Games count: {len(games)}")
        print(f"  Event DB path: {self.event_db.db_path}")

        if len(games) > 0:
            print(f"  First game details:")
            print(f"    game_id: {games[0].game_id}")
            print(f"    dynasty_id: {games[0].dynasty_id}")
            print(f"    event_type: {games[0].event_type}")

        try:
            # Use batch insert for performance (10-50x faster than individual inserts)
            self.event_db.insert_events(games)

            print(f"[PRESEASON_DEBUG Point 6b] ✅ insert_events() completed successfully")
            print(f"  Stored {len(games)} games in database")

            self.logger.debug(f"Stored {len(games)} games in database")

        except Exception as e:
            print(f"[PRESEASON_DEBUG Point 6b] ❌ insert_events() FAILED!")
            print(f"  Error: {e}")
            self.logger.error(f"Failed to store games: {e}")
            raise

    def _validate_season_schedule(self, all_games: List[GameEvent], weeks: int) -> None:
        """
        Validate complete season schedule for correctness.

        Args:
            all_games: All games in the season
            weeks: Number of weeks expected (17 for regular, 3 for preseason)

        Raises:
            ValueError: If validation fails
        """
        total_expected = weeks * self.GAMES_PER_WEEK

        if len(all_games) != total_expected:
            raise ValueError(
                f"Invalid total games: {len(all_games)}, expected {total_expected}"
            )

        # Validate each team plays correct number of games
        team_game_counts: dict[int, int] = {}

        for game in all_games:
            team_game_counts[game.away_team_id] = \
                team_game_counts.get(game.away_team_id, 0) + 1
            team_game_counts[game.home_team_id] = \
                team_game_counts.get(game.home_team_id, 0) + 1

        for team_id in self._all_team_ids:
            games_played = team_game_counts.get(team_id, 0)
            if games_played != weeks:
                raise ValueError(
                    f"Team {team_id} plays {games_played} games, "
                    f"expected {weeks}"
                )

        self.logger.info("✅ Schedule validation passed")

    # ==================== Utility Methods ====================

    def get_schedule_summary(self) -> dict:
        """
        Get summary statistics of the generated schedule.

        Returns:
            Dictionary with schedule statistics
        """
        stats = self.event_db.get_statistics()

        return {
            'total_games': stats.get('total_events', 0),
            'expected_regular_season_games': self.TOTAL_WEEKS * self.GAMES_PER_WEEK,
            'expected_preseason_games': self.PRESEASON_TOTAL_GAMES,
            'weeks': self.TOTAL_WEEKS,
            'games_per_week': self.GAMES_PER_WEEK,
            'total_teams': self.TOTAL_TEAMS,
            'games_per_team_regular': self.TOTAL_WEEKS,
            'games_per_team_preseason': self.PRESEASON_WEEKS
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
    dynasty_id: str = "default",
    logger: logging.Logger = None
) -> RandomScheduleGenerator:
    """
    Factory function to create a schedule generator with database.

    Args:
        database_path: Path to events database
        dynasty_id: Dynasty context for game isolation
        logger: Optional logger instance

    Returns:
        Configured RandomScheduleGenerator instance
    """
    event_db = EventDatabaseAPI(database_path)
    return RandomScheduleGenerator(event_db, dynasty_id, logger)


# Demo/testing entry point
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    logger = logging.getLogger(__name__)

    print("="*80)
    print("NFL SCHEDULE GENERATOR DEMO".center(80))
    print("="*80)

    # Create generator with temporary file database for demo
    # Note: in-memory databases don't work well with batch inserts
    import tempfile
    import os
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()

    event_db = EventDatabaseAPI(temp_db.name)
    generator = RandomScheduleGenerator(event_db, "demo_dynasty", logger)

    print(f"\nTotal teams: {generator.TOTAL_TEAMS}")
    print(f"Regular season: {generator.TOTAL_WEEKS} weeks × {generator.GAMES_PER_WEEK} games = {generator.TOTAL_WEEKS * generator.GAMES_PER_WEEK} total")
    print(f"Preseason: {generator.PRESEASON_WEEKS} weeks × {generator.PRESEASON_GAMES_PER_WEEK} games = {generator.PRESEASON_TOTAL_GAMES} total")

    # Generate preseason with fixed seed for reproducibility
    print(f"\n{'='*80}")
    print("GENERATING PRESEASON".center(80))
    print(f"{'='*80}")
    preseason_games = generator.generate_preseason(season_year=2025, seed=42)

    # Generate regular season
    print(f"\n{'='*80}")
    print("GENERATING REGULAR SEASON".center(80))
    print(f"{'='*80}")
    regular_games = generator.generate_season(season_year=2025, seed=42)

    print(f"\n✅ Season generation complete!")

    # Print summary
    summary = generator.get_schedule_summary()
    print(f"\n{'='*80}")
    print("SCHEDULE SUMMARY".center(80))
    print(f"{'='*80}")
    print(f"Total games generated: {summary['total_games']}")
    print(f"Expected regular season: {summary['expected_regular_season_games']}")
    print(f"Expected preseason: {summary['expected_preseason_games']}")
    print(f"Regular season weeks: {summary['weeks']}")
    print(f"Games per week: {summary['games_per_week']}")
    print(f"Total teams: {summary['total_teams']}")

    # Print sample schedules
    print(f"\n{'='*80}")
    print("SAMPLE: Preseason Week 1".center(80))
    print(f"{'='*80}")
    generator.print_week_schedule(1)

    print(f"\n{'='*80}")
    print("SAMPLE: Regular Season Week 1".center(80))
    print(f"{'='*80}")
    generator.print_week_schedule(1)

    print(f"\n{'='*80}")
    print("DEMO COMPLETE".center(80))
    print(f"{'='*80}\n")

    # Clean up temporary database
    os.unlink(temp_db.name)
    print(f"Temporary database cleaned up: {temp_db.name}")
