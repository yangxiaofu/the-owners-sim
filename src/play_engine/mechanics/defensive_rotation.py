"""
Defensive Rotation Manager - Handles defensive player workload distribution.

Manages defensive player rotation for realistic snap distribution:
- Defensive Line (DE, DT, NT): 55-75% starter share (most rotation)
- Linebackers (MIKE, SAM, WILL, OLB, ILB): 70-85% starter share
- Defensive Backs (CB, FS, SS): 82-95% starter share (least rotation)

Rotation percentages are influenced by defensive coordinator philosophy.
"""

from dataclasses import dataclass
from typing import List, Dict, Union, Optional, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from play_engine.play_calling.defensive_coordinator import DefensiveCoordinator


# Position group mappings
DEFENSIVE_LINE_POSITIONS = frozenset([
    'defensive_end', 'defensive_tackle', 'nose_tackle', 'leo'
])
LINEBACKER_POSITIONS = frozenset([
    'mike_linebacker', 'sam_linebacker', 'will_linebacker',
    'inside_linebacker', 'outside_linebacker', 'linebacker'
])
DEFENSIVE_BACK_POSITIONS = frozenset([
    'cornerback', 'nickel_cornerback', 'free_safety', 'strong_safety', 'safety'
])


@dataclass
class PositionGroupConfig:
    """Configuration for a position group's rotation."""
    starter_share: float  # Target snap percentage for starters (0.0-1.0)
    deviation_tolerance: float = 0.10  # Allow ±10% deviation before forcing correction

    def __post_init__(self):
        """Clamp values to valid ranges."""
        self.starter_share = max(0.50, min(0.98, self.starter_share))
        self.deviation_tolerance = max(0.05, min(0.20, self.deviation_tolerance))


class DefensiveRotationManager:
    """
    Manages defensive player rotation per position group.

    Similar to RBSubstitutionManager but handles multiple position groups:
    - Defensive Line (DE, DT, NT) - heaviest rotation
    - Linebackers (MIKE, SAM, WILL, OLB, ILB) - moderate rotation
    - Defensive Backs (CB, FS, SS, NCB) - minimal rotation

    NFL Baseline Rotation:
    - DL starters play 55-75% of snaps (pass rush fatigue)
    - LB starters play 70-85% of snaps (coverage/run duties)
    - DB starters play 82-95% of snaps (coverage consistency critical)
    """

    def __init__(
        self,
        dl_starter_share: float = 0.65,
        lb_starter_share: float = 0.80,
        db_starter_share: float = 0.90
    ):
        """
        Initialize defensive rotation manager.

        Args:
            dl_starter_share: Target percentage for DL starters (0.55-0.75)
            lb_starter_share: Target percentage for LB starters (0.70-0.85)
            db_starter_share: Target percentage for DB starters (0.82-0.95)
        """
        self.position_configs = {
            'DL': PositionGroupConfig(starter_share=dl_starter_share),
            'LB': PositionGroupConfig(starter_share=lb_starter_share),
            'DB': PositionGroupConfig(starter_share=db_starter_share),
        }

        # Track snaps per player (player_key -> snap_count)
        self.snaps_by_player: Dict[Union[int, str], int] = {}

        # Track total snaps per position group
        self.position_group_snaps: Dict[str, int] = {'DL': 0, 'LB': 0, 'DB': 0}

        # Track which players are starters for each position group
        self._starter_keys: Dict[str, set] = {'DL': set(), 'LB': set(), 'DB': set()}

    @classmethod
    def from_defensive_coordinator(cls, dc: 'DefensiveCoordinator') -> 'DefensiveRotationManager':
        """
        Create manager from DC philosophy.

        Maps DC personnel traits to rotation percentages:
        - High edge_rusher_rotation (1.0) -> more DL rotation (0.55 starter share)
        - Low edge_rusher_rotation (0.0) -> less DL rotation (0.75 starter share)

        Args:
            dc: DefensiveCoordinator with personnel usage traits

        Returns:
            Configured DefensiveRotationManager
        """
        # Default values if DC doesn't have personnel config
        edge_rotation = 0.6
        lb_versatility = 0.5
        safety_flexibility = 0.6

        # Try to get DC personnel traits
        if hasattr(dc, 'personnel'):
            edge_rotation = getattr(dc.personnel, 'edge_rusher_rotation', 0.6)
            lb_versatility = getattr(dc.personnel, 'linebacker_versatility', 0.5)
            safety_flexibility = getattr(dc.personnel, 'safety_flexibility', 0.6)

        # Map traits to starter shares (higher rotation = lower starter share)
        # edge_rusher_rotation: 0.0 -> 0.75, 1.0 -> 0.55 (range: 0.55-0.75)
        dl_share = 0.75 - (edge_rotation * 0.20)

        # linebacker_versatility: 0.0 -> 0.85, 1.0 -> 0.70 (range: 0.70-0.85)
        lb_share = 0.85 - (lb_versatility * 0.15)

        # safety_flexibility: 0.0 -> 0.95, 1.0 -> 0.82 (range: 0.82-0.95)
        db_share = 0.95 - (safety_flexibility * 0.13)

        return cls(
            dl_starter_share=dl_share,
            lb_starter_share=lb_share,
            db_starter_share=db_share
        )

    def get_position_group(self, position: str) -> Optional[str]:
        """
        Determine which position group a player belongs to.

        Args:
            position: Player's primary position string

        Returns:
            'DL', 'LB', 'DB', or None if not a defensive position
        """
        pos_lower = position.lower() if position else ''

        if pos_lower in DEFENSIVE_LINE_POSITIONS:
            return 'DL'
        elif pos_lower in LINEBACKER_POSITIONS or 'linebacker' in pos_lower:
            return 'LB'
        elif pos_lower in DEFENSIVE_BACK_POSITIONS:
            return 'DB'
        return None

    def _get_player_key(self, player) -> Union[int, str]:
        """
        Get unique key for a player.

        Uses player_id if available, otherwise creates name+number key.

        Args:
            player: Player object (dict or object)

        Returns:
            Unique player identifier
        """
        # Try player_id first
        player_id = None
        if hasattr(player, 'player_id'):
            player_id = player.player_id
        elif isinstance(player, dict):
            player_id = player.get('player_id')

        if player_id is not None:
            return player_id

        # Fallback to name+number for synthetic players
        if hasattr(player, 'name'):
            name = player.name
            number = getattr(player, 'number', 0)
        elif isinstance(player, dict):
            name = player.get('name', 'Unknown')
            number = player.get('number', 0)
        else:
            name = 'Unknown'
            number = 0

        return f"{name}_{number}"

    def select_field_players(
        self,
        position_group: str,
        available_players: List,
        slots_needed: int
    ) -> List:
        """
        Select which players should be on the field for this snap.

        Uses soft enforcement with deviation tolerance. Starters get
        their target share, but individual play selection includes randomness.

        Args:
            position_group: 'DL', 'LB', or 'DB'
            available_players: All players at this position group (sorted by depth)
            slots_needed: How many players needed (from formation)

        Returns:
            List of players to put on field
        """
        if not available_players or slots_needed <= 0:
            return []

        # If we don't have enough players, use all available
        if len(available_players) <= slots_needed:
            return available_players[:slots_needed]

        config = self.position_configs.get(position_group)
        if not config:
            return available_players[:slots_needed]

        # Split into starters and backups based on depth chart
        starters = available_players[:slots_needed]
        backups = available_players[slots_needed:]

        # Initialize starter tracking if needed
        for player in starters:
            key = self._get_player_key(player)
            self._starter_keys[position_group].add(key)

        # Calculate current starter share
        total_snaps = self.position_group_snaps[position_group]
        if total_snaps == 0:
            # First snap - use starters
            return starters.copy()

        # Count snaps for starters
        starter_snaps = sum(
            self.snaps_by_player.get(self._get_player_key(p), 0)
            for p in starters
        )
        current_share = starter_snaps / total_snaps if total_snaps > 0 else 1.0

        # Determine if we should substitute
        deviation = current_share - config.starter_share
        selected = list(starters)

        # Hard enforcement: if deviation is too large, force correction
        if deviation > config.deviation_tolerance and backups:
            # Starters playing too much - substitute in a backup
            # Find the starter with most snaps to rest
            starter_snap_counts = [
                (i, self.snaps_by_player.get(self._get_player_key(p), 0))
                for i, p in enumerate(selected)
            ]
            # Sort by snap count descending
            starter_snap_counts.sort(key=lambda x: x[1], reverse=True)

            # Replace the most-used starter with the best backup
            most_used_idx = starter_snap_counts[0][0]
            selected[most_used_idx] = backups[0]

        elif deviation < -config.deviation_tolerance:
            # Starters not playing enough - keep all starters
            # (This is the default, so no change needed)
            pass

        else:
            # Within tolerance - use weighted random for one substitution
            # Probability of subbing based on how close to target
            sub_probability = 1.0 - config.starter_share

            if backups and random.random() < sub_probability * 0.3:
                # Small chance to sub in backup for variety
                # Replace the starter with lowest overall rating
                try:
                    lowest_rated_idx = min(
                        range(len(selected)),
                        key=lambda i: getattr(selected[i], 'overall',
                                            selected[i].get('overall', 75) if isinstance(selected[i], dict) else 75)
                    )
                    selected[lowest_rated_idx] = backups[0]
                except (AttributeError, KeyError):
                    pass  # If we can't determine ratings, keep starters

        return selected

    def record_snap(self, player, position_group: str = None) -> None:
        """
        Record a snap for workload tracking.

        Args:
            player: Player object who played the snap
            position_group: 'DL', 'LB', 'DB' (optional, will be determined from position)
        """
        player_key = self._get_player_key(player)
        self.snaps_by_player[player_key] = self.snaps_by_player.get(player_key, 0) + 1

        # Determine position group if not provided
        if position_group is None:
            position = getattr(player, 'primary_position', None)
            if position is None and isinstance(player, dict):
                position = player.get('primary_position', '')
            position_group = self.get_position_group(position or '')

        if position_group and position_group in self.position_group_snaps:
            self.position_group_snaps[position_group] += 1

    def record_snaps_for_players(self, players: List) -> None:
        """
        Record snaps for multiple players at once.

        Args:
            players: List of Player objects who played the snap
        """
        for player in players:
            self.record_snap(player)

    def get_snap_distribution(self) -> Dict[str, Dict[str, any]]:
        """
        Get current snap distribution summary.

        Returns:
            Dictionary with per-group statistics
        """
        result = {}

        for group in ['DL', 'LB', 'DB']:
            total = self.position_group_snaps[group]
            starter_keys = self._starter_keys[group]
            starter_snaps = sum(
                self.snaps_by_player.get(key, 0)
                for key in starter_keys
            )

            result[group] = {
                'total_snaps': total,
                'starter_snaps': starter_snaps,
                'starter_share': starter_snaps / total if total > 0 else 0.0,
                'target_share': self.position_configs[group].starter_share
            }

        return result

    def reset(self) -> None:
        """Reset all tracking for a new game."""
        self.snaps_by_player.clear()
        self.position_group_snaps = {'DL': 0, 'LB': 0, 'DB': 0}
        self._starter_keys = {'DL': set(), 'LB': set(), 'DB': set()}

    def __repr__(self) -> str:
        total = sum(self.position_group_snaps.values())
        return (
            f"DefensiveRotationManager("
            f"DL={self.position_configs['DL'].starter_share:.0%}, "
            f"LB={self.position_configs['LB'].starter_share:.0%}, "
            f"DB={self.position_configs['DB'].starter_share:.0%}, "
            f"total_snaps={total})"
        )
