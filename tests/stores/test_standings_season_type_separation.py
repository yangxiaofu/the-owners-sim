"""
Unit Tests for Standings Season Type Separation

Tests that regular season and playoff game results are tracked separately.
"""

import pytest
from unittest.mock import Mock
from stores.standings_store import StandingsStore, EnhancedTeamStanding
from shared.game_result import GameResult


class TestStandingsSeasonTypeSeparation:
    """Test suite for season_type separation in standings."""

    @pytest.fixture
    def standings_store(self):
        """Create a StandingsStore for testing."""
        store = StandingsStore(":memory:")  # In-memory database for testing
        store.set_dynasty_context("test_dynasty", 2025)
        return store

    @pytest.fixture
    def mock_teams(self):
        """Create mock team objects."""
        home_team = Mock()
        home_team.team_id = 22  # Detroit Lions

        away_team = Mock()
        away_team.team_id = 23  # Green Bay Packers

        return home_team, away_team

    def test_regular_season_and_playoff_records_separated(self, standings_store, mock_teams):
        """Verify that regular season and playoff records are stored separately."""
        home_team, away_team = mock_teams

        # Simulate a regular season game
        regular_game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 24, 23: 17},
            season_type="regular_season"
        )
        standings_store.update_from_game_result(regular_game)

        # Simulate a playoff game
        playoff_game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 31, 23: 28},
            season_type="playoffs"
        )
        standings_store.update_from_game_result(playoff_game)

        # Verify regular season standing
        reg_standing = standings_store.get_team_standing(22, season_type="regular_season")
        assert reg_standing is not None, "Regular season standing should exist"
        assert reg_standing.wins == 1, "Regular season should have 1 win"
        assert reg_standing.losses == 0, "Regular season should have 0 losses"

        # Verify playoff standing
        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        assert playoff_standing is not None, "Playoff standing should exist"
        assert playoff_standing.wins == 1, "Playoffs should have 1 win"
        assert playoff_standing.losses == 0, "Playoffs should have 0 losses"

        # Verify they are DIFFERENT objects
        assert reg_standing is not playoff_standing, "Regular season and playoff standings should be separate"

    def test_playoff_standings_created_on_demand(self, standings_store, mock_teams):
        """Verify that playoff standings are created when first playoff game is played."""
        home_team, away_team = mock_teams

        # Initially, no playoff standing exists (returns None or default 0-0)
        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        initial_wins = playoff_standing.wins if playoff_standing else 0

        # Play a playoff game
        playoff_game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 21, 23: 17},
            season_type="playoffs"
        )
        standings_store.update_from_game_result(playoff_game)

        # Now playoff standing should exist and have wins
        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        assert playoff_standing is not None, "Playoff standing should be created"
        assert playoff_standing.wins == 1, "Playoff standing should have 1 win"
        assert playoff_standing.losses == 0, "Playoff standing should have 0 losses"

    def test_multiple_games_same_season_type(self, standings_store, mock_teams):
        """Verify that multiple games of the same type accumulate correctly."""
        home_team, away_team = mock_teams

        # Play 3 regular season games
        for i in range(3):
            game = GameResult(
                home_team=home_team,
                away_team=away_team,
                final_score={22: 24, 23: 17},  # Home team always wins
                season_type="regular_season"
            )
            standings_store.update_from_game_result(game)

        # Verify cumulative regular season record
        reg_standing = standings_store.get_team_standing(22, season_type="regular_season")
        assert reg_standing.wins == 3, "Regular season should have 3 wins"
        assert reg_standing.losses == 0, "Regular season should have 0 losses"

        # Play 2 playoff games
        for i in range(2):
            game = GameResult(
                home_team=home_team,
                away_team=away_team,
                final_score={22: 28, 23: 21},
                season_type="playoffs"
            )
            standings_store.update_from_game_result(game)

        # Verify cumulative playoff record
        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        assert playoff_standing.wins == 2, "Playoffs should have 2 wins"

        # Regular season should remain unchanged
        reg_standing = standings_store.get_team_standing(22, season_type="regular_season")
        assert reg_standing.wins == 3, "Regular season should still have 3 wins (not 5!)"

    def test_season_type_defaults_to_regular_season(self, standings_store, mock_teams):
        """Verify that season_type defaults to 'regular_season' if not specified."""
        home_team, away_team = mock_teams

        # Create GameResult without explicitly setting season_type
        # (it should default to "regular_season")
        game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 24, 23: 17}
            # season_type defaults to "regular_season" in GameResult
        )
        standings_store.update_from_game_result(game)

        # Should appear in regular season standings
        reg_standing = standings_store.get_team_standing(22, season_type="regular_season")
        assert reg_standing is not None
        assert reg_standing.wins == 1

        # Should NOT appear in playoff standings
        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        # Should be None or 0-0 (no playoff games played yet)
        playoff_wins = playoff_standing.wins if playoff_standing else 0
        assert playoff_wins == 0, "Playoff wins should be 0 when only regular season games played"

    def test_loss_tracking_separated_by_season_type(self, standings_store, mock_teams):
        """Verify losses are also tracked separately."""
        home_team, away_team = mock_teams

        # Regular season loss
        reg_game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 17, 23: 24},  # Home team loses
            season_type="regular_season"
        )
        standings_store.update_from_game_result(reg_game)

        # Playoff loss
        playoff_game = GameResult(
            home_team=home_team,
            away_team=away_team,
            final_score={22: 20, 23: 24},  # Home team loses
            season_type="playoffs"
        )
        standings_store.update_from_game_result(playoff_game)

        # Verify losses are separate
        reg_standing = standings_store.get_team_standing(22, season_type="regular_season")
        assert reg_standing.losses == 1
        assert reg_standing.wins == 0

        playoff_standing = standings_store.get_team_standing(22, season_type="playoffs")
        assert playoff_standing.losses == 1
        assert playoff_standing.wins == 0
