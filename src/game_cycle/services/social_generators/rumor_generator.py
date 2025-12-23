"""
Rumor Social Post Generator.

Generates posts for trade rumors and speculation:
- Trade rumors (2-4 posts)
- Contract speculation (2-3 posts)
- Coaching changes (3-5 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


class RumorSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for rumors and speculation.

    Rumors generate moderate buzz with mixed sentiment.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a rumor.

        Args:
            season: Season year
            week: Week number
            event_data: Dict containing:
                - team_id: Team involved in rumor
                - rumor_type: 'TRADE', 'CONTRACT', 'COACHING'
                - subject: Subject of rumor (player/coach name)
                - credibility: 'LOW', 'MEDIUM', 'HIGH'

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        rumor_type = event_data.get('rumor_type', 'TRADE')
        subject = event_data.get('subject', 'Unknown')
        credibility = event_data.get('credibility', 'MEDIUM')

        # Determine magnitude and post count
        if credibility == 'HIGH':
            magnitude = 65  # Credible rumor
            post_count = random.randint(3, 5)
        elif credibility == 'MEDIUM':
            magnitude = 50  # Moderate credibility
            post_count = random.randint(2, 3)
        else:
            magnitude = 35  # Low credibility
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'subject': subject,
            'team': self._get_team_name(team_id),
            'rumor_type': rumor_type.lower(),
            'credibility': credibility.lower(),
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'rumor_type': rumor_type,
            'subject': subject,
            'credibility': credibility,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from fans and analysts
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.RUMOR,
            event_outcome='NEUTRAL',  # Rumors are speculative
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts
