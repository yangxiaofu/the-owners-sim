"""
Post Template Loader Service for game_cycle.

Loads and manages social media post templates with:
- Variable substitution
- Anti-repetition tracking
- Sentiment calculation

Part of Milestone 14: Social Media & Fan Reactions.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from collections import defaultdict, deque

if TYPE_CHECKING:
    from transactions.personality_modifiers import TeamContext


# Path to templates configuration
TEMPLATES_PATH = Path(__file__).parent.parent.parent / 'config' / 'social_media' / 'post_templates.json'


class PostTemplateLoader:
    """
    Loads and manages post templates for social media posts.

    Features:
    - Template selection by event type and archetype
    - Variable substitution ({player}, {team}, {score}, etc.)
    - Anti-repetition: Tracks last 10 templates per personality
    - Sentiment calculation based on archetype bias
    """

    def __init__(self):
        """Initialize template loader."""
        self.templates = self._load_templates()
        # Anti-repetition buffer: {personality_id: deque of last 10 template strings}
        self._recent_templates: Dict[int, deque] = defaultdict(lambda: deque(maxlen=10))

    def _load_templates(self) -> Dict[str, Any]:
        """Load templates from JSON configuration."""
        with open(TEMPLATES_PATH, 'r') as f:
            return json.load(f)

    # ==========================================
    # TEMPLATE SELECTION
    # ==========================================

    def get_template(
        self,
        event_type: str,
        archetype: Optional[str],
        personality_id: int,
        event_outcome: Optional[str] = None,
        team_context: Optional['TeamContext'] = None
    ) -> str:
        """
        Get a random template for an event type and archetype.

        Args:
            event_type: Event type ('GAME_RESULT', 'TRADE', 'SIGNING', etc.)
            archetype: Fan archetype or None for media (e.g., 'OPTIMIST', 'PESSIMIST')
            personality_id: Personality ID for anti-repetition tracking
            event_outcome: For GAME_RESULT, specify 'WIN' or 'LOSS'
            team_context: Optional TeamContext for requirements filtering

        Returns:
            Template string with placeholders

        Raises:
            ValueError: If event_type is invalid or no templates available
        """
        # Build template key
        if event_type == 'GAME_RESULT':
            if not event_outcome:
                raise ValueError("event_outcome required for GAME_RESULT")
            template_key = f"GAME_RESULT_{event_outcome}"
        else:
            template_key = event_type

        # Check if template key exists
        if template_key not in self.templates['templates']:
            raise ValueError(f"No templates found for event_type: {template_key}")

        event_templates = self.templates['templates'][template_key]

        # Select archetype templates (or 'ALL' for media/generic)
        if archetype and archetype in event_templates:
            archetype_templates = event_templates[archetype]
        elif 'ALL' in event_templates:
            archetype_templates = event_templates['ALL']
        else:
            # Fallback: pick random archetype's templates
            available_archetypes = list(event_templates.keys())
            if not available_archetypes:
                raise ValueError(f"No templates available for {template_key}")
            fallback_archetype = random.choice(available_archetypes)
            archetype_templates = event_templates[fallback_archetype]

        # Filter templates based on requirements if team_context provided
        if team_context:
            archetype_templates = self._filter_by_requirements(
                archetype_templates,
                team_context,
                event_templates
            )

        # Select template with anti-repetition
        template = self._select_with_anti_repetition(
            templates=archetype_templates,
            personality_id=personality_id
        )

        return template

    def _select_with_anti_repetition(
        self,
        templates: List[str],
        personality_id: int
    ) -> str:
        """
        Select a template that hasn't been used recently by this personality.

        Args:
            templates: List of available templates
            personality_id: Personality ID

        Returns:
            Selected template string
        """
        recent = self._recent_templates[personality_id]

        # Filter out recently used templates
        fresh_templates = [t for t in templates if t not in recent]

        # If all templates used recently, reset buffer
        if not fresh_templates:
            recent.clear()
            fresh_templates = templates

        # Select random template
        selected = random.choice(fresh_templates)

        # Add to recent buffer
        recent.append(selected)

        return selected

    def _filter_by_requirements(
        self,
        archetype_templates: Any,
        team_context: 'TeamContext',
        event_templates: Dict[str, Any]
    ) -> List[str]:
        """
        Filter templates based on requirements and team context.

        Supports two template formats:
        1. Simple list: ["template1", "template2"]
        2. Dict with requirements: {"templates": [...], "requirements": {...}}

        Args:
            archetype_templates: Either list of templates or dict with templates + requirements
            team_context: Current team context
            event_templates: Full event templates dict for fallback

        Returns:
            List of templates that meet requirements
        """
        # Handle simple list format (backward compatibility)
        if isinstance(archetype_templates, list):
            return archetype_templates

        # Handle dict format with requirements
        if isinstance(archetype_templates, dict):
            templates = archetype_templates.get('templates', [])
            requirements = archetype_templates.get('requirements', {})

            # Check if requirements are met
            if self._meets_requirements(requirements, team_context):
                return templates
            else:
                # Requirements not met - fallback to BALANCED archetype
                return self._get_fallback_templates(event_templates)

        # Unknown format - return empty list
        return []

    def _meets_requirements(
        self,
        requirements: Dict[str, Any],
        team_context: 'TeamContext'
    ) -> bool:
        """
        Check if team context meets template requirements.

        Supported requirements:
        - recent_trades: bool - Must have trades in last 2 weeks
        - min_week: int - Minimum week to use template
        - max_week: int - Maximum week to use template
        - playoff_positions: List[str] - Valid playoff positions
        - min_wins: int - Minimum wins required

        Args:
            requirements: Dict of requirement key-value pairs
            team_context: Current team context

        Returns:
            True if all requirements met, False otherwise
        """
        # Check recent trades requirement
        if 'recent_trades' in requirements:
            required = requirements['recent_trades']
            # Note: TeamContext doesn't have recent_trades attribute yet
            # We'll need to add this or handle it gracefully
            has_trades = getattr(team_context, 'recent_trades', False)
            if required and not has_trades:
                return False

        # Check min_week requirement
        if 'min_week' in requirements:
            min_week = requirements['min_week']
            current_week = getattr(team_context, 'current_week', None)
            if current_week is not None and current_week < min_week:
                return False

        # Check max_week requirement
        if 'max_week' in requirements:
            max_week = requirements['max_week']
            current_week = getattr(team_context, 'current_week', None)
            if current_week is not None and current_week > max_week:
                return False

        # Check playoff_positions requirement
        if 'playoff_positions' in requirements:
            valid_positions = requirements['playoff_positions']
            playoff_status = self._get_playoff_status(team_context)
            if playoff_status not in valid_positions:
                return False

        # Check min_wins requirement
        if 'min_wins' in requirements:
            min_wins = requirements['min_wins']
            if team_context.wins < min_wins:
                return False

        # All requirements met
        return True

    def _get_playoff_status(self, team_context: 'TeamContext') -> str:
        """
        Determine playoff status from team context.

        Args:
            team_context: Current team context

        Returns:
            Playoff status string: 'CLINCHED', 'IN_HUNT', 'ELIMINATED', 'LEADER', or 'UNKNOWN'
        """
        # Import PlayoffPosition enum
        from game_cycle.services.team_context_builder import PlayoffPosition

        # Map PlayoffPosition enum to string for template requirements
        if team_context.playoff_position == PlayoffPosition.CLINCHED:
            return 'CLINCHED'
        elif team_context.playoff_position == PlayoffPosition.IN_HUNT:
            return 'IN_HUNT'
        elif team_context.playoff_position == PlayoffPosition.ELIMINATED:
            return 'ELIMINATED'
        elif team_context.playoff_position == PlayoffPosition.LEADER:
            return 'LEADER'
        else:  # PlayoffPosition.UNKNOWN
            return 'UNKNOWN'

    def _get_fallback_templates(self, event_templates: Dict[str, Any]) -> List[str]:
        """
        Get fallback templates when requirements aren't met.

        Falls back to BALANCED archetype, or first available archetype.

        Args:
            event_templates: Full event templates dict

        Returns:
            List of fallback templates
        """
        # Try BALANCED archetype first
        if 'BALANCED' in event_templates:
            balanced_templates = event_templates['BALANCED']
            if isinstance(balanced_templates, list):
                return balanced_templates
            elif isinstance(balanced_templates, dict):
                return balanced_templates.get('templates', [])

        # Try ALL archetype
        if 'ALL' in event_templates:
            all_templates = event_templates['ALL']
            if isinstance(all_templates, list):
                return all_templates
            elif isinstance(all_templates, dict):
                return all_templates.get('templates', [])

        # Last resort: get first available archetype's templates
        for archetype_templates in event_templates.values():
            if isinstance(archetype_templates, list):
                return archetype_templates
            elif isinstance(archetype_templates, dict):
                templates = archetype_templates.get('templates', [])
                if templates:
                    return templates

        # No templates found
        return []

    # ==========================================
    # VARIABLE SUBSTITUTION
    # ==========================================

    def fill_template(
        self,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Fill template with variable values.

        Args:
            template: Template string with {placeholders}
            variables: Dict of variable values

        Returns:
            Filled template string

        Example:
            >>> template = "{player} had {stat} in {team}'s {score} win!"
            >>> variables = {
            ...     'player': 'Patrick Mahomes',
            ...     'stat': '350 yards',
            ...     'team': 'Kansas City',
            ...     'score': '35-17'
            ... }
            >>> fill_template(template, variables)
            "Patrick Mahomes had 350 yards in Kansas City's 35-17 win!"
        """
        try:
            # Use format_map to safely handle missing keys
            return template.format_map(SafeDict(variables))
        except (KeyError, ValueError) as e:
            # Fallback: return template with unfilled placeholders
            return template

    # ==========================================
    # SENTIMENT CALCULATION
    # ==========================================

    def calculate_sentiment(
        self,
        archetype: Optional[str],
        event_outcome: str,
        event_magnitude: int = 50
    ) -> float:
        """
        Calculate post sentiment based on archetype bias and event outcome.

        Args:
            archetype: Fan archetype or None for media
            event_outcome: 'WIN', 'LOSS', 'POSITIVE', 'NEGATIVE', or 'NEUTRAL'
            event_magnitude: Event importance (0-100, default: 50)

        Returns:
            Sentiment score (-1.0 to 1.0)

        Algorithm:
            - Base sentiment from event outcome
            - Modified by archetype bias (60% event, 40% personality)
            - Amplified for extreme personalities on big events
        """
        # Base event sentiment
        event_sentiment_map = {
            'WIN': 0.8,
            'LOSS': -0.8,
            'POSITIVE': 0.6,
            'NEGATIVE': -0.6,
            'NEUTRAL': 0.0
        }
        event_sentiment = event_sentiment_map.get(event_outcome, 0.0)

        # Get archetype bias
        if archetype:
            archetype_bias = self.templates['sentiment_modifiers'].get(archetype, 0.0)
        else:
            archetype_bias = 0.0  # Media personalities

        # Weighted combination: 60% event, 40% personality
        combined_sentiment = (event_sentiment * 0.6) + (archetype_bias * 0.4)

        # Amplify for extreme personalities on big events
        if abs(archetype_bias) > 0.5 and event_magnitude > 70:
            combined_sentiment *= 1.3

        # Clamp to [-1.0, 1.0]
        return max(-1.0, min(1.0, combined_sentiment))

    # ==========================================
    # EMOJI SELECTION
    # ==========================================

    def get_random_emoji(self, sentiment: float) -> str:
        """
        Get a random emoji based on sentiment.

        Args:
            sentiment: Sentiment score (-1.0 to 1.0)

        Returns:
            Random emoji string
        """
        if sentiment > 0.3:
            emoji_category = 'positive'
        elif sentiment < -0.3:
            emoji_category = 'negative'
        else:
            emoji_category = 'neutral'

        emojis = self.templates['emojis'].get(emoji_category, [''])
        return random.choice(emojis) if emojis else ''

    # ==========================================
    # UTILITY METHODS
    # ==========================================

    def get_available_event_types(self) -> List[str]:
        """
        Get list of all available event types.

        Returns:
            List of event type strings
        """
        return list(self.templates['templates'].keys())

    def get_available_archetypes(self, event_type: str) -> List[str]:
        """
        Get list of archetypes with templates for an event type.

        Args:
            event_type: Event type to check

        Returns:
            List of archetype strings
        """
        if event_type not in self.templates['templates']:
            return []
        return list(self.templates['templates'][event_type].keys())

    def get_template_count(self, event_type: Optional[str] = None) -> int:
        """
        Count total templates available.

        Args:
            event_type: Optional filter by event type

        Returns:
            Number of templates
        """
        if event_type:
            if event_type not in self.templates['templates']:
                return 0
            event_templates = self.templates['templates'][event_type]
            return sum(len(templates) for templates in event_templates.values())
        else:
            # Count all templates
            total = 0
            for event_templates in self.templates['templates'].values():
                total += sum(len(templates) for templates in event_templates.values())
            return total

    def reset_anti_repetition(self, personality_id: Optional[int] = None):
        """
        Reset anti-repetition buffer for a personality (or all).

        Args:
            personality_id: Personality ID or None to reset all
        """
        if personality_id:
            self._recent_templates[personality_id].clear()
        else:
            self._recent_templates.clear()


# ==========================================
# HELPER CLASSES
# ==========================================

class SafeDict(dict):
    """
    Dict subclass that returns empty string for missing keys.

    Prevents KeyError during string formatting.
    """
    def __missing__(self, key):
        return f"{{{key}}}"  # Return placeholder unfilled


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def load_template_loader() -> PostTemplateLoader:
    """
    Convenience function to load a template loader instance.

    Returns:
        Initialized PostTemplateLoader

    Example:
        >>> loader = load_template_loader()
        >>> template = loader.get_template('TRADE', 'OPTIMIST', personality_id=1)
        >>> post = loader.fill_template(template, {'player': 'Travis Kelce', 'team': 'Chiefs'})
    """
    return PostTemplateLoader()


def generate_post_text(
    event_type: str,
    archetype: Optional[str],
    personality_id: int,
    variables: Dict[str, Any],
    event_outcome: Optional[str] = None,
    loader: Optional[PostTemplateLoader] = None,
    team_context: Optional['TeamContext'] = None
) -> Dict[str, Any]:
    """
    Convenience function to generate a complete post with sentiment.

    Args:
        event_type: Event type ('GAME_RESULT', 'TRADE', etc.)
        archetype: Fan archetype or None
        personality_id: Personality ID
        variables: Variable values for template
        event_outcome: For GAME_RESULT, 'WIN' or 'LOSS'
        loader: Optional pre-loaded PostTemplateLoader
        team_context: Optional TeamContext for requirements filtering

    Returns:
        Dict with 'post_text' and 'sentiment'

    Example:
        >>> result = generate_post_text(
        ...     event_type='GAME_RESULT',
        ...     archetype='OPTIMIST',
        ...     personality_id=1,
        ...     variables={'winner': 'Chiefs', 'loser': 'Raiders', 'score': '31-17'},
        ...     event_outcome='WIN'
        ... )
        >>> print(result['post_text'])
        "LET'S GOOOOO! Chiefs beat Raiders 31-17! 🔥"
        >>> print(result['sentiment'])
        0.76
    """
    if loader is None:
        loader = PostTemplateLoader()

    # Get template
    template = loader.get_template(
        event_type=event_type,
        archetype=archetype,
        personality_id=personality_id,
        event_outcome=event_outcome,
        team_context=team_context
    )

    # Fill template
    post_text = loader.fill_template(template, variables)

    # Calculate sentiment
    outcome_for_sentiment = event_outcome if event_outcome else 'NEUTRAL'
    sentiment = loader.calculate_sentiment(
        archetype=archetype,
        event_outcome=outcome_for_sentiment,
        event_magnitude=variables.get('magnitude', 50)
    )

    return {
        'post_text': post_text,
        'sentiment': sentiment
    }
