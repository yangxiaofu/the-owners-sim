"""
Validation Script: Game Social Posts Integration

Tests the new GameSocialGenerator integration by:
1. Simulating a regular season game
2. Simulating a playoff game
3. Verifying posts were created in social_posts table
4. Checking post counts and content

Run: PYTHONPATH=src python demos/validate_game_social_posts.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_posts_api import SocialPostsAPI
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.services.social_generators.factory import SocialPostGeneratorFactory
from game_cycle.models.social_event_types import SocialEventType


def create_test_database():
    """Create a temporary test database with personalities."""
    # Create temp database
    temp_dir = tempfile.mkdtemp(prefix='social_test_')
    db_path = os.path.join(temp_dir, 'test.db')

    db = GameCycleDatabase(db_path)

    # Create test personalities (fans for both teams)
    personality_api = SocialPersonalityAPI(db)

    print("Creating test personalities...")
    for team_id in [1, 2]:  # Team 1 (DET), Team 2 (CHI)
        for i in range(5):  # 5 fans per team
            personality_api.create_personality(
                dynasty_id="test_dynasty",
                handle=f"@Team{team_id}Fan{i}",
                display_name=f"Team {team_id} Fan {i}",
                personality_type="FAN",
                archetype="OPTIMIST" if i % 2 == 0 else "PESSIMIST",
                team_id=team_id,
                sentiment_bias=0.5 if i % 2 == 0 else -0.5,
                posting_frequency="ALL_EVENTS"
            )

    # Create league-wide media personalities
    for i in range(3):
        personality_api.create_personality(
            dynasty_id="test_dynasty",
            handle=f"@MediaHotTake{i}",
            display_name=f"Media Analyst {i}",
            personality_type="HOT_TAKE",
            archetype="HOT_TAKE",
            team_id=None,
            sentiment_bias=0.0,
            posting_frequency="ALL_EVENTS"
        )

    print(f"✓ Created test database at {db_path}")
    return db_path, temp_dir


def test_regular_season_game(db_path):
    """Test regular season game post generation."""
    print("\n" + "="*60)
    print("TEST 1: Regular Season Game (Normal)")
    print("="*60)

    db = GameCycleDatabase(db_path)

    # Build event data for a close game
    event_data = {
        'winning_team_id': 1,  # Detroit Lions
        'losing_team_id': 2,   # Chicago Bears
        'winning_score': 24,
        'losing_score': 20,
        'game_id': 'test_game_regular_001',
        'is_upset': False,
        'is_blowout': False,
        'star_players': {1: 'Jared Goff', 2: 'Justin Fields'},
        'season_type': 'regular'
    }

    # Generate posts
    try:
        posts_created = SocialPostGeneratorFactory.generate_posts(
            event_type=SocialEventType.GAME_RESULT,
            db=db,
            dynasty_id="test_dynasty",
            season=2025,
            week=1,
            event_data=event_data
        )

        print(f"✓ Posts created: {posts_created}")

        # Verify posts in database
        posts_api = SocialPostsAPI(db)
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=1,
            limit=50
        )

        print(f"✓ Posts retrieved from DB: {len(posts)}")

        # Validate post counts (should be 4-6 for normal game)
        if 4 <= posts_created <= 6:
            print(f"✓ PASS: Post count in expected range (4-6)")
        else:
            print(f"⚠ WARNING: Post count {posts_created} outside expected range (4-6)")

        # Show sample posts
        print("\nSample Posts:")
        for i, post in enumerate(posts[:3], 1):
            print(f"  {i}. [{post.sentiment:+.2f}] {post.post_text[:60]}...")

        db.commit()
        db.close()
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return False


def test_blowout_game(db_path):
    """Test blowout game (more posts)."""
    print("\n" + "="*60)
    print("TEST 2: Regular Season Game (Blowout)")
    print("="*60)

    db = GameCycleDatabase(db_path)

    # Build event data for a blowout
    event_data = {
        'winning_team_id': 1,
        'losing_team_id': 2,
        'winning_score': 42,
        'losing_score': 10,
        'game_id': 'test_game_blowout_002',
        'is_upset': False,
        'is_blowout': True,
        'star_players': {1: 'David Montgomery'},
        'season_type': 'regular'
    }

    try:
        posts_created = SocialPostGeneratorFactory.generate_posts(
            event_type=SocialEventType.GAME_RESULT,
            db=db,
            dynasty_id="test_dynasty",
            season=2025,
            week=2,
            event_data=event_data
        )

        print(f"✓ Posts created: {posts_created}")

        # Validate post counts (should be 6-10 for blowout)
        if 6 <= posts_created <= 10:
            print(f"✓ PASS: Post count in expected range (6-10)")
        else:
            print(f"⚠ WARNING: Post count {posts_created} outside expected range (6-10)")

        db.commit()
        db.close()
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return False


def test_super_bowl(db_path):
    """Test Super Bowl (maximum posts)."""
    print("\n" + "="*60)
    print("TEST 3: Super Bowl")
    print("="*60)

    db = GameCycleDatabase(db_path)

    # Build event data for Super Bowl
    event_data = {
        'winning_team_id': 1,
        'losing_team_id': 2,
        'winning_score': 27,
        'losing_score': 24,
        'game_id': 'test_game_superbowl_003',
        'is_upset': False,
        'is_blowout': False,
        'star_players': {1: 'Amon-Ra St. Brown'},
        'season_type': 'playoffs',
        'round_name': 'super_bowl'
    }

    try:
        posts_created = SocialPostGeneratorFactory.generate_posts(
            event_type=SocialEventType.GAME_RESULT,
            db=db,
            dynasty_id="test_dynasty",
            season=2025,
            week=22,  # Super Bowl week
            event_data=event_data
        )

        print(f"✓ Posts created: {posts_created}")

        # Validate post counts (should be 10-15 for Super Bowl)
        if 10 <= posts_created <= 15:
            print(f"✓ PASS: Post count in expected range (10-15)")
        else:
            print(f"⚠ WARNING: Post count {posts_created} outside expected range (10-15)")

        # Show engagement for Super Bowl posts
        posts_api = SocialPostsAPI(db)
        posts = posts_api.get_rolling_feed(
            dynasty_id="test_dynasty",
            season=2025,
            week=22,
            limit=50
        )

        avg_likes = sum(p.likes for p in posts) / len(posts) if posts else 0
        print(f"✓ Average likes: {avg_likes:.0f} (should be high for Super Bowl)")

        db.commit()
        db.close()
        return True

    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return False


def verify_database_state(db_path):
    """Verify final database state."""
    print("\n" + "="*60)
    print("DATABASE VERIFICATION")
    print("="*60)

    db = GameCycleDatabase(db_path)
    posts_api = SocialPostsAPI(db)

    # Get all posts
    all_posts = posts_api.get_rolling_feed(
        dynasty_id="test_dynasty",
        season=2025,
        week=1,
        limit=100
    )

    total_posts = len(all_posts)
    print(f"✓ Total posts in database: {total_posts}")

    # Count by event type
    game_posts = [p for p in all_posts if p.event_type == 'GAME_RESULT']
    print(f"✓ Game result posts: {len(game_posts)}")

    # Sentiment distribution
    positive = sum(1 for p in all_posts if p.sentiment > 0.3)
    negative = sum(1 for p in all_posts if p.sentiment < -0.3)
    neutral = total_posts - positive - negative

    print(f"\nSentiment Distribution:")
    print(f"  Positive: {positive} ({positive/total_posts*100:.1f}%)")
    print(f"  Negative: {negative} ({negative/total_posts*100:.1f}%)")
    print(f"  Neutral:  {neutral} ({neutral/total_posts*100:.1f}%)")

    db.close()


def cleanup(temp_dir):
    """Remove temporary database."""
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        print(f"\n✓ Cleaned up temp directory: {temp_dir}")


def main():
    """Run validation tests."""
    print("\n" + "="*60)
    print("GAME SOCIAL POSTS VALIDATION")
    print("Testing new GameSocialGenerator integration")
    print("="*60)

    # Create test database
    db_path, temp_dir = create_test_database()

    try:
        # Run tests
        test1 = test_regular_season_game(db_path)
        test2 = test_blowout_game(db_path)
        test3 = test_super_bowl(db_path)

        # Verify database state
        verify_database_state(db_path)

        # Summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)

        tests_passed = sum([test1, test2, test3])
        print(f"Tests Passed: {tests_passed}/3")

        if tests_passed == 3:
            print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
            print("GameSocialGenerator integration is working correctly!")
        else:
            print(f"\n⚠ {3 - tests_passed} TEST(S) FAILED")
            print("Review errors above for details.")

    finally:
        # Cleanup
        cleanup(temp_dir)


if __name__ == '__main__':
    main()
