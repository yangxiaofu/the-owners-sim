"""
Dynasty Controller for The Owner's Sim UI

Mediates between Dynasty Selection UI and database for dynasty management.
Handles dynasty creation, validation, and retrieval operations.
"""

from typing import List, Dict, Any, Optional, Tuple
import sys
import os
import logging
from datetime import datetime

# Add src to path for imports
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from database.connection import DatabaseConnection
from database.dynasty_database_api import DynastyDatabaseAPI


class DynastyController:
    """
    Controller for Dynasty management operations.

    Manages dynasty lifecycle: creation, validation, retrieval.
    Follows the pattern: Dialog → Controller → Database

    Separation of concerns:
    - DynastyController: Dynasty CRUD operations (THIS)
    - SeasonController: Season management and calendar operations
    - LeagueController: League-wide statistics
    """

    def __init__(self, db_path: str = "data/database/nfl_simulation.db"):
        """
        Initialize dynasty controller.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self.db = DatabaseConnection(db_path)
        self.dynasty_db_api = DynastyDatabaseAPI(db_path)

    def list_existing_dynasties(self) -> List[Dict[str, Any]]:
        """
        Get all existing dynasties from database.

        Returns:
            List of dicts with dynasty metadata:
            - dynasty_id: Unique dynasty identifier
            - dynasty_name: Display name
            - owner_name: Owner's name
            - team_id: User's team (nullable)
            - created_at: Creation timestamp
            - is_active: Active status
        """
        return self.dynasty_db_api.get_all_dynasties()

    def dynasty_exists(self, dynasty_id: str) -> bool:
        """
        Check if a dynasty ID already exists.

        Args:
            dynasty_id: Dynasty identifier to check

        Returns:
            True if dynasty exists, False otherwise
        """
        return self.dynasty_db_api.dynasty_exists(dynasty_id)

    def validate_dynasty_name(self, name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a dynasty name for creation.

        Args:
            name: Dynasty name to validate

        Returns:
            Tuple of (is_valid, error_message)
            - (True, None) if valid
            - (False, "error message") if invalid
        """
        # Check for empty/whitespace only
        if not name or name.strip() == "":
            return (False, "Dynasty name cannot be empty")

        # Check length constraints
        if len(name) < 3:
            return (False, "Dynasty name must be at least 3 characters")

        if len(name) > 50:
            return (False, "Dynasty name must be 50 characters or less")

        # Check for special characters (allow letters, numbers, spaces, hyphens, apostrophes)
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'")
        if not all(c in allowed_chars for c in name):
            return (False, "Dynasty name contains invalid characters (use letters, numbers, spaces, hyphens, apostrophes only)")

        return (True, None)

    def generate_unique_dynasty_id(self, base_name: str) -> str:
        """
        Generate a unique dynasty ID from a base name.

        Strategy:
        1. Convert name to lowercase, replace spaces with underscores
        2. If unique, return it
        3. If not, append _001, _002, etc. until unique

        Args:
            base_name: Base dynasty name

        Returns:
            Unique dynasty_id string
        """
        # Sanitize base name
        base_id = base_name.lower().strip()
        base_id = base_id.replace(" ", "_")
        base_id = base_id.replace("'", "")
        base_id = base_id.replace("-", "_")

        # Remove any non-alphanumeric characters (except underscores)
        base_id = ''.join(c for c in base_id if c.isalnum() or c == '_')

        # Try base ID first
        if not self.dynasty_exists(base_id):
            return base_id

        # Append incrementing suffix until unique
        counter = 1
        while True:
            candidate_id = f"{base_id}_{counter:03d}"
            if not self.dynasty_exists(candidate_id):
                return candidate_id
            counter += 1

            # Safety check - prevent infinite loop
            if counter > 999:
                # Fall back to large counter (highly unlikely to be reached)
                import random
                random_suffix = random.randint(10000, 99999)
                return f"{base_id}_{random_suffix}"

    def create_dynasty(
        self,
        dynasty_name: str,
        owner_name: str = "User",
        team_id: Optional[int] = None,
        season: int = 2025
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Create a new dynasty with initialization.

        Delegates to DynastyInitializationService for complete dynasty setup.
        Controller responsibilities: validation, ID generation, error handling.

        Args:
            dynasty_name: Display name for the dynasty
            owner_name: Owner's name (default: "User")
            team_id: User's team ID 1-32 (optional)
            season: Starting season year (default: 2025)

        Returns:
            Tuple of (success, dynasty_id, error_message)
            - (True, dynasty_id, None) if successful
            - (False, "", "error message") if failed
        """
        # UI Concern: Validate dynasty name
        is_valid, error_msg = self.validate_dynasty_name(dynasty_name)
        if not is_valid:
            return (False, "", error_msg)

        # UI Concern: Generate unique dynasty ID
        dynasty_id = self.generate_unique_dynasty_id(dynasty_name)

        # Delegate to service: Complete dynasty initialization
        from services.dynasty_initialization_service import DynastyInitializationService

        service = DynastyInitializationService(
            db_path=self.db_path,
            logger=logging.getLogger("DynastyInitializationService")
        )

        try:
            result = service.initialize_dynasty(
                dynasty_id=dynasty_id,
                dynasty_name=dynasty_name,
                owner_name=owner_name,
                team_id=team_id,
                season=season
            )

            if result['success']:
                return (True, dynasty_id, None)
            else:
                error_message = result.get('error_message', 'Unknown error during dynasty initialization')
                return (False, "", error_message)

        except Exception as e:
            error_message = f"Failed to create dynasty: {str(e)}"
            print(f"[ERROR DynastyController] {error_message}")
            return (False, "", error_message)

    def get_dynasty_info(self, dynasty_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a dynasty.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty metadata or None if not found
        """
        return self.dynasty_db_api.get_dynasty_by_id(dynasty_id)

    def get_dynasty_stats(self, dynasty_id: str) -> Dict[str, Any]:
        """
        Get statistics about a dynasty (seasons played, games, etc.).

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            Dict with dynasty statistics
        """
        return self.dynasty_db_api.get_dynasty_stats(dynasty_id)

    def delete_dynasty(self, dynasty_id: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a dynasty and all associated data.

        WARNING: This is a destructive operation that cannot be undone.

        Args:
            dynasty_id: Dynasty identifier to delete

        Returns:
            Tuple of (success, error_message)
            - (True, None) if successful
            - (False, "error message") if failed
        """
        success = self.dynasty_db_api.delete_dynasty(dynasty_id)

        if success:
            return True, None
        else:
            return False, f"Failed to delete dynasty: {dynasty_id}"
