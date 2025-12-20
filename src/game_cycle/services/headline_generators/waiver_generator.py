"""
Waiver Wire Generator - Headlines for waiver wire claims.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Notable waiver claims (80+ OVR)
- Standard waiver claims (75+ OVR)
- Quality depth claims (70+ OVR)
- Waiver wire recap summary
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class WaiverGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for waiver wire claims.

    Headline tiers:
    - Notable claim: 80+ OVR - "Team Land Player in Waiver Claim"
    - Standard claim: 75-79 OVR - "Team Claim Player Off Waivers"
    - Quality depth: 70-74 OVR - "Team Add Player via Waivers"
    - Summary: "Waiver Wire Recap: X Players Claimed"

    Limits: 2 notable + 2 standard + 2 quality = 6 max individual headlines
    """

    @property
    def max_headlines(self) -> int:
        """Max 6 individual waiver claim headlines per batch."""
        return 6

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 5+ claims occurred."""
        return 5

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single waiver claim.

        Args:
            event: TransactionEvent for the waiver claim

        Returns:
            GeneratedHeadline appropriate to claim significance
        """
        overall = event.player_overall

        # Notable claim (80+ OVR)
        if overall >= 80:
            return self._generate_notable_claim_headline(event)

        # Standard claim (75-79 OVR)
        if overall >= 75:
            return self._generate_standard_claim_headline(event)

        # Quality depth claim (70-74 OVR)
        if overall >= 70:
            return self._generate_depth_claim_headline(event)

        # Below threshold - no headline
        return None

    def _generate_notable_claim_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for notable waiver claim (80+ OVR)."""
        former_team = event.details.get('former_team_name', 'their former team')
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="WAIVER_CLAIM",
            headline=f"{event.team_name} Land {event.player_name} in Waiver Claim",
            subheadline=f"Former {former_team} {position_abbr} adds quality depth to roster",
            body_text=(
                f"The {event.team_name} have successfully claimed {event.player_name} off waivers. "
                f"The {event.player_overall}-rated {position_abbr} was released by {former_team} "
                f"and will now bolster the {event.team_name}'s roster heading into the {event.season} season."
            ),
            sentiment="POSITIVE",
            priority=70,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'waiver_claim',
                'overall': event.player_overall,
                'former_team_id': event.details.get('former_team_id')
            }
        )

    def _generate_standard_claim_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for standard waiver claim (75-79 OVR)."""
        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="WAIVER_CLAIM",
            headline=f"{event.team_name} Claim {event.player_name} Off Waivers",
            subheadline=f"{position_abbr} acquired to address roster needs",
            body_text=(
                f"The {event.team_name} have added {event.player_name} via the waiver wire. "
                f"The {position_abbr} will provide depth as the team prepares for the upcoming season."
            ),
            sentiment="POSITIVE",
            priority=60,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={'event_type': 'waiver_claim'}
        )

    def _generate_depth_claim_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for quality depth claim (70-74 OVR)."""
        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="WAIVER_CLAIM",
            headline=f"{event.team_name} Add {event.player_name} via Waivers",
            subheadline=f"Depth {position_abbr} claimed off waiver wire",
            body_text=(
                f"The {event.team_name} have claimed {event.player_name} off waivers, "
                f"adding depth at the {position_abbr} position as the team finalizes its roster."
            ),
            sentiment="NEUTRAL",
            priority=50,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={'event_type': 'waiver_claim'}
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate waiver wire recap summary headline.

        Args:
            events: All waiver claim events

        Returns:
            Summary headline for waiver wire activity
        """
        if not events:
            return None

        # Extract cleared_to_fa count from metadata if available
        cleared_count = 0
        for event in events:
            if 'cleared_to_fa_count' in event.details:
                cleared_count = event.details['cleared_to_fa_count']
                break

        # Build subheadline based on available data
        if cleared_count > 0:
            subheadline = f"{cleared_count} unclaimed players enter free agency"
        else:
            subheadline = "Teams finalize rosters through waiver wire activity"

        return GeneratedHeadline(
            headline_type="WAIVER_CLAIM",
            headline=f"Waiver Wire Recap: {len(events)} Players Claimed",
            subheadline=subheadline,
            body_text=(
                f"The waiver wire period has concluded with {len(events)} players being claimed "
                f"by teams across the league. "
                + (f"Additionally, {cleared_count} players cleared waivers and are now free agents."
                   if cleared_count > 0 else
                   "Teams have added depth and addressed roster needs through the waiver process.")
            ),
            sentiment="NEUTRAL",
            priority=55,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'waiver_summary',
                'claims': len(events),
                'cleared': cleared_count
            }
        )

    def generate_with_clearances(
        self,
        events: List[TransactionEvent],
        cleared_to_fa_count: int,
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[GeneratedHeadline]:
        """
        Generate headlines for waiver wire activity including clearance data.

        Convenience method that injects cleared_to_fa_count into event details
        for use in summary headline generation.
        """
        if events:
            events[0].details['cleared_to_fa_count'] = cleared_to_fa_count

        return self.generate_and_save(events, dynasty_id, season, week)