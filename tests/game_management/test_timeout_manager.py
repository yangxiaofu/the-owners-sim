"""
Tests for TimeoutManager.

Tests timeout tracking, usage, and halftime resets per NFL rules.
"""

import pytest
from src.game_management.timeout_manager import TimeoutManager, TimeoutState


class TestTimeoutState:
    """Test TimeoutState dataclass."""

    def test_default_initialization(self):
        """Test default timeout state."""
        state = TimeoutState()
        assert state.home_timeouts == 3
        assert state.away_timeouts == 3
        assert state.timeout_called_this_play is None

    def test_get_timeouts_remaining_home(self):
        """Test getting timeouts for home team."""
        state = TimeoutState(home_timeouts=2, away_timeouts=3)
        assert state.get_timeouts_remaining(team_id=1, home_team_id=1) == 2

    def test_get_timeouts_remaining_away(self):
        """Test getting timeouts for away team."""
        state = TimeoutState(home_timeouts=3, away_timeouts=1)
        assert state.get_timeouts_remaining(team_id=2, home_team_id=1) == 1

    def test_to_dict(self):
        """Test serialization to dict."""
        state = TimeoutState(home_timeouts=2, away_timeouts=1, timeout_called_this_play=1)
        result = state.to_dict()

        assert result["home_timeouts"] == 2
        assert result["away_timeouts"] == 1
        assert result["timeout_called_this_play"] == 1


class TestTimeoutManager:
    """Test TimeoutManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create TimeoutManager for testing."""
        return TimeoutManager(home_team_id=1, away_team_id=2)

    def test_initialization(self, manager):
        """Test TimeoutManager initialization."""
        assert manager.home_team_id == 1
        assert manager.away_team_id == 2
        assert manager.state.home_timeouts == 3
        assert manager.state.away_timeouts == 3

    def test_can_use_timeout_when_available(self, manager):
        """Test can_use_timeout returns True when timeouts available."""
        assert manager.can_use_timeout(team_id=1) is True
        assert manager.can_use_timeout(team_id=2) is True

    def test_can_use_timeout_when_depleted(self, manager):
        """Test can_use_timeout returns False when no timeouts."""
        manager.state.home_timeouts = 0
        assert manager.can_use_timeout(team_id=1) is False

    def test_use_timeout_home_team(self, manager):
        """Test using timeout for home team."""
        result = manager.use_timeout(team_id=1)

        assert result is True
        assert manager.state.home_timeouts == 2
        assert manager.state.away_timeouts == 3  # Unchanged
        assert manager.state.timeout_called_this_play == 1

    def test_use_timeout_away_team(self, manager):
        """Test using timeout for away team."""
        result = manager.use_timeout(team_id=2)

        assert result is True
        assert manager.state.home_timeouts == 3  # Unchanged
        assert manager.state.away_timeouts == 2
        assert manager.state.timeout_called_this_play == 2

    def test_use_timeout_when_none_remaining(self, manager):
        """Test using timeout when depleted returns False."""
        manager.state.home_timeouts = 0
        result = manager.use_timeout(team_id=1)

        assert result is False
        assert manager.state.home_timeouts == 0  # Unchanged

    def test_multiple_timeouts(self, manager):
        """Test using multiple timeouts."""
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=1)

        assert manager.state.home_timeouts == 0
        assert manager.can_use_timeout(team_id=1) is False

    def test_reset_timeouts_for_half(self, manager):
        """Test resetting timeouts at halftime."""
        # Use some timeouts
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=2)

        assert manager.state.home_timeouts == 1
        assert manager.state.away_timeouts == 2

        # Reset at halftime
        manager.reset_timeouts_for_half()

        assert manager.state.home_timeouts == 3
        assert manager.state.away_timeouts == 3
        assert manager.state.timeout_called_this_play is None

    def test_get_timeouts_remaining(self, manager):
        """Test getting timeouts remaining."""
        manager.use_timeout(team_id=1)

        assert manager.get_timeouts_remaining(team_id=1) == 2
        assert manager.get_timeouts_remaining(team_id=2) == 3

    def test_get_timeouts_used(self, manager):
        """Test calculating timeouts used."""
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=1)

        assert manager.get_timeouts_used(team_id=1) == 2
        assert manager.get_timeouts_used(team_id=2) == 0

    def test_clear_timeout_flag(self, manager):
        """Test clearing timeout flag."""
        manager.use_timeout(team_id=1)
        assert manager.state.timeout_called_this_play == 1

        manager.clear_timeout_flag()
        assert manager.state.timeout_called_this_play is None

    def test_to_dict(self, manager):
        """Test exporting state to dict."""
        manager.use_timeout(team_id=1)
        result = manager.to_dict()

        assert result["home_timeouts"] == 2
        assert result["away_timeouts"] == 3
        assert result["timeout_called_this_play"] == 1

    def test_timeout_independence_between_teams(self, manager):
        """Test that each team's timeouts are tracked independently."""
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=1)
        manager.use_timeout(team_id=2)

        assert manager.get_timeouts_remaining(team_id=1) == 1
        assert manager.get_timeouts_remaining(team_id=2) == 2

    def test_halftime_reset_preserves_team_ids(self, manager):
        """Test that halftime reset doesn't change team IDs."""
        original_home = manager.home_team_id
        original_away = manager.away_team_id

        manager.reset_timeouts_for_half()

        assert manager.home_team_id == original_home
        assert manager.away_team_id == original_away