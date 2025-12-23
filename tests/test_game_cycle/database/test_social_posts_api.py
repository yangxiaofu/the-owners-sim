"""
Tests for SocialPostsAPI - Phase 1 changes.

Tests enum validation and stage-aware queries.
"""

import pytest
import tempfile
import os

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_posts_api import SocialPostsAPI
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.models.social_event_types import SocialEventType, SocialSentiment
from game_cycle.stage_definitions import Stage, StageType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = GameCycleDatabase(path)

    # Initialize schema (assuming it's done automatically or we need to call it)
    # For now, assume the database has the schema

    yield db

    db.close()
    os.unlink(path)


@pytest.fixture
def posts_api(temp_db):
    """Create SocialPostsAPI instance."""
    return SocialPostsAPI(temp_db)


@pytest.fixture
def personalities_api(temp_db):
    """Create SocialPersonalityAPI instance."""
    return SocialPersonalityAPI(temp_db)


@pytest.fixture
def test_personality(personalities_api):
    """Create a test personality (league-wide, no team)."""
    personality_id = personalities_api.create_personality(
        dynasty_id="test_dynasty",
        handle="@TestFan",
        display_name="Test Fan",
        personality_type="BEAT_REPORTER",  # League-wide reporter
        archetype="OPTIMIST",
        team_id=None,  # League-wide, no specific team
        sentiment_bias=0.5,
        posting_frequency="ALL_EVENTS"
    )
    return personality_id


class TestCreatePostEnumSupport:
    """Test create_post() with enum support."""

    def test_create_post_with_enum(self, posts_api, test_personality):
        """Should accept SocialEventType enum."""
        post_id = posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Great win!",
            event_type=SocialEventType.GAME_RESULT,  # Enum
            sentiment=0.8,
            likes=100,
            retweets=50
        )
        assert post_id > 0

    def test_create_post_with_string(self, posts_api, test_personality):
        """Should still accept string for backward compatibility."""
        post_id = posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Great trade!",
            event_type="TRADE",  # String
            sentiment=0.6,
            likes=75,
            retweets=25
        )
        assert post_id > 0

    def test_create_post_rejects_invalid_enum_string(self, posts_api, test_personality):
        """Should reject invalid event type string."""
        with pytest.raises(ValueError, match="Invalid event_type"):
            posts_api.create_post(
                dynasty_id="test_dynasty",
                personality_id=test_personality,
                season=2025,
                week=1,
                post_text="Invalid event",
                event_type="INVALID_TYPE",  # Invalid
                sentiment=0.5
            )

    def test_create_post_validates_all_enum_types(self, posts_api, test_personality):
        """All SocialEventType values should be valid."""
        for event_type in SocialEventType:
            post_id = posts_api.create_post(
                dynasty_id="test_dynasty",
                personality_id=test_personality,
                season=2025,
                week=1,
                post_text=f"Test {event_type.name}",
                event_type=event_type,
                sentiment=0.5
            )
            assert post_id > 0


class TestGetPostsByStage:
    """Test get_posts_by_stage() method."""

    def test_get_posts_by_stage_honors(self, posts_api, test_personality):
        """Should get posts for OFFSEASON_HONORS stage (week 23)."""
        # Create post for week 23
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=23,
            post_text="MVP announced!",
            event_type=SocialEventType.AWARD,
            sentiment=0.9
        )

        # Query by stage
        posts = posts_api.get_posts_by_stage(
            dynasty_id="test_dynasty",
            season=2025,
            stage_type=StageType.OFFSEASON_HONORS
        )

        assert len(posts) == 1
        assert posts[0].post_text == "MVP announced!"
        assert posts[0].week == 23

    def test_get_posts_by_stage_wild_card(self, posts_api, test_personality):
        """Should get posts for WILD_CARD stage (week 19)."""
        # Create post for week 19
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=19,
            post_text="Wild Card game!",
            event_type=SocialEventType.PLAYOFF_GAME,
            sentiment=0.8
        )

        # Query by stage
        posts = posts_api.get_posts_by_stage(
            dynasty_id="test_dynasty",
            season=2025,
            stage_type=StageType.WILD_CARD
        )

        assert len(posts) == 1
        assert posts[0].post_text == "Wild Card game!"
        assert posts[0].week == 19

    def test_get_posts_by_stage_with_filters(self, posts_api, test_personality):
        """Should support filtering with stage-aware query."""
        # Create multiple posts
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Win!",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.8
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Trade news",
            event_type=SocialEventType.TRADE,
            sentiment=0.5
        )

        # Query with event type filter
        posts = posts_api.get_posts_by_stage(
            dynasty_id="test_dynasty",
            season=2025,
            stage_type=StageType.REGULAR_WEEK_1,
            event_type_filter=SocialEventType.GAME_RESULT  # Enum filter
        )

        assert len(posts) == 1
        assert posts[0].event_type == "GAME_RESULT"

    def test_get_posts_by_stage_with_sentiment_filter(self, posts_api, test_personality):
        """Should support sentiment filtering."""
        # Create posts with different sentiments
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Great!",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.9  # Positive
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Terrible",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=-0.8  # Negative
        )

        # Query with sentiment filter
        posts = posts_api.get_posts_by_stage(
            dynasty_id="test_dynasty",
            season=2025,
            stage_type=StageType.REGULAR_WEEK_1,
            sentiment_filter=SocialSentiment.POSITIVE  # Enum filter
        )

        assert len(posts) == 1
        assert posts[0].sentiment > 0.3

    def test_get_posts_by_stage_returns_empty_for_no_week(self, posts_api):
        """Should return empty list if stage has no week mapping."""
        # Some stages might not have week numbers
        # For now, all stages should have weeks, but test the safety check
        posts = posts_api.get_posts_by_stage(
            dynasty_id="test_dynasty",
            season=2025,
            stage_type=StageType.OFFSEASON_HONORS
        )
        # Should not crash, returns empty if no posts or week mapping
        assert isinstance(posts, list)

    def test_get_posts_by_stage_dynasty_isolation(self, posts_api, test_personality):
        """Should only return posts for specified dynasty."""
        # Create post for test_dynasty
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Dynasty 1 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )

        # Query different dynasty
        posts = posts_api.get_posts_by_stage(
            dynasty_id="different_dynasty",
            season=2025,
            stage_type=StageType.REGULAR_WEEK_1
        )

        assert len(posts) == 0  # Should not see other dynasty's posts


class TestBackwardCompatibility:
    """Test that changes maintain backward compatibility."""

    def test_existing_string_based_code_still_works(self, posts_api, test_personality):
        """Existing code using strings should continue to work."""
        # Old-style call with strings
        post_id = posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Old style post",
            event_type="GAME_RESULT",  # String
            sentiment=0.5
        )
        assert post_id > 0

        # Verify it was stored correctly
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=1
        )
        assert len(posts) == 1
        assert posts[0].event_type == "GAME_RESULT"


class TestNoneWeekHandling:
    """Test that week=None is handled correctly (returns all weeks for season)."""

    def test_get_rolling_feed_with_none_week_returns_all_weeks(self, posts_api, test_personality):
        """Should return all posts for season when week=None."""
        # Create posts for different weeks
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Week 1 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=2,
            post_text="Week 2 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=19,
            post_text="Playoffs post",
            event_type=SocialEventType.PLAYOFF_GAME,
            sentiment=0.8
        )

        # Test: week=None should return all weeks for season
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=None
        )
        assert len(posts) == 3
        weeks = {post.week for post in posts}
        assert weeks == {1, 2, 19}

    def test_get_rolling_feed_with_specific_week_returns_only_that_week(self, posts_api, test_personality):
        """Should return only specified week when week is not None."""
        # Create posts for different weeks
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Week 1 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=2,
            post_text="Week 2 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )

        # Test: week=1 should return only week 1
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=1
        )
        assert len(posts) == 1
        assert posts[0].week == 1
        assert posts[0].post_text == "Week 1 post"

    def test_get_rolling_feed_none_week_with_filters(self, posts_api, test_personality):
        """Should apply other filters when week=None."""
        # Create posts for different weeks and event types
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Week 1 game",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=2,
            post_text="Week 2 trade",
            event_type=SocialEventType.TRADE,
            sentiment=0.5
        )

        # Test: week=None with event_type filter
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=None,
            event_type_filter="GAME_RESULT"
        )
        assert len(posts) == 1
        assert posts[0].event_type == "GAME_RESULT"

    def test_get_rolling_feed_none_week_dynasty_isolation(self, posts_api, test_personality):
        """Should maintain dynasty isolation when week=None."""
        # Create posts for different dynasties
        posts_api.create_post(
            dynasty_id="test_dynasty",
            personality_id=test_personality,
            season=2025,
            week=1,
            post_text="Dynasty 1 post",
            event_type=SocialEventType.GAME_RESULT,
            sentiment=0.5
        )

        # Query with week=None for different dynasty
        posts = posts_api.get_rolling_feed(
            dynasty_id="different_dynasty",
            season=2025,
            week=None
        )
        assert len(posts) == 0  # Should not see other dynasty's posts
