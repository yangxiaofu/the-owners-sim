"""
Personality Generator Service for game_cycle.

Generates 256-384 recurring fan personalities and 40-45 media personalities
for a dynasty using template-based handle/display name generation.

Part of Milestone 14: Social Media & Fan Reactions.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

from src.game_cycle.database.connection import GameCycleDatabase
from src.game_cycle.database.social_personalities_api import SocialPersonalityAPI


# Path to templates configuration
TEMPLATES_PATH = Path(__file__).parent.parent.parent / 'config' / 'social_media' / 'fan_name_templates.json'

# Fan archetypes (10 total)
FAN_ARCHETYPES = [
    'OPTIMIST', 'PESSIMIST', 'BANDWAGON', 'STATS_NERD', 'OLD_TIMER',
    'HOT_HEAD', 'MEME_LORD', 'TRADE_ANALYST', 'CONSPIRACY', 'BALANCED'
]

# Media personality types
MEDIA_TYPES = {
    'BEAT_REPORTER': 1,  # 1 per team = 32 total
    'HOT_TAKE': (5, 8),  # 5-8 league-wide
    'STATS_ANALYST': (3, 5)  # 3-5 league-wide
}


class PersonalityGenerator:
    """
    Generates social media personalities for a dynasty.

    Creates:
    - 8-12 fan personalities per team (256-384 total)
    - 1 beat reporter per team (32 total)
    - 5-8 hot-take analysts (league-wide)
    - 3-5 stats analysts (league-wide)

    Total: 296-424 personalities
    """

    def __init__(self, db: GameCycleDatabase, dynasty_id: str):
        """
        Initialize personality generator.

        Args:
            db: GameCycleDatabase instance
            dynasty_id: Dynasty identifier
        """
        self.db = db
        self.dynasty_id = dynasty_id
        self.api = SocialPersonalityAPI(db)
        self.templates = self._load_templates()
        self.used_handles: set = set()

    def _load_templates(self) -> Dict[str, Any]:
        """Load name templates from JSON configuration."""
        with open(TEMPLATES_PATH, 'r') as f:
            return json.load(f)

    def generate_all_personalities(self) -> Dict[str, int]:
        """
        Generate all personalities for the dynasty.

        Returns:
            Dict with counts: {'fans': 280, 'beat_reporters': 32, 'hot_takes': 7, 'stats_analysts': 4}

        Raises:
            ValueError: If generation fails
        """
        counts = {
            'fans': 0,
            'beat_reporters': 0,
            'hot_takes': 0,
            'stats_analysts': 0
        }

        # Generate fan personalities for each team (1-32)
        for team_id in range(1, 33):
            team_fans = self._generate_team_fans(team_id)
            counts['fans'] += len(team_fans)

            # Generate beat reporter for this team
            beat_reporter = self._generate_beat_reporter(team_id)
            counts['beat_reporters'] += 1

        # Generate league-wide media personalities
        hot_takes = self._generate_league_wide_media('HOT_TAKE')
        counts['hot_takes'] = len(hot_takes)

        stats_analysts = self._generate_league_wide_media('STATS_ANALYST')
        counts['stats_analysts'] = len(stats_analysts)

        return counts

    def _generate_team_fans(self, team_id: int) -> List[int]:
        """
        Generate 8-12 fan personalities for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            List of created personality IDs
        """
        # Randomly choose 8-12 fans
        num_fans = random.randint(8, 12)

        # Randomly select archetypes (with replacement allowed)
        selected_archetypes = random.choices(FAN_ARCHETYPES, k=num_fans)

        personality_ids = []
        for archetype in selected_archetypes:
            personality_id = self._create_fan_personality(team_id, archetype)
            personality_ids.append(personality_id)

        return personality_ids

    def _create_fan_personality(self, team_id: int, archetype: str) -> int:
        """
        Create a single fan personality.

        Args:
            team_id: Team ID (1-32)
            archetype: Fan archetype (e.g., 'OPTIMIST', 'PESSIMIST')

        Returns:
            Created personality ID

        Raises:
            ValueError: If handle generation fails after retries
        """
        team_data = self.templates['team_data'][str(team_id)]
        archetype_templates = self.templates['fan_name_templates'][archetype]

        # Try up to 10 times to generate a unique handle
        for attempt in range(10):
            handle, display_name = self._generate_handle_and_display(
                archetype_templates,
                team_data
            )

            # Ensure uniqueness
            if handle not in self.used_handles:
                break
        else:
            # Fallback: append random number
            handle = f"{handle}{random.randint(1, 999)}"

        self.used_handles.add(handle)

        # Get archetype settings
        sentiment_bias = self.templates['archetype_sentiment_biases'][archetype]
        posting_frequency = self.templates['archetype_posting_frequencies'][archetype]

        # Create personality
        personality_id = self.api.create_personality(
            dynasty_id=self.dynasty_id,
            handle=handle,
            display_name=display_name,
            personality_type='FAN',
            archetype=archetype,
            team_id=team_id,
            sentiment_bias=sentiment_bias,
            posting_frequency=posting_frequency
        )

        return personality_id

    def _generate_beat_reporter(self, team_id: int) -> int:
        """
        Generate beat reporter for a team.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Created personality ID
        """
        team_data = self.templates['team_data'][str(team_id)]
        beat_templates = self.templates['media_name_templates']['BEAT_REPORTER']

        # Pick random template
        template_idx = random.randint(0, len(beat_templates['handles']) - 1)
        handle_template = beat_templates['handles'][template_idx]
        display_template = beat_templates['display_names'][template_idx]

        handle = '@' + handle_template.format(abbrev=team_data['abbrev'])
        display_name = display_template.format(abbrev=team_data['abbrev'])

        # Ensure uniqueness
        if handle in self.used_handles:
            handle = f"{handle}{random.randint(1, 99)}"

        self.used_handles.add(handle)

        # Beat reporters are neutral (0.0 bias), post on all events
        personality_id = self.api.create_personality(
            dynasty_id=self.dynasty_id,
            handle=handle,
            display_name=display_name,
            personality_type='BEAT_REPORTER',
            archetype=None,  # Media has no archetype
            team_id=team_id,
            sentiment_bias=0.0,
            posting_frequency='ALL_EVENTS'
        )

        return personality_id

    def _generate_league_wide_media(self, media_type: str) -> List[int]:
        """
        Generate league-wide media personalities.

        Args:
            media_type: 'HOT_TAKE' or 'STATS_ANALYST'

        Returns:
            List of created personality IDs
        """
        # Determine count range
        if media_type == 'HOT_TAKE':
            min_count, max_count = MEDIA_TYPES['HOT_TAKE']
        elif media_type == 'STATS_ANALYST':
            min_count, max_count = MEDIA_TYPES['STATS_ANALYST']
        else:
            raise ValueError(f"Invalid media_type: {media_type}")

        num_personalities = random.randint(min_count, max_count)

        media_templates = self.templates['media_name_templates'][media_type]
        personality_ids = []

        for i in range(num_personalities):
            # Pick random template
            if i < len(media_templates['handles']):
                # Use predefined handle (no randomization needed)
                handle = '@' + media_templates['handles'][i]
                display_name = media_templates['display_names'][i]
            else:
                # If we need more than templates, generate with suffix
                template_idx = i % len(media_templates['handles'])
                handle = '@' + media_templates['handles'][template_idx] + str(i)
                display_name = media_templates['display_names'][template_idx] + f" #{i}"

            # Ensure uniqueness
            if handle in self.used_handles:
                handle = f"{handle}{random.randint(1, 99)}"

            self.used_handles.add(handle)

            # Sentiment bias: Hot takes are slightly polarized, stats analysts are neutral
            if media_type == 'HOT_TAKE':
                sentiment_bias = random.uniform(-0.3, 0.3)  # Slight bias either way
                posting_frequency = 'EMOTIONAL_MOMENTS'  # They chase drama
            else:
                sentiment_bias = 0.0
                posting_frequency = 'ALL_EVENTS'

            personality_id = self.api.create_personality(
                dynasty_id=self.dynasty_id,
                handle=handle,
                display_name=display_name,
                personality_type=media_type,
                archetype=None,
                team_id=None,  # League-wide
                sentiment_bias=sentiment_bias,
                posting_frequency=posting_frequency
            )

            personality_ids.append(personality_id)

        return personality_ids

    def _generate_handle_and_display(
        self,
        templates: Dict[str, List[str]],
        team_data: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Generate handle and display name from templates.

        Args:
            templates: Archetype templates dict with 'handles' and 'display_names'
            team_data: Team data with placeholders (nickname, abbrev, etc.)

        Returns:
            Tuple of (handle, display_name)
        """
        # Pick random template
        idx = random.randint(0, len(templates['handles']) - 1)
        handle_template = templates['handles'][idx]
        display_template = templates['display_names'][idx]

        # Fill in placeholders
        handle = '@' + handle_template.format(**team_data)
        display_name = display_template.format(**team_data)

        return handle, display_name

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_generation_summary(self) -> Dict[str, Any]:
        """
        Get summary of generated personalities.

        Returns:
            Dict with counts by type and team
        """
        all_personalities = self.api.get_all_personalities(self.dynasty_id)

        summary = {
            'total': len(all_personalities),
            'by_type': {},
            'by_team': {},
            'by_archetype': {}
        }

        for p in all_personalities:
            # Count by type
            summary['by_type'][p.personality_type] = summary['by_type'].get(p.personality_type, 0) + 1

            # Count by team (if applicable)
            if p.team_id:
                summary['by_team'][p.team_id] = summary['by_team'].get(p.team_id, 0) + 1

            # Count by archetype (if applicable)
            if p.archetype:
                summary['by_archetype'][p.archetype] = summary['by_archetype'].get(p.archetype, 0) + 1

        return summary

    def validate_generation(self) -> Dict[str, Any]:
        """
        Validate that personality generation met requirements.

        Returns:
            Dict with validation results and issues
        """
        issues = []
        summary = self.get_generation_summary()

        # Check total count (should be 296-424)
        if not (296 <= summary['total'] <= 424):
            issues.append(f"Total personality count {summary['total']} outside expected range (296-424)")

        # Check beat reporters (should be exactly 32)
        beat_count = summary['by_type'].get('BEAT_REPORTER', 0)
        if beat_count != 32:
            issues.append(f"Expected 32 beat reporters, got {beat_count}")

        # Check hot takes (should be 5-8)
        hot_take_count = summary['by_type'].get('HOT_TAKE', 0)
        if not (5 <= hot_take_count <= 8):
            issues.append(f"Hot take analysts {hot_take_count} outside expected range (5-8)")

        # Check stats analysts (should be 3-5)
        stats_count = summary['by_type'].get('STATS_ANALYST', 0)
        if not (3 <= stats_count <= 5):
            issues.append(f"Stats analysts {stats_count} outside expected range (3-5)")

        # Check each team has 8-12 fans
        for team_id in range(1, 33):
            fan_count = summary['by_team'].get(team_id, 0)
            # Beat reporter counts as 1, so fans should be fan_count - 1
            actual_fan_count = fan_count - 1  # Subtract beat reporter
            if not (8 <= actual_fan_count <= 12):
                issues.append(f"Team {team_id} has {actual_fan_count} fans (expected 8-12)")

        # Check handle uniqueness
        all_handles = [p.handle for p in self.api.get_all_personalities(self.dynasty_id)]
        if len(all_handles) != len(set(all_handles)):
            duplicates = [h for h in all_handles if all_handles.count(h) > 1]
            issues.append(f"Duplicate handles found: {set(duplicates)}")

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'summary': summary
        }


# ==========================================
# CONVENIENCE FUNCTION
# ==========================================

def generate_personalities_for_dynasty(db: GameCycleDatabase, dynasty_id: str) -> Dict[str, Any]:
    """
    Convenience function to generate all personalities for a dynasty.

    Args:
        db: GameCycleDatabase instance
        dynasty_id: Dynasty identifier

    Returns:
        Dict with generation summary and validation results

    Example:
        >>> from src.game_cycle.database.connection import GameCycleDatabase
        >>> with GameCycleDatabase('path/to/db') as db:
        ...     results = generate_personalities_for_dynasty(db, 'my_dynasty')
        ...     print(results['counts'])
        {'fans': 320, 'beat_reporters': 32, 'hot_takes': 6, 'stats_analysts': 4}
    """
    generator = PersonalityGenerator(db, dynasty_id)

    # Generate all personalities
    counts = generator.generate_all_personalities()

    # Validate
    validation = generator.validate_generation()

    return {
        'counts': counts,
        'summary': generator.get_generation_summary(),
        'validation': validation
    }
