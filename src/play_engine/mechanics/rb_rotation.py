"""
RB Rotation Manager - Handles running back workload distribution.

Tracks carries per game and selects appropriate RB based on:
- Coach philosophy (bellcow vs committee)
- Current workload balance
- Weighted randomness for realistic variation
"""

from typing import List, Optional, Dict, Union, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from play_engine.play_calling.offensive_coordinator import OffensiveCoordinator


class RBSubstitutionManager:
    """
    Manages RB rotation based on workload and coach philosophy.

    Creates realistic carry distribution between starter and backup RBs
    based on the offensive coordinator's play-calling tendencies.
    """

    def __init__(self, starter_share: float = 0.55):
        """
        Initialize RB rotation manager.

        Args:
            starter_share: Target percentage of carries for starter (0.5-0.7)
                          Default 0.55 = committee approach
        """
        self.starter_share = max(0.5, min(0.75, starter_share))  # Clamp to reasonable range
        self.carries_by_player: Dict[Union[int, str], int] = {}  # player_key -> carry count this game

    @classmethod
    def from_coaching_staff(cls, offensive_coordinator: 'OffensiveCoordinator') -> 'RBSubstitutionManager':
        """
        Create manager with starter_share based on OC philosophy.

        Maps OC traits to RB usage:
        - High ground_and_pound_preference (>0.6) → bellcow (0.70 starter)
        - Low ground_and_pound_preference (<0.4) → even committee (0.50 starter)
        - Balanced → committee (0.55 starter)

        Args:
            offensive_coordinator: The team's OC with philosophy traits

        Returns:
            Configured RBSubstitutionManager
        """
        oc = offensive_coordinator

        # Default committee approach
        starter_share = 0.55

        # Derive starter_share from OC philosophy
        if hasattr(oc, 'philosophy') and hasattr(oc.philosophy, 'ground_and_pound_preference'):
            gnp = oc.philosophy.ground_and_pound_preference
            if gnp > 0.6:
                starter_share = 0.70  # Bellcow approach - feature the starter
            elif gnp < 0.4:
                starter_share = 0.50  # Even committee - spread touches
            else:
                starter_share = 0.55  # Default committee
        elif hasattr(oc, 'run_preference'):
            # Fallback to run_preference if no philosophy
            if oc.run_preference > 0.6:
                starter_share = 0.65  # Run-heavy = slightly more starter usage
            else:
                starter_share = 0.55

        return cls(starter_share=starter_share)

    def select_rb_for_carry(self, available_rbs: List) -> Optional[any]:
        """
        Select which RB should get the ball based on workload distribution.

        Uses soft enforcement with weighted randomness for realistic variation.
        The starter_share target is maintained over the course of the game,
        but individual play selection includes randomness.

        Args:
            available_rbs: List of RB Player objects in depth chart order
                          (starter first, backup second)

        Returns:
            Selected Player object, or None if no RBs available
        """
        if not available_rbs:
            return None
        if len(available_rbs) == 1:
            return available_rbs[0]

        starter = available_rbs[0]  # First in depth chart
        backup = available_rbs[1]

        # Get player IDs (handle both attribute and dictionary access)
        # Use player_id if available, otherwise fallback to name+number key for synthetic players
        starter_id = getattr(starter, 'player_id', None) if hasattr(starter, 'player_id') else starter.get('player_id')
        backup_id = getattr(backup, 'player_id', None) if hasattr(backup, 'player_id') else backup.get('player_id')

        # Fallback to name+number key for synthetic players (player_id is None)
        if starter_id is None:
            starter_name = getattr(starter, 'name', None) or starter.get('name', 'Unknown')
            starter_number = getattr(starter, 'number', None) or starter.get('number', 0)
            starter_id = f"{starter_name}_{starter_number}"
        if backup_id is None:
            backup_name = getattr(backup, 'name', None) or backup.get('name', 'Unknown')
            backup_number = getattr(backup, 'number', None) or backup.get('number', 0)
            backup_id = f"{backup_name}_{backup_number}"

        starter_carries = self.carries_by_player.get(starter_id, 0)
        backup_carries = self.carries_by_player.get(backup_id, 0)
        total_carries = starter_carries + backup_carries

        if total_carries == 0:
            # First carry always goes to starter
            return starter

        # Calculate current share
        current_starter_share = starter_carries / total_carries

        # Soft enforcement with deviation tolerance
        # If we're way off target, force correction
        # If we're close to target, use weighted random
        deviation = current_starter_share - self.starter_share

        if deviation > 0.15:
            # Starter has gotten too many - give to backup
            return backup
        elif deviation < -0.15:
            # Starter hasn't gotten enough - give to starter
            return starter
        else:
            # Within range - use weighted random based on target
            return starter if random.random() < self.starter_share else backup

    def record_carry(self, player_key) -> None:
        """
        Record a carry for workload tracking.

        Args:
            player_key: ID or name+number key of the player who carried the ball
        """
        self.carries_by_player[player_key] = self.carries_by_player.get(player_key, 0) + 1

    def get_carry_distribution(self) -> Dict[Union[int, str], int]:
        """
        Get current carry distribution.

        Returns:
            Dictionary of player_id -> carry count
        """
        return self.carries_by_player.copy()

    def reset(self) -> None:
        """Reset carry tracking for a new game."""
        self.carries_by_player.clear()

    def __repr__(self) -> str:
        total = sum(self.carries_by_player.values())
        return f"RBSubstitutionManager(starter_share={self.starter_share:.0%}, total_carries={total})"