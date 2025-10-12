"""
Playoff State Management

This module provides the PlayoffState class for managing playoff tournament state,
including round progression, game completion tracking, and bracket management.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from calendar.date_models import Date
from playoff_system.seeding_models import PlayoffSeeding
from playoff_system.bracket_models import PlayoffBracket


@dataclass
class PlayoffState:
    """
    Manages the state of an ongoing playoff tournament.

    This class tracks all aspects of playoff progression including:
    - Current round (wild_card, divisional, conference, super_bowl)
    - Original seeding configuration
    - Completed games for each round
    - Bracket state for AFC and NFC
    - Simulation progress (games played, days simulated)
    - Current simulation date

    Attributes:
        current_round: The current playoff round being played
        original_seeding: The initial playoff seeding configuration
        completed_games: Dictionary mapping round names to lists of completed game results
        brackets: Dictionary mapping conference names ('AFC', 'NFC') to their brackets
        total_games_played: Total number of playoff games completed
        total_days_simulated: Total number of simulation days advanced
        current_date: The current date in the simulation (for validation)
    """

    current_round: str = 'wild_card'
    original_seeding: Optional[PlayoffSeeding] = None
    completed_games: Dict[str, List[Dict]] = field(default_factory=lambda: {
        'wild_card': [],
        'divisional': [],
        'conference': [],
        'super_bowl': []
    })
    brackets: Dict[str, Optional[PlayoffBracket]] = field(default_factory=lambda: {
        'wild_card': None,
        'divisional': None,
        'conference': None,
        'super_bowl': None
    })
    total_games_played: int = 0
    total_days_simulated: int = 0
    current_date: Optional[Date] = None

    def is_round_complete(self, round_name: str) -> bool:
        """
        Check if a specific playoff round has been completed.

        A round is considered complete when the number of completed games
        matches the expected game count for that round:
        - wild_card: 6 games
        - divisional: 4 games
        - conference: 2 games
        - super_bowl: 1 game

        Args:
            round_name: The name of the round to check ('wild_card', 'divisional',
                       'conference', or 'super_bowl')

        Returns:
            True if the round has the expected number of completed games, False otherwise
        """
        if round_name not in self.completed_games:
            return False

        expected_count = self._get_expected_game_count(round_name)
        actual_count = len(self.completed_games[round_name])

        return actual_count >= expected_count

    def get_active_round(self) -> str:
        """
        Determine which playoff round is currently active.

        This method checks round completion status to determine the current
        active round. The logic follows NFL playoff progression:
        1. Start with wild_card round
        2. Once wild_card is complete, move to divisional
        3. Once divisional is complete, move to conference
        4. Once conference is complete, move to super_bowl
        5. Once super_bowl is complete, playoffs are over

        Returns:
            The name of the currently active round, or 'complete' if all
            playoff rounds have been finished
        """
        if not self.is_round_complete('wild_card'):
            return 'wild_card'
        elif not self.is_round_complete('divisional'):
            return 'divisional'
        elif not self.is_round_complete('conference'):
            return 'conference'
        elif not self.is_round_complete('super_bowl'):
            return 'super_bowl'
        else:
            return 'complete'

    def _get_expected_game_count(self, round_name: str) -> int:
        """
        Get the expected number of games for a playoff round.

        This method returns the standard NFL playoff game counts:
        - Wild Card Round: 6 games (3 per conference)
        - Divisional Round: 4 games (2 per conference)
        - Conference Championships: 2 games (1 per conference)
        - Super Bowl: 1 game

        Args:
            round_name: The name of the round ('wild_card', 'divisional',
                       'conference', or 'super_bowl')

        Returns:
            The expected number of games for the specified round

        Raises:
            ValueError: If an invalid round name is provided
        """
        expected_counts = {
            'wild_card': 6,
            'divisional': 4,
            'conference': 2,
            'super_bowl': 1
        }

        if round_name not in expected_counts:
            raise ValueError(f"Invalid round name: {round_name}")

        return expected_counts[round_name]

    def add_completed_game(self, round_name: str, game: Dict[str, Any]) -> None:
        """
        Record a completed playoff game for a specific round.

        This method adds a game result to the completed games tracking and
        updates the total games played counter. Duplicate games (by event_id)
        are automatically prevented.

        Args:
            round_name: The playoff round the game belongs to ('wild_card',
                       'divisional', 'conference', or 'super_bowl')
            game: Dictionary containing game result data (score, teams, date, etc.)
                  Must include 'event_id' for duplicate detection.

        Note:
            The game dictionary should contain all relevant game information
            needed for bracket advancement and reporting (team IDs, scores,
            winner, game date, etc.)
        """
        if round_name not in self.completed_games:
            self.completed_games[round_name] = []

        # Duplicate detection: check if event_id already exists
        event_id = game.get('event_id', '')
        if event_id:
            existing_ids = [g.get('event_id', '') for g in self.completed_games[round_name]]
            if event_id in existing_ids:
                # Duplicate found - skip adding
                return

        self.completed_games[round_name].append(game)
        self.total_games_played += 1

    def validate(self) -> List[str]:
        """
        Validate the current playoff state for consistency and correctness.

        This method performs comprehensive validation checks including:
        1. Date validation: Ensures current_date is in valid playoff window (January-February)
        2. Round progression: Verifies rounds are completed in correct order
        3. State consistency: Checks for logical inconsistencies in the state

        Returns:
            A list of validation error messages. Empty list means state is valid.

        Examples:
            >>> state = PlayoffState(current_date=Date(2025, 3, 1))
            >>> errors = state.validate()
            >>> if errors:
            ...     print("Validation errors:", errors)
            Validation errors: ['Current date 2025-03-01 is outside valid playoff window (January-February)']
        """
        errors = []

        # Validate current date is in playoff window (January-February)
        if self.current_date is not None:
            if self.current_date.month not in (1, 2):
                errors.append(
                    f"Current date {self.current_date} is outside valid playoff window "
                    f"(January-February)"
                )

        # Validate round progression
        if self.current_round == 'divisional' and not self.is_round_complete('wild_card'):
            errors.append(
                "Cannot be in divisional round when wild_card round is incomplete"
            )

        if self.current_round == 'conference' and not self.is_round_complete('divisional'):
            errors.append(
                "Cannot be in conference round when divisional round is incomplete"
            )

        if self.current_round == 'super_bowl' and not self.is_round_complete('conference'):
            errors.append(
                "Cannot be in super_bowl round when conference round is incomplete"
            )

        # Validate game counts don't exceed expected values
        for round_name, games in self.completed_games.items():
            expected = self._get_expected_game_count(round_name)
            actual = len(games)
            if actual > expected:
                errors.append(
                    f"Round '{round_name}' has {actual} completed games but only "
                    f"{expected} games are expected"
                )

        # Validate total_games_played matches sum of completed games
        actual_total = sum(len(games) for games in self.completed_games.values())
        if self.total_games_played != actual_total:
            errors.append(
                f"total_games_played ({self.total_games_played}) does not match "
                f"actual completed games count ({actual_total})"
            )

        # Validate original_seeding exists if any games have been played
        if self.total_games_played > 0 and self.original_seeding is None:
            errors.append(
                "original_seeding must be set before games can be played"
            )

        # Validate brackets exist for rounds that have games
        for round_name, games in self.completed_games.items():
            if len(games) > 0 and round_name in self.brackets:
                if self.brackets[round_name] is None:
                    errors.append(
                        f"Bracket for round '{round_name}' must be initialized "
                        f"before games can be played"
                    )

        return errors

    def reset(self) -> None:
        """
        Reset playoff state to initial values.

        Clears all completed games, resets brackets, and returns to wild card round.
        Used when restarting playoffs or beginning a new season.
        """
        self.current_round = 'wild_card'
        self.original_seeding = None
        self.completed_games = {
            'wild_card': [],
            'divisional': [],
            'conference': [],
            'super_bowl': []
        }
        self.brackets = {
            'wild_card': None,
            'divisional': None,
            'conference': None,
            'super_bowl': None
        }
        self.total_games_played = 0
        self.total_days_simulated = 0
        self.current_date = None
