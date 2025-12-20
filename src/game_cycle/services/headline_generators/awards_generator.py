"""
Awards Generator - Headlines for NFL Honors awards ceremony.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Most Valuable Player (MVP)
- Defensive Player of the Year (DPOY)
- Offensive Player of the Year (OPOY)
- Offensive Rookie of the Year (OROY)
- Defensive Rookie of the Year (DROY)
- Coach of the Year (COTY)
- NFL Honors summary
"""

from typing import Dict, List, Optional

from constants.position_abbreviations import get_position_abbreviation
from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class AwardsGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for NFL Honors awards.

    Headline tiers:
    - MVP: 95 priority - "Player Wins NFL MVP Award"
    - DPOY/OPOY: 85 priority - "Player Named [Award] of the Year"
    - OROY/DROY: 75 priority - "Player Named [Offensive/Defensive] Rookie of the Year"
    - COTY: 70 priority - "Coach Named Coach of the Year"
    - Summary: 85 priority - "NFL Honors Night Complete: Award Winners Announced"

    Limits: 4 max individual award headlines (MVP, DPOY, OPOY, ROTY)
    """

    # Award priority ordering (highest to lowest)
    AWARD_PRIORITY_MAP = {
        "mvp": 95,
        "dpoy": 85,
        "opoy": 85,
        "oroy": 75,
        "droy": 75,
        "coty": 70,
    }

    # Award full names for headlines
    AWARD_NAMES = {
        "mvp": "NFL MVP Award",
        "dpoy": "Defensive Player of the Year",
        "opoy": "Offensive Player of the Year",
        "oroy": "Offensive Rookie of the Year",
        "droy": "Defensive Rookie of the Year",
        "coty": "Coach of the Year",
    }

    @property
    def max_headlines(self) -> int:
        """Max 4 individual award headlines per batch."""
        return 4

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 2+ awards announced."""
        return 2

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single award.

        Args:
            event: TransactionEvent for the award

        Returns:
            GeneratedHeadline appropriate to award type
        """
        award_id = event.details.get("award_id", "").lower()

        if not award_id or award_id not in self.AWARD_PRIORITY_MAP:
            return None

        if award_id == "mvp":
            return self._generate_mvp_headline(event)
        elif award_id in ["dpoy", "opoy"]:
            return self._generate_poty_headline(event, award_id)
        elif award_id in ["oroy", "droy"]:
            return self._generate_roty_headline(event, award_id)
        elif award_id == "coty":
            return self._generate_coty_headline(event)

        return None

    def _generate_mvp_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for MVP award."""
        vote_share = event.details.get("vote_share", 0.0)
        vote_pct = vote_share * 100
        position_abbr = get_position_abbreviation(event.player_position)

        if vote_share >= 0.75:
            subheadline = f"The {position_abbr} earns {vote_pct:.1f}% of votes in landslide victory"
        elif vote_share >= 0.50:
            subheadline = f"The {position_abbr} secures {vote_pct:.1f}% of votes in convincing win"
        else:
            subheadline = f"The {position_abbr} edges competition with {vote_pct:.1f}% of votes"

        stats_summary = self._get_player_stats_summary(event)
        body_text = (
            f"{event.player_name} has been named the NFL's Most Valuable Player "
            f"for the {event.season} season, capturing {vote_pct:.1f}% of the votes. "
            f"The {position_abbr} capped off an incredible campaign"
        )
        if stats_summary:
            body_text += f" {stats_summary}."
        else:
            body_text += " that saw him dominate opponents week after week."

        return GeneratedHeadline(
            headline_type="AWARD",
            headline=f"{event.player_name} Wins NFL MVP Award",
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=95,
            team_ids=[event.team_id] if event.team_id else [],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'award',
                'award_id': 'mvp',
                'vote_share': vote_share
            }
        )

    def _generate_poty_headline(
        self,
        event: TransactionEvent,
        award_id: str
    ) -> GeneratedHeadline:
        """Generate headline for DPOY/OPOY awards."""
        award_name = self.AWARD_NAMES[award_id]
        vote_share = event.details.get("vote_share", 0.0)
        position_abbr = get_position_abbreviation(event.player_position)

        if award_id == "dpoy":
            subheadline = f"The {position_abbr} terrorized offenses all season long"
        else:
            subheadline = f"The {position_abbr} was unstoppable throughout {event.season}"

        stats_summary = self._get_player_stats_summary(event)
        body_text = (
            f"{event.player_name} has been named the {award_name}. "
            f"The {position_abbr}"
        )
        if stats_summary:
            body_text += f" {stats_summary}."
        else:
            body_text += " had a dominant season, establishing himself as the league's best."

        return GeneratedHeadline(
            headline_type="AWARD",
            headline=f"{event.player_name} Named {award_name}",
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=85,
            team_ids=[event.team_id] if event.team_id else [],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'award',
                'award_id': award_id,
                'vote_share': vote_share
            }
        )

    def _generate_roty_headline(
        self,
        event: TransactionEvent,
        award_id: str
    ) -> GeneratedHeadline:
        """Generate headline for OROY/DROY awards."""
        award_name = self.AWARD_NAMES[award_id]
        position_abbr = get_position_abbreviation(event.player_position)

        if award_id == "droy":
            subheadline = f"The {position_abbr} made an immediate impact on defense"
        else:
            subheadline = f"The {position_abbr} had an immediate impact in his first NFL season"

        stats_summary = self._get_player_stats_summary(event)
        body_text = (
            f"{event.player_name} has been named the {award_name}. "
            f"The {position_abbr}"
        )
        if stats_summary:
            body_text += f" {stats_summary}, showing why he was worth the draft pick."
        else:
            body_text += " made an immediate impact, showing why he was worth the draft pick."

        return GeneratedHeadline(
            headline_type="AWARD",
            headline=f"{event.player_name} Named {award_name}",
            subheadline=subheadline,
            body_text=body_text,
            sentiment="POSITIVE",
            priority=75,
            team_ids=[event.team_id] if event.team_id else [],
            player_ids=[event.player_id] if event.player_id else [],
            metadata={
                'event_type': 'award',
                'award_id': award_id
            }
        )

    def _generate_coty_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for Coach of the Year award."""
        coach_name = event.details.get("coach_name", "Unknown Coach")
        team_record = event.details.get("team_record", "")

        if team_record:
            subheadline = f"Led {event.team_name} to {team_record} record in remarkable season"
        else:
            subheadline = f"Led {event.team_name} to remarkable turnaround"

        body_text = (
            f"{coach_name} has been named the NFL's Coach of the Year. "
            f"The {event.team_name} head coach"
        )
        if team_record:
            body_text += f" led his team to a {team_record} record, exceeding all expectations."
        else:
            body_text += " orchestrated a remarkable season, earning recognition from his peers."

        return GeneratedHeadline(
            headline_type="AWARD",
            headline=f"{coach_name} Named Coach of the Year",
            subheadline=subheadline,
            body_text=body_text,
            sentiment="POSITIVE",
            priority=70,
            team_ids=[event.team_id] if event.team_id else [],
            player_ids=[],
            metadata={
                'event_type': 'award',
                'award_id': 'coty',
                'coach_name': coach_name
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """Generate NFL Honors summary headline."""
        if not events:
            return None

        season = events[0].season if events else 2024

        award_winners = []
        for event in events[:6]:
            award_id = event.details.get("award_id", "").lower()
            if award_id == "coty":
                coach_name = event.details.get("coach_name", "Unknown")
                award_winners.append(f"{coach_name} (Coach of the Year)")
            elif event.player_name:
                award_abbr = award_id.upper()
                award_winners.append(f"{event.player_name} ({award_abbr})")

        winners_text = ", ".join(award_winners) if award_winners else "league's best players"

        return GeneratedHeadline(
            headline_type="AWARD",
            headline=f"NFL Honors: {season} Award Winners Announced",
            subheadline=f"{len(events)} major awards presented at star-studded ceremony",
            body_text=(
                f"The NFL's best were honored at the annual NFL Honors ceremony. "
                f"Winners included: {winners_text}."
            ),
            sentiment="POSITIVE",
            priority=85,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'honors_summary',
                'total_awards': len(events),
                'season': season
            }
        )

    def _get_player_stats_summary(self, event: TransactionEvent) -> str:
        """Build a stats summary string for the award winner."""
        details = event.details
        position = event.player_position

        if position == "QB":
            passing_yards = details.get("passing_yards")
            passing_tds = details.get("passing_tds")
            if passing_yards and passing_tds:
                return f"threw for {passing_yards:,} yards and {passing_tds} touchdowns"

        elif position == "RB":
            rushing_yards = details.get("rushing_yards")
            rushing_tds = details.get("rushing_tds")
            if rushing_yards and rushing_tds:
                return f"rushed for {rushing_yards:,} yards and {rushing_tds} touchdowns"

        elif position == "WR":
            receiving_yards = details.get("receiving_yards")
            receptions = details.get("receptions")
            if receiving_yards and receptions:
                return f"caught {receptions} passes for {receiving_yards:,} yards"

        elif position in ["LB", "MLB", "LOLB", "ROLB", "DE", "DT", "EDGE"]:
            tackles = details.get("total_tackles")
            sacks = details.get("sacks")
            if sacks and sacks >= 10:
                return f"recorded {sacks} sacks"
            elif tackles and tackles >= 100:
                return f"tallied {tackles} total tackles"

        elif position in ["CB", "FS", "SS"]:
            interceptions = details.get("interceptions")
            if interceptions and interceptions >= 5:
                return f"intercepted {interceptions} passes"

        return ""