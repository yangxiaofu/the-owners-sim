"""
Rivalry data models for the schedule and rivalries system.

Part of Milestone 11: Schedule & Rivalries, Tollgate 1.
Defines rivalry types, intensity levels, and core dataclasses
for tracking team rivalries and protected matchups.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


class RivalryType(Enum):
    """
    Types of rivalries between NFL teams.

    Attributes:
        DIVISION: Same-division rivals (auto-generated, 48 total)
        HISTORIC: Classic rivalries with long history (Bears-Packers)
        GEOGRAPHIC: Teams in same city/region (Jets-Giants)
        RECENT: Rivalries formed through recent playoff matchups
    """
    DIVISION = "division"
    HISTORIC = "historic"
    GEOGRAPHIC = "geographic"
    RECENT = "recent"


@dataclass
class Rivalry:
    """
    Represents a rivalry between two NFL teams.

    Enforces team_a_id < team_b_id for consistent lookup ordering.
    Protected rivalries are guaranteed to be scheduled annually.

    Attributes:
        team_a_id: Lower team ID (1-32), enforced by validation
        team_b_id: Higher team ID (1-32)
        rivalry_type: Type of rivalry (DIVISION, HISTORIC, etc.)
        rivalry_name: Human-readable name (e.g., "The Oldest Rivalry")
        intensity: Rivalry intensity score (1-100), affects gameplay modifiers
        is_protected: If True, matchup should be scheduled every year
        rivalry_id: Optional database ID (None for new rivalries)
        created_at: Timestamp when rivalry was created
    """
    team_a_id: int
    team_b_id: int
    rivalry_type: RivalryType
    rivalry_name: str
    intensity: int = 50
    is_protected: bool = False
    rivalry_id: Optional[int] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        """Validate rivalry data after initialization."""
        self._validate_team_ids()
        self._validate_intensity()
        self._validate_rivalry_name()
        self._validate_rivalry_type()

    def _validate_team_ids(self):
        """Ensure team IDs are valid and properly ordered."""
        if not isinstance(self.team_a_id, int) or not isinstance(self.team_b_id, int):
            raise ValueError("team_a_id and team_b_id must be integers")

        if not (1 <= self.team_a_id <= 32):
            raise ValueError(f"team_a_id must be 1-32, got {self.team_a_id}")
        if not (1 <= self.team_b_id <= 32):
            raise ValueError(f"team_b_id must be 1-32, got {self.team_b_id}")
        if self.team_a_id == self.team_b_id:
            raise ValueError("team_a_id and team_b_id must be different")

        # Auto-swap to enforce team_a_id < team_b_id ordering
        if self.team_a_id > self.team_b_id:
            self.team_a_id, self.team_b_id = self.team_b_id, self.team_a_id

    def _validate_intensity(self):
        """Ensure intensity is in valid range."""
        if not isinstance(self.intensity, int):
            raise ValueError(f"intensity must be an integer, got {type(self.intensity)}")
        if not (1 <= self.intensity <= 100):
            raise ValueError(f"intensity must be 1-100, got {self.intensity}")

    def _validate_rivalry_name(self):
        """Ensure rivalry name is not empty."""
        if not self.rivalry_name or not str(self.rivalry_name).strip():
            raise ValueError("rivalry_name cannot be empty")

    def _validate_rivalry_type(self):
        """Ensure rivalry type is valid enum."""
        if not isinstance(self.rivalry_type, RivalryType):
            raise ValueError(
                f"rivalry_type must be RivalryType enum, got {type(self.rivalry_type)}"
            )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> 'Rivalry':
        """
        Create Rivalry from database row dict.

        Args:
            row: Database row as dict (sqlite3.Row or dict)

        Returns:
            Rivalry instance
        """
        return cls(
            rivalry_id=row.get('rivalry_id'),
            team_a_id=row['team_a_id'],
            team_b_id=row['team_b_id'],
            rivalry_type=RivalryType(row['rivalry_type']),
            rivalry_name=row['rivalry_name'],
            intensity=row['intensity'],
            is_protected=bool(row.get('is_protected', 0)),
            created_at=row.get('created_at'),
        )

    def to_db_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for database insertion.

        Returns:
            Dict with database column names and values
        """
        return {
            'team_a_id': self.team_a_id,
            'team_b_id': self.team_b_id,
            'rivalry_type': self.rivalry_type.value,
            'rivalry_name': self.rivalry_name,
            'intensity': self.intensity,
            'is_protected': 1 if self.is_protected else 0,
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dict for serialization/logging.

        Returns:
            Dict with all rivalry data
        """
        return {
            'rivalry_id': self.rivalry_id,
            'team_a_id': self.team_a_id,
            'team_b_id': self.team_b_id,
            'rivalry_type': self.rivalry_type.value,
            'rivalry_name': self.rivalry_name,
            'intensity': self.intensity,
            'is_protected': self.is_protected,
            'created_at': self.created_at,
        }

    @property
    def display_name(self) -> str:
        """Human-readable rivalry display name."""
        return self.rivalry_name

    @property
    def intensity_level(self) -> str:
        """
        Human-readable intensity level.

        Returns:
            String description of intensity level
        """
        if self.intensity >= 90:
            return "Legendary"
        elif self.intensity >= 75:
            return "Intense"
        elif self.intensity >= 50:
            return "Competitive"
        elif self.intensity >= 25:
            return "Developing"
        else:
            return "Mild"

    def __str__(self) -> str:
        """String representation for logging/display."""
        return (
            f"{self.rivalry_name} "
            f"(Team {self.team_a_id} vs Team {self.team_b_id}, "
            f"{self.rivalry_type.value}, intensity: {self.intensity})"
        )

    def involves_team(self, team_id: int) -> bool:
        """
        Check if rivalry involves a specific team.

        Args:
            team_id: Team ID to check (1-32)

        Returns:
            True if team is part of this rivalry
        """
        return team_id == self.team_a_id or team_id == self.team_b_id

    def get_opponent(self, team_id: int) -> Optional[int]:
        """
        Get the opponent team ID for a given team in this rivalry.

        Args:
            team_id: Team ID to find opponent for

        Returns:
            Opponent team ID, or None if team not in rivalry
        """
        if team_id == self.team_a_id:
            return self.team_b_id
        elif team_id == self.team_b_id:
            return self.team_a_id
        return None


# Division mappings for generating division rivalries
# Division ID -> List of team IDs in that division
DIVISION_TEAMS: Dict[int, list] = {
    1: [1, 2, 3, 4],       # AFC East: Bills, Dolphins, Patriots, Jets
    2: [5, 6, 7, 8],       # AFC North: Ravens, Bengals, Browns, Steelers
    3: [9, 10, 11, 12],    # AFC South: Texans, Colts, Jaguars, Titans
    4: [13, 14, 15, 16],   # AFC West: Broncos, Chiefs, Raiders, Chargers
    5: [17, 18, 19, 20],   # NFC East: Cowboys, Giants, Eagles, Commanders
    6: [21, 22, 23, 24],   # NFC North: Bears, Lions, Packers, Vikings
    7: [25, 26, 27, 28],   # NFC South: Falcons, Panthers, Saints, Buccaneers
    8: [29, 30, 31, 32],   # NFC West: Cardinals, Rams, 49ers, Seahawks
}

# Division names for rivalry naming
DIVISION_NAMES: Dict[int, str] = {
    1: "AFC East",
    2: "AFC North",
    3: "AFC South",
    4: "AFC West",
    5: "NFC East",
    6: "NFC North",
    7: "NFC South",
    8: "NFC West",
}