#!/usr/bin/env python3
"""Quick test to see what dates Wild Card games are scheduled on."""

import sys
from pathlib import Path
import tempfile
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from playoff_controller import PlayoffController


def main():
    """Check Wild Card game dates."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='_test.db')
    temp_db_path = temp_db.name
    temp_db.close()

    try:
        controller = PlayoffController(
            database_path=temp_db_path,
            dynasty_id="test",
            season_year=2024,
            verbose_logging=False
        )

        # Get all Wild Card events
        wild_card_events = controller.event_db.get_events_by_game_id_prefix(
            f"playoff_test_2024_wild_",
            event_type="GAME"
        )

        print(f"Wild Card Games: {len(wild_card_events)}")
        print(f"Calendar Start Date: {controller.calendar.get_current_date()}")
        print(f"Wild Card Start Date: {controller.wild_card_start_date}")
        print("\nGame Dates:")
        for event in wild_card_events:
            params = event['data'].get('parameters', event['data'])
            game_date = params.get('game_date', 'NO DATE')
            game_id = event.get('game_id', 'NO ID')
            print(f"  {game_id}: {game_date}")

    finally:
        if os.path.exists(temp_db_path):
            os.unlink(temp_db_path)


if __name__ == "__main__":
    main()
