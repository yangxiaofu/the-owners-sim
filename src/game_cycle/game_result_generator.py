"""
Instant game result generator for game_cycle.

Generates random but realistic NFL scores without full simulation.
"""

import random
from typing import Tuple


def generate_instant_result(
    home_team_id: int,
    away_team_id: int,
    is_playoff: bool = False
) -> Tuple[int, int]:
    """
    Generate random realistic NFL scores instantly.

    Args:
        home_team_id: Home team ID (not used in random generation, but available for future)
        away_team_id: Away team ID (not used in random generation, but available for future)
        is_playoff: If True, uses tighter score ranges (playoff games are often closer)

    Returns:
        Tuple of (home_score, away_score)
    """
    if is_playoff:
        # Playoff games tend to be closer
        base_score = random.randint(17, 28)
        spread = random.randint(-7, 7)
        home_advantage = random.randint(0, 3)  # Slight home advantage

        home_score = max(3, base_score + home_advantage)
        away_score = max(3, base_score - spread)
    else:
        # Regular season - wider range
        # NFL scores typically range from 10-40 with occasional outliers
        home_base = random.randint(14, 31)
        away_base = random.randint(10, 28)

        # Home field advantage: +3 points on average
        home_advantage = random.randint(0, 6)
        home_score = home_base + home_advantage
        away_score = away_base

    # Ensure no ties in playoffs
    if is_playoff and home_score == away_score:
        # Random overtime winner
        if random.random() > 0.5:
            home_score += 3  # Field goal
        else:
            away_score += 3

    # Ensure scores are realistic (divisible by common scoring plays)
    # NFL scores are usually 0, 2, 3, 6, 7, 9, 10, 13, 14, etc.
    # For simplicity, we'll allow any score but favor multiples of 7 and 3
    home_score = _adjust_to_realistic_score(home_score)
    away_score = _adjust_to_realistic_score(away_score)

    # Final tie check for playoffs
    if is_playoff and home_score == away_score:
        home_score += 7  # TD wins it

    return home_score, away_score


def _adjust_to_realistic_score(score: int) -> int:
    """
    Adjust score to be more realistic.

    NFL scores are typically achieved through combinations of:
    - Touchdown + PAT: 7 points
    - Touchdown + 2pt: 8 points
    - Field Goal: 3 points
    - Safety: 2 points

    Common scores: 0, 3, 6, 7, 9, 10, 13, 14, 16, 17, 20, 21, 23, 24, 27, 28, 30, 31, etc.
    """
    # Most common realistic scores
    realistic_scores = [
        0, 3, 6, 7, 9, 10, 12, 13, 14, 16, 17, 19, 20, 21, 23, 24,
        26, 27, 28, 30, 31, 33, 34, 35, 37, 38, 40, 41, 42, 44, 45
    ]

    # Find closest realistic score
    closest = min(realistic_scores, key=lambda x: abs(x - score))
    return closest


def generate_blowout() -> Tuple[int, int]:
    """Generate a blowout game result (rare but happens)."""
    winner_score = random.randint(35, 52)
    loser_score = random.randint(3, 14)

    winner_score = _adjust_to_realistic_score(winner_score)
    loser_score = _adjust_to_realistic_score(loser_score)

    # Random home/away for winner
    if random.random() > 0.5:
        return winner_score, loser_score
    else:
        return loser_score, winner_score


def generate_close_game() -> Tuple[int, int]:
    """Generate a close/competitive game result."""
    base = random.randint(20, 30)
    spread = random.randint(0, 3)

    home_score = _adjust_to_realistic_score(base + spread)
    away_score = _adjust_to_realistic_score(base - spread)

    return home_score, away_score
