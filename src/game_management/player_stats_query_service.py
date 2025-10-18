"""
Player Stats Query Service

Provides a clean, reusable API for querying player statistics from live game simulations.
Centralizes stats access patterns and supports filtering by team, position, and stat thresholds.
"""

from typing import List, Optional
from play_engine.simulation.stats import PlayerStats


class PlayerStatsQueryService:
    """
    Service for querying player statistics from live game simulations.

    Provides static methods for extracting and filtering player stats from
    FullGameSimulator instances. Designed for use in box scores, UI displays,
    and statistical analysis.

    Example Usage:
        >>> from game_management.player_stats_query_service import PlayerStatsQueryService
        >>>
        >>> # Get all live stats from a game
        >>> all_stats = PlayerStatsQueryService.get_live_stats(simulator)
        >>>
        >>> # Filter by team
        >>> team_stats = PlayerStatsQueryService.get_stats_by_team(all_stats, TeamIDs.DETROIT_LIONS)
        >>>
        >>> # Get quarterbacks only
        >>> qb_stats = PlayerStatsQueryService.get_quarterback_stats(team_stats)
    """

    @staticmethod
    def get_live_stats(game_simulator) -> List[PlayerStats]:
        """
        Extract all player statistics from a FullGameSimulator instance.

        Navigates the internal GameLoopController structure to access the
        PlayerStatsAccumulator and retrieve complete player statistics.

        Args:
            game_simulator: FullGameSimulator instance with completed game

        Returns:
            List of PlayerStats objects for all players with recorded stats

        Example:
            >>> all_stats = PlayerStatsQueryService.get_live_stats(simulator)
            >>> print(f"Found stats for {len(all_stats)} players")
        """
        # Access the game loop controller stored in the simulator
        game_loop_controller = game_simulator._game_loop_controller

        # Navigate to the stats aggregator
        stats_aggregator = game_loop_controller.stats_aggregator

        # Get all player stats from the PlayerStatsAccumulator
        all_player_stats = stats_aggregator.player_stats.get_all_players_with_stats()

        # DEBUG: Check if QB stats have interceptions before passing to persistence
        for stats in all_player_stats:
            if hasattr(stats, 'passing_attempts') and stats.passing_attempts > 0:
                ints_thrown = getattr(stats, 'interceptions_thrown', 0)
                if ints_thrown > 0:
                    print(f"🔴 INT DEBUG QueryService: {stats.player_name} has interceptions_thrown={ints_thrown} (being passed to persistence)")

        return all_player_stats

    @staticmethod
    def get_stats_by_team(player_stats: List[PlayerStats], team_id: int) -> List[PlayerStats]:
        """
        Filter player statistics to include only a specific team.

        Args:
            player_stats: List of PlayerStats objects to filter
            team_id: Numerical team ID (1-32) to filter by

        Returns:
            List of PlayerStats objects for the specified team

        Example:
            >>> from constants.team_ids import TeamIDs
            >>> lions_stats = PlayerStatsQueryService.get_stats_by_team(
            ...     all_stats, TeamIDs.DETROIT_LIONS
            ... )
        """
        team_stats = []
        for player_stat in player_stats:
            player_team_id = getattr(player_stat, 'team_id', None)
            if player_team_id == team_id:
                team_stats.append(player_stat)

        return team_stats

    @staticmethod
    def get_stats_by_position(player_stats: List[PlayerStats], position: str) -> List[PlayerStats]:
        """
        Filter player statistics by position.

        Args:
            player_stats: List of PlayerStats objects to filter
            position: Position code (e.g., "QB", "RB", "WR", "TE", "OL", "DL", "LB", "DB")

        Returns:
            List of PlayerStats objects for the specified position

        Example:
            >>> qb_stats = PlayerStatsQueryService.get_stats_by_position(all_stats, "QB")
        """
        position_stats = []
        for player_stat in player_stats:
            player_position = getattr(player_stat, 'position', None)
            if player_position == position:
                position_stats.append(player_stat)

        return position_stats

    @staticmethod
    def get_quarterback_stats(player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Get statistics for all quarterbacks (players with passing attempts).

        Convenience method for box score passing sections. Returns players
        who attempted at least one pass during the game.

        Args:
            player_stats: List of PlayerStats objects to filter

        Returns:
            List of PlayerStats objects for quarterbacks

        Example:
            >>> qbs = PlayerStatsQueryService.get_quarterback_stats(team_stats)
            >>> for qb in qbs:
            ...     print(f"{qb.player_name}: {qb.passing_completions}/{qb.passing_attempts}")
        """
        qb_stats = []
        for player_stat in player_stats:
            passing_attempts = getattr(player_stat, 'passing_attempts', 0)
            if passing_attempts > 0:
                qb_stats.append(player_stat)

        return qb_stats

    @staticmethod
    def get_rusher_stats(player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Get statistics for all rushers (players with rushing attempts).

        Convenience method for box score rushing sections. Returns players
        who carried the ball at least once during the game.

        Args:
            player_stats: List of PlayerStats objects to filter

        Returns:
            List of PlayerStats objects for rushers

        Example:
            >>> rushers = PlayerStatsQueryService.get_rusher_stats(team_stats)
            >>> for rusher in rushers:
            ...     print(f"{rusher.player_name}: {rusher.rushing_attempts} att, {rusher.rushing_yards} yds")
        """
        rusher_stats = []
        for player_stat in player_stats:
            rushing_attempts = getattr(player_stat, 'rushing_attempts', 0)
            if rushing_attempts > 0:
                rusher_stats.append(player_stat)

        return rusher_stats

    @staticmethod
    def get_receiver_stats(player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Get statistics for all receivers (players with targets).

        Convenience method for box score receiving sections. Returns players
        who were targeted at least once during the game.

        Args:
            player_stats: List[PlayerStats] objects to filter

        Returns:
            List of PlayerStats objects for receivers

        Example:
            >>> receivers = PlayerStatsQueryService.get_receiver_stats(team_stats)
            >>> for receiver in receivers:
            ...     print(f"{receiver.player_name}: {receiver.receptions}/{receiver.targets} for {receiver.receiving_yards} yds")
        """
        receiver_stats = []
        for player_stat in player_stats:
            targets = getattr(player_stat, 'targets', 0)
            if targets > 0:
                receiver_stats.append(player_stat)

        return receiver_stats

    @staticmethod
    def get_players_with_snaps(player_stats: List[PlayerStats]) -> List[PlayerStats]:
        """
        Get all players who participated in the game (played at least one snap).

        Returns players with any offensive snaps, defensive snaps, or total snaps > 0.
        Useful for comprehensive box scores showing all participating players.

        Args:
            player_stats: List of PlayerStats objects to filter

        Returns:
            List of PlayerStats objects for players who played

        Example:
            >>> participants = PlayerStatsQueryService.get_players_with_snaps(all_stats)
            >>> print(f"{len(participants)} players saw action")
        """
        players_with_snaps = []
        for player_stat in player_stats:
            offensive_snaps = getattr(player_stat, 'offensive_snaps', 0)
            defensive_snaps = getattr(player_stat, 'defensive_snaps', 0)
            total_snaps = getattr(player_stat, 'total_snaps', 0)

            if offensive_snaps > 0 or defensive_snaps > 0 or total_snaps > 0:
                players_with_snaps.append(player_stat)

        return players_with_snaps

    @staticmethod
    def get_top_performers(
        player_stats: List[PlayerStats],
        stat_attribute: str,
        limit: int = 5,
        minimum_threshold: Optional[int] = None
    ) -> List[PlayerStats]:
        """
        Get top performers by a specific statistical category.

        Args:
            player_stats: List of PlayerStats objects to analyze
            stat_attribute: Attribute name to sort by (e.g., "passing_yards", "rushing_yards")
            limit: Maximum number of players to return (default: 5)
            minimum_threshold: Optional minimum value for the stat to be included

        Returns:
            List of PlayerStats objects sorted by the specified stat (descending)

        Example:
            >>> # Get top 3 rushers with at least 5 carries
            >>> top_rushers = PlayerStatsQueryService.get_top_performers(
            ...     all_stats,
            ...     stat_attribute="rushing_yards",
            ...     limit=3,
            ...     minimum_threshold=5
            ... )
        """
        # Filter by minimum threshold if specified
        filtered_stats = player_stats
        if minimum_threshold is not None:
            filtered_stats = [
                ps for ps in player_stats
                if getattr(ps, stat_attribute, 0) >= minimum_threshold
            ]

        # Sort by the specified attribute (descending)
        sorted_stats = sorted(
            filtered_stats,
            key=lambda ps: getattr(ps, stat_attribute, 0),
            reverse=True
        )

        # Return top N performers
        return sorted_stats[:limit]
