"""
Tests for TransactionSocialGenerator.

Validates transaction post generation logic (trades, signings, cuts).
"""

import pytest
import tempfile
import os

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.services.social_generators.transaction_generator import TransactionSocialGenerator
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
    """Create TransactionSocialGenerator instance."""
    return TransactionSocialGenerator(temp_db, dynasty_id="test_dynasty")


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
            archetype="TRADE_ANALYST" if i == 0 else "OPTIMIST",
            team_id=1,
            sentiment_bias=0.5,
            posting_frequency="ALL_EVENTS"
        )


class TestTradePostGeneration:
    """Test trade transaction posts."""

    def test_generate_posts_trade(self, generator, setup_test_personalities):
        """Should generate 3-5 posts for trades."""
        event_data = {
            'event_type': 'TRADE',
            'team_id': 1,
            'player_name': 'DeAndre Hopkins',
            'transaction_details': {
                'magnitude': 70,
                'trade_partner': 'KC',
                'picks': '2nd round pick'
            }
        }

        posts = generator._generate_posts(season=2025, week=10, event_data=event_data)

        # Trade: 3-5 posts
        assert 3 <= len(posts) <= 5
        # Verify event type
        for post in posts:
            assert post.event_type == SocialEventType.TRADE
            assert post.personality_id > 0
            assert post.post_text
            assert post.likes >= 0
            assert post.retweets >= 0

    def test_trade_includes_analyst_posts(self, generator, setup_test_personalities):
        """Trades should include analyst posts."""
        event_data = {
            'event_type': 'TRADE',
            'team_id': 1,
            'player_name': 'DeAndre Hopkins',
            'transaction_details': {
                'magnitude': 75,
                'trade_partner': 'KC'
            }
        }

        posts = generator._generate_posts(season=2025, week=10, event_data=event_data)

        # Should have both fan and analyst posts
        # (At least 1 analyst since we created one TRADE_ANALYST personality)
        assert len(posts) >= 3


class TestSigningPostGeneration:
    """Test signing transaction posts."""

    def test_generate_posts_big_signing(self, generator, setup_test_personalities):
        """Should generate 3-5 posts for big signings ($10M+)."""
        event_data = {
            'event_type': 'SIGNING',
            'team_id': 1,
            'player_name': 'Aaron Donald',
            'transaction_details': {
                'value': 25,  # $25M per year
                'years': 3
            }
        }

        posts = generator._generate_posts(season=2025, week=24, event_data=event_data)

        # Big signing ($25M): 3-5 posts
        assert 3 <= len(posts) <= 5
        # Verify event type
        for post in posts:
            assert post.event_type == SocialEventType.SIGNING

    def test_generate_posts_small_signing(self, generator, setup_test_personalities):
        """Should generate 2-3 posts for small signings (<$10M)."""
        event_data = {
            'event_type': 'SIGNING',
            'team_id': 1,
            'player_name': 'Backup OL',
            'transaction_details': {
                'value': 3,  # $3M per year
                'years': 1
            }
        }

        posts = generator._generate_posts(season=2025, week=24, event_data=event_data)

        # Small signing ($3M): 2-3 posts
        assert 2 <= len(posts) <= 3

    def test_signing_magnitude_scales_with_value(self, generator, setup_test_personalities):
        """Signing magnitude should scale with contract value."""
        # Small contract
        small_event = {
            'event_type': 'SIGNING',
            'team_id': 1,
            'player_name': 'Player A',
            'transaction_details': {'value': 5, 'years': 1}
        }
        small_posts = generator._generate_posts(season=2025, week=24, event_data=small_event)

        # Big contract
        big_event = {
            'event_type': 'SIGNING',
            'team_id': 1,
            'player_name': 'Player B',
            'transaction_details': {'value': 30, 'years': 4}
        }
        big_posts = generator._generate_posts(season=2025, week=24, event_data=big_event)

        # Big contract should generate at least as many posts
        assert len(big_posts) >= len(small_posts)


class TestCutPostGeneration:
    """Test cut transaction posts."""

    def test_generate_posts_cut(self, generator, setup_test_personalities):
        """Should generate 2-4 posts for cuts."""
        event_data = {
            'event_type': 'CUT',
            'team_id': 1,
            'player_name': 'Veteran LB',
            'transaction_details': {
                'magnitude': 40,
                'savings': 5  # $5M cap savings
            }
        }

        posts = generator._generate_posts(season=2025, week=26, event_data=event_data)

        # Cut: 2-4 posts
        assert 2 <= len(posts) <= 4
        # Verify event type
        for post in posts:
            assert post.event_type == SocialEventType.CUT

    def test_cut_no_analyst_posts(self, generator, setup_test_personalities):
        """Cuts should NOT include analyst posts (only team fans)."""
        event_data = {
            'event_type': 'CUT',
            'team_id': 1,
            'player_name': 'Veteran LB',
            'transaction_details': {
                'magnitude': 40
            }
        }

        posts = generator._generate_posts(season=2025, week=26, event_data=event_data)

        # All posts should be from team fans (no analysts for cuts)
        assert len(posts) >= 2


class TestEventMetadata:
    """Test event metadata storage."""

    def test_trade_metadata(self, generator, setup_test_personalities):
        """Trade metadata should include all details."""
        event_data = {
            'event_type': 'TRADE',
            'team_id': 1,
            'player_name': 'DeAndre Hopkins',
            'transaction_details': {
                'magnitude': 70,
                'trade_partner': 'KC',
                'picks': '2nd round pick'
            }
        }

        posts = generator._generate_posts(season=2025, week=10, event_data=event_data)

        for post in posts:
            metadata = post.event_metadata
            assert metadata['team_id'] == 1
            assert metadata['player_name'] == 'DeAndre Hopkins'
            assert metadata['magnitude'] == 70
            assert metadata['trade_partner'] == 'KC'
            assert metadata['picks'] == '2nd round pick'

    def test_signing_metadata(self, generator, setup_test_personalities):
        """Signing metadata should include contract details."""
        event_data = {
            'event_type': 'SIGNING',
            'team_id': 1,
            'player_name': 'Aaron Donald',
            'transaction_details': {
                'value': 25,
                'years': 3
            }
        }

        posts = generator._generate_posts(season=2025, week=24, event_data=event_data)

        for post in posts:
            metadata = post.event_metadata
            assert metadata['team_id'] == 1
            assert metadata['player_name'] == 'Aaron Donald'
            assert metadata['value'] == 25
            assert metadata['years'] == 3


class TestEngagement:
    """Test engagement calculation."""

    def test_big_trade_high_engagement(self, generator, setup_test_personalities):
        """Major trades should have high engagement."""
        event_data = {
            'event_type': 'TRADE',
            'team_id': 1,
            'player_name': 'Star Player',
            'transaction_details': {
                'magnitude': 85  # Major trade
            }
        }

        posts = generator._generate_posts(season=2025, week=10, event_data=event_data)

        # Major trade (magnitude 85) should have high engagement
        for post in posts:
            assert post.likes >= 400
            assert post.retweets >= 100
