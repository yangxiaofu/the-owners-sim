"""
Draft Generator - Headlines for NFL Draft picks and draft day.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- First overall pick (always headline)
- Top 5 first round picks
- Notable draft picks (high potential or team need)
- Draft day completion summary
"""

from typing import List, Optional

from constants.position_abbreviations import get_position_abbreviation
from src.utils.player_field_extractors import extract_overall_rating
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class DraftGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for NFL Draft picks.

    Headline tiers:
    - #1 Overall: Always headline - "Team Select Player with No. 1 Pick"
    - Top 5 Picks: First round selections 2-5 - "Team Land Player at No. X"
    - Notable Picks: High potential (75+ OVR) or first round (top 10)
    - Summary: "NFL Draft Complete: 224 Selections Made"

    Limits: 1 (#1 overall) + 2 (top 5) = 3 max individual headlines
    """

    @property
    def max_headlines(self) -> int:
        """Max 3 individual draft headlines per batch."""
        return 3

    @property
    def summary_threshold(self) -> int:
        """Generate summary if any picks occurred."""
        return 1  # Always generate summary for draft

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single draft pick.

        Args:
            event: TransactionEvent for the draft pick

        Returns:
            GeneratedHeadline appropriate to pick significance
        """
        # Get overall pick number from details
        draft_pick = getattr(event, 'draft_pick', 0) or 0
        draft_round = getattr(event, 'draft_round', 1) or 1
        overall_pick = event.details.get("overall_pick", draft_pick)

        # #1 Overall pick (always headline)
        if overall_pick == 1:
            return self._generate_first_overall_headline(event, overall_pick)

        # Top 5 first round picks
        if draft_round == 1 and overall_pick <= 5:
            return self._generate_top_five_headline(event, overall_pick)

        # Notable picks (high potential or top 10)
        if event.player_overall >= 75 or (draft_round == 1 and overall_pick <= 10):
            return self._generate_notable_pick_headline(event, overall_pick, draft_round)

        # Below threshold - no headline
        return None

    def _generate_first_overall_headline(
        self,
        event: TransactionEvent,
        overall_pick: int
    ) -> GeneratedHeadline:
        """Generate headline for first overall pick."""
        return GeneratedHeadline(
            headline_type="DRAFT_PICK",
            headline=f"{event.team_name} Select {event.player_name} with No. 1 Pick",
            subheadline=f"The {get_position_abbreviation(event.player_position)} ({event.player_overall} OVR) is the {event.season} NFL Draft's top selection",
            body_text=(
                f"{event.team_name} made {event.player_name} the first overall selection "
                f"in the {event.season} NFL Draft. The {get_position_abbreviation(event.player_position)} is expected "
                f"to make an immediate impact for the franchise."
            ),
            sentiment="HYPE",
            priority=90,
            team_ids=[event.team_id],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'draft_pick',
                'pick_number': overall_pick,
                'round': getattr(event, 'draft_round', 1),
                'overall': event.player_overall
            }
        )

    def _generate_top_five_headline(
        self,
        event: TransactionEvent,
        overall_pick: int
    ) -> GeneratedHeadline:
        """Generate headline for top 5 first round pick."""
        priority = 80 - overall_pick  # 79 for #2, 78 for #3, etc.

        return GeneratedHeadline(
            headline_type="DRAFT_PICK",
            headline=f"{event.team_name} Land {event.player_name} at No. {overall_pick}",
            subheadline=f"The {get_position_abbreviation(event.player_position)} fills a key need for {event.team_name}",
            body_text=(
                f"With the {self._get_ordinal(overall_pick)} pick, {event.team_name} selected "
                f"{event.player_name}. The {get_position_abbreviation(event.player_position)} was considered a top prospect "
                f"and is expected to contribute immediately."
            ),
            sentiment="POSITIVE",
            priority=priority,
            team_ids=[event.team_id],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'draft_pick',
                'pick_number': overall_pick,
                'round': getattr(event, 'draft_round', 1),
                'overall': event.player_overall
            }
        )

    def _generate_notable_pick_headline(
        self,
        event: TransactionEvent,
        overall_pick: int,
        draft_round: int
    ) -> GeneratedHeadline:
        """Generate headline for notable draft pick."""
        tier = self._get_player_tier(event.player_overall)
        is_high_potential = event.player_overall >= 75

        position_abbr = get_position_abbreviation(event.player_position)
        if is_high_potential:
            headline = f"{event.team_name} Select {tier.capitalize()} {position_abbr} {event.player_name}"
            subheadline = f"{event.player_overall} OVR prospect chosen with pick No. {overall_pick}"
        else:
            headline = f"{event.team_name} Draft {event.player_name} in Round {draft_round}"
            subheadline = f"{position_abbr} selected with pick No. {overall_pick}"

        return GeneratedHeadline(
            headline_type="DRAFT_PICK",
            headline=headline,
            subheadline=subheadline,
            body_text=(
                f"The {event.team_name} used the {self._get_ordinal(overall_pick)} overall pick "
                f"to select {event.player_name}, a {position_abbr} out of college. "
                f"The pick addresses a position of need for the team."
            ),
            sentiment="POSITIVE",
            priority=65,
            team_ids=[event.team_id],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'draft_pick',
                'pick_number': overall_pick,
                'round': draft_round,
                'overall': event.player_overall
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate draft completion summary headline.

        Args:
            events: All draft pick events

        Returns:
            Summary headline for draft completion
        """
        if not events:
            return None

        season = events[0].season if events else 2024
        total_picks = len(events)

        return GeneratedHeadline(
            headline_type="DRAFT_PICK",
            headline=f"{season} NFL Draft Complete: {total_picks} Selections Made",
            subheadline="All 32 teams fill roster needs over seven rounds",
            body_text=(
                f"The {season} NFL Draft has concluded with all {total_picks} picks now on the books. "
                f"Teams will now shift focus to rookie minicamps and offseason workouts as they "
                f"integrate their new draft classes into their rosters."
            ),
            sentiment="NEUTRAL",
            priority=85,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'draft_complete',
                'total_picks': total_picks,
                'season': season
            }
        )

    def _get_ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 10 <= n % 100 <= 20:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return f"{n}{suffix}"

    def generate_for_draft_completion(
        self,
        events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[GeneratedHeadline]:
        """
        Generate headlines for completed draft.

        Same as generate_and_save() but always includes summary.
        """
        return self.generate_and_save(events, dynasty_id, season, week)