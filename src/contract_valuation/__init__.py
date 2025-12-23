"""
Contract Valuation Engine.

Provides multi-factor contract valuation with GM personality influence
and owner pressure modifiers. Designed for extensibility and benchmarking.

Usage:
    from contract_valuation import (
        # Main engine
        ContractValuationEngine,
        # Core models
        FactorResult,
        FactorWeights,
        ContractOffer,
        ValuationResult,
        # Context models
        JobSecurityContext,
        ValuationContext,
        OwnerContext,
        # Interfaces
        ValueFactor,
        PressureModifier,
        # Enums
        GMStyle,
    )

Example:
    engine = ContractValuationEngine()
    result = engine.valuate(
        player_data={"player_id": 1, "name": "Player", "position": "QB", "overall_rating": 85},
        valuation_context=ValuationContext.create_default_2025(),
        owner_context=OwnerContext.create_default("dynasty", 1),
    )
    print(f"AAV: ${result.offer.aav:,}")
"""

# Main engine
from contract_valuation.engine import ContractValuationEngine

# Core models
from contract_valuation.models import (
    FactorResult,
    FactorWeights,
    ContractOffer,
    ValuationResult,
)

# Context models
from contract_valuation.context import (
    JobSecurityContext,
    ValuationContext,
    OwnerContext,
)

# Abstract interfaces
from contract_valuation.factors.base import ValueFactor
from contract_valuation.owner_pressure.base import PressureModifier

# Enums
from contract_valuation.gm_influence.styles import GMStyle

__all__ = [
    # Main engine
    "ContractValuationEngine",
    # Core models
    "FactorResult",
    "FactorWeights",
    "ContractOffer",
    "ValuationResult",
    # Context models
    "JobSecurityContext",
    "ValuationContext",
    "OwnerContext",
    # Interfaces
    "ValueFactor",
    "PressureModifier",
    # Enums
    "GMStyle",
]