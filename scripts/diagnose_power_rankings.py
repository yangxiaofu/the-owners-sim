#!/usr/bin/env python3
"""
Diagnostic script for power rankings issues.

Queries the database to check:
- Standings data existence
- Power rankings data existence
- Dynasty isolation integrity
- Data consistency

Usage:
    PYTHONPATH=src python scripts/diagnose_power_rankings.py [dynasty_id] [season]

If no arguments provided, shows all dynasties and their data.
"""

import sqlite3
import sys
from pathlib import Path
from typing import Optional


def diagnose_power_rankings(dynasty_id: Optional[str] = None, season: Optional[int] = None):
    """
    Diagnose power rankings data in the database.

    Args:
        dynasty_id: Optional dynasty ID to filter by
        season: Optional season to filter by
    """
    db_path = Path("data/database/game_cycle/game_cycle.db")

    if not db_path.exists():
        print(f"❌ Database not found: {db_path}")
        return

    print(f"🔍 Diagnosing Power Rankings")
    print(f"Database: {db_path}")
    print("=" * 80)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 1. Check dynasties
        print("\n📊 DYNASTIES:")
        cursor.execute("SELECT DISTINCT dynasty_id FROM dynasty_state")
        dynasties = [row[0] for row in cursor.fetchall()]

        if not dynasties:
            print("  ❌ No dynasties found in database")
            return

        print(f"  Found {len(dynasties)} dynasties:")
        for d in dynasties:
            print(f"    - {d}")

        # Filter by dynasty if specified
        target_dynasties = [dynasty_id] if dynasty_id else dynasties

        for dyn_id in target_dynasties:
            print(f"\n{'=' * 80}")
            print(f"Dynasty: {dyn_id}")
            print(f"{'=' * 80}")

            # 2. Check standings
            print("\n📈 STANDINGS:")
            if season:
                cursor.execute(
                    "SELECT season, COUNT(*) FROM standings WHERE dynasty_id = ? AND season = ? GROUP BY season",
                    (dyn_id, season)
                )
            else:
                cursor.execute(
                    "SELECT season, COUNT(*) FROM standings WHERE dynasty_id = ? GROUP BY season ORDER BY season",
                    (dyn_id,)
                )

            standings_data = cursor.fetchall()

            if not standings_data:
                print(f"  ❌ No standings found for dynasty {dyn_id}")
            else:
                print(f"  Found standings for {len(standings_data)} seasons:")
                for s, count in standings_data:
                    status = "✅" if count == 32 else f"⚠️  ({count} teams, expected 32)"
                    print(f"    Season {s}: {count} teams {status}")

                    # Show sample teams for first season
                    if s == standings_data[0][0]:
                        cursor.execute(
                            """SELECT team_id, wins, losses
                               FROM standings
                               WHERE dynasty_id = ? AND season = ?
                               ORDER BY wins DESC, losses ASC
                               LIMIT 3""",
                            (dyn_id, s)
                        )
                        sample_teams = cursor.fetchall()
                        if sample_teams:
                            print(f"      Sample teams:")
                            for team_id, wins, losses in sample_teams:
                                print(f"        Team {team_id}: {wins}-{losses}")

            # 3. Check power rankings
            print("\n🏆 POWER RANKINGS:")
            if season:
                cursor.execute(
                    "SELECT season, week, COUNT(*) FROM power_rankings WHERE dynasty_id = ? AND season = ? GROUP BY season, week ORDER BY week",
                    (dyn_id, season)
                )
            else:
                cursor.execute(
                    "SELECT season, week, COUNT(*) FROM power_rankings WHERE dynasty_id = ? GROUP BY season, week ORDER BY season, week",
                    (dyn_id,)
                )

            rankings_data = cursor.fetchall()

            if not rankings_data:
                print(f"  ❌ No power rankings found for dynasty {dyn_id}")
            else:
                print(f"  Found power rankings for {len(rankings_data)} weeks:")
                by_season = {}
                for s, w, count in rankings_data:
                    if s not in by_season:
                        by_season[s] = []
                    status = "✅" if count == 32 else f"⚠️  ({count} teams)"
                    by_season[s].append((w, count, status))

                for s, weeks in by_season.items():
                    print(f"    Season {s}: {len(weeks)} weeks")
                    for w, count, status in weeks[:5]:  # Show first 5 weeks
                        print(f"      Week {w}: {count} teams {status}")
                    if len(weeks) > 5:
                        print(f"      ... and {len(weeks) - 5} more weeks")

                    # Show sample ranking for first week of season
                    first_week = weeks[0][0]
                    cursor.execute(
                        """SELECT team_id, rank, tier, blurb
                           FROM power_rankings
                           WHERE dynasty_id = ? AND season = ? AND week = ?
                           ORDER BY rank
                           LIMIT 3""",
                        (dyn_id, s, first_week)
                    )
                    sample_rankings = cursor.fetchall()
                    if sample_rankings:
                        print(f"      Sample rankings (Week {first_week}):")
                        for team_id, rank, tier, blurb in sample_rankings:
                            blurb_preview = blurb[:50] + "..." if blurb and len(blurb) > 50 else (blurb or "No blurb")
                            print(f"        #{rank}. Team {team_id} ({tier}): {blurb_preview}")

            # 4. Check for mismatches
            print("\n🔍 CONSISTENCY CHECKS:")
            if season:
                cursor.execute(
                    """SELECT s.season, COUNT(DISTINCT s.team_id) as standings_teams,
                              (SELECT COUNT(DISTINCT team_id)
                               FROM power_rankings pr
                               WHERE pr.dynasty_id = s.dynasty_id
                               AND pr.season = s.season
                               AND pr.week = 1) as rankings_teams
                       FROM standings s
                       WHERE s.dynasty_id = ? AND s.season = ?
                       GROUP BY s.season""",
                    (dyn_id, season)
                )
            else:
                cursor.execute(
                    """SELECT s.season, COUNT(DISTINCT s.team_id) as standings_teams,
                              (SELECT COUNT(DISTINCT team_id)
                               FROM power_rankings pr
                               WHERE pr.dynasty_id = s.dynasty_id
                               AND pr.season = s.season
                               AND pr.week = 1) as rankings_teams
                       FROM standings s
                       WHERE s.dynasty_id = ?
                       GROUP BY s.season""",
                    (dyn_id,)
                )

            consistency_data = cursor.fetchall()
            if consistency_data:
                for s, standings_count, rankings_count in consistency_data:
                    if standings_count == 32 and rankings_count == 32:
                        print(f"  ✅ Season {s}: {standings_count} teams in standings, {rankings_count} teams in rankings (Week 1)")
                    elif standings_count != 32:
                        print(f"  ⚠️  Season {s}: {standings_count} teams in standings (expected 32)")
                    elif rankings_count != 32:
                        print(f"  ⚠️  Season {s}: {standings_count} teams in standings, but {rankings_count} teams in rankings (Week 1)")

        # 5. Summary
        print(f"\n{'=' * 80}")
        print("SUMMARY:")
        print(f"{'=' * 80}")

        cursor.execute("SELECT COUNT(*) FROM standings WHERE dynasty_id IN ({})".format(
            ','.join('?' * len(target_dynasties))
        ), target_dynasties)
        total_standings = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM power_rankings WHERE dynasty_id IN ({})".format(
            ','.join('?' * len(target_dynasties))
        ), target_dynasties)
        total_rankings = cursor.fetchone()[0]

        print(f"Total standings records: {total_standings}")
        print(f"Total power rankings records: {total_rankings}")

        if total_standings > 0 and total_rankings == 0:
            print("\n⚠️  ISSUE DETECTED:")
            print("Standings exist but NO power rankings found.")
            print("This suggests power rankings generation is failing.")
            print("Check application logs for errors during week simulation.")
        elif total_standings == 0:
            print("\n⚠️  ISSUE DETECTED:")
            print("No standings data found.")
            print("Games may not have been simulated yet.")
        elif total_rankings > 0:
            print("\n✅ Power rankings data exists in database.")
            print("If not displaying in UI, check:")
            print("  1. Dynasty ID matches between save and query")
            print("  2. Week calculation logic in MediaCoverageView")
            print("  3. Application logs for query errors")

    finally:
        conn.close()


if __name__ == "__main__":
    dynasty_id = sys.argv[1] if len(sys.argv) > 1 else None
    season = int(sys.argv[2]) if len(sys.argv) > 2 else None

    diagnose_power_rankings(dynasty_id, season)