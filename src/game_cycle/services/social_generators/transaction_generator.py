"""
Transaction Social Post Generator.

Generates posts for transactions:
- Trades (3-5 posts, magnitude based on trade value)
- Signings (2-5 posts, magnitude based on contract value)
- Cuts (2-4 posts, magnitude ~40)

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


# Transaction magnitude constants
MAGNITUDE_MAJOR_TRADE = 70
MAGNITUDE_CUT_DEFAULT = 40


class TransactionSocialGenerator(BaseSocialPostGenerator):
    """
    Generates social media posts for transactions.

    Handles trades, signings, and cuts with appropriate post volume
    and engagement based on transaction value.
    """

    def _generate_posts(
        self, season: int, week: int, event_data: Dict[str, Any]
    ) -> List[GeneratedSocialPost]:
        """
        Generate posts for a transaction (trade, signing, or cut).

        Args:
            season: Season year
            week: Week number
            event_data: Dict containing:
                - event_type: Transaction type ('TRADE', 'SIGNING', 'CUT')
                - team_id: Primary team involved
                - player_name: Player name
                - transaction_details: Transaction-specific details:
                    For TRADE:
                        - magnitude: Trade importance (optional, default 70)
                        - trade_partner: Partner team name
                        - picks: Draft picks involved
                    For SIGNING:
                        - value: Contract value (millions)
                        - years: Contract length
                    For CUT:
                        - magnitude: Cut importance (optional, default 40)
                        - savings: Cap savings (optional)

        Returns:
            List of GeneratedSocialPost objects
        """
        # Extract common event data
        event_type_str = event_data['event_type']  # String: 'TRADE', 'SIGNING', 'CUT'
        team_id = event_data['team_id']
        player_name = event_data['player_name']
        transaction_details = event_data.get('transaction_details', {})

        # Convert string to enum
        event_type_enum = SocialEventType[event_type_str]

        # Determine magnitude and post count based on transaction type
        if event_type_str == 'TRADE':
            magnitude = transaction_details.get('magnitude', MAGNITUDE_MAJOR_TRADE)
            post_count = random.randint(3, 5)
        elif event_type_str == 'SIGNING':
            contract_value = transaction_details.get('value', 0)
            # $20M contract = ~50 magnitude, scales up to 100
            magnitude = min(100, int(contract_value / 2) + 40)
            post_count = random.randint(3, 5) if contract_value > 10 else random.randint(2, 3)
        elif event_type_str == 'CUT':
            magnitude = transaction_details.get('magnitude', MAGNITUDE_CUT_DEFAULT)
            post_count = random.randint(2, 4)
        else:
            # Unknown transaction type, use defaults
            magnitude = 50
            post_count = 3

        # Build template variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'magnitude': magnitude,
            **transaction_details  # Include all transaction-specific details
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            'season': season,  # For team context
            'week': week,  # For team context
            **transaction_details
        }

        # Generate posts
        posts = []

        # Team fan posts (70% of total)
        team_post_count = int(post_count * 0.7)
        event_outcome = 'POSITIVE' if event_type_str == 'SIGNING' else 'NEUTRAL'

        team_posts = self._generate_team_posts(
            team_id=team_id,
            event_type=event_type_enum,
            event_outcome=event_outcome,
            post_count=team_post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )
        posts.extend(team_posts)

        # Analyst posts for trades and signings (30% of total)
        if event_type_str in ['TRADE', 'SIGNING']:
            analyst_count = post_count - team_post_count
            analyst_posts = self._generate_analyst_posts(
                team_id=team_id,
                event_type=event_type_enum,
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
        """Generate posts from trade/contract analysts."""
        # Get team's analysts (fans with TRADE_ANALYST archetype)
        analysts = self.personality_api.get_personalities_by_team(
            dynasty_id=self.dynasty_id,
            team_id=team_id,
            personality_type='FAN'
        )

        # Filter for trade analysts
        trade_analysts = [p for p in analysts if p.archetype == 'TRADE_ANALYST']

        if not trade_analysts:
            return []

        posts = []
        selected = random.sample(trade_analysts, min(post_count, len(trade_analysts)))

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
