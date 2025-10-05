"""Statistical distributions for player attribute generation."""

import random
import numpy as np
from typing import Tuple


class AttributeDistribution:
    """Statistical distributions for player attribute generation."""

    @staticmethod
    def normal(mean: float, std_dev: float, min_val: float, max_val: float) -> int:
        """Generate value from bounded normal distribution.

        Args:
            mean: Target mean value
            std_dev: Standard deviation
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Integer value within bounds
        """
        value = random.gauss(mean, std_dev)
        return int(max(min_val, min(max_val, value)))

    @staticmethod
    def beta(alpha: float, beta: float, min_val: float, max_val: float) -> int:
        """Generate value from beta distribution.

        Args:
            alpha: Alpha parameter (shape)
            beta: Beta parameter (shape)
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Integer value scaled to range
        """
        value = np.random.beta(alpha, beta)
        scaled = min_val + (max_val - min_val) * value
        return int(scaled)

    @staticmethod
    def weighted_choice(choices: list[Tuple[str, float]]) -> str:
        """Select from weighted choices.

        Args:
            choices: List of (choice, weight) tuples

        Returns:
            Selected choice string
        """
        weights = [w for _, w in choices]
        return random.choices([c for c, _ in choices], weights=weights)[0]
