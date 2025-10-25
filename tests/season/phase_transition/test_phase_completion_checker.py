"""
Tests for PhaseCompletionChecker

Tests the pure logic completion checking for NFL season phases.
Uses dependency injection to test completion logic without database dependencies.
"""

import pytest
from datetime import datetime


class TestPhaseCompletionChecker:
    """Test suite for PhaseCompletionChecker"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import modules needed for tests."""
        import sys
        from pathlib import Path

        # Add src to path for testing
        src_path = str(Path(__file__).parent.parent.parent.parent / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Import using src. prefix to avoid builtin calendar module collision
        from src.calendar.date_models import Date
        from src.season.phase_transition.phase_completion_checker import PhaseCompletionChecker

        self.Date = Date
        self.PhaseCompletionChecker = PhaseCompletionChecker

    # -------------------------------------------------------------------------
    # Regular Season Completion Tests
    # -------------------------------------------------------------------------

    def test_regular_season_complete_by_game_count_exact(self):
        """Test regular season completion when exactly 272 games played"""
        # Arrange: Mock functions that return completion state
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2024, month=12, day=30)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False
        calculate_preseason_start = lambda: self.Date(year=2025, month=8, day=5)

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=calculate_preseason_start
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is True, "272 games should complete regular season"

    def test_regular_season_complete_by_game_count_more_than_272(self):
        """Test regular season completion when more than 272 games played"""
        # Arrange
        get_games_played = lambda: 280
        get_current_date = lambda: self.Date(year=2024, month=12, day=30)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is True, "More than 272 games should complete regular season"

    def test_regular_season_incomplete_by_game_count(self):
        """Test regular season incomplete when fewer than 272 games played"""
        # Arrange
        get_games_played = lambda: 200
        get_current_date = lambda: self.Date(year=2024, month=11, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is False, "Less than 272 games with date before last game should not complete"

    def test_regular_season_complete_by_date_after_last_game(self):
        """Test regular season completion when date is after last game date"""
        # Arrange: Only 250 games played, but date past last game
        get_games_played = lambda: 250
        get_current_date = lambda: self.Date(year=2025, month=1, day=10)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is True, "Date after last game should complete regular season even with <272 games"

    def test_regular_season_incomplete_by_date_before_last_game(self):
        """Test regular season incomplete when date is before last game"""
        # Arrange: Only 100 games played, date well before last game
        get_games_played = lambda: 100
        get_current_date = lambda: self.Date(year=2024, month=10, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is False, "Date before last game with <272 games should not complete"

    def test_regular_season_complete_on_exact_last_game_date(self):
        """Test regular season on the exact last game date (edge case)"""
        # Arrange: Current date equals last game date
        get_games_played = lambda: 270
        get_current_date = lambda: self.Date(year=2025, month=1, day=7)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is False, "On exact last game date (not >), season should not be complete"

    def test_regular_season_zero_games_played(self):
        """Test regular season with zero games played (edge case)"""
        # Arrange
        get_games_played = lambda: 0
        get_current_date = lambda: self.Date(year=2024, month=9, day=1)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert
        assert result is False, "Zero games and early date should not complete"

    # -------------------------------------------------------------------------
    # Playoffs Completion Tests
    # -------------------------------------------------------------------------

    def test_playoffs_complete_when_super_bowl_complete(self):
        """Test playoffs completion when Super Bowl is complete"""
        # Arrange
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=2, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: True  # Super Bowl is complete

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_playoffs_complete()

        # Assert
        assert result is True, "Super Bowl complete should complete playoffs"

    def test_playoffs_incomplete_when_super_bowl_not_complete(self):
        """Test playoffs incomplete when Super Bowl is not complete"""
        # Arrange
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=1, day=20)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False  # Super Bowl not complete

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_playoffs_complete()

        # Assert
        assert result is False, "Super Bowl not complete should not complete playoffs"

    # -------------------------------------------------------------------------
    # Integration Tests (Both Methods)
    # -------------------------------------------------------------------------

    def test_regular_season_and_playoffs_both_complete(self):
        """Test scenario where both regular season and playoffs are complete"""
        # Arrange
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=2, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: True

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is True
        assert checker.is_playoffs_complete() is True

    def test_regular_season_complete_playoffs_incomplete(self):
        """Test scenario where regular season is complete but playoffs are not"""
        # Arrange
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=1, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is True
        assert checker.is_playoffs_complete() is False

    def test_neither_regular_season_nor_playoffs_complete(self):
        """Test scenario where neither phase is complete"""
        # Arrange
        get_games_played = lambda: 150
        get_current_date = lambda: self.Date(year=2024, month=11, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is False
        assert checker.is_playoffs_complete() is False

    # -------------------------------------------------------------------------
    # Edge Cases and Error Handling
    # -------------------------------------------------------------------------

    def test_negative_games_played(self):
        """Test handling of negative games played (error condition)"""
        # Arrange
        get_games_played = lambda: -10
        get_current_date = lambda: self.Date(year=2024, month=9, day=1)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert: Should handle gracefully (negative < 272, so incomplete)
        assert result is False

    def test_date_far_in_future(self):
        """Test handling of date far in future"""
        # Arrange
        get_games_played = lambda: 0
        get_current_date = lambda: self.Date(year=2030, month=1, day=1)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        result = checker.is_regular_season_complete()

        # Assert: Date after last game should complete
        assert result is True, "Far future date should complete regular season"

    def test_callable_functions_called_correctly(self):
        """Test that injected functions are called correctly"""
        # Arrange: Track function calls
        call_counts = {
            "get_games_played": 0,
            "get_current_date": 0,
            "get_last_game_date": 0,
            "is_super_bowl_complete": 0
        }

        def tracked_get_games_played():
            call_counts["get_games_played"] += 1
            return 200

        def tracked_get_current_date():
            call_counts["get_current_date"] += 1
            return self.Date(year=2024, month=11, day=15)

        def tracked_get_last_game_date():
            call_counts["get_last_game_date"] += 1
            return self.Date(year=2025, month=1, day=7)

        def tracked_is_super_bowl_complete():
            call_counts["is_super_bowl_complete"] += 1
            return False

        checker = self.PhaseCompletionChecker(
            get_games_played=tracked_get_games_played,
            get_current_date=tracked_get_current_date,
            get_last_regular_season_game_date=tracked_get_last_game_date,
            is_super_bowl_complete=tracked_is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act
        _ = checker.is_regular_season_complete()
        _ = checker.is_playoffs_complete()

        # Assert: Verify functions were called
        assert call_counts["get_games_played"] == 1, "get_games_played should be called once"
        assert call_counts["get_current_date"] == 1, "get_current_date should be called once"
        assert call_counts["get_last_game_date"] == 1, "get_last_game_date should be called once"
        assert call_counts["is_super_bowl_complete"] == 1, "is_super_bowl_complete should be called once"

    # -------------------------------------------------------------------------
    # Real-World Scenarios
    # -------------------------------------------------------------------------

    def test_2024_season_mid_november_scenario(self):
        """Test realistic mid-season scenario (Week 10)"""
        # Arrange: Realistic Week 10 state
        get_games_played = lambda: 150  # ~150 games through Week 10
        get_current_date = lambda: self.Date(year=2024, month=11, day=15)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is False, "Week 10 should not complete regular season"
        assert checker.is_playoffs_complete() is False, "Week 10 should not have playoffs complete"

    def test_2024_season_end_of_regular_season_scenario(self):
        """Test realistic end of regular season (Week 18 complete)"""
        # Arrange: Week 18 complete, all 272 games played
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=1, day=8)  # Day after last game
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: False

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is True, "Week 18 complete should finish regular season"
        assert checker.is_playoffs_complete() is False, "Playoffs not started yet"

    def test_2024_season_super_bowl_complete_scenario(self):
        """Test realistic Super Bowl complete scenario"""
        # Arrange: Super Bowl complete (mid-February)
        get_games_played = lambda: 272
        get_current_date = lambda: self.Date(year=2025, month=2, day=14)
        get_last_game_date = lambda: self.Date(year=2025, month=1, day=7)
        is_super_bowl_complete = lambda: True

        checker = self.PhaseCompletionChecker(
            get_games_played=get_games_played,
            get_current_date=get_current_date,
            get_last_regular_season_game_date=get_last_game_date,
            is_super_bowl_complete=is_super_bowl_complete,
            calculate_preseason_start=lambda: self.Date(year=2025, month=8, day=5)
        )

        # Act & Assert
        assert checker.is_regular_season_complete() is True
        assert checker.is_playoffs_complete() is True, "Super Bowl complete should finish playoffs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
