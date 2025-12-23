"""
Direct Validation: Social Generators (No Handler Dependencies)

Tests generators directly without importing full handler stack.

Run: python demos/validate_social_generators_direct.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

# Direct imports (avoid handler import chain)
from game_cycle.database.connection import GameCycleDatabase
from game_cycle.database.social_posts_api import SocialPostsAPI
from game_cycle.database.social_personalities_api import SocialPersonalityAPI
from game_cycle.services.social_generators.game_generator import GameSocialGenerator
from game_cycle.services.social_generators.factory import SocialPostGeneratorFactory
from game_cycle.models.social_event_types import SocialEventType


def create_test_personalities(db, dynasty_id="test"):
    """Create test personalities."""
    personality_api = SocialPersonalityAPI(db)

    print("Creating test personalities...")
    # Team fans
    for team_id in [1, 2]:
        for i in range(5):
            personality_api.create_personality(
                dynasty_id=dynasty_id,
                handle=f"@T{team_id}Fan{i}",
                display_name=f"Team {team_id} Fan {i}",
                personality_type="FAN",
                archetype="OPTIMIST" if i % 2 == 0 else "PESSIMIST",
                team_id=team_id,
                sentiment_bias=0.5,
                posting_frequency="ALL_EVENTS"
            )

    # Media
    for i in range(2):
        personality_api.create_personality(
            dynasty_id=dynasty_id,
            handle=f"@Media{i}",
            display_name=f"Media {i}",
            personality_type="HOT_TAKE",
            archetype="HOT_TAKE",
            team_id=None,
            sentiment_bias=0.0,
            posting_frequency="ALL_EVENTS"
        )

    print(f"✓ Created personalities")


def test_factory_dispatch():
    """Test 1: Factory correctly dispatches to GameSocialGenerator."""
    print("\n" + "="*60)
    print("TEST 1: Factory Dispatch")
    print("="*60)

    try:
        # Check factory registration
        assert SocialEventType.GAME_RESULT in SocialPostGeneratorFactory._GENERATOR_MAP
        assert SocialEventType.PLAYOFF_GAME in SocialPostGeneratorFactory._GENERATOR_MAP
        assert SocialEventType.SUPER_BOWL in SocialPostGeneratorFactory._GENERATOR_MAP

        from game_cycle.services.social_generators.game_generator import GameSocialGenerator
        generator_class = SocialPostGeneratorFactory._GENERATOR_MAP[SocialEventType.GAME_RESULT]
        assert generator_class == GameSocialGenerator

        print("✓ PASS: Factory correctly maps GAME_RESULT to GameSocialGenerator")
        return True
    except AssertionError as e:
        print(f"✗ FAIL: {e}")
        return False


def test_regular_game():
    """Test 2: Regular season game posts."""
    print("\n" + "="*60)
    print("TEST 2: Regular Season Game")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='social_')
    db_path = os.path.join(temp_dir, 'test.db')

    try:
        db = GameCycleDatabase(db_path)
        create_test_personalities(db)

        event_data = {
            'winning_team_id': 1,
            'losing_team_id': 2,
            'winning_score': 24,
            'losing_score': 20,
            'game_id': 'test_001',
            'is_upset': False,
            'is_blowout': False,
            'season_type': 'regular'
        }

        posts_created = SocialPostGeneratorFactory.generate_posts(
            event_type=SocialEventType.GAME_RESULT,
            db=db,
            dynasty_id="test",
            season=2025,
            week=1,
            event_data=event_data
        )

        print(f"Posts created: {posts_created}")

        # Verify in DB
        posts_api = SocialPostsAPI(db)
        posts = posts_api.get_rolling_feed("test", 2025, 1, limit=50)

        print(f"Posts in DB: {len(posts)}")
        print(f"Expected range: 4-6")

        if 4 <= posts_created <= 6:
            print("✓ PASS: Post count in expected range")
            success = True
        else:
            print(f"✗ FAIL: Post count {posts_created} outside range")
            success = False

        # Show samples
        if posts:
            print("\nSample posts:")
            for p in posts[:2]:
                print(f"  - [{p.sentiment:+.2f}] {p.post_text[:50]}...")

        db.commit()
        db.close()
        shutil.rmtree(temp_dir)
        return success

    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False


def test_super_bowl():
    """Test 3: Super Bowl posts (maximum engagement)."""
    print("\n" + "="*60)
    print("TEST 3: Super Bowl")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='social_')
    db_path = os.path.join(temp_dir, 'test.db')

    try:
        db = GameCycleDatabase(db_path)
        create_test_personalities(db)

        event_data = {
            'winning_team_id': 1,
            'losing_team_id': 2,
            'winning_score': 27,
            'losing_score': 24,
            'game_id': 'superbowl_001',
            'is_upset': False,
            'is_blowout': False,
            'season_type': 'playoffs',
            'round_name': 'super_bowl'
        }

        posts_created = SocialPostGeneratorFactory.generate_posts(
            event_type=SocialEventType.GAME_RESULT,
            db=db,
            dynasty_id="test",
            season=2025,
            week=22,
            event_data=event_data
        )

        print(f"Posts created: {posts_created}")
        print(f"Expected range: 10-15")

        # Check engagement levels
        posts_api = SocialPostsAPI(db)
        posts = posts_api.get_rolling_feed("test", 2025, 22, limit=50)

        if posts:
            avg_likes = sum(p.likes for p in posts) / len(posts)
            print(f"Average likes: {avg_likes:.0f}")
            print(f"Average retweets: {sum(p.retweets for p in posts) / len(posts):.0f}")

        if 10 <= posts_created <= 15:
            print("✓ PASS: Post count in expected range")
            success = True
        else:
            print(f"✗ FAIL: Post count {posts_created} outside range")
            success = False

        db.commit()
        db.close()
        shutil.rmtree(temp_dir)
        return success

    except Exception as e:
        print(f"✗ FAIL: {e}")
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return False


def main():
    """Run validation."""
    print("="*60)
    print("SOCIAL GENERATORS VALIDATION")
    print("="*60)

    results = []
    results.append(("Factory Dispatch", test_factory_dispatch()))
    results.append(("Regular Game", test_regular_game()))
    results.append(("Super Bowl", test_super_bowl()))

    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)

    passed = sum(1 for _, success in results if success)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("\n✓✓✓ ALL TESTS PASSED ✓✓✓")
    else:
        print(f"\n⚠ {len(results) - passed} test(s) failed")


if __name__ == '__main__':
    main()
