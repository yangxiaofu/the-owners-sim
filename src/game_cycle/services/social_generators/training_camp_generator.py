"""
Training Camp Social Post Generator.

Generates posts for training camp events:
- Standout performances (2-3 posts)
- Position battles (2-4 posts)
- Camp injuries (1-2 posts)
- Roster bubble players (1-2 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


class TrainingCampSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for training camp events.

    Training camp generates modest buzz around standouts,
    battles, and roster decisions.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a training camp event.

        Args:
            season: Season year
            week: Week number (typically 27 for training camp)
            event_data: Dict containing:
                - team_id: Team in camp
                - event_type: 'STANDOUT', 'BATTLE', 'INJURY', 'BUBBLE'
                - player_name: Player(s) involved
                - position: Position
                - description: Event description

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        camp_event_type = event_data.get('camp_event_type', 'STANDOUT')
        player_name = event_data.get('player_name', 'Player')
        position = event_data.get('position', 'Position')
        description = event_data.get('description', 'training camp news')

        # Determine magnitude and post count
        if camp_event_type == 'STANDOUT':
            magnitude = 55  # Standout performance
            post_count = random.randint(2, 3)
        elif camp_event_type == 'BATTLE':
            magnitude = 60  # Position battle (drama)
            post_count = random.randint(2, 4)
        elif camp_event_type == 'INJURY':
            magnitude = 50  # Camp injury
            post_count = random.randint(1, 2)
        else:  # BUBBLE
            magnitude = 45  # Roster bubble player
            post_count = random.randint(1, 2)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'description': description,
            'camp_event': camp_event_type.lower(),
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'camp_event_type': camp_event_type,
            'player_name': player_name,
            'position': position,
            'description': description,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts from team fans
        event_outcome = 'POSITIVE' if camp_event_type == 'STANDOUT' else 'NEUTRAL'
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.TRAINING_CAMP,
            event_outcome=event_outcome,
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts
