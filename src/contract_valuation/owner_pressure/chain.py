"""
Modifier chain application utility.

Applies pressure modifiers sequentially to produce final adjusted AAV.
"""

from typing import List, Tuple, Dict, Any, Optional

from contract_valuation.context import OwnerContext
from contract_valuation.owner_pressure.base import PressureModifier


def apply_modifier_chain(
    base_aav: int,
    context: OwnerContext,
    modifiers: List[PressureModifier],
    player_data: Optional[Dict[str, Any]] = None
) -> Tuple[int, float, List[Dict[str, Any]]]:
    """
    Apply a chain of pressure modifiers sequentially.

    Modifiers are applied in order: JobSecurity -> WinNow -> BudgetStance.
    Each modifier's output becomes the next modifier's input.

    Args:
        base_aav: Starting AAV before any adjustments
        context: Owner/situational context
        modifiers: List of PressureModifier instances to apply
        player_data: Optional player data dict (for age-based modifiers)

    Returns:
        Tuple of:
        - final_aav: AAV after all modifiers applied
        - total_adjustment_pct: Combined adjustment percentage from base
        - modifier_results: List of individual modifier breakdowns
    """
    if base_aav <= 0:
        return base_aav, 0.0, []

    current_aav = base_aav
    modifier_results: List[Dict[str, Any]] = []

    for modifier in modifiers:
        # Handle WinNowModifier which needs player age
        if modifier.modifier_name == "win_now" and player_data:
            player_age = player_data.get("age")
            adjusted_aav, description = modifier.apply(
                current_aav, context, player_age=player_age
            )
        else:
            adjusted_aav, description = modifier.apply(current_aav, context)

        # Calculate adjustment for this modifier
        if current_aav > 0:
            adjustment_pct = (adjusted_aav - current_aav) / current_aav
        else:
            adjustment_pct = 0.0

        pressure_level = modifier.calculate_pressure_level(context)

        modifier_results.append({
            "modifier_name": modifier.modifier_name,
            "input_aav": current_aav,
            "output_aav": adjusted_aav,
            "adjustment_pct": round(adjustment_pct, 4),
            "adjustment_dollars": adjusted_aav - current_aav,
            "pressure_level": round(pressure_level, 3),
            "description": description,
        })

        current_aav = adjusted_aav

    # Calculate total adjustment from original base
    if base_aav > 0:
        total_adjustment_pct = (current_aav - base_aav) / base_aav
    else:
        total_adjustment_pct = 0.0

    return current_aav, round(total_adjustment_pct, 4), modifier_results


def create_default_modifier_chain() -> List[PressureModifier]:
    """
    Create the default modifier chain.

    Returns:
        List of modifiers in application order:
        1. JobSecurityModifier
        2. WinNowModifier
        3. BudgetStanceModifier
    """
    from contract_valuation.owner_pressure.job_security import JobSecurityModifier
    from contract_valuation.owner_pressure.win_now import WinNowModifier
    from contract_valuation.owner_pressure.budget_stance import BudgetStanceModifier

    return [
        JobSecurityModifier(),
        WinNowModifier(),
        BudgetStanceModifier(),
    ]