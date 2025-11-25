"""
Database initializer for game_cycle.

Populates the database with teams, schedule, and initial standings.
"""

import json
import random
from pathlib import Path
from typing import List, Tuple, Dict, Any

from .connection import GameCycleDatabase


class GameCycleInitializer:
    """
    Initializes the game cycle database with:
    - 32 NFL teams
    - 18-week regular season schedule
    - Initial standings (0-0-0)
    - Starting stage state
    """

    # Division matchups for NFL schedule (simplified)
    # Each team plays: 6 division games, 4 same-place-in-division, 4 rotating conference, 3 inter-conference

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db
        self._teams_data: Dict[str, Any] = {}

    def initialize(self, season_year: int = 2025, skip_preseason: bool = True) -> None:
        """
        Full initialization of game cycle database.

        Args:
            season_year: Starting season year
            skip_preseason: If True, start at Week 1 (default)
        """
        self._load_teams_data()
        self._populate_teams()
        self._initialize_standings()
        self._generate_schedule()
        self._initialize_stage_state(season_year, skip_preseason)

    def _load_teams_data(self) -> None:
        """Load team data from JSON file."""
        teams_path = Path(__file__).parent.parent.parent / "data" / "teams.json"

        if not teams_path.exists():
            raise FileNotFoundError(f"Teams data not found: {teams_path}")

        with open(teams_path, 'r') as f:
            data = json.load(f)

        self._teams_data = data.get("teams", {})

    def _populate_teams(self) -> None:
        """Insert all 32 teams into database."""
        if self.db.row_count("teams") == 32:
            return  # Already populated

        teams_to_insert = []
        for team_id_str, team in self._teams_data.items():
            teams_to_insert.append((
                team["team_id"],
                team["full_name"],
                team["abbreviation"],
                team["conference"],
                team["division"]
            ))

        self.db.executemany(
            "INSERT OR REPLACE INTO teams (team_id, name, abbreviation, conference, division) VALUES (?, ?, ?, ?, ?)",
            teams_to_insert
        )

    def _initialize_standings(self) -> None:
        """Initialize standings to 0-0-0 for all teams."""
        self.db.execute("DELETE FROM standings")

        standings_to_insert = [(team_id,) for team_id in range(1, 33)]
        self.db.executemany(
            "INSERT INTO standings (team_id) VALUES (?)",
            standings_to_insert
        )

    def _generate_schedule(self) -> None:
        """Generate an 18-week NFL schedule."""
        self.db.execute("DELETE FROM schedule")

        # Get teams by division
        divisions = self._get_teams_by_division()

        games = []

        # Generate 18 weeks of games
        for week in range(1, 19):
            week_games = self._generate_week_games(week, divisions)
            games.extend(week_games)

        # Insert all games
        self.db.executemany(
            """INSERT INTO schedule
               (week, home_team_id, away_team_id, is_divisional, is_conference)
               VALUES (?, ?, ?, ?, ?)""",
            games
        )

    def _get_teams_by_division(self) -> Dict[str, List[int]]:
        """
        Group teams by conference-division.

        Returns:
            Dict mapping "AFC_East" etc. to list of team_ids
        """
        divisions = {}

        for team_id_str, team in self._teams_data.items():
            key = f"{team['conference']}_{team['division']}"
            if key not in divisions:
                divisions[key] = []
            divisions[key].append(team["team_id"])

        return divisions

    def _generate_week_games(
        self,
        week: int,
        divisions: Dict[str, List[int]]
    ) -> List[Tuple[int, int, int, int, int]]:
        """
        Generate games for a single week.

        Uses a simplified algorithm that ensures:
        - All 32 teams play each week (no byes in this simplified version)
        - Mix of divisional and non-divisional games

        Args:
            week: Week number (1-18)
            divisions: Teams grouped by division

        Returns:
            List of (week, home_team_id, away_team_id, is_divisional, is_conference)
        """
        games = []
        used_teams = set()

        all_teams = list(range(1, 33))
        random.shuffle(all_teams)

        # Create team info lookup
        team_info = {}
        for team_id_str, team in self._teams_data.items():
            team_info[team["team_id"]] = {
                "conference": team["conference"],
                "division": team["division"]
            }

        # Pair up teams
        for i in range(0, 32, 2):
            home_team = all_teams[i]
            away_team = all_teams[i + 1]

            # Determine if divisional/conference game
            home_conf = team_info[home_team]["conference"]
            away_conf = team_info[away_team]["conference"]
            home_div = team_info[home_team]["division"]
            away_div = team_info[away_team]["division"]

            is_conference = 1 if home_conf == away_conf else 0
            is_divisional = 1 if (is_conference and home_div == away_div) else 0

            games.append((week, home_team, away_team, is_divisional, is_conference))

        return games

    def _initialize_stage_state(self, season_year: int, skip_preseason: bool) -> None:
        """Initialize the starting stage state."""
        self.db.execute("DELETE FROM stage_state")

        if skip_preseason:
            stage = "REGULAR_WEEK_1"
            phase = "REGULAR_SEASON"
        else:
            stage = "PRESEASON_WEEK_1"
            phase = "PRESEASON"

        self.db.execute(
            "INSERT INTO stage_state (id, season_year, current_stage, phase) VALUES (1, ?, ?, ?)",
            (season_year, stage, phase)
        )

    def is_initialized(self) -> bool:
        """Check if database is already initialized."""
        return (
            self.db.row_count("teams") == 32 and
            self.db.row_count("standings") == 32 and
            self.db.row_count("schedule") > 0 and
            self.db.row_count("stage_state") == 1
        )
