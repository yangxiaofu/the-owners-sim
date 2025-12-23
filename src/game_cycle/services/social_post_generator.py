"""
Social Post Generator Service for game_cycle.

⚠️ DEPRECATED - DO NOT USE IN NEW CODE ⚠️

This monolithic generator has been replaced by a pluggable architecture.
All handlers (regular_season.py, playoffs.py, offseason.py) have been migrated
to use the new system.

MIGRATION GUIDE:
----------------
Old pattern:
    from ..services.social_post_generator import SocialPostGenerator
    post_generator = SocialPostGenerator(db, dynasty_id)
    posts = post_generator.generate_game_posts(...)
    for post in posts:
        posts_api.create_post(...)  # Manual persistence

New pattern:
    from ..services.social_generators.factory import SocialPostGeneratorFactory
    from ..models.social_event_types import SocialEventType

    event_data = {'winning_team_id': 1, 'losing_team_id': 2, ...}
    posts_created = SocialPostGeneratorFactory.generate_posts(
        event_type=SocialEventType.GAME_RESULT,
        db=db,
        dynasty_id=dynasty_id,
        season=season,
        week=week,
        event_data=event_data
    )  # Automatic persistence

New Architecture:
-----------------
- BaseSocialPostGenerator: Abstract base class with shared logic
- SocialPostGeneratorFactory: Dispatches to correct generator
- 11 Concrete Generators: GameSocialGenerator, AwardSocialGenerator, etc.
- SocialEventType enum: Type-safe event types (replaces magic strings)

See: /src/game_cycle/services/social_generators/
     /docs/14_MILESTONE_Social_Media/PHASE_2_INTEGRATION_SUMMARY.md

This file is kept for reference only and will be removed in a future release.

---

Legacy documentation below:

Main post generation engine that creates social media posts for events:
- Game results (wins/losses/upsets/blowouts)
- Transactions (trades, signings, cuts)
- Awards
- Draft picks
- Injuries

Features:
- Event-to-post-count mapping (4-8 normal, 8-12 upsets)
- 80/20 recurring/random personality mix
- Engagement calculation (likes/retweets)
- Template-based post generation

Part of Milestone 14: Social Media & Fan Reactions.
"""

import warnings
import random

# Emit deprecation warning on import
warnings.warn(
    "SocialPostGenerator is deprecated. Use SocialPostGeneratorFactory instead. "
    "See /docs/14_MILESTONE_Social_Media/PHASE_2_INTEGRATION_SUMMARY.md for migration guide.",
    DeprecationWarning,
    stacklevel=2
)
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.social_personalities_api import SocialPersonalityAPI
from src.game_cycle.services.post_template_loader import PostTemplateLoader
from team_management.teams.team_loader import get_team_by_id


# Event magnitude thresholds
MAGNITUDE_NORMAL = 50
MAGNITUDE_UPSET = 75
MAGNITUDE_BLOWOUT = 80
MAGNITUDE_MAJOR_TRADE = 70


@dataclass
class GeneratedPost:
    """Container for a generated post with all metadata."""
    personality_id: int
    post_text: str
    sentiment: float
    likes: int
    retweets: int
    event_metadata: Dict[str, Any]


class SocialPostGenerator:
    """
    Main social post generation engine.

    Creates posts for game events, transactions, awards, etc.
    Handles personality selection, template filling, and engagement calculation.
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize post generator.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier
        """
        self.db = db
        self.dynasty_id = dynasty_id
        self.personality_api = SocialPersonalityAPI(db)
        self.template_loader = PostTemplateLoader()

    def _get_team_name(self, team_id: int) -> str:
        """
        Get team name/abbreviation for display in posts.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Team abbreviation (e.g., "DET", "KC") or fallback "Team X"
        """
        try:
            team = get_team_by_id(team_id)
            return team.abbreviation if team else f"Team {team_id}"
        except Exception:
            return f"Team {team_id}"

    def _get_round_display_name(self, round_name: str) -> str:
        """
        Get display-friendly playoff round name.

        Args:
            round_name: Internal round name (e.g., 'wild_card', 'super_bowl')

        Returns:
            Display name (e.g., 'Wild Card', 'Super Bowl')
        """
        round_names = {
            'wild_card': 'Wild Card',
            'divisional': 'Divisional Round',
            'conference': 'Conference Championship',
            'super_bowl': 'Super Bowl'
        }
        return round_names.get(round_name, round_name.replace('_', ' ').title())

    # ==========================================
    # GAME POSTS
    # ==========================================

    def generate_game_posts(
        self,
        season: int,
        week: int,
        winning_team_id: int,
        losing_team_id: int,
        winning_score: int,
        losing_score: int,
        game_id: Optional[str] = None,
        is_upset: bool = False,
        is_blowout: bool = False,
        star_players: Optional[Dict[str, str]] = None,
        season_type: str = 'regular',
        round_name: Optional[str] = None
    ) -> List[GeneratedPost]:
        """
        Generate posts for a game result.

        Args:
            season: Season year
            week: Week number
            winning_team_id: Winning team ID
            losing_team_id: Losing team ID
            winning_score: Winner's score
            losing_score: Loser's score
            game_id: Optional game identifier
            is_upset: True if upset victory
            is_blowout: True if blowout (21+ point margin)
            star_players: Optional dict of {team_id: player_name}
            season_type: 'regular' or 'playoffs' (default: 'regular')
            round_name: Playoff round name (e.g., 'wild_card', 'super_bowl')

        Returns:
            List of GeneratedPost objects
        """
        # Determine event magnitude and base post count
        margin = winning_score - losing_score
        is_playoffs = (season_type == 'playoffs')
        is_super_bowl = (round_name == 'super_bowl')

        if is_blowout or margin >= 21:
            magnitude = MAGNITUDE_BLOWOUT
            post_count = random.randint(6, 10)
        elif is_upset:
            magnitude = MAGNITUDE_UPSET
            post_count = random.randint(8, 12)
        else:
            magnitude = MAGNITUDE_NORMAL
            post_count = random.randint(4, 6)

        # Playoff multiplier: Playoff games generate MORE buzz
        if is_playoffs:
            if is_super_bowl:
                # Super Bowl: Maximum engagement (10-15 posts)
                post_count = random.randint(10, 15)
                magnitude = 100  # Maximum magnitude
            else:
                # Other playoff rounds: 1.5x normal posts
                post_count = int(post_count * 1.5)
                magnitude = min(100, magnitude + 10)  # Boost magnitude slightly

        # Event metadata
        event_metadata = {
            'game_id': game_id,
            'winning_team': winning_team_id,
            'losing_team': losing_team_id,
            'score': f"{winning_score}-{losing_score}",
            'margin': margin,
            'is_upset': is_upset,
            'is_blowout': is_blowout,
            'season_type': season_type,
            'round_name': round_name
        }

        # Playoff context for templates
        round_display = self._get_round_display_name(round_name) if round_name else None

        # Generate posts
        posts = []

        # 80% from winning team fans (celebrating)
        winner_post_count = int(post_count * 0.5)
        winner_posts = self._generate_team_posts(
            team_id=winning_team_id,
            event_type='GAME_RESULT',
            event_outcome='WIN',
            post_count=winner_post_count,
            magnitude=magnitude,
            variables={
                'winner': self._get_team_name(winning_team_id),
                'loser': self._get_team_name(losing_team_id),
                'score': f'{winning_score}-{losing_score}',
                'player': star_players.get(winning_team_id, 'the team') if star_players else 'the team',
                'stat': '200+ yards' if star_players else 'great stats',
                'magnitude': magnitude,
                'round': round_display or '',
                'is_playoffs': is_playoffs,
                'is_super_bowl': is_super_bowl
            },
            event_metadata=event_metadata
        )
        posts.extend(winner_posts)

        # 20-30% from losing team fans (upset/angry)
        loser_post_count = int(post_count * 0.3)
        loser_posts = self._generate_team_posts(
            team_id=losing_team_id,
            event_type='GAME_RESULT',
            event_outcome='LOSS',
            post_count=loser_post_count,
            magnitude=magnitude,
            variables={
                'loser': self._get_team_name(losing_team_id),
                'winner': self._get_team_name(winning_team_id),
                'score': f'{winning_score}-{losing_score}',
                'player': star_players.get(losing_team_id, 'the team') if star_players else 'the team',
                'magnitude': magnitude,
                'round': round_display or '',
                'is_playoffs': is_playoffs,
                'is_super_bowl': is_super_bowl
            },
            event_metadata=event_metadata
        )
        posts.extend(loser_posts)

        # Media posts (hot takes on upsets/blowouts OR playoffs)
        if is_upset or is_blowout or is_playoffs:
            media_post_count = random.randint(2, 4) if is_playoffs else random.randint(1, 2)
            media_posts = self._generate_media_posts(
                event_type='GAME_RESULT',
                event_outcome='WIN' if random.random() > 0.5 else 'LOSS',
                post_count=media_post_count,
                magnitude=magnitude,
                variables={
                    'winner': self._get_team_name(winning_team_id),
                    'loser': self._get_team_name(losing_team_id),
                    'score': f'{winning_score}-{losing_score}',
                    'magnitude': magnitude,
                    'round': round_display or '',
                    'is_playoffs': is_playoffs,
                    'is_super_bowl': is_super_bowl
                },
                event_metadata=event_metadata
            )
            posts.extend(media_posts)

        return posts

    def _generate_team_posts(
        self,
        team_id: int,
        event_type: str,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any]
    ) -> List[GeneratedPost]:
        """
        Generate posts from a team's fan personalities.

        Args:
            team_id: Team ID
            event_type: Event type
            event_outcome: Event outcome ('WIN', 'LOSS', etc.)
            post_count: Number of posts to generate
            magnitude: Event magnitude (0-100)
            variables: Template variables
            event_metadata: Event metadata for database

        Returns:
            List of GeneratedPost objects
        """
        # Get team's fan personalities
        fans = self.personality_api.get_personalities_by_team(
            dynasty_id=self.dynasty_id,
            team_id=team_id,
            personality_type='FAN'
        )

        if not fans:
            return []

        posts = []

        # 80/20 recurring/random mix
        recurring_count = int(post_count * 0.8)
        random_count = post_count - recurring_count

        # Select recurring personalities (weighted by posting frequency)
        eligible_fans = self._filter_by_posting_frequency(fans, event_outcome)
        selected_fans = random.sample(eligible_fans, min(recurring_count, len(eligible_fans)))

        for fan in selected_fans:
            post = self._generate_single_post(
                personality=fan,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.append(post)

        # Generate random one-off posts (simulate bandwagon/casual fans)
        for _ in range(random_count):
            # Pick random archetype for one-off fan
            random_fan = random.choice(eligible_fans)
            post = self._generate_single_post(
                personality=random_fan,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata,
                is_random_fan=True
            )
            posts.append(post)

        return posts

    def _generate_media_posts(
        self,
        event_type: str,
        event_outcome: str,
        post_count: int,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any]
    ) -> List[GeneratedPost]:
        """
        Generate posts from league-wide media personalities.

        Args:
            event_type: Event type
            event_outcome: Event outcome
            post_count: Number of posts to generate
            magnitude: Event magnitude
            variables: Template variables
            event_metadata: Event metadata

        Returns:
            List of GeneratedPost objects
        """
        # Get hot take analysts (they post on dramatic events)
        media = self.personality_api.get_league_wide_personalities(
            dynasty_id=self.dynasty_id,
            personality_type='HOT_TAKE'
        )

        if not media:
            return []

        posts = []
        selected_media = random.sample(media, min(post_count, len(media)))

        for personality in selected_media:
            post = self._generate_single_post(
                personality=personality,
                event_type=event_type,
                event_outcome=event_outcome,
                magnitude=magnitude,
                variables=variables,
                event_metadata=event_metadata
            )
            posts.append(post)

        return posts

    def _generate_single_post(
        self,
        personality: Any,  # SocialPersonality object
        event_type: str,
        event_outcome: str,
        magnitude: int,
        variables: Dict[str, Any],
        event_metadata: Dict[str, Any],
        is_random_fan: bool = False
    ) -> GeneratedPost:
        """
        Generate a single post from a personality.

        Args:
            personality: SocialPersonality object
            event_type: Event type
            event_outcome: Event outcome
            magnitude: Event magnitude
            variables: Template variables
            event_metadata: Event metadata
            is_random_fan: True if simulating a random one-off fan

        Returns:
            GeneratedPost object
        """
        # Get template
        template = self.template_loader.get_template(
            event_type=event_type,
            archetype=personality.archetype,
            personality_id=personality.id,
            event_outcome=event_outcome
        )

        # Fill template
        post_text = self.template_loader.fill_template(template, variables)

        # Calculate sentiment
        sentiment = self.template_loader.calculate_sentiment(
            archetype=personality.archetype,
            event_outcome=event_outcome,
            event_magnitude=magnitude
        )

        # Calculate engagement
        likes, retweets = self._calculate_engagement(
            magnitude=magnitude,
            sentiment=sentiment
        )

        return GeneratedPost(
            personality_id=personality.id,
            post_text=post_text,
            sentiment=sentiment,
            likes=likes,
            retweets=retweets,
            event_metadata=event_metadata
        )

    # ==========================================
    # TRANSACTION POSTS
    # ==========================================

    def generate_transaction_posts(
        self,
        season: int,
        week: int,
        event_type: str,  # 'TRADE', 'SIGNING', 'CUT'
        team_id: int,
        player_name: str,
        transaction_details: Dict[str, Any]
    ) -> List[GeneratedPost]:
        """
        Generate posts for transactions (trades, signings, cuts).

        Args:
            season: Season year
            week: Week number
            event_type: Transaction type ('TRADE', 'SIGNING', 'CUT')
            team_id: Primary team involved
            player_name: Player name
            transaction_details: Transaction-specific details (value, years, picks, etc.)

        Returns:
            List of GeneratedPost objects
        """
        # Determine magnitude and post count
        if event_type == 'TRADE':
            magnitude = transaction_details.get('magnitude', MAGNITUDE_MAJOR_TRADE)
            post_count = random.randint(3, 5)
        elif event_type == 'SIGNING':
            contract_value = transaction_details.get('value', 0)
            magnitude = min(100, int(contract_value / 2) + 40)  # $20M = 50 magnitude
            post_count = random.randint(3, 5) if contract_value > 10 else random.randint(2, 3)
        elif event_type == 'CUT':
            magnitude = transaction_details.get('magnitude', 40)
            post_count = random.randint(2, 4)
        else:
            magnitude = MAGNITUDE_NORMAL
            post_count = 3

        # Build variables
        variables = {
            'player': player_name,
            'team': self._get_team_name(team_id),
            'magnitude': magnitude,
            **transaction_details
        }

        # Event metadata
        event_metadata = {
            'team_id': team_id,
            'player_name': player_name,
            **transaction_details
        }

        # Generate posts (mostly from team fans + some analysts)
        posts = []

        # Team fan posts
        team_post_count = int(post_count * 0.7)
        team_posts = self._generate_team_posts(
            team_id=team_id,
            event_type=event_type,
            event_outcome='POSITIVE' if event_type == 'SIGNING' else 'NEUTRAL',
            post_count=team_post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )
        posts.extend(team_posts)

        # Analyst posts (trade analysts for trades, stats nerds for signings)
        if event_type in ['TRADE', 'SIGNING']:
            analyst_count = post_count - team_post_count
            analysts = self.personality_api.get_personalities_by_team(
                dynasty_id=self.dynasty_id,
                team_id=team_id,
                personality_type='FAN'
            )
            # Filter for TRADE_ANALYST archetype
            trade_analysts = [p for p in analysts if p.archetype == 'TRADE_ANALYST']

            if trade_analysts:
                selected = random.sample(trade_analysts, min(analyst_count, len(trade_analysts)))
                for analyst in selected:
                    post = self._generate_single_post(
                        personality=analyst,
                        event_type=event_type,
                        event_outcome='NEUTRAL',
                        magnitude=magnitude,
                        variables=variables,
                        event_metadata=event_metadata
                    )
                    posts.append(post)

        return posts

    # ==========================================
    # AWARD POSTS
    # ==========================================

    def generate_award_posts(
        self,
        season: int,
        week: int,
        award_name: str,
        player_name: str,
        team_id: int,
        player_stats: Optional[str] = None
    ) -> List[GeneratedPost]:
        """
        Generate posts for award announcements.

        Args:
            season: Season year
            week: Week number (or None for season awards)
            award_name: Award name (MVP, DPOY, etc.)
            player_name: Winner's name
            team_id: Winner's team
            player_stats: Optional stat line

        Returns:
            List of GeneratedPost objects
        """
        # Determine magnitude based on award prestige
        prestige_map = {
            'MVP': 100,
            'DPOY': 90,
            'OROY': 85,
            'DROY': 85,
            'CPOY': 80,
            'ALL_PRO_FIRST': 75,
            'PRO_BOWL': 60
        }
        magnitude = prestige_map.get(award_name, 70)
        post_count = random.randint(2, 4) if magnitude > 80 else random.randint(1, 2)

        variables = {
            'player': player_name,
            'award': award_name,
            'stat': player_stats or 'dominant season',
            'team': self._get_team_name(team_id),
            'magnitude': magnitude
        }

        event_metadata = {
            'award': award_name,
            'player_name': player_name,
            'team_id': team_id
        }

        # Generate posts from team fans (celebrating)
        posts = self._generate_team_posts(
            team_id=team_id,
            event_type='AWARD',
            event_outcome='POSITIVE',
            post_count=post_count,
            magnitude=magnitude,
            variables=variables,
            event_metadata=event_metadata
        )

        return posts

    # ==========================================
    # HELPER METHODS
    # ==========================================

    def _filter_by_posting_frequency(
        self,
        personalities: List[Any],
        event_outcome: str
    ) -> List[Any]:
        """
        Filter personalities by posting frequency for this event.

        Args:
            personalities: List of SocialPersonality objects
            event_outcome: Event outcome ('WIN', 'LOSS', etc.)

        Returns:
            Filtered list of personalities who would post
        """
        eligible = []

        for p in personalities:
            if p.posting_frequency == 'ALL_EVENTS':
                eligible.append(p)
            elif p.posting_frequency == 'WIN_ONLY' and event_outcome == 'WIN':
                eligible.append(p)
            elif p.posting_frequency == 'LOSS_ONLY' and event_outcome == 'LOSS':
                eligible.append(p)
            elif p.posting_frequency == 'EMOTIONAL_MOMENTS':
                # Hot heads post on both wins and losses (emotional either way)
                if event_outcome in ['WIN', 'LOSS']:
                    eligible.append(p)
            elif p.posting_frequency == 'UPSET_ONLY':
                # Only post on upsets (would need upset flag, skip for now)
                pass

        return eligible if eligible else personalities  # Fallback to all if none match

    def _calculate_engagement(
        self,
        magnitude: int,
        sentiment: float
    ) -> Tuple[int, int]:
        """
        Calculate likes and retweets based on event importance and sentiment.

        Args:
            magnitude: Event importance (0-100)
            sentiment: Post sentiment (-1.0 to 1.0)

        Returns:
            Tuple of (likes, retweets)

        Algorithm:
            - Base engagement from magnitude
            - Extreme sentiment (very positive or negative) drives more engagement
            - Random variation (±30%)
        """
        # Base engagement from magnitude
        base_likes = magnitude * 10  # 0-1000
        base_retweets = magnitude * 3  # 0-300

        # Extreme sentiment boost (controversial posts get more engagement)
        sentiment_boost = abs(sentiment) * 50  # 0-50

        # Calculate with randomness
        likes = base_likes + random.randint(0, int(sentiment_boost))
        likes = int(likes * random.uniform(0.7, 1.3))  # ±30% variation

        retweets = base_retweets + random.randint(0, int(sentiment_boost // 3))
        retweets = int(retweets * random.uniform(0.7, 1.3))  # ±30% variation

        # Clamp to reasonable ranges
        likes = max(0, min(10000, likes))
        retweets = max(0, min(3000, retweets))

        return likes, retweets


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def generate_game_posts_batch(
    db: GameCycleDatabase,
    dynasty_id: str,
    season: int,
    week: int,
    game_results: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Generate posts for multiple games in a week.

    Args:
        db: GameCycleDatabase instance
        dynasty_id: Dynasty identifier
        season: Season year
        week: Week number
        game_results: List of game result dicts

    Returns:
        List of post dicts ready for SocialPostsAPI.create_post()

    Example:
        >>> game_results = [
        ...     {
        ...         'winning_team_id': 1,
        ...         'losing_team_id': 4,
        ...         'winning_score': 31,
        ...         'losing_score': 17,
        ...         'is_upset': False,
        ...         'is_blowout': False
        ...     }
        ... ]
        >>> posts = generate_game_posts_batch(db, 'dynasty', 2025, 1, game_results)
    """
    generator = SocialPostGenerator(db, dynasty_id)
    all_posts = []

    for game in game_results:
        generated_posts = generator.generate_game_posts(
            season=season,
            week=week,
            **game
        )

        # Convert to dict format for API
        for post in generated_posts:
            all_posts.append({
                'dynasty_id': dynasty_id,
                'personality_id': post.personality_id,
                'season': season,
                'week': week,
                'post_text': post.post_text,
                'event_type': 'GAME_RESULT',
                'sentiment': post.sentiment,
                'likes': post.likes,
                'retweets': post.retweets,
                'event_metadata': post.event_metadata
            })

    return all_posts
