"""
Signing Generator - Headlines for free agency signings.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Elite signings (90+ OVR)
- Star signings (85+ OVR)
- Notable signings (80+ OVR with high AAV)
- Free agency frenzy summary (Wave 1 with 5+ signings)
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class SigningGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for free agency signings.

    Headline tiers:
    - Elite signing: 90+ OVR - "BREAKING: Team Sign Superstar Player"
    - Star signing: 85+ OVR - "Team Land Star Player in Free Agency"
    - Notable signing: 80+ OVR with $10M+ AAV - "Team Address Need with Player Signing"
    - Summary: "Free Agency Frenzy: X Players Sign on Opening Day"

    Limits: 3 star + 2 notable = 5 max individual headlines
    """

    def __init__(self, db_path: str, prominence_calc=None):
        """
        Initialize SigningGenerator.

        Args:
            db_path: Path to game_cycle.db
            prominence_calc: Optional ProminenceCalculator instance
        """
        super().__init__(db_path, prominence_calc)
        self.wave = 1  # Track current FA wave for summary generation

    @property
    def max_headlines(self) -> int:
        """Max 5 individual signing headlines per batch."""
        return 5

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 5+ signings in Wave 1."""
        return 5

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single signing.

        Args:
            event: TransactionEvent for the signing

        Returns:
            GeneratedHeadline appropriate to signing significance
        """
        overall = event.player_overall
        aav = event.financial_impact

        # Elite signing (90+ OVR)
        if overall >= 90:
            return self._generate_elite_signing_headline(event)

        # Star signing (85+ OVR)
        if overall >= 85:
            return self._generate_star_signing_headline(event)

        # Notable signing (80+ OVR with $10M+ AAV)
        if overall >= 80 and aav >= 10_000_000:
            return self._generate_notable_signing_headline(event)

        # Below threshold - no headline
        return None

    def _generate_elite_signing_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate breaking news headline for elite signing."""
        aav_millions = event.financial_impact / 1_000_000
        years = event.contract_years

        # Priority scales with overall (90-94 OVR = 85-89 priority)
        priority = min(92, 80 + (event.player_overall - 85))

        # Position-specific language
        position_phrases = {
            'QB': 'franchise quarterback',
            'EDGE': 'pass rush threat',
            'CB': 'lockdown cornerback',
            'WR': 'elite receiver',
            'LT': 'franchise left tackle',
            'DT': 'defensive cornerstone',
        }
        position_abbr = get_position_abbreviation(event.player_position)
        position_phrase = position_phrases.get(
            position_abbr,
            position_abbr
        )

        return GeneratedHeadline(
            headline_type="SIGNING",
            headline=f"BREAKING: {event.team_name} Sign Superstar {event.player_name}",
            subheadline=f"Blockbuster {years}-year, ${aav_millions:.1f}M/year deal lands {position_phrase}",
            body_text=(
                f"In one of the biggest moves of free agency, the {event.team_name} "
                f"have agreed to terms with {event.player_name}, a {event.player_overall}-rated "
                f"{get_position_abbreviation(event.player_position)}, on a {years}-year contract worth ${aav_millions:.1f}M "
                f"per year. The signing immediately elevates the roster and addresses a critical need "
                f"heading into the {event.season} season."
            ),
            sentiment="HYPE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'fa_signing',
                'tier': 'elite',
                'overall': event.player_overall,
                'aav': event.financial_impact,
                'wave': event.details.get('wave', 1)
            }
        )

    def _generate_star_signing_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for star-level signing."""
        aav_millions = event.financial_impact / 1_000_000
        years = event.contract_years

        # Priority based on AAV for star signings
        priority = min(85, 60 + int(aav_millions))

        return GeneratedHeadline(
            headline_type="SIGNING",
            headline=f"{event.team_name} Land Star {get_position_abbreviation(event.player_position)} {event.player_name}",
            subheadline=f"{years}-year, ${aav_millions:.1f}M/year deal addresses key need",
            body_text=(
                f"The {event.team_name} have made a splash in free agency, signing "
                f"{event.player_name} to a {years}-year contract worth ${aav_millions:.1f}M "
                f"per year. The {event.player_overall}-rated {get_position_abbreviation(event.player_position)} "
                f"brings proven production and fills an important roster need as the team "
                f"builds for the {event.season} season."
            ),
            sentiment="POSITIVE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'fa_signing',
                'tier': 'star',
                'overall': event.player_overall,
                'aav': event.financial_impact,
                'wave': event.details.get('wave', 1)
            }
        )

    def _generate_notable_signing_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for notable signing."""
        aav_millions = event.financial_impact / 1_000_000
        years = event.contract_years

        return GeneratedHeadline(
            headline_type="SIGNING",
            headline=f"{event.team_name} Address Need with {event.player_name} Signing",
            subheadline=f"{get_position_abbreviation(event.player_position)} inks {years}-year, ${aav_millions:.1f}M/year contract",
            body_text=(
                f"{event.team_name} have agreed to terms with {event.player_name} on a "
                f"{years}-year contract worth ${aav_millions:.1f}M per year. The signing "
                f"bolsters the roster heading into the {event.season} season."
            ),
            sentiment="POSITIVE",
            priority=65,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'fa_signing',
                'tier': 'notable',
                'overall': event.player_overall,
                'aav': event.financial_impact,
                'wave': event.details.get('wave', 1)
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate summary headline for free agency frenzy.

        Only generates for Wave 1 with 5+ signings.

        Args:
            events: All signing events

        Returns:
            Summary headline for opening day frenzy, or None to skip
        """
        if not events:
            return None

        # Extract wave from first event (assumes all events from same wave)
        wave = events[0].details.get('wave', 1)

        # Only generate frenzy headline for Wave 1 with enough activity
        if wave != 1 or len(events) < self.summary_threshold:
            return None

        # Get season from first event
        season = events[0].season if events else 2024

        return GeneratedHeadline(
            headline_type="SIGNING",
            headline=f"Free Agency Frenzy: {len(events)} Players Sign on Opening Day",
            subheadline="Elite free agents find new homes as market opens",
            body_text=(
                f"Free agency is officially underway with {len(events)} players signing "
                f"new contracts on the first day of the legal tampering period. Teams wasted "
                f"no time addressing roster needs, with several blockbuster deals reshaping "
                f"the landscape heading into the {season} season."
            ),
            sentiment="HYPE",
            priority=88,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'fa_market_open',
                'wave': wave,
                'total_signings': len(events)
            }
        )

    def generate_and_save(
        self,
        events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int,
        wave: int = 1
    ) -> List[GeneratedHeadline]:
        """
        Generate and persist headlines for signings.

        Extends base method to track FA wave for summary generation.

        Args:
            events: List of TransactionEvents to generate headlines for
            dynasty_id: Current dynasty ID
            season: Current season
            week: Current week
            wave: Current FA wave (1-5)

        Returns:
            List of GeneratedHeadline objects that were saved
        """
        self.wave = wave
        return super().generate_and_save(events, dynasty_id, season, week)

    def generate_for_wave(
        self,
        events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int,
        wave: int = 1
    ) -> List[GeneratedHeadline]:
        """
        Generate and save headlines for a specific FA wave.

        Convenience method that delegates to generate_and_save.

        Args:
            events: List of TransactionEvents to generate headlines for
            dynasty_id: Current dynasty ID
            season: Current season
            week: Current week
            wave: Current FA wave (1-5)

        Returns:
            List of GeneratedHeadline objects that were saved
        """
        return self.generate_and_save(events, dynasty_id, season, week, wave)