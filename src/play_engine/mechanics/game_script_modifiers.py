"""
Game Script Modifiers for Play Calling.

Converts GameScript enum values into play calling adjustments (run/pass ratios,
formation frequencies, tempo changes, defensive responses).
"""

from typing import Dict, Any, Optional
from ..play_calling.game_situation_analyzer import GameScript


class GameScriptModifiers:
    """Apply game script adjustments to play calling weights."""

    # Script-based run/pass multipliers (for max adherence=1.0)
    # Balanced for modern NFL style (~50% run baseline in COMPETITIVE situations)
    RUN_PASS_MULTIPLIERS = {
        GameScript.CONTROL_GAME: {'run': 2.0, 'pass': 0.7},      # 65% run (was 80%)
        GameScript.PROTECT_LEAD: {'run': 1.3, 'pass': 0.85},     # 55% run (was 65%)
        GameScript.COMPETITIVE: {'run': 1.0, 'pass': 1.0},       # 50% run (was 55%)
        GameScript.COMEBACK_MODE: {'run': 0.6, 'pass': 1.4},     # 35% run (unchanged)
        GameScript.DESPERATION: {'run': 0.25, 'pass': 1.75}      # 15% run (was 12%)
    }

    # Formation multipliers
    FORMATION_MULTIPLIERS = {
        GameScript.CONTROL_GAME: {
            'i_formation': 2.0,
            'shotgun': 0.5,
            'four_wide': 0.4
        },
        GameScript.DESPERATION: {
            'shotgun': 2.5,
            'four_wide': 2.0,
            'i_formation': 0.3
        },
        GameScript.PROTECT_LEAD: {
            'i_formation': 1.4,
            'shotgun': 0.8
        },
        GameScript.COMEBACK_MODE: {
            'shotgun': 1.6,
            'four_wide': 1.4
        },
        GameScript.COMPETITIVE: {}  # No changes
    }

    # Tempo recommendations
    TEMPO_RECOMMENDATIONS = {
        GameScript.CONTROL_GAME: "slow",        # Kill clock
        GameScript.PROTECT_LEAD: "normal",      # Balanced
        GameScript.COMPETITIVE: "normal",       # Default
        GameScript.COMEBACK_MODE: "hurry_up",   # Fast pace
        GameScript.DESPERATION: "hurry_up"      # Maximum speed
    }

    @staticmethod
    def get_run_pass_adjustment(
        game_script: GameScript,
        game_script_adherence: float
    ) -> Dict[str, float]:
        """
        Returns run/pass weight multipliers based on script.

        Args:
            game_script: Current game script
            game_script_adherence: Coach trait (0.0-1.0)

        Returns:
            Dict with 'run' and 'pass' multipliers

        Blending Logic:
            adherence=1.0 → use full multiplier
            adherence=0.0 → no change (1.0x)
            adherence=0.5 → halfway between

        Example:
            CONTROL_GAME with adherence=1.0 → {'run': 3.5, 'pass': 0.5}
            CONTROL_GAME with adherence=0.5 → {'run': 2.25, 'pass': 0.75}
            CONTROL_GAME with adherence=0.0 → {'run': 1.0, 'pass': 1.0}
        """
        base = GameScriptModifiers.RUN_PASS_MULTIPLIERS[game_script]

        # Blend toward neutral (1.0) based on adherence
        # Formula: final = 1.0 + (base - 1.0) * adherence
        return {
            'run': 1.0 + (base['run'] - 1.0) * game_script_adherence,
            'pass': 1.0 + (base['pass'] - 1.0) * game_script_adherence
        }

    @staticmethod
    def get_formation_adjustment(
        game_script: GameScript,
        game_script_adherence: float
    ) -> Dict[str, float]:
        """
        Returns formation weight multipliers based on script.

        Args:
            game_script: Current game script
            game_script_adherence: Coach trait (0.0-1.0)

        Returns:
            Dict with formation name → multiplier

        Example:
            CONTROL_GAME with adherence=1.0 → {'i_formation': 2.0, 'shotgun': 0.5, ...}
            DESPERATION with adherence=1.0 → {'shotgun': 2.5, 'four_wide': 2.0, ...}
        """
        base = GameScriptModifiers.FORMATION_MULTIPLIERS.get(game_script, {})
        if not base:
            return {}

        # Blend each formation multiplier
        result = {}
        for formation, multiplier in base.items():
            result[formation] = 1.0 + (multiplier - 1.0) * game_script_adherence

        return result

    @staticmethod
    def get_tempo_adjustment(
        game_script: GameScript,
        game_script_adherence: float
    ) -> Optional[str]:
        """
        Returns recommended tempo based on script.

        Args:
            game_script: Current game script
            game_script_adherence: Coach trait (0.0-1.0)

        Returns:
            Tempo string: "slow", "normal", "hurry_up", "two_minute"
            Returns None if adherence < 0.5 (coach ignores script)

        Note:
            Only applies if adherence > 0.5, otherwise returns None.
            This allows flexible coaches to use their personality tempo instead.
        """
        if game_script_adherence < 0.5:
            return None  # Low adherence ignores script tempo

        return GameScriptModifiers.TEMPO_RECOMMENDATIONS.get(game_script, "normal")

    @staticmethod
    def get_defensive_response(
        opponent_script: GameScript,
        prevent_defense_usage: float
    ) -> Dict[str, Any]:
        """
        Defensive adjustments based on opponent's likely script.

        Args:
            opponent_script: Inferred opponent game script
            prevent_defense_usage: DC trait (0.0-1.0)

        Returns:
            Dict with defensive response:
                - 'use_prevent': bool (trigger prevent defense)
                - 'coverage_adjustment': str (coverage scheme)
                - 'pressure': bool (send pressure)

        Logic:
            - If opponent in DESPERATION and DC has prevent_usage > 0.4:
              Use prevent defense (3-man rush, 6+ DBs, zone)
            - Otherwise: normal coverage
        """
        # Prevent defense vs DESPERATION opponent
        if opponent_script == GameScript.DESPERATION:
            if prevent_defense_usage > 0.4:
                return {
                    'use_prevent': True,
                    'coverage_adjustment': 'Prevent',
                    'pressure': False  # 3-man rush, drop 8 into coverage
                }
            else:
                # Low-usage DC doesn't use prevent
                return {
                    'use_prevent': False,
                    'coverage_adjustment': 'Cover-2',  # Safe zone coverage
                    'pressure': False
                }

        # Default: no special adjustments
        return {
            'use_prevent': False,
            'coverage_adjustment': None,
            'pressure': None
        }
