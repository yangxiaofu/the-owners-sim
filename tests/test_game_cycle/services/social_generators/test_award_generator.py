"""
Tests for AwardSocialGenerator.

Validates award announcement post generation logic.
"""

import pytest
import tempfile
import os

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.services.social_generators.award_generator import AwardSocialGenerator
from game_cycle.models.social_event_types import SocialEventType


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = GameCycleDatabase(path)
    yield db

    db.close()
    os.unlink(path)


@pytest.fixture
def generator(temp_db):
    """Create AwardSocialGenerator instance."""
    return AwardSocialGenerator(temp_db, dynasty_id="test_dynasty")


@pytest.fixture
def setup_test_personalities(temp_db):
    """Create test personalities for posts."""
    personality_api = SocialPersonalityAPI(temp_db)

    # Create fan personalities for team 1
    for i in range(5):
        personality_api.create_personality(
            dynasty_id="test_dynasty",
            handle=f"@Team1Fan{i}",
            display_name=f"Team 1 Fan {i}",
            personality_type="FAN",
            archetype="OPTIMIST" if i % 2 == 0 else "BANDWAGON",
            team_id=1,
            sentiment_bias=0.7,
            posting_frequency="ALL_EVENTS"
        )


class TestAwardPostGeneration:
    """Test award post generation."""

    def test_generate_posts_mvp(self, generator, setup_test_personalities):
        """Should generate 2-4 posts for MVP (highest prestige)."""
        event_data = {
            'award_name': 'MVP',
            'player_name': 'Patrick Mahomes',
            'team_id': 1,
            'player_stats': '4,500 yards, 35 TDs'
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # MVP: 2-4 posts (magnitude 100)
        assert 2 <= len(posts) <= 4
        # All posts should have required fields
        for post in posts:
            assert post.personality_id > 0
            assert post.post_text
            assert post.event_type == SocialEventType.AWARD
            assert post.sentiment > 0  # Awards are positive
            assert post.likes >= 0
            assert post.retweets >= 0

    def test_generate_posts_dpoy(self, generator, setup_test_personalities):
        """Should generate 2-4 posts for DPOY."""
        event_data = {
            'award_name': 'DPOY',
            'player_name': 'TJ Watt',
            'team_id': 1,
            'player_stats': '15 sacks, 3 forced fumbles'
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # DPOY: 2-4 posts (magnitude 90)
        assert 2 <= len(posts) <= 4

    def test_generate_posts_oroy(self, generator, setup_test_personalities):
        """Should generate 2-4 posts for OROY."""
        event_data = {
            'award_name': 'OROY',
            'player_name': 'Caleb Williams',
            'team_id': 1,
            'player_stats': '3,200 yards, 22 TDs'
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # OROY: 2-4 posts (magnitude 85)
        assert 2 <= len(posts) <= 4

    def test_generate_posts_pro_bowl(self, generator, setup_test_personalities):
        """Should generate 1-2 posts for Pro Bowl (lower prestige)."""
        event_data = {
            'award_name': 'PRO_BOWL',
            'player_name': 'Cooper Kupp',
            'team_id': 1
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # Pro Bowl: 1-2 posts (magnitude 60)
        assert 1 <= len(posts) <= 2

    def test_generate_posts_unknown_award(self, generator, setup_test_personalities):
        """Should handle unknown awards with default prestige."""
        event_data = {
            'award_name': 'CUSTOM_AWARD',
            'player_name': 'John Doe',
            'team_id': 1
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # Unknown award: uses DEFAULT magnitude (70)
        assert len(posts) >= 1


class TestAwardPrestige:
    """Test award prestige mapping."""

    def test_award_prestige_values(self, generator):
        """Award prestige should match expected values."""
        assert generator.AWARD_PRESTIGE['MVP'] == 100
        assert generator.AWARD_PRESTIGE['DPOY'] == 90
        assert generator.AWARD_PRESTIGE['OROY'] == 85
        assert generator.AWARD_PRESTIGE['DROY'] == 85
        assert generator.AWARD_PRESTIGE['CPOY'] == 80
        assert generator.AWARD_PRESTIGE['ALL_PRO_FIRST'] == 75
        assert generator.AWARD_PRESTIGE['PRO_BOWL'] == 60
        assert generator.AWARD_PRESTIGE['DEFAULT'] == 70


class TestEventMetadata:
    """Test event metadata storage."""

    def test_event_metadata_complete(self, generator, setup_test_personalities):
        """Event metadata should include all award details."""
        event_data = {
            'award_name': 'MVP',
            'player_name': 'Patrick Mahomes',
            'team_id': 1,
            'player_stats': '4,500 yards, 35 TDs'
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        for post in posts:
            metadata = post.event_metadata
            assert metadata['award'] == 'MVP'
            assert metadata['player_name'] == 'Patrick Mahomes'
            assert metadata['team_id'] == 1

    def test_event_metadata_no_stats(self, generator, setup_test_personalities):
        """Should handle missing player stats."""
        event_data = {
            'award_name': 'PRO_BOWL',
            'player_name': 'Cooper Kupp',
            'team_id': 1
            # No player_stats provided
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # Should not crash, uses default stat line
        assert len(posts) > 0


class TestEngagement:
    """Test engagement calculation."""

    def test_mvp_high_engagement(self, generator, setup_test_personalities):
        """MVP posts should have high engagement (magnitude 100)."""
        event_data = {
            'award_name': 'MVP',
            'player_name': 'Patrick Mahomes',
            'team_id': 1,
            'player_stats': '4,500 yards, 35 TDs'
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # MVP posts should have high engagement (magnitude 100)
        for post in posts:
            assert post.likes >= 500
            assert post.retweets >= 100

    def test_pro_bowl_moderate_engagement(self, generator, setup_test_personalities):
        """Pro Bowl posts should have moderate engagement (magnitude 60)."""
        event_data = {
            'award_name': 'PRO_BOWL',
            'player_name': 'Cooper Kupp',
            'team_id': 1
        }

        posts = generator._generate_posts(season=2025, week=23, event_data=event_data)

        # Pro Bowl posts should have moderate engagement (magnitude 60)
        for post in posts:
            assert post.likes >= 200  # Lower than MVP
            assert post.retweets >= 50
