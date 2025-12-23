"""
Simple validation script for TeamContextBuilder.

Tests the service with a minimal database to verify core functionality.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.services.team_context_builder import (
    TeamContextBuilder,
    PlayoffPosition,
    SeasonPhase
)


def create_test_database(db_path: str):
    """Create minimal test database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS standings (
            dynasty_id TEXT,
            team_id INTEGER,
            season INTEGER,
            season_type TEXT DEFAULT 'regular_season',
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            division_ties INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            conference_ties INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            home_ties INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            away_ties INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            point_differential INTEGER DEFAULT 0,
            made_playoffs BOOLEAN DEFAULT 0,
            made_wild_card BOOLEAN DEFAULT 0,
            won_wild_card BOOLEAN DEFAULT 0,
            won_division_round BOOLEAN DEFAULT 0,
            won_conference BOOLEAN DEFAULT 0,
            won_super_bowl BOOLEAN DEFAULT 0,
            PRIMARY KEY (dynasty_id, team_id, season, season_type)
        );

        CREATE TABLE IF NOT EXISTS box_scores (
            dynasty_id TEXT,
            season INTEGER,
            week INTEGER,
            home_team_id INTEGER,
            away_team_id INTEGER,
            home_score INTEGER,
            away_score INTEGER,
            game_status TEXT DEFAULT 'final',
            PRIMARY KEY (dynasty_id, season, week, home_team_id, away_team_id)
        );

        CREATE TABLE IF NOT EXISTS player_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT,
            season INTEGER,
            transaction_type TEXT,
            player_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transaction_date TEXT,
            details TEXT
        );
    """)
    conn.commit()
    return conn


def test_basic_context():
    """Test basic context building."""
    print("=" * 60)
    print("TEST 1: Basic Context Building")
    print("=" * 60)

    db_path = "/tmp/test_team_context.db"
    conn = create_test_database(db_path)

    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22  # Detroit Lions

    # Insert standings for Lions
    conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 10, 4, 0, 350, 280, 70)
    """, (dynasty_id, team_id, season))
    conn.commit()

    # Build context
    db = GameCycleDatabase(db_path)
    builder = TeamContextBuilder(db)
    context = builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=10
    )

    # Verify
    print(f"✓ Team: {context.team_name} (ID: {context.team_id})")
    print(f"✓ Record: {context.get_record_string()} (Win%: {context.win_pct:.3f})")
    print(f"✓ Division Rank: {context.division_rank}")
    print(f"✓ Conference Rank: {context.conference_rank}")
    print(f"✓ Playoff Position: {context.playoff_position.value}")
    print(f"✓ Season Phase: {context.season_phase.value}")
    print(f"✓ Streak: {context.get_streak_string() or 'No streak'}")

    assert context.team_id == team_id
    assert context.wins == 10
    assert context.losses == 4
    assert context.season == season
    print("\n✅ Test 1 PASSED\n")

    conn.close()


def test_division_ranking():
    """Test division rank calculation."""
    print("=" * 60)
    print("TEST 2: Division Ranking")
    print("=" * 60)

    db_path = "/tmp/test_team_context2.db"
    conn = create_test_database(db_path)

    dynasty_id = "test_dynasty"
    season = 2025

    # NFC North standings (21-24: Bears, Lions, Packers, Vikings)
    teams = [
        (22, 12, 2, "Lions"),    # 1st
        (23, 10, 4, "Packers"),  # 2nd
        (24, 8, 6, "Vikings"),   # 3rd
        (21, 5, 9, "Bears")      # 4th
    ]

    for team_id, wins, losses, name in teams:
        conn.execute("""
            INSERT INTO standings (
                dynasty_id, team_id, season, season_type,
                wins, losses, ties,
                points_for, points_against,
                point_differential
            ) VALUES (?, ?, ?, 'regular_season', ?, ?, 0, ?, ?, ?)
        """, (
            dynasty_id, team_id, season,
            wins, losses,
            wins * 24 + 100,
            losses * 24 + 100,
            (wins - losses) * 24
        ))
    conn.commit()

    db = GameCycleDatabase(db_path)
    builder = TeamContextBuilder(db)

    # Test each team
    for team_id, wins, losses, name in teams:
        context = builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=14
        )
        print(f"✓ {name}: Rank {context.division_rank} ({wins}-{losses})")

    # Verify Lions are 1st
    lions_context = builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=22,
        week=14
    )
    assert lions_context.division_rank == 1, "Lions should be rank 1"

    print("\n✅ Test 2 PASSED\n")
    conn.close()


def test_win_streak():
    """Test win streak calculation."""
    print("=" * 60)
    print("TEST 3: Win Streak")
    print("=" * 60)

    db_path = "/tmp/test_team_context3.db"
    conn = create_test_database(db_path)

    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    # Insert standings
    conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 6, 2, 0, 240, 160, 80)
    """, (dynasty_id, team_id, season))

    # Create 3-game win streak
    games = [
        (6, 24, 20),  # Win
        (7, 27, 17),  # Win
        (8, 31, 21)   # Win (most recent)
    ]

    for week, home_score, away_score in games:
        conn.execute("""
            INSERT INTO box_scores (
                dynasty_id, season, week,
                home_team_id, away_team_id,
                home_score, away_score,
                game_status
            ) VALUES (?, ?, ?, ?, 23, ?, ?, 'final')
        """, (dynasty_id, season, week, team_id, home_score, away_score))
    conn.commit()

    db = GameCycleDatabase(db_path)
    builder = TeamContextBuilder(db)
    context = builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=8
    )

    print(f"✓ Streak: {context.get_streak_string()}")
    print(f"✓ Streak Count: {context.current_streak}")
    print(f"✓ Streak Type: {context.streak_type}")

    assert context.current_streak == 3, "Should have 3-game streak"
    assert context.streak_type == 'W', "Should be win streak"
    assert context.get_streak_string() == 'W3', "Streak string should be W3"

    print("\n✅ Test 3 PASSED\n")
    conn.close()


def test_season_phases():
    """Test season phase determination."""
    print("=" * 60)
    print("TEST 4: Season Phases")
    print("=" * 60)

    db_path = "/tmp/test_team_context4.db"
    conn = create_test_database(db_path)

    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 8, 8, 0, 300, 300, 0)
    """, (dynasty_id, team_id, season))
    conn.commit()

    db = GameCycleDatabase(db_path)
    builder = TeamContextBuilder(db)

    # Test different weeks
    test_cases = [
        (3, SeasonPhase.EARLY, "Early season"),
        (10, SeasonPhase.MID, "Mid season"),
        (16, SeasonPhase.LATE, "Late season"),
        (None, SeasonPhase.PLAYOFFS, "Playoffs")
    ]

    for week, expected_phase, description in test_cases:
        context = builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=week
        )
        print(f"✓ Week {week or 'N/A'}: {context.season_phase.value} ({description})")
        assert context.season_phase == expected_phase, f"Week {week} should be {expected_phase}"

    print("\n✅ Test 4 PASSED\n")
    conn.close()


def test_recent_activity():
    """Test recent activity tracking."""
    print("=" * 60)
    print("TEST 5: Recent Activity")
    print("=" * 60)

    db_path = "/tmp/test_team_context5.db"
    conn = create_test_database(db_path)

    dynasty_id = "test_dynasty"
    season = 2025
    team_id = 22

    conn.execute("""
        INSERT INTO standings (
            dynasty_id, team_id, season, season_type,
            wins, losses, ties,
            points_for, points_against,
            point_differential
        ) VALUES (?, ?, ?, 'regular_season', 8, 8, 0, 300, 300, 0)
    """, (dynasty_id, team_id, season))

    # Add recent trade (5 days ago)
    recent_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
    conn.execute("""
        INSERT INTO player_transactions (
            dynasty_id, season, transaction_type,
            player_id, first_name, last_name, position,
            from_team_id, to_team_id, transaction_date
        ) VALUES (?, ?, 'TRADE', 12345, 'John', 'Smith', 'WR', ?, 23, ?)
    """, (dynasty_id, season, team_id, recent_date))

    # Add old trade (30 days ago - should be excluded)
    old_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    conn.execute("""
        INSERT INTO player_transactions (
            dynasty_id, season, transaction_type,
            player_id, first_name, last_name, position,
            from_team_id, to_team_id, transaction_date
        ) VALUES (?, ?, 'TRADE', 67890, 'Jane', 'Doe', 'QB', ?, 24, ?)
    """, (dynasty_id, season, team_id, old_date))

    conn.commit()

    db = GameCycleDatabase(db_path)
    builder = TeamContextBuilder(db)
    context = builder.build_context(
        dynasty_id=dynasty_id,
        season=season,
        team_id=team_id,
        week=10
    )

    print(f"✓ Recent trades: {len(context.recent_trades)}")
    print(f"✓ Has recent activity: {context.has_recent_activity()}")

    if context.recent_trades:
        trade = context.recent_trades[0]
        print(f"  - Player: {trade['player_name']} ({trade['position']})")
        print(f"  - Type: {trade['type']}")

    assert len(context.recent_trades) == 1, "Should have 1 recent trade"
    assert context.recent_trades[0]['player_name'] == 'John Smith'
    assert context.has_recent_activity() is True

    print("\n✅ Test 5 PASSED\n")
    conn.close()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TeamContextBuilder Validation Tests")
    print("=" * 60 + "\n")

    try:
        test_basic_context()
        test_division_ranking()
        test_win_streak()
        test_season_phases()
        test_recent_activity()

        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TEST FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
