"""
Trade Generator - Headlines for player and pick trades.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Blockbuster trades (90+ OVR or multi-player deals)
- Star trades (85+ OVR)
- Notable trades (80+ OVR)
- Active trade period summary
"""

from typing import List, Optional

from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


class TradeGenerator(BaseHeadlineGenerator):
    """
    Generates headlines for trades (players and/or picks).

    Headline tiers:
    - Blockbuster: 90+ OVR or multi-player (3+ total) - "BLOCKBUSTER: Team Trade Player to Team"
    - Star trade: 85+ OVR - "Team Acquire Player from Team in Trade"
    - Notable trade: 80+ OVR - "Team Trade Player to Team"
    - Summary: "Active Trade Period: X Deals Completed"

    Limits: 5 max individual headlines
    """

    @property
    def max_headlines(self) -> int:
        """Max 5 individual trade headlines per batch."""
        return 5

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 5+ trades occurred."""
        return 5

    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single trade.

        Args:
            event: TransactionEvent for the trade

        Returns:
            GeneratedHeadline appropriate to trade significance
        """
        overall = event.player_overall
        incoming = getattr(event, 'incoming_players', []) or []
        outgoing = getattr(event, 'outgoing_players', []) or []
        total_players = len(incoming) + len(outgoing)

        # Blockbuster trade (90+ OVR or multi-player deal with 3+ total)
        if overall >= 90 or total_players >= 3:
            return self._generate_blockbuster_headline(event)

        # Star trade (85+ OVR)
        if overall >= 85:
            return self._generate_star_trade_headline(event)

        # Notable trade (80+ OVR)
        if overall >= 80:
            return self._generate_notable_trade_headline(event)

        # Below threshold - no headline
        return None

    def _generate_blockbuster_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate breaking news headline for blockbuster trade."""
        incoming = getattr(event, 'incoming_players', []) or []
        outgoing = getattr(event, 'outgoing_players', []) or []
        incoming_picks = getattr(event, 'incoming_picks', []) or []
        outgoing_picks = getattr(event, 'outgoing_picks', []) or []

        # Determine primary direction based on player movement
        if outgoing:
            primary_player = outgoing[0]
            headline = f"BLOCKBUSTER: {event.team_name} Trade {primary_player.get('player_name', 'Star')} to {event.secondary_team_name}"
        elif incoming:
            primary_player = incoming[0]
            headline = f"BLOCKBUSTER: {event.team_name} Acquire {primary_player.get('player_name', 'Star')} from {event.secondary_team_name}"
        else:
            headline = f"BLOCKBUSTER: {event.team_name} and {event.secondary_team_name} Complete Major Trade"

        # Build subheadline
        total_players = len(incoming) + len(outgoing)
        total_picks = len(incoming_picks) + len(outgoing_picks)

        if total_players >= 3:
            subheadline = "Multi-player deal reshapes rosters for both teams"
        elif total_picks > 0:
            subheadline = "Players and draft picks exchanged in blockbuster deal"
        else:
            subheadline = "Franchise-altering move sends shockwaves through league"

        # Build body text
        body_parts = [f"In a blockbuster trade, the {event.team_name} and {event.secondary_team_name} have agreed to a major deal."]

        if outgoing:
            players_str = ", ".join([p.get('player_name', '') for p in outgoing[:2]])
            if len(outgoing) > 2:
                players_str += f" and {len(outgoing) - 2} other{'s' if len(outgoing) > 3 else ''}"
            body_parts.append(f"The {event.team_name} send {players_str} to {event.secondary_team_name}.")

        if incoming:
            players_str = ", ".join([p.get('player_name', '') for p in incoming[:2]])
            if len(incoming) > 2:
                players_str += f" and {len(incoming) - 2} other{'s' if len(incoming) > 3 else ''}"
            body_parts.append(f"In return, they receive {players_str}.")

        if total_picks > 0:
            body_parts.append("Draft picks are also included in the deal.")

        body_parts.append("This move signals both teams' intentions heading into the season.")

        body_text = " ".join(body_parts)

        # Priority based on best player OVR (90-95)
        priority = min(95, 85 + (event.player_overall - 90))

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=priority,
            team_ids=[event.team_id, event.secondary_team_id] if event.secondary_team_id else [event.team_id],
            player_ids=[p.get('player_id') for p in outgoing + incoming if p.get('player_id')],
            metadata={
                'event_type': 'trade',
                'trade_type': 'blockbuster',
                'total_players': total_players,
                'total_picks': total_picks,
                'best_overall': event.player_overall
            }
        )

    def _generate_star_trade_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for star player trade."""
        incoming = getattr(event, 'incoming_players', []) or []
        outgoing = getattr(event, 'outgoing_players', []) or []
        incoming_picks = getattr(event, 'incoming_picks', []) or []
        outgoing_picks = getattr(event, 'outgoing_picks', []) or []

        # Determine primary direction
        if outgoing:
            primary_player = outgoing[0]
            player_name = primary_player.get('player_name', 'Star')
            position = primary_player.get('position', '')
            headline = f"{event.team_name} Trade {player_name} to {event.secondary_team_name}"
            subheadline = f"{event.player_overall} OVR {position} heads to {event.secondary_team_name} in major deal"
        elif incoming:
            primary_player = incoming[0]
            player_name = primary_player.get('player_name', 'Star')
            position = primary_player.get('position', '')
            headline = f"{event.team_name} Acquire {player_name} from {event.secondary_team_name}"
            subheadline = f"{event.player_overall} OVR {position} joins {event.team_name} in trade"
        else:
            headline = f"{event.team_name} and {event.secondary_team_name} Complete Trade"
            subheadline = "Draft picks exchanged between teams"

        # Build body text
        body_parts = [f"The {event.team_name} and {event.secondary_team_name} have agreed to a trade."]

        if outgoing:
            players_str = ", ".join([p.get('player_name', '') for p in outgoing])
            body_parts.append(f"The {event.team_name} send {players_str} to {event.secondary_team_name}.")

        if incoming:
            return_str = ", ".join([p.get('player_name', '') for p in incoming])
            body_parts.append(f"In return, the {event.team_name} receive {return_str}.")

        if incoming_picks or outgoing_picks:
            body_parts.append("Draft picks are also part of the deal.")

        body_parts.append(f"This move signals both teams' intentions heading into the {event.season} season.")

        body_text = " ".join(body_parts)

        # Priority for star trades (80-84)
        priority = min(84, 75 + (event.player_overall - 85))

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="NEUTRAL",
            priority=priority,
            team_ids=[event.team_id, event.secondary_team_id] if event.secondary_team_id else [event.team_id],
            player_ids=[p.get('player_id') for p in outgoing + incoming if p.get('player_id')],
            metadata={
                'event_type': 'trade',
                'trade_type': 'star',
                'overall': event.player_overall
            }
        )

    def _generate_notable_trade_headline(
        self,
        event: TransactionEvent
    ) -> GeneratedHeadline:
        """Generate headline for notable trade."""
        incoming = getattr(event, 'incoming_players', []) or []
        outgoing = getattr(event, 'outgoing_players', []) or []
        incoming_picks = getattr(event, 'incoming_picks', []) or []
        outgoing_picks = getattr(event, 'outgoing_picks', []) or []

        has_players = len(incoming) > 0 or len(outgoing) > 0

        if outgoing:
            primary_player = outgoing[0]
            player_name = primary_player.get('player_name', 'Player')
            headline = f"{event.team_name} Trade {player_name} to {event.secondary_team_name}"
        elif incoming:
            primary_player = incoming[0]
            player_name = primary_player.get('player_name', 'Player')
            headline = f"{event.team_name} Acquire {player_name} from {event.secondary_team_name}"
        else:
            headline = f"{event.team_name} and {event.secondary_team_name} Complete Trade"

        # Build subheadline
        if has_players and (incoming_picks or outgoing_picks):
            subheadline = "Players and picks exchanged in offseason deal"
        elif has_players:
            subheadline = "Trade reshapes rosters for both teams"
        else:
            subheadline = "Draft picks exchanged between teams"

        body_text = (
            f"{event.team_name} and {event.secondary_team_name} have agreed to a trade. "
            f"This move signals both teams' intentions heading into the {event.season} season."
        )

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="NEUTRAL",
            priority=75,
            team_ids=[event.team_id, event.secondary_team_id] if event.secondary_team_id else [event.team_id],
            player_ids=[p.get('player_id') for p in outgoing + incoming if p.get('player_id')],
            metadata={
                'event_type': 'trade',
                'trade_type': 'notable'
            }
        )

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate summary headline for active trade period.

        Args:
            events: All trade events

        Returns:
            Summary headline for trade period
        """
        if not events:
            return None

        trade_count = len(events)
        season = events[0].season if events else 2024

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=f"Active Trade Period: {trade_count} Deals Completed",
            subheadline="Teams reshape rosters ahead of training camp",
            body_text=(
                f"The offseason trade market has been busy with {trade_count} trades completed league-wide. "
                f"Teams continue to position themselves for the upcoming {season} season with strategic roster moves."
            ),
            sentiment="NEUTRAL",
            priority=80,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'trade_summary',
                'trade_count': trade_count
            }
        )