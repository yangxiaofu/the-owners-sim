#!/usr/bin/env python3
"""
Schedule Generator Usage Example

Demonstrates how to use the scheduling module to create
and populate a complete NFL season schedule.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import logging
from scheduling import RandomScheduleGenerator, create_schedule_generator
from events.event_database_api import EventDatabaseAPI


def example_1_basic_usage():
    """Basic usage: Generate a season and view the schedule."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Usage")
    print("="*80)

    # Create generator with custom database
    generator = create_schedule_generator(
        database_path="data/example_schedule.db"
    )

    # Generate season
    print("\nGenerating 2024 season...")
    games = generator.generate_season(season_year=2024)

    # Print summary
    summary = generator.get_schedule_summary()
    print(f"\nGenerated {summary['total_games']} games")
    print(f"Each team plays {summary['games_per_team']} games")

    # View Week 1 schedule
    generator.print_week_schedule(1)


def example_2_reproducible_schedule():
    """Use random seed for reproducible schedules."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Reproducible Schedule with Seed")
    print("="*80)

    # Create generator
    generator = create_schedule_generator(
        database_path="data/reproducible_schedule.db"
    )

    # Generate with fixed seed (will always produce same schedule)
    print("\nGenerating schedule with seed=12345...")
    games = generator.generate_season(season_year=2024, seed=12345)

    print(f"\nGenerated {len(games)} games")
    print("This schedule will be identical every time with seed=12345")


def example_3_custom_start_date():
    """Generate schedule with custom start date."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Custom Start Date")
    print("="*80)

    from datetime import datetime

    # Create generator
    generator = create_schedule_generator(
        database_path="data/custom_date_schedule.db"
    )

    # Generate with custom start date
    custom_start = datetime(2025, 9, 4, 20, 0)  # Thursday, Sept 4, 2025
    print(f"\nGenerating 2025 season starting on {custom_start.strftime('%B %d, %Y')}...")

    games = generator.generate_season(
        season_year=2025,
        start_date=custom_start
    )

    print(f"\nGenerated {len(games)} games")
    generator.print_week_schedule(1)


def example_4_regenerate_schedule():
    """Clear and regenerate a schedule."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Regenerate Schedule")
    print("="*80)

    # Create generator
    generator = create_schedule_generator(
        database_path="data/regenerate_schedule.db"
    )

    # Generate first schedule
    print("\nGenerating initial schedule...")
    generator.generate_season(season_year=2024, seed=100)

    summary = generator.get_schedule_summary()
    print(f"Initial schedule: {summary['total_games']} games")

    # Clear schedule
    print("\nClearing schedule...")
    deleted = generator.clear_schedule()
    print(f"Deleted {deleted} games")

    # Generate new schedule with different seed
    print("\nGenerating new schedule with different matchups...")
    generator.generate_season(season_year=2024, seed=200)

    summary = generator.get_schedule_summary()
    print(f"New schedule: {summary['total_games']} games")


def example_5_view_multiple_weeks():
    """View schedules for multiple weeks."""
    print("\n" + "="*80)
    print("EXAMPLE 5: View Multiple Weeks")
    print("="*80)

    # Create generator
    generator = create_schedule_generator(
        database_path="data/multi_week_schedule.db"
    )

    # Generate season
    print("\nGenerating season...")
    generator.generate_season(season_year=2024)

    # View opening weeks and final week
    print("\n" + "="*80)
    print("Season Opening:")
    print("="*80)
    generator.print_week_schedule(1)
    generator.print_week_schedule(2)

    print("\n" + "="*80)
    print("Season Finale:")
    print("="*80)
    generator.print_week_schedule(17)


def example_6_with_logging():
    """Generate schedule with detailed logging."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Detailed Logging")
    print("="*80)

    # Configure detailed logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger("schedule_generator")

    # Create generator with logger
    event_db = EventDatabaseAPI("data/logged_schedule.db")
    generator = RandomScheduleGenerator(event_db, logger)

    # Generate with logging
    print("\nGenerating season with detailed logs...\n")
    generator.generate_season(season_year=2024, seed=999)

    print("\nLogging complete!")


def main():
    """Run all examples."""
    print("="*80)
    print("RANDOM SCHEDULE GENERATOR EXAMPLES")
    print("="*80)
    print("\nThese examples demonstrate various uses of RandomScheduleGenerator:")
    print("1. Basic usage")
    print("2. Reproducible schedules with random seeds")
    print("3. Custom start dates")
    print("4. Clearing and regenerating schedules")
    print("5. Viewing multiple weeks")
    print("6. Detailed logging")

    # Run all examples
    try:
        example_1_basic_usage()
        example_2_reproducible_schedule()
        example_3_custom_start_date()
        example_4_regenerate_schedule()
        example_5_view_multiple_weeks()
        example_6_with_logging()

        print("\n" + "="*80)
        print("ALL EXAMPLES COMPLETE")
        print("="*80)

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
