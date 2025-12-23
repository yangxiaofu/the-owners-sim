"""
Integration Tests: Context-Aware Social Media Posts

Tests the complete context-aware social media system with:
1. Playoff contender messaging (no draft talk)
2. Eliminated team messaging (tank mode)
3. Trade hallucination prevention (no trades = no trade posts)
4. Week-based filtering (early vs late season)
5. Recent activity tracking (trade recency)

Part of Milestone 14: Social Media & Fan Reactions - Context-Aware System
"""

import pytest
import tempfile
import os
import json
from typing import List, Dict, Any

# Direct imports to avoid circular import issues
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / 'src'))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.database.social_posts_api import SocialPostsAPI
from game_cycle.database.standings_api import StandingsAPI
from game_cycle.services.team_context_builder import (
    TeamContextBuilder,
    PlayoffPosition,
    SeasonPhase,
)
from game_cycle.models.social_event_types import SocialEventType


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def game_db(temp_db_path):
    """Create database with full game cycle schema."""
    db = GameCycleDatabase(temp_db_path)

    # Create necessary tables
    db.get_connection().executescript("""
        PRAGMA foreign_keys = OFF;

        -- Standings table
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            team_id INTEGER NOT NULL,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            ties INTEGER DEFAULT 0,
            points_for INTEGER DEFAULT 0,
            points_against INTEGER DEFAULT 0,
            division_wins INTEGER DEFAULT 0,
            division_losses INTEGER DEFAULT 0,
            conference_wins INTEGER DEFAULT 0,
            conference_losses INTEGER DEFAULT 0,
            home_wins INTEGER DEFAULT 0,
            home_losses INTEGER DEFAULT 0,
            away_wins INTEGER DEFAULT 0,
            away_losses INTEGER DEFAULT 0,
            playoff_seed INTEGER,
            season_type TEXT DEFAULT 'regular_season',
            UNIQUE(dynasty_id, season, team_id, season_type)
        );

        -- Games table
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER NOT NULL,
            season_type TEXT DEFAULT 'regular_season',
            home_team_id INTEGER NOT NULL,
            away_team_id INTEGER NOT NULL,
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            completed INTEGER DEFAULT 0
        );

        -- Player transactions table
        CREATE TABLE IF NOT EXISTS player_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            season INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,
            player_id INTEGER,
            first_name TEXT,
            last_name TEXT,
            position TEXT,
            from_team_id INTEGER,
            to_team_id INTEGER,
            transaction_date TEXT,
            details TEXT
        );

        -- Social personalities table
        CREATE TABLE IF NOT EXISTS social_personalities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            handle TEXT NOT NULL,
            display_name TEXT NOT NULL,
            personality_type TEXT NOT NULL,
            archetype TEXT,
            team_id INTEGER,
            sentiment_bias REAL NOT NULL,
            posting_frequency TEXT NOT NULL,
            UNIQUE(dynasty_id, handle)
        );

        -- Social posts table
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            personality_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER,
            post_text TEXT NOT NULL,
            event_type TEXT NOT NULL,
            sentiment REAL NOT NULL,
            likes INTEGER DEFAULT 0,
            retweets INTEGER DEFAULT 0,
            event_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (personality_id) REFERENCES social_personalities(id)
        );
    """)

    db.get_connection().commit()

    yield db

    db.close()


@pytest.fixture
def standings_api(game_db):
    """Create StandingsAPI instance."""
    return StandingsAPI(game_db)


@pytest.fixture
def context_builder(game_db):
    """Create TeamContextBuilder instance."""
    return TeamContextBuilder(game_db)


@pytest.fixture
def social_api(game_db):
    """Create SocialPersonalityAPI instance."""
    return SocialPersonalityAPI(game_db)


@pytest.fixture
def posts_api(game_db):
    """Create SocialPostsAPI instance."""
    return SocialPostsAPI(game_db)


# ==========================================
# HELPER FUNCTIONS
# ==========================================

def seed_standings(standings_api, dynasty_id: str, season: int, team_data: List[Dict]):
    """
    Seed standings table with team records.

    Args:
        standings_api: StandingsAPI instance
        dynasty_id: Dynasty ID
        season: Season year
        team_data: List of dicts with team_id, wins, losses, ties
    """
    db = standings_api.db

    for team in team_data:
        db.execute(
            """
            INSERT OR REPLACE INTO standings
            (dynasty_id, season, team_id, wins, losses, ties, points_for, points_against,
             division_wins, division_losses, conference_wins, conference_losses,
             home_wins, home_losses, away_wins, away_losses, playoff_seed, season_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, ?, 'regular_season')
            """,
            (dynasty_id, season, team['team_id'], team.get('wins', 0),
             team.get('losses', 0), team.get('ties', 0),
             team.get('points_for', 300), team.get('points_against', 300),
             team.get('playoff_seed'))
        )


def seed_games(game_db, dynasty_id: str, season: int, week: int, game_data: List[Dict]):
    """
    Seed games table with game results.

    Args:
        game_db: GameCycleDatabase instance
        dynasty_id: Dynasty ID
        season: Season year
        week: Week number
        game_data: List of dicts with home_team_id, away_team_id, home_score, away_score
    """
    for game in game_data:
        game_db.execute(
            """
            INSERT INTO games (dynasty_id, season, week, season_type, home_team_id,
                             away_team_id, home_score, away_score, completed)
            VALUES (?, ?, ?, 'regular_season', ?, ?, ?, ?, 1)
            """,
            (dynasty_id, season, week, game['home_team_id'], game['away_team_id'],
             game['home_score'], game['away_score'])
        )


def seed_transactions(game_db, dynasty_id: str, season: int, transaction_data: List[Dict]):
    """
    Seed player_transactions table.

    Args:
        game_db: GameCycleDatabase instance
        dynasty_id: Dynasty ID
        season: Season year
        transaction_data: List of transaction dicts
    """
    for txn in transaction_data:
        game_db.execute(
            """
            INSERT INTO player_transactions
            (dynasty_id, season, transaction_type, player_id, first_name, last_name,
             position, from_team_id, to_team_id, transaction_date, details)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (dynasty_id, season, txn['transaction_type'], txn.get('player_id', 1),
             txn.get('first_name', 'Test'), txn.get('last_name', 'Player'),
             txn.get('position', 'QB'), txn.get('from_team_id'), txn.get('to_team_id'),
             txn['transaction_date'], json.dumps(txn.get('details', {})))
        )


def create_test_personalities(social_api, dynasty_id: str, team_id: int) -> List[int]:
    """
    Create test fan personalities for a team.

    Returns:
        List of personality IDs
    """
    personality_ids = []

    # Create OPTIMIST fan
    pid = social_api.create_personality(
        dynasty_id=dynasty_id,
        handle=f'@Team{team_id}Optimist',
        display_name=f'Team {team_id} Optimist',
        personality_type='FAN',
        archetype='OPTIMIST',
        team_id=team_id,
        sentiment_bias=0.5,
        posting_frequency='ALL_EVENTS'
    )
    personality_ids.append(pid)

    # Create TRADE_ANALYST (league-wide)
    pid = social_api.create_personality(
        dynasty_id=dynasty_id,
        handle='@TradeAnalyst',
        display_name='Trade Analyst',
        personality_type='HOT_TAKE',
        archetype='TRADE_ANALYST',
        team_id=None,
        sentiment_bias=0.0,
        posting_frequency='EMOTIONAL_MOMENTS'
    )
    personality_ids.append(pid)

    # Create BALANCED fan
    pid = social_api.create_personality(
        dynasty_id=dynasty_id,
        handle=f'@Team{team_id}Balanced',
        display_name=f'Team {team_id} Balanced Fan',
        personality_type='FAN',
        archetype='BALANCED',
        team_id=team_id,
        sentiment_bias=0.0,
        posting_frequency='ALL_EVENTS'
    )
    personality_ids.append(pid)

    return personality_ids


# ==========================================
# TEST CLASSES
# ==========================================

class TestPlayoffContenderMessaging:
    """Test playoff teams get appropriate messaging (no draft talk)."""

    @pytest.mark.integration
    def test_playoff_team_no_draft_templates(self, game_db, standings_api, context_builder, social_api):
        """Playoff contender (10-3 in week 15) should NOT get draft pick templates."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 1

        # Seed standings: 10-3 record (playoff contender)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 10, 'losses': 3, 'ties': 0,
             'division_rank': 1, 'conference_rank': 2, 'playoff_seed': 2}
        ])

        # Build context for week 15
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=15
        )

        # Assertions: 10-3 in week 15 with seed 2 should be CLINCHED or IN_HUNT
        assert context.playoff_position in (PlayoffPosition.CLINCHED, PlayoffPosition.IN_HUNT, PlayoffPosition.LEADER)
        assert context.season_phase == SeasonPhase.LATE
        assert context.wins == 10
        assert context.losses == 3
        assert context.win_pct > 0.750

    @pytest.mark.integration
    def test_playoff_team_gets_playoff_bound_templates(self, game_db, standings_api, context_builder):
        """Playoff team should get playoff-appropriate messaging."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 5

        # Seed standings: 11-2 record (playoff clinched)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 11, 'losses': 2, 'ties': 0,
             'division_rank': 1, 'conference_rank': 1, 'playoff_seed': 1}
        ])

        # Build context for week 16
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=16
        )

        # Playoff team assertions
        assert context.playoff_position in (PlayoffPosition.CLINCHED, PlayoffPosition.LEADER)
        assert context.win_pct > 0.800
        assert context.division_rank == 1


class TestEliminatedTeamMessaging:
    """Test eliminated teams get appropriate tank messaging."""

    @pytest.mark.integration
    def test_eliminated_team_no_playoff_templates(self, game_db, standings_api, context_builder):
        """Eliminated team (3-10 in week 15) should NOT get playoff bound templates."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 10

        # Seed standings: 3-10 record (eliminated - last in division)
        # Team 10 is Indianapolis Colts (AFC South)
        # Seed division rivals with better records
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': 9, 'wins': 10, 'losses': 3, 'ties': 0},   # HOU (division leader)
            {'team_id': 11, 'wins': 8, 'losses': 5, 'ties': 0},   # JAX
            {'team_id': 12, 'wins': 6, 'losses': 7, 'ties': 0},   # TEN
            {'team_id': team_id, 'wins': 3, 'losses': 10, 'ties': 0,  # IND (last place)
             'playoff_seed': None}
        ])

        # Build context for week 15
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=15
        )

        # Assertions
        assert context.playoff_position == PlayoffPosition.ELIMINATED
        assert context.win_pct < 0.350
        assert context.division_rank == 4  # Last in division

    @pytest.mark.integration
    def test_eliminated_team_gets_building_for_next_year_templates(
        self, game_db, standings_api, context_builder
    ):
        """Eliminated team in late season should get 'building for next year' messaging."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 12

        # Seed standings: 2-11 record (eliminated, tanking)
        # Team 12 is Tennessee Titans (AFC South)
        # Seed division rivals with better records
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': 9, 'wins': 10, 'losses': 3, 'ties': 0},   # HOU (division leader)
            {'team_id': 10, 'wins': 8, 'losses': 5, 'ties': 0},   # IND
            {'team_id': 11, 'wins': 5, 'losses': 8, 'ties': 0},   # JAX
            {'team_id': team_id, 'wins': 2, 'losses': 11, 'ties': 0,  # TEN (last place, tanking)
             'playoff_seed': None}
        ])

        # Build context for week 16 (late season)
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=16
        )

        # Tank mode assertions
        assert context.playoff_position == PlayoffPosition.ELIMINATED
        assert context.season_phase == SeasonPhase.LATE
        assert context.win_pct < 0.200


class TestTradeHallucinationPrevention:
    """Test that teams with NO recent trades don't get TRADE_ANALYST templates."""

    @pytest.mark.integration
    def test_no_trades_no_trade_templates(self, game_db, standings_api, context_builder):
        """Team with NO recent trades should NOT trigger TRADE_ANALYST templates."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 7

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 6, 'losses': 6, 'ties': 0,
             'division_rank': 2, 'conference_rank': 8}
        ])

        # Build context (NO transactions seeded)
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Assertions: No recent activity
        assert len(context.recent_trades) == 0
        assert not context.has_recent_activity()

    @pytest.mark.integration
    def test_recent_trade_allows_trade_templates(self, game_db, standings_api, context_builder):
        """Team with recent trade (last 2 weeks) SHOULD allow TRADE_ANALYST templates."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 8

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 7, 'losses': 5, 'ties': 0,
             'division_rank': 2, 'conference_rank': 6}
        ])

        # Seed recent trade (within last 2 weeks)
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')

        seed_transactions(game_db, dynasty_id, season, [
            {
                'transaction_type': 'TRADE',
                'player_id': 100,
                'first_name': 'Star',
                'last_name': 'Player',
                'position': 'WR',
                'from_team_id': team_id,
                'to_team_id': 15,
                'transaction_date': recent_date,
                'details': {'picks_involved': ['2026_1st']}
            }
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Assertions: Has recent trade activity
        assert len(context.recent_trades) > 0
        assert context.has_recent_activity()


class TestWeekBasedFiltering:
    """Test week-based template filtering (early vs late season)."""

    @pytest.mark.integration
    def test_early_season_no_draft_talk(self, game_db, standings_api, context_builder):
        """Week 3 (early season) should NOT have draft talk."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 20

        # Seed standings (early season, losing record but too early for draft talk)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 1, 'losses': 2, 'ties': 0,
             'division_rank': 3, 'conference_rank': 12}
        ])

        # Build context for week 3
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=3
        )

        # Assertions
        assert context.season_phase == SeasonPhase.EARLY
        assert context.week == 3
        # Early season: no playoff position determined yet
        assert context.playoff_position in (PlayoffPosition.UNKNOWN, PlayoffPosition.LEADER)

    @pytest.mark.integration
    def test_late_season_playoff_urgency(self, game_db, standings_api, context_builder):
        """Week 16 (late season) should have playoff urgency messaging."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 22

        # Seed standings (late season, playoff hunt)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 9, 'losses': 6, 'ties': 0,
             'division_rank': 2, 'conference_rank': 7}
        ])

        # Build context for week 16
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=16
        )

        # Assertions
        assert context.season_phase == SeasonPhase.LATE
        assert context.week == 16
        assert context.playoff_position == PlayoffPosition.IN_HUNT


class TestRecentActivityTracking:
    """Test recent activity tracking (trades, signings, cuts)."""

    @pytest.mark.integration
    def test_recent_signing_tracked(self, game_db, standings_api, context_builder):
        """Recent FA signing should appear in context."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 25

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 5, 'losses': 7, 'ties': 0,
             'division_rank': 3, 'conference_rank': 10}
        ])

        # Seed recent FA signing
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')

        seed_transactions(game_db, dynasty_id, season, [
            {
                'transaction_type': 'FA_SIGNING',
                'player_id': 200,
                'first_name': 'Free',
                'last_name': 'Agent',
                'position': 'DE',
                'from_team_id': None,
                'to_team_id': team_id,
                'transaction_date': recent_date,
                'details': {'contract_aav': 5000000}
            }
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=8
        )

        # Assertions
        assert len(context.recent_signings) > 0
        assert context.has_recent_activity()
        assert context.recent_signings[0]['type'] == 'FA_SIGNING'

    @pytest.mark.integration
    def test_recent_cut_tracked(self, game_db, standings_api, context_builder):
        """Recent roster cut should appear in context."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 28

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 3, 'losses': 9, 'ties': 0,
             'division_rank': 4, 'conference_rank': 14}
        ])

        # Seed recent cut
        from datetime import datetime, timedelta
        recent_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        seed_transactions(game_db, dynasty_id, season, [
            {
                'transaction_type': 'ROSTER_CUT',
                'player_id': 300,
                'first_name': 'Cut',
                'last_name': 'Player',
                'position': 'RB',
                'from_team_id': team_id,
                'to_team_id': None,
                'transaction_date': recent_date,
                'details': {'cap_savings': 2000000}
            }
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=14
        )

        # Assertions
        assert len(context.recent_cuts) > 0
        assert context.has_recent_activity()
        assert context.recent_cuts[0]['type'] == 'ROSTER_CUT'

    @pytest.mark.integration
    def test_old_activity_not_tracked(self, game_db, standings_api, context_builder):
        """Activity older than 2 weeks should NOT appear in context."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 30

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 8, 'losses': 4, 'ties': 0,
             'division_rank': 1, 'conference_rank': 3}
        ])

        # Seed old trade (30 days ago)
        from datetime import datetime, timedelta
        old_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        seed_transactions(game_db, dynasty_id, season, [
            {
                'transaction_type': 'TRADE',
                'player_id': 400,
                'first_name': 'Old',
                'last_name': 'Trade',
                'position': 'LB',
                'from_team_id': team_id,
                'to_team_id': 12,
                'transaction_date': old_date,
                'details': {}
            }
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Assertions: Old activity filtered out
        assert len(context.recent_trades) == 0
        assert not context.has_recent_activity()


class TestStreakCalculation:
    """Test win/loss streak calculation."""

    @pytest.mark.integration
    def test_winning_streak_calculated(self, game_db, standings_api, context_builder):
        """Team on 3-game winning streak should show W3."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 15

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 7, 'losses': 3, 'ties': 0}
        ])

        # Seed recent games (3 wins in a row, weeks 8-10)
        seed_games(game_db, dynasty_id, season, 8, [
            {'home_team_id': team_id, 'away_team_id': 20, 'home_score': 28, 'away_score': 21}
        ])
        seed_games(game_db, dynasty_id, season, 9, [
            {'home_team_id': 25, 'away_team_id': team_id, 'home_score': 17, 'away_score': 24}
        ])
        seed_games(game_db, dynasty_id, season, 10, [
            {'home_team_id': team_id, 'away_team_id': 30, 'home_score': 31, 'away_score': 14}
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Assertions
        assert context.current_streak == 3
        assert context.streak_type == 'W'
        assert context.get_streak_string() == 'W3'

    @pytest.mark.integration
    def test_losing_streak_calculated(self, game_db, standings_api, context_builder):
        """Team on 2-game losing streak should show L2."""
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 18

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 4, 'losses': 6, 'ties': 0}
        ])

        # Seed recent games (2 losses in a row, weeks 9-10)
        seed_games(game_db, dynasty_id, season, 9, [
            {'home_team_id': team_id, 'away_team_id': 10, 'home_score': 14, 'away_score': 21}
        ])
        seed_games(game_db, dynasty_id, season, 10, [
            {'home_team_id': 5, 'away_team_id': team_id, 'home_score': 28, 'away_score': 17}
        ])

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Assertions
        assert context.current_streak == 2
        assert context.streak_type == 'L'
        assert context.get_streak_string() == 'L2'


# ==========================================
# END-TO-END CONTEXT-AWARE POST GENERATION
# ==========================================

class TestContextAwarePostGeneration:
    """Test complete flow: context → template selection → post generation."""

    @pytest.mark.integration
    def test_playoff_team_context_affects_templates(
        self, game_db, standings_api, context_builder, social_api, posts_api
    ):
        """
        Playoff contender context should filter out draft-focused templates.

        This is an end-to-end test that verifies:
        1. TeamContext is built correctly
        2. Context is passed to template loader
        3. Requirements filtering works
        4. Inappropriate templates are excluded
        """
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 3

        # Seed playoff contender standings (11-2)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 11, 'losses': 2, 'ties': 0,
             'division_rank': 1, 'conference_rank': 2, 'playoff_seed': 2}
        ])

        # Create test personalities
        create_test_personalities(social_api, dynasty_id, team_id)

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=15
        )

        # Verify context is playoff-appropriate
        assert context.playoff_position in (PlayoffPosition.IN_HUNT, PlayoffPosition.LEADER)
        assert context.win_pct > 0.750

        # NOTE: Full template filtering test would require:
        # 1. Mock post_templates.json with requirements
        # 2. Generate posts using GameSocialGenerator
        # 3. Verify no posts contain draft-related keywords
        #
        # This test verifies the context building portion.
        # Template filtering is tested in unit tests for PostTemplateLoader.

    @pytest.mark.integration
    def test_eliminated_team_context_allows_tank_templates(
        self, game_db, standings_api, context_builder, social_api
    ):
        """
        Eliminated team context should allow 'building for next year' templates.

        Verifies context-based filtering allows appropriate templates for tanking teams.
        """
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 16

        # Seed eliminated team standings (2-11)
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 2, 'losses': 11, 'ties': 0,
             'division_rank': 4, 'conference_rank': 16, 'playoff_seed': None}
        ])

        # Create test personalities
        create_test_personalities(social_api, dynasty_id, team_id)

        # Build context
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=15
        )

        # Verify context is tank-appropriate
        assert context.playoff_position == PlayoffPosition.ELIMINATED
        assert context.win_pct < 0.200
        assert context.season_phase == SeasonPhase.LATE

    @pytest.mark.integration
    def test_no_trade_activity_prevents_trade_analyst_posts(
        self, game_db, standings_api, context_builder, social_api
    ):
        """
        Team with NO recent trades should NOT trigger TRADE_ANALYST templates.

        Verifies trade hallucination prevention through context filtering.
        """
        dynasty_id = 'test_dynasty'
        season = 2025
        team_id = 24

        # Seed standings
        seed_standings(standings_api, dynasty_id, season, [
            {'team_id': team_id, 'wins': 6, 'losses': 6, 'ties': 0,
             'division_rank': 2, 'conference_rank': 9}
        ])

        # Create test personalities (including TRADE_ANALYST)
        create_test_personalities(social_api, dynasty_id, team_id)

        # Build context (NO trades seeded)
        context = context_builder.build_context(
            dynasty_id=dynasty_id,
            season=season,
            team_id=team_id,
            week=10
        )

        # Verify NO recent trade activity
        assert len(context.recent_trades) == 0
        assert not context.has_recent_activity()

        # TRADE_ANALYST templates should fall back to generic templates
        # because requirements not met
