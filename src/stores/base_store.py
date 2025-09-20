"""
Base Store

Abstract base class for all entity stores. Provides common interface and
functionality for in-memory storage with transaction support.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
import json
import logging

T = TypeVar('T')


@dataclass
class StoreMetadata:
    """Metadata for store operations and tracking"""
    created_at: datetime = field(default_factory=datetime.now)
    last_modified: datetime = field(default_factory=datetime.now)
    item_count: int = 0
    store_version: str = "1.0.0"
    total_operations: int = 0
    last_cleared: Optional[datetime] = None


@dataclass
class TransactionLogEntry:
    """Entry in the transaction log for debugging and auditing"""
    timestamp: datetime
    operation: str  # 'add', 'update', 'delete', 'clear'
    key: Optional[str]
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)


class BaseStore(ABC, Generic[T]):
    """
    Abstract base class for all entity stores.

    Provides:
    - Common CRUD operations
    - Transaction logging
    - Validation framework
    - Snapshot capabilities for persistence
    """

    def __init__(self, store_name: str):
        """
        Initialize base store.

        Args:
            store_name: Unique name for this store
        """
        self.store_name = store_name
        self.data: Dict[str, T] = {}
        self.metadata = StoreMetadata()
        self.transaction_log: List[TransactionLogEntry] = []
        self.logger = logging.getLogger(f"Store.{store_name}")
        self._is_locked = False  # For transaction support

    @abstractmethod
    def add(self, key: str, item: T) -> None:
        """
        Add an item to the store.

        Args:
            key: Unique identifier for the item
            item: The item to store
        """
        pass

    @abstractmethod
    def get(self, key: str) -> Optional[T]:
        """
        Retrieve an item from the store.

        Args:
            key: Unique identifier for the item

        Returns:
            The item if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> Dict[str, T]:
        """
        Get all items in the store.

        Returns:
            Dictionary of all items keyed by their identifiers
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all items from the store."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate the consistency of data in the store.

        Returns:
            True if data is valid, False otherwise
        """
        pass

    def update(self, key: str, item: T) -> bool:
        """
        Update an existing item in the store.

        Args:
            key: Unique identifier for the item
            item: The updated item

        Returns:
            True if update successful, False if key not found
        """
        if key in self.data:
            self.data[key] = item
            self._update_metadata()
            self._log_transaction('update', key, True)
            return True
        else:
            self._log_transaction('update', key, False, {'error': 'Key not found'})
            return False

    def delete(self, key: str) -> bool:
        """
        Delete an item from the store.

        Args:
            key: Unique identifier for the item

        Returns:
            True if deletion successful, False if key not found
        """
        if key in self.data:
            del self.data[key]
            self._update_metadata()
            self._log_transaction('delete', key, True)
            return True
        else:
            self._log_transaction('delete', key, False, {'error': 'Key not found'})
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the store.

        Args:
            key: Unique identifier to check

        Returns:
            True if key exists, False otherwise
        """
        return key in self.data

    def size(self) -> int:
        """
        Get the number of items in the store.

        Returns:
            Number of items currently stored
        """
        return len(self.data)

    def is_empty(self) -> bool:
        """
        Check if the store is empty.

        Returns:
            True if no items in store, False otherwise
        """
        return len(self.data) == 0

    def lock(self) -> None:
        """Lock the store for exclusive access (transaction support)."""
        self._is_locked = True
        self.logger.debug(f"Store {self.store_name} locked")

    def unlock(self) -> None:
        """Unlock the store."""
        self._is_locked = False
        self.logger.debug(f"Store {self.store_name} unlocked")

    def is_locked(self) -> bool:
        """
        Check if store is locked.

        Returns:
            True if locked, False otherwise
        """
        return self._is_locked

    def get_snapshot(self) -> Dict[str, Any]:
        """
        Get a serializable snapshot of the store for persistence.

        Returns:
            Dictionary containing all store data and metadata
        """
        return {
            'store_name': self.store_name,
            'metadata': {
                'created_at': self.metadata.created_at.isoformat(),
                'last_modified': self.metadata.last_modified.isoformat(),
                'item_count': self.metadata.item_count,
                'store_version': self.metadata.store_version,
                'total_operations': self.metadata.total_operations,
                'last_cleared': self.metadata.last_cleared.isoformat() if self.metadata.last_cleared else None
            },
            'data': self._serialize_data(),
            'transaction_log_size': len(self.transaction_log)
        }

    def get_transaction_log(self, limit: Optional[int] = None) -> List[TransactionLogEntry]:
        """
        Get transaction log entries.

        Args:
            limit: Maximum number of entries to return (most recent first)

        Returns:
            List of transaction log entries
        """
        if limit:
            return self.transaction_log[-limit:]
        return self.transaction_log.copy()

    def clear_transaction_log(self) -> None:
        """Clear the transaction log."""
        self.transaction_log.clear()
        self.logger.info(f"Transaction log cleared for store {self.store_name}")

    @abstractmethod
    def _serialize_data(self) -> Dict[str, Any]:
        """
        Serialize store data for persistence.

        Returns:
            Serializable dictionary of store data
        """
        pass

    def _update_metadata(self) -> None:
        """Update store metadata after operations."""
        self.metadata.last_modified = datetime.now()
        self.metadata.item_count = len(self.data)
        self.metadata.total_operations += 1

    def _log_transaction(self, operation: str, key: Optional[str],
                        success: bool, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a transaction for audit and debugging.

        Args:
            operation: Type of operation performed
            key: Key involved in the operation
            success: Whether operation succeeded
            details: Additional details about the operation
        """
        entry = TransactionLogEntry(
            timestamp=datetime.now(),
            operation=operation,
            key=key,
            success=success,
            details=details or {}
        )
        self.transaction_log.append(entry)

        if not success:
            self.logger.warning(f"Failed operation: {operation} on key {key}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the store.

        Returns:
            Dictionary of store statistics
        """
        successful_ops = sum(1 for entry in self.transaction_log if entry.success)
        failed_ops = len(self.transaction_log) - successful_ops

        return {
            'store_name': self.store_name,
            'item_count': self.size(),
            'total_operations': self.metadata.total_operations,
            'successful_operations': successful_ops,
            'failed_operations': failed_ops,
            'created_at': self.metadata.created_at.isoformat(),
            'last_modified': self.metadata.last_modified.isoformat(),
            'is_locked': self._is_locked
        }