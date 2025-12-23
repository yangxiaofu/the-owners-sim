"""
Injury Social Post Generator.

Generates posts for player injuries:
- Major injuries (4-6 posts, season-ending)
- Moderate injuries (2-3 posts, multi-week)
- Minor injuries (1-2 posts, week-to-week)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class InjurySocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for player injuries.

    Injuries generate negative sentiment with volume based on
    player importance and severity.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a player injury.

        Args:
            season: Season year
            week: Week number
            event_data: Dict containing:
                - team_id: Team of injured player
                - player_name: Injured player
                - position: Player position
                - injury_type: Type of injury (e.g., "ACL", "Concussion")
                - severity: 'MINOR', 'MODERATE', 'MAJOR'
                - weeks_out: Estimated weeks missed

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        position = event_data.get('position', 'Player')
        injury_type = event_data.get('injury_type', 'injury')
        severity = event_data.get('severity', 'MODERATE')
        weeks_out = event_data.get('weeks_out', 1)

        # Determine magnitude and post count based on severity
        if severity == 'MAJOR' or weeks_out >= 8:
            magnitude = 75  # Season-ending injury
            post_count = random.randint(4, 6)
        elif severity == 'MODERATE' or weeks_out >= 3:
            magnitude = 55  # Multi-week injury
            post_count = random.randint(2, 3)
        else:
            magnitude = 40  # Minor injury (week-to-week)
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'injury': injury_type,
            'severity': severity.lower(),
            'weeks': weeks_out,
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'position': position,
            'injury_type': injury_type,
            'severity': severity,
            'weeks_out': weeks_out,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans (negative sentiment)
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.INJURY,
            event_outcome='LOSS',  # Injuries are negative like losses
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts
