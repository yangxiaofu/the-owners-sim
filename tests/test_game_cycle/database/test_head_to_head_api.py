"""
Tests for HeadToHeadAPI and HeadToHeadRecord.

Part of Milestone 11: Schedule & Rivalries, Tollgate 2.
Covers dataclass validation, CRUD operations, streak logic, and dynasty isolation.
"""
import pytest
import sqlite3
import tempfile
import os

from src.game_cycle.models.head_to_head import HeadToHeadRecord
from src.game_cycle.database.head_to_head_api import HeadToHeadAPI
from src.game_cycle.database.connection import GameCycleDatabase


@pytest.fixture
def db_path():
    """Create a temporary database with the schema."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    conn = sqlite3.connect(path)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS dynasties (
            dynasty_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            team_id INTEGER NOT NULL,
            season_year INTEGER NOT NULL DEFAULT 2025
        );

        CREATE TABLE IF NOT EXISTS head_to_head (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            team_a_id INTEGER NOT NULL CHECK(team_a_id BETWEEN 1 AND 32),
            team_b_id INTEGER NOT NULL CHECK(team_b_id BETWEEN 1 AND 32),
            team_a_wins INTEGER DEFAULT 0 CHECK(team_a_wins >= 0),
            team_b_wins INTEGER DEFAULT 0 CHECK(team_b_wins >= 0),
            ties INTEGER DEFAULT 0 CHECK(ties >= 0),
            team_a_home_wins INTEGER DEFAULT 0 CHECK(team_a_home_wins >= 0),
            team_a_away_wins INTEGER DEFAULT 0 CHECK(team_a_away_wins >= 0),
            last_meeting_season INTEGER,
            last_meeting_winner INTEGER,
            current_streak_team INTEGER,
            current_streak_count INTEGER DEFAULT 0 CHECK(current_streak_count >= 0),
            playoff_meetings INTEGER DEFAULT 0 CHECK(playoff_meetings >= 0),
            playoff_team_a_wins INTEGER DEFAULT 0 CHECK(playoff_team_a_wins >= 0),
            playoff_team_b_wins INTEGER DEFAULT 0 CHECK(playoff_team_b_wins >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK(team_a_id < team_b_id),
            CHECK(team_a_id != team_b_id),
            FOREIGN KEY (dynasty_id) REFERENCES dynasties(dynasty_id) ON DELETE CASCADE,
            UNIQUE(dynasty_id, team_a_id, team_b_id)
        );

        CREATE INDEX idx_h2h_dynasty ON head_to_head(dynasty_id);
        CREATE INDEX idx_h2h_team_a ON head_to_head(dynasty_id, team_a_id);
        CREATE INDEX idx_h2h_team_b ON head_to_head(dynasty_id, team_b_id);

        INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('test_dynasty', 'Test Dynasty', 1);
    ''')
    conn.commit()
    conn.close()

    yield path

    os.unlink(path)


@pytest.fixture
def db(db_path):
    """Create GameCycleDatabase instance."""
    return GameCycleDatabase(db_path)


@pytest.fixture
def api(db):
    """Create HeadToHeadAPI instance."""
    return HeadToHeadAPI(db)


# ============================================================================
# HeadToHeadRecord Dataclass Tests
# ============================================================================

class TestHeadToHeadRecordValidation:
    """Tests for HeadToHeadRecord dataclass validation."""

    def test_create_valid_record(self):
        """Should create record with valid parameters."""
        record = HeadToHeadRecord(
            team_a_id=5,
            team_b_id=8,
            team_a_wins=10,
            team_b_wins=5,
            ties=1,
        )
        assert record.team_a_id == 5
        assert record.team_b_id == 8
        assert record.team_a_wins == 10
        assert record.team_b_wins == 5
        assert record.ties == 1

    def test_auto_swap_team_ids_when_reversed(self):
        """Should auto-swap team IDs to enforce team_a < team_b."""
        record = HeadToHeadRecord(
            team_a_id=10,
            team_b_id=5,
        )
        assert record.team_a_id == 5
        assert record.team_b_id == 10

    def test_default_values_are_zero(self):
        """Default values should be 0 for all counts."""
        record = HeadToHeadRecord(team_a_id=1, team_b_id=2)
        assert record.team_a_wins == 0
        assert record.team_b_wins == 0
        assert record.ties == 0
        assert record.team_a_home_wins == 0
        assert record.team_a_away_wins == 0
        assert record.current_streak_count == 0
        assert record.playoff_meetings == 0

    def test_invalid_team_a_id_below_range(self):
        """Should raise error for team_a_id < 1."""
        with pytest.raises(ValueError, match="team_a_id must be 1-32"):
            HeadToHeadRecord(team_a_id=0, team_b_id=2)

    def test_invalid_team_b_id_above_range(self):
        """Should raise error for team_b_id > 32."""
        with pytest.raises(ValueError, match="team_b_id must be 1-32"):
            HeadToHeadRecord(team_a_id=1, team_b_id=33)

    def test_same_team_ids_raises_error(self):
        """Should raise error when team_a == team_b."""
        with pytest.raises(ValueError, match="must be different"):
            HeadToHeadRecord(team_a_id=5, team_b_id=5)

    def test_negative_wins_raises_error(self):
        """Should raise error for negative win count."""
        with pytest.raises(ValueError, match="team_a_wins cannot be negative"):
            HeadToHeadRecord(team_a_id=1, team_b_id=2, team_a_wins=-1)

    def test_negative_ties_raises_error(self):
        """Should raise error for negative tie count."""
        with pytest.raises(ValueError, match="ties cannot be negative"):
            HeadToHeadRecord(team_a_id=1, team_b_id=2, ties=-1)

    def test_negative_streak_count_raises_error(self):
        """Should raise error for negative streak count."""
        with pytest.raises(ValueError, match="current_streak_count cannot be negative"):
            HeadToHeadRecord(team_a_id=1, team_b_id=2, current_streak_count=-1)

    def test_non_integer_team_id_raises_error(self):
        """Should raise error for non-integer team ID."""
        with pytest.raises(ValueError, match="must be integers"):
            HeadToHeadRecord(team_a_id="1", team_b_id=2)


class TestHeadToHeadRecordProperties:
    """Tests for HeadToHeadRecord computed properties."""

    def test_total_games_property(self):
        """total_games should sum wins and ties."""
        record = HeadToHeadRecord(
            team_a_id=1, team_b_id=2,
            team_a_wins=10, team_b_wins=5, ties=2,
        )
        assert record.total_games == 17

    def test_total_playoff_games_property(self):
        """total_playoff_games should equal playoff_meetings."""
        record = HeadToHeadRecord(
            team_a_id=1, team_b_id=2,
            playoff_meetings=3,
        )
        assert record.total_playoff_games == 3

    def test_total_all_games_property(self):
        """total_all_games should include playoffs."""
        record = HeadToHeadRecord(
            team_a_id=1, team_b_id=2,
            team_a_wins=10, team_b_wins=5, ties=2,
            playoff_meetings=3,
        )
        assert record.total_all_games == 20

    def test_series_leader_team_a_leading(self):
        """series_leader should return team_a when leading."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5,
        )
        assert record.series_leader == 5

    def test_series_leader_team_b_leading(self):
        """series_leader should return team_b when leading."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=5, team_b_wins=10,
        )
        assert record.series_leader == 8

    def test_series_leader_tied(self):
        """series_leader should return None when tied."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=10,
        )
        assert record.series_leader is None

    def test_series_margin(self):
        """series_margin should return absolute difference."""
        record = HeadToHeadRecord(
            team_a_id=1, team_b_id=2,
            team_a_wins=10, team_b_wins=5,
        )
        assert record.series_margin == 5

    def test_streak_description_with_streak(self):
        """streak_description should format streak info."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            current_streak_team=5, current_streak_count=3,
        )
        assert record.streak_description == "Team 5: W3"

    def test_streak_description_no_streak(self):
        """streak_description should show no streak message."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            current_streak_team=None, current_streak_count=0,
        )
        assert record.streak_description == "No current streak"


class TestHeadToHeadRecordMethods:
    """Tests for HeadToHeadRecord instance methods."""

    def test_get_record_for_team_a(self):
        """get_record_for_team should format from team_a perspective."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5, ties=1,
        )
        assert record.get_record_for_team(5) == "10-5-1"

    def test_get_record_for_team_b(self):
        """get_record_for_team should format from team_b perspective."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5, ties=1,
        )
        assert record.get_record_for_team(8) == "5-10-1"

    def test_get_record_for_team_not_in_matchup(self):
        """get_record_for_team should raise for non-participating team."""
        record = HeadToHeadRecord(team_a_id=5, team_b_id=8)
        with pytest.raises(ValueError, match="not in this matchup"):
            record.get_record_for_team(10)

    def test_get_wins_for_team_a(self):
        """get_wins_for_team should return team_a wins."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5,
        )
        assert record.get_wins_for_team(5) == 10

    def test_get_wins_for_team_b(self):
        """get_wins_for_team should return team_b wins."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5,
        )
        assert record.get_wins_for_team(8) == 5

    def test_get_losses_for_team(self):
        """get_losses_for_team should return opponent wins."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            team_a_wins=10, team_b_wins=5,
        )
        assert record.get_losses_for_team(5) == 5
        assert record.get_losses_for_team(8) == 10

    def test_get_playoff_record_for_team(self):
        """get_playoff_record_for_team should format playoff record."""
        record = HeadToHeadRecord(
            team_a_id=5, team_b_id=8,
            playoff_team_a_wins=3, playoff_team_b_wins=2,
        )
        assert record.get_playoff_record_for_team(5) == "3-2"
        assert record.get_playoff_record_for_team(8) == "2-3"

    def test_involves_team_returns_true(self):
        """involves_team should return True for participating teams."""
        record = HeadToHeadRecord(team_a_id=5, team_b_id=8)
        assert record.involves_team(5) is True
        assert record.involves_team(8) is True

    def test_involves_team_returns_false(self):
        """involves_team should return False for non-participating team."""
        record = HeadToHeadRecord(team_a_id=5, team_b_id=8)
        assert record.involves_team(10) is False

    def test_get_opponent(self):
        """get_opponent should return the other team."""
        record = HeadToHeadRecord(team_a_id=5, team_b_id=8)
        assert record.get_opponent(5) == 8
        assert record.get_opponent(8) == 5
        assert record.get_opponent(10) is None


class TestHeadToHeadRecordConversion:
    """Tests for HeadToHeadRecord conversion methods."""

    def test_from_db_row(self):
        """from_db_row should create record from dict."""
        row = {
            'record_id': 42,
            'team_a_id': 5,
            'team_b_id': 8,
            'team_a_wins': 10,
            'team_b_wins': 5,
            'ties': 1,
            'team_a_home_wins': 6,
            'team_a_away_wins': 4,
            'last_meeting_season': 2025,
            'last_meeting_winner': 5,
            'current_streak_team': 5,
            'current_streak_count': 3,
            'playoff_meetings': 2,
            'playoff_team_a_wins': 1,
            'playoff_team_b_wins': 1,
            'created_at': '2025-01-01 00:00:00',
            'updated_at': '2025-01-01 00:00:00',
        }
        record = HeadToHeadRecord.from_db_row(row)
        assert record.record_id == 42
        assert record.team_a_id == 5
        assert record.team_b_id == 8
        assert record.team_a_wins == 10
        assert record.current_streak_count == 3

    def test_to_dict(self):
        """to_dict should convert to serializable format."""
        record = HeadToHeadRecord(
            record_id=42,
            team_a_id=5,
            team_b_id=8,
            team_a_wins=10,
            team_b_wins=5,
            ties=1,
        )
        result = record.to_dict()
        assert result['record_id'] == 42
        assert result['team_a_id'] == 5
        assert result['team_b_id'] == 8
        assert result['team_a_wins'] == 10
        assert result['team_b_wins'] == 5
        assert result['ties'] == 1

    def test_str_representation(self):
        """__str__ should return readable format."""
        record = HeadToHeadRecord(
            team_a_id=5,
            team_b_id=8,
            team_a_wins=10,
            team_b_wins=5,
            ties=1,
        )
        result = str(record)
        assert "Team 5 vs Team 8" in result
        assert "10-5-1" in result


# ============================================================================
# HeadToHeadAPI Query Tests
# ============================================================================

class TestGetRecord:
    """Tests for get_record method."""

    def test_get_record_exists(self, api):
        """Should retrieve existing record."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record is not None
        assert record.team_a_id == 5
        assert record.team_b_id == 8

    def test_get_record_reversed_order(self, api):
        """Should find record with reversed team order."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 8, 5)  # Reversed order
        assert record is not None
        assert record.team_a_id == 5
        assert record.team_b_id == 8

    def test_get_record_not_found(self, api):
        """Should return None for non-existent record."""
        record = api.get_record("test_dynasty", 1, 2)
        assert record is None


class TestGetTeamAllRecords:
    """Tests for get_team_all_records method."""

    def test_get_team_all_records(self, api):
        """Should get all records for a team."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("test_dynasty", 5, 6, 28, 21, 2025)
        api.update_after_game("test_dynasty", 5, 7, 17, 10, 2025)

        records = api.get_team_all_records("test_dynasty", 5)
        assert len(records) == 3

    def test_get_team_all_records_sorted_by_games(self, api):
        """Should be sorted by total games descending."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("test_dynasty", 5, 8, 24, 17, 2025)  # 2 games with team 8
        api.update_after_game("test_dynasty", 5, 6, 28, 21, 2025)  # 1 game with team 6

        records = api.get_team_all_records("test_dynasty", 5)
        assert len(records) == 2
        assert records[0].total_games == 2  # Team 8 first
        assert records[1].total_games == 1

    def test_get_team_all_records_empty(self, api):
        """Should return empty list for team with no records."""
        records = api.get_team_all_records("test_dynasty", 15)
        assert records == []


class TestGetTopMatchups:
    """Tests for get_top_matchups_by_games method."""

    def test_get_top_matchups(self, api):
        """Should get matchups with most games."""
        # Create matchups with different game counts
        for _ in range(5):
            api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        for _ in range(3):
            api.update_after_game("test_dynasty", 1, 2, 28, 21, 2025)
        api.update_after_game("test_dynasty", 10, 15, 17, 10, 2025)

        results = api.get_top_matchups_by_games("test_dynasty", limit=3)
        assert len(results) == 3
        assert results[0].total_games == 5  # Teams 5 vs 8
        assert results[1].total_games == 3  # Teams 1 vs 2
        assert results[2].total_games == 1

    def test_get_top_matchups_respects_limit(self, api):
        """Should respect limit parameter."""
        for i in range(5):
            api.update_after_game("test_dynasty", i+1, i+2, 21, 14, 2025)

        results = api.get_top_matchups_by_games("test_dynasty", limit=2)
        assert len(results) == 2


class TestGetLongestStreaks:
    """Tests for get_longest_streaks method."""

    def test_get_longest_streaks(self, api):
        """Should get matchups with longest streaks."""
        # Create 5-game streak
        for _ in range(5):
            api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)

        # Create 3-game streak
        for _ in range(3):
            api.update_after_game("test_dynasty", 1, 2, 28, 21, 2025)

        results = api.get_longest_streaks("test_dynasty", limit=2)
        assert len(results) == 2
        assert results[0].current_streak_count == 5
        assert results[1].current_streak_count == 3

    def test_get_longest_streaks_excludes_no_streak(self, api):
        """Should exclude matchups with no streak."""
        # Create a streak
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)

        # Create a tie (breaks streak)
        api.update_after_game("test_dynasty", 1, 2, 21, 21, 2025)

        results = api.get_longest_streaks("test_dynasty")
        assert len(results) == 1
        assert results[0].team_a_id == 5


# ============================================================================
# HeadToHeadAPI Update Tests
# ============================================================================

class TestUpdateAfterGame:
    """Tests for update_after_game method."""

    def test_update_creates_new_record(self, api):
        """Should create record if it doesn't exist."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record is not None
        assert record.team_a_id == 5
        assert record.team_b_id == 8

    def test_home_team_win_increments_correctly(self, api):
        """Home team win should increment correct counters."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        # Team 5 (lower ID) is team_a, and team 5 was home
        assert record.team_a_wins == 1
        assert record.team_b_wins == 0
        assert record.team_a_home_wins == 1
        assert record.team_a_away_wins == 0

    def test_away_team_win_increments_correctly(self, api):
        """Away team win should increment correct counters."""
        api.update_after_game("test_dynasty", 5, 8, 14, 21, 2025)  # Team 8 wins
        record = api.get_record("test_dynasty", 5, 8)
        # Team 8 won at team 5's home
        assert record.team_a_wins == 0
        assert record.team_b_wins == 1

    def test_away_team_a_win_updates_away_wins(self, api):
        """When team_a wins on the road, increment team_a_away_wins."""
        # Team 5 visits team 8 and wins (home=8, away=5)
        api.update_after_game("test_dynasty", 8, 5, 14, 21, 2025)  # Team 5 (away) wins
        record = api.get_record("test_dynasty", 5, 8)
        assert record.team_a_wins == 1
        assert record.team_a_home_wins == 0
        assert record.team_a_away_wins == 1

    def test_tie_increments_ties(self, api):
        """Tie should increment ties counter."""
        api.update_after_game("test_dynasty", 5, 8, 21, 21, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.ties == 1
        assert record.team_a_wins == 0
        assert record.team_b_wins == 0


class TestLastMeetingTracking:
    """Tests for last meeting updates."""

    def test_last_meeting_season_updated(self, api):
        """Should update last meeting season."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.last_meeting_season == 2025

    def test_last_meeting_winner_home_win(self, api):
        """Should track home team as winner."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.last_meeting_winner == 5

    def test_last_meeting_winner_away_win(self, api):
        """Should track away team as winner."""
        api.update_after_game("test_dynasty", 5, 8, 14, 21, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.last_meeting_winner == 8

    def test_last_meeting_winner_tie(self, api):
        """Should set winner to None on tie."""
        api.update_after_game("test_dynasty", 5, 8, 21, 21, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.last_meeting_winner is None


class TestStreakTracking:
    """Tests for streak logic."""

    def test_streak_starts_after_first_game(self, api):
        """Should start streak with count 1 after first game."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.current_streak_team == 5
        assert record.current_streak_count == 1

    def test_streak_increments_on_consecutive_wins(self, api):
        """Should increment streak on consecutive wins."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("test_dynasty", 5, 8, 24, 17, 2025)
        api.update_after_game("test_dynasty", 5, 8, 28, 21, 2025)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.current_streak_team == 5
        assert record.current_streak_count == 3

    def test_streak_resets_on_different_winner(self, api):
        """Should reset streak when different team wins."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Team 5 wins
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Team 5 wins again
        api.update_after_game("test_dynasty", 5, 8, 14, 21, 2025)  # Team 8 wins
        record = api.get_record("test_dynasty", 5, 8)
        assert record.current_streak_team == 8
        assert record.current_streak_count == 1

    def test_streak_resets_on_tie(self, api):
        """Should reset streak to None on tie."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Team 5 wins
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Team 5 wins again
        api.update_after_game("test_dynasty", 5, 8, 21, 21, 2025)  # Tie
        record = api.get_record("test_dynasty", 5, 8)
        assert record.current_streak_team is None
        assert record.current_streak_count == 0


class TestPlayoffTracking:
    """Tests for playoff game tracking."""

    def test_playoff_increments_meetings(self, api):
        """Playoff game should increment playoff_meetings."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025, is_playoff=True)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.playoff_meetings == 1

    def test_playoff_team_a_win(self, api):
        """Playoff win by team_a should increment playoff_team_a_wins."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025, is_playoff=True)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.playoff_team_a_wins == 1
        assert record.playoff_team_b_wins == 0

    def test_playoff_team_b_win(self, api):
        """Playoff win by team_b should increment playoff_team_b_wins."""
        api.update_after_game("test_dynasty", 5, 8, 14, 21, 2025, is_playoff=True)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.playoff_team_a_wins == 0
        assert record.playoff_team_b_wins == 1

    def test_playoff_does_not_increment_regular_wins(self, api):
        """Playoff game should NOT increment regular season wins."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025, is_playoff=True)
        record = api.get_record("test_dynasty", 5, 8)
        assert record.team_a_wins == 0  # Regular season wins unchanged
        assert record.team_b_wins == 0

    def test_playoff_updates_streak(self, api):
        """Playoff game should update streak like regular game."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Regular win
        api.update_after_game("test_dynasty", 5, 8, 24, 17, 2025, is_playoff=True)  # Playoff win
        record = api.get_record("test_dynasty", 5, 8)
        assert record.current_streak_team == 5
        assert record.current_streak_count == 2


class TestClearAndDelete:
    """Tests for clear_records and delete_record methods."""

    def test_clear_records(self, api):
        """Should clear all records for dynasty."""
        api.update_after_game("test_dynasty", 1, 2, 21, 14, 2025)
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)

        count = api.clear_records("test_dynasty")
        assert count == 2
        assert api.get_record_count("test_dynasty") == 0

    def test_delete_record(self, api):
        """Should delete specific record."""
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        result = api.delete_record("test_dynasty", 5, 8)
        assert result is True
        assert api.get_record("test_dynasty", 5, 8) is None

    def test_delete_nonexistent_record(self, api):
        """Should return False for non-existent record."""
        result = api.delete_record("test_dynasty", 1, 2)
        assert result is False


# ============================================================================
# Dynasty Isolation Tests
# ============================================================================

class TestDynastyIsolation:
    """Tests for dynasty isolation of head-to-head data."""

    def test_records_isolated_by_dynasty(self, api, db_path):
        """Records should be isolated by dynasty."""
        # Add another dynasty
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        # Create records in each dynasty
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("other_dynasty", 5, 8, 14, 21, 2025)

        # Query each dynasty
        test_record = api.get_record("test_dynasty", 5, 8)
        other_record = api.get_record("other_dynasty", 5, 8)

        # Team 5 won in test_dynasty, team 8 won in other_dynasty
        assert test_record.team_a_wins == 1
        assert test_record.team_b_wins == 0
        assert other_record.team_a_wins == 0
        assert other_record.team_b_wins == 1

    def test_get_team_all_records_isolated(self, api, db_path):
        """get_team_all_records should respect dynasty isolation."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("other_dynasty", 5, 6, 21, 14, 2025)

        test_records = api.get_team_all_records("test_dynasty", 5)
        other_records = api.get_team_all_records("other_dynasty", 5)

        assert len(test_records) == 1
        assert test_records[0].team_b_id == 8
        assert len(other_records) == 1
        assert other_records[0].team_b_id == 6

    def test_clear_records_isolated(self, api, db_path):
        """clear_records should only clear specified dynasty."""
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT INTO dynasties (dynasty_id, name, team_id) VALUES ('other_dynasty', 'Other', 2)"
        )
        conn.commit()
        conn.close()

        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)
        api.update_after_game("other_dynasty", 5, 8, 21, 14, 2025)

        api.clear_records("test_dynasty")

        assert api.get_record_count("test_dynasty") == 0
        assert api.get_record_count("other_dynasty") == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegrationScenarios:
    """Integration tests for realistic scenarios."""

    def test_full_season_between_division_rivals(self, api):
        """Simulate a full season with 2 games between rivals."""
        # Game 1: Home team 5 wins
        api.update_after_game("test_dynasty", 5, 8, 28, 21, 2025)
        # Game 2: Away team 5 (at team 8) wins
        api.update_after_game("test_dynasty", 8, 5, 17, 24, 2025)

        record = api.get_record("test_dynasty", 5, 8)
        assert record.team_a_wins == 2  # Team 5 swept
        assert record.team_b_wins == 0
        assert record.team_a_home_wins == 1
        assert record.team_a_away_wins == 1
        assert record.current_streak_team == 5
        assert record.current_streak_count == 2

    def test_multi_year_rivalry_tracking(self, api):
        """Track rivalry across multiple seasons."""
        # Year 1
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2023)
        api.update_after_game("test_dynasty", 8, 5, 14, 21, 2023)  # Team 5 wins away

        # Year 2
        api.update_after_game("test_dynasty", 5, 8, 28, 31, 2024)  # Team 8 wins
        api.update_after_game("test_dynasty", 8, 5, 21, 17, 2024)  # Team 8 wins again

        # Year 3
        api.update_after_game("test_dynasty", 5, 8, 35, 21, 2025)  # Team 5 wins

        record = api.get_record("test_dynasty", 5, 8)
        assert record.total_games == 5
        assert record.team_a_wins == 3  # Team 5
        assert record.team_b_wins == 2  # Team 8
        assert record.last_meeting_season == 2025
        assert record.last_meeting_winner == 5
        assert record.current_streak_team == 5
        assert record.current_streak_count == 1

    def test_regular_and_playoff_combined(self, api):
        """Test combined regular season and playoff tracking."""
        # Regular season games
        api.update_after_game("test_dynasty", 5, 8, 21, 14, 2025)  # Team 5 wins
        api.update_after_game("test_dynasty", 8, 5, 17, 24, 2025)  # Team 5 wins

        # Playoff game
        api.update_after_game("test_dynasty", 5, 8, 14, 21, 2025, is_playoff=True)  # Team 8 wins

        record = api.get_record("test_dynasty", 5, 8)
        assert record.team_a_wins == 2  # Regular only
        assert record.team_b_wins == 0
        assert record.playoff_meetings == 1
        assert record.playoff_team_a_wins == 0
        assert record.playoff_team_b_wins == 1
        # Streak should show team 8 (most recent winner)
        assert record.current_streak_team == 8
        assert record.current_streak_count == 1
