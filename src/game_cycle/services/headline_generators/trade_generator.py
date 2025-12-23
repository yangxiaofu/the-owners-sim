"""
Trade Generator - Headlines for player and pick trades.

Part of Transaction-Media Architecture Refactoring.

Generates headlines for:
- Blockbuster trades (90+ OVR or multi-player deals)
- Star trades (85+ OVR)
- Notable trades (80+ OVR)
- Active trade period summary
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from game_cycle.models.transaction_event import TransactionEvent, TransactionType


@dataclass
class TradeComponents:
    """Extracted trade components for easier processing."""
    incoming: List[Dict[str, Any]]
    outgoing: List[Dict[str, Any]]
    incoming_picks: List[Dict[str, Any]]
    outgoing_picks: List[Dict[str, Any]]

    @property
    def total_players(self) -> int:
        return len(self.incoming) + len(self.outgoing)

    @property
    def total_picks(self) -> int:
        return len(self.incoming_picks) + len(self.outgoing_picks)

    @property
    def has_players(self) -> bool:
        return len(self.incoming) > 0 or len(self.outgoing) > 0

    @property
    def has_picks(self) -> bool:
        return self.total_picks > 0

    @property
    def all_player_ids(self) -> List[int]:
        return [p.get('player_id') for p in self.outgoing + self.incoming if p.get('player_id')]


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

    # OVR thresholds for headline tiers
    BLOCKBUSTER_OVR = 90
    STAR_OVR = 85
    NOTABLE_OVR = 80
    MULTI_PLAYER_THRESHOLD = 3

    # Priority ranges by tier
    BLOCKBUSTER_PRIORITY_BASE = 85
    BLOCKBUSTER_PRIORITY_MAX = 95
    STAR_PRIORITY_BASE = 75
    STAR_PRIORITY_MAX = 84
    NOTABLE_PRIORITY = 75
    SUMMARY_PRIORITY = 80

    @property
    def max_headlines(self) -> int:
        """Max 5 individual trade headlines per batch."""
        return 5

    @property
    def summary_threshold(self) -> int:
        """Generate summary if 5+ trades occurred."""
        return 5

    def _extract_trade_components(self, event: TransactionEvent) -> TradeComponents:
        """
        Extract trade components from event.

        Args:
            event: TransactionEvent containing trade data

        Returns:
            TradeComponents dataclass with all trade assets
        """
        return TradeComponents(
            incoming=getattr(event, 'incoming_players', []) or [],
            outgoing=getattr(event, 'outgoing_players', []) or [],
            incoming_picks=getattr(event, 'incoming_picks', []) or [],
            outgoing_picks=getattr(event, 'outgoing_picks', []) or [],
        )

    def _build_headline_text(
        self,
        event: TransactionEvent,
        components: TradeComponents,
        prefix: str = "",
        default_name: str = "Player"
    ) -> str:
        """
        Build headline text based on trade direction.

        Args:
            event: TransactionEvent with team names
            components: Extracted trade components
            prefix: Optional prefix (e.g., "BLOCKBUSTER: ")
            default_name: Default player name if not found

        Returns:
            Formatted headline string
        """
        if components.outgoing:
            player_name = components.outgoing[0].get('player_name', default_name)
            return f"{prefix}{event.team_name} Trade {player_name} to {event.secondary_team_name}"
        elif components.incoming:
            player_name = components.incoming[0].get('player_name', default_name)
            return f"{prefix}{event.team_name} Acquire {player_name} from {event.secondary_team_name}"
        else:
            action = "Complete Major Trade" if prefix else "Complete Trade"
            return f"{prefix}{event.team_name} and {event.secondary_team_name} {action}"

    def _build_body_text(
        self,
        event: TransactionEvent,
        components: TradeComponents,
        intro: str = "",
        include_season: bool = True
    ) -> str:
        """
        Build body text for trade headline.

        Args:
            event: TransactionEvent with team/season info
            components: Extracted trade components
            intro: Opening sentence (if empty, uses default)
            include_season: Whether to include season in closing

        Returns:
            Formatted body text string
        """
        body_parts = []

        # Opening
        if intro:
            body_parts.append(intro)
        else:
            body_parts.append(f"The {event.team_name} and {event.secondary_team_name} have agreed to a trade.")

        # Outgoing players
        if components.outgoing:
            players_str = self._format_player_list(components.outgoing)
            body_parts.append(f"The {event.team_name} send {players_str} to {event.secondary_team_name}.")

        # Incoming players
        if components.incoming:
            players_str = self._format_player_list(components.incoming)
            body_parts.append(f"In return, they receive {players_str}.")

        # Picks
        if components.has_picks:
            body_parts.append("Draft picks are also included in the deal.")

        # Closing
        if include_season:
            body_parts.append(f"This move signals both teams' intentions heading into the {event.season} season.")
        else:
            body_parts.append("This move signals both teams' intentions heading into the season.")

        return " ".join(body_parts)

    def _format_player_list(self, players: List[Dict[str, Any]], max_named: int = 2) -> str:
        """
        Format a list of players for body text.

        Args:
            players: List of player dicts with 'player_name' key
            max_named: Maximum number of players to name explicitly

        Returns:
            Formatted string like "Player A, Player B and 2 others"
        """
        if not players:
            return ""

        names = [p.get('player_name', '') for p in players[:max_named]]
        players_str = ", ".join(names)

        remaining = len(players) - max_named
        if remaining > 0:
            players_str += f" and {remaining} other{'s' if remaining > 1 else ''}"

        return players_str

    def _get_team_ids(self, event: TransactionEvent) -> List[int]:
        """Get list of team IDs involved in trade."""
        if event.secondary_team_id:
            return [event.team_id, event.secondary_team_id]
        return [event.team_id]

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
        components = self._extract_trade_components(event)

        # Blockbuster trade (90+ OVR or multi-player deal with 3+ total)
        if overall >= self.BLOCKBUSTER_OVR or components.total_players >= self.MULTI_PLAYER_THRESHOLD:
            return self._generate_blockbuster_headline(event, components)

        # Star trade (85+ OVR)
        if overall >= self.STAR_OVR:
            return self._generate_star_trade_headline(event, components)

        # Notable trade (80+ OVR)
        if overall >= self.NOTABLE_OVR:
            return self._generate_notable_trade_headline(event, components)

        # Below threshold - no headline
        return None

    def _generate_blockbuster_headline(
        self,
        event: TransactionEvent,
        components: TradeComponents
    ) -> GeneratedHeadline:
        """Generate breaking news headline for blockbuster trade."""
        headline = self._build_headline_text(event, components, prefix="BLOCKBUSTER: ", default_name="Star")

        # Build subheadline based on trade composition
        if components.total_players >= self.MULTI_PLAYER_THRESHOLD:
            subheadline = "Multi-player deal reshapes rosters for both teams"
        elif components.has_picks:
            subheadline = "Players and draft picks exchanged in blockbuster deal"
        else:
            subheadline = "Franchise-altering move sends shockwaves through league"

        body_text = self._build_body_text(
            event,
            components,
            intro=f"In a blockbuster trade, the {event.team_name} and {event.secondary_team_name} have agreed to a major deal.",
            include_season=False
        )

        # Priority based on best player OVR (85-95)
        priority = min(
            self.BLOCKBUSTER_PRIORITY_MAX,
            self.BLOCKBUSTER_PRIORITY_BASE + (event.player_overall - self.BLOCKBUSTER_OVR)
        )

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="HYPE",
            priority=priority,
            team_ids=self._get_team_ids(event),
            player_ids=components.all_player_ids,
            metadata={
                'event_type': 'trade',
                'trade_type': 'blockbuster',
                'total_players': components.total_players,
                'total_picks': components.total_picks,
                'best_overall': event.player_overall
            }
        )

    def _generate_star_trade_headline(
        self,
        event: TransactionEvent,
        components: TradeComponents
    ) -> GeneratedHeadline:
        """Generate headline for star player trade."""
        headline = self._build_headline_text(event, components, default_name="Star")

        # Build subheadline with player details
        if components.outgoing:
            primary = components.outgoing[0]
            position = primary.get('position', '')
            subheadline = f"{event.player_overall} OVR {position} heads to {event.secondary_team_name} in major deal"
        elif components.incoming:
            primary = components.incoming[0]
            position = primary.get('position', '')
            subheadline = f"{event.player_overall} OVR {position} joins {event.team_name} in trade"
        else:
            subheadline = "Draft picks exchanged between teams"

        body_text = self._build_body_text(event, components)

        # Priority for star trades (75-84)
        priority = min(
            self.STAR_PRIORITY_MAX,
            self.STAR_PRIORITY_BASE + (event.player_overall - self.STAR_OVR)
        )

        return GeneratedHeadline(
            headline_type="TRADE",
            headline=headline,
            subheadline=subheadline,
            body_text=body_text,
            sentiment="NEUTRAL",
            priority=priority,
            team_ids=self._get_team_ids(event),
            player_ids=components.all_player_ids,
            metadata={
                'event_type': 'trade',
                'trade_type': 'star',
                'overall': event.player_overall
            }
        )

    def _generate_notable_trade_headline(
        self,
        event: TransactionEvent,
        components: TradeComponents
    ) -> GeneratedHeadline:
        """Generate headline for notable trade."""
        headline = self._build_headline_text(event, components, default_name="Player")

        # Build subheadline based on trade composition
        if components.has_players and components.has_picks:
            subheadline = "Players and picks exchanged in offseason deal"
        elif components.has_players:
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
            priority=self.NOTABLE_PRIORITY,
            team_ids=self._get_team_ids(event),
            player_ids=components.all_player_ids,
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
            priority=self.SUMMARY_PRIORITY,
            team_ids=[],
            player_ids=[],
            metadata={
                'event_type': 'trade_summary',
                'trade_count': trade_count
            }
        )
