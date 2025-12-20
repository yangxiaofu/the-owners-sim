"""
TransactionEvent - Standardized event model for all transactions.

Part of Transaction-Media Architecture Refactoring.

Replaces inconsistent dict structures returned by transaction services.
Provides unified interface for headline generation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.game_cycle.services.prominence_calculator import ProminenceCalculator


class TransactionType(Enum):
    """Types of transactions that generate media coverage."""
    SIGNING = "SIGNING"
    RESIGNING = "RESIGNING"
    TRADE = "TRADE"
    ROSTER_CUT = "ROSTER_CUT"
    FRANCHISE_TAG = "FRANCHISE_TAG"
    WAIVER_CLAIM = "WAIVER_CLAIM"
    DRAFT_PICK = "DRAFT_PICK"
    AWARD = "AWARD"
    RETIREMENT = "RETIREMENT"
    HOF_INDUCTION = "HOF_INDUCTION"


@dataclass
class TransactionEvent:
    """
    Standardized event model for all transactions.

    Provides unified interface for headline generation across:
    - Signings, Re-signings, Trades
    - Roster Cuts, Waiver Claims
    - Franchise Tags, Draft Picks
    - Awards

    Usage:
        # Create from raw service data
        event = TransactionEvent.from_signing(signing_data, context, team_name, calc)

        # Check if headline-worthy
        if event.is_headline_worthy:
            generator.generate_headline(event)

        # Access computed properties
        priority = event.suggested_priority
        sentiment = event.suggested_sentiment
    """

    # Event identification
    event_type: TransactionType
    dynasty_id: str
    season: int
    week: int

    # Primary participant
    team_id: int
    team_name: str  # Pre-resolved for convenience

    # Player info (optional - some events are team-level)
    player_id: Optional[int] = None
    player_name: Optional[str] = None
    player_position: Optional[str] = None
    player_overall: int = 0
    player_age: int = 0

    # Secondary participant (for trades, claims from other teams)
    secondary_team_id: Optional[int] = None
    secondary_team_name: Optional[str] = None

    # For trades - players/picks going each direction
    incoming_players: List[Dict[str, Any]] = field(default_factory=list)
    outgoing_players: List[Dict[str, Any]] = field(default_factory=list)
    incoming_picks: List[Dict[str, Any]] = field(default_factory=list)
    outgoing_picks: List[Dict[str, Any]] = field(default_factory=list)

    # Financial impact
    financial_impact: int = 0  # AAV, cap savings, tag salary, etc.
    contract_years: int = 0

    # Prominence (computed)
    prominence_level: str = "DEPTH"  # From ProminenceCalculator
    is_headline_worthy: bool = False
    is_surprising: bool = False

    # Headline suggestions (computed)
    suggested_priority: int = 50
    suggested_sentiment: str = "NEUTRAL"

    # Type-specific details
    details: Dict[str, Any] = field(default_factory=dict)

    # For re-signings - is this a departure?
    is_departure: bool = False

    # For draft picks
    draft_round: int = 0
    draft_pick: int = 0

    @classmethod
    def from_signing(
        cls,
        signing_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for FA signings.

        Args:
            signing_data: Dict with player_id, player_name, position, overall, aav, years, team_id
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Resolved team name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for FA signing
        """
        overall = signing_data.get("overall", 0)
        position = signing_data.get("position", "")
        aav = signing_data.get("aav", 0)

        event = cls(
            event_type=TransactionType.SIGNING,
            dynasty_id=dynasty_id,
            season=season,
            week=25,  # FA week
            team_id=signing_data.get("team_id", 0),
            team_name=team_name,
            player_id=signing_data.get("player_id"),
            player_name=signing_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=signing_data.get("age", 0),
            financial_impact=aav,
            contract_years=signing_data.get("years", 1),
            details=signing_data.copy(),
        )

        # Compute prominence
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "signing"
        ).value
        event.is_headline_worthy = prominence_calc.is_headline_worthy(
            overall, "signing", position, aav
        )
        event.suggested_priority = prominence_calc.calculate_priority(
            60, overall, "signing", aav
        )
        event.suggested_sentiment = "POSITIVE"

        return event

    @classmethod
    def from_resigning(
        cls,
        player_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator",
        is_departure: bool = False
    ) -> "TransactionEvent":
        """
        Factory method for re-signings (extensions or departures).

        Args:
            player_data: Dict with player info and contract terms
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Resolved team name
            prominence_calc: ProminenceCalculator instance
            is_departure: True if player is leaving (not re-signed)

        Returns:
            TransactionEvent configured for re-signing
        """
        overall = player_data.get("overall", 0)
        position = player_data.get("position", "")
        aav = player_data.get("aav", 0)

        event = cls(
            event_type=TransactionType.RESIGNING,
            dynasty_id=dynasty_id,
            season=season,
            week=24,  # Re-signing week
            team_id=player_data.get("team_id", 0),
            team_name=team_name,
            player_id=player_data.get("player_id"),
            player_name=player_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=player_data.get("age", 0),
            financial_impact=aav,
            contract_years=player_data.get("years", 1),
            is_departure=is_departure,
            details=player_data.copy(),
        )

        # Compute prominence
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "resigning"
        ).value
        event.is_headline_worthy = prominence_calc.is_headline_worthy(
            overall, "resigning", position, aav
        )
        event.suggested_priority = prominence_calc.calculate_priority(
            65, overall, "resigning", aav
        )
        event.suggested_sentiment = prominence_calc.get_sentiment(
            "resigning", is_departure=is_departure
        )

        return event

    @classmethod
    def from_cut(
        cls,
        cut_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for roster cuts.

        Args:
            cut_data: Dict with player info and cap_savings
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Resolved team name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for roster cut
        """
        overall = cut_data.get("overall", 0)
        position = cut_data.get("position", "")
        cap_savings = cut_data.get("cap_savings", 0)

        # Cuts are "surprising" if star-level player
        is_surprising = overall >= 85

        event = cls(
            event_type=TransactionType.ROSTER_CUT,
            dynasty_id=dynasty_id,
            season=season,
            week=28,  # Roster cuts week
            team_id=cut_data.get("team_id", 0),
            team_name=team_name,
            player_id=cut_data.get("player_id"),
            player_name=cut_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=cut_data.get("age", 0),
            financial_impact=cap_savings,
            is_surprising=is_surprising,
            details=cut_data.copy(),
        )

        # Compute prominence
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "roster_cut"
        ).value
        event.is_headline_worthy = prominence_calc.is_headline_worthy(
            overall, "roster_cut", position, cap_savings, is_surprise=is_surprising
        )
        event.suggested_priority = prominence_calc.calculate_priority(
            55, overall, "roster_cut", cap_savings, is_surprising
        )
        event.suggested_sentiment = "CRITICAL" if is_surprising else "NEGATIVE"

        return event

    @classmethod
    def from_waiver_claim(
        cls,
        claim_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        claiming_team_name: str,
        former_team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for waiver wire claims.

        Args:
            claim_data: Dict with player info and team IDs
            dynasty_id: Current dynasty ID
            season: Current season
            claiming_team_name: Name of team making claim
            former_team_name: Name of team that cut player
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for waiver claim
        """
        overall = claim_data.get("overall", 0)
        position = claim_data.get("position", "")

        event = cls(
            event_type=TransactionType.WAIVER_CLAIM,
            dynasty_id=dynasty_id,
            season=season,
            week=29,  # Waiver wire week
            team_id=claim_data.get("claiming_team_id", 0),
            team_name=claiming_team_name,
            secondary_team_id=claim_data.get("former_team_id"),
            secondary_team_name=former_team_name,
            player_id=claim_data.get("player_id"),
            player_name=claim_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=claim_data.get("age", 0),
            details=claim_data.copy(),
        )

        # Compute prominence
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "waiver_claim"
        ).value
        event.is_headline_worthy = prominence_calc.is_headline_worthy(
            overall, "waiver_claim", position
        )
        event.suggested_priority = prominence_calc.calculate_priority(
            50, overall, "waiver_claim"
        )
        event.suggested_sentiment = "POSITIVE"

        return event

    @classmethod
    def from_franchise_tag(
        cls,
        tag_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for franchise tags.

        Args:
            tag_data: Dict with player info and tag salary
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Resolved team name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for franchise tag
        """
        overall = tag_data.get("overall", 0)
        position = tag_data.get("position", "")
        tag_salary = tag_data.get("tag_salary", 0)

        event = cls(
            event_type=TransactionType.FRANCHISE_TAG,
            dynasty_id=dynasty_id,
            season=season,
            week=23,  # Franchise tag week
            team_id=tag_data.get("team_id", 0),
            team_name=team_name,
            player_id=tag_data.get("player_id"),
            player_name=tag_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=tag_data.get("age", 0),
            financial_impact=tag_salary,
            contract_years=1,  # Tags are 1-year
            details=tag_data.copy(),
        )

        # All franchise tags are headline-worthy
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "franchise_tag"
        ).value
        event.is_headline_worthy = True  # All tags are notable
        event.suggested_priority = prominence_calc.calculate_priority(
            75, overall, "franchise_tag", tag_salary
        )
        event.suggested_sentiment = "HYPE"

        return event

    @classmethod
    def from_trade(
        cls,
        trade_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        other_team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for trades.

        Args:
            trade_data: Dict with trade details including players and picks
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Primary team name
            other_team_name: Trade partner name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for trade
        """
        # Find the highest-rated player involved
        incoming = trade_data.get("incoming_players", [])
        outgoing = trade_data.get("outgoing_players", [])
        all_players = incoming + outgoing

        best_player = max(all_players, key=lambda p: p.get("overall", 0)) if all_players else {}
        overall = best_player.get("overall", 0)
        position = best_player.get("position", "")

        event = cls(
            event_type=TransactionType.TRADE,
            dynasty_id=dynasty_id,
            season=season,
            week=trade_data.get("week", 26),
            team_id=trade_data.get("team_id", 0),
            team_name=team_name,
            secondary_team_id=trade_data.get("other_team_id"),
            secondary_team_name=other_team_name,
            player_id=best_player.get("player_id"),
            player_name=best_player.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            incoming_players=incoming,
            outgoing_players=outgoing,
            incoming_picks=trade_data.get("incoming_picks", []),
            outgoing_picks=trade_data.get("outgoing_picks", []),
            details=trade_data.copy(),
        )

        # Compute prominence based on best player
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "trade"
        ).value
        event.is_headline_worthy = prominence_calc.is_headline_worthy(
            overall, "trade", position
        )
        event.suggested_priority = prominence_calc.calculate_priority(
            70, overall, "trade"
        )
        event.suggested_sentiment = "NEUTRAL"

        return event

    @classmethod
    def from_draft_pick(
        cls,
        pick_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for draft picks.

        Args:
            pick_data: Dict with draft pick and player info
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Drafting team name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for draft pick
        """
        overall = pick_data.get("overall", 0)
        position = pick_data.get("position", "")
        draft_round = pick_data.get("round", 0)
        draft_pick = pick_data.get("pick", 0)

        event = cls(
            event_type=TransactionType.DRAFT_PICK,
            dynasty_id=dynasty_id,
            season=season,
            week=27,  # Draft week
            team_id=pick_data.get("team_id", 0),
            team_name=team_name,
            player_id=pick_data.get("player_id"),
            player_name=pick_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=pick_data.get("age", 22),  # Rookies typically 22
            draft_round=draft_round,
            draft_pick=draft_pick,
            details=pick_data.copy(),
        )

        # Top picks are always headline-worthy
        is_top_pick = draft_round == 1 and draft_pick <= 10
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "draft"
        ).value
        event.is_headline_worthy = is_top_pick or overall >= 75
        event.suggested_priority = prominence_calc.calculate_priority(
            80 if is_top_pick else 60, overall, "draft"
        )
        event.suggested_sentiment = "HYPE"

        return event

    @classmethod
    def from_award(
        cls,
        award_data: Dict[str, Any],
        dynasty_id: str,
        season: int,
        team_name: str,
        prominence_calc: "ProminenceCalculator"
    ) -> "TransactionEvent":
        """
        Factory method for awards (MVP, All-Pro, etc.).

        Args:
            award_data: Dict with award and player info
            dynasty_id: Current dynasty ID
            season: Current season
            team_name: Player's team name
            prominence_calc: ProminenceCalculator instance

        Returns:
            TransactionEvent configured for award
        """
        overall = award_data.get("overall", 0)
        position = award_data.get("position", "")

        event = cls(
            event_type=TransactionType.AWARD,
            dynasty_id=dynasty_id,
            season=season,
            week=22,  # Awards week (offseason honors)
            team_id=award_data.get("team_id", 0),
            team_name=team_name,
            player_id=award_data.get("player_id"),
            player_name=award_data.get("player_name", ""),
            player_position=position,
            player_overall=overall,
            player_age=award_data.get("age", 0),
            details=award_data.copy(),
        )

        # All awards are headline-worthy
        event.prominence_level = prominence_calc.get_prominence(
            overall, position, "award"
        ).value
        event.is_headline_worthy = True
        event.suggested_priority = prominence_calc.calculate_priority(
            85, overall, "award"
        )
        event.suggested_sentiment = "HYPE"

        return event

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "event_type": self.event_type.value,
            "dynasty_id": self.dynasty_id,
            "season": self.season,
            "week": self.week,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "player_position": self.player_position,
            "player_overall": self.player_overall,
            "player_age": self.player_age,
            "secondary_team_id": self.secondary_team_id,
            "secondary_team_name": self.secondary_team_name,
            "incoming_players": self.incoming_players,
            "outgoing_players": self.outgoing_players,
            "incoming_picks": self.incoming_picks,
            "outgoing_picks": self.outgoing_picks,
            "financial_impact": self.financial_impact,
            "contract_years": self.contract_years,
            "prominence_level": self.prominence_level,
            "is_headline_worthy": self.is_headline_worthy,
            "is_surprising": self.is_surprising,
            "suggested_priority": self.suggested_priority,
            "suggested_sentiment": self.suggested_sentiment,
            "is_departure": self.is_departure,
            "draft_round": self.draft_round,
            "draft_pick": self.draft_pick,
            "details": self.details,
        }

    def get_financial_summary(self) -> str:
        """Get human-readable financial summary."""
        if self.event_type == TransactionType.SIGNING:
            return f"${self.financial_impact:,} AAV, {self.contract_years} year{'s' if self.contract_years > 1 else ''}"
        elif self.event_type == TransactionType.ROSTER_CUT:
            return f"${self.financial_impact:,} cap savings"
        elif self.event_type == TransactionType.FRANCHISE_TAG:
            return f"${self.financial_impact:,} tag salary"
        elif self.event_type == TransactionType.RESIGNING:
            if self.is_departure:
                return "Player departing"
            return f"${self.financial_impact:,} AAV, {self.contract_years} year{'s' if self.contract_years > 1 else ''}"
        return ""

    def get_player_summary(self) -> str:
        """Get human-readable player summary."""
        if not self.player_name:
            return ""
        parts = [self.player_name]
        if self.player_position:
            parts.append(f"({self.player_position})")
        if self.player_overall:
            parts.append(f"[{self.player_overall} OVR]")
        return " ".join(parts)