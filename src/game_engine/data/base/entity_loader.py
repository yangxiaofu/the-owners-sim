from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TypeVar, Generic
from .data_source import DataSource, DataSourceError

# Generic type for entity objects
T = TypeVar('T')


class EntityLoader(Generic[T], ABC):
    """
    Abstract base class for loading specific entity types.
    
    Provides common functionality like caching, validation, and data source management.
    Subclasses implement entity-specific loading and mapping logic.
    
    Type parameter T should be the entity class (Team, Player, Stadium, etc.)
    """
    
    def __init__(self, data_source_type: str, **config):
        """
        Initialize the entity loader with a data source.
        
        Args:
            data_source_type: Type of data source ("json", "database", "api")
            **config: Configuration passed to data source constructor
        """
        self.data_source = self._create_data_source(data_source_type, **config)
        self._cache: Dict[Any, T] = {}
        self._cache_enabled = config.get('enable_cache', True)
        self._validate_data_source()
    
    @abstractmethod
    def load(self, ids: List[Any] = None, **filters) -> Dict[Any, T]:
        """
        Load entities by IDs or filters.
        
        Args:
            ids: Optional list of entity IDs to load
            **filters: Additional filters specific to entity type
            
        Returns:
            Dict mapping entity ID -> entity object
        """
        pass
    
    @abstractmethod
    def _map_data(self, raw_data: Dict[str, Any]) -> T:
        """
        Convert raw data dictionary to typed entity object.
        
        Args:
            raw_data: Raw data from data source
            
        Returns:
            Typed entity object
        """
        pass
    
    @abstractmethod
    def get_entity_type(self) -> str:
        """
        Return the entity type name for data source queries.
        
        Returns:
            Entity type string ("teams", "players", etc.)
        """
        pass
    
    def get_all(self) -> Dict[Any, T]:
        """
        Load all entities of this type.
        
        Returns:
            Dict mapping entity ID -> entity object
        """
        return self.load()
    
    def get_by_id(self, entity_id: Any) -> Optional[T]:
        """
        Load a single entity by ID.
        
        Args:
            entity_id: ID of entity to load
            
        Returns:
            Entity object or None if not found
        """
        entities = self.load(ids=[entity_id])
        return entities.get(entity_id)
    
    def count(self, **filters) -> int:
        """
        Count entities matching the given filters.
        
        Args:
            **filters: Filters to apply
            
        Returns:
            Number of matching entities
        """
        entities = self.load(**filters)
        return len(entities)
    
    def _create_data_source(self, source_type: str, **config) -> DataSource:
        """
        Factory method to create appropriate data source.
        
        Args:
            source_type: Type of data source to create
            **config: Configuration for data source
            
        Returns:
            Configured DataSource instance
            
        Raises:
            ValueError: If source_type is not supported
        """
        if source_type == "json":
            from ..sources.json_data_source import JsonDataSource
            return JsonDataSource(**config)
        elif source_type == "database":
            from ..sources.database_data_source import DatabaseDataSource
            return DatabaseDataSource(**config)
        elif source_type == "api":
            from ..sources.api_data_source import ApiDataSource
            return ApiDataSource(**config)
        else:
            raise ValueError(f"Unsupported data source type: {source_type}")
    
    def _validate_data_source(self) -> None:
        """
        Validate that data source is connected and supports our entity type.
        
        Raises:
            DataSourceError: If validation fails
        """
        if not self.data_source.validate_connection():
            raise DataSourceError(f"Data source connection failed for {self.get_entity_type()}")
        
        if not self.data_source.supports_entity_type(self.get_entity_type()):
            raise DataSourceError(f"Data source does not support entity type: {self.get_entity_type()}")
    
    def _apply_cache(self, cache_key: str, loader_func) -> Any:
        """
        Apply caching to a loader function.
        
        Args:
            cache_key: Key for caching
            loader_func: Function to call if not cached
            
        Returns:
            Cached or fresh result
        """
        if not self._cache_enabled:
            return loader_func()
        
        if cache_key not in self._cache:
            self._cache[cache_key] = loader_func()
        
        return self._cache[cache_key]
    
    def _build_cache_key(self, ids: List[Any] = None, **filters) -> str:
        """
        Build a cache key from load parameters.
        
        Args:
            ids: Entity IDs being loaded
            **filters: Additional filters
            
        Returns:
            String cache key
        """
        parts = [self.get_entity_type()]
        
        if ids:
            parts.append(f"ids:{','.join(map(str, sorted(ids)))}")
        
        for key, value in sorted(filters.items()):
            if isinstance(value, list):
                value = ','.join(map(str, sorted(value)))
            parts.append(f"{key}:{value}")
        
        return "|".join(parts)
    
    def _load_raw_data(self, ids: List[Any] = None, **filters) -> List[Dict[str, Any]]:
        """
        Load raw data from data source with filtering.
        
        Args:
            ids: Optional entity IDs to load
            **filters: Additional filters
            
        Returns:
            List of raw data dictionaries
        """
        # Prepare filters for data source
        source_filters = dict(filters)
        if ids is not None:
            source_filters["ids"] = ids
        
        return self.data_source.read(self.get_entity_type(), source_filters)
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for debugging.
        
        Returns:
            Dict with cache size, hit rate, etc.
        """
        return {
            "enabled": self._cache_enabled,
            "size": len(self._cache),
            "keys": list(self._cache.keys()) if len(self._cache) < 10 else f"{len(self._cache)} items"
        }
    
    def validate_entities(self, entities: Dict[Any, T]) -> bool:
        """
        Validate loaded entities for data integrity.
        
        Args:
            entities: Dict of loaded entities
            
        Returns:
            True if all entities are valid
        """
        if not entities:
            return True
        
        # Basic validation - ensure all entities have required attributes
        for entity_id, entity in entities.items():
            if not hasattr(entity, 'id') or entity.id != entity_id:
                return False
        
        return True
    
    def get_loader_info(self) -> Dict[str, Any]:
        """
        Get information about this loader for debugging.
        
        Returns:
            Dict with loader type, entity type, data source info, cache stats
        """
        return {
            "loader_type": self.__class__.__name__,
            "entity_type": self.get_entity_type(),
            "data_source": self.data_source.get_source_info(),
            "cache": self.get_cache_stats()
        }