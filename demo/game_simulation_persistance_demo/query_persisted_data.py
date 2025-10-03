#!/usr/bin/env python3
"""
Query Persisted Data Example

Demonstrates how to query data that was persisted using the demo persistence API.
Shows different query patterns for games, player stats, and standings.

UPDATED: Now uses centralized DatabaseAPI instead of raw SQL queries.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from database.api import DatabaseAPI


def print_header(title: str, width: int = 80):
    """Print formatted header."""
    print(f"\n{'='*width}")
    print(f"{title.center(width)}")
    print(f"{'='*width}\n")


def query_games(db_path: str, dynasty_id: str = "demo_dynasty", season: int = 2024):
    """Query all games for a dynasty using DatabaseAPI."""
    print_header("GAMES")

    db_api = DatabaseAPI(db_path)

    # Query all weeks (NFL regular season has 18 weeks)
    all_games = []
    for week in range(1, 19):
        week_games = db_api.get_game_results(dynasty_id, week, season)
        all_games.extend(week_games)

    if not all_games:
        print("No games found")
        return

    print(f"Found {len(all_games)} game(s):")
    print("-" * 80)

    for game in all_games:
        winner = "Away" if game['away_score'] > game['home_score'] else "Home"
        print(f"Week {game['week']}: Team {game['away_team_id']} @ Team {game['home_team_id']}")
        print(f"  Score: {game['away_score']}-{game['home_score']} (Winner: {winner})")
        print(f"  Total Plays: {game.get('total_plays', 'N/A')}, Duration: {game.get('game_duration_minutes', 'N/A')} min")
        print(f"  Game ID: {game['game_id']}")
        print()


def query_player_stats(db_path: str, dynasty_id: str = "demo_dynasty", season: int = 2024):
    """Query top player statistics using DatabaseAPI."""
    print_header("TOP PERFORMERS")

    db_api = DatabaseAPI(db_path)

    # Top passers using DatabaseAPI
    print("🏈 Top Passers:")
    passers = db_api.get_passing_leaders(dynasty_id, season, limit=5)

    for player in passers:
        comp_pct = player.get('completion_percentage', 0)
        print(f"  {player['player_name']} (Team {player['team_id']}): "
              f"{player['total_passing_yards']} yards, {player['total_passing_tds']} TDs, "
              f"{player['total_completions']}/{player['total_attempts']} ({comp_pct:.1f}%)")

    # Top rushers using DatabaseAPI
    print("\n🏃 Top Rushers:")
    rushers = db_api.get_rushing_leaders(dynasty_id, season, limit=5)

    for player in rushers:
        ypc = player.get('yards_per_carry', 0)
        print(f"  {player['player_name']} (Team {player['team_id']}): "
              f"{player['total_rushing_yards']} yards, {player['total_rushing_tds']} TDs, "
              f"{player['total_attempts']} att ({ypc:.1f} YPC)")

    # Top receivers using DatabaseAPI
    print("\n🎯 Top Receivers:")
    receivers = db_api.get_receiving_leaders(dynasty_id, season, limit=5)

    for player in receivers:
        catch_pct = player.get('catch_percentage', 0)
        print(f"  {player['player_name']} (Team {player['team_id']}): "
              f"{player['total_receiving_yards']} yards, {player['total_receiving_tds']} TDs, "
              f"{player['total_receptions']}/{player['total_targets']} ({catch_pct:.1f}%)")


def query_standings(db_path: str, dynasty_id: str = "demo_dynasty", season: int = 2024):
    """Query current standings using DatabaseAPI."""
    print_header(f"STANDINGS - {season} Season")

    db_api = DatabaseAPI(db_path)

    standings_data = db_api.get_standings(dynasty_id, season)

    if not standings_data or not standings_data.get('divisions'):
        print("No standings data found")
        return

    print(f"{'Team':<10} {'Record':<12} {'Points For':<12} {'Points Against':<15} {'Home':<10} {'Away':<10}")
    print("-" * 80)

    # Extract all teams from divisions
    all_teams = []
    for division_name, teams in standings_data['divisions'].items():
        for team_data in teams:
            team_id = team_data.get('team_id')
            standing = team_data.get('standing')
            if standing:
                all_teams.append({
                    'team_id': team_id,
                    'wins': standing.wins,
                    'losses': standing.losses,
                    'ties': standing.ties,
                    'points_for': standing.points_for,
                    'points_against': standing.points_against,
                    'home_wins': standing.home_wins,
                    'home_losses': standing.home_losses,
                    'away_wins': standing.away_wins,
                    'away_losses': standing.away_losses
                })

    # Sort by wins descending, then points for
    all_teams.sort(key=lambda t: (t['wins'], t['points_for']), reverse=True)

    for team in all_teams:
        record = f"{team['wins']}-{team['losses']}"
        if team['ties'] > 0:
            record += f"-{team['ties']}"

        home_record = f"{team['home_wins']}-{team['home_losses']}"
        away_record = f"{team['away_wins']}-{team['away_losses']}"

        print(f"Team {team['team_id']:<6} {record:<12} {team['points_for']:<12} "
              f"{team['points_against']:<15} {home_record:<10} {away_record:<10}")


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
