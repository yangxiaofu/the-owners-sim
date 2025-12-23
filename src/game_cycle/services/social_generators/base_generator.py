"""
Base Social Post Generator - Abstract class for all social generators.

Pattern: Strategy pattern (similar to headline_generators/base_generator.py)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.database.social_posts_api import SocialPostsAPI
from game_cycle.services.post_template_loader import PostTemplateLoader
from game_cycle.models.social_event_types import SocialEventType
from game_cycle.services.team_context_builder import TeamContextBuilder, TeamContext


logger = logging.getLogger(__name__)


@dataclass
class GeneratedSocialPost:
    """
    Container for a generated post with all metadata.

    This is returned by generators before persistence.
    """
    personality_id: int
    post_text: str
    sentiment: float
    likes: int
    retweets: int
    event_type: SocialEventType
    event_metadata: Dict[str, Any]


class BaseSocialPostGenerator(ABC):
    """
    Abstract base class for social post generators.

    Subclasses implement _generate_posts() for specific event types.
    Base class handles:
    - Personality selection (80/20 recurring/random)
    - Template loading and filling
    - Engagement calculation
    - Database persistence

    Example subclass:
        class GameSocialGenerator(BaseSocialPostGenerator):
            def _generate_posts(self, season, week, event_data):
                # Generate posts for game results
                return [GeneratedSocialPost(...), ...]
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize the base generator.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier
        """
        self.db = db
        self.dynasty_id = dynasty_id
        self.personality_api = SocialPersonalityAPI(db)
        self.posts_api = SocialPostsAPI(db)
        self.template_loader = PostTemplateLoader()

        # Cache for team contexts (per season/week/team)
        # Key: (team_id, season, week), Value: TeamContext
        # Cleared at start of each generate_and_persist() call
        self._team_context_cache: Dict[Tuple[int, int, int], TeamContext] = {}

    @abstractmethod
    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for this event type.

        Subclasses implement event-specific logic here.

        Args:
            season: Season year
            week: Week number
            event_data: Event-specific data (game_id, player_id, etc.)

        Returns:
            List of GeneratedSocialPost objects
        """
        pass

    def generate_and_persist(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> int:
        """
        Generate posts and persist them to the database.

        This is the main entry point called by handlers.

        Args:
            season: Season year
            week: Week number
            event_data: Event-specific data

        Returns:
            Number of posts created
        """
        # Clear team context cache for fresh event
        self._team_context_cache.clear()

        posts = self._generate_posts(season, week, event_data)

        for post in posts:
            self.posts_api.create_post(
                dynasty_id=self.dynasty_id,
                personality_id=post.personality_id,
                season=season,
                week=week,
                post_text=post.post_text,
                event_type=post.event_type,  # Enum (API handles conversion)
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        return len(posts)

    def _get_or_build_team_context(
        self,
        team_id: Optional[int],
        season: Optional[int],
        week: Optional[int]
    ) -> Optional[TeamContext]:
        """
        Get team context from cache or build it.

        This method reduces database queries by caching TeamContext
        for the duration of a single event. Since multiple posts are
        generated for the same team in the same event, caching prevents
        redundant queries.

        Performance: Reduces ~6 queries per post to ~6 queries per team per event.

        Args:
            team_id: Team ID to get context for
            season: Season year
            week: Week number

        Returns:
            TeamContext if successful, None otherwise
        """
        if team_id is None or season is None or week is None:
            return None

        cache_key = (team_id, season, week)

        # Return cached if exists
        if cache_key in self._team_context_cache:
            return self._team_context_cache[cache_key]

        # Build and cache
        try:
            context_builder = TeamContextBuilder(self.db)
            team_context = context_builder.build_context(
                dynasty_id=self.dynasty_id,
                team_id=team_id,
                season=season,
                week=week
            )
            self._team_context_cache[cache_key] = team_context
            return team_context
        except Exception as e:
            logger.warning(f"Failed to build team context for team {team_id}: {e}")
            return None

    def _generate_single_post(
        self,
        personality: Any,  # SocialPersonality object
        event_type: SocialEventType,
        event_outcome: str,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any],
        is_random_fan: bool = False
    ) -> GeneratedSocialPost:
        """
        Generate a single social media post.

        This method handles the complete post generation pipeline:
        1. Build team context for template filtering (with caching)
        2. Select appropriate template based on archetype and context
        3. Fill template with event variables
        4. Calculate sentiment and engagement metrics
        5. Return structured post data

        Args:
            personality: SocialPersonality object
            event_type: Event type enum (GAME_RESULT, TRADE, etc.)
            event_outcome: Event outcome ('WIN', 'LOSS', etc.)
            magnitude: Event magnitude (0-100)
            variables: Template variables for filling
            event_metadata: Event metadata (season, week, etc.)
            is_random_fan: True if simulating a random one-off fan

        Returns:
            GeneratedSocialPost object ready for persistence
        """
        # Build team context for filtering (uses cache if available)
        team_context = self._get_or_build_team_context(
            team_id=personality.team_id if hasattr(personality, 'team_id') else None,
            season=event_metadata.get('season', variables.get('season')),
            week=event_metadata.get('week', variables.get('week'))
        )

        # Get template (convert enum to string for template loader)
        template = self.template_loader.get_template(
            event_type=event_type.value,  # Template loader expects string
            archetype=personality.archetype,
            personality_id=personality.id,
            event_outcome=event_outcome,
            team_context=team_context
        )

        # Fill template with variables
        post_text = self.template_loader.fill_template(template, variables)

        # Calculate sentiment
        sentiment = self.template_loader.calculate_sentiment(
            archetype=personality.archetype,
            event_outcome=event_outcome,
            event_magnitude=magnitude
        )

        # Calculate engagement (likes and retweets)
        likes, retweets = self._calculate_engagement(
            magnitude=magnitude,
            sentiment=sentiment
        )

        # Return structured post
        return GeneratedSocialPost(
            personality_id=personality.id,
            post_text=post_text,
            sentiment=sentiment,
            likes=likes,
            retweets=retweets,
            event_type=event_type,  # Store as enum
            event_metadata=event_metadata
        )

    def _generate_team_posts(
        self,
        team_id: int,
        event_type: SocialEventType,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any],
        personality_type: str = 'FAN',
        archetype_filter: Optional[List[str]] = None
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts from team-affiliated personalities.

        This method handles post generation for a specific team:
        1. Get personalities for the team (fans, media, etc.)
        2. Filter by posting frequency based on event outcome
        3. Apply archetype filter if provided
        4. Generate posts using _generate_single_post()

        Args:
            team_id: Team ID to get personalities for
            event_type: Type of event being posted about
            event_outcome: Event outcome ('WIN', 'LOSS', etc.)
            post_count: Target number of posts to generate
            magnitude: Event magnitude (0-100)
            variables: Template variables for filling
            event_metadata: Event metadata (season, week, etc.)
            personality_type: Type of personality ('FAN', 'MEDIA', etc.)
            archetype_filter: Optional list of archetypes to include

        Returns:
            List of GeneratedSocialPost objects
        """
        import random

        # Get personalities for this team
        personalities = self.personality_api.get_personalities_by_team(
            dynasty_id=self.dynasty_id,
            team_id=team_id,
            personality_type=personality_type
        )

        if not personalities:
            logger.debug(f"No {personality_type} personalities found for team {team_id}")
            return []

        # Apply archetype filter if provided
        if archetype_filter:
            personalities = [p for p in personalities if p.archetype in archetype_filter]
            if not personalities:
                logger.debug(f"No personalities matching archetypes {archetype_filter} for team {team_id}")
                return []

        # Filter by posting frequency based on outcome
        eligible = self._filter_by_posting_frequency(personalities, event_outcome)

        if not eligible:
            logger.debug(f"No eligible personalities for {event_outcome} outcome on team {team_id}")
            return []

        posts = []

        # 80/20 recurring/random mix
        recurring_count = int(post_count * 0.8)
        random_count = post_count - recurring_count

        # Select recurring personalities
        selected_recurring = random.sample(eligible, min(recurring_count, len(eligible)))

        for personality in selected_recurring:
            post = self._generate_single_post(
                personality=personality,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.append(post)

        # Generate random one-off posts (simulate bandwagon/casual fans)
        for _ in range(random_count):
            random_personality = random.choice(eligible)
            post = self._generate_single_post(
                personality=random_personality,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata,
                is_random_fan=True
            )
            posts.append(post)

        return posts

    def _filter_by_posting_frequency(
        self,
        personalities: List[Any],
        event_outcome: str
    ) -> List[Any]:
        """
        Filter personalities by posting frequency for this event.

        Different personalities post at different frequencies:
        - ALL_EVENTS: Post on everything
        - WIN_ONLY: Only post on wins
        - LOSS_ONLY: Only post on losses
        - EMOTIONAL_MOMENTS: Post on wins AND losses (emotional either way)
        - UPSET_ONLY: Only post on upsets (requires upset flag)

        Args:
            personalities: List of SocialPersonality objects
            event_outcome: Event outcome ('WIN', 'LOSS', etc.)

        Returns:
            Filtered list of personalities who would post for this outcome
        """
        eligible = []

        for p in personalities:
            if p.posting_frequency == 'ALL_EVENTS':
                eligible.append(p)
            elif p.posting_frequency == 'WIN_ONLY' and event_outcome == 'WIN':
                eligible.append(p)
            elif p.posting_frequency == 'LOSS_ONLY' and event_outcome == 'LOSS':
                eligible.append(p)
            elif p.posting_frequency == 'EMOTIONAL_MOMENTS':
                # Hot heads post on both wins and losses (emotional either way)
                if event_outcome in ['WIN', 'LOSS']:
                    eligible.append(p)
            elif p.posting_frequency == 'UPSET_ONLY':
                # Only post on upsets (would need upset flag, skip for now)
                pass

        return eligible if eligible else personalities  # Fallback to all if none match

    # ==========================================
    # Shared Helper Methods
    # ==========================================
    # These are copied from the current SocialPostGenerator
    # and will be used by subclasses

    def _select_team_personalities(
        self, team_id: int, event_outcome: str, count: int
    ) -> List:
        """
        Select team personalities for posting (80/20 recurring/random).

        Args:
            team_id: Team ID
            event_outcome: 'WIN' or 'LOSS' (for frequency filtering)
            count: Number of personalities to select

        Returns:
            List of SocialPersonality objects
        """
        # Get all personalities for this team
        personalities = self.personality_api.get_personalities_by_team(
            dynasty_id=self.dynasty_id,
            team_id=team_id
        )

        # Filter by posting frequency based on outcome
        if event_outcome == 'WIN':
            # On wins: ALL_EVENTS, WIN_ONLY, EMOTIONAL_MOMENTS
            eligible = [
                p for p in personalities
                if p.posting_frequency in ('ALL_EVENTS', 'WIN_ONLY', 'EMOTIONAL_MOMENTS')
            ]
        elif event_outcome == 'LOSS':
            # On losses: ALL_EVENTS, LOSS_ONLY, EMOTIONAL_MOMENTS
            eligible = [
                p for p in personalities
                if p.posting_frequency in ('ALL_EVENTS', 'LOSS_ONLY', 'EMOTIONAL_MOMENTS')
            ]
        else:
            # Neutral events: ALL_EVENTS
            eligible = [p for p in personalities if p.posting_frequency == 'ALL_EVENTS']

        if not eligible:
            return []

        # Select personalities (80% recurring, 20% random)
        # For simplicity, use round-robin for now
        import random
        selected = random.sample(eligible, min(count, len(eligible)))
        return selected  # Return full SocialPersonality objects, not just IDs

    def _calculate_engagement(self, magnitude: int, sentiment: float) -> tuple[int, int]:
        """
        Calculate likes and retweets based on magnitude and sentiment.

        Args:
            magnitude: Event magnitude (0-100, e.g., 50=normal, 80=blowout, 100=super bowl)
            sentiment: Post sentiment (-1.0 to 1.0)

        Returns:
            Tuple of (likes, retweets)
        """
        import random

        # Base engagement from magnitude
        base_likes = int(magnitude * 10 * random.uniform(0.5, 1.5))
        base_retweets = int(magnitude * 5 * random.uniform(0.5, 1.5))

        # Boost engagement for extreme sentiment (positive or negative)
        sentiment_multiplier = 1.0 + abs(sentiment) * 0.5

        likes = int(base_likes * sentiment_multiplier)
        retweets = int(base_retweets * sentiment_multiplier)

        # Ensure non-negative
        return max(0, likes), max(0, retweets)

    def _get_team_name(self, team_id: int) -> str:
        """
        Get team abbreviation or fallback name.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team abbreviation (e.g., "DET", "KC") or fallback "Team X"
        """
        from team_management.teams.team_loader import get_team_by_id

        try:
            team = get_team_by_id(team_id)
            return team.abbreviation if team else f"Team {team_id}"
        except Exception:
            return f"Team {team_id}"

    def _calculate_post_count(
        self,
        magnitude: int,
        base_range: Tuple[int, int] = (2, 4)
    ) -> int:
        """
        Calculate number of posts based on event magnitude.

        This centralizes post count logic to ensure consistency across
        all generators. Higher magnitude events generate more social buzz.

        Args:
            magnitude: Event magnitude (0-100)
            base_range: Base (min, max) post count for normal magnitude events

        Returns:
            Post count (typically 1-10)
        """
        import random

        if magnitude >= 90:
            return random.randint(8, 10)  # Major events (Super Bowl, MVP)
        elif magnitude >= 80:
            return random.randint(6, 8)   # Significant events (playoff games, major awards)
        elif magnitude >= 60:
            return random.randint(4, 6)   # Notable events (upsets, Pro Bowl selections)
        else:
            return random.randint(base_range[0], base_range[1])  # Normal events
