"""
Playoff Bracket Data Models

Data structures for representing NFL playoff brackets and games.
"""

from dataclasses import dataclass
from typing import List, Optional

# Use try/except to handle both production and test imports
try:
    from calendar.date_models import Date
except ModuleNotFoundError:
    from src.calendar.date_models import Date


@dataclass
class PlayoffGame:
    """
    Represents a single playoff game with complete context.

    Contains all information needed to identify and schedule a playoff game,
    including teams, seeds, dates, and round information.
    """
    away_team_id: int           # Away team ID (1-32)
    home_team_id: int           # Home team ID (1-32)
    away_seed: int              # Away team's playoff seed (1-7)
    home_seed: int              # Home team's playoff seed (1-7)
    game_date: Date             # When game is scheduled
    round_name: str             # 'wild_card', 'divisional', 'conference', 'super_bowl'
    conference: Optional[str]   # 'AFC', 'NFC', or None for Super Bowl
    game_number: int            # Game within round (1-6 for wild card, etc.)
    week: int                   # Playoff week (1-4)
    season: int                 # Season year (e.g., 2024)

    def is_super_bowl(self) -> bool:
        """Check if this is the Super Bowl game."""
        return self.round_name == 'super_bowl'

    def is_conference_championship(self) -> bool:
        """Check if this is a conference championship game."""
        return self.round_name == 'conference'

    def is_divisional_round(self) -> bool:
        """Check if this is a divisional round game."""
        return self.round_name == 'divisional'

    def is_wild_card(self) -> bool:
        """Check if this is a wild card game."""
        return self.round_name == 'wild_card'

    @property
    def matchup_string(self) -> str:
        """Get matchup as string (e.g., '(2) Chiefs vs (7) Steelers')."""
        if self.conference:
            return f"({self.away_seed}) Team {self.away_team_id} @ ({self.home_seed}) Team {self.home_team_id}"
        return f"Team {self.away_team_id} @ Team {self.home_team_id}"

    @property
    def round_display_name(self) -> str:
        """Get display name for round."""
        display_names = {
            'wild_card': 'Wild Card',
            'divisional': 'Divisional Round',
            'conference': 'Conference Championship',
            'super_bowl': 'Super Bowl'
        }
        return display_names.get(self.round_name, self.round_name)


@dataclass
class PlayoffBracket:
    """
    Collection of playoff games for a specific round.

    Represents one round of the playoff bracket (wild card, divisional, etc.)
    with all scheduled games for that round.
    """
    round_name: str             # 'wild_card', 'divisional', 'conference', 'super_bowl'
    season: int                 # Season year (e.g., 2024)
    games: List[PlayoffGame]    # All games in this round
    start_date: Date            # First game date of the round

    def get_afc_games(self) -> List[PlayoffGame]:
        """Get all AFC games in this round."""
        return [g for g in self.games if g.conference == 'AFC']

    def get_nfc_games(self) -> List[PlayoffGame]:
        """Get all NFC games in this round."""
        return [g for g in self.games if g.conference == 'NFC']

    def get_super_bowl_game(self) -> Optional[PlayoffGame]:
        """Get Super Bowl game if this is the Super Bowl round."""
        if self.round_name == 'super_bowl' and self.games:
            return self.games[0]
        return None

    def get_game_count(self) -> int:
        """Get total number of games in this round."""
        return len(self.games)

    def is_wild_card(self) -> bool:
        """Check if this is the wild card round."""
        return self.round_name == 'wild_card'

    def is_divisional(self) -> bool:
        """Check if this is the divisional round."""
        return self.round_name == 'divisional'

    def is_conference_championship(self) -> bool:
        """Check if this is the conference championship round."""
        return self.round_name == 'conference'

    def is_super_bowl(self) -> bool:
        """Check if this is the Super Bowl."""
        return self.round_name == 'super_bowl'

    @property
    def expected_game_count(self) -> int:
        """Get expected number of games for this round."""
        expected_counts = {
            'wild_card': 6,      # 3 AFC + 3 NFC
            'divisional': 4,     # 2 AFC + 2 NFC
            'conference': 2,     # 1 AFC + 1 NFC
            'super_bowl': 1      # 1 game
        }
        return expected_counts.get(self.round_name, 0)

    def validate(self) -> bool:
        """
        Validate bracket structure.

        Returns:
            True if bracket is valid

        Raises:
            ValueError if bracket is invalid
        """
        # Check game count matches expected
        if len(self.games) != self.expected_game_count:
            raise ValueError(
                f"Expected {self.expected_game_count} games for {self.round_name}, "
                f"got {len(self.games)}"
            )

        # Check all games have same round name
        for game in self.games:
            if game.round_name != self.round_name:
                raise ValueError(
                    f"Game round_name '{game.round_name}' doesn't match "
                    f"bracket round_name '{self.round_name}'"
                )

        # Check conference distribution (except Super Bowl)
        if self.round_name != 'super_bowl':
            afc_count = len(self.get_afc_games())
            nfc_count = len(self.get_nfc_games())
            expected_per_conf = self.expected_game_count // 2

            if afc_count != expected_per_conf or nfc_count != expected_per_conf:
                raise ValueError(
                    f"Expected {expected_per_conf} games per conference, "
                    f"got AFC: {afc_count}, NFC: {nfc_count}"
                )

        return True
