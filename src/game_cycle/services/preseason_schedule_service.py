"""
Preseason Schedule Service - Generates 3-week NFL preseason schedules.

Generates matchups for preseason exhibition games following NFL-style rules:
- No team plays the same opponent twice during preseason
- No division games (avoid seeing division rivals before regular season)
- All 32 teams play each week (16 games per week)

Modern NFL preseason format (2024+):
- 3 preseason games per team
- 48 total games (3 weeks × 16 games per week)
- Single cutdown date after Week 3

Architecture:
    PreseasonScheduleService → UnifiedDatabaseAPI (events_insert_batch)
                             → StandingsAPI (preseason standings)
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple


class PreseasonScheduleService:
    """
    Generates 3-week NFL preseason schedules with non-repeating, non-division matchups.

    Constraints:
    - No team plays the same opponent twice across all 3 weeks
    - No division games (teams in same division never play each other)
    - All 32 teams play exactly 3 preseason games

    Games are stored with season_type='preseason' and update preseason standings.

    Usage:
        service = PreseasonScheduleService(db_path, dynasty_id, season=2026)
        games_created = service.generate_preseason_schedule()
        print(f"Created {games_created} preseason games")  # 48 games
    """

    TOTAL_WEEKS = 3
    TOTAL_TEAMS = 32
    GAMES_PER_WEEK = 16

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        """
        Initialize the preseason schedule service.

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
        with open(teams_path, "r") as f:
            self._teams_data = json.load(f).get("teams", {})

    def generate_preseason_schedule(self, clear_existing: bool = True) -> int:
        """
        Generate a 3-week NFL preseason schedule as game events.

        Also initializes preseason standings for all 32 teams.

        Args:
            clear_existing: If True, clears existing preseason game events first

        Returns:
            Number of games created (48 = 3 weeks × 16 games)
        """
        from database.unified_api import UnifiedDatabaseAPI

        api = UnifiedDatabaseAPI(self._db_path, self._dynasty_id)

        if clear_existing:
            deleted = self._clear_existing_preseason_games(api)
            if deleted > 0:
                print(f"[PreseasonScheduleService] Cleared {deleted} existing preseason games")

        # Initialize preseason standings
        self._initialize_preseason_standings(api)

        # Generate preseason game events
        game_events = self._generate_all_preseason_events()

        # Insert using existing batch API
        api.events_insert_batch(game_events)

        print(
            f"[PreseasonScheduleService] Created {len(game_events)} preseason games for season {self._season}"
        )
        return len(game_events)

    def _initialize_preseason_standings(self, api) -> None:
        """
        Initialize preseason standings for all 32 teams.

        Uses the game_cycle standings table with season_type='preseason'.
        """
        from game_cycle.database.connection import GameCycleDatabase
        from game_cycle.database.standings_api import StandingsAPI

        try:
            db = GameCycleDatabase(self._db_path)
            standings_api = StandingsAPI(db)

            # Check if preseason standings already exist
            existing = standings_api.get_standings(
                self._dynasty_id, self._season, season_type="preseason"
            )
            if existing:
                # Reset to 0-0-0
                standings_api.reset_standings(
                    self._dynasty_id, self._season, season_type="preseason"
                )
                print("[PreseasonScheduleService] Reset existing preseason standings")
            else:
                # Insert new standings for each team
                for team_id in range(1, 33):
                    db.execute(
                        """
                        INSERT OR IGNORE INTO standings
                        (dynasty_id, season, team_id, season_type, wins, losses, ties,
                         points_for, points_against)
                        VALUES (?, ?, ?, 'preseason', 0, 0, 0, 0, 0)
                        """,
                        (self._dynasty_id, self._season, team_id),
                    )
                print("[PreseasonScheduleService] Initialized preseason standings for 32 teams")

            db.close()
        except Exception as e:
            print(f"[PreseasonScheduleService] Error initializing standings: {e}")

    def _clear_existing_preseason_games(self, api) -> int:
        """
        Clear existing preseason games for this dynasty and season.

        Args:
            api: UnifiedDatabaseAPI instance

        Returns:
            Number of games deleted
        """
        try:
            import sqlite3
            conn = sqlite3.connect(api.database_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM events
                WHERE dynasty_id = ?
                AND event_type = 'GAME'
                AND json_extract(data, '$.parameters.season') = ?
                AND json_extract(data, '$.parameters.season_type') = 'preseason'
                """,
                (self._dynasty_id, self._season),
            )
            deleted = cursor.rowcount
            conn.commit()
            conn.close()
            return deleted
        except Exception as e:
            print(f"[PreseasonScheduleService] Error clearing games: {e}")
            return 0

    def _generate_all_preseason_events(self) -> List[Dict[str, Any]]:
        """
        Generate all 48 preseason game events.

        Constraints enforced:
        - No team plays the same opponent twice (across all 3 weeks)
        - No division games (teams never play division rivals)
        - All 32 teams play each week

        Returns:
            List of game event dicts ready for events_insert_batch()
        """
        team_info = self._build_team_info()
        preseason_start = self._calculate_preseason_start()

        # Track which matchups have occurred to prevent duplicates
        used_matchups: Set[Tuple[int, int]] = set()

        # Generate division lookup for quick checking
        divisions = self._build_division_groups(team_info)

        all_events = []
        for week in range(1, self.TOTAL_WEEKS + 1):
            week_matchups = self._generate_valid_week_matchups(
                team_info, divisions, used_matchups
            )

            week_events = self._create_week_events(
                week, week_matchups, team_info, preseason_start
            )
            all_events.extend(week_events)

        return all_events

    def _build_division_groups(
        self, team_info: Dict[int, Dict[str, str]]
    ) -> Dict[str, List[int]]:
        """
        Build a mapping of division key to team IDs.

        Args:
            team_info: Dict mapping team_id to conference/division info

        Returns:
            Dict mapping "AFC_North" -> [team_ids]
        """
        divisions: Dict[str, List[int]] = {}
        for team_id, info in team_info.items():
            key = f"{info['conference']}_{info['division']}"
            if key not in divisions:
                divisions[key] = []
            divisions[key].append(team_id)
        return divisions

    def _are_same_division(
        self,
        team1: int,
        team2: int,
        team_info: Dict[int, Dict[str, str]]
    ) -> bool:
        """Check if two teams are in the same division."""
        info1 = team_info[team1]
        info2 = team_info[team2]
        return (
            info1["conference"] == info2["conference"]
            and info1["division"] == info2["division"]
        )

    def _normalize_matchup(self, team1: int, team2: int) -> Tuple[int, int]:
        """Create a normalized matchup tuple (smaller id first) for tracking."""
        return (min(team1, team2), max(team1, team2))

    def _generate_valid_week_matchups(
        self,
        team_info: Dict[int, Dict[str, str]],
        divisions: Dict[str, List[int]],
        used_matchups: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """
        Generate valid matchups for a single week.

        Constraints:
        - All 32 teams play exactly once
        - No division games
        - No repeat matchups from previous weeks

        Args:
            team_info: Team conference/division lookup
            divisions: Division groupings
            used_matchups: Set of already-used matchup tuples

        Returns:
            List of (home_team, away_team) tuples
        """
        all_teams = list(range(1, self.TOTAL_TEAMS + 1))
        matchups: List[Tuple[int, int]] = []
        matched_teams: Set[int] = set()

        # Sort teams by number of valid opponents (most constrained first)
        def count_valid_opponents(team: int) -> int:
            count = 0
            for opponent in all_teams:
                if opponent == team:
                    continue
                if opponent in matched_teams:
                    continue
                if self._are_same_division(team, opponent, team_info):
                    continue
                if self._normalize_matchup(team, opponent) in used_matchups:
                    continue
                count += 1
            return count

        # Use backtracking if simple greedy fails
        max_attempts = 100
        for attempt in range(max_attempts):
            matchups = []
            matched_teams = set()

            # Shuffle teams for randomness
            shuffled_teams = all_teams.copy()
            random.shuffle(shuffled_teams)

            # Sort by most constrained first (fewer valid opponents)
            if attempt > 10:
                shuffled_teams.sort(key=count_valid_opponents)

            success = True
            for team in shuffled_teams:
                if team in matched_teams:
                    continue

                # Find valid opponent
                valid_opponents = []
                for opponent in shuffled_teams:
                    if opponent == team:
                        continue
                    if opponent in matched_teams:
                        continue
                    if self._are_same_division(team, opponent, team_info):
                        continue
                    if self._normalize_matchup(team, opponent) in used_matchups:
                        continue
                    valid_opponents.append(opponent)

                if not valid_opponents:
                    success = False
                    break

                # Pick random valid opponent
                opponent = random.choice(valid_opponents)

                # Alternate home/away
                if len(matchups) % 2 == 0:
                    matchups.append((team, opponent))
                else:
                    matchups.append((opponent, team))

                matched_teams.add(team)
                matched_teams.add(opponent)

            if success and len(matchups) == self.GAMES_PER_WEEK:
                # Mark matchups as used
                for home, away in matchups:
                    used_matchups.add(self._normalize_matchup(home, away))
                return matchups

        # Fallback: relaxed constraints if we can't find valid matchups
        print(
            "[PreseasonScheduleService] Warning: Could not satisfy all constraints, using relaxed matchups"
        )
        return self._generate_relaxed_matchups(team_info, used_matchups)

    def _generate_relaxed_matchups(
        self,
        team_info: Dict[int, Dict[str, str]],
        used_matchups: Set[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """
        Generate matchups with relaxed constraints (allow division games if needed).

        Used as fallback when strict constraints cannot be satisfied.
        """
        all_teams = list(range(1, self.TOTAL_TEAMS + 1))
        random.shuffle(all_teams)
        matchups = []

        for i in range(0, self.TOTAL_TEAMS, 2):
            home = all_teams[i]
            away = all_teams[i + 1]
            matchups.append((home, away))
            used_matchups.add(self._normalize_matchup(home, away))

        return matchups

    def _create_week_events(
        self,
        week: int,
        matchups: List[Tuple[int, int]],
        team_info: Dict[int, Dict[str, str]],
        preseason_start: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Create game event dicts for a single week.

        Args:
            week: Week number (1-3)
            matchups: List of (home_team, away_team) tuples
            team_info: Team conference/division lookup
            preseason_start: Preseason start date

        Returns:
            List of game event dicts
        """
        events = []
        week_start = preseason_start + timedelta(days=(week - 1) * 7)

        for game_num, (home_team, away_team) in enumerate(matchups, start=1):
            game_id = f"preseason_{self._season}_{week}_{game_num}"
            event_id = str(uuid.uuid4())

            # Saturday 7pm for preseason games
            game_date = week_start + timedelta(days=5)
            game_date = game_date.replace(hour=19, minute=0, second=0, microsecond=0)

            # Determine matchup type
            home_conf = team_info[home_team]["conference"]
            away_conf = team_info[away_team]["conference"]
            is_conference = home_conf == away_conf

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
                        "season_type": "preseason",
                        "game_type": "preseason",
                        "game_date": game_date.isoformat(),
                        "overtime_type": "preseason",
                    },
                    "results": None,
                    "metadata": {
                        "is_playoff_game": False,
                        "is_divisional": False,  # Never divisional in preseason
                        "is_conference": is_conference,
                        "is_preseason": True,
                    },
                },
            }
            events.append(event)

        return events

    def _calculate_preseason_start(self) -> datetime:
        """
        Calculate NFL preseason start date.

        Preseason starts approximately 4 weeks before regular season.
        Regular season starts Thursday after Labor Day.

        Returns:
            datetime of first preseason game week
        """
        sept_1 = datetime(self._season, 9, 1)
        weekday = sept_1.weekday()
        days_until_monday = (7 - weekday) % 7 if weekday != 0 else 0
        labor_day = sept_1 + timedelta(days=days_until_monday)
        regular_season_start = labor_day + timedelta(days=3)
        preseason_start = regular_season_start - timedelta(weeks=4)
        return preseason_start.replace(hour=19, minute=0, second=0, microsecond=0)

    def _build_team_info(self) -> Dict[int, Dict[str, str]]:
        """Build team conference/division lookup."""
        team_info = {}
        for team_id_str, team in self._teams_data.items():
            team_info[team["team_id"]] = {
                "conference": team["conference"],
                "division": team["division"],
            }
        return team_info

    def get_preseason_games(self, week: int = None) -> List[Dict[str, Any]]:
        """
        Get preseason games from the database.

        Args:
            week: Optional week filter (1-3). If None, returns all weeks.

        Returns:
            List of game data dicts with parameters and results
        """
        import sqlite3

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            if week:
                cursor.execute(
                    """
                    SELECT data FROM events
                    WHERE dynasty_id = ?
                    AND event_type = 'GAME'
                    AND json_extract(data, '$.parameters.season') = ?
                    AND json_extract(data, '$.parameters.season_type') = 'preseason'
                    AND CAST(json_extract(data, '$.parameters.week') AS INTEGER) = ?
                    ORDER BY timestamp
                    """,
                    (self._dynasty_id, self._season, week),
                )
            else:
                cursor.execute(
                    """
                    SELECT data FROM events
                    WHERE dynasty_id = ?
                    AND event_type = 'GAME'
                    AND json_extract(data, '$.parameters.season') = ?
                    AND json_extract(data, '$.parameters.season_type') = 'preseason'
                    ORDER BY json_extract(data, '$.parameters.week'), timestamp
                    """,
                    (self._dynasty_id, self._season),
                )

            rows = cursor.fetchall()
            conn.close()
            games = []
            for row in rows:
                data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                games.append(data)
            return games

        except Exception as e:
            print(f"[PreseasonScheduleService] Error getting games: {e}")
            return []
