"""
Statistical Ranking Utilities for The Owner's Sim

Calculate league, conference, and division rankings for players and teams.
"""
from typing import List, Dict, Any
from team_management.teams.team_loader import get_team_by_id


def calculate_rankings(
    stats: List[Dict[str, Any]],
    stat_key: str,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Calculate league-wide rankings for a specific stat.

    Args:
        stats: List of player/team stat dictionaries
        stat_key: Key to rank by (e.g., 'total_passing_yards', 'passer_rating')
        ascending: If True, rank lowest first (for INTs, sacks allowed, etc.)
                   If False, rank highest first (for yards, TDs, etc.)

    Returns:
        Same list with 'league_rank' field added (1st, 2nd, 3rd, etc.)

    Notes:
        - Handles ties: Players with same stat get same rank
        - Next rank skips tied players (e.g., two 1st place = next is 3rd)
        - Returns sorted by rank
    """
    if not stats:
        return []

    # Sort by stat_key (ascending or descending)
    sorted_stats = sorted(
        stats,
        key=lambda x: x.get(stat_key, 0),
        reverse=not ascending
    )

    # Assign ranks handling ties
    current_rank = 1
    previous_value = None
    players_at_current_rank = 0

    for i, player in enumerate(sorted_stats):
        stat_value = player.get(stat_key, 0)

        if previous_value is not None and stat_value == previous_value:
            # Same stat as previous player - same rank
            player['league_rank'] = current_rank
            players_at_current_rank += 1
        else:
            # Different stat - new rank
            if players_at_current_rank > 0:
                # Skip ranks for tied players
                current_rank += players_at_current_rank
                players_at_current_rank = 1
            else:
                # First player or no ties
                current_rank = i + 1
                players_at_current_rank = 1
            player['league_rank'] = current_rank

        previous_value = stat_value

    return sorted_stats


def calculate_conference_rankings(
    stats: List[Dict[str, Any]],
    stat_key: str,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Calculate conference rankings (AFC and NFC separately).

    Args:
        stats: List of player stat dictionaries (must have 'team_id')
        stat_key: Key to rank by
        ascending: Ranking order

    Returns:
        Same list with 'conference_rank' field added

    Notes:
        - AFC players ranked 1-N within AFC
        - NFC players ranked 1-N within NFC
    """
    if not stats:
        return []

    # Split by conference
    afc_players = []
    nfc_players = []

    for player in stats:
        team_id = player.get('team_id')
        if team_id is None:
            continue

        team = get_team_by_id(team_id)
        if team.conference == 'AFC':
            afc_players.append(player)
        elif team.conference == 'NFC':
            nfc_players.append(player)

    # Rank each conference separately
    def rank_conference(players: List[Dict[str, Any]], rank_field: str):
        if not players:
            return

        sorted_players = sorted(
            players,
            key=lambda x: x.get(stat_key, 0),
            reverse=not ascending
        )

        current_rank = 1
        previous_value = None
        players_at_current_rank = 0

        for i, player in enumerate(sorted_players):
            stat_value = player.get(stat_key, 0)

            if previous_value is not None and stat_value == previous_value:
                player[rank_field] = current_rank
                players_at_current_rank += 1
            else:
                if players_at_current_rank > 0:
                    current_rank += players_at_current_rank
                    players_at_current_rank = 1
                else:
                    current_rank = i + 1
                    players_at_current_rank = 1
                player[rank_field] = current_rank

            previous_value = stat_value

    rank_conference(afc_players, 'conference_rank')
    rank_conference(nfc_players, 'conference_rank')

    return stats


def calculate_division_rankings(
    stats: List[Dict[str, Any]],
    stat_key: str,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Calculate division rankings (8 divisions separately).

    Args:
        stats: List of player stat dictionaries (must have 'team_id')
        stat_key: Key to rank by
        ascending: Ranking order

    Returns:
        Same list with 'division_rank' field added

    Notes:
        - Each division (AFC East, NFC North, etc.) ranked 1-N
    """
    if not stats:
        return []

    # Split by division
    divisions = {}

    for player in stats:
        team_id = player.get('team_id')
        if team_id is None:
            continue

        team = get_team_by_id(team_id)
        division = team.division

        if division not in divisions:
            divisions[division] = []
        divisions[division].append(player)

    # Rank each division separately
    for division, players in divisions.items():
        if not players:
            continue

        sorted_players = sorted(
            players,
            key=lambda x: x.get(stat_key, 0),
            reverse=not ascending
        )

        current_rank = 1
        previous_value = None
        players_at_current_rank = 0

        for i, player in enumerate(sorted_players):
            stat_value = player.get(stat_key, 0)

            if previous_value is not None and stat_value == previous_value:
                player['division_rank'] = current_rank
                players_at_current_rank += 1
            else:
                if players_at_current_rank > 0:
                    current_rank += players_at_current_rank
                    players_at_current_rank = 1
                else:
                    current_rank = i + 1
                    players_at_current_rank = 1
                player['division_rank'] = current_rank

            previous_value = stat_value

    return stats


def get_percentile(player_stat: float, all_stats: List[float]) -> float:
    """
    Calculate percentile for a player's stat (0-100).

    Args:
        player_stat: Player's stat value
        all_stats: All player stat values in population

    Returns:
        Percentile (0.0 to 100.0)

    Example:
        Player with 4000 yards in [3000, 3500, 4000, 4500, 5000]
        Returns: 60.0 (better than 60% of players)
    """
    if not all_stats:
        return 0.0

    # Count how many players are below this stat
    count_below = sum(1 for stat in all_stats if stat < player_stat)

    # Calculate percentile
    total = len(all_stats)
    percentile = (count_below / total) * 100.0

    return percentile


def add_all_rankings(
    stats: List[Dict[str, Any]],
    stat_key: str,
    ascending: bool = False
) -> List[Dict[str, Any]]:
    """
    Add all ranking types (league, conference, division) in one call.

    Args:
        stats: List of player stat dictionaries
        stat_key: Key to rank by
        ascending: Ranking order

    Returns:
        Same list with 'league_rank', 'conference_rank', 'division_rank' added
    """
    if not stats:
        return []

    # Call all ranking functions
    stats = calculate_rankings(stats, stat_key, ascending)
    stats = calculate_conference_rankings(stats, stat_key, ascending)
    stats = calculate_division_rankings(stats, stat_key, ascending)

    return stats
