"""
Integration tests for the complete Player Popularity System.

Tests the end-to-end flow including:
- Database layer (PopularityAPI)
- Service layer (PopularityCalculator)
- Integration hooks (headline generation, awards, social posts)

Covers all 10 required scenarios:
1. Breakout game performance → Popularity spike
2. MVP race leader → Sustained high popularity
3. Injury → Gradual decay
4. Trade to big market → Popularity boost
5. Award announcement → Immediate jump
6. Small market vs big market comparison
7. Rookie draft → Initial popularity
8. Playoff performance → 1.5x boost
9. Full season popularity trajectory
10. Dynasty isolation

CURRENT STATUS:
- 3/10 tests passing (Injury Decay, Rookie Draft, Dynasty Isolation)
- 7/10 tests failing due to missing/incomplete schema tables:
  * headlines table (media_coverage_api dependency)
  * awards/award_nominees tables (different column names in production)
  * Social posts tables (not yet in game_cycle schema)

These tests demonstrate proper integration testing patterns:
- Real database setup with actual SQL schema
- Proper fixtures for data setup
- Helper functions for common operations
- Dynasty isolation verification
- End-to-end service → API → database flow testing

To make all tests pass:
1. Add missing tables to game_cycle test schema
2. Align column names with production schema
3. Ensure all service dependencies are available
"""

import json
import pytest
import sqlite3
import tempfile
import os
from pathlib import Path
from typing import Dict, List


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def test_dynasty_id():
    """Standard dynasty ID for testing."""
    return "test_dynasty_popularity"


@pytest.fixture
def test_season():
    """Standard season year for testing."""
    return 2025


@pytest.fixture
def game_cycle_db(test_dynasty_id, test_season):
    """
    Create game cycle database with full schema + popularity tables.

    Sets up:
    - Full game_cycle schema from full_schema.sql
    - Popularity tables (player_popularity, player_popularity_events)
    - Test dynasty
    - Sample players with grades
    - Sample teams data
    """
    # Create temporary database
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Load full schema
    schema_path = Path(__file__).parent.parent.parent.parent / "src" / "game_cycle" / "database" / "full_schema.sql"
    with open(schema_path) as f:
        conn.executescript(f.read())

    # Add missing tables needed for popularity tests
    conn.executescript("""
        -- Analytics tables (stub for testing)
        CREATE TABLE IF NOT EXISTS analytics_player_season_grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            position TEXT NOT NULL,
            overall_grade REAL DEFAULT 0.0,
            offense_grade REAL DEFAULT 0.0,
            defense_grade REAL DEFAULT 0.0,
            special_teams_grade REAL DEFAULT 0.0,
            games_played INTEGER DEFAULT 0,
            snaps_played INTEGER DEFAULT 0,
            UNIQUE(dynasty_id, player_id, season)
        );

        -- Player Popularity Scores
        CREATE TABLE IF NOT EXISTS player_popularity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            popularity_score REAL NOT NULL CHECK(popularity_score BETWEEN 0 AND 100),
            performance_score REAL NOT NULL CHECK(performance_score BETWEEN 0 AND 100),
            visibility_multiplier REAL NOT NULL CHECK(visibility_multiplier BETWEEN 0.5 AND 3.0),
            market_multiplier REAL NOT NULL CHECK(market_multiplier BETWEEN 0.8 AND 2.0),
            week_change REAL,
            trend TEXT CHECK(trend IN ('RISING', 'FALLING', 'STABLE')),
            tier TEXT NOT NULL CHECK(tier IN ('TRANSCENDENT', 'STAR', 'KNOWN', 'ROLE_PLAYER', 'UNKNOWN')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dynasty_id, player_id, season, week)
        );

        CREATE INDEX IF NOT EXISTS idx_player_popularity_lookup
        ON player_popularity(dynasty_id, player_id, season, week);

        CREATE INDEX IF NOT EXISTS idx_player_popularity_leaderboard
        ON player_popularity(dynasty_id, season, week, popularity_score DESC);

        -- Player Popularity Events (audit trail)
        CREATE TABLE IF NOT EXISTS player_popularity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            player_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            impact REAL NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_player_popularity_events_lookup
        ON player_popularity_events(dynasty_id, player_id, season, week);
    """)

    # Create test dynasty
    conn.execute(
        """INSERT INTO dynasties (dynasty_id, dynasty_name, team_id, season_year)
           VALUES (?, 'Test Dynasty Popularity', 1, ?)""",
        (test_dynasty_id, test_season)
    )

    # Create standings for all teams (needed for team success calculations)
    standings_data = []
    for team_id in range(1, 33):
        wins = 10  # Default middle-of-pack record
        losses = 8
        standings_data.append({
            "dynasty_id": test_dynasty_id,
            "season": test_season,
            "team_id": team_id,
            "wins": wins,
            "losses": losses,
            "ties": 0,
            "points_for": wins * 24,
            "points_against": losses * 24,
        })

    conn.executemany(
        """INSERT INTO standings (
               dynasty_id, season, team_id, wins, losses, ties,
               points_for, points_against
           ) VALUES (
               :dynasty_id, :season, :team_id, :wins, :losses, :ties,
               :points_for, :points_against
           )""",
        standings_data,
    )

    conn.commit()

    yield (db_path, conn)

    conn.close()
    try:
        os.unlink(db_path)
    except:
        pass


@pytest.fixture
def popularity_api(game_cycle_db):
    """Create PopularityAPI instance."""
    import sys
    from pathlib import Path
    from unittest.mock import MagicMock

    # Add src to path
    src_path = Path(__file__).parent.parent.parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Mock out the broken import chain temporarily
    sys.modules['persistence.transaction_logger'] = MagicMock()
    sys.modules['utils.player_field_extractors'] = MagicMock()

    # Now import the modules
    from game_cycle.database.popularity_api import PopularityAPI
    from game_cycle.database.connection import GameCycleDatabase

    db_path, _ = game_cycle_db
    db = GameCycleDatabase(db_path)
    return PopularityAPI(db)


@pytest.fixture
def popularity_calculator(game_cycle_db, test_dynasty_id):
    """Create PopularityCalculator service."""
    import sys
    from pathlib import Path
    from unittest.mock import MagicMock

    # Add src to path
    src_path = Path(__file__).parent.parent.parent.parent / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Mock out the broken import chain temporarily
    sys.modules['persistence.transaction_logger'] = MagicMock()
    sys.modules['utils.player_field_extractors'] = MagicMock()

    # Now import the modules
    from game_cycle.services.popularity_calculator import PopularityCalculator
    from game_cycle.database.connection import GameCycleDatabase

    db_path, _ = game_cycle_db
    db = GameCycleDatabase(db_path)
    return PopularityCalculator(db, test_dynasty_id)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_sample_player_grade(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    overall_grade: float = 75.0,
    position: str = "QB"
):
    """
    Create sample player grade in analytics_player_season_grades table.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        overall_grade: PFF overall grade (0-100)
        position: Player position
    """
    conn.execute(
        """INSERT OR REPLACE INTO analytics_player_season_grades (
               dynasty_id, player_id, season, position,
               overall_grade, offense_grade, defense_grade, special_teams_grade,
               games_played, snaps_played
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            dynasty_id, player_id, season, position,
            overall_grade, overall_grade, 0.0, 0.0,
            10, 600
        )
    )
    conn.commit()


def create_national_headline(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    week: int,
    priority: int = 85
):
    """
    Create high-priority national headline for player.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        week: Week number
        priority: Headline priority (>80 = national)
    """
    conn.execute(
        """INSERT INTO headlines (
               dynasty_id, season, week, category, headline_text,
               body_text, priority, player_id, is_breaking_news
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            dynasty_id, season, week, "player_performance",
            f"QB Lights Up Defense for 400 Yards, 4 TDs",
            "Dominant performance in primetime victory",
            priority, player_id, True
        )
    )
    conn.commit()


def create_mvp_nominee(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    rank: int = 1
):
    """
    Create MVP award nominee entry.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        rank: Nomination rank (1 = frontrunner)
    """
    conn.execute(
        """INSERT INTO award_nominees (
               dynasty_id, award_id, player_id, season,
               nomination_rank, votes_received, vote_percentage
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (dynasty_id, "MVP", player_id, season, rank, 50, 0.5)
    )
    conn.commit()


def create_award_winner(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    award_type: str = "MVP"
):
    """
    Create award winner entry.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        award_type: Award type (MVP, OPOY, DPOY, etc.)
    """
    conn.execute(
        """INSERT INTO awards (
               dynasty_id, award_id, season, player_id, team_id,
               position, votes_received, vote_percentage
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (dynasty_id, award_type, season, player_id, 1, "QB", 50, 1.0)
    )
    conn.commit()


def create_all_pro_selection(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    team_type: str = "first"
):
    """
    Create All-Pro selection.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        team_type: 'first' or 'second' team
    """
    conn.execute(
        """INSERT INTO all_pro_selections (
               dynasty_id, season, player_id, team_id, position, team_type
           ) VALUES (?, ?, ?, ?, ?, ?)""",
        (dynasty_id, season, player_id, 1, "QB", team_type)
    )
    conn.commit()


def simulate_injury_weeks(
    conn,
    dynasty_id: str,
    player_id: int,
    season: int,
    start_week: int,
    weeks: int = 4
):
    """
    Simulate player injury for multiple weeks.

    Args:
        conn: Database connection
        dynasty_id: Dynasty identifier
        player_id: Player ID
        season: Season year
        start_week: Week injury starts
        weeks: Number of weeks injured
    """
    conn.execute(
        """INSERT INTO player_injuries (
               dynasty_id, player_id, season, week_occurred,
               injury_type, body_part, severity, estimated_weeks_out,
               occurred_during, is_active
           ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (dynasty_id, player_id, season, start_week,
         "ACL", "knee", "severe", weeks, "game", 1)
    )
    conn.commit()


# ============================================================================
# TEST SCENARIOS
# ============================================================================

class TestPopularityBreakoutGame:
    """Test Scenario 1: Breakout Game → Popularity Spike."""

    def test_breakout_performance_boosts_popularity(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that a breakout game performance increases popularity.

        Setup:
        - Player with 60 popularity (baseline)
        - High PFF grade (90.0 for breakout game)
        - National headline generated

        Expected:
        - Visibility multiplier includes headline boost (+0.3)
        - Performance score is high (90+)
        - Final popularity increases by +10-15 points
        """
        db_path, conn = game_cycle_db
        player_id = 1001
        week = 5

        # Setup: Baseline popularity
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, week - 1,
            popularity_score=60.0,
            performance_score=70.0,
            visibility_multiplier=1.0,
            market_multiplier=1.0
        )

        # Setup: Breakout game grade
        create_sample_player_grade(
            conn, test_dynasty_id, player_id, test_season,
            overall_grade=90.0, position="QB"
        )

        # Setup: National headline for performance
        create_national_headline(
            conn, test_dynasty_id, player_id, test_season, week,
            priority=85
        )

        # Calculate performance score
        performance = popularity_calculator.calculate_performance_score(
            player_id, test_season, week, "QB"
        )

        # Calculate visibility multiplier (includes headline boost)
        visibility = popularity_calculator.calculate_visibility_multiplier(
            player_id, test_season, week
        )

        # Calculate final popularity (simplified for test)
        market = 1.0  # Neutral market
        raw_score = performance * visibility * market
        final_score = min(100.0, raw_score)

        # Save new popularity score
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, week,
            popularity_score=final_score,
            performance_score=performance,
            visibility_multiplier=visibility,
            market_multiplier=market,
            week_change=final_score - 60.0
        )

        # Verify: Performance score is high
        assert performance >= 90.0, f"Expected performance >= 90, got {performance:.1f}"

        # Verify: Visibility includes headline boost
        assert visibility >= 1.3, f"Expected visibility >= 1.3 (includes headline), got {visibility:.1f}"

        # Verify: Popularity increased significantly
        score = popularity_api.get_popularity_score(
            test_dynasty_id, player_id, test_season, week
        )
        assert score is not None
        assert score.popularity_score >= 70.0, \
            f"Expected popularity >= 70 (60 + spike), got {score.popularity_score:.1f}"
        assert score.week_change >= 10.0, \
            f"Expected week change >= 10, got {score.week_change:.1f}"


class TestPopularityMVPRace:
    """Test Scenario 2: MVP Race Leader → Sustained High Popularity."""

    def test_mvp_candidate_maintains_high_popularity(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that MVP race leaders maintain high popularity.

        Setup:
        - Player in MVP race top 3
        - 4 consecutive weeks of tracking

        Expected:
        - Visibility multiplier includes +0.5x MVP bonus
        - Popularity remains 80+ (STAR tier)
        """
        db_path, conn = game_cycle_db
        player_id = 1002

        # Setup: High PFF grade
        create_sample_player_grade(
            conn, test_dynasty_id, player_id, test_season,
            overall_grade=85.0, position="QB"
        )

        # Setup: MVP nominee (top 3)
        create_mvp_nominee(conn, test_dynasty_id, player_id, test_season, rank=2)

        # Simulate 4 consecutive weeks
        for week in range(10, 14):
            # Calculate visibility (includes MVP bonus)
            visibility = popularity_calculator.calculate_visibility_multiplier(
                player_id, test_season, week
            )

            # Verify MVP bonus is applied
            assert visibility >= 1.5, \
                f"Week {week}: Expected visibility >= 1.5 (MVP bonus), got {visibility:.1f}"

            # Calculate performance
            performance = popularity_calculator.calculate_performance_score(
                player_id, test_season, week, "QB"
            )

            # Calculate final popularity
            market = 1.0
            final_score = min(100.0, performance * visibility * market)

            # Save popularity
            popularity_api.save_popularity_score(
                test_dynasty_id, player_id, test_season, week,
                popularity_score=final_score,
                performance_score=performance,
                visibility_multiplier=visibility,
                market_multiplier=market
            )

            # Verify: Maintains STAR tier (75+)
            score = popularity_api.get_popularity_score(
                test_dynasty_id, player_id, test_season, week
            )
            assert score.popularity_score >= 75.0, \
                f"Week {week}: Expected STAR tier (75+), got {score.popularity_score:.1f}"
            assert score.tier == "STAR" or score.tier == "TRANSCENDENT", \
                f"Week {week}: Expected STAR/TRANSCENDENT tier, got {score.tier}"


class TestPopularityInjuryDecay:
    """Test Scenario 3: Injury → Gradual Decay."""

    def test_injury_causes_popularity_decay(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that injuries cause gradual popularity decay.

        Setup:
        - Player with 75 popularity gets injured
        - 4 weeks on IR (no games, no media)

        Expected:
        - Popularity drops by ~12 points (-3 per week)
        - Tier drops from STAR to KNOWN
        """
        db_path, conn = game_cycle_db
        player_id = 1003
        injury_week = 5

        # Setup: High baseline popularity (STAR tier)
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, injury_week - 1,
            popularity_score=75.0,
            performance_score=80.0,
            visibility_multiplier=1.2,
            market_multiplier=1.0,
            tier="STAR"
        )

        # Setup: Injury
        simulate_injury_weeks(
            conn, test_dynasty_id, player_id, test_season,
            injury_week, weeks=4
        )

        # Simulate 4 weeks of decay
        current_popularity = 75.0
        for week in range(injury_week, injury_week + 4):
            # Apply injury decay
            decay = popularity_calculator.apply_weekly_decay(
                current_popularity,
                events_this_week=['INJURY', 'INACTIVE']
            )

            # Update popularity
            current_popularity += decay  # decay is negative
            current_popularity = max(0.0, current_popularity)

            # Save popularity
            popularity_api.save_popularity_score(
                test_dynasty_id, player_id, test_season, week,
                popularity_score=current_popularity,
                performance_score=0.0,  # No performance while injured
                visibility_multiplier=0.5,  # Minimal visibility
                market_multiplier=1.0,
                week_change=decay
            )

            # Log event
            popularity_api.save_popularity_event(
                test_dynasty_id, player_id, test_season, week,
                event_type='INJURY',
                impact=decay,
                description=f"Injured - no activity week {week}"
            )

        # Verify: Total decay is approximately -12 points
        final_score = popularity_api.get_popularity_score(
            test_dynasty_id, player_id, test_season, injury_week + 3
        )
        assert final_score.popularity_score <= 65.0, \
            f"Expected popularity <= 65 (75 - 12), got {final_score.popularity_score:.1f}"
        assert final_score.popularity_score >= 60.0, \
            f"Expected popularity >= 60, got {final_score.popularity_score:.1f}"

        # Verify: Tier dropped from STAR to KNOWN
        assert final_score.tier == "KNOWN", \
            f"Expected KNOWN tier after decay, got {final_score.tier}"

        # Verify: Events logged
        events = popularity_api.get_popularity_events(
            test_dynasty_id, player_id, test_season
        )
        assert len(events) == 4, f"Expected 4 injury events, got {len(events)}"


class TestPopularityTradeImpact:
    """Test Scenario 4: Trade to Big Market → Popularity Boost."""

    def test_trade_to_big_market_boosts_popularity(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that trading to a big market eventually boosts popularity.

        Setup:
        - Player with 70 popularity on Jacksonville (small market, 0.9x)
        - Trade to Dallas Cowboys (large market, 2.0x)

        Expected:
        - Week 0: -20% disruption (70 → 56)
        - Week 4: Full Dallas multiplier applied
        - Final popularity > initial (market boost effect)
        """
        db_path, conn = game_cycle_db
        player_id = 1004
        trade_week = 8
        old_team_id = 11  # Jacksonville (small market)
        new_team_id = 17  # Dallas (large market)

        # Setup: Baseline popularity on small market team
        initial_popularity = 70.0
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, trade_week - 1,
            popularity_score=initial_popularity,
            performance_score=75.0,
            visibility_multiplier=1.0,
            market_multiplier=0.9  # Jacksonville small market
        )

        # Setup: Player grade
        create_sample_player_grade(
            conn, test_dynasty_id, player_id, test_season,
            overall_grade=75.0, position="WR"
        )

        # Week 0: Apply trade disruption
        disrupted_popularity = popularity_calculator.adjust_for_trade(
            player_id, old_team_id, new_team_id, trade_week, initial_popularity
        )

        # Verify immediate disruption (-20%)
        assert disrupted_popularity <= 56.0, \
            f"Expected popularity <= 56 (70 * 0.8), got {disrupted_popularity:.1f}"
        assert disrupted_popularity >= 55.0, \
            f"Expected popularity >= 55, got {disrupted_popularity:.1f}"

        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, trade_week,
            popularity_score=disrupted_popularity,
            performance_score=75.0,
            visibility_multiplier=1.0,
            market_multiplier=0.9,  # Still adjusting
            week_change=disrupted_popularity - initial_popularity
        )

        # Weeks 1-4: Gradual market adjustment
        weeks_to_adjust = 4
        for i in range(1, weeks_to_adjust + 1):
            week = trade_week + i

            # Linear interpolation of market multiplier
            old_market = 0.9
            new_market = 2.0
            progress = i / weeks_to_adjust
            current_market = old_market + (new_market - old_market) * progress

            # Calculate performance
            performance = popularity_calculator.calculate_performance_score(
                player_id, test_season, week, "WR"
            )

            # Calculate visibility
            visibility = 1.0  # Baseline

            # Calculate popularity with gradual market adjustment
            raw_score = performance * visibility * current_market
            final_score = min(100.0, raw_score)

            popularity_api.save_popularity_score(
                test_dynasty_id, player_id, test_season, week,
                popularity_score=final_score,
                performance_score=performance,
                visibility_multiplier=visibility,
                market_multiplier=current_market
            )

        # Verify: Week 4 has full Dallas market multiplier
        final_score = popularity_api.get_popularity_score(
            test_dynasty_id, player_id, test_season, trade_week + 4
        )
        assert final_score.market_multiplier >= 1.9, \
            f"Expected market_multiplier >= 1.9 (Dallas), got {final_score.market_multiplier:.1f}"

        # Verify: Final popularity > initial (market boost effect)
        # With 2.0x market vs 0.9x, popularity should roughly double
        # But starting from disrupted level, so may take time
        # At minimum, should recover past initial 70
        assert final_score.popularity_score >= 70.0, \
            f"Expected final popularity >= 70 (recovered), got {final_score.popularity_score:.1f}"


class TestPopularityAwardImpact:
    """Test Scenario 5: Award Announcement → Immediate Jump."""

    def test_award_win_immediate_boost(
        self,
        game_cycle_db,
        popularity_api,
        test_dynasty_id,
        test_season
    ):
        """
        Test that winning an award immediately boosts popularity.

        Setup:
        - Player with 65 popularity (KNOWN tier)
        - Player wins MVP award

        Expected:
        - Immediate +20 boost (65 → 85)
        - Tier jumps from KNOWN to STAR
        """
        db_path, conn = game_cycle_db
        player_id = 1005
        week = 18  # End of season

        # Setup: Baseline popularity (KNOWN tier)
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, week - 1,
            popularity_score=65.0,
            performance_score=75.0,
            visibility_multiplier=1.0,
            market_multiplier=1.0,
            tier="KNOWN"
        )

        # Setup: MVP award winner
        create_award_winner(
            conn, test_dynasty_id, player_id, test_season, award_type="MVP"
        )

        # Apply award boost (manual calculation for test)
        mvp_boost = 20.0
        new_popularity = 65.0 + mvp_boost

        # Save updated popularity
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, week,
            popularity_score=new_popularity,
            performance_score=75.0,
            visibility_multiplier=1.5,  # Award visibility
            market_multiplier=1.0,
            week_change=mvp_boost
        )

        # Log award event
        popularity_api.save_popularity_event(
            test_dynasty_id, player_id, test_season, week,
            event_type='AWARD',
            impact=mvp_boost,
            description="MVP Award Winner"
        )

        # Verify: Popularity jumped to 85
        score = popularity_api.get_popularity_score(
            test_dynasty_id, player_id, test_season, week
        )
        assert score.popularity_score == 85.0, \
            f"Expected popularity = 85 (65 + 20), got {score.popularity_score:.1f}"

        # Verify: Tier is now STAR
        assert score.tier == "STAR", \
            f"Expected STAR tier (75-89), got {score.tier}"

        # Verify: Event logged
        events = popularity_api.get_popularity_events(
            test_dynasty_id, player_id, test_season, week
        )
        assert len(events) == 1, f"Expected 1 award event, got {len(events)}"
        assert events[0].event_type == 'AWARD'
        assert events[0].impact == 20.0


class TestPopularityMarketComparison:
    """Test Scenario 6: Small Market Star vs Big Market Average."""

    def test_market_size_impacts_popularity(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that market size significantly impacts popularity.

        Setup:
        - Two players with same performance score (75)
        - Player A: Green Bay (large market, ~1.8x)
        - Player B: Jacksonville (small market, ~0.9x)

        Expected:
        - Player A ends with ~20+ points higher popularity
        - Market multiplier creates substantial gap
        """
        db_path, conn = game_cycle_db
        player_a_id = 1006  # Green Bay
        player_b_id = 1007  # Jacksonville
        team_a_id = 13  # Green Bay
        team_b_id = 11  # Jacksonville
        week = 10

        # Setup: Same performance grade for both
        for player_id in [player_a_id, player_b_id]:
            create_sample_player_grade(
                conn, test_dynasty_id, player_id, test_season,
                overall_grade=75.0, position="RB"
            )

        # Calculate market multipliers
        market_a = popularity_calculator.calculate_market_multiplier(team_a_id)
        market_b = popularity_calculator.calculate_market_multiplier(team_b_id)

        # Verify market multipliers are different
        assert market_a >= 1.4, \
            f"Expected Green Bay market >= 1.4, got {market_a:.2f}"
        assert market_b <= 1.0, \
            f"Expected Jacksonville market <= 1.0, got {market_b:.2f}"

        # Calculate performance (same for both)
        performance_a = popularity_calculator.calculate_performance_score(
            player_a_id, test_season, week, "RB"
        )
        performance_b = popularity_calculator.calculate_performance_score(
            player_b_id, test_season, week, "RB"
        )

        # Calculate popularity with market multipliers
        visibility = 1.0  # Same for both
        popularity_a = min(100.0, performance_a * visibility * market_a)
        popularity_b = min(100.0, performance_b * visibility * market_b)

        # Save popularity scores
        popularity_api.save_popularity_score(
            test_dynasty_id, player_a_id, test_season, week,
            popularity_score=popularity_a,
            performance_score=performance_a,
            visibility_multiplier=visibility,
            market_multiplier=market_a
        )

        popularity_api.save_popularity_score(
            test_dynasty_id, player_b_id, test_season, week,
            popularity_score=popularity_b,
            performance_score=performance_b,
            visibility_multiplier=visibility,
            market_multiplier=market_b
        )

        # Verify: Player A has significantly higher popularity
        gap = popularity_a - popularity_b
        assert gap >= 15.0, \
            f"Expected popularity gap >= 15 points, got {gap:.1f} ({popularity_a:.1f} vs {popularity_b:.1f})"

        # Verify: Market multiplier is the differentiator
        score_a = popularity_api.get_popularity_score(
            test_dynasty_id, player_a_id, test_season, week
        )
        score_b = popularity_api.get_popularity_score(
            test_dynasty_id, player_b_id, test_season, week
        )

        assert score_a.performance_score == score_b.performance_score, \
            "Performance scores should be equal"
        assert score_a.market_multiplier > score_b.market_multiplier, \
            "Market multiplier should be higher for Green Bay"


class TestPopularityRookieDraft:
    """Test Scenario 7: Rookie Draft → Initial Popularity."""

    def test_rookie_initial_popularity_by_draft_position(
        self,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that rookies get appropriate initial popularity based on draft position.

        Setup:
        - Draft class with various picks

        Expected:
        - 1st overall: 40 popularity
        - 10th overall: 30 popularity
        - 32nd overall: 25 popularity
        - Undrafted: 5 popularity
        """
        test_cases = [
            (1, 1, 40.0, "1st overall"),
            (1, 10, 30.0, "10th overall"),
            (1, 32, 25.0, "32nd pick (end of 1st)"),
            (2, 33, 20.0, "2nd round"),
            (3, 65, 15.0, "3rd round"),
            (5, 150, 10.0, "5th round"),
            (0, 0, 5.0, "Undrafted"),
        ]

        for draft_round, draft_pick, expected_popularity, description in test_cases:
            player_id = 2000 + draft_pick

            # Initialize rookie popularity
            initial_popularity = popularity_calculator.initialize_rookie_popularity(
                player_id, draft_round, draft_pick
            )

            # Verify expected popularity
            assert initial_popularity == expected_popularity, \
                f"{description}: Expected {expected_popularity}, got {initial_popularity}"

            # Save initial popularity
            popularity_api.save_popularity_score(
                test_dynasty_id, player_id, test_season, week=0,
                popularity_score=initial_popularity,
                performance_score=0.0,  # No performance yet
                visibility_multiplier=1.0,
                market_multiplier=1.0
            )

            # Log draft event
            popularity_api.save_popularity_event(
                test_dynasty_id, player_id, test_season, week=0,
                event_type='DRAFT',
                impact=initial_popularity,
                description=f"Drafted {description}"
            )

        # Verify all rookies saved
        top_rookies = popularity_api.get_top_players(
            test_dynasty_id, test_season, week=0, limit=10
        )
        assert len(top_rookies) >= 5, f"Expected at least 5 rookies, got {len(top_rookies)}"

        # Verify top pick has highest popularity
        assert top_rookies[0].popularity_score == 40.0, \
            f"Expected 1st overall to be top rookie, got {top_rookies[0].popularity_score}"


class TestPopularityPlayoffBoost:
    """Test Scenario 8: Playoff Performance → 1.5x Boost."""

    def test_playoff_performance_amplified(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test that playoff performances get amplified visibility.

        Setup:
        - Player with 70 popularity
        - Super Bowl game (week 22) with strong performance

        Expected:
        - Stats/headlines get 1.5x multiplier
        - Popularity increases more than regular season equivalent
        """
        db_path, conn = game_cycle_db
        player_id = 1008
        regular_week = 10
        playoff_week = 22  # Super Bowl

        # Setup: Baseline popularity
        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, regular_week,
            popularity_score=70.0,
            performance_score=75.0,
            visibility_multiplier=1.0,
            market_multiplier=1.0
        )

        # Setup: Strong playoff performance
        create_sample_player_grade(
            conn, test_dynasty_id, player_id, test_season,
            overall_grade=85.0, position="QB"
        )

        # Setup: National headline for playoff game
        create_national_headline(
            conn, test_dynasty_id, player_id, test_season, playoff_week,
            priority=90  # Super Bowl headline
        )

        # Calculate base stats and headlines impact
        base_stats_impact = 10.0
        base_headlines_impact = 5.0

        # Apply playoff multiplier
        playoff_stats, playoff_headlines = popularity_calculator.apply_playoff_multiplier(
            playoff_week, base_stats_impact, base_headlines_impact
        )

        # Verify: 1.5x multiplier applied
        assert playoff_stats == 15.0, \
            f"Expected playoff stats impact = 15.0 (10 * 1.5), got {playoff_stats}"
        assert playoff_headlines == 7.5, \
            f"Expected playoff headlines impact = 7.5 (5 * 1.5), got {playoff_headlines}"

        # Calculate full visibility with playoff boost
        visibility = popularity_calculator.calculate_visibility_multiplier(
            player_id, test_season, playoff_week
        )

        # Playoff visibility should be higher
        assert visibility >= 1.3, \
            f"Expected playoff visibility >= 1.3, got {visibility:.2f}"

        # Calculate final playoff popularity
        performance = popularity_calculator.calculate_performance_score(
            player_id, test_season, playoff_week, "QB"
        )
        final_score = min(100.0, performance * visibility * 1.0)

        popularity_api.save_popularity_score(
            test_dynasty_id, player_id, test_season, playoff_week,
            popularity_score=final_score,
            performance_score=performance,
            visibility_multiplier=visibility,
            market_multiplier=1.0,
            week_change=final_score - 70.0
        )

        # Verify: Playoff performance boosted popularity significantly
        playoff_score = popularity_api.get_popularity_score(
            test_dynasty_id, player_id, test_season, playoff_week
        )
        assert playoff_score.popularity_score >= 80.0, \
            f"Expected playoff popularity >= 80 (Super Bowl boost), got {playoff_score.popularity_score:.1f}"


class TestPopularityFullSeason:
    """Test Scenario 9: Full Season Popularity Trajectory."""

    def test_full_season_realistic_distribution(
        self,
        game_cycle_db,
        popularity_api,
        popularity_calculator,
        test_dynasty_id,
        test_season
    ):
        """
        Test realistic popularity distribution over a full season.

        Setup:
        - 10 sample players with varying performance
        - Simulate 18-week regular season

        Expected:
        - Top performers increase in popularity
        - Injured players decrease
        - Tier distribution is realistic (few TRANSCENDENT, many UNKNOWN)
        """
        db_path, conn = game_cycle_db

        # Create sample players
        players = [
            {'id': 3001, 'position': 'QB', 'grade': 90.0, 'team_id': 17},  # Star QB
            {'id': 3002, 'position': 'QB', 'grade': 75.0, 'team_id': 11},  # Average QB
            {'id': 3003, 'position': 'RB', 'grade': 85.0, 'team_id': 1},   # Good RB
            {'id': 3004, 'position': 'WR', 'grade': 80.0, 'team_id': 13},  # Good WR
            {'id': 3005, 'position': 'CB', 'grade': 70.0, 'team_id': 32},  # Average CB
            {'id': 3006, 'position': 'OL', 'grade': 75.0, 'team_id': 1},   # Average OL (low visibility)
            {'id': 3007, 'position': 'QB', 'grade': 60.0, 'team_id': 11},  # Backup QB
            {'id': 3008, 'position': 'RB', 'grade': 50.0, 'team_id': 32},  # Backup RB
            {'id': 3009, 'position': 'K', 'grade': 80.0, 'team_id': 1},    # Kicker (low position value)
            {'id': 3010, 'position': 'QB', 'grade': 85.0, 'team_id': 13},  # Will be injured
        ]

        # Initialize all players
        for player in players:
            create_sample_player_grade(
                conn, test_dynasty_id, player['id'], test_season,
                overall_grade=player['grade'], position=player['position']
            )

            # Initial popularity (baseline)
            popularity_api.save_popularity_score(
                test_dynasty_id, player['id'], test_season, week=1,
                popularity_score=30.0,  # All start as ROLE_PLAYER
                performance_score=player['grade'],
                visibility_multiplier=1.0,
                market_multiplier=1.0,
                tier="ROLE_PLAYER"
            )

        # Injure player 3010 at week 5
        simulate_injury_weeks(conn, test_dynasty_id, 3010, test_season, 5, weeks=10)

        # Simulate weeks 2-18
        for week in range(2, 19):
            for player in players:
                player_id = player['id']

                # Calculate components
                performance = popularity_calculator.calculate_performance_score(
                    player_id, test_season, week, player['position']
                )
                visibility = 1.0  # Baseline
                market = popularity_calculator.calculate_market_multiplier(player['team_id'])

                # Apply decay for injured player
                events = []
                if player_id == 3010 and week >= 5:
                    events = ['INJURY', 'INACTIVE']

                # Get previous popularity
                prev_score = popularity_api.get_popularity_score(
                    test_dynasty_id, player_id, test_season, week - 1
                )
                prev_popularity = prev_score.popularity_score if prev_score else 30.0

                # Apply decay
                decay = popularity_calculator.apply_weekly_decay(prev_popularity, events)

                # Calculate new popularity
                raw_score = performance * visibility * market
                final_score = max(0.0, min(100.0, raw_score + decay))

                # Save
                popularity_api.save_popularity_score(
                    test_dynasty_id, player_id, test_season, week,
                    popularity_score=final_score,
                    performance_score=performance,
                    visibility_multiplier=visibility,
                    market_multiplier=market,
                    week_change=final_score - prev_popularity
                )

        # Verify: Top performers have high popularity
        week_18_top = popularity_api.get_top_players(
            test_dynasty_id, test_season, week=18, limit=10
        )

        # Star QB (3001) should be in top tier
        star_qb = popularity_api.get_popularity_score(test_dynasty_id, 3001, test_season, 18)
        assert star_qb.popularity_score >= 80.0, \
            f"Star QB should have high popularity, got {star_qb.popularity_score:.1f}"

        # Injured player (3010) should have decayed
        injured_qb = popularity_api.get_popularity_score(test_dynasty_id, 3010, test_season, 18)
        assert injured_qb.popularity_score <= 60.0, \
            f"Injured QB should have low popularity, got {injured_qb.popularity_score:.1f}"

        # Kicker (3009) should have low popularity despite good grade
        kicker = popularity_api.get_popularity_score(test_dynasty_id, 3009, test_season, 18)
        assert kicker.popularity_score <= 60.0, \
            f"Kicker should have low popularity, got {kicker.popularity_score:.1f}"

        # Verify tier distribution
        transcendent = popularity_api.get_players_by_tier(
            test_dynasty_id, test_season, 18, 'TRANSCENDENT'
        )
        stars = popularity_api.get_players_by_tier(
            test_dynasty_id, test_season, 18, 'STAR'
        )
        unknown = popularity_api.get_players_by_tier(
            test_dynasty_id, test_season, 18, 'UNKNOWN'
        )

        # Should have few transcendent, some stars, many unknown
        assert len(transcendent) <= 2, \
            f"Expected <= 2 TRANSCENDENT players, got {len(transcendent)}"
        assert len(unknown) >= 3, \
            f"Expected >= 3 UNKNOWN players, got {len(unknown)}"


class TestPopularityDynastyIsolation:
    """Test Scenario 10: Dynasty Isolation."""

    def test_dynasty_isolation_maintained(
        self,
        popularity_api,
        test_season
    ):
        """
        Test that popularity data is isolated between dynasties.

        Setup:
        - Two dynasties with same player IDs
        - Update popularity in Dynasty 1 only

        Expected:
        - Dynasty 2 popularity unchanged
        - Queries properly filter by dynasty_id
        """
        dynasty_1 = "dynasty_one"
        dynasty_2 = "dynasty_two"
        player_id = 4001
        week = 10

        # Save popularity in Dynasty 1
        popularity_api.save_popularity_score(
            dynasty_1, player_id, test_season, week,
            popularity_score=80.0,
            performance_score=85.0,
            visibility_multiplier=1.2,
            market_multiplier=1.0
        )

        # Save popularity in Dynasty 2 (different value)
        popularity_api.save_popularity_score(
            dynasty_2, player_id, test_season, week,
            popularity_score=50.0,
            performance_score=60.0,
            visibility_multiplier=1.0,
            market_multiplier=1.0
        )

        # Update Dynasty 1 only
        popularity_api.save_popularity_score(
            dynasty_1, player_id, test_season, week + 1,
            popularity_score=85.0,
            performance_score=90.0,
            visibility_multiplier=1.3,
            market_multiplier=1.0
        )

        # Verify: Dynasty 1 updated
        dynasty_1_score = popularity_api.get_popularity_score(
            dynasty_1, player_id, test_season, week + 1
        )
        assert dynasty_1_score is not None
        assert dynasty_1_score.popularity_score == 85.0

        # Verify: Dynasty 2 unchanged
        dynasty_2_score = popularity_api.get_popularity_score(
            dynasty_2, player_id, test_season, week + 1
        )
        assert dynasty_2_score is None, "Dynasty 2 should have no data for week + 1"

        dynasty_2_original = popularity_api.get_popularity_score(
            dynasty_2, player_id, test_season, week
        )
        assert dynasty_2_original.popularity_score == 50.0, \
            "Dynasty 2 original score should be unchanged"

        # Verify: Top players queries are isolated
        dynasty_1_top = popularity_api.get_top_players(
            dynasty_1, test_season, week + 1, limit=10
        )
        dynasty_2_top = popularity_api.get_top_players(
            dynasty_2, test_season, week + 1, limit=10
        )

        assert len(dynasty_1_top) == 1, "Dynasty 1 should have 1 player in week + 1"
        assert len(dynasty_2_top) == 0, "Dynasty 2 should have 0 players in week + 1"

        # Verify: Events are isolated
        popularity_api.save_popularity_event(
            dynasty_1, player_id, test_season, week,
            event_type='HEADLINE',
            impact=5.0,
            description="Dynasty 1 event"
        )

        dynasty_1_events = popularity_api.get_popularity_events(
            dynasty_1, player_id, test_season
        )
        dynasty_2_events = popularity_api.get_popularity_events(
            dynasty_2, player_id, test_season
        )

        assert len(dynasty_1_events) == 1, "Dynasty 1 should have 1 event"
        assert len(dynasty_2_events) == 0, "Dynasty 2 should have 0 events"
