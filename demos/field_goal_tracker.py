"""
Field Goal Tracker - Extract and categorize field goal attempts by distance

This module provides a helper class to track individual field goal attempts
from game results, extracting distances from play-by-play data and categorizing
them into NFL standard ranges for benchmark validation.
"""

from typing import List, Dict, Tuple


class FieldGoalTracker:
    """
    Tracks individual field goal attempts with distances.

    Extracts FG data from game drive results and PlayStatsSummary objects,
    allowing accurate categorization by distance range for NFL benchmark
    validation.
    """

    def __init__(self):
        """Initialize empty attempts list."""
        self.attempts: List[Dict] = []  # List[Dict] with distance, made, team_id

    def track_game(self, game_result) -> None:
        """
        Extract field goal data from game drives.

        Iterates through all drives and plays in the game result, extracting
        field goal distance and outcome from PlayStatsSummary objects.

        Args:
            game_result: GameResult object with drive_results attribute
        """
        if not hasattr(game_result, 'drive_results'):
            return

        for drive in game_result.drive_results:
            for play in drive.plays:
                # Check if this is a field goal play
                if play.play_type == 'field_goal':
                    # Extract from PlayStatsSummary
                    summary = play.player_stats_summary
                    if summary:
                        distance = getattr(summary, 'field_goal_distance', None)
                        outcome = getattr(summary, 'field_goal_outcome', None)

                        if distance and outcome:
                            self.attempts.append({
                                'distance': distance,
                                'made': outcome == 'made',
                                'team_id': drive.possessing_team_id
                            })

    def get_by_range(self, min_dist: int, max_dist: int) -> Tuple[int, int]:
        """
        Get attempts and makes for a specific distance range.

        Args:
            min_dist: Minimum distance (inclusive)
            max_dist: Maximum distance (inclusive)

        Returns:
            Tuple of (attempts, made) for the distance range
        """
        filtered = [a for a in self.attempts
                   if min_dist <= a['distance'] <= max_dist]
        attempts = len(filtered)
        made = sum(1 for a in filtered if a['made'])
        return attempts, made

    def get_total_stats(self) -> Tuple[int, int]:
        """
        Get total field goal attempts and makes across all distances.

        Returns:
            Tuple of (total_attempts, total_made)
        """
        return len(self.attempts), sum(1 for a in self.attempts if a['made'])

    def get_accuracy_by_range(self, min_dist: int, max_dist: int) -> float:
        """
        Calculate accuracy percentage for a distance range.

        Args:
            min_dist: Minimum distance (inclusive)
            max_dist: Maximum distance (inclusive)

        Returns:
            Accuracy percentage (0-100), or 0.0 if no attempts
        """
        attempts, made = self.get_by_range(min_dist, max_dist)
        return (made / attempts * 100) if attempts > 0 else 0.0
