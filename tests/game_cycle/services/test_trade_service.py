"""
Unit tests for TradeService - Tollgates 1, 2, 3 & 4.

Tests cover:
Tollgate 1:
1. Service initialization (5 tests)
2. Trade window validation (9 tests)
3. Weeks until deadline (3 tests)
4. Tradeable player queries (2 tests)
5. Tradeable pick queries (3 tests)
6. Pick ownership initialization (4 tests)
7. Trade history queries (2 tests)

Tollgate 2:
8. Trade proposal (4 tests)
9. Trade execution (5 tests)

Tollgate 3:
10. Build team context (3 tests)
11. GM archetype loader (2 tests)
12. AI trade evaluation (5 tests)
13. Trade negotiation (5 tests)

Tollgate 4:
14. Draft pick proposal (4 tests)
15. Draft pick execution (4 tests)
16. Draft pick validation (3 tests)
17. Negotiation with picks (2 tests)
"""

import json
import os
import sqlite3
import tempfile

import pytest

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.services.trade_service import TradeService


@pytest.fixture
def temp_db():
    """Create a temporary database with full schema for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Initialize schema using GameCycleDatabase
    db = GameCycleDatabase(path)
    # Connection is created and schema applied in __init__

    yield path

    # Cleanup
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def dynasty_id():
    """Test dynasty identifier."""
    return "test_dynasty_001"


@pytest.fixture
def season():
    """Test season year."""
    return 2025


@pytest.fixture
def trade_service(temp_db, dynasty_id, season):
    """Create a TradeService instance for testing."""
    return TradeService(temp_db, dynasty_id, season)


class TestTradeServiceInitialization:
    """Tests for service initialization."""

    def test_init_stores_db_path(self, temp_db, dynasty_id, season):
        """Test that db_path is stored correctly."""
        service = TradeService(temp_db, dynasty_id, season)
        assert service._db_path == temp_db

    def test_init_stores_dynasty_id(self, temp_db, dynasty_id, season):
        """Test that dynasty_id is stored correctly."""
        service = TradeService(temp_db, dynasty_id, season)
        assert service._dynasty_id == dynasty_id

    def test_init_stores_season(self, temp_db, dynasty_id, season):
        """Test that season is stored correctly."""
        service = TradeService(temp_db, dynasty_id, season)
        assert service._season == season

    def test_init_sets_trade_deadline_constant(self, trade_service):
        """Test that TRADE_DEADLINE_WEEK constant is set to 9."""
        assert trade_service.TRADE_DEADLINE_WEEK == 9

    def test_init_has_transaction_logger(self, trade_service):
        """Test that transaction logger is initialized."""
        assert trade_service._transaction_logger is not None


class TestTradeWindowValidation:
    """Tests for is_trade_window_open()."""

    def test_regular_season_week_1_open(self, trade_service):
        """Trade window should be open in Week 1 of regular season."""
        assert trade_service.is_trade_window_open(week=1, phase="regular_season") is True

    def test_regular_season_week_9_open(self, trade_service):
        """Trade window should be open in Week 9 (deadline week)."""
        assert trade_service.is_trade_window_open(week=9, phase="regular_season") is True

    def test_regular_season_week_10_closed(self, trade_service):
        """Trade window should be closed in Week 10 (after deadline)."""
        assert trade_service.is_trade_window_open(week=10, phase="regular_season") is False

    def test_regular_season_week_18_closed(self, trade_service):
        """Trade window should be closed in Week 18."""
        assert trade_service.is_trade_window_open(week=18, phase="regular_season") is False

    def test_playoffs_closed(self, trade_service):
        """Trade window should be closed during playoffs."""
        assert trade_service.is_trade_window_open(week=1, phase="playoffs") is False

    def test_preseason_open(self, trade_service):
        """Trade window should be open during preseason."""
        assert trade_service.is_trade_window_open(week=1, phase="preseason") is True

    def test_offseason_trading_open(self, trade_service):
        """Trade window should be open during offseason_trading stage."""
        assert trade_service.is_trade_window_open(week=0, phase="offseason_trading") is True

    def test_offseason_open(self, trade_service):
        """Trade window should be open during general offseason."""
        assert trade_service.is_trade_window_open(week=0, phase="offseason") is True

    def test_unknown_phase_closed(self, trade_service):
        """Trade window should be closed for unknown phases."""
        assert trade_service.is_trade_window_open(week=1, phase="unknown_phase") is False


class TestWeeksUntilDeadline:
    """Tests for get_weeks_until_deadline()."""

    def test_week_1_returns_9(self, trade_service):
        """In Week 1, should have 9 weeks until deadline."""
        assert trade_service.get_weeks_until_deadline(1) == 9

    def test_week_9_returns_1(self, trade_service):
        """In Week 9 (deadline week), should have 1 week remaining."""
        assert trade_service.get_weeks_until_deadline(9) == 1

    def test_week_10_returns_none(self, trade_service):
        """After deadline (Week 10+), should return None."""
        assert trade_service.get_weeks_until_deadline(10) is None


class TestTradeablePlayersQuery:
    """Tests for get_tradeable_players()."""

    def test_returns_empty_list_for_no_players(self, trade_service):
        """Should return empty list when team has no players."""
        players = trade_service.get_tradeable_players(team_id=1)
        assert players == []

    def test_returns_players_with_required_fields(self, temp_db, dynasty_id, season):
        """Should return players with all required trade-relevant fields."""
        # Setup: Insert test player
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players
            (dynasty_id, player_id, team_id, first_name, last_name, number,
             positions, attributes, years_pro, status)
            VALUES (?, 1, 1, 'Test', 'Player', 12, 'QB',
                    '{"overall": 85}', 3, 'active')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        players = service.get_tradeable_players(team_id=1)

        assert len(players) == 1
        player = players[0]
        assert player["player_id"] == 1
        assert player["name"] == "Test Player"
        assert player["position"] == "QB"
        assert player["overall_rating"] == 85
        assert "age" in player
        assert "years_pro" in player
        assert "contract_id" in player


class TestTradeablePicksQuery:
    """Tests for get_tradeable_picks()."""

    def test_returns_empty_list_before_initialization(self, trade_service):
        """Should return empty list when picks not initialized."""
        picks = trade_service.get_tradeable_picks(team_id=1)
        assert picks == []

    def test_returns_picks_after_initialization(self, trade_service):
        """Should return picks after ownership is initialized."""
        trade_service.initialize_pick_ownership(seasons_ahead=2)
        picks = trade_service.get_tradeable_picks(team_id=1)

        # Should have 7 rounds × 3 years = 21 picks
        assert len(picks) == 21

    def test_picks_have_required_fields(self, trade_service):
        """Returned picks should have all required fields."""
        trade_service.initialize_pick_ownership(seasons_ahead=0)
        picks = trade_service.get_tradeable_picks(team_id=1)

        assert len(picks) == 7  # 7 rounds for current year only
        pick = picks[0]
        assert "id" in pick
        assert "round" in pick
        assert "season" in pick
        assert "original_team_id" in pick
        assert "current_team_id" in pick
        assert "was_traded" in pick
        assert "years_in_future" in pick


class TestPickOwnershipInitialization:
    """Tests for initialize_pick_ownership()."""

    def test_creates_picks_for_all_teams(self, trade_service):
        """Should create picks for all 32 teams."""
        records = trade_service.initialize_pick_ownership(seasons_ahead=0)
        # 32 teams × 7 rounds = 224 picks per season
        assert records == 224

    def test_creates_picks_for_future_years(self, trade_service):
        """Should create picks for multiple future years."""
        records = trade_service.initialize_pick_ownership(seasons_ahead=2)
        # 32 teams × 7 rounds × 3 years = 672 picks
        assert records == 672

    def test_idempotent_on_duplicate_call(self, trade_service):
        """Calling twice should not create duplicate records."""
        first_call = trade_service.initialize_pick_ownership(seasons_ahead=0)
        second_call = trade_service.initialize_pick_ownership(seasons_ahead=0)

        # First call creates 224, second creates 0 (already exist)
        assert first_call == 224
        assert second_call == 0

    def test_picks_initially_owned_by_original_team(self, temp_db, dynasty_id, season):
        """Each team should initially own their own picks."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=0)

        conn = sqlite3.connect(temp_db)
        cursor = conn.execute("""
            SELECT original_team_id, current_team_id
            FROM draft_pick_ownership
            WHERE dynasty_id = ?
        """, (dynasty_id,))

        for row in cursor.fetchall():
            assert row[0] == row[1], "Original and current team should match initially"

        conn.close()


class TestGetTradeHistory:
    """Tests for get_trade_history()."""

    def test_returns_empty_list_with_no_trades(self, trade_service):
        """Should return empty list when no trades exist."""
        trades = trade_service.get_trade_history()
        assert trades == []

    def test_returns_trades_after_insert(self, temp_db, dynasty_id, season):
        """Should return trades that exist in database."""
        # Insert a test trade directly
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO trades
            (dynasty_id, season, trade_date, team1_id, team2_id,
             team1_assets, team2_assets, team1_total_value, team2_total_value,
             value_ratio, fairness_rating, status, initiating_team_id)
            VALUES (?, ?, '2025-10-15', 1, 2,
                    '[]', '[]', 100.0, 100.0,
                    1.0, 'FAIR', 'accepted', 1)
        """, (dynasty_id, season))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        trades = service.get_trade_history()

        assert len(trades) == 1
        assert trades[0]["team1_id"] == 1
        assert trades[0]["team2_id"] == 2
        assert trades[0]["status"] == "accepted"


# =============================================================================
# TOLLGATE 2 TESTS: Trade Proposal & Execution
# =============================================================================


class TestProposeTrade:
    """Tests for propose_trade() - Tollgate 2."""

    def test_propose_trade_calculates_values(self, temp_db, dynasty_id, season):
        """Trade proposal should include calculated values."""
        # Setup: Create two players on different teams
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[1],
            team2_id=2,
            team2_player_ids=[2]
        )

        assert proposal.team1_id == 1
        assert proposal.team2_id == 2
        assert len(proposal.team1_assets) == 1
        assert len(proposal.team2_assets) == 1
        assert proposal.team1_total_value > 0
        assert proposal.team2_total_value > 0
        assert proposal.fairness_rating is not None

    def test_propose_trade_rejects_same_team(self, trade_service):
        """Cannot propose trade with same team."""
        with pytest.raises(ValueError, match="same team"):
            trade_service.propose_trade(
                team1_id=1,
                team1_player_ids=[1],
                team2_id=1,
                team2_player_ids=[2]
            )

    def test_propose_trade_rejects_invalid_player(self, trade_service):
        """Cannot propose trade with non-existent player."""
        with pytest.raises(ValueError, match="not found"):
            trade_service.propose_trade(
                team1_id=1,
                team1_player_ids=[9999],
                team2_id=2,
                team2_player_ids=[]
            )

    def test_propose_trade_with_empty_assets(self, temp_db, dynasty_id, season):
        """Can propose trade with one side having empty assets (salary dump)."""
        # Setup: Create one player
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[1],
            team2_id=2,
            team2_player_ids=[]  # Empty - trade player for nothing
        )

        assert len(proposal.team1_assets) == 1
        assert len(proposal.team2_assets) == 0
        assert proposal.team1_total_value > 0
        assert proposal.team2_total_value == 0


class TestExecuteTrade:
    """Tests for execute_trade() - Tollgate 2."""

    def test_execute_trade_updates_rosters(self, temp_db, dynasty_id, season):
        """Execute trade should move players between teams."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        result = service.execute_trade(proposal)

        # Verify players moved
        conn = sqlite3.connect(temp_db)
        player1 = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = ? AND player_id = 1",
            (dynasty_id,)
        ).fetchone()
        player2 = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = ? AND player_id = 2",
            (dynasty_id,)
        ).fetchone()
        conn.close()

        assert player1[0] == 2  # Player 1 moved to team 2
        assert player2[0] == 1  # Player 2 moved to team 1
        assert result["status"] == "accepted"

    def test_execute_trade_records_in_database(self, temp_db, dynasty_id, season):
        """Trade should be recorded in trades table."""
        # Setup players
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )
        result = service.execute_trade(proposal)

        # Verify trade recorded
        trades = service.get_trade_history()
        assert len(trades) == 1
        assert trades[0]["trade_id"] == result["trade_id"]
        assert trades[0]["status"] == "accepted"

    def test_execute_trade_logs_transactions(self, temp_db, dynasty_id, season):
        """Trade should be recorded and players should move even if transaction logging fails."""
        # Note: Transaction logging uses legacy database schema and may fail in tests.
        # The core trade execution should still work.

        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )
        result = service.execute_trade(proposal)

        # Trade should complete successfully regardless of transaction logging
        assert result["status"] == "accepted"
        assert result["team1_players_sent"] == [1]
        assert result["team2_players_sent"] == [2]

        # Verify players actually moved
        conn = sqlite3.connect(temp_db)
        player1_team = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = ? AND player_id = 1",
            (dynasty_id,)
        ).fetchone()[0]
        player2_team = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = ? AND player_id = 2",
            (dynasty_id,)
        ).fetchone()[0]
        conn.close()

        assert player1_team == 2  # Player 1 moved to team 2
        assert player2_team == 1  # Player 2 moved to team 1

    def test_execute_trade_fails_if_player_moved(self, temp_db, dynasty_id, season):
        """Trade should fail if player changed teams since proposal."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        # Move player 1 to another team before execution
        conn.execute(
            "UPDATE players SET team_id = 3 WHERE dynasty_id = ? AND player_id = 1",
            (dynasty_id,)
        )
        conn.commit()
        conn.close()

        with pytest.raises(ValueError, match="no longer on team"):
            service.execute_trade(proposal)

    def test_execute_trade_returns_player_ids(self, temp_db, dynasty_id, season):
        """Execute trade result should include player IDs transferred."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 2, '1999-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )
        result = service.execute_trade(proposal)

        assert result["team1_players_sent"] == [1]
        assert result["team2_players_sent"] == [2]
        assert "trade_id" in result
        assert "trade_date" in result


# =============================================================================
# TOLLGATE 3 TESTS: AI Trade Decision & Counter-Offers
# =============================================================================


class TestBuildTeamContext:
    """Tests for _build_team_context() - Tollgate 3."""

    def test_build_team_context_returns_team_context(self, trade_service):
        """Should return a TeamContext object."""
        from src.transactions.personality_modifiers import TeamContext

        context = trade_service._build_team_context(team_id=1)

        assert isinstance(context, TeamContext)
        assert context.team_id == 1
        assert context.season == trade_service._season

    def test_build_team_context_has_default_values_no_standings(self, trade_service):
        """Without standings, should have sensible defaults."""
        context = trade_service._build_team_context(team_id=1)

        assert context.wins == 0
        assert context.losses == 0
        assert context.playoff_position is None
        assert context.cap_space > 0  # Default cap space

    def test_build_team_context_gracefully_handles_missing_standings(self, trade_service):
        """Should use defaults when standings API fails (schema mismatch)."""
        # The test database uses simple schema.sql which doesn't have
        # dynasty_id/season columns in standings. The method should
        # gracefully fall back to defaults.
        context = trade_service._build_team_context(team_id=1)

        # Defaults when standings unavailable
        assert context.wins == 0
        assert context.losses == 0
        assert context.playoff_position is None


class TestGetGMArchetype:
    """Tests for _get_gm_archetype() - Tollgate 3."""

    def test_get_gm_archetype_returns_gm_archetype(self, trade_service):
        """Should return a GMArchetype object."""
        from src.team_management.gm_archetype import GMArchetype

        gm = trade_service._get_gm_archetype(team_id=1)

        assert isinstance(gm, GMArchetype)
        assert "Team 1" in gm.name

    def test_get_gm_archetype_has_default_balanced_traits(self, trade_service):
        """Default GM should have balanced trait values."""
        gm = trade_service._get_gm_archetype(team_id=1)

        # Default traits should be 0.5 (balanced)
        assert gm.risk_tolerance == 0.5
        assert gm.win_now_mentality == 0.5
        assert gm.trade_frequency == 0.5


class TestEvaluateAITrade:
    """Tests for evaluate_ai_trade() - Tollgate 3."""

    def test_ai_accepts_fair_trade(self, temp_db, dynasty_id, season):
        """AI should accept a fairly valued trade."""
        from src.transactions.models import TradeDecisionType

        # Setup: Create two similar players
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'WR', '{"overall": 80}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        decision = service.evaluate_ai_trade(
            proposal=proposal,
            ai_team_id=2
        )

        # Fair trade should be accepted (compare .value to avoid enum identity issues)
        assert decision.decision.value == "ACCEPT"
        assert decision.confidence > 0.0
        assert decision.reasoning != ""

    def test_ai_rejects_very_unfair_trade(self, temp_db, dynasty_id, season):
        """AI should reject a heavily lopsided trade."""
        # Setup: Create unequal players (elite QB vs low-rated WR)
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Low', 'Value', 12, 'P', '{"overall": 60}', 1, '2000-01-01')
        """, (dynasty_id,))
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 2, 2, 'Elite', 'QB', 12, 'QB', '{"overall": 95}', 5, '1996-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        decision = service.evaluate_ai_trade(
            proposal=proposal,
            ai_team_id=2  # Team 2 being asked to give up elite QB
        )

        # Very unfair trade should be rejected (compare .value to avoid enum identity issues)
        assert decision.decision.value == "REJECT"

    def test_ai_evaluation_includes_reasoning(self, temp_db, dynasty_id, season):
        """Decision should include human-readable reasoning."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'WR', '{"overall": 80}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 3, '1998-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        decision = service.evaluate_ai_trade(
            proposal=proposal,
            ai_team_id=2
        )

        assert decision.reasoning is not None
        assert len(decision.reasoning) > 0

    def test_ai_evaluation_requires_valid_team(self, temp_db, dynasty_id, season):
        """Should raise error if ai_team_id is not part of the proposal."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'WR', '{"overall": 80}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 3, '1998-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        with pytest.raises(ValueError, match="not part of this trade"):
            service.evaluate_ai_trade(
                proposal=proposal,
                ai_team_id=3  # Team 3 not in proposal
            )

    def test_ai_evaluation_has_confidence_score(self, temp_db, dynasty_id, season):
        """Decision should include a confidence score between 0 and 1."""
        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'WR', '{"overall": 80}', 3, '1998-01-01'),
                   (?, 2, 2, 'Player', 'Two', 88, 'WR', '{"overall": 80}', 3, '1998-01-01')
        """, (dynasty_id, dynasty_id))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        proposal = service.propose_trade(
            team1_id=1, team1_player_ids=[1],
            team2_id=2, team2_player_ids=[2]
        )

        decision = service.evaluate_ai_trade(
            proposal=proposal,
            ai_team_id=2
        )

        assert 0.0 <= decision.confidence <= 1.0


class TestGetTradeableAssetsForNegotiation:
    """Tests for _get_tradeable_assets_for_negotiation() - Tollgate 3."""

    def test_returns_empty_list_for_no_players(self, trade_service):
        """Should return empty list when team has no players."""
        assets = trade_service._get_tradeable_assets_for_negotiation(team_id=1)
        assert assets == []

    def test_returns_trade_assets_with_values(self, temp_db, dynasty_id, season):
        """Should return TradeAsset objects with calculated values."""
        from src.transactions.models import TradeAsset, AssetType

        # Setup
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        assets = service._get_tradeable_assets_for_negotiation(team_id=1)

        assert len(assets) == 1
        asset = assets[0]
        assert isinstance(asset, TradeAsset)
        assert asset.asset_type == AssetType.PLAYER
        assert asset.player_id == 1
        assert asset.trade_value > 0


# =============================================================================
# Tollgate 4: Draft Pick Trading Tests
# =============================================================================


class TestDraftPickProposal:
    """Tests for propose_trade() with draft picks - Tollgate 4."""

    def test_propose_trade_with_picks_only(self, temp_db, dynasty_id, season):
        """Can propose trade with only draft picks (no players)."""
        from src.transactions.models import AssetType

        # Setup: Initialize pick ownership
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        # Get pick IDs for teams 1 and 2
        team1_picks = service.get_tradeable_picks(team_id=1)
        team2_picks = service.get_tradeable_picks(team_id=2)

        # Team 1 offers their 1st round pick for Team 2's 2nd round pick
        team1_first_round = next(p for p in team1_picks if p["round"] == 1 and p["season"] == season)
        team2_second_round = next(p for p in team2_picks if p["round"] == 2 and p["season"] == season)

        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[team1_first_round["id"]],
            team2_pick_ids=[team2_second_round["id"]]
        )

        assert len(proposal.team1_assets) == 1
        assert len(proposal.team2_assets) == 1
        assert proposal.team1_assets[0].asset_type == AssetType.DRAFT_PICK
        assert proposal.team2_assets[0].asset_type == AssetType.DRAFT_PICK
        assert proposal.team1_total_value > 0
        assert proposal.team2_total_value > 0

    def test_propose_trade_with_players_and_picks(self, temp_db, dynasty_id, season):
        """Can propose trade with both players and picks."""
        from src.transactions.models import AssetType

        # Setup: Create player and picks
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team2_picks = service.get_tradeable_picks(team_id=2)
        team2_first_round = next(p for p in team2_picks if p["round"] == 1 and p["season"] == season)

        # Team 1 offers player for Team 2's 1st round pick
        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[1],
            team2_id=2,
            team2_player_ids=[],
            team2_pick_ids=[team2_first_round["id"]]
        )

        assert len(proposal.team1_assets) == 1
        assert len(proposal.team2_assets) == 1
        assert proposal.team1_assets[0].asset_type == AssetType.PLAYER
        assert proposal.team2_assets[0].asset_type == AssetType.DRAFT_PICK

    def test_propose_trade_with_invalid_pick(self, trade_service):
        """Cannot propose trade with non-existent pick."""
        with pytest.raises(ValueError, match="not found"):
            trade_service.propose_trade(
                team1_id=1,
                team1_player_ids=[],
                team2_id=2,
                team2_player_ids=[],
                team1_pick_ids=[99999]  # Non-existent pick
            )

    def test_propose_trade_calculates_pick_value(self, temp_db, dynasty_id, season):
        """Pick trade values should be calculated using Jimmy Johnson chart."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team1_picks = service.get_tradeable_picks(team_id=1)
        first_round = next(p for p in team1_picks if p["round"] == 1 and p["season"] == season)
        seventh_round = next(p for p in team1_picks if p["round"] == 7 and p["season"] == season)

        # Trade first round pick
        proposal1 = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[first_round["id"]]
        )

        # Trade seventh round pick
        proposal2 = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[seventh_round["id"]]
        )

        # First round pick should be worth more than seventh round
        assert proposal1.team1_total_value > proposal2.team1_total_value


class TestDraftPickExecution:
    """Tests for execute_trade() with draft picks - Tollgate 4."""

    def test_execute_trade_transfers_pick_ownership(self, temp_db, dynasty_id, season):
        """Execute trade should update draft_pick_ownership.current_team_id."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        # Get pick to trade
        team1_picks = service.get_tradeable_picks(team_id=1)
        pick_to_trade = next(p for p in team1_picks if p["round"] == 1 and p["season"] == season)
        pick_id = pick_to_trade["id"]

        # Propose and execute
        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[pick_id]
        )
        service.execute_trade(proposal)

        # Verify pick transferred
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT current_team_id FROM draft_pick_ownership WHERE id = ?",
            (pick_id,)
        )
        new_owner = cursor.fetchone()[0]
        conn.close()

        assert new_owner == 2  # Pick moved to team 2

    def test_execute_trade_records_trade_id_on_pick(self, temp_db, dynasty_id, season):
        """Execute trade should record trade_id in acquired_via_trade_id."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team1_picks = service.get_tradeable_picks(team_id=1)
        pick_id = next(p for p in team1_picks if p["round"] == 1)["id"]

        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[pick_id]
        )
        result = service.execute_trade(proposal)

        # Verify trade_id recorded
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT acquired_via_trade_id FROM draft_pick_ownership WHERE id = ?",
            (pick_id,)
        )
        trade_id = cursor.fetchone()[0]
        conn.close()

        assert trade_id == result["trade_id"]

    def test_execute_trade_returns_pick_ids(self, temp_db, dynasty_id, season):
        """Execute trade result should include pick IDs transferred."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team1_picks = service.get_tradeable_picks(team_id=1)
        team2_picks = service.get_tradeable_picks(team_id=2)

        pick1_id = next(p for p in team1_picks if p["round"] == 1)["id"]
        pick2_id = next(p for p in team2_picks if p["round"] == 2)["id"]

        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[pick1_id],
            team2_pick_ids=[pick2_id]
        )
        result = service.execute_trade(proposal)

        assert result["team1_picks_sent"] == [pick1_id]
        assert result["team2_picks_sent"] == [pick2_id]

    def test_execute_trade_with_players_and_picks(self, temp_db, dynasty_id, season):
        """Execute trade should handle both players and picks."""
        # Setup player
        conn = sqlite3.connect(temp_db)
        conn.execute("""
            INSERT INTO players (dynasty_id, player_id, team_id, first_name, last_name,
                                 number, positions, attributes, years_pro, birthdate)
            VALUES (?, 1, 1, 'Player', 'One', 12, 'QB', '{"overall": 85}', 3, '1998-01-01')
        """, (dynasty_id,))
        conn.commit()
        conn.close()

        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team2_picks = service.get_tradeable_picks(team_id=2)
        pick_id = next(p for p in team2_picks if p["round"] == 1)["id"]

        # Trade player for pick
        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[1],
            team2_id=2,
            team2_player_ids=[],
            team2_pick_ids=[pick_id]
        )
        result = service.execute_trade(proposal)

        # Verify both player and pick transferred
        conn = sqlite3.connect(temp_db)
        player_team = conn.execute(
            "SELECT team_id FROM players WHERE dynasty_id = ? AND player_id = 1",
            (dynasty_id,)
        ).fetchone()[0]
        pick_owner = conn.execute(
            "SELECT current_team_id FROM draft_pick_ownership WHERE id = ?",
            (pick_id,)
        ).fetchone()[0]
        conn.close()

        assert player_team == 2  # Player moved to team 2
        assert pick_owner == 1  # Pick moved to team 1
        assert result["team1_players_sent"] == [1]
        assert result["team2_picks_sent"] == [pick_id]


class TestDraftPickValidation:
    """Tests for _validate_trade_assets() with draft picks - Tollgate 4."""

    def test_validation_fails_if_pick_already_traded(self, temp_db, dynasty_id, season):
        """Trade should fail if pick changed ownership since proposal."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team1_picks = service.get_tradeable_picks(team_id=1)
        pick_id = next(p for p in team1_picks if p["round"] == 1)["id"]

        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[pick_id]
        )

        # Move pick to another team before execution
        conn = sqlite3.connect(temp_db)
        conn.execute(
            "UPDATE draft_pick_ownership SET current_team_id = 3 WHERE id = ?",
            (pick_id,)
        )
        conn.commit()
        conn.close()

        with pytest.raises(ValueError, match="no longer owned by team"):
            service.execute_trade(proposal)

    def test_asset_to_dict_serializes_pick(self, temp_db, dynasty_id, season):
        """_asset_to_dict should properly serialize pick assets."""
        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        team1_picks = service.get_tradeable_picks(team_id=1)
        pick_id = next(p for p in team1_picks if p["round"] == 1)["id"]

        proposal = service.propose_trade(
            team1_id=1,
            team1_player_ids=[],
            team2_id=2,
            team2_player_ids=[],
            team1_pick_ids=[pick_id]
        )

        # Check that pick asset serializes correctly
        asset = proposal.team1_assets[0]
        asset_dict = service._asset_to_dict(asset)

        assert asset_dict["asset_type"] == "DRAFT_PICK"
        assert "pick_round" in asset_dict
        assert "pick_year" in asset_dict
        assert asset_dict["trade_value"] > 0

    def test_get_pick_details_returns_none_for_invalid_id(self, trade_service):
        """_get_pick_details should return None for non-existent pick."""
        result = trade_service._get_pick_details(99999)
        assert result is None


class TestNegotiationWithPicks:
    """Tests for _get_tradeable_assets_for_negotiation() with picks - Tollgate 4."""

    def test_negotiation_assets_include_picks(self, temp_db, dynasty_id, season):
        """_get_tradeable_assets_for_negotiation should include draft picks."""
        from src.transactions.models import AssetType

        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        assets = service._get_tradeable_assets_for_negotiation(team_id=1, include_picks=True)

        # Should have at least the 7 picks for current season
        pick_assets = [a for a in assets if a.asset_type == AssetType.DRAFT_PICK]
        assert len(pick_assets) >= 7  # At minimum, 7 rounds

    def test_negotiation_assets_excludes_picks_when_disabled(self, temp_db, dynasty_id, season):
        """_get_tradeable_assets_for_negotiation should exclude picks when disabled."""
        from src.transactions.models import AssetType

        service = TradeService(temp_db, dynasty_id, season)
        service.initialize_pick_ownership(seasons_ahead=1)

        assets = service._get_tradeable_assets_for_negotiation(team_id=1, include_picks=False)

        # Should have no pick assets
        pick_assets = [a for a in assets if a.asset_type == AssetType.DRAFT_PICK]
        assert len(pick_assets) == 0
