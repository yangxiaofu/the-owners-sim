"""
Game slot models for primetime scheduling (Milestone 11, Tollgate 4).

Defines NFL broadcast time slots and primetime game assignments.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class GameSlot(Enum):
    """NFL broadcast time slots."""

    # Regular weekly slots
    THURSDAY_NIGHT = "TNF"      # 8:20pm ET - Amazon Prime
    SUNDAY_EARLY = "SUN_EARLY"  # 1:00pm ET - CBS/FOX
    SUNDAY_LATE = "SUN_LATE"    # 4:05pm/4:25pm ET - CBS/FOX
    SUNDAY_NIGHT = "SNF"        # 8:20pm ET - NBC
    MONDAY_NIGHT = "MNF"        # 8:15pm ET - ESPN/ABC

    # Special slots
    THANKSGIVING_EARLY = "TG_EARLY"    # 12:30pm ET - Lions host
    THANKSGIVING_LATE = "TG_LATE"      # 4:30pm ET - Cowboys host
    THANKSGIVING_NIGHT = "TG_NIGHT"    # 8:20pm ET - Prime matchup
    CHRISTMAS = "XMAS"                 # Christmas Day games
    INTERNATIONAL = "INTL"             # London/Germany/Mexico
    KICKOFF = "KICKOFF"                # Week 1 Thursday - Defending champ hosts

    @property
    def is_primetime(self) -> bool:
        """Return True if this is a primetime slot."""
        return self in (
            GameSlot.THURSDAY_NIGHT,
            GameSlot.SUNDAY_NIGHT,
            GameSlot.MONDAY_NIGHT,
            GameSlot.THANKSGIVING_EARLY,
            GameSlot.THANKSGIVING_LATE,
            GameSlot.THANKSGIVING_NIGHT,
            GameSlot.CHRISTMAS,
            GameSlot.KICKOFF,
        )

    @property
    def broadcast_network(self) -> str:
        """Return the typical broadcast network for this slot."""
        networks = {
            GameSlot.THURSDAY_NIGHT: "Amazon Prime",
            GameSlot.SUNDAY_EARLY: "CBS/FOX",
            GameSlot.SUNDAY_LATE: "CBS/FOX",
            GameSlot.SUNDAY_NIGHT: "NBC",
            GameSlot.MONDAY_NIGHT: "ESPN",
            GameSlot.THANKSGIVING_EARLY: "CBS",
            GameSlot.THANKSGIVING_LATE: "FOX",
            GameSlot.THANKSGIVING_NIGHT: "NBC",
            GameSlot.CHRISTMAS: "Netflix/NFL Network",
            GameSlot.INTERNATIONAL: "NFL Network",
            GameSlot.KICKOFF: "NBC",
        }
        return networks.get(self, "NFL Network")


@dataclass
class PrimetimeAssignment:
    """Primetime game assignment."""

    game_id: str
    week: int
    slot: GameSlot
    home_team_id: int
    away_team_id: int
    appeal_score: int  # 0-100 matchup appeal score
    broadcast_network: str
    is_flex_eligible: bool  # Can be flexed in/out weeks 12-17
    flexed_from: Optional[GameSlot] = None  # Original slot if flexed

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "game_id": self.game_id,
            "week": self.week,
            "slot": self.slot.value,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "appeal_score": self.appeal_score,
            "broadcast_network": self.broadcast_network,
            "is_flex_eligible": self.is_flex_eligible,
            "flexed_from": self.flexed_from.value if self.flexed_from else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PrimetimeAssignment":
        """Create from dictionary."""
        return cls(
            game_id=data["game_id"],
            week=data["week"],
            slot=GameSlot(data["slot"]),
            home_team_id=data["home_team_id"],
            away_team_id=data["away_team_id"],
            appeal_score=data["appeal_score"],
            broadcast_network=data["broadcast_network"],
            is_flex_eligible=data["is_flex_eligible"],
            flexed_from=GameSlot(data["flexed_from"]) if data.get("flexed_from") else None,
        )


# Team market sizes (1-32 ranking, 1 = largest market)
# Based on NFL team market valuations and TV market sizes
TEAM_MARKET_SIZE = {
    # Large markets (1-10)
    17: 1,   # Cowboys - largest market
    18: 2,   # Giants - NYC
    4: 3,    # Jets - NYC
    19: 4,   # Eagles - Philadelphia
    31: 5,   # 49ers - San Francisco Bay
    30: 6,   # Rams - LA
    16: 7,   # Chargers - LA
    21: 8,   # Bears - Chicago
    3: 9,    # Patriots - Boston
    20: 10,  # Commanders - DC

    # Medium-large markets (11-20)
    2: 11,   # Dolphins - Miami
    9: 12,   # Texans - Houston
    25: 13,  # Falcons - Atlanta
    29: 14,  # Cardinals - Phoenix
    32: 15,  # Seahawks - Seattle
    22: 16,  # Lions - Detroit
    24: 17,  # Vikings - Minneapolis
    13: 18,  # Broncos - Denver
    14: 19,  # Chiefs - Kansas City
    28: 20,  # Buccaneers - Tampa

    # Smaller markets (21-32)
    5: 21,   # Ravens - Baltimore
    6: 22,   # Bengals - Cincinnati
    8: 23,   # Steelers - Pittsburgh
    27: 24,  # Saints - New Orleans
    10: 25,  # Colts - Indianapolis
    7: 26,   # Browns - Cleveland
    23: 27,  # Packers - Green Bay (small but huge fanbase)
    12: 28,  # Titans - Nashville
    26: 29,  # Panthers - Charlotte
    1: 30,   # Bills - Buffalo
    15: 31,  # Raiders - Las Vegas
    11: 32,  # Jaguars - Jacksonville
}


def get_market_score(team_id: int) -> int:
    """
    Get market score for a team (0-20 scale, higher = larger market).

    Args:
        team_id: Team ID (1-32)

    Returns:
        Score from 0-20 based on market size ranking
    """
    ranking = TEAM_MARKET_SIZE.get(team_id, 16)  # Default to middle
    # Convert ranking (1-32) to score (20-0)
    return max(0, 20 - int((ranking - 1) * 20 / 31))
