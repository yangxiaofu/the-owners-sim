"""
Test StatsAPI with '3rd' dynasty to verify data retrieval.

This script tests all major StatsAPI endpoints to confirm:
1. Database connection is working
2. Data exists for '3rd' dynasty
3. API methods are returning data correctly
"""
import sys
import os

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from statistics.stats_api import StatsAPI

# Test configuration
DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "3rd"
SEASON = 2025

def test_passing_leaders():
    """Test passing leaders API"""
    print("\n" + "="*80)
    print("TESTING PASSING LEADERS")
    print("="*80)

    api = StatsAPI(DB_PATH, DYNASTY_ID)

    try:
        leaders = api.get_passing_leaders(SEASON, limit=10)
        print(f"✓ API call succeeded - Found {len(leaders)} passing leaders")

        if len(leaders) > 0:
            print("\nTop 5 Passers:")
            print(f"{'Rank':<6} {'Player':<25} {'Team':<5} {'Yards':<7} {'TDs':<5} {'Rating':<7}")
            print("-" * 80)
            for i, p in enumerate(leaders[:5], 1):
                print(f"{i:<6} {p.player_name:<25} {p.team_id:<5} {p.yards:<7} {p.touchdowns:<5} {p.passer_rating:<7.1f}")
        else:
            print("✗ No passing leaders found for dynasty='3rd', season=2025")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

def test_rushing_leaders():
    """Test rushing leaders API"""
    print("\n" + "="*80)
    print("TESTING RUSHING LEADERS")
    print("="*80)

    api = StatsAPI(DB_PATH, DYNASTY_ID)

    try:
        leaders = api.get_rushing_leaders(SEASON, limit=10)
        print(f"✓ API call succeeded - Found {len(leaders)} rushing leaders")

        if len(leaders) > 0:
            print("\nTop 5 Rushers:")
            print(f"{'Rank':<6} {'Player':<25} {'Team':<5} {'Yards':<7} {'TDs':<5} {'YPC':<7}")
            print("-" * 80)
            for i, r in enumerate(leaders[:5], 1):
                ypc = r.yards / r.attempts if r.attempts > 0 else 0.0
                print(f"{i:<6} {r.player_name:<25} {r.team_id:<5} {r.yards:<7} {r.touchdowns:<5} {ypc:<7.1f}")
        else:
            print("✗ No rushing leaders found for dynasty='3rd', season=2025")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

def test_receiving_leaders():
    """Test receiving leaders API"""
    print("\n" + "="*80)
    print("TESTING RECEIVING LEADERS")
    print("="*80)

    api = StatsAPI(DB_PATH, DYNASTY_ID)

    try:
        leaders = api.get_receiving_leaders(SEASON, limit=10)
        print(f"✓ API call succeeded - Found {len(leaders)} receiving leaders")

        if len(leaders) > 0:
            print("\nTop 5 Receivers:")
            print(f"{'Rank':<6} {'Player':<25} {'Team':<5} {'Rec':<7} {'Yards':<7} {'TDs':<5}")
            print("-" * 80)
            for i, rec in enumerate(leaders[:5], 1):
                print(f"{i:<6} {rec.player_name:<25} {rec.team_id:<5} {rec.receptions:<7} {rec.yards:<7} {rec.touchdowns:<5}")
        else:
            print("✗ No receiving leaders found for dynasty='3rd', season=2025")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

def test_defensive_leaders():
    """Test defensive leaders API"""
    print("\n" + "="*80)
    print("TESTING DEFENSIVE LEADERS")
    print("="*80)

    api = StatsAPI(DB_PATH, DYNASTY_ID)

    try:
        leaders = api.get_defensive_leaders(SEASON, 'tackles_total', limit=10)
        print(f"✓ API call succeeded - Found {len(leaders)} defensive leaders")

        if len(leaders) > 0:
            print("\nTop 5 Tacklers:")
            print(f"{'Rank':<6} {'Player':<25} {'Team':<5} {'Tackles':<8} {'Sacks':<7} {'INTs':<5}")
            print("-" * 80)
            for i, d in enumerate(leaders[:5], 1):
                print(f"{i:<6} {d.player_name:<25} {d.team_id:<5} {d.tackles_total:<8} {d.sacks:<7.1f} {d.interceptions:<5}")
        else:
            print("✗ No defensive leaders found for dynasty='3rd', season=2025")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

def test_special_teams_leaders():
    """Test special teams leaders API"""
    print("\n" + "="*80)
    print("TESTING SPECIAL TEAMS LEADERS")
    print("="*80)

    api = StatsAPI(DB_PATH, DYNASTY_ID)

    try:
        leaders = api.get_special_teams_leaders(SEASON, limit=10)
        print(f"✓ API call succeeded - Found {len(leaders)} special teams leaders")

        if len(leaders) > 0:
            print("\nTop 5 Kickers:")
            print(f"{'Rank':<6} {'Player':<25} {'Team':<5} {'FGM/FGA':<12} {'FG%':<7} {'Long':<5}")
            print("-" * 80)
            for i, k in enumerate(leaders[:5], 1):
                fg_pct = (k.fg_made / k.fg_attempts * 100) if k.fg_attempts > 0 else 0.0
                print(f"{i:<6} {k.player_name:<25} {k.team_id:<5} {k.fg_made}/{k.fg_attempts:<8} {fg_pct:<7.1f} {k.fg_longest:<5}")
        else:
            print("✗ No special teams leaders found for dynasty='3rd', season=2025")

    except Exception as e:
        print(f"✗ API call failed: {e}")
        import traceback
        traceback.print_exc()

def test_raw_database_query():
    """Test raw database query to see if any data exists"""
    print("\n" + "="*80)
    print("TESTING RAW DATABASE QUERY")
    print("="*80)

    import sqlite3

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if player_game_stats table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_game_stats'")
        table_exists = cursor.fetchone()

        if table_exists:
            print("✓ player_game_stats table exists")

            # Count total rows
            cursor.execute("SELECT COUNT(*) FROM player_game_stats")
            total_rows = cursor.fetchone()[0]
            print(f"✓ Total rows in player_game_stats: {total_rows}")

            # Count rows for '3rd' dynasty
            cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE dynasty_id = ?", (DYNASTY_ID,))
            dynasty_rows = cursor.fetchone()[0]
            print(f"✓ Rows for dynasty='3rd': {dynasty_rows}")

            # Count rows for '3rd' dynasty and season 2025
            cursor.execute("SELECT COUNT(*) FROM player_game_stats WHERE dynasty_id = ? AND season = ?", (DYNASTY_ID, SEASON))
            season_rows = cursor.fetchone()[0]
            print(f"✓ Rows for dynasty='3rd', season=2025: {season_rows}")

            # Check all dynasties
            cursor.execute("SELECT DISTINCT dynasty_id FROM player_game_stats")
            dynasties = cursor.fetchall()
            print(f"\nAvailable dynasties: {[d[0] for d in dynasties]}")

            # Check all seasons for '3rd' dynasty
            cursor.execute("SELECT DISTINCT season FROM player_game_stats WHERE dynasty_id = ?", (DYNASTY_ID,))
            seasons = cursor.fetchall()
            print(f"Available seasons for '3rd' dynasty: {[s[0] for s in seasons]}")

            if season_rows == 0:
                print("\n✗ NO DATA FOUND for dynasty='3rd', season=2025")
                print("This is why stats are not showing up in the UI!")
            else:
                print(f"\n✓ Found {season_rows} player stat records for dynasty='3rd', season=2025")

        else:
            print("✗ player_game_stats table does not exist!")

        conn.close()

    except Exception as e:
        print(f"✗ Database query failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n" + "="*80)
    print("STATS API DIAGNOSTIC TEST - Dynasty '3rd', Season 2025")
    print("="*80)

    # Test raw database first
    test_raw_database_query()

    # Test all API endpoints
    test_passing_leaders()
    test_rushing_leaders()
    test_receiving_leaders()
    test_defensive_leaders()
    test_special_teams_leaders()

    print("\n" + "="*80)
    print("DIAGNOSTIC TEST COMPLETE")
    print("="*80)
