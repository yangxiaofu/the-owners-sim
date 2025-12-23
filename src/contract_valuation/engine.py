"""
Contract Valuation Engine - Main orchestrator.

Coordinates value factors, GM influence, and owner pressure modifiers
to produce complete contract valuations with full audit trails.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, TYPE_CHECKING

from contract_valuation.models import (
    FactorResult,
    FactorWeights,
    ContractOffer,
    ValuationResult,
)
from contract_valuation.context import ValuationContext, OwnerContext
from contract_valuation.factors.base import ValueFactor
from contract_valuation.factors import (
    StatsFactor,
    ScoutingFactor,
    MarketFactor,
    RatingFactor,
    AgeFactor,
)
from contract_valuation.gm_influence.styles import GMStyle
from contract_valuation.gm_influence.weight_calculator import (
    GMWeightCalculator,
    WeightCalculationResult,
)
from contract_valuation.owner_pressure.chain import (
    apply_modifier_chain,
    create_default_modifier_chain,
)

if TYPE_CHECKING:
    from team_management.gm_archetype import GMArchetype


class ContractValuationEngine:
    """
    Main orchestrator for contract valuation.

    Coordinates value factors, GM influence, and owner pressure modifiers
    to produce complete contract valuations with full audit trails.

    Usage:
        engine = ContractValuationEngine()
        result = engine.valuate(
            player_data=player_dict,
            valuation_context=market_context,
            owner_context=owner_ctx,
            gm_archetype=gm,
        )
        print(f"AAV: ${result.offer.aav:,}")
        print(f"GM Style: {result.gm_style}")
        print(f"Pressure: {result.pressure_level:.0%}")

    Attributes:
        TIER_THRESHOLDS: Rating thresholds for player tiers
        CONTRACT_YEARS_BY_TIER: Base contract years by tier
        GUARANTEED_PCT_BY_TIER: Base guaranteed percentage by tier
    """

    # Tier thresholds (rating -> tier)
    TIER_THRESHOLDS = {
        "elite": 90,
        "quality": 80,
        "starter": 70,
        "backup": 0,
    }

    # Base contract years by tier
    CONTRACT_YEARS_BY_TIER = {
        "elite": 5,
        "quality": 4,
        "starter": 3,
        "backup": 1,
    }

    # Base guaranteed percentage by tier (calibrated to NFL 2024 market)
    GUARANTEED_PCT_BY_TIER = {
        "elite": 0.70,      # 70% (matches NFL elite 70-80%)
        "quality": 0.55,    # 55% (up from 45%)
        "starter": 0.40,    # 40% (up from 35%)
        "backup": 0.25,
    }

    # Market calibration multiplier (adjusts for systematic bias)
    MARKET_CALIBRATION = 1.10  # +10% to center on NFL market

    # Position-specific age thresholds for contract year reductions
    # Format: (age_for_minus_1_year, age_for_minus_2_years)
    # Based on position peak windows - shorter peaks = earlier reductions
    POSITION_AGE_THRESHOLDS = {
        # Short career positions (peak ends early)
        "RB": (28, 30),      # Peak 24-27, drops fast after
        "FB": (29, 31),      # Slightly longer than RB
        # Medium career positions
        "CB": (30, 32),      # Peak 25-29
        "LB": (30, 32),      # Peak 25-29
        "MLB": (30, 32),
        "LOLB": (30, 32),
        "ROLB": (30, 32),
        "S": (31, 33),       # Peak 26-30
        "FS": (31, 33),
        "SS": (31, 33),
        # Standard career positions
        "WR": (31, 33),      # Peak 26-30
        "TE": (31, 33),      # Peak 26-30
        "EDGE": (31, 33),    # Peak 26-30
        "DT": (31, 33),      # Peak 26-30
        "LE": (31, 33),
        "RE": (31, 33),
        # Long career positions (offensive line)
        "OT": (33, 35),      # Peak 27-32
        "LT": (33, 35),
        "RT": (33, 35),
        "OG": (32, 34),      # Peak 26-31
        "LG": (32, 34),
        "RG": (32, 34),
        "C": (32, 34),
        # Longest career positions
        "QB": (34, 35),      # Peak 28-33, cap at 3 years for 35+
        "K": (38, 42),       # Peak 28-38, very long careers
        "P": (38, 42),
    }

    # Default thresholds for unknown positions
    DEFAULT_AGE_THRESHOLDS = (30, 33)

    # Young high-potential bonus thresholds
    YOUNG_HIGH_POTENTIAL_THRESHOLD = 25
    HIGH_POTENTIAL_RATING = 85

    def __init__(
        self,
        factors: Optional[List[ValueFactor]] = None,
        weight_calculator: Optional[GMWeightCalculator] = None,
    ):
        """
        Initialize the valuation engine.

        Args:
            factors: Custom list of ValueFactor instances.
                    If None, uses default factors (Stats, Scouting, Market, Rating, Age).
            weight_calculator: Custom GMWeightCalculator.
                              If None, creates default calculator.
        """
        self._factors = factors if factors is not None else self._create_default_factors()
        self._weight_calculator = weight_calculator or GMWeightCalculator()

    @staticmethod
    def _create_default_factors() -> List[ValueFactor]:
        """Create the default set of valuation factors."""
        return [
            StatsFactor(),
            ScoutingFactor(),
            MarketFactor(),
            RatingFactor(),
            AgeFactor(),
        ]

    def valuate(
        self,
        player_data: Dict[str, Any],
        valuation_context: ValuationContext,
        owner_context: OwnerContext,
        gm_archetype: Optional["GMArchetype"] = None,
        override_weights: Optional[FactorWeights] = None,
    ) -> ValuationResult:
        """
        Perform complete contract valuation for a player.

        Args:
            player_data: Player information dictionary containing:
                - player_id: int (required)
                - name: str (required)
                - position: str (required)
                - age: int (optional but recommended)
                - overall_rating: int 0-99 (optional but recommended)
                - stats: Dict[str, Any] (optional, for StatsFactor)
                - attributes: Dict[str, Any] (optional, for ScoutingFactor)
                - contract_year: bool (optional, for MarketFactor)
            valuation_context: Market context (cap, season, rates)
            owner_context: Owner/GM situational context
            gm_archetype: Optional GMArchetype for weight calculation.
                         If None and override_weights is None, uses BALANCED.
            override_weights: Optional FactorWeights to use directly,
                            bypassing GMArchetype calculation.

        Returns:
            ValuationResult with complete contract offer and audit trail.

        Raises:
            ValueError: If required player_data fields are missing.
        """
        # Step 1: Validate required fields
        self._validate_player_data(player_data)

        # Step 2: Calculate all factor results
        factor_results = self._calculate_factors(player_data, valuation_context)

        # Step 3: Determine weights (from archetype, override, or default)
        weights, gm_style, gm_description = self._determine_weights(
            gm_archetype, override_weights
        )

        # Step 4: Aggregate factors with weights -> base AAV
        base_aav, factor_contributions = self._aggregate_factors(
            factor_results, weights
        )

        # Step 4b: Apply market calibration to center on NFL market
        base_aav = int(base_aav * self.MARKET_CALIBRATION)

        # Step 5: Apply pressure modifier chain -> adjusted AAV
        adjusted_aav, total_pressure_pct, modifier_results = self._apply_pressure(
            base_aav, owner_context, player_data
        )

        # Step 6: Determine contract structure
        contract_offer = self._determine_contract_structure(
            adjusted_aav, player_data, owner_context
        )

        # Step 7: Build pressure description
        pressure_level, pressure_description = self._build_pressure_summary(
            owner_context, modifier_results
        )

        # Step 8: Build and return ValuationResult
        return ValuationResult(
            offer=contract_offer,
            factor_contributions=factor_contributions,
            gm_style=gm_style,
            gm_style_description=gm_description,
            pressure_level=pressure_level,
            pressure_adjustment_pct=total_pressure_pct,
            pressure_description=pressure_description,
            raw_factor_results=factor_results,
            weights_used=weights,
            base_aav=base_aav,
            player_id=player_data["player_id"],
            player_name=player_data["name"],
            position=player_data["position"],
            valuation_timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def valuate_batch(
        self,
        players: List[Dict[str, Any]],
        valuation_context: ValuationContext,
        owner_context: OwnerContext,
        gm_archetype: Optional["GMArchetype"] = None,
        override_weights: Optional[FactorWeights] = None,
    ) -> List[ValuationResult]:
        """
        Valuate multiple players in batch.

        Args:
            players: List of player data dictionaries
            valuation_context: Shared market context
            owner_context: Shared owner context
            gm_archetype: Optional shared GM archetype
            override_weights: Optional shared weights

        Returns:
            List of ValuationResult for each player
        """
        return [
            self.valuate(
                player_data=player,
                valuation_context=valuation_context,
                owner_context=owner_context,
                gm_archetype=gm_archetype,
                override_weights=override_weights,
            )
            for player in players
        ]

    def _validate_player_data(self, player_data: Dict[str, Any]) -> None:
        """
        Validate required player data fields.

        Args:
            player_data: Player information dictionary

        Raises:
            ValueError: If required fields missing or invalid
        """
        required_fields = ["player_id", "name", "position"]
        missing = [f for f in required_fields if f not in player_data]
        if missing:
            raise ValueError(f"Missing required player_data fields: {missing}")

        # Validate position is a string
        if not isinstance(player_data["position"], str):
            raise ValueError("position must be a string")

        # Validate player_id is an int
        if not isinstance(player_data["player_id"], int):
            raise ValueError("player_id must be an integer")

    def _calculate_factors(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext,
    ) -> List[FactorResult]:
        """
        Calculate values from all factors.

        Runs each factor's calculate() method, catching failures gracefully.
        If a factor fails, it's excluded from the results.

        Args:
            player_data: Player information dictionary
            context: Valuation context

        Returns:
            List of FactorResult from each successful factor
        """
        results: List[FactorResult] = []

        for factor in self._factors:
            try:
                result = factor.calculate(player_data, context)
                results.append(result)
            except (ValueError, KeyError, TypeError):
                # Factor couldn't calculate (missing data, etc.)
                # Continue with other factors
                pass
            except Exception:
                # Unexpected error - continue
                pass

        # If no factors succeeded, must have at least a fallback
        if not results:
            # Fallback to RatingFactor only
            try:
                rating_factor = RatingFactor()
                result = rating_factor.calculate(player_data, context)
                results.append(result)
            except Exception:
                # Absolute fallback: create minimal result
                results.append(self._create_fallback_result(player_data, context))

        return results

    def _create_fallback_result(
        self,
        player_data: Dict[str, Any],
        context: ValuationContext,
    ) -> FactorResult:
        """Create fallback result when all factors fail."""
        # Use 1% of cap as absolute minimum
        fallback_aav = int(context.salary_cap * 0.01)
        return FactorResult(
            name="fallback",
            raw_value=fallback_aav,
            confidence=0.30,
            breakdown={
                "reason": "All factors failed",
                "fallback_aav": fallback_aav,
            },
        )

    def _determine_weights(
        self,
        gm_archetype: Optional["GMArchetype"],
        override_weights: Optional[FactorWeights],
    ) -> Tuple[FactorWeights, str, str]:
        """
        Determine factor weights from archetype or override.

        Priority:
        1. override_weights (if provided)
        2. gm_archetype (calculate via GMWeightCalculator)
        3. BALANCED style (default)

        Args:
            gm_archetype: Optional GMArchetype instance
            override_weights: Optional explicit weights

        Returns:
            Tuple of (weights, gm_style_name, gm_style_description)
        """
        if override_weights is not None:
            # Use override directly
            return (
                override_weights,
                "custom",
                "Custom factor weights provided directly.",
            )

        if gm_archetype is not None:
            # Calculate from archetype
            result: WeightCalculationResult = self._weight_calculator.calculate_weights(
                gm_archetype
            )
            return (
                result.weights,
                result.dominant_style.value,
                result.rationale,
            )

        # Default to BALANCED
        balanced = GMStyle.BALANCED
        return (
            balanced.get_weights(),
            balanced.value,
            balanced.get_description(),
        )

    def _aggregate_factors(
        self,
        factor_results: List[FactorResult],
        weights: FactorWeights,
    ) -> Tuple[int, Dict[str, int]]:
        """
        Aggregate factor results using weighted average.

        Maps factor names to weight fields:
        - "stats_based" -> stats_weight
        - "scouting" -> scouting_weight
        - "market" -> market_weight
        - "rating" -> rating_weight
        - "age" -> Treated as adjustment factor, uses rating_weight

        Args:
            factor_results: List of FactorResult from factors
            weights: Factor weights to apply

        Returns:
            Tuple of (base_aav, factor_contributions dict)
        """
        # Map factor names to weight attributes
        weight_map = {
            "stats_based": weights.stats_weight,
            "scouting": weights.scouting_weight,
            "market": weights.market_weight,
            "rating": weights.rating_weight,
            "age": weights.rating_weight,  # Age shares rating weight
            "fallback": 1.0,  # Fallback gets full weight if only factor
        }

        # Calculate weighted sum
        weighted_sum = 0.0
        total_weight = 0.0
        contributions: Dict[str, int] = {}

        for result in factor_results:
            weight = weight_map.get(result.name, 0.0)
            if weight > 0:
                # Adjust weight by confidence
                effective_weight = weight * result.confidence
                contribution = result.raw_value * effective_weight
                weighted_sum += contribution
                total_weight += effective_weight
                contributions[result.name] = int(result.raw_value * weight)

        # Calculate weighted average
        if total_weight > 0:
            base_aav = int(weighted_sum / total_weight)
        else:
            # Fallback if no weights applied
            base_aav = int(sum(r.raw_value for r in factor_results) / len(factor_results))

        return base_aav, contributions

    def _apply_pressure(
        self,
        base_aav: int,
        owner_context: OwnerContext,
        player_data: Dict[str, Any],
    ) -> Tuple[int, float, List[Dict[str, Any]]]:
        """
        Apply pressure modifier chain to base AAV.

        Uses default modifier chain: JobSecurity -> WinNow -> BudgetStance.

        Args:
            base_aav: Pre-pressure AAV
            owner_context: Owner/GM context
            player_data: Player data (for age-based modifiers)

        Returns:
            Tuple of (adjusted_aav, total_adjustment_pct, modifier_results)
        """
        modifiers = create_default_modifier_chain()
        return apply_modifier_chain(
            base_aav, owner_context, modifiers, player_data
        )

    def _determine_contract_structure(
        self,
        aav: int,
        player_data: Dict[str, Any],
        owner_context: OwnerContext,
    ) -> ContractOffer:
        """
        Determine contract years, guarantees, and signing bonus.

        Logic:
        1. Base years from tier (elite=5, quality=4, starter=3, backup=1)
        2. Age adjustments (-1 for 30+, -2 for 33+)
        3. Young high-potential bonus (+1 for <25 with high rating)
        4. Clamp to owner's max_contract_years
        5. Guarantees from tier + pressure adjustment
        6. Clamp to owner's max_guaranteed_pct

        Args:
            aav: Annual average value
            player_data: Player information
            owner_context: Owner constraints

        Returns:
            Complete ContractOffer
        """
        # Get player info
        rating = player_data.get("overall_rating", 75)
        age = player_data.get("age", 27)

        # Determine tier
        tier = self._rating_to_tier(rating)

        # Base years from tier
        base_years = self.CONTRACT_YEARS_BY_TIER[tier]

        # Get position for position-aware age adjustments
        position = player_data.get("position", "").upper()

        # Age adjustments (position-aware)
        years = self._apply_age_year_adjustment(base_years, age, position)

        # Young high-potential bonus
        if age < self.YOUNG_HIGH_POTENTIAL_THRESHOLD and rating >= self.HIGH_POTENTIAL_RATING:
            years += 1

        # Clamp to owner constraint
        years = min(years, owner_context.max_contract_years)
        years = max(1, years)  # At least 1 year
        years = min(years, 7)  # ContractOffer max is 7

        # Calculate guarantees
        base_guaranteed_pct = self.GUARANTEED_PCT_BY_TIER[tier]

        # Pressure adjustment (hot seat GMs give higher guarantees)
        pressure = owner_context.job_security.calculate_security_score()
        if pressure > 0.7:
            # Hot seat: +10-15%
            pressure_bonus = 0.10 + (pressure - 0.7) * 0.166  # scales to +15% at 1.0
            base_guaranteed_pct += pressure_bonus
        elif pressure < 0.3:
            # Secure: -5%
            base_guaranteed_pct -= 0.05

        # Clamp to owner constraint
        guaranteed_pct = min(base_guaranteed_pct, owner_context.max_guaranteed_pct)
        guaranteed_pct = max(0.20, guaranteed_pct)  # Minimum 20%
        guaranteed_pct = min(guaranteed_pct, 1.0)  # Max 100%

        # Calculate contract values
        total_value = aav * years
        guaranteed = int(total_value * guaranteed_pct)

        # Signing bonus is typically 30-50% of guaranteed
        signing_bonus_pct = 0.40 if tier in ["elite", "quality"] else 0.30
        signing_bonus = int(guaranteed * signing_bonus_pct)

        return ContractOffer(
            aav=aav,
            years=years,
            total_value=total_value,
            guaranteed=guaranteed,
            signing_bonus=signing_bonus,
            guaranteed_pct=round(guaranteed_pct, 3),
        )

    def _rating_to_tier(self, rating: int) -> str:
        """Map overall rating to tier."""
        if rating >= self.TIER_THRESHOLDS["elite"]:
            return "elite"
        elif rating >= self.TIER_THRESHOLDS["quality"]:
            return "quality"
        elif rating >= self.TIER_THRESHOLDS["starter"]:
            return "starter"
        else:
            return "backup"

    def _apply_age_year_adjustment(
        self, base_years: int, age: int, position: str = ""
    ) -> int:
        """
        Apply position-aware age-based year adjustments.

        Different positions have different career arcs:
        - RBs decline earliest (28+)
        - QBs/K/P have longest careers (34+/38+)
        - Most positions follow standard 30+/33+ thresholds

        Args:
            base_years: Base contract years from tier
            age: Player's current age
            position: Player's position (e.g., "RB", "QB")

        Returns:
            Adjusted contract years (minimum 1)
        """
        # Get position-specific thresholds
        thresholds = self.POSITION_AGE_THRESHOLDS.get(
            position, self.DEFAULT_AGE_THRESHOLDS
        )
        age_minus_1, age_minus_2 = thresholds

        if age >= age_minus_2:
            return max(1, base_years - 2)
        elif age >= age_minus_1:
            return max(1, base_years - 1)
        return base_years

    def _build_pressure_summary(
        self,
        owner_context: OwnerContext,
        modifier_results: List[Dict[str, Any]],
    ) -> Tuple[float, str]:
        """
        Build pressure level and description from modifier results.

        Args:
            owner_context: Owner context
            modifier_results: Results from each modifier

        Returns:
            Tuple of (pressure_level, description_string)
        """
        # Calculate overall pressure level
        pressure = owner_context.job_security.calculate_security_score()

        # Build description from modifier results
        descriptions = [
            r.get("description", "") for r in modifier_results if r.get("description")
        ]
        combined_description = (
            " | ".join(descriptions) if descriptions else "No pressure adjustments applied."
        )

        return pressure, combined_description