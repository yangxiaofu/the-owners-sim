"""
Example: Using Mock Stats Generator

Demonstrates how to generate mock player statistics for a simulated game
and insert them into the database.
"""

from src.game_cycle.services import MockStatsGenerator
import sqlite3


def generate_and_insert_mock_stats():
    """Generate mock stats for a game and insert into database."""

    # Database configuration
    db_path = "data/database/game_cycle/game_cycle.db"
    dynasty_id = "test_dynasty"

    # Initialize generator
    generator = MockStatsGenerator(db_path, dynasty_id)

    # Generate stats for a game
    # Example: Detroit Lions (22) vs Kansas City Chiefs (15)
    mock_stats = generator.generate(
        game_id="2025_week1_DET_KC",
        home_team_id=22,  # Detroit Lions
        away_team_id=15,  # Kansas City Chiefs
        home_score=28,
        away_score=24
    )

    print(f"\n🏈 Generated stats for game: {mock_stats.game_id}")
    print(f"   Home: Team {mock_stats.home_team_id} - {mock_stats.home_score}")
    print(f"   Away: Team {mock_stats.away_team_id} - {mock_stats.away_score}")
    print(f"   Total player stats generated: {len(mock_stats.player_stats)}\n")

    # Display some sample stats
    print("📊 Sample Player Stats:")
    print("-" * 80)

    for stat in mock_stats.player_stats[:5]:  # First 5 players
        print(f"\n{stat['player_name']} ({stat['position']}) - Team {stat['team_id']}")

        # Passing stats
        if stat['passing_attempts'] > 0:
            print(f"  Passing: {stat['passing_completions']}/{stat['passing_attempts']} "
                  f"for {stat['passing_yards']} yards, "
                  f"{stat['passing_tds']} TDs, {stat['passing_interceptions']} INTs "
                  f"(Rating: {stat['passing_rating']})")

        # Rushing stats
        if stat['rushing_attempts'] > 0:
            print(f"  Rushing: {stat['rushing_attempts']} carries, "
                  f"{stat['rushing_yards']} yards, {stat['rushing_tds']} TDs")

        # Receiving stats
        if stat['receptions'] > 0:
            print(f"  Receiving: {stat['receptions']} rec, "
                  f"{stat['receiving_yards']} yards, {stat['receiving_tds']} TDs")

        # Defensive stats
        if stat['tackles_total'] > 0:
            print(f"  Defense: {stat['tackles_total']} tackles, "
                  f"{stat['sacks']} sacks, {stat['interceptions']} INTs")

        # Kicking stats
        if stat['field_goals_attempted'] > 0:
            print(f"  Kicking: {stat['field_goals_made']}/{stat['field_goals_attempted']} FG, "
                  f"{stat['extra_points_made']}/{stat['extra_points_attempted']} XP")

        print(f"  Fantasy Points: {stat['fantasy_points']}")

    print("\n" + "-" * 80)

    # Insert into database (example)
    print("\n💾 Inserting stats into database...")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # Prepare INSERT statement
        columns = list(mock_stats.player_stats[0].keys())
        placeholders = ', '.join(['?'] * len(columns))
        column_names = ', '.join(columns)

        insert_sql = f"""
            INSERT INTO player_game_stats ({column_names})
            VALUES ({placeholders})
        """

        # Insert all player stats
        for stat in mock_stats.player_stats:
            values = [stat[col] for col in columns]
            cursor.execute(insert_sql, values)

        conn.commit()
        print(f"✅ Successfully inserted {len(mock_stats.player_stats)} player stat records")


def verify_stat_consistency():
    """Verify that generated stats are internally consistent."""

    db_path = "data/database/game_cycle/game_cycle.db"
    dynasty_id = "test_dynasty"

    generator = MockStatsGenerator(db_path, dynasty_id)

    # Generate stats
    mock_stats = generator.generate(
        game_id="consistency_check",
        home_team_id=1,
        away_team_id=2,
        home_score=35,
        away_score=31
    )

    print("\n🔍 Verifying stat consistency...")

    # Group by team
    home_stats = [s for s in mock_stats.player_stats if s['team_id'] == 1]
    away_stats = [s for s in mock_stats.player_stats if s['team_id'] == 2]

    for team_name, team_stats in [("Home", home_stats), ("Away", away_stats)]:
        print(f"\n{team_name} Team:")

        # Get QB passing yards
        qb_stats = [s for s in team_stats if s['position'] == 'QB']
        if qb_stats:
            passing_yards = qb_stats[0]['passing_yards']
            print(f"  QB Passing Yards: {passing_yards}")

            # Sum all receiving yards
            total_receiving = sum(s['receiving_yards'] for s in team_stats)
            print(f"  Total Receiving Yards: {total_receiving}")

            diff = abs(passing_yards - total_receiving)
            status = "✅ MATCH" if diff <= 1 else "❌ MISMATCH"
            print(f"  Consistency Check: {status} (diff: {diff} yards)")

        # Count TDs
        passing_tds = sum(s['passing_tds'] for s in team_stats)
        receiving_tds = sum(s['receiving_tds'] for s in team_stats)
        rushing_tds = sum(s['rushing_tds'] for s in team_stats)

        print(f"  Passing TDs: {passing_tds}")
        print(f"  Receiving TDs: {receiving_tds}")
        print(f"  Rushing TDs: {rushing_tds}")
        print(f"  Total TDs: {passing_tds + rushing_tds}")

        # Check TD consistency (passing TDs should equal receiving TDs)
        td_status = "✅ MATCH" if passing_tds == receiving_tds else "❌ MISMATCH"
        print(f"  TD Consistency: {td_status}")


if __name__ == "__main__":
    print("=" * 80)
    print("Mock Stats Generator Example")
    print("=" * 80)

    # Note: This is an example - update paths/IDs as needed
    # generate_and_insert_mock_stats()

    # Uncomment to run:
    # verify_stat_consistency()

    print("\n💡 To use this example:")
    print("   1. Update db_path and dynasty_id to match your database")
    print("   2. Uncomment the function calls in __main__")
    print("   3. Run: python examples/mock_stats_example.py")
