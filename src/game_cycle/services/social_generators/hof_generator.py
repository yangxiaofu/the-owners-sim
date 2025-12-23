"""
Hall of Fame Social Post Generator.

Generates posts for Hall of Fame inductions:
- HOF inductions (5-8 posts, magnitude 100)
- HOF finalists (2-3 posts)
- HOF snubs (3-5 posts, controversial)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class HOFSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for Hall of Fame announcements.

    HOF inductions are prestigious events generating high engagement.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a Hall of Fame induction.

        Args:
            season: Season year
            week: Week number (typically 23 for HOF announcements)
            event_data: Dict containing:
                - player_name: Player inducted
                - team_id: Primary team (optional, most associated team)
                - position: Player position
                - career_stats: Career achievements (optional)
                - is_first_ballot: True if first-ballot HOFer

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        player_name = event_data['player_name']
        team_id = event_data.get('team_id')  # May be None for league-wide
        position = event_data.get('position', 'Player')
        career_stats = event_data.get('career_stats', 'legendary career')
        is_first_ballot = event_data.get('is_first_ballot', False)

        # HOF inductions are maximum prestige
        magnitude = 100
        post_count = random.randint(5, 8) if is_first_ballot else random.randint(3, 5)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id) if team_id else 'NFL',
            'position': position,
            'stats': career_stats,
            'is_first_ballot': is_first_ballot,
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'player_name': player_name,
            'team_id': team_id,
            'position': position,
            'career_stats': career_stats,
            'is_first_ballot': is_first_ballot,
            'season': season,  # For team context
            'week': week  # For team context
        }

        posts = []

        # If player has primary team, generate team fan posts
        if team_id:
            team_post_count = int(post_count * 0.6)
            team_posts = self._generate_team_posts(
                team_id=team_id,
                event_type=SocialEventType.HOF_INDUCTION,
                event_outcome='POSITIVE',
                post_count=team_post_count,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.extend(team_posts)

        # League-wide media posts (analysts celebrating legacy)
        media_count = post_count - len(posts)
        media_posts = self._generate_media_posts(
            event_type=SocialEventType.HOF_INDUCTION,
            event_outcome='POSITIVE',
            post_count=media_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )
        posts.extend(media_posts)

        return posts

    def _generate_media_posts(
        self,
        event_type: SocialEventType,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """Generate posts from league-wide media."""
        media = self.personality_api.get_league_wide_personalities(
            dynasty_id=self.dynasty_id,
            personality_type='HOT_TAKE'
        )

        if not media:
            return []

        posts = []
        selected = random.sample(media, min(post_count, len(media)))

        for personality in selected:
            post = self._generate_single_post(
                personality=personality,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.append(post)

        return posts
