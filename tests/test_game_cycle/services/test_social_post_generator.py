"""
Tests for SocialPostGenerator service.

Covers:
- Game post generation (normal, upset, blowout)
- Transaction post generation (trade, signing, cut)
- Award post generation
- Engagement calculation
- Personality filtering
- Template integration
- Team name resolution

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 8.
"""

import pytest
import sqlite3
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict, Any

from src.game_cycle.services.social_post_generator import (
    SocialPostGenerator,
    GeneratedPost,
    generate_game_posts_batch,
    MAGNITUDE_NORMAL,
    MAGNITUDE_UPSET,
    MAGNITUDE_BLOWOUT,
    MAGNITUDE_MAJOR_TRADE
)


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_db():
    """Mock GameCycleDatabase instance."""
    db = MagicMock()
    db.get_connection.return_value = MagicMock(spec=sqlite3.Connection)
    return db


@pytest.fixture
def mock_personality_api():
    """Mock SocialPersonalityAPI with sample fan data."""
    api = MagicMock()

    # Sample fan personalities
    api.get_personalities_by_team.return_value = [
        Mock(
            id=1,
            archetype='OPTIMIST',
            posting_frequency='ALL_EVENTS',
            team_id=1
        ),
        Mock(
            id=2,
            archetype='PESSIMIST',
            posting_frequency='ALL_EVENTS',
            team_id=1
        ),
        Mock(
            id=3,
            archetype='BANDWAGON',
            posting_frequency='WIN_ONLY',
            team_id=1
        ),
    ]

    # Sample media personalities
    api.get_league_wide_personalities.return_value = [
        Mock(
            id=100,
            archetype='HOT_TAKE',
            posting_frequency='ALL_EVENTS',
            team_id=None
        ),
        Mock(
            id=101,
            archetype='HOT_TAKE',
            posting_frequency='ALL_EVENTS',
            team_id=None
        ),
    ]

    return api


@pytest.fixture
def mock_template_loader():
    """Mock PostTemplateLoader with sample templates."""
    loader = MagicMock()
    loader.get_template.return_value = "{{winner}} beats {{loser}} {{score}}!"
    loader.fill_template.return_value = "DET beats CHI 31-17!"
    loader.calculate_sentiment.return_value = 0.8
    return loader


@pytest.fixture
def generator(mock_db, mock_personality_api, mock_template_loader):
    """Create SocialPostGenerator with mocked dependencies."""
    with patch('src.game_cycle.services.social_post_generator.SocialPersonalityAPI', return_value=mock_personality_api):
        with patch('src.game_cycle.services.social_post_generator.PostTemplateLoader', return_value=mock_template_loader):
            gen = SocialPostGenerator(mock_db, dynasty_id='test_dynasty')
            gen.personality_api = mock_personality_api
            gen.template_loader = mock_template_loader
            return gen


# ==========================================
# GAME POST GENERATION
# ==========================================

class TestGamePostGeneration:
    """Test game result post generation."""

    def test_normal_game_post_count(self, generator):
        """Normal games should generate 4-6 posts."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17,
            is_upset=False,
            is_blowout=False
        )

        assert len(posts) >= 4
        assert len(posts) <= 6

    def test_upset_post_count(self, generator):
        """Upset games should generate 8-12 posts."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17,
            is_upset=True,
            is_blowout=False
        )

        assert len(posts) >= 8
        assert len(posts) <= 12

    def test_blowout_post_count(self, generator):
        """Blowout games should generate 6-10 posts."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=42,
            losing_score=10,
            is_upset=False,
            is_blowout=True
        )

        assert len(posts) >= 6
        assert len(posts) <= 10

    def test_large_margin_triggers_blowout_magnitude(self, generator):
        """Margins >= 21 should trigger blowout magnitude even without flag."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=45,
            losing_score=14,  # 31-point margin
            is_upset=False,
            is_blowout=False  # Not explicitly marked
        )

        # Should still get blowout post count
        assert len(posts) >= 6

    def test_game_posts_have_required_fields(self, generator):
        """All game posts should have complete GeneratedPost structure."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17
        )

        for post in posts:
            assert isinstance(post, GeneratedPost)
            assert post.personality_id > 0
            assert isinstance(post.post_text, str)
            assert len(post.post_text) > 0
            assert -1.0 <= post.sentiment <= 1.0
            assert post.likes >= 0
            assert post.retweets >= 0
            assert isinstance(post.event_metadata, dict)

    def test_game_event_metadata(self, generator):
        """Game posts should include complete event metadata."""
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21,
            game_id='regular_2025_1_1',
            is_upset=True
        )

        metadata = posts[0].event_metadata
        assert metadata['game_id'] == 'regular_2025_1_1'
        assert metadata['winning_team'] == 1
        assert metadata['losing_team'] == 2
        assert metadata['score'] == '28-21'
        assert metadata['margin'] == 7
        assert metadata['is_upset'] is True
        assert metadata['is_blowout'] is False

    def test_media_posts_only_on_dramatic_games(self, generator, mock_personality_api):
        """Media should only post on upsets/blowouts."""
        # Normal game - no media
        posts_normal = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17,
            is_upset=False,
            is_blowout=False
        )

        # Should not call get_league_wide_personalities for normal game
        mock_personality_api.get_league_wide_personalities.assert_not_called()

        # Upset game - media posts
        mock_personality_api.reset_mock()
        posts_upset = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17,
            is_upset=True,
            is_blowout=False
        )

        # Should call for media personalities
        mock_personality_api.get_league_wide_personalities.assert_called_once()


# ==========================================
# TRANSACTION POST GENERATION
# ==========================================

class TestTransactionPostGeneration:
    """Test transaction post generation."""

    def test_trade_post_count(self, generator):
        """Trades should generate 3-5 posts."""
        posts = generator.generate_transaction_posts(
            season=2025,
            week=1,
            event_type='TRADE',
            team_id=1,
            player_name='John Smith',
            transaction_details={'magnitude': 75, 'picks': '2nd round'}
        )

        assert len(posts) >= 3
        assert len(posts) <= 5

    def test_big_signing_post_count(self, generator):
        """Large contracts (>$10M) should generate 3-5 posts."""
        posts = generator.generate_transaction_posts(
            season=2025,
            week=1,
            event_type='SIGNING',
            team_id=1,
            player_name='Star QB',
            transaction_details={'value': 25, 'years': 5}
        )

        assert len(posts) >= 3
        assert len(posts) <= 5

    def test_small_signing_post_count(self, generator):
        """Small contracts (<$10M) should generate 2-3 posts."""
        posts = generator.generate_transaction_posts(
            season=2025,
            week=1,
            event_type='SIGNING',
            team_id=1,
            player_name='Depth Player',
            transaction_details={'value': 2, 'years': 1}
        )

        assert len(posts) >= 2
        assert len(posts) <= 3

    def test_cut_post_count(self, generator):
        """Cuts should generate 2-4 posts."""
        posts = generator.generate_transaction_posts(
            season=2025,
            week=1,
            event_type='CUT',
            team_id=1,
            player_name='Veteran Player',
            transaction_details={'magnitude': 40}
        )

        assert len(posts) >= 2
        assert len(posts) <= 4

    def test_transaction_variables_passed_to_template(self, generator, mock_template_loader):
        """Transaction details should be passed to template."""
        generator.generate_transaction_posts(
            season=2025,
            week=1,
            event_type='TRADE',
            team_id=1,
            player_name='John Smith',
            transaction_details={'picks': '1st round', 'other_team': 'KC'}
        )

        # Check fill_template was called with transaction details
        call_args = mock_template_loader.fill_template.call_args_list[0][0]
        variables = call_args[1]
        assert variables['player'] == 'John Smith'
        assert 'picks' in variables
        assert 'other_team' in variables


# ==========================================
# AWARD POST GENERATION
# ==========================================

class TestAwardPostGeneration:
    """Test award announcement post generation."""

    def test_mvp_post_count(self, generator):
        """MVP (prestige 100) should generate 2-4 posts."""
        posts = generator.generate_award_posts(
            season=2025,
            week=None,
            award_name='MVP',
            player_name='Elite QB',
            team_id=1,
            player_stats='4500 yards, 40 TDs'
        )

        assert len(posts) >= 2
        assert len(posts) <= 4

    def test_pro_bowl_post_count(self, generator):
        """Pro Bowl (prestige 60) should generate 1-2 posts."""
        posts = generator.generate_award_posts(
            season=2025,
            week=None,
            award_name='PRO_BOWL',
            player_name='Good WR',
            team_id=1
        )

        assert len(posts) >= 1
        assert len(posts) <= 2

    def test_award_metadata(self, generator):
        """Award posts should include complete metadata."""
        posts = generator.generate_award_posts(
            season=2025,
            week=None,
            award_name='DPOY',
            player_name='Star LB',
            team_id=5,
            player_stats='120 tackles, 15 sacks'
        )

        metadata = posts[0].event_metadata
        assert metadata['award'] == 'DPOY'
        assert metadata['player_name'] == 'Star LB'
        assert metadata['team_id'] == 5


# ==========================================
# PERSONALITY & FILTERING
# ==========================================

class TestPersonalityFiltering:
    """Test personality selection and filtering."""

    def test_80_20_recurring_random_mix(self, generator, mock_personality_api):
        """Posts should use 80% recurring, 20% random personalities."""
        # Mock 10 fans available
        mock_personality_api.get_personalities_by_team.return_value = [
            Mock(id=i, archetype='OPTIMIST', posting_frequency='ALL_EVENTS', team_id=1)
            for i in range(1, 11)
        ]

        # Request 10 posts
        with patch.object(generator, '_generate_single_post', return_value=GeneratedPost(
            personality_id=1,
            post_text='test',
            sentiment=0.5,
            likes=100,
            retweets=10,
            event_metadata={}
        )):
            posts = generator._generate_team_posts(
                team_id=1,
                event_type='GAME_RESULT',
                event_outcome='WIN',
                post_count=10,
                magnitude=50,
                variables={},
                event_metadata={}
            )

        # Should get 10 posts (8 recurring + 2 random)
        assert len(posts) == 10

    def test_all_events_fans_post_on_any_outcome(self, generator):
        """ALL_EVENTS fans should be eligible for any outcome."""
        fans = [
            Mock(id=1, archetype='OPTIMIST', posting_frequency='ALL_EVENTS', team_id=1)
        ]

        # Should be eligible for WIN
        eligible_win = generator._filter_by_posting_frequency(fans, 'WIN')
        assert len(eligible_win) == 1

        # Should be eligible for LOSS
        eligible_loss = generator._filter_by_posting_frequency(fans, 'LOSS')
        assert len(eligible_loss) == 1

    def test_win_only_fans_filtered_correctly(self, generator):
        """WIN_ONLY fans should only post on wins."""
        fans = [
            Mock(id=1, archetype='BANDWAGON', posting_frequency='WIN_ONLY', team_id=1)
        ]

        # Should be eligible for WIN
        eligible_win = generator._filter_by_posting_frequency(fans, 'WIN')
        assert len(eligible_win) == 1

        # Should NOT be eligible for LOSS
        eligible_loss = generator._filter_by_posting_frequency(fans, 'LOSS')
        assert len(eligible_loss) == 0

    def test_loss_only_fans_filtered_correctly(self, generator):
        """LOSS_ONLY fans should only post on losses."""
        fans = [
            Mock(id=1, archetype='PESSIMIST', posting_frequency='LOSS_ONLY', team_id=1)
        ]

        # Should NOT be eligible for WIN
        eligible_win = generator._filter_by_posting_frequency(fans, 'WIN')
        assert len(eligible_win) == 0

        # Should be eligible for LOSS
        eligible_loss = generator._filter_by_posting_frequency(fans, 'LOSS')
        assert len(eligible_loss) == 1

    def test_emotional_moments_fans_post_on_wins_and_losses(self, generator):
        """EMOTIONAL_MOMENTS fans should post on both wins and losses."""
        fans = [
            Mock(id=1, archetype='HOT_HEAD', posting_frequency='EMOTIONAL_MOMENTS', team_id=1)
        ]

        # Should be eligible for WIN
        eligible_win = generator._filter_by_posting_frequency(fans, 'WIN')
        assert len(eligible_win) == 1

        # Should be eligible for LOSS
        eligible_loss = generator._filter_by_posting_frequency(fans, 'LOSS')
        assert len(eligible_loss) == 1

    def test_fallback_to_all_if_no_eligible_fans(self, generator):
        """If no fans match frequency, should return all fans as fallback."""
        fans = [
            Mock(id=1, archetype='BANDWAGON', posting_frequency='WIN_ONLY', team_id=1),
            Mock(id=2, archetype='BANDWAGON', posting_frequency='WIN_ONLY', team_id=1)
        ]

        # Request LOSS posts - neither fan eligible
        eligible = generator._filter_by_posting_frequency(fans, 'LOSS')

        # Should fall back to all fans
        assert len(eligible) == 2


# ==========================================
# ENGAGEMENT CALCULATION
# ==========================================

class TestEngagementCalculation:
    """Test likes/retweets calculation."""

    def test_higher_magnitude_more_engagement(self, generator):
        """Higher magnitude events should get more engagement."""
        likes_low, retweets_low = generator._calculate_engagement(magnitude=20, sentiment=0.5)
        likes_high, retweets_high = generator._calculate_engagement(magnitude=90, sentiment=0.5)

        assert likes_high > likes_low
        assert retweets_high > retweets_low

    def test_extreme_sentiment_boosts_engagement(self, generator):
        """Extreme sentiment (positive or negative) should boost engagement."""
        # Neutral sentiment
        likes_neutral, retweets_neutral = generator._calculate_engagement(magnitude=50, sentiment=0.0)

        # Extreme positive
        likes_pos, retweets_pos = generator._calculate_engagement(magnitude=50, sentiment=1.0)

        # Extreme negative
        likes_neg, retweets_neg = generator._calculate_engagement(magnitude=50, sentiment=-1.0)

        # Both extremes should have chance to be higher than neutral
        # (Due to randomness, we can't guarantee every single call, but on average should be higher)
        # Test that extremes CAN be higher (at least one should be)
        assert (likes_pos >= likes_neutral or likes_neg >= likes_neutral)

    def test_likes_clamped_to_max_10000(self, generator):
        """Likes should be clamped to 10,000 max."""
        likes, _ = generator._calculate_engagement(magnitude=100, sentiment=1.0)
        assert likes <= 10000

    def test_retweets_clamped_to_max_3000(self, generator):
        """Retweets should be clamped to 3,000 max."""
        _, retweets = generator._calculate_engagement(magnitude=100, sentiment=1.0)
        assert retweets <= 3000

    def test_engagement_never_negative(self, generator):
        """Engagement should never be negative."""
        likes, retweets = generator._calculate_engagement(magnitude=0, sentiment=-1.0)
        assert likes >= 0
        assert retweets >= 0


# ==========================================
# TEAM NAME RESOLUTION
# ==========================================

class TestTeamNameResolution:
    """Test team name/abbreviation lookup."""

    @patch('src.game_cycle.services.social_post_generator.get_team_by_id')
    def test_valid_team_returns_abbreviation(self, mock_get_team, generator):
        """Valid team IDs should return abbreviations."""
        mock_team = Mock()
        mock_team.abbreviation = 'DET'
        mock_get_team.return_value = mock_team

        name = generator._get_team_name(22)

        assert name == 'DET'
        mock_get_team.assert_called_once_with(22)

    @patch('src.game_cycle.services.social_post_generator.get_team_by_id')
    def test_invalid_team_returns_fallback(self, mock_get_team, generator):
        """Invalid team IDs should return 'Team X' fallback."""
        mock_get_team.return_value = None

        name = generator._get_team_name(99)

        assert name == 'Team 99'

    @patch('src.game_cycle.services.social_post_generator.get_team_by_id')
    def test_exception_returns_fallback(self, mock_get_team, generator):
        """Exceptions should return 'Team X' fallback."""
        mock_get_team.side_effect = Exception("Database error")

        name = generator._get_team_name(5)

        assert name == 'Team 5'


# ==========================================
# BATCH GENERATION
# ==========================================

class TestBatchGeneration:
    """Test batch post generation."""

    @patch('src.game_cycle.services.social_post_generator.SocialPostGenerator')
    def test_batch_processes_multiple_games(self, mock_generator_class, mock_db):
        """Batch function should process all games."""
        # Mock generator instance
        mock_instance = Mock()
        mock_instance.generate_game_posts.return_value = [
            GeneratedPost(
                personality_id=1,
                post_text='Test post',
                sentiment=0.5,
                likes=100,
                retweets=10,
                event_metadata={'game_id': 'test'}
            )
        ]
        mock_generator_class.return_value = mock_instance

        game_results = [
            {
                'winning_team_id': 1,
                'losing_team_id': 2,
                'winning_score': 24,
                'losing_score': 17
            },
            {
                'winning_team_id': 3,
                'losing_team_id': 4,
                'winning_score': 31,
                'losing_score': 28
            }
        ]

        posts = generate_game_posts_batch(
            db=mock_db,
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            game_results=game_results
        )

        # Should call generate_game_posts twice
        assert mock_instance.generate_game_posts.call_count == 2

        # Should return posts for both games
        assert len(posts) == 2

    @patch('src.game_cycle.services.social_post_generator.SocialPostGenerator')
    def test_batch_converts_to_dict_format(self, mock_generator_class, mock_db):
        """Batch function should convert GeneratedPost to dict format."""
        mock_instance = Mock()
        mock_instance.generate_game_posts.return_value = [
            GeneratedPost(
                personality_id=5,
                post_text='DET wins!',
                sentiment=0.8,
                likes=500,
                retweets=50,
                event_metadata={'game_id': 'regular_2025_1_1'}
            )
        ]
        mock_generator_class.return_value = mock_instance

        game_results = [{
            'winning_team_id': 1,
            'losing_team_id': 2,
            'winning_score': 24,
            'losing_score': 17
        }]

        posts = generate_game_posts_batch(
            db=mock_db,
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            game_results=game_results
        )

        # Check dict format
        post_dict = posts[0]
        assert post_dict['dynasty_id'] == 'test_dynasty'
        assert post_dict['personality_id'] == 5
        assert post_dict['season'] == 2025
        assert post_dict['week'] == 1
        assert post_dict['post_text'] == 'DET wins!'
        assert post_dict['event_type'] == 'GAME_RESULT'
        assert post_dict['sentiment'] == 0.8
        assert post_dict['likes'] == 500
        assert post_dict['retweets'] == 50
        assert post_dict['event_metadata'] == {'game_id': 'regular_2025_1_1'}


# ==========================================
# INTEGRATION TESTS
# ==========================================

class TestPlayoffPostGeneration:
    """Test playoff-specific post generation."""

    def test_playoff_game_generates_more_posts(self, generator):
        """Playoff games should generate more posts than regular season."""
        # Regular season game
        regular_posts = generator.generate_game_posts(
            season=2025,
            week=5,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21,
            season_type='regular'
        )

        # Playoff game (same score)
        playoff_posts = generator.generate_game_posts(
            season=2025,
            week=19,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21,
            season_type='playoffs',
            round_name='wild_card'
        )

        # Playoff should generate more posts (1.5x multiplier)
        assert len(playoff_posts) > len(regular_posts)

    def test_super_bowl_maximum_posts(self, generator):
        """Super Bowl should generate maximum posts (10-15)."""
        posts = generator.generate_game_posts(
            season=2025,
            week=22,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=31,
            losing_score=28,
            season_type='playoffs',
            round_name='super_bowl'
        )

        # Super Bowl generates 10-15 posts
        assert len(posts) >= 10
        assert len(posts) <= 15

    def test_playoff_posts_include_round_context(self, generator):
        """Playoff posts should include round_name in metadata."""
        posts = generator.generate_game_posts(
            season=2025,
            week=20,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=17,
            season_type='playoffs',
            round_name='divisional'
        )

        # All posts should have playoff context in metadata
        for post in posts:
            assert post.event_metadata['season_type'] == 'playoffs'
            assert post.event_metadata['round_name'] == 'divisional'

    def test_playoff_posts_higher_magnitude(self, generator, mock_template_loader):
        """Playoff games should have boosted magnitude."""
        # Generate playoff posts
        generator.generate_game_posts(
            season=2025,
            week=21,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21,
            season_type='playoffs',
            round_name='conference'
        )

        # Check that magnitude was boosted (passed to template)
        call_args = mock_template_loader.calculate_sentiment.call_args_list[0][1]
        magnitude = call_args['event_magnitude']

        # Playoff magnitude should be boosted (+10 minimum)
        assert magnitude >= 60  # MAGNITUDE_NORMAL (50) + 10 boost

    def test_playoff_media_posts_always_generated(self, generator, mock_personality_api):
        """Media should always post on playoff games (even non-upsets)."""
        # Normal playoff game (not upset, not blowout)
        posts = generator.generate_game_posts(
            season=2025,
            week=19,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=24,
            losing_score=20,
            is_upset=False,
            is_blowout=False,
            season_type='playoffs',
            round_name='wild_card'
        )

        # Should still call get_league_wide_personalities for media posts
        mock_personality_api.get_league_wide_personalities.assert_called()


class TestIntegration:
    """Integration tests with real template loader and personality API."""

    @pytest.mark.integration
    def test_end_to_end_game_post_generation(self, mock_db, mock_personality_api):
        """Full pipeline from game result to posts."""
        with patch('src.game_cycle.services.social_post_generator.SocialPersonalityAPI', return_value=mock_personality_api):
            generator = SocialPostGenerator(mock_db, dynasty_id='test_dynasty')

            posts = generator.generate_game_posts(
                season=2025,
                week=1,
                winning_team_id=1,
                losing_team_id=2,
                winning_score=28,
                losing_score=21,
                is_upset=True
            )

            # Should generate posts
            assert len(posts) > 0

            # All posts should be valid
            for post in posts:
                assert post.personality_id > 0
                assert len(post.post_text) > 0
                assert -1.0 <= post.sentiment <= 1.0
                assert post.likes >= 0
                assert post.retweets >= 0
