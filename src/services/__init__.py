"""
Services Package

Business logic services extracted from monolithic controllers to improve
separation of concerns and reduce God Object anti-patterns.

Available Services:
- TransactionService: AI transaction evaluation and execution

Available Helpers:
- extract_playoff_champions: Extract AFC/NFC champions from playoff results

This package was created as part of Phase 3: Service Extraction refactoring.
"""

from src.services.transaction_service import TransactionService
from src.services.playoff_helpers import extract_playoff_champions

__all__ = ['TransactionService', 'extract_playoff_champions']
