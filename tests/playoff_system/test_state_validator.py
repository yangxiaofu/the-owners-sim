"""
Tests for Playoff State Validator

Tests the 40+ validation checks that ensure playoff state consistency.
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.playoff_system.state_validator import (
    PlayoffStateValidator,
    ValidationSeverity,
    ValidationError,
    ValidationResult,
    validate_playoff_state
)


# Test Fixtures

@pytest.fixture
def mock_seed():
    """Create mock playoff seed"""
    def _create_seed(team_id, seed_number, is_division_winner=False):
        seed = Mock()
        seed.team_id = team_id
        seed.seed_number = seed_number
        seed.is_division_winner = is_division_winner
        return seed
    return _create_seed


@pytest.fixture
def valid_seeding(mock_seed):
    """Create valid playoff seeding"""
    seeding = Mock()
    seeding.afc_seeds = [mock_seed(i, i, i <= 4) for i in range(1, 8)]
    seeding.nfc_seeds = [mock_seed(i + 16, i, i <= 4) for i in range(1, 8)]
    return seeding


@pytest.fixture
def valid_state(valid_seeding):
    """Create valid playoff state"""
    state = Mock()
    state.current_round = "wild_card"
    state.original_seeding = valid_seeding
    state.completed_games = {}
    state.brackets = {}
    state.total_games_played = 0
    state.total_days_simulated = 0
    return state


@pytest.fixture
def valid_controller(valid_state):
    """Create valid playoff controller"""
    controller = Mock()
    controller.state = valid_state
    controller.calendar_manager = None  # Optional
    return controller


@pytest.fixture
def validator(valid_controller):
    """Create validator instance"""
    return PlayoffStateValidator(valid_controller)


# ValidationError Tests

class TestValidationError:
    """Test ValidationError dataclass"""

    def test_error_creation(self):
        """Test creating validation error"""
        error = ValidationError(
            severity=ValidationSeverity.ERROR,
            category="seeding",
            message="Invalid seed number",
            context={"team_id": 5, "seed_number": 10},
            suggestion="Check seeding algorithm"
        )

        assert error.severity == ValidationSeverity.ERROR
        assert error.category == "seeding"
        assert error.message == "Invalid seed number"
        assert error.context["team_id"] == 5
        assert error.suggestion == "Check seeding algorithm"

    def test_error_string_representation(self):
        """Test error __str__ method"""
        error = ValidationError(
            severity=ValidationSeverity.WARNING,
            category="bracket",
            message="Missing games",
            context={"round": "divisional"},
            suggestion="Regenerate bracket"
        )

        error_str = str(error)
        assert "WARNING" in error_str
        assert "bracket" in error_str
        assert "Missing games" in error_str
        assert "divisional" in error_str
        assert "Regenerate bracket" in error_str


# ValidationResult Tests

class TestValidationResult:
    """Test ValidationResult dataclass"""

    def test_result_starts_valid(self):
        """Test result starts as valid"""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error_invalidates_result(self):
        """Test adding error invalidates result"""
        result = ValidationResult(valid=True)

        result.add_error(
            ValidationSeverity.ERROR,
            "test",
            "Test error"
        )

        assert result.valid is False
        assert len(result.errors) == 1

    def test_add_warning_keeps_valid(self):
        """Test adding warning doesn't invalidate result"""
        result = ValidationResult(valid=True)

        result.add_error(
            ValidationSeverity.WARNING,
            "test",
            "Test warning"
        )

        assert result.valid is True  # Still valid
        assert len(result.warnings) == 1
        assert len(result.errors) == 0

    def test_get_summary(self):
        """Test summary generation"""
        result = ValidationResult(valid=False, total_checks=10)
        result.add_error(ValidationSeverity.ERROR, "test", "Error 1")
        result.add_error(ValidationSeverity.ERROR, "test", "Error 2")
        result.add_error(ValidationSeverity.WARNING, "test", "Warning 1")

        summary = result.get_summary()

        assert "FAIL" in summary
        assert "10" in summary  # total checks
        assert "2" in summary  # 2 errors
        assert "1" in summary  # 1 warning


# Seeding Validation Tests

class TestSeedingValidation:
    """Test seeding validation (7 checks)"""

    def test_valid_seeding(self, validator):
        """Test validation passes with valid seeding"""
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is True
        assert result.total_checks == 7

    def test_missing_seeding(self, valid_controller):
        """Test validation fails when seeding is None"""
        valid_controller.state.original_seeding = None
        validator = PlayoffStateValidator(valid_controller)

        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("seeding found" in e.message for e in result.errors)

    def test_missing_afc_seeds(self, valid_controller, mock_seed):
        """Test validation fails when AFC seeds missing"""
        valid_controller.state.original_seeding.afc_seeds = None

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("AFC" in e.message for e in result.errors)

    def test_wrong_seed_count(self, valid_controller, mock_seed):
        """Test validation fails with wrong number of seeds"""
        # Only 5 seeds instead of 7
        valid_controller.state.original_seeding.afc_seeds = [
            mock_seed(i, i) for i in range(1, 6)
        ]

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("5 seeds (expected 7)" in e.message for e in result.errors)

    def test_invalid_seed_number(self, valid_controller, mock_seed):
        """Test validation fails with invalid seed number"""
        # Seed number 10 (should be 1-7)
        valid_controller.state.original_seeding.afc_seeds[6] = mock_seed(7, 10)

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("Invalid seed number: 10" in e.message for e in result.errors)

    def test_invalid_team_id(self, valid_controller, mock_seed):
        """Test validation fails with invalid team ID"""
        # Team ID 50 (should be 1-32)
        valid_controller.state.original_seeding.afc_seeds[0] = mock_seed(50, 1)

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("Invalid team ID: 50" in e.message for e in result.errors)

    def test_duplicate_teams(self, valid_controller, mock_seed):
        """Test validation fails with duplicate team IDs"""
        # Team 1 appears twice
        valid_controller.state.original_seeding.afc_seeds[6] = mock_seed(1, 7)

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is False
        assert any("Duplicate team IDs" in e.message for e in result.errors)

    def test_division_winner_not_marked(self, valid_controller, mock_seed):
        """Test warning when seed 1-4 not marked as division winner"""
        # Seed 2 not marked as division winner
        valid_controller.state.original_seeding.afc_seeds[1] = mock_seed(2, 2, is_division_winner=False)

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_seeding(result)

        assert result.valid is True  # Only warning, not error
        assert len(result.warnings) > 0
        assert any("division winner" in w.message for w in result.warnings)


# Game Count Validation Tests

class TestGameCountValidation:
    """Test game count validation (8 checks)"""

    def test_valid_game_counts(self, validator):
        """Test validation passes with valid game counts"""
        result = ValidationResult(valid=True)
        validator._validate_game_counts(result)

        assert result.valid is True
        assert result.total_checks == 8

    def test_total_mismatch(self, valid_controller):
        """Test validation fails when total != sum"""
        valid_controller.state.total_games_played = 10
        valid_controller.state.completed_games = {
            'wild_card': [{}, {}]  # Only 2 games
        }

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_game_counts(result)

        assert result.valid is False
        assert any("Total games mismatch" in e.message for e in result.errors)

    def test_negative_total(self, valid_controller):
        """Test validation fails with negative total"""
        valid_controller.state.total_games_played = -5

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_game_counts(result)

        assert result.valid is False
        assert any("Negative total_games_played" in e.message for e in result.errors)

    def test_too_many_games_in_round(self, valid_controller):
        """Test validation fails with too many games in round"""
        # Wild Card should have max 6 games
        valid_controller.state.completed_games = {
            'wild_card': [{} for _ in range(8)]  # 8 games!
        }
        valid_controller.state.total_games_played = 8

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_game_counts(result)

        assert result.valid is False
        assert any("8 completed games (max 6)" in e.message for e in result.errors)

    def test_games_in_future_round(self, valid_controller):
        """Test validation fails with games in future round"""
        # Current round is wild_card, but divisional has completed games
        valid_controller.state.current_round = "wild_card"
        valid_controller.state.completed_games = {
            'divisional': [{}]  # Game in future round!
        }
        valid_controller.state.total_games_played = 1

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_game_counts(result)

        assert result.valid is False
        assert any("Future round" in e.message for e in result.errors)


# Round Progression Validation Tests

class TestRoundProgressionValidation:
    """Test round progression validation (6 checks)"""

    def test_valid_round_progression(self, validator):
        """Test validation passes with valid progression"""
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert result.valid is True
        assert result.total_checks == 6

    def test_invalid_current_round(self, valid_controller):
        """Test validation fails with invalid round name"""
        valid_controller.state.current_round = "quarter_finals"  # Invalid!

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert result.valid is False
        assert any("Invalid current round" in e.message for e in result.errors)

    def test_previous_round_incomplete(self, valid_controller):
        """Test validation fails when previous round incomplete"""
        # At divisional but wild card not complete
        valid_controller.state.current_round = "divisional"
        valid_controller.state.completed_games = {
            'wild_card': [{}, {}]  # Only 2/6 games
        }

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert result.valid is False
        assert any("incomplete" in e.message for e in result.errors)

    def test_current_round_complete_not_advanced(self, valid_controller):
        """Test warning when current round complete but not advanced"""
        # Wild card complete (6/6) but still current round
        valid_controller.state.current_round = "wild_card"
        valid_controller.state.completed_games = {
            'wild_card': [{} for _ in range(6)]
        }
        valid_controller.state.total_games_played = 6

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert len(result.warnings) > 0
        assert any("complete but not advanced" in w.message for w in result.warnings)

    def test_negative_days_simulated(self, valid_controller):
        """Test validation fails with negative days"""
        valid_controller.state.total_days_simulated = -10

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert result.valid is False
        assert any("Negative days simulated" in e.message for e in result.errors)

    def test_unreasonable_days_simulated(self, valid_controller):
        """Test warning with unreasonably high days"""
        valid_controller.state.total_days_simulated = 150

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_round_progression(result)

        assert len(result.warnings) > 0
        assert any("Unusually high days" in w.message for w in result.warnings)


# Team Data Validation Tests

class TestTeamDataValidation:
    """Test team data validation (5 checks)"""

    def test_valid_team_data(self, validator):
        """Test validation passes with valid team data"""
        result = ValidationResult(valid=True)
        validator._validate_team_data(result)

        assert result.valid is True
        assert result.total_checks == 5

    def test_invalid_team_id_in_game(self, valid_controller):
        """Test validation fails with invalid team ID"""
        valid_controller.state.completed_games = {
            'wild_card': [
                {'away_team_id': 50, 'home_team_id': 1}  # Team 50 invalid!
            ]
        }

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_team_data(result)

        assert result.valid is False
        assert any("Invalid team ID" in e.message for e in result.errors)

    def test_team_not_in_seeding(self, valid_controller):
        """Test validation fails when team in game but not seeded"""
        valid_controller.state.completed_games = {
            'wild_card': [
                {'away_team_id': 10, 'home_team_id': 11}  # Teams not in seeding!
            ]
        }

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_team_data(result)

        assert result.valid is False
        assert any("not in seeding" in e.message for e in result.errors)

    def test_team_plays_itself(self, valid_controller):
        """Test validation fails when team plays itself"""
        valid_controller.state.completed_games = {
            'wild_card': [
                {'away_team_id': 5, 'home_team_id': 5}  # Same team!
            ]
        }

        validator = PlayoffStateValidator(valid_controller)
        result = ValidationResult(valid=True)
        validator._validate_team_data(result)

        assert result.valid is False
        assert any("plays itself" in e.message for e in result.errors)


# Integration Tests

class TestValidateAll:
    """Test complete validation (all checks)"""

    def test_validate_all_valid_state(self, validator):
        """Test validate_all passes with valid state"""
        result = validator.validate_all()

        assert result.valid is True
        assert result.total_checks == 40  # 7+10+8+6+5+4

    def test_validate_all_multiple_errors(self, valid_controller, mock_seed):
        """Test validate_all catches multiple errors"""
        # Introduce multiple errors
        valid_controller.state.original_seeding.afc_seeds[0] = mock_seed(50, 1)  # Invalid team ID
        valid_controller.state.total_games_played = -5  # Negative
        valid_controller.state.current_round = "invalid_round"  # Invalid round

        validator = PlayoffStateValidator(valid_controller)
        result = validator.validate_all()

        assert result.valid is False
        assert len(result.errors) >= 3  # At least 3 errors

    def test_convenience_function(self, valid_controller):
        """Test validate_playoff_state convenience function"""
        result = validate_playoff_state(valid_controller)

        assert isinstance(result, ValidationResult)
        assert result.valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
