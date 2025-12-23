"""
Social Feed Demo Script

Demonstrates the social media & fan reactions system:
1. Generate personalities for a dynasty
2. Simulate game events and generate posts
3. Query posts with filters
4. Display formatted feed

Part of Milestone 14: Social Media & Fan Reactions, Tollgate 8.

Usage:
    PYTHONPATH=src python demos/social_feed_demo.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.social_personalities_api import SocialPersonalityAPI
from src.game_cycle.database.social_posts_api import SocialPostsAPI
from src.game_cycle.services.social_post_generator import SocialPostGenerator


# ==========================================
# DEMO SETUP
# ==========================================

def create_demo_database():
    """Create temporary database with social media schema."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    db = GameCycleDatabase(path)

    # Create social_personalities table
    db.get_connection().execute("""
        CREATE TABLE social_personalities (
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
        CREATE TABLE social_posts (
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

    return db, path


def create_sample_personalities(db: GameCycleDatabase, dynasty_id: str):
    """Create sample personalities for demo."""
    api = SocialPersonalityAPI(db)

    print("📝 Creating sample personalities...")

    # Team 1 (Detroit Lions) fans
    personalities = []

    # Optimists (positive bias, post on all events)
    for i in range(2):
        pid = api.create_personality(
            dynasty_id=dynasty_id,
            handle=f'@DetroitBeliever{i+1}',
            display_name=f'Detroit Believer #{i+1}',
            personality_type='FAN',
            archetype='OPTIMIST',
            team_id=22,  # DET
            sentiment_bias=0.6,
            posting_frequency='ALL_EVENTS'
        )
        personalities.append(('OPTIMIST', pid))

    # Pessimists (negative bias, post on losses)
    for i in range(2):
        pid = api.create_personality(
            dynasty_id=dynasty_id,
            handle=f'@LionsCynic{i+1}',
            display_name=f'Lions Cynic #{i+1}',
            personality_type='FAN',
            archetype='PESSIMIST',
            team_id=22,
            sentiment_bias=-0.5,
            posting_frequency='LOSS_ONLY'
        )
        personalities.append(('PESSIMIST', pid))

    # Bandwagon fans (slight positive, win only)
    pid = api.create_personality(
        dynasty_id=dynasty_id,
        handle='@NewLionsFan',
        display_name='New Lions Fan',
        personality_type='FAN',
        archetype='BANDWAGON',
        team_id=22,
        sentiment_bias=0.3,
        posting_frequency='WIN_ONLY'
    )
    personalities.append(('BANDWAGON', pid))

    # Stats nerd (neutral, all events)
    pid = api.create_personality(
        dynasty_id=dynasty_id,
        handle='@LionsStatsGuru',
        display_name='Lions Stats Guru',
        personality_type='FAN',
        archetype='STATS_NERD',
        team_id=22,
        sentiment_bias=0.0,
        posting_frequency='ALL_EVENTS'
    )
    personalities.append(('STATS_NERD', pid))

    # Team 2 (Kansas City Chiefs) fans
    for i in range(3):
        pid = api.create_personality(
            dynasty_id=dynasty_id,
            handle=f'@ChiefsKingdom{i+1}',
            display_name=f'Chiefs Kingdom #{i+1}',
            personality_type='FAN',
            archetype='OPTIMIST',
            team_id=14,  # KC
            sentiment_bias=0.5,
            posting_frequency='ALL_EVENTS'
        )
        personalities.append(('OPTIMIST', pid))

    # League-wide media
    pid = api.create_personality(
        dynasty_id=dynasty_id,
        handle='@HotTakeKing',
        display_name='Hot Take King',
        personality_type='HOT_TAKE',
        archetype=None,
        team_id=None,
        sentiment_bias=0.2,
        posting_frequency='EMOTIONAL_MOMENTS'
    )
    personalities.append(('HOT_TAKE', pid))

    pid = api.create_personality(
        dynasty_id=dynasty_id,
        handle='@NFLStatsNerd',
        display_name='NFL Stats Nerd',
        personality_type='STATS_ANALYST',
        archetype=None,
        team_id=None,
        sentiment_bias=0.0,
        posting_frequency='ALL_EVENTS'
    )
    personalities.append(('STATS_ANALYST', pid))

    print(f"✅ Created {len(personalities)} personalities")
    print()

    return personalities


# ==========================================
# DEMO SCENARIOS
# ==========================================

def demo_normal_game(db: GameCycleDatabase, dynasty_id: str):
    """Demonstrate normal game scenario."""
    print("=" * 80)
    print("SCENARIO 1: Normal Game - DET 28, KC 24")
    print("=" * 80)
    print()

    generator = SocialPostGenerator(db, dynasty_id)
    posts_api = SocialPostsAPI(db)

    # Generate posts
    posts = generator.generate_game_posts(
        season=2025,
        week=1,
        winning_team_id=22,  # DET
        losing_team_id=14,   # KC
        winning_score=28,
        losing_score=24,
        is_upset=False,
        is_blowout=False
    )

    print(f"📱 Generated {len(posts)} posts for normal game")
    print()

    # Store in database
    for post in posts:
        posts_api.create_post(
            dynasty_id=dynasty_id,
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

    # Display sample posts
    display_posts(db, dynasty_id, season=2025, week=1, limit=5)
    print()


def demo_upset_game(db: GameCycleDatabase, dynasty_id: str):
    """Demonstrate upset game scenario."""
    print("=" * 80)
    print("SCENARIO 2: Upset Game - DET 35, KC 10 (Blowout Upset)")
    print("=" * 80)
    print()

    generator = SocialPostGenerator(db, dynasty_id)
    posts_api = SocialPostsAPI(db)

    # Generate posts
    posts = generator.generate_game_posts(
        season=2025,
        week=2,
        winning_team_id=22,  # DET
        losing_team_id=14,   # KC
        winning_score=35,
        losing_score=10,
        is_upset=True,
        is_blowout=True
    )

    print(f"📱 Generated {len(posts)} posts for upset/blowout game (more posts!)")
    print()

    # Store in database
    for post in posts:
        posts_api.create_post(
            dynasty_id=dynasty_id,
            personality_id=post.personality_id,
            season=2025,
            week=2,
            post_text=post.post_text,
            event_type='GAME_RESULT',
            sentiment=post.sentiment,
            likes=post.likes,
            retweets=post.retweets,
            event_metadata=post.event_metadata
        )

    # Display sample posts
    display_posts(db, dynasty_id, season=2025, week=2, limit=8)
    print()


def demo_filtered_feed(db: GameCycleDatabase, dynasty_id: str):
    """Demonstrate filtered feed queries."""
    print("=" * 80)
    print("SCENARIO 3: Filtered Feeds")
    print("=" * 80)
    print()

    posts_api = SocialPostsAPI(db)

    # Filter 1: Team filter (DET fans only)
    print("🔍 Filter: Team 22 (DET) fans only")
    print("-" * 80)
    team_posts = posts_api.get_rolling_feed(
        dynasty_id=dynasty_id,
        season=2025,
        week=2,
        limit=5,
        offset=0,
        team_filter=22
    )
    display_post_list(db, dynasty_id, team_posts)
    print()

    # Filter 2: Positive sentiment only
    print("🔍 Filter: Positive sentiment only")
    print("-" * 80)
    positive_posts = posts_api.get_rolling_feed(
        dynasty_id=dynasty_id,
        season=2025,
        week=2,
        limit=5,
        offset=0,
        sentiment_filter='POSITIVE'
    )
    display_post_list(db, dynasty_id, positive_posts)
    print()

    # Filter 3: Combined filters (DET fans + positive)
    print("🔍 Filter: DET fans + Positive sentiment")
    print("-" * 80)
    combined_posts = posts_api.get_rolling_feed(
        dynasty_id=dynasty_id,
        season=2025,
        week=2,
        limit=5,
        offset=0,
        team_filter=22,
        sentiment_filter='POSITIVE'
    )
    display_post_list(db, dynasty_id, combined_posts)
    print()


def demo_transaction_posts(db: GameCycleDatabase, dynasty_id: str):
    """Demonstrate transaction posts."""
    print("=" * 80)
    print("SCENARIO 4: Transaction Posts - Big Free Agent Signing")
    print("=" * 80)
    print()

    generator = SocialPostGenerator(db, dynasty_id)
    posts_api = SocialPostsAPI(db)

    # Generate signing posts
    posts = generator.generate_transaction_posts(
        season=2025,
        week=3,
        event_type='SIGNING',
        team_id=22,  # DET
        player_name='Star QB',
        transaction_details={'value': 30, 'years': 5}
    )

    print(f"📱 Generated {len(posts)} posts for big FA signing")
    print()

    # Store in database
    for post in posts:
        posts_api.create_post(
            dynasty_id=dynasty_id,
            personality_id=post.personality_id,
            season=2025,
            week=3,
            post_text=post.post_text,
            event_type='SIGNING',
            sentiment=post.sentiment,
            likes=post.likes,
            retweets=post.retweets,
            event_metadata=post.event_metadata
        )

    # Display posts
    display_posts(db, dynasty_id, season=2025, week=3, limit=5)
    print()


def demo_award_posts(db: GameCycleDatabase, dynasty_id: str):
    """Demonstrate award posts."""
    print("=" * 80)
    print("SCENARIO 5: Award Posts - MVP Announcement")
    print("=" * 80)
    print()

    generator = SocialPostGenerator(db, dynasty_id)
    posts_api = SocialPostsAPI(db)

    # Generate award posts
    posts = generator.generate_award_posts(
        season=2025,
        week=None,
        award_name='MVP',
        player_name='Elite QB',
        team_id=22,  # DET
        player_stats='4500 yards, 40 TDs, 5 INTs'
    )

    print(f"📱 Generated {len(posts)} posts for MVP award")
    print()

    # Store in database
    for post in posts:
        posts_api.create_post(
            dynasty_id=dynasty_id,
            personality_id=post.personality_id,
            season=2025,
            week=None,
            post_text=post.post_text,
            event_type='AWARD',
            sentiment=post.sentiment,
            likes=post.likes,
            retweets=post.retweets,
            event_metadata=post.event_metadata
        )

    # Display posts
    display_posts(db, dynasty_id, season=2025, week=None, limit=5)
    print()


# ==========================================
# DISPLAY HELPERS
# ==========================================

def display_posts(db: GameCycleDatabase, dynasty_id: str, season: int, week: int, limit: int = 5):
    """Display posts in formatted feed."""
    posts_api = SocialPostsAPI(db)
    personality_api = SocialPersonalityAPI(db)

    posts = posts_api.get_rolling_feed(
        dynasty_id=dynasty_id,
        season=season,
        week=week,
        limit=limit,
        offset=0
    )

    display_post_list(db, dynasty_id, posts)


def display_post_list(db: GameCycleDatabase, dynasty_id: str, posts):
    """Display list of posts."""
    personality_api = SocialPersonalityAPI(db)

    for i, post in enumerate(posts, 1):
        personality = personality_api.get_personality_by_id(post.personality_id)

        # Sentiment emoji
        if post.sentiment > 0.3:
            sentiment_emoji = "😊"
        elif post.sentiment < -0.3:
            sentiment_emoji = "😠"
        else:
            sentiment_emoji = "😐"

        # Archetype badge
        archetype_badge = f"[{personality.archetype}]" if personality.archetype else "[MEDIA]"

        print(f"{i}. {personality.handle} {archetype_badge} {sentiment_emoji}")
        print(f"   {personality.display_name}")
        print(f"   {post.post_text}")
        print(f"   ❤️ {post.likes:,}  🔄 {post.retweets:,}  📊 Sentiment: {post.sentiment:+.2f}")
        print()


# ==========================================
# MAIN DEMO
# ==========================================

def main():
    """Run complete social media demo."""
    print()
    print("🏈 SOCIAL MEDIA & FAN REACTIONS DEMO")
    print("=" * 80)
    print()

    # Create database
    db, db_path = create_demo_database()
    dynasty_id = 'demo_dynasty'

    try:
        # Setup
        personalities = create_sample_personalities(db, dynasty_id)

        print(f"📊 Demo Dynasty: {dynasty_id}")
        print(f"📂 Database: {db_path}")
        print()

        # Run scenarios
        demo_normal_game(db, dynasty_id)
        demo_upset_game(db, dynasty_id)
        demo_filtered_feed(db, dynasty_id)
        demo_transaction_posts(db, dynasty_id)
        demo_award_posts(db, dynasty_id)

        # Summary
        posts_api = SocialPostsAPI(db)
        all_posts = posts_api.get_all_posts(dynasty_id, season=2025)

        print("=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(f"Total Personalities: {len(personalities)}")
        print(f"Total Posts Generated: {len(all_posts)}")
        print()
        print("✅ Demo completed successfully!")
        print()
        print("Key Features Demonstrated:")
        print("  • Personality generation with archetypes")
        print("  • Event-to-post-count mapping (normal vs upset/blowout)")
        print("  • Sentiment calculation based on archetype + event outcome")
        print("  • Engagement calculation (likes/retweets)")
        print("  • Database-level filtering (team, event type, sentiment)")
        print("  • Pagination support")
        print()

    finally:
        # Cleanup
        db.close()
        if os.path.exists(db_path):
            os.unlink(db_path)
            print(f"🗑️ Cleaned up temporary database: {db_path}")
        print()


if __name__ == '__main__':
    main()
