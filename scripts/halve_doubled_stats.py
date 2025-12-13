#!/usr/bin/env python3
"""
Halve Doubled Stats Script

Fixes stats that were doubled BEFORE insertion into the database.
This affects games played before the duplicate detection fix was implemented.

Usage:
    python scripts/halve_doubled_stats.py [db_path]

If no path is provided, uses the default game cycle database.
"""

import sqlite3
import sys
from pathlib import Path


def halve_doubled_stats(db_path: str, cutoff_date: str = None):
    """
    Halve all player stat values for games with doubled stats.

    Args:
        db_path: Path to database file
        cutoff_date: Optional game_id cutoff (e.g., 'game_20251201')
                    Only games BEFORE this will be halved
    """

    print(f"\n🔍 Opening database: {db_path}")

    if not Path(db_path).exists():
        print(f"❌ Error: Database file not found: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Count total rows before
        cursor.execute("SELECT COUNT(*) FROM player_game_stats")
        total_before = cursor.fetchone()[0]
        print(f"📊 Total rows in database: {total_before:,}")

        # Build WHERE clause for cutoff
        where_clause = ""
        params = []
        if cutoff_date:
            where_clause = "WHERE game_id < ?"
            params.append(cutoff_date)

            cursor.execute(f"SELECT COUNT(*) FROM player_game_stats {where_clause}", params)
            affected_rows = cursor.fetchone()[0]
            print(f"📅 Rows matching cutoff (<{cutoff_date}): {affected_rows:,}")
        else:
            print("⚠️  No cutoff specified - will halve ALL games!")
            affected_rows = total_before

        # Show sample of current values (before halving)
        print("\n📋 Sample stats BEFORE halving:")
        cursor.execute(f"""
            SELECT player_name, position, passing_tds, passing_yards, rushing_tds, rushing_yards
            FROM player_game_stats
            {where_clause}
            AND (passing_attempts > 0 OR rushing_attempts > 0)
            ORDER BY passing_tds DESC, rushing_tds DESC
            LIMIT 5
        """, params)

        for row in cursor.fetchall():
            print(f"   {row[0]:20} ({row[1]:3}) - Pass: {row[2]:2} TDs, {row[3]:4} yds | Rush: {row[4]:2} TDs, {row[5]:4} yds")

        # Confirm before halving
        if affected_rows == 0:
            print("\n✅ No rows to update")
            conn.close()
            return True

        response = input(f"\n❓ Halve stats for {affected_rows:,} rows? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Halving cancelled by user")
            conn.close()
            return False

        # Halve all stat values
        print("\n➗ Halving stats...")

        update_query = f"""
            UPDATE player_game_stats
            SET
                -- Passing stats
                passing_yards = passing_yards / 2,
                passing_tds = passing_tds / 2,
                passing_attempts = passing_attempts / 2,
                passing_completions = passing_completions / 2,
                passing_interceptions = passing_interceptions / 2,
                passing_sacks = passing_sacks / 2,
                passing_sack_yards = passing_sack_yards / 2,
                air_yards = air_yards / 2,

                -- Rushing stats
                rushing_yards = rushing_yards / 2,
                rushing_tds = rushing_tds / 2,
                rushing_attempts = rushing_attempts / 2,
                rushing_fumbles = rushing_fumbles / 2,
                -- rushing_long is MAX, don't halve

                -- Receiving stats
                receiving_yards = receiving_yards / 2,
                receiving_tds = receiving_tds / 2,
                receptions = receptions / 2,
                targets = targets / 2,
                receiving_drops = receiving_drops / 2,
                yards_after_catch = yards_after_catch / 2,
                -- receiving_long is MAX, don't halve

                -- Defensive stats
                tackles_total = tackles_total / 2,
                tackles_solo = tackles_solo / 2,
                tackles_assist = tackles_assist / 2,
                sacks = sacks / 2.0,
                interceptions = interceptions / 2,
                forced_fumbles = forced_fumbles / 2,
                fumbles_recovered = fumbles_recovered / 2,
                passes_defended = passes_defended / 2,
                tackles_for_loss = tackles_for_loss / 2,
                qb_hits = qb_hits / 2,
                qb_pressures = qb_pressures / 2,

                -- Special teams stats
                field_goals_made = field_goals_made / 2,
                field_goals_attempted = field_goals_attempted / 2,
                extra_points_made = extra_points_made / 2,
                extra_points_attempted = extra_points_attempted / 2,
                punts = punts / 2,
                punt_yards = punt_yards / 2,

                -- O-Line stats
                pass_blocks = pass_blocks / 2,
                pancakes = pancakes / 2,
                sacks_allowed = sacks_allowed / 2,
                hurries_allowed = hurries_allowed / 2,
                pressures_allowed = pressures_allowed / 2,
                missed_assignments = missed_assignments / 2,
                holding_penalties = holding_penalties / 2,
                false_start_penalties = false_start_penalties / 2,
                downfield_blocks = downfield_blocks / 2,
                double_team_blocks = double_team_blocks / 2,
                chip_blocks = chip_blocks / 2,

                -- Performance metrics
                snap_counts_offense = snap_counts_offense / 2,
                snap_counts_defense = snap_counts_defense / 2,
                snap_counts_special_teams = snap_counts_special_teams / 2,

                fantasy_points = fantasy_points / 2.0
            {where_clause}
        """

        cursor.execute(update_query, params)
        updated_count = cursor.rowcount
        conn.commit()

        print(f"✅ Updated {updated_count:,} rows")

        # Show sample of values AFTER halving
        print("\n📋 Sample stats AFTER halving:")
        cursor.execute(f"""
            SELECT player_name, position, passing_tds, passing_yards, rushing_tds, rushing_yards
            FROM player_game_stats
            {where_clause}
            AND (passing_attempts > 0 OR rushing_attempts > 0)
            ORDER BY passing_tds DESC, rushing_tds DESC
            LIMIT 5
        """, params)

        for row in cursor.fetchall():
            print(f"   {row[0]:20} ({row[1]:3}) - Pass: {row[2]:2} TDs, {row[3]:4} yds | Rush: {row[4]:2} TDs, {row[5]:4} yds")

        print(f"\n🎉 Success! Halved stats for {updated_count:,} rows")

        conn.close()
        return True

    except Exception as e:
        print(f"\n❌ Error during halving: {e}")
        print("\nRolling back changes...")
        conn.rollback()
        conn.close()
        return False


if __name__ == "__main__":
    # Default database path
    default_db_path = "data/database/game_cycle/game_cycle.db"

    # Allow custom path from command line
    db_path = sys.argv[1] if len(sys.argv) > 1 else default_db_path

    # Optional cutoff date (only halve games before this)
    cutoff = sys.argv[2] if len(sys.argv) > 2 else None

    print("=" * 70)
    print("     HALVE DOUBLED STATS SCRIPT")
    print("=" * 70)
    print("\n⚠️  This will HALVE all stat values for affected games!")
    print("   Use this to fix games where stats were doubled before insertion.")

    if cutoff:
        print(f"\n📅 Cutoff: Only games before {cutoff} will be affected")
    else:
        print("\n⚠️  NO CUTOFF: ALL games will be affected!")
        print("   Consider passing a cutoff date as 2nd argument:")
        print("   python scripts/halve_doubled_stats.py [db_path] game_20251201")

    success = halve_doubled_stats(db_path, cutoff)

    if success:
        print("\n✅ Script completed successfully")
        print("\n💡 Next steps:")
        print("   1. Check Box Score dialog - stats should match play-by-play")
        print("   2. Simulate a new game - verify stats aren't doubled")
        print("   3. If still doubled, run safeguard fix")
        sys.exit(0)
    else:
        print("\n❌ Script completed with errors")
        sys.exit(1)
