"""Tests for Sprint 1 components of player generation system."""

import pytest
import random
import sys
from pathlib import Path

# Add src to path for testing
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

from src.player_generation.core.distributions import AttributeDistribution
from src.player_generation.core.correlations import AttributeCorrelation
from src.player_generation.archetypes.base_archetype import (
    PlayerArchetype, Position, AttributeRange
)
from src.player_generation.core.generation_context import (
    GenerationConfig, GenerationContext
)
from src.player_generation.models.generated_player import (
    GeneratedPlayer, ScoutingReport, PlayerBackground, DevelopmentProfile
)
from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry


class TestAttributeDistribution:
    """Tests for AttributeDistribution class."""

    def test_normal_distribution_respects_bounds(self):
        """Verify normal distribution stays within min/max."""
        for _ in range(1000):
            val = AttributeDistribution.normal(mean=70, std_dev=10, min_val=40, max_val=99)
            assert 40 <= val <= 99

    def test_beta_distribution_shape(self):
        """Verify beta distribution creates expected shape."""
        values = [AttributeDistribution.beta(2, 5, 40, 99) for _ in range(1000)]
        mean_val = sum(values) / len(values)
        assert 50 <= mean_val <= 65  # Alpha=2, Beta=5 skews low

    def test_weighted_choice_distribution(self):
        """Verify weighted choices follow probability distribution."""
        choices = [("A", 0.7), ("B", 0.2), ("C", 0.1)]
        results = [AttributeDistribution.weighted_choice(choices) for _ in range(1000)]
        assert results.count("A") > results.count("B") > results.count("C")


class TestAttributeCorrelation:
    """Tests for AttributeCorrelation class."""

    def test_negative_correlation_size_speed(self):
        """High size should correlate with lower speed."""
        high_size_speeds = []
        low_size_speeds = []

        for _ in range(100):
            high_speed = AttributeCorrelation.apply_correlation(
                base_value=95, correlated_attr="speed", base_attr="size",
                target_mean=70, target_std=10
            )
            low_speed = AttributeCorrelation.apply_correlation(
                base_value=60, correlated_attr="speed", base_attr="size",
                target_mean=70, target_std=10
            )
            high_size_speeds.append(high_speed)
            low_size_speeds.append(low_speed)

        # High size should produce lower speeds on average
        assert sum(high_size_speeds) / 100 < sum(low_size_speeds) / 100

    def test_positive_correlation_strength_size(self):
        """High size should correlate with higher strength."""
        high_size_str = []
        low_size_str = []

        for _ in range(100):
            high_str = AttributeCorrelation.apply_correlation(
                base_value=95, correlated_attr="strength", base_attr="size",
                target_mean=70, target_std=10
            )
            low_str = AttributeCorrelation.apply_correlation(
                base_value=60, correlated_attr="strength", base_attr="size",
                target_mean=70, target_std=10
            )
            high_size_str.append(high_str)
            low_size_str.append(low_str)

        # High size should produce higher strength on average
        assert sum(high_size_str) / 100 > sum(low_size_str) / 100

    def test_get_correlation(self):
        """Test correlation coefficient retrieval."""
        assert AttributeCorrelation.get_correlation("size", "speed") == -0.6
        assert AttributeCorrelation.get_correlation("speed", "size") == -0.6
        assert AttributeCorrelation.get_correlation("unknown", "attr") == 0


class TestPlayerArchetype:
    """Tests for PlayerArchetype class."""

    def test_archetype_creation(self):
        """Verify archetype can be created with valid data."""
        archetype = PlayerArchetype(
            archetype_id="pocket_passer_qb",
            position=Position.QB,
            name="Pocket Passer",
            description="Traditional pocket quarterback",
            physical_attributes={
                "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5),
                "strength": AttributeRange(min=70, max=85, mean=77, std_dev=5)
            },
            mental_attributes={
                "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
            },
            position_attributes={
                "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5)
            },
            overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
            frequency=0.3,
            peak_age_range=(28, 32),
            development_curve="normal"
        )

        is_valid, error = archetype.validate()
        assert is_valid
        assert error is None

    def test_archetype_validation_catches_invalid_ranges(self):
        """Verify validation catches invalid attribute ranges."""
        archetype = PlayerArchetype(
            archetype_id="test",
            position=Position.QB,
            name="Test",
            description="Test archetype",
            physical_attributes={
                "speed": AttributeRange(min=100, max=110, mean=105, std_dev=5)  # Invalid!
            },
            mental_attributes={},
            position_attributes={},
            overall_range=AttributeRange(min=70, max=90, mean=80, std_dev=5),
            frequency=0.5,
            peak_age_range=(25, 30),
            development_curve="normal"
        )

        is_valid, error = archetype.validate()
        assert not is_valid
        assert "Invalid range" in error

    def test_get_attribute_names(self):
        """Test attribute name retrieval."""
        archetype = PlayerArchetype(
            archetype_id="test",
            position=Position.QB,
            name="Test",
            description="Test",
            physical_attributes={"speed": AttributeRange(65, 80, 72, 5)},
            mental_attributes={"awareness": AttributeRange(75, 95, 85, 5)},
            position_attributes={"accuracy": AttributeRange(80, 99, 90, 5)},
            overall_range=AttributeRange(70, 95, 82, 8),
            frequency=1.0,
            peak_age_range=(28, 32),
            development_curve="normal"
        )

        attr_names = archetype.get_attribute_names()
        assert "speed" in attr_names
        assert "awareness" in attr_names
        assert "accuracy" in attr_names
        assert len(attr_names) == 3


class TestGenerationConfig:
    """Tests for GenerationConfig class."""

    def test_draft_context_overall_ranges(self):
        """Verify draft rounds produce appropriate overall ranges."""
        configs = [
            (1, 75, 95),
            (3, 68, 85),
            (7, 55, 72)
        ]

        for round_num, expected_min, expected_max in configs:
            config = GenerationConfig(
                context=GenerationContext.NFL_DRAFT,
                draft_round=round_num
            )
            min_val, max_val = config.get_overall_range()
            assert min_val == expected_min
            assert max_val == expected_max

    def test_udfa_context_caps_overall(self):
        """Verify UDFA context limits overall ceiling."""
        config = GenerationConfig(context=GenerationContext.UDFA)
        min_val, max_val = config.get_overall_range()
        assert max_val <= 68  # UDFA ceiling

    def test_scouting_error_margins(self):
        """Verify scouting confidence affects error margin."""
        high_conf = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            scouting_confidence="high"
        )
        low_conf = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            scouting_confidence="low"
        )

        assert high_conf.get_scouting_error_margin() < low_conf.get_scouting_error_margin()


class TestGeneratedPlayer:
    """Tests for GeneratedPlayer and related classes."""

    def test_generated_player_creation(self):
        """Verify GeneratedPlayer can be created with complete data."""
        player = GeneratedPlayer(
            player_id="DRAFT_2025_001",
            name="John Smith",
            position="QB",
            age=22,
            jersey_number=12,
            true_ratings={"accuracy": 85, "arm_strength": 88},
            scouted_ratings={"accuracy": 82, "arm_strength": 90},
            true_overall=86,
            scouted_overall=85,
            archetype_id="pocket_passer_qb",
            generation_context="nfl_draft",
            dynasty_id="test_dynasty",
            draft_round=1,
            draft_pick=15
        )

        assert player.player_id == "DRAFT_2025_001"
        assert player.get_display_overall() == 85  # Shows scouted

    def test_development_profile_phase_detection(self):
        """Verify development profile correctly identifies phases."""
        # Growth phase
        growth = DevelopmentProfile(
            current_age=23, peak_age_min=27, peak_age_max=31,
            development_curve="normal", growth_rate=2.0, decline_rate=1.5
        )
        assert growth.is_in_growth_phase()
        assert not growth.is_in_peak_phase()

        # Peak phase
        peak = DevelopmentProfile(
            current_age=29, peak_age_min=27, peak_age_max=31,
            development_curve="normal", growth_rate=2.0, decline_rate=1.5
        )
        assert peak.is_in_peak_phase()

        # Decline phase
        decline = DevelopmentProfile(
            current_age=33, peak_age_min=27, peak_age_max=31,
            development_curve="normal", growth_rate=2.0, decline_rate=1.5
        )
        assert decline.is_in_decline_phase()

    def test_player_to_dict_conversion(self):
        """Verify conversion to Player class format."""
        player = GeneratedPlayer(
            player_id="TEST_001",
            name="Test Player",
            position="WR",
            age=24,
            jersey_number=80,
            true_ratings={"speed": 90, "catching": 85}
        )

        player_dict = player.to_player_dict()
        assert player_dict["name"] == "Test Player"
        assert player_dict["primary_position"] == "WR"
        assert player_dict["ratings"]["speed"] == 90

    def test_scouting_report_grade_conversion(self):
        """Test scouting grade from overall rating."""
        assert ScoutingReport.get_grade_from_overall(92) == "A+"
        assert ScoutingReport.get_grade_from_overall(87) == "A"
        assert ScoutingReport.get_grade_from_overall(82) == "A-"
        assert ScoutingReport.get_grade_from_overall(77) == "B+"
        assert ScoutingReport.get_grade_from_overall(72) == "B"
        assert ScoutingReport.get_grade_from_overall(67) == "B-"
        assert ScoutingReport.get_grade_from_overall(62) == "C+"
        assert ScoutingReport.get_grade_from_overall(55) == "C"


class TestArchetypeRegistry:
    """Tests for ArchetypeRegistry class."""

    def test_registry_initialization(self):
        """Verify registry initializes correctly."""
        registry = ArchetypeRegistry()
        assert registry is not None
        assert isinstance(registry.archetypes, dict)

    def test_get_archetype_by_id(self):
        """Test retrieving archetype by ID."""
        registry = ArchetypeRegistry()
        # Registry might be empty if no config files exist
        assert registry.get_archetype("nonexistent") is None

    def test_get_archetypes_by_position(self):
        """Test position filtering."""
        registry = ArchetypeRegistry()
        qb_archetypes = registry.get_archetypes_by_position("QB")
        assert isinstance(qb_archetypes, list)

    def test_list_all_archetypes(self):
        """Test listing all archetype IDs."""
        registry = ArchetypeRegistry()
        all_ids = registry.list_all_archetypes()
        assert isinstance(all_ids, list)

    def test_get_archetype_count(self):
        """Test archetype count."""
        registry = ArchetypeRegistry()
        count = registry.get_archetype_count()
        assert isinstance(count, int)
        assert count >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])