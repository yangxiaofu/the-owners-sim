"""
Unit tests for rivalry gameplay modifiers.

Part of Milestone 11: Schedule & Rivalries, Tollgate 5.
Tests modifier calculation, head-to-head effects, and game descriptions.
"""

import pytest
from src.game_management.rivalry_modifiers import (
    IntensityLevel,
    RivalryGameModifiers,
    calculate_rivalry_modifiers,
    get_rivalry_game_description,
    NO_RIVALRY_MODIFIERS,
    LEGENDARY_RIVALRY_MODIFIERS,
    DIVISION_RIVALRY_MODIFIERS,
    _calculate_intensity_modifiers,
    _apply_head_to_head_effects,
    _apply_playoff_boost,
)
from src.game_cycle.models.rivalry import Rivalry, RivalryType
from src.game_cycle.models.head_to_head import HeadToHeadRecord


# ============================================================================
# IntensityLevel Tests
# ============================================================================

class TestIntensityLevel:
    """Tests for IntensityLevel enum."""

    def test_legendary_threshold(self):
        """Intensity 90+ should be LEGENDARY."""
        assert IntensityLevel.from_intensity(90) == IntensityLevel.LEGENDARY
        assert IntensityLevel.from_intensity(95) == IntensityLevel.LEGENDARY
        assert IntensityLevel.from_intensity(100) == IntensityLevel.LEGENDARY

    def test_intense_threshold(self):
        """Intensity 70-89 should be INTENSE."""
        assert IntensityLevel.from_intensity(70) == IntensityLevel.INTENSE
        assert IntensityLevel.from_intensity(80) == IntensityLevel.INTENSE
        assert IntensityLevel.from_intensity(89) == IntensityLevel.INTENSE

    def test_moderate_threshold(self):
        """Intensity 50-69 should be MODERATE."""
        assert IntensityLevel.from_intensity(50) == IntensityLevel.MODERATE
        assert IntensityLevel.from_intensity(60) == IntensityLevel.MODERATE
        assert IntensityLevel.from_intensity(69) == IntensityLevel.MODERATE

    def test_mild_threshold(self):
        """Intensity 30-49 should be MILD."""
        assert IntensityLevel.from_intensity(30) == IntensityLevel.MILD
        assert IntensityLevel.from_intensity(40) == IntensityLevel.MILD
        assert IntensityLevel.from_intensity(49) == IntensityLevel.MILD

    def test_minimal_threshold(self):
        """Intensity 1-29 should be MINIMAL."""
        assert IntensityLevel.from_intensity(1) == IntensityLevel.MINIMAL
        assert IntensityLevel.from_intensity(15) == IntensityLevel.MINIMAL
        assert IntensityLevel.from_intensity(29) == IntensityLevel.MINIMAL

    def test_boundary_values(self):
        """Test exact boundary values."""
        # 89 is INTENSE, 90 is LEGENDARY
        assert IntensityLevel.from_intensity(89) == IntensityLevel.INTENSE
        assert IntensityLevel.from_intensity(90) == IntensityLevel.LEGENDARY

        # 69 is MODERATE, 70 is INTENSE
        assert IntensityLevel.from_intensity(69) == IntensityLevel.MODERATE
        assert IntensityLevel.from_intensity(70) == IntensityLevel.INTENSE


# ============================================================================
# RivalryGameModifiers Tests
# ============================================================================

class TestRivalryGameModifiers:
    """Tests for RivalryGameModifiers dataclass."""

    def test_default_values(self):
        """Default modifiers should be neutral (1.0)."""
        mods = RivalryGameModifiers()
        assert mods.home_offensive_boost == 1.0
        assert mods.home_defensive_boost == 1.0
        assert mods.away_offensive_boost == 1.0
        assert mods.away_defensive_boost == 1.0
        assert mods.turnover_variance == 1.0
        assert mods.penalty_rate_modifier == 1.0
        assert mods.crowd_noise_boost == 1.0
        assert mods.intensity_level == IntensityLevel.MINIMAL

    def test_is_rivalry_game_false_for_minimal(self):
        """MINIMAL intensity should not be a rivalry game."""
        mods = RivalryGameModifiers(intensity_level=IntensityLevel.MINIMAL)
        assert mods.is_rivalry_game is False

    def test_is_rivalry_game_true_for_non_minimal(self):
        """Non-MINIMAL intensities should be rivalry games."""
        for level in [IntensityLevel.MILD, IntensityLevel.MODERATE,
                      IntensityLevel.INTENSE, IntensityLevel.LEGENDARY]:
            mods = RivalryGameModifiers(intensity_level=level)
            assert mods.is_rivalry_game is True

    def test_total_home_boost(self):
        """Total home boost should average offensive and defensive."""
        mods = RivalryGameModifiers(
            home_offensive_boost=1.10,
            home_defensive_boost=1.06
        )
        assert mods.total_home_boost == pytest.approx(1.08)

    def test_total_away_boost(self):
        """Total away boost should average offensive and defensive."""
        mods = RivalryGameModifiers(
            away_offensive_boost=1.04,
            away_defensive_boost=1.08
        )
        assert mods.total_away_boost == pytest.approx(1.06)

    def test_to_dict(self):
        """to_dict should include all fields."""
        mods = RivalryGameModifiers(
            home_offensive_boost=1.05,
            intensity_level=IntensityLevel.INTENSE,
            is_revenge_game_home=True,
            home_on_streak=3
        )
        d = mods.to_dict()
        assert d["home_offensive_boost"] == 1.05
        assert d["intensity_level"] == "intense"
        assert d["is_revenge_game_home"] is True
        assert d["home_on_streak"] == 3

    def test_to_dict_serialization(self):
        """to_dict should produce serializable values."""
        import json
        mods = LEGENDARY_RIVALRY_MODIFIERS
        d = mods.to_dict()
        # Should not raise
        json_str = json.dumps(d)
        assert "legendary" in json_str


# ============================================================================
# calculate_rivalry_modifiers Tests
# ============================================================================

class TestCalculateRivalryModifiers:
    """Tests for calculate_rivalry_modifiers function."""

    def test_no_rivalry_returns_defaults(self):
        """No rivalry should return default modifiers."""
        mods = calculate_rivalry_modifiers(
            rivalry=None,
            head_to_head=None,
            home_team_id=21,
            away_team_id=23,
            is_playoff=False
        )
        assert mods.home_offensive_boost == 1.0
        assert mods.turnover_variance == 1.0
        assert mods.intensity_level == IntensityLevel.MINIMAL

    def test_legendary_rivalry_high_modifiers(self):
        """Legendary rivalry should have maximum modifiers."""
        rivalry = Rivalry(
            team_a_id=21,  # Bears
            team_b_id=23,  # Packers
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="The Oldest Rivalry",
            intensity=95
        )
        mods = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=None,
            home_team_id=21,
            away_team_id=23,
            is_playoff=False
        )
        assert mods.intensity_level == IntensityLevel.LEGENDARY
        # 95% intensity = 1.0 + 0.95 * 0.08 = 1.076
        assert mods.home_offensive_boost == pytest.approx(1.076)
        # Turnover: 1.0 + 0.95 * 0.40 = 1.38
        assert mods.turnover_variance == pytest.approx(1.38)
        # Penalty: 1.0 + 0.95 * 0.35 = 1.3325
        assert mods.penalty_rate_modifier == pytest.approx(1.3325)

    def test_moderate_rivalry_moderate_modifiers(self):
        """Moderate rivalry should have medium modifiers."""
        rivalry = Rivalry(
            team_a_id=5,
            team_b_id=8,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="AFC North Battle",
            intensity=55
        )
        mods = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=None,
            home_team_id=5,
            away_team_id=8,
            is_playoff=False
        )
        assert mods.intensity_level == IntensityLevel.MODERATE
        # 55% intensity = 1.0 + 0.55 * 0.08 = 1.044
        assert mods.home_offensive_boost == pytest.approx(1.044)

    def test_playoff_boost_increases_modifiers(self):
        """Playoff games should have boosted modifiers."""
        rivalry = Rivalry(
            team_a_id=17,
            team_b_id=19,
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="NFC East Showdown",
            intensity=70
        )
        regular = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=None,
            home_team_id=17,
            away_team_id=19,
            is_playoff=False
        )
        playoff = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=None,
            home_team_id=17,
            away_team_id=19,
            is_playoff=True
        )
        # Playoff boosts regular by 2%
        assert playoff.home_offensive_boost > regular.home_offensive_boost
        assert playoff.turnover_variance > regular.turnover_variance
        # Playoff = regular * 1.02
        assert playoff.home_offensive_boost == pytest.approx(
            regular.home_offensive_boost * 1.02
        )


# ============================================================================
# Head-to-Head Effects Tests
# ============================================================================

class TestHeadToHeadEffects:
    """Tests for head-to-head modifier effects."""

    @pytest.fixture
    def base_rivalry(self):
        """Basic rivalry for testing."""
        return Rivalry(
            team_a_id=7,  # Browns
            team_b_id=8,  # Steelers
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="AFC North Rivalry",
            intensity=75
        )

    @pytest.fixture
    def h2h_home_lost_last(self):
        """H2H where home team (7) lost last meeting."""
        return HeadToHeadRecord(
            team_a_id=7,
            team_b_id=8,
            team_a_wins=10,
            team_b_wins=15,
            last_meeting_winner=8,  # Away team won
            current_streak_team=8,
            current_streak_count=2
        )

    @pytest.fixture
    def h2h_away_lost_last(self):
        """H2H where away team (8) lost last meeting."""
        return HeadToHeadRecord(
            team_a_id=7,
            team_b_id=8,
            team_a_wins=12,
            team_b_wins=13,
            last_meeting_winner=7,  # Home team won
            current_streak_team=7,
            current_streak_count=1
        )

    def test_revenge_game_home_team(self, base_rivalry, h2h_home_lost_last):
        """Home team gets revenge boost if they lost last meeting."""
        mods = calculate_rivalry_modifiers(
            rivalry=base_rivalry,
            head_to_head=h2h_home_lost_last,
            home_team_id=7,
            away_team_id=8,
            is_playoff=False
        )
        assert mods.is_revenge_game_home is True
        assert mods.is_revenge_game_away is False
        # Base intensity boost + revenge boost
        base_boost = 1.0 + (75 / 100) * 0.08  # 1.06
        revenge_boost = 0.03  # +3% offense
        assert mods.home_offensive_boost == pytest.approx(base_boost + revenge_boost)

    def test_revenge_game_away_team(self, base_rivalry, h2h_away_lost_last):
        """Away team gets revenge boost if they lost last meeting."""
        mods = calculate_rivalry_modifiers(
            rivalry=base_rivalry,
            head_to_head=h2h_away_lost_last,
            home_team_id=7,
            away_team_id=8,
            is_playoff=False
        )
        assert mods.is_revenge_game_home is False
        assert mods.is_revenge_game_away is True

    def test_winning_streak_defense_boost(self, base_rivalry):
        """Team on winning streak gets defensive confidence boost."""
        h2h = HeadToHeadRecord(
            team_a_id=7,
            team_b_id=8,
            team_a_wins=10,
            team_b_wins=8,
            current_streak_team=7,  # Home team on streak
            current_streak_count=4
        )
        mods = calculate_rivalry_modifiers(
            rivalry=base_rivalry,
            head_to_head=h2h,
            home_team_id=7,
            away_team_id=8,
            is_playoff=False
        )
        assert mods.home_on_streak == 4
        # 4-game streak = +4% defense boost (capped at 5%)
        base_boost = 1.0 + (75 / 100) * 0.08  # 1.06
        streak_boost = 0.04  # 1% per win, 4 wins
        assert mods.home_defensive_boost == pytest.approx(base_boost + streak_boost)

    def test_losing_streak_desperation_boost(self, base_rivalry):
        """Team on losing streak gets desperate offense boost."""
        h2h = HeadToHeadRecord(
            team_a_id=7,
            team_b_id=8,
            team_a_wins=5,
            team_b_wins=12,
            current_streak_team=8,  # Away team on 4-game streak
            current_streak_count=4
        )
        mods = calculate_rivalry_modifiers(
            rivalry=base_rivalry,
            head_to_head=h2h,
            home_team_id=7,
            away_team_id=8,
            is_playoff=False
        )
        assert mods.away_on_streak == 4
        # Home team facing 4-game losing streak gets +2% offense
        base_boost = 1.0 + (75 / 100) * 0.08
        desperation_boost = 0.02
        assert mods.home_offensive_boost >= base_boost + desperation_boost

    def test_streak_capped_at_5_percent(self, base_rivalry):
        """Streak defense boost should be capped at 5%."""
        h2h = HeadToHeadRecord(
            team_a_id=7,
            team_b_id=8,
            team_a_wins=20,
            team_b_wins=5,
            current_streak_team=7,  # Home team on huge streak
            current_streak_count=10
        )
        mods = calculate_rivalry_modifiers(
            rivalry=base_rivalry,
            head_to_head=h2h,
            home_team_id=7,
            away_team_id=8,
            is_playoff=False
        )
        base_boost = 1.0 + (75 / 100) * 0.08  # 1.06
        max_streak_boost = 0.05  # capped
        assert mods.home_defensive_boost == pytest.approx(base_boost + max_streak_boost)


# ============================================================================
# Internal Functions Tests
# ============================================================================

class TestInternalFunctions:
    """Tests for internal modifier calculation functions."""

    def test_calculate_intensity_modifiers_zero(self):
        """Zero intensity (not realistic) should give base modifiers."""
        # Note: Real rivalries have intensity 1-100, but test edge case
        mods = _calculate_intensity_modifiers(0, IntensityLevel.MINIMAL)
        assert mods.home_offensive_boost == 1.0
        assert mods.turnover_variance == 1.0

    def test_calculate_intensity_modifiers_max(self):
        """Maximum intensity should give max modifiers."""
        mods = _calculate_intensity_modifiers(100, IntensityLevel.LEGENDARY)
        assert mods.home_offensive_boost == pytest.approx(1.08)
        assert mods.turnover_variance == pytest.approx(1.40)
        assert mods.penalty_rate_modifier == pytest.approx(1.35)
        assert mods.crowd_noise_boost == pytest.approx(1.25)

    def test_apply_playoff_boost(self):
        """Playoff boost should multiply all performance modifiers."""
        base = RivalryGameModifiers(
            home_offensive_boost=1.05,
            home_defensive_boost=1.05,
            away_offensive_boost=1.05,
            away_defensive_boost=1.05,
            turnover_variance=1.20,
            penalty_rate_modifier=1.20
        )
        boosted = _apply_playoff_boost(base)
        assert boosted.home_offensive_boost == pytest.approx(1.05 * 1.02)
        assert boosted.turnover_variance == pytest.approx(1.20 * 1.10)
        assert boosted.penalty_rate_modifier == pytest.approx(1.20 * 1.05)


# ============================================================================
# Game Description Tests
# ============================================================================

class TestGetRivalryGameDescription:
    """Tests for get_rivalry_game_description function."""

    def test_no_rivalry_empty_string(self):
        """Non-rivalry games should return empty description."""
        mods = RivalryGameModifiers()  # default = MINIMAL
        desc = get_rivalry_game_description(mods)
        assert desc == ""

    def test_legendary_rivalry_description(self):
        """Legendary rivalries should have dramatic description."""
        mods = RivalryGameModifiers(intensity_level=IntensityLevel.LEGENDARY)
        desc = get_rivalry_game_description(mods)
        assert "legendary" in desc.lower()
        assert "intensity" in desc.lower()

    def test_intense_rivalry_description(self):
        """Intense rivalries should mention heightened stakes."""
        mods = RivalryGameModifiers(intensity_level=IntensityLevel.INTENSE)
        desc = get_rivalry_game_description(mods)
        assert "intense" in desc.lower()

    def test_revenge_game_home_description(self):
        """Revenge games should mention seeking revenge."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.MODERATE,
            is_revenge_game_home=True
        )
        desc = get_rivalry_game_description(mods)
        assert "Home team" in desc
        assert "revenge" in desc.lower()

    def test_revenge_game_away_description(self):
        """Away team revenge should be mentioned."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.MODERATE,
            is_revenge_game_away=True
        )
        desc = get_rivalry_game_description(mods)
        assert "Away team" in desc
        assert "avenge" in desc.lower() or "defeat" in desc.lower()

    def test_winning_streak_home_description(self):
        """Home team on streak should be mentioned."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.MODERATE,
            home_on_streak=5
        )
        desc = get_rivalry_game_description(mods)
        assert "5-game" in desc
        assert "Home team" in desc

    def test_winning_streak_away_description(self):
        """Away team on streak should be mentioned."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.MODERATE,
            away_on_streak=4
        )
        desc = get_rivalry_game_description(mods)
        assert "4" in desc
        assert "Away team" in desc

    def test_short_streak_not_mentioned(self):
        """Streaks < 3 should not be mentioned."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.MODERATE,
            home_on_streak=2
        )
        desc = get_rivalry_game_description(mods)
        assert "streak" not in desc.lower()


# ============================================================================
# Pre-defined Modifier Sets Tests
# ============================================================================

class TestPredefinedModifiers:
    """Tests for pre-defined modifier constants."""

    def test_no_rivalry_modifiers(self):
        """NO_RIVALRY_MODIFIERS should be all defaults."""
        assert NO_RIVALRY_MODIFIERS.home_offensive_boost == 1.0
        assert NO_RIVALRY_MODIFIERS.turnover_variance == 1.0
        assert NO_RIVALRY_MODIFIERS.is_rivalry_game is False

    def test_legendary_rivalry_modifiers(self):
        """LEGENDARY_RIVALRY_MODIFIERS should have max values."""
        assert LEGENDARY_RIVALRY_MODIFIERS.home_offensive_boost == 1.08
        assert LEGENDARY_RIVALRY_MODIFIERS.turnover_variance == 1.40
        assert LEGENDARY_RIVALRY_MODIFIERS.penalty_rate_modifier == 1.35
        assert LEGENDARY_RIVALRY_MODIFIERS.crowd_noise_boost == 1.25
        assert LEGENDARY_RIVALRY_MODIFIERS.intensity_level == IntensityLevel.LEGENDARY

    def test_division_rivalry_modifiers(self):
        """DIVISION_RIVALRY_MODIFIERS should have moderate values."""
        assert DIVISION_RIVALRY_MODIFIERS.home_offensive_boost == 1.04
        assert DIVISION_RIVALRY_MODIFIERS.turnover_variance == 1.20
        assert DIVISION_RIVALRY_MODIFIERS.intensity_level == IntensityLevel.MODERATE
        assert DIVISION_RIVALRY_MODIFIERS.is_rivalry_game is True


# ============================================================================
# Integration Tests
# ============================================================================

class TestRivalryModifiersIntegration:
    """Integration tests for full modifier calculation flow."""

    def test_bears_packers_legendary_rivalry(self):
        """Test iconic Bears-Packers rivalry calculation."""
        rivalry = Rivalry(
            team_a_id=21,  # Bears
            team_b_id=23,  # Packers
            rivalry_type=RivalryType.HISTORIC,
            rivalry_name="The Oldest Rivalry",
            intensity=95,
            is_protected=True
        )
        h2h = HeadToHeadRecord(
            team_a_id=21,
            team_b_id=23,
            team_a_wins=95,
            team_b_wins=103,
            ties=6,
            last_meeting_winner=23,  # Packers won last
            current_streak_team=23,
            current_streak_count=2
        )
        # Bears at home, seeking revenge
        mods = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=h2h,
            home_team_id=21,  # Bears
            away_team_id=23,  # Packers
            is_playoff=False
        )

        assert mods.intensity_level == IntensityLevel.LEGENDARY
        assert mods.is_rivalry_game is True
        assert mods.is_revenge_game_home is True  # Bears lost last
        assert mods.away_on_streak == 2

        # Bears get revenge boost
        assert mods.home_offensive_boost > 1.05

        # High chaos in legendary rivalry
        assert mods.turnover_variance > 1.30

    def test_playoff_rivalry_amplification(self):
        """Test that playoff rivalry has enhanced effects."""
        rivalry = Rivalry(
            team_a_id=17,  # Cowboys
            team_b_id=19,  # Eagles
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="Battle for NFC East",
            intensity=80
        )
        h2h = HeadToHeadRecord(
            team_a_id=17,
            team_b_id=19,
            team_a_wins=70,
            team_b_wins=55,
            current_streak_team=17,
            current_streak_count=3
        )
        # Playoff game
        mods = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=h2h,
            home_team_id=17,
            away_team_id=19,
            is_playoff=True
        )

        # Should have high intensity effects
        assert mods.intensity_level == IntensityLevel.INTENSE
        # Playoff boost applied
        assert mods.home_offensive_boost > 1.06
        # High turnover variance (base + playoff)
        assert mods.turnover_variance > 1.35

    def test_mild_rivalry_minimal_effects(self):
        """Mild rivalries should have minimal but present effects."""
        rivalry = Rivalry(
            team_a_id=10,  # Colts
            team_b_id=12,  # Titans
            rivalry_type=RivalryType.DIVISION,
            rivalry_name="AFC South Division",
            intensity=35
        )
        mods = calculate_rivalry_modifiers(
            rivalry=rivalry,
            head_to_head=None,
            home_team_id=10,
            away_team_id=12,
            is_playoff=False
        )

        assert mods.intensity_level == IntensityLevel.MILD
        assert mods.is_rivalry_game is True
        # Small but non-zero effects
        assert 1.0 < mods.home_offensive_boost < 1.05
        assert 1.0 < mods.turnover_variance < 1.20

    def test_full_game_description_with_all_factors(self):
        """Test description with revenge + streak."""
        mods = RivalryGameModifiers(
            intensity_level=IntensityLevel.LEGENDARY,
            is_revenge_game_home=True,
            away_on_streak=5
        )
        desc = get_rivalry_game_description(mods)
        assert "legendary" in desc.lower()
        assert "revenge" in desc.lower()
        assert "5" in desc
