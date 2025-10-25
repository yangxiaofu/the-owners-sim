"""
Tests for RegularToPlayoffsHandler

Tests the REGULAR_SEASON → PLAYOFFS transition handler with dependency injection.
Verifies transition execution, rollback, error handling, and parameter validation.
"""

import pytest
from unittest.mock import Mock, MagicMock


class TestRegularToPlayoffsHandler:
    """Test suite for RegularToPlayoffsHandler"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import modules and create test fixtures."""
        import sys
        from pathlib import Path

        # Add src to path
        src_path = str(Path(__file__).parent.parent.parent.parent / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Import required classes
        from src.season.phase_transition.transition_handlers.regular_to_playoffs import RegularToPlayoffsHandler
        from src.season.phase_transition.models import PhaseTransition

        self.RegularToPlayoffsHandler = RegularToPlayoffsHandler
        self.PhaseTransition = PhaseTransition

    # -------------------------------------------------------------------------
    # Constructor Tests
    # -------------------------------------------------------------------------

    def test_constructor_with_valid_parameters(self):
        """Test constructor with valid parameters"""
        # Arrange
        get_standings = Mock(return_value={"team1": {"wins": 10}})
        seed_playoffs = Mock(return_value={"afc_1": 1})
        create_controller = Mock(return_value=Mock())
        update_phase = Mock()

        # Act
        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=seed_playoffs,
            create_playoff_controller=create_controller,
            update_database_phase=update_phase,
            dynasty_id="test_dynasty",
            season_year=2024
        )

        # Assert
        assert handler._dynasty_id == "test_dynasty"
        assert handler._season_year == 2024
        assert handler._verbose_logging is False

    def test_constructor_with_verbose_logging(self):
        """Test constructor with verbose logging enabled"""
        # Arrange
        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(),
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024,
            verbose_logging=True
        )

        # Assert
        assert handler._verbose_logging is True

    def test_constructor_rejects_empty_dynasty_id(self):
        """Test constructor rejects empty dynasty_id"""
        # Act & Assert
        with pytest.raises(ValueError, match="dynasty_id cannot be empty"):
            self.RegularToPlayoffsHandler(
                get_standings=Mock(),
                seed_playoffs=Mock(),
                create_playoff_controller=Mock(),
                update_database_phase=Mock(),
                dynasty_id="",
                season_year=2024
            )

    def test_constructor_rejects_invalid_season_year(self):
        """Test constructor rejects season year before 1920"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid season year"):
            self.RegularToPlayoffsHandler(
                get_standings=Mock(),
                seed_playoffs=Mock(),
                create_playoff_controller=Mock(),
                update_database_phase=Mock(),
                dynasty_id="test_dynasty",
                season_year=1919
            )

    # -------------------------------------------------------------------------
    # Successful Execution Tests
    # -------------------------------------------------------------------------

    def test_execute_successful_transition(self):
        """Test successful execution of REGULAR_SEASON → PLAYOFFS"""
        # Arrange: Mock all dependencies
        mock_standings = {"team1": {"wins": 10, "losses": 7}}
        mock_seeding = {"afc_1": 1, "nfc_1": 2}
        mock_controller = Mock()

        get_standings = Mock(return_value=mock_standings)
        seed_playoffs = Mock(return_value=mock_seeding)
        create_controller = Mock(return_value=mock_controller)
        update_phase = Mock()

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=seed_playoffs,
            create_playoff_controller=create_controller,
            update_database_phase=update_phase,
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act
        result = handler.execute(transition)

        # Assert: Verify all steps executed in order
        get_standings.assert_called_once_with("test_dynasty", 2024)
        seed_playoffs.assert_called_once_with(mock_standings)
        create_controller.assert_called_once_with(mock_seeding)
        update_phase.assert_called_once_with("PLAYOFFS")
        assert result == mock_controller

    def test_execute_calls_dependencies_in_correct_order(self):
        """Test that dependencies are called in the correct order"""
        # Arrange: Track call order
        call_order = []

        def track_get_standings(dynasty_id, year):
            call_order.append("get_standings")
            return {"team1": {"wins": 10}}

        def track_seed_playoffs(standings):
            call_order.append("seed_playoffs")
            return {"afc_1": 1}

        def track_create_controller(seeding):
            call_order.append("create_controller")
            return Mock()

        def track_update_phase(phase):
            call_order.append("update_phase")

        handler = self.RegularToPlayoffsHandler(
            get_standings=track_get_standings,
            seed_playoffs=track_seed_playoffs,
            create_playoff_controller=track_create_controller,
            update_database_phase=track_update_phase,
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act
        handler.execute(transition)

        # Assert: Verify correct order
        assert call_order == [
            "get_standings",
            "seed_playoffs",
            "create_controller",
            "update_phase"
        ]

    # -------------------------------------------------------------------------
    # Validation Tests
    # -------------------------------------------------------------------------

    def test_execute_rejects_invalid_from_phase(self):
        """Test execute rejects invalid from_phase"""
        # Arrange
        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(),
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="PLAYOFFS",  # Wrong!
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid from_phase"):
            handler.execute(transition)

    def test_execute_rejects_invalid_to_phase(self):
        """Test execute rejects invalid to_phase"""
        # Arrange
        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(),
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="OFFSEASON",  # Wrong!
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid to_phase"):
            handler.execute(transition)

    # -------------------------------------------------------------------------
    # Error Handling Tests
    # -------------------------------------------------------------------------

    def test_execute_fails_when_standings_retrieval_fails(self):
        """Test execute fails gracefully when standings retrieval fails"""
        # Arrange
        get_standings = Mock(side_effect=Exception("Database error"))

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            handler.execute(transition)

    def test_execute_fails_when_standings_empty(self):
        """Test execute fails when standings are empty"""
        # Arrange
        get_standings = Mock(return_value={})  # Empty standings

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Standings data is empty"):
            handler.execute(transition)

    def test_execute_fails_when_playoff_seeding_fails(self):
        """Test execute fails when playoff seeding fails"""
        # Arrange
        get_standings = Mock(return_value={"team1": {"wins": 10}})
        seed_playoffs = Mock(side_effect=Exception("Seeding error"))

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=seed_playoffs,
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(Exception, match="Seeding error"):
            handler.execute(transition)

    def test_execute_fails_when_seeding_empty(self):
        """Test execute fails when seeding result is empty"""
        # Arrange
        get_standings = Mock(return_value={"team1": {"wins": 10}})
        seed_playoffs = Mock(return_value={})  # Empty seeding

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=seed_playoffs,
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Playoff seeding failed"):
            handler.execute(transition)

    def test_execute_fails_when_controller_creation_returns_none(self):
        """Test execute fails when controller creation returns None"""
        # Arrange
        get_standings = Mock(return_value={"team1": {"wins": 10}})
        seed_playoffs = Mock(return_value={"afc_1": 1})
        create_controller = Mock(return_value=None)  # Returns None

        handler = self.RegularToPlayoffsHandler(
            get_standings=get_standings,
            seed_playoffs=seed_playoffs,
            create_playoff_controller=create_controller,
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to create playoff controller"):
            handler.execute(transition)

    # -------------------------------------------------------------------------
    # Rollback Tests
    # -------------------------------------------------------------------------

    def test_rollback_restores_previous_phase(self):
        """Test rollback restores database to previous phase"""
        # Arrange
        update_phase = Mock()

        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(return_value={"team1": {"wins": 10}}),
            seed_playoffs=Mock(return_value={"afc_1": 1}),
            create_playoff_controller=Mock(return_value=Mock()),
            update_database_phase=update_phase,
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Execute first to save rollback state
        handler.execute(transition)
        update_phase.reset_mock()

        # Act: Rollback
        handler.rollback(transition)

        # Assert: Should restore to REGULAR_SEASON
        update_phase.assert_called_once_with("REGULAR_SEASON")

    def test_rollback_fails_without_prior_execute(self):
        """Test rollback fails if execute was not called first"""
        # Arrange
        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(),
            seed_playoffs=Mock(),
            create_playoff_controller=Mock(),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Act & Assert
        with pytest.raises(RuntimeError, match="No rollback data available"):
            handler.rollback(transition)

    def test_rollback_clears_rollback_data(self):
        """Test rollback clears rollback data after successful restore"""
        # Arrange
        handler = self.RegularToPlayoffsHandler(
            get_standings=Mock(return_value={"team1": {"wins": 10}}),
            seed_playoffs=Mock(return_value={"afc_1": 1}),
            create_playoff_controller=Mock(return_value=Mock()),
            update_database_phase=Mock(),
            dynasty_id="test_dynasty",
            season_year=2024
        )

        transition = self.PhaseTransition(
            from_phase="REGULAR_SEASON",
            to_phase="PLAYOFFS",
            trigger="manual"
        )

        # Execute and rollback
        handler.execute(transition)
        handler.rollback(transition)

        # Act & Assert: Second rollback should fail
        with pytest.raises(RuntimeError, match="No rollback data available"):
            handler.rollback(transition)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
