"""
Playoff Constants

Constants specific to NFL playoff structure, rounds, and tournament progression.
"""

from enum import Enum
from typing import Dict, List, Tuple

# Playoff Structure Constants
PLAYOFF_TEAMS_PER_CONFERENCE = 7
DIVISION_WINNERS_PER_CONFERENCE = 4
WILD_CARD_TEAMS_PER_CONFERENCE = 3
TEAMS_WITH_BYES = 2  # One per conference (#1 seeds)

# Total playoff teams
TOTAL_PLAYOFF_TEAMS = PLAYOFF_TEAMS_PER_CONFERENCE * 2  # 14 total


class PlayoffRound(Enum):
    """NFL Playoff round definitions"""
    WILD_CARD = "Wild Card"
    DIVISIONAL = "Divisional"
    CONFERENCE_CHAMPIONSHIP = "Conference Championship"
    SUPER_BOWL = "Super Bowl"


# Playoff round progression
PLAYOFF_ROUNDS = [
    PlayoffRound.WILD_CARD,
    PlayoffRound.DIVISIONAL,
    PlayoffRound.CONFERENCE_CHAMPIONSHIP,
    PlayoffRound.SUPER_BOWL
]

# Games per round
GAMES_PER_ROUND = {
    PlayoffRound.WILD_CARD: 6,              # 3 AFC + 3 NFC
    PlayoffRound.DIVISIONAL: 4,             # 2 AFC + 2 NFC
    PlayoffRound.CONFERENCE_CHAMPIONSHIP: 2,  # 1 AFC + 1 NFC
    PlayoffRound.SUPER_BOWL: 1              # 1 final game
}

# Teams advancing from each round
TEAMS_ADVANCING_PER_CONFERENCE = {
    PlayoffRound.WILD_CARD: 4,              # 4 teams per conference advance
    PlayoffRound.DIVISIONAL: 2,             # 2 teams per conference advance
    PlayoffRound.CONFERENCE_CHAMPIONSHIP: 1, # 1 team per conference advances
    PlayoffRound.SUPER_BOWL: 1              # 1 overall champion
}

# Wild Card round matchup structure
# Format: (higher_seed, lower_seed)
WILD_CARD_MATCHUPS = [
    (2, 7),  # 2 seed vs 7 seed
    (3, 6),  # 3 seed vs 6 seed
    (4, 5)   # 4 seed vs 5 seed
]

# Seeds that get first round byes
FIRST_ROUND_BYE_SEEDS = [1]  # Only #1 seeds get byes

# Playoff seeding ranges
DIVISION_WINNER_SEEDS = list(range(1, 5))      # Seeds 1-4
WILD_CARD_SEEDS = list(range(5, 8))            # Seeds 5-7

# Tournament bracket structure
class BracketStructure:
    """Defines how teams advance through the tournament bracket"""

    @staticmethod
    def get_divisional_matchups(wild_card_winners: List[int], conference: str) -> List[Tuple[int, int]]:
        """
        Generate divisional round matchups based on wild card winners.

        Args:
            wild_card_winners: List of team IDs that won wild card games
            conference: 'AFC' or 'NFC'

        Returns:
            List of (higher_seed_team_id, lower_seed_team_id) tuples
        """
        # #1 seed always plays lowest remaining seed
        # Remaining two teams play each other
        # This is a simplified version - actual implementation would need
        # to consider the specific seeding of wild card winners
        return []  # Implementation depends on actual seeding

    @staticmethod
    def get_conference_championship_matchup(divisional_winners: List[int]) -> Tuple[int, int]:
        """
        Generate conference championship matchup.

        Args:
            divisional_winners: List of 2 team IDs that won divisional games

        Returns:
            Tuple of (higher_seed_team_id, lower_seed_team_id)
        """
        if len(divisional_winners) != 2:
            raise ValueError("Conference championship requires exactly 2 teams")

        # Higher seed hosts (would need actual seeding info to determine)
        return tuple(divisional_winners)


# Playoff timing constants (in days from Wild Card weekend)
PLAYOFF_SCHEDULE_TIMING = {
    PlayoffRound.WILD_CARD: 0,              # Week 0 (reference point)
    PlayoffRound.DIVISIONAL: 7,             # 1 week later
    PlayoffRound.CONFERENCE_CHAMPIONSHIP: 14, # 2 weeks later
    PlayoffRound.SUPER_BOWL: 28             # 4 weeks later (2 week gap)
}

# Home field advantage rules
HOME_FIELD_RULES = {
    PlayoffRound.WILD_CARD: "higher_seed",
    PlayoffRound.DIVISIONAL: "higher_seed",
    PlayoffRound.CONFERENCE_CHAMPIONSHIP: "higher_seed",
    PlayoffRound.SUPER_BOWL: "neutral_site"
}

# Tiebreaker application order for playoff seeding
DIVISION_TIEBREAKER_ORDER = [
    "head_to_head",
    "division_record",
    "conference_record",
    "common_games",
    "strength_of_victory",
    "strength_of_schedule",
    "combined_ranking",
    "net_points_conference",
    "net_points_all",
    "coin_flip"
]

WILD_CARD_TIEBREAKER_ORDER = [
    "head_to_head",
    "conference_record",
    "common_games",
    "strength_of_victory",
    "strength_of_schedule",
    "combined_ranking",
    "net_points_conference",
    "net_points_all",
    "coin_flip"
]


def get_round_name(round_enum: PlayoffRound) -> str:
    """Get display name for a playoff round."""
    return round_enum.value


def get_next_round(current_round: PlayoffRound) -> PlayoffRound:
    """
    Get the next round after the current round.

    Args:
        current_round: Current playoff round

    Returns:
        Next playoff round

    Raises:
        ValueError: If current round is Super Bowl (no next round)
    """
    round_index = PLAYOFF_ROUNDS.index(current_round)
    if round_index >= len(PLAYOFF_ROUNDS) - 1:
        raise ValueError("Super Bowl is the final round")

    return PLAYOFF_ROUNDS[round_index + 1]


def is_final_round(round_enum: PlayoffRound) -> bool:
    """Check if this is the final playoff round."""
    return round_enum == PlayoffRound.SUPER_BOWL


def requires_neutral_site(round_enum: PlayoffRound) -> bool:
    """Check if this round is played at a neutral site."""
    return HOME_FIELD_RULES[round_enum] == "neutral_site"


def get_seeds_in_round(round_enum: PlayoffRound) -> List[int]:
    """
    Get the possible seeds that could be playing in a given round.

    Args:
        round_enum: Playoff round

    Returns:
        List of possible seed numbers
    """
    if round_enum == PlayoffRound.WILD_CARD:
        return [2, 3, 4, 5, 6, 7]  # #1 seeds have byes
    elif round_enum == PlayoffRound.DIVISIONAL:
        return [1, 2, 3, 4, 5, 6, 7]  # All seeds possible
    elif round_enum == PlayoffRound.CONFERENCE_CHAMPIONSHIP:
        return [1, 2, 3, 4, 5, 6, 7]  # All seeds possible
    elif round_enum == PlayoffRound.SUPER_BOWL:
        return [1, 2, 3, 4, 5, 6, 7]  # All seeds possible
    else:
        return []