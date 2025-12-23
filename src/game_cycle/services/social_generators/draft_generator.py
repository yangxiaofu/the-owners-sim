"""
Draft Pick Social Post Generator.

Generates posts for NFL Draft selections:
- First round picks (4-6 posts)
- Day 2 picks (2-4 posts)
- Day 3 picks (1-2 posts)
- Surprise/reach picks (5-7 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType


logger = logging.getLogger(__name__)


class DraftSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for draft picks.

    Draft picks generate high engagement, especially first round
    and surprise selections.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a draft pick.

        Args:
            season: Season year
            week: Week number (typically 25 for draft)
            event_data: Dict containing:
                - team_id: Team making the pick
                - player_name: Player selected
                - position: Player position
                - round: Draft round (1-7)
                - pick_number: Overall pick number
                - is_surprise: True if reach/surprise pick
                - college: Player's college (optional)

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        position = event_data.get('position', 'Player')
        round_num = event_data.get('round', 1)
        pick_number = event_data.get('pick_number', 1)
        is_surprise = event_data.get('is_surprise', False)
        college = event_data.get('college', 'College')

        # Determine magnitude and post count based on round and context
        if round_num == 1:
            magnitude = 80  # First round - high buzz
            post_count = random.randint(4, 6)
        elif round_num <= 3:
            magnitude = 60  # Day 2 (rounds 2-3)
            post_count = random.randint(2, 4)
        else:
            magnitude = 40  # Day 3 (rounds 4-7)
            post_count = random.randint(1, 2)

        # Surprise picks generate extra buzz
        if is_surprise:
            magnitude = min(100, magnitude + 15)
            post_count = random.randint(5, 7)

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'position': position,
            'round': round_num,
            'pick': pick_number,
            'college': college,
            'is_surprise': is_surprise,
            'magnitude': magnitude
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'position': position,
            'round': round_num,
            'pick_number': pick_number,
            'is_surprise': is_surprise,
            'college': college,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Generate posts
        posts = []

        # Team fan posts (excited about new pick)
        team_post_count = int(post_count * 0.7)
        team_posts = self._generate_team_posts(
            team_id=team_id,
            event_type=SocialEventType.DRAFT_PICK,
            event_outcome='POSITIVE' if not is_surprise else 'NEUTRAL',
            post_count=team_post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )
        posts.extend(team_posts)

        # Draft analyst posts (especially for surprises)
        if is_surprise or round_num == 1:
            analyst_count = post_count - team_post_count
            analyst_posts = self._generate_analyst_posts(
                team_id=team_id,
                event_type=SocialEventType.DRAFT_PICK,
                event_outcome='NEUTRAL',
                post_count=analyst_count,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.extend(analyst_posts)

        return posts

    # ==========================================
    # Helper Methods
    # ==========================================

    def _generate_analyst_posts(
        self,
        team_id: int,
        event_type: SocialEventType,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """Generate posts from draft analysts."""
        # Get draft analysts (fans with appropriate archetype)
        analysts = self.personality_api.get_personalities_by_team(
            dynasty_id=self.dynasty_id,
            team_id=team_id,
            personality_type='FAN'
        )

        # Filter for trade analysts (they also cover draft)
        draft_analysts = [p for p in analysts if p.archetype in ['TRADE_ANALYST', 'OPTIMIST']]

        if not draft_analysts:
            return []

        posts = []
        selected = random.sample(draft_analysts, min(post_count, len(draft_analysts)))

        for analyst in selected:
            post = self._generate_single_post(
                personality=analyst,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.append(post)

        return posts
