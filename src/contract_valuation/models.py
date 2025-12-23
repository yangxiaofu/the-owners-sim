"""
Core data models for the Contract Valuation Engine.

Provides dataclasses for:
- FactorResult: Result from a single valuation factor
- FactorWeights: How factors are weighted in the final valuation
- ContractOffer: Generated contract offer with financial details
- ValuationResult: Complete valuation with full audit trail
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class FactorResult:
    """
    Result from a single valuation factor.

    Each factor (stats, scouting, market, rating) produces an independent
    AAV estimate. These are combined using GM-determined weights.

    Attributes:
        name: Factor identifier (e.g., "stats_based", "scouting")
        raw_value: Unweighted AAV estimate in dollars
        confidence: 0.0-1.0 reliability score for this estimate
        breakdown: Detailed calculation steps for audit trail
    """

    name: str
    raw_value: int
    confidence: float
    breakdown: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate all fields."""
        self._validate_name()
        self._validate_raw_value()
        self._validate_confidence()
        self._validate_breakdown()

    def _validate_name(self):
        """Validate name is a non-empty string."""
        if not self.name or not isinstance(self.name, str):
            raise ValueError("name must be a non-empty string")

    def _validate_raw_value(self):
        """Validate raw_value is a non-negative integer."""
        if not isinstance(self.raw_value, int) or self.raw_value < 0:
            raise ValueError(f"raw_value must be a non-negative integer, got {self.raw_value}")

    def _validate_confidence(self):
        """Validate confidence is between 0.0 and 1.0."""
        if not isinstance(self.confidence, (int, float)):
            raise ValueError(f"confidence must be a number, got {type(self.confidence)}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {self.confidence}")

    def _validate_breakdown(self):
        """Validate breakdown is a dictionary."""
        if not isinstance(self.breakdown, dict):
            raise ValueError("breakdown must be a dictionary")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "raw_value": self.raw_value,
            "confidence": self.confidence,
            "breakdown": self.breakdown.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorResult":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            raw_value=data["raw_value"],
            confidence=data["confidence"],
            breakdown=data.get("breakdown", {}),
        )


@dataclass
class FactorWeights:
    """
    Factor contribution weights for valuation.

    Determines how much each factor contributes to the final AAV.
    Weights must sum to 1.0 (with small tolerance for floating point).

    Different GM styles produce different weight distributions:
    - Analytics-heavy: Higher stats_weight
    - Scout-focused: Higher scouting_weight
    - Market-driven: Higher market_weight
    - Balanced: Even distribution

    Attributes:
        stats_weight: Weight for stats-based factor
        scouting_weight: Weight for scouting grades factor
        market_weight: Weight for market comparables factor
        rating_weight: Weight for overall rating factor
    """

    stats_weight: float = 0.30
    scouting_weight: float = 0.25
    market_weight: float = 0.25
    rating_weight: float = 0.20

    def __post_init__(self):
        """Validate weights."""
        self._validate_individual_weights()
        self._validate_sum()

    def _validate_individual_weights(self):
        """Validate each weight is between 0.0 and 1.0."""
        for attr in ['stats_weight', 'scouting_weight', 'market_weight', 'rating_weight']:
            value = getattr(self, attr)
            if not isinstance(value, (int, float)):
                raise ValueError(f"{attr} must be a number, got {type(value)}")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{attr} must be 0.0-1.0, got {value}")

    def _validate_sum(self):
        """Validate weights sum to 1.0 (with tolerance)."""
        total = self.stats_weight + self.scouting_weight + self.market_weight + self.rating_weight
        if not 0.99 <= total <= 1.01:
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "stats_weight": self.stats_weight,
            "scouting_weight": self.scouting_weight,
            "market_weight": self.market_weight,
            "rating_weight": self.rating_weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "FactorWeights":
        """Create from dictionary."""
        return cls(
            stats_weight=data.get("stats_weight", 0.30),
            scouting_weight=data.get("scouting_weight", 0.25),
            market_weight=data.get("market_weight", 0.25),
            rating_weight=data.get("rating_weight", 0.20),
        )

    @classmethod
    def create_analytics_heavy(cls) -> "FactorWeights":
        """Factory for analytics-focused GM style."""
        return cls(
            stats_weight=0.50,
            scouting_weight=0.15,
            market_weight=0.20,
            rating_weight=0.15,
        )

    @classmethod
    def create_scout_focused(cls) -> "FactorWeights":
        """Factory for scout-focused GM style."""
        return cls(
            stats_weight=0.15,
            scouting_weight=0.50,
            market_weight=0.20,
            rating_weight=0.15,
        )

    @classmethod
    def create_balanced(cls) -> "FactorWeights":
        """Factory for balanced GM style."""
        return cls(
            stats_weight=0.30,
            scouting_weight=0.25,
            market_weight=0.25,
            rating_weight=0.20,
        )

    @classmethod
    def create_market_driven(cls) -> "FactorWeights":
        """Factory for market-driven GM style."""
        return cls(
            stats_weight=0.15,
            scouting_weight=0.15,
            market_weight=0.55,
            rating_weight=0.15,
        )


@dataclass
class ContractOffer:
    """
    Generated contract offer with all financial details.

    Represents the output of the valuation engine - a concrete
    contract offer that can be presented to a player.

    Attributes:
        aav: Annual average value in dollars
        years: Contract length (1-7 years)
        total_value: Total contract value in dollars
        guaranteed: Total guaranteed money in dollars
        signing_bonus: Upfront signing bonus in dollars
        guaranteed_pct: Guaranteed percentage (0.0-1.0)
    """

    aav: int
    years: int
    total_value: int
    guaranteed: int
    signing_bonus: int
    guaranteed_pct: float

    def __post_init__(self):
        """Validate all fields."""
        self._validate_aav()
        self._validate_years()
        self._validate_total_value()
        self._validate_guaranteed()
        self._validate_signing_bonus()
        self._validate_guaranteed_pct()

    def _validate_aav(self):
        """Validate AAV is a non-negative integer."""
        if not isinstance(self.aav, int) or self.aav < 0:
            raise ValueError(f"aav must be a non-negative integer, got {self.aav}")

    def _validate_years(self):
        """Validate years is between 1 and 7."""
        if not isinstance(self.years, int) or not 1 <= self.years <= 7:
            raise ValueError(f"years must be 1-7, got {self.years}")

    def _validate_total_value(self):
        """Validate total_value is a non-negative integer."""
        if not isinstance(self.total_value, int) or self.total_value < 0:
            raise ValueError(f"total_value must be a non-negative integer, got {self.total_value}")

    def _validate_guaranteed(self):
        """Validate guaranteed is non-negative and doesn't exceed total_value."""
        if not isinstance(self.guaranteed, int) or self.guaranteed < 0:
            raise ValueError(f"guaranteed must be a non-negative integer, got {self.guaranteed}")
        if self.guaranteed > self.total_value:
            raise ValueError(
                f"guaranteed ({self.guaranteed}) cannot exceed total_value ({self.total_value})"
            )

    def _validate_signing_bonus(self):
        """Validate signing_bonus is a non-negative integer."""
        if not isinstance(self.signing_bonus, int) or self.signing_bonus < 0:
            raise ValueError(f"signing_bonus must be a non-negative integer, got {self.signing_bonus}")

    def _validate_guaranteed_pct(self):
        """Validate guaranteed_pct is between 0.0 and 1.0."""
        if not isinstance(self.guaranteed_pct, (int, float)):
            raise ValueError(f"guaranteed_pct must be a number, got {type(self.guaranteed_pct)}")
        if not 0.0 <= self.guaranteed_pct <= 1.0:
            raise ValueError(f"guaranteed_pct must be 0.0-1.0, got {self.guaranteed_pct}")

    @property
    def cap_hit_year1(self) -> int:
        """
        Calculate approximate year 1 cap hit.

        Prorates signing bonus over contract length and adds base salary.
        """
        if self.years == 0:
            return 0
        prorated_bonus = self.signing_bonus // self.years
        base_salary = (self.total_value - self.signing_bonus) // self.years
        return prorated_bonus + base_salary

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "aav": self.aav,
            "years": self.years,
            "total_value": self.total_value,
            "guaranteed": self.guaranteed,
            "signing_bonus": self.signing_bonus,
            "guaranteed_pct": self.guaranteed_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContractOffer":
        """Create from dictionary."""
        return cls(
            aav=data["aav"],
            years=data["years"],
            total_value=data["total_value"],
            guaranteed=data["guaranteed"],
            signing_bonus=data["signing_bonus"],
            guaranteed_pct=data["guaranteed_pct"],
        )


@dataclass
class ValuationResult:
    """
    Complete valuation with full audit trail for benchmarking.

    Contains the final contract offer plus all intermediate calculations
    for debugging, benchmarking, and transparency.

    Attributes:
        offer: The generated contract offer
        factor_contributions: Factor name -> weighted contribution in dollars
        gm_style: GM style name (e.g., "analytics_heavy")
        gm_style_description: Human-readable description of style
        pressure_level: 0.0-1.0 job security pressure level
        pressure_adjustment_pct: Percentage adjustment from pressure
        pressure_description: Human-readable pressure explanation
        raw_factor_results: List of individual factor results
        weights_used: The factor weights that were applied
        base_aav: AAV before pressure adjustments
        player_id: Player being valued
        player_name: Player's name
        position: Player's position
        valuation_timestamp: ISO format timestamp
    """

    offer: ContractOffer
    factor_contributions: Dict[str, int]
    gm_style: str
    gm_style_description: str
    pressure_level: float
    pressure_adjustment_pct: float
    pressure_description: str
    raw_factor_results: List[FactorResult]
    weights_used: FactorWeights
    base_aav: int
    player_id: int
    player_name: str
    position: str
    valuation_timestamp: str

    def __post_init__(self):
        """Validate fields."""
        self._validate_pressure_level()
        self._validate_factor_results()

    def _validate_pressure_level(self):
        """Validate pressure_level is between 0.0 and 1.0."""
        if not isinstance(self.pressure_level, (int, float)):
            raise ValueError(f"pressure_level must be a number, got {type(self.pressure_level)}")
        if not 0.0 <= self.pressure_level <= 1.0:
            raise ValueError(f"pressure_level must be 0.0-1.0, got {self.pressure_level}")

    def _validate_factor_results(self):
        """Validate raw_factor_results is a list."""
        if not isinstance(self.raw_factor_results, list):
            raise ValueError("raw_factor_results must be a list")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "offer": self.offer.to_dict(),
            "factor_contributions": self.factor_contributions.copy(),
            "gm_style": self.gm_style,
            "gm_style_description": self.gm_style_description,
            "pressure_level": self.pressure_level,
            "pressure_adjustment_pct": self.pressure_adjustment_pct,
            "pressure_description": self.pressure_description,
            "raw_factor_results": [fr.to_dict() for fr in self.raw_factor_results],
            "weights_used": self.weights_used.to_dict(),
            "base_aav": self.base_aav,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "valuation_timestamp": self.valuation_timestamp,
        }

    def to_benchmark_format(self) -> Dict[str, Any]:
        """
        Export for benchmark comparison against real NFL contracts.

        Returns a simplified dict focused on key contract metrics
        for validation against actual NFL contract data.
        """
        return {
            "player_name": self.player_name,
            "position": self.position,
            "aav": self.offer.aav,
            "years": self.offer.years,
            "total_value": self.offer.total_value,
            "guaranteed": self.offer.guaranteed,
            "guaranteed_pct": self.offer.guaranteed_pct,
            "gm_style": self.gm_style,
            "pressure_level": self.pressure_level,
            "base_aav": self.base_aav,
            "adjustment_pct": self.pressure_adjustment_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValuationResult":
        """Create from dictionary."""
        return cls(
            offer=ContractOffer.from_dict(data["offer"]),
            factor_contributions=data["factor_contributions"],
            gm_style=data["gm_style"],
            gm_style_description=data["gm_style_description"],
            pressure_level=data["pressure_level"],
            pressure_adjustment_pct=data["pressure_adjustment_pct"],
            pressure_description=data["pressure_description"],
            raw_factor_results=[FactorResult.from_dict(fr) for fr in data["raw_factor_results"]],
            weights_used=FactorWeights.from_dict(data["weights_used"]),
            base_aav=data["base_aav"],
            player_id=data["player_id"],
            player_name=data["player_name"],
            position=data["position"],
            valuation_timestamp=data["valuation_timestamp"],
        )