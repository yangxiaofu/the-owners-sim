"""
Base Play Simulator - Shared functionality for all play simulators.

Provides common helper methods used by RunPlaySimulator, PassPlaySimulator,
and other play type simulators. Consolidates duplicate code for:
- Player finding by position
- Snap tracking for all players on field
- Touchdown detection
- Player stats validation

Part of play engine refactoring to reduce code duplication.
"""

from typing import List, Optional, Tuple
from .stats import PlayerStats, create_player_stats_from_player


class BasePlaySimulator:
    """
    Base class providing shared functionality for play simulators.

    Subclasses should set these attributes in __init__:
    - offensive_players: List of offensive Player objects
    - defensive_players: List of defensive Player objects
    - offensive_formation: Offensive formation string
    - defensive_formation: Defensive formation string
    - offensive_team_id: Team ID of offensive team (1-32)
    - defensive_team_id: Team ID of defensive team (1-32)
    """

    # Subclasses must set these
    offensive_players: List = None
    defensive_players: List = None
    offensive_formation: str = None
    defensive_formation: str = None
    offensive_team_id: int = None
    defensive_team_id: int = None
    field_position: int = 50

    # ============================================
    # Player Finding Methods
    # ============================================

    def _find_player_by_position(self, position: str):
        """
        Find player with specified position from offensive players.

        Args:
            position: Position string to search for

        Returns:
            Player object or None if not found

        Note:
            Subclasses may override this to add position-specific logic
            (e.g., RunPlaySimulator handles RB rotation with selected_ball_carrier)
        """
        # Default: find first matching player
        for player in self.offensive_players:
            if player.primary_position == position:
                return player
        return None

    def _find_players_by_positions(self, positions: List[str]) -> List:
        """
        Find all offensive players matching specified positions.

        Args:
            positions: List of position strings to match

        Returns:
            List of matching Player objects
        """
        found_players = []
        for player in self.offensive_players:
            if player.primary_position in positions:
                found_players.append(player)
        return found_players

    def _find_defensive_players_by_positions(self, positions: List[str]) -> List:
        """
        Find all defensive players matching specified positions.

        Args:
            positions: List of position strings to match

        Returns:
            List of matching Player objects
        """
        found_players = []
        for player in self.defensive_players:
            if player.primary_position in positions:
                found_players.append(player)
        return found_players

    # ============================================
    # Snap Tracking
    # ============================================

    def _track_snaps_for_all_players(self, player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Track snaps for the 22 players on the field during this play.

        Uses formation-based personnel requirements to determine how many players
        of each position should get snaps. This ensures realistic snap distribution
        (e.g., only 1 RB gets snaps in most formations, not all RBs on roster).

        Supports position aliases so generic positions (e.g., 'linebacker') can
        fill specific formation slots (e.g., 'mike_linebacker').

        Args:
            player_stats: List of PlayerStats objects (may be empty or contain
                         only players with statistical attribution)

        Returns:
            Updated list of PlayerStats objects ensuring proper snap tracking

        Raises:
            ValueError: If offensive or defensive formation is not found in personnel requirements
        """
        from play_engine.mechanics.formations import OffensiveFormation, DefensiveFormation
        from constants.position_abbreviations import get_position_limit_with_aliases

        # Get personnel requirements from formation - fail loudly if not found
        off_personnel = OffensiveFormation.get_personnel_requirements(self.offensive_formation)
        if not off_personnel:
            raise ValueError(f"Unknown offensive formation: '{self.offensive_formation}'. "
                           f"Add personnel requirements to OffensiveFormation.get_personnel_requirements()")

        def_personnel = DefensiveFormation.get_personnel_requirements(self.defensive_formation)
        if not def_personnel:
            raise ValueError(f"Unknown defensive formation: '{self.defensive_formation}'. "
                           f"Add personnel requirements to DefensiveFormation.get_personnel_requirements()")

        # Create a dictionary to track existing PlayerStats objects by player name
        existing_stats = {stats.player_name: stats for stats in player_stats}

        # Track how many players of each position we've added
        off_position_counts = {}
        def_position_counts = {}

        # Track offensive snaps based on formation personnel
        offensive_count = 0
        for player in self.offensive_players:
            if offensive_count >= 11:
                break  # Only 11 players on field

            position = getattr(player, 'primary_position', '')

            # Get the limit for this position from formation (with alias support)
            pos_limit, tracking_pos = get_position_limit_with_aliases(position, off_personnel, off_position_counts)

            # Check if we've already filled this position
            pos_count = off_position_counts.get(tracking_pos, 0)
            if pos_count >= pos_limit:
                continue  # Skip - formation doesn't use more of this position

            player_name = player.name
            if player_name in existing_stats:
                existing_stats[player_name].add_offensive_snap()
            else:
                new_stats = create_player_stats_from_player(player, team_id=self.offensive_team_id)
                new_stats.add_offensive_snap()
                existing_stats[player_name] = new_stats
                player_stats.append(new_stats)

            off_position_counts[tracking_pos] = pos_count + 1
            offensive_count += 1

        # Track defensive snaps based on formation personnel
        defensive_count = 0
        for player in self.defensive_players:
            if defensive_count >= 11:
                break

            position = getattr(player, 'primary_position', '')

            # Get the limit for this position from formation (with alias support)
            pos_limit, tracking_pos = get_position_limit_with_aliases(position, def_personnel, def_position_counts)

            # Check if we've already filled this position
            pos_count = def_position_counts.get(tracking_pos, 0)
            if pos_count >= pos_limit:
                continue  # Skip - formation doesn't use more of this position

            player_name = player.name
            if player_name in existing_stats:
                existing_stats[player_name].add_defensive_snap()
            else:
                new_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
                new_stats.add_defensive_snap()
                existing_stats[player_name] = new_stats
                player_stats.append(new_stats)

            def_position_counts[tracking_pos] = pos_count + 1
            defensive_count += 1

        return player_stats

    # ============================================
    # Touchdown Detection
    # ============================================

    def _detect_touchdown(
        self,
        original_yards: int,
        final_yards: int,
        play_negated: bool
    ) -> Tuple[int, int, bool]:
        """
        Detect if play resulted in a touchdown and calculate actual yards/points.

        Handles the case where original play reached end zone but penalty may
        have affected the outcome. Touchdowns generally stand even with penalties
        (penalty enforced on PAT/kickoff).

        Args:
            original_yards: Yards before penalty adjustment
            final_yards: Yards after penalty adjustment
            play_negated: Whether penalty negated the play entirely

        Returns:
            Tuple of (actual_yards, points_scored, is_touchdown)
        """
        # Check if ORIGINAL play reached end zone (penalties don't negate TDs in most cases)
        original_target = self.field_position + original_yards
        original_was_touchdown = original_target >= 100

        if original_was_touchdown and not play_negated:
            # TD stands - penalty will be enforced on PAT/kickoff
            actual_yards = 100 - self.field_position
            return actual_yards, 6, True

        # Non-TD play or play was negated by penalty - use penalty-adjusted yards
        target_yard_line = self.field_position + final_yards
        is_touchdown = target_yard_line >= 100

        if is_touchdown:
            actual_yards = 100 - self.field_position
            return actual_yards, 6, True

        return final_yards, 0, False

    # ============================================
    # Player Stats Validation
    # ============================================

    def _validate_player_stats(self, player_stats: List[PlayerStats]) -> None:
        """
        Validate that all player stats have correct team_id assignments.

        Prints warnings for any players with missing or invalid team IDs.
        This helps catch bugs in stats attribution logic.

        Args:
            player_stats: List of PlayerStats to validate
        """
        for stats in player_stats:
            if stats.team_id is None:
                print(f"[WARN] Player {stats.player_name} missing team_id!")
            elif (self.offensive_team_id and self.defensive_team_id and
                  stats.team_id not in [self.offensive_team_id, self.defensive_team_id]):
                print(f"[WARN] Player {stats.player_name} has invalid team_id {stats.team_id}! "
                      f"(Expected {self.offensive_team_id} or {self.defensive_team_id})")

    # ============================================
    # Special Teams Snap Tracking
    # ============================================

    def _track_special_teams_snaps_for_all_players(
        self,
        player_stats_dict: dict,
        kicking_team: List = None,
        return_team: List = None
    ) -> dict:
        """
        Track special teams snaps for ALL 22 players on the field during special teams plays.

        This is used by field goal, punt, kickoff, and extra point simulators to ensure
        all players on the field get proper snap attribution, not just those with
        statistical contributions (kicker, returner, etc.).

        Args:
            player_stats_dict: Dictionary mapping player names to PlayerStats objects
            kicking_team: List of kicking team Player objects (defaults to offensive_players)
            return_team: List of return team Player objects (defaults to defensive_players)

        Returns:
            Updated player_stats_dict with special teams snaps added
        """
        # Use instance players if not explicitly provided
        if kicking_team is None:
            kicking_team = self.offensive_players or []
        if return_team is None:
            return_team = self.defensive_players or []

        # Track special teams snaps for all 11 kicking team players
        for player in kicking_team:
            player_name = player.name
            if player_name in player_stats_dict:
                # Player already has stats object, just add the snap
                player_stats_dict[player_name].add_special_teams_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, team_id=self.offensive_team_id)
                new_stats.add_special_teams_snap()
                player_stats_dict[player_name] = new_stats

        # Track special teams snaps for all 11 return team players
        for player in return_team:
            player_name = player.name
            if player_name in player_stats_dict:
                # Player already has stats object, just add the snap
                player_stats_dict[player_name].add_special_teams_snap()
            else:
                # Create new PlayerStats object for this player
                new_stats = create_player_stats_from_player(player, team_id=self.defensive_team_id)
                new_stats.add_special_teams_snap()
                player_stats_dict[player_name] = new_stats

        return player_stats_dict

    # ============================================
    # Environmental Modifiers
    # ============================================

    def _get_environmental_modifier(
        self,
        weather_condition: str = None,
        kick_distance: int = 40
    ) -> float:
        """
        Get environmental modifier for kicking plays.

        Weather effects on kicks:
        - Rain: Wet ball affects grip (-5-12% depending on distance)
        - Snow: Visibility + wet ball (-8-20% depending on distance)
        - Heavy Wind: Major trajectory impact (-10-25% depending on distance)

        Longer kicks are MORE affected by weather (exponential scaling).

        Args:
            weather_condition: Weather condition string ("clear", "rain", "snow", "heavy_wind")
                              If None, uses self.weather_condition if available
            kick_distance: Distance of kick in yards (affects weather scaling)

        Returns:
            Environmental modifier (0.4-1.0, where 1.0 = no weather effect)
        """
        # Get weather condition from instance if not provided
        if weather_condition is None:
            weather_condition = getattr(self, 'weather_condition', 'clear')

        if weather_condition == "clear":
            return 1.0  # No weather effects

        # Distance scaling factor (longer kicks = more weather impact)
        # 20-yard kick: 0.5x effect, 40-yard: 1.0x, 60-yard: 1.5x
        distance_factor = 0.5 + (kick_distance - 20) / 40.0
        distance_factor = max(0.5, min(distance_factor, 2.0))  # Clamp to [0.5, 2.0]

        base_modifier = 1.0

        if weather_condition == "rain":
            # Wet ball reduces accuracy by 5-12% (scaled by distance)
            base_modifier = 1.0 - (0.08 * distance_factor)  # -4% to -16%

        elif weather_condition == "snow":
            # Visibility + wet ball reduces accuracy by 8-20%
            base_modifier = 1.0 - (0.12 * distance_factor)  # -6% to -24%

        elif weather_condition == "heavy_wind":
            # Wind affects trajectory dramatically
            base_modifier = 1.0 - (0.15 * distance_factor)  # -7.5% to -30%

        # Clamp to realistic range (weather can't make kicks impossible, but can be very hard)
        return max(base_modifier, 0.4)  # Min 40% of base accuracy

    # ============================================
    # Player Rating Utilities
    # ============================================

    def _get_player_rating_with_fallback(
        self,
        player,
        primary_attr: str,
        fallback_attr: str = 'overall',
        default: int = 75
    ) -> int:
        """
        Get player rating with fallback chain for missing attributes.

        This is useful for synthetic/test players that may not have all attributes
        defined, or for players where a specific attribute returns a low default.

        Fallback chain:
        1. Try primary_attr (e.g., 'accuracy')
        2. If <= 50 (likely default), try fallback_attr (e.g., 'overall')
        3. If still <= 50, return default value

        Args:
            player: Player object with get_rating method
            primary_attr: Primary attribute to check (e.g., 'accuracy', 'kicking_power')
            fallback_attr: Fallback attribute if primary is missing (default: 'overall')
            default: Default value if both attributes are missing (default: 75)

        Returns:
            Player rating (int, typically 50-99)
        """
        if not player or not hasattr(player, 'get_rating'):
            return default

        # Try primary attribute
        rating = player.get_rating(primary_attr)

        # If primary returns a low default (likely undefined), try fallback
        if rating <= 50:
            rating = player.get_rating(fallback_attr)

        # If still low, use the provided default
        if rating <= 50:
            rating = default

        return rating