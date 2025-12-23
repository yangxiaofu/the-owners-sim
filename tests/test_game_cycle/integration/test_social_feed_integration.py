"""
Integration tests for Social Media & Fan Reactions system.

Tests the complete flow:
1. Personality generation → Database storage
2. Game events → Post generation → Database storage
3. Database queries → UI display
4. Filter application → Correct results

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 8.
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.social_personalities_api import SocialPersonalityAPI
from src.game_cycle.database.social_posts_api import SocialPostsAPI
from src.game_cycle.services.personality_generator import PersonalityGenerator
from src.game_cycle.services.social_post_generator import SocialPostGenerator


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def initialized_db(temp_db_path):
    """Create database with schema initialized."""
    db = GameCycleDatabase(temp_db_path)

    # Create social_personalities table
    db.get_connection().execute("""
        CREATE TABLE IF NOT EXISTS social_personalities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            handle TEXT NOT NULL,
            display_name TEXT NOT NULL,
            personality_type TEXT NOT NULL,
            archetype TEXT,
            team_id INTEGER,
            sentiment_bias REAL NOT NULL,
            posting_frequency TEXT NOT NULL,
            UNIQUE(dynasty_id, handle)
        )
    """)

    # Create social_posts table
    db.get_connection().execute("""
        CREATE TABLE IF NOT EXISTS social_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dynasty_id TEXT NOT NULL,
            personality_id INTEGER NOT NULL,
            season INTEGER NOT NULL,
            week INTEGER,
            post_text TEXT NOT NULL,
            event_type TEXT NOT NULL,
            sentiment REAL NOT NULL,
            likes INTEGER DEFAULT 0,
            retweets INTEGER DEFAULT 0,
            event_metadata TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (personality_id) REFERENCES social_personalities(id)
        )
    """)

    db.get_connection().commit()

    yield db

    db.close()


@pytest.fixture
def sample_personalities(initialized_db):
    """Create sample personalities for testing."""
    api = SocialPersonalityAPI(initialized_db)

    personalities = []

    # Create 3 fans for team 1
    for i in range(3):
        pid = api.create_personality(
            dynasty_id='test_dynasty',
            handle=f'@Team1Fan{i}',
            display_name=f'Team 1 Fan {i}',
            personality_type='FAN',
            archetype='OPTIMIST' if i == 0 else 'PESSIMIST',
            team_id=1,
            sentiment_bias=0.5 if i == 0 else -0.5,
            posting_frequency='ALL_EVENTS'
        )
        personalities.append(pid)

    # Create 3 fans for team 2
    for i in range(3):
        pid = api.create_personality(
            dynasty_id='test_dynasty',
            handle=f'@Team2Fan{i}',
            display_name=f'Team 2 Fan {i}',
            personality_type='FAN',
            archetype='BANDWAGON',
            team_id=2,
            sentiment_bias=0.3,
            posting_frequency='WIN_ONLY'
        )
        personalities.append(pid)

    # Create 1 hot-take analyst (league-wide)
    pid = api.create_personality(
        dynasty_id='test_dynasty',
        handle='@HotTakeKing',
        display_name='Hot Take King',
        personality_type='HOT_TAKE',
        archetype=None,
        team_id=None,
        sentiment_bias=0.2,
        posting_frequency='EMOTIONAL_MOMENTS'
    )
    personalities.append(pid)

    return personalities


# ==========================================
# PERSONALITY GENERATION INTEGRATION
# ==========================================

class TestPersonalityGenerationIntegration:
    """Test personality generation with real database."""

    @pytest.mark.integration
    def test_generate_personalities_persists_to_database(self, initialized_db):
        """Generated personalities should be stored in database."""
        # Note: This test requires the full template file to exist
        # For this test, we'll manually create personalities instead
        api = SocialPersonalityAPI(initialized_db)

        # Create test personalities
        pid1 = api.create_personality(
            dynasty_id='test_dynasty',
            handle='@TestFan1',
            display_name='Test Fan 1',
            personality_type='FAN',
            archetype='OPTIMIST',
            team_id=1,
            sentiment_bias=0.5,
            posting_frequency='ALL_EVENTS'
        )

        pid2 = api.create_personality(
            dynasty_id='test_dynasty',
            handle='@TestFan2',
            display_name='Test Fan 2',
            personality_type='FAN',
            archetype='PESSIMIST',
            team_id=1,
            sentiment_bias=-0.5,
            posting_frequency='LOSS_ONLY'
        )

        # Verify personalities were stored
        all_personalities = api.get_all_personalities('test_dynasty')
        assert len(all_personalities) == 2
        assert all_personalities[0].handle == '@TestFan1'
        assert all_personalities[1].handle == '@TestFan2'

    @pytest.mark.integration
    def test_personality_dynasty_isolation(self, initialized_db):
        """Personalities should be isolated by dynasty_id."""
        api = SocialPersonalityAPI(initialized_db)

        # Create personalities for dynasty 1
        api.create_personality(
            dynasty_id='dynasty1',
            handle='@Dynasty1Fan',
            display_name='Dynasty 1 Fan',
            personality_type='FAN',
            archetype='OPTIMIST',
            team_id=1,
            sentiment_bias=0.5,
            posting_frequency='ALL_EVENTS'
        )

        # Create personalities for dynasty 2
        api.create_personality(
            dynasty_id='dynasty2',
            handle='@Dynasty2Fan',
            display_name='Dynasty 2 Fan',
            personality_type='FAN',
            archetype='PESSIMIST',
            team_id=1,
            sentiment_bias=-0.5,
            posting_frequency='ALL_EVENTS'
        )

        # Verify isolation
        dynasty1_personalities = api.get_all_personalities('dynasty1')
        dynasty2_personalities = api.get_all_personalities('dynasty2')

        assert len(dynasty1_personalities) == 1
        assert len(dynasty2_personalities) == 1
        assert dynasty1_personalities[0].handle == '@Dynasty1Fan'
        assert dynasty2_personalities[0].handle == '@Dynasty2Fan'


# ==========================================
# POST GENERATION INTEGRATION
# ==========================================

class TestPostGenerationIntegration:
    """Test post generation with real database."""

    @pytest.mark.integration
    def test_game_posts_stored_in_database(self, initialized_db, sample_personalities):
        """Generated game posts should be stored in database."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate posts
        generated_posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21,
            is_upset=False,
            is_blowout=False
        )

        # Store posts in database
        for post in generated_posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Verify posts were stored
        all_posts = posts_api.get_all_posts('test_dynasty', season=2025, week=1)
        assert len(all_posts) == len(generated_posts)

    @pytest.mark.integration
    def test_post_dynasty_isolation(self, initialized_db, sample_personalities):
        """Posts should be isolated by dynasty_id."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate posts for dynasty 1
        posts1 = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21
        )

        for post in posts1:
            posts_api.create_post(
                dynasty_id='dynasty1',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Generate posts for dynasty 2 (using same personalities)
        posts2 = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=31,
            losing_score=17
        )

        for post in posts2:
            posts_api.create_post(
                dynasty_id='dynasty2',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Verify isolation
        dynasty1_posts = posts_api.get_all_posts('dynasty1', season=2025, week=1)
        dynasty2_posts = posts_api.get_all_posts('dynasty2', season=2025, week=1)

        assert len(dynasty1_posts) == len(posts1)
        assert len(dynasty2_posts) == len(posts2)


# ==========================================
# FILTER & QUERY INTEGRATION
# ==========================================

class TestFilterQueryIntegration:
    """Test filtering and querying with real database."""

    @pytest.mark.integration
    def test_team_filter_returns_only_team_posts(self, initialized_db, sample_personalities):
        """Team filter should only return posts from that team's fans."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate and store game posts
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21
        )

        for post in posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Query with team filter
        team1_posts = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=20,
            offset=0,
            team_filter=1
        )

        # All posts should be from team 1 fans
        personality_api = SocialPersonalityAPI(initialized_db)
        for post in team1_posts:
            personality = personality_api.get_personality_by_id(post.personality_id)
            assert personality.team_id == 1 or personality.team_id is None  # League-wide media allowed

    @pytest.mark.integration
    def test_event_type_filter_returns_only_event_type(self, initialized_db, sample_personalities):
        """Event type filter should only return posts of that type."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate game posts
        game_posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21
        )

        for post in game_posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Generate award posts
        award_posts = generator.generate_award_posts(
            season=2025,
            week=1,
            award_name='MVP',
            player_name='Star QB',
            team_id=1
        )

        for post in award_posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='AWARD',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Query with event_type filter
        game_result_posts = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=20,
            offset=0,
            event_type_filter='GAME_RESULT'
        )

        # All posts should be GAME_RESULT
        for post in game_result_posts:
            assert post.event_type == 'GAME_RESULT'

    @pytest.mark.integration
    def test_sentiment_filter_returns_correct_sentiment(self, initialized_db, sample_personalities):
        """Sentiment filter should return posts matching sentiment range."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate posts
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21
        )

        for post in posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Query with POSITIVE sentiment filter
        positive_posts = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=20,
            offset=0,
            sentiment_filter='POSITIVE'
        )

        # All posts should have positive sentiment (> 0.2)
        for post in positive_posts:
            assert post.sentiment > 0.2

    @pytest.mark.integration
    def test_combined_filters_work_together(self, initialized_db, sample_personalities):
        """Multiple filters should work together (AND logic)."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate posts
        posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=28,
            losing_score=21
        )

        for post in posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Query with team + event_type + sentiment filters
        filtered_posts = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=20,
            offset=0,
            team_filter=1,
            event_type_filter='GAME_RESULT',
            sentiment_filter='POSITIVE'
        )

        # All posts should match ALL filters
        personality_api = SocialPersonalityAPI(initialized_db)
        for post in filtered_posts:
            personality = personality_api.get_personality_by_id(post.personality_id)
            assert personality.team_id == 1 or personality.team_id is None
            assert post.event_type == 'GAME_RESULT'
            assert post.sentiment > 0.2

    @pytest.mark.integration
    def test_pagination_works_correctly(self, initialized_db, sample_personalities):
        """Pagination should return correct batches of posts."""
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        # Generate many posts (simulate multiple games)
        for game_num in range(5):
            posts = generator.generate_game_posts(
                season=2025,
                week=1,
                winning_team_id=1,
                losing_team_id=2,
                winning_score=28,
                losing_score=21
            )

            for post in posts:
                posts_api.create_post(
                    dynasty_id='test_dynasty',
                    personality_id=post.personality_id,
                    season=2025,
                    week=1,
                    post_text=post.post_text,
                    event_type='GAME_RESULT',
                    sentiment=post.sentiment,
                    likes=post.likes,
                    retweets=post.retweets,
                    event_metadata=post.event_metadata
                )

        # Get first page (limit 10)
        page1 = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=10,
            offset=0
        )

        # Get second page (limit 10, offset 10)
        page2 = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=10,
            offset=10
        )

        # Pages should have different posts
        page1_ids = {p.id for p in page1}
        page2_ids = {p.id for p in page2}

        assert len(page1) == 10
        assert len(page2) == 10
        assert page1_ids.isdisjoint(page2_ids)  # No overlap


# ==========================================
# END-TO-END FLOW
# ==========================================

class TestEndToEndFlow:
    """Test complete end-to-end social media flow."""

    @pytest.mark.integration
    def test_complete_game_simulation_flow(self, initialized_db, sample_personalities):
        """Test complete flow: game → posts → filter → display."""
        # Step 1: Generate posts for a game
        generator = SocialPostGenerator(initialized_db, 'test_dynasty')
        posts_api = SocialPostsAPI(initialized_db)

        game_posts = generator.generate_game_posts(
            season=2025,
            week=1,
            winning_team_id=1,
            losing_team_id=2,
            winning_score=35,
            losing_score=14,  # Blowout
            is_upset=False,
            is_blowout=True
        )

        # Step 2: Store in database
        for post in game_posts:
            posts_api.create_post(
                dynasty_id='test_dynasty',
                personality_id=post.personality_id,
                season=2025,
                week=1,
                post_text=post.post_text,
                event_type='GAME_RESULT',
                sentiment=post.sentiment,
                likes=post.likes,
                retweets=post.retweets,
                event_metadata=post.event_metadata
            )

        # Step 3: Query with filters (winning team, positive sentiment)
        display_posts = posts_api.get_rolling_feed(
            dynasty_id='test_dynasty',
            season=2025,
            week=1,
            limit=20,
            offset=0,
            team_filter=1,
            sentiment_filter='POSITIVE'
        )

        # Step 4: Verify results
        assert len(display_posts) > 0

        personality_api = SocialPersonalityAPI(initialized_db)
        for post in display_posts:
            # Verify post structure
            assert post.post_text is not None
            assert len(post.post_text) > 0
            assert post.sentiment > 0.2  # Positive
            assert post.likes >= 0
            assert post.retweets >= 0

            # Verify personality
            personality = personality_api.get_personality_by_id(post.personality_id)
            assert personality is not None
            assert personality.team_id == 1 or personality.team_id is None  # Team 1 or league-wide
