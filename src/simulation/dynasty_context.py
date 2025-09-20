"""
Dynasty Context Manager

Provides global access to dynasty ID and related context throughout
the simulation. Uses singleton pattern to ensure consistent dynasty
ID across all components.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, date


class DynastyContext:
    """
    Singleton class managing dynasty-wide context.
    
    A dynasty represents a complete simulation run, from season initialization
    through completion. All data persisted to the database is tagged with the
    dynasty ID to allow multiple simulation runs to coexist.
    """
    
    _instance: Optional['DynastyContext'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'DynastyContext':
        """Enforce singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize dynasty context (only runs once due to singleton)."""
        if not self._initialized:
            self.dynasty_id: Optional[str] = None
            self.season_year: Optional[int] = None
            self.dynasty_name: Optional[str] = None
            self.created_at: Optional[datetime] = None
            self.metadata: Dict[str, Any] = {}
            self._initialized = True
    
    def initialize_dynasty(self, 
                          dynasty_name: str,
                          season_year: int,
                          dynasty_id: Optional[str] = None) -> str:
        """
        Initialize a new dynasty or load an existing one.
        
        Args:
            dynasty_name: Human-readable name for this dynasty
            season_year: Starting season year (e.g., 2025)
            dynasty_id: Optional existing dynasty ID to load
            
        Returns:
            The dynasty ID (generated or provided)
        """
        if dynasty_id:
            self.dynasty_id = dynasty_id
        else:
            # Generate new UUID for this dynasty
            self.dynasty_id = str(uuid.uuid4())
        
        self.dynasty_name = dynasty_name
        self.season_year = season_year
        self.created_at = datetime.now()
        
        # Initialize metadata
        self.metadata = {
            'version': '1.0.0',
            'simulation_type': 'full_season',
            'start_date': date.today().isoformat(),
            'initial_year': season_year
        }
        
        return self.dynasty_id
    
    def get_dynasty_id(self) -> str:
        """
        Get the current dynasty ID.
        
        Returns:
            Dynasty ID string
            
        Raises:
            RuntimeError: If dynasty has not been initialized
        """
        if not self.dynasty_id:
            raise RuntimeError(
                "Dynasty not initialized. Call initialize_dynasty() first."
            )
        return self.dynasty_id
    
    def get_season_year(self) -> int:
        """
        Get the current season year.
        
        Returns:
            Season year
            
        Raises:
            RuntimeError: If dynasty has not been initialized
        """
        if not self.season_year:
            raise RuntimeError(
                "Dynasty not initialized. Call initialize_dynasty() first."
            )
        return self.season_year
    
    def set_metadata(self, key: str, value: Any) -> None:
        """
        Set a metadata value for this dynasty.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value for this dynasty.
        
        Args:
            key: Metadata key
            default: Default value if key not found
            
        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)
    
    def advance_season(self, new_year: int) -> None:
        """
        Advance to a new season year.
        
        Args:
            new_year: The new season year
        """
        if not self.dynasty_id:
            raise RuntimeError(
                "Dynasty not initialized. Call initialize_dynasty() first."
            )
        
        self.season_year = new_year
        self.metadata['current_year'] = new_year
        self.metadata['seasons_completed'] = self.metadata.get('seasons_completed', 0) + 1
    
    def reset(self) -> None:
        """
        Reset the dynasty context (useful for testing).
        
        Warning: This clears all dynasty data. Use with caution.
        """
        self.dynasty_id = None
        self.season_year = None
        self.dynasty_name = None
        self.created_at = None
        self.metadata = {}
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current dynasty context.
        
        Returns:
            Dictionary with dynasty information
        """
        if not self.dynasty_id:
            return {'status': 'not_initialized'}
        
        return {
            'dynasty_id': self.dynasty_id,
            'dynasty_name': self.dynasty_name,
            'season_year': self.season_year,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata
        }
    
    def is_initialized(self) -> bool:
        """
        Check if dynasty has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self.dynasty_id is not None
    
    @classmethod
    def get_instance(cls) -> 'DynastyContext':
        """
        Get the singleton instance.
        
        Returns:
            The DynastyContext instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __str__(self) -> str:
        """String representation."""
        if self.dynasty_id:
            return f"Dynasty '{self.dynasty_name}' ({self.dynasty_id[:8]}...) - Year {self.season_year}"
        return "Dynasty (not initialized)"
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return f"DynastyContext(id={self.dynasty_id}, name={self.dynasty_name}, year={self.season_year})"


# Global accessor function for convenience
def get_dynasty_context() -> DynastyContext:
    """
    Get the global dynasty context instance.
    
    Returns:
        The singleton DynastyContext instance
    """
    return DynastyContext.get_instance()


def get_current_dynasty_id() -> str:
    """
    Get the current dynasty ID.
    
    Returns:
        Dynasty ID string
        
    Raises:
        RuntimeError: If dynasty has not been initialized
    """
    return get_dynasty_context().get_dynasty_id()
