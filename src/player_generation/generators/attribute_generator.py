"""Generates player attributes based on archetype."""

from typing import Dict
from ..core.distributions import AttributeDistribution
from ..core.correlations import AttributeCorrelation
from ..archetypes.base_archetype import PlayerArchetype, AttributeRange


class AttributeGenerator:
    """Generates player attributes based on archetype."""

    @staticmethod
    def generate_attributes(archetype: PlayerArchetype) -> Dict[str, int]:
        """Generate all attributes for a player based on archetype.

        Args:
            archetype: Player archetype defining attribute ranges

        Returns:
            Dictionary of attribute name to value
        """
        attributes = {}

        # Step 1: Generate physical attributes first (they affect others)
        physical_attrs = AttributeGenerator._generate_physical_attributes(
            archetype.physical_attributes
        )
        attributes.update(physical_attrs)

        # Step 2: Generate mental attributes
        mental_attrs = AttributeGenerator._generate_mental_attributes(
            archetype.mental_attributes
        )
        attributes.update(mental_attrs)

        # Step 3: Generate position-specific attributes with correlations
        position_attrs = AttributeGenerator._generate_position_attributes(
            archetype.position_attributes,
            physical_attrs
        )
        attributes.update(position_attrs)

        return attributes

    @staticmethod
    def _generate_physical_attributes(attr_ranges: Dict[str, AttributeRange]) -> Dict[str, int]:
        """Generate physical attributes with correlations.

        Args:
            attr_ranges: Physical attribute ranges

        Returns:
            Dictionary of physical attributes
        """
        attributes = {}

        # Generate size first if it exists (affects other physicals)
        if "size" in attr_ranges:
            size_range = attr_ranges["size"]
            attributes["size"] = AttributeDistribution.normal(
                size_range.mean, size_range.std_dev,
                size_range.min, size_range.max
            )

        # Generate other physical attributes with correlations
        for attr_name, attr_range in attr_ranges.items():
            if attr_name == "size":
                continue  # Already generated

            if "size" in attributes:
                # Apply size correlation
                attributes[attr_name] = AttributeCorrelation.apply_correlation(
                    base_value=attributes["size"],
                    correlated_attr=attr_name,
                    base_attr="size",
                    target_mean=attr_range.mean,
                    target_std=attr_range.std_dev
                )
            else:
                # No correlation
                attributes[attr_name] = AttributeDistribution.normal(
                    attr_range.mean, attr_range.std_dev,
                    attr_range.min, attr_range.max
                )

        return attributes

    @staticmethod
    def _generate_mental_attributes(attr_ranges: Dict[str, AttributeRange]) -> Dict[str, int]:
        """Generate mental attributes.

        Args:
            attr_ranges: Mental attribute ranges

        Returns:
            Dictionary of mental attributes
        """
        attributes = {}

        # Mental attributes are mostly independent
        for attr_name, attr_range in attr_ranges.items():
            attributes[attr_name] = AttributeDistribution.normal(
                attr_range.mean, attr_range.std_dev,
                attr_range.min, attr_range.max
            )

        return attributes

    @staticmethod
    def _generate_position_attributes(
        attr_ranges: Dict[str, AttributeRange],
        physical_attrs: Dict[str, int]
    ) -> Dict[str, int]:
        """Generate position attributes with physical correlations.

        Args:
            attr_ranges: Position-specific attribute ranges
            physical_attrs: Previously generated physical attributes

        Returns:
            Dictionary of position attributes
        """
        attributes = {}

        for attr_name, attr_range in attr_ranges.items():
            # Check for relevant correlations
            if attr_name == "speed" and "size" in physical_attrs:
                attributes[attr_name] = AttributeCorrelation.apply_correlation(
                    base_value=physical_attrs["size"],
                    correlated_attr="speed",
                    base_attr="size",
                    target_mean=attr_range.mean,
                    target_std=attr_range.std_dev
                )
            else:
                attributes[attr_name] = AttributeDistribution.normal(
                    attr_range.mean, attr_range.std_dev,
                    attr_range.min, attr_range.max
                )

        return attributes

    @staticmethod
    def calculate_overall(attributes: Dict[str, int], position: str) -> int:
        """Calculate overall rating based on position-weighted attributes.

        Args:
            attributes: Player attributes
            position: Player position

        Returns:
            Overall rating (40-99)
        """
        # Position-specific weights
        weights = {
            "QB": {"accuracy": 0.25, "arm_strength": 0.20, "awareness": 0.20,
                   "speed": 0.10, "agility": 0.10, "strength": 0.15},
            "RB": {"speed": 0.25, "agility": 0.20, "strength": 0.15,
                   "carrying": 0.15, "vision": 0.15, "elusiveness": 0.10},
            "WR": {"speed": 0.25, "catching": 0.25, "route_running": 0.20,
                   "agility": 0.15, "awareness": 0.15},
            "TE": {"catching": 0.20, "route_running": 0.15, "blocking": 0.20,
                   "speed": 0.15, "strength": 0.15, "awareness": 0.15},
            "OT": {"pass_blocking": 0.25, "run_blocking": 0.25, "strength": 0.20,
                   "awareness": 0.15, "agility": 0.15},
            "OG": {"run_blocking": 0.25, "pass_blocking": 0.25, "strength": 0.25,
                   "awareness": 0.15, "agility": 0.10},
            "C": {"pass_blocking": 0.20, "run_blocking": 0.20, "strength": 0.20,
                  "awareness": 0.25, "agility": 0.15},
            "EDGE": {"pass_rush": 0.25, "power_moves": 0.20, "speed": 0.20,
                     "finesse_moves": 0.15, "pursuit": 0.10, "awareness": 0.10},
            "DT": {"power_moves": 0.25, "block_shedding": 0.25, "strength": 0.20,
                   "pursuit": 0.15, "awareness": 0.15},
            "LB": {"tackling": 0.20, "pursuit": 0.20, "awareness": 0.20,
                   "speed": 0.15, "coverage": 0.15, "strength": 0.10},
            "CB": {"coverage": 0.25, "speed": 0.25, "agility": 0.20,
                   "awareness": 0.15, "press": 0.15},
            "S": {"awareness": 0.25, "speed": 0.20, "coverage": 0.20,
                  "tackling": 0.20, "pursuit": 0.15},
            "K": {"kick_power": 0.40, "kick_accuracy": 0.40, "awareness": 0.20},
            "P": {"kick_power": 0.40, "kick_accuracy": 0.40, "awareness": 0.20},
        }

        position_weights = weights.get(position, {})
        if not position_weights:
            # Fallback: average all attributes
            return int(sum(attributes.values()) / len(attributes))

        weighted_sum = sum(
            attributes.get(attr, 70) * weight
            for attr, weight in position_weights.items()
        )

        return int(weighted_sum)