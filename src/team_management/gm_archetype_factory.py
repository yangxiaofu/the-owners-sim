"""
GM Archetype Factory

Factory for loading and creating GM archetypes with caching.
"""

import json
from pathlib import Path
from typing import Dict, Optional

from .gm_archetype import GMArchetype


class GMArchetypeFactory:
    """
    Factory for loading and creating GM archetypes.

    Loads base templates from JSON and applies team-specific customizations.
    Caches loaded archetypes for performance.
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize factory with config directory path.

        Args:
            config_path: Path to config directory (defaults to src/config)
        """
        if config_path is None:
            # Default to src/config relative to this file
            current_file = Path(__file__)
            src_dir = current_file.parent.parent
            config_path = src_dir / "config"

        self.config_path = config_path
        self.base_archetypes_path = config_path / "gm_archetypes" / "base_archetypes.json"
        self.gm_profiles_path = config_path / "gm_profiles"

        # Cache for loaded archetypes
        self._base_archetypes: Dict[str, GMArchetype] = {}
        self._team_archetypes: Dict[int, GMArchetype] = {}

        # Load base archetypes on initialization
        self._load_base_archetypes()

    def _load_base_archetypes(self):
        """Load all base archetype templates from JSON"""
        if not self.base_archetypes_path.exists():
            raise FileNotFoundError(
                f"Base archetypes file not found: {self.base_archetypes_path}"
            )

        with open(self.base_archetypes_path, 'r') as f:
            data = json.load(f)

        for key, archetype_data in data.items():
            self._base_archetypes[key] = GMArchetype.from_dict(archetype_data)

    def get_base_archetype(self, archetype_name: str) -> GMArchetype:
        """
        Get a base archetype template by name.

        Args:
            archetype_name: Name of archetype (win_now, rebuilder, etc.)

        Returns:
            GMArchetype instance

        Raises:
            ValueError: If archetype name not found
        """
        if archetype_name not in self._base_archetypes:
            available = ', '.join(self._base_archetypes.keys())
            raise ValueError(
                f"Unknown archetype '{archetype_name}'. Available: {available}"
            )

        return self._base_archetypes[archetype_name]

    def get_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Get the GM archetype for a specific team.

        Loads from cache if available, otherwise loads from JSON config.

        Args:
            team_id: Team ID (1-32)

        Returns:
            GMArchetype instance for the team

        Raises:
            ValueError: If team_id is invalid
            FileNotFoundError: If team config file not found
        """
        if not 1 <= team_id <= 32:
            raise ValueError(f"team_id must be between 1 and 32, got {team_id}")

        # Check cache first
        if team_id in self._team_archetypes:
            return self._team_archetypes[team_id]

        # Load from file
        team_archetype = self._load_team_archetype(team_id)

        # Cache and return
        self._team_archetypes[team_id] = team_archetype
        return team_archetype

    def _load_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Load team archetype from JSON config file.

        Args:
            team_id: Team ID (1-32)

        Returns:
            GMArchetype instance
        """
        # Find team config file
        team_files = list(self.gm_profiles_path.glob(f"team_{team_id:02d}_*.json"))

        if not team_files:
            raise FileNotFoundError(
                f"No GM profile found for team_id {team_id} in {self.gm_profiles_path}"
            )

        if len(team_files) > 1:
            raise ValueError(
                f"Multiple GM profiles found for team_id {team_id}: {team_files}"
            )

        # Load team config
        with open(team_files[0], 'r') as f:
            team_config = json.load(f)

        # Get base archetype
        base_archetype_name = team_config.get('base_archetype')
        if not base_archetype_name:
            raise ValueError(
                f"Team config {team_files[0]} missing 'base_archetype' field"
            )

        base_archetype = self.get_base_archetype(
            base_archetype_name.lower().replace('-', '_').replace(' ', '_')
        )

        # Apply customizations if present
        customizations = team_config.get('customizations', {})
        if customizations:
            return base_archetype.apply_customizations(customizations)

        return base_archetype

    def get_all_team_archetypes(self) -> Dict[int, GMArchetype]:
        """
        Get archetypes for all 32 teams.

        Returns:
            Dict mapping team_id to GMArchetype
        """
        return {
            team_id: self.get_team_archetype(team_id)
            for team_id in range(1, 33)
        }

    def clear_cache(self):
        """Clear the team archetype cache"""
        self._team_archetypes.clear()

    def reload_team_archetype(self, team_id: int) -> GMArchetype:
        """
        Reload a team archetype from disk, bypassing cache.

        Args:
            team_id: Team ID (1-32)

        Returns:
            Freshly loaded GMArchetype instance
        """
        if team_id in self._team_archetypes:
            del self._team_archetypes[team_id]

        return self.get_team_archetype(team_id)
