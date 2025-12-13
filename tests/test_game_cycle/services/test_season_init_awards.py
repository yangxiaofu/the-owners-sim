"""
Tests for Awards Integration in SeasonInitializationService.

Tests the _calculate_awards() method and the "Calculate Awards" InitStep
that was added to the season initialization pipeline.

Part of Milestone 10: Awards System.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from src.game_cycle.services.season_init_service import (
    SeasonInitializationService,
    InitStep,
    StepStatus,
    StepResult,
)
from src.game_cycle.services.awards.result_models import (
    AwardResult,
    AllProTeam,
    ProBowlRoster,
    StatisticalLeadersResult,
)


# ============================================
# Fixtures
# ============================================

@pytest.fixture
def mock_db_path(tmp_path):
    """Create a temporary database path."""
    return str(tmp_path / "test_season_init.db")


@pytest.fixture
def service(mock_db_path):
    """Create a SeasonInitializationService instance."""
    return SeasonInitializationService(
        db_path=mock_db_path,
        dynasty_id="test_dynasty",
        from_season=2024,
        to_season=2025
    )


@pytest.fixture
def mock_award_result():
    """Create a mock AwardResult for testing."""
    return AwardResult(
        award_id="mvp",
        season=2024,
        winner=MagicMock(player_name="Patrick Mahomes", player_id=100, team_id=1),
        finalists=[],
        all_votes=[],
        candidates_evaluated=10
    )


@pytest.fixture
def mock_all_pro_result():
    """Create a mock AllProTeam result."""
    return AllProTeam(
        season=2024,
        first_team={},
        second_team={},
        total_selections=44
    )


@pytest.fixture
def mock_pro_bowl_result():
    """Create a mock ProBowlRoster result."""
    return ProBowlRoster(
        season=2024,
        afc_roster={},
        nfc_roster={},
        total_selections=88
    )


@pytest.fixture
def mock_stat_leaders_result():
    """Create a mock StatisticalLeadersResult."""
    return StatisticalLeadersResult(
        season=2024,
        leaders_by_category={},
        total_recorded=120
    )


# ============================================
# Pipeline Structure Tests
# ============================================

class TestAwardsPipelineStructure:
    """Tests for the awards step in the pipeline structure."""

    def test_awards_step_exists_in_pipeline(self, service):
        """Verify "Calculate Awards" step exists in the pipeline."""
        step_names = [step.name for step in service._steps]
        assert "Calculate Awards" in step_names

    def test_awards_step_position(self, service):
        """Verify awards step comes after "Archive Stats" and before "Reset Team Records"."""
        step_names = [step.name for step in service._steps]

        archive_idx = step_names.index("Archive Stats")
        awards_idx = step_names.index("Calculate Awards")
        reset_idx = step_names.index("Reset Team Records")

        assert awards_idx > archive_idx, "Awards should come after Archive Stats"
        assert awards_idx < reset_idx, "Awards should come before Reset Team Records"

    def test_awards_step_is_not_required(self, service):
        """Verify the awards step has required=False."""
        awards_step = None
        for step in service._steps:
            if step.name == "Calculate Awards":
                awards_step = step
                break

        assert awards_step is not None
        assert awards_step.required is False

    def test_awards_step_has_correct_handler(self, service):
        """Verify the awards step is wired to _calculate_awards method."""
        awards_step = None
        for step in service._steps:
            if step.name == "Calculate Awards":
                awards_step = step
                break

        assert awards_step is not None
        assert awards_step.handler == service._calculate_awards

    def test_awards_step_has_description(self, service):
        """Verify the awards step has a descriptive message."""
        awards_step = None
        for step in service._steps:
            if step.name == "Calculate Awards":
                awards_step = step
                break

        assert awards_step is not None
        assert len(awards_step.description) > 0
        assert "award" in awards_step.description.lower()


# ============================================
# Handler Method Tests
# ============================================

class TestCalculateAwardsHandler:
    """Tests for the _calculate_awards() handler method."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_returns_success_dict(self, mock_awards_class, service,
                                                     mock_award_result, mock_all_pro_result,
                                                     mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify _calculate_awards returns dict with success key."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        result = service._calculate_awards()

        assert isinstance(result, dict)
        assert "success" in result
        assert "message" in result
        assert result["success"] is True

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_uses_from_season(self, mock_awards_class, service):
        """Verify _calculate_awards uses from_season, not to_season."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        service._calculate_awards()

        # Verify AwardsService was instantiated with from_season
        mock_awards_class.assert_called_once_with(
            db_path=service._db_path,
            dynasty_id=service._dynasty_id,
            season=service._from_season  # Should use from_season (2024), not to_season (2025)
        )

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_calls_all_service_methods(self, mock_awards_class, service,
                                                         mock_award_result, mock_all_pro_result,
                                                         mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify all 4 awards service methods are called."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        service._calculate_awards()

        mock_service.awards_already_calculated.assert_called_once()
        mock_service.calculate_all_awards.assert_called_once()
        mock_service.select_all_pro_teams.assert_called_once()
        mock_service.select_pro_bowl_rosters.assert_called_once()
        mock_service.record_statistical_leaders.assert_called_once()

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_idempotency_skip(self, mock_awards_class, service):
        """Verify calculation skips when awards_already_calculated returns True."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        result = service._calculate_awards()

        # Should check for existing awards
        mock_service.awards_already_calculated.assert_called_once()

        # Should NOT call any calculation methods
        mock_service.calculate_all_awards.assert_not_called()
        mock_service.select_all_pro_teams.assert_not_called()
        mock_service.select_pro_bowl_rosters.assert_not_called()
        mock_service.record_statistical_leaders.assert_not_called()

        # Should return success with skipped flag
        assert result["success"] is True
        assert result.get("skipped") is True

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_returns_winners_dict(self, mock_awards_class, service,
                                                     mock_award_result):
        """Verify result includes winners dictionary."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False

        mock_results = {
            "mvp": mock_award_result,
            "opoy": AwardResult("opoy", 2024, None, [], [], 0)  # No winner
        }
        mock_service.calculate_all_awards.return_value = mock_results
        mock_service.select_all_pro_teams.return_value = AllProTeam(2024, {}, {}, 44)
        mock_service.select_pro_bowl_rosters.return_value = ProBowlRoster(2024, {}, {}, 88)
        mock_service.record_statistical_leaders.return_value = StatisticalLeadersResult(2024, {}, 120)

        result = service._calculate_awards()

        assert "winners" in result
        assert isinstance(result["winners"], dict)
        assert result["winners"]["mvp"] == "Patrick Mahomes"
        assert result["winners"]["opoy"] is None

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_returns_counts(self, mock_awards_class, service,
                                              mock_award_result, mock_all_pro_result,
                                              mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify result includes selection counts."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        result = service._calculate_awards()

        assert result["all_pro_selections"] == 44
        assert result["pro_bowl_selections"] == 88
        assert result["stat_leaders_recorded"] == 120

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_includes_season(self, mock_awards_class, service,
                                               mock_award_result, mock_all_pro_result,
                                               mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify result includes the season year."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        result = service._calculate_awards()

        assert result["season"] == 2024  # from_season


# ============================================
# Error Handling Tests
# ============================================

class TestAwardsErrorHandling:
    """Tests for error handling in awards calculation."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_handles_exception(self, mock_awards_class, service):
        """Verify graceful handling of exceptions."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.side_effect = Exception("Database error")

        result = service._calculate_awards()

        assert result["success"] is False
        assert "error" in result
        assert "Database error" in result["message"]

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_calculate_awards_failure_returns_error_message(self, mock_awards_class, service):
        """Verify error result contains error message."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.calculate_all_awards.side_effect = RuntimeError("Calculation failed")
        mock_service.awards_already_calculated.return_value = False

        result = service._calculate_awards()

        assert result["success"] is False
        assert "message" in result
        assert "failed" in result["message"].lower()

    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._apply_cap_rollover')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._generate_draft_class')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._generate_schedule')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._reset_team_records')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._calculate_awards')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._archive_stats')
    def test_awards_failure_doesnt_crash_pipeline(self, mock_archive, mock_awards, mock_reset,
                                                    mock_schedule, mock_draft, mock_cap, mock_db_path):
        """Verify pipeline continues after awards failure (required=False)."""
        # Setup mocks
        mock_archive.return_value = {"success": True, "message": "Archived"}
        mock_awards.return_value = {"success": False, "message": "Awards failed"}
        mock_reset.return_value = {"success": True, "message": "Reset"}
        mock_schedule.return_value = {"success": True, "message": "Schedule"}
        mock_draft.return_value = {"success": True, "message": "Draft"}
        mock_cap.return_value = {"success": True, "message": "Cap"}

        # Create service AFTER mocks are set up
        service = SeasonInitializationService(
            db_path=mock_db_path,
            dynasty_id="test_dynasty",
            from_season=2024,
            to_season=2025
        )

        results = service.run_all()

        # Find results by name
        results_dict = {r.step_name: r for r in results}

        # Awards step should fail
        assert results_dict["Calculate Awards"].status == StepStatus.FAILED

        # But subsequent required steps should still run and complete
        assert results_dict["Reset Team Records"].status == StepStatus.COMPLETED
        assert results_dict["Generate Schedule"].status == StepStatus.COMPLETED


# ============================================
# Integration Tests
# ============================================

class TestAwardsPipelineIntegration:
    """Integration tests with mocked AwardsService."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_full_pipeline_runs_awards_step(self, mock_awards_class, service,
                                             mock_award_result, mock_all_pro_result,
                                             mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify awards step runs during full pipeline execution."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        # Mock all other steps
        with patch.object(service, '_archive_stats', return_value={"success": True, "message": "Archived"}), \
             patch.object(service, '_reset_team_records', return_value={"success": True, "message": "Reset"}), \
             patch.object(service, '_generate_schedule', return_value={"success": True, "message": "Schedule"}), \
             patch.object(service, '_generate_draft_class', return_value={"success": True, "message": "Draft"}), \
             patch.object(service, '_apply_cap_rollover', return_value={"success": True, "message": "Cap"}):

            results = service.run_all()

        # Find awards result
        awards_result = None
        for result in results:
            if result.step_name == "Calculate Awards":
                awards_result = result
                break

        assert awards_result is not None
        assert awards_result.status == StepStatus.COMPLETED

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_skipped_when_already_calculated(self, mock_awards_class, service):
        """Verify full pipeline respects idempotency check."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        # Mock other steps
        with patch.object(service, '_archive_stats', return_value={"success": True, "message": "Archived"}), \
             patch.object(service, '_reset_team_records', return_value={"success": True, "message": "Reset"}), \
             patch.object(service, '_generate_schedule', return_value={"success": True, "message": "Schedule"}), \
             patch.object(service, '_generate_draft_class', return_value={"success": True, "message": "Draft"}), \
             patch.object(service, '_apply_cap_rollover', return_value={"success": True, "message": "Cap"}):

            results = service.run_all()

        # Awards should complete successfully (even though skipped)
        awards_result = None
        for result in results:
            if result.step_name == "Calculate Awards":
                awards_result = result
                break

        assert awards_result is not None
        assert awards_result.status == StepStatus.COMPLETED
        assert "already" in awards_result.message.lower()

    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._apply_cap_rollover')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._generate_draft_class')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._generate_schedule')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._reset_team_records')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._calculate_awards')
    @patch('src.game_cycle.services.season_init_service.SeasonInitializationService._archive_stats')
    def test_pipeline_continues_after_awards_failure(self, mock_archive, mock_awards, mock_reset,
                                                       mock_schedule, mock_draft, mock_cap, mock_db_path):
        """Verify non-required awards step doesn't block pipeline."""
        # Setup mocks - awards fails, others succeed
        mock_archive.return_value = {"success": True, "message": "Archived"}
        mock_awards.return_value = {"success": False, "message": "Awards failed", "error": "Fatal error"}
        mock_reset.return_value = {"success": True, "message": "Reset"}
        mock_schedule.return_value = {"success": True, "message": "Schedule"}
        mock_draft.return_value = {"success": True, "message": "Draft"}
        mock_cap.return_value = {"success": True, "message": "Cap"}

        # Create service AFTER mocks are set up
        service = SeasonInitializationService(
            db_path=mock_db_path,
            dynasty_id="test_dynasty",
            from_season=2024,
            to_season=2025
        )

        results = service.run_all()

        # Get results by name
        results_dict = {r.step_name: r for r in results}

        # Awards failed but pipeline continued
        assert results_dict["Calculate Awards"].status == StepStatus.FAILED
        assert results_dict["Reset Team Records"].status == StepStatus.COMPLETED
        assert results_dict["Generate Schedule"].status == StepStatus.COMPLETED


# ============================================
# Mock Return Value Tests
# ============================================

class TestAwardsReturnValues:
    """Tests for different return value scenarios."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_with_empty_results(self, mock_awards_class, service):
        """Verify handling of empty award results (no candidates)."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {}  # Empty results
        mock_service.select_all_pro_teams.return_value = AllProTeam(2024, {}, {}, 0)
        mock_service.select_pro_bowl_rosters.return_value = ProBowlRoster(2024, {}, {}, 0)
        mock_service.record_statistical_leaders.return_value = StatisticalLeadersResult(2024, {}, 0)

        result = service._calculate_awards()

        assert result["success"] is True
        assert result["awards_calculated"] == 0
        assert result["all_pro_selections"] == 0
        assert result["pro_bowl_selections"] == 0
        assert result["stat_leaders_recorded"] == 0

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_with_no_winner(self, mock_awards_class, service):
        """Verify handling when award has no winner."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False

        # Award results with no winners
        mock_results = {
            "mvp": AwardResult("mvp", 2024, None, [], [], 0),
            "opoy": AwardResult("opoy", 2024, None, [], [], 0),
        }
        mock_service.calculate_all_awards.return_value = mock_results
        mock_service.select_all_pro_teams.return_value = AllProTeam(2024, {}, {}, 44)
        mock_service.select_pro_bowl_rosters.return_value = ProBowlRoster(2024, {}, {}, 88)
        mock_service.record_statistical_leaders.return_value = StatisticalLeadersResult(2024, {}, 120)

        result = service._calculate_awards()

        assert result["success"] is True
        assert result["winners"]["mvp"] is None
        assert result["winners"]["opoy"] is None

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_logs_winners(self, mock_awards_class, service, caplog,
                                  mock_award_result, mock_all_pro_result,
                                  mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify logging occurs during awards calculation."""
        import logging
        caplog.set_level(logging.INFO)

        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        service._calculate_awards()

        # Check logs contain award information
        log_text = caplog.text.lower()
        assert "awards" in log_text or "calculating" in log_text


# ============================================
# Service Creation Tests
# ============================================

class TestAwardsServiceCreation:
    """Tests for AwardsService instantiation."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_service_created_with_correct_params(self, mock_awards_class, service):
        """Verify AwardsService is instantiated with correct parameters."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        service._calculate_awards()

        mock_awards_class.assert_called_once_with(
            db_path=service._db_path,
            dynasty_id=service._dynasty_id,
            season=service._from_season
        )

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_service_uses_from_season_not_to_season(self, mock_awards_class, service):
        """Explicitly verify from_season is used, not to_season."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        service._calculate_awards()

        call_args = mock_awards_class.call_args
        assert call_args[1]["season"] == 2024  # from_season
        assert call_args[1]["season"] != 2025  # NOT to_season


# ============================================
# Edge Cases
# ============================================

class TestAwardsEdgeCases:
    """Edge case tests for awards calculation."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_first_season_year_one(self, mock_awards_class, mock_db_path):
        """Verify awards work for dynasty year 1."""
        service = SeasonInitializationService(
            db_path=mock_db_path,
            dynasty_id="test_dynasty",
            from_season=2024,
            to_season=2025
        )

        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {}
        mock_service.select_all_pro_teams.return_value = AllProTeam(2024, {}, {}, 44)
        mock_service.select_pro_bowl_rosters.return_value = ProBowlRoster(2024, {}, {}, 88)
        mock_service.record_statistical_leaders.return_value = StatisticalLeadersResult(2024, {}, 120)

        result = service._calculate_awards()

        assert result["success"] is True

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_with_partial_data(self, mock_awards_class, service):
        """Verify handling when some methods succeed and some fail."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False

        # Some methods succeed, one fails
        mock_service.calculate_all_awards.return_value = {"mvp": MagicMock()}
        mock_service.select_all_pro_teams.return_value = AllProTeam(2024, {}, {}, 44)
        mock_service.select_pro_bowl_rosters.side_effect = Exception("Pro Bowl failed")

        # The exception should propagate and be caught by handler
        result = service._calculate_awards()

        assert result["success"] is False
        assert "error" in result

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_step_status_on_success(self, mock_awards_class, service,
                                            mock_award_result, mock_all_pro_result,
                                            mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify step status is COMPLETED on success."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        awards_step = None
        for step in service._steps:
            if step.name == "Calculate Awards":
                awards_step = step
                break

        result = service._run_step(awards_step)

        assert result.status == StepStatus.COMPLETED

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_step_status_on_failure(self, mock_awards_class, service):
        """Verify step status is FAILED on exception."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.side_effect = Exception("Fatal error")

        awards_step = None
        for step in service._steps:
            if step.name == "Calculate Awards":
                awards_step = step
                break

        result = service._run_step(awards_step)

        assert result.status == StepStatus.FAILED
        assert "Fatal error" in result.message

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_step_skipped_attribute(self, mock_awards_class, service):
        """Verify result has 'skipped' key when awards are already calculated."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = True

        result = service._calculate_awards()

        assert "skipped" in result
        assert result["skipped"] is True
        assert result["success"] is True


# ============================================
# Result Format Tests
# ============================================

class TestAwardsResultFormat:
    """Tests for the structure of awards calculation results."""

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_result_has_all_expected_keys(self, mock_awards_class, service,
                                                   mock_award_result, mock_all_pro_result,
                                                   mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify result dictionary has all expected keys."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {"mvp": mock_award_result}
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        result = service._calculate_awards()

        expected_keys = [
            "success", "season", "awards_calculated", "all_pro_selections",
            "pro_bowl_selections", "stat_leaders_recorded", "winners", "message"
        ]
        for key in expected_keys:
            assert key in result

    @patch('src.game_cycle.services.awards_service.AwardsService')
    def test_awards_result_message_is_descriptive(self, mock_awards_class, service,
                                                    mock_award_result, mock_all_pro_result,
                                                    mock_pro_bowl_result, mock_stat_leaders_result):
        """Verify result message contains useful information."""
        mock_service = MagicMock()
        mock_awards_class.return_value = mock_service
        mock_service.awards_already_calculated.return_value = False
        mock_service.calculate_all_awards.return_value = {
            "mvp": mock_award_result,
            "opoy": mock_award_result
        }
        mock_service.select_all_pro_teams.return_value = mock_all_pro_result
        mock_service.select_pro_bowl_rosters.return_value = mock_pro_bowl_result
        mock_service.record_statistical_leaders.return_value = mock_stat_leaders_result

        result = service._calculate_awards()

        message = result["message"].lower()
        assert "award" in message
        assert "2024" in message or str(service._from_season) in message
        assert "all-pro" in message or "pro bowl" in message
