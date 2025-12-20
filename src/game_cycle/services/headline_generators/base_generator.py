"""
Base Headline Generator - Abstract base class for type-specific generators.

Part of Transaction-Media Architecture Refactoring.

Handles common operations:
- Database connection management
- MediaCoverageAPI initialization
- Headline persistence
- Event filtering by prominence
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.media_coverage_api import MediaCoverageAPI
from game_cycle.models.transaction_event import TransactionEvent
from game_cycle.services.prominence_calculator import ProminenceCalculator


@dataclass
class GeneratedHeadline:
    """
    Output from headline generator.

    Contains all data needed for persistence and display.
    """

    headline_type: str
    """Type of headline (ROSTER_CUT, SIGNING, TRADE, etc.)."""

    headline: str
    """Main headline text."""

    subheadline: str
    """Supporting subheadline text."""

    body_text: str
    """Full article body text."""

    sentiment: str
    """Sentiment: POSITIVE, NEGATIVE, NEUTRAL, HYPE, CRITICAL."""

    priority: int
    """Display priority (higher = more prominent, 0-95)."""

    team_ids: List[int] = field(default_factory=list)
    """Team IDs involved in this headline."""

    player_ids: List[Optional[int]] = field(default_factory=list)
    """Player IDs involved in this headline."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata for logging/debugging."""

    def to_headline_data(self) -> Dict[str, Any]:
        """
        Convert to dict format expected by MediaCoverageAPI.save_headline().

        Returns:
            Dict matching headline_data schema
        """
        return {
            'headline_type': self.headline_type,
            'headline': self.headline,
            'subheadline': self.subheadline,
            'body_text': self.body_text,
            'sentiment': self.sentiment,
            'priority': self.priority,
            'team_ids': self.team_ids,
            'player_ids': self.player_ids,
            'game_id': None,
            'metadata': self.metadata,
        }


class BaseHeadlineGenerator(ABC):
    """
    Base class for type-specific headline generators.

    Handles common operations:
    - Database connection management
    - MediaCoverageAPI initialization
    - Headline persistence
    - Event filtering

    Subclasses must implement:
    - max_headlines property
    - _generate_headline() method
    - Optionally: _generate_summary() method

    Usage:
        generator = RosterCutGenerator(db_path)
        headlines = generator.generate_and_save(events, dynasty_id, season, week)
    """

    def __init__(
        self,
        db_path: str,
        prominence_calc: Optional[ProminenceCalculator] = None
    ):
        """
        Initialize generator.

        Args:
            db_path: Path to game_cycle.db
            prominence_calc: Optional ProminenceCalculator (creates new if not provided)
        """
        self.db_path = db_path
        self.prominence_calc = prominence_calc or ProminenceCalculator()

    def generate_and_save(
        self,
        events: List[TransactionEvent],
        dynasty_id: str,
        season: int,
        week: int
    ) -> List[GeneratedHeadline]:
        """
        Generate and persist headlines for a list of events.

        Handles database connection lifecycle automatically.
        Filters to headline-worthy events and respects max_headlines limit.

        Args:
            events: List of TransactionEvents to generate headlines for
            dynasty_id: Current dynasty ID
            season: Current season
            week: Current week

        Returns:
            List of GeneratedHeadline objects that were saved
        """
        if not events:
            return []

        headlines: List[GeneratedHeadline] = []
        gc_db = GameCycleDatabase(self.db_path)

        try:
            media_api = MediaCoverageAPI(gc_db)

            # Filter to headline-worthy events
            worthy_events = [e for e in events if e.is_headline_worthy]

            # Sort by priority (highest first)
            worthy_events.sort(key=lambda e: e.suggested_priority, reverse=True)

            # Generate headlines for top events (up to max_headlines)
            for event in worthy_events[:self.max_headlines]:
                headline = self._generate_headline(event)
                if headline:
                    self._save_headline(media_api, dynasty_id, season, week, headline)
                    headlines.append(headline)

            # Generate summary if applicable
            if len(events) >= self.summary_threshold:
                summary = self._generate_summary(events)
                if summary:
                    self._save_headline(media_api, dynasty_id, season, week, summary)
                    headlines.append(summary)

        finally:
            gc_db.close()

        return headlines

    def _save_headline(
        self,
        media_api: MediaCoverageAPI,
        dynasty_id: str,
        season: int,
        week: int,
        headline: GeneratedHeadline
    ) -> None:
        """
        Persist headline to database.

        Args:
            media_api: MediaCoverageAPI instance
            dynasty_id: Dynasty identifier
            season: Season year
            week: Week number
            headline: GeneratedHeadline to save
        """
        media_api.save_headline(
            dynasty_id=dynasty_id,
            season=season,
            week=week,
            headline_data=headline.to_headline_data()
        )

    @property
    @abstractmethod
    def max_headlines(self) -> int:
        """
        Maximum individual headlines to generate per batch.

        Override in subclass to set appropriate limit.
        """
        pass

    @property
    def summary_threshold(self) -> int:
        """
        Minimum events to trigger summary headline.

        Override in subclass if different from default.
        Default: 5 events
        """
        return 5

    @abstractmethod
    def _generate_headline(
        self,
        event: TransactionEvent
    ) -> Optional[GeneratedHeadline]:
        """
        Generate headline for a single event.

        Args:
            event: TransactionEvent to generate headline for

        Returns:
            GeneratedHeadline if generated, None to skip
        """
        pass

    def _generate_summary(
        self,
        events: List[TransactionEvent]
    ) -> Optional[GeneratedHeadline]:
        """
        Generate summary headline for multiple events.

        Override in subclass to provide summary headline.
        Default: No summary.

        Args:
            events: All events (not just headline-worthy ones)

        Returns:
            GeneratedHeadline for summary, or None to skip
        """
        return None

    def _format_cap_amount(self, amount: int) -> str:
        """
        Format dollar amount for headlines.

        Args:
            amount: Amount in dollars

        Returns:
            Formatted string (e.g., "$15.2M", "$850K")
        """
        if amount >= 1_000_000:
            return f"${amount / 1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount / 1_000:.0f}K"
        else:
            return f"${amount:,}"

    def _get_player_tier(self, overall: int) -> str:
        """
        Get player tier description for headlines.

        Args:
            overall: Player overall rating

        Returns:
            Tier string (Elite, Star, Quality, Depth, etc.)
        """
        if overall >= 90:
            return "elite"
        elif overall >= 85:
            return "star"
        elif overall >= 80:
            return "quality"
        elif overall >= 75:
            return "solid"
        else:
            return "depth"

    def _get_position_group(self, position: str) -> str:
        """
        Get position group for headlines.

        Args:
            position: Player position

        Returns:
            Position group (offense, defense, special teams)
        """
        offensive = {'QB', 'RB', 'FB', 'WR', 'TE', 'LT', 'LG', 'C', 'RG', 'RT'}
        special_teams = {'K', 'P', 'LS', 'KR', 'PR'}

        if position in offensive:
            return "offense"
        elif position in special_teams:
            return "special teams"
        else:
            return "defense"