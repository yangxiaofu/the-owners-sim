"""
Database Module

Provides SQLite database connectivity and management for the NFL simulation.
Supports multiple dynasties with complete data isolation.
"""

from .connection import DatabaseConnection

__all__ = ['DatabaseConnection']