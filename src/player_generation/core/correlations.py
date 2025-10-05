"""Manages correlated attribute generation for realistic player profiles."""

from typing import Dict, Optional
import random


class AttributeCorrelation:
    """Manages correlated attribute generation."""

    # Correlation coefficients (-1.0 to 1.0)
    CORRELATIONS = {
        ("size", "speed"): -0.6,  # Bigger players are slower
        ("strength", "size"): 0.7,  # Bigger players are stronger
        ("awareness", "experience"): 0.8,  # Experience improves awareness
        ("acceleration", "speed"): 0.9,  # Speed and acceleration highly correlated
        ("agility", "size"): -0.5,  # Bigger players less agile
    }

    @staticmethod
    def apply_correlation(
        base_value: int,
        correlated_attr: str,
        base_attr: str,
        target_mean: int,
        target_std: int
    ) -> int:
        """Apply correlation between two attributes.

        Args:
            base_value: Value of the base attribute
            correlated_attr: Name of attribute to generate
            base_attr: Name of base attribute
            target_mean: Target mean for correlated attribute
            target_std: Target standard deviation

        Returns:
            Correlated attribute value within bounds
        """
        correlation = AttributeCorrelation.CORRELATIONS.get(
            (base_attr, correlated_attr), 0
        )

        if correlation == 0:
            # No correlation - use pure random
            return int(random.gauss(target_mean, target_std))

        # Calculate correlated value
        base_deviation = (base_value - target_mean) / target_std
        correlated_deviation = correlation * base_deviation
        correlated_value = target_mean + (correlated_deviation * target_std)

        # Add some random noise
        noise = random.gauss(0, target_std * 0.3)
        final_value = correlated_value + noise

        return int(max(40, min(99, final_value)))

    @staticmethod
    def get_correlation(attr1: str, attr2: str) -> float:
        """Get correlation coefficient between two attributes.

        Args:
            attr1: First attribute name
            attr2: Second attribute name

        Returns:
            Correlation coefficient (0 if no correlation)
        """
        return AttributeCorrelation.CORRELATIONS.get(
            (attr1, attr2),
            AttributeCorrelation.CORRELATIONS.get((attr2, attr1), 0)
        )
