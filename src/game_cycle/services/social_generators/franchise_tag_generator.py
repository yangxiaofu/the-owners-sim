"""
Franchise Tag Social Post Generator.

Generates posts for franchise tag designations:
- Exclusive tags (2-3 posts)
- Non-exclusive tags (2-3 posts)
- Transition tags (1-2 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class FranchiseTagSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for franchise tag designations.

    Franchise tags are controversial - fans have mixed reactions
    depending on player status and team situation.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a franchise tag designation.

        Args:
            season: Season year
            week: Week number (typically 23 for franchise tag period)
            event_data: Dict containing:
                - team_id: Team applying the tag
                - player_name: Player being tagged
                - position: Player position
                - tag_value: Tag salary amount (millions)
                - tag_type: 'EXCLUSIVE', 'NON_EXCLUSIVE', or 'TRANSITION'

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        position = event_data.get('position', 'Player')
        tag_value = event_data.get('tag_value', 0)
        tag_type = event_data.get('tag_type', 'EXCLUSIVE')

        # Determine magnitude and post count based on tag value
        # Higher value tags generate more buzz
        if tag_value > 20:
            magnitude = 75  # Major tag (QB, EDGE, WR1)
            post_count = random.randint(2, 3)
        elif tag_value > 15:
            magnitude = 65  # Solid starter
            post_count = random.randint(2, 3)
        else:
            magnitude = 55  # Lower-tier tag
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'value': f'${tag_value}M' if tag_value > 0 else 'franchise tag',
            'tag_type': tag_type,
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'position': position,
            'tag_value': tag_value,
            'tag_type': tag_type,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans
        # Franchise tags are controversial - mixed sentiment
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.FRANCHISE_TAG,
            event_outcome='NEUTRAL',  # Tags are controversial, not clearly positive
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts

    # ==========================================
    # Helper Methods
    # ==========================================
