"""
Award Social Post Generator.

Generates posts for award announcements:
- MVP (2-4 posts, magnitude 100)
- DPOY, OROY, DROY (2-4 posts, magnitude 85-90)
- CPOY (2-4 posts, magnitude 80)
- All-Pro (1-2 posts, magnitude 75)
- Pro Bowl (1-2 posts, magnitude 60)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType
from game_cycle.services.team_context_builder import TeamContextBuilder
from team_management.teams.team_loader import get_team_by_id


logger = logging.getLogger(__name__)


class AwardSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for award announcements.

    Handles major awards (MVP, DPOY, etc.) and recognitions (All-Pro, Pro Bowl)
    with appropriate post volume and engagement based on award prestige.
    """

    # Award prestige mapping (determines magnitude and post volume)
    AWARD_PRESTIGE = {
        'MVP': 100,
        'DPOY': 90,
        'OROY': 85,
        'DROY': 85,
        'CPOY': 80,
        'ALL_PRO_FIRST': 75,
        'ALL_PRO_SECOND': 65,
        'PRO_BOWL': 60,
        # Fallback for unknown awards
        'DEFAULT': 70
    }

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for an award announcement.

        Args:
            season: Season year
            week: Week number (typically 23 for offseason awards)
            event_data: Dict containing:
                - award_name: Award name (MVP, DPOY, etc.)
                - player_name: Winner's name
                - team_id: Winner's team ID
                - player_stats: Optional stat line (e.g., "4,500 yards, 35 TDs")

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        award_name = event_data['award_name']
        player_name = event_data['player_name']
        team_id = event_data['team_id']
        player_stats = event_data.get('player_stats')

        # Determine magnitude based on award prestige
        magnitude = self.AWARD_PRESTIGE.get(award_name, self.AWARD_PRESTIGE['DEFAULT'])

        # Calculate post count based on prestige
        if magnitude >= 80:
            post_count = random.randint(2, 4)  # Major awards
        else:
            post_count = random.randint(1, 2)  # Minor recognitions

        # Build template variables
        variables = {
            'player': player_name,
            'award': award_name,
            'stat': player_stats or 'dominant season',
            'team': self._get_team_name(team_id),
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'award': award_name,
            'player_name': player_name,
            'team_id': team_id,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans (celebrating their player's honor)
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.AWARD,
            event_outcome='POSITIVE',
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts
