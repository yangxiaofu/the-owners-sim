"""
Roster Cut Generator - Headlines for roster cuts and cutdown day.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Star surprise cuts (85+ OVR)
- Veteran cap casualties (80+ OVR or $5M+ savings)
- Notable roster cuts (75+ OVR)
- Cutdown day summary
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class RosterCutGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for roster cuts.

    Headline tiers:
    - Star surprise: 85+ OVR - "BREAKING: Team Release Player"
    - Veteran/Cap casualty: 80+ OVR or $5M+ savings - "Team Cut Player to Create Cap Space"
    - Notable cuts: 75+ OVR - "Player Among Team Roster Casualties"
    - Summary: "Cutdown Day Complete: All 32 Teams Set 53-Man Rosters"

    Limits: 2 star + 2 veteran + 3 notable = 7 max individual headlines
    """

    @property
    def max_headlines(self) -> int:
        """Max 7 individual cut headlines per batch."""
        return 7

    @property
    def summary_threshold(self) -> int:
        """Generate summary if any cuts occurred."""
        return 1  # Always generate summary for roster cuts

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single roster cut.

        Args:
            event: TransactionEvent for the cut

        Returns:
            GeneratedHeadline appropriate to cut significance
        """
        overall = event.player_overall
        cap_savings = event.financial_impact
        cap_savings_m = cap_savings / 1_000_000

        # Star surprise cut (85+ OVR)
        if event.is_surprising or overall >= 85:
            return self._generate_star_cut_headline(event, cap_savings_m)

        # Veteran / cap casualty (80+ OVR or $5M+ savings)
        if overall >= 80 or cap_savings >= 5_000_000:
            return self._generate_veteran_cut_headline(event, cap_savings_m)

        # Notable cut (75+ OVR)
        if overall >= 75:
            return self._generate_notable_cut_headline(event)

        # Below threshold - no headline
        return None

    def _generate_star_cut_headline(
        self,
        event: TransactionEvent,
        cap_savings_m: float
    ) -> GeneratedHeadline:
        """Generate breaking news headline for star cut."""
        priority = min(88, 80 + (event.player_overall - 85))
        position_abbr = get_position_abbreviation(event.player_position)

        return GeneratedHeadline(
            headline_type="ROSTER_CUT",
            headline=f"BREAKING: {event.team_name} Release {event.player_name}",
            subheadline=f"Shocking move sends {event.player_overall} OVR {position_abbr} to free agency",
            body_text=(
                f"In a surprising move, the {event.team_name} have released "
                f"{event.player_name}, a {event.player_overall}-rated {position_abbr}. "
                f"The move clears ${cap_savings_m:.1f}M in cap space as the team "
                f"finalizes their roster."
            ),
            sentiment="CRITICAL",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'roster_cut',
                'overall': event.player_overall,
                'cap_savings': event.financial_impact,
                'is_surprise': True
            }
        )

    def _generate_veteran_cut_headline(
        self,
        event: TransactionEvent,
        cap_savings_m: float
    ) -> GeneratedHeadline:
        """Generate headline for veteran or cap casualty cut."""
        position_abbr = get_position_abbreviation(event.player_position)
        if cap_savings_m >= 5:
            headline = f"{event.team_name} Cut {event.player_name} to Create Cap Space"
            subheadline = f"${cap_savings_m:.1f}M in cap relief as team reshapes roster"
        else:
            headline = f"{event.team_name} Part Ways with {event.player_name}"
            subheadline = f"Veteran {position_abbr} released as team trims roster"

        return GeneratedHeadline(
            headline_type="ROSTER_CUT",
            headline=headline,
            subheadline=subheadline,
            body_text=(
                f"The {event.team_name} have released {event.player_name} "
                f"({position_abbr}), saving ${cap_savings_m:.1f}M against the salary cap. "
                f"The move comes as teams finalize their 53-man rosters ahead of the regular season."
            ),
            sentiment="NEGATIVE",
            priority=70,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={
                'event_type': 'roster_cut',
                'cap_savings': event.financial_impact
            }
        )

    def _generate_notable_cut_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for notable roster cut."""
        position_abbr = get_position_abbreviation(event.player_position)
        return GeneratedHeadline(
            headline_type="ROSTER_CUT",
            headline=f"{event.player_name} Among {event.team_name} Roster Casualties",
            subheadline=f"{position_abbr} released as team finalizes 53-man roster",
            body_text=(
                f"{event.player_name} has been released by the {event.team_name} "
                f"as part of roster cutdowns. The {position_abbr} will now "
                f"look for opportunities elsewhere in the league."
            ),
            sentiment="NEUTRAL",
            priority=60,
            team_ids=[event.team_id],
            player_ids=[event.player_id],
            metadata={'event_type': 'roster_cut'}
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate cutdown day summary headline.

        Args:
            events: All cut events

        Returns:
            Summary headline for cutdown day
        """
        if not events:
            return None

        # Get season from first event
        season = events[0].season if events else 2024

        return GeneratedHeadline(
            headline_type="ROSTER_CUT",
            headline="Cutdown Day Complete: All 32 Teams Set 53-Man Rosters",
            subheadline=f"Over {len(events)} players released league-wide as teams finalize rosters",
            body_text=(
                f"Cutdown day has concluded with all 32 teams finalizing their 53-man rosters "
                f"for the {season} season. Over {len(events)} players were released league-wide, "
                f"with many now available via waivers or free agency."
            ),
            sentiment="NEUTRAL",
            priority=75,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'cutdown_summary',
                'total_cuts': len(events)
            }
        )

    def generate_for_final_cuts(
        self,
        events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[GeneratedHeadline]:
        """
        Generate headlines for final roster cutdown.

        Same as generate_and_save() but always includes summary.

        Args:
            events: List of cut TransactionEvents
            dynasty_id: Current dynasty ID
            season: Current season
            week: Current week

        Returns:
            List of generated headlines including summary
        """
        # Use standard generation (summary_threshold=1 ensures summary is generated)
        return self.generate_and_save(events, dynasty_id, season, week)