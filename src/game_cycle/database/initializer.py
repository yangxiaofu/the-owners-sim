"""
Database initializer for game_cycle.

Populates the database with teams, schedule, and initial standings.
"""

import json
from pathlib import Path
from typing import Dict, Any

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
        self._season_year: int = 2025

    def initialize(self, season_year: int = 2025, skip_preseason: bool = True) -> None:
        """
        Full initialization of game cycle database.

        Args:
            season_year: Starting season year
            skip_preseason: If True, start at Week 1 (default)
        """
        self._season_year = season_year
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
        """Generate an 18-week NFL schedule using ScheduleService."""
        from ..services.schedule_service import ScheduleService

        # Use a default dynasty_id for initial schedule generation
        # This will be overwritten when a dynasty is created
        default_dynasty_id = "_schedule_init_"
        service = ScheduleService(self.db.db_path, default_dynasty_id, self._season_year)
        service.generate_schedule(clear_existing=True)

    def _initialize_stage_state(self, season_year: int, skip_preseason: bool) -> None:
        """Initialize the starting stage state."""
        self.db.execute("DELETE FROM stage_state")

        if skip_preseason:
            stage = "REGULAR_WEEK_1"
            phase = "REGULAR_SEASON"
        else:
            # Start at training camp to go through preseason weeks
            # (OFFSEASON_PRESEASON_W1/W2/W3 are part of offseason flow now)
            stage = "OFFSEASON_TRAINING_CAMP"
            phase = "OFFSEASON"

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
