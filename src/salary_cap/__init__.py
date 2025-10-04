"""
NFL Salary Cap System

Complete salary cap management system including contract tracking,
cap space calculations, dead money, franchise tags, and compliance validation.

Core Components:
- CapDatabaseAPI: Database operations for all cap data
- CapCalculator: Mathematical operations for cap calculations
- ContractManager: Contract creation and modification
- CapValidator: NFL rule compliance validation
- TagManager: Franchise tags and RFA tenders

Based on 2024-2025 NFL CBA rules.
"""

from .cap_calculator import CapCalculator
from .contract_manager import ContractManager
from .cap_database_api import CapDatabaseAPI
from .cap_validator import CapValidator

__version__ = "1.0.0"

__all__ = [
    "CapCalculator",
    "ContractManager",
    "CapDatabaseAPI",
    "CapValidator",
]
