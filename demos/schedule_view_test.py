#!/usr/bin/env python3
"""
Schedule View Test Demo

Quick test script to diagnose schedule_view issues without running full app.
Copies current database and displays schedule view in isolation.

Usage:
    PYTHONPATH=src python demos/schedule_view_test.py

Features:
- Shows schedule view with current database data
- Prints debug info about loaded games
- Allows comparing displayed data vs database queries
"""

import sys
import os
import shutil
from pathlib import Path

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget,
    QPushButton, QLabel, QHBoxLayout, QTextEdit
)
from PySide6.QtCore import Qt

# Import after path setup
from game_cycle_ui.views.schedule_view import ScheduleView
from game_cycle.database.connection import GameCycleDatabase


class ScheduleTestWindow(QMainWindow):
    """Test window for schedule view debugging."""

    def __init__(self, db_path: str, dynasty_id: str, season: int):
        super().__init__()
        self.db_path = db_path
        self.dynasty_id = dynasty_id
        self.season = season

        self.setWindowTitle(f"Schedule View Test - {dynasty_id} (Season {season})")
        self.setGeometry(100, 100, 1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Info header
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"Dynasty: {dynasty_id}"))
        info_layout.addWidget(QLabel(f"Season: {season}"))
        info_layout.addWidget(QLabel(f"DB: {db_path}"))
        layout.addLayout(info_layout)

        # Control buttons
        btn_layout = QHBoxLayout()

        reload_btn = QPushButton("Reload Data")
        reload_btn.clicked.connect(self._reload_data)
        btn_layout.addWidget(reload_btn)

        query_btn = QPushButton("Query Database")
        query_btn.clicked.connect(self._query_database)
        btn_layout.addWidget(query_btn)

        compare_btn = QPushButton("Compare Data")
        compare_btn.clicked.connect(self._compare_data)
        btn_layout.addWidget(compare_btn)

        layout.addLayout(btn_layout)

        # Schedule view
        self.schedule_view = ScheduleView()
        layout.addWidget(self.schedule_view, stretch=3)

        # Debug output
        self.debug_output = QTextEdit()
        self.debug_output.setReadOnly(True)
        self.debug_output.setMaximumHeight(200)
        layout.addWidget(self.debug_output, stretch=1)

        # Load initial data
        self._reload_data()

    def _reload_data(self):
        """Reload schedule data and print debug info."""
        self.debug_output.clear()
        self._log("=== Reloading Schedule Data ===")
        self._log(f"Dynasty: {self.dynasty_id}")
        self._log(f"Season: {self.season}")
        self._log(f"DB Path: {self.db_path}")

        # Set context - this triggers data load
        self.schedule_view.set_context(self.dynasty_id, self.db_path, self.season)

        # Print loaded data stats
        schedule_data = self.schedule_view._schedule_data
        self._log(f"\nLoaded {len(schedule_data)} weeks of data")

        for week in sorted(schedule_data.keys()):
            games = schedule_data[week]
            self._log(f"  Week {week}: {len(games)} games")
            if week == 1 and games:
                self._log(f"    First game: home={games[0].home_team_id}, away={games[0].away_team_id}")

    def _query_database(self):
        """Query database directly and show results."""
        self._log("\n=== Database Query Results ===")

        db = GameCycleDatabase(self.db_path)

        # Query games table
        games = db.query_all(
            """SELECT game_id, week, home_team_id, away_team_id, home_score, away_score
               FROM games
               WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season' AND week = 1
               ORDER BY game_id""",
            (self.dynasty_id, self.season)
        )

        self._log(f"\nGames table (Week 1): {len(games)} games")
        for g in games[:5]:
            self._log(f"  {g['game_id']}: home={g['home_team_id']}, away={g['away_team_id']}, "
                     f"score={g['away_score']}-{g['home_score']}")
        if len(games) > 5:
            self._log(f"  ... and {len(games) - 5} more")

        # Query events table
        events = db.query_all(
            """SELECT event_id, game_id,
                      json_extract(data, '$.parameters.week') as week,
                      json_extract(data, '$.parameters.home_team_id') as home,
                      json_extract(data, '$.parameters.away_team_id') as away
               FROM events
               WHERE dynasty_id = ?
                 AND json_extract(data, '$.parameters.season') = ?
                 AND json_extract(data, '$.parameters.season_type') = 'regular_season'
                 AND json_extract(data, '$.parameters.week') = 1
               ORDER BY game_id""",
            (self.dynasty_id, self.season)
        )

        self._log(f"\nEvents table (Week 1): {len(events)} events")
        for e in events[:5]:
            self._log(f"  {e['game_id']}: home={e['home']}, away={e['away']}")
        if len(events) > 5:
            self._log(f"  ... and {len(events) - 5} more")

    def _compare_data(self):
        """Compare UI data with database data."""
        self._log("\n=== Data Comparison ===")

        # Get UI data
        ui_games = self.schedule_view._schedule_data.get(1, [])
        self._log(f"\nUI shows {len(ui_games)} games for Week 1")

        # Get DB data
        db = GameCycleDatabase(self.db_path)
        db_games = db.query_all(
            """SELECT game_id, home_team_id, away_team_id
               FROM games
               WHERE dynasty_id = ? AND season = ? AND season_type = 'regular_season' AND week = 1""",
            (self.dynasty_id, self.season)
        )
        self._log(f"DB has {len(db_games)} games for Week 1")

        # Compare
        ui_game_ids = {g.id for g in ui_games}
        db_game_ids = {g['game_id'] for g in db_games}

        only_ui = ui_game_ids - db_game_ids
        only_db = db_game_ids - ui_game_ids

        if only_ui:
            self._log(f"\n⚠️ Games in UI but NOT in DB: {only_ui}")
        if only_db:
            self._log(f"\n⚠️ Games in DB but NOT in UI: {only_db}")
        if not only_ui and not only_db and len(ui_games) == len(db_games):
            self._log("\n✓ UI and DB match!")

        # Check for malformed games
        malformed = [g for g in ui_games if not g.home_team_id or not g.away_team_id]
        if malformed:
            self._log(f"\n⚠️ Malformed games in UI: {len(malformed)}")
            for g in malformed:
                self._log(f"  ID={g.id}, home={g.home_team_id}, away={g.away_team_id}")

    def _log(self, msg: str):
        """Add message to debug output."""
        self.debug_output.append(msg)
        print(msg)


def get_latest_dynasty(db_path: str) -> tuple[str, int]:
    """Get most recent dynasty and season from database."""
    db = GameCycleDatabase(db_path)
    result = db.query_one(
        """SELECT dynasty_id, MAX(season) as season
           FROM games
           WHERE season_type = 'regular_season'
           GROUP BY dynasty_id
           ORDER BY season DESC, dynasty_id DESC
           LIMIT 1"""
    )
    if result:
        return result['dynasty_id'], result['season']
    return None, None


def main():
    """Main entry point."""
    # Database path
    db_path = "data/database/game_cycle/game_cycle.db"

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("Run from project root directory")
        sys.exit(1)

    # Get dynasty/season from command line or use latest
    if len(sys.argv) >= 3:
        dynasty_id = sys.argv[1]
        season = int(sys.argv[2])
    else:
        dynasty_id, season = get_latest_dynasty(db_path)
        if not dynasty_id:
            print("No game data found in database")
            sys.exit(1)
        print(f"Using latest dynasty: {dynasty_id}, season {season}")

    # Create Qt app
    app = QApplication(sys.argv)

    # Create and show window
    window = ScheduleTestWindow(db_path, dynasty_id, season)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
