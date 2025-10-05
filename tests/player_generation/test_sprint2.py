"""Tests for Sprint 2 components of player generation system."""

import pytest
import sys
from pathlib import Path

# Add src to path for testing
src_path = str(Path(__file__).parent.parent.parent / "src")
sys.path.insert(0, src_path)

# Import after path setup
from src.player_generation.generators.attribute_generator import AttributeGenerator
from src.player_generation.generators.name_generator import NameGenerator
from src.player_generation.generators.player_generator import PlayerGenerator
from src.player_generation.generators.draft_class_generator import DraftClassGenerator
from src.player_generation.archetypes.base_archetype import (
    PlayerArchetype, Position, AttributeRange
)
from src.player_generation.core.generation_context import (
    GenerationConfig, GenerationContext
)


class TestAttributeGenerator:
    """Tests for AttributeGenerator class."""

    def test_attribute_generation_respects_ranges(self):
        """Verify generated attributes fall within archetype ranges."""
        archetype = PlayerArchetype(
            archetype_id="test",
            position=Position.QB,
            name="Test",
            description="Test archetype",
            physical_attributes={
                "speed": AttributeRange(min=65, max=80, mean=72, std_dev=5)
            },
            mental_attributes={
                "awareness": AttributeRange(min=75, max=95, mean=85, std_dev=5)
            },
            position_attributes={
                "accuracy": AttributeRange(min=80, max=99, mean=90, std_dev=5)
            },
            overall_range=AttributeRange(min=70, max=95, mean=82, std_dev=8),
            frequency=1.0,
            peak_age_range=(28, 32),
            development_curve="normal"
        )

        # Generate 100 players to test distribution
        for _ in range(100):
            attrs = AttributeGenerator.generate_attributes(archetype)
            assert 65 <= attrs["speed"] <= 80
            assert 75 <= attrs["awareness"] <= 95
            assert 80 <= attrs["accuracy"] <= 99

    def test_calculate_overall_qb(self):
        """Test overall calculation for QB position."""
        attrs = {
            "accuracy": 90,
            "arm_strength": 85,
            "awareness": 80,
            "speed": 70,
            "agility": 65,
            "strength": 75
        }

        overall = AttributeGenerator.calculate_overall(attrs, "QB")
        # Overall should be weighted heavily toward accuracy, arm_strength, awareness
        assert 75 <= overall <= 90


class TestNameGenerator:
    """Tests for NameGenerator class."""

    def test_name_generation(self):
        """Verify name generation produces valid names."""
        name = NameGenerator.generate_name()
        assert " " in name  # Should have space between first and last
        parts = name.split()
        assert len(parts) == 2
        assert parts[0] in NameGenerator.FIRST_NAMES
        assert parts[1] in NameGenerator.LAST_NAMES


class TestPlayerGenerator:
    """Tests for PlayerGenerator class."""

    def test_player_generation_with_archetype(self):
        """Verify player generation with specified archetype."""
        archetype = PlayerArchetype(
            archetype_id="test_qb",
            position=Position.QB,
            name="Test QB",
            description="Test",
            physical_attributes={
                "speed": AttributeRange(70, 85, 77, 5)
            },
            mental_attributes={
                "awareness": AttributeRange(80, 95, 87, 5)
            },
            position_attributes={
                "accuracy": AttributeRange(85, 99, 92, 4)
            },
            overall_range=AttributeRange(75, 92, 83, 6),
            frequency=1.0,
            peak_age_range=(28, 32),
            development_curve="normal"
        )

        config = GenerationConfig(
            context=GenerationContext.NFL_DRAFT,
            draft_round=1,
            draft_pick=5,
            draft_year=2025
        )

        generator = PlayerGenerator()
        player = generator.generate_player(config, archetype)

        assert player is not None
        assert player.position == "QB"
        assert player.archetype_id == "test_qb"
        assert player.draft_round == 1
        assert player.draft_pick == 5
        assert player.player_id == "DRAFT_2025_005"


class TestDraftClassGenerator:
    """Tests for DraftClassGenerator class."""

    @pytest.fixture
    def mock_registry(self):
        """Create mock archetype registry with sample archetypes."""
        from src.player_generation.archetypes.archetype_registry import ArchetypeRegistry

        registry = ArchetypeRegistry()

        # Create mock archetypes for all positions used in draft
        positions = ["QB", "RB", "WR", "TE", "OT", "OG", "C", "EDGE", "DT", "LB", "CB", "S"]

        for pos in positions:
            archetype = PlayerArchetype(
                archetype_id=f"test_{pos.lower()}",
                position=Position[pos],
                name=f"Test {pos}",
                description=f"Test archetype for {pos}",
                physical_attributes={
                    "speed": AttributeRange(min=65, max=90, mean=77, std_dev=8),
                    "strength": AttributeRange(min=60, max=95, mean=77, std_dev=10)
                },
                mental_attributes={
                    "awareness": AttributeRange(min=70, max=90, mean=80, std_dev=6)
                },
                position_attributes={
                    "technique": AttributeRange(min=65, max=95, mean=80, std_dev=8)
                },
                overall_range=AttributeRange(min=60, max=95, mean=77, std_dev=10),
                frequency=1.0,
                peak_age_range=(25, 30),
                development_curve="normal"
            )
            registry.archetypes[archetype.archetype_id] = archetype

        return registry

    def test_draft_class_size(self, mock_registry):
        """Verify draft class has correct number of players."""
        generator = PlayerGenerator(registry=mock_registry)
        class_gen = DraftClassGenerator(generator)

        draft_class = class_gen.generate_draft_class(year=2025)

        assert len(draft_class) == 224  # 7 rounds * 32 picks

    def test_round_positions_count(self):
        """Test that round position generation produces correct count."""
        generator = PlayerGenerator()
        class_gen = DraftClassGenerator(generator)

        for round_num in range(1, 8):
            positions = class_gen._get_round_positions(round_num)
            assert len(positions) == 32


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
