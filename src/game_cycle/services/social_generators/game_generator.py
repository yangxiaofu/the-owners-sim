"""
Game Result Social Post Generator.

Generates posts for:
- Regular season games (4-6 posts)
- Upsets (8-12 posts)
- Blowouts (6-10 posts)
- Playoff games (1.5x multiplier)
- Super Bowl (10-15 posts)

Part of Milestone 14: Social Media - Phase 2 Architectural Refactoring.
"""

import logging
import random
from typing import List, Dict, Any, Optional, Tuple

from .base_generator import BaseSocialPostGenerator, GeneratedSocialPost
from game_cycle.models.social_event_types import SocialEventType
from game_cycle.services.team_context_builder import TeamContextBuilder
from team_management.teams.team_loader import get_team_by_id


logger = logging.getLogger(__name__)


# Event magnitude thresholds
MAGNITUDE_NORMAL = 50
MAGNITUDE_UPSET = 75
MAGNITUDE_BLOWOUT = 80


class GameSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for game results.

    Handles regular season games, playoffs, and Super Bowl with
    appropriate post volume and engagement based on game context.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a game result.

        Args:
            season: Season year
            week: Week number
            event_data: Dict containing:
                - winning_team_id: Winning team ID
                - losing_team_id: Losing team ID
                - winning_score: Winner's score
                - losing_score: Loser's score
                - game_id: Optional game identifier
                - is_upset: True if upset victory
                - is_blowout: True if blowout (21+ point margin)
                - star_players: Optional dict of {team_id: player_name}
                - season_type: 'regular' or 'playoffs' (default: 'regular')
                - round_name: Playoff round name (e.g., 'wild_card', 'super_bowl')

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract event data
        winning_team_id = event_data['winning_team_id']
        losing_team_id = event_data['losing_team_id']
        winning_score = event_data['winning_score']
        losing_score = event_data['losing_score']
        game_id = event_data.get('game_id')
        is_upset = event_data.get('is_upset', False)
        is_blowout = event_data.get('is_blowout', False)
        star_players = event_data.get('star_players', {})
        season_type = event_data.get('season_type', 'regular')
        round_name = event_data.get('round_name')

        # Determine event magnitude and base post count
        margin = winning_score - losing_score
        is_playoffs = (season_type == 'playoffs')
        is_super_bowl = (round_name == 'super_bowl')

        if is_blowout or margin >= 21:
            magnitude = MAGNITUDE_BLOWOUT
            post_count = random.randint(6, 10)
        elif is_upset:
            magnitude = MAGNITUDE_UPSET
            post_count = random.randint(8, 12)
        else:
            magnitude = MAGNITUDE_NORMAL
            post_count = random.randint(4, 6)

        # Playoff multiplier: Playoff games generate MORE buzz
        if is_playoffs:
            if is_super_bowl:
                # Super Bowl: Maximum engagement (10-15 posts)
                post_count = random.randint(10, 15)
                magnitude = 100  # Maximum magnitude
            else:
                # Other playoff rounds: 1.5x normal posts
                post_count = int(post_count * 1.5)
                magnitude = min(100, magnitude + 10)  # Boost magnitude slightly

        # Event metadata
        event_metadata = {
            'game_id': game_id,
            'winning_team': winning_team_id,
            'losing_team': losing_team_id,
            'score': f"{winning_score}-{losing_score}",
            'margin': margin,
            'is_upset': is_upset,
            'is_blowout': is_blowout,
            'season_type': season_type,
            'round_name': round_name,
            'season': season,  # For team context
            'week': week  # For team context
        }

        # Playoff context for templates
        round_display = self._get_round_display_name(round_name) if round_name else None

        # Generate posts
        posts = []

        # 50% from winning team fans (celebrating)
        winner_post_count = int(post_count * 0.5)
        winner_posts = self._generate_team_posts(
            team_id=winning_team_id,
            event_type=SocialEventType.GAME_RESULT,
            event_outcome='WIN',
            post_count=winner_post_count,
            magnitude=magnitude,
            variables={
                'winner': self._get_team_name(winning_team_id),
                'loser': self._get_team_name(losing_team_id),
                'score': f'{winning_score}-{losing_score}',
                'player': star_players.get(winning_team_id, 'the team') if star_players else 'the team',
                'stat': '200+ yards' if star_players else 'great stats',
                'magnitude': magnitude,
                'round': round_display or '',
                'is_playoffs': is_playoffs,
                'is_super_bowl': is_super_bowl
            },
            event_metadata=event_metadata
        )
        posts.extend(winner_posts)

        # 30% from losing team fans (upset/angry)
        loser_post_count = int(post_count * 0.3)
        loser_posts = self._generate_team_posts(
            team_id=losing_team_id,
            event_type=SocialEventType.GAME_RESULT,
            event_outcome='LOSS',
            post_count=loser_post_count,
            magnitude=magnitude,
            variables={
                'loser': self._get_team_name(losing_team_id),
                'winner': self._get_team_name(winning_team_id),
                'score': f'{winning_score}-{losing_score}',
                'player': star_players.get(losing_team_id, 'the team') if star_players else 'the team',
                'magnitude': magnitude,
                'round': round_display or '',
                'is_playoffs': is_playoffs,
                'is_super_bowl': is_super_bowl
            },
            event_metadata=event_metadata
        )
        posts.extend(loser_posts)

        # Media posts (hot takes on upsets/blowouts OR playoffs)
        if is_upset or is_blowout or is_playoffs:
            media_post_count = random.randint(2, 4) if is_playoffs else random.randint(1, 2)
            media_posts = self._generate_media_posts(
                event_type=SocialEventType.GAME_RESULT,
                event_outcome='WIN' if random.random() > 0.5 else 'LOSS',
                post_count=media_post_count,
                magnitude=magnitude,
                variables={
                    'winner': self._get_team_name(winning_team_id),
                    'loser': self._get_team_name(losing_team_id),
                    'score': f'{winning_score}-{losing_score}',
                    'magnitude': magnitude,
                    'round': round_display or '',
                    'is_playoffs': is_playoffs,
                    'is_super_bowl': is_super_bowl
                },
                event_metadata=event_metadata
            )
            posts.extend(media_posts)

        return posts

    # ==========================================
    # Helper Methods
    # ==========================================

    def _generate_media_posts(
        self,
        event_type: SocialEventType,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts from league-wide media personalities.

        Args:
            event_type: Event type enum
            event_outcome: Event outcome
            post_count: Number of posts to generate
            magnitude: Event magnitude
            variables: Template variables
            event_metadata: Event metadata

        Returns:
            List of GeneratedSocialPost objects
        """
        # Get hot take analysts (they post on dramatic events)
        media = self.personality_api.get_league_wide_personalities(
            dynasty_id=self.dynasty_id,
            personality_type='HOT_TAKE'
        )

        if not media:
            return []

        posts = []
        selected_media = random.sample(media, min(post_count, len(media)))

        for personality in selected_media:
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

    def _get_round_display_name(self, round_name: str) -> str:
        """
        Get display-friendly playoff round name.

        Args:
            round_name: Internal round name (e.g., 'wild_card', 'super_bowl')

        Returns:
            Display name (e.g., 'Wild Card', 'Super Bowl')
        """
        round_names = {
            'wild_card': 'Wild Card',
            'divisional': 'Divisional Round',
            'conference': 'Conference Championship',
            'super_bowl': 'Super Bowl'
        }
        return round_names.get(round_name, round_name.replace('_', ' ').title())
