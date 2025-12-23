"""
Shared constants for social media post generation.

This module centralizes all magnitude calculations, post count mappings,
and engagement formulas to ensure consistency across generators.
"""

import random
from typing import Optional


# ============================================================================
# MAGNITUDE THRESHOLDS
# ============================================================================

class MagnitudeThresholds:
    """Event magnitude thresholds (0-100 scale)."""
    MAJOR = 90      # Championship-level events
    HIGH = 80       # Playoff games, major awards
    SIGNIFICANT = 60  # Regular season upsets
    NORMAL = 50     # Standard games/events
    LOW = 30        # Minor transactions


# ============================================================================
# POST COUNT RANGES
# ============================================================================

class PostCountRanges:
    """Post count ranges by magnitude level."""
    MAJOR = (8, 10)       # 90+ magnitude
    HIGH = (6, 8)         # 80-89 magnitude
    SIGNIFICANT = (4, 6)  # 60-79 magnitude
    NORMAL = (2, 4)       # 50-59 magnitude
    LOW = (1, 2)          # <50 magnitude


# ============================================================================
# GAME EVENT MAGNITUDES
# ============================================================================

class GameMagnitudes:
    """Magnitude calculations for game results."""

    @staticmethod
    def calculate(
        score_diff: int,
        is_playoff: bool,
        is_upset: bool,
        playoff_round: Optional[str] = None
    ) -> int:
        """Calculate game magnitude based on context.

        Args:
            score_diff: Absolute score difference
            is_playoff: Whether this is a playoff game
            is_upset: Whether this is considered an upset
            playoff_round: Specific playoff round (SUPER_BOWL, etc.)

        Returns:
            Magnitude value (0-100)
        """
        base = MagnitudeThresholds.NORMAL

        # Playoff multiplier
        if is_playoff:
            if playoff_round == 'SUPER_BOWL':
                base = 100
            elif playoff_round == 'CONFERENCE_CHAMPIONSHIP':
                base = 95
            elif playoff_round == 'DIVISIONAL':
                base = 85
            else:  # Wild Card
                base = 80

        # Blowout adjustment
        if score_diff >= 20:
            base += 10

        # Upset bonus
        if is_upset:
            base += 15

        return min(100, base)


# ============================================================================
# AWARD MAGNITUDES
# ============================================================================

class AwardMagnitudes:
    """Prestige values for awards."""
    MVP = 100
    DPOY = 90
    OPOY = 85
    CPOY = 80
    DROY = 75
    OROY = 75
    ALL_PRO_FIRST = 70
    ALL_PRO_SECOND = 60
    PRO_BOWL = 50
    WEEKLY_AWARD = 40


# ============================================================================
# TRANSACTION MAGNITUDES
# ============================================================================

class TransactionMagnitudes:
    """Magnitude calculations for transactions."""

    @staticmethod
    def calculate_trade_magnitude(
        player_value: int,
        draft_picks_involved: int,
        is_star: bool
    ) -> int:
        """Calculate trade magnitude.

        Args:
            player_value: Player's trade value (0-100)
            draft_picks_involved: Number of draft picks in trade
            is_star: Whether a star player is involved

        Returns:
            Magnitude value (0-100)
        """
        base = min(80, player_value // 2)

        if is_star:
            base += 20

        base += min(20, draft_picks_involved * 5)

        return min(100, base)

    @staticmethod
    def calculate_signing_magnitude(
        contract_value: int,
        is_franchise_player: bool
    ) -> int:
        """Calculate FA signing magnitude.

        Args:
            contract_value: Total contract value in millions
            is_franchise_player: Whether this is a franchise cornerstone

        Returns:
            Magnitude value (0-100)
        """
        base = min(70, contract_value // 2) + 40

        if is_franchise_player:
            base += 20

        return min(100, base)


# ============================================================================
# ENGAGEMENT CALCULATIONS
# ============================================================================

class EngagementFormulas:
    """Engagement metrics (likes, retweets) formulas."""

    BASE_LIKES_MIN = 100
    BASE_LIKES_MAX = 500

    BASE_RETWEETS_MIN = 20
    BASE_RETWEETS_MAX = 100

    SENTIMENT_MULTIPLIERS = {
        'positive': 1.5,
        'neutral': 1.0,
        'negative': 1.2  # Controversy generates engagement
    }

    @staticmethod
    def calculate_likes(magnitude: int, sentiment: str) -> int:
        """Calculate like count.

        Args:
            magnitude: Event magnitude (0-100)
            sentiment: Sentiment type (positive/neutral/negative)

        Returns:
            Number of likes
        """
        base = random.randint(
            EngagementFormulas.BASE_LIKES_MIN,
            EngagementFormulas.BASE_LIKES_MAX
        )

        magnitude_mult = 1 + (magnitude / 100)
        sentiment_mult = EngagementFormulas.SENTIMENT_MULTIPLIERS.get(sentiment, 1.0)

        return int(base * magnitude_mult * sentiment_mult)

    @staticmethod
    def calculate_retweets(magnitude: int, sentiment: str) -> int:
        """Calculate retweet count.

        Args:
            magnitude: Event magnitude (0-100)
            sentiment: Sentiment type (positive/neutral/negative)

        Returns:
            Number of retweets
        """
        base = random.randint(
            EngagementFormulas.BASE_RETWEETS_MIN,
            EngagementFormulas.BASE_RETWEETS_MAX
        )

        magnitude_mult = 1 + (magnitude / 100)
        sentiment_mult = EngagementFormulas.SENTIMENT_MULTIPLIERS.get(sentiment, 1.0)

        return int(base * magnitude_mult * sentiment_mult)
