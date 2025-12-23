"""
HOF Headline Generator - Generates headlines for Hall of Fame inductions.

Part of HOF Milestone (T7 - OFFSEASON_HONORS Integration).

Handles:
- First-ballot induction headlines (highest priority)
- Standard induction headlines
- Class summary headline
"""

from typing import List, Optional

from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent


class HOFGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for Hall of Fame inductions.

    First-ballot inductees get special headlines with higher priority.
    Creates a class summary if multiple inductees.
    """

    @property
    def max_headlines(self) -> int:
        """Maximum 5 headlines (one per inductee max)."""
        return 5

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 2+ inductees."""
        return 2

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for HOF induction.

        Args:
            event: TransactionEvent for HOF induction

        Returns:
            GeneratedHeadline for the induction
        """
        details = event.details or {}
        is_first_ballot = details.get('is_first_ballot', False)
        vote_percentage = details.get('vote_percentage', 0.0)
        years_on_ballot = details.get('years_on_ballot', 1)
        achievements = details.get('achievements', [])

        if is_first_ballot:
            return self._generate_first_ballot_headline(event, vote_percentage, achievements)
        else:
            return self._generate_standard_headline(event, vote_percentage, years_on_ballot, achievements)

    def _generate_first_ballot_headline(
        self,
        event: TransactionEvent,
        vote_percentage: float,
        achievements: List[str]
    ) -> GeneratedHeadline:
        """
        Generate headline for first-ballot HOF inductee.

        First-ballot inductees get special treatment with higher priority.
        """
        player_name = event.player_name
        position = event.player_position
        team_name = event.team_name or "the NFL"
        vote_pct_display = f"{vote_percentage * 100:.1f}%"

        # Build achievement string
        achievement_str = ""
        if achievements:
            top_achievements = achievements[:3]
            achievement_str = ", ".join(top_achievements)

        headline = f"{player_name} Elected to Hall of Fame on First Ballot"
        subheadline = f"Legendary {position} joins Canton's elite class"

        body_text = (
            f"{player_name} has been inducted into the Pro Football Hall of Fame "
            f"in their first year of eligibility, receiving {vote_pct_display} of votes. "
            f"The former {team_name} {position} was a dominant force throughout their career"
        )
        if achievement_str:
            body_text += f", earning honors including {achievement_str}."
        else:
            body_text += "."

        body_text += (
            f" Canton welcomes another legend as {player_name} "
            f"takes their place among football's immortals."
        )

        return GeneratedHeadline(
            headline_type="HALL_OF_FAME",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=92,  # Very high priority for first-ballot
            team_ids=event.team_ids if event.team_ids else [],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                "event_type": "hof_induction",
                "first_ballot": True,
                "vote_percentage": vote_percentage,
            }
        )

    def _generate_standard_headline(
        self,
        event: TransactionEvent,
        vote_percentage: float,
        years_on_ballot: int,
        achievements: List[str]
    ) -> GeneratedHeadline:
        """
        Generate headline for non-first-ballot HOF inductee.
        """
        player_name = event.player_name
        position = event.player_position
        team_name = event.team_name or "the NFL"
        vote_pct_display = f"{vote_percentage * 100:.1f}%"

        # Different headline based on wait time
        if years_on_ballot <= 3:
            headline = f"{player_name} Enshrined in Pro Football Hall of Fame"
            subheadline = f"{position} earns Canton call after short wait"
        elif years_on_ballot <= 10:
            headline = f"{player_name} Finally Gets the Call to Canton"
            subheadline = f"Patience rewarded as {position} enters Hall of Fame"
        else:
            headline = f"Long Wait Ends: {player_name} Enters Hall of Fame"
            subheadline = f"After {years_on_ballot} years, {position} achieves ultimate honor"

        body_text = (
            f"After {years_on_ballot} years on the ballot, {player_name} has been "
            f"inducted into the Pro Football Hall of Fame with {vote_pct_display} of votes. "
            f"The former {team_name} {position} can finally call themselves a Hall of Famer."
        )

        if achievements:
            body_text += f" Career highlights include: {', '.join(achievements[:3])}."

        return GeneratedHeadline(
            headline_type="HALL_OF_FAME",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=88,  # High priority but below first-ballot
            team_ids=event.team_ids if event.team_ids else [],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                "event_type": "hof_induction",
                "first_ballot": False,
                "years_on_ballot": years_on_ballot,
                "vote_percentage": vote_percentage,
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate summary headline for HOF class.

        Only generated if 2+ inductees.
        """
        if len(events) < self.summary_threshold:
            return None

        # Count first-ballot inductees
        first_ballot_count = sum(
            1 for e in events
            if e.details and e.details.get('is_first_ballot', False)
        )

        # Get inductee names
        names = [e.player_name for e in events if e.player_name]

        if len(names) == 2:
            names_str = f"{names[0]} and {names[1]}"
        else:
            names_str = f"{', '.join(names[:-1])}, and {names[-1]}"

        headline = f"Hall of Fame Class of {events[0].details.get('induction_season', 2030)} Announced"

        if first_ballot_count > 0:
            subheadline = f"{len(events)} inducted, {first_ballot_count} on first ballot"
        else:
            subheadline = f"{len(events)} legends earn football's highest honor"

        body_text = (
            f"The Pro Football Hall of Fame welcomes its newest class: {names_str}. "
        )
        if first_ballot_count > 0:
            body_text += f"{first_ballot_count} inductee(s) earned first-ballot honors. "

        body_text += (
            f"Canton adds {len(events)} new bronze busts as these legends "
            f"take their rightful place in football history."
        )

        return GeneratedHeadline(
            headline_type="HALL_OF_FAME_CLASS",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=90,  # High priority for class summary
            team_ids=[],  # Multiple teams
            player_ids=[e.player_id for e in events if e.player_id],
            metadata={
                "event_type": "hof_class_summary",
                "inductee_count": len(events),
                "first_ballot_count": first_ballot_count,
            }
        )
