"""
Headline Generators Package - Type-specific headline generators for transactions.

Part of Transaction-Media Architecture Refactoring.

Provides:
- BaseHeadlineGenerator: Abstract base class with shared logic
- Type-specific generators for all transaction types
- GeneratedHeadline: Output dataclass for generated headlines
"""

from .base_generator import BaseHeadlineGenerator, GeneratedHeadline
from .cut_generator import RosterCutGenerator
from .signing_generator import SigningGenerator
from .trade_generator import TradeGenerator
from .tag_generator import FranchiseTagGenerator
from .resigning_generator import ResigningGenerator
from .waiver_generator import WaiverGenerator
from .draft_generator import DraftGenerator
from .awards_generator import AwardsGenerator

__all__ = [
    # Base classes
    'BaseHeadlineGenerator',
    'GeneratedHeadline',
    # Type-specific generators
    'RosterCutGenerator',
    'SigningGenerator',
    'TradeGenerator',
    'FranchiseTagGenerator',
    'ResigningGenerator',
    'WaiverGenerator',
    'DraftGenerator',
    'AwardsGenerator',
]