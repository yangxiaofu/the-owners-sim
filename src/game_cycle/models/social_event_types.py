"""
Social Event Types for social media posts.

Part of Milestone 14: Social Media & Fan Reactions.
Provides type-safe enums for event types and sentiment categories.
"""

from enum import Enum


class SocialEventType(Enum):
    """
    Types of events that generate social media posts.

    Values match database strings for backward compatibility.
    """

    # Game Events
    GAME_RESULT = "GAME_RESULT"
    """Regular or playoff game results."""

    PLAYOFF_GAME = "PLAYOFF_GAME"
    """Playoff-specific game posts (higher engagement)."""

    SUPER_BOWL = "SUPER_BOWL"
    """Super Bowl posts (maximum engagement)."""

    # Transaction Events
    TRADE = "TRADE"
    """Player/pick trades."""

    SIGNING = "SIGNING"
    """Free agent signings."""

    FRANCHISE_TAG = "FRANCHISE_TAG"
    """Franchise tag applications."""

    RESIGNING = "RESIGNING"
    """Contract extensions for own players."""

    CUT = "CUT"
    """Roster cuts and releases."""

    WAIVER_CLAIM = "WAIVER_CLAIM"
    """Waiver wire claims."""

    DRAFT_PICK = "DRAFT_PICK"
    """NFL Draft selections."""

    # Award Events
    AWARD = "AWARD"
    """MVP, DPOY, All-Pro, Pro Bowl."""

    HOF_INDUCTION = "HOF_INDUCTION"
    """Hall of Fame inductions."""

    # Other
    INJURY = "INJURY"
    """Player injuries and IR placements."""

    RUMOR = "RUMOR"
    """Trade rumors, speculation."""

    TRAINING_CAMP = "TRAINING_CAMP"
    """Training camp battles, depth chart updates."""


class SocialSentiment(Enum):
    """
    Sentiment categories for filtering social media posts.

    Used in UI filter bar and API queries.
    """

    ALL = "ALL"
    """Show all posts regardless of sentiment."""

    POSITIVE = "POSITIVE"
    """Positive sentiment (score > 0.3)."""

    NEGATIVE = "NEGATIVE"
    """Negative sentiment (score < -0.3)."""

    NEUTRAL = "NEUTRAL"
    """Neutral sentiment (-0.3 <= score <= 0.3)."""
