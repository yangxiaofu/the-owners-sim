"""
Database Module

Provides SQLite database connectivity and management for the NFL simulation.
Supports multiple dynasties with complete data isolation.
"""

from .connection import DatabaseConnection
from .transaction_context import TransactionContext, TransactionState, transaction

__all__ = ['DatabaseConnection', 'TransactionContext', 'TransactionState', 'transaction']