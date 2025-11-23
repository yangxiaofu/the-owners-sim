#!/usr/bin/env python3
"""
Standalone Draft Day Demo Launcher

Interactive NFL draft simulation where you control a randomly-assigned team.
Run this script directly to launch the draft day interface.
"""

import sys
import os
import random
from pathlib import Path

# Add project root and src/ to Python path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Now import from local directory and src/
from setup_demo_database import setup_draft_demo_database
from team_management.teams.team_loader import get_team_by_id
from draft_day_dialog import DraftDayDialog
from draft_demo_controller import DraftDemoController

from PySide6.QtWidgets import QApplication, QMessageBox


def main():
    """Main entry point for standalone draft day demo."""

    # Database path
    demo_dir = Path(__file__).parent
    db_path = demo_dir / "draft_demo.db"

    # Dynasty ID is always the same for the demo
    dynasty_id = "draft_day_demo"

    # Check if database exists, create if not
    if not db_path.exists():
        print("Draft demo database not found. Setting up draft database...")
        print("This may take 10-15 seconds to generate 224 prospects...\n")

        success = setup_draft_demo_database(str(db_path))

        if not success:
            print("❌ Failed to create draft database. Exiting.")
            sys.exit(1)

        print(f"\n✅ Draft database created successfully!")
        print(f"   Location: {db_path}")
        print(f"   Dynasty ID: {dynasty_id}\n")
    else:
        print(f"Using existing draft database: {db_path}")

    # Randomly select user team (1-32)
    user_team_id = random.randint(1, 32)
    team_info = get_team_by_id(user_team_id)
    team_name = team_info.full_name

    print("\n" + "=" * 60)
    print("WELCOME TO THE NFL DRAFT")
    print("=" * 60)
    print(f"You are the General Manager of: {team_name}")
    print(f"Team ID: {user_team_id}")
    print("\nGood luck building your championship roster!")
    print("=" * 60 + "\n")

    # Create Qt application
    app = QApplication(sys.argv)

    # Create controller
    try:
        controller = DraftDemoController(
            db_path=str(db_path),
            dynasty_id=dynasty_id,
            season=2026,  # Draft year
            user_team_id=user_team_id
        )
    except ValueError as e:
        print(f"❌ Error initializing draft controller: {e}")
        sys.exit(1)

    # Launch draft day dialog
    dialog = DraftDayDialog(controller=controller)
    dialog.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
