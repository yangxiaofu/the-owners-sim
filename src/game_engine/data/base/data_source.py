from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class DataSource(ABC):
    """
    Abstract data source interface for pluggable data backends.
    
    Implementations can load from:
    - JSON files (development/testing)
    - SQLite database (production)
    - REST APIs (future integration)
    - Mock generators (unit testing)
    """
    
    @abstractmethod
    def read(self, entity_type: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Read raw data for an entity type with optional filtering.
        
        Args:
            entity_type: Type of entity to load ("teams", "players", "stadiums", etc.)
            filters: Optional filters dict with keys like:
                - ids: List of entity IDs to load
                - team_ids: Filter players by team
                - positions: Filter players by position
                - division: Filter teams by division
                
        Returns:
            List of raw data dictionaries
            
        Example:
            # Load specific teams
            data_source.read("teams", {"ids": [1, 2, 3]})
            
            # Load players for specific teams and positions
            data_source.read("players", {"team_ids": [1, 2], "positions": ["RB", "QB"]})
        """
        pass
    
    @abstractmethod
    def validate_connection(self) -> bool:
        """
        Test if the data source is accessible and contains valid data.
        
        Returns:
            True if connection is valid and data can be read
        """
        pass
    
    def get_source_info(self) -> Dict[str, Any]:
        """
        Get information about this data source for debugging/logging.
        
        Returns:
            Dict with source type, location, status, etc.
        """
        return {
            "type": self.__class__.__name__,
            "connected": self.validate_connection()
        }
    
    def supports_entity_type(self, entity_type: str) -> bool:
        """
        Check if this data source supports the given entity type.
        
        Args:
            entity_type: Entity type to check
            
        Returns:
            True if entity type is supported
        """
        try:
            # Attempt to read with empty result - if no exception, it's supported
            self.read(entity_type, {"ids": []})
            return True
        except (ValueError, KeyError, FileNotFoundError):
            return False
    
    def get_supported_filters(self, entity_type: str) -> List[str]:
        """
        Get list of supported filter keys for an entity type.
        
        Args:
            entity_type: Entity type to check
            
        Returns:
            List of supported filter keys
        """
        # Default implementation - subclasses can override
        common_filters = ["ids"]
        
        if entity_type == "players":
            return common_filters + ["team_ids", "positions", "roles"]
        elif entity_type == "teams":
            return common_filters + ["division", "conference"] 
        elif entity_type == "stadiums":
            return common_filters + ["city", "surface_type"]
        else:
            return common_filters


class DataSourceError(Exception):
    """Base exception for data source related errors."""
    pass


class ConnectionError(DataSourceError):
    """Raised when data source connection fails."""
    pass


class ValidationError(DataSourceError):
    """Raised when data validation fails."""
    pass


class FilterError(DataSourceError):
    """Raised when invalid filters are applied."""
    pass