"""
Database API for rivalry operations.

Part of Milestone 11: Schedule & Rivalries, Tollgate 1.
Handles CRUD operations for rivalries with dynasty isolation.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .connection import GameCycleDatabase
from ..models.rivalry import Rivalry, RivalryType, DIVISION_TEAMS, DIVISION_NAMES


class RivalryAPI:
    """
    API for rivalry database operations.

    Follows dynasty isolation pattern - all operations require dynasty_id.
    Provides methods for querying, creating, and managing rivalries.
    """

    def __init__(self, db: GameCycleDatabase):
        """
        Initialize with database connection.

        Args:
            db: GameCycleDatabase instance
        """
        self.db = db
        self._logger = logging.getLogger(__name__)

    # -------------------- Query Methods --------------------

    def get_rivalry(
        self,
        dynasty_id: str,
        rivalry_id: int
    ) -> Optional[Rivalry]:
        """
        Get a specific rivalry by ID.

        Args:
            dynasty_id: Dynasty identifier for isolation
            rivalry_id: Rivalry database ID

        Returns:
            Rivalry if found, None otherwise
        """
        row = self.db.query_one(
            """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                      rivalry_name, intensity, is_protected, created_at
               FROM rivalries
               WHERE dynasty_id = ? AND rivalry_id = ?""",
            (dynasty_id, rivalry_id)
        )
        return self._row_to_rivalry(row) if row else None

    def get_rivalry_between_teams(
        self,
        dynasty_id: str,
        team_id_1: int,
        team_id_2: int
    ) -> Optional[Rivalry]:
        """
        Get rivalry between two specific teams.

        Args:
            dynasty_id: Dynasty identifier
            team_id_1: First team ID (1-32)
            team_id_2: Second team ID (1-32)

        Returns:
            Rivalry if found, None otherwise
        """
        # Ensure consistent ordering for lookup
        team_a = min(team_id_1, team_id_2)
        team_b = max(team_id_1, team_id_2)

        row = self.db.query_one(
            """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                      rivalry_name, intensity, is_protected, created_at
               FROM rivalries
               WHERE dynasty_id = ? AND team_a_id = ? AND team_b_id = ?""",
            (dynasty_id, team_a, team_b)
        )
        return self._row_to_rivalry(row) if row else None

    def get_rivalries_for_team(
        self,
        dynasty_id: str,
        team_id: int,
        rivalry_type: Optional[RivalryType] = None
    ) -> List[Rivalry]:
        """
        Get all rivalries involving a specific team.

        Args:
            dynasty_id: Dynasty identifier
            team_id: Team ID (1-32)
            rivalry_type: Optional filter by rivalry type

        Returns:
            List of Rivalry objects sorted by intensity descending
        """
        if rivalry_type:
            rows = self.db.query_all(
                """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                          rivalry_name, intensity, is_protected, created_at
                   FROM rivalries
                   WHERE dynasty_id = ?
                     AND (team_a_id = ? OR team_b_id = ?)
                     AND rivalry_type = ?
                   ORDER BY intensity DESC""",
                (dynasty_id, team_id, team_id, rivalry_type.value)
            )
        else:
            rows = self.db.query_all(
                """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                          rivalry_name, intensity, is_protected, created_at
                   FROM rivalries
                   WHERE dynasty_id = ?
                     AND (team_a_id = ? OR team_b_id = ?)
                   ORDER BY intensity DESC""",
                (dynasty_id, team_id, team_id)
            )
        return [self._row_to_rivalry(row) for row in rows]

    def get_all_rivalries(
        self,
        dynasty_id: str,
        rivalry_type: Optional[RivalryType] = None
    ) -> List[Rivalry]:
        """
        Get all rivalries for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            rivalry_type: Optional filter by rivalry type

        Returns:
            List of Rivalry objects sorted by intensity descending
        """
        if rivalry_type:
            rows = self.db.query_all(
                """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                          rivalry_name, intensity, is_protected, created_at
                   FROM rivalries
                   WHERE dynasty_id = ? AND rivalry_type = ?
                   ORDER BY intensity DESC""",
                (dynasty_id, rivalry_type.value)
            )
        else:
            rows = self.db.query_all(
                """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                          rivalry_name, intensity, is_protected, created_at
                   FROM rivalries
                   WHERE dynasty_id = ?
                   ORDER BY intensity DESC""",
                (dynasty_id,)
            )
        return [self._row_to_rivalry(row) for row in rows]

    def get_protected_rivalries(
        self,
        dynasty_id: str
    ) -> List[Rivalry]:
        """
        Get all protected rivalries that must be scheduled annually.

        Args:
            dynasty_id: Dynasty identifier

        Returns:
            List of protected Rivalry objects
        """
        rows = self.db.query_all(
            """SELECT rivalry_id, team_a_id, team_b_id, rivalry_type,
                      rivalry_name, intensity, is_protected, created_at
               FROM rivalries
               WHERE dynasty_id = ? AND is_protected = 1
               ORDER BY intensity DESC""",
            (dynasty_id,)
        )
        return [self._row_to_rivalry(row) for row in rows]

    def get_rivalry_count(
        self,
        dynasty_id: str,
        rivalry_type: Optional[RivalryType] = None
    ) -> int:
        """
        Get count of rivalries for a dynasty.

        Args:
            dynasty_id: Dynasty identifier
            rivalry_type: Optional filter by type

        Returns:
            Number of rivalries
        """
        if rivalry_type:
            row = self.db.query_one(
                "SELECT COUNT(*) as count FROM rivalries WHERE dynasty_id = ? AND rivalry_type = ?",
                (dynasty_id, rivalry_type.value)
            )
        else:
            row = self.db.query_one(
                "SELECT COUNT(*) as count FROM rivalries WHERE dynasty_id = ?",
                (dynasty_id,)
            )
        return row['count'] if row else 0

    # -------------------- Update Methods --------------------

    def create_rivalry(
        self,
        dynasty_id: str,
        rivalry: Rivalry
    ) -> int:
        """
        Create a new rivalry.

        Args:
            dynasty_id: Dynasty identifier
            rivalry: Rivalry object to create

        Returns:
            ID of created rivalry

        Raises:
            ValueError: If rivalry already exists between teams
        """
        # Check if rivalry already exists
        existing = self.get_rivalry_between_teams(
            dynasty_id, rivalry.team_a_id, rivalry.team_b_id
        )
        if existing:
            raise ValueError(
                f"Rivalry already exists between teams {rivalry.team_a_id} and {rivalry.team_b_id}"
            )

        cursor = self.db.execute(
            """INSERT INTO rivalries
               (dynasty_id, team_a_id, team_b_id, rivalry_type, rivalry_name, intensity, is_protected)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                dynasty_id,
                rivalry.team_a_id,
                rivalry.team_b_id,
                rivalry.rivalry_type.value,
                rivalry.rivalry_name,
                rivalry.intensity,
                1 if rivalry.is_protected else 0,
            )
        )
        return cursor.lastrowid

    def create_rivalries_batch(
        self,
        dynasty_id: str,
        rivalries: List[Rivalry]
    ) -> int:
        """
        Create multiple rivalries in a single transaction.

        Uses INSERT OR IGNORE to skip duplicates.

        Args:
            dynasty_id: Dynasty identifier
            rivalries: List of Rivalry objects

        Returns:
            Number of rivalries created
        """
        if not rivalries:
            return 0

        params_list = [
            (
                dynasty_id,
                r.team_a_id,
                r.team_b_id,
                r.rivalry_type.value,
                r.rivalry_name,
                r.intensity,
                1 if r.is_protected else 0,
            )
            for r in rivalries
        ]

        self.db.executemany(
            """INSERT OR IGNORE INTO rivalries
               (dynasty_id, team_a_id, team_b_id, rivalry_type, rivalry_name, intensity, is_protected)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            params_list
        )
        return len(rivalries)

    def update_intensity(
        self,
        dynasty_id: str,
        rivalry_id: int,
        intensity: int
    ) -> bool:
        """
        Update rivalry intensity.

        Args:
            dynasty_id: Dynasty identifier
            rivalry_id: Rivalry database ID
            intensity: New intensity value (1-100)

        Returns:
            True if update succeeded

        Raises:
            ValueError: If intensity out of range
        """
        if not (1 <= intensity <= 100):
            raise ValueError(f"intensity must be 1-100, got {intensity}")

        cursor = self.db.execute(
            """UPDATE rivalries
               SET intensity = ?
               WHERE dynasty_id = ? AND rivalry_id = ?""",
            (intensity, dynasty_id, rivalry_id)
        )
        return cursor.rowcount > 0

    def update_protected_status(
        self,
        dynasty_id: str,
        rivalry_id: int,
        is_protected: bool
    ) -> bool:
        """
        Update whether rivalry is protected (annually scheduled).

        Args:
            dynasty_id: Dynasty identifier
            rivalry_id: Rivalry database ID
            is_protected: Whether rivalry should be protected

        Returns:
            True if update succeeded
        """
        cursor = self.db.execute(
            """UPDATE rivalries
               SET is_protected = ?
               WHERE dynasty_id = ? AND rivalry_id = ?""",
            (1 if is_protected else 0, dynasty_id, rivalry_id)
        )
        return cursor.rowcount > 0

    def delete_rivalry(
        self,
        dynasty_id: str,
        rivalry_id: int
    ) -> bool:
        """
        Delete a rivalry.

        Args:
            dynasty_id: Dynasty identifier
            rivalry_id: Rivalry database ID

        Returns:
            True if deletion succeeded
        """
        cursor = self.db.execute(
            "DELETE FROM rivalries WHERE dynasty_id = ? AND rivalry_id = ?",
            (dynasty_id, rivalry_id)
        )
        return cursor.rowcount > 0

    def clear_rivalries(
        self,
        dynasty_id: str,
        rivalry_type: Optional[RivalryType] = None
    ) -> int:
        """
        Clear all rivalries for a dynasty (optionally by type).

        Args:
            dynasty_id: Dynasty identifier
            rivalry_type: Optional filter - only clear this type

        Returns:
            Number of rivalries deleted
        """
        if rivalry_type:
            cursor = self.db.execute(
                "DELETE FROM rivalries WHERE dynasty_id = ? AND rivalry_type = ?",
                (dynasty_id, rivalry_type.value)
            )
        else:
            cursor = self.db.execute(
                "DELETE FROM rivalries WHERE dynasty_id = ?",
                (dynasty_id,)
            )
        return cursor.rowcount

    # -------------------- Initialization Methods --------------------

    def initialize_rivalries(
        self,
        dynasty_id: str,
        config_path: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Initialize all rivalries for a dynasty.

        Creates:
        1. Division rivalries (48 total - 6 per division x 8 divisions)
        2. Historic/Geographic rivalries from config file

        Args:
            dynasty_id: Dynasty identifier
            config_path: Optional path to rivalries.json config

        Returns:
            Dict with counts: {'division': N, 'historic': M, 'geographic': P}
        """
        counts = {'division': 0, 'historic': 0, 'geographic': 0}

        # 1. Create division rivalries
        division_rivalries = self._generate_division_rivalries()
        if division_rivalries:
            self.create_rivalries_batch(dynasty_id, division_rivalries)
            counts['division'] = len(division_rivalries)
            self._logger.info(f"Created {counts['division']} division rivalries")

        # 2. Load and create historic/geographic rivalries from config
        config_rivalries = self._load_rivalries_from_config(config_path)
        for rivalry in config_rivalries:
            try:
                self.create_rivalry(dynasty_id, rivalry)
                if rivalry.rivalry_type == RivalryType.HISTORIC:
                    counts['historic'] += 1
                elif rivalry.rivalry_type == RivalryType.GEOGRAPHIC:
                    counts['geographic'] += 1
            except ValueError:
                # Rivalry already exists (e.g., division rivalry covers same teams)
                # Update the existing rivalry to historic/geographic type if needed
                existing = self.get_rivalry_between_teams(
                    dynasty_id, rivalry.team_a_id, rivalry.team_b_id
                )
                if existing and existing.rivalry_type == RivalryType.DIVISION:
                    # Division rivalry exists, but config has historic/geographic
                    # Keep the division rivalry but update intensity if higher
                    if rivalry.intensity > existing.intensity:
                        self.update_intensity(dynasty_id, existing.rivalry_id, rivalry.intensity)
                    if rivalry.is_protected:
                        self.update_protected_status(dynasty_id, existing.rivalry_id, True)
                pass

        self._logger.info(
            f"Initialized rivalries: {counts['division']} division, "
            f"{counts['historic']} historic, {counts['geographic']} geographic"
        )
        return counts

    def _generate_division_rivalries(self) -> List[Rivalry]:
        """
        Generate all 48 division rivalries.

        Each division has 4 teams, creating 6 rivalries per division (4 choose 2).
        Total: 8 divisions x 6 = 48 division rivalries.

        Returns:
            List of Rivalry objects for all division rivalries
        """
        rivalries = []

        for div_id, team_ids in DIVISION_TEAMS.items():
            division_name = DIVISION_NAMES.get(div_id, f"Division {div_id}")

            # Generate all pairs within division
            for i, team_a in enumerate(team_ids):
                for team_b in team_ids[i + 1:]:
                    rivalry = Rivalry(
                        team_a_id=team_a,
                        team_b_id=team_b,
                        rivalry_type=RivalryType.DIVISION,
                        rivalry_name=f"{division_name} Division Rivalry",
                        intensity=70,  # Base intensity for division rivals
                        is_protected=False,  # Division games are already guaranteed
                    )
                    rivalries.append(rivalry)

        return rivalries

    def _load_rivalries_from_config(
        self,
        config_path: Optional[str] = None
    ) -> List[Rivalry]:
        """
        Load historic/geographic rivalries from JSON config.

        Args:
            config_path: Path to rivalries.json (uses default if None)

        Returns:
            List of Rivalry objects from config
        """
        if config_path is None:
            # Navigate from current file location to src/config/rivalries.json
            current_dir = Path(__file__).parent
            project_root = current_dir.parent.parent.parent
            config_path = project_root / "src" / "config" / "rivalries.json"

        if not Path(config_path).exists():
            self._logger.warning(f"Rivalries config not found: {config_path}")
            return []

        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            self._logger.error(f"Failed to load rivalries config: {e}")
            return []

        rivalries = []
        for entry in config.get('rivalries', []):
            try:
                # Determine is_protected based on intensity >= 85 if not explicitly set
                is_protected = entry.get('is_protected', entry.get('intensity', 50) >= 85)

                rivalry = Rivalry(
                    team_a_id=entry['team_a_id'],
                    team_b_id=entry['team_b_id'],
                    rivalry_type=RivalryType(entry['rivalry_type']),
                    rivalry_name=entry['rivalry_name'],
                    intensity=entry.get('intensity', 75),
                    is_protected=is_protected,
                )
                rivalries.append(rivalry)
            except (KeyError, ValueError) as e:
                self._logger.warning(f"Invalid rivalry config entry: {e}")
                continue

        return rivalries

    # -------------------- Private Methods --------------------

    def _row_to_rivalry(self, row) -> Rivalry:
        """Convert database row to Rivalry object."""
        return Rivalry(
            rivalry_id=row['rivalry_id'],
            team_a_id=row['team_a_id'],
            team_b_id=row['team_b_id'],
            rivalry_type=RivalryType(row['rivalry_type']),
            rivalry_name=row['rivalry_name'],
            intensity=row['intensity'],
            is_protected=bool(row['is_protected']),
            created_at=row['created_at'],
        )