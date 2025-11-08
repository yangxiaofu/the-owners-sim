"""
Playoff Helper Functions

Simple utility functions for extracting playoff results and champions.

These helpers were extracted from SeasonCycleController to simplify
statistics archival and reduce inline complexity.
"""

from typing import Tuple, Optional


def extract_playoff_champions(playoff_controller) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract AFC and NFC champion team IDs from playoff results.

    Args:
        playoff_controller: PlayoffController instance with completed conference championships

    Returns:
        Tuple of (afc_champion_id, nfc_champion_id)
        Returns (None, None) if conference championship results unavailable
    """
    afc_champion_id = None
    nfc_champion_id = None

    # Get conference championship results
    conference_games = playoff_controller.get_round_games('conference_championship')
    for game in conference_games:
        winner_id = game.get('winner_id')
        # Determine conference by team ID (AFC: 1-16, NFC: 17-32)
        if winner_id:
            if 1 <= winner_id <= 16:
                afc_champion_id = winner_id
            elif 17 <= winner_id <= 32:
                nfc_champion_id = winner_id

    return afc_champion_id, nfc_champion_id
