"""
Statistical Aggregation Utilities for The Owner's Sim

Aggregate player statistics by team, position, and league.
"""
from typing import List, Dict, Any
from team_management.teams.team_loader import get_team_by_id


def aggregate_team_stats(player_stats: List[Dict[str, Any]], team_id: int) -> Dict[str, Any]:
    """
    Aggregate all player stats for a specific team.

    Args:
        player_stats: List of all player stat dictionaries
        team_id: Team ID to aggregate

    Returns:
        Dict with team totals:
        {
            'team_id': int,
            'total_passing_yards': int,
            'total_passing_tds': int,
            'total_rushing_yards': int,
            'total_rushing_tds': int,
            'total_receiving_yards': int,
            'total_receiving_tds': int,
            'total_points_scored': int,  # Estimated from TDs
            'player_count': int,
            'games': int,  # Max games across all players
        }
    """
    # Filter by team_id
    team_players = [p for p in player_stats if p.get('team_id') == team_id]

    if not team_players:
        return {
            'team_id': team_id,
            'total_passing_yards': 0,
            'total_passing_tds': 0,
            'total_rushing_yards': 0,
            'total_rushing_tds': 0,
            'total_receiving_yards': 0,
            'total_receiving_tds': 0,
            'total_points_scored': 0,
            'player_count': 0,
            'games': 0,
        }

    # Sum all relevant stats
    total_passing_yards = sum(p.get('passing_yards', 0) for p in team_players)
    total_passing_tds = sum(p.get('passing_touchdowns', 0) for p in team_players)
    total_rushing_yards = sum(p.get('rushing_yards', 0) for p in team_players)
    total_rushing_tds = sum(p.get('rushing_touchdowns', 0) for p in team_players)
    total_receiving_yards = sum(p.get('receiving_yards', 0) for p in team_players)
    total_receiving_tds = sum(p.get('receiving_touchdowns', 0) for p in team_players)

    # Calculate total_points_scored from TDs (6 points each)
    total_points_scored = (total_passing_tds + total_rushing_tds + total_receiving_tds) * 6

    # Get max games across all players
    max_games = max(p.get('games', 0) for p in team_players)

    return {
        'team_id': team_id,
        'total_passing_yards': total_passing_yards,
        'total_passing_tds': total_passing_tds,
        'total_rushing_yards': total_rushing_yards,
        'total_rushing_tds': total_rushing_tds,
        'total_receiving_yards': total_receiving_yards,
        'total_receiving_tds': total_receiving_tds,
        'total_points_scored': total_points_scored,
        'player_count': len(team_players),
        'games': max_games,
    }


def aggregate_position_stats(player_stats: List[Dict[str, Any]], position: str) -> Dict[str, Any]:
    """
    Aggregate stats for all players at a specific position.

    Args:
        player_stats: List of all player stat dictionaries
        position: Position to aggregate (e.g., 'QB', 'RB', 'WR')

    Returns:
        Dict with position totals:
        {
            'position': str,
            'player_count': int,
            'total_yards': int,
            'total_touchdowns': int,
            'avg_yards_per_player': float,
            'avg_tds_per_player': float,
        }
    """
    # Filter by position
    position_players = [p for p in player_stats if p.get('position') == position]

    if not position_players:
        return {
            'position': position,
            'player_count': 0,
            'total_yards': 0,
            'total_touchdowns': 0,
            'avg_yards_per_player': 0.0,
            'avg_tds_per_player': 0.0,
        }

    # Sum all yards (passing, rushing, receiving)
    total_yards = sum(
        p.get('passing_yards', 0) + p.get('rushing_yards', 0) + p.get('receiving_yards', 0)
        for p in position_players
    )

    # Sum all touchdowns
    total_touchdowns = sum(
        p.get('passing_touchdowns', 0) + p.get('rushing_touchdowns', 0) + p.get('receiving_touchdowns', 0)
        for p in position_players
    )

    player_count = len(position_players)

    return {
        'position': position,
        'player_count': player_count,
        'total_yards': total_yards,
        'total_touchdowns': total_touchdowns,
        'avg_yards_per_player': total_yards / player_count,
        'avg_tds_per_player': total_touchdowns / player_count,
    }


def aggregate_conference_stats(player_stats: List[Dict[str, Any]], conference: str) -> Dict[str, Any]:
    """
    Aggregate stats for all players in a conference.

    Args:
        player_stats: List of all player stat dictionaries (must have team_id)
        conference: Conference name ('AFC' or 'NFC')

    Returns:
        Dict with conference totals:
        {
            'conference': str,
            'player_count': int,
            'total_passing_yards': int,
            'total_rushing_yards': int,
            'total_receiving_yards': int,
            'total_touchdowns': int,
        }
    """
    # Filter by conference using team_id
    conference_players = []
    for p in player_stats:
        team_id = p.get('team_id')
        if team_id:
            team = get_team_by_id(team_id)
            if team and team.conference == conference:
                conference_players.append(p)

    if not conference_players:
        return {
            'conference': conference,
            'player_count': 0,
            'total_passing_yards': 0,
            'total_rushing_yards': 0,
            'total_receiving_yards': 0,
            'total_touchdowns': 0,
        }

    # Sum all stats
    total_passing_yards = sum(p.get('passing_yards', 0) for p in conference_players)
    total_rushing_yards = sum(p.get('rushing_yards', 0) for p in conference_players)
    total_receiving_yards = sum(p.get('receiving_yards', 0) for p in conference_players)
    total_touchdowns = sum(
        p.get('passing_touchdowns', 0) + p.get('rushing_touchdowns', 0) + p.get('receiving_touchdowns', 0)
        for p in conference_players
    )

    return {
        'conference': conference,
        'player_count': len(conference_players),
        'total_passing_yards': total_passing_yards,
        'total_rushing_yards': total_rushing_yards,
        'total_receiving_yards': total_receiving_yards,
        'total_touchdowns': total_touchdowns,
    }


def calculate_league_averages(player_stats: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculate league-wide averages for all stats.

    Args:
        player_stats: List of all player stat dictionaries

    Returns:
        Dict with league averages:
        {
            'avg_passing_yards': float,
            'avg_rushing_yards': float,
            'avg_receiving_yards': float,
            'avg_touchdowns': float,
            'avg_games_played': float,
        }
    """
    if not player_stats:
        return {
            'avg_passing_yards': 0.0,
            'avg_rushing_yards': 0.0,
            'avg_receiving_yards': 0.0,
            'avg_touchdowns': 0.0,
            'avg_games_played': 0.0,
        }

    player_count = len(player_stats)

    avg_passing_yards = sum(p.get('passing_yards', 0) for p in player_stats) / player_count
    avg_rushing_yards = sum(p.get('rushing_yards', 0) for p in player_stats) / player_count
    avg_receiving_yards = sum(p.get('receiving_yards', 0) for p in player_stats) / player_count
    avg_touchdowns = sum(
        p.get('passing_touchdowns', 0) + p.get('rushing_touchdowns', 0) + p.get('receiving_touchdowns', 0)
        for p in player_stats
    ) / player_count
    avg_games_played = sum(p.get('games', 0) for p in player_stats) / player_count

    return {
        'avg_passing_yards': avg_passing_yards,
        'avg_rushing_yards': avg_rushing_yards,
        'avg_receiving_yards': avg_receiving_yards,
        'avg_touchdowns': avg_touchdowns,
        'avg_games_played': avg_games_played,
    }


def aggregate_all_teams(player_stats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregate stats for all 32 NFL teams.

    Args:
        player_stats: List of all player stat dictionaries

    Returns:
        List of 32 team aggregation dicts (one per team)
    """
    # Call aggregate_team_stats for each team_id (1-32)
    team_aggregations = []
    for team_id in range(1, 33):
        team_agg = aggregate_team_stats(player_stats, team_id)
        team_aggregations.append(team_agg)

    # Return list sorted by team_id (already sorted)
    return team_aggregations


def compare_teams(
    player_stats: List[Dict[str, Any]],
    team_id_1: int,
    team_id_2: int
) -> Dict[str, Any]:
    """
    Compare stats between two teams.

    Args:
        player_stats: List of all player stat dictionaries
        team_id_1: First team
        team_id_2: Second team

    Returns:
        Dict with comparison:
        {
            'team_1': Dict (team_id_1 aggregated stats),
            'team_2': Dict (team_id_2 aggregated stats),
            'differences': Dict (team_1 - team_2 for each stat),
        }
    """
    # Get aggregated stats for both teams
    team_1_stats = aggregate_team_stats(player_stats, team_id_1)
    team_2_stats = aggregate_team_stats(player_stats, team_id_2)

    # Calculate differences (team_1 - team_2)
    differences = {
        'total_passing_yards': team_1_stats['total_passing_yards'] - team_2_stats['total_passing_yards'],
        'total_passing_tds': team_1_stats['total_passing_tds'] - team_2_stats['total_passing_tds'],
        'total_rushing_yards': team_1_stats['total_rushing_yards'] - team_2_stats['total_rushing_yards'],
        'total_rushing_tds': team_1_stats['total_rushing_tds'] - team_2_stats['total_rushing_tds'],
        'total_receiving_yards': team_1_stats['total_receiving_yards'] - team_2_stats['total_receiving_yards'],
        'total_receiving_tds': team_1_stats['total_receiving_tds'] - team_2_stats['total_receiving_tds'],
        'total_points_scored': team_1_stats['total_points_scored'] - team_2_stats['total_points_scored'],
        'player_count': team_1_stats['player_count'] - team_2_stats['player_count'],
        'games': team_1_stats['games'] - team_2_stats['games'],
    }

    return {
        'team_1': team_1_stats,
        'team_2': team_2_stats,
        'differences': differences,
    }
