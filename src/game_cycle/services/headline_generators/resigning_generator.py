"""
Resigning Generator - Headlines for contract extensions and departures.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Mega-deal extensions (90+ OVR or $20M+ AAV)
- Star extensions (85+ OVR)
- Notable extensions (80+ OVR)
- Re-signing period summary
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from utils.player_field_extractors import extract_overall_rating
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class ResigningGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for contract extensions and re-signing departures.

    Headline tiers:
    - Mega-deal: 90+ OVR or $20M+ AAV - "Team Lock Up Superstar Long-Term"
    - Star extension: 85+ OVR - "Team Lock Up Player Long-Term"
    - Big money: $15M+ AAV (below 85 OVR) - "Team Commit Big Money to Player"
    - Notable extension: 80+ OVR - "Team Extend Player"
    - Notable departure: 80+ OVR - "Player Hits Free Agent Market"
    - Summary: "Re-Signing Period Complete: X Players Extended"

    Limits: 2 mega + 2 star + 2 big money + 1 notable = 7 max individual headlines
    """

    @property
    def max_headlines(self) -> int:
        """Max 7 individual resigning headlines per batch."""
        return 7

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 5+ total resigning events occurred."""
        return 5

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single re-signing or departure.

        Args:
            event: TransactionEvent for the re-signing or departure

        Returns:
            GeneratedHeadline appropriate to extension significance
        """
        # Handle departures separately
        if getattr(event, 'is_departure', False):
            return self._generate_departure_headline(event)

        overall = event.player_overall
        aav = event.financial_impact
        aav_m = aav / 1_000_000

        # Mega-deal extension (90+ OVR or $20M+ AAV)
        if overall >= 90 or aav >= 20_000_000:
            return self._generate_mega_deal_headline(event, aav_m)

        # Star extension (85+ OVR)
        if overall >= 85:
            return self._generate_star_extension_headline(event, aav_m)

        # Big money deal ($15M+ AAV, below 85 OVR)
        if aav >= 15_000_000:
            return self._generate_big_money_headline(event, aav_m)

        # Notable extension (80+ OVR)
        if overall >= 80:
            return self._generate_notable_extension_headline(event, aav_m)

        # Below threshold - no headline
        return None

    def _generate_mega_deal_headline(
        self,
        event: TransactionEvent,
        aav_m: float
    ) -> GeneratedHeadline:
        """Generate breaking news headline for mega-deal extension."""
        overall = event.player_overall
        years = event.contract_years

        if overall >= 90:
            priority = min(95, 85 + (overall - 90))
        else:
            priority = min(95, 85 + int((aav_m - 20) // 2))

        total_value = aav_m * years
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"BREAKING: {event.team_name} Lock Up {event.player_name} with Mega-Deal",
            subheadline=f"${total_value:.0f}M extension ({years} years, ${aav_m:.1f}M/year) keeps superstar in place",
            body_text=(
                f"In a franchise-defining move, the {event.team_name} have secured "
                f"{event.player_name} with a massive {years}-year extension worth "
                f"${aav_m:.1f}M per year. The ${total_value:.0f}M deal keeps the "
                f"{overall}-rated {position_abbr} in place through the "
                f"{event.season + years} season and represents one of the largest "
                f"contracts in the league."
            ),
            sentiment="HYPE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'resigning',
                'overall': event.player_overall,
                'aav': event.financial_impact,
                'years': event.contract_years,
                'is_mega_deal': True
            }
        )

    def _generate_star_extension_headline(
        self,
        event: TransactionEvent,
        aav_m: float
    ) -> GeneratedHeadline:
        """Generate headline for star extension (85+ OVR)."""
        overall = event.player_overall
        years = event.contract_years
        priority = min(90, 80 + (overall - 85))
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"{event.team_name} Lock Up {event.player_name} Long-Term",
            subheadline=f"{years}-year, ${aav_m:.1f}M/year extension secures star's future",
            body_text=(
                f"The {event.team_name} have reached a long-term agreement with "
                f"{event.player_name} on a {years}-year extension worth ${aav_m:.1f}M "
                f"per year. The deal keeps the {overall}-rated {position_abbr} "
                f"in place through the {event.season + years} season."
            ),
            sentiment="POSITIVE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'resigning',
                'overall': event.player_overall,
                'aav': event.financial_impact,
                'years': event.contract_years
            }
        )

    def _generate_big_money_headline(
        self,
        event: TransactionEvent,
        aav_m: float
    ) -> GeneratedHeadline:
        """Generate headline for big money deal ($15M+ AAV)."""
        years = event.contract_years
        total_value = aav_m * years
        priority = min(85, 70 + int(aav_m // 2))
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"{event.team_name} Commit Big Money to {event.player_name}",
            subheadline=f"${total_value:.0f}M deal keeps key player in place",
            body_text=(
                f"The {event.team_name} have made a significant investment in "
                f"{event.player_name}, signing the {position_abbr} to a "
                f"{years}-year deal worth ${aav_m:.1f}M per year. The extension "
                f"represents a major commitment to the team's core."
            ),
            sentiment="POSITIVE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'resigning',
                'aav': event.financial_impact,
                'years': event.contract_years
            }
        )

    def _generate_notable_extension_headline(
        self,
        event: TransactionEvent,
        aav_m: float
    ) -> GeneratedHeadline:
        """Generate headline for notable extension (80+ OVR)."""
        years = event.contract_years
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"{event.team_name} Extend {event.player_name}",
            subheadline=f"{years}-year extension keeps {position_abbr} with team",
            body_text=(
                f"The {event.team_name} have agreed to a {years}-year contract "
                f"extension with {event.player_name}. The deal, worth ${aav_m:.1f}M "
                f"per year, ensures the {position_abbr} remains with the "
                f"organization for the foreseeable future."
            ),
            sentiment="POSITIVE",
            priority=70,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'resigning',
                'aav': event.financial_impact,
                'years': event.contract_years
            }
        )

    def _generate_departure_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for notable departure (player released to free agency).

        Only generates headlines for 80+ OVR players.
        """
        overall = event.player_overall

        if overall < 80:
            return None

        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"{event.player_name} Hits Free Agent Market",
            subheadline=f"{event.team_name} unable to reach agreement with {overall} OVR {position_abbr}",
            body_text=(
                f"{event.player_name} will enter free agency after the {event.team_name} "
                f"were unable to reach an agreement on a new contract. The {overall}-rated "
                f"{position_abbr} is expected to draw significant interest on the "
                f"open market."
            ),
            sentiment="NEUTRAL",
            priority=65,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'departure',
                'overall': event.player_overall
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """Generate re-signing period summary headline."""
        if not events:
            return None

        resigned = [e for e in events if not getattr(e, 'is_departure', False)]
        released = [e for e in events if getattr(e, 'is_departure', False)]

        return GeneratedHeadline(
            headline_type="RESIGNING",
            headline=f"Re-Signing Period Complete: {len(resigned)} Players Extended",
            subheadline=f"{len(released)} players become free agents as teams finalize rosters",
            body_text=(
                f"The re-signing period has concluded with {len(resigned)} players "
                f"agreeing to new contracts with their current teams. Meanwhile, "
                f"{len(released)} players have entered free agency after failing to "
                f"reach new deals. Free agency will begin shortly."
            ),
            sentiment="NEUTRAL",
            priority=68,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'resigning_summary',
                'resigned': len(resigned),
                'released': len(released)
            }
        )

    def generate_with_departures(
        self,
        resigning_events: List[TransactionEvent],
        departure_events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[GeneratedHeadline]:
        """
        Generate headlines for both re-signings and departures.

        Convenience method that combines both event types before generation.
        """
        all_events = resigning_events + departure_events
        return self.generate_and_save(all_events, dynasty_id, season, week)