"""
GM Archetype System

Defines General Manager personalities and decision-making philosophies.
Used to drive AI transaction decisions throughout the simulation.
"""

from dataclasses import dataclass
from typing import Dict, Any
import json


@dataclass
class GMArchetype:
    """
    Defines a General Manager's personality and decision-making philosophy.

    All trait values use 0.0-1.0 continuous scales:
    - 0.0-0.3: Low/Weak tendency
    - 0.3-0.7: Moderate/Balanced
    - 0.7-1.0: High/Strong tendency
    """

    # Identification
    name: str
    description: str

    # Core Personality Traits (0.0-1.0)
    risk_tolerance: float = 0.5
    """Willingness to take gambles on unproven players or risky trades"""

    win_now_mentality: float = 0.5
    """Championship urgency (low = rebuild focus, high = win immediately)"""

    draft_pick_value: float = 0.5
    """How much GM values draft picks vs proven players"""

    cap_management: float = 0.5
    """Financial discipline (low = spends freely, high = conservative with cap)"""

    trade_frequency: float = 0.5
    """Base likelihood of making trades"""

    veteran_preference: float = 0.5
    """Youth focus (low) vs veteran focus (high)"""

    star_chasing: float = 0.3
    """Tendency to pursue superstar players vs balanced roster building"""

    loyalty: float = 0.5
    """Tendency to keep existing players vs turnover"""

    # Situational Modifiers (0.0-1.0)
    desperation_threshold: float = 0.7
    """Performance level (win %) that triggers desperate moves"""

    patience_years: int = 3
    """Number of years willing to commit to rebuild before pivoting"""

    deadline_activity: float = 0.5
    """Trade deadline aggressiveness (relative to normal trade_frequency)"""

    # Position Philosophy (0.0-1.0)
    premium_position_focus: float = 0.6
    """Prioritization of QB/Edge/OT over other positions"""

    # Valuation Style Traits (0.0-1.0)
    analytics_preference: float = 0.5
    """How much GM trusts stats/analytics (0.0 = ignores, 1.0 = primary driver)"""

    scouting_preference: float = 0.5
    """How much GM trusts scouting reports (0.0 = ignores, 1.0 = primary driver)"""

    market_awareness: float = 0.5
    """How much GM tracks market rates (0.0 = ignores, 1.0 = market-driven)"""

    def __post_init__(self):
        """Validate all trait values are within acceptable ranges"""
        self._validate_traits()

    def _validate_traits(self):
        """Ensure all float traits are between 0.0 and 1.0"""
        float_traits = [
            'risk_tolerance', 'win_now_mentality', 'draft_pick_value',
            'cap_management', 'trade_frequency', 'veteran_preference',
            'star_chasing', 'loyalty', 'desperation_threshold',
            'deadline_activity', 'premium_position_focus',
            'analytics_preference', 'scouting_preference', 'market_awareness'
        ]

        for trait_name in float_traits:
            value = getattr(self, trait_name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"{trait_name} must be between 0.0 and 1.0, got {value}"
                )

        # Validate patience_years
        if not 1 <= self.patience_years <= 10:
            raise ValueError(
                f"patience_years must be between 1 and 10, got {self.patience_years}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert archetype to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'description': self.description,
            'risk_tolerance': self.risk_tolerance,
            'win_now_mentality': self.win_now_mentality,
            'draft_pick_value': self.draft_pick_value,
            'cap_management': self.cap_management,
            'trade_frequency': self.trade_frequency,
            'veteran_preference': self.veteran_preference,
            'star_chasing': self.star_chasing,
            'loyalty': self.loyalty,
            'desperation_threshold': self.desperation_threshold,
            'patience_years': self.patience_years,
            'deadline_activity': self.deadline_activity,
            'premium_position_focus': self.premium_position_focus,
            'analytics_preference': self.analytics_preference,
            'scouting_preference': self.scouting_preference,
            'market_awareness': self.market_awareness
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GMArchetype':
        """Create archetype from dictionary"""
        return cls(**data)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'GMArchetype':
        """Create from JSON string"""
        return cls.from_dict(json.loads(json_str))

    def apply_customizations(self, customizations: Dict[str, Any]) -> 'GMArchetype':
        """
        Create a new archetype with customized trait values.

        Args:
            customizations: Dict of trait names to new values

        Returns:
            New GMArchetype instance with updated traits
        """
        archetype_dict = self.to_dict()
        archetype_dict.update(customizations)
        return GMArchetype.from_dict(archetype_dict)

    @classmethod
    def get_default(cls) -> 'GMArchetype':
        """
        Get a default balanced GM archetype.

        Returns:
            GMArchetype with balanced traits (0.5 for most values)
        """
        return cls(
            name="Default GM",
            description="Balanced general manager with moderate tendencies across all decision-making areas",
        )
