"""
Franchise Tag Generator - Headlines for franchise tag applications.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Elite franchise tags (premium positions: QB, LT, RT, EDGE, WR, DE)
- High-value tags ($20M+ tag salary)
- Transition tags (non-exclusive)
- Franchise tag deadline summary
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class FranchiseTagGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for franchise tag applications.

    Headline tiers:
    - Premium position tags: QB, LT, RT, EDGE, WR, DE - "Team Lock In Player with Franchise Tag"
    - High-value tags: $20M+ salary - "Team Place Franchise Tag on Player"
    - Transition tags: Non-exclusive - "Team Apply Transition Tag to Player"
    - Summary: "Franchise Tag Deadline: X Players Tagged League-Wide"

    All franchise tags are notable by definition. Limits: 5 individual tag headlines.
    """

    @property
    def max_headlines(self) -> int:
        """Max 5 individual tag headlines per batch."""
        return 5

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 4+ tags occurred."""
        return 4

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single franchise tag application.

        Args:
            event: TransactionEvent for the franchise tag

        Returns:
            GeneratedHeadline appropriate to tag type and player prominence
        """
        tag_type = event.details.get("tag_type", "franchise")
        tag_salary = event.financial_impact
        tag_salary_m = tag_salary / 1_000_000
        position_abbr = get_position_abbreviation(event.player_position)

        # Premium positions (higher priority)
        premium_positions = {"QB", "LT", "RT", "EDGE", "WR", "DE"}

        # Transition tag (non-exclusive)
        if tag_type == "transition":
            return self._generate_transition_tag_headline(event, tag_salary_m)

        # Premium position tag (exclusive)
        if position_abbr in premium_positions:
            return self._generate_premium_tag_headline(event, tag_salary_m)

        # Standard franchise tag
        return self._generate_standard_tag_headline(event, tag_salary_m)

    def _generate_premium_tag_headline(
        self,
        event: TransactionEvent,
        tag_salary_m: float
    ) -> GeneratedHeadline:
        """Generate headline for premium position franchise tag."""
        priority = 85

        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="FRANCHISE_TAG",
            headline=f"{event.team_name} Lock In {event.player_name} with Franchise Tag",
            subheadline=f"Star {position_abbr} guaranteed ${tag_salary_m:.1f}M under exclusive tag",
            body_text=(
                f"{event.team_name} have applied the franchise tag to {event.player_name}, "
                f"guaranteeing the {position_abbr} ${tag_salary_m:.1f}M for the {event.season} season. "
                f"The move prevents the player from hitting the open market while the team works "
                f"toward a long-term extension."
            ),
            sentiment="HYPE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'franchise_tag',
                'tag_type': event.details.get('tag_type', 'franchise'),
                'tag_salary': event.financial_impact,
                'position': event.player_position
            }
        )

    def _generate_standard_tag_headline(
        self,
        event: TransactionEvent,
        tag_salary_m: float
    ) -> GeneratedHeadline:
        """Generate headline for standard franchise tag."""
        priority = 80 if tag_salary_m >= 20 else 75
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="FRANCHISE_TAG",
            headline=f"{event.team_name} Place Franchise Tag on {event.player_name}",
            subheadline=f"{position_abbr} will earn ${tag_salary_m:.1f}M guaranteed if no long-term deal reached",
            body_text=(
                f"{event.team_name} have applied the franchise tag to {event.player_name}, "
                f"guaranteeing the {position_abbr} ${tag_salary_m:.1f}M for the {event.season} season. "
                f"The move prevents the player from hitting the open market while the team works "
                f"toward a long-term extension."
            ),
            sentiment="NEUTRAL",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'franchise_tag',
                'tag_type': event.details.get('tag_type', 'franchise'),
                'tag_salary': event.financial_impact,
                'position': event.player_position
            }
        )

    def _generate_transition_tag_headline(
        self,
        event: TransactionEvent,
        tag_salary_m: float
    ) -> GeneratedHeadline:
        """Generate headline for transition tag (non-exclusive)."""
        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="FRANCHISE_TAG",
            headline=f"{event.team_name} Apply Transition Tag to {event.player_name}",
            subheadline=f"{position_abbr} can negotiate with other teams, {event.team_name} have right of first refusal",
            body_text=(
                f"{event.team_name} have applied the transition tag to {event.player_name}, "
                f"guaranteeing the {position_abbr} ${tag_salary_m:.1f}M for the {event.season} season. "
                f"Unlike the franchise tag, the transition tag allows {event.player_name} to negotiate "
                f"with other teams, though {event.team_name} retain the right of first refusal on any offer sheet."
            ),
            sentiment="NEUTRAL",
            priority=75,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'franchise_tag',
                'tag_type': 'transition',
                'tag_salary': event.financial_impact,
                'position': event.player_position
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate franchise tag deadline summary headline.

        Args:
            events: All franchise tag events

        Returns:
            Summary headline for franchise tag deadline
        """
        if not events:
            return None

        total_value = sum(e.financial_impact for e in events)
        total_value_m = total_value / 1_000_000
        season = events[0].season if events else 2024

        return GeneratedHeadline(
            headline_type="FRANCHISE_TAG",
            headline=f"Franchise Tag Deadline: {len(events)} Players Tagged League-Wide",
            subheadline=f"Teams commit ${total_value_m:.0f}M in tag guarantees",
            body_text=(
                f"The franchise tag window has closed with {len(events)} players receiving tags "
                f"across the league. Teams have committed over ${total_value_m:.0f}M in guaranteed money "
                f"to retain key players."
            ),
            sentiment="NEUTRAL",
            priority=78,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'franchise_tag_summary',
                'tag_count': len(events),
                'total_value': total_value
            }
        )