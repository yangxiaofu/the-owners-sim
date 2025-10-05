"""Central registry for player archetypes."""

from typing import Dict, List, Optional
import json
from pathlib import Path
from .base_archetype import PlayerArchetype, Position, AttributeRange
import random


class ArchetypeRegistry:
    """Central registry for player archetypes."""

    def __init__(self, config_dir: str = "src/config/archetypes/"):
        """Initialize registry and load archetypes.

        Args:
            config_dir: Directory containing archetype JSON files
        """
        self.config_dir = Path(config_dir)
        self.archetypes: Dict[str, PlayerArchetype] = {}
        self._load_archetypes()

    def _load_archetypes(self):
        """Load all archetype definitions from JSON files."""
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            return

        for json_file in self.config_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    # Handle both single archetype and list of archetypes
                    if isinstance(data, list):
                        for archetype_data in data:
                            self._load_single_archetype(archetype_data)
                    else:
                        self._load_single_archetype(data)
            except Exception as e:
                print(f"Error loading archetype file {json_file}: {e}")

    def _load_single_archetype(self, data: Dict):
        """Load a single archetype from data.

        Args:
            data: Archetype data dictionary
        """
        try:
            archetype = self._dict_to_archetype(data)
            is_valid, error = archetype.validate()
            if is_valid:
                self.archetypes[archetype.archetype_id] = archetype
            else:
                print(f"Invalid archetype {archetype.archetype_id}: {error}")
        except Exception as e:
            print(f"Error parsing archetype: {e}")

    def _dict_to_archetype(self, data: Dict) -> PlayerArchetype:
        """Convert JSON dict to PlayerArchetype object.

        Args:
            data: Archetype data dictionary

        Returns:
            PlayerArchetype object
        """
        # Convert attribute dicts to AttributeRange objects
        def parse_attrs(attrs_dict):
            return {
                name: AttributeRange(**range_data)
                for name, range_data in attrs_dict.items()
            }

        return PlayerArchetype(
            archetype_id=data["archetype_id"],
            position=Position[data["position"]],
            name=data["name"],
            description=data["description"],
            physical_attributes=parse_attrs(data["physical_attributes"]),
            mental_attributes=parse_attrs(data["mental_attributes"]),
            position_attributes=parse_attrs(data["position_attributes"]),
            overall_range=AttributeRange(**data["overall_range"]),
            frequency=data["frequency"],
            peak_age_range=tuple(data["peak_age_range"]),
            development_curve=data["development_curve"]
        )

    def get_archetype(self, archetype_id: str) -> Optional[PlayerArchetype]:
        """Get archetype by ID.

        Args:
            archetype_id: Unique archetype identifier

        Returns:
            PlayerArchetype if found, None otherwise
        """
        return self.archetypes.get(archetype_id)

    def get_archetypes_by_position(self, position: str) -> List[PlayerArchetype]:
        """Get all archetypes for a position.

        Args:
            position: Position name (e.g., "QB", "RB")

        Returns:
            List of archetypes for the position
        """
        try:
            pos_enum = Position[position]
            return [a for a in self.archetypes.values() if a.position == pos_enum]
        except KeyError:
            return []

    def select_random_archetype(self, position: str) -> Optional[PlayerArchetype]:
        """Select random archetype for position weighted by frequency.

        Args:
            position: Position name

        Returns:
            Random archetype or None if no archetypes available
        """
        archetypes = self.get_archetypes_by_position(position)
        if not archetypes:
            return None

        # Weight by frequency
        weights = [a.frequency for a in archetypes]
        return random.choices(archetypes, weights=weights)[0]

    def list_all_archetypes(self) -> List[str]:
        """Get list of all archetype IDs.

        Returns:
            List of archetype ID strings
        """
        return list(self.archetypes.keys())

    def get_archetype_count(self) -> int:
        """Get total number of registered archetypes.

        Returns:
            Count of loaded archetypes
        """
        return len(self.archetypes)

    def get_positions(self) -> List[str]:
        """Get list of all positions with archetypes.

        Returns:
            List of position names
        """
        positions = set(a.position.value for a in self.archetypes.values())
        return sorted(list(positions))