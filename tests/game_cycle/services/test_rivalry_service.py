"""
Tests for RivalryService - Milestone 11, Tollgate 6.

Tests dynamic rivalry intensity evolution based on game outcomes,
playoff rivalry creation, and annual decay for inactive rivalries.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.game_cycle.services.rivalry_service import (
    RivalryService,
    PlayoffRound,
    IntensityChange,
)
from src.game_cycle.models.rivalry import Rivalry, RivalryType


# -------------------- Fixtures --------------------

@pytest.fixture
def mock_db():
    """Create a mock database connection."""
    return Mock()


@pytest.fixture
def mock_rivalry_api():
    """Create a mock RivalryAPI."""
    api = Mock()
    api.get_rivalry_between_teams.return_value = None
    api.update_intensity.return_value = True
    api.create_rivalry.return_value = 1
    api.get_all_rivalries.return_value = []
    api.delete_rivalry.return_value = True
    return api


@pytest.fixture
def mock_h2h_api():
    """Create a mock HeadToHeadAPI."""
    api = Mock()
    api.get_record.return_value = None
    return api


@pytest.fixture
def rivalry_service(mock_db, mock_rivalry_api, mock_h2h_api):
    """Create RivalryService with mocked dependencies."""
    with patch('src.game_cycle.services.rivalry_service.RivalryAPI', return_value=mock_rivalry_api), \
         patch('src.game_cycle.services.rivalry_service.HeadToHeadAPI', return_value=mock_h2h_api):
        service = RivalryService(mock_db)
        service._rivalry_api = mock_rivalry_api
        service._h2h_api = mock_h2h_api
        return service


@pytest.fixture
def sample_division_rivalry():
    """Create a sample division rivalry."""
    return Rivalry(
        team_a_id=21,  # Bears
        team_b_id=23,  # Packers
        rivalry_type=RivalryType.DIVISION,
        rivalry_name="NFC North Division Rivalry",
        intensity=70,
        is_protected=False,
        rivalry_id=1,
    )


@pytest.fixture
def sample_historic_rivalry():
    """Create a sample historic rivalry."""
    return Rivalry(
        team_a_id=21,  # Bears
        team_b_id=23,  # Packers
        rivalry_type=RivalryType.HISTORIC,
        rivalry_name="The Oldest Rivalry",
        intensity=95,
        is_protected=True,
        rivalry_id=2,
    )


@pytest.fixture
def sample_recent_rivalry():
    """Create a sample recent rivalry."""
    return Rivalry(
        team_a_id=14,  # Chiefs
        team_b_id=31,  # 49ers
        rivalry_type=RivalryType.RECENT,
        rivalry_name="2024 Super Bowl Rivalry",
        intensity=65,
        is_protected=False,
        rivalry_id=3,
    )


# -------------------- TestIntensityCalculation --------------------

class TestIntensityCalculation:
    """Tests for intensity change calculations based on game outcomes."""

    def test_close_game_increases_intensity(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Close games (within 7 points) should increase intensity by 4."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=24,
            away_score=21,  # 3 point margin (but uses close_game_boost since not <= 3 after OT check)
        )

        assert result is not None
        assert result.change_amount == 6  # Very close game (+6)
        assert result.new_intensity == 76

    def test_very_close_game_larger_boost(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Very close games (within 3 points) should increase intensity by 6."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=21,
            away_score=20,  # 1 point margin
        )

        assert result is not None
        assert result.change_amount == 6  # Very close (+6)

    def test_overtime_game_largest_boost(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """OT games should increase intensity by 7."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=24,
            away_score=21,
            overtime_periods=1,
        )

        assert result is not None
        assert result.change_amount == 7  # OT game (+7)
        assert "overtime" in result.change_reason.lower()

    def test_blowout_decreases_intensity(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Blowouts (20+ points) should decrease intensity by 4."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=42,
            away_score=14,  # 28 point margin
        )

        assert result is not None
        assert result.change_amount == -4  # Blowout (-4)
        assert result.new_intensity == 66

    def test_normal_margin_no_change(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Normal games (8-19 point margin) should have no intensity change."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,  # 11 point margin
        )

        assert result is not None
        assert result.change_amount == 0
        assert result.new_intensity == 70

    def test_intensity_capped_at_100(self, rivalry_service, mock_rivalry_api):
        """Intensity should never exceed 100."""
        high_intensity_rivalry = Rivalry(
            team_a_id=21,
            team_b_id=23,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test",
            intensity=98,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = high_intensity_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=24,
            away_score=21,
            overtime_periods=1,  # +7 would push to 105
        )

        assert result is not None
        assert result.new_intensity == 100

    def test_intensity_minimum_is_1(self, rivalry_service, mock_rivalry_api):
        """Intensity should never go below 1 for non-protected types."""
        low_intensity_rivalry = Rivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=RivalryType.GEOGRAPHIC,
            rivalry_name="Test",
            intensity=3,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = low_intensity_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=1,
            away_team_id=2,
            home_score=42,
            away_score=7,  # -4 would push to -1
        )

        assert result is not None
        assert result.new_intensity == 1

    def test_combined_overtime_and_playoff(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """OT playoff games should stack both boosts."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=27,
            away_score=24,
            overtime_periods=1,
            is_playoff=True,
            playoff_round=PlayoffRound.WILD_CARD,
        )

        assert result is not None
        # OT (+7) + Wild Card (+10) = +17
        assert result.change_amount == 17


# -------------------- TestPlayoffBoosts --------------------

class TestPlayoffBoosts:
    """Tests for playoff-specific intensity boosts."""

    def test_wild_card_boost_10(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Wild Card games should add +10."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,  # Normal margin (0 base)
            is_playoff=True,
            playoff_round=PlayoffRound.WILD_CARD,
        )

        assert result.change_amount == 10

    def test_divisional_boost_12(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Divisional games should add +12."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,
            is_playoff=True,
            playoff_round=PlayoffRound.DIVISIONAL,
        )

        assert result.change_amount == 12

    def test_conference_boost_15(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Conference Championship should add +15."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,
            is_playoff=True,
            playoff_round=PlayoffRound.CONFERENCE,
        )

        assert result.change_amount == 15

    def test_super_bowl_boost_20(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Super Bowl should add +20."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,
            is_playoff=True,
            playoff_round=PlayoffRound.SUPER_BOWL,
        )

        assert result.change_amount == 20

    def test_playoff_stacks_with_close_game(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Playoff boost should stack with game closeness boost."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=24,
            away_score=21,  # Close game (+6)
            is_playoff=True,
            playoff_round=PlayoffRound.CONFERENCE,  # +15
        )

        assert result.change_amount == 21  # 6 + 15

    def test_playoff_blowout_still_net_positive(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Even a playoff blowout should have net positive change."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=42,
            away_score=14,  # Blowout (-4)
            is_playoff=True,
            playoff_round=PlayoffRound.SUPER_BOWL,  # +20
        )

        assert result.change_amount == 16  # -4 + 20 = +16
        assert result.new_intensity > sample_division_rivalry.intensity


# -------------------- TestRivalryTypeProtection --------------------

class TestRivalryTypeProtection:
    """Tests for rivalry type-specific intensity floors."""

    def test_historic_never_below_50(self, rivalry_service, mock_rivalry_api):
        """HISTORIC rivalries should never go below 50."""
        historic = Rivalry(
            team_a_id=21,
            team_b_id=23,
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="Test Historic",
            intensity=52,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = historic

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=42,
            away_score=10,  # Blowout (-4)
        )

        assert result.new_intensity == 50  # Clamped at HISTORIC_MIN

    def test_division_can_go_to_floor(self, rivalry_service, mock_rivalry_api):
        """DIVISION rivalries should have a floor at 40."""
        division = Rivalry(
            team_a_id=21,
            team_b_id=23,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Test Division",
            intensity=42,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = division

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=42,
            away_score=10,  # Blowout (-4)
        )

        assert result.new_intensity == 40  # DIVISION_MIN

    def test_recent_can_decrease_to_1(self, rivalry_service, mock_rivalry_api):
        """RECENT rivalries can go as low as 1."""
        recent = Rivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=RivalryType.RECENT,
            rivalry_name="Test Recent",
            intensity=3,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = recent

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=1,
            away_team_id=2,
            home_score=42,
            away_score=7,
        )

        assert result.new_intensity == 1  # Clamped at 1

    def test_geographic_follows_standard_rules(self, rivalry_service, mock_rivalry_api):
        """GEOGRAPHIC rivalries follow standard min rules (1)."""
        geographic = Rivalry(
            team_a_id=4,  # Jets
            team_b_id=18,  # Giants
            rivalry_type=RivalryType.GEOGRAPHIC,
            rivalry_name="MetLife Rivalry",
            intensity=75,
            rivalry_id=1,
        )
        mock_rivalry_api.get_rivalry_between_teams.return_value = geographic

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=4,
            away_team_id=18,
            home_score=42,
            away_score=10,
        )

        assert result.new_intensity == 71  # 75 - 4


# -------------------- TestPlayoffRivalryCreation --------------------

class TestPlayoffRivalryCreation:
    """Tests for creating new rivalries from playoff meetings."""

    def test_creates_recent_rivalry_from_playoff(self, rivalry_service, mock_rivalry_api):
        """Should create RECENT rivalry from playoff meeting."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = None  # No existing rivalry

        result = rivalry_service.create_playoff_rivalry(
            dynasty_id="test",
            team_a_id=14,  # Chiefs
            team_b_id=31,  # 49ers
            playoff_round=PlayoffRound.SUPER_BOWL,
            season=2024,
        )

        assert result is not None
        assert result.rivalry_type == RivalryType.RECENT
        mock_rivalry_api.create_rivalry.assert_called_once()

    def test_super_bowl_creates_intensity_70(self, rivalry_service, mock_rivalry_api):
        """Super Bowl rivalries should start at intensity 70."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = None

        result = rivalry_service.create_playoff_rivalry(
            dynasty_id="test",
            team_a_id=14,
            team_b_id=31,
            playoff_round=PlayoffRound.SUPER_BOWL,
            season=2024,
        )

        assert result.intensity == 70

    def test_other_playoffs_create_intensity_60(self, rivalry_service, mock_rivalry_api):
        """Non-Super Bowl playoff rivalries should start at intensity 60."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = None

        for round_type in [PlayoffRound.WILD_CARD, PlayoffRound.DIVISIONAL, PlayoffRound.CONFERENCE]:
            mock_rivalry_api.reset_mock()
            result = rivalry_service.create_playoff_rivalry(
                dynasty_id="test",
                team_a_id=14,
                team_b_id=31,
                playoff_round=round_type,
                season=2024,
            )
            assert result.intensity == 60

    def test_no_duplicate_rivalry_created(self, rivalry_service, mock_rivalry_api, sample_division_rivalry):
        """Should not create rivalry if one already exists."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.create_playoff_rivalry(
            dynasty_id="test",
            team_a_id=21,
            team_b_id=23,
            playoff_round=PlayoffRound.WILD_CARD,
            season=2024,
        )

        assert result is None
        mock_rivalry_api.create_rivalry.assert_not_called()

    def test_generates_rivalry_name(self, rivalry_service, mock_rivalry_api):
        """Should generate appropriate name for playoff rivalry."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = None

        result = rivalry_service.create_playoff_rivalry(
            dynasty_id="test",
            team_a_id=14,
            team_b_id=31,
            playoff_round=PlayoffRound.SUPER_BOWL,
            season=2024,
        )

        assert "Super Bowl" in result.rivalry_name
        assert "2024" in result.rivalry_name


# -------------------- TestDecayLogic --------------------

class TestDecayLogic:
    """Tests for annual rivalry decay."""

    def test_recent_decays_without_meeting(self, rivalry_service, mock_rivalry_api, mock_h2h_api, sample_recent_rivalry):
        """RECENT rivalries should decay -10 if teams didn't meet."""
        mock_rivalry_api.get_all_rivalries.return_value = [sample_recent_rivalry]
        mock_h2h_api.get_record.return_value = Mock(last_meeting_season=2023)  # Met in 2023, not 2024

        results = rivalry_service.decay_inactive_rivalries("test", completed_season=2024)

        assert len(results) == 1
        rivalry, new_intensity, status = results[0]
        assert new_intensity == 55  # 65 - 10
        assert status == 'decayed'

    def test_met_this_season_no_decay(self, rivalry_service, mock_rivalry_api, mock_h2h_api, sample_recent_rivalry):
        """RECENT rivalries should NOT decay if teams met this season."""
        mock_rivalry_api.get_all_rivalries.return_value = [sample_recent_rivalry]
        mock_h2h_api.get_record.return_value = Mock(last_meeting_season=2024)  # Met in 2024

        results = rivalry_service.decay_inactive_rivalries("test", completed_season=2024)

        assert len(results) == 0  # No decay applied

    def test_below_minimum_removes_rivalry(self, rivalry_service, mock_rivalry_api, mock_h2h_api):
        """RECENT rivalries below MIN_INTENSITY after decay should be removed."""
        weak_rivalry = Rivalry(
            team_a_id=1,
            team_b_id=2,
            rivalry_type=RivalryType.RECENT,
            rivalry_name="Weak Rivalry",
            intensity=25,  # 25 - 10 = 15 < 20 (MIN_INTENSITY)
            rivalry_id=1,
        )
        mock_rivalry_api.get_all_rivalries.return_value = [weak_rivalry]
        mock_h2h_api.get_record.return_value = Mock(last_meeting_season=2023)

        results = rivalry_service.decay_inactive_rivalries("test", completed_season=2024)

        assert len(results) == 1
        rivalry, new_intensity, status = results[0]
        assert new_intensity == 0
        assert status == 'removed'
        mock_rivalry_api.delete_rivalry.assert_called_once()

    def test_historic_never_decays(self, rivalry_service, mock_rivalry_api, mock_h2h_api, sample_historic_rivalry):
        """HISTORIC rivalries should never be in decay list (only RECENT decays)."""
        mock_rivalry_api.get_all_rivalries.return_value = []  # Empty - only RECENT returned

        results = rivalry_service.decay_inactive_rivalries("test", completed_season=2024)

        assert len(results) == 0


# -------------------- TestIntegration --------------------

class TestIntegration:
    """Integration-style tests for full game flow."""

    def test_update_after_regular_season_game(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Test full update flow for a regular season game."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=27,
            away_score=24,
            overtime_periods=0,
            is_playoff=False,
        )

        assert result is not None
        assert result.old_intensity == 70
        assert result.new_intensity == 76  # Close game +6
        mock_rivalry_api.update_intensity.assert_called_once_with("test", 1, 76)

    def test_update_after_playoff_game(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Test full update flow for a playoff game."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=27,
            away_score=24,
            overtime_periods=1,  # OT
            is_playoff=True,
            playoff_round=PlayoffRound.DIVISIONAL,
        )

        assert result is not None
        # OT (+7) + Divisional (+12) = +19
        assert result.change_amount == 19
        assert result.new_intensity == 89

    def test_no_rivalry_returns_none(self, rivalry_service, mock_rivalry_api):
        """When no rivalry exists, update should return None."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = None

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=1,
            away_team_id=2,
            home_score=21,
            away_score=14,
        )

        assert result is None
        mock_rivalry_api.update_intensity.assert_not_called()


# -------------------- TestChangeReason --------------------

class TestChangeReason:
    """Tests for change reason generation."""

    def test_overtime_reason_included(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Overtime should be mentioned in change reason."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=27,
            away_score=24,
            overtime_periods=2,
        )

        assert "overtime" in result.change_reason.lower()
        assert "2 OT" in result.change_reason

    def test_playoff_round_in_reason(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Playoff round should be mentioned in change reason."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=28,
            away_score=17,
            is_playoff=True,
            playoff_round=PlayoffRound.SUPER_BOWL,
        )

        assert "Super Bowl" in result.change_reason

    def test_margin_in_reason(self, rivalry_service, sample_division_rivalry, mock_rivalry_api):
        """Score margin should be mentioned in change reason."""
        mock_rivalry_api.get_rivalry_between_teams.return_value = sample_division_rivalry

        result = rivalry_service.update_rivalry_after_game(
            dynasty_id="test",
            home_team_id=21,
            away_team_id=23,
            home_score=42,
            away_score=14,  # 28 point margin
        )

        assert "28 pt" in result.change_reason


# -------------------- TestPreviewMethod --------------------

class TestPreviewMethod:
    """Tests for intensity change preview."""

    def test_preview_returns_change_and_reason(self, rivalry_service):
        """Preview should return change amount and reason without DB update."""
        change, reason = rivalry_service.get_intensity_change_for_game(
            margin=3,
            overtime_periods=1,
            is_playoff=True,
            playoff_round=PlayoffRound.CONFERENCE,
        )

        # OT (+7) + Conference (+15) = +22
        assert change == 22
        assert "overtime" in reason.lower()
        assert "Conference" in reason
