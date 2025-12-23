"""
Waiver Wire Social Post Generator.

Generates posts for waiver wire claims:
- Waiver pickups (2-3 posts)
- Competitive waiver battles (3-4 posts)
- Emergency pickups (1-2 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class WaiverSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for waiver wire claims.

    Waiver claims generate modest buzz, especially for known names
    or injury replacements.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a waiver claim.

        Args:
            season: Season year
            week: Week number
            event_data: Dict containing:
                - team_id: Team claiming the player
                - player_name: Player claimed
                - position: Player position
                - waiver_priority: Waiver order used (optional)
                - is_emergency: True if emergency pickup (injury replacement)

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        position = event_data.get('position', 'Player')
        waiver_priority = event_data.get('waiver_priority')
        is_emergency = event_data.get('is_emergency', False)

        # Determine magnitude and post count
        if is_emergency:
            magnitude = 50  # Emergency pickup (injury replacement)
            post_count = random.randint(2, 3)
        else:
            magnitude = 45  # Standard waiver claim
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'priority': waiver_priority if waiver_priority else 'waiver claim',
            'is_emergency': is_emergency,
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'position': position,
            'waiver_priority': waiver_priority,
            'is_emergency': is_emergency,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.WAIVER_CLAIM,
            event_outcome='NEUTRAL',
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts
