"""Core player generation engine."""

import random
import uuid
from typing import Optional
from ..models.generated_player import GeneratedPlayer
from ..archetypes.base_archetype import PlayerArchetype
from ..archetypes.archetype_registry import ArchetypeRegistry
from ..core.generation_context import GenerationConfig, GenerationContext
from .attribute_generator import AttributeGenerator
from .name_generator import NameGenerator


class PlayerGenerator:
    """Core player generation engine."""

    def __init__(self, registry: Optional[ArchetypeRegistry] = None):
        """Initialize player generator.

        Args:
            registry: Archetype registry (creates new one if not provided)
        """
        self.registry = registry or ArchetypeRegistry()

    def generate_player(
        self,
        config: GenerationConfig,
        archetype: Optional[PlayerArchetype] = None
    ) -> GeneratedPlayer:
        """Generate a single player.

        Args:
            config: Generation configuration
            archetype: Optional specific archetype (selects randomly if not provided)

        Returns:
            Generated player with all attributes

        Raises:
            ValueError: If archetype cannot be determined
        """
        # Select archetype if not provided
        if archetype is None:
            if config.archetype_id:
                archetype = self.registry.get_archetype(config.archetype_id)
            elif config.position:
                archetype = self.registry.select_random_archetype(config.position)

            if archetype is None:
                raise ValueError("Could not determine archetype for generation")

        # Generate attributes
        true_ratings = AttributeGenerator.generate_attributes(archetype)

        # Calculate overall
        true_overall = AttributeGenerator.calculate_overall(
            true_ratings,
            archetype.position.value
        )

        # Apply overall constraints from config
        min_overall, max_overall = config.get_overall_range()
        if true_overall < min_overall or true_overall > max_overall:
            # Scale attributes to fit range
            scale_factor = (min_overall + max_overall) / 2 / true_overall
            true_ratings = {k: int(v * scale_factor) for k, v in true_ratings.items()}
            true_overall = AttributeGenerator.calculate_overall(
                true_ratings,
                archetype.position.value
            )

        # Generate name
        name = NameGenerator.generate_name()

        # Generate player ID
        player_id = self._generate_player_id(config)

        # Determine age
        age = config.age or self._get_default_age(config.context)

        # Create player
        player = GeneratedPlayer(
            player_id=player_id,
            name=name,
            position=archetype.position.value,
            age=age,
            true_ratings=true_ratings,
            true_overall=true_overall,
            archetype_id=archetype.archetype_id,
            generation_context=config.context.value,
            draft_round=config.draft_round,
            draft_pick=config.draft_pick
        )

        return player

    def _generate_player_id(self, config: GenerationConfig) -> str:
        """Generate unique player ID.

        Args:
            config: Generation configuration

        Returns:
            Unique player ID string
        """
        if config.context == GenerationContext.NFL_DRAFT:
            year = config.draft_year or 2025
            pick = config.draft_pick or 0
            return f"DRAFT_{year}_{pick:03d}"
        elif config.context == GenerationContext.UDFA:
            return f"UDFA_{uuid.uuid4().hex[:8]}"
        else:
            return f"GEN_{uuid.uuid4().hex[:8]}"

    def _get_default_age(self, context: GenerationContext) -> int:
        """Get default age based on context.

        Args:
            context: Generation context

        Returns:
            Default age for context
        """
        if context == GenerationContext.NFL_DRAFT:
            return random.randint(21, 23)
        elif context == GenerationContext.UDFA:
            return random.randint(22, 24)
        else:
            return random.randint(23, 26)