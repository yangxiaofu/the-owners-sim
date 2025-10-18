"""
Debug script to trace passing leaders API call
"""
import sys
import os

src_path = os.path.join(os.path.dirname(__file__), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.api import DatabaseAPI

DB_PATH = "data/database/nfl_simulation.db"
DYNASTY_ID = "3rd"
SEASON = 2025

# Test DatabaseAPI directly
print("="*80)
print("TESTING DatabaseAPI.get_passing_leaders() DIRECTLY")
print("="*80)

db_api = DatabaseAPI(DB_PATH)
raw_stats = db_api.get_passing_leaders(DYNASTY_ID, SEASON, limit=10)

print(f"\nReturned {len(raw_stats)} results")
print(f"\nFirst result (if any):")
if len(raw_stats) > 0:
    print(raw_stats[0])
else:
    print("No results returned!")

# Check what's in the raw stats
if len(raw_stats) > 0:
    print(f"\nAll field names in first result:")
    for key in raw_stats[0].keys():
        print(f"  - {key}: {raw_stats[0][key]}")

print("\n" + "="*80)
