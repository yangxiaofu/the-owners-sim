"""
Statistical Filtering Utilities for The Owner's Sim

Filter statistical data by conference, division, team, position, and more.
"""
from typing import List, Dict, Any

from team_management.teams.team_loader import get_team_by_id


class StatFilters:
    """Static methods for filtering statistical data"""

    @staticmethod
    def filter_by_conference(stats: List[Dict[str, Any]], conference: str) -> List[Dict[str, Any]]:
        """
        Filter stats by conference (AFC or NFC).

        Args:
            stats: List of player stat dictionaries (must have 'team_id' field)
            conference: Conference name ('AFC' or 'NFC')

        Returns:
            Filtered list of stats

        Raises:
            ValueError: If conference is not 'AFC' or 'NFC'
        """
        # Validate conference
        valid_conferences = ['AFC', 'NFC']
        if conference.upper() not in valid_conferences:
            raise ValueError(f"Invalid conference: {conference}. Must be one of {valid_conferences}")

        filtered = []
        for stat in stats:
            team_id = stat.get('team_id')
            if team_id is None:
                continue

            team = get_team_by_id(team_id)
            if team and team.conference.upper() == conference.upper():
                filtered.append(stat)

        return filtered

    @staticmethod
    def filter_by_division(stats: List[Dict[str, Any]], division: str) -> List[Dict[str, Any]]:
        """
        Filter stats by division (East, North, South, West).

        Args:
            stats: List of player stat dictionaries (must have 'team_id' field)
            division: Division name ('East', 'North', 'South', 'West')

        Returns:
            Filtered list of stats

        Raises:
            ValueError: If division is not valid
        """
        # Validate division
        valid_divisions = ['EAST', 'NORTH', 'SOUTH', 'WEST']
        if division.upper() not in valid_divisions:
            raise ValueError(f"Invalid division: {division}. Must be one of {valid_divisions}")

        filtered = []
        for stat in stats:
            team_id = stat.get('team_id')
            if team_id is None:
                continue

            team = get_team_by_id(team_id)
            if team and team.division.upper() == division.upper():
                filtered.append(stat)

        return filtered

    @staticmethod
    def filter_by_conference_division(stats: List[Dict[str, Any]], conference: str, division: str) -> List[Dict[str, Any]]:
        """
        Filter stats by specific conference division (e.g., 'AFC East', 'NFC North').

        Args:
            stats: List of player stat dictionaries (must have 'team_id' field)
            conference: Conference name ('AFC' or 'NFC')
            division: Division name ('East', 'North', 'South', 'West')

        Returns:
            Filtered list of stats

        Raises:
            ValueError: If conference or division is not valid
        """
        # Validate inputs using the individual validators
        valid_conferences = ['AFC', 'NFC']
        valid_divisions = ['EAST', 'NORTH', 'SOUTH', 'WEST']

        if conference.upper() not in valid_conferences:
            raise ValueError(f"Invalid conference: {conference}. Must be one of {valid_conferences}")
        if division.upper() not in valid_divisions:
            raise ValueError(f"Invalid division: {division}. Must be one of {valid_divisions}")

        filtered = []
        for stat in stats:
            team_id = stat.get('team_id')
            if team_id is None:
                continue

            team = get_team_by_id(team_id)
            if (team and
                team.conference.upper() == conference.upper() and
                team.division.upper() == division.upper()):
                filtered.append(stat)

        return filtered

    @staticmethod
    def filter_by_team(stats: List[Dict[str, Any]], team_id: int) -> List[Dict[str, Any]]:
        """
        Filter stats by team ID.

        Args:
            stats: List of player stat dictionaries (must have 'team_id' field)
            team_id: Numerical team ID (1-32)

        Returns:
            Filtered list of stats
        """
        return [stat for stat in stats if stat.get('team_id') == team_id]

    @staticmethod
    def filter_by_position(stats: List[Dict[str, Any]], positions: List[str]) -> List[Dict[str, Any]]:
        """
        Filter stats by position(s).

        Args:
            stats: List of player stat dictionaries (must have 'position' field)
            positions: List of positions to include (e.g., ['QB'], ['RB', 'WR', 'TE'])

        Returns:
            Filtered list of stats
        """
        if not positions:
            return []

        # Convert positions to uppercase for case-insensitive comparison
        positions_upper = [pos.upper() for pos in positions]

        filtered = []
        for stat in stats:
            position = stat.get('position')
            if position and position.upper() in positions_upper:
                filtered.append(stat)

        return filtered

    @staticmethod
    def filter_by_minimum(stats: List[Dict[str, Any]], stat_key: str, minimum: int) -> List[Dict[str, Any]]:
        """
        Filter stats by minimum value for a specific stat.

        Args:
            stats: List of player stat dictionaries
            stat_key: Key to check (e.g., 'attempts', 'games_played', 'total_attempts')
            minimum: Minimum value required

        Returns:
            Filtered list of stats where stat_key >= minimum

        Example:
            # Get only QBs with 100+ attempts
            filter_by_minimum(qb_stats, 'attempts', 100)
        """
        filtered = []
        for stat in stats:
            value = stat.get(stat_key)
            if value is not None and value >= minimum:
                filtered.append(stat)

        return filtered

    @staticmethod
    def filter_by_games_played(stats: List[Dict[str, Any]], minimum_games: int) -> List[Dict[str, Any]]:
        """
        Filter players who played at least minimum_games.

        Args:
            stats: List of player stat dictionaries (must have 'games' or 'games_played' field)
            minimum_games: Minimum number of games required

        Returns:
            Filtered list of stats
        """
        filtered = []
        for stat in stats:
            # Support both 'games' and 'games_played' field names
            games = stat.get('games') or stat.get('games_played')
            if games is not None and games >= minimum_games:
                filtered.append(stat)

        return filtered
