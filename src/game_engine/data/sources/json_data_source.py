import json
import os
from typing import Dict, List, Any, Optional
from ..base.data_source import DataSource, ConnectionError, ValidationError, FilterError


class JsonDataSource(DataSource):
    """
    JSON file-based data source implementation.
    
    Loads data from JSON files in a specified directory.
    Expected file structure:
    - base_path/teams.json
    - base_path/players.json
    - base_path/stadiums.json
    - etc.
    
    Each JSON file should have format:
    {
      "entity_type": {
        "id1": {...},
        "id2": {...}
      }
    }
    """
    
    def __init__(self, base_path: str = "src/game_engine/data/sample_data"):
        """
        Initialize JSON data source.
        
        Args:
            base_path: Directory containing JSON files
        """
        self.base_path = base_path
        self._data_cache: Dict[str, Dict[str, Any]] = {}
        self._file_timestamps: Dict[str, float] = {}
        
        # Ensure base path exists
        if not os.path.exists(base_path):
            raise ConnectionError(f"Base path does not exist: {base_path}")
    
    def read(self, entity_type: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Read entities from JSON file with optional filtering.
        
        Args:
            entity_type: Type of entity ("teams", "players", etc.)
            filters: Optional filters to apply
            
        Returns:
            List of entity dictionaries
            
        Raises:
            ConnectionError: If file cannot be read
            FilterError: If invalid filters are provided
        """
        # Load data from file (with caching)
        entities_dict = self._load_entity_file(entity_type)
        
        # Convert to list of entities with ID included
        entities_list = []
        for entity_id, entity_data in entities_dict.items():
            entity_copy = dict(entity_data)
            entity_copy['id'] = self._parse_id(entity_id)
            entities_list.append(entity_copy)
        
        # Apply filters if provided
        if filters:
            entities_list = self._apply_filters(entities_list, filters)
        
        return entities_list
    
    def validate_connection(self) -> bool:
        """
        Test if JSON data source is accessible.
        
        Returns:
            True if base path exists and is readable
        """
        try:
            return os.path.exists(self.base_path) and os.access(self.base_path, os.R_OK)
        except Exception:
            return False
    
    def get_source_info(self) -> Dict[str, Any]:
        """Get information about this JSON data source."""
        return {
            "type": "JsonDataSource",
            "base_path": self.base_path,
            "connected": self.validate_connection(),
            "cached_files": list(self._data_cache.keys()),
            "available_files": self._get_available_files()
        }
    
    def supports_entity_type(self, entity_type: str) -> bool:
        """Check if JSON file exists for entity type."""
        file_path = os.path.join(self.base_path, f"{entity_type}.json")
        return os.path.exists(file_path)
    
    def _load_entity_file(self, entity_type: str) -> Dict[str, Any]:
        """
        Load and cache JSON file for entity type.
        
        Args:
            entity_type: Type of entity to load
            
        Returns:
            Dict mapping entity ID -> entity data
            
        Raises:
            ConnectionError: If file cannot be read
            ValidationError: If JSON is invalid
        """
        file_path = os.path.join(self.base_path, f"{entity_type}.json")
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise ConnectionError(f"JSON file not found: {file_path}")
        
        # Check if we need to reload (file changed or not cached)
        try:
            file_mtime = os.path.getmtime(file_path)
            if (entity_type not in self._data_cache or 
                self._file_timestamps.get(entity_type, 0) < file_mtime):
                
                # Load fresh data from file
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate JSON structure
                if not isinstance(data, dict) or entity_type not in data:
                    raise ValidationError(f"Invalid JSON structure in {file_path}. Expected: {{'entity_type': {{}}}}")
                
                # Cache the data
                self._data_cache[entity_type] = data[entity_type]
                self._file_timestamps[entity_type] = file_mtime
                
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ConnectionError(f"Error reading {file_path}: {e}")
        
        return self._data_cache[entity_type]
    
    def _apply_filters(self, entities: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply filters to list of entities.
        
        Args:
            entities: List of entity dictionaries
            filters: Filters to apply
            
        Returns:
            Filtered list of entities
        """
        filtered = entities
        
        # Filter by IDs
        if 'ids' in filters and filters['ids'] is not None:
            id_set = set(filters['ids'])
            filtered = [e for e in filtered if e['id'] in id_set]
        
        # Filter players by team_ids
        if 'team_ids' in filters and filters['team_ids'] is not None:
            team_id_set = set(filters['team_ids'])
            filtered = [e for e in filtered if e.get('team_id') in team_id_set]
        
        # Filter players by positions
        if 'positions' in filters and filters['positions'] is not None:
            position_set = set(filters['positions'])
            filtered = [e for e in filtered if e.get('position') in position_set]
        
        # Filter players by roles
        if 'roles' in filters and filters['roles'] is not None:
            role_set = set(filters['roles'])
            filtered = [e for e in filtered if e.get('role') in role_set]
        
        # Filter teams by division
        if 'division' in filters and filters['division'] is not None:
            filtered = [e for e in filtered if e.get('division') == filters['division']]
        
        # Filter teams by conference
        if 'conference' in filters and filters['conference'] is not None:
            filtered = [e for e in filtered if e.get('conference') == filters['conference']]
        
        # Filter stadiums by city
        if 'city' in filters and filters['city'] is not None:
            filtered = [e for e in filtered if e.get('city') == filters['city']]
        
        # Filter stadiums by surface type
        if 'surface_type' in filters and filters['surface_type'] is not None:
            filtered = [e for e in filtered if e.get('surface_type') == filters['surface_type']]
        
        return filtered
    
    def _parse_id(self, id_str: str) -> Any:
        """
        Parse ID string to appropriate type.
        
        Args:
            id_str: String ID from JSON
            
        Returns:
            Parsed ID (int for numeric IDs, str otherwise)
        """
        try:
            # Try to parse as integer
            return int(id_str)
        except ValueError:
            # Keep as string
            return id_str
    
    def _get_available_files(self) -> List[str]:
        """Get list of available JSON files in base path."""
        try:
            files = []
            for filename in os.listdir(self.base_path):
                if filename.endswith('.json'):
                    files.append(filename[:-5])  # Remove .json extension
            return files
        except Exception:
            return []
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._data_cache.clear()
        self._file_timestamps.clear()
    
    def refresh_entity(self, entity_type: str) -> None:
        """
        Force refresh of specific entity type from file.
        
        Args:
            entity_type: Entity type to refresh
        """
        if entity_type in self._data_cache:
            del self._data_cache[entity_type]
        if entity_type in self._file_timestamps:
            del self._file_timestamps[entity_type]