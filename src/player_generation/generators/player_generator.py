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
from .background_generator import BackgroundGenerator


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

        # Calculate potential (Tollgate 3: Individual Player Potential)
        # Pass draft_round for sleeper system (late-round diamonds in the rough)
        potential = self._calculate_potential(true_overall, archetype, age, config.draft_round)

        # Store potential in true_ratings for database persistence
        true_ratings['potential'] = potential

        # Generate background (college, hometown)
        background_gen = BackgroundGenerator()
        background = background_gen.generate_background(config)

        # Create player
        player = GeneratedPlayer(
            player_id=player_id,
            name=name,
            position=archetype.position.value,
            age=age,
            true_ratings=true_ratings,
            true_overall=true_overall,
            potential=potential,
            archetype_id=archetype.archetype_id,
            generation_context=config.context.value,
            draft_round=config.draft_round,
            draft_pick=config.draft_pick,
            background=background
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

    def _calculate_potential(
        self,
        true_overall: int,
        archetype: PlayerArchetype,
        age: int,
        draft_round: Optional[int] = None
    ) -> int:
        """
        Calculate player potential based on archetype, age, and draft position.

        Potential represents the maximum achievable overall rating.
        - Minimum: current overall (can't have lower potential than current)
        - Maximum: 99
        - Young players get more headroom than veterans
        - Late-round picks have a small chance to be "sleepers" with high potential

        Sleeper System (creates "diamond in the rough" prospects):
        - Rounds 4-5: 8% chance of 85-92 potential ("Dak Prescott" type)
        - Rounds 6-7: 5% chance of 88-95 potential ("Tom Brady" type)
        - UDFA: 3% chance of 85-90 potential ("Antonio Brown" type)

        Args:
            true_overall: Player's current true overall rating
            archetype: Player's archetype (for ceiling reference)
            age: Player's age
            draft_round: Draft round (1-7) or None for non-draft players

        Returns:
            Potential rating (60-99)
        """
        # Get archetype ceiling for reference
        archetype_max = 95
        if archetype.overall_range:
            archetype_max = archetype.overall_range.max

        # Age factor: younger players have more growth room
        peak_start = 27  # Default peak start
        if archetype.peak_age_range:
            peak_start = archetype.peak_age_range[0]

        if age >= peak_start:
            # At/past peak - potential is close to current
            random_bonus = random.randint(0, 3)
        else:
            # Pre-peak - more growth potential
            years_to_peak = peak_start - age
            max_bonus = 8 + min(years_to_peak, 5)
            random_bonus = random.randint(3, max_bonus)

        potential = min(99, true_overall + random_bonus)

        # Ensure potential is at least archetype_max - 10 for viable prospects
        min_potential = min(99, archetype_max - 10)
        potential = max(potential, min_potential)

        # Never below current overall
        potential = max(potential, true_overall)

        # Sleeper system: Late-round picks have a chance for high potential
        # These are the "diamonds in the rough" - low overall but high ceiling
        if draft_round is not None and draft_round >= 4:
            sleeper_roll = random.random()
            if draft_round in [4, 5] and sleeper_roll < 0.08:  # 8% chance
                # Mid-late round sleeper (Dak Prescott, Russell Wilson type)
                potential = max(potential, random.randint(85, 92))
            elif draft_round in [6, 7] and sleeper_roll < 0.05:  # 5% chance
                # Deep sleeper (Tom Brady, Antonio Brown type)
                potential = max(potential, random.randint(88, 95))

        return potential