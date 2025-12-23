"""
Tests for SocialEventType and SocialSentiment enums.

Part of Phase 1: Low-Risk Wins - Enum validation.
"""

import pytest

from game_cycle.models.social_event_types import SocialEventType, SocialSentiment


class TestSocialEventType:
    """Test SocialEventType enum."""

    def test_enum_values_match_database_strings(self):
        """Enum values should match database strings for backward compatibility."""
        assert SocialEventType.GAME_RESULT.value == "GAME_RESULT"
        assert SocialEventType.TRADE.value == "TRADE"
        assert SocialEventType.SIGNING.value == "SIGNING"
        assert SocialEventType.FRANCHISE_TAG.value == "FRANCHISE_TAG"
        assert SocialEventType.RESIGNING.value == "RESIGNING"
        assert SocialEventType.CUT.value == "CUT"
        assert SocialEventType.WAIVER_CLAIM.value == "WAIVER_CLAIM"
        assert SocialEventType.DRAFT_PICK.value == "DRAFT_PICK"
        assert SocialEventType.AWARD.value == "AWARD"
        assert SocialEventType.HOF_INDUCTION.value == "HOF_INDUCTION"
        assert SocialEventType.INJURY.value == "INJURY"
        assert SocialEventType.RUMOR.value == "RUMOR"
        assert SocialEventType.TRAINING_CAMP.value == "TRAINING_CAMP"

    def test_all_event_types_defined(self):
        """All expected event types should be defined."""
        expected_types = {
            "GAME_RESULT",
            "PLAYOFF_GAME",
            "SUPER_BOWL",
            "TRADE",
            "SIGNING",
            "FRANCHISE_TAG",
            "RESIGNING",
            "CUT",
            "WAIVER_CLAIM",
            "DRAFT_PICK",
            "AWARD",
            "HOF_INDUCTION",
            "INJURY",
            "RUMOR",
            "TRAINING_CAMP",
        }
        actual_types = {e.value for e in SocialEventType}
        assert actual_types == expected_types

    def test_enum_can_be_converted_to_string(self):
        """Enum should convert to string value."""
        event_type = SocialEventType.GAME_RESULT
        assert event_type.value == "GAME_RESULT"
        assert str(event_type.value) == "GAME_RESULT"

    def test_enum_can_be_compared(self):
        """Enum values should be comparable."""
        assert SocialEventType.GAME_RESULT == SocialEventType.GAME_RESULT
        assert SocialEventType.GAME_RESULT != SocialEventType.TRADE


class TestSocialSentiment:
    """Test SocialSentiment enum."""

    def test_enum_values_match_expected_strings(self):
        """Sentiment enum values should match expected strings."""
        assert SocialSentiment.ALL.value == "ALL"
        assert SocialSentiment.POSITIVE.value == "POSITIVE"
        assert SocialSentiment.NEGATIVE.value == "NEGATIVE"
        assert SocialSentiment.NEUTRAL.value == "NEUTRAL"

    def test_all_sentiment_types_defined(self):
        """All sentiment types should be defined."""
        expected_sentiments = {"ALL", "POSITIVE", "NEGATIVE", "NEUTRAL"}
        actual_sentiments = {s.value for s in SocialSentiment}
        assert actual_sentiments == expected_sentiments

    def test_sentiment_enum_can_be_converted_to_string(self):
        """Sentiment enum should convert to string value."""
        sentiment = SocialSentiment.POSITIVE
        assert sentiment.value == "POSITIVE"
        assert str(sentiment.value) == "POSITIVE"

    def test_sentiment_enum_can_be_compared(self):
        """Sentiment enum values should be comparable."""
        assert SocialSentiment.POSITIVE == SocialSentiment.POSITIVE
        assert SocialSentiment.POSITIVE != SocialSentiment.NEGATIVE
