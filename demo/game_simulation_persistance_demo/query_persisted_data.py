#!/usr/bin/env python3
"""
Query Persisted Data Example

Demonstrates how to query data that was persisted using the demo persistence API.
Shows different query patterns for games, player stats, and standings.
"""

import sys
import sqlite3
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def print_header(title: str, width: int = 80):
    """Print formatted header."""
    print(f"\n{'='*width}")
    print(f"{title.center(width)}")
    print(f"{'='*width}\n")


def query_games(db_path: str, dynasty_id: str = "demo_dynasty"):
    """Query all games for a dynasty."""
    print_header("GAMES")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT game_id, season, week,
               away_team_id, home_team_id,
               away_score, home_score,
               total_plays, game_duration_minutes
        FROM games
        WHERE dynasty_id = ?
        ORDER BY season, week
    """

    cursor.execute(query, (dynasty_id,))
    games = cursor.fetchall()

    if not games:
        print("No games found")
        return

    print(f"Found {len(games)} game(s):")
    print("-" * 80)

    for game in games:
        winner = "Away" if game['away_score'] > game['home_score'] else "Home"
        print(f"Week {game['week']}: Team {game['away_team_id']} @ Team {game['home_team_id']}")
        print(f"  Score: {game['away_score']}-{game['home_score']} (Winner: {winner})")
        print(f"  Total Plays: {game['total_plays']}, Duration: {game['game_duration_minutes']} min")
        print(f"  Game ID: {game['game_id']}")
        print()

    conn.close()


def query_player_stats(db_path: str, dynasty_id: str = "demo_dynasty"):
    """Query top player statistics."""
    print_header("TOP PERFORMERS")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Top passers
    print("🏈 Top Passers:")
    cursor.execute("""
        SELECT player_name, team_id,
               SUM(passing_yards) as total_yards,
               SUM(passing_tds) as total_tds,
               SUM(passing_completions) as completions,
               SUM(passing_attempts) as attempts
        FROM player_game_stats
        WHERE dynasty_id = ? AND passing_attempts > 0
        GROUP BY player_id, player_name, team_id
        ORDER BY total_yards DESC
        LIMIT 5
    """, (dynasty_id,))

    for row in cursor.fetchall():
        comp_pct = (row['completions'] / row['attempts'] * 100) if row['attempts'] > 0 else 0
        print(f"  {row['player_name']} (Team {row['team_id']}): "
              f"{row['total_yards']} yards, {row['total_tds']} TDs, "
              f"{row['completions']}/{row['attempts']} ({comp_pct:.1f}%)")

    # Top rushers
    print("\n🏃 Top Rushers:")
    cursor.execute("""
        SELECT player_name, team_id,
               SUM(rushing_yards) as total_yards,
               SUM(rushing_tds) as total_tds,
               SUM(rushing_attempts) as attempts
        FROM player_game_stats
        WHERE dynasty_id = ? AND rushing_attempts > 0
        GROUP BY player_id, player_name, team_id
        ORDER BY total_yards DESC
        LIMIT 5
    """, (dynasty_id,))

    for row in cursor.fetchall():
        ypc = (row['total_yards'] / row['attempts']) if row['attempts'] > 0 else 0
        print(f"  {row['player_name']} (Team {row['team_id']}): "
              f"{row['total_yards']} yards, {row['total_tds']} TDs, "
              f"{row['attempts']} att ({ypc:.1f} YPC)")

    # Top receivers
    print("\n🎯 Top Receivers:")
    cursor.execute("""
        SELECT player_name, team_id,
               SUM(receiving_yards) as total_yards,
               SUM(receiving_tds) as total_tds,
               SUM(receptions) as catches,
               SUM(targets) as targets
        FROM player_game_stats
        WHERE dynasty_id = ? AND targets > 0
        GROUP BY player_id, player_name, team_id
        ORDER BY total_yards DESC
        LIMIT 5
    """, (dynasty_id,))

    for row in cursor.fetchall():
        catch_pct = (row['catches'] / row['targets'] * 100) if row['targets'] > 0 else 0
        print(f"  {row['player_name']} (Team {row['team_id']}): "
              f"{row['total_yards']} yards, {row['total_tds']} TDs, "
              f"{row['catches']}/{row['targets']} ({catch_pct:.1f}%)")

    conn.close()


def query_standings(db_path: str, dynasty_id: str = "demo_dynasty", season: int = 2024):
    """Query current standings."""
    print_header(f"STANDINGS - {season} Season")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT team_id, wins, losses, ties,
               points_for, points_against,
               home_wins, home_losses,
               away_wins, away_losses
        FROM standings
        WHERE dynasty_id = ? AND season = ?
        ORDER BY wins DESC, points_for DESC
    """

    cursor.execute(query, (dynasty_id, season))
    teams = cursor.fetchall()

    if not teams:
        print("No standings data found")
        return

    print(f"{'Team':<10} {'Record':<12} {'Points For':<12} {'Points Against':<15} {'Home':<10} {'Away':<10}")
    print("-" * 80)

    for team in teams:
        record = f"{team['wins']}-{team['losses']}"
        if team['ties'] > 0:
            record += f"-{team['ties']}"

        point_diff = team['points_for'] - team['points_against']
        home_record = f"{team['home_wins']}-{team['home_losses']}"
        away_record = f"{team['away_wins']}-{team['away_losses']}"

        print(f"Team {team['team_id']:<6} {record:<12} {team['points_for']:<12} "
              f"{team['points_against']:<15} {home_record:<10} {away_record:<10}")

    conn.close()


def query_game_detail(db_path: str, game_id: str):
    """Query detailed stats for a specific game."""
    print_header(f"GAME DETAILS: {game_id}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get game info
    cursor.execute("""
        SELECT * FROM games WHERE game_id = ?
    """, (game_id,))

    game = cursor.fetchone()
    if not game:
        print(f"Game not found: {game_id}")
        return

    print(f"Week {game['week']}, {game['season']}")
    print(f"Team {game['away_team_id']} @ Team {game['home_team_id']}")
    print(f"Final Score: {game['away_score']}-{game['home_score']}")
    print(f"Total Plays: {game['total_plays']}")
    print()

    # Get player stats for this game
    print("Player Statistics:")
    cursor.execute("""
        SELECT player_name, team_id, position,
               passing_yards, passing_tds,
               rushing_yards, rushing_tds,
               receiving_yards, receiving_tds,
               receptions, targets
        FROM player_game_stats
        WHERE game_id = ?
        ORDER BY team_id,
                 (passing_yards + rushing_yards + receiving_yards) DESC
    """, (game_id,))

    players = cursor.fetchall()
    print(f"  {len(players)} players with stats")

    conn.close()


def main():
    """Main query execution."""
    db_path = "demo/game_simulation_persistance_demo/data/demo_events.db"

    print("=" * 80)
    print("DEMO PERSISTENCE DATA QUERY TOOL".center(80))
    print("=" * 80)
    print(f"\nDatabase: {db_path}\n")

    # Query all data
    query_games(db_path)
    query_player_stats(db_path)
    query_standings(db_path)

    print("\n" + "=" * 80)
    print("Query complete!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
