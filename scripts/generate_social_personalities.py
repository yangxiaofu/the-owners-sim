"""
Generate social media personalities for a dynasty.

One-time setup script to create 8-12 fan personalities per team,
beat reporters, and league-wide media commentators.

Usage:
    PYTHONPATH=src python scripts/generate_social_personalities.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.services.personality_generator import PersonalityGenerator

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "database" / "game_cycle" / "game_cycle.db"
DYNASTY_ID = "default"  # Default dynasty ID


def main():
    """Generate all social media personalities."""
    print("=" * 60)
    print("Social Media Personality Generator")
    print("=" * 60)

    # Connect to database
    print(f"\nConnecting to database: {DB_PATH}")
    db = GameCycleDatabase(str(DB_PATH))

    # Create generator
    print(f"Generating personalities for dynasty: {DYNASTY_ID}")
    generator = PersonalityGenerator(db, DYNASTY_ID)

    # Check if personalities already exist
    from game_cycle.database.social_personalities_api import SocialPersonalityAPI
    api = SocialPersonalityAPI(db)
    existing = api.get_all_personalities(DYNASTY_ID)

    if existing:
        print(f"\n⚠️  WARNING: {len(existing)} personalities already exist!")
        response = input("Delete and regenerate? (yes/no): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            db.close()
            return

        # Delete existing personalities
        print("Deleting existing personalities...")
        conn = db.get_connection()
        conn.execute("DELETE FROM social_personalities WHERE dynasty_id = ?", (DYNASTY_ID,))
        conn.commit()

    # Generate personalities
    print("\nGenerating personalities...")
    print("  - 8-12 fans per team (32 teams)")
    print("  - 1 beat reporter per team")
    print("  - 5-8 hot-take analysts (league-wide)")
    print("  - 3-5 stats analysts (league-wide)")
    print()

    counts = generator.generate_all_personalities()

    # Display results
    print("\n" + "=" * 60)
    print("Generation Complete!")
    print("=" * 60)
    print(f"  Fans:            {counts['fans']:3d}")
    print(f"  Beat Reporters:  {counts['beat_reporters']:3d}")
    print(f"  Hot Takes:       {counts['hot_takes']:3d}")
    print(f"  Stats Analysts:  {counts['stats_analysts']:3d}")
    print(f"  {'─' * 25}")
    total = sum(counts.values())
    print(f"  TOTAL:          {total:3d}")
    print()

    # Close database
    db.close()
    print("✓ Personalities saved to database successfully!")


if __name__ == '__main__':
    main()
