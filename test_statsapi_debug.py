"""
Debug script to test StatsAPI
"""
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from statistics.stats_api import StatsAPI

DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "3rd"
SEASON = 2025

# Test StatsAPI
print("="*80)
print("TESTING StatsAPI.get_passing_leaders()")
print("="*80)

api = StatsAPI(DB_PATH, DYNASTY_ID)

try:
    leaders = api.get_passing_leaders(SEASON, limit=10)
    print(f"\nReturned {len(leaders)} passing leaders")

    if len(leaders) > 0:
        print(f"\nTop 3 passers:")
        for i, leader in enumerate(leaders[:3], 1):
            print(f"{i}. {leader.player_name}: {leader.yards} yards, {leader.passer_rating:.1f} rating, {leader.interceptions} INTs")
    else:
        print("No passing leaders returned!")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
