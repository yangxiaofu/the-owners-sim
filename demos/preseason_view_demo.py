"""
Demo script to test the Preseason View styling and layout.

Opens the Preseason View directly with sample data to verify:
- SummaryPanel header with stats
- Theme color usage
- User game highlighting
- Roster status colors
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import Qt

from game_cycle_ui.views.preseason_view import PreseasonView


def main():
    """Run the preseason view demo."""
    app = QApplication(sys.argv)

    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Preseason View Demo - Theme Standardization")
    window.resize(1200, 800)

    # Create central widget
    central = QWidget()
    layout = QVBoxLayout(central)
    layout.setContentsMargins(0, 0, 0, 0)

    # Create preseason view
    preseason_view = PreseasonView()
    layout.addWidget(preseason_view)

    window.setCentralWidget(central)

    # Set context
    preseason_view.set_context(
        dynasty_id="demo_dynasty",
        db_path="demo.db",
        season=2025,
        user_team_id=1  # Buffalo Bills
    )

    # Set to Week 3 (to enable navigation to Week 1 and Week 2)
    preseason_view.set_week(3)

    # Create sample games (16 games for preseason week)
    sample_games = [
        # User's game (Buffalo Bills)
        {
            "game_id": "preseason_2025_w1_g01",
            "home_team_id": 14,  # Kansas City Chiefs
            "away_team_id": 1,   # Buffalo Bills (USER)
            "home_team_name": "Kansas City Chiefs",
            "away_team_name": "Buffalo Bills",
            "home_abbreviation": "KC",
            "away_abbreviation": "BUF",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 27,
            "away_score": 24,
            "is_played": True,
            "is_user_game": True,
            "week": 1
        },
        # Other games
        {
            "game_id": "preseason_2025_w1_g02",
            "home_team_id": 2,
            "away_team_id": 3,
            "home_team_name": "Miami Dolphins",
            "away_team_name": "New England Patriots",
            "home_abbreviation": "MIA",
            "away_abbreviation": "NE",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 21,
            "away_score": 17,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g03",
            "home_team_id": 5,
            "away_team_id": 6,
            "home_team_name": "Baltimore Ravens",
            "away_team_name": "Cincinnati Bengals",
            "home_abbreviation": "BAL",
            "away_abbreviation": "CIN",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 14,
            "away_score": 10,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g04",
            "home_team_id": 7,
            "away_team_id": 8,
            "home_team_name": "Cleveland Browns",
            "away_team_name": "Pittsburgh Steelers",
            "home_abbreviation": "CLE",
            "away_abbreviation": "PIT",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 20,
            "away_score": 23,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g05",
            "home_team_id": 9,
            "away_team_id": 10,
            "home_team_name": "Houston Texans",
            "away_team_name": "Indianapolis Colts",
            "home_abbreviation": "HOU",
            "away_abbreviation": "IND",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 28,
            "away_score": 31,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g06",
            "home_team_id": 11,
            "away_team_id": 12,
            "home_team_name": "Jacksonville Jaguars",
            "away_team_name": "Tennessee Titans",
            "home_abbreviation": "JAX",
            "away_abbreviation": "TEN",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 17,
            "away_score": 14,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g07",
            "home_team_id": 13,
            "away_team_id": 15,
            "home_team_name": "Denver Broncos",
            "away_team_name": "Las Vegas Raiders",
            "home_abbreviation": "DEN",
            "away_abbreviation": "LV",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 24,
            "away_score": 20,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g08",
            "home_team_id": 16,
            "away_team_id": 17,
            "home_team_name": "Los Angeles Chargers",
            "away_team_name": "Dallas Cowboys",
            "home_abbreviation": "LAC",
            "away_abbreviation": "DAL",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 21,
            "away_score": 27,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g09",
            "home_team_id": 18,
            "away_team_id": 19,
            "home_team_name": "New York Giants",
            "away_team_name": "Philadelphia Eagles",
            "home_abbreviation": "NYG",
            "away_abbreviation": "PHI",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 10,
            "away_score": 24,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g10",
            "home_team_id": 20,
            "away_team_id": 21,
            "home_team_name": "Washington Commanders",
            "away_team_name": "Chicago Bears",
            "home_abbreviation": "WAS",
            "away_abbreviation": "CHI",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 17,
            "away_score": 20,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g11",
            "home_team_id": 22,
            "away_team_id": 23,
            "home_team_name": "Detroit Lions",
            "away_team_name": "Green Bay Packers",
            "home_abbreviation": "DET",
            "away_abbreviation": "GB",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 31,
            "away_score": 28,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g12",
            "home_team_id": 24,
            "away_team_id": 25,
            "home_team_name": "Minnesota Vikings",
            "away_team_name": "Atlanta Falcons",
            "home_abbreviation": "MIN",
            "away_abbreviation": "ATL",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 23,
            "away_score": 20,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g13",
            "home_team_id": 26,
            "away_team_id": 27,
            "home_team_name": "Carolina Panthers",
            "away_team_name": "New Orleans Saints",
            "home_abbreviation": "CAR",
            "away_abbreviation": "NO",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 14,
            "away_score": 21,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g14",
            "home_team_id": 28,
            "away_team_id": 29,
            "home_team_name": "Tampa Bay Buccaneers",
            "away_team_name": "Arizona Cardinals",
            "home_abbreviation": "TB",
            "away_abbreviation": "ARI",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 27,
            "away_score": 24,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g15",
            "home_team_id": 30,
            "away_team_id": 31,
            "home_team_name": "Los Angeles Rams",
            "away_team_name": "San Francisco 49ers",
            "home_abbreviation": "LAR",
            "away_abbreviation": "SF",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 20,
            "away_score": 34,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        },
        {
            "game_id": "preseason_2025_w1_g16",
            "home_team_id": 32,
            "away_team_id": 4,
            "home_team_name": "Seattle Seahawks",
            "away_team_name": "New York Jets",
            "home_abbreviation": "SEA",
            "away_abbreviation": "NYJ",
            "home_record": "0-0",
            "away_record": "0-0",
            "home_score": 17,
            "away_score": 13,
            "is_played": True,
            "is_user_game": False,
            "week": 1
        }
    ]

    # Set games
    preseason_view.set_games(sample_games)

    # Set roster status (Week 1 - no cuts required)
    preseason_view.set_roster_status(90, 90)

    # Show window
    window.show()

    print("=" * 70)
    print("Preseason View Demo - Week Navigation Testing")
    print("=" * 70)
    print("\nStarting at Week 3 - Test navigation features:")
    print("1. ✓ Prev Week button should be ENABLED (can go back to Week 2, 1)")
    print("2. ✓ Next Week button should be DISABLED (already at Week 3)")
    print("3. ✓ Click 'Prev Week' to view Week 2 games")
    print("4. ✓ Review mode indicator should appear: '(Review Mode - Read Only)'")
    print("5. ✓ Cuts section should be HIDDEN when viewing Week 1 or 2")
    print("6. ✓ Click 'Prev Week' again to view Week 1 games")
    print("7. ✓ Click 'Next Week' to return to Week 2, then Week 3")
    print("8. ✓ At Week 3, cuts section should be VISIBLE")
    print("\nDouble-click any game to test box score viewing")
    print("=" * 70)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
