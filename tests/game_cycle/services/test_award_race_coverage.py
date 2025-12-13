"""
Unit tests for AwardRaceCoverageService.

Part of Milestone 12: Media Coverage, Tollgate 5.

Tests:
- MVP coverage generation (6 tests)
- Rookie coverage generation (5 tests)
- Award prediction generation (4 tests)
- Movement detection (2 tests)
- Edge cases and fallbacks (3 tests)
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from src.game_cycle.services.award_race_coverage import (
    AwardRaceCoverageService,
    AwardCoverageType,
    MovementType,
    MovementInfo,
    RaceContext,
    HeadlineData,
    AWARD_MVP,
    AWARD_OROY,
    AWARD_DROY,
    AWARD_OPOY,
    AWARD_DPOY,
)
from src.game_cycle.database.awards_api import AwardRaceEntry


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_db():
    """Create mock database."""
    return MagicMock()


@pytest.fixture
def mock_awards_api():
    """Create mock AwardsAPI."""
    return MagicMock()


@pytest.fixture
def mock_media_api():
    """Create mock MediaCoverageAPI."""
    return MagicMock()


@pytest.fixture
def service(mock_db, mock_awards_api, mock_media_api):
    """Create service with mocked dependencies."""
    with patch('src.game_cycle.services.award_race_coverage.AwardsAPI') as awards_cls, \
         patch('src.game_cycle.services.award_race_coverage.MediaCoverageAPI') as media_cls:
        awards_cls.return_value = mock_awards_api
        media_cls.return_value = mock_media_api

        svc = AwardRaceCoverageService(mock_db, "test_dynasty", 2025)
        svc._awards_api = mock_awards_api
        svc._media_api = mock_media_api
        return svc


@pytest.fixture
def sample_mvp_standings():
    """Create sample MVP standings."""
    return [
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="mvp",
            player_id=101,
            team_id=1,
            position="QB",
            cumulative_score=85.5,
            rank=1,
            week_score=9.2,
            first_name="Patrick",
            last_name="Mahomes"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="mvp",
            player_id=102,
            team_id=2,
            position="QB",
            cumulative_score=80.0,
            rank=2,
            week_score=8.5,
            first_name="Josh",
            last_name="Allen"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="mvp",
            player_id=103,
            team_id=3,
            position="QB",
            cumulative_score=75.0,
            rank=3,
            week_score=7.0,
            first_name="Jalen",
            last_name="Hurts"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="mvp",
            player_id=104,
            team_id=4,
            position="RB",
            cumulative_score=70.0,
            rank=4,
            week_score=8.0,
            first_name="Christian",
            last_name="McCaffrey"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="mvp",
            player_id=105,
            team_id=5,
            position="WR",
            cumulative_score=65.0,
            rank=5,
            week_score=9.0,
            first_name="Tyreek",
            last_name="Hill"
        ),
    ]


@pytest.fixture
def sample_previous_standings():
    """Create sample previous week standings (before movement)."""
    return [
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=9,
            award_type="mvp",
            player_id=101,
            team_id=1,
            position="QB",
            cumulative_score=76.3,
            rank=1,
            week_score=8.5,
            first_name="Patrick",
            last_name="Mahomes"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=9,
            award_type="mvp",
            player_id=103,
            team_id=3,
            position="QB",
            cumulative_score=73.0,
            rank=2,  # Josh Allen was 4th, now 2nd (rising)
            week_score=7.5,
            first_name="Jalen",
            last_name="Hurts"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=9,
            award_type="mvp",
            player_id=104,
            team_id=4,
            position="RB",
            cumulative_score=72.0,
            rank=3,
            week_score=7.0,
            first_name="Christian",
            last_name="McCaffrey"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=9,
            award_type="mvp",
            player_id=102,
            team_id=2,
            position="QB",
            cumulative_score=71.5,
            rank=4,
            week_score=8.0,
            first_name="Josh",
            last_name="Allen"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=9,
            award_type="mvp",
            player_id=105,
            team_id=5,
            position="WR",
            cumulative_score=68.0,
            rank=5,
            week_score=6.5,
            first_name="Tyreek",
            last_name="Hill"
        ),
    ]


@pytest.fixture
def sample_rookie_standings():
    """Create sample OROY standings."""
    return [
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="oroy",
            player_id=201,
            team_id=10,
            position="QB",
            cumulative_score=60.0,
            rank=1,
            week_score=7.5,
            first_name="Caleb",
            last_name="Williams"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="oroy",
            player_id=202,
            team_id=11,
            position="WR",
            cumulative_score=55.0,
            rank=2,
            week_score=8.0,
            first_name="Marvin",
            last_name="Harrison"
        ),
    ]


@pytest.fixture
def sample_droy_standings():
    """Create sample DROY standings."""
    return [
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="droy",
            player_id=301,
            team_id=20,
            position="EDGE",
            cumulative_score=55.0,
            rank=1,
            week_score=7.0,
            first_name="Dallas",
            last_name="Turner"
        ),
        AwardRaceEntry(
            dynasty_id="test_dynasty",
            season=2025,
            week=10,
            award_type="droy",
            player_id=302,
            team_id=21,
            position="CB",
            cumulative_score=50.0,
            rank=2,
            week_score=6.5,
            first_name="Quinyon",
            last_name="Mitchell"
        ),
    ]


# =============================================================================
# MVP COVERAGE TESTS (6 tests)
# =============================================================================

class TestMVPCoverage:
    """Tests for MVP coverage generation."""

    def test_generate_mvp_leader_headline(self, service, sample_mvp_standings, sample_previous_standings):
        """Test generating headline for MVP leader."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_mvp_standings,  # Current week
            sample_previous_standings,  # Previous week
        ]

        headlines = service.generate_weekly_mvp_coverage(week=10)

        # Should have at least one headline
        assert len(headlines) >= 1

        # First headline should be about leader
        leader_headline = headlines[0]
        assert "Patrick Mahomes" in leader_headline["headline"]
        assert leader_headline["headline_type"] == "AWARD"
        assert leader_headline["player_ids"] == [101]

    def test_detect_rising_candidate(self, service, sample_mvp_standings, sample_previous_standings):
        """Test detecting rising MVP candidate."""
        # Josh Allen moved from rank 4 to rank 2
        movements = service._detect_movement(sample_mvp_standings, sample_previous_standings)

        josh_allen = next((m for m in movements if m.player_id == 102), None)
        assert josh_allen is not None
        assert josh_allen.movement_type == MovementType.RISING
        assert josh_allen.spots_moved == 2  # 4 -> 2

    def test_detect_falling_candidate(self, service, sample_mvp_standings, sample_previous_standings):
        """Test detecting falling MVP candidate."""
        # Jalen Hurts moved from rank 2 to rank 3
        movements = service._detect_movement(sample_mvp_standings, sample_previous_standings)

        jalen_hurts = next((m for m in movements if m.player_id == 103), None)
        assert jalen_hurts is not None
        # Only 1 spot move, should be STABLE (threshold is 2)
        assert jalen_hurts.movement_type == MovementType.STABLE

    def test_handle_tie_scenario(self, service):
        """Test handling when scores are very close."""
        tight_standings = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=10,
                award_type="mvp", player_id=1, team_id=1, position="QB",
                cumulative_score=50.0, rank=1, first_name="Player", last_name="One"
            ),
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=10,
                award_type="mvp", player_id=2, team_id=2, position="QB",
                cumulative_score=49.5, rank=2, first_name="Player", last_name="Two"
            ),
        ]
        movements = service._detect_movement(tight_standings, [])
        context = service._build_race_context(AWARD_MVP, tight_standings, movements, 10)

        assert context.is_tight_race is True
        assert context.gap_to_second == 0.5

    def test_empty_standings_fallback(self, service):
        """Test handling empty standings."""
        service._awards_api.get_award_race_standings.return_value = []

        headlines = service.generate_weekly_mvp_coverage(week=10)

        assert headlines == []

    def test_runaway_leader_detection(self, service):
        """Test detecting runaway leader."""
        runaway_standings = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=15,
                award_type="mvp", player_id=1, team_id=1, position="QB",
                cumulative_score=100.0, rank=1, first_name="Patrick", last_name="Mahomes"
            ),
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=15,
                award_type="mvp", player_id=2, team_id=2, position="QB",
                cumulative_score=75.0, rank=2, first_name="Josh", last_name="Allen"
            ),
        ]
        movements = service._detect_movement(runaway_standings, [])
        context = service._build_race_context(AWARD_MVP, runaway_standings, movements, 15)

        assert context.is_runaway is True
        assert context.gap_to_second == 25.0


# =============================================================================
# ROOKIE COVERAGE TESTS (5 tests)
# =============================================================================

class TestRookieCoverage:
    """Tests for rookie coverage generation."""

    def test_generate_oroy_headlines(self, service, sample_rookie_standings):
        """Test generating OROY headlines."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_rookie_standings,  # OROY current
            [],  # OROY previous
            [],  # DROY current
            [],  # DROY previous
        ]

        headlines = service.generate_weekly_rookie_coverage(week=10)

        # Should have OROY headline
        assert any("Caleb Williams" in h["headline"] for h in headlines)

    def test_generate_droy_headlines(self, service, sample_droy_standings):
        """Test generating DROY headlines."""
        service._awards_api.get_award_race_standings.side_effect = [
            [],  # OROY current
            [],  # OROY previous
            sample_droy_standings,  # DROY current
            [],  # DROY previous
        ]

        headlines = service.generate_weekly_rookie_coverage(week=10)

        # Should have DROY headline
        assert any("Dallas Turner" in h["headline"] for h in headlines)

    def test_combined_rookie_headline(self, service, sample_rookie_standings, sample_droy_standings):
        """Test generating combined rookie headline."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_rookie_standings,  # OROY current
            [],  # OROY previous
            sample_droy_standings,  # DROY current
            [],  # DROY previous
        ]

        # Week 10 is even, so combined headline should be generated
        headlines = service.generate_weekly_rookie_coverage(week=10)

        combined = [h for h in headlines if "Caleb Williams" in h["headline"] and "Dallas Turner" in h["headline"]]
        assert len(combined) == 1

    def test_rookie_comparison_narrative(self, service, sample_rookie_standings):
        """Test rookie coverage includes leader narrative."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_rookie_standings,
            [],
            [],
            [],
        ]

        headlines = service.generate_weekly_rookie_coverage(week=10)

        # Leader headline should mention the leader
        leader_headline = next((h for h in headlines if "Caleb Williams" in h["headline"]), None)
        assert leader_headline is not None
        assert leader_headline["sentiment"] in ["POSITIVE", "HYPE"]

    def test_missing_data_fallback(self, service):
        """Test handling missing rookie data."""
        service._awards_api.get_award_race_standings.return_value = []

        headlines = service.generate_weekly_rookie_coverage(week=10)

        # Should handle gracefully with no crashes
        assert isinstance(headlines, list)


# =============================================================================
# PREDICTION TESTS (4 tests)
# =============================================================================

class TestAwardPredictions:
    """Tests for award prediction generation."""

    def test_mid_season_prediction(self, service, sample_mvp_standings):
        """Test mid-season MVP prediction at Week 9."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_mvp_standings,  # MVP
            sample_mvp_standings,  # OPOY
            sample_mvp_standings,  # DPOY
        ]

        headlines = service.generate_award_predictions(week=9)

        # Should have at least MVP prediction
        assert len(headlines) >= 1

        # First headline should be MVP related
        mvp_pred = headlines[0]
        assert mvp_pred["headline_type"] == "AWARD"
        assert "metadata" in mvp_pred
        # Verify it's an award prediction with proper structure
        assert mvp_pred["metadata"].get("coverage_type") == "AWARD_PREDICTION" or \
               mvp_pred["metadata"].get("award_type") in ["mvp", "opoy", "dpoy"]

    def test_late_season_prediction(self, service, sample_mvp_standings):
        """Test late-season prediction at Week 15+."""
        service._awards_api.get_award_race_standings.side_effect = [
            sample_mvp_standings,
            sample_mvp_standings,
            sample_mvp_standings,
        ]

        headlines = service.generate_award_predictions(week=15)

        assert len(headlines) >= 1
        # Late season predictions should have higher priority
        for h in headlines:
            assert h["priority"] >= 60

    def test_confidence_calculation(self, service, sample_mvp_standings):
        """Test confidence percentage calculation."""
        # Test with clear leader
        confidence = service._calculate_confidence(sample_mvp_standings, week=15)

        # With 5.5 point gap and week 15, should have moderate-high confidence
        assert confidence >= 50
        assert confidence <= 100

    def test_no_prediction_mid_week(self, service, sample_mvp_standings):
        """Test no predictions generated at non-key weeks."""
        service._awards_api.get_award_race_standings.return_value = sample_mvp_standings

        # Week 10 is not a key week for predictions
        headlines = service.generate_award_predictions(week=10)

        assert headlines == []


# =============================================================================
# MOVEMENT DETECTION TESTS (2 tests)
# =============================================================================

class TestMovementDetection:
    """Tests for movement detection algorithm."""

    def test_new_entry_detection(self, service, sample_mvp_standings):
        """Test detecting new entry to top 5."""
        # Previous week has different player
        previous = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=9,
                award_type="mvp", player_id=999, team_id=30, position="QB",
                cumulative_score=70.0, rank=5, first_name="Old", last_name="Player"
            ),
        ]

        movements = service._detect_movement(sample_mvp_standings, previous)

        # Tyreek Hill (105) should be NEW_ENTRY since he wasn't in previous
        tyreek = next((m for m in movements if m.player_id == 105), None)
        assert tyreek is not None
        assert tyreek.movement_type == MovementType.NEW_ENTRY

    def test_stable_player_detection(self, service):
        """Test detecting stable player (±1 spot)."""
        current = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=10,
                award_type="mvp", player_id=1, team_id=1, position="QB",
                cumulative_score=80.0, rank=2, first_name="Stable", last_name="Player"
            ),
        ]
        previous = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=9,
                award_type="mvp", player_id=1, team_id=1, position="QB",
                cumulative_score=75.0, rank=1, first_name="Stable", last_name="Player"
            ),
        ]

        movements = service._detect_movement(current, previous)

        # 1 spot drop should be STABLE
        assert movements[0].movement_type == MovementType.STABLE


# =============================================================================
# EDGE CASES AND INTEGRATION (3 tests)
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and integration."""

    def test_week_before_tracking_start(self, service):
        """Test no coverage before tracking start week."""
        headlines = service.generate_weekly_mvp_coverage(week=5)

        # Should return empty before week 6
        assert headlines == []

    def test_generate_all_coverage(self, service, sample_mvp_standings, sample_rookie_standings, sample_droy_standings):
        """Test generating all coverage types."""
        service._awards_api.get_award_race_standings.side_effect = [
            # MVP coverage calls
            sample_mvp_standings,  # MVP current
            [],  # MVP previous
            # Rookie coverage calls
            sample_rookie_standings,  # OROY current
            [],  # OROY previous
            sample_droy_standings,  # DROY current
            [],  # DROY previous
            # Prediction calls (week 9)
            sample_mvp_standings,  # MVP
            sample_mvp_standings,  # OPOY
            sample_mvp_standings,  # DPOY
        ]

        headlines = service.generate_all_coverage(week=9)

        # Should have multiple headlines
        assert len(headlines) >= 3

        # Should have mix of coverage types
        has_mvp = any("Patrick Mahomes" in h["headline"] or "MVP" in h["headline"] for h in headlines)
        has_rookie = any("Caleb Williams" in h["headline"] or "Dallas Turner" in h["headline"] for h in headlines)

        assert has_mvp
        assert has_rookie

    def test_missing_player_names(self, service):
        """Test handling entries with missing player names."""
        standings = [
            AwardRaceEntry(
                dynasty_id="test_dynasty", season=2025, week=10,
                award_type="mvp", player_id=1, team_id=1, position="QB",
                cumulative_score=80.0, rank=1,
                first_name=None, last_name=None  # Missing names
            ),
        ]
        service._awards_api.get_award_race_standings.side_effect = [
            standings,
            [],
        ]

        headlines = service.generate_weekly_mvp_coverage(week=10)

        # Should handle gracefully with fallback
        assert len(headlines) >= 1
        assert "Unknown" in headlines[0]["headline"]


# =============================================================================
# TEMPLATE VALIDATION TESTS
# =============================================================================

class TestTemplates:
    """Tests for template system."""

    def test_mvp_templates_have_placeholders(self):
        """Verify MVP templates have expected placeholders."""
        from src.game_cycle.services.award_race_coverage import (
            MVP_LEADER_TEMPLATES,
            MVP_RISING_TEMPLATES,
            MVP_FALLING_TEMPLATES,
        )

        for template in MVP_LEADER_TEMPLATES:
            assert "{player}" in template or "{" in template

        for template in MVP_RISING_TEMPLATES:
            assert "{player}" in template

        for template in MVP_FALLING_TEMPLATES:
            assert "{player}" in template

    def test_rookie_templates_have_placeholders(self):
        """Verify rookie templates have expected placeholders."""
        from src.game_cycle.services.award_race_coverage import (
            OROY_LEADER_TEMPLATES,
            DROY_LEADER_TEMPLATES,
            ROOKIE_COMBINED_TEMPLATES,
        )

        for template in OROY_LEADER_TEMPLATES:
            assert "{player}" in template

        for template in DROY_LEADER_TEMPLATES:
            assert "{player}" in template

        for template in ROOKIE_COMBINED_TEMPLATES:
            assert "{oroy_leader}" in template
            assert "{droy_leader}" in template

    def test_prediction_templates_have_placeholders(self):
        """Verify prediction templates have expected placeholders."""
        from src.game_cycle.services.award_race_coverage import (
            MID_SEASON_PREDICTION_TEMPLATES,
            LATE_SEASON_PREDICTION_TEMPLATES,
        )

        for template in MID_SEASON_PREDICTION_TEMPLATES:
            assert "{player}" in template

        for template in LATE_SEASON_PREDICTION_TEMPLATES:
            assert "{player}" in template

    def test_template_count(self):
        """Verify we have 45+ templates total."""
        from src.game_cycle.services.award_race_coverage import (
            MVP_LEADER_TEMPLATES,
            MVP_RISING_TEMPLATES,
            MVP_FALLING_TEMPLATES,
            MVP_TIGHT_RACE_TEMPLATES,
            MVP_RUNAWAY_TEMPLATES,
            MVP_NEWCOMER_TEMPLATES,
            OROY_LEADER_TEMPLATES,
            OROY_RISING_TEMPLATES,
            DROY_LEADER_TEMPLATES,
            DROY_RISING_TEMPLATES,
            ROOKIE_COMBINED_TEMPLATES,
            MID_SEASON_PREDICTION_TEMPLATES,
            LATE_SEASON_PREDICTION_TEMPLATES,
            PREDICTION_UNCERTAINTY_TEMPLATES,
        )

        total = (
            len(MVP_LEADER_TEMPLATES) +
            len(MVP_RISING_TEMPLATES) +
            len(MVP_FALLING_TEMPLATES) +
            len(MVP_TIGHT_RACE_TEMPLATES) +
            len(MVP_RUNAWAY_TEMPLATES) +
            len(MVP_NEWCOMER_TEMPLATES) +
            len(OROY_LEADER_TEMPLATES) +
            len(OROY_RISING_TEMPLATES) +
            len(DROY_LEADER_TEMPLATES) +
            len(DROY_RISING_TEMPLATES) +
            len(ROOKIE_COMBINED_TEMPLATES) +
            len(MID_SEASON_PREDICTION_TEMPLATES) +
            len(LATE_SEASON_PREDICTION_TEMPLATES) +
            len(PREDICTION_UNCERTAINTY_TEMPLATES)
        )

        assert total >= 45, f"Expected 45+ templates, got {total}"
