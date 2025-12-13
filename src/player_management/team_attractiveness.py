"""Team attractiveness factors for player decision-making."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class TeamAttractiveness:
    """Team attractiveness factors for player decision-making.

    Combines static factors (market size, taxes, weather) with dynamic factors
    (playoff history, winning culture) to influence player preferences.
    """

    # Required
    team_id: int

    # Static factors (from config - loaded externally)
    market_size: int = 50  # 1-100 (NYC=95, Green Bay=25)
    state_income_tax_rate: float = 0.05  # 0.0-0.13 (Texas=0, California=0.13)
    weather_score: int = 50  # 1-100 (Miami=85, Green Bay=30)
    state: Optional[str] = None  # Two-letter state code

    # Dynamic factors (computed each season)
    playoff_appearances_5yr: int = 0  # 0-5
    super_bowl_wins_5yr: int = 0  # 0-5
    winning_culture_score: int = 50  # 0-100 computed from 5-year record
    coaching_prestige: int = 50  # 0-100 based on coach tenure/success
    current_season_wins: int = 0
    current_season_losses: int = 0

    def __post_init__(self):
        """Validate all fields after initialization."""
        self._validate()

    def _validate(self):
        """Ensure all values are within acceptable ranges."""
        # Team ID must be 1-32
        if not 1 <= self.team_id <= 32:
            raise ValueError(f"team_id must be 1-32, got {self.team_id}")

        # Score validations (1-100)
        if not 1 <= self.market_size <= 100:
            raise ValueError(f"market_size must be 1-100, got {self.market_size}")
        if not 1 <= self.weather_score <= 100:
            raise ValueError(f"weather_score must be 1-100, got {self.weather_score}")
        if not 0 <= self.winning_culture_score <= 100:
            raise ValueError(
                f"winning_culture_score must be 0-100, got {self.winning_culture_score}"
            )
        if not 0 <= self.coaching_prestige <= 100:
            raise ValueError(
                f"coaching_prestige must be 0-100, got {self.coaching_prestige}"
            )

        # Tax rate validation (max is ~13.3% in California)
        if not 0.0 <= self.state_income_tax_rate <= 0.15:
            raise ValueError(
                f"state_income_tax_rate must be 0.0-0.15, got {self.state_income_tax_rate}"
            )

        # 5-year history validations
        if not 0 <= self.playoff_appearances_5yr <= 5:
            raise ValueError(
                f"playoff_appearances_5yr must be 0-5, got {self.playoff_appearances_5yr}"
            )
        if not 0 <= self.super_bowl_wins_5yr <= 5:
            raise ValueError(
                f"super_bowl_wins_5yr must be 0-5, got {self.super_bowl_wins_5yr}"
            )

        # Season record validations
        if self.current_season_wins < 0:
            raise ValueError("current_season_wins cannot be negative")
        if self.current_season_losses < 0:
            raise ValueError("current_season_losses cannot be negative")

    @property
    def contender_score(self) -> int:
        """Calculate 0-100 score for how much of a contender this team is.

        Weights:
        - Current record (40%)
        - Playoff appearances (30%)
        - Super Bowls (20%)
        - Winning culture (10%)
        """
        total_games = self.current_season_wins + self.current_season_losses
        if total_games > 0:
            win_pct = self.current_season_wins / total_games
            current_record_score = win_pct * 100
        else:
            current_record_score = 50  # Default mid-range if no games played

        playoff_score = (self.playoff_appearances_5yr / 5) * 100
        super_bowl_score = (self.super_bowl_wins_5yr / 5) * 100

        weighted_score = (
            current_record_score * 0.40
            + playoff_score * 0.30
            + super_bowl_score * 0.20
            + self.winning_culture_score * 0.10
        )

        return int(min(100, max(0, weighted_score)))

    @property
    def tax_advantage_score(self) -> int:
        """Calculate 0-100 score for tax advantage (higher = better).

        No-tax states (0%) get 100, max tax (13%) gets 0.
        """
        # Normalize: 0% = 100, 13% = 0
        return int(
            max(0, min(100, (0.13 - self.state_income_tax_rate) / 0.13 * 100))
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "team_id": self.team_id,
            "market_size": self.market_size,
            "state_income_tax_rate": self.state_income_tax_rate,
            "weather_score": self.weather_score,
            "state": self.state,
            "playoff_appearances_5yr": self.playoff_appearances_5yr,
            "super_bowl_wins_5yr": self.super_bowl_wins_5yr,
            "winning_culture_score": self.winning_culture_score,
            "coaching_prestige": self.coaching_prestige,
            "current_season_wins": self.current_season_wins,
            "current_season_losses": self.current_season_losses,
            # Include computed properties
            "contender_score": self.contender_score,
            "tax_advantage_score": self.tax_advantage_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TeamAttractiveness":
        """Create TeamAttractiveness from dictionary."""
        return cls(
            team_id=data["team_id"],
            market_size=data.get("market_size", 50),
            state_income_tax_rate=data.get("state_income_tax_rate", 0.05),
            weather_score=data.get("weather_score", 50),
            state=data.get("state"),
            playoff_appearances_5yr=data.get("playoff_appearances_5yr", 0),
            super_bowl_wins_5yr=data.get("super_bowl_wins_5yr", 0),
            winning_culture_score=data.get("winning_culture_score", 50),
            coaching_prestige=data.get("coaching_prestige", 50),
            current_season_wins=data.get("current_season_wins", 0),
            current_season_losses=data.get("current_season_losses", 0),
        )

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "TeamAttractiveness":
        """Create from database row."""
        if hasattr(row, "keys"):
            row = dict(row)
        return cls.from_dict(row)