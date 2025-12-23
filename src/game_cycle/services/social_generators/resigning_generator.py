"""
Re-signing Social Post Generator.

Generates posts for contract extensions (re-signing own players):
- Star player extensions (3-5 posts)
- Role player extensions (2-3 posts)
- Depth player extensions (1-2 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class ResigningSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for contract extensions (re-signings).

    Re-signings are typically positive (keeping your own players)
    with post volume based on player importance and contract size.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a contract extension.

        Args:
            season: Season year
            week: Week number (typically 24 for re-signing period)
            event_data: Dict containing:
                - team_id: Team extending the player
                - player_name: Player being extended
                - position: Player position
                - contract_value: Annual value (millions)
                - contract_years: Contract length
                - is_star: True if star player (optional)

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        position = event_data.get('position', 'Player')
        contract_value = event_data.get('contract_value', 0)
        contract_years = event_data.get('contract_years', 1)
        is_star = event_data.get('is_star', False)

        # Determine magnitude and post count based on contract value
        if is_star or contract_value > 20:
            magnitude = 75  # Star extension
            post_count = random.randint(3, 5)
        elif contract_value > 10:
            magnitude = 60  # Solid starter
            post_count = random.randint(2, 3)
        else:
            magnitude = 45  # Depth/role player
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'value': f'${contract_value}M',
            'years': contract_years,
            'total': f'${contract_value * contract_years}M',
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'position': position,
            'contract_value': contract_value,
            'contract_years': contract_years,
            'is_star': is_star,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans (positive - keeping their player)
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.RESIGNING,
            event_outcome='POSITIVE',  # Re-signings are generally positive
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts

    # ==========================================
    # Helper Methods
    # ==========================================
