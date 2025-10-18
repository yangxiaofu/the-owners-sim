"""
Debug script to trace leaderboard builder
"""
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.api import DatabaseAPI
from statistics.leaderboards import LeaderboardBuilder

DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "3rd"
SEASON = 2025

# Test LeaderboardBuilder
print("="*80)
print("TESTING LeaderboardBuilder.build_passing_leaderboard()")
print("="*80)

db_api = DatabaseAPI(DB_PATH)
builder = LeaderboardBuilder(db_api)

try:
    leaders = builder.build_passing_leaderboard(DYNASTY_ID, SEASON, limit=10)
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
