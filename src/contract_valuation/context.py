"""
Context models for the Contract Valuation Engine.

Provides context objects that influence valuation:
- JobSecurityContext: GM job security pressure calculation
- ValuationContext: Market context (cap, rates, season)
- OwnerContext: Owner/situational context with constraints
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class JobSecurityContext:
    """
    GM job security context for pressure calculations.

    Calculates a security score from 0.0 (very secure) to 1.0 (hot seat).
    Higher scores lead to more desperate behavior (overpaying for talent).

    Attributes:
        tenure_years: Years with current team
        playoff_appearances: Playoff appearances during tenure
        recent_win_pct: Win percentage last 2 seasons (0.0-1.0)
        owner_patience: Owner patience level (0.0-1.0)
    """

    tenure_years: int
    playoff_appearances: int
    recent_win_pct: float
    owner_patience: float

    def __post_init__(self):
        """Validate all fields."""
        self._validate_tenure()
        self._validate_playoff_appearances()
        self._validate_win_pct()
        self._validate_patience()

    def _validate_tenure(self):
        """Validate tenure_years is non-negative."""
        if not isinstance(self.tenure_years, int) or self.tenure_years < 0:
            raise ValueError(f"tenure_years must be a non-negative integer, got {self.tenure_years}")

    def _validate_playoff_appearances(self):
        """Validate playoff_appearances is non-negative."""
        if not isinstance(self.playoff_appearances, int) or self.playoff_appearances < 0:
            raise ValueError(
                f"playoff_appearances must be a non-negative integer, got {self.playoff_appearances}"
            )

    def _validate_win_pct(self):
        """Validate recent_win_pct is between 0.0 and 1.0."""
        if not isinstance(self.recent_win_pct, (int, float)):
            raise ValueError(f"recent_win_pct must be a number, got {type(self.recent_win_pct)}")
        if not 0.0 <= self.recent_win_pct <= 1.0:
            raise ValueError(f"recent_win_pct must be 0.0-1.0, got {self.recent_win_pct}")

    def _validate_patience(self):
        """Validate owner_patience is between 0.0 and 1.0."""
        if not isinstance(self.owner_patience, (int, float)):
            raise ValueError(f"owner_patience must be a number, got {type(self.owner_patience)}")
        if not 0.0 <= self.owner_patience <= 1.0:
            raise ValueError(f"owner_patience must be 0.0-1.0, got {self.owner_patience}")

    def calculate_security_score(self) -> float:
        """
        Calculate job security score.

        Returns:
            Score from 0.0 (very secure) to 1.0 (hot seat).
            Higher score = more pressure = more likely to overpay.

        Factors:
        - New GMs have more pressure (need to prove themselves)
        - Low win rate increases pressure significantly
        - Playoff appearances reduce pressure
        - Patient owners reduce pressure
        """
        # Base pressure from tenure (new GMs have more pressure)
        if self.tenure_years <= 1:
            tenure_pressure = 0.6
        elif self.tenure_years <= 3:
            tenure_pressure = 0.4
        else:
            tenure_pressure = 0.2

        # Pressure from win rate (most significant factor)
        if self.recent_win_pct < 0.35:
            win_pressure = 0.8
        elif self.recent_win_pct < 0.50:
            win_pressure = 0.5
        else:
            win_pressure = 0.2

        # Playoff bonus reduces pressure
        playoff_bonus = min(0.3, self.playoff_appearances * 0.1)

        # Owner patience reduces pressure
        patience_reduction = self.owner_patience * 0.3

        # Combine factors
        raw_score = (tenure_pressure * 0.3) + (win_pressure * 0.7) - playoff_bonus - patience_reduction

        # Clamp to valid range
        return max(0.0, min(1.0, raw_score))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tenure_years": self.tenure_years,
            "playoff_appearances": self.playoff_appearances,
            "recent_win_pct": self.recent_win_pct,
            "owner_patience": self.owner_patience,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JobSecurityContext":
        """Create from dictionary."""
        return cls(
            tenure_years=data["tenure_years"],
            playoff_appearances=data["playoff_appearances"],
            recent_win_pct=data["recent_win_pct"],
            owner_patience=data["owner_patience"],
        )

    @classmethod
    def create_secure(cls) -> "JobSecurityContext":
        """Factory for a secure GM (low pressure)."""
        return cls(
            tenure_years=5,
            playoff_appearances=2,
            recent_win_pct=0.65,
            owner_patience=0.8,
        )

    @classmethod
    def create_hot_seat(cls) -> "JobSecurityContext":
        """Factory for a GM on the hot seat (high pressure)."""
        return cls(
            tenure_years=3,
            playoff_appearances=0,
            recent_win_pct=0.35,
            owner_patience=0.3,
        )

    @classmethod
    def create_new_hire(cls) -> "JobSecurityContext":
        """Factory for a newly hired GM (moderate pressure)."""
        return cls(
            tenure_years=0,
            playoff_appearances=0,
            recent_win_pct=0.50,
            owner_patience=0.7,
        )


@dataclass
class ValuationContext:
    """
    Market context for valuation.

    Provides salary cap, season info, and position market rates
    that factors use to calculate appropriate AAV values.

    Attributes:
        salary_cap: Current year salary cap in dollars
        season: Current season year
        position_market_rates: Position -> tier -> AAV mapping
    """

    salary_cap: int
    season: int
    position_market_rates: Dict[str, Dict[str, int]] = field(default_factory=dict)

    def __post_init__(self):
        """Validate all fields."""
        self._validate_salary_cap()
        self._validate_season()
        self._validate_market_rates()

    def _validate_salary_cap(self):
        """Validate salary_cap is a positive integer."""
        if not isinstance(self.salary_cap, int) or self.salary_cap <= 0:
            raise ValueError(f"salary_cap must be a positive integer, got {self.salary_cap}")

    def _validate_season(self):
        """Validate season is a valid year (2020+)."""
        if not isinstance(self.season, int) or self.season < 2020:
            raise ValueError(f"season must be a valid year (2020+), got {self.season}")

    def _validate_market_rates(self):
        """Validate position_market_rates is a dictionary."""
        if not isinstance(self.position_market_rates, dict):
            raise ValueError("position_market_rates must be a dictionary")

    def get_market_rate(self, position: str, tier: str = "starter") -> Optional[int]:
        """
        Get market rate for a position and tier.

        Args:
            position: Player position (e.g., "QB", "WR")
            tier: Contract tier ("backup", "starter", "quality", "elite")

        Returns:
            Market AAV in dollars, or None if not found
        """
        pos_rates = self.position_market_rates.get(position.upper(), {})
        return pos_rates.get(tier)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "salary_cap": self.salary_cap,
            "season": self.season,
            "position_market_rates": {
                pos: tiers.copy() for pos, tiers in self.position_market_rates.items()
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValuationContext":
        """Create from dictionary."""
        return cls(
            salary_cap=data["salary_cap"],
            season=data["season"],
            position_market_rates=data.get("position_market_rates", {}),
        )

    @classmethod
    def create_default_2025(cls) -> "ValuationContext":
        """Factory for 2025 market context with default rates."""
        return cls(
            salary_cap=255_000_000,
            season=2025,
            position_market_rates={
                "QB": {
                    "backup": 3_000_000,
                    "starter": 15_000_000,
                    "quality": 35_000_000,
                    "elite": 50_000_000,
                },
                "RB": {
                    "backup": 1_000_000,
                    "starter": 4_000_000,
                    "quality": 8_000_000,
                    "elite": 14_000_000,
                },
                "WR": {
                    "backup": 2_000_000,
                    "starter": 8_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "TE": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 18_000_000,
                },
                "OT": {
                    "backup": 2_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 25_000_000,
                },
                "LT": {
                    "backup": 2_500_000,
                    "starter": 12_000_000,
                    "quality": 20_000_000,
                    "elite": 27_000_000,
                },
                "RT": {
                    "backup": 2_000_000,
                    "starter": 9_000_000,
                    "quality": 16_000_000,
                    "elite": 23_000_000,
                },
                "OG": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 18_000_000,
                },
                "LG": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 18_000_000,
                },
                "RG": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 18_000_000,
                },
                "C": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 16_000_000,
                },
                "FB": {
                    "backup": 1_000_000,
                    "starter": 2_000_000,
                    "quality": 3_500_000,
                    "elite": 5_000_000,
                },
                "EDGE": {
                    "backup": 3_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "LE": {
                    "backup": 3_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "RE": {
                    "backup": 3_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "DT": {
                    "backup": 2_000_000,
                    "starter": 8_000_000,
                    "quality": 14_000_000,
                    "elite": 22_000_000,
                },
                "LB": {
                    "backup": 2_000_000,
                    "starter": 8_000_000,
                    "quality": 14_000_000,
                    "elite": 20_000_000,
                },
                "MLB": {
                    "backup": 2_000_000,
                    "starter": 8_000_000,
                    "quality": 14_000_000,
                    "elite": 20_000_000,
                },
                "LOLB": {
                    "backup": 3_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "ROLB": {
                    "backup": 3_000_000,
                    "starter": 10_000_000,
                    "quality": 18_000_000,
                    "elite": 28_000_000,
                },
                "CB": {
                    "backup": 2_000_000,
                    "starter": 8_000_000,
                    "quality": 15_000_000,
                    "elite": 22_000_000,
                },
                "S": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 16_000_000,
                },
                "FS": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 16_000_000,
                },
                "SS": {
                    "backup": 1_500_000,
                    "starter": 6_000_000,
                    "quality": 12_000_000,
                    "elite": 16_000_000,
                },
                "K": {
                    "backup": 1_000_000,
                    "starter": 3_000_000,
                    "quality": 5_000_000,
                    "elite": 7_000_000,
                },
                "P": {
                    "backup": 1_000_000,
                    "starter": 2_500_000,
                    "quality": 4_000_000,
                    "elite": 5_500_000,
                },
            },
        )


@dataclass
class OwnerContext:
    """
    Owner/situational context for pressure modifiers.

    Combines job security, owner philosophy, and contract constraints
    to modify valuation based on team situation.

    Attributes:
        dynasty_id: Dynasty identifier for isolation
        team_id: Team identifier (1-32)
        job_security: GM's job security context
        owner_philosophy: Owner spending philosophy ("aggressive", "balanced", "conservative")
        team_philosophy: Team building philosophy ("win_now", "maintain", "rebuild")
        win_now_mode: Whether team is in championship window
        max_contract_years: Owner's max contract length constraint (1-7)
        max_guaranteed_pct: Owner's max guaranteed percentage constraint (0.0-1.0)
    """

    dynasty_id: str
    team_id: int
    job_security: JobSecurityContext
    owner_philosophy: str
    team_philosophy: str
    win_now_mode: bool
    max_contract_years: int
    max_guaranteed_pct: float

    def __post_init__(self):
        """Validate all fields."""
        self._validate_team_id()
        self._validate_owner_philosophy()
        self._validate_team_philosophy()
        self._validate_contract_constraints()

    def _validate_team_id(self):
        """Validate team_id is between 1 and 32."""
        if not isinstance(self.team_id, int) or not 1 <= self.team_id <= 32:
            raise ValueError(f"team_id must be 1-32, got {self.team_id}")

    def _validate_owner_philosophy(self):
        """Validate owner_philosophy is a valid value."""
        valid = {"aggressive", "balanced", "conservative"}
        if self.owner_philosophy not in valid:
            raise ValueError(f"owner_philosophy must be one of {valid}, got {self.owner_philosophy}")

    def _validate_team_philosophy(self):
        """Validate team_philosophy is a valid value."""
        valid = {"win_now", "maintain", "rebuild"}
        if self.team_philosophy not in valid:
            raise ValueError(f"team_philosophy must be one of {valid}, got {self.team_philosophy}")

    def _validate_contract_constraints(self):
        """Validate contract constraint fields."""
        if not isinstance(self.max_contract_years, int) or not 1 <= self.max_contract_years <= 7:
            raise ValueError(f"max_contract_years must be 1-7, got {self.max_contract_years}")
        if not isinstance(self.max_guaranteed_pct, (int, float)):
            raise ValueError(
                f"max_guaranteed_pct must be a number, got {type(self.max_guaranteed_pct)}"
            )
        if not 0.0 <= self.max_guaranteed_pct <= 1.0:
            raise ValueError(f"max_guaranteed_pct must be 0.0-1.0, got {self.max_guaranteed_pct}")

    def get_budget_multiplier(self) -> float:
        """
        Get spending multiplier based on owner philosophy.

        Returns:
            Multiplier to apply to base valuation:
            - Aggressive: 1.15x (willing to overpay)
            - Balanced: 1.00x (market rate)
            - Conservative: 0.90x (value-focused)
        """
        multipliers = {
            "aggressive": 1.15,
            "balanced": 1.00,
            "conservative": 0.90,
        }
        return multipliers.get(self.owner_philosophy, 1.00)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "dynasty_id": self.dynasty_id,
            "team_id": self.team_id,
            "job_security": self.job_security.to_dict(),
            "owner_philosophy": self.owner_philosophy,
            "team_philosophy": self.team_philosophy,
            "win_now_mode": self.win_now_mode,
            "max_contract_years": self.max_contract_years,
            "max_guaranteed_pct": self.max_guaranteed_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OwnerContext":
        """Create from dictionary."""
        return cls(
            dynasty_id=data["dynasty_id"],
            team_id=data["team_id"],
            job_security=JobSecurityContext.from_dict(data["job_security"]),
            owner_philosophy=data["owner_philosophy"],
            team_philosophy=data["team_philosophy"],
            win_now_mode=data["win_now_mode"],
            max_contract_years=data["max_contract_years"],
            max_guaranteed_pct=data["max_guaranteed_pct"],
        )

    @classmethod
    def from_owner_directives(
        cls,
        directives: Any,
        job_security: JobSecurityContext
    ) -> "OwnerContext":
        """
        Create from OwnerDirectives model.

        Args:
            directives: OwnerDirectives instance from game_cycle.models
            job_security: JobSecurityContext for this GM

        Returns:
            OwnerContext configured from directives
        """
        return cls(
            dynasty_id=directives.dynasty_id,
            team_id=directives.team_id,
            job_security=job_security,
            owner_philosophy=directives.budget_stance,
            team_philosophy=directives.team_philosophy,
            win_now_mode=directives.team_philosophy == "win_now",
            max_contract_years=directives.max_contract_years,
            max_guaranteed_pct=directives.max_guaranteed_percent,
        )

    @classmethod
    def create_default(
        cls,
        dynasty_id: str,
        team_id: int
    ) -> "OwnerContext":
        """Factory for default balanced context."""
        return cls(
            dynasty_id=dynasty_id,
            team_id=team_id,
            job_security=JobSecurityContext.create_secure(),
            owner_philosophy="balanced",
            team_philosophy="maintain",
            win_now_mode=False,
            max_contract_years=5,
            max_guaranteed_pct=0.75,  # Increased to allow NFL-realistic guarantees
        )