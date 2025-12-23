"""
Social Post Generator Factory - Dispatches to correct generator.

Follows the factory pattern to select the appropriate social post generator
based on the event type.

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

from typing import Dict, Type, Any

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.models.social_event_types import SocialEventType
from .base_generator import BaseSocialPostGenerator
from .game_generator import GameSocialGenerator
from .award_generator import AwardSocialGenerator
from .transaction_generator import TransactionSocialGenerator
from .franchise_tag_generator import FranchiseTagSocialGenerator
from .resigning_generator import ResigningSocialGenerator
from .waiver_generator import WaiverSocialGenerator
from .draft_generator import DraftSocialGenerator
from .hof_generator import HOFSocialGenerator
from .injury_generator import InjurySocialGenerator
from .rumor_generator import RumorSocialGenerator
from .training_camp_generator import TrainingCampSocialGenerator


class SocialPostGeneratorFactory:
    """
    Factory for creating the appropriate social post generator.

    Maps SocialEventType enum to concrete generator classes.
    Provides both factory method and convenience wrapper.

    Example:
        # Create generator
        generator = SocialPostGeneratorFactory.create_generator(
            SocialEventType.GAME_RESULT, db, dynasty_id
        )
        posts_created = generator.generate_and_persist(season, week, event_data)

        # Or use convenience method
        posts_created = SocialPostGeneratorFactory.generate_posts(
            SocialEventType.GAME_RESULT, db, dynasty_id, season, week, event_data
        )
    """

    # Mapping of event types to generator classes
    _GENERATOR_MAP: Dict[SocialEventType, Type[BaseSocialPostGenerator]] = {
        # Game events - use GameSocialGenerator
        SocialEventType.GAME_RESULT: GameSocialGenerator,
        SocialEventType.PLAYOFF_GAME: GameSocialGenerator,  # Same logic as regular games
        SocialEventType.SUPER_BOWL: GameSocialGenerator,    # Same logic with magnitude boost

        # Transaction events - TransactionSocialGenerator handles multiple types
        SocialEventType.TRADE: TransactionSocialGenerator,
        SocialEventType.SIGNING: TransactionSocialGenerator,
        SocialEventType.CUT: TransactionSocialGenerator,

        # Offseason transaction events
        SocialEventType.FRANCHISE_TAG: FranchiseTagSocialGenerator,
        SocialEventType.RESIGNING: ResigningSocialGenerator,
        SocialEventType.WAIVER_CLAIM: WaiverSocialGenerator,
        SocialEventType.DRAFT_PICK: DraftSocialGenerator,

        # Award events
        SocialEventType.AWARD: AwardSocialGenerator,
        SocialEventType.HOF_INDUCTION: HOFSocialGenerator,

        # Other events
        SocialEventType.INJURY: InjurySocialGenerator,
        SocialEventType.RUMOR: RumorSocialGenerator,
        SocialEventType.TRAINING_CAMP: TrainingCampSocialGenerator,
    }

    @classmethod
    def create_generator(
        cls,
        event_type: SocialEventType,
        db: GameCycleDatabase,
        dynasty_id: str
    ) -> BaseSocialPostGenerator:
        """
        Create the appropriate generator for an event type.

        Args:
            event_type: Type of event (enum)
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier

        Returns:
            Concrete generator instance (subclass of BaseSocialPostGenerator)

        Raises:
            ValueError: If no generator exists for the event type
        """
        generator_class = cls._GENERATOR_MAP.get(event_type)

        if not generator_class:
            raise ValueError(
                f"No generator registered for event type: {event_type}. "
                f"Available types: {list(cls._GENERATOR_MAP.keys())}"
            )

        return generator_class(db, dynasty_id)

    @classmethod
    def generate_posts(
        cls,
        event_type: SocialEventType,
        db: GameCycleDatabase,
        dynasty_id: str,
        season: int,
        week: int,
        event_data: Dict[str, Any]
    ) -> int:
        """
        Convenience method: create generator and generate posts in one call.

        Args:
            event_type: Type of event (enum)
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            event_data: Event-specific data (varies by generator)

        Returns:
            Number of posts created

        Raises:
            ValueError: If no generator exists for the event type

        Example:
            >>> posts_count = SocialPostGeneratorFactory.generate_posts(
            ...     event_type=SocialEventType.GAME_RESULT,
            ...     db=db,
            ...     dynasty_id='test_dynasty',
            ...     season=2025,
            ...     week=1,
            ...     event_data={
            ...         'winning_team_id': 1,
            ...         'losing_team_id': 2,
            ...         'winning_score': 28,
            ...         'losing_score': 17,
            ...         'is_upset': False,
            ...         'is_blowout': False
            ...     }
            ... )
            >>> print(f"Created {posts_count} posts")
        """
        generator = cls.create_generator(event_type, db, dynasty_id)
        return generator.generate_and_persist(season, week, event_data)

    @classmethod
    def is_supported(cls, event_type: SocialEventType) -> bool:
        """
        Check if a generator exists for this event type.

        Args:
            event_type: Event type to check

        Returns:
            True if generator exists, False otherwise
        """
        return event_type in cls._GENERATOR_MAP

    @classmethod
    def get_supported_types(cls) -> list[SocialEventType]:
        """
        Get list of all supported event types.

        Returns:
            List of SocialEventType enums with registered generators
        """
        return list(cls._GENERATOR_MAP.keys())
