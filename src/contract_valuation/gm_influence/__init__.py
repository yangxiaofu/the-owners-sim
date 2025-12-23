"""
GM influence system for contract valuation.

Determines how GM personality affects factor weighting in valuations.
"""

from .styles import GMStyle
from .weight_calculator import GMWeightCalculator, WeightCalculationResult

__all__ = [
    'GMStyle',
    'GMWeightCalculator',
    'WeightCalculationResult',
]