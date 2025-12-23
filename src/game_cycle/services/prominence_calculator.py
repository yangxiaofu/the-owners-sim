"""
Prominence Calculator - Unified player prominence detection for media coverage.

Part of Transaction-Media Architecture Refactoring.

Centralizes star player detection logic that was previously scattered
across 8+ headline generation methods in offseason.py.
"""

from enum import Enum
from typing import Optional


class ProminenceLevel(Enum):
    """Player prominence levels for media coverage decisions."""
    ELITE = "ELITE"      # 90+ OVR - Always headline
    STAR = "STAR"        # 85-89 OVR - Usually headline
    STARTER = "STARTER"  # 80-84 OVR - Context-dependent
    ROTATION = "ROTATION"  # 75-79 OVR - Notable only
    DEPTH = "DEPTH"      # <75 OVR - Rarely headline


class ProminenceCalculator:
    """
    Unified player prominence detection for media coverage.

    Provides consistent star player detection across all transaction types:
    - Signings, Re-signings, Trades
    - Roster Cuts, Waiver Claims
    - Franchise Tags, Draft Picks

    Usage:
        calc = ProminenceCalculator()

        # Check if a transaction is headline-worthy
        if calc.is_headline_worthy(player_overall, "signing", position="QB"):
            generate_headline(...)

        # Get prominence level for styling decisions
        level = calc.get_prominence(player_overall, position="WR")
        if level == ProminenceLevel.ELITE:
            use_breaking_news_template()

        # Calculate headline priority
        priority = calc.calculate_priority(base_priority=60, overall=88, "trade")
    """

    # Position importance - premium positions get visibility boost
    PREMIUM_POSITIONS = {
        "QB": 1.5,   # Quarterbacks are always newsworthy
        "LT": 1.3,   # Left tackles protect the blindside
        "RT": 1.2,   # Right tackles
        "EDGE": 1.3, # Pass rushers
        "DE": 1.2,   # Defensive ends
        "WR": 1.2,   # Wide receivers
        "CB": 1.2,   # Cornerbacks
    }

    # Transaction-specific thresholds
    # Each transaction type has different newsworthiness criteria
    THRESHOLDS = {
        "resigning": {
            "star": 85,      # Star extensions always headline
            "notable": 80,   # Notable departures
        },
        "franchise_tag": {
            "star": 0,       # All tags are notable (they're $15M+ decisions)
            "notable": 0,
        },
        "roster_cut": {
            "star": 85,      # Star cuts are shocking
            "notable": 75,   # Lower threshold - cuts have "surprise" value
            "surprise": 80,  # Unexpected cut threshold
        },
        "waiver_claim": {
            "star": 80,      # Starter-caliber claims
            "notable": 70,   # Lower threshold - waiver claims are rarer
        },
        "signing": {
            "star": 85,      # Star signings
            "notable": 75,   # Quality signings
        },
        "trade": {
            "star": 85,      # Star trades
            "notable": 80,   # Notable trades
        },
        "draft": {
            "star": 0,       # Top picks always headline
            "notable": 10,   # Top 10 picks
        },
        "award": {
            "star": 0,       # All awards are notable
            "notable": 0,
        },
    }

    def get_prominence(
        self,
        overall: int,
        position: Optional[str] = None,
        transaction_type: Optional[str] = None
    ) -> ProminenceLevel:
        """
        Determine player prominence level.

        Args:
            overall: Player's overall rating (0-99)
            position: Player position (for premium position boost)
            transaction_type: Context for threshold selection (unused currently)

        Returns:
            ProminenceLevel enum value
        """
        # Apply position boost for premium positions
        effective_overall = overall
        if position and position in self.PREMIUM_POSITIONS:
            # Premium positions get +3 effective OVR for visibility
            effective_overall += 3

        if effective_overall >= 90:
            return ProminenceLevel.ELITE
        elif effective_overall >= 85:
            return ProminenceLevel.STAR
        elif effective_overall >= 80:
            return ProminenceLevel.STARTER
        elif effective_overall >= 75:
            return ProminenceLevel.ROTATION
        else:
            return ProminenceLevel.DEPTH

    def is_headline_worthy(
        self,
        overall: int,
        transaction_type: str,
        position: Optional[str] = None,
        cap_impact: int = 0,
        is_surprise: bool = False
    ) -> bool:
        """
        Determine if a transaction should generate a headline.

        Uses transaction-specific thresholds and considers:
        - Player overall rating
        - Position premium (QBs, pass rushers more newsworthy)
        - Financial impact (big contracts, cap savings)
        - Surprise factor (unexpected moves)

        Args:
            overall: Player's overall rating
            transaction_type: Type of transaction (signing, trade, roster_cut, etc.)
            position: Player position for premium boost
            cap_impact: Financial impact in dollars (AAV, cap savings, etc.)
            is_surprise: Whether this is an unexpected transaction

        Returns:
            True if transaction should generate a headline
        """
        thresholds = self.THRESHOLDS.get(
            transaction_type,
            {"star": 85, "notable": 80}  # Default thresholds
        )

        # Get prominence level (includes position boost)
        prominence = self.get_prominence(overall, position, transaction_type)

        # Elite/Star players always generate headlines
        if prominence in (ProminenceLevel.ELITE, ProminenceLevel.STAR):
            return True

        # Surprise transactions lower the threshold
        if is_surprise and overall >= thresholds.get("surprise", 75):
            return True

        # High financial impact makes transactions newsworthy
        if cap_impact >= 5_000_000:  # $5M+ is significant
            return True

        # Check against notable threshold
        return overall >= thresholds.get("notable", 80)

    def calculate_priority(
        self,
        base_priority: int,
        overall: int,
        transaction_type: str,
        cap_impact: int = 0,
        is_surprise: bool = False
    ) -> int:
        """
        Calculate headline priority based on prominence.

        Higher priority headlines appear first in media coverage.
        Priority range: 0-95 (capped to allow manual boosts).

        Args:
            base_priority: Base priority for this headline type
            overall: Player's overall rating
            transaction_type: Type of transaction
            cap_impact: Financial impact in dollars
            is_surprise: Whether this is unexpected

        Returns:
            Calculated priority (0-95)
        """
        priority = base_priority

        # Star bonus - elite players get higher priority
        if overall >= 90:
            priority += (overall - 90) + 5  # +5 to +14 for 90-99 OVR
        elif overall >= 85:
            priority += (overall - 85)  # +0 to +4 for 85-89 OVR

        # Financial impact bonus
        if cap_impact >= 20_000_000:
            priority += 10  # Mega deals
        elif cap_impact >= 10_000_000:
            priority += 5   # Big deals

        # Surprise bonus - unexpected moves get attention
        if is_surprise:
            priority += 8

        # Cap at 95 to leave room for manual priority boosts
        return min(95, priority)

    def get_sentiment(
        self,
        transaction_type: str,
        is_surprise: bool = False,
        is_departure: bool = False
    ) -> str:
        """
        Suggest sentiment for headline based on transaction type.

        Args:
            transaction_type: Type of transaction
            is_surprise: Whether this is unexpected
            is_departure: Whether player is leaving (for re-signings)

        Returns:
            Sentiment string: POSITIVE, NEGATIVE, NEUTRAL, HYPE, CRITICAL
        """
        if is_surprise:
            return "CRITICAL"

        if transaction_type in ("signing", "resigning", "waiver_claim"):
            if is_departure:
                return "NEUTRAL"
            return "POSITIVE"

        if transaction_type == "roster_cut":
            return "NEGATIVE"

        if transaction_type == "trade":
            return "NEUTRAL"

        if transaction_type in ("franchise_tag", "draft", "award"):
            return "HYPE"

        return "NEUTRAL"